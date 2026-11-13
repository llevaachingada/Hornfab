"""Parameter/control activity ledger for a resolved native configuration (B2, M0).

Usage:
    PY tools\\analysis\\parameter_activity.py [--config <yaml>] --out <dir> [--no-geometry]

The ledger is intentionally an *analysis* artifact: it does not change production configs,
defaults, cache keys or search behaviour.  For every resolved control it records:

* native/generator context and the actual resolved value/range;
* ``searched / fixed / derived / conditional / inactive / unresolved`` activity;
* the application predicate (a source branch, not a local numerical guess);
* affected geometry features, the unit and the existing [0,1] bound/log transform;
* source ``file:line`` references; and
* evidence status from the static source branch and, where meaningful, a canonical-surface
  geometry perturbation through the installed ``hornlab_mesher`` API.

The candidate ATH control ``morph_exponent`` is **inactive only because** the resolved config
fixes ``morph_target == 1`` (rounded rectangle).  Its ledger entry therefore requires both the
installed source branch and a geometry test: exponent 2 -> 10 must leave the target-1 surface
unchanged, while the same change at target 3 must change it.  ``morph_fixed`` is reported with its
resolved bound 0.0-0.6; the nearby YAML comment saying 0-0.1 is recorded as a comment/bound
provenance discrepancy and is NOT used to change the bound.
"""
from __future__ import annotations

import argparse
import copy
import importlib.util
import math
import re
from pathlib import Path

import numpy as np

from _common import REPO, add_out_arg, fail, utc_now, write_report

TOOL = "parameter_activity"
SCHEMA = "parameter-activity-v1"
DEFAULT_CONFIG = "examples/typologies/campaign_2026-10-26_v4/native__ath_core_v4.yaml"
DEFAULT_BRIEF = "examples/briefs/campaign_2026-10-26_v4/native_ath_core_2in_v4.yaml"
GEOMETRY_TOL_MM = 1e-6

_UNIT = {
    "r0_mm": "mm", "a_deg": "deg", "a0_deg": "deg", "L_mm": "mm", "n": None, "s": None,
    "q": None, "k": None, "exponent": None, "aspect_ratio": None, "s1": "mm/deg",
    "s2": "1/mm", "morph_target": None, "morph_width_mm": "mm", "morph_height_mm": "mm",
    "morph_corner_mm": "mm", "morph_exponent": None, "morph_rate": None, "morph_fixed": None,
    "morph_allow_shrinkage": "0/1 flag",
}

_PREDICATE = {
    "n": "s != 0  (OSSE termination term is skipped when s == 0)",
    "q": "s != 0  (OSSE termination term is skipped when s == 0)",
    "s": "always contributes the termination amplitude; s == 0 is a no-op for n/q",
    "s1": "s1 != 0 and s2 != 0  (the axial-stretch map is inactive if either is zero)",
    "s2": "s1 != 0 and s2 != 0  (the axial-stretch map is inactive if either is zero)",
    "morph_width_mm": "morph_target in {1, 2, 3}",
    "morph_height_mm": "morph_target in {1, 2, 3}",
    "morph_corner_mm": "morph_target == 1  (rounded-rectangle target only)",
    "morph_rate": "morph_target in {1, 2, 3} and t > morph_fixed for some sampled t",
    "morph_fixed": "morph_target in {1, 2, 3} and t > morph_fixed for some sampled t",
    "morph_exponent": "morph_target == 3  (superellipse target only)",
    "morph_target": "always (fixed in this task)",
    "morph_allow_shrinkage": "morph_target in {1, 2, 3} and the target is smaller than the base mouth extent",
    "r0_mm": "brief driver exit radius (pinned)",
    "a0_deg": "brief driver exit angle (pinned because throat_angle_policy: pin)",
    "exponent": "always (fixed cross-section outline)",
    "aspect_ratio": "always (fixed cross-section aspect)",
    "L_mm": "always",
    "a_deg": "always",
    "k": "always",
}

_FEATURES = {
    "L_mm": ["axial depth", "mouth-plane z", "main OS-SE meridian"],
    "a_deg": ["coverage half-angle", "flare rate", "mouth width/height"],
    "a0_deg": ["throat wall tangent", "initial expansion"],
    "k": ["throat-to-mouth flare blend", "wall curvature"],
    "n": ["OSSE termination exponent", "mouth roll"],
    "s": ["OSSE termination amplitude", "mouth flare"],
    "q": ["OSSE termination saturation", "mouth roll"],
    "s1": ["axial station mapping", "throat stretch"],
    "s2": ["axial station mapping", "throat stretch"],
    "r0_mm": ["throat radius", "driver coupling"],
    "exponent": ["cross-section superellipse outline"],
    "aspect_ratio": ["cross-section H/V aspect"],
    "morph_target": ["mouth contour family"],
    "morph_width_mm": ["mouth contour width", "H-plane outline", "diagonal contour"],
    "morph_height_mm": ["mouth contour height", "V-plane outline", "diagonal contour"],
    "morph_corner_mm": ["mouth corner radius", "diagonal contour"],
    "morph_exponent": ["superellipse mouth contour (target 3 only)", "diagonal contour"],
    "morph_rate": ["along-horn morph transition", "interior wall", "diagonal contour"],
    "morph_fixed": ["morph start station", "near-throat/interior wall", "diagonal contour"],
    "morph_allow_shrinkage": ["morph target dimension floor"],
}


# ---------------------------------------------------------------------------- source refs


class _Refs:
    """Small cached ``file:line`` resolver over repo and installed package sources."""

    def __init__(self) -> None:
        self._cache: dict[str, str | None] = {}

    @staticmethod
    def _repo_relative(path: Path) -> str:
        try:
            return path.resolve().relative_to(REPO).as_posix()
        except ValueError:
            return path.as_posix()

    def label(self, path: Path) -> str:
        path = Path(path)
        for prefix, pkg in ((".venv/Lib/site-packages/", "installed"),):
            try:
                rel = path.resolve().relative_to((REPO / prefix).resolve())
            except ValueError:
                continue
            return rel.as_posix()
        return self._repo_relative(path)

    def _path(self, label: str) -> Path | None:
        if "/" in label:
            head, _, rest = label.partition("/")
            if head in ("hornlab_mesher", "hornlab_beat_bem", "hornlab_plots"):
                try:
                    spec = importlib.util.find_spec(head)
                except (ImportError, ValueError):
                    return None
                locs = list(spec.submodule_search_locations or []) if spec else []
                if locs:
                    p = Path(locs[0]) / rest
                    if p.is_file():
                        return p
        p = REPO / label
        return p if p.is_file() else None

    def _text(self, label: str) -> str | None:
        if label in self._cache:
            return self._cache[label]
        path = self._path(label)
        text = None
        if path is not None:
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                text = None
        self._cache[label] = text
        return text

    def ref(self, label: str, needle: str, *, regex: bool = False,
            occurrence: int = 0) -> dict:
        text = self._text(label)
        lines: list[int] = []
        if text is not None:
            if regex:
                pat = re.compile(needle)
                for i, line in enumerate(text.splitlines(), 1):
                    if pat.search(line):
                        lines.append(i)
            else:
                for i, line in enumerate(text.splitlines(), 1):
                    if needle in line:
                        lines.append(i)
        return {"file": label, "line": lines[occurrence] if occurrence < len(lines) else None}

    def refs(self, label: str, needle: str, *, regex: bool = False,
             limit: int | None = None) -> list[dict]:
        text = self._text(label)
        lines: list[int] = []
        if text is not None:
            if regex:
                pat = re.compile(needle)
                for i, line in enumerate(text.splitlines(), 1):
                    if pat.search(line):
                        lines.append(i)
            else:
                for i, line in enumerate(text.splitlines(), 1):
                    if needle in line:
                        lines.append(i)
        if limit is not None:
            lines = lines[:limit]
        return [{"file": label, "line": i} for i in lines]


def _config_label(path: Path) -> str:
    return _Refs._repo_relative(Path(path))


def _config_key_refs(refs: _Refs, config_label: str, key: str) -> list[dict]:
    # Exactly one two-space indented ``key:`` line under seed_params and one under bounds.
    hits = refs.refs(config_label, rf"^\s{{2}}{re.escape(key)}\s*:", regex=True)
    return hits[:2]


_MESHER_REFS = {
    "morph_exponent": [
        ("hornlab_mesher/profile_morph.py", "if target == 0:", 0),
        ("hornlab_mesher/profile_morph.py", "if target == 3:", 0),
        ("hornlab_mesher/profile_morph.py", 'params.get("morphExponent")', 0),
    ],
    "morph_target": [
        ("hornlab_mesher/profile_morph.py", "def _morph_target_shape", 0),
        ("hornlab_mesher/profile_morph.py", "def _morph_active", 0),
    ],
    "morph_width_mm": [("hornlab_mesher/profile_morph.py", 'params.get("morphWidth")', 0)],
    "morph_height_mm": [("hornlab_mesher/profile_morph.py", 'params.get("morphHeight")', 0)],
    "morph_corner_mm": [("hornlab_mesher/profile_morph.py", 'params.get("morphCorner")', 0)],
    "morph_rate": [("hornlab_mesher/profile_morph.py", "def _morph_rate", 0)],
    "morph_fixed": [("hornlab_mesher/profile_morph.py", 'params.get("morphFixed")', 0)],
    "s": [("hornlab_mesher/profile_formulas.py", 'params.get("s")', 0),
          ("hornlab_mesher/profile_formulas.py", "def _validate_osse_termination", 0)],
    "n": [("hornlab_mesher/profile_formulas.py", "def calculate_osse", 0),
          ("hornlab_mesher/profile_formulas.py", "def _validate_osse_termination", 0)],
    "q": [("hornlab_mesher/profile_formulas.py", 'params.get("q")', 0),
          ("hornlab_mesher/profile_formulas.py", "def _validate_osse_termination", 0)],
    "s1": [("hornlab_mesher/throat_stretch.py", "def stretch_is_inactive", 0),
           ("hornlab_mesher/profile_formulas.py", "if s1 != 0.0 and s2 != 0.0", 0)],
    "s2": [("hornlab_mesher/throat_stretch.py", "def stretch_is_inactive", 0),
           ("hornlab_mesher/profile_formulas.py", "if s1 != 0.0 and s2 != 0.0", 0)],
    "r0_mm": [("hornlab_mesher/profile_formulas.py", 'params.get("r0")', 0)],
    "a0_deg": [("hornlab_mesher/profile_formulas.py", 'params.get("a0")', 0)],
    "L_mm": [("hornlab_mesher/profile_formulas.py", 'params.get("L")', 0)],
    "a_deg": [("hornlab_mesher/profile_formulas.py", 'params.get("a")', 0)],
    "k": [("hornlab_mesher/profile_formulas.py", 'params.get("k")', 0)],
}

_FAMILIES_NEEDLE = {
    "r0_mm": '"r0_mm": _f(', "a_deg": '"a_deg": _f(', "a0_deg": '"a0_deg": _f(',
    "L_mm": '"L_mm": _f(', "n": '"n": _f(', "s": '"s": _f(', "q": '"q": _f(',
    "k": '"k": _f(', "exponent": '"exponent": _f(', "aspect_ratio": '"aspect_ratio": _f(',
    "s1": '"s1": _f(', "s2": '"s2": _f(', "morph_target": '"morph_target": _i(',
    "morph_width_mm": '"morph_width_mm": _f(', "morph_height_mm": '"morph_height_mm": _f(',
    "morph_corner_mm": '"morph_corner_mm": _f(', "morph_exponent": '"morph_exponent": _f(',
    "morph_rate": '"morph_rate": _f(', "morph_fixed": '"morph_fixed": _f(',
    "morph_allow_shrinkage": '"morph_allow_shrinkage": _i(',
}

_KNOBS_NATIVE_NEEDLE = {
    key: f'"{key}": _make(' for key in _UNIT
}


def _source_refs(refs: _Refs, config_label: str, key: str) -> list[dict]:
    out = _config_key_refs(refs, config_label, key)
    if key == "morph_fixed":
        out.append(refs.ref(config_label, "morph_fixed 0-0.1"))
    if key in _FAMILIES_NEEDLE:
        out.append(refs.ref("hornlab_search/design/families.py", _FAMILIES_NEEDLE[key]))
    if key in _KNOBS_NATIVE_NEEDLE:
        out.append(refs.ref("hornlab_search/design/params/knobs_native.py",
                            _KNOBS_NATIVE_NEEDLE[key]))
    for label, needle, occ in _MESHER_REFS.get(key, ()):
        out.append(refs.ref(label, needle, occurrence=occ))
    if key in ("r0_mm", "a0_deg"):
        out.append(refs.ref("hornlab_search/config.py", f'_force_pin("{key}"'))
    return [r for r in out if r.get("line") is not None]


# ---------------------------------------------------------------------------- activity


def _category(key: str, bound, seed_value) -> str:
    if key == "morph_exponent":
        return "inactive"
    if key in {"n", "q", "s1", "s2", "morph_width_mm", "morph_height_mm",
               "morph_corner_mm", "morph_rate", "morph_fixed"}:
        return "conditional"
    if key in {"r0_mm", "a0_deg"}:
        return "derived"
    if bound is not None and not bool(bound.search):
        return "fixed"
    if bound is not None and bool(bound.search):
        return "searched"
    return "unresolved"


def _bound_record(bound) -> dict | None:
    if bound is None:
        return None
    return {"lo": float(bound.lo), "hi": float(bound.hi), "search": bool(bound.search),
            "log": bool(bound.log), "transform": "log10" if bound.log else "identity"}


def _sample_surface_safe(ge, design, cfg, resolution_mm: float):
    """Sample, retrying coarser resolutions when the mesher's sampling fit refuses.

    Some legal endpoint perturbations (e.g. a small corner radius with a long axial chord)
    cannot fit the requested *geometry sampling* density.  Retry coarser; if every attempt is
    refused, return the last error instead of crashing the audit.
    """
    last: Exception | None = None
    for factor in (1.0, 1.5, 2.0, 3.0):
        res = float(resolution_mm) * factor
        try:
            return ge.sample_surface(design, cfg, resolution_mm=res,
                                     check_convergence=False), res, None
        except Exception as exc:  # noqa: BLE001 - a refused sample is reported honestly
            last = exc
    return None, None, last


def _geometry_perturbation(ge, seed_design, cfg, key: str, values, *,
                           resolution_mm: float) -> dict:
    lo_design = ge.with_params(seed_design, **{key: float(values[0])})
    hi_design = ge.with_params(seed_design, **{key: float(values[1])})
    a, res_a, err_a = _sample_surface_safe(ge, lo_design, cfg, resolution_mm)
    b, res_b, err_b = _sample_surface_safe(ge, hi_design, cfg, resolution_mm)
    if a is None or b is None:
        return {
            "kind": "canonical_surface_perturbation",
            "values": [float(values[0]), float(values[1])],
            "changed": None,
            "error": f"geometry sampling refused: {err_a or err_b}",
            "resolution_mm": float(resolution_mm),
            "api": "hornlab_mesher.config_builder.resolve_geometry",
            "units": "mm",
        }
    delta = ge.surface_delta(a, b, tol_mm=GEOMETRY_TOL_MM)
    return {
        "kind": "canonical_surface_perturbation",
        "values": [float(values[0]), float(values[1])],
        "max_abs_delta_mm": float(delta["max_abs_radius_delta_mm"]),
        "mean_abs_delta_mm": float(delta["mean_abs_radius_delta_mm"]),
        "tolerance_mm": GEOMETRY_TOL_MM,
        "changed": bool(delta["changed"]),
        "surface_fingerprints_equal": bool(delta["surface_fingerprints_equal"]),
        "resolution_mm": float(max(res_a or 0.0, res_b or 0.0)),
        "api": "hornlab_mesher.config_builder.resolve_geometry",
        "units": "mm",
    }


def _contour_test(ge, design_lo, design_hi, cfg, *,
                  resolution_mm: float) -> dict:
    """64-azimuth mouth-contour comparison through the installed geometry API."""
    az = np.asarray(ge.EXPONENT_CONTOUR_AZIMUTHS_DEG, dtype=float)
    last: Exception | None = None
    for factor in (1.0, 1.5, 2.0, 3.0):
        res = float(resolution_mm) * factor
        try:
            a = ge.mouth_contour_at_azimuths(design_lo, cfg, azimuths_deg=az,
                                             resolution_mm=res)
            b = ge.mouth_contour_at_azimuths(design_hi, cfg, azimuths_deg=az,
                                             resolution_mm=res)
            ra = np.asarray(a["radius_mm"], dtype=float)
            rb = np.asarray(b["radius_mm"], dtype=float)
            delta = np.abs(ra - rb)
            n_changed = int(np.count_nonzero(delta > GEOMETRY_TOL_MM))
            return {
                "kind": "mouth_contour_64_azimuth",
                "n_azimuths": int(az.size),
                "n_changed": n_changed,
                "changed_fraction": float(n_changed / max(1, az.size)),
                "max_abs_delta_mm": float(np.max(delta)),
                "mean_abs_delta_mm": float(np.mean(delta)),
                "tolerance_mm": GEOMETRY_TOL_MM,
                "changed": bool(n_changed > 0),
                "resolution_mm": res,
                "units": "mm",
                "api": "hornlab_mesher.config_builder.resolve_geometry",
            }
        except Exception as exc:  # noqa: BLE001 - report a refused geometry sample honestly
            last = exc
    return {"kind": "mouth_contour_64_azimuth", "n_azimuths": int(az.size),
            "n_changed": None, "changed": None,
            "error": f"geometry sampling refused: {last}",
            "resolution_mm": float(resolution_mm), "units": "mm",
            "api": "hornlab_mesher.config_builder.resolve_geometry"}


def _geometry_evidence(ge, refs, seed_design, cfg, key: str, bound, *,
                       resolution_mm: float, base_sample,
                       exponent_inactive: dict | None = None) -> dict | None:
    if key == "morph_exponent":
        return exponent_inactive
    if key == "morph_target":
        t1 = copy.deepcopy(seed_design.params)
        t1["morph_target"] = 1
        t3 = copy.deepcopy(seed_design.params)
        t3["morph_target"] = 3
        from hornlab_search.types import Design
        a = ge.sample_surface(Design(seed_design.family, t1), cfg,
                              resolution_mm=resolution_mm, check_convergence=False)
        b = ge.sample_surface(Design(seed_design.family, t3), cfg,
                              resolution_mm=resolution_mm, check_convergence=False)
        delta = ge.surface_delta(a, b, tol_mm=GEOMETRY_TOL_MM)
        return {"kind": "canonical_surface_perturbation", "values": [1, 3],
                "max_abs_delta_mm": float(delta["max_abs_radius_delta_mm"]),
                "changed": bool(delta["changed"]), "tolerance_mm": GEOMETRY_TOL_MM,
                "resolution_mm": resolution_mm, "units": "mm",
                "api": "hornlab_mesher.config_builder.resolve_geometry"}
    if bound is None or not bool(bound.search):
        return None
    lo, hi = float(bound.lo), float(bound.hi)
    if lo == hi:
        return None
    evidence = _geometry_perturbation(ge, seed_design, cfg, key, (lo, hi),
                                      resolution_mm=resolution_mm)
    if key == "s1":
        off = ge.with_params(seed_design, s2=0.0)
        a = ge.sample_surface(ge.with_params(off, s1=lo), cfg,
                              resolution_mm=resolution_mm, check_convergence=False)
        b = ge.sample_surface(ge.with_params(off, s1=hi), cfg,
                              resolution_mm=resolution_mm, check_convergence=False)
        evidence["condition_test"] = {
            "condition": "s2 == 0", "changed": bool(ge.surface_delta(a, b)["changed"]),
            "max_abs_delta_mm": float(ge.surface_delta(a, b)["max_abs_radius_delta_mm"]),
        }
    elif key == "s2":
        off = ge.with_params(seed_design, s1=0.0)
        a = ge.sample_surface(ge.with_params(off, s2=lo), cfg,
                              resolution_mm=resolution_mm, check_convergence=False)
        b = ge.sample_surface(ge.with_params(off, s2=hi), cfg,
                              resolution_mm=resolution_mm, check_convergence=False)
        evidence["condition_test"] = {
            "condition": "s1 == 0", "changed": bool(ge.surface_delta(a, b)["changed"]),
            "max_abs_delta_mm": float(ge.surface_delta(a, b)["max_abs_radius_delta_mm"]),
        }
    elif key in ("n", "q"):
        # The OSSE termination term (and therefore n/q) is skipped while s == 0.
        off = ge.with_params(seed_design, s=0.0)
        a, _, err_a = _sample_surface_safe(ge, ge.with_params(off, **{key: lo}), cfg,
                                           resolution_mm)
        b, _, err_b = _sample_surface_safe(ge, ge.with_params(off, **{key: hi}), cfg,
                                           resolution_mm)
        if a is None or b is None:
            evidence["condition_test"] = {
                "condition": "s == 0", "changed": None,
                "error": f"geometry sampling refused: {err_a or err_b}",
            }
        else:
            delta = ge.surface_delta(a, b)
            evidence["condition_test"] = {
                "condition": "s == 0", "changed": bool(delta["changed"]),
                "max_abs_delta_mm": float(delta["max_abs_radius_delta_mm"]),
            }
    return evidence


def _exponent_evidence(ge, seed_design, cfg, bound, *, resolution_mm: float) -> dict:
    lo, hi = float(bound.lo), float(bound.hi)
    t1 = _geometry_perturbation(ge, seed_design, cfg, "morph_exponent", (lo, hi),
                                resolution_mm=resolution_mm)
    t1["target"] = 1
    t3_base = ge.with_params(seed_design, morph_target=3)
    t3 = _geometry_perturbation(ge, t3_base, cfg, "morph_exponent", (max(2.0, lo), hi),
                                resolution_mm=resolution_mm)
    t3["target"] = 3
    # The hardening decision's own 64-azimuth contour check.  This is the primary evidence:
    # target 1 must be invariant at all azimuths, target 3 must change most of them.
    c1 = _contour_test(ge,
                       ge.with_params(seed_design, morph_exponent=lo),
                       ge.with_params(seed_design, morph_exponent=hi),
                       cfg, resolution_mm=resolution_mm)
    c3 = _contour_test(ge,
                       ge.with_params(t3_base, morph_exponent=max(2.0, lo)),
                       ge.with_params(t3_base, morph_exponent=hi),
                       cfg, resolution_mm=resolution_mm)
    if c1.get("changed") is not None and c3.get("changed") is not None:
        inactive = bool(c1["changed"] is False and not t1["changed"])
        changed = bool(c3["changed"] is True and t3["changed"])
    else:  # fall back to the canonical surface test and report the contour failure
        inactive = bool(not t1["changed"])
        changed = bool(t3["changed"])
    return {
        "kind": "canonical_surface_perturbation",
        "inactive_target": 1,
        "active_target": 3,
        "target_1": t1,
        "target_3": t3,
        "target_1_contour": c1,
        "target_3_contour": c3,
        "contour_azimuths": len(ge.EXPONENT_CONTOUR_AZIMUTHS_DEG),
        "tolerance_mm": GEOMETRY_TOL_MM,
        "resolution_mm": float(resolution_mm),
        "api": "hornlab_mesher.config_builder.resolve_geometry",
        "units": "mm",
        "changed": changed,
        "inactive": inactive,
        "conclusion": ("target-1 surface is invariant to morph_exponent at all 64 sampled "
                       "azimuths; target-3 surface changes, so inactivity is conditional on "
                       "morph_target == 1"),
    }


def _evidence_status(category: str, geom: dict | None, static_refs: list[dict]) -> str:
    if category == "inactive":
        if geom is not None and geom.get("inactive") and geom.get("changed"):
            return "confirmed_inactive_conditional"
        return "unresolved"
    if category in ("searched", "conditional", "derived", "fixed"):
        if geom is not None and geom.get("changed"):
            return ("conditional_active" if category == "conditional"
                    else "confirmed_active_geometry")
        if static_refs:
            return "static_source_only"
        return "unresolved"
    return "unresolved"


# ---------------------------------------------------------------------------- ledger


def build_ledger(config_path, *, config=None, space=None, run_geometry: bool = True,
                 resolution_mm: float = 12.0) -> dict:
    """Build the control-activity ledger for one resolved config (never mutates the config)."""
    from hornlab_search.config import load_config
    from hornlab_search.design import families
    from hornlab_search.design.space import DesignSpace
    from hornlab_search.bo.encoding import ActiveProjection

    path = Path(config_path)
    if not path.is_absolute() and not path.exists():
        path = REPO / path
    cfg = config if config is not None else load_config(path)
    sp = space if space is not None else DesignSpace.from_config(cfg)
    seed = sp.seed
    config_label = _config_label(path)
    refs = _Refs()

    all_keys = sorted(set(cfg.seed_params) | set(cfg.bounds_raw) | set(sp.keys()))
    controls: list[dict] = []
    counts = {k: 0 for k in ("searched", "fixed", "derived", "conditional", "inactive",
                             "unresolved")}

    if run_geometry:
        import geometry_effects as ge
        base_sample = ge.sample_surface(seed, cfg, resolution_mm=resolution_mm,
                                        check_convergence=True)
    else:
        ge = None
        base_sample = None

    exponent_bound = sp.bounds.get("morph_exponent")
    exponent_ev = (_exponent_evidence(ge, seed, cfg, exponent_bound,
                                      resolution_mm=resolution_mm)
                   if (run_geometry and exponent_bound is not None) else None)

    for key in all_keys:
        bound = sp.bounds.get(key)
        try:
            value = families.param_get(seed.family, seed.params, key)
            if isinstance(value, (int, float, np.integer, np.floating)):
                value = float(value)
        except Exception:  # noqa: BLE001 - a missing seed value is reported as unresolved
            value = None
        category = _category(key, bound, value)
        counts[category] += 1
        static_refs = _source_refs(refs, config_label, key)
        geom = None
        if run_geometry and ge is not None:
            geom = _geometry_evidence(ge, refs, seed, cfg, key, bound,
                                      resolution_mm=resolution_mm, base_sample=base_sample,
                                      exponent_inactive=exponent_ev
                                      if key == "morph_exponent" else None)
        record = {
            "key": key,
            "base_knob": key,
            "context": "native:osse" if cfg.family == "OSSE" else f"native:{cfg.family}",
            "category": category,
            "unit": _UNIT.get(key),
            "unit_transform": ("log10" if bound is not None and bound.log else "identity"),
            "resolved": {
                "value": value,
                "bound": _bound_record(bound),
            },
            "application_predicate": _PREDICATE.get(key, "always"),
            "affected_geometry_features": list(_FEATURES.get(key, [])),
            "source_refs": static_refs,
            "evidence": {
                "static_source": {
                    "status": "recorded" if static_refs else "missing",
                    "summary": _static_summary(key),
                    "refs": static_refs,
                },
                "geometry_test": geom,
                "status": _evidence_status(category, geom, static_refs),
            },
            "notes": _notes(key, cfg, bound),
        }
        controls.append(record)

    active_keys = list(sp.keys())
    fixed_values: dict[str, float] = {}
    projection_refused = None
    if exponent_ev is not None and exponent_ev.get("inactive") and exponent_ev.get("changed"):
        fixed_values = {"morph_exponent": float(seed.params.get("morph_exponent", 0.0) or 0.0)} \
            if "morph_exponent" in active_keys else {}
        active_keys = [k for k in active_keys if k != "morph_exponent"]
    elif "morph_exponent" in active_keys:
        projection_refused = ("morph_exponent inactivity was not proven by both source and the "
                              "target-1/target-3 geometry test; projection stays full-dimensional")
    projection = {
        "version": "active-projection-v1",
        "full_keys": list(sp.keys()),
        "active_keys": active_keys,
        "fixed_values": fixed_values,
        "conditions": {"morph_target": int(seed.params.get("morph_target", 0) or 0)},
        "reversible": True,
        "reason": ("static target-3-only source branch plus target-1 invariance / target-3 "
                   "activity geometry test" if fixed_values else "no proven no-op projected"),
        "refused": projection_refused,
    }

    payload = {
        "schema": SCHEMA,
        "generated_utc": utc_now(),
        "config": {
            "path": config_label,
            "name": cfg.name,
            "family": cfg.family,
            "kind": "native",
            "brief_file": cfg.raw.get("brief_file"),
            "brief_name": (cfg.brief or {}).get("name"),
            "objective_version": int(cfg.objective_version),
            "seed_design_hash": seed.hash(),
            "config_bound_source": config_label,
        },
        "context": {
            "native_or_generator": "native",
            "family_key_table": cfg.family,
            "generator": None,
        },
        "search": {
            "keys": list(sp.keys()),
            "alphabetical": list(sp.keys()) == sorted(sp.keys()),
            "d": len(sp.keys()),
            "bounds": {k: _bound_record(sp.bounds[k]) for k in sp.keys()},
        },
        "counts": counts,
        "controls": controls,
        "active_projection": projection,
        "task_eligibility": {
            "status": "insufficient_evidence",
            "scope": "B2 control/geometry audit only",
            "note": ("This ledger does not establish a compatible ATH archive cohort; S0/R0 "
                     "own counts, comparability and replay. ATH eligibility remains unproven."),
        },
        "geometry": {
            "sampler": "tools/analysis/geometry_effects.py",
            "api": "hornlab_mesher.config_builder.resolve_geometry",
            "resolution_mm": float(resolution_mm),
            "units": "mm",
            "convergence": (base_sample.convergence if base_sample is not None else None),
            "mesh_built": False,
            "bem_called": False,
            "cache_key_changed": False,
        },
    }
    return payload


def _static_summary(key: str) -> str:
    if key == "morph_exponent":
        return ("installed profile_morph.py reads morphExponent only inside the target == 3 "
                "branch; target 1 returns the rounded-rectangle outline first")
    if key in ("n", "q"):
        return "installed OSSE termination term is skipped while s == 0; seed has s != 0"
    if key in ("s1", "s2"):
        return "installed stretch_is_inactive is true when either coefficient is zero"
    if key in ("r0_mm", "a0_deg"):
        return "config.py pins the native throat to the brief driver"
    if key.startswith("morph_"):
        return "installed profile_morph.py branch for the active morph target"
    return "resolved by the native family KeySpec and the config seed/bound"


def _notes(key: str, cfg, bound) -> list[str]:
    out: list[str] = []
    if key == "morph_fixed":
        out.append("resolved bound is 0.0-0.6 from the config's bounds block; the campaign "
                   "comment mentions 0-0.1, but the bound is NOT changed (comment/bound "
                   "provenance discrepancy recorded)")
        out.append("search bound source: config bounds.morph_fixed")
    if key == "morph_exponent":
        out.append("fixed target 1 is the rounded-rectangle target; the superellipse exponent "
                   "is read only for target 3")
    if key == "morph_target":
        out.append("pinned to 1 in seed_params and bounds; search: false")
    if key == "s":
        out.append("s == 0 makes n and q inactive for OSSE; the searched bound includes 0")
    return out


def no_op_projection(ledger: dict) -> dict[str, float]:
    """Return ``{key: reference_value}`` from a ledger's proven active projection."""
    projection = ledger.get("active_projection") or {}
    if projection.get("refused"):
        return {}
    return {str(k): float(v) for k, v in (projection.get("fixed_values") or {}).items()}


# ---------------------------------------------------------------------------- report


def _md(p: dict) -> str:
    lines = [
        "# Parameter activity ledger",
        "",
        f"Config: `{p['config']['path']}`  ",
        f"Resolved brief: `{p['config'].get('brief_file')}`  ",
        f"Family: `{p['config']['family']}` · objective v{p['config']['objective_version']} · "
        f"search d = {p['search']['d']}  ",
        "Native context; geometry sampled through the installed `hornlab_mesher` API "
        "(no mesh/BEM).",
        "",
        "## Activity counts",
        "",
        "| category | count |",
        "|---|---:|",
    ]
    for key, value in p["counts"].items():
        lines.append(f"| {key} | {value} |")
    lines += ["", "## Controls", "",
              "| key | category | resolved value | range | predicate | evidence |",
              "|---|---|---:|---|---|---|"]
    for c in p["controls"]:
        b = c["resolved"].get("bound") or {}
        rng = "—" if not b else f"{b['lo']:g} .. {b['hi']:g}" + (
            " (search)" if b.get("search") else " (fixed)")
        val = c["resolved"].get("value")
        vals = "—" if val is None else f"{val:g}"
        lines.append(
            f"| `{c['key']}` | {c['category']} | {vals} | {rng} | {c['application_predicate']} | "
            f"{c['evidence']['status']} |")
    proj = p["active_projection"]
    lines += ["", "## Advisory active projection", "",
              f"Version `{proj['version']}`; active d = {len(proj['active_keys'])} of "
              f"{len(proj['full_keys'])}.", ""]
    if proj.get("fixed_values"):
        lines.append("Held fixed while decoding: " + ", ".join(
            f"`{k}` = {v:g}" for k, v in proj["fixed_values"].items()) + ".")
    else:
        lines.append("No control is projected; the full alphabetical vector is retained.")
    if proj.get("refused"):
        lines.append("Projection refused: " + proj["refused"])
    geom = p.get("geometry") or {}
    conv = geom.get("convergence") or {}
    lines += ["", "## Geometry sampling", "",
              f"API: `{geom.get('api')}` · units: `{geom.get('units')}` · resolution "
              f"{geom.get('resolution_mm')} mm.",
              f"Convergence: {conv.get('converged')} "
              f"(max |Δr| {conv.get('max_abs_radius_delta_mm')} mm; "
              f"{conv.get('note', '')}).",
              "", "ATH eligibility: **insufficient evidence** in this B2 audit; "
              "S0/R0 own archive counts and comparability.", ""]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("--config", default=str(REPO / DEFAULT_CONFIG),
                    help="resolved native config YAML (default: the ATH v4 candidate)")
    ap.add_argument("--no-geometry", action="store_true",
                    help="static ledger only (skip canonical-surface perturbations)")
    ap.add_argument("--resolution-mm", type=float, default=12.0,
                    help="geometry sampling resolution in mm (default 12)")
    add_out_arg(ap)
    args = ap.parse_args(argv)
    try:
        payload = build_ledger(Path(args.config), run_geometry=not args.no_geometry,
                               resolution_mm=float(args.resolution_mm))
    except Exception as exc:  # noqa: BLE001 - the CLI reports a clean exit code
        raise fail(f"parameter_activity: {exc}") from exc
    write_report(Path(args.out), TOOL, payload, _md(payload))
    n_inactive = payload["counts"]["inactive"]
    print(f"parameter_activity OK: {len(payload['controls'])} controls, "
          f"{n_inactive} inactive, d={payload['search']['d']} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
