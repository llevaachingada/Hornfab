"""Chart rendering for the A/B report: matplotlib PNG (base64) when matplotlib is importable, else a built-in
dependency-free renderer (inline SVG lines, small PNG heat maps written with zlib). Both return an HTML fragment, so
``report`` does not care which one ran. ``backend="builtin"`` forces the fallback (tests).
"""
from __future__ import annotations

import base64
import html
import io
import struct
import zlib

import numpy as np

COL_A = "#0072B2"
COL_B = "#D55E00"
COL_D = "#555555"
ANGLE_COLORS = ("#0072B2", "#009E73", "#CC79A7", "#E69F00", "#56B4E9", "#000000")


def have_matplotlib() -> bool:
    try:
        import matplotlib  # noqa: F401
        return True
    except Exception:
        return False


def _use_mpl(backend: str) -> bool:
    return backend == "matplotlib" or (backend == "auto" and have_matplotlib())


# ------------------------------------------------------------------ matplotlib

def _mpl():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    return plt


def _png_img(fig, alt: str) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
    _mpl().close(fig)
    return (f'<img alt="{html.escape(alt)}" src="data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}">')


def _mpl_lines(title, xlabel, ylabel, series, logx, ylim, hlines):
    plt = _mpl()
    fig, ax = plt.subplots(figsize=(6.6, 3.3))
    for s in series:
        y = np.asarray(s["y"], dtype=float)
        ax.plot(s["x"], y, label=s["label"], color=s.get("color", COL_D), linestyle="--" if s.get("dash") else "-",
                linewidth=s.get("width", 1.4))
    for h in hlines or ():
        ax.axhline(h, color="#999999", linewidth=0.8, linestyle=":")
    if logx:
        ax.set_xscale("log")
    if ylim:
        ax.set_ylim(*ylim)
    ax.set_title(title, fontsize=10)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, which="both", alpha=0.25)
    if len(series) > 1:
        ax.legend(fontsize=7, ncol=2 if len(series) > 4 else 1)
    return _png_img(fig, title)


def _mpl_heat(title, x, y, Z, vmin, vmax, diverging, zlabel):
    plt = _mpl()
    fig, ax = plt.subplots(figsize=(6.6, 3.0))
    m = ax.pcolormesh(x, y, np.asarray(Z).T, shading="auto", cmap="RdBu_r" if diverging else "viridis", vmin=vmin, vmax=vmax)
    ax.set_xscale("log")
    ax.set_title(title, fontsize=10)
    ax.set_xlabel("Hz")
    ax.set_ylabel("angle (deg)")
    fig.colorbar(m, ax=ax, label=zlabel)
    return _png_img(fig, title)


# ------------------------------------------------------------------ built-in renderer

def _nice_ticks(lo, hi, n=5):
    if hi <= lo:
        return [lo]
    step = (hi - lo) / n
    mag = 10 ** np.floor(np.log10(step))
    for m in (1, 2, 5, 10):
        if step <= m * mag:
            step = m * mag
            break
    t0 = np.ceil(lo / step) * step
    return [float(v) for v in np.arange(t0, hi + 0.5 * step, step)]


def _svg_lines(title, xlabel, ylabel, series, logx, ylim, hlines):
    W, H, L, R, T, B = 660, 330, 56, 14, 26, 44
    xs = np.concatenate([np.asarray(s["x"], dtype=float) for s in series])
    ys = np.concatenate([np.asarray(s["y"], dtype=float) for s in series])
    ys = ys[np.isfinite(ys)]
    x0, x1 = float(xs.min()), float(xs.max())
    y0, y1 = ylim if ylim else ((float(ys.min()), float(ys.max())) if ys.size else (0.0, 1.0))
    if y1 - y0 < 1e-9:
        y0, y1 = y0 - 1, y1 + 1
    pad = 0.04 * (y1 - y0)
    y0, y1 = (y0, y1) if ylim else (y0 - pad, y1 + pad)

    def px(v):
        t = (np.log10(v) - np.log10(x0)) / (np.log10(x1) - np.log10(x0)) if logx else (v - x0) / (x1 - x0 or 1)
        return L + t * (W - L - R)

    def py(v):
        return T + (1 - (v - y0) / (y1 - y0)) * (H - T - B)
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{html.escape(title)}" xmlns="http://www.w3.org/2000/svg" '
           f'style="width:100%;height:auto;background:var(--chart-bg,#fff)">',
           f'<text x="{W / 2}" y="16" text-anchor="middle" font-size="12" fill="currentColor">{html.escape(title)}</text>']
    for t in _nice_ticks(y0, y1):
        out.append(f'<line x1="{L}" x2="{W - R}" y1="{py(t):.1f}" y2="{py(t):.1f}" stroke="#8886" stroke-width="0.5"/>'
                   f'<text x="{L - 4}" y="{py(t) + 3:.1f}" text-anchor="end" font-size="9" fill="currentColor">{t:g}</text>')
    if logx:
        d = 10 ** np.floor(np.log10(x0))
        ticks = [m * d * 10 ** k for k in range(0, 8) for m in (1, 2, 5) if x0 <= m * d * 10 ** k <= x1]
    else:
        ticks = _nice_ticks(x0, x1)
    for t in ticks:
        out.append(f'<line x1="{px(t):.1f}" x2="{px(t):.1f}" y1="{T}" y2="{H - B}" stroke="#8886" stroke-width="0.5"/>'
                   f'<text x="{px(t):.1f}" y="{H - B + 12}" text-anchor="middle" font-size="9" fill="currentColor">{t:g}</text>')
    for h in hlines or ():
        if y0 <= h <= y1:
            out.append(f'<line x1="{L}" x2="{W - R}" y1="{py(h):.1f}" y2="{py(h):.1f}" stroke="#999" stroke-dasharray="2 3"/>')
    for s in series:
        x, y = np.asarray(s["x"], dtype=float), np.asarray(s["y"], dtype=float)
        pts = " ".join(f"{px(a):.1f},{py(b):.1f}" for a, b in zip(x, y) if np.isfinite(b))
        dash = ' stroke-dasharray="5 3"' if s.get("dash") else ""
        out.append(f'<polyline fill="none" stroke="{s.get("color", COL_D)}" stroke-width="{s.get("width", 1.4)}"{dash} points="{pts}"/>')
    out.append(f'<text x="{(L + W - R) / 2}" y="{H - 6}" text-anchor="middle" font-size="10" fill="currentColor">{html.escape(xlabel)}</text>')
    out.append(f'<text x="12" y="{(T + H - B) / 2}" font-size="10" fill="currentColor" transform="rotate(-90 12 {(T + H - B) / 2})" '
               f'text-anchor="middle">{html.escape(ylabel)}</text>')
    lx = L + 8
    for i, s in enumerate(series):
        ly = T + 10 + 11 * i
        if i > 9:
            break
        dash = ' stroke-dasharray="5 3"' if s.get("dash") else ""
        out.append(f'<line x1="{lx}" x2="{lx + 18}" y1="{ly}" y2="{ly}" stroke="{s.get("color", COL_D)}" stroke-width="2"{dash}/>'
                   f'<text x="{lx + 22}" y="{ly + 3}" font-size="9" fill="currentColor">{html.escape(str(s["label"]))}</text>')
    out.append("</svg>")
    return "".join(out)


_VIRIDIS = [(0.0, (68, 1, 84)), (0.25, (59, 82, 139)), (0.5, (33, 144, 140)), (0.75, (93, 201, 99)), (1.0, (253, 231, 37))]
_DIVERGING = [(0.0, (33, 102, 172)), (0.5, (247, 247, 247)), (1.0, (178, 24, 43))]


def _cmap(values01: np.ndarray, stops) -> np.ndarray:
    pos = np.array([s[0] for s in stops])
    out = np.empty(values01.shape + (3,), dtype=np.uint8)
    for c in range(3):
        out[..., c] = np.interp(values01, pos, [s[1][c] for s in stops]).astype(np.uint8)
    return out


def _png_bytes(rgb: np.ndarray) -> bytes:
    h, w, _ = rgb.shape
    raw = b"".join(b"\x00" + rgb[i].tobytes() for i in range(h))

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))


def _builtin_heat(title, x, y, Z, vmin, vmax, diverging, zlabel):
    Z = np.asarray(Z, dtype=float).T                       # (n_angle, n_freq)
    t = np.clip((np.nan_to_num(Z, nan=vmin) - vmin) / max(vmax - vmin, 1e-9), 0, 1)
    rgb = _cmap(t[::-1], _DIVERGING if diverging else _VIRIDIS)        # angle increases upward
    rgb = np.repeat(np.repeat(rgb, max(1, 300 // rgb.shape[1] + 1), axis=1), 3, axis=0)
    src = base64.b64encode(_png_bytes(rgb)).decode()
    return (f'<figure style="margin:0"><figcaption style="font-size:12px">{html.escape(title)}</figcaption>'
            f'<img alt="{html.escape(title)}" style="width:100%;image-rendering:pixelated" src="data:image/png;base64,{src}">'
            f'<div style="font-size:11px;opacity:.8">x: {x[0]:g} to {x[-1]:g} Hz (log, left to right); y: {y[0]:g} (bottom) to '
            f'{y[-1]:g} deg (top); colour {vmin:g} to {vmax:g} {html.escape(zlabel)} '
            f'({"blue to red" if diverging else "dark to bright"})</div></figure>')


# ------------------------------------------------------------------ public

def line_chart(title, xlabel, ylabel, series, *, logx=True, ylim=None, hlines=None, backend="auto") -> str:
    series = [s for s in series if s.get("y") is not None]
    if not series:
        return f"<p><em>{html.escape(title)}: no data</em></p>"
    if _use_mpl(backend):
        return _mpl_lines(title, xlabel, ylabel, series, logx, ylim, hlines)
    return _svg_lines(title, xlabel, ylabel, series, logx, ylim, hlines)


def heat_chart(title, x, y, Z, *, vmin, vmax, diverging=False, zlabel="dB", backend="auto") -> str:
    if Z is None:
        return f"<p><em>{html.escape(title)}: no data</em></p>"
    if _use_mpl(backend):
        return _mpl_heat(title, x, y, Z, vmin, vmax, diverging, zlabel)
    return _builtin_heat(title, x, y, Z, vmin, vmax, diverging, zlabel)
