"""Offline tests for tools/analysis/offline_scores.py (R0).

Synthetic dataset shards only: no mesh, no BEM, no GPU, no DatasetStore. The tests pin the R0
pilot's hard guarantees:

* zero backend calls (the guard is installed and never fires);
* no writable Store recovery (DatasetStore.__init__ is patched to raise, the pilot still runs);
* source files unchanged (hash before/after);
* original replay parity, weight/tolerance/target variant identities;
* honest ``insufficient_evidence`` when no ATH-compatible rows exist (no substitution);
* bounded preservation inventory + a temp-root restore/rescore;
* the legacy surrogate source-level capability matrix (objective.scalar v1, no impedance).
"""
from __future__ import annotations

import dataclasses
import importlib.util
import json
import math
import sys

import numpy as np
import pytest

from conftest import REPO, make_fake_response
from hornlab_search.dataset.store import DatasetStore
from hornlab_search.metrics.compute import compute_metrics
from hornlab_search.objective.scalar_v4 import V4Params, objective_v4
from hornlab_search.targets.spec import Target

_TOOL = REPO / "tools" / "analysis" / "offline_scores.py"
BRIEF = (REPO / "examples" / "briefs" / "campaign_2026-10-26_v4"
         / "native_ath_core_2in_v4.yaml")


def _load_tool(name: str, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


off = _load_tool("offline_scores_tool", _TOOL)


def _ath_target() -> Target:
    return Target.from_dict({
        "coverage_h_deg": 50.0, "coverage_v_deg": 50.0,
        "band_lo_hz": 300.0, "band_hi_hz": 8000.0,
        "di_target_db": None, "di_slope_target": 0.0, "z_min": 0.0,
        "f0_hz": 1280.0,
        "freq_weights": {"band_hz": [[2500.0, 5500.0, 2.0]]},
    })


ATH_WEIGHTS = {"cov": 1.0, "rip": 1.0, "di": 0.3, "dislope": 0.5, "flat": 0.5,
               "load": 0.0, "distd": 0.5, "diag": 0.5}
ATH_BLOCK = {
    "version": 4,
    "tolerances": {"cov": 2.0, "rip": 1.0, "di": 0.4, "dislope": 9.0, "flat": 1.5,
                   "load": 0.3, "distd": 2.0, "diag": 2.0},
    "cov_narrow_ratio": 2.0,
    "cov_below_f0": "mask",
    "diag_reference": "round",
}


def _row(name: str, target: Target, *, weights=None, block=None) -> tuple[dict, dict, float]:
    resp = make_fake_response()
    w = weights or ATH_WEIGHTS
    b = block or ATH_BLOCK
    m = compute_metrics(resp, target)
    j, terms = objective_v4(m, resp, True, target, w, V4Params.from_block(b))
    arrays = {
        "freqs_hz": np.asarray(resp.freqs_hz),
        "h_angles_deg": np.asarray(resp.h_angles_deg),
        "v_angles_deg": np.asarray(resp.v_angles_deg),
        "spl_h_db": np.asarray(resp.spl_h_db),
        "spl_v_db": np.asarray(resp.spl_v_db),
        "balloon_dirs": np.asarray(resp.balloon_dirs),
        "spl_balloon_db": np.asarray(resp.spl_balloon_db),
        "z_throat": np.asarray(resp.z_throat),
        "bw_h_deg": np.asarray(m.bw_h_deg),
        "bw_v_deg": np.asarray(m.bw_v_deg),
        "di_db": np.asarray(m.di_db),
        "ripple_h_db": np.asarray(m.ripple_h_db),
        "ripple_v_db": np.asarray(m.ripple_v_db),
        "on_axis_db": np.asarray(m.on_axis_db),
    }
    meta = {
        "ok": True,
        "design_hash": name,
        "mesh_hash": "m-" + name,
        "solve_hash": "s-" + name,
        "family": "OSSE",
        "params": {"L_mm": 260.0, "a_deg": 24.2},
        "mesh": {"n_triangles": 5000, "n_dof": 2598},
        "solve": {"backend": "fake", "n_dof": 2598, "freqs_hz": list(resp.freqs_hz),
                  "observation": {"distance_m": 2.0}},
        "excitation": {"kind": "uniform_normal_velocity"},
        "lib_shas": {"hornlab_mesher": "m" * 40},
        "metrics_scalars": dict(m.scalars),
        "objective": j,
        "terms": terms,
        "objective_version": 4,
        "target": dataclasses.asdict(target),
    }
    return meta, arrays, float(j)


def _write_dataset(root, rows) -> None:
    root.mkdir(parents=True, exist_ok=True)
    shard = root / "shard-0000"
    shard.mkdir(parents=True, exist_ok=True)
    lines = []
    for i, (meta, arrays, _j) in enumerate(rows):
        lines.append(json.dumps(meta))
        np.savez(shard / f"rec-{i:04d}.npz", **arrays)
    (root / "shard-0000.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _empty_roots(tmp_path):
    return {
        "dataset_cpu": tmp_path / "dataset_cpu",
        "cache_solve": tmp_path / "cache" / "solve",
        "cache_cpu_solve": tmp_path / "cache_cpu" / "solve",
        "runs": tmp_path / "runs",
    }


# ------------------------------------------------------------------ end-to-end pilot

def test_pilot_runs_zero_backend_calls_and_leaves_sources_unchanged(tmp_path, monkeypatch):
    ds = tmp_path / "dataset"
    _write_dataset(ds, [_row("ath-1", _ath_target()), _row("ath-2", _ath_target())])
    out = tmp_path / "out"
    roots = _empty_roots(tmp_path)
    before = {p.relative_to(ds): off._sha256_file(p) for p in ds.rglob("*") if p.is_file()}

    # Prove the pilot never constructs a writable DatasetStore (which could repair/truncate).
    def _no_store(*_a, **_k):
        raise AssertionError("offline_scores must not construct DatasetStore")

    monkeypatch.setattr(DatasetStore, "__init__", _no_store)

    rc = off.main([
        "--dataset", str(ds), "--brief", str(BRIEF), "--out", str(out),
        "--limit", "10",
        "--dataset-cpu", str(roots["dataset_cpu"]),
        "--cache-solve", str(roots["cache_solve"]),
        "--cache-cpu-solve", str(roots["cache_cpu_solve"]),
        "--runs", str(roots["runs"]),
    ])
    assert rc == 0
    payload = json.loads((out / "offline_scores.json").read_text(encoding="utf-8"))
    assert payload["status"] == "ok"
    c = payload["counts"]
    assert c["rows_seen"] == 2 and c["ath_full"] == 2 and c["ath_full_ok_with_npz"] == 2
    assert c["scored"] == 2 and c["exact_complete"] == 2
    assert payload["parity"]["n_compared"] == 2
    assert payload["parity"]["max_abs_delta"] <= 1e-6
    assert payload["backend_guard"]["calls"] == 0
    assert payload["source_guard"]["unchanged"] is True
    # weight/tolerance variants: same physical+metric identity, new score identity
    for name in ("weight", "tolerance"):
        v = payload["variants"][name]
        assert v["n"] == 2
        assert v["physical_same"] == 2
        assert v["metric_changed"] == 0
        assert v["score_changed"] == 2
    # target change regenerates metrics (new metric id), same physical id
    t = payload["variants"]["target"]
    assert t["n"] == 2 and t["physical_same"] == 2 and t["metric_changed"] == 2
    assert t["score_changed"] == 2
    # identities are present and deterministic
    ids = payload["identities"]
    assert ids["n_unique_physical"] == 2
    assert ids["n_unique_metric"] == 2
    assert all(len(r["physical_id"]) == 64 for r in ids["sample"])
    # preservation + surrogate audit present
    assert payload["preservation"]["dataset"]["n_files"] >= 3
    assert payload["preservation"]["traces"]["exists"] is False
    assert payload["surrogate_audit"]["objective_versions_supported"] == [1]
    assert payload["surrogate_audit"]["predicted_impedance"] is False
    # nothing was written next to the dataset
    after = {p.relative_to(ds): off._sha256_file(p) for p in ds.rglob("*") if p.is_file()}
    assert after == before
    assert sorted(p.name for p in ds.iterdir()) == ["shard-0000", "shard-0000.jsonl"]


def test_pilot_is_deterministic(tmp_path):
    ds = tmp_path / "dataset"
    _write_dataset(ds, [_row("ath-1", _ath_target())])
    roots = _empty_roots(tmp_path)
    common = [
        "--dataset", str(ds), "--brief", str(BRIEF), "--limit", "5",
        "--dataset-cpu", str(roots["dataset_cpu"]),
        "--cache-solve", str(roots["cache_solve"]),
        "--cache-cpu-solve", str(roots["cache_cpu_solve"]),
        "--runs", str(roots["runs"]),
    ]
    out1, out2 = tmp_path / "o1", tmp_path / "o2"
    assert off.main(common + ["--out", str(out1)]) == 0
    assert off.main(common + ["--out", str(out2)]) == 0
    a = json.loads((out1 / "offline_scores.json").read_text(encoding="utf-8"))
    b = json.loads((out2 / "offline_scores.json").read_text(encoding="utf-8"))
    assert a["counts"] == b["counts"]
    assert a["parity"] == b["parity"]
    assert a["identities"] == b["identities"]
    assert a["backend_guard"]["calls"] == b["backend_guard"]["calls"] == 0


def test_no_ath_rows_is_insufficient_evidence_not_a_substitute(tmp_path):
    other = Target.from_dict({
        "coverage_h_deg": 90.0, "coverage_v_deg": 60.0,
        "band_lo_hz": 500.0, "band_hi_hz": 10000.0,
        "di_target_db": None, "di_slope_target": 0.0, "z_min": 0.0,
    })
    ds = tmp_path / "dataset"
    _write_dataset(ds, [_row("other-1", other)])
    out = tmp_path / "out"
    roots = _empty_roots(tmp_path)
    rc = off.main([
        "--dataset", str(ds), "--brief", str(BRIEF), "--out", str(out),
        "--dataset-cpu", str(roots["dataset_cpu"]),
        "--cache-solve", str(roots["cache_solve"]),
        "--cache-cpu-solve", str(roots["cache_cpu_solve"]),
        "--runs", str(roots["runs"]),
    ])
    assert rc == 0
    payload = json.loads((out / "offline_scores.json").read_text(encoding="utf-8"))
    assert payload["status"] == "insufficient_evidence"
    assert payload["counts"]["rows_seen"] == 1
    assert payload["counts"]["ath_core"] == 0
    assert payload["counts"]["ath_full"] == 0
    assert payload["counts"]["scored"] == 0


# ------------------------------------------------------------------ guard behaviour

def test_backend_guard_raises_and_counts():
    with off.BackendGuard() as guard:
        import hornlab_search.solve.base as base
        with pytest.raises(RuntimeError, match="forbidden backend"):
            base.get_backend("beat_cuda")
    assert guard.calls == 1
    assert guard.names == ["backend.get_backend"]


# ------------------------------------------------------------------ preservation + restore

def test_preservation_inventory_and_temp_root_restore_rescore(tmp_path):
    ds = tmp_path / "dataset"
    rows = [_row("ath-1", _ath_target()), _row("ath-2", _ath_target())]
    _write_dataset(ds, rows)
    inv = off.preservation_inventory({"dataset": ds}, max_files=32)
    assert inv["dataset"]["n_files"] == 3          # jsonl + 2 npz
    assert len(inv["dataset"]["checksums"]) == 3
    assert inv["traces"]["exists"] is False

    restored = tmp_path / "restored"
    copied = off.copy_dataset_sample(ds, restored, max_rows=2)
    assert copied["rows"] == 2 and copied["npz_copied"] == [0, 1]

    # temp-root rescore matches the original row's identities and J
    brief = off.replay.load_brief_context(BRIEF)
    original = list(off.iter_dataset_rows(ds, with_arrays=True))
    copied_rows = list(off.iter_dataset_rows(restored, with_arrays=True))
    assert len(copied_rows) == 2
    for (s0, r0, m0, a0), (s1, r1, m1, a1) in zip(original, copied_rows):
        res0 = off.replay.replay_record(m0, a0, brief=brief)
        res1 = off.replay.replay_record(m1, a1, brief=brief)
        assert res0.status == res1.status == off.replay.STATUS_EXACT_COMPLETE
        assert res0.j == pytest.approx(res1.j, abs=1e-12)
        assert (res0.physical_id, res0.metric_id, res0.score_id) == \
               (res1.physical_id, res1.metric_id, res1.score_id)


# ------------------------------------------------------------------ surrogate audit

def test_legacy_surrogate_audit_has_exact_capability_matrix():
    audit = off.legacy_surrogate_audit(REPO)
    assert audit["audit_only"] is True
    assert audit["preserved_legacy_semantics"] is True
    assert audit["objective_versions_supported"] == [1]
    assert audit["predicted_impedance"] is False
    assert audit["predicted_balloon"] is False
    files = {(e["file"], e["line"]): e for e in audit["evidence"]}
    predict_refs = [e for e in audit["evidence"] if e["file"].endswith("surrogate/predict.py")]
    train_refs = [e for e in audit["evidence"] if e["file"].endswith("surrogate/train.py")]
    assert predict_refs and train_refs
    assert any("from ..objective.scalar import" in e["code"] for e in predict_refs)
    assert any(e["code"].strip() == "z_throat_real=None)" for e in predict_refs)
    assert any("from ..objective.scalar import" in e["code"] for e in train_refs)
    assert any("gate_report" in e["code"] for e in audit["evidence"])
    assert any("config_mismatch" in e["code"] for e in audit["evidence"])
    assert audit["refusal_gap"]


# ------------------------------------------------------------------ ATH compatibility helper

def test_ath_compatibility_core_vs_full():
    core = ATH_BLOCK  # unused; helper only looks at target
    t = dataclasses.asdict(_ath_target())
    assert off.ath_compatibility(t) == {"core": True, "full": True}
    t2 = dict(t, coverage_h_deg=90.0)
    assert off.ath_compatibility(t2) == {"core": False, "full": False}
    t3 = dict(t)
    t3.pop("freq_weights")
    # core still matches; full requires the brief's presence weighting to be declared
    assert off.ath_compatibility(t3)["core"] is True
