"""Gate A (CPU, read-only): what the 650-900 Hz "loading hump" is, from STORED solves only.

Fable senior, 2026-11-19, follow-up to ../score_term_audit_2026-11-19/REPORT.md. No BEM solve, no
mesher, nothing under runs/ rewritten; outputs go to --out (must be new or empty).

For the six audit designs, on every stored grid (screen and, when present, verify), per frequency:
  * complex throat impedance z (BEM convention exp(-i w t), Im<0 mass-like; also given as the
    engineering conj), |Gamma| = |(z-1)/(z+1)| (plane-wave diagnostic only), load-term pieces;
  * source convention check: the solver drives UNIT NORMAL ACCELERATION (meta.spl_reference), so the
    stored level is converted to unit VELOCITY by +20 log10(w);
  * energy balance: P_rad (balloon, sin-theta quadrature, full sphere at meta.distance_m) vs
    P_in = 1/2 rho c Re(z) |v|^2 S (S = full-model throat area). Ratio ~1 = conventions consistent;
  * a voltage-driven response through hornlab_search.driver.compression.drive() over a BRACKET of
    HF1440-class parameters (FaitalPRO publishes Re 6.8 ohm, 86 mm coil, 35.8 mm exit; it does NOT
    publish Bl, Mmd, Sd, fs, Qms), with and without an ideal 700 Hz 2nd-order Butterworth high pass.
Plus the duplicate-hash census (Gate A item 2) over the v10 rescore rows.
"""
from __future__ import annotations

import argparse
import collections
import csv
import itertools
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from hornlab_search.constants import C_AIR, RHO_AIR  # noqa: E402
from hornlab_search.driver.compression import CompressionDriver, drive  # noqa: E402
from hornlab_search.metrics.loudness import throat_area_m2  # noqa: E402
from hornlab_search.objective.scalar_v7 import _first_crossing_hz  # noqa: E402
from hornlab_search.solve.cache import load_response  # noqa: E402

FX, LOADED_HI = 700.0, 5600.0          # home v10 brief: crossover and loaded_hi_hz
DESIGNS = {                            # label -> (design_hash prefix, run dir of the v10 rescore row)
    "fold_warm_best": ("00826f071b24", "runs/study-0c9805ad97208a2e/screen"),
    "fold_warm_688f": ("688ffe811b6a", "runs/20261116T130335Z-screen-ab4fb9"),
    "morph_v7": ("436a4d221328", "runs/20261115T154322Z-screen-07bea2"),
    "ext_throat_v7": ("a23763f1c6fc", "runs/study-4e1a6a9cd4bb5201/screen"),
    "tritonia_v9": ("3050a4666f51", "runs/study-3ddea3acb9d6fd51/screen"),
    "rosse_rect_cd": ("fd45d3b5e62f", "runs/20261116T150941Z-screen-0e777a"),
}
# Bracket, labelled [inferred]: typical 1.4"-exit / ~3-4" annular-diaphragm compression drivers.
BRACKET = dict(sd_cm2=(30.0, 45.0), mmd_g=(1.5, 3.0), bl_tm=(12.0, 18.0), fs_hz=(450.0, 700.0),
               front_chamber_cm3=(0.0, 3.0))
FIXED = dict(kind="compression", re_ohm=6.8, le_mh=0.05, qms=3.0)


def design_dir(run: Path, prefix: str) -> Path | None:
    dd = run / "designs"
    hits = [p for p in dd.iterdir() if p.name.startswith(prefix)] if dd.is_dir() else []
    return hits[0] if hits else None


def balloon_power(resp) -> np.ndarray:
    """Radiated power per unit throat acceleration, full sphere, peak-amplitude convention."""
    dirs = np.asarray(resp.balloon_dirs, float)
    p = np.asarray(resp.p_balloon)
    th = np.arccos(np.clip(dirs[:, 2], -1, 1))
    w = np.sin(th)
    w = w * (4 * np.pi / w.sum())                  # equal-angle theta-phi grid -> sum = 4 pi
    r = float(resp.meta["distance_m"])
    return (r ** 2) * (np.abs(p) ** 2 @ w) / (2 * RHO_AIR * C_AIR)


def per_freq(resp) -> dict:
    f = np.asarray(resp.freqs_hz, float)
    om = 2 * np.pi * f
    z = np.asarray(resp.z_throat, complex)
    S = throat_area_m2(resp)
    ax = resp.axis_index
    on_acc = 20 * np.log10(np.abs(np.asarray(resp.p_h)[:, ax]) / 20e-6)
    on_vel = on_acc + 20 * np.log10(om)
    p_rad = balloon_power(resp)
    p_in = 0.5 * RHO_AIR * C_AIR * z.real * S / om ** 2
    return dict(f=f, re_z=z.real, im_z_bem=z.imag, im_z_eng=-z.imag,
                gamma=np.abs((z - 1) / (z + 1)), on_acc_db=on_acc, on_vel_db=on_vel,
                pwl_vel_db=10 * np.log10(p_rad * om ** 2), energy_ratio=p_rad / p_in,
                throat_area_m2=np.full(f.shape, S))


def rel(f, y, at, ref=2000.0):
    """y at frequency `at` minus y at `ref`, linear in log f between stored samples."""
    lf = np.log(f)
    return float(np.interp(np.log(at), lf, y) - np.interp(np.log(ref), lf, y))


def detrend_bump(f, y, lo=600.0, hi=3000.0):
    """Max and std of the residual of y vs a straight line in log2 f over [lo, hi] (stored samples)."""
    m = (f >= lo) & (f <= hi)
    if m.sum() < 3:
        return float("nan"), float("nan")
    x = np.log2(f[m])
    res = y[m] - np.polyval(np.polyfit(x, y[m], 1), x)
    return float(res.max()), float(res.std())


def load_pieces(f, re_z):
    lfp20 = _first_crossing_hz(f, re_z, 0.20)
    m = (f >= FX) & (f <= LOADED_HI)
    rez_min = float(re_z[m].min())
    lfp_pen = max(0.0, np.log2(lfp20 * 1.6 / FX)) if lfp20 else float("nan")
    return dict(lfp20_hz=lfp20, rez_min=rez_min, f_rez_min=float(f[m][np.argmin(re_z[m])]),
                lfp_pen=lfp_pen, rez_pen=max(0.0, 0.5 - rez_min),
                load_raw=lfp_pen + max(0.0, 0.5 - rez_min))


def hp2(f, fc=700.0):
    s = 1j * f / fc
    return s ** 2 / (s ** 2 + np.sqrt(2) * s + 1)


def driver_summary(resp):
    rows = []
    keys = list(BRACKET)
    for combo in itertools.product(*BRACKET.values()):
        prm = dict(FIXED, name="bracket", **dict(zip(keys, combo)))
        out = drive(CompressionDriver.from_dict(prm), resp, volts_rms=2.83)
        f = out["freqs_hz"]
        spl = out["spl_onaxis_db"]
        pw = 10 * np.log10(out["acoustic_power_w"])
        spl_hp = spl + 20 * np.log10(np.abs(hp2(f)))
        rows.append(dict(**dict(zip(keys, combo)),
                         on_828_rel_2k=rel(f, spl, 828), on_643_rel_2k=rel(f, spl, 643),
                         pw_828_rel_2k=rel(f, pw, 828),
                         on_bump_max_db=detrend_bump(f, spl)[0], on_bump_std_db=detrend_bump(f, spl)[1],
                         pw_bump_max_db=detrend_bump(f, pw)[0],
                         hp_on_828_rel_2k=rel(f, spl_hp, 828), hp_on_643_rel_2k=rel(f, spl_hp, 643),
                         xmax_mm_700=float(np.interp(np.log(700), np.log(f), out["excursion_mm_peak"])),
                         eff_pct_828=float(np.interp(np.log(828), np.log(f), out["efficiency_pct"]))))
    return rows


def find_verify(prefix: str) -> list[Path]:
    hits = []
    for root, dirs, _ in os.walk(ROOT / "runs"):
        p = Path(root)
        if "analysis" in p.parts or "lanes" in p.parts:
            dirs[:] = []
            continue
        if p.name == "designs":
            hits += [p / d for d in dirs if d.startswith(prefix) and "verify" in p.parts]
            dirs[:] = []
    return hits


def duplicate_census(out: Path) -> dict:
    """Gate A item 2: hashes stored in >1 run dir - same grid/mesh or not, and how far apart."""
    rows = [json.loads(x) for x in open(ROOT / "runs/analysis/v10_rescore_2026-11-18/v10/rescore.jsonl",
                                        encoding="utf-8")]
    hashes = {r["design_hash"] for r in rows if r["j"] is not None}
    loc = collections.defaultdict(list)
    for root, dirs, _ in os.walk(ROOT / "runs"):
        p = Path(root)
        if "analysis" in p.parts or "lanes" in p.parts:
            dirs[:] = []
            continue
        if p.name == "designs":
            for d in dirs:
                if d in hashes and (p / d / "response.npz").exists():
                    loc[d].append(p / d)
            dirs[:] = []
    recs = []
    for h, ds in loc.items():
        if len(ds) < 2:
            continue
        R = [load_response(d / "response.npz") for d in ds]
        same_grid = all(np.array_equal(R[0].freqs_hz, r.freqs_hz) for r in R[1:])
        same_dof = len({r.n_dof for r in R}) == 1
        leaves = [d.parent.parent.name for d in ds]
        rec = dict(design_hash=h, n_dirs=len(ds), dirs=[str(d.relative_to(ROOT)) for d in ds],
                   same_grid=same_grid, same_n_dof=same_dof, n_dof=[r.n_dof for r in R],
                   n_freqs=[len(r.freqs_hz) for r in R], backend=[r.backend for r in R],
                   leaf_names=leaves, leaf_collision=len(set(leaves)) < len(leaves))
        if same_grid:
            dz = max(float(np.max(np.abs(np.asarray(r.z_throat) - np.asarray(R[0].z_throat)))) for r in R[1:])
            ds_ = max(float(np.max(np.abs(np.asarray(r.spl_h_db) - np.asarray(R[0].spl_h_db)))) for r in R[1:])
            rec.update(max_abs_dz=dz, max_abs_dspl_h_db=ds_)
        recs.append(rec)
    (out / "duplicate_hashes.json").write_text(json.dumps(recs, indent=1), encoding="utf-8")
    sg = [r for r in recs if r["same_grid"]]
    return dict(ambiguous=len(recs), same_grid=len(sg),
                same_grid_and_dof=sum(r["same_n_dof"] for r in sg),
                identical=sum(r.get("max_abs_dz", 1) == 0 and r.get("max_abs_dspl_h_db", 1) == 0 for r in sg),
                max_dz_same_grid=max((r["max_abs_dz"] for r in sg), default=None),
                max_dspl_same_grid_db=max((r["max_abs_dspl_h_db"] for r in sg), default=None),
                leaf_collisions=sum(r["leaf_collision"] for r in recs),
                diff_grid_examples=[(r["design_hash"], r["n_freqs"], r["n_dof"]) for r in recs
                                    if not r["same_grid"]][:5])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True)
    out = Path(ap.parse_args().out)
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"refusing: {out} exists and is not empty")
    out.mkdir(parents=True, exist_ok=True)

    summary, csv_rows, drv_rows = {}, [], []
    for label, (prefix, run) in DESIGNS.items():
        dd = design_dir(ROOT / run, prefix)
        grids = [("screen", dd)] + [(f"verify:{p.parent.parent.parent.name}", p) for p in find_verify(prefix)]
        summary[label] = {"design_dir": str(dd.relative_to(ROOT))}
        for gname, gdir in grids:
            resp = load_response(gdir / "response.npz")
            M = json.load(open(gdir / "metrics.json"))
            q = per_freq(resp)
            f = q["f"]
            for i in range(len(f)):
                csv_rows.append({"design": label, "grid": gname, **{k: float(v[i]) for k, v in q.items()},
                                 "di_db": M["di_db"][i], "bw_h_deg": M["bw_h_deg"][i], "bw_v_deg": M["bw_v_deg"][i]})
            s = dict(grid_dir=str(gdir.relative_to(ROOT)), n_freqs=len(f), **load_pieces(f, q["re_z"]),
                     re_z_643_828_1065=[float(np.interp(np.log(x), np.log(f), q["re_z"])) for x in (643, 828, 1065)],
                     re_z_2k=float(np.interp(np.log(2000), np.log(f), q["re_z"])),
                     im_z_eng_643_828_1065=[float(np.interp(np.log(x), np.log(f), q["im_z_eng"])) for x in (643, 828, 1065)],
                     gamma_643_828_1065=[float(np.interp(np.log(x), np.log(f), q["gamma"])) for x in (643, 828, 1065)],
                     on_acc_rel2k_643_828=[rel(f, q["on_acc_db"], x) for x in (643, 828)],
                     on_vel_rel2k_643_828=[rel(f, q["on_vel_db"], x) for x in (643, 828)],
                     pwl_vel_rel2k_643_828=[rel(f, q["pwl_vel_db"], x) for x in (643, 828)],
                     pwl_acc_rel2k_643_828=[rel(f, q["pwl_vel_db"] - 20 * np.log10(2 * np.pi * f), x) for x in (643, 828)],
                     rez_ratio_db_828_vs_2k=float(10 * np.log10(np.interp(np.log(828), np.log(f), q["re_z"])
                                                                / np.interp(np.log(2000), np.log(f), q["re_z"]))),
                     energy_ratio_range=[float(np.nanmin(q["energy_ratio"])), float(np.nanmax(q["energy_ratio"]))],
                     energy_ratio_400_3000=[float(x) for x in q["energy_ratio"][(f >= 400) & (f <= 3000)]],
                     on_vel_bump=detrend_bump(f, q["on_vel_db"]), pwl_vel_bump=detrend_bump(f, q["pwl_vel_db"]))
            if gname == "screen" or "verify" in gname:
                dr = driver_summary(resp)
                for r in dr:
                    drv_rows.append({"design": label, "grid": gname, **r})
                s["driver_bracket"] = {k: [float(np.min([r[k] for r in dr])), float(np.median([r[k] for r in dr])),
                                           float(np.max([r[k] for r in dr]))]
                                       for k in dr[0] if k not in BRACKET}
            summary[label][gname] = s

    with open(out / "per_frequency.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(csv_rows[0]))
        w.writeheader()
        w.writerows(csv_rows)
    with open(out / "driver_bracket.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(drv_rows[0]))
        w.writeheader()
        w.writerows(drv_rows)
    summary["_duplicates"] = duplicate_census(out)
    summary["_conventions"] = {
        "source": "unit normal acceleration of the throat cap (meta.spl_reference); unit velocity = +20log10(w)",
        "z": "specific, normalised by rho c; BEM exp(-i w t) so Im<0 is mass-like; im_z_eng = -Im",
        "gamma": "|(z-1)/(z+1)|, single plane-wave mode assumption, diagnostic only",
        "rel2k": "value at f minus value at 2000 Hz, linear in log f between stored samples",
        "energy_ratio": "P_rad(balloon, sin-theta quadrature) / (1/2 rho c Re z S |v|^2)",
        "driver": "drive() at 2.83 V rms, bracket over " + json.dumps(BRACKET) + " with " + json.dumps(FIXED),
        "hp": "ideal 2nd-order Butterworth voltage high pass at 700 Hz (no impedance interaction)",
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=1, default=float), encoding="utf-8")
    print(json.dumps(summary, indent=1, default=lambda o: round(float(o), 3)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
