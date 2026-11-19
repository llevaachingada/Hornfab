"""P5 backend: saved-horn assets, the sourced driver catalog, spec validate/save and ``hw-screen``.

Everything here runs on the real committed tree (assets/drivers/defaults/entry script) or on a
throwaway repository built from the committed files - no meshing, no solver, no GPU.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hornlab_search.gui import data_hw_new as H  # noqa: E402
from hornlab_search.gui import jobs as J  # noqa: E402
from hornlab_search.system import contracts as C  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
DRIVER_TS = REPO / "examples" / "systems" / "driver_ts"
COMMITTED_SPEC = REPO / H.DEFAULT_SPEC_REL
ENTRY = REPO / "tools" / "system" / "gui_system_job.py"
VENV_PY = REPO / ".venv" / "Scripts" / "python.exe"
ASSET = "0123456789abcdef"
SPEC_REL = "examples/systems/two_way_80x50_700_research.yaml"


def _spec_doc() -> dict:
    return copy.deepcopy(yaml.safe_load(COMMITTED_SPEC.read_text(encoding="utf-8")))


def _mini_repo(tmp_path: Path) -> Path:
    """A repository-shaped temp tree with the committed spec and the real driver stems."""
    root = tmp_path / "repo"
    (root / "examples" / "systems").mkdir(parents=True)
    shutil.copyfile(COMMITTED_SPEC, root / SPEC_REL)
    shutil.copytree(DRIVER_TS, root / "examples" / "systems" / "driver_ts")
    (root / "examples" / "systems" / "driver_geometry").mkdir(parents=True)
    (root / "runs").mkdir()
    return root


def _args(**over) -> dict:
    args = {"spec": SPEC_REL, "asset_id": ASSET, "drivers": ["faitalpro_12pr300"],
            "study": "study1", "scan_limit": 50, "limit_boxes": 2, "shortlist_size": 3}
    args.update(over)
    return args


# --------------------------------------------------------------------------- real tree


def test_assets_parse_from_the_real_tree() -> None:
    if not (REPO / "runs").is_dir():
        pytest.skip("canonical runs/ tree is absent")
    data = H.hw_assets(REPO, REPO / "system_runs", limit=2)
    assert isinstance(data["assets"], list) and isinstance(data["notes"], list)
    assert any("no meshing" in n for n in data["notes"])
    for row in data["assets"]:
        assert set(row) == {"asset_id", "name", "brief_id", "design_hash", "quality",
                            "band_hz", "full_domain_mesh", "runs"}
        assert isinstance(row["full_domain_mesh"], bool)
        assert isinstance(row["runs"], list)
        assert row["band_hz"] is None or len(row["band_hz"]) == 2
        if row["band_hz"] is not None:
            assert row["band_hz"][0] <= row["band_hz"][1]


def test_full_domain_index_reads_the_records_own_design_hash() -> None:
    store = REPO / "system_runs"
    if not (store / "system" / "ref_case" / "horn_full").is_dir():
        pytest.skip("no recorded full-domain cases")
    index = H._full_domain_index(store)
    assert index, "recorded full-domain cases must expose their design_hash_original"
    for entry in index.values():
        assert entry["mesh_path"].endswith("mesh.msh")
        assert Path(store, entry["mesh_path"]).is_file()


def test_drivers_parse_from_the_real_tree() -> None:
    if not DRIVER_TS.is_dir():
        pytest.skip("driver T/S tree is absent")
    data = H.hw_drivers(REPO, REPO / "system_runs")
    by_id = {d["driver_id"]: d for d in data["drivers"]}
    assert {"faitalpro_10pr300", "faitalpro_10pr320",
            "faitalpro_12pr300", "faitalpro_12pr320"} <= set(by_id)
    twelve = by_id["faitalpro_12pr300"]
    assert twelve["name"] == "FaitalPRO 12PR300"
    assert twelve["qts"] == pytest.approx(0.36, abs=0.02)      # derived from the YAML's own fields
    assert twelve["provenance"]["field_sources"]["qts"] == "derived"
    assert twelve["provenance"]["field_sources"]["vas_l"] == "derived"
    assert twelve["provenance"]["field_sources"]["fs_hz"] == "vendor"
    assert twelve["geometry"]["complete"] is False
    assert "dust_cap_diameter_mm" in twelve["geometry"]["missing_fields"]
    assert twelve["provenance"]["ts_source"].startswith("https://")
    assert twelve["geometry"]["present_fields"] == ["cutout_mm", "frame_od_mm", "depth_mm"]


def test_spec_defaults_come_from_the_committed_yaml() -> None:
    if not COMMITTED_SPEC.is_file():
        pytest.skip("committed example spec is absent")
    data = H.hw_spec_defaults(REPO)
    assert data["source"] == SPEC_REL
    assert data["spec"]["schema_version"] == C.SCHEMA_VERSION
    assert data["spec"]["experiment_id"] == "two_way_80x50_700_pilot"
    assert C.parse_system_spec_dict(data["spec"]).experiment_id == "two_way_80x50_700_pilot"


# --------------------------------------------------------------------------- validate_spec


def test_validate_spec_accepts_the_committed_example() -> None:
    out = H.validate_spec(_spec_doc())
    assert out["ok"] is True and out["errors"] == []
    assert out["normalized"]["schema_version"] == C.SCHEMA_VERSION


def test_validate_spec_names_the_bad_field() -> None:
    doc = _spec_doc()
    doc["cabinet"]["external_width_mm_range"] = [510, 340]
    out = H.validate_spec(doc)
    assert out["ok"] is False
    err = out["errors"][0]
    assert err["field"] == "external_width_mm"
    assert err["message"] == "external_width_mm range must be lo <= hi, got [510.0, 340.0]"
    assert out["normalized"] is None


def test_validate_spec_returns_the_parsers_unknown_key_message() -> None:
    doc = _spec_doc()
    doc["not_a_key"] = 1
    out = H.validate_spec(doc)
    assert out["ok"] is False
    assert out["errors"][0]["message"] == "unknown spec keys: ['not_a_key']"


# --------------------------------------------------------------------------- save_spec


def test_save_spec_writes_lf_and_round_trips(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    rel = H.save_spec(root, "my_spec", _spec_doc())
    assert rel == "examples/systems/user/my_spec.yaml"
    path = root / rel
    raw = path.read_bytes()
    assert b"\r\n" not in raw and raw.endswith(b"\n")
    parsed = C.parse_system_spec_dict(yaml.safe_load(path.read_text(encoding="utf-8")))
    assert parsed.experiment_id == "two_way_80x50_700_pilot"


def test_save_spec_never_overwrites_without_replace(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    H.save_spec(root, "my_spec", _spec_doc())
    with pytest.raises(ValueError, match="already exists"):
        H.save_spec(root, "my_spec", _spec_doc())
    assert H.save_spec(root, "my_spec", _spec_doc(), replace=True).endswith("my_spec.yaml")


@pytest.mark.parametrize("name", [
    "../escape", "a/b", "a\\b", "", ".hidden", "a..b", "x" * 122, "a b", None, 7,
])
def test_save_spec_refuses_traversal_names(tmp_path: Path, name) -> None:
    with pytest.raises(ValueError):
        H.save_spec(tmp_path / "repo", name, _spec_doc())


def test_save_spec_refuses_an_invalid_spec_with_the_parser_message(tmp_path: Path) -> None:
    doc = _spec_doc()
    doc["cabinet"]["external_width_mm_range"] = [510, 340]
    with pytest.raises(ValueError, match="external_width_mm range must be lo <= hi"):
        H.save_spec(tmp_path / "repo", "bad", doc)


# --------------------------------------------------------------------------- hw-screen argv


def test_hw_screen_argv_is_cpu_only_and_points_at_screens(tmp_path: Path) -> None:
    root = _mini_repo(tmp_path)
    jm = J.JobManager(root, root / "runs")
    argv, gpu = jm.build_argv("hw-screen", _args(backend="beat_cpu"))
    assert gpu is False
    assert argv == [
        "screen", "--spec", SPEC_REL, "--asset-id", ASSET,
        "--drivers", "faitalpro_12pr300",
        "--out", "system_runs/screens/study1", "--runs-root", "runs",
        "--scan-limit", "50", "--limit-boxes", "2", "--shortlist-size", "3",
    ]
    assert "--backend" not in argv
    assert not any("cuda" in str(x).lower() or "gpu" in str(x).lower() for x in argv)


def test_hw_screen_defaults_come_from_the_spec_and_the_cli() -> None:
    # defaults are checked through the data-layer helper so no temp tree is needed for the study
    argv = H.screen_argv(REPO, {"spec": SPEC_REL, "asset_id": ASSET,
                                "drivers": ["faitalpro_12pr300"]})
    assert argv[argv.index("--out") + 1] == "system_runs/screens/two_way_80x50_700_pilot"
    assert argv[argv.index("--scan-limit") + 1] == "300"
    assert argv[argv.index("--limit-boxes") + 1] == "4"
    assert argv[argv.index("--shortlist-size") + 1] == str(H.DEFAULT_SHORTLIST_SIZE)


@pytest.mark.parametrize("over, field", [
    ({"backend": "beat_cuda"}, "backend"),
    ({"backend": "bempp_cpu"}, "backend"),
    ({"spec": "../outside.yaml"}, "spec"),
    ({"spec": "examples/nope.yaml"}, "spec"),
    ({"scan_limit": 0}, "scan_limit"),
    ({"scan_limit": 5001}, "scan_limit"),
    ({"limit_boxes": 0}, "limit_boxes"),
    ({"limit_boxes": 65}, "limit_boxes"),
    ({"shortlist_size": 0}, "shortlist_size"),
    ({"drivers": []}, "drivers"),
    ({"drivers": ["../x"]}, "drivers"),
    ({"drivers": ["not_a_driver"]}, "drivers"),
    ({"asset_id": "zzz"}, "asset_id"),
    ({"study": "../x"}, "study"),
])
def test_hw_screen_refuses_bad_arguments_with_a_field_name(tmp_path: Path, over, field) -> None:
    root = _mini_repo(tmp_path)
    jm = J.JobManager(root, root / "runs")
    with pytest.raises(J.JobError, match=field):
        jm.build_argv("hw-screen", _args(**over))


def test_hw_screen_refuses_a_spec_the_parser_rejects(tmp_path: Path) -> None:
    root = _mini_repo(tmp_path)
    doc = _spec_doc()
    doc["cabinet"]["external_width_mm_range"] = [510, 340]
    (root / SPEC_REL).write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    with pytest.raises(J.JobError, match="spec: external_width_mm range must be lo <= hi"):
        J.JobManager(root, root / "runs").build_argv("hw-screen", _args())


# --------------------------------------------------------------------------- preview / entry


def test_preview_and_job_view_show_the_real_entry_command(tmp_path: Path) -> None:
    root = _mini_repo(tmp_path)
    jm = J.JobManager(root, root / "runs")
    preview = jm.preview("hw-screen", _args())
    assert preview["gpu"] is False
    assert preview["entry"] == J.HW_ENTRY
    assert preview["command"] == (
        "python tools/system/gui_system_job.py screen "
        "--spec examples/systems/two_way_80x50_700_research.yaml "
        "--asset-id 0123456789abcdef --drivers faitalpro_12pr300 "
        "--out system_runs/screens/study1 --runs-root runs "
        "--scan-limit 50 --limit-boxes 2 --shortlist-size 3")
    job = jm._new_job("hw-screen", preview["argv"], False)
    assert job.entry == "tools/system/gui_system_job.py"
    assert job.view()["command"] == preview["command"]


def test_existing_kinds_keep_the_stock_prefix(tmp_path: Path) -> None:
    run = "20261025T000001Z-screen-bbb222"
    root = tmp_path / "repo"
    (root / "runs" / run).mkdir(parents=True)
    preview = J.JobManager(root, root / "runs").preview("report", {"run": run})
    assert preview["entry"] is None
    assert preview["command"].startswith("hornlab-search report ")


def test_hw_screen_is_refused_while_the_cpu_lane_is_held(tmp_path: Path) -> None:
    root = _mini_repo(tmp_path)
    jm = J.JobManager(root, root / "runs")
    (root / "runs" / ".cpu.lane.lock").write_text(
        json.dumps({"pid": os.getpid(), "user": "night", "command": "night 1"}), encoding="utf-8")
    with pytest.raises(J.JobError, match=r"CPU lane busy \(night"):
        jm.launch("hw-screen", _args())


def test_only_one_system_job_at_a_time(tmp_path: Path) -> None:
    root = _mini_repo(tmp_path)
    jm = J.JobManager(root, root / "runs")
    running = jm._new_job("hw-screen", ["screen"], False)
    running.status = "running"
    jm.jobs[running.id] = running
    with pytest.raises(J.JobError, match="system job started from this GUI is still running"):
        jm.launch("hw-screen", _args())


def test_entry_script_is_importable_and_helpable(capsys: pytest.CaptureFixture) -> None:
    if not ENTRY.is_file():
        pytest.skip("entry script is absent")
    spec = importlib.util.spec_from_file_location("gui_system_job", ENTRY)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert callable(module.main)
    assert module.main(["--help"]) == 0
    out = capsys.readouterr().out
    first, *rest = out.splitlines()
    assert first.startswith("gui_system_job argv: --help")
    assert "screen" in "\n".join(rest) and "reference" in "\n".join(rest)


def test_entry_script_runs_under_the_venv_python() -> None:
    if not VENV_PY.is_file() or not ENTRY.is_file():
        pytest.skip("venv interpreter or entry script is absent")
    proc = subprocess.run([str(VENV_PY), str(ENTRY), "--help"], cwd=str(REPO),
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.splitlines()[0].startswith("gui_system_job argv: --help")
