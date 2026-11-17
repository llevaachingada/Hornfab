"""Klangfilm-Lame H/V Phase A contact sheet (matplotlib Agg only; CPU; no meshing/BEM).

Renders ONLY the accepted seeds reported by ``klangfilm_hv_preflight`` (imported, not duplicated),
plus clearly labelled grey panels for the rejected seeds with the exact kernel refusal text.

Outputs (150 dpi) under ``docs/evidence/klangfilm_hv_2026-11-16``:
  contact_sheet_oblique.png, contact_sheet_front.png, contact_sheet_top.png, contact_sheet_side.png
  sections_hv.png      H/V meridian sections in true scale, A0 dashed reference
  throat_zoom.png      0-20 mm throat zoom (1 mm ticks) + 5 mm / 15 mm cross-section insets
  sheet_metadata.json  input sha256s, camera/scale config, per-panel numbers, rejection reasons

Every panel is SURFACE ONLY: no mesh/BEM validation, the 3 mm shell is NOT shown, and the camera
is fixed orthographic with one identical millimetre scale across panels.

Run: ``.venv\\Scripts\\python.exe tools/geometry/klangfilm_hv_contact_sheet.py``
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import yaml
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.geometry import klangfilm_lame_hv as K  # noqa: E402
from tools.geometry import klangfilm_hv_preflight as P  # noqa: E402

EVIDENCE = ROOT / "docs/evidence/klangfilm_hv_2026-11-16"
FACE = "#f5f3ef"
REJECT_FACE = "#b8b4ad"
VIEWS = {"oblique": (18, -58), "front": (90, -90), "top": (0, -90), "side": (0, 0)}
#: One identical millimetre scale for every 3D panel (covers the largest accepted seed + margin).
LIM_XY = 340.0
LIM_Z = (0.0, 300.0)
SEED_COLOR = {"a0": "#9a8f80", "a1": "#c58155", "a2": "#b5563f", "a3b": "#4f7d5b",
              "a4b": "#4a6fa5", "a5": "#8a6fb0"}
EDGE_COLOR = {"a0": "#4a4038", "a1": "#614634", "a2": "#5a2418", "a3b": "#243d2c",
              "a4b": "#22384f", "a5": "#42315a"}
A0_COLOR = "#333333"

FOOTNOTE = ("Surface-only; no mesh/BEM validation; 3 mm shell NOT shown; "
            "fixed orthographic camera and identical millimetre scale on every panel.")


# ------------------------------------------------------------------ helpers
def _sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _brief(rec: dict) -> dict:
    return yaml.safe_load((ROOT / rec["brief_path"]).read_text(encoding="utf-8"))


def _profile(rec: dict):
    return K.profile(rec["shape"], float(_brief(rec)["driver"]["exit_radius_mm"]))


def _station(tab: dict, z_mm: float):
    turn = K.forward_slice(tab)
    zf = np.asarray(tab["z"][: turn + 1], dtype=float)
    return (float(np.interp(z_mm, zf, tab["a"][: turn + 1])),
            float(np.interp(z_mm, zf, tab["b"][: turn + 1])),
            float(np.interp(z_mm, zf, tab["p"][: turn + 1])))


def _lame_outline(a: float, b: float, p: float, n: int = 480):
    phi = np.linspace(0.0, 2.0 * np.pi, n)
    co, si = np.cos(phi), np.sin(phi)
    x = a * np.sign(co) * np.abs(co) ** (2.0 / p)
    y = b * np.sign(si) * np.abs(si) ** (2.0 / p)
    return x, y


def panel_numbers(rec: dict) -> dict:
    """All numbers printed in a panel title, recomputed from kernel/public profile."""
    d = rec["diagnostics"]
    tab = _profile(rec)
    return {
        "seed": rec["seed"],
        "r_h0_mm": float(tab["a"][0]),
        "r_v0_mm": float(tab["b"][0]),
        "theta_model_h_deg": d["theta_model_h_deg"],
        "theta_model_v_deg": d["theta_model_v_deg"],
        "theta_mesh_h_deg": d["mesh_halfangle_h_deg"],
        "theta_mesh_v_deg": d["mesh_halfangle_v_deg"],
        "target_h_deg": d["wall_halfangle_h_target_deg"],
        "target_v_deg": d["wall_halfangle_v_target_deg"],
        "q0": d["q_at_0"], "q5": d["q_at_5mm"], "q15": d["q_at_15mm"],
        "p_throat": d["lame_p_at_throat"], "p_half": d["lame_p_by_forward_fraction"].get("0.5"),
        "axial_turns": d["axial_turns_whole_profile"],
        "W_mm": d["max_width_mm"], "H_mm": d["max_height_mm"], "D_mm": d["depth_mm"],
        "outer_mm": rec["envelope"]["outer_estimate_mm"],
        "envelope_within": rec["envelope"]["within"],
        "envelope_exceeded_axes": rec["envelope"]["exceeded"],
        "z_forward_mm": d["z_forward_mm"],
        "delta_h_max_mm": d["delta_h_max_mm"], "delta_v_max_mm": d["delta_v_max_mm"],
    }


def _title(n: dict) -> str:
    th = "n/a" if n["target_h_deg"] is None else f"{n['target_h_deg']:.1f}"
    tv = "n/a" if n["target_v_deg"] is None else f"{n['target_v_deg']:.1f}"
    return (
        f"{n['seed']}   "
        f"r_H(0)={n['r_h0_mm']:.2f}  r_V(0)={n['r_v0_mm']:.2f} mm\n"
        f"θ_H(0+) model {n['theta_model_h_deg']:.2f} / mesh {n['theta_mesh_h_deg']:.2f} deg "
        f"(target {th})\n"
        f"θ_V(0+) model {n['theta_model_v_deg']:.2f} / mesh {n['theta_mesh_v_deg']:.2f} deg "
        f"(target {tv})\n"
        f"q(0)/q(5)/q(15) = {n['q0']:.3f} / {n['q5']:.3f} / {n['q15']:.3f}\n"
        f"p throat {n['p_throat']:.3f} | p@0.5 {n['p_half']:.3f}\n"
        f"axial turns {n['axial_turns']} | W/H/D {n['W_mm']:.0f}/{n['H_mm']:.0f}/{n['D_mm']:.0f} mm\n"
        f"outer est. {n['outer_mm']['width']:.0f}/{n['outer_mm']['height']:.0f}/"
        f"{n['outer_mm']['depth']:.0f} mm vs 600/480/480"
    )


def _envelope_text(n: dict) -> tuple[str, str]:
    if n["envelope_within"]:
        return "envelope OK (sampled conservative estimate)", "#333333"
    axes = ", ".join(n["envelope_exceeded_axes"])
    return f"ENVELOPE EXCEEDED: {axes}", "#a3261b"


def _surface(ax, pts: np.ndarray, color: str, edge: str) -> None:
    p = np.asarray(pts, dtype=float).copy()
    p[:, :, 2] -= p[:, :, 2].min()
    for sx, sy in ((1, 1), (-1, 1), (-1, -1), (1, -1)):
        ax.plot_surface(sx * p[:, :, 0], sy * p[:, :, 1], p[:, :, 2], rstride=2, cstride=3,
                        color=color, edgecolor=edge, linewidth=0.1, shade=True,
                        antialiased=True, alpha=0.95)


def _style_3d(ax, view: str) -> None:
    ax.set_facecolor(FACE)
    ax.set_proj_type("ortho")
    ax.set_xlim(-LIM_XY, LIM_XY)
    ax.set_ylim(-LIM_XY, LIM_XY)
    ax.set_zlim(*LIM_Z)
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(*VIEWS[view])
    ax.set_axis_off()


# ------------------------------------------------------------------ figures
def _save_png(fig, out: Path) -> None:
    """Save through an in-memory buffer, then write bytes.

    PIL's direct ``Image.save(path)`` intermittently raised ``OSError: [Errno 22] Invalid argument``
    for these large 3-D canvases on this Windows box (three different target files across runs, while
    a minimal probe always succeeded). Buffering removes the file-open path from the backend entirely
    and makes the written bytes identical run to run.
    """
    import io
    import os
    import time
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, facecolor=fig.get_facecolor())
    out.parent.mkdir(parents=True, exist_ok=True)
    # A fresh sibling name avoids opening a file another process (scanner/preview/dropped agent
    # session) may still hold; os.replace then swaps it into place atomically.
    tmp = out.with_name(f".{out.name}.{os.getpid()}.tmp")
    tmp.write_bytes(buf.getvalue())
    for attempt in range(6):
        try:
            os.replace(tmp, out)
            return
        except OSError:
            if attempt == 5:
                tmp.unlink(missing_ok=True)
                raise
            time.sleep(0.4)


def contact_sheets(result: dict, accepted: list, rejected: list) -> dict:
    images = {}
    for view in VIEWS:
        fig = plt.figure(figsize=(21.0, 9.6), facecolor=FACE)
        gs = fig.add_gridspec(2, 6, height_ratios=[3.0, 2.0])
        for col, rec in enumerate(accepted):
            ax = fig.add_subplot(gs[0, col], projection="3d")
            _style_3d(ax, view)
            _surface(ax, rec["points"], SEED_COLOR[rec["seed"]], EDGE_COLOR[rec["seed"]])
            n = panel_numbers(rec)
            ax.text2D(0.02, 0.99, _title(n), transform=ax.transAxes, va="top", ha="left",
                      fontsize=6.2, family="DejaVu Sans")
            text, color = _envelope_text(n)
            ax.text2D(0.02, 0.02, text, transform=ax.transAxes, va="bottom", ha="left",
                      fontsize=6.8, color=color, weight="bold")
        for col, rec in enumerate(rejected):
            ax = fig.add_subplot(gs[1, col], projection="3d")
            ax.set_facecolor(REJECT_FACE)
            ax.set_proj_type("ortho")
            ax.set_xlim(-LIM_XY, LIM_XY); ax.set_ylim(-LIM_XY, LIM_XY); ax.set_zlim(*LIM_Z)
            ax.set_box_aspect((1, 1, 1)); ax.view_init(*VIEWS[view]); ax.set_axis_off()
            ax.text2D(0.5, 0.62, f"{rec['seed']}\nREJECTED\n(no geometry)", transform=ax.transAxes,
                      ha="center", va="center", fontsize=11, weight="bold", color="#2b2b2b")
            ax.text2D(0.05, 0.10, f"kernel refusal:\n{rec['rejection_reason']}",
                      transform=ax.transAxes, ha="left", va="bottom", fontsize=7.2, color="#7a1c12",
                      wrap=True)
        for col in range(len(rejected), 6):
            ax = fig.add_subplot(gs[1, col])
            ax.set_axis_off()
        fig.suptitle(f"Klangfilm-Lame H/V Phase A — {view} view — accepted surfaces "
                     f"(top) / rejected seeds (bottom)", fontsize=17, weight="bold")
        fig.text(0.5, 0.012, FOOTNOTE, ha="center", fontsize=10)
        fig.subplots_adjust(left=0.005, right=0.995, bottom=0.05, top=0.93, wspace=0.02, hspace=0.02)
        out = EVIDENCE / f"contact_sheet_{view}.png"
        _save_png(fig, out)
        plt.close(fig)
        images[out.name] = str(out.relative_to(ROOT))
    return images


def sections_hv(accepted: list) -> str:
    fig, axes = plt.subplots(2, 1, figsize=(13.5, 10.5), facecolor=FACE)
    profiles = {rec["seed"]: _profile(rec) for rec in accepted}
    xmin = min(float(np.min(t["z"])) for t in profiles.values())
    xmax = max(float(np.max(t["z"])) for t in profiles.values())
    ymax = max(float(max(np.max(np.abs(t["a"])), np.max(np.abs(t["b"])))) for t in profiles.values())
    for ax, comp, axis_name in ((axes[0], "a", "H"), (axes[1], "b", "V")):
        ax.set_facecolor(FACE)
        for rec in accepted:
            tab = profiles[rec["seed"]]
            r = np.asarray(tab[comp], dtype=float)
            z = np.asarray(tab["z"], dtype=float)
            lw = 2.4 if rec["seed"] == "a0" else 1.4
            ls = "--" if rec["seed"] == "a0" else "-"
            color = A0_COLOR if rec["seed"] == "a0" else SEED_COLOR[rec["seed"]]
            label = f"{rec['seed']} (A0 reference)" if rec["seed"] == "a0" else rec["seed"]
            ax.plot(z, r, color=color, lw=lw, ls=ls, label=label)
            ax.plot(z, -r, color=color, lw=lw, ls=ls)
        ax.set_xlim(xmin - 5.0, xmax + 5.0)
        ax.set_ylim(-ymax * 1.05, ymax * 1.05)
        ax.set_aspect("equal")
        ax.grid(alpha=0.25)
        ax.set_xlabel("axial z (mm)")
        ax.set_ylabel(f"{axis_name} wall radius (mm)")
        ax.set_title(f"{axis_name} meridian section — true scale (mm), A0 dashed", fontsize=12)
    axes[0].legend(loc="upper left", fontsize=8, ncol=2)
    fig.suptitle("Klangfilm-Lame H/V Phase A — H and V meridian sections, true scale", fontsize=16,
                 weight="bold")
    fig.text(0.5, 0.012, FOOTNOTE, ha="center", fontsize=10)
    fig.subplots_adjust(left=0.075, right=0.985, bottom=0.06, top=0.92, hspace=0.28)
    out = EVIDENCE / "sections_hv.png"
    _save_png(fig, out)
    plt.close(fig)
    return str(out.relative_to(ROOT))


def throat_zoom(accepted: list) -> str:
    profiles = {rec["seed"]: _profile(rec) for rec in accepted}
    fig, axes = plt.subplots(2, 2, figsize=(13.5, 11.0), facecolor=FACE)

    # 0-20 mm axial zooms for H and V, 1 mm tick guidance. Both panels MUST share one radius
    # range: a per-panel autoscale gives H and V different vertical mm scales and makes the two
    # panels visually incomparable.
    panels = ((axes[0, 0], "a", "H"), (axes[0, 1], "b", "V"))
    y_lo, y_hi = np.inf, -np.inf
    for _ax, comp, _axis_name in panels:
        for rec in accepted:
            tab = profiles[rec["seed"]]
            turn = K.forward_slice(tab)
            z = np.asarray(tab["z"][: turn + 1], dtype=float)
            r = np.asarray(tab[comp][: turn + 1], dtype=float)
            m = (z >= 0.0) & (z <= 20.0)
            y_lo, y_hi = min(y_lo, float(r[m].min())), max(y_hi, float(r[m].max()))
    pad = 0.06 * max(y_hi - y_lo, 1e-9)
    for ax, comp, axis_name in panels:
        ax.set_facecolor(FACE)
        for rec in accepted:
            tab = profiles[rec["seed"]]
            turn = K.forward_slice(tab)
            z = np.asarray(tab["z"][: turn + 1], dtype=float)
            r = np.asarray(tab[comp][: turn + 1], dtype=float)
            m = (z >= 0.0) & (z <= 20.0)
            color = A0_COLOR if rec["seed"] == "a0" else SEED_COLOR[rec["seed"]]
            ls = "--" if rec["seed"] == "a0" else "-"
            ax.plot(z[m], r[m], color=color, lw=2.2 if rec["seed"] == "a0" else 1.5, ls=ls,
                    label=rec["seed"])
        ax.set_xlim(0.0, 20.0)
        ax.set_ylim(y_lo - pad, y_hi + pad)
        ax.set_xticks(np.arange(0.0, 21.0, 1.0))
        ax.set_xticks(np.arange(0.0, 20.5, 0.5), minor=True)
        ax.tick_params(axis="x", labelsize=7, labelrotation=90)
        ax.grid(alpha=0.35, which="both")
        ax.set_xlabel("axial z (mm), 1 mm major ticks")
        ax.set_ylabel(f"{axis_name} wall radius (mm)")
        ax.set_title(f"{axis_name} throat region 0-20 mm", fontsize=12)
        ax.legend(fontsize=8)
        d = next(r for r in accepted if r["seed"] == "a0")["diagnostics"]
        ax.annotate(f"A0 model θ_{axis_name}={d['theta_model_h_deg' if comp == 'a' else 'theta_model_v_deg']:.2f} deg",
                    xy=(0.98, 0.04), xycoords="axes fraction", ha="right", fontsize=8, color="#333333")

    # 5 mm and 15 mm downstream cross-sections (Lame section at the axial station).
    for ax, z_mm in ((axes[1, 0], 5.0), (axes[1, 1], 15.0)):
        ax.set_facecolor(FACE)
        for rec in accepted:
            a, b, p = _station(profiles[rec["seed"]], z_mm)
            x, y = _lame_outline(a, b, p)
            color = A0_COLOR if rec["seed"] == "a0" else SEED_COLOR[rec["seed"]]
            ls = "--" if rec["seed"] == "a0" else "-"
            ax.plot(x, y, color=color, lw=2.0 if rec["seed"] == "a0" else 1.3, ls=ls,
                    label=f"{rec['seed']} a={a:.2f} b={b:.2f} p={p:.2f}")
        ax.set_aspect("equal")
        ax.grid(alpha=0.25)
        ax.set_xlabel("x (mm)")
        ax.set_ylabel("y (mm)")
        ax.set_title(f"cross-section inset @ z = {z_mm:.0f} mm", fontsize=12)
        ax.legend(fontsize=6.6, loc="upper right")
    fig.suptitle("Klangfilm-Lame H/V Phase A — throat zoom and downstream cross-sections",
                 fontsize=16, weight="bold")
    fig.text(0.5, 0.012, FOOTNOTE, ha="center", fontsize=10)
    fig.subplots_adjust(left=0.075, right=0.985, bottom=0.06, top=0.92, wspace=0.24, hspace=0.30)
    out = EVIDENCE / "throat_zoom.png"
    _save_png(fig, out)
    plt.close(fig)
    return str(out.relative_to(ROOT))


# ------------------------------------------------------------------ main
def main() -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    result = P.run_preflight(with_convergence=False, with_points=True)
    accepted = [r for r in result["seeds"] if r["status"] == "accepted"]
    rejected = [r for r in result["seeds"] if r["status"] == "rejected"]
    if not accepted:
        raise SystemExit("no accepted seeds to render")

    images = contact_sheets(result, accepted, rejected)
    images["sections_hv.png"] = sections_hv(accepted)
    images["throat_zoom.png"] = throat_zoom(accepted)

    panels = {}
    for rec in accepted:
        n = panel_numbers(rec)
        panels[rec["seed"]] = {
            "status": "accepted",
            **n,
            "theta_model_h_deg_mesh_delta": n["theta_mesh_h_deg"] - n["theta_model_h_deg"],
            "theta_model_v_deg_mesh_delta": n["theta_mesh_v_deg"] - n["theta_model_v_deg"],
            "grid_sha256": rec["grid_sha256"],
        }
    for rec in rejected:
        panels[rec["seed"]] = {"status": "rejected", "rejection_reason": rec["rejection_reason"]}

    input_paths = [*(ROOT / r["config_path"] for r in result["seeds"]),
                   ROOT / "tools/geometry/klangfilm_lame_hv.py",
                   ROOT / "tools/geometry/klangfilm_lame.py",
                   ROOT / "tools/geometry/lame_cap.py",
                   ROOT / "tools/geometry/klangfilm_hv_preflight.py",
                   Path(__file__).resolve(), P.CACHED_METRICS]
    metadata = {
        "scope": result["scope"],
        "schema": result["schema"], "kind": result["kind"],
        "footnote": FOOTNOTE,
        "envelope_mm": result["envelope_mm"],
        "camera": {
            "projection": "orthographic (fixed)",
            "views": {k: {"elev_deg": v[0], "azim_deg": v[1]} for k, v in VIEWS.items()},
            "box_aspect": [1, 1, 1],
            "limits_mm": {"x": [-LIM_XY, LIM_XY], "y": [-LIM_XY, LIM_XY], "z": list(LIM_Z)},
            "z_shift": "per-surface minimum z subtracted before display",
            "identical_scale": True,
        },
        "images": images,
        "input_sha256": {str(p.relative_to(ROOT)): _sha_file(p) for p in input_paths},
        "panels": panels,
        "rejected_seeds": [{"seed": r["seed"], "reason": r["rejection_reason"]} for r in rejected],
    }
    (EVIDENCE / "sheet_metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(f"rendered {len(accepted)} accepted/{len(rejected)} rejected seeds")
    for name, rel in images.items():
        print(f"  {name}  {rel}")
    print(f"  sheet_metadata.json  docs/evidence/klangfilm_hv_2026-11-16/sheet_metadata.json")


if __name__ == "__main__":
    main()
