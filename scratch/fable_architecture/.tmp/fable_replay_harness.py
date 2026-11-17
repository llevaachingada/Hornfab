"""Shared, read-only replay harness for the four FABLE research requests (2026-11-16).

No solver, mesher, GPU, queue or config write. Pure numpy/scipy + hornlab_search imports.
The parity fix for regenerated metrics is the one found in recon: the solver's balloon is a
theta-phi grid, so DI must be recomputed with sin(theta) quadrature (search/evaluate.py
``metrics_from_response`` semantics) before handing a collapsed one-column balloon to
``compute_metrics``. Without it, replay regeneration differs from the stored DI by up to 8 dB.
"""
from __future__ import annotations

import dataclasses
import json
import math
import pathlib
import sys
import warnings

import numpy as np
from scipy.interpolate import PchipInterpolator

warnings.filterwarnings("ignore")

REPO = pathlib.Path(r"C:\Users\hunte\Hrns\hornlab-search")
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from hornlab_search.metrics.compute import compute_metrics
from hornlab_search.metrics.di import di_from_balloon, sin_theta_weights
from hornlab_search.objective import replay as R
from hornlab_search.objective.scalar_v7 import V7Params, objective_v7, resolve_v7_weights
from hornlab_search.objective.scalar_v9 import V9Params, objective_v9, resolve_v9_weights
from hornlab_search.solve.base import spl_from_pressure, theta_deg_from_dirs
from hornlab_search.solve.cache import load_response
from hornlab_search.targets.spec import Target
from hornlab_search.types import MetricSet, Response

# The landscape brief of record (the standard v7 brief, not the 'smooth' variant).
LANDSCAPE_BRIEF = REPO / "examples" / "briefs" / "home_landscape_2026-11-15" / "room_landscape_80x50_700_hf1440_v7.yaml"
LANDSCAPE_CFG = REPO / "examples" / "typologies" / "home_landscape_2026-11-15" / "hl__ext_throat_hvlaw_v7.yaml"
GRID_58 = np.geomspace(350.0, 8000.0, 58)


def json_load(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def brief(path):
    return R.brief_from_config(path)


def brief_file(path):
    """Resolve a standalone brief YAML (target/weights/objective) through the real loader."""
    return R.load_brief_context(path)


def landscape_brief():
    return brief_file(LANDSCAPE_BRIEF)


def metrics_parity(resp: Response, target: Target) -> MetricSet:
    """Regenerate metrics exactly as the solve path did (sin-theta balloon DI).

    ``search/evaluate.metrics_from_response`` collapses the theta-phi balloon to a one-column
    weighted-mean balloon so that ``compute_metrics``' equal-weight DI reproduces the sin(theta)
    weighted DI. Replicated here so a replay can be parity-exact without importing the search
    pipeline. A Fibonacci (equal-area) balloon would not need this; the repo's solver writes a
    theta-phi grid (repeated theta rows), which is what the run/dataset storage carries.
    """
    raw = resp
    has_balloon = resp.spl_balloon_db is not None and resp.balloon_dirs is not None
    if has_balloon:
        dirs = np.asarray(resp.balloon_dirs, dtype=float)
        theta = theta_deg_from_dirs(dirs)
        # theta-phi grid iff theta values repeat (n_phi > 1); equal-area sets do not repeat exactly.
        rounded = np.round(theta, 6)
        is_grid = (resp.meta or {}).get("balloon_grid") is not None or \
            (np.unique(rounded).size < rounded.size)
        if is_grid:
            bal = np.asarray(resp.spl_balloon_db, dtype=float)
            w = sin_theta_weights(theta)
            ax = resp.axis_index
            collapsed = np.empty((bal.shape[0], 1))
            for i in range(bal.shape[0]):
                di = di_from_balloon(bal[i], resp.spl_h_db[i, ax], weights=w)
                collapsed[i, 0] = float(resp.spl_h_db[i, ax]) - di
            raw = dataclasses.replace(resp, spl_balloon_db=collapsed,
                                      balloon_dirs=np.array([[0.0, 0.0, 1.0]]))
    return compute_metrics(raw, target)


def score_v7(metrics: MetricSet, resp: Response | None, target: Target, weights: dict,
             params: V7Params):
    return objective_v7(metrics, resp, True, target, weights, params)


def score_v9(metrics: MetricSet, resp: Response | None, target: Target, weights: dict,
             params: V9Params):
    return objective_v9(metrics, resp, True, target, weights, params)


def replay_exact_v7(run_dir, design_hash, brief_obj=None, target=None, weights=None, params=None):
    """Stored-metrics parity replay (no regeneration): should equal the stored status objective."""
    b = brief_obj or brief(pathlib.Path(run_dir) / "config.yaml")
    res = R.replay_run_dir(run_dir, design_hash, brief=b, regenerate_metrics=False)
    return res


def resp_from_run(run_dir, design_hash):
    d = pathlib.Path(run_dir) / "designs" / design_hash
    if not d.is_dir():
        d = pathlib.Path(run_dir) / "verify" / "designs" / design_hash
    return load_response(d / "response.npz")


def meta_from_run(run_dir, design_hash):
    d = pathlib.Path(run_dir) / "designs" / design_hash
    if not d.is_dir():
        d = pathlib.Path(run_dir) / "verify" / "designs" / design_hash
    s = json_load(d / "status.json")
    return d, s


def _interp_1d(x, a, xnew):
    a = np.asarray(a)
    if np.iscomplexobj(a):
        return (PchipInterpolator(x, a.real, axis=0)(xnew)
                + 1j * PchipInterpolator(x, a.imag, axis=0)(xnew))
    if a.ndim == 1:
        return PchipInterpolator(x, a)(xnew)
    return PchipInterpolator(x, a, axis=0)(xnew)


def select_log_spaced(freqs, n: int) -> np.ndarray:
    """Indices of ``n`` log-spaced points chosen from the stored grid (endpoints included).

    Nearest stored frequency to each of ``n`` log-spaced targets, unique, then topped up by
    the largest log-gap node if two targets collapse onto one node. Deterministic.
    """
    f = np.asarray(freqs, dtype=float)
    if n >= f.size:
        return np.arange(f.size)
    targets = np.geomspace(f[0], f[-1], n)
    lf = np.log(f)
    idx = np.unique([int(np.argmin(np.abs(lf - np.log(t)))) for t in targets])
    if idx.size < n:
        picked = set(int(i) for i in idx)
        order = np.argsort(lf)
        while len(picked) < n:
            gaps = [(lf[order[k + 1]] - lf[order[k]], int(order[k]), int(order[k + 1]))
                    for k in range(order.size - 1)]
            gaps.sort(reverse=True)
            for _g, a, b in gaps:
                if a not in picked:
                    picked.add(a)
                    break
                if b not in picked:
                    picked.add(b)
                    break
        idx = np.array(sorted(picked))
    return idx[:n] if idx.size > n else idx


def interp_response(resp: Response, fnew, *, method: str = "pchip") -> Response:
    """Interpolate a Response onto a new frequency grid.

    ``pchip``: log-frequency PCHIP on every real/complex array; p_h/p_v/p_balloon dropped
    (SPL is the scored quantity, and dropping the pressures makes it explicit that no
    pressure-derived field was used).
    ``rational_pressure``: p_h/p_v are interpolated as complex rational functions on
    log10(f) and the cut SPL arrays are rebuilt with ``spl_from_pressure``; balloon/z stay PCHIP.
    """
    f = np.asarray(resp.freqs_hz, dtype=float)
    x = np.log(f)
    xn = np.log(np.asarray(fnew, dtype=float))
    out = dict(freqs_hz=np.asarray(fnew, dtype=float),
               spl_h_db=None, spl_v_db=None, spl_balloon_db=None, z_throat=None,
               p_h=None, p_v=None, p_balloon=None)
    if method == "pchip":
        out["spl_h_db"] = _interp_1d(x, resp.spl_h_db, xn)
        out["spl_v_db"] = _interp_1d(x, resp.spl_v_db, xn)
        out["spl_balloon_db"] = (None if resp.spl_balloon_db is None
                                 else _interp_1d(x, resp.spl_balloon_db, xn))
        out["z_throat"] = None if resp.z_throat is None else _interp_1d(x, resp.z_throat, xn)
    elif method == "rational_pressure":
        if resp.p_h is None or resp.p_v is None:
            raise ValueError("rational_pressure needs stored p_h and p_v")
        ph = fh_interp_columns(x, resp.p_h, xn)
        pv = fh_interp_columns(x, resp.p_v, xn)
        out["spl_h_db"] = spl_from_pressure(ph)
        out["spl_v_db"] = spl_from_pressure(pv)
        out["spl_balloon_db"] = (None if resp.spl_balloon_db is None
                                 else _interp_1d(x, resp.spl_balloon_db, xn))
        out["z_throat"] = None if resp.z_throat is None else _interp_1d(x, resp.z_throat, xn)
    else:
        raise ValueError(f"unknown interpolation method {method!r}")
    return dataclasses.replace(resp, **out)


def _fh_weights(t, d=3):
    """Floater-Hormann barycentric weights of order d (no poles, exact at the nodes)."""
    n = t.size
    if n <= d + 1:
        d = max(0, n - 1)
    w = np.zeros(n)
    for k in range(n):
        lo = max(0, k - d)
        hi = min(k, n - d - 1)
        s = 0.0
        for i in range(lo, hi + 1):
            prod = 1.0
            for j in range(i, i + d + 1):
                if j != k:
                    prod *= (t[k] - t[j])
            s += ((-1.0) ** i) / prod
        w[k] = s
    return w


def fh_interp_columns(x, y, xnew, d=3):
    """Barycentric rational (Floater-Hormann) interpolation down the axis 0 of ``y``.

    ``x``/``xnew`` are log10(f). One rational interpolant per column; the same node weights
    are shared. Exact at the nodes, and used only inside the retained node span here.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y)
    xnew = np.asarray(xnew, dtype=float)
    w = _fh_weights(x, d=d)
    y2 = y.reshape(x.size, -1)
    diff = xnew[:, None] - x[None, :]
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = w[None, :] / diff                      # (nnew, n)
        terms = ratio[:, :, None] * y2[None, :, :]    # (nnew, n, m)
        out = np.sum(terms, axis=1) / np.sum(ratio, axis=1)[:, None]
    exact = np.isclose(diff, 0.0, atol=1e-12)
    for i in range(xnew.size):
        hit = np.nonzero(exact[i])[0]
        if hit.size:
            out[i] = y2[hit[0]]
    return out.reshape((xnew.size,) + y.shape[1:])


def target_from_record(t: dict) -> Target:
    """Dataset/config target dict -> Target (including v9 profile fields if present)."""
    return Target.from_dict(dict(t))


def load_landscape_runs():
    """The 80x50 / 600x480x480 landscape runs from 2026-11-15 onward (75 runs, 3414 ok rows)."""
    root = REPO / "runs"
    out = []
    import yaml
    for rd in sorted(root.iterdir()):
        cfgp = rd / "config.yaml"
        ndp = rd / "search.ndjson"
        if not rd.is_dir() or not cfgp.is_file() or not ndp.is_file():
            continue
        if rd.name[:8] < "20261115":
            continue
        try:
            cfg = yaml.safe_load(cfgp.read_text(encoding="utf-8"))
        except Exception:
            continue
        tg = cfg.get("target") or {}
        env = (cfg.get("brief") or {}).get("envelope") or {}
        if not (tg.get("coverage_h_deg") == 80 and tg.get("coverage_v_deg") == 50
                and env.get("max_mouth_h_mm") == 480):
            continue
        rows = []
        for line in ndp.read_text(encoding="utf-8").splitlines():
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
        out.append(dict(dir=rd, cfg=cfg, rows=rows))
    return out


if __name__ == "__main__":
    # parity smoke: regenerate screen metrics and compare to stored for every study pair
    import glob
    worst = 0.0
    n = 0
    for S in sorted((REPO / "runs").glob("study-*")):
        sd = S / "screen"
        if not (sd / "config.yaml").is_file():
            continue
        b = brief(sd / "config.yaml")
        for d in sorted((sd / "designs").iterdir()):
            if not d.is_dir() or not (d / "response.npz").is_file():
                continue
            resp = load_response(d / "response.npz")
            m = metrics_parity(resp, b.target)
            stored = json_load(d / "metrics.json")
            di = np.asarray(stored["di_db"], float)
            worst = max(worst, float(np.nanmax(np.abs(di - m.di_db))) if di.shape == m.di_db.shape else float("inf"))
            n += 1
            break
    print("parity smoke: worst regenerated-vs-stored DI across study screen designs:", worst, "n", n)
