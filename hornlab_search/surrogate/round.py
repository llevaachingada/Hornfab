"""CP-8d round helper: solve a ``proposals.json`` with the real BEM and report ``round_report``.

The surrogate's 30 exploit + 10 explore designs are only a HYPOTHESIS until each one is solved by
the real solver. ``run_round`` evaluates every proposal through the NORMAL
``hornlab_search.search.evaluate.evaluate`` path (so the dataset records, ndjson rows, solve cache
and traces all behave exactly as in a search), compares the solved proposals with a random baseline,
and writes ``ismo_round1.json`` next to the round.

OFFLINE TESTS: only argument/file validation is covered offline (``load_proposals`` and the CLI's
pre-flight checks in ``_cmd_surrogate``); the solve path needs the real backend and a GPU and is
therefore NOT exercised by the offline test suite. Do not claim the round ran from an offline run.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import numpy as np

from ..dataset.record import DEFAULT_TRACE_FRACTION, to_jsonable
from ..objective.terms import PENALTY_FAILED
from ..search import evaluate as eval_mod
from ..search import rundir
from ..types import Design
from . import ismo

#: How many early (non-surrogate-picked) SOLVED evaluations of a search are the random baseline.
N_RANDOM = 40

#: The failure convention, recorded verbatim next to every ``random_true_J`` block.
RANDOM_CONVENTION = (
    "a proposal whose BEM solve FAILED carries the finite penalty PENALTY_FAILED (1.0e3), not "
    "NaN; ismo.round_report coerces any true_J >= PENALTY_FAILED to NaN (an unsolved proposal) so "
    "a penalty cannot masquerade as a real objective and drag the median, and counts it in "
    "n_solved_failed. Failure / non-finite objective rows in the random baseline are excluded here "
    "before the call, so only solved rows enter median_random_J.")


# ------------------------------------------------------------------ proposals

_REQUIRED_FIELDS = ("family", "params", "kind", "pred_J", "std")


def load_proposals(path) -> list[dict]:
    """Load and validate a ``proposals.json`` written by ``surrogate propose``. Raises ``ValueError``
    naming the file and the problem; returns a list of
    ``{family, params, kind, pred_J, std}`` dicts (offline, no torch, no solver)."""
    p = Path(path)
    if not p.is_file():
        raise ValueError(f"proposals file does not exist: {p}")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise ValueError(f"proposals file {p} is not valid JSON: {exc}") from None
    if not isinstance(data, list) or not data:
        raise ValueError(f"proposals file {p} must be a non-empty JSON list")
    out = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"proposals[{i}] is not an object")
        missing = [k for k in _REQUIRED_FIELDS if k not in item]
        if missing:
            raise ValueError(f"proposals[{i}] is missing field(s) {missing}")
        if not isinstance(item["params"], dict):
            raise ValueError(f"proposals[{i}].params must be an object")
        if item["kind"] not in ("exploit", "explore"):
            raise ValueError(
                f"proposals[{i}].kind must be 'exploit' or 'explore', got {item['kind']!r}")
        try:
            pred_j, std = float(item["pred_J"]), float(item["std"])
        except (TypeError, ValueError):
            raise ValueError(f"proposals[{i}].pred_J / .std must be numbers") from None
        out.append({"family": str(item["family"]), "params": dict(item["params"]),
                    "kind": str(item["kind"]), "pred_J": pred_j, "std": std})
    return out


# ------------------------------------------------------------------ random baseline


def _load_random_baseline(random_run, *, n: int = N_RANDOM) -> tuple[list[float], dict]:
    """(first ``n`` solved objectives, provenance) from a search run's ``search.ndjson``.

    ``random_true_J`` is the search's early evaluations (CMA generation-0 samples and the seed),
    which were NOT surrogate-picked: they are the honest "is the surrogate better than random"
    baseline. Only ``ok`` rows with a finite objective below ``PENALTY_FAILED`` are used; the rest
    are counted as excluded (see ``RANDOM_CONVENTION``)."""
    prov = {"run_id": None, "path": None, "rows_scanned": 0, "rows_used": 0,
            "failure_rows_excluded": 0, "solved_rows_available": 0,
            "failure_handling": "no random baseline supplied; median_random_J is NaN",
            "convention": RANDOM_CONVENTION}
    if random_run is None:
        return [], prov
    run_dir = Path(random_run)
    ndjson = run_dir / "search.ndjson"
    prov["run_id"] = run_dir.name
    prov["path"] = str(ndjson)
    if not ndjson.exists():
        prov["failure_handling"] = "search.ndjson not found; no random baseline"
        return [], prov
    rows = eval_mod.read_ndjson(ndjson)
    solved, failed = [], 0
    for r in rows:
        obj = r.get("objective")
        if (r.get("ok") and obj is not None and np.isfinite(float(obj))
                and float(obj) < PENALTY_FAILED):
            solved.append(float(obj))
        else:
            failed += 1
    prov.update({"rows_scanned": len(rows), "rows_used": min(n, len(solved)),
                 "failure_rows_excluded": failed, "solved_rows_available": len(solved),
                 "failure_handling": ("ok=False and penalty/NaN objective rows are EXCLUDED "
                                      "before round_report; only solved rows are used")})
    return solved[:n], prov


def _min_pairwise_unit_cube_distance(space, designs: list[Design]):
    """Smallest pairwise Euclidean distance between designs mapped into the unit cube, or None when
    fewer than two are given. A tiny value means the 'different' proposals are near-clones."""
    if len(designs) < 2:
        return None
    U = np.stack([space.normalize(d) for d in designs])
    diff = U[:, None, :] - U[None, :, :]
    dist = np.sqrt((diff ** 2).sum(-1))
    iu = np.triu_indices(len(designs), k=1)
    vals = dist[iu]
    return float(vals.min()) if vals.size else None


def _bundle_provenance(bundle_path) -> dict:
    if bundle_path is None:
        return {"path": None, "gates_passed": None, "n_heldout": None,
                "problem": "no bundle path supplied"}
    p = Path(bundle_path)
    try:
        from .model import load_bundle
        gr = (load_bundle(p).get("meta") or {}).get("gate_report") or {}
        return {"path": str(p), "gates_passed": gr.get("gates_passed"),
                "n_heldout": gr.get("n_heldout"), "problem": None}
    except Exception as exc:  # noqa: BLE001 - report a missing/corrupt bundle, do not hide it
        return {"path": str(p), "gates_passed": None, "n_heldout": None,
                "problem": f"{type(exc).__name__}: {exc}"}


# ------------------------------------------------------------------ the round


def run_round(proposals_path, cfg, *, mode: str = "screen", out_dir=None, bundle_path=None,
              store=None, cache_dir=None, random_run=None,
              trace_fraction: float = DEFAULT_TRACE_FRACTION, backend=None) -> dict:
    """Solve every proposal with the real backend, compare to the random baseline, write
    ``ismo_round1.json``.

    ``out_dir`` is created if absent; the solves happen in a FRESH run dir ``out_dir/round1`` with
    its own ``search.ndjson`` (via ``make_context(..., ndjson=...)``). ``random_run`` is an
    existing search run dir whose early SOLVED evaluations seed ``random_true_J``; when omitted and
    ``out_dir`` itself holds a ``search.ndjson``, ``out_dir`` is used, otherwise the baseline is
    empty. ``store``/``cache_dir``/``backend`` allow reuse of an existing dataset, cache and backend
    (the CLI passes them). Returns the ``ismo_round1.json`` payload.

    This is an OPERATIONAL helper: it runs one real solve per proposal. Offline tests cover only
    ``load_proposals`` and the CLI's pre-flight validation, never this function's solve path.
    """
    if mode not in ("screen", "verify", "final"):
        raise ValueError(f"mode must be screen|verify|final, got {mode!r}")
    if out_dir is None:
        raise ValueError("out_dir is required")
    props = load_proposals(proposals_path)                 # validation before any heavy import
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if random_run is None and (out_dir / "search.ndjson").exists():
        random_run = out_dir
    run_dir = out_dir / "round1"
    run_dir.mkdir(parents=True, exist_ok=True)

    from .. import cli as _cli
    from ..design.space import DesignSpace
    from ..search.evaluate import evaluate, make_context
    from ..solve import worker

    space = DesignSpace.from_config(cfg)
    n_before = len(store) if store is not None else 0
    worker.install_handlers()
    backend = backend if backend is not None else _cli._backend(cfg)
    worker.warm(backend)
    ctx = make_context(cfg, store, cache_dir=cache_dir, trace_fraction=trace_fraction,
                       ndjson=run_dir / "search.ndjson")

    rows = []
    for p in props:
        design = Design(p["family"], dict(p["params"]))
        t0 = time.perf_counter()
        ev = evaluate(design, space, cfg, mode, run_dir, store, backend, ctx=ctx)
        rows.append({"kind": p["kind"], "design_hash": design.hash(), "pred_J": p["pred_J"],
                     "true_J": float(ev.objective), "ok": not bool(ev.error), "error": ev.error,
                     "seconds": time.perf_counter() - t0})
    n_after = len(store) if store is not None else 0

    random_vals, provenance = _load_random_baseline(random_run)
    report = ismo.round_report([r["pred_J"] for r in rows], [r["true_J"] for r in rows],
                               random_vals)

    solved = [r for r in rows
              if r["ok"] and np.isfinite(r["true_J"]) and r["true_J"] < PENALTY_FAILED]

    def _median(kind: str) -> float:
        v = [r["true_J"] for r in solved if r["kind"] == kind]
        return float(np.median(v)) if v else float("nan")

    med_exploit, med_explore = _median("exploit"), _median("explore")
    exploits = [Design(p["family"], dict(p["params"])) for p in props if p["kind"] == "exploit"]
    spread = _min_pairwise_unit_cube_distance(space, exploits)

    payload = {
        "report": report,
        "rows": rows,
        "medians": {
            "pooled_true_J": report["median_true_J"],
            "exploit_true_J": med_exploit, "explore_true_J": med_explore,
            "n_exploit_solved": sum(1 for r in solved if r["kind"] == "exploit"),
            "n_explore_solved": sum(1 for r in solved if r["kind"] == "explore"),
            "random_J": report["median_random_J"],
        },
        "parameter_spread": {
            "min_pairwise_unit_cube_distance_exploit": spread,
            "n_exploit": len(exploits),
            "n_explore": sum(1 for p in props if p["kind"] == "explore"),
            "keys": space.keys(),
        },
        "random_true_J": {"provenance": provenance, "values": random_vals},
        "store_records_before": n_before,
        "store_records_after": n_after,
        "bundle": _bundle_provenance(bundle_path),
        "config_sha": rundir.config_sha(cfg.raw),
        "mode": mode,
        "proposals_path": str(Path(proposals_path)),
        "round_dir": str(run_dir),
        "generated_utc": rundir.utc_now(),
    }
    dest = out_dir / "ismo_round1.json"
    tmp = dest.with_name(dest.name + ".tmp")
    tmp.write_text(json.dumps(to_jsonable(payload), indent=1, sort_keys=True, allow_nan=False),
                   encoding="utf-8")
    os.replace(tmp, dest)

    fmt = lambda v: "nan" if v is None or not np.isfinite(v) else f"{v:.6g}"   # noqa: E731
    print(f"surrogate round: pooled median true J {fmt(report['median_true_J'])} "
          f"(exploit {fmt(med_exploit)} n={payload['medians']['n_exploit_solved']}; "
          f"explore {fmt(med_explore)} n={payload['medians']['n_explore_solved']}); "
          f"random median {fmt(report['median_random_J'])}")
    print(f"  parameter spread: min pairwise unit-cube distance among exploit designs "
          f"{'n/a' if spread is None else format(spread, '.4g')} ({len(exploits)} exploits)")
    print(f"  random baseline: {provenance['rows_used']} solved rows of "
          f"{provenance['rows_scanned']} scanned from {provenance['run_id']} "
          f"({provenance['failure_rows_excluded']} failure rows excluded)")
    print(f"  round report: working={report['working']}, "
          f"spearman_on_proposals={report['spearman_on_proposals']}, "
          f"n_solved_failed={report['n_solved_failed']}, store {n_before}->{n_after} records")
    print(f"surrogate round OK: {len(rows)} proposals solved -> {dest}")
    return payload
