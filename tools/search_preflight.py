#!/usr/bin/env python
"""Pre-flight gate for a hornlab-search CMA run.

The 2026-11-14 night produced no improvement: every run's best J was its eval-0 seed.
Four independent facts explained it (and this tool computes each one from the config and
prior run directories, never from hard-coded per-run numbers):

1. the seed was the previous run's converged best (no headroom);
2. ``sigma0 = 0.15`` in normalized units was ~3-6x the width of the good basin;
3. 22-36% of evaluations were envelope/mesh refusals, so the effective budget was smaller;
4. ``infeasible_penalty: graded`` was inert for native families (only pre-mesh generator
   envelope estimates are graded; everything else got the flat 1000 penalty).

Run this before spending a night:

    .venv\\Scripts\\python.exe tools/search_preflight.py CONFIG [CONFIG ...]

Default ``--samples 0`` builds no mesh (the history/seed/sigma checks are still exact).
``--samples N`` samples the normalized box through the real validator (mesh + envelope) and
reports the refusal tally. ``--geometry-only`` runs only the generated-design pre-mesh
``_generator_error`` check and never imports/uses gmsh.

Exit codes: 0 normally, 1 on HARD faults, 1 on warnings only with ``--strict``, 2 on usage.
``--json`` prints one machine-readable object instead of the markdown tables.
"""
from __future__ import annotations

import argparse
import copy
import dataclasses
import json
import math
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

# Running ``tools/search_preflight.py`` puts ``tools/`` on sys.path, not the repo root. The
# package is normally installed editable, but the gate must also work from a bare checkout.
REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from hornlab_search.config import ConfigError, load_config, mesh_spec  # noqa: E402
from hornlab_search.design.families import param_get  # noqa: E402
from hornlab_search.design.space import Bound, DesignSpace  # noqa: E402
from hornlab_search.search import warmstart  # noqa: E402

#: A prior top-k is "inactive" on a key when its normalized values span less than this.
INACTIVE_SPREAD = 0.02
#: ... or when the best row sits within this normalized distance of a bound.
INACTIVE_BOUND_BAND = 0.01
#: Warn when the spread-recommended sigma is less than this fraction of the configured sigma0.
SIGMA_TOO_LARGE_RATIO = 0.5


# ------------------------------------------------------------------ chi-square (no scipy)

def _gamma_series(s: float, x: float) -> float:
    """Regularized lower incomplete gamma P(s, x) by the standard power series (x < s+1)."""
    term = 1.0 / s
    total = term
    ap = s
    for _ in range(10_000):
        ap += 1.0
        term *= x / ap
        total += term
        if abs(term) < abs(total) * 1e-15:
            break
    return total * math.exp(-x + s * math.log(x) - math.lgamma(s))


def _gamma_cf(s: float, x: float) -> float:
    """Regularized upper incomplete gamma Q(s, x) by the continued fraction (x >= s+1)."""
    tiny = 1e-300
    b = x + 1.0 - s
    c = 1.0 / tiny
    d = 1.0 / b
    h = d
    for i in range(1, 10_000):
        an = -i * (i - s)
        b += 2.0
        d = an * d + b
        if abs(d) < tiny:
            d = tiny
        c = b + an / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-15:
            break
    return math.exp(-x + s * math.log(x) - math.lgamma(s)) * h


def chi2_cdf(x: float, k: float) -> float:
    """CDF of a chi-square with ``k`` degrees of freedom, without scipy.

    ``P(k/2, x/2)`` with the standard series/continued-fraction split. Used for the
    expected-hits estimate: a zero-mean isotropic Gaussian step in ``d`` normalized
    dimensions has its squared radius distributed chi-square with ``d`` dof.
    """
    x = float(x)
    k = float(k)
    if k <= 0.0:
        raise ValueError(f"chi2 needs k > 0, got {k!r}")
    if x <= 0.0:
        return 0.0
    if not math.isfinite(x):
        return 1.0
    s = k / 2.0
    y = x / 2.0
    if y < s + 1.0:
        return _gamma_series(s, y)
    return 1.0 - _gamma_cf(s, y)


#: The private name used in the preflight contract (kept alongside the public spelling).
_chi2_cdf = chi2_cdf


# ------------------------------------------------------------------ small helpers

def _searched_bounds(cfg) -> dict[str, dict]:
    """Bounds entries that are actually searched (``search`` defaults to true)."""
    out: dict[str, dict] = {}
    for key, bound in (cfg.bounds_raw or {}).items():
        if isinstance(bound, dict) and bool(bound.get("search", True)):
            out[str(key)] = bound
    return out


def _seed_value(cfg, key: str):
    """The value eval 0 will use for ``key``.

    Native families read through ``families.param_get`` (nested keys included); generated
    configs keep generator knobs flat in ``seed_params``.
    """
    if getattr(cfg, "generator", None):
        return cfg.seed_params[key]
    return param_get(cfg.family, cfg.seed_params, key)


def _row_param(cfg, params: dict, key: str):
    """Read a searched key from a run's persisted ``params``.

    WHY: generated/grid runs store their knobs at ``params["grid"]["knobs"]`` (or
    ``params["_knobs"]`` for a refused generated design), so ``families.param_get`` cannot
    see them. The L1 A/B is exactly such a family; without this the prior history and the
    changed-region check are blind on the real runs (2026-11-14 L1).
    """
    generator = getattr(cfg, "generator", None)
    if generator:
        name = (generator or {}).get("name")
        node = params.get(name) if isinstance(params, dict) and name else None
        if isinstance(node, dict) and isinstance(node.get("knobs"), dict):
            if key in node["knobs"]:
                return node["knobs"][key]
        if isinstance(params, dict) and isinstance(params.get("_knobs"), dict):
            if key in params["_knobs"]:
                return params["_knobs"][key]
        raise KeyError(key)
    return param_get(cfg.family, params, key)


def _same_knob_value(seed_value, prior_value) -> bool:
    """True when a seed knob equals a prior best's knob at the seed's written precision.

    WHY: the H1 seed is the prior incumbent copied into YAML at four decimals
    (``a_deg: 36.1555`` vs the run's ``36.1554992059``), so a 1e-9 relative comparison alone
    reports "differs" for the exact nested-incumbent case this check exists to catch. The
    fast path is the requested tight ``math.isclose``; the fallback compares at the number
    of decimals the seed itself was written with, so rounding is not a real difference but
    a genuinely different knob still fails.
    """
    try:
        seed = float(seed_value)
        prior = float(prior_value)
    except (TypeError, ValueError):
        return seed_value == prior_value
    if math.isclose(seed, prior, rel_tol=1e-9, abs_tol=1e-12):
        return True
    text = format(seed, ".15g")
    if "." in text and "e" not in text.lower():
        decimals = len(text.split(".", 1)[1])
        return round(seed, decimals) == round(prior, decimals)
    return math.isclose(seed, prior, rel_tol=1e-6, abs_tol=1e-8)


def _fmt(v) -> str:
    if v is None:
        return "n/a"
    if isinstance(v, float):
        return f"{v:.6g}"
    return str(v)


def _brief_identity(cfg) -> str:
    """Stable identity of the brief an arm was scored under."""
    brief = getattr(cfg, "brief", None)
    if isinstance(brief, dict) and brief.get("name"):
        return f"brief:{brief['name']}"
    raw = getattr(cfg, "raw", None) or {}
    return str(raw.get("brief_file") or "none")


def _arm_identity(cfg) -> dict:
    """The fields the A/B gate requires to match for a fair matched pair."""
    return {
        "brief": _brief_identity(cfg),
        "family": cfg.family,
        "objective_version": int(getattr(cfg, "objective_version", 1)),
        "budget": int(cfg.search.budget),
        "backend": str(cfg.solve.backend),
    }


def _changed_bound_keys(cfg, other) -> list[str]:
    """Searched bound keys whose lo/hi/log (or presence) differ between the two arms."""
    keys = set(_searched_bounds(cfg)) | set(_searched_bounds(other))
    changed = []
    for key in sorted(keys):
        a = cfg.bounds_raw.get(key)
        b = other.bounds_raw.get(key)
        a_searched = isinstance(a, dict) and bool(a.get("search", True))
        b_searched = isinstance(b, dict) and bool(b.get("search", True))
        if not (a_searched or b_searched):
            continue
        if a is None or b is None:
            changed.append(key)
            continue
        for field in ("lo", "hi", "log"):
            av = a.get(field)
            bv = b.get(field)
            if field == "log":
                av = bool(av)
                bv = bool(bv)
            elif av is not None:
                av = float(av)
            if bv is not None and field != "log":
                bv = float(bv)
            if av != bv:
                changed.append(key)
                break
    return changed


def _prior_bests(from_runs) -> list[dict]:
    """Prior bests with the data needed to detect a NESTED incumbent.

    A hash match is the fast path, but the same geometry can carry extra neutral knobs
    (e.g. all azimuth amplitudes at 0), so the seed can be the prior best while the design
    hash differs. Carry the objective, params and the prior run's searched keys to compare
    the shared knobs when the hash does not match.
    """
    out = []
    for run_dir in from_runs or []:
        run_dir = Path(run_dir)
        best = warmstart.read_json(run_dir / "best.json") or {}
        run_json = warmstart.read_json(run_dir / "run.json") or {}
        design_hash = best.get("design_hash")
        if not design_hash:
            design_hash = (run_json.get("best") or {}).get("design_hash")
        if not design_hash:
            continue
        params = best.get("params")
        if not isinstance(params, dict):
            params = None
        objective = best.get("objective")
        if objective is None:
            objective = (run_json.get("best") or {}).get("objective")
        prior_keys = warmstart._searched_knobs(run_json)
        if prior_keys is None and isinstance(params, dict):
            prior_keys = sorted(params)
        out.append({
            "design_hash": str(design_hash),
            "run_dir": str(run_dir),
            "objective": objective,
            "params": params,
            "prior_keys": prior_keys,
        })
    return out


def _with_warm_start(cfg, from_runs, top_k: int):
    """Shallow copy of ``cfg`` whose search.warm_start points at ``from_runs``."""
    ws = {
        "from_runs": [str(Path(p)) for p in from_runs],
        "top_k": int(top_k),
        "sigma_from_spread": True,
        "allow_cross_brief": False,
    }
    cfg_any: Any = cfg
    search: Any = getattr(cfg_any, "search", None)
    try:
        return dataclasses.replace(
            cfg_any, search=dataclasses.replace(search, warm_start=ws))
    except TypeError:
        # Not dataclasses: fall back to the shallow-copy contract.
        out = copy.copy(cfg_any)
        out.search = copy.copy(search)
        out.search.warm_start = ws
        return out


def _top_rows(cfg, space, from_runs, top_k: int) -> list[tuple[float, dict, dict]]:
    """The prior best rows: (objective, {key: unit in THIS box}, {key: raw value}).

    ``warmstart._searched_knobs`` keeps a run whose recorded searched knobs differ out of
    the activity check; ``_row_param`` reads native keys and generated grid knobs alike.
    The raw values let the A/B added-region check normalize the SAME prior designs in the
    other arm's box.
    """
    rows: list[tuple[float, dict, dict]] = []
    keys = space.keys()
    for run_dir in from_runs or []:
        run_dir = Path(run_dir)
        run_json = warmstart.read_json(run_dir / "run.json") or {}
        prior_keys = warmstart._searched_knobs(run_json)
        if prior_keys is not None and prior_keys != keys:
            continue
        for row in warmstart.read_ndjson(run_dir / "search.ndjson"):
            if not (row.get("ok") and isinstance(row.get("params"), dict)):
                continue
            try:
                raw = {key: _row_param(cfg, row["params"], key) for key in keys}
                unit = {
                    key: space.bounds[key].to_unit(float(raw[key]))[0]  # type: ignore[arg-type]
                    for key in keys
                }
            except (KeyError, TypeError, ValueError):
                continue
            try:
                objective = float(row["objective"])
            except (KeyError, TypeError, ValueError):
                continue
            rows.append((objective, unit, raw))
    rows.sort(key=lambda item: item[0])
    return rows[: max(1, int(top_k))]


# ------------------------------------------------------------------ findings / report

def _finding(severity: str, code: str, message: str, config_path: str) -> dict:
    return {"severity": severity, "code": code, "message": message, "config": config_path}


def _new_report(cfg, path: str) -> dict:
    return {
        "path": path,
        "name": cfg.name,
        "family": cfg.family,
        "generator": None if not getattr(cfg, "generator", None)
        else (cfg.generator or {}).get("name"),
        "searched_keys": [],
        "seed_outside_box": [],
        "seed_key_missing": [],
        "seed_design_hash": None,
        "prior_bests": [],
        "history": None,
        "sigma": {},
        "sampling": {},
        "refusals": {},
        "graded": {},
        "ab": None,
        "findings": [],
    }


# ------------------------------------------------------------------ checks

def _check_seed(cfg, path: str, report: dict) -> None:
    """Checks 1 and 2: the seed must be a real, in-box design.

    WHY: ``DesignSpace.normalize`` clips out-of-box values silently, but eval 0 is scored
    from the unclipped seed. On 2026-11-14 the narrow T arm had ``g_T = 0.8`` outside the
    searched ``[0.687, 0.777]`` box: the run's first evaluation was already geometry nobody
    could search back to, and later the best J never left that seed. A key absent from the
    seed is also changed before iteration (the midpoint fill), so it is a WARN.
    """
    for key, bound in sorted(_searched_bounds(cfg).items()):
        lo, hi = float(bound["lo"]), float(bound["hi"])
        try:
            value = _seed_value(cfg, key)
        except KeyError:
            report["seed_key_missing"].append(key)
            report["findings"].append(_finding(
                "WARN", "seed_key_missing",
                f"searched key '{key}' is absent from seed_params; DesignSpace fills it with "
                f"the bound midpoint {0.5 * (lo + hi):g}, changing the seed geometry",
                path))
            continue
        except Exception as exc:  # a malformed path, not a missing key
            report["findings"].append(_finding(
                "WARN", "seed_unreadable",
                f"searched key '{key}' could not be read from seed_params: "
                f"{type(exc).__name__}: {exc}",
                path))
            continue
        try:
            numeric = float(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            report["findings"].append(_finding(
                "WARN", "seed_unreadable",
                f"searched key '{key}' has non-numeric seed value {value!r}",
                path))
            continue
        if numeric < lo or numeric > hi:
            report["seed_outside_box"].append(
                {"key": key, "value": numeric, "lo": lo, "hi": hi})
            report["findings"].append(_finding(
                "HARD", "seed_outside_box",
                f"{key}={_fmt(numeric)} is outside the searched box [{_fmt(lo)}, {_fmt(hi)}]; "
                f"DesignSpace.normalize() silently clips it, but eval 0 still scores the "
                f"unclipped seed (2026-11-14 evidence)",
                path))


def _check_no_headroom(cfg, path: str, report: dict, space, prior_bests) -> None:
    """Check 3: the seed must not already be the prior run's converged best.

    WHY: the 2026-11-14 night seeded every run with the previous best, so there was no
    headroom by construction and every result looked like a failure to improve. The hash is
    the fast path; the nested case (the H1 2026-11-13 run: six prior knobs plus three new
    azimuth amplitudes at 0) is the same incumbent with a different params dict, so the
    shared knobs are compared when the hash differs.
    """
    if space is None or not prior_bests:
        return
    seed = getattr(space, "seed", None)
    if seed is None:
        return
    try:
        seed_hash = seed.hash()
    except Exception:  # noqa: BLE001 - no hash means this check simply cannot run
        return
    report["seed_design_hash"] = seed_hash
    for best in prior_bests:
        prior_objective = best.get("objective")
        if best.get("design_hash") == seed_hash:
            report["findings"].append(_finding(
                "WARN", "no_headroom",
                f"seed design hash {seed_hash} EQUALS the prior best from {best['run_dir']}; "
                f"the run starts at the old optimum and can only match it (2026-11-14 evidence)",
                path))
            continue
        prior_keys = best.get("prior_keys") or []
        params = best.get("params")
        if not prior_keys or not isinstance(params, dict):
            continue
        matched = True
        for key in prior_keys:
            try:
                seed_value = _seed_value(cfg, key)
                prior_value = _row_param(cfg, params, key)
            except (KeyError, TypeError, ValueError):
                matched = False
                break
            if not _same_knob_value(seed_value, prior_value):
                matched = False
                break
        if not matched:
            continue
        new_keys = sorted(set(space.keys()) - set(prior_keys))
        objective_text = (f"{float(prior_objective):.4f}"
                          if isinstance(prior_objective, (int, float)) else "unknown")
        if new_keys:
            message = (
                f"seed matches the prior best on every shared knob; only "
                f"{', '.join(new_keys)} are new - the run starts at the nested incumbent "
                f"(prior J={objective_text}); the params hash differs only by those extras "
                f"(2026-11-13 H1 evidence)")
        else:
            message = (
                f"seed matches the prior best on every prior-searched knob (prior "
                f"J={objective_text}); the params hash differs only by rounding/extras - "
                f"the run starts at the old optimum")
        report["findings"].append(_finding("WARN", "no_headroom", message, path))


def _generator_history_fallback(cfg, path: str, report: dict, space, from_runs,
                                top_k: int):
    """A local history record for generated configs whose run rows the production
    ``mean_and_sigma`` cannot read.

    WHY: real grid runs store knobs at ``row["params"]["grid"]["knobs"]``, so
    ``warmstart.mean_and_sigma`` raises ``WarmStartError`` on the L1 family ("row 0 lacks
    knob 'g_T'") and the A/B would be blind. Validate the same run identity fields the
    production helper checks, then compute the spread/recommended sigma from ``_top_rows``.
    """
    version_self = int(getattr(cfg, "objective_version", 1))
    raw_self = getattr(cfg, "raw", None) or {}
    brief_self = raw_self.get("brief_file") or (
        raw_self.get("brief") if isinstance(raw_self.get("brief"), dict) else None)
    sources = []
    for run_dir in from_runs or []:
        run_dir = Path(run_dir)
        try:
            version, brief, run_json = warmstart._identity(run_dir)
        except warmstart.WarmStartError as exc:
            report["findings"].append(_finding(
                "WARN", "history_unusable", f"generator history is unusable: {exc}", path))
            return None
        if version != version_self or brief != brief_self:
            report["findings"].append(_finding(
                "WARN", "history_unusable",
                f"generator history is unusable: {run_dir} has objective version {version} "
                f"and brief {brief!r}, this config has version {version_self} and brief "
                f"{brief_self!r}",
                path))
            return None
        if str(run_json.get("family")) != str(cfg.family):
            report["findings"].append(_finding(
                "WARN", "history_unusable",
                f"generator history is unusable: {run_dir} has family "
                f"{run_json.get('family')!r}, this config {cfg.family!r}",
                path))
            return None
        sources.append({
            "path": str(run_dir),
            "config_sha": run_json.get("config_sha"),
            "objective_version": version,
        })
    rows = _top_rows(cfg, space, from_runs, top_k)
    if len(rows) < 2:
        report["findings"].append(_finding(
            "WARN", "history_unusable",
            f"generator history is unusable: fewer than 2 usable prior rows ({len(rows)})",
            path))
        return None
    keys = space.keys()
    per_key = [[unit[key] for _, unit, _ in rows] for key in keys]
    spreads = [float(max(values) - min(values)) for values in per_key]
    spread = float(np.median(spreads)) if spreads else 0.0
    sigma0 = float(min(max(spread, warmstart.SIGMA_FLOOR), float(cfg.search.sigma0)))
    return {
        "from_runs": [str(Path(p)) for p in from_runs],
        "top_k": int(top_k),
        "sources": sources,
        "mean_design_hash": None,
        "mean_objective": rows[0][0],
        "sigma0": sigma0,
        "sigma_from_spread": {
            "median_spread": spread,
            "sigma0": sigma0,
            "top_k": len(rows),
        },
        "rows": len(rows),
        "source": "preflight-fallback",
    }


def _check_history(cfg, path: str, report: dict, space, from_runs, top_k: int):
    """Check 8: build the warm-start mean/sigma from prior run dirs.

    WHY: the recommended sigma is derived from the prior top-k normalized spread, not
    invented. ``mean_and_sigma`` is the exact production path the search itself uses, so a
    preflight number and the run's number cannot drift apart. Its ``WarmStartError`` is a
    warning here, never a crash (a missing/incompatible source must not hide the other
    checks).
    """
    if not from_runs:
        report["findings"].append(_finding(
            "INFO", "no_history",
            "--from-runs absent: no prior-run history, seed-headroom/spread/expected-hits "
            "checks are informational only",
            path))
        return None
    if space is None:
        return None
    try:
        _, record = warmstart.mean_and_sigma(
            _with_warm_start(cfg, from_runs, top_k), space)
    except warmstart.WarmStartError as exc:
        if getattr(cfg, "generator", None):
            fallback = _generator_history_fallback(
                cfg, path, report, space, from_runs, top_k)
            if fallback is not None:
                report["history"] = fallback
                return fallback
        report["findings"].append(_finding(
            "WARN", "history_unusable",
            f"warm-start history is unusable: {exc}",
            path))
        return None
    except Exception as exc:  # noqa: BLE001 - never crash the gate on a history problem
        report["findings"].append(_finding(
            "WARN", "history_unusable",
            f"warm-start history raised {type(exc).__name__}: {exc}",
            path))
        return None
    report["history"] = record
    return record


def _check_sigma(cfg, path: str, report: dict, record, dims: int,
                 refusal_fraction, min_expected_hits: float) -> None:
    """Checks 4: warn when sigma0 is far above the prior basin or the hit count is tiny.

    WHY: on 2026-11-14 ``sigma0 = 0.15`` was ~3-6x the normalized basin, so almost every
    CMA step landed outside the good region. The expected-hits number uses the actual
    prior top-k spread and the chi-square probability that an isotropic Gaussian step lands
    inside that spread in ``d`` dimensions:

        budget * (1 - refusal_fraction) * chi2_cdf((spread / sigma0)^2, d)

    The refusal fraction is sampled (``--samples``); with no sampling it is treated as 0
    and the table says so, which is the optimistic case.
    """
    config_sigma = float(cfg.search.sigma0)
    info = {
        "config_sigma0": config_sigma,
        "recommended_sigma": None,
        "median_spread": None,
        "dims": int(dims),
        "expected_hits": None,
        "min_expected_hits": float(min_expected_hits),
        "refusal_fraction": None if refusal_fraction is None else float(refusal_fraction),
    }
    report["sigma"] = info
    if record is None:
        return
    sigma_rec = record.get("sigma_from_spread")
    spread = sigma_rec.get("median_spread") if isinstance(sigma_rec, dict) else None
    recommended = record.get("sigma0")
    if recommended is not None:
        recommended = float(recommended)
        info["recommended_sigma"] = recommended
        if recommended < SIGMA_TOO_LARGE_RATIO * config_sigma:
            report["findings"].append(_finding(
                "WARN", "sigma_too_large",
                f"spread-recommended sigma {_fmt(recommended)} is below half the configured "
                f"sigma0 {_fmt(config_sigma)}; sigma0 was ~3-6x the basin on 2026-11-14",
                path))
    if spread is None or dims <= 0:
        info["note"] = "prior top-k has fewer than two rows; no spread estimate"
        return
    spread = float(spread)
    info["median_spread"] = spread
    ratio = spread / config_sigma if config_sigma > 0 else float("inf")
    cdf = chi2_cdf(ratio * ratio, dims)
    frac = 1.0 - (float(refusal_fraction) if refusal_fraction is not None else 0.0)
    expected = float(cfg.search.budget) * frac * cdf
    info["expected_hits"] = expected
    if expected < min_expected_hits:
        detail = (f"{_fmt(refusal_fraction)} sampled refusals"
                  if refusal_fraction is not None else "no refusal sampling (assumed 0)")
        report["findings"].append(_finding(
            "WARN", "low_hits",
            f"expected in-basin hits at sigma0 {_fmt(config_sigma)} is {expected:.2f} "
            f"(< {min_expected_hits:g}; spread {_fmt(spread)}, d={dims}, "
            f"budget {int(cfg.search.budget)}, {detail}); 2026-11-14 had 22-36% refusals "
            f"and no improvement",
            path))


def _sample(cfg, path: str, report: dict, space, samples: int, seed: int,
            geometry_only: bool) -> None:
    """Check 5: sample the box through the real validator and tally refusal kinds.

    WHY: 22-36% of the 2026-11-14 evaluations were refusals, so the nominal budget was not
    the effective budget. The refusal mapping mirrors ``search/evaluate.py`` exactly:
    pre-mesh generator errors -> invalid_envelope/invalid_geometry; GeometryInvalidError ->
    invalid_geometry; MeshTooLargeError -> mesh_too_large; GeneratorError -> invalid_geometry;
    MeshConsistencyError -> HARD (a config bug, never a bad candidate); anything else ->
    exception. A post-mesh ``envelope_violation`` is invalid_geometry, exactly as
    ``evaluate`` maps it (only the pre-mesh generator estimate is gradeable).
    ``--geometry-only`` runs the generated-design ``_generator_error`` check only and never
    imports gmsh.
    """
    if samples <= 0:
        report["sampling"] = {
            "samples": 0,
            "status": "not sampled",
            "note": "--samples 0 (default): no mesh was built",
        }
        return
    if space is None:
        report["sampling"] = {"samples": samples, "status": "not sampled",
                              "note": "design space could not be built"}
        return
    keys = space.keys()
    rng = np.random.default_rng(int(seed))
    xs = rng.random((int(samples), len(keys)))
    counts: Counter[str] = Counter()
    valid = refused = unvalidated = 0
    status = ("geometry-only (generated pre-mesh _generator_error only; no gmsh)"
              if geometry_only else "meshed (screen mesh + envelope)")
    note = None

    def _refuse(kind: str) -> None:
        nonlocal refused
        counts[kind] += 1
        refused += 1

    # A lazy inner function: --geometry-only never imports the mesher/evaluator at all.
    def _mesh_verdict(design, out_dir):
        from hornlab_search.design.generators.registry import GeneratorError
        from hornlab_search.mesh.build import MeshConsistencyError, build_mesh
        from hornlab_search.search.evaluate import envelope_violation
        from hornlab_search.types import GeometryInvalidError, MeshTooLargeError
        try:
            mesh = build_mesh(design, mesh_spec("screen", cfg), cfg, out_dir, mode="screen")
            why = envelope_violation(mesh, getattr(cfg, "brief", None))
        except MeshConsistencyError as exc:
            return "hard", str(exc)
        except GeometryInvalidError:
            return "invalid_geometry", None
        except MeshTooLargeError:
            return "mesh_too_large", None
        except GeneratorError:
            return "invalid_geometry", None
        except Exception as exc:  # noqa: BLE001 - mirror evaluate's 'exception' row
            return "exception", f"{type(exc).__name__}: {exc}"
        if why:
            return "invalid_geometry", None
        return None, None

    with tempfile.TemporaryDirectory(prefix="hornlab-preflight-") as td:
        for i in range(int(samples)):
            x = xs[i]
            try:
                design = space.denormalize(x)
            except Exception as exc:  # noqa: BLE001 - mirror evaluate's 'exception' row
                _refuse("exception")
                note = f"denormalize raised {type(exc).__name__}: {exc}"
                continue
            params = design.params if isinstance(design.params, dict) else {}
            generator_error = params.get("_generator_error")
            if generator_error:
                kind = ("invalid_envelope" if str(generator_error).startswith("invalid_envelope")
                        else "invalid_geometry")
                _refuse(kind)
                continue
            if geometry_only:
                if getattr(cfg, "generator", None):
                    valid += 1
                else:
                    unvalidated += 1
                continue
            kind, detail = _mesh_verdict(design, Path(td) / f"d{i:05d}")
            if kind == "hard":
                report["sampling"] = {
                    "samples": samples, "status": "hard (mesh consistency)",
                    "distribution": "uniform box",
                    "valid": valid, "refused": refused, "unvalidated": unvalidated,
                    "kinds": dict(counts),
                }
                report["findings"].append(_finding(
                    "HARD", "mesh_consistency",
                    f"MeshConsistencyError while sampling: {detail} (a units/symmetry config "
                    f"bug, not a bad candidate)",
                    path))
                return
            if kind == "exception":
                _refuse("exception")
                if detail:
                    note = f"sampling raised {detail}"
                continue
            if kind:
                _refuse(kind)
            else:
                valid += 1

    validated = valid + refused
    valid_fraction = (valid / validated) if validated else None
    refusal_fraction = (refused / validated) if validated else None
    predicted = (float(cfg.search.budget) * valid_fraction
                 if valid_fraction is not None else None)
    report["sampling"] = {
        "samples": int(samples),
        "status": status,
        "distribution": "uniform box",
        "valid": valid,
        "refused": refused,
        "unvalidated": unvalidated,
        "kinds": dict(counts),
        "valid_fraction": valid_fraction,
        "refusal_fraction": refusal_fraction,
        "predicted_valid_evals": predicted,
    }
    if note:
        report["sampling"]["note"] = note
    report["refusals"] = {
        "distribution": "uniform box",
        "valid_fraction": valid_fraction,
        "refusal_fraction": refusal_fraction,
        "predicted_valid_evals": predicted,
        "kinds": dict(counts),
    }
    if refused:
        tally = ", ".join(f"{kind}={n}" for kind, n in sorted(counts.items()))
        report["findings"].append(_finding(
            "WARN", "refusals",
            f"{refused}/{validated} sampled designs were refused [{tally}]; valid fraction "
            f"{_fmt(valid_fraction)}, predicted valid evals {_fmt(predicted)} of "
            f"{int(cfg.search.budget)}; uniform box sample (an upper bound away from the "
            f"seed; CMA concentrates near it); 2026-11-14 had 22-36% refusals"
            + ("; geometry-only sees pre-mesh refusals only" if geometry_only else ""),
            path))
    if unvalidated:
        report["findings"].append(_finding(
            "INFO", "geometry_only_unvalidated",
            f"{unvalidated}/{samples} native samples were not validated by --geometry-only "
            f"(no pre-mesh generator check exists for native families)",
            path))


def _check_graded(cfg, path: str, report: dict) -> None:
    """Check 6: graded infeasibility is inert unless a pre-mesh envelope refusal exists.

    WHY: on 2026-11-14 ``infeasible_penalty: graded`` was set on every arm, but native
    families and post-mesh refusals never hit the graded branch; they all got the flat
    PENALTY_INVALID (1000), so the setting changed nothing. The real lever for a refusing
    box is ``resample_strict`` together with ``budget_counts: valid``.
    """
    penalty = str(getattr(cfg.search, "infeasible_penalty", "flat"))
    sampling = report.get("sampling") or {}
    kinds = sampling.get("kinds") or {}
    refused = int(sampling.get("refused") or 0)
    info = {"infeasible_penalty": penalty, "sampled_refusals": refused,
            "invalid_envelope": int(kinds.get("invalid_envelope", 0))}
    report["graded"] = info
    if penalty != "graded" or refused <= 0:
        return
    if info["invalid_envelope"] > 0:
        return
    report["findings"].append(_finding(
        "WARN", "graded_inert",
        f"infeasible_penalty 'graded' but none of the {refused} sampled refusals is "
        f"invalid_envelope; only pre-mesh generator estimates are graded, while these "
        f"refusals get the flat PENALTY_INVALID ({1000:g}). Use "
        f"search.infeasible_penalty: resample_strict with search.budget_counts: valid to "
        f"replace refusals instead (2026-11-14 evidence)",
        path))


def _bound_from(bounds: dict):
    """A normalizing Bound for one arm's key, or None when the interval is degenerate."""
    try:
        lo, hi = float(bounds["lo"]), float(bounds["hi"])
    except (KeyError, TypeError, ValueError):
        return None
    if lo == hi:
        return None
    try:
        return Bound(lo=lo, hi=hi, search=bool(bounds.get("search", True)),
                     log=bool(bounds.get("log", False)))
    except ValueError:
        return None


def _make_added_region(rows, key: str, bound, lo: float, hi: float, axis: str,
                       treatment: str) -> dict:
    """One added interval, its treatment arm, and how many prior top-k rows sit inside."""
    unit_lo = float(bound.to_unit(lo)[0])
    unit_hi = float(bound.to_unit(hi)[0])
    if unit_hi < unit_lo:
        unit_lo, unit_hi = unit_hi, unit_lo
    inside = 0
    for _, _, raw in rows:
        if key not in raw:
            continue
        try:
            u = float(bound.to_unit(float(raw[key]))[0])
        except (KeyError, TypeError, ValueError):
            continue
        if axis == "lo":
            hit = unit_lo <= u < unit_hi
        elif axis == "hi":
            hit = unit_lo < u <= unit_hi
        else:
            hit = unit_lo <= u <= unit_hi
        inside += int(hit)
    return {
        "treatment": treatment,
        "axis": axis,
        "raw": [float(lo), float(hi)],
        "unit": [unit_lo, unit_hi],
        "rows_inside": inside,
        "n": len(rows),
    }


def _format_added_region(region: dict) -> str:
    lo, hi = region["raw"]
    if region["axis"] == "lo":
        return f"[{_fmt(lo)}, {_fmt(hi)})"
    if region["axis"] == "hi":
        return f"({_fmt(lo)}, {_fmt(hi)}]"
    return f"[{_fmt(lo)}, {_fmt(hi)}]"


def _added_regions(cfg, other, key: str, rows, path: str) -> list[dict]:
    """Intervals one arm adds relative to the other, in the adding arm's own box.

    WHY: the L1 treatment lowered ``g_fc_hz`` lo 600 -> 540, but every prior top-k design
    sat at ~638-700 Hz. The key was active, yet the added [540, 600) region had never been
    searched, so a J difference could not be attributed to it (2026-11-14 L1).
    """
    a = cfg.bounds_raw.get(key)
    b = other.bounds_raw.get(key)
    a_label = path
    b_label = str(getattr(other, "_preflight_path", "(other)"))
    regions: list[dict] = []
    if not isinstance(a, dict) or not isinstance(b, dict):
        existing = a if isinstance(a, dict) else b if isinstance(b, dict) else None
        if existing is not None:
            bound = _bound_from(existing)
            if bound is not None:
                label = a_label if isinstance(a, dict) else b_label
                regions.append(_make_added_region(
                    rows, key, bound, bound.lo, bound.hi, "whole", label))
        return regions
    a_bound, b_bound = _bound_from(a), _bound_from(b)
    if (bool(a.get("search", True)) != bool(b.get("search", True))
            or bool(a.get("log", False)) != bool(b.get("log", False))):
        bound = a_bound or b_bound
        if bound is not None:
            label = a_label if a_bound is not None else b_label
            regions.append(_make_added_region(
                rows, key, bound, bound.lo, bound.hi, "whole", label))
        return regions
    try:
        a_lo, a_hi = float(a["lo"]), float(a["hi"])
        b_lo, b_hi = float(b["lo"]), float(b["hi"])
    except (KeyError, TypeError, ValueError):
        return regions
    if a_lo < b_lo and a_bound is not None:
        regions.append(_make_added_region(rows, key, a_bound, a_lo, b_lo, "lo", a_label))
    elif b_lo < a_lo and b_bound is not None:
        regions.append(_make_added_region(rows, key, b_bound, b_lo, a_lo, "lo", b_label))
    if a_hi > b_hi and a_bound is not None:
        regions.append(_make_added_region(rows, key, a_bound, b_hi, a_hi, "hi", a_label))
    elif b_hi > a_hi and b_bound is not None:
        regions.append(_make_added_region(rows, key, b_bound, a_hi, b_hi, "hi", b_label))
    return regions


def _check_ab(cfg, other, path: str, report: dict, space, from_runs, top_k: int) -> None:
    """Check 7: is this a matched A/B arm, and do the changed knobs actually move?

    WHY: the 2026-11-14 report items compared arms that differed in budget/backend or in a
    knob that never left one value in the prior top-k, so "no effect" could not be read as
    a result. A changed key whose prior top-k normalized spread is < 0.02 (or whose best
    row sits within 1% of a bound) is pinned/inactive and cannot separate the arms. Even an
    active key can be blind on the treatment side: the L1 lowers ``g_fc_hz`` lo 600 -> 540
    while every prior top-k design sits at ~638-700 Hz, so the added [540, 600) region was
    never searched; ``ab_unvisited_region`` reports that independently.
    """
    if other is None:
        return
    changed = _changed_bound_keys(cfg, other)
    mine = _arm_identity(cfg)
    theirs = _arm_identity(other)
    unmatched = {
        field: [mine[field], theirs[field]]
        for field in mine
        if mine[field] != theirs[field]
    }
    info = {
        "other": str(getattr(other, "_preflight_path", "(other)")),
        "changed_keys": changed,
        "unmatched": unmatched,
        "inactive_keys": {},
        "added_regions": {},
        "binding_keys": {},
        "all_changed_inactive": None,
    }
    report["ab"] = info
    if unmatched:
        detail = ", ".join(f"{k}: {v[0]!r} != {v[1]!r}" for k, v in unmatched.items())
        report["findings"].append(_finding(
            "WARN", "ab_unmatched",
            f"arms are not a matched pair ({detail}); a J difference cannot be attributed "
            f"to the changed bounds",
            path))
    if not changed:
        return
    if not from_runs or space is None:
        info["note"] = "no --from-runs: changed-key activity cannot be checked"
        return
    rows = _top_rows(cfg, space, from_runs, top_k)
    if not rows:
        info["note"] = "no usable prior top-k rows: changed-key activity cannot be checked"
        return

    # The binding dimension of the prior top-k: a key whose BEST design sits on a bound.
    # The 2026-11-14 L1 lesson is not that the added fc region was unvisited (the treatment
    # run did sample it) but that every winner pinned g_stop_deg at its lo bound while the
    # treatment moved g_fc_hz, so the treatment never relieved the actual constraint.
    binding_keys: dict[str, dict] = {}
    top_unit = rows[0][1]
    top_raw = rows[0][2]
    for key in space.keys():
        if key not in top_unit:
            continue
        unit = float(top_unit[key])
        if unit <= INACTIVE_BOUND_BAND:
            side = "lo"
        elif unit >= 1.0 - INACTIVE_BOUND_BAND:
            side = "hi"
        else:
            continue
        binding_keys[key] = {"side": side, "unit": unit, "raw": top_raw.get(key)}
    info["binding_keys"] = binding_keys
    if binding_keys and not (set(binding_keys) & set(changed)):
        pinned = "; ".join(
            f"{key} at its {entry['side']} bound (raw {_fmt(entry['raw'])})"
            for key, entry in sorted(binding_keys.items())
        )
        report["findings"].append(_finding(
            "WARN", "ab_treatment_misses_binding_key",
            f"prior top-k pins {pinned}; the treatment changes "
            f"{', '.join(sorted(changed))}, so it cannot relieve the binding constraint "
            f"(2026-11-14 L1: winners at g_stop_deg=120.0, treatment moved g_fc_hz "
            f"lo 600->540)",
            path))

    inactive: dict[str, dict] = {}
    incomplete = False
    for key in changed:
        if key not in space.bounds:
            incomplete = True
            continue
        values = [unit[key] for _, unit, _ in rows if key in unit]
        if not values:
            incomplete = True
            continue
        spread = float(max(values) - min(values))
        top1 = float(values[0])
        at_bound = top1 <= INACTIVE_BOUND_BAND or top1 >= 1.0 - INACTIVE_BOUND_BAND
        is_inactive = bool(spread < INACTIVE_SPREAD or at_bound)
        inactive[key] = {"spread": spread, "top1": top1, "at_bound": at_bound,
                         "inactive": is_inactive}
        if not is_inactive:
            incomplete = True
    info["inactive_keys"] = inactive
    if not incomplete and inactive:
        info["all_changed_inactive"] = True
        report["findings"].append(_finding(
            "WARN", "ab_changed_keys_inactive",
            f"every changed bound key ({', '.join(sorted(inactive))}) is pinned/inactive in "
            f"the prior top-k (normalized spread < {INACTIVE_SPREAD} or top-1 within 1% of "
            f"a bound); the A/B cannot separate the arms (2026-11-14 evidence)",
            path))
    else:
        info["all_changed_inactive"] = False

    # A widening experiment is EXPECTED to open regions the prior top-k never visited.
    # This is INFO, not a verdict: the treatment run's own ndjson must be checked to see
    # whether it sampled the added region (the preflight cannot see that run otherwise).
    added_regions = {
        key: regions
        for key in changed
        if (regions := _added_regions(cfg, other, key, rows, path))
    }
    info["added_regions"] = added_regions
    unvisited = [
        (key, region)
        for key, regions in added_regions.items()
        for region in regions
        if region["n"] > 0 and region["rows_inside"] == 0
    ]
    if unvisited:
        n = unvisited[0][1]["n"]
        descriptors = [
            f"{region['treatment']} adds {_format_added_region(region)} for {key}"
            for key, region in unvisited
        ]
        shown = descriptors[:3]
        if len(descriptors) > 3:
            shown.append(f"+{len(descriptors) - 3} more")
        report["findings"].append(_finding(
            "INFO", "ab_region_unrepresented_in_prior",
            f"{'; '.join(shown)}; 0/{n} prior top-k designs lie there, which is expected "
            f"for a widening experiment. Confirm the treatment run's own ndjson samples "
            f"that region (pass it to --from-runs); the preflight cannot see it otherwise.",
            path))


_VALID_DIRECTIVITIES = frozenset(("cd", "narrowing"))


def _load_brief_raw(cfg, config_path: str) -> dict | None:
    """Load the raw brief YAML for a config, or None when it cannot be read.

    The brief is either embedded (``cfg.raw["brief"]`` dict) or referenced by
    ``brief_file:``. Path resolution follows the same rules as ``load_config``.
    """
    raw = getattr(cfg, "raw", None) or {}
    embedded = raw.get("brief")
    if isinstance(embedded, dict):
        return embedded
    brief_file = raw.get("brief_file")
    if not brief_file:
        return None
    config_dir = Path(config_path).parent
    for base in (config_dir, REPO):
        candidate = base / brief_file
        try:
            if candidate.exists():
                return yaml.safe_load(candidate.read_text(encoding="utf-8")) or {}
        except Exception:  # noqa: BLE001 - unreadable brief = no check
            pass
    return None


def _check_directivity(cfg, path: str, report: dict) -> None:
    """Item 8 (2026-11-16): HARD when the typology and brief disagree on directivity tag.

    Both the typology YAML and the brief YAML carry an optional ``directivity: cd | narrowing``
    top-level key. When BOTH are tagged and the tags differ, the pairing is wrong (a CD-only
    brief on a narrowing typology, or vice versa) and the run must be refused.
    """
    raw = getattr(cfg, "raw", None) or {}
    cfg_dir = raw.get("directivity")
    if cfg_dir is None:
        return
    cfg_dir = str(cfg_dir).strip()
    if cfg_dir not in _VALID_DIRECTIVITIES:
        return  # unknown tag - not our problem here
    brief_raw = _load_brief_raw(cfg, path)
    if not isinstance(brief_raw, dict):
        return
    brief_dir = brief_raw.get("directivity")
    if brief_dir is None:
        return
    brief_dir = str(brief_dir).strip()
    if brief_dir not in _VALID_DIRECTIVITIES:
        return
    if cfg_dir != brief_dir:
        report["findings"].append(_finding(
            "HARD", "directivity_mismatch",
            f"directivity mismatch: typology says {cfg_dir!r} but brief says {brief_dir!r}; "
            f"a narrowing typology must not run with a CD brief and vice versa "
            f"(item 8, 2026-11-16)",
            path))


# ------------------------------------------------------------------ reporting

def _analyze(cfg, path: str, args, other, prior_bests) -> dict:
    report = _new_report(cfg, path)
    report["searched_keys"] = sorted(_searched_bounds(cfg))
    _check_seed(cfg, path, report)
    _check_directivity(cfg, path, report)
    try:
        space = DesignSpace.from_config(cfg)
    except Exception as exc:  # noqa: BLE001 - a broken box is a hard config fault
        space = None
        report["findings"].append(_finding(
            "HARD", "space_build_failed",
            f"DesignSpace.from_config failed: {type(exc).__name__}: {exc}",
            path))
    if space is not None:
        report["searched_keys"] = sorted(space.keys())
        _check_no_headroom(cfg, path, report, space, prior_bests)
    record = _check_history(cfg, path, report, space, args.from_runs, args.top_k)
    _sample(cfg, path, report, space, args.samples, args.seed, args.geometry_only)
    sampling = report.get("sampling") or {}
    refusal_fraction = sampling.get("refusal_fraction")
    dims = len(space.keys()) if space is not None else 0
    _check_sigma(cfg, path, report, record, dims, refusal_fraction,
                 args.min_expected_hits)
    _check_graded(cfg, path, report)
    _check_ab(cfg, other, path, report, space, args.from_runs, args.top_k)
    return report


def _cell(value) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _table(report: dict) -> list[str]:
    sampling = report.get("sampling") or {}
    sigma = report.get("sigma") or {}
    history = report.get("history")
    graded = report.get("graded") or {}
    ab = report.get("ab")
    lines = [
        f"### {report['name']}",
        "",
        f"`{report['path']}`",
        "",
        "| item | value |",
        "| --- | --- |",
    ]

    def row(label, value):
        lines.append(f"| {_cell(label)} | {_cell(value)} |")

    family = report["family"]
    if report.get("generator"):
        family += f" (generator: {report['generator']})"
    row("family", family)
    row("searched keys", ", ".join(report["searched_keys"]) or "(none)")
    outside = report.get("seed_outside_box") or []
    row("seed in box", "NO - " + "; ".join(
        f"{o['key']}={_fmt(o['value'])} outside [{_fmt(o['lo'])}, {_fmt(o['hi'])}]"
        for o in outside) if outside else "yes")
    row("seed key missing", ", ".join(report.get("seed_key_missing") or []) or "none")
    no_history = [f for f in report["findings"] if f["code"] == "no_headroom"]
    if no_history:
        row("seed headroom", "NO - seed matches a prior best (headroom by construction)")
    elif report.get("seed_design_hash"):
        row("seed headroom", f"seed hash {report['seed_design_hash']} differs from prior best")
    else:
        row("seed headroom", "not checked (no --from-runs)")
    if history:
        spread = (history.get("sigma_from_spread") or {}).get("median_spread")
        row("history", f"mean J {_fmt(history.get('mean_objective'))}; "
                       f"mean hash {_fmt(history.get('mean_design_hash'))}; "
                       f"sigma0 {_fmt(history.get('sigma0'))}; "
                       f"spread {_fmt(spread) if spread is not None else 'n/a'}; "
                       f"sources {len(history.get('sources') or [])}")
    else:
        unusable = [f for f in report["findings"] if f["code"] == "history_unusable"]
        row("history", "unusable (WARN history_unusable)" if unusable else "no_history")
    if sigma:
        expected = sigma.get("expected_hits")
        row("sigma / hits", f"config {_fmt(sigma.get('config_sigma0'))}; "
                            f"recommended {_fmt(sigma.get('recommended_sigma'))}; "
                            f"spread {_fmt(sigma.get('median_spread'))}; "
                            f"expected hits "
                            f"{'n/a' if expected is None else f'{expected:.2f}'} "
                            f"(min {_fmt(sigma.get('min_expected_hits'))})")
    if sampling:
        if sampling.get("status") == "not sampled":
            row("sampling", "not sampled (--samples 0)")
        else:
            kinds = sampling.get("kinds") or {}
            tally = ", ".join(f"{k}={v}" for k, v in sorted(kinds.items())) or "none"
            row("sampling", f"{sampling.get('status')}; N={sampling.get('samples')}; "
                            f"valid={sampling.get('valid')} refused={sampling.get('refused')}"
                            + (f" unvalidated={sampling['unvalidated']}"
                               if sampling.get("unvalidated") else "")
                            + "; uniform box sample (an upper bound away from the seed; "
                              "CMA concentrates near it)")
            row("refusals", f"valid fraction "
                            f"{_fmt(sampling.get('valid_fraction'))}; "
                            f"predicted valid evals "
                            f"{_fmt(sampling.get('predicted_valid_evals'))}; [{tally}]")
    if graded:
        row("graded penalty", f"{graded.get('infeasible_penalty')}; "
                              f"sampled refusals {graded.get('sampled_refusals')}; "
                              f"invalid_envelope {graded.get('invalid_envelope')}")
    if ab:
        changed = ", ".join(ab.get("changed_keys") or []) or "none"
        row(f"A/B vs {ab.get('other')}", f"changed searched bound keys: {changed}")
        if ab.get("all_changed_inactive"):
            row("A/B activity", "WARN: every changed key is pinned/inactive in the prior top-k")
        binding = ab.get("binding_keys") or {}
        if binding:
            row("A/B binding keys", "; ".join(
                f"{key} at {entry['side']} (raw {_fmt(entry['raw'])})"
                for key, entry in sorted(binding.items())))
        added = ab.get("added_regions") or {}
        if added:
            parts = []
            for key, regions in sorted(added.items()):
                for region in regions:
                    parts.append(
                        f"{key} {_format_added_region(region)} "
                        f"({region['rows_inside']}/{region['n']} prior rows)")
            if len(parts) > 3:
                parts = parts[:3] + [f"+{len(parts) - 3} more"]
            row("A/B added regions", "; ".join(parts))
    return lines


def _render_markdown(reports: list[dict], strict: bool) -> str:
    lines: list[str] = ["# hornlab-search preflight", ""]
    for report in reports:
        lines.extend(_table(report))
        lines.append("")
    lines.append("### WARN / HARD")
    lines.append("")
    findings = [f for r in reports for f in r["findings"]
                if f["severity"] in ("WARN", "HARD")]
    if findings:
        for finding in findings:
            lines.append(f"- {finding['severity']} `{finding['code']}` "
                         f"({finding['config']}): {finding['message']}")
    else:
        lines.append("No WARN/HARD findings.")
    infos = [f for r in reports for f in r["findings"] if f["severity"] == "INFO"]
    if infos:
        lines.append("")
        lines.append("### INFO")
        lines.append("")
        for finding in infos:
            lines.append(f"- `{finding['code']}` ({finding['config']}): "
                         f"{finding['message']}")
    lines.append("")
    hards = [f for f in findings if f["severity"] == "HARD"]
    warns = [f for f in findings if f["severity"] == "WARN"]
    if hards:
        lines.append(f"Result: HARD ({len(hards)} hard fault(s)) - do not spend a night.")
    elif warns and strict:
        lines.append(f"Result: WARN ({len(warns)} warning(s)) and --strict - refusing.")
    elif warns:
        lines.append(f"Result: ok with {len(warns)} warning(s) (use --strict to refuse).")
    else:
        lines.append("Result: ok.")
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------ CLI

def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="search_preflight.py",
        description="Pre-flight gate for a hornlab-search run: seed, history, sigma, "
                    "refusals and A/B matching.")
    parser.add_argument("configs", nargs="+", metavar="CONFIG",
                        help="one or more config YAMLs")
    parser.add_argument("--brief", metavar="PATH", default=None,
                        help="brief to apply (same as load_config --brief)")
    parser.add_argument("--from-runs", nargs="+", default=None, metavar="RUN_DIR",
                        help="prior run directories for history/headroom/spread checks")
    parser.add_argument("--samples", type=int, default=0, metavar="N",
                        help="sample N points through the real validator (default 0 = no mesh)")
    parser.add_argument("--geometry-only", action="store_true",
                        help="sample only the generated-design _generator_error (no gmsh)")
    parser.add_argument("--ab", metavar="OTHER_CONFIG", default=None,
                        help="compare every CONFIG with this other arm")
    parser.add_argument("--top-k", type=int, default=10, metavar="K",
                        help="prior top-k rows for spread/activity (default 10)")
    parser.add_argument("--min-expected-hits", type=float, default=3.0, metavar="H",
                        help="warn when expected in-basin hits fall below H (default 3.0)")
    parser.add_argument("--seed", type=int, default=0, metavar="S",
                        help="deterministic sampling RNG seed (default 0)")
    parser.add_argument("--json", action="store_true",
                        help="print one JSON object instead of markdown")
    parser.add_argument("--strict", action="store_true",
                        help="exit 1 on warnings as well as hard faults")
    return parser


def main(argv=None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.samples < 0:
        parser.error("--samples must be >= 0")
    if args.top_k < 1:
        parser.error("--top-k must be >= 1")
    if args.min_expected_hits <= 0:
        parser.error("--min-expected-hits must be > 0")

    configs = []
    for path in args.configs:
        try:
            configs.append((path, load_config(path, brief=args.brief)))
        except (ConfigError, OSError) as exc:
            print(f"error: {path}: {exc}", file=sys.stderr)
            return 2
    other = None
    if args.ab:
        try:
            other = load_config(args.ab, brief=args.brief)
            # A presentation-only attribute; Config is a dataclass and stays untouched.
            setattr(other, "_preflight_path", args.ab)
        except (ConfigError, OSError) as exc:
            print(f"error: {args.ab}: {exc}", file=sys.stderr)
            return 2

    prior_bests = _prior_bests(args.from_runs)
    reports = [_analyze(cfg, path, args, other, prior_bests) for path, cfg in configs]
    findings = [f for r in reports for f in r["findings"]]
    hards = [f for f in findings if f["severity"] == "HARD"]
    warns = [f for f in findings if f["severity"] == "WARN"]
    exit_code = 1 if (hards or (warns and args.strict)) else 0

    if args.json:
        payload = {
            "strict": bool(args.strict),
            "exit_code": exit_code,
            "configs": reports,
            "hards": hards,
            "warnings": warns,
            "infos": [f for f in findings if f["severity"] == "INFO"],
        }
        print(json.dumps(payload, indent=2, default=str))
    else:
        print(_render_markdown(reports, args.strict), end="")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
