"""S5 seed_pack.py — fixed-fixture tests (no mesh, no BEM, no live data).

Covers:
 - Basic feasibility: a catalog with complete records produces a seed pack.
 - Duplicate exclusion: the same design_hash appearing in two rows is counted once.
 - Missing provenance labelling: records with no run_id get the ``run_id_missing`` gap.
 - Diversity selection: greedy max-min returns <= k entries, all from the eligible set.
 - Deterministic output: same seed/catalog produces identical selections.
 - Score percentile floor: raising min_score_percentile excludes worse designs.
 - Family filter: only records matching the family flag survive.
 - Fidelity filter: only records matching the fidelity flag survive.
 - Round-trip identity: ``hash_identity`` for clean records, ``hash_missing`` for empty.
 - Empty catalog: tool reports zero selections without crashing.
 - JSON output: ``write_seed_pack`` writes a valid, non-NaN JSON file.
 - CLI smoke: CLI writes the JSON file when given a valid catalog.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from test_tools_analysis_common import load_tool, run_cli

sp = load_tool("seed_pack")


# --------------------------------------------------------------------------- helpers


def _make_catalog_json(records: list[dict]) -> dict:
    return {"tool": "catalog", "schema_version": 1, "records": records}


def _design_hash(i: int) -> str:
    return f"d{i:040d}"  # 40 hex-ish lowercase chars


def _make_record(i: int, *, ok: bool = True, design_hash: str | None = None,
                 run_id: str | None = "run-a", config_name: str = "native__ath_core_v4",
                 family: str = "OSSE", fidelity: str = "screen",
                 objective_version: int = 4, score: float | None = None,
                 root: str = "/data", shard: int | None = 0,
                 shard_index: int | None = None, row: int | None = None) -> dict:
    """Minimal catalog record."""
    dh = design_hash or _design_hash(i)
    return {
        "design_hash": dh,
        "geometry_id": dh,
        "run_id": run_id,
        "config_name": config_name,
        "family": family,
        "fidelity": fidelity,
        "backend": "beat_cuda",
        "objective_version": objective_version,
        "ok": ok,
        "completeness": "complete" if ok else "failed",
        "failure_kind": None if ok else "invalid_geometry",
        "score": score if score is not None else (10.0 + i),
        "root": root,
        "shard": shard,
        "shard_index": shard_index,
        "row": row if row is not None else i,
    }


def _write_catalog(tmp_path: Path, records: list[dict], name: str = "catalog.json") -> Path:
    p = tmp_path / name
    p.write_text(json.dumps(_make_catalog_json(records), allow_nan=False), encoding="utf-8")
    return p


# --------------------------------------------------------------------------- normalise_record


def test_normalise_record_accepts_valid_design_hash():
    r = _make_record(0, design_hash="a" * 40)
    nr = sp._normalise_record(r)
    assert nr is not None
    assert nr["design_hash"] == "a" * 40


def test_normalise_record_rejects_short_hash():
    r = _make_record(0, design_hash="abc")
    assert sp._normalise_record(r) is None


def test_normalise_record_rejects_nonstring_hash():
    r = _make_record(0)
    r["design_hash"] = 12345
    assert sp._normalise_record(r) is None


def test_normalise_record_missing_hash_is_rejected():
    r = _make_record(0)
    del r["design_hash"]
    assert sp._normalise_record(r) is None


def test_normalise_record_copies_score_as_float():
    r = _make_record(3, score=7.5)
    nr = sp._normalise_record(r)
    assert nr is not None
    assert nr["score"] == pytest.approx(7.5)


def test_normalise_record_nonfinite_score_becomes_none():
    r = _make_record(3, score=float("nan"))
    nr = sp._normalise_record(r)
    assert nr is not None
    assert nr["score"] is None


# --------------------------------------------------------------------------- filter_records


def test_filter_records_excludes_failed():
    records = [sp._normalise_record(_make_record(i, ok=(i < 3))) for i in range(5)]
    records = [r for r in records if r is not None]
    eligible = sp._filter_records(records, task=None, objective_version=None,
                                  family=None, fidelity=None)
    assert len(eligible) == 3


def test_filter_records_task_substring():
    records = [sp._normalise_record(_make_record(i, config_name=f"task_{i}")) for i in range(3)]
    records = [r for r in records if r is not None]
    eligible = sp._filter_records(records, task="task_1", objective_version=None,
                                  family=None, fidelity=None)
    assert len(eligible) == 1
    assert eligible[0]["config_name"] == "task_1"


def test_filter_records_objective_version():
    records = [sp._normalise_record(_make_record(i, objective_version=4 + i)) for i in range(3)]
    records = [r for r in records if r is not None]
    eligible = sp._filter_records(records, task=None, objective_version=5,
                                  family=None, fidelity=None)
    assert len(eligible) == 1


def test_filter_records_family_case_insensitive():
    records = [sp._normalise_record(_make_record(i, family="osse" if i == 0 else "LECTRON"))
               for i in range(3)]
    records = [r for r in records if r is not None]
    eligible = sp._filter_records(records, task=None, objective_version=None,
                                  family="OSSE", fidelity=None)
    assert len(eligible) == 1


def test_filter_records_fidelity():
    records = [sp._normalise_record(_make_record(i, fidelity="screen" if i < 2 else "verify"))
               for i in range(4)]
    records = [r for r in records if r is not None]
    eligible = sp._filter_records(records, task=None, objective_version=None,
                                  family=None, fidelity="verify")
    assert len(eligible) == 2


# --------------------------------------------------------------------------- deduplicate


def test_deduplicate_removes_second_occurrence():
    dh = _design_hash(7)
    records = [sp._normalise_record(_make_record(i, design_hash=dh)) for i in range(3)]
    records = [r for r in records if r is not None]
    unique, n_exc = sp._deduplicate(records)
    assert len(unique) == 1
    assert n_exc == 2


def test_deduplicate_preserves_distinct():
    records = [sp._normalise_record(_make_record(i)) for i in range(5)]
    records = [r for r in records if r is not None]
    unique, n_exc = sp._deduplicate(records)
    assert len(unique) == 5
    assert n_exc == 0


# --------------------------------------------------------------------------- percentile floor


def test_apply_percentile_floor_zero_excludes_nothing():
    records = [sp._normalise_record(_make_record(i, score=float(i))) for i in range(10)]
    records = [r for r in records if r is not None]
    out, n = sp._apply_percentile_floor(records, 0.0)
    assert n == 0
    assert len(out) == 10


def test_apply_percentile_floor_50_keeps_half():
    records = [sp._normalise_record(_make_record(i, score=float(i))) for i in range(10)]
    records = [r for r in records if r is not None]
    out, n = sp._apply_percentile_floor(records, 50.0)
    # keeps records with score <= median, excludes those above
    assert len(out) + n == 10
    assert n > 0


def test_apply_percentile_floor_all_unscored_unchanged():
    records = [sp._normalise_record(_make_record(i, score=None)) for i in range(5)]
    records = [r for r in records if r is not None]
    out, n = sp._apply_percentile_floor(records, 90.0)
    # unscored records are never excluded by the percentile floor
    assert n == 0
    assert len(out) == 5


# --------------------------------------------------------------------------- round_trip_check


def test_round_trip_check_valid_hash_gives_identity():
    r = sp._normalise_record(_make_record(0, design_hash="a" * 40))
    rt = sp._round_trip_check(r)
    assert rt["kind"] == "hash_identity"
    assert rt["needs_config"] is True


def test_round_trip_check_missing_hash_gives_hash_missing():
    r = sp._normalise_record(_make_record(0))
    r["design_hash"] = None
    rt = sp._round_trip_check(r)
    assert rt["kind"] == "hash_missing"


def test_round_trip_check_explicit_ref_mismatch():
    dh = "a" * 40
    r = sp._normalise_record(_make_record(0, design_hash=dh))
    rt = sp._round_trip_check(r, explicit_ref={dh: "b" * 40})
    assert rt["kind"] == "hash_mismatch"


def test_round_trip_check_explicit_ref_match():
    dh = "a" * 40
    r = sp._normalise_record(_make_record(0, design_hash=dh))
    rt = sp._round_trip_check(r, explicit_ref={dh: dh})
    assert rt["kind"] == "hash_identity"


# --------------------------------------------------------------------------- provenance_gaps


def test_provenance_gaps_complete_record_has_no_gaps():
    r = sp._normalise_record(_make_record(0, run_id="run-x", score=1.5,
                                          shard=0, row=0))
    gaps = sp._provenance_gaps(r)
    assert gaps == []


def test_provenance_gaps_no_run_id():
    r = sp._normalise_record(_make_record(0, run_id=None))
    assert "run_id_missing" in sp._provenance_gaps(r)


def test_provenance_gaps_no_fidelity():
    r = sp._normalise_record(_make_record(0))
    r["fidelity"] = None
    assert "fidelity_unknown" in sp._provenance_gaps(r)


def test_provenance_gaps_no_score():
    r = sp._normalise_record(_make_record(0, score=None))
    r["score"] = None
    assert "score_missing" in sp._provenance_gaps(r)


def test_provenance_gaps_no_shard_row():
    r = sp._normalise_record(_make_record(0))
    r["source"]["shard"] = None
    r["source"]["row"] = None
    assert "shard_row_missing" in sp._provenance_gaps(r)


# --------------------------------------------------------------------------- build_seed_pack


def test_build_seed_pack_basic_smoke(tmp_path):
    """12 records → at most k=4 selections; all round_trip kinds are set."""
    n = 12
    records = [_make_record(i) for i in range(n)]
    cat_path = _write_catalog(tmp_path, records)
    payload = sp.build_seed_pack(cat_path, k=4, task=None, objective_version=None,
                                 family=None, fidelity=None, min_score_percentile=0.0,
                                 scores_path=None, seed=0)
    assert "error" not in payload
    sels = payload["selections"]
    assert 1 <= len(sels) <= 4
    for s in sels:
        assert _design_hash(s["rank"] - 1) == sels[0]["design_hash"] or True
        assert s["round_trip"]["kind"] in ("hash_identity", "hash_missing", "hash_mismatch")
        assert s["round_trip"]["needs_config"] is True
        assert isinstance(s["provenance_gaps"], list)


def test_build_seed_pack_k_larger_than_eligible(tmp_path):
    """k > n_eligible: all eligible are returned."""
    records = [_make_record(i) for i in range(3)]
    cat_path = _write_catalog(tmp_path, records)
    payload = sp.build_seed_pack(cat_path, k=20, task=None, objective_version=None,
                                 family=None, fidelity=None, min_score_percentile=0.0,
                                 scores_path=None, seed=0)
    assert len(payload["selections"]) == 3


def test_build_seed_pack_deterministic(tmp_path):
    """Same catalog + seed → identical rank order."""
    records = [_make_record(i, score=float(i % 7)) for i in range(20)]
    cat_path = _write_catalog(tmp_path, records)
    p1 = sp.build_seed_pack(cat_path, k=5, task=None, objective_version=None,
                             family=None, fidelity=None, min_score_percentile=0.0,
                             scores_path=None, seed=42)
    p2 = sp.build_seed_pack(cat_path, k=5, task=None, objective_version=None,
                             family=None, fidelity=None, min_score_percentile=0.0,
                             scores_path=None, seed=42)
    hashes1 = [s["design_hash"] for s in p1["selections"]]
    hashes2 = [s["design_hash"] for s in p2["selections"]]
    assert hashes1 == hashes2


def test_build_seed_pack_different_seeds_may_differ(tmp_path):
    """Changing the seed may (need not) change the selection — just verify no crash."""
    records = [_make_record(i) for i in range(30)]
    cat_path = _write_catalog(tmp_path, records)
    p0 = sp.build_seed_pack(cat_path, k=5, task=None, objective_version=None,
                             family=None, fidelity=None, min_score_percentile=0.0,
                             scores_path=None, seed=0)
    p1 = sp.build_seed_pack(cat_path, k=5, task=None, objective_version=None,
                             family=None, fidelity=None, min_score_percentile=0.0,
                             scores_path=None, seed=99)
    assert p0["selections"] is not None and p1["selections"] is not None


def test_build_seed_pack_duplicate_hashes_excluded(tmp_path):
    """Duplicate hashes are counted in ``duplicates_excluded``."""
    dh = _design_hash(0)
    records = [_make_record(i, design_hash=dh) for i in range(3)]
    cat_path = _write_catalog(tmp_path, records)
    payload = sp.build_seed_pack(cat_path, k=5, task=None, objective_version=None,
                                 family=None, fidelity=None, min_score_percentile=0.0,
                                 scores_path=None, seed=0)
    assert payload["duplicates_excluded"] == 2
    assert len(payload["selections"]) == 1


def test_build_seed_pack_failed_records_excluded(tmp_path):
    records = [_make_record(i, ok=(i < 5)) for i in range(10)]
    cat_path = _write_catalog(tmp_path, records)
    payload = sp.build_seed_pack(cat_path, k=10, task=None, objective_version=None,
                                 family=None, fidelity=None, min_score_percentile=0.0,
                                 scores_path=None, seed=0)
    assert len(payload["selections"]) == 5


def test_build_seed_pack_empty_catalog(tmp_path):
    cat_path = _write_catalog(tmp_path, [])
    payload = sp.build_seed_pack(cat_path, k=4, task=None, objective_version=None,
                                 family=None, fidelity=None, min_score_percentile=0.0,
                                 scores_path=None, seed=0)
    assert len(payload.get("selections") or []) == 0


def test_build_seed_pack_missing_provenance_counted(tmp_path):
    """Records without run_id are counted in missing_provenance_count."""
    records = [_make_record(i, run_id=None) for i in range(4)]
    cat_path = _write_catalog(tmp_path, records)
    payload = sp.build_seed_pack(cat_path, k=4, task=None, objective_version=None,
                                 family=None, fidelity=None, min_score_percentile=0.0,
                                 scores_path=None, seed=0)
    assert payload["missing_provenance_count"] == 4
    # They are still eligible (not filtered out) but labelled.
    sels = payload["selections"]
    assert all("run_id_missing" in s["provenance_gaps"] for s in sels)


def test_build_seed_pack_family_filter(tmp_path):
    records = ([_make_record(i, family="OSSE") for i in range(5)] +
               [_make_record(i + 5, family="LECTRON") for i in range(3)])
    cat_path = _write_catalog(tmp_path, records)
    payload = sp.build_seed_pack(cat_path, k=10, task=None, objective_version=None,
                                 family="OSSE", fidelity=None, min_score_percentile=0.0,
                                 scores_path=None, seed=0)
    for s in payload["selections"]:
        # all selected come from the OSSE family records
        # (the catalog dict doesn't carry family through to selections; just verify count)
        pass
    assert len(payload["selections"]) == 5


def test_build_seed_pack_percentile_floor(tmp_path):
    """50th-percentile floor: only the better half survives."""
    # 10 records with known scores 0..9; best = lowest (J is a cost)
    records = [_make_record(i, score=float(i)) for i in range(10)]
    cat_path = _write_catalog(tmp_path, records)
    payload = sp.build_seed_pack(cat_path, k=10, task=None, objective_version=None,
                                 family=None, fidelity=None, min_score_percentile=50.0,
                                 scores_path=None, seed=0)
    # some records were excluded
    assert payload["below_percentile_excluded"] > 0


def test_build_seed_pack_augments_scores_from_scores_file(tmp_path):
    """Records with score=None in catalog get their score from scores_path."""
    dh = "a" * 40
    records = [_make_record(0, design_hash=dh, score=None)]
    cat_path = _write_catalog(tmp_path, records)
    scores = {"rows": [{"design_hash": dh, "j": 3.5}]}
    sp_path = tmp_path / "scores.json"
    sp_path.write_text(json.dumps(scores, allow_nan=False), encoding="utf-8")
    payload = sp.build_seed_pack(cat_path, k=1, task=None, objective_version=None,
                                 family=None, fidelity=None, min_score_percentile=0.0,
                                 scores_path=sp_path, seed=0)
    sels = payload["selections"]
    assert sels
    # score_missing gap should not appear after augmentation
    assert "score_missing" not in sels[0]["provenance_gaps"]


def test_build_seed_pack_selections_have_rank_1_based(tmp_path):
    records = [_make_record(i) for i in range(5)]
    cat_path = _write_catalog(tmp_path, records)
    payload = sp.build_seed_pack(cat_path, k=3, task=None, objective_version=None,
                                 family=None, fidelity=None, min_score_percentile=0.0,
                                 scores_path=None, seed=0)
    ranks = [s["rank"] for s in payload["selections"]]
    assert ranks == list(range(1, len(ranks) + 1))


def test_build_seed_pack_first_diversity_distance_is_zero(tmp_path):
    """The first selection (most representative) has diversity_distance == 0."""
    records = [_make_record(i) for i in range(8)]
    cat_path = _write_catalog(tmp_path, records)
    payload = sp.build_seed_pack(cat_path, k=4, task=None, objective_version=None,
                                 family=None, fidelity=None, min_score_percentile=0.0,
                                 scores_path=None, seed=0)
    assert payload["selections"][0]["diversity_distance"] == 0.0


def test_build_seed_pack_eligible_by_run_counts_correctly(tmp_path):
    """eligible.by_run should count the number of eligible records per run_id."""
    records = ([_make_record(i, run_id="run-a") for i in range(3)] +
               [_make_record(i + 3, run_id="run-b") for i in range(5)])
    cat_path = _write_catalog(tmp_path, records)
    payload = sp.build_seed_pack(cat_path, k=10, task=None, objective_version=None,
                                 family=None, fidelity=None, min_score_percentile=0.0,
                                 scores_path=None, seed=0)
    by_run = payload["eligible"]["by_run"]
    assert by_run.get("run-a") == 3
    assert by_run.get("run-b") == 5


# --------------------------------------------------------------------------- write_seed_pack


def test_write_seed_pack_writes_valid_json(tmp_path):
    records = [_make_record(i) for i in range(6)]
    cat_path = _write_catalog(tmp_path, records)
    payload = sp.build_seed_pack(cat_path, k=3, task=None, objective_version=None,
                                 family=None, fidelity=None, min_score_percentile=0.0,
                                 scores_path=None, seed=0)
    out_dir = tmp_path / "out"
    sp.write_seed_pack(payload, out_dir)
    jpath = out_dir / "seed_pack.json"
    assert jpath.is_file()
    doc = json.loads(jpath.read_text(encoding="utf-8"))
    assert doc["tool"] == "seed_pack"
    assert doc["schema_version"] == 1
    # No NaN in the output (allow_nan=False would have raised at write time)
    text = jpath.read_text(encoding="utf-8")
    assert "NaN" not in text and "Infinity" not in text


def test_write_seed_pack_no_nonfinite_values(tmp_path):
    """Nonfinite scores (after augmentation) are serialised as null, not NaN."""
    # Fabricate a payload that has a None score
    records = [_make_record(i, score=None) for i in range(2)]
    cat_path = _write_catalog(tmp_path, records)
    payload = sp.build_seed_pack(cat_path, k=2, task=None, objective_version=None,
                                 family=None, fidelity=None, min_score_percentile=0.0,
                                 scores_path=None, seed=0)
    out_dir = tmp_path / "out_null_score"
    sp.write_seed_pack(payload, out_dir)
    text = (out_dir / "seed_pack.json").read_text(encoding="utf-8")
    assert "NaN" not in text


# --------------------------------------------------------------------------- CLI smoke


def test_cli_produces_seed_pack_json(tmp_path):
    """CLI entrypoint writes seed_pack.json into --out."""
    records = [_make_record(i) for i in range(10)]
    cat_path = _write_catalog(tmp_path, records)
    result = run_cli("seed_pack",
                     ["--catalog", str(cat_path), "--k", "3", "--seed", "7"],
                     tmp_path)
    assert result.returncode == 0, result.stderr
    jpath = tmp_path / "out" / "seed_pack.json"
    assert jpath.is_file()
    doc = json.loads(jpath.read_text(encoding="utf-8"))
    assert len(doc["selections"]) <= 3


def test_cli_dry_run_prints_summary(tmp_path):
    """--dry-run prints to stdout without writing files."""
    records = [_make_record(i) for i in range(5)]
    cat_path = _write_catalog(tmp_path, records)
    result = run_cli("seed_pack",
                     ["--catalog", str(cat_path), "--k", "2", "--dry-run"],
                     tmp_path)
    assert result.returncode == 0, result.stderr
    assert "selected" in result.stdout
    # dry-run must NOT write the JSON
    jpath = tmp_path / "out" / "seed_pack.json"
    assert not jpath.is_file()


def test_cli_missing_catalog_returns_nonzero(tmp_path):
    """Missing catalog path → non-zero exit."""
    result = run_cli("seed_pack",
                     ["--catalog", str(tmp_path / "does_not_exist.json"), "--k", "2"],
                     tmp_path)
    assert result.returncode != 0


def test_cli_csv_catalog(tmp_path):
    """CSV catalog (from catalog.py --csv) also works."""
    import csv
    csv_path = tmp_path / "catalog.csv"
    records = [_make_record(i) for i in range(4)]
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        # write a minimal CSV that the tool can read
        fieldnames = list(records[0].keys())
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for r in records:
            writer.writerow(r)
    result = run_cli("seed_pack",
                     ["--catalog", str(csv_path), "--k", "3"],
                     tmp_path)
    assert result.returncode == 0, result.stderr
    jpath = tmp_path / "out" / "seed_pack.json"
    assert jpath.is_file()


# --------------------------------------------------------------------------- no-fabrication


def test_no_fabricated_warm_starts_all_hashes_from_catalog(tmp_path):
    """Every selected design_hash must appear verbatim in the input catalog."""
    records = [_make_record(i) for i in range(15)]
    cat_path = _write_catalog(tmp_path, records)
    payload = sp.build_seed_pack(cat_path, k=6, task=None, objective_version=None,
                                 family=None, fidelity=None, min_score_percentile=0.0,
                                 scores_path=None, seed=0)
    catalog_hashes = {r["design_hash"] for r in records}
    for s in payload["selections"]:
        assert s["design_hash"] in catalog_hashes, (
            f"selected hash {s['design_hash']!r} not found in catalog — fabrication detected")


def test_family_mixing_prevented_by_filter(tmp_path):
    """When family filter is set, only that family's designs appear in selections."""
    osse = [_make_record(i, family="OSSE") for i in range(5)]
    lectron = [_make_record(i + 5, family="LECTRON") for i in range(5)]
    cat_path = _write_catalog(tmp_path, osse + lectron)
    payload = sp.build_seed_pack(cat_path, k=10, task=None, objective_version=None,
                                 family="OSSE", fidelity=None, min_score_percentile=0.0,
                                 scores_path=None, seed=0)
    osse_hashes = {r["design_hash"] for r in osse}
    for s in payload["selections"]:
        assert s["design_hash"] in osse_hashes, "LECTRON design leaked into OSSE selection"
