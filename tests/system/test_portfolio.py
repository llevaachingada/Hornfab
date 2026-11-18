"""Stage 3 tests: diverse selection determinism, budget identity, alternate-screen honesty."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hornlab_search.compare.hornfab_side import canonical_to_accel  # noqa: E402
from hornlab_search.system import contracts as C  # noqa: E402
from hornlab_search.system import horn_assets as HA  # noqa: E402
from hornlab_search.system import horn_import, portfolio  # noqa: E402


def _asset(asset_id: str, family: str, brief: str, design: str,
           freqs=(700.0, 1000.0, 1300.0)) -> C.HornAsset:
    return C.HornAsset(
        asset_id=asset_id, design_hash=design, response_path=f"nonvirtual/{asset_id}/response.npz",
        mesh_path=None, geometry=C.GeometryMetadata(family=family, brief_id=brief),
        available_fields=frozenset({"p_balloon", "p_h", "p_v", "spl_balloon_db", "freqs_hz"}),
        quality="MAGNITUDE_ONLY", freqs_hz=tuple(freqs), source_basis=None,
    )


def test_selection_is_deterministic_and_diverse() -> None:
    assets = [
        _asset("a1", "OSSE", "brief1", "d1"),
        _asset("a2", "OSSE", "brief1", "d2"),
        _asset("a3", "OSSE", "brief2", "d3"),
        _asset("a4", "R-OSSE", "brief1", "d4"),
        _asset("a5", "FREEFORM", "lecleach", "d5"),
        _asset("a6", "ICW", "brief1", "d6"),
        _asset("a7", "ICW", "brief1", "d7"),
        _asset("a8", "OSSE", "brief3", "d8"),
        # ineligible: no balloon -> always reported as lost, never silently dropped
        C.HornAsset(asset_id="a9", design_hash="d9", response_path="x",
                    mesh_path=None, geometry=C.GeometryMetadata(family="OSSE"),
                    available_fields=frozenset({"spl_h_db"}), quality="MAGNITUDE_ONLY",
                    freqs_hz=(700.0,), source_basis=None),
    ]
    chosen, rejected = portfolio.select_diverse_assets(assets, k=4)
    buckets = {portfolio._bucket(a) for a in chosen}
    assert chosen == portfolio.select_diverse_assets(assets, k=4)[0]
    assert len(chosen) == 4
    assert len(buckets) >= 3, "round-robin must span distinct family|brief buckets"
    assert any(r["asset_id"] == "a9" and r["reason"].startswith("no p_balloon")
               for r in rejected)


def _inv(assets: tuple) -> HA.InventoryResult:
    return HA.InventoryResult(runs_root="virtual", runs_scanned=len(assets),
                              design_dirs_scanned=len(assets), skipped_dirs=0,
                              duplicates_collapsed=0, assets=tuple(assets))


def _realish_asset(tmp_path: Path, asset_id: str, family: str, brief: str) -> C.HornAsset:
    """An asset backed by a real synthetic NPZ (balloon + cuts), like the stored layout."""
    freqs = np.array([700.0, 1000.0, 1300.0])
    theta = np.linspace(0.0, np.pi, 73)
    dirs = np.stack([np.sin(theta), np.zeros_like(theta), np.cos(theta)], axis=1)
    p_vel = np.ones((3, 1)) * np.exp(-0.5 * (theta / 1.2) ** 2)[None, :].astype(complex)
    ang = np.linspace(-90.0, 90.0, 73)
    shape = np.exp(-0.5 * (np.radians(ang) / 1.0) ** 2).astype(complex)
    pv = np.ones((3, 1)) * shape[None, :]
    path = tmp_path / f"{asset_id}.npz"
    np.savez(path, freqs_hz=freqs, h_angles_deg=ang, v_angles_deg=ang,
             spl_h_db=90.0 + 20.0 * np.log10(np.abs(pv)),
             spl_v_db=90.0 + 20.0 * np.log10(np.abs(pv)),
             spl_balloon_db=90.0 + 20.0 * np.log10(np.abs(p_vel)),
             balloon_dirs=dirs,
             p_h=canonical_to_accel(pv, freqs), p_v=canonical_to_accel(pv, freqs),
             p_balloon=canonical_to_accel(p_vel, freqs),
             meta=np.array(json.dumps({"distance_m": 2.0})), backend=np.array("synthetic"))
    return C.HornAsset(
        asset_id=asset_id, design_hash=f"d{asset_id}", response_path=str(path),
        mesh_path=None, geometry=C.GeometryMetadata(family=family, brief_id=brief),
        available_fields=frozenset({"p_balloon", "p_h", "p_v", "spl_balloon_db", "freqs_hz"}),
        quality="MAGNITUDE_ONLY", freqs_hz=(700.0, 1000.0, 1300.0), source_basis=None,
    )


def _spec(**overrides: Any) -> C.SystemSpecV1:
    fields: dict[str, Any] = dict(
        experiment_id="portfolio_test",
        mode="fixed_horn",
        horn=C.HornRef(asset_id="unused"),
        woofer=C.WooferRef(driver_id="faitalpro_12pr300"),
        cabinet=C.VentedBoxRanges(net_volume_l_range=(35.0, 60.0), tuning_hz_range=(30.0, 40.0),
                                  port_throat_area_cm2_range=(60.0, 100.0),
                                  port_nfr_range=(0.0, 0.0)),
        assembly=C.AssemblyRanges(),
        dsp=C.DspRanges(xo_hz_range=(700.0, 1300.0)),
        target=C.SystemTargets(listening_angle_h_deg=(-30.0, 30.0),
                               listening_angle_v_deg=(-15.0, 15.0), low_freq_f3_hz_max=55.0),
        fidelity="screen_only",
    )
    fields.update(overrides)
    return C.SystemSpecV1(**fields)


def test_portfolio_budget_identity_and_visibility(tmp_path: Path) -> None:
    """Same spec/limit/grid for every horn; lost candidates keep rows; never ranks horn J."""
    inv = _inv((_realish_asset(tmp_path, "p1", "OSSE", "b1"),
                _realish_asset(tmp_path, "p2", "FREEFORM", "b2"),
                # ineligible (no balloon field) -> reported as a lost candidate row
                C.HornAsset(asset_id="p3_no_balloon", design_hash="d3",
                            response_path="nonvirtual/p3/response.npz", mesh_path=None,
                            geometry=C.GeometryMetadata(family="ICW", brief_id="b3"),
                            available_fields=frozenset({"spl_h_db"}), quality="MAGNITUDE_ONLY",
                            freqs_hz=(700.0,), source_basis=None)))
    result = portfolio.run_portfolio(_spec(), driver_stems=("faitalpro_12pr300",),
                                     inventory=inv, k=2, limit_boxes=3)
    # budget identity: every (horn, driver) cell has exactly the same box-candidate count
    cells: dict[tuple[str, str], int] = {}
    for row in result.rows:
        if row.get("lost_candidate"):
            continue
        key = (row["portfolio"]["asset_id"], row["portfolio"]["driver"])
        cells[key] = cells.get(key, 0) + 1
    assert len(cells) == 2 and len(set(cells.values())) == 1, cells
    # lost-candidate rows exist and name their reason
    lost = [r for r in result.rows if r.get("lost_candidate")]
    assert lost and all("reason" in r["portfolio"] for r in lost)
    # the report never loads or ranks a horn objective value
    text = result.report["json"] + result.report["markdown"]
    assert '"objective"' not in text and "best J" not in text
    # deterministic: same inputs -> same study id and identical rows
    second = portfolio.run_portfolio(_spec(), driver_stems=("faitalpro_12pr300",),
                                     inventory=inv, k=2, limit_boxes=3)
    assert second.meta["study_id"] == result.meta["study_id"]
    assert second.rows == result.rows
    # rows carry top-level axis aliases for the renderer
    sample = next(r for r in result.rows if not r.get("lost_candidate"))
    assert sample["lf_headroom"] == sample["axes"]["lf_headroom"]


def test_portfolio_reports_screen_disagreement(tmp_path: Path, monkeypatch) -> None:
    """The alternate cuts screen runs beside the balloon screen; disagreement is a REPORT."""
    inv = _inv((_realish_asset(tmp_path, "p1", "OSSE", "b1"),))

    def fake_cuts(converted: Any, xo_points) -> dict[float, float | None]:
        return {float(x): 40.0 for x in xo_points}   # deliberately far from the balloon screen

    monkeypatch.setattr(portfolio, "cuts_beamwidth_by_xo", fake_cuts)
    result = portfolio.run_portfolio(_spec(), driver_stems=("faitalpro_12pr300",),
                                     inventory=inv, k=1, limit_boxes=2)
    flagged = [r for r in result.rows if not r.get("lost_candidate")
               and r["portfolio"]["screen_disagreement_flag"]]
    assert flagged, "a far alternate screen must be visible as disagreement rows"
    assert all(r["portfolio"]["alternate_screen_note"] for r in flagged)
    # the alternate is a report column, never a forced rejection or a score edit
    assert any(r["crossover_physics"] in ("SCREEN", "FAIL") for r in flagged)


def _cuts_npz(tmp_path: Path, width_deg: float) -> Path:
    freqs = np.array([700.0, 1000.0, 1300.0])
    ang = np.linspace(-90.0, 90.0, 181)
    shape = np.exp(-0.5 * (np.radians(ang) / math.radians(width_deg)) ** 2)
    pv = np.ones((3, 1)) * shape[None, :]
    path = tmp_path / f"cuts_{width_deg:g}.npz"
    np.savez(path, freqs_hz=freqs, h_angles_deg=ang, v_angles_deg=ang,
             spl_h_db=90.0 + 20.0 * np.log10(pv), spl_v_db=90.0 + 20.0 * np.log10(pv),
             p_h=canonical_to_accel(pv, freqs), p_v=canonical_to_accel(pv, freqs),
             meta=np.array(json.dumps({"distance_m": 2.0})), backend=np.array("synthetic"))
    return path


def test_cuts_beamwidth_by_xo_matches_the_expected_width(tmp_path: Path) -> None:
    """A gaussian -6 dB half-width of ~53.6 deg reads ~107 degen wide in the cuts screen."""
    # exp(-0.5 (x/w)^2) falls 6 dB (factor 0.5) at |x| = w*sqrt(2 ln 2)
    asset = C.HornAsset(
        asset_id="cuts", design_hash="d", response_path=str(_cuts_npz(tmp_path, 53.6)),
        mesh_path=None, geometry=C.GeometryMetadata(family="OSSE"),
        available_fields=frozenset({"p_h", "p_v", "spl_h_db", "spl_v_db", "freqs_hz"}),
        quality="MAGNITUDE_ONLY", freqs_hz=(700.0, 1000.0, 1300.0), source_basis=None,
    )
    cuts = horn_import.convert_asset(asset, mode="cuts")
    by_xo = portfolio.cuts_beamwidth_by_xo(cuts, (700.0, 1000.0, 1300.0))
    # the chord spans -53.6*sqrt(2 ln 2) .. +... ; the alternate screen reports chord/2,
    # the same angular-radius quantity as the balloon screen
    expected = 53.6 * math.sqrt(2.0 * math.log(2.0))
    for value in by_xo.values():
        assert value is not None and value == pytest.approx(expected, rel=0.02)
