"""Offline tests for ``hornlab_search.system.jobs`` (contract section 6)."""
from __future__ import annotations

import os
import shlex
import subprocess
import sys

import pytest

from hornlab_search.system.jobs import (
    JOB_KINDS,
    JobError,
    build_job,
    preview,
)

CLI = "hornlab_search.system.cli"
SEED = "hornlab_search.system.woofer_seed"

KIND_KWARGS = {
    "screen": dict(spec="examples/systems/x.yaml", asset_id="a" * 16, drivers=["d1", "d2"]),
    "pilot": dict(spec="examples/systems/x.yaml", asset_id="a" * 16, limit_boxes=4),
    "portfolio": dict(spec="examples/systems/x.yaml", driver_stems=["d1", "d2"], k=4),
    "bl_stage": dict(root="C:/bl", dry_run=True),
    "bl_validate": dict(case_dir="system_runs/system/e/c", request="req.json"),
    "bl_solve": dict(case_dir="system_runs/system/e/c", request="req.json",
                     authorization_id="AUTH-0001"),
    "funnel": dict(plan="plan.json", execute=True, allow_bl=True, authorization="auth.json"),
}


def _joined(job) -> str:
    if os.name == "nt":
        return subprocess.list2cmdline(list(job.argv))
    return shlex.join(list(job.argv))


def test_every_contract_kind_is_covered() -> None:
    assert set(JOB_KINDS) == set(KIND_KWARGS)


@pytest.mark.parametrize("kind", JOB_KINDS)
def test_preview_equals_the_joined_argv_for_every_kind(kind: str) -> None:
    job = build_job(kind, **KIND_KWARGS[kind])
    assert preview(job) == _joined(job)
    assert job.argv[0] == sys.executable
    assert job.kind == kind
    assert job.lane == "cpu"
    assert dict(job.env) == {}


@pytest.mark.parametrize("kind,verb", [
    ("pilot", ("pilot",)),
    ("portfolio", ("portfolio",)),
    ("bl_stage", ("reference", "prepare")),
    ("bl_validate", ("reference", "validate")),
    ("bl_solve", ("reference", "solve")),
    ("funnel", ("funnel",)),
])
def test_reference_and_cli_kinds_use_the_cli_module(kind: str, verb: tuple[str, ...]) -> None:
    job = build_job(kind, **KIND_KWARGS[kind])
    assert job.argv[1:3] == ("-m", CLI)
    assert job.argv[3:3 + len(verb)] == verb


def test_screen_uses_the_woofer_seed_module_like_the_gui_bridge() -> None:
    job = build_job("screen", **KIND_KWARGS["screen"])
    assert job.argv[1:3] == ("-m", SEED)
    assert job.argv[3:5] == ("--spec", "examples/systems/x.yaml")
    assert job.argv[job.argv.index("--drivers") + 1:job.argv.index("--drivers") + 3] == ("d1", "d2")


def test_bl_solve_without_authorization_refuses_at_build_time() -> None:
    with pytest.raises(JobError) as caught:
        build_job("bl_solve", case_dir="system_runs/system/e/c", request="req.json")
    assert caught.value.token == "AUTH_MISSING"
    assert "AUTH_MISSING" in str(caught.value)
    assert caught.value.detail == ""


def test_bl_solve_records_and_forwards_the_authorization_id() -> None:
    job = build_job("bl_solve", **KIND_KWARGS["bl_solve"])
    assert job.authorization_id == "AUTH-0001"
    assert "--authorized-by" in job.argv
    assert job.argv[job.argv.index("--authorized-by") + 1] == "AUTH-0001"


def test_inputs_sha256_is_deterministic_and_input_sensitive() -> None:
    first = build_job("screen", spec="a.yaml", asset_id="a" * 16)
    same = build_job("screen", spec="a.yaml", asset_id="a" * 16)
    other = build_job("screen", spec="b.yaml", asset_id="a" * 16)
    assert first.inputs_sha256 == same.inputs_sha256
    assert first.inputs_sha256 != other.inputs_sha256
    assert len(first.inputs_sha256) == 64


def test_env_and_cwd_are_normalised() -> None:
    job = build_job("pilot", spec="s.yaml", env={"B": "2", "A": "1"}, cwd_rel="sub")
    assert job.env == (("A", "1"), ("B", "2"))
    assert job.cwd_rel == "sub"


def test_unknown_kind_and_argument_refuse_with_tokens() -> None:
    with pytest.raises(JobError) as caught:
        build_job("gpu_run")
    assert caught.value.token == "UNKNOWN_JOB_KIND"
    with pytest.raises(JobError) as caught:
        build_job("pilot", spec="s.yaml", surprise=1)
    assert caught.value.token == "UNKNOWN_ARG"
