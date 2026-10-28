"""One self-contained HTML report for a run directory (08_TASK_PIPELINE section 6).

Physics figures (directivity heatmap, polar overlays, DI, impedance) come from ``hornlab_plots``,
which returns base64 PNG strings; matplotlib is never imported here. Three charts have no
``hornlab_plots`` equivalent (convergence, the stacked term bars, and beamwidth / DI against
frequency with the ``f_break`` / ``f11`` marker lines and the target band the task asks for), so
those are small inline SVGs written by ``_svg_lines`` / ``_svg_stacked``: markup, not a plotting
library. Jinja2 renders the page.

Honesty rules baked in: the noise floor is the first box; a best that did not beat the seed says
so in the first sentence; a pinned parameter is reported as a wrong bound, not as an optimum;
every design shown carries its DI provenance.
"""
from __future__ import annotations

import base64
import html as _html
import json
import logging
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from jinja2 import Environment, select_autoescape
from markupsafe import Markup

from ..config import Config, load_config
from ..constants import BESSEL_J1P_11, C_AIR, KEELE_K
from ..design import families
from ..design.space import Bound
from ..metrics.loudness import Z_HALF, Z_LOADED, horn_loudness
from ..objective import WEIGHTED_KEYS, weighted_terms
from ..search.evaluate import error_kind, mouth_dims_m, read_ndjson
from ..solve import cache as solve_cache
from ..targets.spec import Target
from ..targets.venue import feasibility_report
from ..types import MeshResult

log = logging.getLogger("hornlab_search.report.html")

PNG_DPI = 110
PINNED_FRACTION_FLAG = 0.5
PINNED_WITHIN = 0.02

#: Measured noise-floor inputs (CP-7, docs/CONTINUITY.md entry of 2026-10-13 06:20). value_db None
#: means "not measured yet". The floor is the largest value: today that is the two-solver disagreement
#: (beat vs bempp), which is NOT mesh-limited. A run's run.json may override the list under the key
#: ``noise_floor``.
NOISE_FLOOR_INPUTS = [
    {"name": "solver idempotence (two identical solves)", "value_db": 3.6e-5,
     "source": "CP-7 measured"},
    {"name": "left/right symmetry (max asymmetry)", "value_db": 4e-6,
     "source": "CP-7d measured"},
    {"name": "full domain vs quarter domain (symmetry / mesh)", "value_db": 0.023,
     "source": "CP-7d measured, band up to 3 kHz"},
    {"name": "discretization error at epw = 6 versus epw = 18 (DI)", "value_db": 0.028,
     "source": "CP-7c measured on band 500-2500 Hz only; error above 2.5 kHz NOT measured"},
    {"name": "two solvers: beat (Burton-Miller, LU) vs bempp (STANDARD) on one mesh", "value_db": 0.039,
     "source": "CP-7b measured"},
]

PALETTE = ["#2f6db5", "#c4562b", "#3e8e5a", "#8a5cb5", "#b59a2f", "#4aa3a8", "#a8486b", "#6b6b6b"]
TERM_COLORS = {"cov": "#2f6db5", "rip": "#c4562b", "di": "#3e8e5a", "dislope": "#8a5cb5",
               "flat": "#b59a2f", "load": "#4aa3a8", "penalty": "#a8486b"}


# ------------------------------------------------------------------ small helpers


def _uri(b64: str) -> str:
    return "data:image/png;base64," + b64


def _fmt(x, nd=3) -> str:
    if x is None:
        return "n/a"
    try:
        x = float(x)
    except (TypeError, ValueError):
        return str(x)
    if not math.isfinite(x):
        return "n/a"
    return f"{x:.{nd}g}" if abs(x) < 1e-3 or abs(x) >= 1e5 else f"{x:.{nd}f}".rstrip("0").rstrip(".")


def _nan(x) -> np.ndarray:
    return np.array([np.nan if v is None else v for v in x], dtype=float)


def _svg_lines(series, *, width=620, height=250, xlabel="", ylabel="", xlog=False, vlines=(),
               band=None, hlines=(), title="", ylim=None) -> str:
    """Inline-SVG line chart. series: dicts with x, y, label, color, step (bool), dash (bool),
    points (bool). vlines: (x, label, color). band: (x0, x1) shaded. hlines: (y, label, color)."""
    ml, mr, mt, mb = 52, 12, 22, 40
    pw, ph = width - ml - mr, height - mt - mb
    xs, ys = [], []
    for s in series:
        x = np.asarray(s["x"], float)
        y = np.asarray(s["y"], float)
        k = np.isfinite(x) & np.isfinite(y) & ((x > 0) if xlog else True)
        s["_x"], s["_y"] = x[k], y[k]
        xs.extend(s["_x"].tolist())
        ys.extend(s["_y"].tolist())
    xs += [v[0] for v in vlines if np.isfinite(v[0]) and (v[0] > 0 or not xlog)]
    ys += [h[0] for h in hlines if np.isfinite(h[0])]
    if not xs or not ys:
        return '<p class="muted">(no finite data to plot)</p>'
    x0, x1 = min(xs), max(xs)
    if band:
        x0, x1 = min(x0, band[0]), max(x1, band[1])
    y0, y1 = (ylim if ylim else (min(ys), max(ys)))
    if y1 - y0 < 1e-12:
        y0, y1 = y0 - 1.0, y1 + 1.0
    pad = 0.06 * (y1 - y0)
    if not ylim:
        y0, y1 = y0 - pad, y1 + pad
    tx = (lambda v: math.log10(v)) if xlog else (lambda v: v)
    a0, a1 = tx(x0), tx(x1)
    if a1 - a0 < 1e-12:
        a0, a1 = a0 - 1, a1 + 1

    def X(v):
        return ml + (tx(v) - a0) / (a1 - a0) * pw

    def Y(v):
        return mt + (1 - (v - y0) / (y1 - y0)) * ph

    o = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{_html.escape(title or ylabel)}" '
         f'xmlns="http://www.w3.org/2000/svg" class="chart">']
    if band:
        o.append(f'<rect x="{X(band[0]):.1f}" y="{mt}" width="{X(band[1]) - X(band[0]):.1f}" '
                 f'height="{ph}" fill="#2f6db5" opacity="0.08"/>')
    for i in range(5):                                         # y grid + labels
        v = y0 + (y1 - y0) * i / 4
        o.append(f'<line x1="{ml}" x2="{ml + pw}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="#8884" />')
        o.append(f'<text x="{ml - 5}" y="{Y(v) + 4:.1f}" text-anchor="end" class="tick">{_fmt(v, 3)}</text>')
    if xlog:
        ticks = [t for t in (100, 200, 500, 1000, 2000, 5000, 10000, 20000) if x0 * 0.9 <= t <= x1 * 1.1]
    else:
        ticks = [x0 + (x1 - x0) * i / 5 for i in range(6)]
    for t in ticks:
        o.append(f'<line x1="{X(t):.1f}" x2="{X(t):.1f}" y1="{mt}" y2="{mt + ph}" stroke="#8882"/>')
        o.append(f'<text x="{X(t):.1f}" y="{mt + ph + 14}" text-anchor="middle" class="tick">'
                 f'{_fmt(t, 4)}</text>')
    for v, lab, col in vlines:
        if np.isfinite(v) and (v > 0 or not xlog):
            o.append(f'<line x1="{X(v):.1f}" x2="{X(v):.1f}" y1="{mt}" y2="{mt + ph}" stroke="{col}" '
                     f'stroke-dasharray="5 3"/><text x="{X(v) + (-3 if X(v) > ml + pw - 28 else 3):.1f}" '
                     f'y="{mt + 11}" text-anchor="{"end" if X(v) > ml + pw - 28 else "start"}" '
                     f'class="tick" fill="{col}">{_html.escape(lab)}</text>')
    for v, lab, col in hlines:
        if np.isfinite(v):
            o.append(f'<line x1="{ml}" x2="{ml + pw}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="{col}" '
                     f'stroke-dasharray="6 3"/><text x="{ml + pw - 2}" y="{Y(v) - 3:.1f}" '
                     f'text-anchor="end" class="tick" fill="{col}">{_html.escape(lab)}</text>')
    for k, s in enumerate(series):
        col = s.get("color") or PALETTE[k % len(PALETTE)]
        x, y = s["_x"], s["_y"]
        if x.size == 0:
            continue
        if s.get("step"):
            pts = []
            for i in range(x.size):
                if i:
                    pts.append(f"{X(x[i]):.1f},{Y(y[i - 1]):.1f}")
                pts.append(f"{X(x[i]):.1f},{Y(y[i]):.1f}")
        else:
            pts = [f"{X(a):.1f},{Y(b):.1f}" for a, b in zip(x, y)]
        dash = ' stroke-dasharray="4 3"' if s.get("dash") else ""
        o.append(f'<polyline fill="none" stroke="{col}" stroke-width="1.8"{dash} points="{" ".join(pts)}"/>')
        if s.get("points"):
            for a, b in zip(x, y):
                o.append(f'<circle cx="{X(a):.1f}" cy="{Y(b):.1f}" r="2.2" fill="{col}"/>')
    o.append(f'<text x="{ml + pw / 2}" y="{height - 4}" text-anchor="middle" class="axl">'
             f'{_html.escape(xlabel)}</text>')
    o.append(f'<text x="12" y="{mt + ph / 2}" text-anchor="middle" class="axl" '
             f'transform="rotate(-90 12 {mt + ph / 2})">{_html.escape(ylabel)}</text>')
    o.append("</svg>")
    leg = "".join(f'<span class="key"><i style="background:{s.get("color") or PALETTE[k % len(PALETTE)]}">'
                  f'</i>{_html.escape(s["label"])}</span>'
                  for k, s in enumerate(series) if s.get("label"))
    return "".join(o) + (f'<div class="legend">{leg}</div>' if leg else "")


def _svg_stacked(rows, keys, *, width=620) -> str:
    """Horizontal stacked bars. rows: [(label, {key: value})]."""
    if not rows:
        return ""
    lab_w, bar_h, gap = 150, 20, 8
    mx = max(sum(max(v.get(k, 0.0), 0.0) for k in keys) for _, v in rows) or 1.0
    pw = width - lab_w - 60
    h = len(rows) * (bar_h + gap) + 10
    o = [f'<svg viewBox="0 0 {width} {h}" xmlns="http://www.w3.org/2000/svg" class="chart" '
         f'role="img" aria-label="objective term breakdown">']
    for i, (lab, v) in enumerate(rows):
        y = 5 + i * (bar_h + gap)
        o.append(f'<text x="{lab_w - 6}" y="{y + 14}" text-anchor="end" class="tick">{_html.escape(lab)}</text>')
        x = lab_w
        for k in keys:
            w = max(v.get(k, 0.0), 0.0) / mx * pw
            if w > 0:
                o.append(f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="{bar_h}" '
                         f'fill="{TERM_COLORS.get(k, "#888")}"><title>{k} = {_fmt(v.get(k))}</title></rect>')
                x += w
        o.append(f'<text x="{x + 4:.1f}" y="{y + 14}" class="tick">{_fmt(sum(max(v.get(k, 0.0), 0) for k in keys))}</text>')
    o.append("</svg>")
    leg = "".join(f'<span class="key"><i style="background:{TERM_COLORS.get(k, "#888")}"></i>{k}</span>'
                  for k in keys)
    return "".join(o) + f'<div class="legend">{leg}</div>'


# ------------------------------------------------------------------ data gathering


def _load_cfg(run_dir: Path) -> Config | None:
    p = run_dir / "config.yaml"
    if p.exists():
        try:
            return load_config(p)
        except Exception as exc:  # noqa: BLE001
            log.warning("cannot load %s: %s", p, exc)
    return None


def _bounds(cfg: Config | None) -> dict:
    if cfg is None:
        return {}
    return {k: Bound(float(b["lo"]), float(b["hi"]), bool(b.get("search", True)),
                     bool(b.get("log", False))) for k, b in cfg.bounds_raw.items()}


def _unit(bounds: dict, family: str, params: dict, key: str):
    b = bounds[key]
    if not b.search or b.hi == b.lo:
        return None
    try:
        v = float(families.param_get(family, params, key))
    except Exception:  # noqa: BLE001
        return None
    return b.to_unit(v)[0]


def _msg_group(err: str) -> tuple[str, str]:
    kind = error_kind(err)
    body = err.split(":", 1)[1].strip() if ":" in err else err
    first = body.splitlines()[0] if body else ""
    return kind, re.sub(r"\d+(\.\d+)?", "#", first)[:110]


def noise_floor(run: dict) -> dict:
    items = run.get("noise_floor") or NOISE_FLOOR_INPUTS
    vals = [i["value_db"] for i in items if i.get("value_db") is not None]
    floor = max(vals) if vals else None
    which = next((i for i in items if i.get("value_db") == floor), None) if floor is not None else None
    return {"items": items, "floor_db": floor, "limiting": which,
            "complete": all(i.get("value_db") is not None for i in items)}


def _design_figures(run_dir: Path, row: dict, target: Target, family: str, bounds: dict) -> dict:
    """PNG figures and SVG charts for one design. Never raises: a missing response gives a note."""
    import hornlab_plots as hp
    out = {"pngs": [], "svgs": [], "note": "", "loud": ""}
    r = None
    try:
        r = solve_cache.load_response(run_dir / "designs" / row["design_hash"] / "response.npz")
    except Exception as exc:  # noqa: BLE001
        out["note"] = f"response.npz not available ({type(exc).__name__}); curves drawn from stored metrics only"
    m = row.get("metrics")
    f = _nan(m["freqs_hz"]) if m else (r.freqs_hz if r is not None else np.array([]))
    f_break = (m or {}).get("scalars", {}).get("f_break_h_hz"), (m or {}).get("scalars", {}).get("f_break_v_hz")
    f11 = (m or {}).get("scalars", {}).get("f11_hz")
    vl = []
    for v, lab, col in ((f_break[0], "f_break H", "#c4562b"), (f_break[1], "f_break V", "#a8486b"),
                        (f11, "f11", "#3e8e5a")):
        if v is not None and np.isfinite(v):
            vl.append((float(v), lab, col))
    band = (target.band_lo_hz, target.band_hi_hz)
    if m:
        out["svgs"].append(("Beamwidth (-6 dB, total included angle)", _svg_lines(
            [{"x": f, "y": _nan(m["bw_h_deg"]), "label": "horizontal", "color": PALETTE[0], "points": True},
             {"x": f, "y": _nan(m["bw_v_deg"]), "label": "vertical", "color": PALETTE[1], "points": True}],
            xlabel="frequency (Hz)", ylabel="degrees", xlog=True, vlines=vl, band=band,
            hlines=[(target.coverage_h_deg, "target H", PALETTE[0]),
                    (target.coverage_v_deg, "target V", PALETTE[1])], title="beamwidth")))
        sl = m.get("scalars", {}).get("di_slope_db_per_dec")
        di_t = target.di_target_db
        if di_t is None:
            from ..objective.terms import di_target
            di_t = di_target(target)
        out["svgs"].append((f"Directivity index (source: {m['di_source']}; slope "
                            f"{_fmt(sl)} dB/decade, target {_fmt(target.di_slope_target)})", _svg_lines(
            [{"x": f, "y": _nan(m["di_db"]), "label": "DI", "color": PALETTE[2], "points": True}],
            xlabel="frequency (Hz)", ylabel="dB", xlog=True, vlines=vl, band=band,
            hlines=[(di_t, "target DI", PALETTE[2])], title="directivity index")))
    if r is not None:
        try:
            ax = r.axis_index
            hn = (r.spl_h_db - r.spl_h_db[:, ax:ax + 1]).T            # (angles, freqs)
            vn = (r.spl_v_db - r.spl_v_db[:, ax:ax + 1]).T
            tf = np.geomspace(max(target.band_lo_hz, f.min()), min(target.band_hi_hz, f.max()), 4)
            out["pngs"].append(("Directivity heatmap, horizontal (dB re on-axis; -6 dB contour)",
                                _uri(hp.directivity_heatmap_b64(r.freqs_hz, r.h_angles_deg, hn, dpi=PNG_DPI,
                                                                title="horizontal"))))
            out["pngs"].append(("Directivity heatmap, vertical",
                                _uri(hp.directivity_heatmap_b64(r.freqs_hz, r.v_angles_deg, vn, dpi=PNG_DPI,
                                                                title="vertical"))))
            out["pngs"].append(("Horizontal polar overlay at " + ", ".join(f"{x:.0f}" for x in tf) + " Hz",
                                _uri(hp.polar_line_b64(r.freqs_hz, r.h_angles_deg, r.spl_h_db, tf,
                                                       dpi=PNG_DPI, title="horizontal polar"))))
            out["pngs"].append(("Vertical polar overlay",
                                _uri(hp.polar_line_b64(r.freqs_hz, r.v_angles_deg, r.spl_v_db, tf,
                                                       dpi=PNG_DPI, title="vertical polar"))))
            if m:
                out["pngs"].append(("Directivity index (hornlab_plots)",
                                    _uri(hp.directivity_index_b64(r.freqs_hz, _nan(m["di_db"]), dpi=PNG_DPI))))
            if r.z_throat is not None:
                # P12 (2026-10-27): report-only horn loudness, docs/DRIVER_MODEL.md; never in J.
                ld = horn_loudness(r, f0_hz=target.f0_effective_hz())
                lv = np.asarray(ld["onaxis_db_per_mps"], dtype=float)
                lv_max = float(np.max(lv[np.isfinite(lv)])) if np.isfinite(lv).any() else float("nan")
                out["svgs"].append(("Throat loading: output vs a fully loaded throat for the same throat "
                                    "motion (10 log10 Re z, dB; horn only, before any driver)", _svg_lines(
                    [{"x": ld["freqs_hz"], "y": ld["loading_db"], "label": "10 log10 Re z", "color": PALETTE[3],
                      "points": True}],
                    xlabel="frequency (Hz)", ylabel="dB", xlog=True, vlines=vl, band=band,
                    hlines=[(10 * math.log10(Z_LOADED), "Re z 0.7", PALETTE[0]),
                            (10 * math.log10(Z_HALF), "Re z 0.5", PALETTE[1])], title="throat loading")))
                out["loud"] = (f"loudness (report-only, horn only): output gap at f0 "
                               f"{_fmt(ld['output_gap_at_f0_db'], 1)} dB &middot; loaded (Re z >= 0.5) from "
                               f"{_fmt(ld['f_loaded_hz'], 0)} Hz &middot; on-axis level per 1 m/s throat velocity "
                               f"at 1 m: {_fmt(lv_max, 1)} dB max &middot; "
                               f"driven source area {_fmt(ld['throat_area_m2'] * 1e6, 0)} mm2 "
                               f"(throat shape vs driver exit: tools/loudness_report.py)")
                z = np.asarray(r.z_throat)
                out["pngs"].append(("Throat impedance, normalized by rho*c",
                                    _uri(hp.impedance_b64(r.freqs_hz, z.real, z.imag, dpi=PNG_DPI,
                                                          ylabel="Z / (rho c)"))))
        except Exception as exc:  # noqa: BLE001 - one bad figure must not sink the report
            log.warning("figures for %s failed: %s", row["design_hash"], exc)
            out["note"] += f" figure error: {type(exc).__name__}: {exc}"
    return out


# ------------------------------------------------------------------ template

_TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>hornlab-search report {{ run_id }}</title>
<style>
:root{--bg:#fff;--fg:#1c2330;--muted:#5b6678;--card:#f5f7fa;--line:#d5dbe4;--warn:#fff4e0;--warnline:#e0a13a;--bad:#fde8e8;--badline:#c0392b;--good:#e7f5ec;--goodline:#2e8b57}
@media (prefers-color-scheme: dark){:root{--bg:#14181f;--fg:#e4e8ef;--muted:#9aa5b8;--card:#1d232d;--line:#334;--warn:#3a2f17;--warnline:#c8902f;--bad:#3a1d1d;--badline:#d9534f;--good:#173324;--goodline:#3fae75}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,Segoe UI,sans-serif}
main{max-width:980px;margin:0 auto;padding:16px}
h1{font-size:1.5rem;margin:.2em 0}h2{font-size:1.15rem;margin:1.6em 0 .5em;border-bottom:1px solid var(--line);padding-bottom:.2em}h3{font-size:1rem;margin:1.2em 0 .4em}
.muted{color:var(--muted)}.box{border:1px solid var(--line);background:var(--card);border-radius:8px;padding:12px 14px;margin:.8em 0}
.warn{background:var(--warn);border-color:var(--warnline)}.bad{background:var(--bad);border-color:var(--badline)}.good{background:var(--good);border-color:var(--goodline)}
table{display:block;overflow-x:auto;max-width:100%;border-collapse:collapse;width:100%;font-size:.9rem;margin:.4em 0}th,td{border:1px solid var(--line);padding:3px 7px;text-align:right;white-space:nowrap}th:first-child,td:first-child{text-align:left}th{background:var(--card)}
td.l{text-align:left}code,.mono{font-family:ui-monospace,Consolas,monospace;font-size:.85em}
.chart{width:100%;height:auto}.chart .tick{font:10px sans-serif;fill:var(--muted)}.chart .axl{font:11px sans-serif;fill:var(--muted)}
.legend{font-size:.8rem;color:var(--muted);margin:2px 0 8px}.key{margin-right:12px;white-space:nowrap}.key i{display:inline-block;width:10px;height:10px;margin-right:4px;border-radius:2px}
img{max-width:100%;height:auto;border:1px solid var(--line);border-radius:4px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:10px}
.big{font-size:1.25rem}.pin{color:var(--badline);font-weight:600}
pre{background:var(--card);border:1px solid var(--line);padding:8px;overflow:auto;font-size:.8rem}
</style></head><body><main>
<h1>hornlab-search report</h1>
<p class="muted">run <span class="mono">{{ run_id }}</span> &middot; config <b>{{ config_name }}</b> ({{ family }}) &middot; mode <b>{{ mode }}</b> &middot; {{ created }}</p>

<!-- 2. the noise floor, at the top, in a box -->
<div class="box warn" id="noise-floor"><b>Noise floor: {{ nf.floor_txt }}</b>
<p>The largest of the measured solver / mesh / discretization disagreements is the smallest difference this tool can resolve. <b>No claimed improvement smaller than this number means anything.</b>
The floor is set by the two-solver disagreement, not by mesh refinement. Caveat: the epw = 6 discretization error was measured only on 500-2500 Hz; its error above 2.5 kHz is <b>not measured</b>.
{% if not nf.complete %}Some inputs are not measured yet, so the true floor is at least this large.{% endif %}</p>
<table><tr><th>source of disagreement</th><th>dB</th><th>from</th></tr>
{% for i in nf['items'] %}<tr><td>{{ i.name }}</td><td>{{ i.val }}</td><td class="l">{{ i.source }}</td></tr>{% endfor %}</table>
<p class="muted">CMA-ES stops on <code>tolfun = {{ tolfun }}</code> (objective units). It should sit above the objective-space equivalent of the floor above; that conversion is not measured, so judge it against the repeat-solve scatter of J. The objective is not in dB, so a final-objective gap this small is a tie.</p></div>

<!-- 5. the honest summary line -->
<div class="box {{ summary.cls }}" id="summary"><span class="big">{{ summary.headline }}</span><br>{{ summary.detail }}</div>

<h2>Run</h2>
<table>
<tr><td>evaluations</td><td>{{ stats.rows }} rows ({{ stats.new }} computed, {{ stats.cached }} cache hits)</td></tr>
<tr><td>failures</td><td>{{ stats.failed }} ({{ stats.failed_pct }}%)</td></tr>
<tr><td>total GPU solve time</td><td>{{ stats.solve_s }} s; mesh {{ stats.mesh_s }} s</td></tr>
<tr><td>throughput</td><td>{{ stats.per_candidate }} s/candidate, {{ stats.cph }} candidates/hour &rarr; 1,000 evaluations = {{ stats.h1k }} h, 10,000 = {{ stats.h10k }} h</td></tr>
<tr><td>machine</td><td class="l">{{ machine }}</td></tr>
<tr><td>backend</td><td class="l">{{ backend }}</td></tr>
{% for k, v in lib_shas.items() %}<tr><td>{{ k }}</td><td class="mono">{{ v }}</td></tr>{% endfor %}
</table>

<!-- 3. feasibility -->
<h2>Feasibility</h2>
<div class="box {{ feas.cls }}" id="feasibility"><p>{{ feas.note }}</p>
<table><tr><th></th><th>needed (m)</th><th>seed (m)</th><th>best (m)</th></tr>
<tr><td>mouth width (H)</td><td>{{ feas.need_h }}</td><td>{{ feas.seed_h }}</td><td>{{ feas.best_h }}</td></tr>
<tr><td>mouth height (V)</td><td>{{ feas.need_v }}</td><td>{{ feas.seed_v }}</td><td>{{ feas.best_v }}</td></tr></table>
<p class="muted">needed = {{ keele }} / (f_low &times; coverage), with f_low = {{ band_lo }} Hz and coverage the TOTAL included angle (Hughes / Keele). A design check, never a constraint on the search. Actual sizes are the outer bounding box of the solved mesh and include the shell.</p></div>

<!-- 4. convergence -->
<h2>Convergence</h2>
{{ convergence }}

<!-- 6. term breakdown -->
<h2>Objective term breakdown</h2>
<p class="muted">Weighted terms (weight &times; raw term), seed and the top designs. Lower is better.</p>
{{ term_bars }}
<table><tr><th>design</th><th>J</th>{% for k in term_keys %}<th>{{ k }} raw</th>{% endfor %}<th>n_nan</th><th>DI source</th></tr>
{% for d in designs %}<tr><td>{{ d.label }} <span class="mono">{{ d.hash }}</span></td><td>{{ d.J }}</td>{% for k in term_keys %}<td>{{ d.raw[k] }}</td>{% endfor %}<td>{{ d.n_nan }}</td><td>{{ d.di_source }}</td></tr>{% endfor %}</table>

<!-- 7. per design -->
<h2>Designs</h2>
{% for d in designs %}
<h3>{{ d.label }} <span class="mono">{{ d.hash }}</span> &mdash; J = {{ d.J }}, DI source: {{ d.di_source }}{% if d.di_source == 'cuts_estimate' %} <span class="pin">(ESTIMATE)</span>{% endif %}</h3>
<table><tr><th>parameter</th><th>value</th><th>lo</th><th>hi</th><th>fraction of range</th></tr>
{% for p in d.params %}<tr><td>{{ p.key }}</td><td>{{ p.value }}</td><td>{{ p.lo }}</td><td>{{ p.hi }}</td><td>{{ p.frac }}</td></tr>{% endfor %}</table>
<p class="muted">f_break (H, V) = {{ d.f_break }} Hz &middot; f11 = {{ d.f11 }} Hz &middot; mouth ~ {{ d.mouth }} m &middot; {{ d.n_dof }} dofs</p>
<p class="muted">report-only (not in J): SPDI band mean {{ d.spdi }} dB, range {{ d.spdi_range }} dB &middot; listening window re on-axis {{ d.lw }} dB &middot; forward beam shape p = {{ d.beam_p }} (2 round, ~4 rounded square; qualitative at screen balloon resolution)</p>
{% if d.loud %}<p class="muted">{{ d.loud }}</p>{% endif %}
{% if d.note %}<p class="muted">{{ d.note }}</p>{% endif %}
{% for title, svg in d.svgs %}<h4>{{ title }}</h4>{{ svg }}{% endfor %}
<div class="grid">{% for title, uri in d.pngs %}<figure style="margin:0"><img alt="{{ title }}" src="{{ uri }}"><figcaption class="muted">{{ title }}</figcaption></figure>{% endfor %}</div>
{% endfor %}

<!-- 8. bounds -->
<h2>Bounds report</h2>
<p>For each searchable key: how often the top {{ bounds.k }} designs sat within {{ bounds.within }}% of a bound. <b>A pinned parameter means the bound is wrong, not that the answer is optimal.</b></p>
<table><tr><th>key</th><th>lo</th><th>hi</th><th>seed</th><th>best</th><th>at lo</th><th>at hi</th><th></th></tr>
{% for r in bounds.rows %}<tr><td>{{ r.key }}</td><td>{{ r.lo }}</td><td>{{ r.hi }}</td><td>{{ r.seed }}</td><td>{{ r.best }}</td><td>{{ r.at_lo }}</td><td>{{ r.at_hi }}</td><td class="l">{% if r.pinned %}<span class="pin">PINNED &mdash; widen this bound</span>{% endif %}</td></tr>{% endfor %}</table>

<!-- 9. failures -->
<h2>Failures</h2>
{% if failures %}<table><tr><th>reason</th><th>message (digits masked)</th><th>count</th></tr>
{% for f in failures %}<tr><td>{{ f.kind }}</td><td class="l">{{ f.msg }}</td><td>{{ f.n }}</td></tr>{% endfor %}</table>
{% if stats.failed_pct_num >= 50 %}<div class="box bad">{{ stats.failed_pct }}% of the evaluations failed: the search explored far less of the space than the budget suggests.</div>{% endif %}
{% else %}<p>No failed evaluations.</p>{% endif %}

{% if verify %}<h2>Verification (re-solved at verify fidelity)</h2>
<table><tr><th>design</th><th>screen J</th><th>verify J</th></tr>
{% for v in verify %}<tr><td class="mono">{{ v.hash }}</td><td>{{ v.screen }}</td><td>{{ v.verify }}</td></tr>{% endfor %}</table>{% endif %}

<!-- 10. DI provenance -->
<h2>DI provenance</h2>
<table><tr><th>design</th><th>di_source</th></tr>{% for d in designs %}<tr><td>{{ d.label }} <span class="mono">{{ d.hash }}</span></td><td>{{ d.di_source }}</td></tr>{% endfor %}</table>
<p class="muted">{{ di_counts }}. No checkpoint may be passed on a cuts_estimate DI.</p>

<!-- 11. dataset -->
<h2>Dataset</h2>
<div class="box {{ dataset.cls }}">{{ dataset.text }}{% if dataset.warning %}<br><b>WARNING: {{ dataset.warning }}</b>{% endif %}</div>

<!-- 12. reproduction -->
<h2>Reproduction</h2>
<pre>{{ repro }}</pre>
</main></body></html>
"""

_ENV = Environment(autoescape=select_autoescape(["html"], default=True))


# ------------------------------------------------------------------ build


def build_report(run_dir, out=None, top_n: int = 5, *, store=None, figures: bool = True) -> Path:
    """Render ``run_dir`` to one HTML file and return its path. Never fails on an empty or
    all-failed run: it says so."""
    run_dir = Path(run_dir)
    run = json.loads((run_dir / "run.json").read_text(encoding="utf-8")) if (run_dir / "run.json").exists() else {}
    cfg = _load_cfg(run_dir)
    rows = read_ndjson(run_dir / "search.ndjson")
    target = Target.from_dict(cfg.target_raw) if cfg else Target(75.0, 45.0, 700.0, 5000.0, None)
    weights = dict(cfg.weights) if cfg else {}
    bounds = _bounds(cfg)
    family = (cfg.family if cfg else run.get("family")) or (rows[0]["family"] if rows else "?")
    ok_rows = [r for r in rows if r.get("ok")]
    new_rows = [r for r in rows if not r.get("cached")]
    seed_row = rows[0] if rows else None
    if run.get("seed") and rows:
        seed_row = next((r for r in rows if r["design_hash"] == run["seed"]["design_hash"]), rows[0])
    best_row = min(ok_rows, key=lambda r: r["objective"]) if ok_rows else None

    # ---- unique ranking, top N (+ seed shown separately)
    seen, ranked = set(), []
    for r in sorted(ok_rows, key=lambda r: r["objective"]):
        if r["design_hash"] not in seen:
            seen.add(r["design_hash"])
            ranked.append(r)
    show = []
    if seed_row is not None:
        show.append(("seed", seed_row))
    for i, r in enumerate(ranked[:top_n], start=1):
        show.append((f"top {i}", r))

    # ---- summary
    summary = _summary(seed_row, best_row, rows)

    # ---- stats
    n_fail = sum(1 for r in rows if not r.get("ok"))
    solve_s = sum(float((r.get("seconds") or {}).get("solve") or 0.0) for r in new_rows)
    mesh_s = sum(float((r.get("seconds") or {}).get("mesh") or 0.0) for r in new_rows)
    tot_s = [float((r.get("seconds") or {}).get("total") or 0.0) for r in new_rows]
    per = (sum(tot_s) / len(tot_s)) if tot_s else float("nan")
    cph = 3600.0 / per if per and math.isfinite(per) and per > 0 else float("nan")
    stats = {"rows": len(rows), "new": len(new_rows), "cached": len(rows) - len(new_rows),
             "failed": n_fail, "failed_pct": _fmt(100.0 * n_fail / len(rows), 3) if rows else "0",
             "failed_pct_num": 100.0 * n_fail / len(rows) if rows else 0.0,
             "solve_s": _fmt(solve_s, 4), "mesh_s": _fmt(mesh_s, 3), "per_candidate": _fmt(per, 3),
             "cph": _fmt(cph, 3), "h1k": _fmt(1000 / cph if cph == cph and cph > 0 else float("nan"), 3),
             "h10k": _fmt(10000 / cph if cph == cph and cph > 0 else float("nan"), 3)}

    # ---- noise floor
    nf = noise_floor(run)
    nf_view = {"floor_txt": "not yet measured" if nf["floor_db"] is None else
               f"{_fmt(nf['floor_db'], 3)} dB (limited by: {nf['limiting']['name']})",
               "complete": nf["complete"],
               "items": [{"name": i["name"], "val": _fmt(i.get("value_db"), 3),
                          "source": i.get("source", "")} for i in nf["items"]]}

    # ---- feasibility
    feas = _feasibility(target, seed_row, best_row)

    # ---- convergence + terms
    convergence = _convergence(rows, seed_row)
    designs = _designs(show, run_dir, target, weights, bounds, family, figures)
    term_rows = [(f"{d['label']} {d['hash'][:6]}", d["weighted"]) for d in designs]
    term_bars = _svg_stacked(term_rows, list(WEIGHTED_KEYS) + ["penalty"]) if designs else \
        '<p class="muted">no designs to show</p>'

    # ---- bounds
    bounds_view = _bounds_report(ok_rows, ranked, top_n, bounds, family, seed_row, best_row)

    # ---- failures
    groups = Counter(_msg_group(r["error"]) for r in rows if not r.get("ok") and r.get("error"))
    failures = [{"kind": k, "msg": m, "n": n} for (k, m), n in groups.most_common()]

    # ---- verify
    verify = []
    vrows = read_ndjson(run_dir / "verify" / "search.ndjson")
    if vrows:
        screen = {r["design_hash"]: r for r in rows}
        verify = [{"hash": v["design_hash"], "screen": _fmt(screen.get(v["design_hash"], {}).get("objective"), 4),
                   "verify": _fmt(v["objective"], 4)} for v in vrows]

    # ---- DI provenance and dataset
    di_counts = Counter((r.get("metrics") or {}).get("di_source", "n/a") for r in ok_rows)
    di_text = "DI source over all successful evaluations: " + (
        ", ".join(f"{k} = {n}" for k, n in sorted(di_counts.items())) or "none")
    dataset = _dataset_view(run, store, new_rows)

    machine = " | ".join(f"{k}: {v}" for k, v in (run.get("toolchain") or {}).items()
                         if k in ("gpu", "cpu", "os", "driver"))
    lib = run.get("lib_shas") or {}
    repro = _repro(run, cfg)

    tmpl = _ENV.from_string(_TEMPLATE)
    html_text = tmpl.render(
        run_id=run.get("run_id", run_dir.name), config_name=run.get("config_name", "?"), family=family,
        mode=run.get("mode", "?"), created=run.get("created_utc", ""), nf=nf_view,
        tolfun=_fmt(cfg.search.tolfun if cfg else None, 3), summary=summary, stats=stats,
        machine=machine or "n/a", backend=run.get("backend", "n/a"), lib_shas=lib, feas=feas,
        keele=f"{KEELE_K:g}", band_lo=_fmt(target.band_lo_hz, 5), convergence=Markup(convergence),
        term_bars=Markup(term_bars), term_keys=list(WEIGHTED_KEYS), designs=designs,
        bounds=bounds_view, failures=failures, verify=verify, di_counts=di_text, dataset=dataset,
        repro=repro)
    out = Path(out) if out is not None else run_dir / "report.html"
    out.write_text(html_text, encoding="utf-8")
    return out


def _summary(seed_row, best_row, rows) -> dict:
    if not rows:
        return {"cls": "bad", "headline": "No evaluations in this run.",
                "detail": "search.ndjson is empty or missing."}
    if best_row is None:
        return {"cls": "bad", "headline": "No evaluation succeeded.",
                "detail": f"All {len(rows)} evaluations failed; see the failure table. The seed did "
                          "not even produce a score, so there is nothing to compare."}
    seed_ok = seed_row is not None and seed_row.get("ok")
    if not seed_ok:
        return {"cls": "warn", "headline": f"Best objective {_fmt(best_row['objective'], 5)}; the seed itself failed.",
                "detail": f"Seed: {seed_row.get('error', '')[:160] if seed_row else 'missing'}. There is no "
                          "baseline to measure an improvement against."}
    s, b = float(seed_row["objective"]), float(best_row["objective"])
    imp = 100.0 * (s - b) / s if s > 0 else 0.0
    if b >= s - 1e-12:
        return {"cls": "bad",
                "headline": "The search did NOT improve on the seed.",
                "detail": f"Best objective {_fmt(b, 5)} vs seed {_fmt(s, 5)} (the seed is the best design found). "
                          "This is a result: within this budget nothing beat the starting design."}
    return {"cls": "good",
            "headline": f"Best objective {_fmt(b, 5)} vs seed {_fmt(s, 5)}: {_fmt(imp, 3)}% lower.",
            "detail": f"Best found at evaluation {best_row.get('n')} of {len(rows)}. Lower is better. "
                      "Check the noise floor above before trusting a small difference."}


def _feasibility(target: Target, seed_row, best_row) -> dict:
    fr = feasibility_report(target)

    def dims(row):
        if not row or row.get("bbox_m") is None:
            return None, None
        m = MeshResult("", 0, None, row.get("quadrants") or "", row.get("symmetry_plane"), {},
                       tuple(row["bbox_m"]), 0.0)
        return mouth_dims_m(m)

    sh, sv = dims(seed_row)
    bh, bv = dims(best_row)
    fits = [(d is None or d >= need * 0.999) for d, need in ((sh, fr["mouth_h_m"]), (sv, fr["mouth_v_m"]))]
    note = fr["note"]
    if sh is not None:
        short = [n for n, ok in (("width", fits[0]), ("height", fits[1])) if not ok]
        note += (" The seed mouth is too small to hold the target to the band edge in "
                 + " and ".join(short) + ": expect pattern control to be lost below the break frequency, "
                 "and a search cannot fix that without a bigger mouth." if short else
                 " The seed mouth is large enough in both axes.")
    return {"note": note, "cls": "warn" if sh is not None and not all(fits) else "",
            "need_h": _fmt(fr["mouth_h_m"], 3), "need_v": _fmt(fr["mouth_v_m"], 3),
            "seed_h": _fmt(sh, 3), "seed_v": _fmt(sv, 3), "best_h": _fmt(bh, 3), "best_v": _fmt(bv, 3)}


def _convergence(rows, seed_row) -> str:
    if not rows:
        return '<p class="muted">no data</p>'
    n = np.arange(len(rows))
    J = np.array([r["objective"] if r.get("ok") else np.nan for r in rows], float)
    best = np.minimum.accumulate(np.where(np.isfinite(J), J, np.inf))
    best[~np.isfinite(best)] = np.nan
    series = [{"x": n, "y": J, "label": "evaluation", "color": "#9aa5b8", "points": True},
              {"x": n, "y": best, "label": "running best", "color": PALETTE[0], "step": True}]
    hl = []
    if seed_row and seed_row.get("ok"):
        hl.append((float(seed_row["objective"]), "seed", PALETTE[1]))
    finite = J[np.isfinite(J)]
    ylim = None
    if finite.size:
        top = float(np.percentile(finite, 90)) * 1.1
        ylim = (0.0, max(top, float(np.nanmax(best)) * 1.5 if np.isfinite(best).any() else top))
    return _svg_lines(series, xlabel="evaluation number (failures not drawn)", ylabel="objective J",
                      hlines=hl, ylim=ylim, title="convergence")


def _designs(show, run_dir, target, weights, bounds, family, figures) -> list[dict]:
    out = []
    for label, row in show:
        terms = row.get("terms") or {}
        wt = weighted_terms(terms, weights)
        m = row.get("metrics") or {}
        sc = m.get("scalars") or {}
        keys = sorted(bounds)
        params = []
        for k in keys:
            b = bounds[k]
            try:
                v = families.param_get(family, row["params"], k)
            except Exception:  # noqa: BLE001
                continue
            frac = _unit(bounds, family, row["params"], k)
            params.append({"key": k, "value": _fmt(v, 5) if isinstance(v, (int, float)) else str(v),
                           "lo": _fmt(b.lo, 5), "hi": _fmt(b.hi, 5),
                           "frac": "fixed" if not b.search else (_fmt(frac, 3) if frac is not None else "n/a")})
        d = {"label": label, "hash": row["design_hash"], "J": _fmt(row["objective"], 5),
             "raw": {k: _fmt(terms.get(k), 4) for k in WEIGHTED_KEYS}, "weighted": wt,
             "n_nan": int(terms.get("n_nan", 0) or 0), "di_source": m.get("di_source", "n/a"),
             "params": params, "n_dof": row.get("n_dof"),
             "f_break": f"{_fmt(sc.get('f_break_h_hz'), 4)}, {_fmt(sc.get('f_break_v_hz'), 4)}",
             "f11": _fmt(sc.get("f11_hz"), 4),
             "spdi": _fmt(sc.get("spdi_mean_db"), 3), "spdi_range": _fmt(sc.get("spdi_range_db"), 3),
             "lw": _fmt(sc.get("lw_minus_on_axis_mean_db"), 3), "beam_p": _fmt(sc.get("beam_p_mean"), 3),
             "mouth": "n/a", "pngs": [], "svgs": [], "note": "", "loud": ""}
        if row.get("bbox_m"):
            mw, mh = mouth_dims_m(MeshResult("", 0, None, row.get("quadrants") or "",
                                             row.get("symmetry_plane"), {}, tuple(row["bbox_m"]), 0.0))
            d["mouth"] = f"{mw:.3f} x {mh:.3f}"
        if figures and row.get("ok"):
            f = _design_figures(run_dir, row, target, family, bounds)
            d["pngs"], d["svgs"], d["note"] = f["pngs"], [(t, Markup(s)) for t, s in f["svgs"]], f["note"]
            d["loud"] = Markup(f.get("loud", ""))
        out.append(d)
    return out


def _bounds_report(ok_rows, ranked, top_n, bounds, family, seed_row, best_row) -> dict:
    k = max(top_n, int(math.ceil(0.1 * len(ranked)))) if ranked else 0
    top = ranked[:k]
    rows = []
    for key in sorted(bounds):
        b = bounds[key]
        if not b.search:
            continue
        at_lo = at_hi = 0
        for r in top:
            u = _unit(bounds, family, r["params"], key)
            if u is None:
                continue
            at_lo += u <= PINNED_WITHIN
            at_hi += u >= 1.0 - PINNED_WITHIN
        pinned = bool(top) and max(at_lo, at_hi) / len(top) >= PINNED_FRACTION_FLAG

        def val(row):
            if row is None:
                return "n/a"
            try:
                return _fmt(families.param_get(family, row["params"], key), 5)
            except Exception:  # noqa: BLE001
                return "n/a"
        rows.append({"key": key, "lo": _fmt(b.lo, 5), "hi": _fmt(b.hi, 5), "seed": val(seed_row),
                     "best": val(best_row), "at_lo": f"{at_lo}/{len(top)}", "at_hi": f"{at_hi}/{len(top)}",
                     "pinned": pinned})
    return {"k": k, "within": int(PINNED_WITHIN * 100), "rows": rows}


def _dataset_view(run: dict, store, new_rows) -> dict:
    s = None
    try:
        if store is None and run.get("dataset_dir") and Path(run["dataset_dir"]).is_dir():
            from ..dataset.store import DatasetStore
            store = DatasetStore(Path(run["dataset_dir"]))
        if store is not None:
            s = store.stats()
    except Exception as exc:  # noqa: BLE001
        log.warning("dataset stats unavailable: %s", exc)
    frac = run.get("trace_fraction")
    if s is None:
        return {"cls": "", "warning": None,
                "text": f"{len(new_rows)} records written by this run; dataset directory not available "
                        f"to the report. Trace sampling fraction {_fmt(frac)}."}
    text = (f"{len(new_rows)} records written by this run; cumulative {s['n']} records "
            f"({s['n_ok']} ok, {s['n_failed']} failed), {s['disk_mb']:.1f} MB on disk. "
            f"Trace fraction configured {_fmt(frac)}, measured {100 * s['trace_fraction']:.1f}%. "
            f"Family balance: {s['family_balance']}.")
    return {"cls": "warn" if s["family_warning"] else "", "text": text, "warning": s["family_warning"]}


def _repro(run: dict, cfg) -> str:
    lines = []
    if run.get("command"):
        lines.append("command:    " + str(run["command"]))
    lines.append(f"config:     {run.get('config_path') or 'config.yaml in the run directory'}")
    lines.append(f"config sha: {run.get('config_sha', 'n/a')}")
    lines.append(f"cma seed:   {run.get('cma_seed', 'n/a')}   mode: {run.get('mode', 'n/a')}   "
                 f"budget: {run.get('budget', 'n/a')}")
    for k, v in (run.get("lib_shas") or {}).items():
        lines.append(f"{k:18s} {v}")
    return "\n".join(lines)
