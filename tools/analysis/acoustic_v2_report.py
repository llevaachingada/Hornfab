"""Rev2 acoustic_v2 report: analyse stored responses (zero BEM) and decide the matched ablation.

Usage (repo root):
    PY tools\\analysis\\acoustic_v2_report.py --night runs\\nights\\rev2_gpu_ablation_2026-11-13 --out runs\\analysis\\rev2_2026-11-13
    PY tools\\analysis\\acoustic_v2_report.py --runs runs\\<dirA> runs\\<dirB> --out <dir>

Reads each job's run dir from the night's summary.jsonl (or --runs), takes the best ok design's
``designs/<hash>/response.npz`` (verify-mode runs: ``verify/designs`` if present), and writes:
  analyses.jsonl     one row per response: physical_solve_id, response_sha256, analysis_id, all v2 fields
  RESULTS.json       per-arm summary vs its matched control + fidelity-ladder noise floor
  DECISION.md        pre-declared rule from docs/research/QUEUE_PLAN_REV2_2026-11-13.md applied
Never writes into runs/<run> or dataset/ or cache/.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from hornlab_search.dataset import identity_v2 as idv  # noqa: E402
from hornlab_search.metrics import acoustic_v2 as av2  # noqa: E402

# arm -> matched control (Rev2 4: scheme a = same mouth, b = same core)
PAIRS = {
    "abl_s1_lip12_a3": "abl_s0_control", "abl_s1_lip6_a3": "abl_s0_control",
    "abl_s1_lip12_a6": "abl_s0_control", "abl_s2_wall12_a3": "abl_s0_control",
    "abl_m_rate2": "abl_m_rate4", "abl_m_rate8": "abl_m_rate4",
    "ath_a1_core": "ath_a0_control", "ath_a1_sf_only": "ath_a0_control",
    "ath_a1_cos_only": "ath_a0_control", "ath_a2_hex": "ath_a0_control",
    # 2026-11-13: ath_a2_hex (m=6) has no mirror symmetry and cannot be built on a quarter
    # model; ath_a2_oct (m=8, amp 34) is the substituted petal arm.
    "ath_a2_oct": "ath_a0_control",
}
FIDELITY = ("fid_epw6", "fid_epw10", "fid_dist8m", "fid_ang145")
FID_BASE = "fid_base_verify"


def _best_response(run: Path) -> tuple[Path | None, dict]:
    rows = []
    for name in ("verify/search.ndjson", "search.ndjson"):
        p = run / name
        if p.is_file():
            for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if r.get("ok") and r.get("design_hash"):
                    r["_sub"] = "verify/designs" if name.startswith("verify") else "designs"
                    rows.append(r)
            if rows:
                break
    rows.sort(key=lambda r: float(r.get("objective") if r.get("objective") is not None else 1e9))
    for r in rows:
        f = run / r["_sub"] / r["design_hash"] / "response.npz"
        if f.is_file():
            return f, r
    return None, {}


def _cfg_target(run: Path) -> dict:
    try:
        import yaml
        c = yaml.safe_load((run / "config.yaml").read_text(encoding="utf-8"))
        return c.get("target") or {}
    except Exception:  # noqa: BLE001
        return {}


def _band_mean(freqs, vals, lo, hi):
    f = np.asarray(freqs, float)
    v = np.array([np.nan if x is None else x for x in vals], float)
    m = (f >= lo) & (f <= hi) & np.isfinite(v)
    return float(v[m].mean()) if m.any() else None


def summarize(a: dict, tgt: dict) -> dict:
    lo, hi = float(tgt.get("band_lo_hz") or 0), float(tgt.get("band_hi_hz") or 1e9)
    f = a["freqs_hz"]
    s = {"band_hz": [lo, hi]}
    for c in ("h", "v"):
        m = a.get(f"main_{c}", {})
        if "width_deg" in m:
            s[f"bw6_main_{c}_mean"] = _band_mean(f, m["width_deg"], lo, hi)
            s[f"max_offaxis_{c}_db"] = _band_mean(f, m["max_offaxis_db"], lo, hi)
    L = a.get("lobes", {})
    if "outside_peak_db" in L:
        s["outside_peak_db_mean"] = _band_mean(f, L["outside_peak_db"], lo, hi)
        s["outside_power_fraction_mean"] = _band_mean(f, L["outside_power_fraction"], lo, hi)
        s["max_above_axis_db_max"] = max([x for x in L["max_above_axis_db"] if x is not None], default=None)
        s["islands_max"] = max([x for x in L["island_count"] if x is not None], default=None)
    d = a.get("di_balloon", {})
    if "di_db" in d:
        s["di_mean"] = _band_mean(f, d["di_db"], lo, hi)
    s["loading_onset_hz"] = a.get("loading", {}).get("onset_hz")
    for c in ("h", "v"):
        po = a.get(f"pattern_onset_{c}")
        if po:
            s[f"pattern_onset_{c}_hz"] = po.get("onset_hz")
            s[f"pattern_onset_{c}_status"] = po.get("status")
    return s


KEYS = ("bw6_main_h_mean", "bw6_main_v_mean", "outside_peak_db_mean", "outside_power_fraction_mean",
        "di_mean", "max_above_axis_db_max")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--night", help="runs/nights/<night> dir with summary.jsonl")
    ap.add_argument("--runs", nargs="*", default=[], help="explicit run dirs (job id = config name)")
    ap.add_argument("--out", required=True)
    ns = ap.parse_args(argv)
    jobs: dict[str, Path] = {}
    if ns.night:
        for line in (Path(ns.night) / "summary.jsonl").read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            if r.get("run_dir"):
                jobs[r["id"]] = Path(r["run_dir"])
    for rd in ns.runs:
        p = Path(rd)
        try:
            import yaml
            jobs[yaml.safe_load((p / "config.yaml").read_text(encoding="utf-8")).get("name") or p.name] = p
        except Exception:  # noqa: BLE001
            jobs[p.name] = p
    out = Path(ns.out)
    out.mkdir(parents=True, exist_ok=True)
    summ, missing = {}, []
    for jid, run in jobs.items():
        f, row = _best_response(run)
        if f is None:
            missing.append(jid)
            continue
        tgt = _cfg_target(run)
        a = av2.analyze_response(f, tgt.get("coverage_h_deg"), tgt.get("coverage_v_deg"))
        rsha = idv.file_sha256(f)
        rec = {"job": jid, "run_dir": str(run), "design_hash": row.get("design_hash"),
               "physical_solve_id": idv.physical_solve_id(row.get("design_hash"), row.get("mesh_hash"),
                                                         row.get("solve_hash")),
               "response_sha256": rsha,
               "analysis_id": idv.analysis_id(rsha, av2.METHOD_VERSION, {"target": tgt}),
               "legacy_objective": row.get("objective"), "available": a["available"],
               "summary": summarize(a, tgt), "analysis": a}
        idv.append_jsonl(out / "analyses.jsonl", rec)
        summ[jid] = rec["summary"]
    # fidelity noise floor: max |delta| of each key across the one-factor ladder vs base
    floor = {}
    base = summ.get(FID_BASE) or summ.get("abl_s0_control")
    if base:
        for k in KEYS:
            ds = [abs(summ[j][k] - base[k]) for j in FIDELITY
                  if j in summ and summ[j].get(k) is not None and base.get(k) is not None]
            floor[k] = max(ds) if ds else None
    arms = {}
    for arm, ctl in PAIRS.items():
        if arm not in summ or ctl not in summ:
            continue
        delta = {k: (summ[arm][k] - summ[ctl][k]) if summ[arm].get(k) is not None
                 and summ[ctl].get(k) is not None else None for k in KEYS}
        beyond = {k: (d is not None and floor.get(k) is not None and abs(d) > floor[k])
                  for k, d in delta.items()}
        arms[arm] = {"control": ctl, "delta": delta, "beyond_noise_floor": beyond,
                     "changes_field": any(beyond.get(k) for k in ("outside_peak_db_mean",
                                                                  "bw6_main_h_mean", "bw6_main_v_mean",
                                                                  "outside_power_fraction_mean"))}
    far = None
    if "fid_dist8m" in summ and base:
        far = {k: (summ["fid_dist8m"][k] - base[k]) if summ["fid_dist8m"].get(k) is not None
               and base.get(k) is not None else None for k in KEYS}
    results = {"method": av2.METHOD_VERSION, "jobs": summ, "noise_floor": floor, "arms": arms,
               "far_field_8m_minus_2m": far, "missing_responses": missing,
               "evidence": "computed (BEM, stored responses); not measured"}
    (out / "RESULTS.json").write_text(json.dumps(results, indent=1, default=str), encoding="utf-8")
    lines = ["# Rev2 ablation decision", "",
             "Rule (pre-declared): an arm changes the field only if a main-lobe/outside-lobe metric moves",
             "by more than the one-factor fidelity spread for that metric. J is not the readout.", "",
             "| Arm | Control | dBW6 H | dBW6 V | d outside peak dB | d outside power | Decision |",
             "|---|---|---|---|---|---|---|"]
    fmt = lambda v: "n/a" if v is None else f"{v:+.2f}"  # noqa: E731
    for arm, r in arms.items():
        d = r["delta"]
        dec = "accept (changes field)" if r["changes_field"] else "insufficient_evidence / negative"
        lines.append(f"| {arm} | {r['control']} | {fmt(d['bw6_main_h_mean'])} | {fmt(d['bw6_main_v_mean'])} | "
                     f"{fmt(d['outside_peak_db_mean'])} | {fmt(d['outside_power_fraction_mean'])} | {dec} |")
    lines += ["", f"Noise floor: {json.dumps(floor)}", f"Far field 8 m minus 2 m: {json.dumps(far)}",
              f"Missing responses: {missing}"]
    (out / "DECISION.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"analysed {len(summ)} job(s), {len(arms)} arm pair(s), missing {len(missing)} -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
