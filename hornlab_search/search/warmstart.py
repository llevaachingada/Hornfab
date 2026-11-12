"""B.1 (day 2026-11-12): data warm start — ``search.warm_start``.

``search.warm_start: {from_runs: [<run dir>...], top_k: 10, sigma_from_spread: true,
allow_cross_brief: false}`` starts the CMA mean at the best valid design among the given run
directories (SAME family and the SAME searched knob names, normalized in THIS config's box;
designs outside the box are clipped and counted). With ``sigma_from_spread``, ``sigma0``
becomes the median per-knob spread of the ``top_k`` best valid rows (normalized max-min),
clamped to ``[0.05, cfg.search.sigma0]``; absent/insufficient data keeps the config's sigma0.

Runs of another objective version or another brief (``brief_file``/embedded ``brief`` in the
run's config snapshot) are refused with ConfigError unless ``allow_cross_brief: true``.

The warm start never changes the solve hash: it only picks the initial mean/sigma of the ES;
the solve hash formula (design hash - mesh hash - solve hash) is untouched. run.json gets a
``warm_start`` block with the source hashes. Absent ``search.warm_start`` = today's behaviour
(the caller keeps the config seed/sigma byte for byte).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from .rundir import read_json
from .evaluate import read_ndjson

SIGMA_FLOOR = 0.05                 # plan B.1: sigma_from_spread clamps into [0.05, sigma0]


class WarmStartError(Exception):
    """A configured warm_start source is unusable (mapped onto ConfigError by the caller)."""


def _identity(run_dir: Path) -> tuple[int, object, dict]:
    """(objective_version, brief identity, run.json) of a source run from its config snapshot."""
    rj = read_json(run_dir / "run.json")
    if not rj:
        raise WarmStartError(f"{run_dir}: no run.json (not a started run directory?)")
    raw = rj.get("config") if isinstance(rj.get("config"), dict) else {}
    objective = raw.get("objective") if isinstance(raw.get("objective"), dict) else None
    version = int(objective.get("version", 1)) if objective is not None else \
        int(rj.get("objective_version", 1))
    brief = raw.get("brief_file") or (raw.get("brief") if isinstance(raw.get("brief"), dict)
                                      else None)
    return version, brief, rj


def _searched_knobs(rj: dict) -> list[str] | None:
    raw = rj.get("config") if isinstance(rj.get("config"), dict) else {}
    bounds = raw.get("bounds") if isinstance(raw.get("bounds"), dict) else None
    if not bounds:
        return None
    return sorted(k for k, b in bounds.items()
                  if not isinstance(b, dict) or b.get("search", True))


def mean_and_sigma(cfg, space) -> tuple[object | None, dict | None]:
    """(warm seed Design, run.json record) or ``(None, None)`` when ``search.warm_start`` is
    absent (today's behaviour byte for byte)."""
    ws_block = getattr(getattr(cfg, "search", None), "warm_start", None)
    if not ws_block or not ws_block.get("from_runs"):
        return None, None
    allow_cross = bool(ws_block.get("allow_cross_brief", False))
    version_self = int(getattr(cfg, "objective_version", 1))
    raw_self = getattr(cfg, "raw", None)
    raw_self = raw_self if isinstance(raw_self, dict) else {}
    brief_self = raw_self.get("brief_file") or (
        raw_self.get("brief") if isinstance(raw_self.get("brief"), dict) else None)
    keys = space.keys()
    family = str(cfg.family)
    best: tuple[float, str, np.ndarray, dict] | None = None
    top: list[tuple[float, str, np.ndarray]] = []
    clipped = 0
    rows_seen = 0
    sources = []
    for raw_path in ws_block["from_runs"]:
        run_dir = Path(raw_path)
        version, brief, rj = _identity(run_dir)
        if (version != version_self or brief != brief_self) and not allow_cross:
            raise WarmStartError(
                f"{run_dir}: warm_start refuses objective version/brief mismatch "
                f"(run v{version}, this config v{version_self}; set "
                f"search.warm_start.allow_cross_brief: true to override)")
        if str(rj.get("family")) != family:
            raise WarmStartError(f"{run_dir}: warm_start refuses family mismatch "
                                 f"(run {rj.get('family')!r}, this config {family!r})")
        knobs = _searched_knobs(rj)
        if knobs is None or knobs != keys:
            raise WarmStartError(
                f"{run_dir}: warm_start refuses knob-name mismatch (run {knobs!r} vs this "
                f"config {keys!r} — the SAME searched knobs are required)")
        rows = read_ndjson(run_dir / "search.ndjson")
        here = [r for r in rows if r.get("ok") and isinstance(r.get("params"), dict)]
        rows_seen += len(rows)
        for r in here:
            try:
                unit = [space.bounds[k].to_unit(float(_param_get(space, r["params"], k)))
                        for k in keys]
            except KeyError as exc:
                raise WarmStartError(f"{run_dir}: row {r.get('n')} lacks knob {exc}") from None
            if any(c[1] for c in unit):
                clipped += 1
            vec = np.asarray([c[0] for c in unit], dtype=float)
            entry = (float(r["objective"]), str(r.get("design_hash")), vec)
            top.append(entry)
            if best is None or entry[0] < best[0]:
                best = (entry[0], entry[1], vec, r["params"])
        sources.append({"path": str(run_dir), "config_sha": rj.get("config_sha"),
                        "objective_version": version, "rows": len(rows), "valid": len(here)})
    if best is None:
        raise WarmStartError(f"warm_start: no valid (ok) row among {ws_block['from_runs']}")
    top_k_n = max(1, int(ws_block.get("top_k", 10)))
    top_k = sorted(top, key=lambda t: (t[0], t[1]))[:top_k_n]
    design = space.denormalize(best[2])            # the CMA mean: the best valid design, in-box
    sigma0 = float(cfg.search.sigma0)
    sigma_record = None
    if bool(ws_block.get("sigma_from_spread", True)) and len(top_k) >= 2:
        stack = np.vstack([t[2] for t in top_k])
        spread = float(np.median(np.max(stack, axis=0) - np.min(stack, axis=0)))
        sigma0 = float(min(max(spread, SIGMA_FLOOR), float(cfg.search.sigma0)))
        sigma_record = {"median_spread": spread, "sigma0": sigma0, "top_k": len(top_k)}
    record = {"from_runs": [str(Path(p)) for p in ws_block["from_runs"]],
              "top_k": top_k_n, "sources": sources,
              "mean_design_hash": best[1], "mean_objective": best[0],
              "sigma0": sigma0, "sigma_from_spread": sigma_record,
              "rows_seen": rows_seen, "designs_clipped_to_box": clipped}
    return design, record


def _param_get(space, params: dict, key: str) -> object:
    from ..design import families
    return families.param_get(space.family, params, key)
