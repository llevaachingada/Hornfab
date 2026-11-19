"""Offline tests for tools/night_queue/fidelity_pairs.py (B1 two-tier fixed-design job).

No solver, mesher, GPU or dataset: ``evaluate`` and the context/warm factories are injected
fakes. The tests pin the parts that can silently waste a night or mislabel a pair: the row
selection (verify's lowest-J-per-hash rule), the requested hash order, the refusal on a missing
hash, the two tiers per design, and the resume skip.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from conftest import EXAMPLES

from hornlab_search.config import load_config, mesh_spec, solve_spec
from hornlab_search.types import MeshTooLargeError

REPO = Path(__file__).resolve().parents[1]
TOOL = REPO / "tools" / "night_queue" / "fidelity_pairs.py"
BASE = EXAMPLES / "typologies" / "meh_2026-10-30" / "meh_t2a_search.yaml"


def _real_cfg(tmp_path: Path):
    raw = yaml.safe_load(BASE.read_text(encoding="utf-8"))
    raw["brief_file"] = str((BASE.parent / raw["brief_file"]).resolve())
    p = tmp_path / "c.yaml"
    p.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return load_config(p)


def _load_tool():
    spec = importlib.util.spec_from_file_location("fidelity_pairs", TOOL)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


module = _load_tool()

ROWS = [
    {"design_hash": "h1", "objective": 4.0, "ok": True, "family": "freeform", "params": {}},
    {"design_hash": "h1", "objective": 3.5, "ok": True, "family": "freeform", "params": {}},
    {"design_hash": "h2", "objective": 3.0, "ok": True, "family": "freeform", "params": {}},
    {"design_hash": "h3", "objective": 9.0, "ok": False, "family": "freeform", "params": {}},
]


def _run_dir(tmp_path: Path, rows=None, name: str = "run") -> Path:
    d = tmp_path / name
    d.mkdir()
    (d / "search.ndjson").write_text(
        "\n".join(json.dumps(r) for r in (rows or ROWS)) + "\n", encoding="utf-8")
    return d


# ------------------------------------------------------------------ selection


def test_select_rows_lowest_j_per_hash_in_requested_order():
    got = module.select_rows(ROWS, ["h2", "h1"])
    assert [r["design_hash"] for r in got] == ["h2", "h1"]
    assert got[1]["objective"] == 3.5          # the second h1 row, not the first


def test_select_rows_ignores_failed_rows():
    with pytest.raises(module.MissingDesignError):
        module.select_rows(ROWS, ["h3"])


def test_select_rows_refuses_missing_hash():
    with pytest.raises(module.MissingDesignError) as exc:
        module.select_rows(ROWS, ["h1", "nope"])
    assert "nope" in str(exc.value)


# ------------------------------------------------------------------ input parsing


def test_parse_design_specs_repeatable_and_csv(tmp_path):
    csv_path = tmp_path / "designs.csv"
    csv_path.write_text("run,design\nruns/a,h2\nruns/b,h3\n", encoding="utf-8")
    pairs = module.parse_design_specs(["runs/a:h1"], str(csv_path))
    assert pairs == [("runs/a", "h1"), ("runs/a", "h2"), ("runs/b", "h3")]


def test_parse_design_specs_dedups_and_refuses_empty():
    assert module.parse_design_specs(["runs/a:h1", "runs/a:h1"], None) == [("runs/a", "h1")]
    with pytest.raises(module.MissingDesignError):
        module.parse_design_specs(None, None)


def test_parse_design_specs_refuses_bad_spec():
    with pytest.raises(module.MissingDesignError):
        module.parse_design_specs(["no-colon"], None)


# ------------------------------------------------------------------ the loop


def _cfg():
    return SimpleNamespace(name="c", family="freeform", raw={"name": "c", "solve": {}},
                           solve=SimpleNamespace(backend="beat_cuda"))


def test_run_pairs_evaluates_both_tiers_per_design(tmp_path, monkeypatch):
    run = _run_dir(tmp_path)
    out = tmp_path / "out"
    calls, warm = [], []

    def fake_evaluate(design, space, cfg, mode, run_dir, store, backend, *, ctx=None):
        calls.append((design.hash(), mode))
        return SimpleNamespace(error="", objective=1.0, design_hash=design.hash(), metrics=None)

    monkeypatch.setattr(module, "_write_mode_meta", lambda *a, **k: None)
    monkeypatch.setattr(module, "_backend_obj",
                        lambda cfg: SimpleNamespace(name=str(cfg.solve.backend), warm=lambda: None))
    module.run_pairs(
        [(str(run), "h1"), (str(run), "h2")], out,
        config_for_run=lambda p: _cfg(), evaluate_fn=fake_evaluate,
        make_ctx_fn=lambda cfg, store, **k: SimpleNamespace(), warm_fn=warm.append,
        space_for_cfg=lambda cfg: object(), store=None, echo=lambda *a, **k: None)

    h1, h2 = module._design_for(ROWS[0]).hash(), module._design_for(ROWS[2]).hash()
    assert calls == [(h1, "verify"), (h1, "finalist"), (h2, "verify"), (h2, "finalist")]
    assert [b.name for b in warm] == ["beat_cuda", "beat_cuda"]
    assert all(not isinstance(b, str) for b in warm)   # regression pin: warm must get the object
    assert {p.name for p in out.iterdir()} >= {"run__verify", "run__finalist", "pairs.json"}
    pairs = json.loads((out / "pairs.json").read_text(encoding="utf-8"))
    assert pairs["check"] == module.PAIR_CHECK
    assert "NOT mesh convergence" in pairs["warning"]
    assert len(pairs["designs"]) == 2
    assert pairs["designs"][0]["modes"]["finalist"]["ok"] is True


def test_run_pairs_resumes_an_already_ok_tier(tmp_path, monkeypatch):
    run = _run_dir(tmp_path)
    out = tmp_path / "out"
    calls = []

    def fake_evaluate(design, space, cfg, mode, run_dir, store, backend, *, ctx=None):
        calls.append((design.hash(), mode))
        return SimpleNamespace(error="", objective=1.0, design_hash=design.hash(), metrics=None)

    monkeypatch.setattr(module, "_write_mode_meta", lambda *a, **k: None)
    monkeypatch.setattr(module, "_backend_obj",
                        lambda cfg: SimpleNamespace(name=str(cfg.solve.backend), warm=lambda: None))
    h1 = "h1"                                  # the stored row's hash is what the resume keys on
    d = out / "run__verify"
    d.mkdir(parents=True)
    (d / "search.ndjson").write_text(
        json.dumps({"ok": True, "design_hash": h1}) + "\n", encoding="utf-8")
    module.run_pairs(
        [(str(run), "h1")], out, config_for_run=lambda p: _cfg(),
        evaluate_fn=fake_evaluate, make_ctx_fn=lambda cfg, store, **k: SimpleNamespace(),
        warm_fn=lambda b: None, space_for_cfg=lambda cfg: object(), store=None,
        echo=lambda *a, **k: None)
    assert [m for _, m in calls] == ["finalist"]     # verify was already ok -> skipped


def test_write_mode_meta_writes_a_loadable_run_dir(tmp_path, monkeypatch):
    """The real meta writer (not the stubbed one) must produce run.json + a config snapshot."""
    import hornlab_search.search.evaluate as ev
    from hornlab_search.search import rundir

    monkeypatch.setattr(ev, "collect_lib_shas", lambda: {"hornlab_mesher": "deadbeef"})
    monkeypatch.setattr(rundir, "runtime_provenance", lambda: {"python": "test"})
    monkeypatch.setattr(rundir, "toolchain_snapshot", lambda: {"present": False})
    d = tmp_path / "run__verify"
    d.mkdir()
    module._write_mode_meta(d, _cfg(), tmp_path / "run", "verify", rundir)
    meta = json.loads((d / "run.json").read_text(encoding="utf-8"))
    assert meta["mode"] == "verify"
    assert meta["fidelity_pairs_of"]["mode"] == "verify"
    assert (d / "config.yaml").is_file()


def test_missing_hash_aborts_before_any_solve(tmp_path, monkeypatch):
    run = _run_dir(tmp_path)
    calls = []

    def fake_evaluate(*a, **k):
        calls.append(a)
        raise AssertionError("evaluate must not be reached")

    monkeypatch.setattr(module, "_write_mode_meta", lambda *a, **k: None)
    with pytest.raises(module.MissingDesignError):
        module.run_pairs(
            [(str(run), "nope")], tmp_path / "out", config_for_run=lambda p: _cfg(),
            evaluate_fn=fake_evaluate, make_ctx_fn=lambda *a, **k: SimpleNamespace(),
            warm_fn=lambda b: None, space_for_cfg=lambda cfg: object(), store=None,
            echo=lambda *a, **k: None)
    assert calls == []


def test_run_pairs_keeps_one_context_per_source_run(tmp_path, monkeypatch):
    """Two source configs must never share a context: provenance/target would leak across runs."""
    run_a = _run_dir(tmp_path, name="runA")
    run_b = _run_dir(tmp_path, name="runB")
    out = tmp_path / "out"
    cfg_a = _cfg()
    cfg_a.name = "A"
    cfg_b = _cfg()
    cfg_b.name = "B"
    by_path = {str(run_a): cfg_a, str(run_b): cfg_b}
    seen = []

    def make_ctx(cfg, store, **k):
        return SimpleNamespace(config_name=cfg.name)

    def fake_evaluate(design, space, cfg, mode, run_dir, store, backend, *, ctx=None):
        assert ctx is not None
        seen.append((cfg.name, mode, ctx.config_name))
        return SimpleNamespace(error="", objective=1.0, design_hash=design.hash(), metrics=None)

    monkeypatch.setattr(module, "_write_mode_meta", lambda *a, **k: None)
    monkeypatch.setattr(module, "_backend_obj",
                        lambda cfg: SimpleNamespace(name=str(cfg.solve.backend), warm=lambda: None))
    module.run_pairs(
        [(str(run_a), "h1"), (str(run_b), "h2")], out,
        config_for_run=lambda p: by_path[str(p)], evaluate_fn=fake_evaluate,
        make_ctx_fn=make_ctx, warm_fn=lambda b: None,
        space_for_cfg=lambda cfg: object(), store=None, echo=lambda *a, **k: None)
    assert seen == [("A", "verify", "A"), ("A", "finalist", "A"),
                    ("B", "verify", "B"), ("B", "finalist", "B")]
    assert {p.name for p in out.iterdir()} >= {
        "runA__verify", "runA__finalist", "runB__verify", "runB__finalist", "pairs.json"}


# ------------------------------------------------------------------ B1 mesh refinement
# NOTE: these use a REAL Config (the example YAML) because refine_config/dataclasses.replace and
# solve_spec need real dataclasses; no mesher or solver is ever called.

METRICS = {
    "freqs_hz": [400.0, 700.0, 1000.0, 2000.0],
    "bw_h_deg": [100.0, 90.0, 80.0, 70.0],
    "bw_v_deg": [80.0, 70.0, 60.0, 50.0],
    "di_db": [5.0, 6.0, 7.0, 8.0],
    "ripple_h_db": [1.0, 1.2, 1.4, 1.6],
    "ripple_v_db": [0.8, 0.9, 1.0, 1.1],
}


class _FakeMem:
    def __init__(self, period=1.0):
        self.period = period

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def record(self):
        return {"vram_baseline_mib": 420, "peak_vram_mib": 1800,
                "host_shared_peak_mib": 3, "host_dedicated_peak_mib": 1300, "spilled": False}


def _ref_row(cfg, h="h1", J=4.0):
    return {"design_hash": h, "objective": J, "ok": True, "family": "freeform", "params": {},
            "solve_hash": solve_spec("screen", cfg).hash(), "n_triangles": 7391, "n_dof": 3837,
            "terms": {"cov": 1.0, "rip": 0.5, "di": 1.5}, "metrics": METRICS}


def test_refine_config_scales_only_epw_value(tmp_path):
    cfg = _real_cfg(tmp_path)
    ref = module.refine_config(cfg, 2.0)
    assert ref.mesh.epw == pytest.approx(cfg.mesh.epw * 2.0)
    assert ref.mesh.dof_cap("screen") == cfg.mesh.dof_cap("screen")
    assert ref.mesh.rear_res_factor == cfg.mesh.rear_res_factor
    assert ref.mesh.quadrants == cfg.mesh.quadrants
    assert solve_spec("screen", ref).hash() == solve_spec("screen", cfg).hash()
    assert mesh_spec("screen", ref).epw == pytest.approx(mesh_spec("screen", cfg).epw * 2.0)
    assert mesh_spec("screen", ref).f_max_hz == mesh_spec("screen", cfg).f_max_hz


def test_refine_config_for_snapshot_records_the_override(tmp_path):
    cfg = _real_cfg(tmp_path)
    snap = module.refine_config_for_snapshot(cfg, 3.0)
    assert snap.raw["mesh"]["epw"] == pytest.approx(cfg.mesh.epw * 3.0)
    assert snap.raw["name"] == cfg.raw["name"]


def test_reference_grid_accepts_the_stored_hash_and_refuses_a_foreign_one(tmp_path):
    cfg = _real_cfg(tmp_path)
    row = _ref_row(cfg)
    grid = module.reference_grid(cfg, row, module.refine_config(cfg, 2.0))
    assert grid["same_grid"] is True
    assert grid["n_freqs"] == len(solve_spec("screen", cfg).freqs_hz)
    row["solve_hash"] = "deadbeefdead"
    with pytest.raises(module.GridMismatchError):
        module.reference_grid(cfg, row, module.refine_config(cfg, 2.0))


def test_metric_summary_and_term_deltas():
    s = module.metric_summary(METRICS)
    assert s["present"] is True
    assert s["n_in_band"] == 4
    assert s["bw_h_deg"] == pytest.approx(85.0)
    assert s["di_db"] == pytest.approx(6.5)
    d = module.term_deltas({"cov": 1.0, "rip": 0.5}, {"cov": 1.5, "rip": 0.5})
    assert d["cov"] == pytest.approx(0.5)
    assert d["rip"] == pytest.approx(0.0)
    assert module.term_deltas({}, {})["di"] is None


def test_mesh_verdict_buckets_and_cap_bound():
    assert "fits" in module.mesh_verdict(5000)
    assert "borderline" in module.mesh_verdict(12000)
    assert "infeasible" in module.mesh_verdict(21000)
    assert "CAP-BOUND" in module.mesh_verdict(21000, cap_bound_at=24000)


def test_j_gain_threshold_ignores_duplicate_scores():
    rows = [{"objective": 3.0}, {"objective": 3.000003}, {"objective": 3.005}, {"objective": 3.10}]
    assert module.j_gain_threshold(rows) == pytest.approx(0.005, abs=1e-5)


def _run_refine(tmp_path, monkeypatch, *, evaluate_fn, factor=2.0, teardown=True, vram=True,
                rows=None, gain_threshold=None):
    cfg = _real_cfg(tmp_path)
    run = _run_dir(tmp_path, rows=rows or [_ref_row(cfg)])
    out = tmp_path / "out"
    warm, teardown_calls = [], []

    monkeypatch.setattr(module, "_write_mode_meta", lambda *a, **k: None)
    # The 2026-11-18 fix: warm_fn and evaluate_fn must receive the backend OBJECT, never the
    # cfg string (the five B1 probes crashed on 'str' has no attribute name). Inject a stand-in.
    monkeypatch.setattr(module, "_backend_obj",
                        lambda cfg: SimpleNamespace(name=str(cfg.solve.backend), warm=lambda: None))
    results = module.run_refine(
        [(str(run), "h1")], out, config_for_run=lambda p: cfg, evaluate_fn=evaluate_fn,
        make_ctx_fn=lambda cfg, store, **k: SimpleNamespace(),
        warm_fn=warm.append, space_for_cfg=lambda cfg: object(), factor=factor,
        store=None, teardown_fn=lambda **k: teardown_calls.append(k) or [],
        teardown_per_design=teardown, vram_factory=_FakeMem if vram else None,
        metrics_json_fn=lambda m: METRICS, gain_threshold=gain_threshold,
        echo=lambda *a, **k: None)
    return cfg, run, out, results, warm, teardown_calls


def test_run_refine_uses_the_stored_row_and_same_grid(tmp_path, monkeypatch):
    cfg = _real_cfg(tmp_path)
    seen = {}

    def fake_evaluate(design, space, cfg_v, mode, run_dir, store, backend, *, ctx=None):
        seen.update(epw=cfg_v.mesh.epw, mode=mode, solve_hash=solve_spec(mode, cfg_v).hash(),
                    cap=cfg_v.mesh.dof_cap("screen"))
        return SimpleNamespace(error="", objective=5.0, terms={"cov": 2.0, "rip": 0.5},
                               metrics=object(),
                               mesh=SimpleNamespace(n_triangles=28859, n_dof=14718,
                                                    quadrants="1"),
                               mesh_hash="mesh2")

    cfg, run, out, results, warm, teardown_calls = _run_refine(
        tmp_path, monkeypatch, evaluate_fn=fake_evaluate, gain_threshold=0.5)
    assert seen["epw"] == pytest.approx(cfg.mesh.epw * 2.0)
    assert seen["mode"] == "screen"
    assert seen["solve_hash"] == solve_spec("screen", cfg).hash()      # same grid identity
    assert seen["cap"] == cfg.mesh.dof_cap("screen")                   # cap untouched
    assert [b.name for b in warm] == ["beat_cuda"] and teardown_calls == [{"verify": True}]
    assert all(not isinstance(b, str) for b in warm)   # regression pin: warm must get the object
    r = results[0]
    assert r["reference"]["J"] == pytest.approx(4.0)
    assert r["delta"]["J"] == pytest.approx(1.0)
    assert r["delta"]["terms"]["cov"] == pytest.approx(1.0)
    assert r["refined"]["n_dof"] == 14718
    assert r["vram"]["host_shared_peak_mib"] == 3
    assert r["flags"]["mesh_sensitive"] is True
    rec = json.loads((out / "refine.json").read_text(encoding="utf-8"))
    assert rec["check"] == module.REFINE_CHECK
    assert rec["designs"][0]["grid"]["same_grid"] is True


def test_run_refine_merges_per_design_records(tmp_path, monkeypatch):
    cfg = _real_cfg(tmp_path)
    run_a = _run_dir(tmp_path, rows=[_ref_row(cfg, h="h1")], name="runA")
    run_b = _run_dir(tmp_path, rows=[_ref_row(cfg, h="h2")], name="runB")
    out = tmp_path / "out"
    monkeypatch.setattr(module, "_write_mode_meta", lambda *a, **k: None)
    monkeypatch.setattr(module, "_backend_obj",
                        lambda cfg: SimpleNamespace(name=str(cfg.solve.backend), warm=lambda: None))

    def fake(design, space, cfg_v, mode, run_dir, store, backend, *, ctx=None):
        return SimpleNamespace(error="", objective=5.0, terms={}, metrics=object(),
                               mesh=SimpleNamespace(n_triangles=1000, n_dof=510, quadrants="1"),
                               mesh_hash="m")

    for run, h in ((run_a, "h1"), (run_b, "h2")):
        module.run_refine(
            [(str(run), h)], out, config_for_run=lambda p: cfg, evaluate_fn=fake,
            make_ctx_fn=lambda *a, **k: SimpleNamespace(), warm_fn=lambda b: None,
            space_for_cfg=lambda c: object(), factor=2.0, store=None,
            teardown_fn=lambda **k: [], teardown_per_design=False, vram_factory=None,
            metrics_json_fn=lambda m: METRICS, echo=lambda *a, **k: None)
    rec = json.loads((out / "refine.json").read_text(encoding="utf-8"))
    assert {d["design_hash"] for d in rec["designs"]} == {"h1", "h2"}


def test_run_refine_marks_a_cap_bound_build(tmp_path, monkeypatch):
    def fake_evaluate(*a, **k):
        return SimpleNamespace(error="mesh_too_large: 30000 dofs exceeds the dof cap 24000",
                               objective=0.0, terms=None, metrics=None, mesh=None,
                               mesh_hash=None)

    _, _, _, results, _, _ = _run_refine(tmp_path, monkeypatch, evaluate_fn=fake_evaluate)
    r = results[0]
    assert r["refined"]["error_kind"] == "mesh_too_large"
    assert r["flags"]["cap_bound"] is True
    assert "CAP-BOUND" in r["flags"]["verdict"]


def test_run_refine_marks_a_spilled_measurement(tmp_path, monkeypatch):
    class Spilled(_FakeMem):
        def record(self):
            return {"vram_baseline_mib": 420, "peak_vram_mb": 8100,
                    "host_shared_peak_mib": 900, "host_dedicated_peak_mib": 7000,
                    "spilled": True}

    cfg = _real_cfg(tmp_path)
    run = _run_dir(tmp_path, rows=[_ref_row(cfg)])
    monkeypatch.setattr(module, "_write_mode_meta", lambda *a, **k: None)
    monkeypatch.setattr(module, "_backend_obj",
                        lambda cfg: SimpleNamespace(name=str(cfg.solve.backend), warm=lambda: None))
    results = module.run_refine(
        [(str(run), "h1")], tmp_path / "out", config_for_run=lambda p: cfg,
        evaluate_fn=lambda *a, **k: SimpleNamespace(
            error="", objective=5.0, terms={}, metrics=object(),
            mesh=SimpleNamespace(n_triangles=28859, n_dof=14718, quadrants="1"),
            mesh_hash="m"),
        make_ctx_fn=lambda cfg, store, **k: SimpleNamespace(), warm_fn=lambda b: None,
        space_for_cfg=lambda cfg: object(), factor=2.0, store=None,
        teardown_fn=lambda **k: [], teardown_per_design=False, vram_factory=Spilled,
        metrics_json_fn=lambda m: METRICS, echo=lambda *a, **k: None)
    assert results[0]["flags"]["spilled"] is True


# ------------------------------------------------------------------ CPU sizing dry run


class _FakeBuild:
    def __init__(self, *, refuse_refined=False, tri=1000):
        self.calls = []
        self.refuse_refined = refuse_refined
        self.tri = tri
        self.base_epw = None

    def __call__(self, design, ms, cfg, out_dir, *, mode=None):
        self.base_epw = self.base_epw or cfg.mesh.epw
        if not hasattr(self, "base_cap"):
            self.base_cap = cfg.mesh.dof_cap("screen")
        self.calls.append((cfg.mesh.epw, cfg.mesh.dof_cap("screen"), ms.max_triangles))
        if self.refuse_refined and cfg.mesh.epw != self.base_epw and \
                cfg.mesh.dof_cap("screen") == self.base_cap:
            raise MeshTooLargeError("30000 dofs exceeds the dof cap 24000")
        return SimpleNamespace(path=str(Path(out_dir) / "mesh.msh"), n_triangles=self.tri,
                               quadrants="1", res_mm={"mouth": 7.1, "throat": 3.5, "rear": 7},
                               seconds=0.1)


def test_build_meshes_builds_reference_and_both_factors(tmp_path):
    cfg = _real_cfg(tmp_path)
    run = _run_dir(tmp_path, rows=[_ref_row(cfg)])
    fb = _FakeBuild(tri=28859)
    out = tmp_path / "sizing"
    res = module.build_meshes([(str(run), "h1")], out, config_for_run=lambda p: cfg,
                              factors=[2.0, 3.0], build_fn=fb,
                              summary_fn=lambda p: {"n_nodes_used": 14718},
                              echo=lambda *a, **k: None)
    assert [c[0] for c in fb.calls] == pytest.approx(
        [cfg.mesh.epw, cfg.mesh.epw * 2, cfg.mesh.epw * 3])
    cands = res[0]["candidates"]
    assert set(cands) == {"ref", "x2", "x3"}
    assert cands["x2"]["dof"] == 14719
    assert "borderline" in cands["x2"]["verdict"]
    assert (out / "mesh_dryrun.json").is_file()


def test_build_meshes_cap_bound_uses_a_lifted_diagnostic(tmp_path):
    cfg = _real_cfg(tmp_path)
    run = _run_dir(tmp_path, rows=[_ref_row(cfg)])
    fb = _FakeBuild(refuse_refined=True)
    res = module.build_meshes([(str(run), "h1")], tmp_path / "sizing",
                              config_for_run=lambda p: cfg, factors=[3.0], build_fn=fb,
                              summary_fn=lambda p: {"n_nodes_used": 38000},
                              echo=lambda *a, **k: None)
    x3 = res[0]["candidates"]["x3"]
    assert x3["cap_bound"] is True
    assert x3["diagnostic"]["ok"] is True
    assert x3["diagnostic"]["dof"] == 38000
    assert x3["verdict"].startswith("CAP-BOUND")
    assert x3["diagnostic"]["cap_lifted"] > 24000


def test_build_meshes_records_a_geometry_refusal(tmp_path):
    cfg = _real_cfg(tmp_path)
    run = _run_dir(tmp_path, rows=[_ref_row(cfg)])
    from hornlab_search.types import GeometryInvalidError

    def fake_build(design, ms, c, out_dir, *, mode=None):
        raise GeometryInvalidError("23 non-sliver triangle(s) lie entirely in the x=0 plane")

    res = module.build_meshes([(str(run), "h1")], tmp_path / "sizing",
                              config_for_run=lambda p: cfg, factors=[2.0], build_fn=fake_build,
                              summary_fn=lambda p: {}, echo=lambda *a, **k: None)
    x2 = res[0]["candidates"]["x2"]
    assert x2["ok"] is False
    assert x2["cap_bound"] is False
    assert "invalid_geometry" in x2["error"]
