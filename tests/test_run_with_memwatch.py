"""Offline tests for tools/bench/run_with_memwatch.py (C4 measurement wrapper).

Hermetic: no GPU, no real Windows counters, no solver. The tool is loaded by path (it is a script,
not a package module). The aggregation helper is pure; spawn mode runs a trivial ``-c print('ok')``
child; attach mode uses a temporary runs root that no real host can name, so the no-hosts path is
deterministic even while a production solve owns the real gpu lane.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys

from conftest import REPO

TOOL = REPO / "tools" / "bench" / "run_with_memwatch.py"


def _load_tool():
    spec = importlib.util.spec_from_file_location("run_with_memwatch_tool", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


memwatch = _load_tool()
SPILL_MIB = memwatch._bench_common.SPILL_MIB


# ------------------------------------------------------------------ (c) pure aggregation


def test_aggregate_samples_peak_and_spill():
    samples = [
        {"at": "2026-11-13T00:00:00+00:00", "dedicated_mib": 100, "shared_mib": 200},
        {"at": "2026-11-13T00:00:01+00:00", "dedicated_mib": 300,
         "shared_mib": SPILL_MIB + 88},
    ]
    agg = memwatch.aggregate_samples(samples)
    assert agg["dedicated_peak_mib"] == 300
    assert agg["shared_peak_mib"] == SPILL_MIB + 88
    assert agg["spill_mib"] == 88
    assert agg["spilled"] is True
    assert agg["samples_at"] == ["2026-11-13T00:00:00+00:00", "2026-11-13T00:00:01+00:00"]


def test_aggregate_samples_threshold_is_strict():
    agg = memwatch.aggregate_samples(
        [{"at": "t", "dedicated_mib": 1, "shared_mib": SPILL_MIB}])
    assert agg["shared_peak_mib"] == SPILL_MIB
    assert agg["spill_mib"] == 0
    assert agg["spilled"] is False


def test_aggregate_samples_empty_is_null_not_crash():
    agg = memwatch.aggregate_samples([])
    assert agg["dedicated_peak_mib"] is None
    assert agg["shared_peak_mib"] is None
    assert agg["spill_mib"] is None
    assert agg["spilled"] is False
    assert agg["samples_at"] == []


# ------------------------------------------------------------------ (a) spawn mode


def test_spawn_mode_writes_json_and_propagates_exit_code(tmp_path):
    ok_out = tmp_path / "spawn_ok.json"
    rc = memwatch.main(["--out", str(ok_out), "--", sys.executable, "-c", "print('ok')"])
    assert rc == 0
    data = json.loads(ok_out.read_text(encoding="utf-8"))
    assert data["child_cmd"][0] == sys.executable
    assert data["exit_code"] == 0
    assert data["wall_s"] > 0
    assert data["off_windows"] == (os.name != "nt")
    assert isinstance(data["spilled"], bool)
    assert isinstance(data["pids_sampled"], list)
    assert "samples_at" in data

    bad_out = tmp_path / "spawn_exit3.json"
    rc3 = memwatch.main(["--out", str(bad_out), "--",
                         sys.executable, "-c", "import sys; sys.exit(3)"])
    assert rc3 == 3
    assert json.loads(bad_out.read_text(encoding="utf-8"))["exit_code"] == 3


# ------------------------------------------------------------------ (b) attach, no hosts


def test_attach_no_hosts_writes_record_and_exits_zero(tmp_path):
    runs = tmp_path / "runs"
    (runs / "lanes" / "gpu" / "workers").mkdir(parents=True)
    out = tmp_path / "attach.json"
    rc = memwatch.main(["--attach", "--lane", "gpu", "--runs-dir", str(runs),
                        "--deadline-seconds", "1", "--out", str(out)])
    assert rc == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["no_hosts_seen"] is True
    assert data["pids_sampled"] == []
    assert data["child_cmd"] is None
    assert data["exit_code"] == 0
    assert data["wall_s"] > 0
    assert data["off_windows"] == (os.name != "nt")


# ------------------------------------------------------------------ snapshot hardening


def test_snapshot_writer_stamps_partial_and_build_record_tolerates_exit_none():
    snapper = memwatch._snapshot_writer("DUMMY", 0.5)
    assert snapper is not None
    assert snapper["due"](0.0) is True
    assert memwatch._snapshot_writer("DUMMY", None) is None
    assert memwatch._snapshot_writer("DUMMY", 0) is None
    # a running watch has no exit code yet: the record builder must emit null, not crash
    record = memwatch._build_record(child_cmd=["x"], exit_code=None, wall_s=1.0,
                                    agg=memwatch.aggregate_samples([]),
                                    pids_sampled=[], off_windows=False)
    assert record["exit_code"] is None


def test_snapshot_writer_writes_partial_records_at_intervals(tmp_path):
    out = tmp_path / "snap.json"
    snapper = memwatch._snapshot_writer(out, 0.05)
    agg0 = memwatch.aggregate_samples([{"at": "t", "dedicated_mib": 10, "shared_mib": 5}])
    snapper["write"]({"child_cmd": None, "exit_code": None, "agg": agg0,
                      "pids_sampled": {1}, "off_windows": False}, wall_s=0.1, now=0.1)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["partial"] is True
    assert data["exit_code"] is None
    assert data["dedicated_peak_mib"] == 10
    # final record (no partial key) supersedes the snapshot
    agg1 = memwatch.aggregate_samples([{"at": "t", "dedicated_mib": 20, "shared_mib": 6}])
    memwatch._write_json(out, memwatch._build_record(
        child_cmd=None, exit_code=0, wall_s=2.0, agg=agg1, pids_sampled=[], off_windows=False))
    final = json.loads(out.read_text(encoding="utf-8"))
    assert final.get("partial", False) is False
    assert final["exit_code"] == 0


def test_spawn_mode_with_write_every_still_writes_final_record(tmp_path):
    out = tmp_path / "spawn_snap.json"
    rc = memwatch.main(["--out", str(out), "--write-every-seconds", "0.05", "--",
                        sys.executable, "-c", "print('ok')"])
    assert rc == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["exit_code"] == 0
    assert data.get("partial", False) is False
