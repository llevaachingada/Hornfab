"""Recommend which CMA search knobs to pin from a finished run's covariance snapshot.

Rules (plan 2026-10-31): small ``σ√C_ii`` share + below-median std → propose pin at the run's
best value, unless Spearman |ρ| says the knob still drives J. Never auto-mutates a live search;
callers write ``pin_plan.json`` / a patched YAML.

B.3 (day 2026-11-12): wall analysis from the run's OWN ``search.ndjson`` (top-decile fraction
within a relative margin of each bound) and the ``narrow`` config writer: a copy of the run's
``config.yaml`` where ONLY the bounds, ``search.seed`` (+1) and ``name`` may change, with a
header comment listing exactly what changed and why. ``--widen`` additionally WIDENS the knobs
walled at a bound (owner opt-in); knobs walled in >50% of all valid rows are flagged for
PINNING instead. No tools/analysis import — this is self-contained here.
"""
from __future__ import annotations

import copy
import math
from pathlib import Path
from typing import Any

DEFAULT_SHARE_FLOOR = 0.04
DEFAULT_SHARE_FACTOR = 0.5
DEFAULT_STD_RATIO = 0.35
DEFAULT_RHO_KEEP = 0.35
DEFAULT_MIN_KEEP = 2
DEFAULT_MAX_PIN_FRACTION = 0.5

# B.3 (narrow) defaults; all overridable through the CLI for one call of the writer.
DEFAULT_WALL_FRAC = 0.03     # a design is "at a wall" within 3% of the box span from a bound
DEFAULT_WALL_MASS = 0.5      # >= half the top decile at a wall counts as walled
DEFAULT_PAD_FRAC = 0.10      # narrow margin beyond the top-decile span, in old-box widths
WIDEN_STEP_FRAC = 0.10       # --widen extends a walled side by this fraction of the span
DEFAULT_PIN_CAND_FRAC = 0.5  # all-rows wall fraction above this → flagged for pinning


def _as_dict(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _median(xs: list[float]) -> float:
    if not xs:
        return 0.0
    s = sorted(xs)
    m = len(s) // 2
    if len(s) % 2:
        return float(s[m])
    return 0.5 * (float(s[m - 1]) + float(s[m]))


def permanently_pinned_keys(bounds: dict | None) -> set[str]:
    """Keys already ``search: false`` in the config bounds."""
    out: set[str] = set()
    for k, v in _as_dict(bounds).items():
        if isinstance(v, dict) and v.get("search") is False:
            out.add(str(k))
    return out


def recommend_pins(
    cma_covariance: dict,
    *,
    best_params: dict | None = None,
    sens: list[dict] | None = None,
    bounds: dict | None = None,
    share_floor: float = DEFAULT_SHARE_FLOOR,
    share_factor: float = DEFAULT_SHARE_FACTOR,
    std_ratio: float = DEFAULT_STD_RATIO,
    rho_keep: float = DEFAULT_RHO_KEEP,
    min_keep: int = DEFAULT_MIN_KEEP,
    max_pin_fraction: float = DEFAULT_MAX_PIN_FRACTION,
) -> dict[str, Any]:
    """Return a JSON-able pin plan from ``cma_covariance`` (+ optional Spearman / best).

    Each decision: ``{key, action: pin|keep, value?, reasons[], share, std_unit, C_ii?, rho?}``.
    """
    cov = _as_dict(cma_covariance)
    coords = list(cov.get("coordinates") or [])
    if not coords:
        return {
            "decisions": [],
            "pin": [],
            "keep": [],
            "thresholds": {},
            "note": "no cma_covariance.coordinates — nothing to recommend",
        }

    best = {str(k): v for k, v in _as_dict(best_params).items()}
    rho_by_key: dict[str, float | None] = {}
    for row in sens or []:
        if isinstance(row, dict) and row.get("key") is not None:
            rho_by_key[str(row["key"])] = (
                float(row["rho"]) if row.get("rho") is not None else None
            )

    permanent = permanently_pinned_keys(bounds)
    # Only consider knobs that appear in the covariance (searchable at search time).
    rows: list[dict] = []
    stds: list[float] = []
    for c in coords:
        if not isinstance(c, dict) or c.get("key") is None:
            continue
        key = str(c["key"])
        if key in permanent:
            continue
        std = float(c.get("std_unit") or 0.0)
        share = float(c.get("share") or 0.0)
        rows.append({
            "key": key,
            "share": share,
            "std_unit": std,
            "C_ii": float(c["C_ii"]) if c.get("C_ii") is not None else None,
            "rho": rho_by_key.get(key),
        })
        stds.append(std)

    n = len(rows)
    if n == 0:
        return {
            "decisions": [],
            "pin": [],
            "keep": [],
            "thresholds": {},
            "note": "all covariance knobs are already permanently pinned",
        }

    share_thresh = max(float(share_floor), float(share_factor) / float(n))
    med_std = _median(stds)
    std_thresh = float(std_ratio) * med_std
    max_pins = max(0, min(n - int(min_keep), int(math.floor(float(max_pin_fraction) * n))))

    # Rank pin candidates: smallest share first (ties → smaller std_unit, then key).
    candidates = sorted(rows, key=lambda r: (r["share"], r["std_unit"], r["key"]))
    pin_keys: list[str] = []
    reasons_by_key: dict[str, list[str]] = {r["key"]: [] for r in rows}

    for r in candidates:
        key = r["key"]
        reasons: list[str] = []
        eligible = True
        if r["share"] > share_thresh:
            eligible = False
            reasons.append(f"share {r['share']:.4f} > thresh {share_thresh:.4f}")
        else:
            reasons.append(f"share {r['share']:.4f} ≤ thresh {share_thresh:.4f}")
        if r["std_unit"] > std_thresh:
            eligible = False
            reasons.append(f"std_unit {r['std_unit']:.4f} > {std_ratio}×median={std_thresh:.4f}")
        else:
            reasons.append(f"std_unit {r['std_unit']:.4f} ≤ {std_ratio}×median={std_thresh:.4f}")
        rho = r["rho"]
        if rho is not None and abs(float(rho)) >= float(rho_keep):
            eligible = False
            reasons.append(f"|rho|={abs(float(rho)):.3f} ≥ rho_keep={rho_keep} (Spearman veto)")
        elif rho is not None:
            reasons.append(f"|rho|={abs(float(rho)):.3f} < rho_keep={rho_keep}")
        if key not in best:
            eligible = False
            reasons.append("no_best_value")
        if eligible:
            if len(pin_keys) >= max_pins:
                reasons.append(f"cap max_pins={max_pins} reached")
                eligible = False
            else:
                reasons.append("propose pin at best")
                pin_keys.append(key)
        reasons_by_key[key] = reasons

    pin_set = set(pin_keys)
    # Enforce min_keep: if somehow over-pinned, drop highest-share pins first.
    while n - len(pin_set) < int(min_keep) and pin_set:
        drop = max(pin_set, key=lambda k: next(r["share"] for r in rows if r["key"] == k))
        pin_set.remove(drop)
        reasons_by_key[drop].append(f"reverted to keep (min_keep={min_keep})")

    decisions: list[dict] = []
    for r in sorted(rows, key=lambda x: (0 if x["key"] in pin_set else 1, x["share"], x["key"])):
        key = r["key"]
        action = "pin" if key in pin_set else "keep"
        rec: dict[str, Any] = {
            "key": key,
            "action": action,
            "reasons": reasons_by_key[key],
            "share": r["share"],
            "std_unit": r["std_unit"],
            "C_ii": r["C_ii"],
            "rho": r["rho"],
        }
        if action == "pin":
            rec["value"] = float(best[key])
        decisions.append(rec)

    return {
        "decisions": decisions,
        "pin": [d["key"] for d in decisions if d["action"] == "pin"],
        "keep": [d["key"] for d in decisions if d["action"] == "keep"],
        "thresholds": {
            "share_floor": float(share_floor),
            "share_factor": float(share_factor),
            "share_thresh": share_thresh,
            "std_ratio": float(std_ratio),
            "std_thresh": std_thresh,
            "median_std_unit": med_std,
            "rho_keep": float(rho_keep),
            "min_keep": int(min_keep),
            "max_pin_fraction": float(max_pin_fraction),
            "max_pins": max_pins,
            "n_searchable": n,
        },
        "permanently_pinned": sorted(permanent),
        "note": ("Pins are recommendations from the CMA search distribution + Spearman guard; "
                 "not a physical Sobol decomposition. Apply with apply_pins_to_config / CLI."),
    }


def apply_pins_to_config(doc: dict, plan: dict) -> dict:
    """Return a deep copy of ``doc`` with recommended pins applied (``search: false``, lo=hi).

    Also sets ``seed_params[key]`` to the pin value so the seed matches the pinned geometry.
    Keys not marked ``action: pin`` are left unchanged.
    """
    out = copy.deepcopy(doc)
    bounds = dict(_as_dict(out.get("bounds")))
    seed = dict(_as_dict(out.get("seed_params")))
    for d in plan.get("decisions") or []:
        if not isinstance(d, dict) or d.get("action") != "pin":
            continue
        key = str(d["key"])
        if d.get("value") is None:
            continue
        v = float(d["value"])
        bounds[key] = {"lo": v, "hi": v, "search": False}
        seed[key] = v
    out["bounds"] = bounds
    out["seed_params"] = seed
    return out


def format_pin_plan_md(plan: dict, *, run_id: str | None = None) -> str:
    """Markdown table for ``PIN_PLAN.md``."""
    lines = [
        "# CMA pin plan",
        "",
    ]
    if run_id:
        lines.append(f"Run: `{run_id}`")
        lines.append("")
    th = _as_dict(plan.get("thresholds"))
    if th:
        lines += [
            "## Thresholds",
            "",
            f"- share ≤ `{th.get('share_thresh')}` "
            f"(floor `{th.get('share_floor')}`, factor/N `{th.get('share_factor')}`/`{th.get('n_searchable')}`)",
            f"- std_unit ≤ `{th.get('std_ratio')}` × median `{th.get('median_std_unit')}` → `{th.get('std_thresh')}`",
            f"- Spearman veto if `|rho|` ≥ `{th.get('rho_keep')}`",
            f"- min_keep `{th.get('min_keep')}`, max_pins `{th.get('max_pins')}`",
            "",
        ]
    perm = plan.get("permanently_pinned") or []
    if perm:
        lines += ["Permanently pinned (unchanged): " + ", ".join(f"`{k}`" for k in perm), ""]
    lines += [
        "## Decisions",
        "",
        "| Key | Action | Value | share | σ√Cᵢᵢ | ρ | Reasons |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for d in plan.get("decisions") or []:
        val = d.get("value")
        val_s = f"{val:.6g}" if isinstance(val, (int, float)) else "—"
        rho = d.get("rho")
        rho_s = f"{rho:.3f}" if isinstance(rho, (int, float)) else "—"
        reasons = "; ".join(d.get("reasons") or [])
        lines.append(
            f"| `{d.get('key')}` | **{d.get('action')}** | {val_s} | "
            f"{float(d.get('share') or 0):.4f} | {float(d.get('std_unit') or 0):.4f} | "
            f"{rho_s} | {reasons} |"
        )
    pin = plan.get("pin") or []
    keep = plan.get("keep") or []
    lines += [
        "",
        f"**Pin ({len(pin)}):** " + (", ".join(f"`{k}`" for k in pin) if pin else "_(none)_"),
        f"**Keep ({len(keep)}):** " + (", ".join(f"`{k}`" for k in keep) if keep else "_(none)_"),
        "",
    ]
    if plan.get("note"):
        lines += [f"_{plan['note']}_", ""]
    return "\n".join(lines)


# ---------------------------------------------------------------------- B.3 (narrow / widen)


def _param_get(family: str, params: dict, key: str):
    from hornlab_search.design import families as _families
    return _families.param_get(family, params, key)


def wall_analysis(rows: list[dict], bounds: dict, *, family: str = "OSSE",
                  wall_frac: float = DEFAULT_WALL_FRAC) -> dict:
    """Per searched knob: the top-decile span and lo/hi wall fractions (top decile AND all
    valid rows). ``rows`` are search.ndjson rows; a row counts when ``ok`` and its params
    carry the knob. JSON-able."""
    valid = [r for r in rows if r.get("ok") and isinstance(r.get("params"), dict)]
    n = len(valid)
    k = max(1, math.ceil(0.1 * n))
    top = sorted(valid, key=lambda r: (float(r.get("objective", math.inf)), str(r.get("n"))))[:k]
    knobs: dict[str, Any] = {}
    for key, b in sorted(_as_dict(bounds).items()):
        if not isinstance(b, dict) or b.get("search") is False:
            continue
        lo, hi = float(b.get("lo")), float(b.get("hi"))
        if not (math.isfinite(lo) and math.isfinite(hi)) or hi <= lo:
            continue
        span = hi - lo
        tol = float(wall_frac) * span

        def _vals(rs):
            vs = []
            for r in rs:
                try:
                    vs.append(float(_param_get(family, r["params"], key)))
                except Exception:  # noqa: BLE001 - missing/unwrappable key: not countable
                    return None
            return vs

        vs_top, vs_all = _vals(top), _vals(valid)
        if vs_top is None or vs_all is None:
            continue

        def _frac(vs, wall):
            # lo wall: value <= lo + tol; hi wall: value >= hi - tol
            if wall == "lo":
                return (sum(1 for v in vs if v <= lo + tol) / len(vs)) if vs else 0.0
            return (sum(1 for v in vs if v >= hi - tol) / len(vs)) if vs else 0.0

        knobs[str(key)] = {"lo": lo, "hi": hi, "n_top": len(vs_top),
                           "top_lo": min(vs_top), "top_hi": max(vs_top),
                           "wall_lo_frac_top": _frac(vs_top, "lo"),
                           "wall_hi_frac_top": _frac(vs_top, "hi"),
                           "wall_lo_frac_all": _frac(vs_all, "lo"),
                           "wall_hi_frac_all": _frac(vs_all, "hi")}
    return {"n_valid": n, "top_decile_n": k, "wall_frac": float(wall_frac), "knobs": knobs}


def narrow_bounds(analysis: dict, bounds: dict, *, wall_mass: float = DEFAULT_WALL_MASS,
                  pad_frac: float = DEFAULT_PAD_FRAC, widen: bool = False) -> tuple[dict, list[dict], list[str]]:
    """(new bounds dict, changes list, pin candidates).

    Rule per searched knob (from the plan's A.5 + B.3 amendment): narrow the non-walled sides
    to the top-decile span padded by ``pad_frac * old span`` (clipped inside the current box);
    a side with >= ``wall_mass`` of the top decile at the wall is NOT narrowed — it gets WIDENED
    by ``WIDEN_STEP_FRAC * span`` only when ``widen`` is set. Knobs whose ALL-rows wall fraction
    exceeds 50% are returned as pin candidates (consider ``search: false`` instead). The
    returned dict shares everything except the changed bounds; ``changes`` carries old->new."""
    new_bounds = dict(_as_dict(bounds))
    ka = _as_dict(analysis.get("knobs"))
    changes: list[dict] = []
    pin_candidates: list[str] = []
    for key in sorted(new_bounds):
        info = ka.get(key)
        if not info:
            continue
        b = new_bounds[key]
        lo, hi = float(info["lo"]), float(info["hi"])
        span = hi - lo
        old = bool(b.get("search", True))
        w_hi, w_lo = float(info["wall_hi_frac_top"]), float(info["wall_lo_frac_top"])
        all_w_hi, all_w_lo = float(info["wall_hi_frac_all"]), float(info["wall_lo_frac_all"])
        new = dict(b)
        new_lo = lo if w_lo >= wall_mass else max(lo, info["top_lo"] - pad_frac * span) \
            if old else lo
        new_hi = hi if w_hi >= wall_mass else min(hi, info["top_hi"] + pad_frac * span) \
            if old else hi
        if widen and w_hi >= wall_mass and old:
            new_hi = hi + WIDEN_STEP_FRAC * span
        if widen and w_lo >= wall_mass and old:
            new_lo = lo - WIDEN_STEP_FRAC * span
        if all_w_hi > 0.5 or all_w_lo > 0.5:
            pin_candidates.append(key)
        # rounding: bounds are usually given to <= 6 significant decimals; keep repr-clean
        new_lo = round(new_lo, 10)
        new_hi = round(new_hi, 10)
        if new_hi <= new_lo:
            continue
        delta = []
        if new_lo != lo:
            new["lo"] = new_lo
            delta.append(f"lo {lo:g}->{new_lo:g}")
        if new_hi != hi:
            new["hi"] = new_hi
            delta.append(f"hi {hi:g}->{new_hi:g}")
        if delta:
            new_bounds[key] = new
            changes.append({"key": key, "changes": delta, "old_lo": lo, "old_hi": hi,
                            "new_lo": new_lo, "new_hi": new_hi,
                            "wall_hi_frac_top": w_hi, "wall_lo_frac_top": w_lo})
    return new_bounds, changes, pin_candidates


def write_narrow_config(run_dir: Path, *, out_path: Path, family: str = "OSSE",
                        wall_frac: float = DEFAULT_WALL_FRAC,
                        wall_mass: float = DEFAULT_WALL_MASS,
                        pad_frac: float = DEFAULT_PAD_FRAC, widen: bool = False) -> dict:
    """Write ``out_path``: a copy of the run's ``config.yaml`` where ONLY the bounds,
    ``search.seed`` (+1) and ``name`` may change (B.3), plus a header comment listing exactly
    what changed and why. Returns the report (analysis summary, changes, out path). Raises
    FileNotFoundError when the run has no config.yaml / search.ndjson."""
    import yaml

    run_dir = Path(run_dir)
    cfg_path = run_dir / "config.yaml"
    if not cfg_path.is_file():
        raise FileNotFoundError(f"{cfg_path} not found (the run dir has no config snapshot)")
    doc = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    rows = read_rows(run_dir)
    if not rows:
        raise FileNotFoundError(f"{run_dir / 'search.ndjson'} has no rows")
    bounds = doc.get("bounds")
    if not isinstance(bounds, dict):
        raise ValueError("the run's config.yaml has no bounds mapping")
    analysis = wall_analysis(rows, bounds, family=family, wall_frac=wall_frac)
    new_bounds, changes, pin_candidates = narrow_bounds(
        analysis, bounds, wall_mass=wall_mass, pad_frac=pad_frac, widen=widen)
    out = copy.deepcopy(doc)
    out["bounds"] = new_bounds
    # seed +1 and name are the ONLY other permitted changes
    cfg_search = out.get("search") if isinstance(out.get("search"), dict) else {}
    old_seed = cfg_search.get("seed")
    seed_val = int(old_seed) + 1 if isinstance(old_seed, (int, float)) else old_seed
    if isinstance(cfg_search, dict):
        cfg_search["seed"] = seed_val
        out["search"] = cfg_search
    else:
        out["search"] = {"seed": seed_val}
    suffix = "widen" if widen else "narrow"
    base_name = str(doc.get("name") or run_dir.name)
    out["name"] = f"{base_name}_{suffix}"
    header = _narrow_header(run_dir, analysis, changes, pin_candidates, widen=widen,
                           old_seed=old_seed, new_seed=seed_val,
                           old_name=base_name, new_name=out["name"])
    text = header + yaml.safe_dump(out, sort_keys=False)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
    return {"analysis": analysis, "changes": changes, "pin_candidates": pin_candidates,
            "out": str(out_path), "seed": {"old": old_seed, "new": seed_val},
            "name": out["name"]}


def read_rows(run_dir: Path) -> list[dict]:
    from hornlab_search.search.evaluate import read_ndjson
    return read_ndjson(Path(run_dir) / "search.ndjson")


def _narrow_header(run_dir: Path, analysis: dict, changes: list[dict], pin_candidates: list[str],
                   *, widen: bool, old_seed, new_seed, old_name: str, new_name: str) -> str:
    mode = "WIDENED-BOUNDS" if widen else "NARROW-BOUNDS"
    lines = [f"# {mode} FOLLOW-UP (day 2026-11-12 B.3, run {run_dir.name}: "
             f"{analysis['n_valid']} valid, top decile n={analysis['top_decile_n']}, "
             f"wall margin {analysis['wall_frac']:.3f} of each box width):"]
    if changes:
        parts = []
        for c in changes:
            extra = ""
            if widen and max(c["wall_hi_frac_top"], c["wall_lo_frac_top"]) >= DEFAULT_WALL_MASS:
                extra = f" (walled: {max(c['wall_hi_frac_top'], c['wall_lo_frac_top']):.2f} of the top decile)"
            parts.append(f"{c['key']} {' '.join(c['changes'])}{extra}")
        lines.append(f"# ONLY these change vs the run's config.yaml: {', '.join(parts)}, "
                     f"seed {old_seed}->{new_seed}, name {old_name}->{new_name}. "
                     f"Everything else identical.")
    else:
        lines.append(f"# No knob changed: the top decile holds no wall anywhere; ONLY "
                     f"seed {old_seed}->{new_seed} and name {old_name}->{new_name} differ from "
                     f"the run's config.yaml.")
    for k in pin_candidates:
        lines.append(f"# PIN CANDIDATE {k}: at a bound in more than 50% of all valid rows — "
                     f"consider search: false (pin) instead of widening.")
    lines.append("# Generated by hornlab-search narrow (pin_from_cma.wall_analysis); the run dir "
                 "itself is not modified.")
    return "\n".join(l for l in lines) + "\n"
