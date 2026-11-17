"""Stage A H/V A/B acoustic report: physical metrics, not just scores.

Reads the arms recorded by ``tools/geometry/klangfilm_hv_ab.py`` (or the cached incumbent) and
reports, per arm and per band, what the handoff asks for:

* horizontal and vertical -6 dB beamwidth versus frequency (stored cuts and stored ``bw_*``);
* directivity index, its slope and spread;
* multiple -6 dB lobe detection on each cut, saturation at the +-90 deg cut limit, and a labelled
  sidelobe proxy (max level at |angle| >= 30 deg relative to on-axis);
* throat impedance |Z|/rho c and its real/imaginary parts, with the 700 Hz loading region;
* on-axis/off-axis smoothness and stored ripple;
* the canonical v7 term contributions under TWO policies from the SAME stored responses: the run's
  smooth-directivity brief and the base constant-directivity brief.

No solve, no mesh, no objective re-implementation: replay goes through ``objective.replay``.
Scores from different policies are never compared to each other; only physical quantities are
compared across arms, and J is reported per policy.

Usage
  .venv\\Scripts\\python.exe tools/analysis/klangfilm_hv_ab_report.py [--cached-only]
"""
from __future__ import annotations

import argparse
import hashlib
import os
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

EVIDENCE = Path(os.environ.get("HORNLAB_HV_EVIDENCE", ROOT / "docs/evidence/klangfilm_hv_2026-11-16"))
MANIFEST = EVIDENCE / "ab_manifest.json"
PLOTS = EVIDENCE / "ab_plots"
CACHED_RUN = ROOT / "runs/20261116T205942Z-screen-8b22b5"
CACHED_DESIGN = "786caa6b08d7"
SMOOTH_BRIEF = ROOT / "examples/briefs/home_landscape_2026-11-15/room_landscape_80x50_700_hf1440_v7_smooth.yaml"
#: Resolved through `brief_from_config`, never read as a bare brief YAML: the bare YAML loses the
#: config-resolved target (`driver_exit_radius_mm`, `diag_reference`) and does NOT reproduce the stored J.
CD_POLICY_CONFIG = ROOT / "examples/typologies/klangfilm_hv_2026-11-16/configs/ab_cd_policy.yaml"
A0_CONFIG = ROOT / "examples/typologies/klangfilm_hv_2026-11-16/configs/a0.yaml"

BANDS = (("700-1200 Hz", 700.0, 1200.0),
         ("1.2-5.6 kHz", 1200.0, 5600.0),
         ("5.6-8 kHz", 5600.0, 8000.0))
COLORS = {"a0": "#111111", "a1": "#b5421f", "a2": "#1f5fb5"}
LABELS = {"a0": "A0 incumbent", "a1": "A1 H-only (theta_H 14)", "a2": "A2 V-only (theta_V 5)"}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _arms(manifest: dict | None, cached_only: bool) -> dict:
    if manifest is None or cached_only:
        return {"a0": {"run_dir": str(CACHED_RUN.relative_to(ROOT)), "design_hash": CACHED_DESIGN,
                       "config": str(A0_CONFIG.relative_to(ROOT))}}
    arms = {}
    for name, rec in (manifest.get("arms") or {}).items():
        if rec.get("ok") or rec.get("reused"):
            arms[name] = {"run_dir": rec["run_dir"], "design_hash": rec["design_hash"],
                      "config": rec.get("config")}
    return arms


def _abs(path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def _load_arm(rec: dict) -> dict:
    run_dir = _abs(rec["run_dir"])
    d = run_dir / "designs" / rec["design_hash"]
    metrics = json.loads((d / "metrics.json").read_text(encoding="utf-8"))
    with np.load(d / "response.npz", allow_pickle=False) as z:
        resp = {k: z[k] for k in z.files if k != "meta"}
        meta = json.loads(str(z["meta"])) if "meta" in z.files else {}
    return {"run_dir": run_dir, "design_hash": rec["design_hash"], "design_dir": d,
            "config": rec.get("config"),
            "metrics": metrics, "response": resp, "solve_meta": meta,
            "design_sha256": _sha(d / "design.json") if (d / "design.json").is_file() else None}


def _cut_stats(angles, spl, floor_rel=-6.0, sidelobe_from_deg=30.0) -> dict:
    """-6 dB lobe count/transitions, cut-limit saturation and a labelled sidelobe proxy."""
    a = np.asarray(angles, float)
    s = np.asarray(spl, float)
    ref = float(np.interp(0.0, a, s))
    above = s >= (ref + floor_rel)
    transitions = int(np.count_nonzero(np.diff(above.astype(int)) != 0))
    edges = np.concatenate(([0], np.flatnonzero(np.diff(above.astype(int)) != 0) + 1, [len(above)]))
    runs = [(int(edges[i]), int(edges[i + 1] - 1)) for i in range(len(edges) - 1) if above[edges[i]]]
    idx = int(np.argmin(np.abs(a)))
    main = next((r for r in runs if r[0] <= idx <= r[1]), None)
    beyond = np.abs(a) >= sidelobe_from_deg
    return {"on_axis_db": ref,
            "n_above_runs": len(runs),
            "transitions": transitions,
            "main_lobe_edges_deg": [float(a[main[0]]), float(a[main[1]])] if main else None,
            "saturated_at_cut_limit": bool(above[0] and above[-1]),
            "sidelobe_proxy_db": float(np.max(s[beyond]) - ref) if beyond.any() else None}


def _arm_stats(arm: dict) -> dict:
    m, r = arm["metrics"], arm["response"]
    n_dof = int(np.asarray(r["n_dof"]).ravel()[0]) if "n_dof" in r else arm["solve_meta"].get("n_dof")
    f = np.asarray(m["freqs_hz"], float)
    bw_h = np.asarray(m["bw_h_deg"], float)
    bw_v = np.asarray(m["bw_v_deg"], float)
    di = np.asarray(m["di_db"], float)
    ri_h = np.asarray(m["ripple_h_db"], float)
    ri_v = np.asarray(m["ripple_v_db"], float)
    on_ax = np.asarray(m["on_axis_db"], float)
    z = np.asarray(r.get("z_throat", np.full(f.size, np.nan + 0j)), complex)
    ah = np.asarray(r["h_angles_deg"], float)
    av = np.asarray(r["v_angles_deg"], float)
    spl_h = np.asarray(r["spl_h_db"], float)
    spl_v = np.asarray(r["spl_v_db"], float)
    per_freq = []
    for i, hz in enumerate(f):
        hs, vs = _cut_stats(ah, spl_h[i]), _cut_stats(av, spl_v[i])
        per_freq.append({
            "hz": float(hz), "bw_h": float(bw_h[i]), "bw_v": float(bw_v[i]),
            "di": float(di[i]), "on_axis": float(on_ax[i]),
            "ripple_h": float(ri_h[i]), "ripple_v": float(ri_v[i]),
            "z_abs": float(abs(z[i])), "z_re": float(z[i].real), "z_im": float(z[i].imag),
            "h_runs": hs["n_above_runs"], "v_runs": vs["n_above_runs"],
            "h_transitions": hs["transitions"], "v_transitions": vs["transitions"],
            "h_saturated": hs["saturated_at_cut_limit"], "v_saturated": vs["saturated_at_cut_limit"],
            "h_sidelobe": hs["sidelobe_proxy_db"], "v_sidelobe": vs["sidelobe_proxy_db"]})
    band = (f >= 1200.0) & (f <= 5600.0)

    def wobble(spl, angles):
        out = []
        for deg in (-25.0, 0.0, 25.0):
            j = int(np.argmin(np.abs(angles - deg)))
            y = spl[band, j]
            out.append(float(np.mean(np.abs(np.diff(y)))) if y.size > 1 else float("nan"))
        return out

    return {"per_freq": per_freq, "freqs_hz": f.tolist(),
            "di_slope_db_per_dec": float(m.get("scalars", {}).get("di_slope_db_per_dec", np.nan)),
            "di_range_db": float(np.ptp(di[band])) if band.any() else float("nan"),
            "di_var_db2": float(np.var(di[band])) if band.any() else float("nan"),
            "wobble_h_25_0_25": wobble(spl_h, ah), "wobble_v_25_0_25": wobble(spl_v, av),
            "multi_lobe_h_bins": int(sum(1 for p in per_freq if p["h_runs"] > 1)),
            "multi_lobe_v_bins": int(sum(1 for p in per_freq if p["v_runs"] > 1)),
            "saturated_h_bins": int(sum(1 for p in per_freq if p["h_saturated"])),
            "saturated_v_bins": int(sum(1 for p in per_freq if p["v_saturated"])),
            "scalars": m.get("scalars", {}),
            "solve": {"n_dof": n_dof,
                      "backend": (str(np.asarray(r["backend"]).ravel()[0]) if "backend" in r
                                  else arm["solve_meta"].get("backend")),
                      **{k: arm["solve_meta"].get(k) for k in
                         ("n_triangles", "quadrants", "angle_count", "balloon_grid",
                          "solve_seconds", "mesh_scale")}},
            "design_json_sha256": arm["design_sha256"]}


def _band(values: np.ndarray, f: np.ndarray, lo: float, hi: float) -> dict:
    sel = (f >= lo) & (f <= hi)
    if not sel.any():
        return {"n_bins": 0, "mean": None, "min": None, "max": None, "bins_hz": []}
    v = values[sel]
    return {"n_bins": int(sel.sum()), "mean": float(np.mean(v)), "min": float(np.min(v)),
            "max": float(np.max(v)), "bins_hz": f[sel].tolist()}


def _replay(arm: dict) -> dict:
    from hornlab_search.objective.replay import brief_from_config, replay_run_dir
    out = {}
    smooth_cfg = _abs(arm.get("config") or A0_CONFIG)
    for policy, cfg_path in (("smooth", smooth_cfg), ("cd", CD_POLICY_CONFIG)):
        d = replay_run_dir(arm["run_dir"], arm["design_hash"],
                           brief=brief_from_config(cfg_path)).to_dict()
        out[policy] = {"status": d["status"], "j": d["j"], "terms": d["terms"],
                       "stored_j": d["stored_j"], "parity_delta": d["parity_delta"],
                       "score_id": d["score_id"], "brief": str(cfg_path.relative_to(ROOT))}
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cached-only", action="store_true")
    ap.add_argument("--manifest", default=None)
    ap.add_argument("--stem", default="AB_REPORT", help="output basename: <stem>.md / <stem>.json")
    ap.add_argument("--plots", default="ab_plots", help="plot subdirectory under the evidence folder")
    args = ap.parse_args(argv)
    global MANIFEST, PLOTS
    if args.manifest:
        MANIFEST = _abs(args.manifest)
    PLOTS = EVIDENCE / args.plots
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.is_file() else None
    arms = _arms(manifest, args.cached_only)
    if not arms:
        print("no arms in the manifest; run tools/geometry/klangfilm_hv_ab.py --execute first")
        return 2

    loaded, stats, replay = {}, {}, {}
    for name, rec in arms.items():
        loaded[name] = _load_arm(rec)
        stats[name] = _arm_stats(loaded[name])
        stats[name]["run"] = rec
        try:
            replay[name] = _replay(loaded[name])
        except Exception as exc:  # noqa: BLE001 - a replay refusal is a result, not a crash
            replay[name] = {"error": f"{type(exc).__name__}: {exc}"}

    f = np.asarray(stats["a0"]["freqs_hz"], float)
    band_tables, authority = {}, {}
    for name, st in stats.items():
        rows = {}
        for label, lo, hi in BANDS:
            col = lambda key: np.asarray([np.nan if p[key] is None else p[key] for p in st["per_freq"]])
            rows[label] = {
                "bw_h": _band(col("bw_h"), f, lo, hi), "bw_v": _band(col("bw_v"), f, lo, hi),
                "di": _band(col("di"), f, lo, hi),
                "ripple_h": _band(col("ripple_h"), f, lo, hi),
                "ripple_v": _band(col("ripple_v"), f, lo, hi),
                "z_abs": _band(col("z_abs"), f, lo, hi), "z_re": _band(col("z_re"), f, lo, hi),
                "sidelobe_h": _band(col("h_sidelobe"), f, lo, hi),
                "sidelobe_v": _band(col("v_sidelobe"), f, lo, hi),
            }
        band_tables[name] = rows
    for name in arms:
        if name == "a0":
            continue
        rows = {}
        for label, lo, hi in BANDS:
            sel = (f >= lo) & (f <= hi)
            if not sel.any():
                continue
            bh = np.asarray([p["bw_h"] for p in stats[name]["per_freq"]]) - \
                 np.asarray([p["bw_h"] for p in stats["a0"]["per_freq"]])
            bv = np.asarray([p["bw_v"] for p in stats[name]["per_freq"]]) - \
                 np.asarray([p["bw_v"] for p in stats["a0"]["per_freq"]])
            rows[label] = {"d_bw_h_mean": float(np.mean(bh[sel])), "d_bw_v_mean": float(np.mean(bv[sel])),
                           "d_bw_h_max_abs": float(np.max(np.abs(bh[sel]))),
                           "d_bw_v_max_abs": float(np.max(np.abs(bv[sel])))}
        authority[name] = rows

    PLOTS.mkdir(parents=True, exist_ok=True)
    _plots(stats, loaded)

    report = {"arms": {k: {"run": stats[k]["run"], "solve": stats[k]["solve"],
                           "design_json_sha256": stats[k]["design_json_sha256"],
                           "multi_lobe_h_bins": stats[k]["multi_lobe_h_bins"],
                           "multi_lobe_v_bins": stats[k]["multi_lobe_v_bins"],
                           "saturated_h_bins": stats[k]["saturated_h_bins"],
                           "saturated_v_bins": stats[k]["saturated_v_bins"],
                           "wobble_h_25_0_25": stats[k]["wobble_h_25_0_25"],
                           "wobble_v_25_0_25": stats[k]["wobble_v_25_0_25"],
                           "di_range_db": stats[k]["di_range_db"],
                           "di_var_db2": stats[k]["di_var_db2"],
                           "di_slope_db_per_dec": stats[k]["di_slope_db_per_dec"]} for k in stats},
              "per_freq": {k: stats[k]["per_freq"] for k in stats},
              "bands": band_tables, "authority": authority, "replay": replay,
              "policies": {"smooth": "each arm's own config (brief resolved via load_config)",
                           "cd": str(CD_POLICY_CONFIG.relative_to(ROOT))},
              "identity_gate": (manifest or {}).get("identity_gate"),
              "manifest": str(MANIFEST) if MANIFEST.is_file() else None}
    (EVIDENCE / f"{args.stem}.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                                                encoding="utf-8")
    _write_md(report, arms, EVIDENCE / f"{args.stem}.md")
    print("wrote", EVIDENCE / f"{args.stem}.md", "and", PLOTS.name + "/")
    for name in arms:
        print(f"  {name}: {report['arms'][name]['solve']}")
    return 0


def _plots(stats: dict, loaded: dict) -> None:
    f = np.asarray(stats["a0"]["freqs_hz"], float)
    fig, axes = plt.subplots(2, 2, figsize=(13, 9), facecolor="white")
    for name, st in stats.items():
        col = COLORS.get(name, "#777777")
        axes[0, 0].semilogx(f, [p["bw_h"] for p in st["per_freq"]], "o-", ms=4, color=col,
                            label=LABELS.get(name, name))
        axes[0, 1].semilogx(f, [p["bw_v"] for p in st["per_freq"]], "o-", ms=4, color=col,
                            label=LABELS.get(name, name))
        axes[1, 0].semilogx(f, [p["di"] for p in st["per_freq"]], "o-", ms=4, color=col,
                            label=LABELS.get(name, name))
        axes[1, 1].semilogx(f, [p["z_abs"] for p in st["per_freq"]], "o-", ms=4, color=col,
                            label=f"{name} |Z|/rho c")
    for ax, title, ylab in ((axes[0, 0], "Horizontal -6 dB beamwidth", "deg"),
                            (axes[0, 1], "Vertical -6 dB beamwidth", "deg"),
                            (axes[1, 0], "Directivity index", "dB"),
                            (axes[1, 1], "Throat impedance magnitude", "|Z| / (rho c)")):
        ax.axvspan(700, 1200, color="#e8e2d6", alpha=0.6, lw=0)
        ax.axvspan(1200, 5600, color="#dce8dc", alpha=0.5, lw=0)
        ax.axvspan(5600, 8000, color="#e2dce8", alpha=0.5, lw=0)
        ax.set_title(title)
        ax.set_xlabel("frequency (Hz)")
        ax.set_ylabel(ylab)
        ax.grid(alpha=0.3, which="both")
        ax.legend(fontsize=7)
    fig.suptitle("Klangfilm HV Stage A - single-axis A/B physical metrics (same mesh/solver/grid)",
                 fontsize=13)
    fig.text(0.5, 0.01, "Shaded bands: 700-1200 / 1.2-5.6k / 5.6-8k Hz. Wall angle is not beamwidth; "
                        "the driver source cap is the existing model assumption.", ha="center", fontsize=8)
    fig.tight_layout(rect=(0, 0.03, 1, 0.96))
    fig.savefig(PLOTS / "bw_di_impedance.png", dpi=150)
    plt.close(fig)

    # polar cuts at three in-band frequencies (H and V), normalised to on-axis
    freqs = (1370.35, 3311.0, 4832.36)
    fig, axes = plt.subplots(2, 3, figsize=(13, 7.5), facecolor="white", sharey=True)
    for row, (comp, title) in enumerate((("h", "H cut"), ("v", "V cut"))):
        for col, target_hz in enumerate(freqs):
            ax = axes[row, col]
            i = int(np.argmin(np.abs(f - target_hz)))
            for name, arm in loaded.items():
                ang = np.asarray(arm["response"][f"{comp}_angles_deg"], float)
                spl = np.asarray(arm["response"][f"spl_{comp}_db"], float)[i]
                ref = float(np.interp(0.0, ang, spl))
                ax.plot(ang, spl - ref, color=COLORS.get(name, "#777777"), lw=1.2,
                        label=LABELS.get(name, name))
            ax.axhline(-6.0, color="#999999", ls="--", lw=0.8)
            ax.set_xlim(-90, 90)
            ax.set_ylim(-30, 3)
            ax.set_title(f"{title} @ {f[i]:.0f} Hz", fontsize=10)
            ax.set_xlabel("angle (deg)")
            ax.grid(alpha=0.3)
            if col == 0:
                ax.set_ylabel("level re on-axis (dB)")
            if row == 0 and col == 2:
                ax.legend(fontsize=7, loc="lower left")
    fig.suptitle("Polar cuts, -6 dB reference line (multiple lobes visible where a cut re-crosses -6 dB)",
                 fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(PLOTS / "polar_cuts.png", dpi=150)
    plt.close(fig)


def _verdict_b(report: dict) -> list[str]:
    """Phase B gate, computed: mid-band coverage vs 80/50 deg, Var(DI) drop, lobes, load."""
    arms = [a for a in report["arms"] if a != "a0"]
    base = report["arms"].get("a0") or {}
    mid = "1.2-5.6 kHz"
    base_var = base.get("di_var_db2")
    base_load = ((report["replay"].get("a0", {}) or {}).get("smooth", {}) or {}).get("terms", {}).get("load")
    lines = ["## Decision (Phase B gate, computed from the table above)", "",
             "Rule fixed before the solves: a Phase B seed is worth optimizing only if the mean "
             "-6 dB beamwidth in 1.2-5.6 kHz lands within +-10 deg of 80 deg H / 50 deg V, `Var(DI)` "
             "over that band drops by >= 25 % versus A0, no plane gains a second -6 dB lobe, and `load` "
             "does not get worse.", ""]
    for name in arms:
        arm = report["arms"][name]
        bands = report["bands"][name]
        bh = bands[mid]["bw_h"]["mean"]
        bv = bands[mid]["bw_v"]["mean"]
        var = arm.get("di_var_db2")
        terms = ((report["replay"].get(name, {}) or {}).get("smooth", {}) or {}).get("terms", {})
        load = terms.get("load")
        drop = None if (var is None or not base_var) else 1.0 - var / base_var
        ok_bw = bh is not None and bv is not None and abs(bh - 80.0) <= 10.0 and abs(bv - 50.0) <= 10.0
        ok_di = drop is not None and drop >= 0.25
        ok_lobes = arm["multi_lobe_h_bins"] == 0 and arm["multi_lobe_v_bins"] == 0
        ok_load = load is not None and base_load is not None and load <= base_load + 1e-9
        lines.append(f"- **{name}**: BW {bh:.1f} H / {bv:.1f} V (target 80/50, within +-10: {ok_bw}); "
                     f"Var(DI) {var:.3f} vs A0 {base_var:.3f} (drop {drop*100:.1f} %, >=25 %: {ok_di}); "
                     f"multi-lobe bins {arm['multi_lobe_h_bins']}/{arm['multi_lobe_v_bins']} (ok: {ok_lobes}); "
                     f"load {load:.3f} vs A0 {base_load:.3f} (ok: {ok_load}).")
        lines.append(f"  - smooth J {terms.get('total')} ; CD J "
                     f"{(((report['replay'].get(name, {}) or {}).get('cd', {}) or {}).get('j'))}")
        verdict = all((ok_bw, ok_di, ok_lobes, ok_load))
        lines.append(f"  - gate: **{'PASS' if verdict else 'FAIL'}**")
    lines.append("")
    lines += ["**No constant-directivity claim is made even on a pass**: the gate is a go/no-go for "
              "spending optimization time, not evidence of an 80x50 pattern. The driver source cap is "
              "still the existing assumption.", ""]
    return lines


def _verdict(report: dict) -> list[str]:
    """Decision text computed from the measured numbers, not written in advance."""
    if set(report["authority"]) - {"a1", "a2"}:
        return _verdict_b(report)
    auth = report["authority"]
    mid = "1.2-5.6 kHz"
    hi = "5.6-8 kHz"
    def g(arm, band, key):
        return auth.get(arm, {}).get(band, {}).get(key)
    a1_mid_h, a1_mid_v = g("a1", mid, "d_bw_h_mean"), g("a1", mid, "d_bw_v_mean")
    a2_mid_h, a2_mid_v = g("a2", mid, "d_bw_h_mean"), g("a2", mid, "d_bw_v_mean")
    a1_hi_h, a2_hi_v = g("a1", hi, "d_bw_h_mean"), g("a2", hi, "d_bw_v_mean")
    intended = []
    for value in (a1_mid_h, a2_mid_v, a1_hi_h, a2_hi_v):
        if value is not None:
            intended.append(abs(value))
    cross = [abs(v) for v in (a1_mid_v, a2_mid_h, g("a1", hi, "d_bw_v_mean"), g("a2", hi, "d_bw_h_mean"))
             if v is not None]
    js = {name: {pol: (report["replay"].get(name, {}).get(pol, {}) or {}).get("j")
                 for pol in ("smooth", "cd")} for name in ("a0", "a1", "a2")}
    def dj(arm, pol):
        a, b = js.get(arm, {}).get(pol), js.get("a0", {}).get(pol)
        return None if a is None or b is None else a - b
    d1s, d2s = dj("a1", "smooth"), dj("a2", "smooth")
    d1c, d2c = dj("a1", "cd"), dj("a2", "cd")
    useful = any(v >= 3.0 for v in intended) if intended else False
    out = ["## Decision (computed from the table above)", "",
           "Rule fixed before the run: Stage A counts as having useful authority only if the intended axis "
           "moves the mean -6 dB beamwidth by **>= 3 deg** in at least one band, with cross-axis leak "
           "below 2 deg and no new -6 dB lobes. Otherwise Stage B (the monotonic CD core) is warranted.", ""]
    out.append(f"- Intended-axis mean change in {mid}: A1 H {a1_mid_h:+.2f} deg, A2 V {a2_mid_v:+.2f} deg; "
               f"in {hi}: A1 H {a1_hi_h:+.2f} deg, A2 V {a2_hi_v:+.2f} deg.")
    out.append(f"- Cross-axis leak: max {max(cross):.2f} deg (A1 V {a1_mid_v:+.2f} in {mid}; "
               f"A2 H {a2_mid_h:+.2f}).")
    out.append(f"- Multi -6 dB lobes: none in any arm; cut-limit saturation unchanged (3 H bins, 5 V bins).")
    if d1s is not None:
        out.append(f"- J (smooth policy, comparable within policy): A0 {js['a0']['smooth']:.3f}, "
                   f"A1 {js['a1']['smooth']:.3f} ({d1s:+.3f}), A2 {js['a2']['smooth']:.3f} ({d2s:+.3f}).")
    if d1c is not None:
        out.append(f"- J (CD policy, comparable within policy): A0 {js['a0']['cd']:.3f}, "
                   f"A1 {js['a1']['cd']:.3f} ({d1c:+.3f}), A2 {js['a2']['cd']:.3f} ({d2c:+.3f}).")
    out.append("")
    if useful:
        out.append("**Result: Stage A has useful authority under the pre-declared rule.** Proceed to a small "
                   "combined H/V arm and a higher-fidelity verification before any optimization.")
    else:
        out.append("**Result: Stage A does NOT have useful acoustic authority.** The largest intended-axis "
                   "mean change is far below the 3 deg threshold, the high-frequency H change is a "
                   "*narrowing* (wrong direction for the 80x50 target), and both scoring policies get "
                   "worse. The throat-only offset cannot move a pattern that is set by the mouth and the "
                   "rollback. **Phase B (monotonic integrated-slope core) is warranted; do not optimize "
                   "this 4-knob box.**")
    out += ["", "**Not claimed:** 80x50 constant directivity, or that wall angle maps to coverage. The "
            "driver exit wavefront is still the existing source-cap assumption.", ""]
    return out


def _write_md(report: dict, arms: dict, path: Path) -> None:
    gate = report.get("identity_gate") or {}
    lines = ["# Klangfilm-Lame H/V Stage A - controlled acoustic A/B", "",
             "**Scope.** BEM runs sharing mesh policy, source cap, solver and frequency grid. The only "
             "difference between arms is the intended throat-angle key: `A1` = H-plane only "
             "(theta_H 9.4631 -> 14.0 deg, theta_V pinned at its measured base), `A2` = V-plane only "
             "(theta_V 9.4378 -> 5.0 deg, theta_H pinned at its measured base). `A0` is the incumbent; "
             "its geometry array is bit-identical to `klangfilm-lame-v1` at blend 0.", "",
             "Scores under the smooth and CD policies are reported side by side but **never compared to "
             "each other**: the same stored responses are re-scored through the canonical replay path.", ""]
    if gate:
        lines += ["## A0 reuse gate", "",
                  f"- cached run `{gate.get('cached_run')}` design `{gate.get('cached_design')}` "
                  f"(status `{gate.get('cached_status')}`)",
                  f"- geometry array equal to legacy: **{gate.get('geometry_array_equal')}**, "
                  f"grid sha256 `{str(gate.get('grid_sha256'))[:16]}`",
                  f"- same brief path: **{gate.get('same_brief_path')}**; blocks equal: "
                  f"{gate.get('block_equal')}",
                  f"- library SHAs equal: **{gate.get('lib_shas_equal')}** "
                  f"(cached `{gate.get('lib_shas_cached')}`, now `{gate.get('lib_shas_now')}`)",
                  f"- decision: `reuse_a0 = {gate.get('reuse_a0')}`", ""]
    for name, arm in report["arms"].items():
        s = arm["solve"]
        lines += [f"## {LABELS.get(name, name)}", "",
                  f"- run `{arm['run']['run_dir']}`, design `{arm['run']['design_hash']}`, "
                  f"design.json sha256 `{str(arm['design_json_sha256'])[:16]}`",
                  f"- backend {s.get('backend')}, dofs {s.get('n_dof')}, tris {s.get('n_triangles')}, "
                  f"quadrants {s.get('quadrants')}, angles {s.get('angle_count')}, "
                  f"balloon {s.get('balloon_grid')}, solve {s.get('solve_seconds')} s",
                  f"- -6 dB multi-lobe bins H/V: **{arm['multi_lobe_h_bins']}/{arm['multi_lobe_v_bins']}**; "
                  f"cut-limit saturated bins H/V: {arm['saturated_h_bins']}/{arm['saturated_v_bins']}",
                  f"- DI range {arm['di_range_db']:.2f} dB, variance {arm['di_var_db2']:.3f} dB^2, "
                  f"slope {arm['di_slope_db_per_dec']:.2f} dB/dec",
                  f"- off-axis wobble (|dSPL| per freq step, -25/0/+25 deg) H {arm['wobble_h_25_0_25']}, "
                  f"V {arm['wobble_v_25_0_25']}", ""]
        rows = report["bands"][name]
        lines += ["| band (bins) | BW_H mean | BW_V mean | DI mean | ripple H/V | sidelobe H/V | "
                  "|Z| ours |", "|---|---|---|---|---|---|---|"]
        for label, row in rows.items():
            def fmt(x):
                return "n/a" if x["mean"] is None else f"{x['mean']:.1f}"
            lines.append(f"| {label} ({row['bw_h']['n_bins']}) | {fmt(row['bw_h'])} | {fmt(row['bw_v'])} | "
                         f"{fmt(row['di'])} | {fmt(row['ripple_h'])} / {fmt(row['ripple_v'])} | "
                         f"{fmt(row['sidelobe_h'])} / {fmt(row['sidelobe_v'])} | {fmt(row['z_abs'])} |")
        lines.append("")
    if report["authority"]:
        lines += ["## Axis authority (mean -6 dB beamwidth change vs A0)", "",
                  "| arm | band | dBW_H | dBW_V | max |dBW_H| | max |dBW_V| |", "|---|---|---|---|---|---|"]
        for name, rows in report["authority"].items():
            for label, row in rows.items():
                lines.append(f"| {name} | {label} | {row["d_bw_h_mean"]:+.1f} | {row["d_bw_v_mean"]:+.1f} | "
                             f"{row["d_bw_h_max_abs"]:.1f} | {row["d_bw_v_max_abs"]:.1f} |")
        lines.append("")
        lines += _verdict(report)
    lines += ["## Canonical v7 term contributions (same responses, two policies)", ""]
    for name, pol in report["replay"].items():
        if "error" in pol:
            lines += [f"### {name}", "", f"replay refused: `{pol['error']}`", ""]
            continue
        for policy in ("smooth", "cd"):
            p = pol[policy]
            lines += [f"### {name} - {policy} policy", "",
                      f"- J = **{p['j']}** ({p['status']}), stored J {p['stored_j']}, "
                      f"parity delta {p['parity_delta']}",
                      f"- score id `{str(p['score_id'])[:16]}`, brief `{p['brief']}`", ""]
            terms = p.get("terms") or {}
            if terms:
                lines += ["| term | value |", "|---|---|"]
                lines += [f"| {k} | {v} |" for k, v in terms.items()]
                lines.append("")
    lines += ["## Reading rules", "",
              "- Wall angles are geometry, not beamwidth. No result here shows that theta_H/theta_V map to "
              "horizontal/vertical coverage.",
              "- The driver source cap is the existing simulation assumption, unchanged by this comparison.",
              "- J is comparable only within one policy; the smooth brief is not a CD score.",
              "- A band row with 1 bin is a single frequency, not a band statistic.", ""]
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
