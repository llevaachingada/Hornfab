"""tools/data/renumber_objective_v5_to_v7.py: hardened "v5" rows become v7, MEH v5 rows stay 5."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "renumber", ROOT / "tools" / "data" / "renumber_objective_v5_to_v7.py")
rn = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rn)

MEH_START = "2026-10-31T00:00:00Z"


def test_classifier_separates_hardened_from_meh():
    hard = {"objective_version": 5, "terms": {"flat_cv": 0.2}, "created_utc": "2026-11-05T00:00:00Z"}
    hard_failed = {"objective_version": 5, "terms": {"cov": 1.0}, "created_utc": "2026-10-29T03:00:00Z"}
    meh = {"objective_version": 5, "terms": {"lw_resid": 1.0}, "created_utc": "2026-10-29T03:00:00Z"}
    meh_failed = {"objective_version": 5, "terms": {"cov": 1.0}, "created_utc": "2026-11-01T03:00:00Z"}
    v4 = {"objective_version": 4, "terms": {"flat_cv": 1.0}, "created_utc": "2026-10-29T03:00:00Z"}
    assert rn.is_hardened_record(hard, MEH_START)
    assert rn.is_hardened_record(hard_failed, MEH_START)
    assert not rn.is_hardened_record(meh, MEH_START)
    assert not rn.is_hardened_record(meh_failed, MEH_START)
    assert not rn.is_hardened_record(v4, MEH_START)


def _shard(tmp: Path, rows: list[dict]) -> Path:
    (tmp / "dataset").mkdir()
    p = tmp / "dataset" / "shard-0000.jsonl"
    p.write_text("".join(json.dumps(r, separators=(",", ":")) + "\n" for r in rows), encoding="utf-8")
    return p


def test_apply_relabels_only_hardened_rows_backs_up_and_is_idempotent(tmp_path):
    rows = [{"objective_version": 5, "terms": {"flat_cv": 0.1}, "created_utc": "2026-10-29T01:00:00Z"},
            {"objective_version": 5, "terms": {"notch": 0.1}, "created_utc": "2026-11-01T01:00:00Z"}]
    shard = _shard(tmp_path, rows)
    (tmp_path / "runs").mkdir()
    run = tmp_path / "runs" / "20261029T000000Z-screen-x"
    run.mkdir()
    (run / "run.json").write_text(json.dumps({"objective_version": 5,
                                              "objective": {"version": 5, "loaded_re_z": 0.4}}),
                                  encoding="utf-8")
    (run / "search.ndjson").write_text('{"objective_version": 5}\n', encoding="utf-8")
    meh_run = tmp_path / "runs" / "20261101T000000Z-screen-y"
    meh_run.mkdir()
    (meh_run / "run.json").write_text(json.dumps({"objective_version": 5, "objective": {"version": 5}}),
                                      encoding="utf-8")

    backup = tmp_path / "bk"
    assert rn.main(["--repo", str(tmp_path), "--backup", str(backup), "--apply"]) == 0
    out = [json.loads(line) for line in shard.read_text(encoding="utf-8").splitlines()]
    assert [r["objective_version"] for r in out] == [7, 5]
    assert json.loads((run / "run.json").read_text())["objective_version"] == 7
    assert json.loads((run / "run.json").read_text())["objective"]["version"] == 7
    assert '"objective_version": 7' in (run / "search.ndjson").read_text()
    assert json.loads((meh_run / "run.json").read_text())["objective_version"] == 5
    assert (backup / "dataset" / "shard-0000.jsonl").is_file()

    before = shard.read_text(encoding="utf-8")
    assert rn.main(["--repo", str(tmp_path), "--backup", str(backup), "--apply"]) == 0
    assert shard.read_text(encoding="utf-8") == before
