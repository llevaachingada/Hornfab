"""Swarm lane H: optional run_id / config_name / typology record fields. Offline.

The fields are additive: absent keys stay absent (schema v1 readers unchanged), present keys
round-trip through strict JSON and still validate. ``typology_name`` is the single label rule.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from hornlab_search.dataset.record import build_record, typology_name, validate_record
from test_dataset_factory import GRID, LIB_SHAS, TARGET, make_eval, solve_spec


def _built(**kw):
    return build_record(make_eval(3), TARGET, LIB_SHAS, solve_spec=solve_spec(), grid=GRID,
                        area_m2=0.125, created_utc="2026-10-13T00:00:00Z", **kw)


def test_without_provenance_fields_the_keys_are_absent_and_valid():
    meta, _ = _built()
    for key in ("run_id", "config_name", "typology"):
        assert key not in meta
    validate_record(meta)


def test_with_provenance_fields_they_round_trip_and_validate():
    meta, _ = _built(run_id="20261031T201057Z-screen-d3158e",
                     config_name="atlas_v2_osse_hv", typology="core:os:osse")
    validate_record(meta)
    assert json.loads(json.dumps(meta))["run_id"] == "20261031T201057Z-screen-d3158e"
    assert meta["config_name"] == "atlas_v2_osse_hv"
    assert meta["typology"] == "core:os:osse"


def test_empty_values_are_omitted_not_written_as_null_or_empty_string():
    meta, _ = _built(run_id="", config_name=None, typology="")
    for key in ("run_id", "config_name", "typology"):
        assert key not in meta
    validate_record(meta)


def test_typology_name_uses_generator_spec_name_and_profiles():
    gen = {"name": "typology", "spec": {"name": "core", "profile_h": {"type": "os"},
                                        "profile_v": {"type": "osse"}}}
    assert typology_name(gen, "FREEFORM") == "core:os/osse"


def test_typology_name_collapses_equal_profiles_and_falls_back_to_family():
    gen = {"spec": {"name": "core", "profile_h": {"type": "os"}, "profile_v": {"type": "os"}}}
    assert typology_name(gen, "FREEFORM") == "core:os"
    assert typology_name(None, "OSSE") == "OSSE"
    assert typology_name({}, None) == ""

# ------------------------------------------------------------------ keepers backfill

def _shard_record(i: int, **kw):
    meta, _ = build_record(make_eval(i), TARGET, LIB_SHAS, solve_spec=solve_spec(), grid=GRID,
                           area_m2=0.125, created_utc="2026-10-13T00:00:00Z", **kw)
    validate_record(meta)
    return meta


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, separators=(",", ":")) + "\n" for r in rows),
                    encoding="utf-8")


def _synthetic_two_run_tree(tmp_path: Path):
    dataset = tmp_path / "dataset"
    runs = tmp_path / "runs"
    rec0 = _shard_record(0)
    rec1 = _shard_record(1, config_name="manual_keep")
    rec2 = _shard_record(2)                     # no run row: must stay untouched
    _write_jsonl(dataset / "shard-0000.jsonl", [rec0, rec1, rec2])

    run_a = runs / "20261031T201057Z-screen-d3158e"
    run_b = runs / "20261031T202159Z-screen-ba7648"
    gen = {"name": "typology", "spec": {"name": "core", "profile_h": {"type": "os"}}}
    _write_jsonl(run_a / "search.ndjson", [
        {"design_hash": rec0["design_hash"], "solve_hash": rec0["solve_hash"],
         "family": "FREEFORM", "generator": gen}])
    _write_jsonl(run_b / "search.ndjson", [
        {"design_hash": rec1["design_hash"], "solve_hash": rec1["solve_hash"],
         "family": "OSSE"}])
    (run_a / "config.yaml").write_text("name: atlas_core_hv\nfamily: FREEFORM\n", encoding="utf-8")
    (run_b / "config.yaml").write_text("name: osse_baseline\nfamily: OSSE\n", encoding="utf-8")
    return dataset, runs


def test_keepers_backfill_joins_two_runs_and_never_overwrites(tmp_path):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "data"))
    import keepers

    dataset, runs = _synthetic_two_run_tree(tmp_path)
    before = (dataset / "shard-0000.jsonl").read_text(encoding="utf-8")
    plan, stats = keepers.plan_backfill(dataset, runs)
    assert stats["runs_indexed"] == 2 and stats["rows_joined"] == 2
    assert stats["rows_changed"] == 2 and stats["fields_added"] == 5

    # dry run writes nothing
    assert keepers.main(["--backfill", "--dataset", str(dataset), "--runs", str(runs),
                         "--quiet"]) == 0
    assert (dataset / "shard-0000.jsonl").read_text(encoding="utf-8") == before

    backup = tmp_path / "backup"
    assert keepers.main(["--backfill", "--dataset", str(dataset), "--runs", str(runs),
                         "--apply", "--backup", str(backup), "--quiet"]) == 0
    rows = [json.loads(line) for line in (dataset / "shard-0000.jsonl").read_text(
        encoding="utf-8").splitlines()]

    assert rows[0]["run_id"] == "20261031T201057Z-screen-d3158e"
    assert rows[0]["config_name"] == "atlas_core_hv"
    assert rows[0]["typology"] == "core:os"
    assert rows[1]["run_id"] == "20261031T202159Z-screen-ba7648"
    assert rows[1]["config_name"] == "manual_keep"      # existing value wins
    assert rows[1]["typology"] == "OSSE"
    assert "run_id" not in rows[2] and "config_name" not in rows[2]
    for row in rows:
        validate_record(row)
    assert (backup / "shard-0000.jsonl").read_text(encoding="utf-8") == before
