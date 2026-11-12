"""Offline tests for tools/data/merge_lane_dataset.py (D.3, 2026-11-12).

Hermetic: the CPU-lane dataset, the main dataset and the parity report are tiny JSON
fixtures in tmp_path. No real dataset, no GPU, no network.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from conftest import REPO

TOOL = REPO / "tools" / "data" / "merge_lane_dataset.py"


def _load_tool():
    spec = importlib.util.spec_from_file_location("merge_lane_dataset_tool", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


merge = _load_tool()


# ------------------------------------------------------------------ fixtures


def _row(**over):
    rec = {
        "design_hash": "aaaa1111",
        "mesh_hash": "mmmm",
        "solve_hash": "ssss",
        "family": "OSSE",
        "objective_version": 7,
        "solve": {"backend": "beat_cpu", "mode": "screen"},
        "objective": 3.2,
        "ok": True,
        "created_utc": "2026-11-12T14:38:19Z",
        "provenance": {"config": "atlas__ath_core", "brief": "native_ath_core_2in_v4"},
    }
    rec.update(over)
    return rec


def _dataset(tmp_path: Path, name: str, rows: list[dict]) -> Path:
    root = tmp_path / name
    root.mkdir(parents=True)
    (root / "shard-0001.jsonl").write_text(
        "".join("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n"
                if rows else ""), encoding="utf-8")
    return root


def _parity(tmp_path: Path, **over) -> Path:
    report = {"tool": "lane_parity", "generated_utc": "2026-11-12T18:00:00Z",
              "n_compared": 3, "n_within_0p2": 3, "threshold_db": 0.2, "min_designs": 3,
              "pass": True, "gate": "CP-7b"}
    report.update(over)
    path = tmp_path / "parity.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    return path


def _run(tmp_path, args):
    return merge.main(args)


def _shard_rows(dst: Path) -> list[dict]:
    path = dst / merge.LANE_SHARD_NAME
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


# ------------------------------------------------------------------ parity gate


def test_parity_verdict_accepts_schema_and_drift():
    passed, _ = merge.parity_verdict({"pass": True})
    assert passed is True
    assert merge.parity_verdict({"pass": False})[0] is False
    assert merge.parity_verdict({"verdict": "PASS"})[0] is True
    assert merge.parity_verdict({"status": "passed"})[0] is True
    assert merge.parity_verdict({"result": "PASS"})[0] is True
    assert merge.parity_verdict({"verdict": "FAIL"})[0] is False
    assert merge.parity_verdict({})[0] is False          # fail closed


def test_unreadable_parity_report_fails_loudly(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    try:
        merge.load_parity(bad)
    except SystemExit as exc:
        assert "not valid JSON" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("unreadable parity was accepted")


# ------------------------------------------------------------------ selection


def test_selection_takes_only_cpu_rows_and_tags_provenance(tmp_path):
    src = _dataset(tmp_path, "dataset_cpu", [
        _row(design_hash="cpu1"),
        _row(design_hash="gpu1", solve={"backend": "beat_cuda", "mode": "screen"}),
        _row(design_hash="nobackend", solve={}),
    ])
    dst = _dataset(tmp_path, "dataset", [_row(design_hash="already",
                                              solve={"backend": "beat_cuda", "mode": "screen"})])
    plan_data = merge.plan_merge(src, dst)
    selected = [rec["design_hash"] for _, rec in plan_data["selected"]]
    assert selected == ["cpu1"]
    assert plan_data["skipped_not_cpu"] == 2
    assert plan_data["skipped_duplicate"] == 0
    tagged = plan_data["selected"][0][1]
    assert tagged["provenance"]["lane"] == "cpu"
    assert tagged["provenance"]["config"] == "atlas__ath_core"   # old provenance keys kept


def test_selection_skips_rows_already_in_destination(tmp_path):
    cpu_row = _row(design_hash="dup", solve={"backend": "beat_cpu", "mode": "screen"})
    src = _dataset(tmp_path, "dataset_cpu", [cpu_row])
    # The destination already holds the same design/mesh/solve/version/mode identity.
    dst = _dataset(tmp_path, "dataset", [dict(cpu_row, solve={"backend": "beat_cuda",
                                                              "mode": "screen"},
                                              provenance={"origin": "gpu"})])
    plan_data = merge.plan_merge(src, dst)
    assert plan_data["selected"] == []
    assert plan_data["skipped_duplicate"] == 1


# ------------------------------------------------------------------ CLI behaviour


def test_dry_run_is_the_default_and_writes_nothing(tmp_path, capsys):
    src = _dataset(tmp_path, "dataset_cpu", [_row(design_hash="cpu1")])
    dst = _dataset(tmp_path, "dataset", [])
    parity = _parity(tmp_path)

    rc = _run(tmp_path, ["--src", str(src), "--dst", str(dst), "--parity", str(parity)])

    assert rc == 0
    out = capsys.readouterr().out
    assert "would merge row cpu1" in out and "nothing written" in out
    assert not (dst / merge.LANE_SHARD_NAME).exists()
    assert not (dst / merge.MANIFEST_NAME).exists()
    assert [p.name for p in dst.glob("*")] == ["shard-0001.jsonl"]   # only the fixture shard


def test_apply_merges_pass_report_rows_into_the_lane_shard(tmp_path, capsys):
    src = _dataset(tmp_path, "dataset_cpu", [_row(design_hash="cpu1"),
                                             _row(design_hash="cpu2", objective_version=4)])
    dst = _dataset(tmp_path, "dataset", [])
    parity = _parity(tmp_path)

    rc = _run(tmp_path, ["--src", str(src), "--dst", str(dst), "--parity", str(parity),
                         "--apply"])

    assert rc == 0
    rows = _shard_rows(dst)
    assert [r["design_hash"] for r in rows] == ["cpu1", "cpu2"]   # deterministic order
    assert all(r["provenance"]["lane"] == "cpu" for r in rows)
    manifest = json.loads((dst / merge.MANIFEST_NAME).read_text(encoding="utf-8"))
    assert manifest["parity_pass"] is True and manifest["n_rows_total"] == 2
    assert not (dst / "shard-0001.jsonl").read_text(encoding="utf-8").strip()  # existing shards untouched


def test_apply_refuses_when_parity_fails(tmp_path, capsys):
    src = _dataset(tmp_path, "dataset_cpu", [_row()])
    dst = _dataset(tmp_path, "dataset", [])
    parity = _parity(tmp_path, **{"pass": False})

    rc = _run(tmp_path, ["--src", str(src), "--dst", str(dst), "--parity", str(parity),
                         "--apply"])

    assert rc == 1
    assert "does not say PASS" in capsys.readouterr().err
    assert not (dst / merge.LANE_SHARD_NAME).exists()


def test_apply_refuses_when_parity_gate_is_unrecognised(tmp_path, capsys):
    """No recognisable gate -> fail closed: the merge refuses (rc 1), nothing is written."""
    src = _dataset(tmp_path, "dataset_cpu", [_row()])
    dst = _dataset(tmp_path, "dataset", [])
    parity = _parity(tmp_path)
    parity.write_text(json.dumps({"tool": "lane_parity"}), encoding="utf-8")

    rc = _run(tmp_path, ["--src", str(src), "--dst", str(dst), "--parity", str(parity), "--apply"])
    assert rc == 1
    assert "does not say PASS" in capsys.readouterr().err
    assert not (dst / merge.LANE_SHARD_NAME).exists()


def test_rerun_with_same_parity_is_a_noop(tmp_path, capsys):
    src = _dataset(tmp_path, "dataset_cpu", [_row(design_hash="cpu1")])
    dst = _dataset(tmp_path, "dataset", [])
    parity = _parity(tmp_path)
    argv = ["--src", str(src), "--dst", str(dst), "--parity", str(parity), "--apply"]

    assert _run(tmp_path, argv) == 0
    shard = dst / merge.LANE_SHARD_NAME
    first = shard.read_bytes()
    first_manifest = (dst / merge.MANIFEST_NAME).read_bytes()

    capsys.readouterr()
    rc = _run(tmp_path, argv)
    out = capsys.readouterr().out
    assert rc == 0 and "idempotent no-op" in out
    assert shard.read_bytes() == first               # byte-identical, untouched
    assert (dst / merge.MANIFEST_NAME).read_bytes() == first_manifest


def test_existing_merged_rows_survive_a_new_merge(tmp_path, capsys):
    """A second merge with a different parity report keeps the first rows and appends new ones."""
    src = _dataset(tmp_path, "dataset_cpu", [_row(design_hash="cpu1")])
    dst = _dataset(tmp_path, "dataset", [])
    parity_a = _parity(tmp_path)
    argv = ["--src", str(src), "--dst", str(dst), "--parity", str(parity_a), "--apply"]
    assert _run(tmp_path, argv) == 0

    (src / "shard-0002.jsonl").write_text(
        json.dumps(_row(design_hash="cpu3")), encoding="utf-8")
    parity_b = tmp_path / "parity_b.json"
    report = json.loads(parity_a.read_text(encoding="utf-8"))
    parity_b.write_text(json.dumps({**report, "generated_utc": "2026-11-12T19:00:00Z"}),
                        encoding="utf-8")
    capsys.readouterr()
    rc = _run(tmp_path, ["--src", str(src), "--dst", str(dst), "--parity", str(parity_b),
                         "--apply"])
    assert rc == 0
    rows = _shard_rows(dst)
    assert [r["design_hash"] for r in rows] == ["cpu1", "cpu3"]
    # The previous shard was backed up before the rewrite (renumber-tool model)
    backups = list((dst.parent / "_backup_merge_lane").glob(merge.LANE_SHARD_NAME))
    assert len(backups) == 1
    assert [json.loads(line)["design_hash"] for line in
            backups[0].read_text(encoding="utf-8").splitlines() if line.strip()] == ["cpu1"]


def test_missing_inputs_fail_rc_2(tmp_path, capsys):
    src = _dataset(tmp_path, "dataset_cpu", [_row()])
    dst = _dataset(tmp_path, "dataset", [])
    parity = _parity(tmp_path)

    assert merge.main(["--src", str(tmp_path / "ghost"), "--dst", str(dst),
                       "--parity", str(parity)]) == 2
    assert merge.main(["--src", str(src), "--dst", str(dst),
                       "--parity", str(tmp_path / "ghost.json")]) == 2

    empty = tmp_path / "empty_cpu"
    empty.mkdir()
    capsys.readouterr()
    rc = merge.main(["--src", str(empty), "--dst", str(dst), "--parity", str(parity)])
    assert rc == 2
    assert "no shard" in capsys.readouterr().err
