"""Offline tests for the optional night-runner admission gate (``--admission PATH``).

The gate is a policy check, not a sandbox: it refuses a whole night unless a JSON packet names
the night and exactly its job ids. Hermetic: no GPU, no Julia, no ``hornlab-search`` subprocess;
the tool is loaded by path like ``test_tools_night_runner.py``.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest
import yaml

from conftest import REPO

TOOL = REPO / "tools" / "run_campaign_night.py"


def _load_tool():
    spec = importlib.util.spec_from_file_location("run_campaign_night_admission", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


night = _load_tool()

NIGHT = "held_2026-11-15"


# ------------------------------------------------------------------ helpers


def _night_doc(ids: tuple[str, ...] = ("alpha", "beta")) -> dict:
    return {
        "night": NIGHT,
        "jobs": [{"id": job_id, "kind": "command", "argv": ["echo", job_id]}
                 for job_id in ids],
    }


def _write_night(tmp_path: Path, doc: dict | None = None) -> Path:
    path = tmp_path / "night.yaml"
    path.write_text(yaml.safe_dump(doc or _night_doc(), sort_keys=False), encoding="utf-8")
    return path


def _write_admission(tmp_path: Path, payload: object) -> Path:
    path = tmp_path / "admission.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _write_raw_admission(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "admission.json"
    path.write_text(text, encoding="utf-8")
    return path


def _refuse_launch(monkeypatch) -> None:
    """Prove a refused night reaches no job: ``run_night`` must never be called."""
    def boom(*args, **kwargs):  # pragma: no cover - only fires on a gate bypass
        raise AssertionError("run_night was called for a refused admission")

    monkeypatch.setattr(night, "run_night", boom)


# ------------------------------------------------------------------ default behaviour


def test_no_admission_flag_keeps_existing_dry_run_behaviour(tmp_path, capsys):
    rc = night.main(["--night", str(_write_night(tmp_path)), "--dry-run"])

    assert rc == 0
    out = capsys.readouterr().out
    assert "admission" not in out.lower()
    assert "night: " in out and "alpha" in out and "beta" in out


def test_admission_argument_defaults_to_none():
    args = night._parse_args(["--night", "night.yaml"])
    assert args.admission is None


# ------------------------------------------------------------------ accepted packet


def test_matching_admission_is_accepted_and_dry_run_still_prints_the_plan(
        tmp_path, capsys):
    night_path = _write_night(tmp_path)
    admission = _write_admission(
        tmp_path, {"night": NIGHT, "allowed_job_ids": ["alpha", "beta"]})

    rc = night.main(["--night", str(night_path), "--admission", str(admission), "--dry-run"])

    assert rc == 0
    out = capsys.readouterr().out
    assert f"admission accepted for night {NIGHT}: 2 job(s) allowed" in out
    assert "1. alpha [command]" in out and "2. beta [command]" in out


def test_load_admission_normalises_ids_and_check_admission_accepts(tmp_path):
    admission = night.load_admission(_write_admission(
        tmp_path, {"night": NIGHT, "allowed_job_ids": ["alpha", "beta"]}))
    assert admission == {"night": NIGHT, "allowed_job_ids": ("alpha", "beta")}

    plan = night.load_night(_write_night(tmp_path), repo_root=tmp_path)
    night.check_admission(plan, admission)  # does not raise


# ------------------------------------------------------------------ packet is missing/broken


def test_missing_admission_file_is_refused(tmp_path, capsys, monkeypatch):
    _refuse_launch(monkeypatch)
    missing = tmp_path / "nope.json"

    rc = night.main(["--night", str(_write_night(tmp_path)), "--admission", str(missing)])

    assert rc == 2
    err = capsys.readouterr().err
    assert "cannot read admission file" in err and "nope.json" in err


def test_invalid_json_is_refused(tmp_path, capsys, monkeypatch):
    _refuse_launch(monkeypatch)
    admission = _write_raw_admission(tmp_path, "{not json")

    rc = night.main(["--night", str(_write_night(tmp_path)), "--admission", str(admission)])

    assert rc == 2
    assert "invalid JSON in admission file" in capsys.readouterr().err


def test_non_object_json_is_refused(tmp_path, capsys, monkeypatch):
    _refuse_launch(monkeypatch)
    admission = _write_admission(tmp_path, ["alpha", "beta"])

    rc = night.main(["--night", str(_write_night(tmp_path)), "--admission", str(admission)])

    assert rc == 2
    assert "admission must be a JSON object" in capsys.readouterr().err


# ------------------------------------------------------------------ night field


def test_missing_night_is_refused(tmp_path, capsys, monkeypatch):
    _refuse_launch(monkeypatch)
    admission = _write_admission(tmp_path, {"allowed_job_ids": ["alpha", "beta"]})

    rc = night.main(["--night", str(_write_night(tmp_path)), "--admission", str(admission)])

    assert rc == 2
    assert "admission 'night' must be a non-empty string" in capsys.readouterr().err


def test_mismatched_night_is_refused(tmp_path, capsys, monkeypatch):
    _refuse_launch(monkeypatch)
    admission = _write_admission(
        tmp_path, {"night": "other_night", "allowed_job_ids": ["alpha", "beta"]})

    rc = night.main(["--night", str(_write_night(tmp_path)), "--admission", str(admission)])

    assert rc == 2
    err = capsys.readouterr().err
    assert "does not match night" in err
    assert "other_night" in err and NIGHT in err


# ------------------------------------------------------------------ allowed_job_ids field


@pytest.mark.parametrize("payload, expected", [
    ({"night": NIGHT}, "admission 'allowed_job_ids' must be a list"),
    ({"night": NIGHT, "allowed_job_ids": "alpha"},
     "admission 'allowed_job_ids' must be a list"),
    ({"night": NIGHT, "allowed_job_ids": []},
     "admission 'allowed_job_ids' must not be empty"),
    ({"night": NIGHT, "allowed_job_ids": ["alpha", 7]},
     "admission allowed_job_ids[1] must be a non-empty string"),
    ({"night": NIGHT, "allowed_job_ids": ["alpha", ""]},
     "admission allowed_job_ids[1] must be a non-empty string"),
    ({"night": NIGHT, "allowed_job_ids": ["alpha", "alpha"]},
     "admission allowed_job_ids contains duplicate id 'alpha'"),
])
def test_bad_allowed_job_ids_are_refused(tmp_path, capsys, monkeypatch, payload, expected):
    _refuse_launch(monkeypatch)
    admission = _write_admission(tmp_path, payload)

    rc = night.main(["--night", str(_write_night(tmp_path)), "--admission", str(admission)])

    assert rc == 2
    assert expected in capsys.readouterr().err


# ------------------------------------------------------------------ plan membership


def test_unlisted_job_refuses_the_whole_night(tmp_path, capsys, monkeypatch):
    _refuse_launch(monkeypatch)
    admission = _write_admission(
        tmp_path, {"night": NIGHT, "allowed_job_ids": ["alpha"]})

    rc = night.main(["--night", str(_write_night(tmp_path)), "--admission", str(admission)])

    assert rc == 2
    err = capsys.readouterr().err
    assert "not in admission allowed_job_ids: beta" in err
    assert "refusing the whole night" in err


def test_stale_allowed_id_is_refused(tmp_path, capsys, monkeypatch):
    _refuse_launch(monkeypatch)
    admission = _write_admission(
        tmp_path, {"night": NIGHT, "allowed_job_ids": ["alpha", "beta", "ghost"]})

    rc = night.main(["--night", str(_write_night(tmp_path)), "--admission", str(admission)])

    assert rc == 2
    err = capsys.readouterr().err
    assert "(stale packet): ghost" in err
