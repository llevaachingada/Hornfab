"""Klangfilm-Lame H/V Phase A geometry preflight (CPU only; no meshing, no BEM, no GPU).

Loads the ``a0``..``a5`` geometry-diagnostic YAML configs under
``examples/typologies/klangfilm_hv_2026-11-16/configs``, builds each kernel shape dict from
``seed_params`` (``g_`` prefix stripped), resolves the brief relative to the config, and calls the
Phase A kernel ``tools/geometry/klangfilm_lame_hv.py`` **directly** (never the package adapter).

Every number below is computed from the kernel or from cached run data. Nothing is asserted about
acoustic quality: this file reports sampled inner-surface geometry, a conservative sampled envelope
estimate, and a DIAGNOSTIC directivity summary of one already-solved design.

CD diagnostic policy (explicit; see ``J_CD_cached``):
  F_CD  = cached ``freqs_hz`` in the inclusive band [1200, 5600] Hz
  e_H   = (BW_H - 80) / 8        (deg, 8 deg tolerance)
  e_V   = (BW_V - 50) / 8        (deg, 8 deg tolerance)
  tau   = 8 deg                  (reference tolerance; recorded, not an extra term)
  J     = mean(e_H^2) + mean(e_V^2) + Var(DI)      (population variance, ddof = 0)
This is a DIAGNOSTIC, NOT the v7 objective. The cached run used ``di_slope_target = +5 dB/dec`` with
NO DI weight, so J_CD_cached must not be compared across objectives or treated as a score.

Outputs:
  docs/evidence/klangfilm_hv_2026-11-16/preflight.json   (machine, sorted keys)
  docs/evidence/klangfilm_hv_2026-11-16/PREFLIGHT.md     (human table)

Run: ``.venv\\Scripts\\python.exe tools/geometry/klangfilm_hv_preflight.py``
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.geometry import klangfilm_lame_hv as K  # noqa: E402
from tools.geometry import klangfilm_lame as PARENT  # noqa: E402

CONFIG_DIR = ROOT / "examples/typologies/klangfilm_hv_2026-11-16/configs"
EVIDENCE_DIR = ROOT / "docs/evidence/klangfilm_hv_2026-11-16"
CACHED_METRICS = ROOT / "runs/20261116T205942Z-screen-8b22b5/designs/786caa6b08d7/metrics.json"
ENVELOPE_MM = {"width": 600.0, "height": 480.0, "depth": 480.0}
SEED_ORDER = ("a0", "a1", "a2", "a3", "a3b", "a4", "a4b", "a5")

# ------------------------------------------------------------------ CD diagnostic policy (explicit)
CD_POLICY = {
    "name": "J_CD_cached",
    "kind": "DIAGNOSTIC (NOT the v7 objective)",
    "band_hz": [1200.0, 5600.0],
    "band_inclusive": True,
    "target_h_deg": 80.0,
    "target_v_deg": 50.0,
    "tolerance_deg": 8.0,
    "tau_deg": 8.0,
    "e_h": "(BW_H_deg - 80) / 8",
    "e_v": "(BW_V_deg - 50) / 8",
    "J": "mean(e_h^2) + mean(e_v^2) + Var(DI)",
    "variance": "population variance (ddof=0) over the selected bands",
    "objective_note": ("cached run config used di_slope_target = +5 dB/dec with no DI weight; "
                       "J values are NOT comparable across objectives and are not a score"),
    "source": "runs/20261116T205942Z-screen-8b22b5/designs/786caa6b08d7/metrics.json",
}


# ------------------------------------------------------------------ helpers
def _clean(obj):
    """Recursively convert numpy scalars/arrays to JSON-native values."""
    if isinstance(obj, dict):
        return {str(k): _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return [_clean(v) for v in obj.tolist()]
    if isinstance(obj, (np.floating, np.integer)):
        return float(obj) if isinstance(obj, np.floating) else int(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    return obj


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha_file(path: Path) -> str:
    return _sha_bytes(path.read_bytes())


def _grid_sha(pts: np.ndarray) -> str:
    return _sha_bytes(np.ascontiguousarray(pts, dtype="<f8").tobytes())


def load_configs():
    """Return ``[(seed_id, config_path, config_dict), ...]`` in SEED_ORDER."""
    out = []
    for sid in SEED_ORDER:
        path = CONFIG_DIR / f"{sid}.yaml"
        if not path.exists():
            raise FileNotFoundError(f"missing config {path}")
        cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
        out.append((sid, path, cfg))
    return out


def shape_from_config(cfg: dict) -> dict:
    shape = {key[2:]: value for key, value in cfg["seed_params"].items()}
    for key in ("n_phi", "n_s", "wall_thickness_mm"):
        shape[key] = cfg["generator"][key]
    return shape


def _forward_axes(shape: dict, brief: dict):
    """Return ``(z, a, b)`` on the monotonic forward branch (dense parent stations)."""
    tab = K.profile(shape, float(brief["driver"]["exit_radius_mm"]))
    turn = K.forward_slice(tab)
    return (np.asarray(tab["z"][: turn + 1], dtype=float),
            np.asarray(tab["a"][: turn + 1], dtype=float),
            np.asarray(tab["b"][: turn + 1], dtype=float))


def _envelope_from_points(pts: np.ndarray, wall_thickness_mm: float) -> dict:
    """Conservative sampled outer envelope: inner sampled bounds + wall thickness (not a mesh cert)."""
    inner_w = float(2.0 * np.abs(pts[:, :, 0]).max())
    inner_h = float(2.0 * np.abs(pts[:, :, 1]).max())
    inner_d = float(np.ptp(pts[:, :, 2]))
    outer = {"width": inner_w + 2.0 * wall_thickness_mm,
             "height": inner_h + 2.0 * wall_thickness_mm,
             "depth": inner_d + wall_thickness_mm}
    return {
        "method": "sampled_conservative_estimate",
        "inner_sampled_mm": {"width": inner_w, "height": inner_h, "depth": inner_d},
        "outer_estimate_mm": outer,
        "limits_mm": dict(ENVELOPE_MM),
        "exceeded": [k for k in ("width", "height", "depth") if outer[k] > ENVELOPE_MM[k]],
        "within": all(outer[k] <= ENVELOPE_MM[k] for k in ("width", "height", "depth")),
        "note": "inner sampled quarter-grid reflected on symmetry planes + wall thickness; not a mesh certificate",
    }


def _convergence(shape: dict, brief: dict, base_diag: dict) -> dict:
    """Rebuild at n_phi=37 and n_s=128; report numeric deltas and the mesh-chord trend (no hard bound)."""
    def nums(diag):
        return {
            "max_width_mm": diag["max_width_mm"],
            "max_height_mm": diag["max_height_mm"],
            "throat_radius_spread_mm": diag["throat_radius_spread_mm"],
            "mesh_halfangle_h_deg": diag["mesh_halfangle_h_deg"],
            "mesh_halfangle_v_deg": diag["mesh_halfangle_v_deg"],
            "theta_model_h_deg": diag["theta_model_h_deg"],
            "theta_model_v_deg": diag["theta_model_v_deg"],
        }

    base = nums(base_diag)
    out = {"base_n_phi": int(shape["n_phi"]), "base_n_s": int(shape["n_s"]), "base": base}
    for label, key, value in (("n_phi_37", "n_phi", 37), ("n_s_128", "n_s", 128)):
        variant = dict(shape)
        variant[key] = value
        diag = K.diagnostics(variant, brief)
        got = nums(diag)
        out[label] = got
        out[f"delta_{label}_vs_base"] = {
            "max_width_mm": got["max_width_mm"] - base["max_width_mm"],
            "max_height_mm": got["max_height_mm"] - base["max_height_mm"],
            "throat_radius_spread_mm": got["throat_radius_spread_mm"] - base["throat_radius_spread_mm"],
            "mesh_minus_model_h_deg": got["mesh_halfangle_h_deg"] - got["theta_model_h_deg"],
            "mesh_minus_model_v_deg": got["mesh_halfangle_v_deg"] - got["theta_model_v_deg"],
        }
    base_abs_h = abs(base["mesh_halfangle_h_deg"] - base["theta_model_h_deg"])
    base_abs_v = abs(base["mesh_halfangle_v_deg"] - base["theta_model_v_deg"])
    fine = out["n_s_128"]
    fine_abs_h = abs(fine["mesh_halfangle_h_deg"] - fine["theta_model_h_deg"])
    fine_abs_v = abs(fine["mesh_halfangle_v_deg"] - fine["theta_model_v_deg"])
    out["mesh_chord_abs_error_deg"] = {"n_s_64_h": base_abs_h, "n_s_128_h": fine_abs_h,
                                       "n_s_64_v": base_abs_v, "n_s_128_v": fine_abs_v}
    out["trend_toward_model_h"] = bool(fine_abs_h < base_abs_h)
    out["trend_toward_model_v"] = bool(fine_abs_v < base_abs_v)
    out["trend"] = ("mesh H chord moves toward the model angle with n_s 64 -> 128"
                    if fine_abs_h < base_abs_h else
                    "mesh H chord does not move toward the model angle with n_s 64 -> 128")
    out["trend_v"] = ("mesh V chord moves toward the model angle with n_s 64 -> 128"
                      if fine_abs_v < base_abs_v else
                      "mesh V chord does not move toward the model angle with n_s 64 -> 128")
    return out


def j_cd_cached() -> dict:
    """Named CD diagnostic from CACHED metrics only (no solve). See CD_POLICY."""
    metrics = json.loads(CACHED_METRICS.read_text(encoding="utf-8"))
    freqs = np.asarray(metrics["freqs_hz"], dtype=float)
    bw_h = np.asarray(metrics["bw_h_deg"], dtype=float)
    bw_v = np.asarray(metrics["bw_v_deg"], dtype=float)
    di = np.asarray(metrics["di_db"], dtype=float)
    lo, hi = CD_POLICY["band_hz"]
    mask = (freqs >= lo) & (freqs <= hi)
    if not mask.any():
        raise ValueError("cached metrics have no bands inside the CD diagnostic band")
    e_h = (bw_h[mask] - CD_POLICY["target_h_deg"]) / CD_POLICY["tolerance_deg"]
    e_v = (bw_v[mask] - CD_POLICY["target_v_deg"]) / CD_POLICY["tolerance_deg"]
    di_band = di[mask]
    var_di = float(np.var(di_band, ddof=0))
    j = float(np.mean(e_h ** 2) + np.mean(e_v ** 2) + var_di)
    scalars = metrics.get("scalars", {})
    per_band = [
        {"freq_hz": float(freqs[i]), "bw_h_deg": float(bw_h[i]), "bw_v_deg": float(bw_v[i]),
         "di_db": float(di[i]), "e_h": float(e_h[j2]), "e_v": float(e_v[j2])}
        for j2, i in enumerate(np.flatnonzero(mask))
    ]
    f_break_h = scalars.get("f_break_h_hz")
    f_break_v = scalars.get("f_break_v_hz")
    return {
        "policy": CD_POLICY,
        "n_bands": int(mask.sum()),
        "band_hz_used": [float(freqs[mask][0]), float(freqs[mask][-1])],
        "per_band": per_band,
        "mean_e_h_sq": float(np.mean(e_h ** 2)),
        "mean_e_v_sq": float(np.mean(e_v ** 2)),
        "var_di": var_di,
        "J_CD_cached": j,
        "di_mean_db": float(di_band.mean()),
        "di_min_db": float(di_band.min()),
        "di_max_db": float(di_band.max()),
        "di_range_db": float(di_band.max() - di_band.min()),
        "f_break_observations": {
            "f_break_h_hz": f_break_h, "f_break_v_hz": f_break_v,
            "f_load_hz": scalars.get("f_load_hz"),
            "note": ("f_break_h/f_break_v are cached reductions of the beamwidth curves; the "
                     "J_CD_cached band starts at 1200 Hz, above both break points, so the whole "
                     "diagnostic band is in the post-break narrowing region"),
        },
        "cached_metrics_path": str(CACHED_METRICS.relative_to(ROOT)),
        "di_source": metrics.get("di_source"),
        "WARNING": ("DIAGNOSTIC, NOT the v7 objective. The cached run used di_slope_target=+5 dB/dec "
                    "with no DI weight; do not compare J across objectives."),
    }


# ------------------------------------------------------------------ core loader
def run_preflight(with_convergence: bool = True, with_points: bool = False) -> dict:
    """Build every seed record, compute deviations/convergence, and the cached CD diagnostic."""
    seeds = []
    for sid, path, cfg in load_configs():
        brief_path = (path.parent / cfg["brief_file"]).resolve()
        brief = yaml.safe_load(brief_path.read_text(encoding="utf-8"))
        shape = shape_from_config(cfg)
        rec = {
            "seed": sid,
            "config_path": str(path.relative_to(ROOT)),
            "config_sha256": _sha_file(path),
            "brief_path": str(brief_path.relative_to(ROOT)),
            "shape": shape,
        }
        try:
            pts, meta = K.make_grid(shape, brief)
            diag = K.diagnostics(shape, brief)
            z, a, b = _forward_axes(shape, brief)
            rec.update({
                "status": "accepted",
                "rejection_reason": None,
                "diagnostics": _clean(diag),
                "meta": _clean({
                    "schema": K.SCHEMA, "kind": K.KIND, "core_mode": meta["core_mode"],
                    "area_mode": meta["area_mode"], "construction_label": meta["construction_label"],
                    "core_info": meta["core_info"], "r0_mm": meta["r0_mm"],
                }),
                "envelope": _envelope_from_points(pts, float(shape["wall_thickness_mm"])),
                "grid_sha256": _grid_sha(pts),
                "grid_shape": list(pts.shape),
                "forward_axes": {"z_mm": z.tolist(), "a_mm": a.tolist(), "b_mm": b.tolist()},
            })
            if with_points:
                rec["points"] = pts
        except ValueError as exc:
            rec.update({
                "status": "rejected",
                "rejection_reason": str(exc),
                "rejection_type": type(exc).__name__,
                "envelope": None, "grid_sha256": None,
            })
        seeds.append(rec)

    # A0 legacy bit-exact control: blend 0 must reproduce the parent grid exactly.
    a0 = next(s for s in seeds if s["seed"] == "a0")
    if a0["status"] == "accepted":
        a0_cfg = yaml.safe_load((ROOT / a0["config_path"]).read_text(encoding="utf-8"))
        a0_brief = yaml.safe_load((ROOT / a0["brief_path"]).read_text(encoding="utf-8"))
        legacy_pts, _ = PARENT.make_grid(K.legacy_view(a0["shape"]), a0_brief)
        a0["legacy_control"] = {
            "legacy_grid_sha256": _grid_sha(legacy_pts),
            "hv_grid_sha256": a0["grid_sha256"],
            "bit_exact": bool(a0["grid_sha256"] == _grid_sha(legacy_pts)),
            "note": "cd_core_blend = 0 must reproduce klangfilm_lame-v1 bit-for-bit",
        }

    # Forward semi-axis deviation vs A0 (A0's forward z grid is the common abscissa).
    a0_fwd = a0.get("forward_axes")
    if a0_fwd is not None:
        z_ref = np.asarray(a0_fwd["z_mm"], dtype=float)
        a_ref = np.asarray(a0_fwd["a_mm"], dtype=float)
        b_ref = np.asarray(a0_fwd["b_mm"], dtype=float)
        for rec in seeds:
            if rec["status"] != "accepted":
                continue
            fwd = rec["forward_axes"]
            a_i = np.interp(z_ref, np.asarray(fwd["z_mm"], dtype=float),
                            np.asarray(fwd["a_mm"], dtype=float))
            b_i = np.interp(z_ref, np.asarray(fwd["z_mm"], dtype=float),
                            np.asarray(fwd["b_mm"], dtype=float))
            rec["deviation_vs_a0"] = {
                "abscissa": "A0 monotonic forward z stations, linear interpolation",
                "max_abs_a_minus_a0_mm": float(np.max(np.abs(a_i - a_ref))),
                "max_abs_b_minus_b0_mm": float(np.max(np.abs(b_i - b_ref))),
                "note": ("a5 also changes parent genes, so its deviation is not a single-knob measure; "
                         "a1..a4b share the parent genes with A0"),
            }
            del rec["forward_axes"]

    # Convergence for accepted, non-legacy seeds (blend > 0).
    if with_convergence:
        for rec in seeds:
            if rec["status"] != "accepted":
                continue
            if rec["diagnostics"]["core_mode"] == "legacy":
                rec["convergence"] = None
                continue
            brief = yaml.safe_load((ROOT / rec["brief_path"]).read_text(encoding="utf-8"))
            rec["convergence"] = _convergence(rec["shape"], brief, rec["diagnostics"])

    return {
        "scope": ("Phase A Klangfilm-Lame H/V entrance experiment: sampled inner quarter surfaces only. "
                  "No meshing, BEM, GPU, shell, curvature, intersection, acoustic or readiness claim."),
        "schema": K.SCHEMA,
        "kind": K.KIND,
        "envelope_mm": dict(ENVELOPE_MM),
        "environment": {"python": sys.version.split()[0], "numpy": np.__version__, "pyyaml": yaml.__version__},
        "input_sha256": {
            str(p.relative_to(ROOT)): _sha_file(p)
            for p in [*(p for _, p, _ in load_configs()),
                      ROOT / "tools/geometry/klangfilm_lame_hv.py",
                      ROOT / "tools/geometry/klangfilm_lame.py",
                      ROOT / "tools/geometry/lame_cap.py",
                      CACHED_METRICS]
        },
        "cd_diagnostic": j_cd_cached(),
        "seeds": seeds,
        "seed_order": list(SEED_ORDER),
    }


# ------------------------------------------------------------------ report writers
def _fmt(value, digits=2, dash="—"):
    if value is None:
        return dash
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _seed_row(rec: dict) -> dict:
    if rec["status"] == "rejected":
        return {"seed": rec["seed"], "status": "rejected", "reason": rec["rejection_reason"]}
    d = rec["diagnostics"]
    q0, q5, q15 = d["q_at_0"], d["q_at_5mm"], d["q_at_15mm"]
    p = d["lame_p_by_forward_fraction"]
    return {
        "seed": rec["seed"],
        "status": "accepted",
        "theta_model_h": d["theta_model_h_deg"], "theta_model_v": d["theta_model_v_deg"],
        "theta_mesh_h": d["mesh_halfangle_h_deg"], "theta_mesh_v": d["mesh_halfangle_v_deg"],
        "target_h": d["wall_halfangle_h_target_deg"], "target_v": d["wall_halfangle_v_target_deg"],
        "q0": q0, "q5": q5, "q15": q15,
        "p_throat": p.get("0.0"), "p_02": p.get("0.2"), "p_05": p.get("0.5"), "p_08": p.get("0.8"),
        "W": d["max_width_mm"], "H": d["max_height_mm"], "D": d["depth_mm"],
        "envelope_outer": rec["envelope"]["outer_estimate_mm"],
        "envelope_within": rec["envelope"]["within"],
        "delta_vs_a0_h": rec.get("deviation_vs_a0", {}).get("max_abs_a_minus_a0_mm"),
        "delta_vs_a0_v": rec.get("deviation_vs_a0", {}).get("max_abs_b_minus_b0_mm"),
        "rejection_reason": None,
    }


def write_reports(result: dict) -> dict:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    rows = [_seed_row(r) for r in result["seeds"]]
    payload = dict(result)
    payload["seed_rows"] = rows
    (EVIDENCE_DIR / "preflight.json").write_text(
        json.dumps(_clean(payload), indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")

    lines = []
    lines.append("# Klangfilm-Lame H/V Phase A — geometry preflight")
    lines.append("")
    lines.append("**DIAGNOSTIC ONLY.** Surface geometry from the Phase A kernel "
                 "(`klangfilm-lame-hv-v1`); no meshing, BEM, GPU, shell, curvature or acoustic "
                 "validation. These are geometry hypotheses, not acoustic winners.")
    lines.append("")
    lines.append("Kernel called directly (`tools/geometry/klangfilm_lame_hv.py`), never the package "
                 "adapter. H/V angles below are TRUE WALL HALF-ANGLES (not beamwidth halves). "
                 "Envelope is a `sampled_conservative_estimate` (inner sampled quarter grid + wall "
                 "thickness), not a mesh certificate.")
    lines.append("")
    lines.append("Two as-specified seeds (a3, a4) are refused by the kernel's no-constriction "
                 "invariant: a negative `g_*_mid_gain_mm` lets the B2 basis dominate the local wall "
                 "slope, so the forward V radius stops being non-decreasing. The feasible variants "
                 "(a3b, a4b) replace only that impossible negative gain with 0.0; the negative-V "
                 "idea is recorded as Phase B motivation, not as a bug.")
    lines.append("")
    lines.append("## Seed status")
    lines.append("")
    lines.append("| seed | status | θ_H model/mesh (deg) | θ_V model/mesh (deg) | targets H/V (deg) | "
                 "q(0)/q(5)/q(15) | p throat/0.2/0.5/0.8 | W/H/D inner (mm) | envelope | "
                 "Δ vs A0 H/V (mm) | rejection reason |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for row in rows:
        if row["status"] == "rejected":
            lines.append(f"| {row['seed']} | **rejected** | — | — | — | — | — | — | — | — | "
                         f"`{row['reason']}` |")
            continue
        lines.append(
            f"| {row['seed']} | accepted | "
            f"{row['theta_model_h']:.2f} / {row['theta_mesh_h']:.2f} | "
            f"{row['theta_model_v']:.2f} / {row['theta_mesh_v']:.2f} | "
            f"{_fmt(row['target_h'], 1)} / {_fmt(row['target_v'], 1)} | "
            f"{row['q0']:.3f}/{row['q5']:.3f}/{row['q15']:.3f} | "
            f"{row['p_throat']:.3f}/{row['p_02']:.3f}/{row['p_05']:.3f}/{row['p_08']:.3f} | "
            f"{row['W']:.1f}/{row['H']:.1f}/{row['D']:.1f} | "
            f"{'OK' if row['envelope_within'] else '**EXCEEDED**'} | "
            f"{row['delta_vs_a0_h']:.3f} / {row['delta_vs_a0_v']:.3f} | — |")
    lines.append("")
    lines.append("Δ vs A0 = max |forward semi-axis − A0 forward semi-axis| on A0's forward z stations. "
                 "A0 (blend 0) is the legacy control; a5 also changes parent genes, so its Δ is not a "
                 "single-knob measure.")
    lines.append("")
    a0 = next((r for r in result["seeds"] if r["seed"] == "a0"), None)
    if a0 and a0.get("legacy_control"):
        lc = a0["legacy_control"]
        lines.append(f"A0 legacy control: blend 0 grid is "
                     f"{'**bit-exact**' if lc['bit_exact'] else '**NOT bit-exact**'} with "
                     f"`klangfilm_lame-v1` (sha256 `{lc['hv_grid_sha256'][:16]}…`).")
        lines.append("")
    lines.append("## Convergence (accepted, non-legacy seeds)")
    lines.append("")
    lines.append("Rebuilt at `n_phi=37` and at `n_s=128`. The mesh chord is expected to approach the "
                 "analytic model angle as `n_s` rises; no hard bound is asserted, the numbers and trend "
                 "are reported.")
    lines.append("")
    lines.append("| seed | Δmax W @n_phi37 (mm) | Δmax H @n_phi37 (mm) | Δthroat spread @n_phi37 (mm) | "
                 "Δmax W @n_s128 (mm) | Δmax H @n_s128 (mm) | mesh−model H/V @n_s64 (deg) | "
                 "mesh−model H/V @n_s128 (deg) | trend H/V toward model |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for rec in result["seeds"]:
        conv = rec.get("convergence")
        if rec["status"] != "accepted" or conv is None:
            continue
        dphi = conv["delta_n_phi_37_vs_base"]
        dns = conv["delta_n_s_128_vs_base"]
        b = conv["base"]
        f = conv["n_s_128"]
        lines.append(
            f"| {rec['seed']} | {dphi['max_width_mm']:+.4f} | {dphi['max_height_mm']:+.4f} | "
            f"{dphi['throat_radius_spread_mm']:+.5f} | "
            f"{dns['max_width_mm']:+.4f} | {dns['max_height_mm']:+.4f} | "
            f"{b['mesh_halfangle_h_deg'] - b['theta_model_h_deg']:+.3f} / "
            f"{b['mesh_halfangle_v_deg'] - b['theta_model_v_deg']:+.3f} | "
            f"{f['mesh_halfangle_h_deg'] - f['theta_model_h_deg']:+.3f} / "
            f"{f['mesh_halfangle_v_deg'] - f['theta_model_v_deg']:+.3f} | "
            f"{'toward' if conv['trend_toward_model_h'] else 'away'} / "
            f"{'toward' if conv['trend_toward_model_v'] else 'away'} |")
    lines.append("")
    cd = result["cd_diagnostic"]
    lines.append("## Cached CD diagnostic `J_CD_cached`")
    lines.append("")
    lines.append(f"**{cd['policy']['kind']}.** Band `[1200, 5600] Hz` inclusive; "
                 f"`{cd['policy']['J']}`; {cd['policy']['variance']}; "
                 f"`tau = {cd['policy']['tau_deg']} deg` recorded as the reference tolerance. "
                 f"**{cd['policy']['objective_note']}.**")
    lines.append("")
    lines.append(f"- `J_CD_cached = {cd['J_CD_cached']:.6f}` over {cd['n_bands']} cached bands "
                 f"({cd['band_hz_used'][0]:.2f}–{cd['band_hz_used'][1]:.2f} Hz).")
    lines.append(f"- mean e_H² = {cd['mean_e_h_sq']:.6f}, mean e_V² = {cd['mean_e_v_sq']:.6f}, "
                 f"Var(DI) = {cd['var_di']:.6f}.")
    lines.append(f"- DI mean = {cd['di_mean_db']:.3f} dB, range = {cd['di_range_db']:.3f} dB "
                 f"({cd['di_min_db']:.3f}–{cd['di_max_db']:.3f} dB).")
    fb = cd["f_break_observations"]
    lines.append(f"- f_break H = {fb['f_break_h_hz']} Hz, f_break V = {fb['f_break_v_hz']} Hz, "
                 f"f_load = {fb['f_load_hz']} Hz. {fb['note']}.")
    lines.append("")
    lines.append("| freq (Hz) | BW_H (deg) | BW_V (deg) | DI (dB) | e_H | e_V |")
    lines.append("|---|---|---|---|---|---|")
    for band in cd["per_band"]:
        lines.append(f"| {band['freq_hz']:.2f} | {band['bw_h_deg']:.3f} | {band['bw_v_deg']:.3f} | "
                     f"{band['di_db']:.3f} | {band['e_h']:+.4f} | {band['e_v']:+.4f} |")
    lines.append("")
    lines.append("Source: `" + cd["cached_metrics_path"] + "` (cached; no solve in this preflight).")
    lines.append("")
    (EVIDENCE_DIR / "PREFLIGHT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"rows": rows, "json": payload}


def main() -> None:
    result = run_preflight(with_convergence=True, with_points=False)
    write_reports(result)
    print(f"Klangfilm-Lame H/V Phase A preflight - schema {K.SCHEMA}")
    print(f"{'seed':<4} {'status':<9} {'theta H model/mesh':<22} {'theta V model/mesh':<22} "
          f"{'W/H/D mm':<22} envelope")
    for rec in result["seeds"]:
        if rec["status"] == "rejected":
            print(f"{rec['seed']:<4} {'REJECTED':<9} {'-':<22} {'-':<22} {'-':<22} "
                  f"{rec['rejection_reason']}")
            continue
        d = rec["diagnostics"]
        env = rec["envelope"]
        print(f"{rec['seed']:<4} {'accepted':<9} "
              f"{d['theta_model_h_deg']:6.2f} / {d['mesh_halfangle_h_deg']:6.2f}      "
              f"{d['theta_model_v_deg']:6.2f} / {d['mesh_halfangle_v_deg']:6.2f}      "
              f"{d['max_width_mm']:6.1f}/{d['max_height_mm']:6.1f}/{d['depth_mm']:6.1f}   "
              f"{'OK' if env['within'] else 'ENVELOPE EXCEEDED ' + ','.join(env['exceeded'])}")
    n_acc = sum(r["status"] == "accepted" for r in result["seeds"])
    n_rej = len(result["seeds"]) - n_acc
    print(f"\naccepted {n_acc}, rejected {n_rej}")
    print(f"J_CD_cached = {result['cd_diagnostic']['J_CD_cached']:.6f} "
          f"({result['cd_diagnostic']['n_bands']} bands, DIAGNOSTIC not the v7 objective)")
    print(f"wrote {EVIDENCE_DIR / 'preflight.json'}")
    print(f"wrote {EVIDENCE_DIR / 'PREFLIGHT.md'}")


if __name__ == "__main__":
    main()
