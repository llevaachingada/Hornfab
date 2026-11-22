"""Stage 2 CLI tests: help, driver listing, LF-only pilot smoke with manifest determinism."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from hornlab_search.system import cli  # noqa: E402
from hornlab_search.system import provenance  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
SPEC = REPO / "examples" / "systems" / "two_way_80x50_700_research.yaml"


def test_help_is_available(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        cli.main(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "pilot" in out and "list-drivers" in out and "list-assets" in out
    assert "funnel" in out
    assert "screen-calibration" in out


def test_screen_calibration_help_is_available(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        cli.main(["screen-calibration", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    for flag in ("--out", "--rel-tol", "--max-deg", "--driver-id", "--generated-utc"):
        assert flag in out


def test_funnel_help_and_empty_store_smoke(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as exc:
        cli.main(["funnel", "--help"])
    assert exc.value.code == 0
    out_dir = tmp_path / "funnel"
    assert cli.main(["funnel", "--root", str(tmp_path), "--out", str(out_dir)]) == 0
    assert (out_dir / "funnel_ledger.json").is_file()
    assert (out_dir / "funnel_ledger.md").is_file()


def test_pilot_help_documents_new_flags(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        cli.main(["pilot", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    for flag in ("--spec", "--driver-stem", "--asset-id", "--scan-limit", "--limit-boxes",
                 "--driver-ts-dir", "--geometry", "--runs-root", "--out"):
        assert flag in out


def test_list_drivers_sees_the_verified_12inch_stems() -> None:
    code = cli.main(["list-drivers"])
    assert code == 0


def test_pilot_lf_only_smoke_writes_a_manifest_and_is_reproducible(tmp_path: Path) -> None:
    argv = ["pilot", "--spec", str(SPEC), "--driver-stem", "faitalpro_12pr300",
            "--limit-boxes", "2", "--out", str(tmp_path)]
    assert cli.main(argv) == 0
    base = tmp_path / "system"
    case_dirs = sorted((base / "two_way_80x50_700_pilot").iterdir())
    assert len(case_dirs) == 1
    payload = provenance.load_manifest(case_dirs[0] / "manifest.json")["payload"]
    study = payload["study_id"]
    assert payload["kind"] == "system_pilot_v0"
    assert len(payload["rows"]) == 2

    assert cli.main(argv) == 0   # second, identical run
    case_dirs = sorted((base / "two_way_80x50_700_pilot").iterdir())
    assert len(case_dirs) == 2   # immutable store: a NEW case dir, never a rewrite
    second = provenance.load_manifest(case_dirs[1] / "manifest.json")["payload"]
    assert second["study_id"] == study
    assert second["rows"] == payload["rows"]


def test_pilot_rejects_unknown_spec_key(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text(SPEC.read_text(encoding="utf-8").replace(
        "fidelity: screen_only", "fidelity: screen_only\npredictor: off"), encoding="utf-8")
    with pytest.raises(Exception, match="unknown spec keys"):
        cli.main(["pilot", "--spec", str(bad), "--driver-stem", "faitalpro_12pr300",
                  "--out", str(tmp_path)])
