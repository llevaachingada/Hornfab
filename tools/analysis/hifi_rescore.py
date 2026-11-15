"""hifi_rescore.py - offline DSP-aware / passive "hi-fi" re-score of stored designs (NO GPU, NO solver).

Background and evidence: ``docs/research/ONAXIS_WEIGHTING_2026-11-14.md``. Objective v7 scores on-axis
response at 0 deg only (``flat`` from band_lo, i.e. BELOW the crossover; ``flat_cv`` XO-3 kHz) and does
not separate what an equaliser can fix from what it cannot. This tool re-scores every stored valid
design from its ``designs/<hash>/response.npz`` (73-angle H/V cuts + balloon) with CTA-2034-style
curves and two scoring modes:

* ``dsp``  : J_dsp = J_v7 - (flat + flat_cv contributions) + the NON-EQ-able terms below.
  The playback chain is assumed to EQ the listening window (LW) flat, so only what differs from
  seat to seat, the in-room shape relative to the LW, and fine roughness the EQ will not chase count.
* ``passive``: J_passive = J_dsp + ``lw_shape`` (broad LW deviation a passive network must absorb).

Curves (unit-VELOCITY levels: the stored unit-acceleration SPL + 20 log10 f, i.e. driver-like):
  LW  = energy mean of 0 deg, V +-10, H +-10/20/30 (CTA-2034 listening window)
  ER  = energy mean of floor (V -20..-40), ceiling (V +40..+60), front wall (H 0..+-30),
        side walls (H +-40..+-80), rear (H +-90: the solved cuts stop at +-90 deg, an approximation)
  SP  = energy mean of the balloon directions
  PIR = 0.12 LW + 0.44 ER + 0.44 SP (energy), CTA-2034's predicted in-room response

Raw hi-fi terms over [F_X, band_hi] (F_X = the brief's f0, the crossover):
  ``seat_spread_db`` - per frequency, the std across the 9 LW curves of (curve - LW), after removing
      each curve's own mean offset (its fixed taper); averaged over frequency. Seat-to-seat
      coloration: an LW EQ cannot fix it. (NOT EQ-able)
  ``xo_spread_db``   - the same restricted to [F_X, 1.6 F_X]: the directivity hand-off at the crossover.
  ``pir_shape_db``   - residual std of (PIR - LW) about a straight line vs log2 f: once the LW is
      EQ'd flat, how lumpy the in-room / reverberant balance is (a smooth DI). (NOT EQ-able)
  ``lw_rough_db``    - residual std of LW about a CUBIC in log2 f (a broad 1-2 octave EQ removes the
      cubic): fine roughness the EQ will not chase. (Mostly NOT EQ-able in practice)
  ``lw_shape_db``    - residual std of LW about a straight line: the broad shape (EQ-able; scored only
      in ``passive`` mode).

Tolerances are DATA-CALIBRATED per brief group (as v8 did): the median raw value over the top decile
of that group's designs ranked by stored J_v7. Default weights: seat 1.0, xo 0.5, pir 1.0, rough 0.5,
shape 1.0 (passive only). Nothing here changes any objective or brief.

    .venv\\Scripts\\python.exe tools\\analysis\\hifi_rescore.py --run runs\\<a> --run runs\\<b> ... \\
        --out scratch\\hifi_rescore_<date> [--verify] [--top 20]

``--verify`` reads ``<run>/verify/`` (search.ndjson + designs) instead of the screen rows; verify grids
are finer (6 points/octave), so verify scores are the better evidence when they exist.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import add_out_arg, fail, read_ndjson, read_yaml  # noqa: E402

TOOL = "hifi_rescore"
HIFI_KEYS = ("seat_spread_db", "xo_spread_db", "pir_shape_db", "lw_rough_db", "lw_shape_db")
DEFAULT_WEIGHTS = {"seat_spread_db": 1.0, "xo_spread_db": 0.5, "pir_shape_db": 1.0,
                   "lw_rough_db": 0.5, "lw_shape_db": 1.0}
DSP_KEYS = ("seat_spread_db", "xo_spread_db", "pir_shape_db", "lw_rough_db")
PASSIVE_KEYS = DSP_KEYS + ("lw_shape_db",)
XO_SPAN = 1.6
ANGLE_TOL = 1.3          # deg: a requested angle must be on the solved grid (2.5 deg spacing)


# ----------------------------------------------------------------------------- curves

def _e_avg(curves: list[np.ndarray]) -> np.ndarray:
    return 10.0 * np.log10(np.mean([10.0 ** (c / 10.0) for c in curves], axis=0))


def _pick(angles: np.ndarray, spl: np.ndarray, a: float) -> np.ndarray:
    i = int(np.argmin(np.abs(angles - a)))
    if abs(float(angles[i]) - a) > ANGLE_TOL:
        raise ValueError(f"angle {a} deg is not on the solved grid (nearest {angles[i]})")
    return spl[:, i]


def spin_curves(freqs, h_angles, spl_h, v_angles, spl_v, spl_balloon) -> dict:
    """CTA-2034-style curves in unit-velocity dB. Arrays: spl_* are (n_freq, n_angle/n_dir)."""
    f = np.asarray(freqs, dtype=float)
    vel = 20.0 * np.log10(f)[:, None]
    ha, va = np.asarray(h_angles, float), np.asarray(v_angles, float)
    sh = np.asarray(spl_h, float) + vel
    sv = np.asarray(spl_v, float) + vel
    sb = np.asarray(spl_balloon, float) + vel
    H = lambda a: _pick(ha, sh, a)  # noqa: E731
    V = lambda a: _pick(va, sv, a)  # noqa: E731
    members = [H(0), V(10), V(-10)] + [H(s * a) for a in (10, 20, 30) for s in (1, -1)]
    lw = _e_avg(members)
    floor = _e_avg([V(-a) for a in (20, 30, 40)])
    ceil = _e_avg([V(a) for a in (40, 50, 60)])
    front = _e_avg([H(s * a) for a in (0, 10, 20, 30) for s in (1, -1)])
    side = _e_avg([H(s * a) for a in (40, 50, 60, 70, 80) for s in (1, -1)])
    rear = _e_avg([H(90), H(-90)])
    er = _e_avg([floor, ceil, front, side, rear])
    sp = _e_avg([sb[:, j] for j in range(sb.shape[1])])
    pir = 10.0 * np.log10(0.12 * 10 ** (lw / 10) + 0.44 * 10 ** (er / 10) + 0.44 * 10 ** (sp / 10))
    return {"f": f, "on": H(0), "lw": lw, "lw_members": members, "er": er, "sp": sp, "pir": pir}


def _resid_std(x: np.ndarray, y: np.ndarray, deg: int) -> float:
    deg = min(deg, x.size - 2)
    if deg < 1:
        return float("nan")
    c = np.polyfit(x, y, deg)
    return float(np.std(y - np.polyval(c, x)))


def _spread(curves: dict, sel: np.ndarray) -> float:
    if int(sel.sum()) < 2:
        return float("nan")
    dev = np.array([m[sel] - curves["lw"][sel] for m in curves["lw_members"]])
    dev = dev - dev.mean(axis=1, keepdims=True)
    return float(np.mean(np.std(dev, axis=0)))


def hifi_terms(curves: dict, f_lo: float, f_hi: float) -> dict:
    """Raw hi-fi terms over [f_lo, f_hi] (dB). NaN when fewer than 3 frequencies fall in the band."""
    f = curves["f"]
    sel = (f >= f_lo) & (f <= f_hi) & np.isfinite(curves["lw"])
    out = {k: float("nan") for k in HIFI_KEYS}
    if int(sel.sum()) < 3:
        return out
    x = np.log2(f[sel])
    out["seat_spread_db"] = _spread(curves, sel)
    out["xo_spread_db"] = _spread(curves, sel & (f <= XO_SPAN * f_lo))
    out["pir_shape_db"] = _resid_std(x, (curves["pir"] - curves["lw"])[sel], 1)
    out["lw_rough_db"] = _resid_std(x, curves["lw"][sel], 3)
    out["lw_shape_db"] = _resid_std(x, curves["lw"][sel], 1)
    return out


# ----------------------------------------------------------------------------- scoring

def onaxis_contribution(terms: dict, weights: dict) -> float:
    """What v7's two 0-deg terms add to J (stored terms are already raw/tol)."""
    return sum(float(weights.get(k, 0.0)) * float(terms.get(k) or 0.0) for k in ("flat", "flat_cv"))


def calibrate_tolerances(items: list[dict], frac: float = 0.10, n_min: int = 3) -> dict:
    """Median raw value of each hi-fi term over the top decile by J_v7 (floor 0.05 dB)."""
    ranked = sorted(items, key=lambda r: r["J_v7"])
    top = ranked[:max(n_min, math.ceil(len(ranked) * frac))]
    tol = {}
    for k in HIFI_KEYS:
        vals = [r["hifi"][k] for r in top if math.isfinite(r["hifi"][k])]
        tol[k] = max(0.05, float(np.median(vals))) if vals else 1.0
    return tol


def score(item: dict, tol: dict, weights: dict, keys: tuple) -> float:
    total = item["J_v7"] - item["onaxis_v7"]
    for k in keys:
        v = item["hifi"][k]
        if not math.isfinite(v):
            return float("inf")
        total += weights[k] * v / tol[k]
    return float(total)


def _spearman(a, b) -> float:
    a, b = np.asarray(a, float), np.asarray(b, float)
    if a.size < 3:
        return float("nan")
    ra, rb = np.argsort(np.argsort(a)), np.argsort(np.argsort(b))
    return float(np.corrcoef(ra, rb)[0, 1])


# ----------------------------------------------------------------------------- IO

def collect(run_dir: Path, use_verify: bool) -> tuple[list[dict], str]:
    base = run_dir / "verify" if use_verify else run_dir
    cfg = read_yaml(run_dir / "config.yaml") or {}
    brief = cfg.get("brief") if isinstance(cfg.get("brief"), dict) else {}
    target = cfg.get("target") or {}
    weights = cfg.get("weights") or {}
    f_lo = float(target.get("f0_hz") or target.get("band_lo_hz") or 0.0)
    f_hi = float(target.get("band_hi_hz") or 20000.0)
    rows = read_ndjson(base / "search.ndjson") if (base / "search.ndjson").is_file() else []
    items, seen = [], set()
    for r in rows:
        if not r.get("ok") or r.get("objective") is None or r.get("design_hash") in seen:
            continue
        npz = base / "designs" / str(r["design_hash"]) / "response.npz"
        if not npz.is_file():
            continue
        z = np.load(npz, allow_pickle=True)
        try:
            curves = spin_curves(z["freqs_hz"], z["h_angles_deg"], z["spl_h_db"], z["v_angles_deg"],
                                 z["spl_v_db"], z["spl_balloon_db"])
        except (KeyError, ValueError):
            continue
        seen.add(r["design_hash"])
        items.append({"run": run_dir.name, "design": r["design_hash"], "J_v7": float(r["objective"]),
                      "onaxis_v7": onaxis_contribution(r.get("terms") or {}, weights),
                      "n_freq": int(curves["f"].size), "hifi": hifi_terms(curves, f_lo, f_hi)})
    group = f"v{rows[0].get('objective_version') if rows else '?'}:{brief.get('name') or cfg.get('brief_file') or '?'}"
    return items, group


def analyse(items: list[dict], weights: dict, top: int) -> dict:
    tol = calibrate_tolerances(items)
    for it in items:
        it["J_dsp"] = score(it, tol, weights, DSP_KEYS)
        it["J_passive"] = score(it, tol, weights, PASSIVE_KEYS)
    ok = [it for it in items if math.isfinite(it["J_dsp"]) and math.isfinite(it["J_passive"])]
    jv = [it["J_v7"] for it in ok]
    rank_v7 = {it["design"]: i + 1 for i, it in enumerate(sorted(ok, key=lambda r: r["J_v7"]))}
    out = {"n": len(ok), "tolerances": tol, "weights": weights}
    for mode in ("dsp", "passive"):
        key = f"J_{mode}"
        order = sorted(ok, key=lambda r: r[key])
        top_v7 = {it["design"] for it in sorted(ok, key=lambda r: r["J_v7"])[:top]}
        top_m = [it["design"] for it in order[:top]]
        out[mode] = {
            "spearman_vs_v7": _spearman(jv, [it[key] for it in ok]),
            f"top{top}_overlap": len(top_v7 & set(top_m)),
            "v7_best_rank": 1 + [it["design"] for it in order].index(
                min(ok, key=lambda r: r["J_v7"])["design"]) if ok else None,
            "top": [{"design": it["design"], "run": it["run"], key: it[key], "J_v7": it["J_v7"],
                     "v7_rank": rank_v7[it["design"]], **it["hifi"]} for it in order[:top]],
        }
    # shares of the dsp score at the top decile (is any one term dominating?)
    dec = sorted(ok, key=lambda r: r["J_dsp"])[:max(3, math.ceil(len(ok) * 0.1))]
    share = defaultdict(float)
    for it in dec:
        share["v7_rest"] += (it["J_v7"] - it["onaxis_v7"]) / it["J_dsp"]
        for k in DSP_KEYS:
            share[k] += weights[k] * it["hifi"][k] / tol[k] / it["J_dsp"]
    out["dsp_top_decile_share"] = {k: v / len(dec) for k, v in share.items()}
    return out


def to_md(payload: dict) -> str:
    L = [f"# Hi-fi re-score ({payload['source']})", "",
         "Offline, no GPU. Method and evidence: `docs/research/ONAXIS_WEIGHTING_2026-11-14.md`.", ""]
    for g, res in payload["groups"].items():
        L += [f"## {g} - {res['n']} designs", "",
              "Calibrated tolerances (top-decile median by J_v7): "
              + ", ".join(f"`{k}` {v:.3f}" for k, v in res["tolerances"].items()), "",
              "| mode | Spearman vs J_v7 | top-N overlap | v7 #1 ranks |", "|---|---:|---:|---:|"]
        for m in ("dsp", "passive"):
            r = res[m]
            ov = [v for k, v in r.items() if k.startswith("top") and k.endswith("_overlap")][0]
            L.append(f"| {m} | {r['spearman_vs_v7']:+.2f} | {ov} | {r['v7_best_rank']} |")
        L += ["", "Share of J_dsp in its own top decile: "
              + ", ".join(f"`{k}` {v:.0%}" for k, v in res["dsp_top_decile_share"].items()), ""]
        for m in ("dsp", "passive"):
            L += [f"### Top designs under `{m}`", "",
                  "| # | design | run | J_" + m + " | J_v7 | v7 rank | seat | xo | pir | rough | shape |",
                  "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
            for i, t in enumerate(res[m]["top"], 1):
                L.append(f"| {i} | `{t['design']}` | {t['run'][-6:]} | {t['J_' + m]:.3f} | {t['J_v7']:.3f} | "
                         f"{t['v7_rank']} | {t['seat_spread_db']:.2f} | {t['xo_spread_db']:.2f} | "
                         f"{t['pir_shape_db']:.2f} | {t['lw_rough_db']:.2f} | {t['lw_shape_db']:.2f} |")
            L.append("")
    return "\n".join(L) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run", action="append", required=True, help="run dir (repeatable)")
    ap.add_argument("--verify", action="store_true", help="score <run>/verify instead of the screen rows")
    ap.add_argument("--top", type=int, default=20)
    add_out_arg(ap)
    a = ap.parse_args(argv)
    out = Path(a.out)
    parts = [p.lower() for p in out.resolve().parts]
    if "runs" in parts and "analysis" not in parts[parts.index("runs") + 1:parts.index("runs") + 2]:
        raise fail("--out must not be inside runs/ (use scratch/ or runs/analysis/...)")
    groups: dict[str, list[dict]] = defaultdict(list)
    for rd in a.run:
        p = Path(rd)
        if not (p / "config.yaml").is_file():
            raise fail(f"{p} is not a run dir (no config.yaml)")
        items, g = collect(p, a.verify)
        groups[g].extend(items)
    payload = {"tool": TOOL, "source": "verify" if a.verify else "screen", "runs": a.run, "groups": {}}
    for g, items in groups.items():
        if len(items) < 3:
            print(f"{TOOL}: group {g} has {len(items)} usable design(s); skipped", file=sys.stderr)
            continue
        payload["groups"][g] = analyse(items, dict(DEFAULT_WEIGHTS), a.top)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{TOOL}.json").write_text(json.dumps(payload, indent=1, default=float), encoding="utf-8")
    (out / f"{TOOL}.md").write_text(to_md(payload), encoding="utf-8")
    print(f"{TOOL} OK: {sum(r['n'] for r in payload['groups'].values())} design(s) in "
          f"{len(payload['groups'])} group(s) -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
