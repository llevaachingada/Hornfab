"""Phase B geometry preflight and plots (CPU only, no mesh/solve).

Compares the incumbent A0 (legacy v1) with the three Phase B monotone-core seeds and writes:

  docs/evidence/klangfilm_hv_2026-11-16/PHASE_B_GEOMETRY.md / phase_b_geometry.json
  docs/evidence/klangfilm_hv_2026-11-16/phase_b_sections.png
  docs/evidence/klangfilm_hv_2026-11-16/phase_b_laws.png

Every number is computed. No acoustic claim: Phase B has not been solved.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from tools.geometry import klangfilm_lame as K  # noqa: E402
from tools.geometry import klangfilm_lame_hv_core as C  # noqa: E402

EVIDENCE = ROOT / "docs/evidence/klangfilm_hv_2026-11-16"
A0_CONFIG = ROOT / "examples/typologies/klangfilm_hv_2026-11-16/configs/a0.yaml"
BRIEF = {"driver": {"exit_radius_mm": 18.0, "exit_angle_deg": 2.0}}
ENVELOPE = {"w": 600.0, "h": 480.0, "d": 480.0}
COLORS = {"a0": "#111111", "b1": "#1f6f3f", "b2": "#8a4fbf", "b3": "#c2761d", "b4": "#2f8fa8"}


def _a0_shape():
    cfg = yaml.safe_load(A0_CONFIG.read_text(encoding="utf-8"))
    out = {k[2:]: float(v) for k, v in cfg["seed_params"].items() if k[2:] in K.SHAPE_KEYS}
    out.update({k: float(cfg["generator"][k]) for k in ("n_phi", "n_s", "wall_thickness_mm")})
    return out


def _a0_profiles():
    """Full v1 meridian, including the intrinsic rollback: the real mouth is the LAST station."""
    tab = K.profile(_a0_shape(), 18.0)
    return tab["z"], tab["a"], tab["b"], tab["p"]


def main() -> int:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    a0_shape = _a0_shape()
    a0_pts, _ = K.make_grid(a0_shape, BRIEF)
    a0_d = K.diagnostics(a0_shape, BRIEF)
    from tools.geometry import lame_cap as _cap
    _a0_tab = K.profile(a0_shape, 18.0)
    _z, _a, _b, _p = _a0_profiles()
    a0_mouth_area = float(_cap.flat_lame_area(float(_a[-1]), float(_b[-1]), max(float(_p[-1]), 2.0)))
    rows = [{
        "seed": "a0", "kind": "legacy v1 (control)",
        "theta_h": f"{a0_d['wall_halfangle_h_deg']:.2f} deg (parent)",
        "theta_v": f"{a0_d['wall_halfangle_v_deg']:.2f} deg (parent)",
        "core_mm": None, "p_mouth": 5.006, "area_throat_mm2": float(np.pi * 18 ** 2),
        "area_mouth_mm2": a0_mouth_area, "w_mm": a0_d["max_width_mm"],
        "h_mm": a0_d["max_height_mm"],
        "d_mm": a0_d["depth_mm"],
        "turns": int(np.count_nonzero(np.sign(np.diff(_a0_tab["z"])[1:])
                                      != np.sign(np.diff(_a0_tab["z"])[:-1]))),
        "clearance_mm": None,
        "grid_sha256": hashlib.sha256(np.asarray(a0_pts).tobytes()).hexdigest(),
    }]
    for name in sorted(C.SEEDS):
        sh = C.seed_shape(name)
        pts, meta = C.make_grid(sh, BRIEF)
        d = C.diagnostics(sh, BRIEF)
        rows.append({
            "seed": name, "kind": "monotone H/V core",
            "theta_h": f"{sh['theta_h0_deg']:.1f} -> {sh['theta_h1_deg']:.1f} deg",
            "theta_v": f"{sh['theta_v0_deg']:.1f} -> {sh['theta_v1_deg']:.1f} deg",
            "core_mm": float(sh["core_length_mm"]), "p_mouth": float(sh["lame_p_mouth"]),
            "area_throat_mm2": d["throat_section"]["area_mm2"],
            "area_mouth_mm2": d["mouth_section"]["area_mm2"],
            "w_mm": d["max_width_mm"], "h_mm": d["max_height_mm"], "d_mm": d["depth_mm"],
            "turns": d["h_meridian_turns"] + d["v_meridian_turns"],
            "clearance_mm": d["min_lip_clearance_mm"], "beak": d["beak_offsets_mm"],
            "grid_sha256": hashlib.sha256(np.asarray(pts).tobytes()).hexdigest(),
            "schema": meta["schema"], "wavefront_model": meta["wavefront_model"],
        })
    for row in rows:
        row["envelope_ok"] = bool(row["w_mm"] <= ENVELOPE["w"] and row["h_mm"] <= ENVELOPE["h"]
                                  and row["d_mm"] <= ENVELOPE["d"])

    (EVIDENCE / "phase_b_geometry.json").write_text(
        json.dumps({"envelope_mm": ENVELOPE, "rows": rows, "brief": BRIEF}, indent=2, sort_keys=True)
        + "\n", encoding="utf-8")

    md = ["# Phase B geometry preflight (CPU only, no solve)", "",
          "Monotone integrated-slope H/V core: `theta_i(z) = theta_i0 + (theta_i1-theta_i0) Q(z/L)`,",
          "`r_i(z) = r0 + int tan(theta_i) dz`, Lamé section with independent `p(z)`, and a late swept",
          "beak. `cd_core_blend = 0` returns the v1 grid bit-for-bit. No acoustic result exists for any",
          "Phase B seed; this table is geometry only.", "",
          "| seed | kind | theta_H | theta_V | L mm | p mouth | area throat->mouth (mm2) | W/H/D mm | turns | lip clear mm | envelope | grid sha256 |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for row in rows:
        area = f"{row['area_throat_mm2']:.0f} -> " + (f"{row['area_mouth_mm2']:.0f}"
                                                      if row["area_mouth_mm2"] else "n/a")
        clear = "-" if row["clearance_mm"] is None else f"{row['clearance_mm']:.1f}"
        md.append(f"| {row['seed']} | {row['kind']} | {row['theta_h']} | {row['theta_v']} | "
                  f"{row['core_mm'] if row['core_mm'] else '-'} | {row['p_mouth']:.2f} | {area} | "
                  f"{row['w_mm']:.0f}/{row['h_mm']:.0f}/{row['d_mm']:.0f} | {row['turns']} | "
                  f"{clear} | {'OK' if row['envelope_ok'] else 'OVER'} | "
                  f"`{row['grid_sha256'][:16]}` |")
    md += ["", "`turns` counts axial sign changes on the H and V meridians (0 = a pure forward core; a",
           "positive beak over a late gate can add one intended setback).", "",
           "The `p` column is `lame_p_mouth` for the core seeds and the parent's own value for A0.",
           "",
           "**Not a validity certificate.** `lame_shell`/`check_self_approach` and a real mesh are still",
           "required before any Phase B solve; the lip clearance here is a sampled minimum between the last",
           "station and the body.", ""]
    (EVIDENCE / "PHASE_B_GEOMETRY.md").write_text("\n".join(md), encoding="utf-8")

    # sections
    z0, a0, b0, _p0 = _a0_profiles()
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5), facecolor="white")
    axes[0].plot(z0, a0, "--", color=COLORS["a0"], lw=2, label="a0 H (v1)")
    axes[1].plot(z0, b0, "--", color=COLORS["a0"], lw=2, label="a0 V (v1)")
    for name in sorted(C.SEEDS):
        sh = C.seed_shape(name)
        tab = C.core_table(sh, 18.0)
        axes[0].plot(tab["z"], tab["a"], color=COLORS.get(name, "#777"), lw=1.6, label=f"{name} H")
        axes[1].plot(tab["z"], tab["b"], color=COLORS[name], lw=1.6, label=f"{name} V")
    for ax, title in ((axes[0], "H meridian"), (axes[1], "V meridian")):
        ax.set_title(title)
        ax.set_xlabel("axial z (mm)")
        ax.set_ylabel("wall radius (mm)")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
    fig.suptitle("Phase B monotone core vs the v1 incumbent (true scale, no beak offsets on the meridians)",
                 fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(EVIDENCE / "phase_b_sections.png", dpi=150)
    plt.close(fig)

    # slope/area laws
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), facecolor="white")
    from tools.geometry import lame_cap
    for name in sorted(C.SEEDS):
        sh = C.seed_shape(name)
        tab = C.core_table(sh, 18.0)
        axes[0].plot(tab["z"], np.degrees(tab["theta_h"]), color=COLORS.get(name, "#777"), lw=1.6,
                     label=f"{name} H")
        axes[0].plot(tab["z"], np.degrees(tab["theta_v"]), color=COLORS.get(name, "#777"), lw=1.6, ls=":")
        area = np.array([lame_cap.flat_lame_area(a, b, max(p, 2.0))
                         for a, b, p in zip(tab["a"], tab["b"], tab["p"])])
        axes[1].plot(tab["z"], area, color=COLORS.get(name, "#777"), lw=1.6, label=name)
    axes[0].set_title("wall angle law (solid H, dotted V)")
    axes[0].set_xlabel("axial z (mm)")
    axes[0].set_ylabel("wall half-angle (deg)")
    axes[1].set_title("flat Lamé section area")
    axes[1].set_xlabel("axial z (mm)")
    axes[1].set_ylabel("area (mm^2)")
    for ax in axes:
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(EVIDENCE / "phase_b_laws.png", dpi=150)
    plt.close(fig)

    print("wrote PHASE_B_GEOMETRY.md, phase_b_geometry.json, phase_b_sections.png, phase_b_laws.png")
    for row in rows:
        print(f"  {row['seed']}: {row['w_mm']:.0f}x{row['h_mm']:.0f}x{row['d_mm']:.0f} mm "
              f"turns={row['turns']} envelope_ok={row['envelope_ok']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
