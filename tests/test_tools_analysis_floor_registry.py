"""Full-identity numerical-floor registry (P0b): exact keys, no borrowed thresholds."""
from __future__ import annotations

import yaml

from test_tools_analysis_common import REPO, load_tool, make_row, write_run
from _common import load_run

fr = load_tool("floor_registry")
ca = load_tool("continuation_advice")

V7_BRIEF = "examples/briefs/home_landscape_2026-11-15/room_landscape_80x50_700_hf1440_v7.yaml"
COMPACT400_BRIEF = ("examples/briefs/compact400_2026-11-19/"
                    "compact400_xo1000_1400_hf1440_v10xo.yaml")


def _brief_run(tmp_path, brief_rel, rows, name):
    brief_path = (REPO / brief_rel).resolve()
    cfg = dict(yaml.safe_load(brief_path.read_text(encoding="utf-8")))
    cfg["brief_file"] = str(brief_path)
    cfg["name"] = f"test_{name}"
    cfg["family"] = "OSSE"
    cfg["solve"] = {"backend": "beat_cuda", "angle_count": 73, "balloon": True,
                    "balloon_points_screen": 512}
    cfg["mesh"] = {"quadrants": "1", "epw": 6.0, "rear_res_factor": 1.5}
    return write_run(rows, tmp_path, name, config=cfg, family="OSSE")


def test_registry_has_the_four_sourced_entries_and_compact_caveat():
    by_id = {e["id"]: e for e in fr.entries()}
    assert set(by_id) == {"v7_home_landscape_this_pass",
                          "v10_home_corridor_preferred_edge",
                          "v10_home_shipped_preferred_edge", "v10_home_slope5",
                          "compact400_v10xo"}
    assert by_id["v7_home_landscape_this_pass"]["floor_J"] == 0.3104791983512361
    assert by_id["v10_home_corridor_preferred_edge"]["floor_J"] == 0.46773899691673904
    assert by_id["v10_home_shipped_preferred_edge"]["floor_J"] == 0.46773899691673904
    assert by_id["v10_home_slope5"]["floor_J"] == 0.4863165895744908
    compact = by_id["compact400_v10xo"]
    assert compact["floor_J"] == 0.1293
    assert compact["components"]["frequency_sd_top_J"] == 0.1291110736609016
    assert compact["components"]["mesh_sd_J"] == 0.007676441842658574
    assert "whole-fleet" in compact["caveat"].lower()
    assert "not a repeatability floor measured on 400 mm horns" in compact["caveat"]
    # the generic v10 floor is a different entry and never attached to compact400
    assert compact["floor_J"] != by_id["v10_home_corridor_preferred_edge"]["floor_J"]
    assert compact["identity"]["brief"]["name"] == "compact400_xo1000_1400_hf1440_v10xo"


def test_v7_run_resolves_by_exact_brief_and_score_identity(tmp_path):
    rows = [make_row(i, 5.0 - 0.005 * i, version=7) for i in range(30)]
    run = _brief_run(tmp_path, V7_BRIEF, rows, "v7")
    identity = fr.identity_from_run(load_run(run))
    assert identity["objective_version"] == 7
    assert identity["brief"]["name"] == "room_landscape_80x50_700_hf1440_v7"
    assert identity["brief"]["sha256"]
    assert identity["brief"]["match_quality"] == "resolved_file"
    assert identity["score_identity"]["hash"]
    resolution = fr.resolve(identity)
    assert resolution["status"] == "matched"
    assert resolution["matched_entry"] == "v7_home_landscape_this_pass"
    assert resolution["match_quality"] in ("exact", "exact_core")
    assert resolution["floor_J"] == 0.3104791983512361
    assert "solver.backend" in resolution["unverified_fields"]


def test_v10_shipped_brief_has_its_own_exact_identity_entry(tmp_path):
    brief_rel = ("examples/briefs/home_landscape_2026-11-18_v10/"
                 "room_landscape_80x50_700_hf1440_v10.yaml")
    rows = [make_row(i, 1.5 - 0.005 * i, version=10) for i in range(30)]
    run = _brief_run(tmp_path, brief_rel, rows, "v10")
    resolution = fr.floor_for_run(load_run(run))
    assert resolution["status"] == "matched"
    assert resolution["matched_entry"] == "v10_home_shipped_preferred_edge"
    assert resolution["floor_J"] == 0.46773899691673904


def test_compact400_never_receives_the_generic_v10_floor(tmp_path):
    rows = [make_row(i, 2.0 - 0.01 * i, version=10) for i in range(30)]
    run = _brief_run(tmp_path, COMPACT400_BRIEF, rows, "compact")
    resolution = fr.floor_for_run(load_run(run))
    assert resolution["status"] == "matched"
    assert resolution["matched_entry"] == "compact400_v10xo"
    assert resolution["floor_J"] == 0.1293
    assert resolution["floor_J"] != 0.46773899691673904
    # A 0.18 J compact400 gain is above the compact floor band and must not be dismissed by
    # the home-v10 0.4677 floor.
    gain = 0.18
    curve = [{"n": i + 1, "best": 5.0 - gain * (i + 1) / 100 if i >= 50 else 5.0}
             for i in range(150)]
    advice = ca.advise(curve, resolution["floor_J"])
    assert advice["advice"] == "propose continuation"
    assert advice["advice"] != "do not propose"


def test_copied_run_config_resolves_examples_briefs_tail(tmp_path):
    """A run copied under runs/<x>/ loses the ``examples`` segment; the tail must re-root."""
    real = (REPO / V7_BRIEF).resolve()
    cfg = dict(yaml.safe_load(real.read_text(encoding="utf-8")))
    cfg["brief_file"] = ("../../briefs/home_landscape_2026-11-15/"
                         "room_landscape_80x50_700_hf1440_v7.yaml")
    cfg["name"] = "test_copied"
    cfg["family"] = "OSSE"
    cfg["solve"] = {"backend": "beat_cuda"}
    cfg["mesh"] = {"quadrants": "1"}
    rows = [make_row(i, 5.0 - 0.005 * i, version=7) for i in range(30)]
    run_name = "20261115T162516Z-screen-e31b23"
    run_dir = (tmp_path / "runs" / run_name).resolve()
    run = write_run(rows, tmp_path / "runs", run_name, config=cfg,
                    extra_run_json={"config_path": str(run_dir / "config.yaml")})

    identity = fr.identity_from_run(load_run(run))
    assert identity["brief"]["match_quality"] == "resolved_file"
    assert identity["brief"]["sha256"]
    assert identity["brief"]["path"] == V7_BRIEF
    resolution = fr.resolve(identity)
    assert resolution["status"] == "matched"
    assert resolution["matched_entry"] == "v7_home_landscape_this_pass"
    assert resolution["floor_J"] == 0.3104791983512361

    # A genuinely different brief is still refused (no tail guess may silently match it).
    raw = yaml.safe_load(real.read_text(encoding="utf-8"))
    raw["target"]["coverage_h_deg"] = 120.0
    other = tmp_path / "different_brief.yaml"
    other.write_text(yaml.safe_dump(raw), encoding="utf-8")
    cfg2 = dict(raw)
    cfg2["brief_file"] = str(other)
    cfg2["name"] = "test_different_again"
    cfg2["family"] = "OSSE"
    cfg2["solve"] = {"backend": "beat_cuda"}
    cfg2["mesh"] = {"quadrants": "1"}
    run2 = write_run(rows, tmp_path / "runs", "different_again", config=cfg2)
    resolution2 = fr.floor_for_run(load_run(run2))
    assert resolution2["status"] == "no_applicable_floor"
    assert resolution2["floor_J"] is None
    assert "brief.sha256" in resolution2["mismatched_fields"]


def test_unknown_identity_names_the_missing_fields(tmp_path):
    rows = [make_row(i, 5.0 - 0.01 * i, version=4) for i in range(30)]
    run = write_run(rows, tmp_path, "v4")
    resolution = fr.floor_for_run(load_run(run))
    assert resolution["status"] == "no_applicable_floor"
    assert resolution["matched_entry"] is None
    assert resolution["floor_J"] is None
    fields = set(resolution["missing_fields"]) | set(resolution["mismatched_fields"])
    assert "brief.sha256" in fields or "brief.name" in fields
    assert "score_identity.hash" in fields
    assert resolution["why"].startswith("no applicable published floor")


def test_mismatched_brief_is_refused_not_borrowed(tmp_path):
    compact = (REPO / COMPACT400_BRIEF).resolve()
    raw = yaml.safe_load(compact.read_text(encoding="utf-8"))
    raw["target"]["coverage_h_deg"] = 120.0          # a different brief identity
    modified = tmp_path / "different_brief.yaml"
    modified.write_text(yaml.safe_dump(raw), encoding="utf-8")

    cfg = dict(raw)
    cfg["brief_file"] = str(modified)
    cfg["name"] = "test_different"
    cfg["family"] = "OSSE"
    cfg["solve"] = {"backend": "beat_cuda"}
    cfg["mesh"] = {"quadrants": "1"}
    rows = [make_row(i, 2.0 - 0.01 * i, version=10) for i in range(30)]
    run = write_run(rows, tmp_path, "different", config=cfg)

    resolution = fr.floor_for_run(load_run(run))
    assert resolution["status"] == "no_applicable_floor"
    assert resolution["floor_J"] is None
    assert "brief.sha256" in resolution["mismatched_fields"]
    assert resolution["why"].startswith("no applicable published floor")
