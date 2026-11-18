"""Stage 3 portfolio screening: diverse saved horns under ONE identical CPU budget.

Rules (master doc §6.2/§10.4 Stage 3):
* Selection is stratified by (family, brief) coverage FIRST, never by a scalar objective.
  v7/v9 horn J values are NOT loaded here at all — they exist in different objective versions
  and must never be compared "as if common"; this module simply never reads them.
* Every selected horn gets the IDENTICAL inner budget: same driver set, same spec ranges,
  same box sample size, same crossover grid (via :func:`optimize.run_pilot`).
* A second, independent screen approximation (plane-cuts -6 dB width, max of H/V planes)
  runs beside the balloon screen; disagreements are REPORTED rows, not silent corrections
  (false-negative visibility). Nothing is deleted: rejected/lost candidates keep rows.
* Outputs are deterministic; reruns reproduce byte-identical reports and ids.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

import numpy as np

from hornlab_search.system import contracts as C, optimize, score
from hornlab_search.system import horn_assets as HA
from hornlab_search.system import horn_import, provenance

__all__ = ["PortfolioResult", "select_diverse_assets", "run_portfolio", "cuts_beamwidth_by_xo"]

#: Disagreement tolerance between the balloon-radius screen and the cuts-width screen (deg).
SCREEN_DISAGREE_TOL_DEG = 8.0


@dataclass(frozen=True)
class PortfolioResult:
    asset_summary: tuple[dict, ...]
    rows: tuple[dict, ...]
    report: Mapping[str, str]
    meta: dict[str, Any] = field(default_factory=dict)

    def to_manifest_payload(self) -> dict[str, Any]:
        return {
            "kind": "system_portfolio_v0",
            "study_id": self.meta.get("study_id"),
            "asset_summary": list(self.asset_summary),
            "rows": list(self.rows),
            "meta": dict(self.meta),
        }


def _bucket(asset: C.HornAsset) -> str:
    family = asset.geometry.family or "UNKNOWN"
    brief = asset.geometry.brief_id or "UNKNOWN"
    return f"{family}|{brief[:40]}"


def select_diverse_assets(assets: Sequence[C.HornAsset], k: int = 6) -> tuple[tuple[C.HornAsset, ...], tuple[dict, ...]]:
    """Round-robin over (family, brief) buckets, asset_id order inside each bucket.

    Deterministic; eligibility = complex-balloon-capable stored fields (the screens need them)
    and a nonempty frequency axis. Rejections stay visible in ``rejected`` rows with reasons.
    """
    eligible: dict[str, list[C.HornAsset]] = {}
    rejected: list[dict] = []
    for asset in sorted(assets, key=lambda a: (a.asset_id,)):
        if "p_balloon" not in asset.available_fields:
            rejected.append({"asset_id": asset.asset_id, "reason": "no p_balloon field",
                             "family": asset.geometry.family})
            continue
        if len(asset.freqs_hz) < 2:
            rejected.append({"asset_id": asset.asset_id, "reason": "degenerate frequency axis",
                             "family": asset.geometry.family})
            continue
        eligible.setdefault(_bucket(asset), []).append(asset)

    buckets = sorted(eligible)
    chosen: list[C.HornAsset] = []
    taken: set[str] = set()
    idx = 0
    while len(chosen) < k and any(idx < len(eligible[b]) for b in buckets):
        for bucket in buckets:
            if idx < len(eligible[bucket]) and len(chosen) < k:
                asset = eligible[bucket][idx]
                bucket_ids = {a.design_hash for a in chosen}
                if asset.design_hash in bucket_ids or asset.asset_id in taken:
                    continue
                taken.add(asset.asset_id)
                chosen.append(asset)
        idx += 1
    summary = [{"asset_id": a.asset_id, "design_hash": a.design_hash,
                "family": a.geometry.family, "brief_id": a.geometry.brief_id,
                "bucket": _bucket(a),
                "freq_lo_hz": a.freqs_hz[0], "freq_hi_hz": a.freqs_hz[-1],
                "n_freqs": len(a.freqs_hz), "quality": a.quality}
               for a in chosen]
    return tuple(chosen), tuple(rejected + [
        {"asset_id": a.asset_id,
         "reason": f"bucket {_bucket(a)} already filled (round-robin depth {idx})",
         "family": a.geometry.family}
        for b in buckets for a in eligible[b][idx:]][:16])


def cuts_beamwidth_by_xo(converted: Any, xo_points: Sequence[float]) -> dict[float, float | None]:
    """Alternate screen: plane-cuts -6 dB HALF-ANGLE, max(H,V)-chord/2, at each crossover.

    Reference level per plane/frequency is the max over the +-10 deg on-axis band; the chord is
    the widest -6 dB span of that plane. Half of that chord is the same quantity as the
    balloon-radius screen (angular radius from the main-lobe peak), so the comparison is
    apples-to-apples. Per-frequency values are log-interpolated to each ``xo``.
    """
    resp = converted.response
    p = resp.p_by_excitation["horn"]
    half = p.shape[1] // 2
    angles = np.linspace(-90.0, 90.0, half)
    near = np.abs(angles) <= 10.0
    f = resp.frequencies_hz
    widths = np.full(f.shape, np.nan)
    for lo, hi in ((0, half), (half, p.shape[1])):
        db = 20.0 * np.log10(np.maximum(np.abs(p[:, lo:hi]), 1e-30))
        for i in range(db.shape[0]):
            ref = float(np.max(db[i][near]))
            idxs = np.nonzero(db[i] >= ref - 6.0)[0]
            if idxs.size == 0:
                continue
            span = float(angles[idxs[-1]] - angles[idxs[0]])
            half_chord = 0.5 * span
            if not np.isfinite(widths[i]) or half_chord > widths[i]:
                widths[i] = half_chord   # max(nan, x) is nan under Python comparison semantics
    out: dict[float, float | None] = {}
    for xo in xo_points:
        out[float(xo)] = (float(np.interp(math.log(xo), np.log(f), widths))
                          if bool(np.any(np.isfinite(widths))) and f.size >= 2 else None)
    return out


def run_portfolio(spec: C.SystemSpecV1, *,
                  driver_stems: Sequence[str],
                  inventory: HA.InventoryResult | None = None,
                  runs_root: str | None = None,
                  scan_limit: int = 60,
                  k: int = 6,
                  limit_boxes: int = 8,
                  driver_ts_dir: str | None = None,
                  out_dir: str | None = None) -> PortfolioResult:
    """One portfolio pass: identical budget for every (horn, driver) cell, report-only.

    ``inventory`` may be injected (tests); otherwise a bounded newest-first scan builds one.
    """
    if inventory is None:
        inventory = HA.inventory_runs(runs_root, limit=scan_limit)
    selected, rejected = select_diverse_assets(inventory.assets, k=k)
    if not selected:
        raise C.DataQualityError("no eligible horn assets for the portfolio screen")

    rows: list[dict] = []
    asset_summary: list[dict] = []
    xo_grid = optimize._xo_grid(spec.dsp)
    for asset in selected:
        converted_balloon = horn_import.convert_asset(asset, mode="balloon")
        converted_cuts = (horn_import.convert_asset(asset, mode="cuts")
                          if {"p_h", "p_v"} <= set(asset.available_fields) else None)
        cuts_by_xo = (None if converted_cuts is None
                      else cuts_beamwidth_by_xo(converted_cuts, xo_grid))
        entry = {"asset_id": asset.asset_id, "design_hash": asset.design_hash,
                 "family": asset.geometry.family, "brief_id": asset.geometry.brief_id,
                 "freq_range_hz": [asset.freqs_hz[0], asset.freqs_hz[-1]],
                 "n_freqs": len(asset.freqs_hz),
                 "quality": asset.quality,
                 "cuts_screen_by_xo_deg": cuts_by_xo}
        asset_summary.append(entry)

        for stem in driver_stems:
            result = optimize.run_pilot(
                spec, driver_stem=stem, asset=asset,
                limit_boxes=limit_boxes, driver_ts_dir=driver_ts_dir)
            for row in result.rows:
                grow = dict(row)
                disagreement = None
                bal: dict = row["crossover_screen"]["horn_bw_deg"]
                if cuts_by_xo is not None:
                    diffs = []
                    for k, bal_v in bal.items():
                        cuts_v = cuts_by_xo.get(k)
                        if bal_v is not None and cuts_v is not None:
                            diffs.append(abs(float(bal_v) - float(cuts_v)))
                    disagreement = max(diffs, default=None)
                grow["portfolio"] = {
                    "asset_id": asset.asset_id,
                    "family": asset.geometry.family,
                    "brief_id": asset.geometry.brief_id,
                    "driver": stem,
                    "alternate_cuts_half_angle_deg": cuts_by_xo,
                    "alternate_screen_note": ("max(H,V) plane-cuts -6 dB chord/2 (half-angle, "
                                              "same quantity as the balloon radius) at each xo; "
                                              "screen approximation; disagreements are report-"
                                              "only, never silent corrections"),
                    "screen_disagreement_deg": disagreement,
                    "screen_disagreement_flag": bool(
                        disagreement is not None and disagreement > SCREEN_DISAGREE_TOL_DEG),
                }
                grow["row_id"] = f"{asset.asset_id[:6]}|{stem}|{row['row_id']}"
                # top-level axis aliases again (renderer convention)
                for name in ("feasible_construction", "lf_headroom", "crossover_physics",
                             "angular_field"):
                    grow[name] = row["axes"][name]
                rows.append(grow)
    rejected_rows = [
        {"row_id": f"lost|{i:02d}", "portfolio": {"asset_id": r["asset_id"],
                                                  "reason": r["reason"],
                                                  "family": r.get("family")},
         "lost_candidate": True}
        for i, r in enumerate(rejected)]
    rows_out = rows + rejected_rows
    report = score.render_report(
        rows_out, axes=("feasible_construction", "lf_headroom", "crossover_physics",
                        "angular_field"))
    study_hash = C.system_study_id({
        "experiment_id": spec.experiment_id,
        "mode": spec.mode,
        "drivers": tuple(sorted(driver_stems)),
        "assets": tuple(sorted(a.asset_id for a in selected)),
        "k": k, "limit_boxes": limit_boxes, "scan_limit": scan_limit,
        "seed": "deterministic-no-rng",
        "note": "not a horn leaderboard; v9/v7 J never loaded",
    })
    result = PortfolioResult(
        asset_summary=tuple(asset_summary), rows=tuple(rows_out), report=report,
        meta={"study_id": study_hash,
              "system_objective_version": C.SYSTEM_OBJECTIVE_VERSION,
              "fidelity_cap": "screen_only",
              "same_budget_per_cell": True,
              "rejected_count": len(rejected),
              "gpu_or_solves_used": False,
              "screen_disagree_tol_deg": SCREEN_DISAGREE_TOL_DEG})
    if out_dir is not None:
        case = provenance.new_case_dir("portfolio_screen", store_root=out_dir, tag="portfolio")
        provenance.write_manifest(case, result.to_manifest_payload())
        result.meta["case_dir"] = str(case)
    return result
