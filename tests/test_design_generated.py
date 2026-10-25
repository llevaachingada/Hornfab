"""Typology generator wiring: briefs, GeneratedSpace (knobs -> FREEFORM), provenance, loading
metrics and the failure cache (docs/TYPOLOGY_PLAN.md s3-s7). Offline; the mesher is needed only
for the OSSE meridian sampler and the FREEFORM fidelity check (``requires_mesher``)."""
import json
from pathlib import Path

import numpy as np
import pytest

from conftest import EXAMPLES, requires_mesher
from hornlab_search.config import ConfigError, load_brief, load_config
from hornlab_search.design import families
from hornlab_search.design.generated import GENERATOR_ERROR_KEY, GeneratedSpace
from hornlab_search.design.space import DesignSpace
from hornlab_search.search.evaluate import LOADING_KEYS, loading_extras
from hornlab_search.targets.spec import Target

TYP = EXAMPLES / "typologies"
BRIEFS = EXAMPLES / "briefs"
CLASSICAL = ("conical", "exponential", "hypex", "tractrix")


def _cfg(name, **kw):
    return load_config(TYP / f"{name}.yaml", **kw)


def test_briefs_load_and_validate(tmp_path):
    for p in BRIEFS.glob("*.yaml"):
        b = load_brief(p)
        assert b["symmetry"] in ("hv", "axisymmetric") and b["driver"]["exit_radius_mm"] > 0
    bad = tmp_path / "bad.yaml"
    bad.write_text((BRIEFS / "axi_90x90_1in.yaml").read_text().replace("coverage_v_deg: 90.0", "coverage_v_deg: 60.0"))
    with pytest.raises(ConfigError, match="axisymmetric"):
        load_brief(bad)


def test_brief_and_seed_override_reach_config_and_sha():
    from hornlab_search.search import rundir
    a = load_config(EXAMPLES / "rosse_baseline.yaml")
    # (WP2 2026-10-24: osse_baseline is tied to its 1.4-inch driver and refused under a 1-inch
    # brief; rosse_baseline matches the hifi brief's driver, so the pin is a no-op here.)
    b = load_config(EXAMPLES / "rosse_baseline.yaml", brief=BRIEFS / "hifi_90x60_1in.yaml", cma_seed=777)
    assert b.search.seed == 777 and b.target_raw["coverage_v_deg"] == 60.0
    assert b.brief["name"] == "hifi_90x60_1in" and b.raw["brief"]["name"] == "hifi_90x60_1in"
    assert rundir.config_sha(a.raw) != rundir.config_sha(b.raw)
    assert a.generator is None and isinstance(DesignSpace.from_config(a), DesignSpace)


def test_saved_run_config_reloads_with_its_embedded_brief(tmp_path):
    """run_dir/config.yaml (merged raw) must reload to the same target, brief and config_sha."""
    import yaml
    from hornlab_search.search import rundir
    for src, brief in ((EXAMPLES / "rosse_baseline.yaml", BRIEFS / "hifi_90x60_1in.yaml"),
                       (TYP / "conical.yaml", None)):
        cfg = load_config(src, **({} if brief is None else {"brief": brief}))
        p = tmp_path / f"{src.stem}.yaml"
        p.write_text(yaml.safe_dump(cfg.raw, sort_keys=False))
        again = load_config(p)
        assert again.target_raw == cfg.target_raw and again.weights == cfg.weights
        assert again.brief["name"] == cfg.brief["name"]
        assert rundir.config_sha(again.raw) == rundir.config_sha(cfg.raw)


def test_cli_search_applies_brief_and_seed(monkeypatch, tmp_path):
    """Regression (2026-10-22): `search --brief/--cma-seed` reached `run` but not `search`."""
    from hornlab_search import cli
    from hornlab_search.search import cma as cma_mod
    seen = {}

    def fake_search(cfg, run_dir, mode, **kw):
        seen["target"], seen["seed"] = dict(cfg.target_raw), cfg.search.seed
        raise KeyboardInterrupt

    monkeypatch.setattr(cma_mod, "search", fake_search)
    monkeypatch.setattr("hornlab_search.solve.worker.warm", lambda b: None)
    monkeypatch.setattr(cli, "_backend", lambda cfg: object())
    cli.main(["search", "--config", str(EXAMPLES / "icw_termination.yaml"), "--brief",
              str(BRIEFS / "axi_90x90_1in.yaml"), "--cma-seed", "777", "--runs-dir", str(tmp_path / "r"),
              "--dataset-dir", str(tmp_path / "ds"), "--cache-dir", str(tmp_path / "c")])
    assert seen["target"]["coverage_h_deg"] == 90.0 and seen["target"]["z_min"] == 0.7 and seen["seed"] == 777


def test_generator_config_needs_brief_and_freeform(tmp_path):
    txt = (TYP / "conical.yaml").read_text()
    p = tmp_path / "x.yaml"
    p.write_text(txt.replace("brief_file: ../briefs/axi_90x90_1in.yaml", ""))
    with pytest.raises(ConfigError, match="needs a brief"):
        load_config(p)
    p.write_text(txt.replace("family: FREEFORM", "family: OSSE").replace(
        "brief_file: ../briefs/axi_90x90_1in.yaml", f"brief_file: {BRIEFS / 'axi_90x90_1in.yaml'}"))
    with pytest.raises(ConfigError, match="FREEFORM"):
        load_config(p)


@pytest.mark.parametrize("name", CLASSICAL)
def test_classical_seed_is_a_valid_freeform_design(name):
    cfg = _cfg(name)
    space = DesignSpace.from_config(cfg)
    assert isinstance(space, GeneratedSpace) and space.family == "FREEFORM"
    families.validate(space.seed)                       # our FREEFORM schema
    pH = space.seed.params["profileH"]["points"]
    assert pH[0][0] == 0.0 and abs(pH[0][1] - 12.7) < 1e-6        # brief driver radius
    assert all(b[0] > a[0] and b[1] > a[1] for a, b in zip(pH, pH[1:]))   # z and r increasing
    assert space.seed.params["profileV"] == space.seed.params["profileH"]  # axisymmetric
    x0 = space.normalize(space.seed)
    assert x0.shape == (len(space.keys()),)


@pytest.mark.parametrize("name", CLASSICAL)
def test_denormalize_never_raises_and_corners_are_invalid_or_legal(name):
    space = DesignSpace.from_config(_cfg(name))
    k = len(space.keys())
    rng = np.random.default_rng(0)
    for x in [np.zeros(k), np.ones(k), *rng.random((10, k))]:
        d = space.denormalize(x)
        if GENERATOR_ERROR_KEY not in d.params:
            families.validate(d)
        assert np.allclose(space.normalize(d), np.clip(x, 0, 1), atol=1e-6)
        prov = space.provenance(d)
        assert prov["brief"] == "axi_90x90_1in" and set(space.keys()) <= set(prov["knobs"])


def test_envelope_violation_is_a_generator_error():
    space = DesignSpace.from_config(_cfg("conical"))
    d = space.design_from_knobs({**space.seed_knobs, "h_rm_mm": 400.0})
    assert GENERATOR_ERROR_KEY in d.params and "envelope" in d.params[GENERATOR_ERROR_KEY]


def test_normalize_refuses_foreign_designs():
    space = DesignSpace.from_config(_cfg("conical"))
    other = DesignSpace.from_config(_cfg("exponential")).seed
    with pytest.raises(ValueError, match="not produced by this space"):
        space.normalize(other)


@requires_mesher
@pytest.mark.parametrize("name", ["osse_axi", "hyb_osse_h_hypex_v", "hyb_osse_h_tractrix_v",
                                  "blend_osse_tractrix", "blend_conical_exponential",
                                  "perturbed_osse_hv", "perturbed_tractrix"])
def test_hybrid_seeds_are_valid(name):
    space = DesignSpace.from_config(_cfg(name))
    families.validate(space.seed)
    pH, pV = space.seed.params["profileH"]["points"], space.seed.params["profileV"]["points"]
    assert pH[0][0] == pV[0][0] == 0.0 and abs(pH[-1][0] - pV[-1][0]) < 1e-9   # one z span


@requires_mesher
@pytest.mark.parametrize("name", CLASSICAL + ("osse_axi",))
def test_mesher_freeform_reproduces_the_analytic_meridian(name):
    """V2: Magnus's own FREEFORM evaluator vs the generator's dense analytic meridian, <= 0.2 mm."""
    from hornlab_mesher.profile_formulas import profile_points
    from hornlab_search.design.generators import registry
    cfg = _cfg(name)
    space = DesignSpace.from_config(cfg)
    gen, brief, knobs = cfg.generator, cfg.brief, space.seed_knobs
    m = registry.build_meridian(gen["profile_h"], knobs, "h", r0=12.7, a0=brief["driver"]["exit_angle_deg"],
                                L=knobs["L_mm"], max_wall=gen["max_wall_deg"], phi=0.0)
    pts = space.seed.params["profileH"]["points"]
    m = registry._truncate(m, pts[-1][0])
    mesher_params = {"type": "FREEFORM", **space.seed.params}
    xy = np.asarray(profile_points(mesher_params, 800), dtype=float)
    err = np.max(np.abs(np.interp(xy[:, 0], m.z_mm, m.r_mm) - xy[:, 1]))
    assert err <= 0.2, f"{name}: mesher FREEFORM deviates {err:.3f} mm from the analytic meridian"


def test_envelope_violation_applies_to_any_mesh():
    from hornlab_search.search.evaluate import envelope_violation
    from hornlab_search.types import MeshResult
    brief = load_brief(BRIEFS / "hifi_90x60_1in.yaml")          # 400 x 300 x 220 mm
    ok = MeshResult(path="", n_triangles=1, n_dof=1, quadrants="1", symmetry_plane="yz+xz", res_mm={},
                    bbox_m=(0, 0, -0.006, 0.19, 0.14, 0.2), seconds=0.0)
    assert envelope_violation(ok, brief) == "" and envelope_violation(ok, None) == ""
    big = MeshResult(path="", n_triangles=1, n_dof=1, quadrants="1", symmetry_plane="yz+xz", res_mm={},
                     bbox_m=(0, 0, -0.006, 0.34, 0.20, 0.30), seconds=0.0)
    msg = envelope_violation(big, brief)
    assert "width 680" in msg and "height 400" in msg and "depth" in msg


def test_loading_extras():
    t = Target(90, 90, 700, 5500, None)
    f = np.array([500, 700, 1000, 2000, 4000, 5500.0])
    out = loading_extras(f, np.array([0.2, 0.5, 0.75, 0.9, 1.0, 1.02]), t)
    assert out["f_load_hz"] == 1000 and set(out) == set(LOADING_KEYS)
    assert out["z_ripple"] == pytest.approx(np.std([0.75, 0.9, 1.0, 1.02]))
    assert np.isnan(loading_extras(f, np.full(6, 0.3), t)["f_load_hz"])
    assert all(np.isnan(v) for v in loading_extras(f, None, t).values())


def test_failure_marker_replays_without_counting(tmp_path):
    """A deterministic failure is remembered by key in the cache dir; a fresh run replays it as
    cached, so it does not consume search budget (ISSUES 2026-10-22)."""
    from hornlab_search.search import evaluate as E
    cfg = _cfg("conical")
    space = DesignSpace.from_config(cfg)
    bad = space.design_from_knobs({**space.seed_knobs, "h_rm_mm": 400.0})   # envelope -> invalid
    ctx1 = E.make_context(cfg, None, cache_dir=tmp_path / "cache")
    ev1 = E.evaluate(bad, space, cfg, "screen", tmp_path / "run1", None, None, ctx=ctx1)
    assert ev1.error.startswith("invalid_geometry") and not ev1.cached
    markers = list((tmp_path / "cache" / "solve" / "failures").glob("*.json"))
    assert len(markers) == 1 and json.loads(markers[0].read_text())["kind"] == "invalid_geometry"
    ctx2 = E.make_context(cfg, None, cache_dir=tmp_path / "cache")
    ev2 = E.evaluate(bad, space, cfg, "screen", tmp_path / "run2", None, None, ctx=ctx2)
    assert ev2.error.startswith("invalid_geometry") and ev2.cached
    row = json.loads((tmp_path / "run2" / "search.ndjson").read_text().splitlines()[0])
    assert row["generator"]["knobs"]["h_rm_mm"] == 400.0


def test_failure_marker_is_ignored_after_a_library_change(tmp_path):
    from hornlab_search.search import evaluate as E
    cfg = _cfg("conical")
    space = DesignSpace.from_config(cfg)
    bad = space.design_from_knobs({**space.seed_knobs, "h_rm_mm": 400.0})
    ctx1 = E.make_context(cfg, None, cache_dir=tmp_path / "c", lib_shas={"hornlab_mesher": "old"})
    E.evaluate(bad, space, cfg, "screen", tmp_path / "r1", None, None, ctx=ctx1)
    ctx2 = E.make_context(cfg, None, cache_dir=tmp_path / "c", lib_shas={"hornlab_mesher": "new"})
    ev = E.evaluate(bad, space, cfg, "screen", tmp_path / "r2", None, None, ctx=ctx2)
    assert ev.error.startswith("invalid_geometry") and not ev.cached     # re-evaluated, not replayed


def test_campaign_counts_keys_from_yaml_bounds():
    from hornlab_search.search.campaign import _count_keys
    assert _count_keys({"name": "c", "config": "typologies/conical.yaml"}) == 2
    assert _count_keys({"name": "p", "config": "typologies/perturbed_osse_hv.yaml"}) == 18
    assert _count_keys({"name": "o", "config": "osse_baseline.yaml"}) == 9
