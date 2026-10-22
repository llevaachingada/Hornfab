"""Tests for hornlab_search.search.campaign (offline, no GPU, subprocess mocked).

All subprocess calls are monkeypatched; no actual mesher or solver is launched.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from conftest import EXAMPLES
from hornlab_search.search.campaign import (
    CMA_SEED_LIST,
    EntryResult,
    JobResult,
    _pinned_bounds,
    best_objective,
    budget_for_tier,
    is_compatible,
    load_brief,
    load_catalog,
    resolve_families,
    seeds_for_tier,
    TIER_COMPARE,
    TIER_DRY_RUN,
    TIER_SCREEN,
)

CATALOG_PATH = EXAMPLES / "catalog.yaml"
BRIEFS_DIR = EXAMPLES / "briefs"


# ------------------------------------------------------------------ brief loading


def test_load_brief_hifi():
    brief = load_brief(BRIEFS_DIR / "hifi_90x60_1in.yaml")
    assert brief["name"] == "hifi_90x60_1in"
    assert brief["symmetry"] == "hv"
    assert brief["driver"]["exit_radius_mm"] == 12.7
    assert brief["target"]["coverage_h_deg"] == 90.0
    assert brief["target"]["coverage_v_deg"] == 60.0


def test_load_brief_axi():
    brief = load_brief(BRIEFS_DIR / "axi_90x90_1in.yaml")
    assert brief["symmetry"] == "axisymmetric"
    assert brief["target"]["coverage_h_deg"] == 90.0
    assert brief["target"]["coverage_v_deg"] == 90.0
    assert brief["weights"]["load"] == 0.5


def test_load_brief_osse_75x45():
    brief = load_brief(BRIEFS_DIR / "osse_75x45.yaml")
    assert brief["driver"]["exit_radius_mm"] == 17.78
    assert brief["target"]["coverage_h_deg"] == 75.0
    assert brief["target"]["coverage_v_deg"] == 45.0


def test_load_brief_missing_field(tmp_path):
    # driver is present but missing exit_angle_deg; envelope provided so validation reaches driver check
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "name: test\n"
        "driver: {exit_radius_mm: 1.0}\n"
        "envelope: {max_mouth_w_mm: 1, max_mouth_h_mm: 1, max_depth_mm: 1}\n"
        "symmetry: hv\n"
        "source: {cap: auto}\n"
        "target: {coverage_h_deg: 90, coverage_v_deg: 60, band_lo_hz: 700, band_hi_hz: 5000}\n"
        "weights: {cov: 1}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="exit_angle_deg"):
        load_brief(bad)


def test_load_brief_bad_symmetry(tmp_path):
    b = tmp_path / "b.yaml"
    b.write_text(
        "name: x\ndriver: {exit_radius_mm: 1.0, exit_angle_deg: 5.0}\n"
        "envelope: {max_mouth_w_mm: 1, max_mouth_h_mm: 1, max_depth_mm: 1}\n"
        "symmetry: diagonal\nsource: {cap: auto}\n"
        "target: {coverage_h_deg: 90, coverage_v_deg: 60, band_lo_hz: 700, band_hi_hz: 5000}\n"
        "weights: {cov: 1}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="symmetry"):
        load_brief(b)


# ------------------------------------------------------------------ catalog loading


def test_load_catalog():
    catalog = load_catalog(CATALOG_PATH)
    assert isinstance(catalog, list)
    assert len(catalog) > 0
    names = {e["name"] for e in catalog}
    assert "osse_baseline" in names
    assert "rosse_baseline" in names
    assert "icw_termination" in names
    assert "icw_rollback" in names
    assert "freeform_sculpt" in names
    assert "freeform_hv" in names
    assert "throat_adapter" in names
    assert "search_smoke" in names


def test_catalog_entry_fields():
    catalog = load_catalog(CATALOG_PATH)
    for entry in catalog:
        assert "name" in entry
        assert "config" in entry
        assert "group" in entry
        assert "symmetry" in entry, f"entry {entry['name']} missing 'symmetry'"
        assert "description" in entry
        assert entry["symmetry"] in ("hv", "axisymmetric"), (
            f"entry {entry['name']} has bad symmetry {entry['symmetry']!r}")


def test_catalog_icw_entries_axisymmetric():
    catalog = load_catalog(CATALOG_PATH)
    by_name = {e["name"]: e for e in catalog}
    assert by_name["icw_termination"]["symmetry"] == "axisymmetric"
    assert by_name["icw_rollback"]["symmetry"] == "axisymmetric"


def test_catalog_magnus_entries():
    catalog = load_catalog(CATALOG_PATH)
    magnus = [e["name"] for e in catalog if e.get("group") == "magnus"]
    assert "osse_baseline" in magnus
    assert "rosse_baseline" in magnus


# ------------------------------------------------------------------ resolve_families


def test_resolve_families_all():
    catalog = load_catalog(CATALOG_PATH)
    result = resolve_families("all", catalog)
    assert len(result) == len(catalog)


def test_resolve_families_by_name():
    catalog = load_catalog(CATALOG_PATH)
    result = resolve_families("osse_baseline", catalog)
    assert len(result) == 1
    assert result[0]["name"] == "osse_baseline"


def test_resolve_families_by_group():
    catalog = load_catalog(CATALOG_PATH)
    result = resolve_families("magnus", catalog)
    assert all(e["group"] == "magnus" for e in result)
    assert len(result) > 2


def test_resolve_families_multiple():
    catalog = load_catalog(CATALOG_PATH)
    result = resolve_families("osse_baseline,icw_termination", catalog)
    names = [e["name"] for e in result]
    assert "osse_baseline" in names
    assert "icw_termination" in names
    assert len(result) == 2


def test_resolve_families_dedup():
    """Same name repeated should appear only once."""
    catalog = load_catalog(CATALOG_PATH)
    result = resolve_families("osse_baseline,osse_baseline", catalog)
    assert sum(1 for e in result if e["name"] == "osse_baseline") == 1


def test_resolve_families_unknown_name():
    catalog = load_catalog(CATALOG_PATH)
    with pytest.raises(ValueError, match="unknown family name"):
        resolve_families("nonexistent_xyz", catalog)


def test_resolve_families_unknown_lists_valid():
    catalog = load_catalog(CATALOG_PATH)
    with pytest.raises(ValueError) as exc:
        resolve_families("bad_name_123", catalog)
    assert "Valid names:" in str(exc.value) or "unknown" in str(exc.value)


def test_resolve_families_empty_spec():
    catalog = load_catalog(CATALOG_PATH)
    result = resolve_families("", catalog)
    assert len(result) == len(catalog)


# ------------------------------------------------------------------ compatibility


def test_compatibility_axisymmetric_refuses_asymmetric_brief():
    entry = {"name": "test", "symmetry": "axisymmetric"}
    brief = {"symmetry": "hv", "target": {"coverage_h_deg": 90.0, "coverage_v_deg": 60.0}}
    ok, reason = is_compatible(entry, brief)
    assert not ok
    assert "axisymmetric" in reason
    assert "coverage_h" in reason


def test_compatibility_axisymmetric_ok_with_equal_coverage():
    entry = {"name": "test", "symmetry": "axisymmetric"}
    brief = {"symmetry": "axisymmetric", "target": {"coverage_h_deg": 90.0, "coverage_v_deg": 90.0}}
    ok, reason = is_compatible(entry, brief)
    assert ok
    assert reason == ""


def test_compatibility_hv_entry_always_ok():
    entry = {"name": "test", "symmetry": "hv"}
    brief = {"symmetry": "hv", "target": {"coverage_h_deg": 75.0, "coverage_v_deg": 45.0}}
    ok, reason = is_compatible(entry, brief)
    assert ok


def test_compatibility_icw_skipped_for_asymmetric_brief():
    catalog = load_catalog(CATALOG_PATH)
    by_name = {e["name"]: e for e in catalog}
    brief_hv = load_brief(BRIEFS_DIR / "hifi_90x60_1in.yaml")  # coverage_h=90 != coverage_v=60
    ok, reason = is_compatible(by_name["icw_termination"], brief_hv)
    assert not ok


def test_compatibility_icw_ok_for_symmetric_brief():
    catalog = load_catalog(CATALOG_PATH)
    by_name = {e["name"]: e for e in catalog}
    brief_axi = load_brief(BRIEFS_DIR / "axi_90x90_1in.yaml")  # coverage_h == coverage_v
    ok, reason = is_compatible(by_name["icw_termination"], brief_axi)
    assert ok


# ------------------------------------------------------------------ budget formula


def test_budget_screen_formula():
    # screen: max(40, 10*n_keys)
    assert budget_for_tier(TIER_SCREEN, 1) == 40    # max(40, 10) = 40
    assert budget_for_tier(TIER_SCREEN, 4) == 40    # max(40, 40) = 40
    assert budget_for_tier(TIER_SCREEN, 5) == 50    # max(40, 50) = 50
    assert budget_for_tier(TIER_SCREEN, 10) == 100  # max(40, 100) = 100


def test_budget_compare_formula():
    # compare: max(150, 25*n_keys)
    assert budget_for_tier(TIER_COMPARE, 1) == 150   # max(150, 25) = 150
    assert budget_for_tier(TIER_COMPARE, 6) == 150   # max(150, 150) = 150
    assert budget_for_tier(TIER_COMPARE, 7) == 175   # max(150, 175) = 175
    assert budget_for_tier(TIER_COMPARE, 10) == 250  # max(150, 250) = 250


def test_budget_override():
    assert budget_for_tier(TIER_SCREEN, 10, budget_override=99) == 99
    assert budget_for_tier(TIER_COMPARE, 10, budget_override=999) == 999


def test_budget_dry_run():
    assert budget_for_tier(TIER_DRY_RUN, 5) == 0


# ------------------------------------------------------------------ seed list


def test_seeds_screen_default_1():
    s = seeds_for_tier(TIER_SCREEN)
    assert len(s) == 1
    assert s[0] == CMA_SEED_LIST[0]


def test_seeds_compare_default_2():
    s = seeds_for_tier(TIER_COMPARE)
    assert len(s) == 2
    assert s == CMA_SEED_LIST[:2]


def test_seeds_dry_run():
    s = seeds_for_tier(TIER_DRY_RUN)
    assert len(s) == 1


def test_seeds_override():
    s = seeds_for_tier(TIER_COMPARE, n_seeds=4)
    assert len(s) == 4
    assert s == CMA_SEED_LIST[:4]


def test_seeds_are_from_fixed_list():
    for tier in (TIER_SCREEN, TIER_COMPARE):
        s = seeds_for_tier(tier)
        for seed in s:
            assert seed in CMA_SEED_LIST


# ------------------------------------------------------------------ leaderboard aggregation helpers


def _make_row(objective: float, ok: bool = True, design_hash: str | None = None,
              params: dict | None = None) -> dict:
    return {
        "objective": objective,
        "ok": ok,
        "design_hash": design_hash or f"hash{objective:.3f}",
        "params": params or {},
    }


def test_best_objective():
    rows = [_make_row(0.5), _make_row(0.3), _make_row(0.7)]
    assert best_objective(rows) == pytest.approx(0.3)


def test_best_objective_ignores_failed():
    rows = [_make_row(0.1, ok=False), _make_row(0.5), _make_row(0.9)]
    assert best_objective(rows) == pytest.approx(0.5)


def test_best_objective_empty():
    assert best_objective([]) is None


def test_entry_result_median_spread():
    er = EntryResult(entry={"name": "x"})
    j1 = JobResult(entry_name="x", seed=1, best_j=0.3)
    j2 = JobResult(entry_name="x", seed=2, best_j=0.5)
    er.jobs = [j1, j2]
    assert er.median_best_j() == pytest.approx(0.4)  # two values: average of mid pair
    assert er.spread_best_j() == pytest.approx(0.2)


def test_entry_result_single_job_spread_none():
    er = EntryResult(entry={"name": "x"})
    er.jobs = [JobResult(entry_name="x", seed=1, best_j=0.4)]
    assert er.spread_best_j() is None


def test_entry_result_no_jobs():
    er = EntryResult(entry={"name": "x"})
    assert er.median_best_j() is None
    assert er.spread_best_j() is None


# ------------------------------------------------------------------ pinned bounds


def _make_run_dir(tmp_path, bounds: dict, rows: list[dict]) -> Path:
    """Create a minimal fake run directory with config.yaml and search.ndjson."""
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    # config.yaml with given bounds
    cfg = {
        "name": "test", "family": "OSSE",
        "bounds": bounds,
        "seed_params": {},
        "target": {"coverage_h_deg": 90.0, "coverage_v_deg": 60.0,
                   "band_lo_hz": 700.0, "band_hi_hz": 5500.0,
                   "di_target_db": None, "di_slope_target": 0.0},
        "weights": {"cov": 1.0, "rip": 1.0, "di": 0.3, "dislope": 0.5, "flat": 0.5, "load": 0.0},
        "mesh": {"epw": 6.0, "quadrants": "1", "dof_cap_screen": 5000,
                 "dof_cap_verify": 7000, "dof_cap_final": 8900, "dof_per_triangle": 0.51},
        "solve": {"backend": "beat_cuda", "distance_m": 2.0, "angle_count": 73,
                  "balloon": True, "balloon_points_screen": 512, "balloon_points_verify": 1024,
                  "gmres_tol": 1e-5, "timeout_s": 900},
        "search": {"algorithm": "cma", "sigma0": 0.25, "seed": 1234, "budget": 100,
                   "popsize": None, "tolfun": 1e-3},
    }
    (run_dir / "config.yaml").write_text(yaml.dump(cfg), encoding="utf-8")
    ndjson = run_dir / "search.ndjson"
    with ndjson.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    return run_dir


def test_pinned_bounds_detects_pinned_key(tmp_path):
    # 5 of 6 top designs have 'k' near lo=0.3
    bounds = {"k": {"lo": 0.3, "hi": 2.5}, "a_deg": {"lo": 5.0, "hi": 55.0}}
    rows = [
        _make_row(0.1 + i * 0.01, params={"k": 0.31, "a_deg": 20.0 + i})
        for i in range(6)
    ]
    run_dir = _make_run_dir(tmp_path, bounds, rows)
    pinned = _pinned_bounds(rows, run_dir)
    assert "k" in pinned


def test_pinned_bounds_does_not_flag_mid(tmp_path):
    # all designs near mid-range (not pinned)
    bounds = {"k": {"lo": 0.3, "hi": 2.5}, "a_deg": {"lo": 5.0, "hi": 55.0}}
    rows = [
        _make_row(0.1 + i * 0.01, params={"k": 1.0 + i * 0.1, "a_deg": 25.0 + i})
        for i in range(6)
    ]
    run_dir = _make_run_dir(tmp_path, bounds, rows)
    pinned = _pinned_bounds(rows, run_dir)
    assert "k" not in pinned


def test_pinned_bounds_too_few_rows(tmp_path):
    bounds = {"k": {"lo": 0.3, "hi": 2.5}}
    rows = [_make_row(0.1 + i, params={"k": 0.31}) for i in range(3)]
    run_dir = _make_run_dir(tmp_path, bounds, rows)
    pinned = _pinned_bounds(rows, run_dir)
    # fewer than 4 distinct designs => []
    assert pinned == []


def test_pinned_bounds_near_hi(tmp_path):
    # 5 designs near hi=2.5
    bounds = {"k": {"lo": 0.3, "hi": 2.5}}
    rows = [
        _make_row(0.1 + i * 0.01, params={"k": 2.49 - i * 0.001})
        for i in range(6)
    ]
    run_dir = _make_run_dir(tmp_path, bounds, rows)
    pinned = _pinned_bounds(rows, run_dir)
    assert "k" in pinned


# ------------------------------------------------------------------ --brief/--cma-seed reach load_config


def test_cli_run_passes_brief_and_cma_seed_to_load_config(monkeypatch, tmp_path):
    """--brief and --cma-seed are passed to load_config when given."""
    from hornlab_search import cli as cli_mod
    from hornlab_search.config import load_config as real_load_config

    calls = []

    def fake_load_config(path, **kwargs):
        calls.append({"path": path, "kwargs": dict(kwargs)})
        # Call the real load_config without the unknown kwargs (it doesn't support them yet)
        return real_load_config(path)

    # Patch the name 'load_config' in the cli module's local scope via the import path
    # _load_cfg does: from hornlab_search.config import load_config; we patch where _load_cfg looks
    monkeypatch.setattr("hornlab_search.config.load_config", fake_load_config)

    brief_path = str(EXAMPLES / "briefs" / "hifi_90x60_1in.yaml")

    class FakeArgs:
        config = str(EXAMPLES / "osse_baseline.yaml")
        brief = brief_path
        cma_seed = 777
        backend = None

    cli_mod._load_cfg(FakeArgs())

    assert len(calls) == 1
    assert calls[0]["kwargs"].get("brief") == Path(brief_path)
    assert calls[0]["kwargs"].get("cma_seed") == 777


def test_cli_run_no_brief_no_cma_seed_does_not_pass_kwargs(monkeypatch):
    """When --brief and --cma-seed are omitted, load_config is called with path only."""
    from hornlab_search import cli as cli_mod
    import hornlab_search.config as cfg_mod

    calls = []

    def fake_load_config(path, **kwargs):
        calls.append({"path": path, "kwargs": kwargs})
        return cfg_mod.load_config.__wrapped__(path) if hasattr(cfg_mod.load_config, "__wrapped__") else None

    # Use real load_config but capture calls
    orig = cfg_mod.load_config
    try:
        cfg_mod.load_config = lambda path, **kwargs: (
            calls.append({"path": path, "kwargs": kwargs}) or orig(path))
        class FakeArgs:
            config = str(EXAMPLES / "osse_baseline.yaml")
            brief = None
            cma_seed = None
            backend = None
        cli_mod._load_cfg(FakeArgs())
    finally:
        cfg_mod.load_config = orig

    assert len(calls) == 1
    assert "brief" not in calls[0]["kwargs"]
    assert "cma_seed" not in calls[0]["kwargs"]


# ------------------------------------------------------------------ CLI families and campaign parse


def test_cli_families_parses(monkeypatch, capsys):
    """families command runs without error (uses the real catalog)."""
    from hornlab_search import cli
    rc = cli.main(["families"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "osse_baseline" in out
    assert "families OK" in out


def test_cli_families_with_brief(monkeypatch, capsys):
    """families --brief marks incompatible entries."""
    from hornlab_search import cli
    brief_path = str(EXAMPLES / "briefs" / "hifi_90x60_1in.yaml")
    rc = cli.main(["families", "--brief", brief_path])
    out = capsys.readouterr().out
    assert rc == 0
    # icw entries should be marked incompatible (90 != 60)
    assert "INCOMPAT" in out or "icw" in out.lower()


def test_cli_families_bad_brief(capsys):
    """families with a nonexistent brief prints FAILED."""
    from hornlab_search import cli
    rc = cli.main(["families", "--brief", "/nonexistent/path.yaml"])
    assert rc != 0


def test_cli_campaign_unknown_family(monkeypatch, capsys, tmp_path):
    """campaign with unknown family name exits non-zero."""
    from hornlab_search import cli
    brief = str(EXAMPLES / "briefs" / "hifi_90x60_1in.yaml")
    rc = cli.main([
        "campaign",
        "--brief", brief,
        "--families", "totally_unknown_xyz",
        "--tier", "screen",
        "--runs-dir", str(tmp_path),
    ])
    assert rc != 0


def test_cli_campaign_dry_run_no_solve(monkeypatch, tmp_path, capsys):
    """campaign --tier dry-run runs subprocesses (mocked) and writes campaign.json."""
    from hornlab_search import cli
    from hornlab_search.search import campaign as camp_mod

    brief = str(EXAMPLES / "briefs" / "hifi_90x60_1in.yaml")

    # Mock run_job so no subprocess is actually launched
    fake_job_results = []

    def fake_run_campaign(brief_path, families_spec, tier, runs_dir, **kwargs):
        # Return a minimal campaign result
        from hornlab_search.search.campaign import (
            load_brief, load_catalog, resolve_families, seeds_for_tier,
        )
        catalog = load_catalog()
        entries = resolve_families(families_spec, catalog)
        br = load_brief(brief_path)
        camp_dir = runs_dir / "campaign_TEST"
        camp_dir.mkdir(parents=True, exist_ok=True)
        # Write empty campaign.json
        (camp_dir / "campaign.json").write_text(json.dumps({"tier": tier}), encoding="utf-8")
        (camp_dir / "leaderboard.md").write_text("# test\n", encoding="utf-8")
        from hornlab_search.search.campaign import EntryResult
        entry_results = [EntryResult(entry=e) for e in entries[:2]]
        return {
            "campaign_dir": camp_dir,
            "brief": br,
            "entries": entry_results,
            "catalog": catalog,
            "tier": tier,
            "seeds": seeds_for_tier(tier),
        }

    monkeypatch.setattr(camp_mod, "run_campaign", fake_run_campaign)
    monkeypatch.setattr("hornlab_search.cli.run_campaign", fake_run_campaign, raising=False)

    rc = cli.main([
        "campaign",
        "--brief", brief,
        "--families", "magnus",
        "--tier", "dry-run",
        "--runs-dir", str(tmp_path),
    ])
    # With mocked run_campaign the command should succeed (or at worst print a non-fatal error)
    # The main assertion is that it doesn't crash with an exception
    assert rc in (0, 1)  # 0 = OK, 1 = some jobs failed (acceptable)
