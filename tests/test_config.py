"""Checkpoint CP-1 tests (03_TASK_SCAFFOLD.md). Need only numpy, scipy, pyyaml, pytest."""
from __future__ import annotations

import ast
import dataclasses
import json
import os
import subprocess
import sys

import numpy as np
import pytest

from conftest import (
    FAKE_ANGLE_COUNT,
    FAKE_BALLOON_POINTS,
    FAKE_FREQS,
    FAKE_ON_AXIS_DB,
    REPO,
)
from hornlab_search import constants
from hornlab_search import types as types_mod
from hornlab_search.config import freq_grid, load_config
from hornlab_search.types import Design, MeshSpec, ObservationSpec, SolveSpec

EXAMPLE_NAMES = ["osse_baseline", "throat_adapter", "icw_termination", "freeform_hv", "search_smoke"]

# Config fields that the loader treats as optional (may legitimately be None).
OPTIONAL_FIELDS = {"search.popsize", "search.restarts", "search.qd", "mesh.band_split",
                   # WP14: absent = today; these only exist when a config opts in.
                   "solve.near_correction", "solve.near_correction_cutoff",
                   "solve.near_correction_order", "solve.solve_precision",
                   # WP16: J0 source-profile angle; absent = today.
                   "solve.source_profile_alpha"}


def _load_example(name):
    return load_config(REPO / "examples" / f"{name}.yaml")


# ------------------------------------------------------------------ 1

@pytest.mark.parametrize("name", EXAMPLE_NAMES)
def test_examples_load_with_no_none_in_required_fields(name):
    cfg = _load_example(name)
    for f in dataclasses.fields(cfg):
        if f.name in ("brief", "generator", "grid", "mounting", "objective_params"):  # optional by design
            continue                                  # (s3-s5; WP4 grid; WP12 mounting)
        value = getattr(cfg, f.name)
        assert value is not None, f"{name}: {f.name} is None"
        if dataclasses.is_dataclass(value):
            for sf in dataclasses.fields(value):
                key = f"{f.name}.{sf.name}"
                if key in OPTIONAL_FIELDS:
                    continue
                assert getattr(value, sf.name) is not None, f"{name}: {key} is None"
    assert cfg.name and cfg.family
    assert cfg.seed_params and cfg.bounds_raw and cfg.target_raw and cfg.weights


# ------------------------------------------------------------------ 2

def test_freq_grid_screen_shape():
    g = freq_grid(500, 10000, 12)
    assert isinstance(g, tuple)
    assert len(g) == 12
    assert all(b > a for a, b in zip(g, g[1:]))
    assert g[0] == 500.0
    assert g[-1] == 10000.0


# ------------------------------------------------------------------ 3

@pytest.mark.parametrize("name", EXAMPLE_NAMES)
def test_angle_count_odd_and_divides_180(name):
    # NOTE: the plan's literal wording "(angle_count - 1) divides 180 evenly" fails for the
    # contracted default 73 (180 / 72 = 2.5). The intent is a clean angular step, so the step
    # 180/(n-1) must be a whole number of hundredths of a degree (73 -> 2.50 deg), and the
    # grid -90..+90 must hit 0 exactly.
    n = _load_example(name).solve.angle_count
    assert n % 2 == 1, f"{name}: angle_count {n} is even"
    assert 18000 % (n - 1) == 0, f"{name}: step 180/{n - 1} deg is not a whole 0.01 deg"
    half = (n - 1) // 2
    grid = np.arange(-half, half + 1) * (18000 // (n - 1)) / 100.0
    assert grid[0] == -90.0 and grid[-1] == 90.0 and grid[half] == 0.0


# ------------------------------------------------------------------ 4

_DESIGN = {
    "family": "OSSE",
    "params": {"throat_diameter_mm": 25.4, "length_mm": 120.0, "coverage_h_deg": 90,
               "k": 1.0, "n": 4.0, "q": 0.995, "s": 0.7, "profile": "osse"},
}

_SUBPROCESS_CODE = (
    "import json, sys\n"
    "from hornlab_search.types import Design\n"
    "d = json.loads(sys.argv[1])\n"
    "print(Design(d['family'], d['params']).hash())\n"
)


def _hash_in_subprocess(seed: str) -> str:
    env = dict(os.environ)
    env["PYTHONHASHSEED"] = seed
    env["PYTHONPATH"] = str(REPO) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    out = subprocess.run(
        [sys.executable, "-c", _SUBPROCESS_CODE, json.dumps(_DESIGN)],
        capture_output=True, text=True, env=env, cwd=str(REPO), timeout=120,
    )
    assert out.returncode == 0, out.stderr
    return out.stdout.strip()


def test_design_hash_stable_across_processes():
    local = Design(_DESIGN["family"], dict(_DESIGN["params"])).hash()
    assert len(local) == 12 and all(c in "0123456789abcdef" for c in local)
    # Different salts for Python's builtin hash(): a stable hash must not care.
    assert _hash_in_subprocess("1") == local
    assert _hash_in_subprocess("4242") == local


def test_types_hash_uses_hashlib_not_builtin_hash():
    src = (REPO / "hornlab_search" / "types.py").read_text(encoding="utf-8")
    assert "hashlib" in src
    tree = ast.parse(src)
    imports_hashlib = any(
        isinstance(node, ast.Import) and any(a.name == "hashlib" for a in node.names)
        for node in ast.walk(tree)
    )
    assert imports_hashlib, "types.py does not import hashlib"
    builtin_hash_calls = [
        node.lineno for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "hash"
    ]
    assert not builtin_hash_calls, f"builtin hash() called at lines {builtin_hash_calls}"
    assert types_mod._hash({"a": 1}) == types_mod._hash({"a": 1})


# ------------------------------------------------------------------ 5

def _base_solve_spec() -> SolveSpec:
    return SolveSpec(
        mode="screen",
        freqs_hz=freq_grid(500, 10000, 12),
        backend="beat_cuda",
        observation=ObservationSpec(distance_m=2.0, angle_count=73, balloon=True, balloon_points=512),
        gmres_tol=1e-5,
        extra={},
    )


def _solve_spec_variants(base: SolveSpec) -> dict[str, SolveSpec]:
    obs = base.observation
    freqs = list(base.freqs_hz)
    shifted = list(freqs)
    shifted[5] = round(shifted[5] + 0.01, 2)
    return {
        "mode": dataclasses.replace(base, mode="verify"),
        "freqs_hz:+0.01Hz": dataclasses.replace(base, freqs_hz=tuple(shifted)),
        "freqs_hz:dropped": dataclasses.replace(base, freqs_hz=tuple(freqs[:-1])),
        "backend": dataclasses.replace(base, backend="bempp_cpu"),
        "observation.distance_m": dataclasses.replace(
            base, observation=dataclasses.replace(obs, distance_m=2.5)),
        "observation.angle_count": dataclasses.replace(
            base, observation=dataclasses.replace(obs, angle_count=37)),
        "observation.balloon": dataclasses.replace(
            base, observation=dataclasses.replace(obs, balloon=False)),
        "observation.balloon_points": dataclasses.replace(
            base, observation=dataclasses.replace(obs, balloon_points=1024)),
        "gmres_tol": dataclasses.replace(base, gmres_tol=1e-6),
        "extra": dataclasses.replace(base, extra={"note": "x"}),
    }


def test_solve_spec_hash_covers_every_field():
    base = _base_solve_spec()
    h0 = base.hash()
    assert h0 == _base_solve_spec().hash()
    variants = _solve_spec_variants(base)
    covered = {k.split(":")[0].split(".")[0] for k in variants}
    assert covered == {f.name for f in dataclasses.fields(SolveSpec)}
    assert {k.split(".")[1] for k in variants if k.startswith("observation.")} == \
        {f.name for f in dataclasses.fields(ObservationSpec)}
    for label, spec in variants.items():
        assert spec.hash() != h0, f"SolveSpec.hash() ignores {label}"


# ------------------------------------------------------------------ 6

def test_mesh_spec_hash_changes_with_quadrants():
    a = MeshSpec(epw=6.0, f_max_hz=10000.0, quadrants="1234", max_triangles=50000)
    assert a.hash() == MeshSpec(epw=6.0, f_max_hz=10000.0, quadrants="1234", max_triangles=50000).hash()
    hashes = {q: dataclasses.replace(a, quadrants=q).hash() for q in ("1234", "12", "14", "1")}
    assert len(set(hashes.values())) == 4, hashes


# ------------------------------------------------------------------ 7

def test_fake_response_properties(fake_response):
    r = fake_response
    nf, na, nb = len(FAKE_FREQS), FAKE_ANGLE_COUNT, FAKE_BALLOON_POINTS

    # shapes consistent with its own arrays
    assert r.freqs_hz.shape == (nf,)
    assert np.array_equal(r.freqs_hz, np.asarray(freq_grid(500, 10000, 12)))
    assert r.h_angles_deg.shape == (na,) and r.v_angles_deg.shape == (na,)
    assert r.spl_h_db.shape == (r.freqs_hz.size, r.h_angles_deg.size)
    assert r.spl_v_db.shape == (r.freqs_hz.size, r.v_angles_deg.size)
    assert r.balloon_dirs.shape == (nb, 3)
    assert r.spl_balloon_db.shape == (r.freqs_hz.size, r.balloon_dirs.shape[0])
    assert r.z_throat.shape == (nf,) and np.iscomplexobj(r.z_throat)
    assert r.backend == "fake" and r.n_dof is not None

    # no NaN / inf anywhere
    for name in ("freqs_hz", "h_angles_deg", "v_angles_deg", "spl_h_db", "spl_v_db",
                 "balloon_dirs", "spl_balloon_db", "z_throat"):
        arr = getattr(r, name)
        assert np.all(np.isfinite(arr)), f"{name} has NaN/inf"

    # angles: ascending, -90..+90 inclusive, exact 0, shared on-axis index
    for ang in (r.h_angles_deg, r.v_angles_deg):
        assert np.all(np.diff(ang) > 0)
        assert ang[0] == -90.0 and ang[-1] == 90.0
        assert np.any(ang == 0.0)
    i0 = r.axis_index
    assert r.h_angles_deg[i0] == 0.0 and r.v_angles_deg[i0] == 0.0
    assert i0 == (na - 1) // 2

    # balloon directions are unit vectors, cover the full sphere
    norms = np.linalg.norm(r.balloon_dirs, axis=1)
    assert np.max(np.abs(norms - 1.0)) < 1e-9
    assert r.balloon_dirs[:, 2].max() > 0.99 and r.balloon_dirs[:, 2].min() < -0.99

    # absolute dB SPL: on-axis is the level and the maximum
    for cut in (r.spl_h_db, r.spl_v_db):
        assert np.all(cut[:, i0] == FAKE_ON_AXIS_DB)
        assert np.all(np.argmax(cut, axis=1) == i0)
        assert np.all(cut.max(axis=1) == cut[:, i0])
    assert np.all(r.spl_balloon_db.max(axis=1) <= FAKE_ON_AXIS_DB + 1e-12)

    # cardioid: within +/-90 deg the cut never drops below the -6 dB point
    # (20*log10(0.5)); it reaches it only at exactly +/-90, so no -6 dB crossing
    # inside the cut and a -6 dB total included beamwidth of 180.0.
    six_db = 20.0 * np.log10(0.5)
    for cut, ang in ((r.spl_h_db, r.h_angles_deg), (r.spl_v_db, r.v_angles_deg)):
        rel = cut - cut[:, [i0]]
        assert np.all(rel >= six_db - 1e-9)
        interior = np.abs(ang) < 90.0
        assert np.all(rel[:, interior] > six_db)
        assert np.allclose(rel[:, ~interior], six_db, atol=1e-9)
        # monotone fall-off away from axis, symmetric
        assert np.all(np.diff(rel[:, i0:], axis=1) < 0)
        assert np.allclose(rel, rel[:, ::-1], atol=1e-12)
        expected = 20.0 * np.log10((1.0 + np.cos(np.radians(ang))) / 2.0)
        assert np.allclose(rel, expected, atol=1e-9)

    # balloon is the same cardioid: DI of a cardioid is 10*log10(3) = 4.77 dB
    p2 = 10.0 ** ((r.spl_balloon_db - FAKE_ON_AXIS_DB) / 10.0)
    di = 10.0 * np.log10(1.0 / p2.mean(axis=1))
    assert np.allclose(di, 10.0 * np.log10(3.0), atol=0.05)

    # deterministic
    from conftest import make_fake_response
    r2 = make_fake_response()
    assert np.array_equal(r.spl_h_db, r2.spl_h_db)
    assert np.array_equal(r.spl_balloon_db, r2.spl_balloon_db)


def test_fibonacci_512(fibonacci_512):
    d = fibonacci_512
    assert d.shape == (512, 3)
    assert np.max(np.abs(np.linalg.norm(d, axis=1) - 1.0)) < 1e-9
    assert np.allclose(d.mean(axis=0), 0.0, atol=1e-2)
    assert len(np.unique(np.round(d, 12), axis=0)) == 512


# ------------------------------------------------------------------ 8

def test_keele_constant_reproduces_worked_example():
    assert abs(constants.KEELE_K / (0.3048 * 90) - 926) < 1

# ------------------------------------------------------------------ WP5/WP7/WP8 (M3)

def _variant(tmp_path, mutate):
    """Load an example config, mutate its raw YAML, write it back and load it."""
    import yaml
    raw = yaml.safe_load((REPO / "examples" / "search_smoke.yaml").read_text(encoding="utf-8"))
    mutate(raw)
    p = tmp_path / "variant.yaml"
    p.write_text(yaml.safe_dump(raw), encoding="utf-8")
    return load_config(p)


def test_new_optional_keys_absent_keep_mesh_and_solve_specs_bit_identical():
    """Old runs must reproduce: the added settings are absent from the raw YAML, their defaults
    add nothing to MeshSpec/SolveSpec, and the hashes equal a manually built CURRENT field set."""
    from hornlab_search import types as types_mod
    from hornlab_search.config import mesh_spec, mode_freqs, solve_spec
    from hornlab_search.mesh import sizing

    for name in ("osse_baseline", "search_smoke"):
        cfg = _load_example(name)
        assert cfg.mesh.rear_res_factor == 1.0 and cfg.mesh.band_split is None
        assert cfg.solve.source_motion == "normal"
        for mode in ("screen", "verify"):
            ms = mesh_spec(mode, cfg)
            max_tri = sizing.max_triangles_for(
                cfg.mesh.dof_cap(mode), cfg.mesh.quadrants, cfg.mesh.dof_per_triangle,
                cfg.mesh.max_triangle_slack)
            manual_mesh = types_mod._hash(types_mod._canon({
                "epw": float(cfg.mesh.epw),
                "f_max_hz": float(max(mode_freqs(mode, cfg))),
                "quadrants": cfg.mesh.quadrants,
                "max_triangles": max_tri,
                "allow_large_mesh": False,
            }))
            assert ms.hash() == manual_mesh, f"{name}/{mode}: MeshSpec field drift"

            ss = solve_spec(mode, cfg)
            assert dict(ss.extra) == {}
            manual_solve = types_mod._canon({
                "mode": mode,
                "freqs_hz": [round(float(f), 4) for f in mode_freqs(mode, cfg)],
                "backend": str(cfg.solve.backend),
                "observation": {
                    "distance_m": float(cfg.solve.distance_m),
                    "angle_count": int(cfg.solve.angle_count),
                    "balloon": bool(cfg.solve.balloon),
                    "balloon_points": cfg.solve.balloon_points(mode),
                },
                "gmres_tol": float(cfg.solve.gmres_tol),
                "extra": {},
            })
            assert ss.hash() == types_mod._hash(manual_solve), f"{name}/{mode}: SolveSpec field drift"


def test_rear_res_factor_loads_and_is_validated(tmp_path):
    from hornlab_search.config import ConfigError

    cfg = _variant(tmp_path, lambda raw: raw["mesh"].update(rear_res_factor=1.5))
    assert cfg.mesh.rear_res_factor == 1.5
    for bad in (0, -1.0, float("nan"), float("inf"), True, "1.5"):
        with pytest.raises(ConfigError, match="rear_res_factor"):
            _variant(tmp_path, lambda raw, b=bad: raw["mesh"].update(rear_res_factor=b))


def test_source_motion_loads_only_when_it_differs_elsewhere(tmp_path):
    from hornlab_search.config import ConfigError, solve_spec

    cfg = _variant(tmp_path, lambda raw: raw["solve"].update(source_motion="axial"))
    assert cfg.solve.source_motion == "axial"
    assert solve_spec("screen", cfg).extra["source_motion"] == "axial"
    cfg_normal = _variant(tmp_path, lambda raw: raw["solve"].update(source_motion="normal"))
    assert solve_spec("screen", cfg_normal).extra == {}

    with pytest.raises(ConfigError, match="source_motion"):
        _variant(tmp_path, lambda raw: raw["solve"].update(source_motion="sideways"))
    with pytest.raises(ConfigError, match="source_motion"):
        _variant(tmp_path, lambda raw: raw["solve"].update(source_motion="axial", backend="bempp_cpu"))


@pytest.mark.parametrize("block", [
    {"edges_hz": []},
    {"edges_hz": [3000, 2000]},
    {"edges_hz": [3000, 3000]},
    {"edges_hz": [600]},                  # below the target band_lo (700 Hz)
    {"edges_hz": [4500]},                 # at the target band_hi, not inside
    {"edges_hz": ["x"]},
    {"edges_hz": [True]},
    {"edges_hz": [float("nan")]},
    {"edges_hz": [3000], "extra": 1},
    [],
])
def test_band_split_validation_rejects_bad_edges(tmp_path, block):
    from hornlab_search.config import ConfigError

    with pytest.raises(ConfigError, match="band_split"):
        _variant(tmp_path, lambda raw: raw["mesh"].update(band_split=block))


def test_band_split_valid_edges_normalized_and_enter_solve_extra(tmp_path):
    from hornlab_search.config import solve_spec

    cfg = _variant(tmp_path, lambda raw: raw["mesh"].update(
        band_split={"edges_hz": [2000, 3000]}))
    assert cfg.mesh.band_split == {"edges_hz": [2000.0, 3000.0]}
    extra = solve_spec("screen", cfg).extra
    assert extra["mesh_policy"] == "band_split_v1"
    assert extra["band_edges_hz"] == [2000.0, 3000.0]
