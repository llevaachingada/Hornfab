"""Focused offline tests for the S2 read-only cache producer audit.

All cache trees are synthetic ``tmp_path`` fixtures. Nothing here touches a real cache,
solver, mesher, dataset or network, and no assertion accepts a cache mutation.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
TOOL = REPO / "tools" / "analysis" / "cache_producer_audit.py"


def _load_tool():
    spec = importlib.util.spec_from_file_location("cache_producer_audit", TOOL)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


module = _load_tool()


def _key(design: str, mesh: str = "b" * 12, solve: str = "c" * 12) -> str:
    return f"{design}-{mesh}-{solve}"


def _make_entry(root: Path, key: str, *, status=None, meta=None, npz=True,
                trace=False, response_present=True) -> Path:
    d = root / key
    d.mkdir(parents=True, exist_ok=True)
    if status is not None:
        (d / "status.json").write_text(json.dumps(status), encoding="utf-8")
    if npz and response_present:
        arrays = {"meta": np.array(json.dumps(meta or {}, sort_keys=True)),
                  "backend": np.array("beat_cuda")}
        if trace:
            arrays["p_h"] = np.zeros((1, 2))
        with open(d / "response.npz", "wb") as fh:
            np.savez(fh, **arrays)
    return d


@pytest.fixture()
def cache_tree(tmp_path):
    root = tmp_path / "cache" / "solve"
    _make_entry(root, _key("a" * 12),
                status={"ok": True, "objective": 1.0, "mode": "screen"},
                meta={"quadrants": 2, "symmetry_plane": "x"})
    _make_entry(root, _key("d" * 12),
                status={"ok": True, "objective": 2.0, "lib_shas": {"mesher": "deadbeef"}},
                meta={"quadrants": 2})
    _make_entry(root, _key("e" * 12),
                status={"ok": False, "error": "solve failed"},
                meta={"quadrants": 2})
    _make_entry(root, _key("f" * 12), status=None, meta={})
    _make_entry(root, _key("0" * 12),
                status={"ok": True, "objective": 3.0},
                meta={"seam_check": {"1000": {}}, "band_edges_hz": [1000.0]}, trace=True)
    return root


def _snapshot(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): (p.stat().st_size,
                                             p.read_bytes() if p.is_file() else None)
            for p in sorted(root.rglob("*"))}


def test_key_finding_and_no_cache_writes(cache_tree):
    before = _snapshot(cache_tree)
    payload = module.build_report([cache_tree], sample_limit=10, repo_root=REPO,
                                  generated_utc="2026-01-01T00:00:00Z")
    after = _snapshot(cache_tree)
    assert before == after
    assert payload["behavior_changed"] is False
    assert payload["no_cache_writes"] is True
    kf = payload["key_finding"]
    assert kf["key_format"] == "{design_hash}-{mesh_hash}-{solve_hash}"
    assert kf["producer_pins_checked"] is False
    assert "ok:true" in kf["lookup_validity"]
    inv = payload["inventory"]["roots"][0]
    assert inv["entry_count"] == 5
    assert inv["producer_evidence_present"] == 1
    assert inv["producer_evidence_unknown"] == 4
    assert inv["markers"]["seam"] == 1
    assert inv["markers"]["band_split"] == 1
    assert inv["markers"]["trace"] == 1
    assert inv["score_only_reusable"] == 3      # ok:true plus a loadable response
    assert payload["risk_summary"]["sampled_unknown_fraction"] == 0.8


def test_unknown_producer_evidence_stays_unknown_not_a_miss(cache_tree):
    payload = module.build_report([cache_tree], sample_limit=10, repo_root=REPO,
                                  generated_utc="2026-01-01T00:00:00Z")
    rows = {r["key"]: r for r in payload["inventory"]["roots"][0]["entries"]}
    unknown = rows[_key("a" * 12)]
    known = rows[_key("d" * 12)]
    assert unknown["producer_evidence"] == "unknown"
    assert unknown["producer_fields_found"] == []
    assert known["producer_evidence"] == "present"
    assert known["producer_fields_found"] == ["lib_shas"]
    # the audit reports unknown evidence; it does not pretend the entry missed
    assert unknown["status_ok"] is True and unknown["score_only_reusable"] is True


def test_sample_cap_is_respected_and_stated(tmp_path):
    root = tmp_path / "cache" / "solve"
    for i in range(20):
        _make_entry(root, _key(f"{i:012x}"), status={"ok": True, "objective": i})
    payload = module.build_report([root], sample_limit=5, repo_root=REPO,
                                  generated_utc="2026-01-01T00:00:00Z")
    inv = payload["inventory"]["roots"][0]
    assert inv["entry_count"] == 20
    assert inv["sampled_entry_count"] == 5
    assert inv["sample_limit"] == 5
    assert payload["completeness"]["bounded_sample_cap"] == 5
    assert len(inv["entries"]) == 5
    # deterministic evenly spaced sample, not the first five names
    keys = [r["key"] for r in inv["entries"]]
    all_names = sorted(p.name for p in root.iterdir() if p.is_dir())
    assert keys != all_names[:5]


def test_output_is_deterministic_and_canonical(cache_tree):
    a = module.build_report([cache_tree], sample_limit=10, repo_root=REPO,
                            generated_utc="2026-01-01T00:00:00Z")
    b = module.build_report([cache_tree], sample_limit=10, repo_root=REPO,
                            generated_utc="2026-01-01T00:00:00Z")
    ja = json.dumps(a, sort_keys=True, allow_nan=False)
    jb = json.dumps(b, sort_keys=True, allow_nan=False)
    assert ja == jb
    assert module.to_markdown(a) == module.to_markdown(b)

    def _finite(v):
        if isinstance(v, float):
            assert np.isfinite(v)
        elif isinstance(v, dict):
            for x in v.values():
                _finite(x)
        elif isinstance(v, (list, tuple)):
            for x in v:
                _finite(x)
    _finite(a)


def test_cli_writes_only_the_two_artifacts(cache_tree, tmp_path):
    out = tmp_path / "evidence"
    before = _snapshot(cache_tree)
    rc = module.main(["--cache-root", str(cache_tree), "--out", str(out),
                      "--sample-limit", "10"])
    assert rc == 0
    assert sorted(p.name for p in out.iterdir()) == [
        "cache_producer_audit.json", "cache_producer_audit.md"]
    assert _snapshot(cache_tree) == before
    data = json.loads((out / "cache_producer_audit.json").read_text(encoding="utf-8"))
    assert data["no_cache_writes"] is True and data["behavior_changed"] is False


def test_cli_refuses_out_inside_cache_root(cache_tree, tmp_path):
    before = _snapshot(cache_tree)
    rc = module.main(["--cache-root", str(cache_tree), "--out", str(cache_tree / "reports")])
    assert rc == 2
    assert _snapshot(cache_tree) == before
    assert not (cache_tree / "reports").exists()


def test_cli_help(capsys):
    with pytest.raises(SystemExit) as exc:
        module.main(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    for flag in ("--cache-root", "--out", "--sample-limit"):
        assert flag in out


def test_caller_coverage_includes_real_call_sites(cache_tree):
    payload = module.build_report([cache_tree], sample_limit=5, repo_root=REPO,
                                  generated_utc="2026-01-01T00:00:00Z")
    callers = payload["source_caller_coverage"]["callers"]
    by_func = {}
    for c in callers:
        by_func.setdefault((c["file"], c["function"]), []).append(c)
    ev = "hornlab_search/search/evaluate.py"
    for func in ("_compute", "_compute_band_split", "_seam_check", "_compute_meh", "_persist"):
        assert (ev, func) in by_func, func
    assert all(c["line"] > 0 for c in callers)
    # the seam site does both a read and a write, and says so
    seam = by_func[(ev, "_seam_check")]
    assert {c["symbol"] for c in seam} >= {"key", "lookup", "store"}
    assert all("seam" in c["role"] for c in seam)
    mb = by_func[("hornlab_search/mesh/build.py", "build_mesh")]
    assert {c["symbol"] for c in mb} >= {"mesh_cache_key", "_copy_entry", "prebuilt_key"}
    ev_calls = by_func[(ev, "_compute")]
    assert "build_mesh" in {c["symbol"] for c in ev_calls}
    assert payload["source_caller_coverage"]["n_call_sites"] == len(callers) > 10


def test_missing_root_is_reported_not_invented(tmp_path):
    payload = module.build_report([tmp_path / "nope"], sample_limit=5, repo_root=REPO,
                                  generated_utc="2026-01-01T00:00:00Z")
    inv = payload["inventory"]["roots"][0]
    assert inv["exists"] is False and inv["entry_count"] == 0
    assert payload["risk_summary"]["sampled_unknown_fraction"] is None
