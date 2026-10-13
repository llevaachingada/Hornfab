"""One candidate, end to end. ``evaluate`` NEVER raises (the search loop is never killed by one
bad candidate), with ONE deliberate exception: the mesh consistency errors (units bug, quadrants
vs symmetry flag, 01_CONTRACTS section 15) propagate and stop the run, because a wrong-units
horn solves fine and looks smooth.

Order of side effects for a non-cached candidate (08_TASK_PIPELINE section 3):
  mesh -> solve -> metrics -> objective -> solve cache -> traces -> DATASET RECORD -> ndjson row.
The dataset record is written BEFORE the ndjson append, so a crash between them loses a log line,
never a training record.

Cache semantics (documented choices, see NOTES_FOR_SENIOR):
  * ``ctx.known`` is the in-run memo, preloaded from ``search.ndjson`` on resume. A hit costs
    nothing, writes nothing (not a new ndjson row, not a new dataset record), consumes no budget.
    Successful rows and DETERMINISTIC failures (invalid geometry, mesh too large) are memoized;
    solver failures are not (a retry may succeed).
  * ``ctx.cache_dir/solve/<design>-<mesh>-<solve>/`` is the cross-run solve cache (hit requires
    ``ok: true``). A hit recomputes metrics and the objective from the stored Response with the
    CURRENT target and weights, appends an ndjson row flagged ``cached``, and writes a dataset
    record only if the store has none for that (design, mode) yet.
"""
from __future__ import annotations

import dataclasses
import json
import logging
import os
import subprocess
import time
import traceback
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, distribution
from pathlib import Path

import numpy as np

from .. import config as config_mod
from ..dataset.record import DEFAULT_TRACE_FRACTION, build_record, should_capture_traces, to_jsonable
from ..mesh.build import MeshConsistencyError, build_mesh
from ..metrics.compute import compute_metrics
from ..metrics.di import di_from_balloon, sin_theta_weights
from ..objective import PENALTY_FAILED, PENALTY_INVALID, objective, penalty_result
from ..solve import cache as solve_cache
from ..solve.base import theta_deg_from_dirs
from ..targets.spec import Target
from ..types import (Design, Evaluation, GeometryInvalidError, MeshResult, MeshTooLargeError,
                     MetricSet, Response, SolveOutcome)

log = logging.getLogger("hornlab_search.search.evaluate")

KIND_INVALID = "invalid_geometry"
KIND_TOO_LARGE = "mesh_too_large"
KIND_SOLVE = "solve_failed"
KIND_METRICS = "metrics_failed"
KIND_EXC = "exception"
#: Pure functions of the design: worth memoizing, and re-running them is wasted effort.
DETERMINISTIC_KINDS = (KIND_INVALID, KIND_TOO_LARGE)

TRACE_KIND = "p1_pressure_by_node+dp0_neumann_by_element"


# ------------------------------------------------------------------ provenance

_LIB_DISTS = {"hornlab_mesher": "hornlab_waveguide_mesher", "hornlab_beat_bem": "hornlab_beat_bem",
              "hornlab_bempp_bem": "hornlab_bempp_bem", "hornlab_plots": "hornlab_plots"}


def collect_lib_shas() -> dict:
    """The five SHAs every dataset record carries (record.REQUIRED_LIB_SHAS). The four HornLab
    packages come from each distribution's direct_url.json (the pinned git commit); this package's
    own commit from ``git rev-parse HEAD``. ``"unknown"`` when it cannot be determined."""
    out = {}
    for key, dist_name in _LIB_DISTS.items():
        sha = "unknown"
        for name in (dist_name, dist_name.replace("_", "-")):
            try:
                raw = distribution(name).read_text("direct_url.json")
            except PackageNotFoundError:
                continue
            if raw:
                try:
                    sha = (json.loads(raw).get("vcs_info") or {}).get("commit_id") or "unknown"
                except ValueError:
                    pass
            break
        out[key] = sha
    sha = "unknown"
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=Path(__file__).resolve().parents[2],
                           capture_output=True, text=True, timeout=10)
        if r.returncode == 0 and r.stdout.strip():
            sha = r.stdout.strip()
    except Exception:  # noqa: BLE001 - provenance is best effort
        pass
    out["hornlab_search"] = sha
    return out


# ------------------------------------------------------------------ context


@dataclass
class EvalContext:
    """Everything ``evaluate`` needs besides its contract arguments, shared across a run."""
    target: Target
    weights: dict
    lib_shas: dict
    cache_dir: Path | None = None
    trace_fraction: float = DEFAULT_TRACE_FRACTION
    known: dict = field(default_factory=dict)          # key -> lite Evaluation (resume / in-run)
    store_seen: set = field(default_factory=set)       # {(design_hash, mode, ok)} already in the store
    n_rows: int = 0                                    # rows in search.ndjson (next row number)
    counters: Counter = field(default_factory=Counter)
    write_ndjson: bool = True

    @property
    def solve_cache_root(self) -> Path | None:
        return None if self.cache_dir is None else Path(self.cache_dir) / "solve"

    @property
    def mesh_cache_root(self) -> Path | None:
        return None if self.cache_dir is None else Path(self.cache_dir) / "mesh"


def make_context(cfg, store=None, *, cache_dir=None, lib_shas=None,
                 trace_fraction: float = DEFAULT_TRACE_FRACTION, ndjson: Path | None = None) -> EvalContext:
    ctx = EvalContext(target=Target.from_dict(cfg.target_raw), weights=dict(cfg.weights),
                      lib_shas=lib_shas if lib_shas is not None else collect_lib_shas(),
                      cache_dir=None if cache_dir is None else Path(cache_dir),
                      trace_fraction=float(trace_fraction))
    if store is not None:
        ctx.store_seen = {(e.get("design_hash"), e.get("mode"), bool(e.get("ok"))) for e in store.index}
    if ndjson is not None:
        ctx.known, ctx.n_rows = load_known(ndjson)
    return ctx


# ------------------------------------------------------------------ metrics from a Response


def mouth_dims_m(mesh: MeshResult) -> tuple[float, float]:
    """(width along x, height along y) of the FULL horn, from the solved mesh's bounding box and
    the symmetry plane that reduced it. Includes the freestanding shell, so it is the outer
    envelope; an approximation of the mouth used only for the f_break design check."""
    b = mesh.bbox_m
    sp = mesh.symmetry_plane or ""
    w = (b[3] - b[0]) * (2.0 if "yz" in sp else 1.0)
    h = (b[4] - b[1]) * (2.0 if "xz" in sp else 1.0)
    return float(w), float(h)


def throat_radius_m(design: Design) -> float | None:
    r0 = design.params.get("r0_mm")
    return float(r0) / 1000.0 if isinstance(r0, (int, float)) and r0 > 0 else None


def metrics_from_response(resp: Response, target: Target, *, mesh: MeshResult | None = None,
                          design: Design | None = None) -> MetricSet:
    """``compute_metrics`` with the balloon DI done correctly.

    The solver's balloon is a THETA-PHI grid (``resp.meta['balloon_grid']``), not the equal-area
    set ``compute_metrics`` assumes (equal weights would over-count the poles). compute_metrics
    is not ours to edit, so the sin(theta) quadrature is done HERE with
    ``di_from_balloon(weights=sin_theta_weights(theta))`` and handed to compute_metrics as a
    one-column "balloon" whose single power equals the weighted mean, which makes compute_metrics'
    own equal-weight DI come out as exactly the weighted DI (and keeps di_source == 'balloon',
    its slope, mean and every other scalar consistent). A balloon without ``balloon_grid`` in meta
    is taken to be equal-area (e.g. a Fibonacci set) and passed through untouched.
    """
    kw = {}
    if mesh is not None:
        kw["mouth_h_m"], kw["mouth_v_m"] = mouth_dims_m(mesh)
    if design is not None:
        kw["throat_radius_m"] = throat_radius_m(design)
    has_balloon = resp.spl_balloon_db is not None and resp.balloon_dirs is not None
    if has_balloon and resp.meta.get("balloon_grid") is not None:
        bal = np.asarray(resp.spl_balloon_db, dtype=float)
        w = sin_theta_weights(theta_deg_from_dirs(np.asarray(resp.balloon_dirs, dtype=float)))
        ax = resp.axis_index
        collapsed = np.empty((bal.shape[0], 1))
        for i in range(bal.shape[0]):
            di = di_from_balloon(bal[i], resp.spl_h_db[i, ax], weights=w)
            # di_from_balloon(collapsed) = -10 log10(10**((collapsed - ax)/10)) = ax - collapsed
            collapsed[i, 0] = float(resp.spl_h_db[i, ax]) - di
        resp = dataclasses.replace(resp, spl_balloon_db=collapsed,
                                   balloon_dirs=np.array([[0.0, 0.0, 1.0]]))
    return compute_metrics(resp, target, **kw)


# ------------------------------------------------------------------ rows (search.ndjson)


def _arr(x):
    return None if x is None else np.asarray(x, dtype=float).tolist()


def metrics_to_json(m: MetricSet | None) -> dict | None:
    if m is None:
        return None
    return to_jsonable({"freqs_hz": m.freqs_hz, "bw_h_deg": m.bw_h_deg, "bw_v_deg": m.bw_v_deg,
                        "di_db": m.di_db, "di_source": m.di_source, "ripple_h_db": m.ripple_h_db,
                        "ripple_v_db": m.ripple_v_db, "on_axis_db": m.on_axis_db,
                        "z_throat_real": m.z_throat_real, "scalars": m.scalars})


def _nanarr(x) -> np.ndarray:
    return np.array([np.nan if v is None else v for v in x], dtype=float)


def metrics_from_json(d: dict | None) -> MetricSet | None:
    if not d:
        return None
    return MetricSet(
        freqs_hz=_nanarr(d["freqs_hz"]), bw_h_deg=_nanarr(d["bw_h_deg"]),
        bw_v_deg=_nanarr(d["bw_v_deg"]), di_db=_nanarr(d["di_db"]), di_source=d["di_source"],
        ripple_h_db=_nanarr(d["ripple_h_db"]), ripple_v_db=_nanarr(d["ripple_v_db"]),
        on_axis_db=_nanarr(d["on_axis_db"]),
        z_throat_real=None if d.get("z_throat_real") is None else _nanarr(d["z_throat_real"]),
        scalars=dict(d.get("scalars") or {}))


def error_kind(error: str) -> str:
    return error.split(":", 1)[0] if error else ""


def evaluation_to_row(ev: Evaluation, mode: str, n: int, seconds: dict) -> dict:
    m = ev.mesh
    out = ev.outcome
    return to_jsonable({
        "n": n, "mode": mode, "key": f"{ev.design_hash}-{ev.mesh_hash}-{ev.solve_hash}",
        "design_hash": ev.design_hash, "mesh_hash": ev.mesh_hash, "solve_hash": ev.solve_hash,
        "family": ev.design.family, "params": ev.design.params,
        "objective": ev.objective, "terms": ev.terms, "ok": not ev.error, "error": ev.error,
        "kind": error_kind(ev.error), "cached": ev.cached, "seconds": seconds,
        "n_dof": None if m is None else m.n_dof,
        "n_triangles": None if m is None else m.n_triangles,
        "quadrants": None if m is None else m.quadrants,
        "symmetry_plane": None if m is None else m.symmetry_plane,
        "bbox_m": None if m is None else list(m.bbox_m),
        "res_mm": None if m is None else m.res_mm,
        "peak_vram_mb": None if out is None else out.peak_vram_mb,
        "metrics": metrics_to_json(ev.metrics),
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    })


def row_to_evaluation(row: dict) -> Evaluation:
    """A lite Evaluation (no Response) from an ndjson row; ``cached`` is True."""
    mesh = None
    if row.get("n_triangles") is not None:
        mesh = MeshResult(path="", n_triangles=int(row["n_triangles"]), n_dof=row.get("n_dof"),
                          quadrants=row.get("quadrants") or "", symmetry_plane=row.get("symmetry_plane"),
                          res_mm=dict(row.get("res_mm") or {}),
                          bbox_m=tuple(row.get("bbox_m") or (0,) * 6),
                          seconds=float((row.get("seconds") or {}).get("mesh") or 0.0))
    ok = bool(row.get("ok"))
    outcome = SolveOutcome(ok, None, float((row.get("seconds") or {}).get("solve") or 0.0),
                           row.get("peak_vram_mb"), "" if ok else str(row.get("error", "")))
    return Evaluation(
        design_hash=row["design_hash"], design=Design(row["family"], dict(row["params"])),
        mesh_hash=row["mesh_hash"], solve_hash=row["solve_hash"], objective=float(row["objective"]),
        terms=dict(row["terms"]), metrics=metrics_from_json(row.get("metrics")), mesh=mesh,
        outcome=outcome, cached=True, error=str(row.get("error") or ""))


def append_ndjson(path: Path, row: dict) -> None:
    """One line, opened in append mode per write, flushed and fsynced: a hard kill leaves every
    earlier line intact and at worst a torn LAST line (which readers skip)."""
    line = json.dumps(row, allow_nan=False, separators=(",", ":")) + "\n"
    with open(path, "ab") as f:
        f.write(line.encode("utf-8"))
        f.flush()
        os.fsync(f.fileno())


def read_ndjson(path: Path) -> list[dict]:
    """Every parseable line; a torn final line (hard kill) is skipped."""
    rows = []
    p = Path(path)
    if not p.exists():
        return rows
    for i, line in enumerate(p.read_bytes().decode("utf-8", errors="replace").splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except ValueError:
            log.warning("%s line %d is not valid JSON (torn write?); skipped", p, i + 1)
    return rows


def load_known(path: Path) -> tuple[dict, int]:
    """({key: lite Evaluation}, number of rows) from an existing search.ndjson."""
    rows = read_ndjson(path)
    known = {}
    for r in rows:
        if r.get("ok") or r.get("kind") in DETERMINISTIC_KINDS:
            try:
                known[r["key"]] = row_to_evaluation(r)
            except Exception as exc:  # noqa: BLE001 - a bad old row is skipped, not fatal
                log.warning("could not reload ndjson row %s: %s", r.get("n"), exc)
    return known, len(rows)


# ------------------------------------------------------------------ evaluate


def _grid_info(mesh_dir: Path) -> tuple[float | None, dict]:
    """(area_m2 of the solved mesh, mesh.grid block) from build_mesh's mesh_meta.json.

    The mesher's structured surface sampling is ``angular_segments x length_segments`` (defaults 64
    x 32 in hornlab_mesher). ``available`` is True: the grid itself is reachable through the
    mesher's public ``config_builder.build_point_grid`` (TOOLCHAIN C4) and is regenerated from the
    recorded params; it is not stored per record."""
    area = None
    seg = {"angular_segments": 64, "length_segments": 32}
    try:
        meta = json.loads((Path(mesh_dir) / "mesh_meta.json").read_text(encoding="utf-8"))
        area = float(meta["summary"]["area_m2"])
        msec = (meta.get("mesher_config") or {}).get("mesh") or {}
        for k in seg:
            if msec.get(k) is not None:
                seg[k] = int(msec[k])
    except Exception as exc:  # noqa: BLE001
        log.debug("no mesh_meta.json in %s: %s", mesh_dir, exc)
    return area, {**seg, "available": True}


def _write_json(path: Path, obj) -> None:
    path.write_text(json.dumps(to_jsonable(obj), indent=1, sort_keys=True), encoding="utf-8")


def evaluate(design: Design, space, cfg, mode: str, run_dir, store, backend, *,
             ctx: EvalContext | None = None) -> Evaluation:
    """One candidate, end to end. NEVER raises (except ``MeshConsistencyError``, see module doc).

    ``space`` is accepted for the contract signature (a surrogate evaluator will use it); ``ctx``
    carries the target, weights, caches and counters shared across a run (built on the fly when
    omitted, which is what a one-off call wants).
    """
    # ABSOLUTE: the Julia host resolves a relative mesh path against its own working directory
    # (found live: `--resume runs\<dir>` made every solve fail with "opening file ... No such file").
    run_dir = Path(run_dir).resolve()
    ctx = ctx or make_context(cfg, store)
    t_start = time.perf_counter()
    mspec = config_mod.mesh_spec(mode, cfg)
    sspec = config_mod.solve_spec(mode, cfg)
    dh, mh, sh = design.hash(), mspec.hash(), sspec.hash()
    key = f"{dh}-{mh}-{sh}"

    hit = ctx.known.get(key)
    if hit is not None:
        ctx.counters["cache_hits_run"] += 1
        log.info("eval %s J=%.4f cached=True (in-run/resume)", dh, hit.objective)
        return dataclasses.replace(hit, design=design)

    design_dir = run_dir / "designs" / dh
    st: dict = {"mesh": None, "outcome": None, "resp": None, "metrics": None, "kind": "", "err": "",
                "from_disk": False, "area": None, "grid": None, "raw_traces": None, "J": None,
                "terms": None}
    try:
        _compute(design, cfg, mode, mspec, sspec, key, design_dir, backend, ctx, st)
    except MeshConsistencyError:
        raise                                   # units / symmetry bug: stop the run (section 15)
    except Exception as exc:  # noqa: BLE001 - the contract: any unexpected exception is a penalty row
        st["kind"], st["err"] = KIND_EXC, f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
        log.error("evaluation %s raised: %s", dh, st["err"][:2000])

    kind = st["kind"]
    if kind:
        err = f"{kind}: {st['err']}"
        J, terms = penalty_result(PENALTY_INVALID if kind in DETERMINISTIC_KINDS else PENALTY_FAILED)
    else:
        err, J, terms = "", st["J"], st["terms"]
    mesh, outcome = st["mesh"], st["outcome"]
    if outcome is None and kind:
        outcome = SolveOutcome(False, None, 0.0, None, err)
    ev = Evaluation(design_hash=dh, design=design, mesh_hash=mh, solve_hash=sh, objective=float(J),
                    terms=terms, metrics=None if kind else st["metrics"], mesh=mesh, outcome=outcome,
                    cached=bool(st["from_disk"] and not kind), error=err)
    seconds = {"mesh": 0.0 if mesh is None else float(mesh.seconds),
               "solve": 0.0 if (outcome is None or st["from_disk"]) else float(outcome.seconds),
               "total": time.perf_counter() - t_start}
    try:
        _persist(ev, mode, sspec, design_dir, ctx, store, st, seconds)
    except Exception:  # noqa: BLE001 - bookkeeping must not kill a search
        log.error("persisting evaluation %s failed:\n%s", dh, traceback.format_exc()[:2000])

    ctx.counters["cache_hits_disk" if ev.cached else "evaluated"] += 1
    if kind:
        ctx.counters[f"failure:{kind}"] += 1
    ctx.counters["mesh_seconds"] += seconds["mesh"]
    ctx.counters["solve_seconds"] += seconds["solve"]
    log.info("eval %s J=%.4f mesh=%.1fs solve=%.1fs dofs=%s cached=%s%s", dh, ev.objective,
             seconds["mesh"], seconds["solve"], None if mesh is None else mesh.n_dof, ev.cached,
             f" FAILED[{kind}]" if kind else "")
    return ev


def _compute(design, cfg, mode, mspec, sspec, key, design_dir, backend, ctx, st) -> None:
    """Mesh, solve, metrics, objective. Fills ``st``; sets st['kind'] on an expected failure."""
    try:
        mesh = build_mesh(design, mspec, cfg, design_dir, mode=mode, cache_dir=ctx.mesh_cache_root)
    except GeometryInvalidError as exc:
        st["kind"], st["err"] = KIND_INVALID, str(exc)
        return
    except MeshTooLargeError as exc:
        st["kind"], st["err"] = KIND_TOO_LARGE, str(exc)
        return
    st["mesh"] = mesh
    st["area"], st["grid"] = _grid_info(design_dir)

    resp = None
    root = ctx.solve_cache_root
    if root is not None:
        resp = solve_cache.lookup(key, root)
        if resp is not None:
            st["from_disk"] = True
            st["outcome"] = SolveOutcome(True, resp, 0.0, None, "cache hit")
    if resp is None:
        want_traces = (store_wants_traces(ctx, design) and hasattr(backend, "solve_traced"))
        if want_traces:
            outcome, raw = backend.solve_traced(mesh, sspec)
            st["raw_traces"] = raw
        else:
            outcome = backend.solve(mesh, sspec)
        st["outcome"] = outcome
        if not outcome.ok or outcome.response is None:
            st["kind"], st["err"] = KIND_SOLVE, outcome.message or "solve failed"
            log.error("solve failed for %s: %s", design.hash(), st["err"][:2000])
            return
        resp = outcome.response
    st["resp"] = resp
    if resp.n_dof is not None:
        mesh.n_dof = int(resp.n_dof)
    try:
        st["metrics"] = metrics_from_response(resp, ctx.target, mesh=mesh, design=design)
    except Exception as exc:  # noqa: BLE001
        st["kind"], st["err"] = KIND_METRICS, f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
        return
    st["J"], st["terms"] = objective(st["metrics"], True, ctx.target, ctx.weights)
    if root is not None and not st["from_disk"]:
        try:
            solve_cache.store(key, root, resp, {"ok": True, "objective": st["J"],
                                                "n_dof": resp.n_dof, "mode": mode})
        except Exception as exc:  # noqa: BLE001 - a cache write failure is not a failed candidate
            log.warning("solve cache write failed for %s: %s", key, exc)


def store_wants_traces(ctx: EvalContext, design: Design) -> bool:
    return ctx.trace_fraction > 0 and should_capture_traces(design.hash(), ctx.trace_fraction)


def _persist(ev: Evaluation, mode: str, sspec, design_dir: Path, ctx: EvalContext, store, st: dict,
             seconds: dict) -> None:
    """design dir files, boundary traces, DATASET RECORD, then the ndjson row (in that order)."""
    design_dir.mkdir(parents=True, exist_ok=True)
    _write_json(design_dir / "design.json", {"family": ev.design.family, "params": ev.design.params,
                                             "design_hash": ev.design_hash})
    ok = not ev.error
    _write_json(design_dir / "status.json", {
        "ok": ok, "error": ev.error, "kind": error_kind(ev.error), "objective": ev.objective,
        "mode": mode, "key": f"{ev.design_hash}-{ev.mesh_hash}-{ev.solve_hash}", "cached": ev.cached,
        "seconds": seconds, "terms": ev.terms})
    if ok:
        solve_cache.save_response(design_dir / "response.npz", st["resp"])
        _write_json(design_dir / "metrics.json", metrics_to_json(ev.metrics))

    # ---- boundary traces (1 in N, deterministic) and the dataset record
    trace_info = None
    if store is not None and ok and st["raw_traces"] is not None and not st["from_disk"]:
        try:
            from ..solve.traces import package_traces
            packaged = package_traces(ev.mesh, sspec, st["raw_traces"])
            rel = store.append_traces(ev.design_hash, packaged)
            trace_info = {"path": rel, "kind": TRACE_KIND}
        except Exception as exc:  # noqa: BLE001
            log.warning("trace capture for %s failed: %s", ev.design_hash, exc)
    if store is not None:
        seen = (ev.design_hash, mode, ok)
        if st["from_disk"] and seen in ctx.store_seen:
            log.debug("dataset already holds %s (%s); not duplicating a cache hit", *seen[:2])
        else:
            try:
                meta, arrays = build_record(
                    ev, ctx.target, ctx.lib_shas, solve_spec=sspec, area_m2=st["area"],
                    grid=st["grid"], traces=trace_info, trace_sample_fraction=ctx.trace_fraction)
                store.append(meta, arrays)
                ctx.store_seen.add(seen)
            except Exception as exc:  # noqa: BLE001 - ValueError from validate_record, or I/O
                log.error("dataset record for %s was NOT written: %s: %s", ev.design_hash,
                          type(exc).__name__, exc)

    # ---- the ndjson row, last
    row = evaluation_to_row(ev, mode, ctx.n_rows, seconds)
    if ctx.write_ndjson:
        append_ndjson(design_dir.parent.parent / "search.ndjson", row)
    ctx.n_rows += 1
    if ok or error_kind(ev.error) in DETERMINISTIC_KINDS:
        ctx.known[row["key"]] = row_to_evaluation(row)
