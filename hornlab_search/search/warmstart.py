"""B.1 (day 2026-11-12): data warm start — ``search.warm_start``.

``search.warm_start: {from_runs: [<run dir>...], top_k: 10, sigma_from_spread: true,
allow_cross_brief: false}`` starts the CMA mean at the best valid design among the given run
directories (SAME family and the SAME searched knob names, normalized in THIS config's box;
designs outside the box are clipped and counted). With ``sigma_from_spread``, ``sigma0``
becomes the median per-knob spread of the ``top_k`` best valid rows (normalized max-min),
clamped to ``[0.05, cfg.search.sigma0]``; absent/insufficient data keeps the config's sigma0.

Runs of another objective version or another brief (``brief_file``/embedded ``brief`` in the
run's config snapshot) are refused with ConfigError unless ``allow_cross_brief: true``.

P1b (senior optimizer audit, 2026-11-21): the OPT-IN ``search.warm_start.covariance`` block
additionally transfers the source run's CMA covariance shape into this config's box. It is
separately identified and never active unless requested; absent/false leaves the mean-only
warm start byte for byte unchanged. See :func:`covariance` for the exact convention.

The warm start never changes the solve hash: it only picks the initial mean/sigma/shape of the
ES; the solve hash formula (design hash - mesh hash - solve hash) is untouched. run.json gets a
``warm_start`` block with the source hashes. Absent ``search.warm_start`` = today's behaviour
(the caller keeps the config seed/sigma byte for byte).
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np

from .rundir import read_json
from .evaluate import read_ndjson

SIGMA_FLOOR = 0.05                 # plan B.1: sigma_from_spread clamps into [0.05, sigma0]

# P1b: conservative, deterministically recorded defaults for ``search.warm_start.covariance``.
COVARIANCE_DEFAULTS = {
    "blend": 0.25,          # weight of the transferred shape; 1 - blend keeps identity
    "eig_floor": 1.0e-6,
    "eig_cap": 1.0e6,
    "max_dim": 16,          # the covariance sidecar only stores C for n <= 16
    "scale_sigma": True,    # overall width = the declared/config sigma0
}


class WarmStartError(Exception):
    """A configured warm_start source is unusable (mapped onto ConfigError by the caller)."""


def _brief_key(raw: dict | None) -> tuple[str | None, str | None]:
    """Location-independent brief identity of a config/snapshot.

    The same brief may be spelled as a relative ``brief_file`` in a source run and an absolute
    path in a derived arm config, or embedded as a dict.  Compare the resolved content: the
    embedded payload is normalized (loader path/config metadata removed) and hashed; a bare
    ``brief_file`` falls back to its path string for the legacy message.
    """
    if not isinstance(raw, dict):
        return (None, None)
    brief = raw.get("brief")
    if isinstance(brief, dict):
        payload = {k: v for k, v in brief.items() if k not in ("path", "config", "brief")}
        payload["name"] = brief.get("name") or raw.get("name")
        objective = (brief.get("objective") if isinstance(brief.get("objective"), dict)
                     else raw.get("objective"))
        if isinstance(objective, dict):
            payload["version"] = objective.get("version")
        text = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
        return ("embedded", hashlib.sha256(text.encode("utf-8")).hexdigest())
    brief_file = raw.get("brief_file")
    if isinstance(brief_file, str) and brief_file.strip():
        return ("path", brief_file)
    return (None, None)


def _grid_key(raw: dict | None) -> str | None:
    """Identity of the solve grid REPLACEMENT policies in a config/snapshot.

    ``solve.freq_grid`` and ``solve.screen_grid`` (2026-11-23) change which frequencies are
    solved, and therefore what a stored J means, but they live in the config's ``solve`` block
    and are NOT part of the brief payload hashed by :func:`_brief_key`. A warm start from a run
    on a different grid would mix scores under one seed, so the guard compares this key too.

    ``None`` = the frozen grids (and the brief's additive ``grid.screen_extra_hz``, which *is*
    part of the brief payload). Two ``None`` keys are equal, so every historical pair behaves
    byte-identically; a key on one side only is a mismatch.
    """
    if not isinstance(raw, dict):
        return None
    solve = raw.get("solve") if isinstance(raw.get("solve"), dict) else {}
    parts = {k: solve[k] for k in ("screen_grid", "freq_grid")
             if isinstance(solve.get(k), dict)}
    if not parts:
        return None
    return json.dumps(parts, sort_keys=True, default=str, separators=(",", ":"))


def _grid_label(key: str | None) -> str:
    """Short human label for a :func:`_grid_key` value (error messages only)."""
    if key is None:
        return "the frozen grids"
    return f"a grid override {key[:120]}" + ("..." if len(key) > 120 else "")


def _brief_label(key) -> str:
    kind, value = key if isinstance(key, tuple) and len(key) == 2 else (None, key)
    if kind == "embedded":
        return f"embedded brief {str(value)[:12]}"
    return f"brief {value!r}"


def _identity(run_dir: Path) -> tuple[int, tuple[str | None, str | None], dict]:
    """(objective_version, brief identity, run.json) of a source run from its config snapshot."""
    rj = read_json(run_dir / "run.json")
    if not rj:
        raise WarmStartError(f"{run_dir}: no run.json (not a started run directory?)")
    raw = rj.get("config") if isinstance(rj.get("config"), dict) else {}
    objective = raw.get("objective") if isinstance(raw.get("objective"), dict) else None
    version = int(objective.get("version", 1)) if objective is not None else \
        int(rj.get("objective_version", 1))
    return version, _brief_key(raw), rj


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
    if ws_block.get("covariance"):
        # P1b: the covariance transfer is a plain single-ES CMA feature. Refuse an unsupported
        # combination loudly instead of silently ignoring the opt-in (CMA-ME and restarts use
        # their own ES construction and are out of scope for this pass).
        alg = str(getattr(getattr(cfg, "search", None), "algorithm", "cma"))
        if alg != "cma":
            raise WarmStartError(
                f"search.warm_start.covariance is only implemented for search.algorithm: cma "
                f"(plain single-ES), got {alg!r}")
        if getattr(getattr(cfg, "search", None), "restarts", None) is not None:
            raise WarmStartError(
                "search.warm_start.covariance is only implemented for the plain single-ES CMA "
                "path; search.restarts is set (restart ES instances are not covariance-seeded)")
    allow_cross = bool(ws_block.get("allow_cross_brief", False))
    version_self = int(getattr(cfg, "objective_version", 1))
    raw_self = getattr(cfg, "raw", None)
    raw_self = raw_self if isinstance(raw_self, dict) else {}
    brief_self = _brief_key(raw_self)
    grid_self = _grid_key(raw_self)
    keys = space.keys()
    family = str(cfg.family)
    best: tuple[float, str, np.ndarray, dict] | None = None
    best_run: Path | None = None
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
                f"(run v{version} {_brief_label(brief)}, this config v{version_self} "
                f"{_brief_label(brief_self)}; set "
                f"search.warm_start.allow_cross_brief: true to override)")
        if str(rj.get("family")) != family:
            raise WarmStartError(f"{run_dir}: warm_start refuses family mismatch "
                                 f"(run {rj.get('family')!r}, this config {family!r})")
        if not allow_cross and _grid_key(rj.get("config")) != grid_self:
            raise WarmStartError(
                f"{run_dir}: warm_start refuses a solve-grid mismatch "
                f"(run {_grid_label(_grid_key(rj.get('config')))}, this config "
                f"{_grid_label(grid_self)}; the stored J was measured on different solved "
                f"frequencies, so it is not comparable — set "
                f"search.warm_start.allow_cross_brief: true to override)")
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
                best_run = run_dir
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
    if ws_block.get("covariance"):
        # P1b: only present when the covariance transfer is opted in (absent = byte-identical
        # mean-only record).
        record["mean_source"] = str(best_run)
    return design, record


def _param_get(space, params: dict, key: str) -> object:
    """Read a searched knob from a stored row.

    Generated rows (``generator: grid``) nest the adapter knobs at
    ``params["grid"]["knobs"]``, which ``families.resolve_path`` does not walk; the warm start
    must read them or every warm-started generated lane refuses (2026-11-19, SCOUT40). The
    fallback is only tried when the normal path raises, so native/flat rows are unchanged.
    """
    from ..design import families
    try:
        return families.param_get(space.family, params, key)
    except KeyError:
        grid = params.get("grid") if isinstance(params, dict) else None
        knobs = grid.get("knobs") if isinstance(grid, dict) else None
        if isinstance(knobs, dict) and key in knobs:
            return knobs[key]
        raise

# --------------------------------------------------------------------------- P1b covariance transfer

def _cov_options(value) -> dict:
    """Resolved covariance options (defaults filled); ``True`` means "all defaults"."""
    if value is True:
        return dict(COVARIANCE_DEFAULTS)
    if not isinstance(value, dict):
        raise WarmStartError(
            f"warm_start.covariance must be true/false or a mapping, got {value!r}")
    opts = dict(COVARIANCE_DEFAULTS)
    opts.update(value)
    return opts


def _clip_eigs(matrix: np.ndarray, eig_floor: float, eig_cap: float) -> np.ndarray:
    """Symmetrize and clip every eigenvalue into ``[eig_floor, eig_cap]``."""
    m = (np.asarray(matrix, dtype=float) + np.asarray(matrix, dtype=float).T) / 2.0
    w, v = np.linalg.eigh(m)
    w = np.clip(w, float(eig_floor), float(eig_cap))
    return (v * w) @ v.T


def transfer_covariance(
    C_old,
    sigma_old: float,
    spans_old,
    spans_new,
    *,
    blend: float,
    eig_floor: float,
    eig_cap: float,
    scale_sigma: bool = True,
    sigma0: float | None = None,
) -> tuple[np.ndarray, float, dict]:
    """Transfer a CMA covariance from one bound box into another.

    Convention (senior optimizer audit, P1b)::

        Sigma_old = sigma_old**2 * C_old                  # physical units
        T         = D_new^-1 D_old Sigma_old D_old D_new^-1
        C_target  = d * T / trace(T)                       # trace(d) SHAPE

    ``D`` are ``diag(span)`` in the search coordinate (``hi - lo``; ``log10`` widths for log
    bounds). The overall width is then set explicitly:

    * ``scale_sigma=True``  -> the ES sigma is the declared/config ``sigma0`` and the sampling
      covariance is ``sigma0**2 * C_target`` (shape transferred, width re-declared);
    * ``scale_sigma=False`` -> the ES sigma is ``sqrt(trace(T) / trace(C_target))``, so
      ``sigma**2 * C_target`` reproduces ``trace(T)`` even when the eigenvalue clip/blend has
      changed the shape's trace.

    Eigenvalue floor/cap and the conservative identity blend are applied to the dimensionless
    shape. Returns ``(C_target, effective_sigma, info)``; raises ``WarmStartError`` when the
    inputs are not finite/SPD.
    """
    C_old = np.asarray(C_old, dtype=float)
    if C_old.ndim != 2 or C_old.shape[0] != C_old.shape[1] or C_old.shape[0] == 0:
        raise WarmStartError(f"warm_start.covariance: C must be a non-empty square matrix, got "
                             f"shape {C_old.shape}")
    d = int(C_old.shape[0])
    so = np.asarray(spans_old, dtype=float).reshape(-1)
    sn = np.asarray(spans_new, dtype=float).reshape(-1)
    if so.size != d or sn.size != d:
        raise WarmStartError(f"warm_start.covariance: span length {so.size}/{sn.size} != C dim {d}")
    if not np.all(np.isfinite(C_old)):
        raise WarmStartError("warm_start.covariance: source C contains non-finite values")
    if not (np.all(np.isfinite(so)) and np.all(np.isfinite(sn))) or np.any(so <= 0) or np.any(sn <= 0):
        raise WarmStartError("warm_start.covariance: bound spans must be finite and > 0")
    sig = float(sigma_old)
    if not np.isfinite(sig) or sig <= 0:
        raise WarmStartError(f"warm_start.covariance: source sigma must be finite and > 0, got "
                             f"{sigma_old!r}")
    floor, cap = float(eig_floor), float(eig_cap)
    if not np.isfinite(floor) or floor <= 0:
        raise WarmStartError(f"warm_start.covariance: eig_floor must be finite and > 0, got "
                             f"{eig_floor!r}")
    if not np.isfinite(cap) or cap < floor:
        raise WarmStartError(f"warm_start.covariance: eig_cap must be finite and >= eig_floor, "
                             f"got {eig_cap!r}")
    b = float(blend)
    if not np.isfinite(b) or not (0.0 <= b <= 1.0):
        raise WarmStartError(f"warm_start.covariance: blend must be in [0, 1], got {blend!r}")

    w_old = np.linalg.eigvalsh((C_old + C_old.T) / 2.0)
    if float(w_old.min()) <= 0.0:
        raise WarmStartError("warm_start.covariance: source C is not SPD "
                             f"(min eigenvalue {float(w_old.min()):.6g})")

    sigma_old_cov = sig ** 2 * C_old
    # T_ij = span_old_i span_old_j Sigma_ij / (span_new_i span_new_j)
    T = (so[:, None] * sigma_old_cov * so[None, :]) / (sn[:, None] * sn[None, :])
    T = (T + T.T) / 2.0
    if not np.all(np.isfinite(T)):
        raise WarmStartError("warm_start.covariance: transformed covariance is non-finite")
    tr = float(np.trace(T))
    if not np.isfinite(tr) or tr <= 0.0:
        raise WarmStartError(f"warm_start.covariance: transformed covariance has invalid trace "
                             f"{tr!r}")

    shape = T * (d / tr)                       # trace == d before regularisation
    shape = _clip_eigs(shape, floor, cap)
    c_new = (1.0 - b) * np.eye(d) + b * shape
    c_new = _clip_eigs(c_new, floor, cap)      # identity blend stays SPD; re-clip for safety
    w = np.linalg.eigvalsh(c_new)
    if not np.all(np.isfinite(w)) or float(w.min()) <= 0.0:
        raise WarmStartError("warm_start.covariance: regularised covariance is not SPD")

    if scale_sigma:
        if sigma0 is None:
            raise WarmStartError("warm_start.covariance: scale_sigma requires sigma0")
        target = float(sigma0)
    else:
        # Preserve the transferred overall scale even when clipping/blending changed the trace.
        target = float(np.sqrt(tr / float(np.trace(c_new))))
    if not np.isfinite(target) or target <= 0.0:
        raise WarmStartError(f"warm_start.covariance: invalid target sigma {target!r}")

    info = {
        "blend": b,
        "eig_floor": floor,
        "eig_cap": cap,
        "scale_sigma": bool(scale_sigma),
        "target_sigma": target,
        "trace": float(np.trace(c_new)),
        "raw_trace": tr,
        "condition_number": float(w[-1] / w[0]),
        "eigenvalues": [float(x) for x in w],
        "symmetrized": True,
        "spd_verified": True,
    }
    return c_new, target, info


def _spans_from_bounds(bounds: dict, keys: list[str], where: str) -> np.ndarray:
    spans = []
    for k in keys:
        b = bounds.get(k)
        if not isinstance(b, dict) or "lo" not in b or "hi" not in b:
            raise WarmStartError(f"{where}: no lo/hi bounds for searched knob {k!r}")
        lo, hi = float(b["lo"]), float(b["hi"])
        if bool(b.get("log", False)):
            if lo <= 0.0 or hi <= 0.0:
                raise WarmStartError(f"{where}: log bounds for {k!r} must be > 0")
            lo, hi = math.log10(lo), math.log10(hi)
        span = hi - lo
        if not np.isfinite(span) or span <= 0.0:
            raise WarmStartError(f"{where}: bound span for {k!r} must be finite and > 0")
        spans.append(span)
    return np.asarray(spans, dtype=float)


def _source_spans(rj: dict, keys: list[str]) -> np.ndarray:
    raw = rj.get("config") if isinstance(rj.get("config"), dict) else {}
    bounds = raw.get("bounds") if isinstance(raw.get("bounds"), dict) else {}
    return _spans_from_bounds(bounds, keys, "warm_start.covariance source run")


def _current_spans(space, keys: list[str]) -> np.ndarray:
    spans = []
    for k in keys:
        b = space.bounds[k]
        lo, hi = float(b.lo), float(b.hi)
        if bool(getattr(b, "log", False)):
            lo, hi = math.log10(lo), math.log10(hi)
        span = hi - lo
        if not np.isfinite(span) or span <= 0.0:
            raise WarmStartError(f"warm_start.covariance: bound span for {k!r} must be finite "
                                 f"and > 0")
        spans.append(span)
    return np.asarray(spans, dtype=float)


def _source_compatible(cfg, ws_block: dict, run_dir: Path, keys: list[str]) -> tuple[int, dict]:
    version, brief, rj = _identity(run_dir)
    allow_cross = bool(ws_block.get("allow_cross_brief", False))
    version_self = int(getattr(cfg, "objective_version", 1))
    raw_self = getattr(cfg, "raw", None)
    raw_self = raw_self if isinstance(raw_self, dict) else {}
    brief_self = _brief_key(raw_self)
    grid_self = _grid_key(raw_self)
    if (version != version_self or brief != brief_self) and not allow_cross:
        raise WarmStartError(
            f"{run_dir}: warm_start.covariance refuses objective version/brief mismatch "
            f"(run v{version} {_brief_label(brief)}, this config v{version_self} "
            f"{_brief_label(brief_self)}; set "
            f"search.warm_start.allow_cross_brief: true to override)")
    if str(rj.get("family")) != str(cfg.family):
        raise WarmStartError(f"{run_dir}: warm_start.covariance refuses family mismatch "
                             f"(run {rj.get('family')!r}, this config {cfg.family!r})")
    if not allow_cross and _grid_key(rj.get("config")) != grid_self:
        raise WarmStartError(
            f"{run_dir}: warm_start.covariance refuses a solve-grid mismatch "
            f"(run {_grid_label(_grid_key(rj.get('config')))}, this config "
            f"{_grid_label(grid_self)}; set search.warm_start.allow_cross_brief: true to override)")
    knobs = _searched_knobs(rj)
    if knobs is None or knobs != keys:
        raise WarmStartError(
            f"{run_dir}: warm_start.covariance refuses knob-name mismatch (run {knobs!r} vs "
            f"this config {keys!r} — the SAME searched knobs are required)")
    return version, rj


def covariance(cfg, space, record: dict | None = None) -> tuple[np.ndarray | None, dict | None]:
    """(transferred initial C, run.json covariance record) or ``(None, None)`` when
    ``search.warm_start.covariance`` is absent/false.

    The source is the run that supplied the warm mean (``record["mean_source"]``) or, when the
    record is unavailable, the first ``from_runs`` entry. The same family / objective version /
    brief / searched-knob checks as :func:`mean_and_sigma` gate the transfer. A requested but
    unusable covariance (missing sidecar, compressed/restart-only summary, non-finite/non-SPD C,
    dimension above ``max_dim``) raises ``WarmStartError`` — never a silent fallback.
    """
    ws_block = getattr(getattr(cfg, "search", None), "warm_start", None)
    if not ws_block or not ws_block.get("from_runs"):
        return None, None
    requested = ws_block.get("covariance")
    if not requested:
        return None, None
    opts = _cov_options(requested)
    keys = list(space.keys())
    d = len(keys)
    max_dim = int(opts["max_dim"])
    if d > max_dim:
        raise WarmStartError(
            f"warm_start.covariance: this config's CMA dimension is {d}, above max_dim "
            f"{max_dim}; raise search.warm_start.covariance.max_dim (1..16) or disable the "
            f"transfer")

    src_txt = (record or {}).get("mean_source")
    run_dir = Path(src_txt) if src_txt else Path(ws_block["from_runs"][0])
    version, rj = _source_compatible(cfg, ws_block, run_dir, keys)
    spans_old = _source_spans(rj, keys)
    spans_new = _current_spans(space, keys)

    cov_path = run_dir / "cma" / "covariance.json"
    snap = read_json(cov_path)
    if not isinstance(snap, dict):
        raise WarmStartError(
            f"{run_dir}: warm_start.covariance requested but cma/covariance.json is missing or "
            f"unreadable; run the source with plain single-ES CMA so the full C sidecar exists")
    snap_keys = snap.get("keys")
    if list(snap_keys or []) != keys:
        raise WarmStartError(
            f"{run_dir}: warm_start.covariance refuses knob-name/order mismatch between "
            f"cma/covariance.json {snap_keys!r} and this config {keys!r}")
    C_raw = snap.get("C")
    if C_raw is None:
        raise WarmStartError(
            f"{run_dir}: cma/covariance.json is a compressed/restart-only summary without the "
            f"full C matrix; a full single-ES covariance is required for the transfer")
    C_old = np.asarray(C_raw, dtype=float)
    if C_old.shape != (d, d):
        raise WarmStartError(
            f"{run_dir}: cma/covariance.json C has shape {C_old.shape}, expected {(d, d)}")
    if not np.all(np.isfinite(C_old)):
        raise WarmStartError(f"{run_dir}: cma/covariance.json C contains non-finite values")
    sigma_old = snap.get("sigma")
    try:
        sigma_old = float(sigma_old)
    except (TypeError, ValueError):
        raise WarmStartError(
            f"{run_dir}: cma/covariance.json has no usable sigma, got {snap.get('sigma')!r}") from None
    if not np.isfinite(sigma_old) or sigma_old <= 0.0:
        raise WarmStartError(f"{run_dir}: cma/covariance.json sigma must be finite and > 0, got "
                             f"{sigma_old!r}")
    w_old = np.linalg.eigvalsh((C_old + C_old.T) / 2.0)
    if float(w_old.min()) <= 0.0:
        raise WarmStartError(
            f"{run_dir}: cma/covariance.json C is not SPD (min eigenvalue "
            f"{float(w_old.min()):.6g}); refusing the covariance warm start")

    sigma0 = float(getattr(cfg.search, "sigma0"))
    C_new, target, info = transfer_covariance(
        C_old, sigma_old, spans_old, spans_new,
        blend=opts["blend"], eig_floor=opts["eig_floor"], eig_cap=opts["eig_cap"],
        scale_sigma=bool(opts["scale_sigma"]), sigma0=sigma0)
    c_sha = hashlib.sha256(
        json.dumps(C_raw, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    record_out = {
        "source": {
            "run": str(run_dir),
            "covariance_path": str(cov_path),
            "C_sha256": c_sha,
            "sigma": sigma_old,
            "objective_version": version,
            "n_dim": d,
        },
        "keys": keys,
        "spans_old": {k: float(v) for k, v in zip(keys, spans_old)},
        "spans_new": {k: float(v) for k, v in zip(keys, spans_new)},
        "span_convention": ("hi - lo in the search coordinate "
                            "(log10(hi) - log10(lo) for log bounds)"),
        "formula": ("Sigma_old = sigma_old^2 * C_old; "
                    "T = D_new^-1 D_old Sigma_old D_old D_new^-1"),
        "blend": info["blend"],
        "eig_floor": info["eig_floor"],
        "eig_cap": info["eig_cap"],
        "max_dim": max_dim,
        "scale_sigma": info["scale_sigma"],
        "target_sigma": target,
        "sigma_convention": (
            "C normalized to trace d; effective sigma = config search.sigma0 (declared width)"
            if info["scale_sigma"] else
            "C normalized to trace d; effective sigma = sqrt(trace(T)/trace(C)) "
            "(transferred width)"),
        "trace": info["trace"],
        "raw_trace": info["raw_trace"],
        "condition_number": info["condition_number"],
        "eigenvalues": info["eigenvalues"],
        "symmetrized": True,
        "spd_verified": True,
    }
    return C_new, record_out
