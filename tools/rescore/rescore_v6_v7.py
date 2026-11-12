"""Offline objective v6 vs v7 re-score over the stored dataset. NO GPU, NO solver.

Every committed dataset row already carries the target-free metric arrays (``freqs_hz``,
``bw_h_deg``, ``bw_v_deg``, ``di_db``, ``on_axis_db``, ``ripple_*``, ``z_throat`` and the polars), so
a stored evaluation can be re-scored under a different objective version without touching the
solver, the mesh cache or ``dataset/``. This tool:

* walks ``<dataset>/shard-*.jsonl`` and the matching ``shard-NNNN/rec-NNNN.npz`` arrays;
* reads each row with ``gate_audit.parse_stored_row`` (deliberately version-agnostic);
* rebuilds a ``MetricSet`` + ``Response`` and scores the stored metrics with ``objective_v6`` and
  ``objective_v7``;
* computes the canonical owner gates (``gate_audit.gate_*``) over the stored arrays;
* writes a per-row CSV, a summary JSON and a markdown table under ``--out`` (never into
  ``dataset/``).

Brief classes (the repo's own A/B/C vocabulary, see the brief headers):

* **A** - constant-directivity waveguide (CD);
* **B** - loading / rollback (Le Cleac'h, salmon, low-reach PA that is loading-scored);
* **C** - low-reach PA that falls off below f0.

The stored row keeps its OWN ``target``: the metric curves were produced against it and coverage,
band and f0 semantics are target-specific. A brief supplies the scoring configuration for its
version (weights + objective block). For v6 the only shipped brief is the class-B
``native_lecleach_1200_1in_v6``; it is therefore applied to every class (a v6 brief for A/C does
not exist, which the report states explicitly). For v7 the class-matched briefs are picked from
``examples/briefs/hardened_2026-10-29_v5/`` (renumbered to version 7 on 2026-11-12).

Usage (from the repo root; pass the dataset explicitly when the worktree has none)::

    .venv\\Scripts\\python.exe tools/rescore/rescore_v6_v7.py \
        --dataset C:\\path\\to\\hornlab-search\\dataset \
        --out scratch/rescore_2026-11-12 \
        --md docs/evidence/RESCORE_V6_V7_2026-11-12.md
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
# ``gate_audit`` lives in this directory and is imported as a plain module, exactly as a script
# would; that keeps the canonical gate definitions in ONE place.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import gate_audit as ga  # noqa: E402

from scipy.stats import kendalltau  # noqa: E402

from hornlab_search.constants import BESSEL_J1P_11, C_AIR  # noqa: E402
from hornlab_search.objective.scalar_v6 import V6Params, objective_v6  # noqa: E402
from hornlab_search.objective.scalar_v7 import V7Params, objective_v7  # noqa: E402
from hornlab_search.targets.spec import Target  # noqa: E402
from hornlab_search.types import MetricSet, Response  # noqa: E402

#: The one v6 brief that exists (class B, Le Cleac'h / loading_smooth).
V6_BRIEF = REPO_ROOT / "examples" / "briefs" / "campaign_2026-10-26_v6" / "native_lecleach_1200_1in_v6.yaml"
#: Class-matched v7 briefs (the hardened 2026-10-29 set, now objective.version 7).
V7_BRIEFS = {
    "A": REPO_ROOT / "examples" / "briefs" / "hardened_2026-10-29_v5" / "b1w_hifi_90x60_850_wide_v5.yaml",
    "B": REPO_ROOT / "examples" / "briefs" / "hardened_2026-10-29_v5" / "b3bt_pa_90x60_600_load_tall_v5.yaml",
    "C": REPO_ROOT / "examples" / "briefs" / "hardened_2026-10-29_v5" / "b3a_pa_90x90_480_square_v5.yaml",
}

#: Penalty rows (v6/v7 return PENALTY_FAILED for an unmeasurable valid row) are ranked last.
PENALTY_FLOOR = 1.0e3
HARD_BAND_HI_HZ = 8000.0
TOP_N = 20


# ------------------------------------------------------------------ brief loading


@dataclass(frozen=True)
class BriefConfig:
    name: str
    version: int
    weights: dict
    params: Any


def load_brief(path: Path) -> BriefConfig:
    """Parse a brief YAML and build the matching ``V6Params`` / ``V7Params``."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: brief must be a mapping")
    objective = raw.get("objective") or {}
    version = int(objective.get("version", 0))
    weights = dict(raw.get("weights") or {})
    if version == 6:
        params = V6Params.from_block(objective)
    elif version == 7:
        params = V7Params.from_block(objective)
    else:
        raise ValueError(f"{path}: expected objective.version 6 or 7, got {version!r}")
    return BriefConfig(name=str(raw.get("name") or path.stem), version=version,
                       weights=weights, params=params)


def brief_configs() -> dict[int, dict[str, BriefConfig]]:
    """``{version: {class: BriefConfig}}``. v6 has only the class-B brief, by design."""
    v7 = {cls: load_brief(path) for cls, path in V7_BRIEFS.items()}
    v6_brief = load_brief(V6_BRIEF)
    v6 = {cls: v6_brief for cls in ("A", "B", "C")}
    return {6: v6, 7: v7}


# ------------------------------------------------------------------ row classification


def classify_target(target: Target) -> str:
    """Class A/B/C from the stored target (the repo's own brief-class vocabulary).

    B is any loading-scored target (``z_min >= 0.5`` or a deliberate rising-DI target),
    C is a low-reach PA target (f0 at or below 500 Hz), and everything else is CD class A.
    Deterministic and documented in the evidence report.
    """
    if float(target.z_min) >= 0.5 or float(target.di_slope_target) >= 2.0:
        return "B"
    if target.f0_hz is not None and float(target.f0_hz) <= 500.0:
        return "C"
    return "A"


# ------------------------------------------------------------------ dataset rows


def target_key(target: Target) -> str:
    f0 = "none" if target.f0_hz is None else f"{float(target.f0_hz):g}"
    return (f"{target.coverage_h_deg:g}x{target.coverage_v_deg:g}"
            f"_{target.band_lo_hz:g}-{target.band_hi_hz:g}_f0={f0}")


def _row_to_gate_row(meta: dict, arrays: dict) -> dict:
    """Build the synthetic row ``gate_audit.parse_stored_row`` expects from a dataset record."""
    z = arrays.get("z_throat")
    z_real = None if z is None else np.real(np.asarray(z, dtype=complex))
    return {
        "ok": True,
        "design_hash": meta.get("design_hash"),
        "mesh_hash": meta.get("mesh_hash"),
        "family": meta.get("family"),
        "objective": meta.get("objective"),
        "n_dof": (meta.get("solve") or {}).get("n_dof"),
        "seconds": {"total": (meta.get("solve") or {}).get("seconds")},
        "metrics": {
            "freqs_hz": arrays.get("freqs_hz"),
            "bw_h_deg": arrays.get("bw_h_deg"),
            "bw_v_deg": arrays.get("bw_v_deg"),
            "di_db": arrays.get("di_db"),
            "z_throat_real": z_real,
            "scalars": meta.get("metrics_scalars") or {},
        },
    }


def _finite_array(name: str, arrays: dict, freq_len: int) -> np.ndarray | None:
    raw = arrays.get(name)
    if raw is None:
        return None
    arr = np.asarray(raw, dtype=float)
    if arr.shape != (freq_len,):
        return None
    return arr


def build_scoring_inputs(meta: dict, arrays: dict, parsed: dict) -> tuple[MetricSet, Response | None]:
    """Rebuild the MetricSet (and Response when the polars are stored) from a dataset record."""
    scalars = dict(meta.get("metrics_scalars") or {})
    n = int(parsed["freqs"].size)
    ripples_h = _finite_array("ripple_h_db", arrays, n)
    ripples_v = _finite_array("ripple_v_db", arrays, n)
    on_axis = _finite_array("on_axis_db", arrays, n)
    metrics = MetricSet(
        freqs_hz=np.asarray(parsed["freqs"], dtype=float),
        bw_h_deg=np.asarray(parsed["bw_h"], dtype=float),
        bw_v_deg=np.asarray(parsed["bw_v"], dtype=float),
        di_db=np.asarray(parsed["di_db"], dtype=float),
        di_source=str(scalars.get("di_source") or "balloon"),
        ripple_h_db=(ripples_h if ripples_h is not None else np.full(n, np.nan)),
        ripple_v_db=(ripples_v if ripples_v is not None else np.full(n, np.nan)),
        on_axis_db=(on_axis if on_axis is not None else np.full(n, np.nan)),
        z_throat_real=parsed["z_real"],
        scalars=scalars,
    )
    h_angles = arrays.get("h_angles_deg")
    v_angles = arrays.get("v_angles_deg")
    spl_h = arrays.get("spl_h_db")
    spl_v = arrays.get("spl_v_db")
    if h_angles is None or v_angles is None or spl_h is None or spl_v is None:
        return metrics, None
    resp = Response(
        freqs_hz=np.asarray(parsed["freqs"], dtype=float),
        h_angles_deg=np.asarray(h_angles, dtype=float),
        v_angles_deg=np.asarray(v_angles, dtype=float),
        spl_h_db=np.asarray(spl_h, dtype=float),
        spl_v_db=np.asarray(spl_v, dtype=float),
        balloon_dirs=(None if arrays.get("balloon_dirs") is None
                      else np.asarray(arrays["balloon_dirs"], dtype=float)),
        spl_balloon_db=(None if arrays.get("spl_balloon_db") is None
                        else np.asarray(arrays["spl_balloon_db"], dtype=float)),
        z_throat=(None if arrays.get("z_throat") is None
                  else np.asarray(arrays["z_throat"], dtype=complex)),
        backend=str((meta.get("solve") or {}).get("backend") or ""),
        meta={"distance_m": ((meta.get("solve") or {}).get("observation") or {}).get("distance_m")},
    )
    return metrics, resp


# ------------------------------------------------------------------ scoring


def score_versions(metrics: MetricSet, resp: Response | None, target: Target,
                   briefs: dict[int, dict[str, BriefConfig]], cls: str) -> dict[int, tuple[float, dict]]:
    out: dict[int, tuple[float, dict]] = {}
    v6 = briefs[6][cls]
    v7 = briefs[7][cls]
    out[6] = objective_v6(metrics, resp, True, target, v6.weights, v6.params)
    out[7] = objective_v7(metrics, resp, True, target, v7.weights, v7.params)
    return out


def gate_results(parsed: dict, target: Target) -> dict[str, Any]:
    """Canonical owner gates on the stored arrays. The throat gate needs a mesh (absent here)."""
    f = np.asarray(parsed["freqs"], dtype=float)
    f_x = float(target.f0_effective_hz())
    band_hi = min(HARD_BAND_HI_HZ, float(target.band_hi_hz))
    f0_v = float(target.f0_v_hz) if target.f0_v_hz is not None else f_x
    h = ga.gate_h(f, parsed["bw_h"], target.coverage_h_deg, f_x, band_hi)
    v = ga.gate_v(f, parsed["bw_v"], target.coverage_v_deg, f_x, f0_v, band_hi)
    di = ga.gate_di_rise(f, parsed["di_db"], f_x, band_hi)
    bw8k = ga.gate_bw8k(f, parsed["bw_h"], parsed["bw_v"],
                        target.coverage_h_deg, target.coverage_v_deg, band_hi)
    driver_f11 = None
    if target.driver_exit_radius_mm is not None:
        driver_f11 = float(BESSEL_J1P_11 * C_AIR
                           / (2.0 * math.pi * (float(target.driver_exit_radius_mm) / 1000.0)))
    f11 = ga.resolve_f11_hz({"loaded_hi_hz": target.loaded_hi_hz,
                             "driver_f11_hz": driver_f11}, parsed.get("f11_hz"))
    load = ga.gate_loading(f, parsed["z_real"], f_x, f11_hz=f11, band_hi=band_hi)
    gates: dict[str, Any] = {"h": h.passed, "v": v.passed, "di": di.passed,
                             "bw8k": bw8k.gate.passed, "load": load.gate.passed}
    gates["pass_all_no_throat"] = all(gates[k] for k in ("h", "v", "di", "bw8k", "load"))
    gates["throat"] = None              # unresolved: the dataset stores no mesh
    gates["unresolved"] = sorted({
        k for k, res in (("h", h), ("v", v), ("di", di), ("bw8k", bw8k.gate),
                         ("load", load.gate))
        if res.unresolved
    } | {"throat"})
    gates["lfp20_hz"] = load.lfp20_hz
    gates["rez_min_from_fx"] = load.rez_min_from_fx
    gates["f11_hz"] = load.f11_hz
    return gates


# ------------------------------------------------------------------ dataset walk


def iter_dataset_rows(dataset_root: Path):
    """Yield ``(shard, row_index, meta, arrays)`` for every row whose arrays are present."""
    shard_files = sorted(dataset_root.glob("shard-*.jsonl"))
    for shard_path in shard_files:
        try:
            shard = int(shard_path.stem.split("-")[1])
        except (IndexError, ValueError):
            continue
        with shard_path.open("r", encoding="utf-8") as fh:
            for row, line in enumerate(fh):
                line = line.strip()
                if not line:
                    continue
                try:
                    meta = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not meta.get("ok"):
                    continue
                npz_path = dataset_root / f"shard-{shard:04d}" / f"rec-{row:04d}.npz"
                if not npz_path.is_file():
                    continue
                try:
                    with np.load(npz_path, allow_pickle=False) as z:
                        arrays = {k: z[k] for k in z.files}
                except Exception:  # noqa: BLE001 - a corrupt array file is a skip, not a crash
                    continue
                yield shard, row, meta, arrays


def score_dataset(dataset_root: Path, briefs: dict[int, dict[str, BriefConfig]],
                  limit: int | None = None) -> dict:
    counters: Counter = Counter()
    rows: list[dict] = []
    for shard, row, meta, arrays in iter_dataset_rows(dataset_root):
        counters["rows_seen"] += 1
        if limit is not None and len(rows) >= limit:
            break
        try:
            target = Target.from_dict(meta.get("target") or {})
        except Exception:  # noqa: BLE001 - an old/invalid target is a skip with a reason
            counters["target_invalid"] += 1
            continue
        parsed = ga.parse_stored_row(_row_to_gate_row(meta, arrays), "dataset")
        if parsed is None:
            counters["parse_failed"] += 1
            continue
        try:
            metrics, resp = build_scoring_inputs(meta, arrays, parsed)
            cls = classify_target(target)
            scored = score_versions(metrics, resp, target, briefs, cls)
        except Exception:  # noqa: BLE001 - one bad row must not stop the sweep
            counters["scoring_error"] += 1
            continue
        gates = gate_results(parsed, target)
        j6, t6 = scored[6]
        j7, t7 = scored[7]
        for version, j in ((6, j6), (7, j7)):
            if not math.isfinite(float(j)):
                counters[f"nonfinite_v{version}"] += 1
        if not (math.isfinite(float(j6)) and math.isfinite(float(j7))):
            counters["nonfinite_pair"] += 1
            continue
        rows.append({
            "shard": shard,
            "row": row,
            "design_hash": str(meta.get("design_hash") or ""),
            "family": str(meta.get("family") or ""),
            "stored_version": meta.get("objective_version"),
            "class": cls,
            "target_key": target_key(target),
            "J_v6": float(j6),
            "J_v7": float(j7),
            "v6_load_near": float(t6.get("load_near", float("nan"))),
            "v6_z_smooth": float(t6.get("z_smooth", float("nan"))),
            "v7_load": float(t7.get("load", float("nan"))),
            "v7_flat_cv": float(t7.get("flat_cv", float("nan"))),
            "v7_lfp20_hz": float(t7.get("lfp20_hz", float("nan"))),
            "gate_h": gates["h"], "gate_v": gates["v"], "gate_di": gates["di"],
            "gate_bw8k": gates["bw8k"], "gate_load": gates["load"],
            "gate_pass_all_no_throat": gates["pass_all_no_throat"],
            "gate_unresolved": ";".join(gates["unresolved"]),
        })
        counters["scored"] += 1
        if len(rows) % 2000 == 0:
            print(f"  scored {len(rows)} rows ...", flush=True)
    counters["unique_designs"] = len({(r["design_hash"], r["target_key"]) for r in rows})
    return {"rows": rows, "counters": dict(counters)}


# ------------------------------------------------------------------ analysis


def _better(j: float) -> tuple[int, float]:
    """Sort key: finite rows first, penalty rows last."""
    return (0, j) if math.isfinite(j) and j < PENALTY_FLOOR else (1, j)


def unique_best(rows: list[dict], version: int) -> list[dict]:
    best: dict[tuple[str, str], dict] = {}
    key = f"J_v{version}"
    for r in rows:
        k = (r["design_hash"], r["target_key"])
        cur = best.get(k)
        if cur is None or _better(r[key]) < _better(cur[key]):
            best[k] = r
    return sorted(best.values(), key=lambda r: (_better(r[key]), r["design_hash"],
                                                r["target_key"]))


def class_summary(rows: list[dict]) -> dict:
    out: dict = {}
    for cls in ("A", "B", "C"):
        subset = [r for r in rows if r["class"] == cls]
        if not subset:
            continue
        u6 = unique_best(subset, 6)
        u7 = unique_best(subset, 7)
        j6 = np.array([r["J_v6"] for r in u6], dtype=float)
        j7 = np.array([r["J_v7"] for r in u7], dtype=float)
        # Kendall tau pairs the two scores on the SAME (design, target) keys.
        keyed6 = {(r["design_hash"], r["target_key"]): r["J_v6"] for r in u6}
        keyed7 = {(r["design_hash"], r["target_key"]): r["J_v7"] for r in u7}
        shared = sorted(set(keyed6) & set(keyed7))
        tau = float("nan")
        if len(shared) >= 2:
            a = np.array([keyed6[k] for k in shared], dtype=float)
            b = np.array([keyed7[k] for k in shared], dtype=float)
            if len(set(a.tolist())) > 1 and len(set(b.tolist())) > 1:
                tau = float(kendalltau(a, b)[0])
        top6 = {k for k in
                ((r["design_hash"], r["target_key"]) for r in u6[:TOP_N])}
        top7 = {k for k in
                ((r["design_hash"], r["target_key"]) for r in u7[:TOP_N])}
        # Kendall tau restricted to the union of the two top-20 sets, so the rank agreement of the
        # shortlists themselves is visible next to the all-design tau above.
        tau_top = float("nan")
        union = sorted(top6 | top7)
        if len(union) >= 2:
            a = np.array([keyed6[k] for k in union], dtype=float)
            b = np.array([keyed7[k] for k in union], dtype=float)
            if len(set(a.tolist())) > 1 and len(set(b.tolist())) > 1:
                tau_top = float(kendalltau(a, b)[0])
        gates = {
            "rows": len(subset),
            "designs": len({(r["design_hash"], r["target_key"]) for r in subset}),
            "row_pass": {g: sum(1 for r in subset if r.get(g)) for g in
                         ("gate_h", "gate_v", "gate_di", "gate_bw8k", "gate_load",
                          "gate_pass_all_no_throat")},
            "unique_pass": {g: sum(1 for r in unique_best(subset, 6) if r.get(g)) for g in
                            ("gate_h", "gate_v", "gate_di", "gate_bw8k", "gate_load",
                             "gate_pass_all_no_throat")},
            "top_overlap": len(top6 & top7),
            "penalty_v6": sum(1 for r in subset if r["J_v6"] >= PENALTY_FLOOR),
            "penalty_v7": sum(1 for r in subset if r["J_v7"] >= PENALTY_FLOOR),
        }
        out[cls] = {
            "rows": len(subset),
            "unique_designs": len(shared),
            "kendall_tau": tau,
            "kendall_tau_top20_union": tau_top,
            "top20_overlap": len(top6 & top7),
            "top20_v6": u6[:TOP_N],
            "top20_v7": u7[:TOP_N],
            "gates": gates,
        }
    return out


# ------------------------------------------------------------------ output


CSV_FIELDS = ("shard", "row", "design_hash", "family", "class", "target_key",
              "stored_version", "J_v6", "J_v7", "v6_load_near", "v6_z_smooth",
              "v7_load", "v7_flat_cv", "v7_lfp20_hz", "gate_h", "gate_v", "gate_di",
              "gate_bw8k", "gate_load", "gate_pass_all_no_throat", "gate_unresolved")


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _fmt(x: Any, digits: int = 4) -> str:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return "n/a"
    return f"{v:.{digits}f}" if math.isfinite(v) else "n/a"


def _top_table(rows: list[dict], version: int) -> list[str]:
    jkey = f"J_v{version}"
    lines = ["| Rank | Design | Family | Target | J | gate (no throat) |",
             "|---:|---|---|---|---:|---|"]
    for rank, r in enumerate(rows, 1):
        gate = "pass" if r.get("gate_pass_all_no_throat") else "fail"
        lines.append(f"| {rank} | `{r['design_hash']}` | {r['family']} | "
                     f"`{r['target_key']}` | {_fmt(r[jkey])} | {gate} |")
    return lines


def write_summary_json(path: Path, summary: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    def clean(obj):
        if isinstance(obj, dict):
            return {k: clean(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [clean(v) for v in obj]
        if isinstance(obj, float) and not math.isfinite(obj):
            return None
        return obj

    path.write_text(json.dumps(clean(summary), indent=2, sort_keys=True), encoding="utf-8")


def write_markdown(path: Path, summary: dict, csv_path: Path) -> None:
    lines: list[str] = []
    lines.append("# Objective v6 vs v7 offline re-score")
    lines.append("")
    lines.append("Generated by `tools/rescore/rescore_v6_v7.py` from the committed dataset shards "
                 "(`shard-*.jsonl` + `shard-NNNN/rec-NNNN.npz`). Zero GPU, zero solver: the stored "
                 "metric arrays are re-scored, not re-solved. `dataset/` is never written.")
    lines.append("")
    lines.append("## Method")
    lines.append("")
    lines.append("- Each stored row keeps its OWN `target`; the brief supplies the version's "
                 "weights + objective block.")
    lines.append("- Rows are read with `gate_audit.parse_stored_row` (version-agnostic) and "
                 "re-scored with `objective_v6` and `objective_v7`.")
    lines.append("- Class A/B/C comes from the stored target: A = CD default, B = loading-scored "
                 "(`z_min >= 0.5` or `di_slope_target >= 2`), C = low-reach (`f0 <= 500 Hz`).")
    lines.append("- v6 has one shipped brief only (`native_lecleach_1200_1in_v6`, class B); it is "
                 "applied to every class. v7 uses the class-matched hardened brief.")
    lines.append("- Top-20 is unique by (design hash, target); ties/penalties sort last.")
    lines.append("- Kendall tau is over every unique design scored under BOTH versions in the class.")
    lines.append("- Gate counts use the canonical `gate_audit` definitions. The throat gate is "
                 "**UNRESOLVED** for every row: the dataset stores no mesh, so "
                 "`gate_pass_all_no_throat` excludes it.")
    lines.append("")
    lines.append(f"- Scored rows: **{summary['counters'].get('scored', 0)}** "
                 f"(seen {summary['counters'].get('rows_seen', 0)}, "
                 f"skipped target_invalid {summary['counters'].get('target_invalid', 0)}, "
                 f"parse_failed {summary['counters'].get('parse_failed', 0)}, "
                 f"scoring_error {summary['counters'].get('scoring_error', 0)})")
    lines.append(f"- CSV: `{csv_path.name}`")
    lines.append("")
    for cls in ("A", "B", "C"):
        block = summary["classes"].get(cls)
        if not block:
            continue
        lines.append(f"## Class {cls}")
        lines.append("")
        lines.append(f"- Rows: **{block['rows']}**; unique (design, target): "
                     f"**{block['unique_designs']}**")
        lines.append(f"- Kendall tau (v6 vs v7): **{_fmt(block['kendall_tau'], 4)}** "
                     f"(all shared designs)")
        lines.append(f"- Kendall tau on the top-20 union: "
                     f"**{_fmt(block.get('kendall_tau_top20_union'), 4)}**")
        lines.append(f"- Top-20 overlap: **{block['top20_overlap']} / 20**")
        lines.append(f"- Rows scoring the failure penalty: v6 {block['gates']['penalty_v6']}, "
                     f"v7 {block['gates']['penalty_v7']}")
        g = block["gates"]
        lines.append("")
        lines.append("| Gate | Row passes | Unique-design passes |")
        lines.append("|---|---:|---:|")
        for key, label in (("gate_h", "H"), ("gate_v", "V"), ("gate_di", "DI"),
                           ("gate_bw8k", "BW8K"), ("gate_load", "Loading")):
            lines.append(f"| {label} | {g['row_pass'][key]} | {g['unique_pass'][key]} |")
        lines.append(f"| pass_all (no throat) | {g['row_pass']['gate_pass_all_no_throat']} | "
                     f"{g['unique_pass']['gate_pass_all_no_throat']} |")
        lines.append(f"| Throat | unresolved (no mesh in dataset) | unresolved |")
        lines.append("")
        lines.append("### Top 20 under v6")
        lines.append("")
        lines.extend(_top_table(block["top20_v6"], 6))
        lines.append("")
        lines.append("### Top 20 under v7")
        lines.append("")
        lines.extend(_top_table(block["top20_v7"], 7))
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ------------------------------------------------------------------ CLI


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Offline objective v6 vs v7 re-score (no GPU, no solver)")
    ap.add_argument("--dataset", type=Path, default=REPO_ROOT / "dataset")
    ap.add_argument("--out", type=Path, default=REPO_ROOT / "scratch" / "rescore_2026-11-12")
    ap.add_argument("--md", type=Path, default=REPO_ROOT / "docs" / "evidence"
                    / "RESCORE_V6_V7_2026-11-12.md")
    ap.add_argument("--limit", type=int, default=None,
                    help="optional max scored rows (for a quick smoke run)")
    args = ap.parse_args(argv)

    if not args.dataset.is_dir():
        print(f"error: --dataset {args.dataset} is not a directory", file=sys.stderr)
        return 2
    briefs = brief_configs()
    print(f"v6 brief: {briefs[6]['A'].name}")
    print("v7 briefs: " + ", ".join(f"{k}={v.name}" for k, v in sorted(briefs[7].items())))
    result = score_dataset(args.dataset, briefs, limit=args.limit)
    rows = result["rows"]
    classes = class_summary(rows)
    summary = {"counters": result["counters"],
               "briefs": {"v6": {k: v.name for k, v in briefs[6].items()},
                          "v7": {k: v.name for k, v in briefs[7].items()}},
               "classes": classes}
    args.out.mkdir(parents=True, exist_ok=True)
    csv_path = args.out / "rescore_v6_v7.csv"
    write_csv(csv_path, rows)
    write_summary_json(args.out / "summary.json", summary)
    write_markdown(args.md, summary, csv_path)
    print(f"wrote {len(rows)} rows to {csv_path} and {args.md}")
    print("SUMMARY " + json.dumps({k: {"rows": v["rows"], "tau": v["kendall_tau"],
                                       "top20_overlap": v["top20_overlap"]}
                                   for k, v in classes.items()}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
