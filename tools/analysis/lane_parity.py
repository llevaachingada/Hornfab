"""A.7 lane_parity.py — GPU vs CPU parity of stored verify responses (gate CP-7b).

Usage:  PY tools\\analysis\\lane_parity.py --gpu <run dir> --cpu <run dir> --out <dir>

For every ``design_hash`` present in BOTH run dirs (and with both
``designs/<hash>/response.npz`` files loadable), computes the max |dSPL| over frequencies
and angles between the two stored responses (``spl_h_db`` + ``spl_v_db`` and, when
present, ``spl_balloon_db``) and the J difference between the runs' rows for that design.
PASS (CP-7b): at least 3 designs agree within 0.2 dB. This decides whether ``dataset_cpu``
may join ``dataset/`` (Group D's D.3). Read-only everywhere.
Schema: ``tools/analysis/schema.md`` § lane_parity.json.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from _common import add_out_arg, fail, read_ndjson, write_report

TOOL = "lane_parity"
THRESHOLD_DB = 0.2
MIN_DESIGNS = 3
_G = "CP-7b"


def _row_by_design(run_dir: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for r in read_ndjson(Path(run_dir) / "search.ndjson"):
        if r.get("ok") is True and r.get("design_hash"):
            dh = str(r["design_hash"])
            cur = out.get(dh)
            if cur is None or (r.get("n") or 0) > (cur.get("n") or 0):
                out[dh] = r
    return out


def _response_spl(run_dir: Path, design_hash: str):
    """(freqs, [2D dSPL arrays]) from ``designs/<hash>/response.npz``; None when missing/bad."""
    p = Path(run_dir) / "designs" / design_hash / "response.npz"
    if not p.is_file():
        return None
    try:
        with np.load(p, allow_pickle=False) as z:
            freqs = np.asarray(z["freqs_hz"], dtype=float)
            spl = {"spl_h_db": np.asarray(z["spl_h_db"], dtype=float),
                   "spl_v_db": np.asarray(z["spl_v_db"], dtype=float)}
            if "spl_balloon_db" in z.files:
                spl["spl_balloon_db"] = np.asarray(z["spl_balloon_db"], dtype=float)
    except Exception:  # noqa: BLE001 - unreadable response is a per-design note, not a crash
        return None
    return freqs, spl


def _design_dspl(freqs, spl_a: dict, spl_b: dict) -> float | None:
    """Max |dSPL| over frequencies and angles across every plane the two responses share."""
    fa = np.asarray(freqs, dtype=float)
    dmax: float | None = None
    for name, arr_a in spl_a.items():
        arr_b = spl_b.get(name)
        if arr_b is None or arr_a.shape != arr_b.shape:
            continue
        if arr_a.ndim == 2 and fa.size != arr_a.shape[0]:
            continue  # the frequency axis does not match the stored grid
        d = np.abs(arr_a - arr_b)
        d = d[np.isfinite(d)]
        if d.size == 0:
            continue
        m = float(d.max())
        dmax = m if dmax is None else max(dmax, m)
    return dmax


def _same_freq_grid(freqs_a, freqs_b) -> bool:
    fa, fb = np.asarray(freqs_a, dtype=float), np.asarray(freqs_b, dtype=float)
    return fa.shape == fb.shape and bool(np.allclose(fa, fb, rtol=1e-9, atol=1e-9))


def analyse(gpu_dir: Path, cpu_dir: Path) -> dict:
    gpu_dir, cpu_dir = Path(gpu_dir), Path(cpu_dir)
    rows_gpu, rows_cpu = _row_by_design(gpu_dir), _row_by_design(cpu_dir)
    common = sorted(set(rows_gpu) & set(rows_cpu))
    designs = []
    n_within = 0
    for dh in common:
        resp_gpu = _response_spl(gpu_dir, dh)
        resp_cpu = _response_spl(cpu_dir, dh)
        entry: dict = {"design_hash": dh, "compared": False, "max_abs_dspl_db": None,
                       "d_j": None, "source": f"designs/{dh}/response.npz", "note": ""}
        jg = rows_gpu[dh].get("objective")
        jc = rows_cpu[dh].get("objective")
        if isinstance(jg, (int, float)) and isinstance(jc, (int, float)) \
                and np.isfinite(jg) and np.isfinite(jc):
            entry["d_j"] = abs(float(jg) - float(jc))
        if resp_gpu is None and resp_cpu is None:
            entry["note"] = "response.npz missing on both sides"
            designs.append(entry)
            continue
        if resp_gpu is None or resp_cpu is None:
            entry["note"] = "response.npz missing on one side"
            designs.append(entry)
            continue
        if not _same_freq_grid(resp_gpu[0], resp_cpu[0]):
            entry["note"] = "frequency grid mismatch between the two responses"
            designs.append(entry)
            continue
        dmax = _design_dspl(resp_gpu[0], resp_gpu[1], resp_cpu[1])
        if dmax is None:
            entry["note"] = "no shared SPL plane (shape mismatch)"
            designs.append(entry)
            continue
        entry["compared"] = True
        entry["max_abs_dspl_db"] = dmax
        if dmax <= THRESHOLD_DB:
            n_within += 1
        designs.append(entry)
    designs.sort(key=lambda d: (d["max_abs_dspl_db"] is None, d["max_abs_dspl_db"]))
    return {"gpu_dir": str(gpu_dir), "cpu_dir": str(cpu_dir),
            "designs": designs, "n_common_hashes": len(common),
            "n_compared": sum(1 for d in designs if d["compared"]),
            "n_within_0p2": n_within,
            "threshold_db": THRESHOLD_DB, "min_designs": MIN_DESIGNS,
            "pass": n_within >= MIN_DESIGNS, "gate": _G,
            "note": "PASS decides whether dataset_cpu may join dataset/"}


def analyse_pooled(pairs) -> dict:
    """CP-7b across several (gpu_dir, cpu_dir) pairs.

    Each pair is analysed independently (no cross-pair response comparison). A design
    hash counts once across pairs; it counts as within-threshold when its BEST compared
    pair is within 0.2 dB, and it is listed with every pair it appeared in.
    """
    pairs = [(Path(g), Path(c)) for g, c in pairs]
    if not pairs:
        raise ValueError("pooled mode needs at least one --pair")
    per_pair = [analyse(g, c) for g, c in pairs]
    best: dict[str, dict] = {}
    for idx, payload in enumerate(per_pair):
        for d in payload["designs"]:
            if not d["compared"]:
                continue
            cur = best.get(d["design_hash"])
            if cur is None or d["max_abs_dspl_db"] < cur["max_abs_dspl_db"]:
                best[d["design_hash"]] = {**d, "pair_index": idx}
    within = sorted(h for h, d in best.items() if d["max_abs_dspl_db"] <= THRESHOLD_DB)
    return {"mode": "pooled", "pairs": per_pair,
            "n_pairs": len(per_pair),
            "n_distinct_compared": len(best),
            "n_within_0p2": len(within), "within_hashes": within,
            "threshold_db": THRESHOLD_DB, "min_designs": MIN_DESIGNS,
            "pass": len(within) >= MIN_DESIGNS, "gate": _G,
            "dedupe": "design_hash counted once across pairs (best compared pair)",
            "note": "PASS decides whether dataset_cpu may join dataset/"}


def _md_pooled(payload: dict) -> str:
    lines = ["# Lane parity (GPU vs CPU), pooled", "",
             f"- pairs: **{payload['n_pairs']}**; distinct designs compared: "
             f"**{payload['n_distinct_compared']}**; within {payload['threshold_db']} dB: "
             f"**{payload['n_within_0p2']}**",
             f"- gate **{payload['gate']}**: PASS needs >= {payload['min_designs']} distinct designs"
             f" -> **{'PASS' if payload['pass'] else 'FAIL'}**", ""]
    for i, p in enumerate(payload["pairs"]):
        lines += [f"## Pair {i}", "", _md(p)]
    return "\n".join(lines)


def _md(payload: dict) -> str:
    lines = ["# Lane parity (GPU vs CPU)", "",
             f"- GPU: `{payload['gpu_dir']}`", f"- CPU: `{payload['cpu_dir']}`",
             f"- designs compared: **{payload['n_compared']}**"
             f" (of {payload['n_common_hashes']} shared design hashes); "
             f"within {payload['threshold_db']} dB: **{payload['n_within_0p2']}**",
             f"- gate **{payload['gate']}**: PASS needs >= {payload['min_designs']} designs"
             f" within {payload['threshold_db']} dB -> "
             f"**{'PASS' if payload['pass'] else 'FAIL'}**", "",
             "| design | max |dSPL| (dB) | |dJ| | note |", "|---|---:|---:|---|"]
    for d in payload["designs"]:
        dspl = d["max_abs_dspl_db"]
        dspl_s = "—" if dspl is None else f"{dspl:.4f}"
        dj = d["d_j"]
        dj_s = "—" if dj is None else f"{dj:.4f}"
        lines.append(f"| `{d['design_hash']}` | {dspl_s} | {dj_s} | {d['note']} |")
    lines.append("")
    return "\n".join(lines)


def charts(payload: dict) -> dict:
    """PNG charts for this report (used by main() and by report_day)."""
    def fn(plt):
        vals = [(d["design_hash"], d["max_abs_dspl_db"]) for d in payload["designs"]
                if d["max_abs_dspl_db"] is not None]
        if not vals:
            return None
        fig, ax = plt.subplots(figsize=(7, 4))
        names = [v[0][:10] for v in vals]
        ax.bar(names, [v[1] for v in vals])
        ax.axhline(THRESHOLD_DB, color="r", ls="--", lw=1, label=f"{THRESHOLD_DB} dB gate")
        ax.axhline(0.0, color="k", lw=0.6)
        ax.set_ylabel("max |dSPL| over freqs & angles (dB)")
        ax.tick_params(axis="x", rotation=45)
        ax.legend()
        fig.tight_layout()
        return fig
    return {"lane_parity.png": fn}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=( __doc__ or "").splitlines()[0])
    ap.add_argument("--gpu", help="verify run dir produced on the GPU lane")
    ap.add_argument("--cpu", help="verify run dir produced on the CPU lane")
    ap.add_argument("--pair", action="append", default=[], metavar="GPU_DIR,CPU_DIR",
                    help="pooled mode: repeat for several GPU/CPU run-dir pairs")
    add_out_arg(ap)
    args = ap.parse_args(argv)
    if args.pair:
        if args.gpu or args.cpu:
            ap.error("use either --gpu/--cpu or --pair, not both")
        pairs = []
        for raw in args.pair:
            parts = raw.split(",")
            if len(parts) != 2 or not all(p.strip() for p in parts):
                ap.error(f"--pair needs GPU_DIR,CPU_DIR, got {raw!r}")
            pairs.append((parts[0].strip(), parts[1].strip()))
        payload = analyse_pooled(pairs)
        write_report(Path(args.out), TOOL, payload, _md_pooled(payload), {})
        print(f"lane_parity pooled OK: {payload['n_pairs']} pairs, "
              f"{payload['n_within_0p2']} distinct designs within {THRESHOLD_DB} dB -> "
              f"{'PASS' if payload['pass'] else 'FAIL'} ({_G})")
        return 0
    if not (args.gpu and args.cpu):
        ap.error("--gpu and --cpu are required (or use --pair)")
    payload = analyse(Path(args.gpu), Path(args.cpu))

    write_report(Path(args.out), TOOL, payload, _md(payload), charts(payload))
    print(f"lane_parity OK: {payload['n_compared']} designs compared, "
          f"{payload['n_within_0p2']} within {THRESHOLD_DB} dB -> "
          f"{'PASS' if payload['pass'] else 'FAIL'} ({_G})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
