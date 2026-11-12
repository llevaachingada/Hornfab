"""Tests for the two-way HF labs flow in tools/hf_sync.py. Offline: the hf CLI is faked."""
from __future__ import annotations

import io
import json
import sys
import tarfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))

import hf_sync  # noqa: E402
from hornlab_search.dataset.record import build_record  # noqa: E402
from test_dataset_factory import GRID, LIB_SHAS, TARGET, make_eval, solve_spec  # noqa: E402


@pytest.fixture()
def fake_dataset(tmp_path):
    """A small dataset root with one shard of one real record."""
    root = tmp_path / "dataset"
    root.mkdir()
    meta, _ = build_record(make_eval(1), TARGET, LIB_SHAS, solve_spec=solve_spec(), grid=GRID,
                           area_m2=0.125, created_utc="2026-10-13T00:00:00Z")
    (root / "shard-0000.jsonl").write_text(json.dumps(meta, separators=(",", ":")) + "\n",
                                           encoding="utf-8")
    return root


# ------------------------------------------------------------------ pack

def test_pack_runs_the_manifest_census_first_and_includes_it(fake_dataset, tmp_path, capsys):
    stage = tmp_path / "stage"
    hf_sync.pack(stage, ["dataset"], False, dataset_root=fake_dataset, lab="hunter-4060")

    manifest = fake_dataset / "MANIFEST.json"
    assert manifest.is_file()
    doc = json.loads(manifest.read_text(encoding="utf-8"))
    assert doc["lab"] == "hunter-4060" and doc["total_rows"] == 1

    with tarfile.open(stage / "dataset-000.tar") as tf:
        names = set(tf.getnames())
    assert "dataset/shard-0000.jsonl" in names
    assert "dataset/MANIFEST.json" in names
    out = capsys.readouterr().out
    assert "[manifest]" in out and "1 rows" in out


def test_pack_dry_run_writes_nothing(tmp_path, fake_dataset):
    stage = tmp_path / "stage"
    hf_sync.pack(stage, ["dataset"], True, dataset_root=fake_dataset, lab="hunter-4060")
    assert not (fake_dataset / "MANIFEST.json").exists()
    assert not stage.exists() or not list(stage.glob("*.tar"))


def test_pack_without_the_dataset_group_still_ships_the_manifest(fake_dataset, tmp_path,
                                                                 monkeypatch):
    runs = tmp_path / "runs" / "20261031T201057Z-screen-d3158e"
    runs.mkdir(parents=True)
    (runs / "run.json").write_text(json.dumps({"run_id": runs.name}), encoding="utf-8")
    monkeypatch.setattr(hf_sync, "RUNS_ROOT", tmp_path / "runs")

    stage = tmp_path / "stage"
    hf_sync.pack(stage, ["text"], False, dataset_root=fake_dataset, lab="collin")

    with tarfile.open(stage / "manifest-000.tar") as tf:
        names = set(tf.getnames())
    assert names == {"dataset/MANIFEST.json"}
    # the shipped manifest is labelled with the pushed lab
    with tarfile.open(stage / "manifest-000.tar") as tf:
        member = tf.extractfile("dataset/MANIFEST.json")
        assert member is not None
        doc = json.loads(member.read().decode("utf-8"))
    assert doc["lab"] == "collin"


# ------------------------------------------------------------------ push

def _commands(monkeypatch):
    calls: list[tuple[list[str], dict | None]] = []

    def fake_run(cmd, *, env=None):
        calls.append((cmd, env))

    monkeypatch.setattr(hf_sync, "_run", fake_run)
    return calls


def _env_of(call) -> dict:
    return call[1] or {}


def test_push_packs_then_uploads_under_the_lab_prefix_with_xet_disabled(fake_dataset, tmp_path,
                                                                        monkeypatch):
    calls = _commands(monkeypatch)
    runs = tmp_path / "runs"
    runs.mkdir()
    monkeypatch.setattr(hf_sync, "RUNS_ROOT", runs)

    stage = tmp_path / "stage"
    hf_sync.push("collin", "myname/hornlab-search-data", stage, ["text"],
                 dataset_root=fake_dataset)

    (create, up) = (calls[0][0], calls[1][0])
    assert create[:2] == ["hf", "repos"] and "--private" in create
    assert "myname/hornlab-search-data" in create
    # uploads always disable the Xet upload path in code
    assert _env_of(calls[0]).get("HF_HUB_DISABLE_XET") == "1"
    assert _env_of(calls[1]).get("HF_HUB_DISABLE_XET") == "1"
    assert up[:2] == ["hf", "upload"] and "myname/hornlab-search-data" in up
    assert "labs/collin" in up and str(stage) in up
    # push packs first, with the lab label
    assert json.loads((fake_dataset / "MANIFEST.json").read_text(encoding="utf-8"))["lab"] == "collin"


def test_push_dry_run_makes_no_network_call(fake_dataset, tmp_path, monkeypatch):
    calls = _commands(monkeypatch)
    hf_sync.push("collin", "myname/hornlab-search-data", tmp_path / "stage", ["text"],
                 dry_run=True, dataset_root=fake_dataset)
    assert calls == []


# ------------------------------------------------------------------ pull

def _fake_download(monkeypatch, lab: str, tars: dict[str, dict[str, bytes]]):
    """hf download that materialises the requested lab's tars into the --local-dir stage."""
    def fake_run(cmd, *, env=None):
        assert cmd[0] == "hf" and cmd[1] == "download"
        stage = Path(cmd[cmd.index("--local-dir") + 1])
        for tar_name, members in tars.items():
            path = stage / "labs" / lab / tar_name
            path.parent.mkdir(parents=True, exist_ok=True)
            with tarfile.open(path, "w") as tf:
                for name, payload in members.items():
                    info = tarfile.TarInfo(name)
                    info.size = len(payload)
                    tf.addfile(info, fileobj=io.BytesIO(payload))
    return fake_run


def test_pull_extracts_a_lab_into_dataset_ext(tmp_path, monkeypatch):
    row = json.dumps({"schema_version": 1, "note": "shape only - ingestion validates"})
    fake_run = _fake_download(monkeypatch, "collin", {
        "dataset-000.tar": {"dataset/shard-0000.jsonl": (row + "\n").encode("utf-8"),
                            "runs/20261031T201057Z-screen-d3158e/search.ndjson": row.encode("utf-8")},
    })
    monkeypatch.setattr(hf_sync, "_run", fake_run)

    into = tmp_path / "dataset_ext" / "collin"
    hf_sync.pull("collin", "myname/hornlab-search-data", into)

    shard = into / "dataset" / "shard-0000.jsonl"
    run = into / "runs" / "20261031T201057Z-screen-d3158e" / "search.ndjson"
    assert shard.is_file() and run.is_file()
    assert json.loads(shard.read_text(encoding="utf-8"))["schema_version"] == 1


def test_pull_refuses_anything_outside_dataset_ext(tmp_path, monkeypatch):
    calls = _commands(monkeypatch)
    with pytest.raises(SystemExit):
        hf_sync.pull("collin", "r/x", tmp_path / "somewhere_else")
    with pytest.raises(SystemExit):
        hf_sync._guard_not_dataset(hf_sync.REPO / "dataset" / "subdir")
    assert calls == []  # refused before any network call


# ------------------------------------------------------------------ legacy flows preserved

def test_legacy_upload_and_pull_all_still_target_the_repo_root(tmp_path, monkeypatch):
    calls = _commands(monkeypatch)
    hf_sync.upload(tmp_path / "stage", "r/x", public=False)
    assert calls[-1][0][:2] == ["hf", "upload"]
    assert "." in calls[-1][0]               # repo root, not labs/<name>/
    assert "labs" not in calls[-1][0]
    assert _env_of(calls[-1]).get("HF_HUB_DISABLE_XET") == "1"
    hf_sync.pull_all("r/x", tmp_path / "dest")
    assert calls[-1][0][:2] == ["hf", "download"] and "*.tar" in calls[-1][0]
    assert _env_of(calls[-1]).get("HF_HUB_DISABLE_XET") is None   # downloads keep Xet
