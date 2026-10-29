"""C0 (2026-10-28): extended-throat coupling plane, per design.

The mesher's OSSE/R-OSSE throat extension anchors ``r0_mm`` at the MAIN throat and tapers back to
the driven end at ``r0 - L*tan(theta)`` (half-angle from the axis). When ``L`` is searched the
coupling plane must still land on the brief's driver exit, so ``search/evaluate.py`` derives
``r0_mm = exit_r + L*tan(theta)`` and ``a0_deg = theta`` from a SHALLOW COPY of the candidate's
params, before the design hash / mesh key are computed. The candidate object is never mutated and
a zero-length extension is a no-op (byte-identical design and mesh hashes).

The real-mesh tests build a small quarter mesh on the CPU (no solver).
"""
from __future__ import annotations

import math

import pytest
import yaml

from conftest import requires_mesher
from hornlab_search.config import load_config, mesh_spec
from hornlab_search.design.space import DesignSpace
from hornlab_search.mesh.build import build_mesh, mesh_cache_key
from hornlab_search.mesh.throat_check import fits_exit, throat_shape
from hornlab_search.search.evaluate import _derive_throat_coupling
from hornlab_search.types import Design

EXIT_R_MM = 18.0
EXT_L_MM = 160.0
EXT_ANGLE_DEG = 3.0
#: The exact derived MAIN throat radius the mesher must start from.
DERIVED_R0_MM = EXIT_R_MM + EXT_L_MM * math.tan(math.radians(EXT_ANGLE_DEG))
EXIT_DIAMETER_MM = 2.0 * EXIT_R_MM

TARGET = {"coverage_h_deg": 75.0, "coverage_v_deg": 45.0, "band_lo_hz": 700.0,
          "band_hi_hz": 8000.0, "di_target_db": None, "di_slope_target": 0.0}
WEIGHTS = {"cov": 1.0, "rip": 1.0, "di": 0.3, "dislope": 0.5, "flat": 0.5, "load": 0.0}

SEED = {"r0_mm": 18.0, "a_deg": 37.5, "a0_deg": EXT_ANGLE_DEG, "L_mm": 260.0,
        "n": 4.0, "s": 0.7, "q": 0.995, "k": 1.0, "exponent": 2.0, "aspect_ratio": 1.0,
        "throat_ext_length_mm": EXT_L_MM, "throat_ext_angle_deg": EXT_ANGLE_DEG}
BOUNDS = {"r0_mm": {"lo": 18.0, "hi": 28.0}, "a_deg": {"lo": 5.0, "hi": 55.0},
          "a0_deg": {"lo": 2.0, "hi": 5.0}, "L_mm": {"lo": 140.0, "hi": 420.0},
          "n": {"lo": 2.0, "hi": 8.0}, "s": {"lo": 0.0, "hi": 1.0},
          "q": {"lo": 0.90, "hi": 1.0}, "k": {"lo": 0.3, "hi": 2.5},
          "exponent": {"lo": 1.0, "hi": 8.0}, "aspect_ratio": {"lo": 1.0, "hi": 2.0},
          "throat_ext_length_mm": {"lo": 120.0, "hi": 200.0},
          "throat_ext_angle_deg": {"lo": 2.0, "hi": 5.0}}


def _write_cfg(tmp_path, family="OSSE", aspect_ratio=1.0):
    cfg_doc = {
        "name": f"ext_{family.lower()}", "family": family,
        "seed_params": {**SEED, "aspect_ratio": aspect_ratio},
        "bounds": dict(BOUNDS),
        "target": dict(TARGET), "weights": dict(WEIGHTS),
        # CPU mesher only: the dof cap is raised so the test can resolve the 36 mm throat.
        "mesh": {"epw": 6.0, "quadrants": "1", "dof_cap_screen": 9000,
                 "dof_cap_verify": 9000, "dof_cap_final": 9000, "dof_per_triangle": 0.51},
        "solve": {"backend": "beat_cuda", "distance_m": 2.0, "angle_count": 73, "balloon": True,
                  "balloon_points_screen": 512, "balloon_points_verify": 1024,
                  "gmres_tol": 1e-5, "timeout_s": 900},
        "search": {"algorithm": "cma", "sigma0": 0.25, "seed": 1234, "budget": 200,
                   "popsize": None, "tolfun": 1e-3},
    }
    brief_doc = {"name": "ext_brief",
                 "driver": {"exit_radius_mm": EXIT_R_MM, "exit_angle_deg": EXT_ANGLE_DEG},
                 "envelope": {"max_mouth_w_mm": 700.0, "max_mouth_h_mm": 700.0,
                              "max_depth_mm": 600.0},
                 "symmetry": "hv", "target": dict(TARGET), "weights": dict(WEIGHTS)}
    cp = tmp_path / "ext.yaml"
    bp = tmp_path / "brief.yaml"
    cp.write_text(yaml.safe_dump(cfg_doc), encoding="utf-8")
    bp.write_text(yaml.safe_dump(brief_doc), encoding="utf-8")
    return load_config(cp, brief=bp)


@pytest.fixture(scope="module")
def ext_cfg(tmp_path_factory):
    return _write_cfg(tmp_path_factory.mktemp("ext_c0"))


def _seed(ext_cfg) -> Design:
    return DesignSpace.from_config(ext_cfg).seed


# ------------------------------------------------------------------ derivation (no mesher)


def test_derivation_puts_the_coupling_plane_at_the_driver_exit(ext_cfg):
    seed = _seed(ext_cfg)
    assert seed.family == "OSSE"
    assert seed.params["r0_mm"] == EXIT_R_MM        # the candidate keeps its own (main) value
    derived = _derive_throat_coupling(seed, ext_cfg)
    assert DERIVED_R0_MM == pytest.approx(26.385, abs=1e-3)
    assert derived.params["r0_mm"] == pytest.approx(DERIVED_R0_MM, rel=0, abs=1e-12)
    assert derived.params["a0_deg"] == EXT_ANGLE_DEG          # continuous wall slope
    # the driven plane sits at exit_r below the main throat by exactly L*tan(theta)
    assert derived.params["r0_mm"] - EXT_L_MM * math.tan(math.radians(EXT_ANGLE_DEG)) \
        == pytest.approx(EXIT_R_MM, abs=1e-12)


def test_derivation_does_not_mutate_the_candidate(ext_cfg):
    seed = _seed(ext_cfg)
    before = dict(seed.params)
    derived = _derive_throat_coupling(seed, ext_cfg)
    assert seed.params == before
    assert derived is not seed and derived.params is not seed.params
    assert seed.hash() != derived.hash()


def test_zero_length_extension_is_a_noop_for_design_and_mesh_hashes(ext_cfg):
    """L = 0 (or the keys absent): the derivation returns the SAME design, so the design hash,
    the mesh-spec hash and the mesh cache key are exactly the current path's."""
    seed = _seed(ext_cfg)
    mspec = mesh_spec("screen", ext_cfg)
    zero = Design(seed.family, {**seed.params, "throat_ext_length_mm": 0.0})
    out = _derive_throat_coupling(zero, ext_cfg)
    assert out is zero
    assert out.hash() == zero.hash()
    assert mspec.hash() == mesh_spec("screen", ext_cfg).hash()
    assert mesh_cache_key(out, mspec, ext_cfg) == mesh_cache_key(zero, mspec, ext_cfg)
    absent = Design(seed.family, {k: v for k, v in seed.params.items()
                                  if not k.startswith("throat_ext_")})
    before = absent.hash()
    assert _derive_throat_coupling(absent, ext_cfg) is absent
    assert absent.hash() == before


@requires_mesher
def test_coupling_plane_mesh_is_round_at_the_driver_exit(ext_cfg, tmp_path):
    """A real quarter mesh: throat_check's tag-2 plane widens to the 36 mm exit, round."""
    seed = _seed(ext_cfg)
    derived = _derive_throat_coupling(seed, ext_cfg)
    mesh = build_mesh(derived, mesh_spec("screen", ext_cfg), ext_cfg, tmp_path / "mesh",
                      mode="screen")
    shape = throat_shape(mesh.path)
    assert shape["width_mm"] == pytest.approx(EXIT_DIAMETER_MM, abs=0.5)
    assert shape["height_mm"] == pytest.approx(EXIT_DIAMETER_MM, abs=0.5)
    assert abs(shape["roundness"] - 1.0) <= 0.03
    assert fits_exit(shape, EXIT_DIAMETER_MM) == (True, "round, matches the exit")
    # the main throat itself is the derived r0, so the wall really is the extension taper
    assert derived.params["r0_mm"] > EXIT_R_MM


# Non-round coupling (aspect_ratio != 1) is deliberately NOT tested here: the installed mesher
# pin b922e80 (v0.2.4) scales the whole meridian, so the driven plane stretches; upstream de72b68
# ("Keep the throat circular under a non-circular cross-section") fixes it. D searches lock
# aspect_ratio = 1, so the round-plane assertion above is the binding test. Revisit before
# allowing a non-round coupling plane; tracked in docs/ISSUES.md.
