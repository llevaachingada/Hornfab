"""One self-contained HTML report + summary.json + a plain-text verdict table for an A/B ``Comparison``."""
from __future__ import annotations

import html
import json
from pathlib import Path

import numpy as np

from . import charts
from .analysis import Comparison
from .conventions import check_conventions

BADGE = {"pass": "PASS", "warn": "WARN", "fail": "FAIL", "n/a": "n/a"}


def _fmt(x, nd=2):
    return "-" if x is None else f"{x:.{nd}f}"


def verdict_text(cmp: Comparison, findings: list[dict]) -> str:
    bands = [b for b, *_ in cmp.bands]
    w = max(len(m.title) for m in cmp.metrics.values()) if cmp.metrics else 20
    lines = [f"A/B VERDICT: {cmp.overall.upper()}   A = {cmp.label_a}   B = {cmp.label_b}",
             "Tolerances are starting points for a sanity check, not standards. Cells: verdict max|d|/rms (unit of the row).",
             "", f"{'metric':<{min(w, 70)}}  {'tol':>6}  " + "  ".join(f"{b:>16}" for b in bands) + "  overall"]
    for k, m in cmp.metrics.items():
        cells = []
        for b in bands:
            s = m.stats[b]
            cells.append(f"{BADGE[m.verdicts[b]]} {_fmt(s['max_abs'])}/{_fmt(s['rms'])}" if s["n"] else "n/a")
        lines.append(f"{m.title[:70]:<{min(w, 70)}}  {m.tol:>6g}  " + "  ".join(f"{c:>16}" for c in cells) + f"  {BADGE[m.overall]}")
    if findings:
        lines += ["", "LIKELY CAUSES (convention / unit checker):"]
        lines += [f" - [{f['likelihood']}] {f['code']}: {f['message']}" for f in findings]
    elif cmp.overall in ("fail", "warn"):
        lines += ["", "No known convention mistake explains the differences (see docs/ab/BOUNDARY_LAB_AB.md, section on failures)."]
    if cmp.notes:
        lines += ["", "NOTES:"] + [f" - {n}" for n in cmp.notes]
    lines += ["", f"DI source: A {cmp.a.di_source}, B {cmp.b.di_source}. Alignment: {cmp.info['note']} "
                  f"({cmp.info['n_common']} common frequencies, {cmp.info['overlap_hz'][0]:g}-{cmp.info['overlap_hz'][1]:g} Hz)."]
    return "\n".join(lines) + "\n"


def _charts(cmp: Comparison, backend: str) -> list[tuple[str, list[str]]]:
    f = cmp.freqs
    sec: list[tuple[str, list[str]]] = []
    A, B = cmp.label_a, cmp.label_b
    c = cmp.curves
    if "on_axis" in c:
        tol = cmp.tolerances.on_axis_db
        sec.append(("On-axis frequency response", [
            charts.line_chart("On-axis SPL (absolute, 1 m/s drive basis)", "Hz", "dB", [
                {"label": A, "x": f, "y": c["on_axis"]["A"], "color": charts.COL_A},
                {"label": B, "x": f, "y": c["on_axis"]["B"], "color": charts.COL_B, "dash": True}], backend=backend),
            charts.line_chart("On-axis difference A - B", "Hz", "dB", [
                {"label": "absolute", "x": f, "y": c["on_axis"]["A"] - c["on_axis"]["B"], "color": charts.COL_D},
                {"label": "shape (band-mean removed)", "x": f, "y": c["on_axis"]["A_shape"] - c["on_axis"]["B_shape"],
                 "color": "#009E73"}], hlines=[-tol, 0, tol], backend=backend)]))
    for plane in ("H", "V"):
        fam = c.get(f"off_axis_{plane}")
        if not fam:
            continue
        ser, dser = [], []
        for i, (ang, (a_, b_)) in enumerate(sorted(fam.items())):
            col = charts.ANGLE_COLORS[i % len(charts.ANGLE_COLORS)]
            ser += [{"label": f"{A} {ang:g}", "x": f, "y": a_, "color": col},
                    {"label": f"{B} {ang:g}", "x": f, "y": b_, "color": col, "dash": True}]
            dser.append({"label": f"{ang:g} deg", "x": f, "y": a_ - b_, "color": col})
        tol = cmp.tolerances.off_axis_db
        sec.append((f"Off-axis, {plane} plane (re on-axis; solid = A, dashed = B)", [
            charts.line_chart(f"{plane} plane at 15/30/45/60/90 deg", "Hz", "dB re on-axis", ser, ylim=(-40, 3), backend=backend),
            charts.line_chart(f"{plane} plane difference A - B", "Hz", "dB", dser, hlines=[-tol, 0, tol], backend=backend)]))
    for plane in ("H", "V"):
        m = cmp.maps.get(plane)
        if not m:
            continue
        ang = m["angles"]
        sec.append((f"{plane} polar map (dB re on-axis)", [
            charts.heat_chart(f"{A}: {plane}", f, ang, m["A"], vmin=-30, vmax=0, backend=backend),
            charts.heat_chart(f"{B}: {plane}", f, ang, m["B"], vmin=-30, vmax=0, backend=backend),
            charts.heat_chart(f"Difference A - B: {plane}", f, ang, m["diff"], vmin=-6, vmax=6, diverging=True, backend=backend)]))
    bw = [(p, c[f"beamwidth_{p}"]) for p in ("H", "V") if f"beamwidth_{p}" in c]
    if bw:
        sec.append(("-6 dB beamwidth", [charts.line_chart(f"{p} beamwidth (180 = no crossing)", "Hz", "deg", [
            {"label": A, "x": f, "y": d["A"], "color": charts.COL_A}, {"label": B, "x": f, "y": d["B"], "color": charts.COL_B, "dash": True}],
            backend=backend) for p, d in bw]))
    if "di" in c:
        tol = cmp.tolerances.di_db
        sec.append((f"Directivity index (A {cmp.a.di_source}, B {cmp.b.di_source})", [
            charts.line_chart("DI", "Hz", "dB", [{"label": A, "x": f, "y": c["di"]["A"], "color": charts.COL_A},
                                                 {"label": B, "x": f, "y": c["di"]["B"], "color": charts.COL_B, "dash": True}], backend=backend),
            charts.line_chart("DI difference A - B", "Hz", "dB", [{"label": "A - B", "x": f, "y": c["di"]["A"] - c["di"]["B"],
                                                                 "color": charts.COL_D}], hlines=[-tol, 0, tol], backend=backend)]))
    bal = cmp.maps.get("balloon")
    if bal and "balloon" in cmp.metrics:
        sec.append(("Balloon", [charts.line_chart("Balloon difference, RMS over the sphere", "Hz", "dB",
                                                  [{"label": "RMS A-B", "x": f, "y": cmp.metrics["balloon"].delta, "color": charts.COL_D}],
                                                  hlines=[cmp.tolerances.balloon_db], backend=backend)]))
    if "phase_axis" in c:
        d = cmp.metrics["phase_axis"].delta
        sec.append(("On-axis phase (propagation delay removed)", [
            charts.line_chart("Phase", "Hz", "deg", [{"label": A, "x": f, "y": c["phase_axis"]["A"], "color": charts.COL_A},
                                                     {"label": B, "x": f, "y": c["phase_axis"]["B"], "color": charts.COL_B, "dash": True}],
                              backend=backend),
            charts.line_chart("Phase difference A - B (wrapped)", "Hz", "deg", [{"label": "A - B", "x": f, "y": d, "color": charts.COL_D}],
                              hlines=[-cmp.tolerances.phase_deg, 0, cmp.tolerances.phase_deg], backend=backend)]))
    if "z" in c:
        z = c["z"]
        sec.append(("Throat impedance (Z / rho c, exp(+i w t))", [
            charts.line_chart("Real part", "Hz", "Z/rho c", [{"label": A, "x": f, "y": z["A"].real, "color": charts.COL_A},
                                                              {"label": B, "x": f, "y": z["B"].real, "color": charts.COL_B, "dash": True}], backend=backend),
            charts.line_chart("Imaginary part", "Hz", "Z/rho c", [{"label": A, "x": f, "y": z["A"].imag, "color": charts.COL_A},
                                                                   {"label": B, "x": f, "y": z["B"].imag, "color": charts.COL_B, "dash": True}], backend=backend)]))
    return sec


_CSS = """
:root{--bg:#fff;--fg:#1b1b1b;--muted:#666;--card:#f6f6f6;--line:#ddd;--pass:#1a7f37;--warn:#9a6700;--fail:#cf222e;--chart-bg:#fff}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#121212;--fg:#e8e8e8;--muted:#a0a0a0;--card:#1c1c1c;--line:#333;--pass:#3fb950;--warn:#d29922;--fail:#f85149;--chart-bg:#1c1c1c}}
:root[data-theme="dark"]{--bg:#121212;--fg:#e8e8e8;--muted:#a0a0a0;--card:#1c1c1c;--line:#333;--pass:#3fb950;--warn:#d29922;--fail:#f85149;--chart-bg:#1c1c1c}
body{background:var(--bg);color:var(--fg);font:15px/1.45 system-ui,sans-serif;margin:0;padding:16px;max-width:1200px;margin-inline:auto}
h1{font-size:22px}h2{font-size:17px;margin-top:28px;border-bottom:1px solid var(--line);padding-bottom:4px}
.banner{padding:12px 16px;border-radius:8px;background:var(--card);border-left:8px solid var(--line);font-size:18px}
.banner.pass{border-color:var(--pass)}.banner.warn{border-color:var(--warn)}.banner.fail{border-color:var(--fail)}
table{border-collapse:collapse;width:100%;font-size:13px}td,th{border:1px solid var(--line);padding:4px 6px;text-align:right}th:first-child,td:first-child{text-align:left}
td.pass{color:var(--pass);font-weight:600}td.warn{color:var(--warn);font-weight:600}td.fail{color:var(--fail);font-weight:600}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(380px,1fr));gap:12px}.grid>*{background:var(--card);padding:6px;border-radius:6px;overflow:hidden}
img,svg{max-width:100%;height:auto}ul{padding-left:20px}code{background:var(--card);padding:1px 4px;border-radius:3px}.muted{color:var(--muted)}
.wrap{overflow-x:auto}
"""


def build_report(cmp: Comparison, out_dir, *, title: str = "Hornfab vs Boundary Lab", provenance: dict | None = None,
                 backend: str = "auto") -> dict:
    """Write ``report.html``, ``summary.json``, ``verdict.txt`` (+ ``comparison_arrays.npz``) into ``out_dir``."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    findings = check_conventions(cmp)
    cmp.conventions = findings
    text = verdict_text(cmp, findings)
    (out / "verdict.txt").write_text(text, encoding="utf-8")
    summ = cmp.to_json()
    summ["provenance"] = provenance or {}
    summ["chart_backend"] = "matplotlib" if backend == "matplotlib" or (backend == "auto" and charts.have_matplotlib()) else "builtin"
    (out / "summary.json").write_text(json.dumps(summ, indent=2, default=float), encoding="utf-8")
    arr = {"freqs_hz": cmp.freqs}
    for k, m in cmp.metrics.items():
        arr[f"delta_{k}"] = np.asarray(m.delta)
    for plane in ("H", "V"):
        if plane in cmp.maps:
            arr.update({f"map_{plane}_A": cmp.maps[plane]["A"], f"map_{plane}_B": cmp.maps[plane]["B"],
                        f"map_{plane}_angles": cmp.maps[plane]["angles"]})
    np.savez_compressed(out / "comparison_arrays.npz", **arr)

    e = html.escape
    bands = [b for b, *_ in cmp.bands]
    rows = ["<tr><th>Metric</th><th>Tol</th>" + "".join(f"<th>{e(b)}</th>" for b in bands) + "<th>Overall</th></tr>"]
    for k, m in cmp.metrics.items():
        cells = ""
        for b in bands:
            s = m.stats[b]
            tip = f"max {_fmt(s['max_abs'])} / rms {_fmt(s['rms'])} / bias {_fmt(s['median'])} (n={s['n']})"
            cells += f"<td class='{m.verdicts[b] if m.verdicts[b] != 'n/a' else ''}' title='{e(tip)}'>{BADGE[m.verdicts[b]]}<br><span class='muted'>{_fmt(s['max_abs'])}/{_fmt(s['rms'])}</span></td>"
        rows.append(f"<tr><td>{e(m.title)}<br><span class='muted'>{e(m.note)}</span></td><td>{m.tol:g} {e(m.unit)}</td>{cells}"
                    f"<td class='{m.overall if m.overall != 'n/a' else ''}'>{BADGE[m.overall]}</td></tr>")
    fnd = "".join(f"<li><b>{e(f['code'])}</b> <span class='muted'>({e(f['likelihood'])})</span>: {e(f['message'])}</li>" for f in findings)
    parts = [f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
             f"<title>A/B check</title><style>{_CSS}</style></head><body>",
             f"<h1>{e(title)}</h1>",
             f"<div class='banner {cmp.overall}'><b>Verdict: {e(cmp.overall.upper())}</b> &nbsp; A = {e(cmp.label_a)} &nbsp; B = {e(cmp.label_b)}"
             f"<br><span class='muted' style='font-size:13px'>Cells show max|d| / rms of A - B. Tolerances are starting points for a sanity check, not standards; "
             f"hover a cell for the bias.</span></div>",
             "<h2>Verdict table</h2><div class='wrap'><table>" + "".join(rows) + "</table></div>"]
    if findings:
        parts.append(f"<h2>Likely causes (convention / unit checker)</h2><ul>{fnd}</ul>")
    elif cmp.overall in ("warn", "fail"):
        parts.append("<h2>Likely causes</h2><p>No known convention mistake explains the differences. See the failure guide in "
                     "<code>docs/ab/BOUNDARY_LAB_AB.md</code>.</p>")
    if cmp.notes:
        parts.append("<h2>Notes</h2><ul>" + "".join(f"<li>{e(n)}</li>" for n in cmp.notes) + "</ul>")
    for name, figs in _charts(cmp, backend):
        parts.append(f"<h2>{e(name)}</h2><div class='grid'>" + "".join(f"<div>{x}</div>" for x in figs) + "</div>")
    parts.append("<h2>Provenance</h2><pre style='white-space:pre-wrap;font-size:12px'>" + e(json.dumps(
        {"alignment": cmp.info, "tolerances": summ["tolerances"], "A": cmp.a.meta.get("reference_meta", {}) and
         {k: v for k, v in cmp.a.meta.items() if k != "reference_meta"} or cmp.a.meta,
         "B": cmp.b.meta, "extra": provenance or {}}, indent=1, default=str)[:20000]) + "</pre></body></html>")
    (out / "report.html").write_text("\n".join(parts), encoding="utf-8")
    return {"overall": cmp.overall, "findings": findings, "out": str(out)}
