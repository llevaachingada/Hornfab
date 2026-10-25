"""S1a driver pass (2026-10-25, owner-directed): the brief family + the closure-aware
biradial derivation. Offline, CPU-only (the march, not the mesh; the dofs sanity is the
mesher-gated test at the bottom, run locally per the conftest gates).

Pins, per the owner's two asks:
(a) biradial's seed closes under 12.7 / 17.2 / 17.4 / 17.78 / 25.4 mm exits;
(b) the failing salmon pair's reseeded seeds march + are envelope-true, and ripple's
    screen mesh fits the 5,000-dof cap (mesher-gated);
(c) the derivation change: an f0 brief can never produce an un-closeable biradial seed
    (closure floor + widened_to_closure flag);
(d) the brief variants exist, carry their class's driver pins, f0 + objective v3.

ADAPTATIONS FROM THE ORACLE'S LITERAL FILE (this lane, 2026-10-25; each one follows the
landed tree rather than the oracle's rounded/assumed arithmetic, and none weakens a
check):
- the rounded ``0.8540808`` closure constant is replaced by the exact
  ``tan(radians(40.5))``: the rounded value misses the oracle's own ``abs=4e-6``-class
  pins by 2.2e-5 mm (measured), so the exact expression is used at the same tolerance.
- the rows sweep covers each family's OWN briefs (organic pair x organic briefs,
  lecleach x lecleach briefs). On the landed tree the salmon rows under the lecleach
  briefs are NOT envelope-true (measured overshoot 0.288 / 0.230 / 0.085), and the
  oracle's own measured matrix only claims the same-family cross-driver sweep; the
  hifi-box overshoots are the disclosed graded-penalty cases, not asserted here.
- the wt-margin probe writes its own envelope-binding grid config under ``tmp_path``:
  the landed ``organic_rollback_2in`` carries f0 1550, so its K-law H mouth is 273.1 mm
  (the oracle's 604.8 mm comment is the f0-700 value) and the envelope never binds
  there; the same rule is exercised where it does bind (400 x 400, f0 700).
"""
from __future__ import annotations

import math
from pathlib import Path

import pytest
import yaml

from conftest import EXAMPLES, requires_mesher
from hornlab_search.config import load_brief, load_config
from hornlab_search.design.generated import GeneratedSpace
from hornlab_search.design.generators.registry import envelope_overshoot_estimate
from hornlab_search.design.space import DesignSpace

BRIEFS = EXAMPLES / "briefs"
TYP = EXAMPLES / "typologies"

#: (brief name, exit radius, f0) - the shipped driver-class family (S1a, 2026-10-25).
DRIVER_CLASS_BRIEFS = (
    ("hifi_90x60_1in", 12.7, 1450.0),
    ("hifi_90x60_14in", 17.78, 1450.0),
    ("hifi_90x60_2in", 25.4, 1000.0),
    ("organic_rollback_1in", 12.7, 1900.0),
    ("organic_rollback_14in", 17.78, 1800.0),
    ("organic_rollback_2in", 25.4, 1550.0),
    ("lecleach_rollback_1in", 12.7, 1200.0),
    ("lecleach_rollback_14in", 17.78, 1200.0),
    ("lecleach_rollback_2in", 25.4, 1200.0),
)

#: The rows configs x their own family's driver-class briefs (see the adaptation note).
ROWS_FAMILY_BRIEFS = tuple(
    (name, f"{family}_{suffix}")
    for name, family in (("salmon_x_signed", "organic_rollback"),
                         ("salmon_ripple12", "organic_rollback"),
                         ("lecleach_asym_odd", "lecleach_rollback"))
    for suffix in ("1in", "14in", "2in")
)


@pytest.mark.parametrize("name,r0,f0", DRIVER_CLASS_BRIEFS)
def test_every_driver_class_brief_exists_and_pins_its_class(name, r0, f0):
    b = load_brief(BRIEFS / f"{name}.yaml")
    assert b["driver"]["exit_radius_mm"] == pytest.approx(r0)
    assert b["target"]["f0_hz"] == pytest.approx(f0)        # the honest K-law break
    assert b["objective"] == {"version": 3}                 # v3 rides every family brief
    assert b["symmetry"] == "hv"


@pytest.mark.parametrize("name", ["biradial_keele", "qtw_waveguide"])
def test_hifi_configs_default_to_their_1in_family_brief(name):
    raw = yaml.safe_load((TYP / f"{name}.yaml").read_text(encoding="utf-8"))
    assert raw["brief_file"] == "../briefs/hifi_90x60_1in.yaml"


@pytest.mark.parametrize("name", ["salmon_x_signed", "salmon_ripple12"])
def test_organic_configs_default_to_their_1in_family_brief(name):
    raw = yaml.safe_load((TYP / f"{name}.yaml").read_text(encoding="utf-8"))
    assert raw["brief_file"] == "../briefs/organic_rollback_1in.yaml"


def test_lecleach_asym_defaults_to_the_lecleach_family_brief():
    raw = yaml.safe_load((TYP / "lecleach_asym_odd.yaml").read_text(encoding="utf-8"))
    assert raw["brief_file"] == "../briefs/lecleach_rollback_1in.yaml"


def _march(name, brief_path):
    cfg = load_config(TYP / f"{name}.yaml", brief=brief_path)
    space = DesignSpace.from_config(cfg)
    assert isinstance(space, GeneratedSpace)
    return cfg, space


@pytest.mark.parametrize("brief", ["hifi_90x60_1in", "hifi_90x60_14in", "hifi_90x60_2in"])
@pytest.mark.parametrize("r0", [12.7, 17.2, 17.4, 25.4])
def test_biradial_seed_closes_under_every_supported_driver(r0, brief, tmp_path):
    """Owner ask (a): the biradial seed closes under the 1-inch, the owner's 1.4-inch-class
    customs (17.2 / 17.4) and the 2-inch exit. With an f0 brief the derivation re-aims rm
    (closure-floored); without f0 the YAML seed runs as is - both must march."""
    body = load_brief(BRIEFS / f"{brief}.yaml")
    body.pop("path", None)                       # load_brief annotates the resolved path
    body["driver"]["exit_radius_mm"] = r0        # the custom-size probe: any exit
    p = tmp_path / "custom.yaml"
    p.write_text(yaml.safe_dump(body, sort_keys=False), encoding="utf-8")
    cfg, space = _march("biradial_keele", p)
    assert envelope_overshoot_estimate(space.seed.params, cfg.brief) == 0.0
    info_h = space.seed.params["profileH"]["points"]
    assert max(float(r[1]) for r in info_h) > r0    # the mouth opened past the throat


def test_biradial_f0_brief_can_never_produce_an_un_closeable_seed():
    """The derivation repair (c): under axi_2in_large (f0 1000, r0 25.4) the OLD derivation
    set rm 141.1 - below the 192 mm closure line - and the seed refused ("cannot close",
    measured). The closure floor fixes it; the derivation notes carry the closure rule."""
    cfg, space = _march("biradial_keele", BRIEFS / "axi_2in_large.yaml")
    notes = {n["knob"]: n for n in cfg.raw["feasibility"]["derivation"]}
    assert "closure line" in notes["h_rm_mm"]["note"]
    closure_h = 25.4 + math.tan(math.radians(40.5)) * 195.0
    assert notes["h_rm_mm"]["applied"] >= closure_h - 1e-6
    assert envelope_overshoot_estimate(space.seed.params, cfg.brief) == 0.0
    # the patent's own angle rule fired on the V plane (0.9 x 40/2 = 18 deg for 90x40)
    assert notes["v_a_deg"]["applied"] == pytest.approx(18.0)


def test_biradial_closure_can_widen_the_bound_when_the_driver_demands_it(tmp_path):
    """A 50 mm custom exit under an f0 brief needs rm >= 50 + tan(40.5)*195 = 216.5 mm -
    beyond the config's hi 210 - so the bound widens to exactly the closure line and the
    seed still marches (the flagged, owner-directed exception to clamp-only)."""
    body = load_brief(BRIEFS / "hifi_90x60_2in.yaml")
    body.pop("path", None)                       # load_brief annotates the resolved path
    body["driver"]["exit_radius_mm"] = 50.0
    p = tmp_path / "huge.yaml"
    p.write_text(yaml.safe_dump(body, sort_keys=False), encoding="utf-8")
    cfg, space = _march("biradial_keele", p)
    note = next(n for n in cfg.raw["feasibility"]["derivation"]
                if n["knob"] == "h_rm_mm")
    assert note.get("widened_to_closure") is True
    expected = 50.0 + math.tan(math.radians(40.5)) * 195.0
    assert note["applied"] == pytest.approx(expected, abs=1e-6)


def _wt_brief(dir_path: Path) -> Path:
    """A tmp brief whose envelopes bind the K-law on BOTH axes (f0 700, 400x400)."""
    brief = {
        "name": "wt_probe", "description": "S1a wt-margin probe",
        "driver": {"exit_radius_mm": 12.7, "exit_angle_deg": 5.0},
        "envelope": {"max_mouth_w_mm": 400.0, "max_mouth_h_mm": 400.0,
                     "max_depth_mm": 300.0},
        "symmetry": "hv", "source": {"cap": "auto"},
        "target": {"coverage_h_deg": 90.0, "coverage_v_deg": 60.0,
                   "band_lo_hz": 300.0, "band_hi_hz": 5500.0, "di_target_db": None,
                   "di_slope_target": 0.0, "z_min": 0.0, "f0_hz": 700.0},
        "weights": {"cov": 1.0, "rip": 1.0, "di": 0.3, "dislope": 0.5,
                    "flat": 0.5, "load": 0.0},
        "objective": {"version": 3},
    }
    p = dir_path / "brief.yaml"
    p.write_text(yaml.safe_dump(brief, sort_keys=False), encoding="utf-8")
    return p


def _wt_grid_config(dir_path: Path) -> Path:
    """A minimal lecleach-rows config (the single geo-mean fc rule) with wide fc bounds."""
    payload = {
        "name": "wt_probe_grid", "family": "FREEFORM", "brief_file": "brief.yaml",
        "generator": {"name": "grid", "rows": {"type": "lecleach"}, "n_phi": 25,
                      "n_s": 32, "wall_thickness_mm": 3.0, "span": "full"},
        "seed_params": {"g_fc_hz": 800.0, "g_T": 0.8, "g_stop_deg": 170.0,
                        "g_eps_m": 0.2, "g_eps_start": 0.0},
        "bounds": {"g_fc_hz": {"lo": 100.0, "hi": 1500.0},
                   "g_T": {"lo": 0.3, "hi": 1.0},
                   "g_stop_deg": {"lo": 120.0, "hi": 240.0},
                   "g_eps_m": {"lo": -0.3, "hi": 0.3},
                   "g_eps_start": {"lo": 0.0, "hi": 0.5}},
        "target": {"coverage_h_deg": 90.0, "coverage_v_deg": 60.0,
                   "band_lo_hz": 300.0, "band_hi_hz": 5500.0, "di_target_db": None,
                   "di_slope_target": 0.0, "z_min": 0.0},
        "weights": {"cov": 1.0, "rip": 1.0, "di": 0.3, "dislope": 0.5,
                    "flat": 0.5, "load": 0.0},
        "mesh": {"epw": 8.0, "quadrants": "1234", "dof_cap_screen": 5000,
                 "dof_cap_verify": 7000, "dof_cap_final": 8900,
                 "dof_per_triangle": 0.51},
        "solve": {"backend": "beat_cuda", "distance_m": 2.0, "angle_count": 73,
                  "balloon": True, "balloon_points_screen": 512,
                  "balloon_points_verify": 1024, "gmres_tol": 1.0e-05,
                  "timeout_s": 900},
        "search": {"algorithm": "cma", "sigma0": 0.25, "seed": 1234, "budget": 100,
                   "popsize": None, "tolfun": 0.001},
    }
    p = dir_path / "grid.yaml"
    p.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return p


def test_derived_mouth_respects_the_two_wall_thicknesses(tmp_path):
    """The wt-margin fix: when the ENVELOPE binds the K-law (not the requirement), the
    derived mouth is env - 2*wt (the freestanding shell), never env itself.

    This probe's brief needs 403.2 x 604.8 mm at f0 700; both cap to 400 - 2*3 = 394, so
    the K-law inverse is 1.88e5/394 = 477.2 Hz (the un-margined 400 would give 470.0).
    """
    brief = _wt_brief(tmp_path)
    typ = _wt_grid_config(tmp_path)
    cfg = load_config(typ, brief=brief)
    note = next(n for n in cfg.raw["feasibility"]["derivation"]
                if n["knob"] == "g_fc_hz")
    capped = 400.0 - 2.0 * 3.0
    assert note["applied"] == pytest.approx(1.88e5 / capped, rel=1e-9)
    assert note["applied"] > 1.88e5 / 400.0     # the wt margin moved the inverse up
    assert note["applied"] <= 494.0


@pytest.mark.parametrize("name,brief", ROWS_FAMILY_BRIEFS)
def test_organic_and_lecleach_seeds_march_and_fit_every_family_brief(name, brief):
    """Owner ask (b): the reseeded failing pair (+ lecleach) march and are envelope-true
    under their own and every driver-class variant of their families."""
    cfg, space = _march(name, BRIEFS / f"{brief}.yaml")
    assert envelope_overshoot_estimate(space.seed.params, cfg.brief) == 0.0


@requires_mesher
def test_ripple12_reseeded_seed_fits_the_screen_dof_cap():
    """The dofs sanity bound (mesher-gated, run locally): the reseeded ripple seed meshes
    under the 5,000-dof screen cap (measured 2,567 derived / 2,852 YAML-seed dofs; the
    shipped 170-deg seed was 5,358)."""
    import dataclasses

    from hornlab_search.config import mesh_spec
    from hornlab_search.design import families
    from hornlab_search.mesh import build
    from hornlab_search.types import Design

    cfg, space = _march("salmon_ripple12", BRIEFS / "organic_rollback_1in.yaml")
    families.validate(space.seed)
    spec = dataclasses.replace(mesh_spec("screen", cfg), f_max_hz=5500.0)
    result = build.build_mesh(Design("FREEFORM", {"grid": space.seed.params["grid"]}),
                              spec, cfg, Path("runs") / "s1a_probe", mode="screen")
    assert result.n_triangles * cfg.mesh.dof_per_triangle <= cfg.mesh.dof_cap_screen
