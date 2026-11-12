"""Offline tests for the two-lane night runner (2026-11-12): argv building and lane branching.

No GPU, no Julia, no ``hornlab-search`` subprocess. The tool is loaded by path (a script) and its
subprocess/hygiene layer is replaced with a fake wherever a real launcher would be needed.
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest
import yaml

from conftest import REPO

TOOL = REPO / "tools" / "run_campaign_night.py"


def _load_tool():
    spec = importlib.util.spec_from_file_location("run_campaign_night_lanes", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


night = _load_tool()

NIGHT_NAME = "cpu_2026-11-12"


def _write_night(tmp_path: Path, doc: dict) -> Path:
    path = tmp_path / "night.yaml"
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    return path


def _cpu_doc() -> dict:
    return {
        "night": NIGHT_NAME,
        "lane": "cpu",
        "jobs": [{
            "id": "c2_lecleach_small",
            "kind": "search",
            "mode": "screen",
            "budget": 3,
            "backend": "beat_cpu",
            "cache_dir": "cache_cpu",
            "dataset_dir": "dataset_cpu",
            "env": {"HORNLAB_STAGE_TIMING": "1"},
            "config": "examples/typologies/lecleach_rollback.yaml",
        }],
    }


# ------------------------------------------------------------------ lane_env / build_job_env


def test_lane_env_gives_each_lane_its_own_worker_dir(tmp_path):
    gpu = night.lane_env("gpu", tmp_path)
    cpu = night.lane_env("cpu", tmp_path)
    assert gpu["HORNLAB_BEAT_WORKER_DIR"] == str(tmp_path / "lanes" / "gpu" / "workers")
    assert cpu["HORNLAB_BEAT_WORKER_DIR"] == str(tmp_path / "lanes" / "cpu" / "workers")
    assert gpu["HORNLAB_BEAT_WORKER_DIR"] != cpu["HORNLAB_BEAT_WORKER_DIR"]


def test_lane_env_caps_threads_on_the_cpu_lane_only(tmp_path):
    cpu = night.lane_env("cpu", tmp_path)
    gpu = night.lane_env("gpu", tmp_path)
    assert cpu["JULIA_NUM_THREADS"] == str(night.CPU_LANE_THREADS)
    assert cpu["OPENBLAS_NUM_THREADS"] == str(night.CPU_LANE_THREADS)
    assert "JULIA_NUM_THREADS" not in gpu


def test_lane_env_rejects_unknown_lane(tmp_path):
    try:
        night.lane_env("tpu", tmp_path)
    except ValueError as exc:
        assert "lane" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("unknown lane was accepted")


def test_build_job_env_precedence_lane_then_job(tmp_path):
    job = night.Job(id="j", kind="search", argv=("x",), timeout_s=1.0,
                    env={"HORNLAB_NUM_THREADS": "3", "JULIA_NUM_THREADS": "3"})
    env = night.build_job_env(job, "cpu", tmp_path, base={"PATH": "p"})
    assert env["PATH"] == "p"
    assert env["HORNLAB_BEAT_WORKER_DIR"] == str(tmp_path / "lanes" / "cpu" / "workers")
    assert env["JULIA_NUM_THREADS"] == "3"             # job env wins over the lane default
    assert env["OPENBLAS_NUM_THREADS"] == str(night.CPU_LANE_THREADS)


def test_build_job_env_does_not_mutate_the_base(tmp_path):
    base = {"PATH": "p"}
    night.build_job_env(night.Job(id="j", kind="search", argv=("x",), timeout_s=1.0),
                        "cpu", tmp_path, base=base)
    assert base == {"PATH": "p"}


# ------------------------------------------------------------------ argv building


def test_search_argv_carries_backend_cache_and_dataset(tmp_path):
    plan = night.load_night(_write_night(tmp_path, _cpu_doc()), repo_root=tmp_path)
    argv = plan.jobs[0].argv
    assert argv[:2] == (str(tmp_path / ".venv" / "Scripts" / "hornlab-search.exe"), "search")
    joined = " ".join(argv)
    assert "--backend beat_cpu" in joined
    assert "--cache-dir cache_cpu" in joined
    assert "--dataset-dir dataset_cpu" in joined
    assert plan.jobs[0].backend == "beat_cpu"
    assert plan.jobs[0].cache_dir == "cache_cpu"
    assert plan.jobs[0].dataset_dir == "dataset_cpu"
    assert plan.jobs[0].env == {"HORNLAB_STAGE_TIMING": "1"}


def test_search_argv_omits_absent_optional_flags(tmp_path):
    doc = {"night": "n", "jobs": [{"id": "j", "kind": "search", "budget": 1,
                                   "config": "examples/osse_baseline.yaml"}]}
    plan = night.load_night(_write_night(tmp_path, doc), repo_root=tmp_path)
    joined = " ".join(plan.jobs[0].argv)
    assert "--backend" not in joined and "--cache-dir" not in joined
    assert "--dataset-dir" not in joined
    assert plan.lane == "gpu"                          # top-level lane defaults to gpu


def test_load_night_rejects_an_unknown_lane(tmp_path):
    doc = {"night": "n", "lane": "tpu", "jobs": [{"id": "j", "kind": "search", "budget": 1}]}
    try:
        night.load_night(_write_night(tmp_path, doc), repo_root=tmp_path)
    except ValueError as exc:
        assert "lane" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("unknown lane was accepted")


def test_load_night_validates_env_is_a_mapping(tmp_path):
    doc = {"night": "n", "jobs": [{"id": "j", "kind": "search", "budget": 1, "env": [1, 2]}]}
    try:
        night.load_night(_write_night(tmp_path, doc), repo_root=tmp_path)
    except ValueError as exc:
        assert "env" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("a list env was accepted")


# ------------------------------------------------------------------ no image-name kill remains


def test_the_taskkill_image_name_block_is_gone():
    text = TOOL.read_text(encoding="utf-8")
    assert "/IM" not in text and "taskkill /F /IM" not in text
    assert not hasattr(night, "_kill_julia") and not hasattr(night, "_julia_pids")


# ------------------------------------------------------------------ NightRunner lane branching


def test_cpu_pre_hygiene_skips_the_gpu_lock_and_vram(tmp_path, monkeypatch):
    runner = night.NightRunner(repo_root=tmp_path, runs_root=tmp_path / "runs", lane="cpu")
    monkeypatch.setattr(runner, "_gpu_clean", lambda log_path: 0)
    monkeypatch.setattr(night, "_vram_mb", lambda: (_ for _ in ()).throw(
        AssertionError("cpu lane must not read nvidia-smi")))
    out = runner.pre_hygiene(night.Job(id="j", kind="search", argv=("x",), timeout_s=1.0),
                             tmp_path / "j.log")
    assert out["baseline_mb"] is None


def test_cpu_runner_gpu_clean_is_lane_aware(tmp_path, monkeypatch):
    runner = night.NightRunner(repo_root=tmp_path, runs_root=tmp_path / "runs", lane="cpu")
    seen = {}

    def fake_run_capture(argv, timeout, cwd=None):
        seen["argv"] = argv
        return 0, ""

    monkeypatch.setattr(night, "_run_capture", fake_run_capture)
    runner._gpu_clean(tmp_path / "j.log")
    assert "--lane" in seen["argv"]
    assert seen["argv"][seen["argv"].index("--lane") + 1] == "cpu"


class _LockProbeRunner:
    """FakeRunner that records whether the lane lock is held when hygiene runs."""

    def __init__(self, lock_path: Path):
        self.lock_path = lock_path
        self.lock_live_during_run: list[bool] = []

    def pre_hygiene(self, job, log_path):
        self.lock_live_during_run.append(self.lock_path.exists())
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("pre\n", encoding="utf-8")
        return {"baseline_mb": None, "note": ""}

    def run(self, job, log_path):
        self.lock_live_during_run.append(self.lock_path.exists())
        return 0, False

    def post_hygiene(self, job, log_path):
        self.lock_live_during_run.append(self.lock_path.exists())
        return {"after_mb": None, "peak_mb": None, "note": ""}


def test_cpu_night_holds_the_cpu_lane_marker_for_the_whole_run(tmp_path):
    doc = _cpu_doc()
    plan = night.load_night(_write_night(tmp_path, doc), repo_root=tmp_path)
    runs_root = tmp_path / "runs"
    probe = _LockProbeRunner(runs_root / ".cpu.lane.lock")
    night.run_night(plan, repo_root=tmp_path, runs_root=runs_root, runner=probe)
    assert probe.lock_live_during_run == [True, True, True]
    assert not (runs_root / ".cpu.lane.lock").exists()      # released at the end
    assert not (runs_root / ".gpu.lock").exists()           # cpu lane never takes the GPU lock


def test_gpu_night_does_not_take_the_cpu_marker(tmp_path):
    doc = {"night": "g", "jobs": [{"id": "j", "kind": "command", "argv": ["echo", "x"]}]}
    plan = night.load_night(_write_night(tmp_path, doc), repo_root=tmp_path)
    runs_root = tmp_path / "runs"
    probe = _LockProbeRunner(runs_root / ".cpu.lane.lock")
    night.run_night(plan, repo_root=tmp_path, runs_root=runs_root, runner=probe)
    assert probe.lock_live_during_run == [False, False, False]


# ------------------------------------------------------------------ per-lane row logging (L1.5)


def _evaluation():
    from hornlab_search.types import Design, Evaluation
    return Evaluation(design_hash="d", design=Design("OSSE", {"a": 1.0}), mesh_hash="m",
                      solve_hash="s", objective=1.5, terms={"cov": 0.1}, metrics=None,
                      mesh=None, outcome=None)


def test_current_lane_reads_the_registry_dir_only(monkeypatch):
    from hornlab_search.search.evaluate import current_lane
    monkeypatch.setenv("HORNLAB_BEAT_WORKER_DIR", str(Path("runs") / "lanes" / "cpu" / "workers"))
    assert current_lane() == "cpu"
    monkeypatch.setenv("HORNLAB_BEAT_WORKER_DIR", str(Path("runs") / "lanes" / "gpu" / "workers"))
    assert current_lane() == "gpu"
    monkeypatch.setenv("HORNLAB_BEAT_WORKER_DIR", "C:\\w")
    assert current_lane() is None
    monkeypatch.delenv("HORNLAB_BEAT_WORKER_DIR", raising=False)
    assert current_lane() is None


def test_row_lane_and_backend_are_additive_and_omitted_when_unknown():
    from hornlab_search.search.evaluate import evaluation_to_row
    ev = _evaluation()
    plain = evaluation_to_row(ev, "screen", 0, {})
    assert "lane" not in plain and "backend" not in plain
    tagged = evaluation_to_row(ev, "screen", 0, {}, lane="cpu", backend="beat_cpu")
    assert tagged["lane"] == "cpu" and tagged["backend"] == "beat_cpu"
    assert tagged["key"] == plain["key"] and tagged["objective"] == plain["objective"]


# ------------------------------------------------------------------ command-kind log parsing (L1.3)


def test_parse_run_dir_from_search_ok_line(tmp_path):
    """``parse_run_dir`` finds the run dir from the CLI's ``search OK: N rows in <dir>/search.ndjson``
    summary line — which appears in COMMAND-kind jobs wrapping hornlab-search search."""
    run_dir = tmp_path / "runs" / "20261112T000000Z-screen-abc123"
    log = (
        "search: runs/... output ...\n"
        "  seed J=0.5  best J=0.3 (improved on the seed); stop: budget\n"
        f"search OK: 400 rows in {run_dir}/search.ndjson; "
        "best in <dir>/best.json; report with: hornlab-search report <dir>\n"
    )
    parsed = night.parse_run_dir(log, repo_root=tmp_path)
    assert parsed == run_dir


def test_parse_best_j_from_command_job_log():
    """``parse_best_j`` works for COMMAND-kind job logs."""
    log = "  seed J=0.500000  best J=0.312345 (improved on the seed); stop: budget\n"
    assert night.parse_best_j(log) == pytest.approx(0.312345)


def test_command_job_result_carries_run_dir_and_evals(tmp_path):
    """When a COMMAND job writes the ``search OK`` line, ``_run_one`` fills in run_dir and evals."""
    run_dir = tmp_path / "runs" / "20261112T000000Z-screen-abc123"
    run_dir.mkdir(parents=True)
    ndjson = run_dir / "search.ndjson"
    ndjson.write_text(
        '{"ok":true,"n":0}\n{"ok":true,"n":1}\n{"ok":false,"n":2}\n',
        encoding="utf-8")

    log_text = (
        "hornlab-search search --config examples/foo.yaml --budget 10 --mode screen\n"
        "  seed J=0.5  best J=0.31 (improved on the seed); stop: budget\n"
        f"search OK: 3 rows in {run_dir}/search.ndjson; "
        f"best in {run_dir}/best.json; report with: hornlab-search report {run_dir}\n"
    )

    class _LogWriterRunner:
        """A runner that writes the prepared log text and returns exit 0."""
        def pre_hygiene(self, job, log_path):
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_path.write_text("", encoding="utf-8")
            return {"baseline_mb": None, "note": ""}

        def run(self, job, log_path):
            # Append the log text so _run_one's _read_text sees it
            with open(log_path, "a", encoding="utf-8") as fh:
                fh.write(log_text)
            return 0, False

        def post_hygiene(self, job, log_path):
            return {"after_mb": None, "peak_mb": None, "note": ""}

    doc = {
        "night": "test", "lane": "cpu",
        "jobs": [{"id": "c1", "kind": "command", "argv": ["echo", "done"]}],
    }
    plan = night.load_night(_write_night(tmp_path, doc), repo_root=tmp_path)
    result = night._run_one(plan, plan.jobs[0],
                            night_dir=tmp_path, runner=_LogWriterRunner(),
                            repo_root=tmp_path)
    assert result.run_dir is not None and str(run_dir) in result.run_dir
    assert result.evals_ndjson == 3
    assert result.best_J == pytest.approx(0.31)

