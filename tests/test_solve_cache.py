"""solve/cache.py: keys, hit/miss rules, bit-identical round trip. Offline."""
from __future__ import annotations

import dataclasses
import os
import subprocess
import sys

import numpy as np
import pytest

from conftest import make_fake_response
from hornlab_search.config import solve_spec
from hornlab_search.solve import cache
from hornlab_search.types import Response


def _full_response() -> Response:
    r = make_fake_response()
    nf, na = r.spl_h_db.shape
    rng = np.random.default_rng(7)
    r.p_h = (rng.normal(size=(nf, na)) + 1j * rng.normal(size=(nf, na))).astype(np.complex128)
    r.p_v = (rng.normal(size=(nf, na)) + 1j * rng.normal(size=(nf, na))).astype(np.complex128)
    r.p_balloon = (rng.normal(size=r.spl_balloon_db.shape) + 1j * rng.normal(size=r.spl_balloon_db.shape))
    r.spl_h_db[0, 0] = np.nextafter(r.spl_h_db[0, 0], 1e9)            # a non-round float
    r.meta = {"balloon_grid": [16, 32], "gmres_tol_applied": None, "t": {"assembly_s": 0.5},
              "note": "ok", "flag": True}
    return r


def _assert_same(a: Response, b: Response):
    for f in dataclasses.fields(Response):
        x, y = getattr(a, f.name), getattr(b, f.name)
        if isinstance(x, np.ndarray):
            assert isinstance(y, np.ndarray), f.name
            assert x.dtype == y.dtype and x.shape == y.shape, f.name
            assert x.tobytes() == y.tobytes(), f.name                  # bit-identical
        else:
            assert x == y, f.name
            assert (x is None) == (y is None), f.name


# 4
def test_cache_key_is_stable_across_processes(cfg):
    spec = solve_spec("screen", cfg)
    here = cache.key("d" * 12, "m" * 12, spec.hash())
    code = ("from hornlab_search.config import load_config, solve_spec\n"
            "from hornlab_search.solve import cache\n"
            "from pathlib import Path\n"
            f"cfg = load_config(Path(r'{(__import__('conftest').EXAMPLES / 'osse_baseline.yaml')}'))\n"
            "print(cache.key('d'*12, 'm'*12, solve_spec('screen', cfg).hash()))\n")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True,
                         timeout=120).stdout.strip()
    assert out == here
    assert here.count("-") == 2 and len(here) == 12 * 3 + 2


# 5
def test_ok_true_is_a_hit_and_ok_false_is_a_miss(tmp_path):
    r = _full_response()
    cache.store("good", tmp_path, r, {"ok": True, "seconds": 1.0})
    got = cache.lookup("good", tmp_path)
    assert got is not None
    cache.store("bad", tmp_path, r, {"ok": False, "error": "solver died"})
    assert cache.lookup("bad", tmp_path) is None
    assert cache.lookup_status("bad", tmp_path)["error"] == "solver died"
    cache.store("failrow", tmp_path, None, {"ok": False, "error": "no response"})
    assert cache.lookup("failrow", tmp_path) is None
    assert cache.lookup("never-stored", tmp_path) is None


def test_ok_true_without_a_response_is_refused(tmp_path):
    with pytest.raises(ValueError):
        cache.store("k", tmp_path, None, {"ok": True})


def test_corrupt_or_half_written_entry_is_a_miss_not_a_crash(tmp_path):
    r = _full_response()
    cache.store("k", tmp_path, r, {"ok": True})
    (tmp_path / "k" / cache.RESPONSE_FILE).write_bytes(b"not an npz")
    assert cache.lookup("k", tmp_path) is None
    (tmp_path / "k" / cache.STATUS_FILE).write_text("{ not json")
    assert cache.lookup("k", tmp_path) is None


def test_rewriting_an_entry_as_failed_invalidates_the_old_hit(tmp_path):
    r = _full_response()
    cache.store("k", tmp_path, r, {"ok": True})
    cache.store("k", tmp_path, None, {"ok": False, "error": "later failure"})
    assert cache.lookup("k", tmp_path) is None


# 6
def test_changing_one_frequency_by_0p01_hz_changes_the_hash_and_misses(tmp_path, cfg):
    spec = solve_spec("screen", cfg)
    freqs = list(spec.freqs_hz)
    freqs[3] = freqs[3] + 0.01
    spec2 = dataclasses.replace(spec, freqs_hz=tuple(freqs))
    assert spec.hash() != spec2.hash()
    k1, k2 = cache.key("d", "m", spec.hash()), cache.key("d", "m", spec2.hash())
    cache.store(k1, tmp_path, _full_response(), {"ok": True})
    assert cache.lookup(k1, tmp_path) is not None
    assert cache.lookup(k2, tmp_path) is None


# 7
@pytest.mark.parametrize("change", ["distance", "angle_count"])
def test_changing_distance_or_angle_count_misses(tmp_path, cfg, change):
    spec = solve_spec("screen", cfg)
    obs = spec.observation
    obs2 = (dataclasses.replace(obs, distance_m=obs.distance_m + 0.5) if change == "distance"
            else dataclasses.replace(obs, angle_count=obs.angle_count + 2))
    spec2 = dataclasses.replace(spec, observation=obs2)
    assert spec.hash() != spec2.hash()
    cache.store(cache.key("d", "m", spec.hash()), tmp_path, _full_response(), {"ok": True})
    assert cache.lookup(cache.key("d", "m", spec2.hash()), tmp_path) is None


# 8
def test_store_then_lookup_round_trips_every_array_bit_identically(tmp_path):
    r = _full_response()
    cache.store("rt", tmp_path, r, {"ok": True})
    got = cache.lookup("rt", tmp_path)
    _assert_same(r, got)
    assert got.p_h.dtype == np.complex128 and got.z_throat.dtype == np.complex128


def test_none_fields_round_trip_as_none(tmp_path):
    r = make_fake_response()
    r.balloon_dirs = r.spl_balloon_db = r.z_throat = None
    r.n_dof = None
    cache.store("n", tmp_path, r, {"ok": True})
    got = cache.lookup("n", tmp_path)
    _assert_same(r, got)
    assert got.balloon_dirs is None and got.z_throat is None and got.p_h is None and got.n_dof is None


def test_npz_keys_are_exactly_the_response_field_names(tmp_path):
    r = _full_response()
    cache.save_response(tmp_path / "x.npz", r)
    with np.load(tmp_path / "x.npz", allow_pickle=False) as z:
        names = {f.name for f in dataclasses.fields(Response)}
        assert set(z.files) == names                      # every field present for a full response
    r2 = make_fake_response()
    cache.save_response(tmp_path / "y.npz", r2)
    with np.load(tmp_path / "y.npz", allow_pickle=False) as z:
        assert set(z.files) <= names and "p_h" not in z.files


def test_copy_entry_hardlinks_response_but_copies_status(tmp_path):
    cache.store("k", tmp_path / "c", _full_response(), {"ok": True, "seconds": 1.0})
    dst = cache.copy_entry("k", tmp_path / "c", tmp_path / "run" / "designs" / "h")
    cache_resp = tmp_path / "c" / "k" / cache.RESPONSE_FILE
    cache_status = tmp_path / "c" / "k" / cache.STATUS_FILE
    assert os.path.samefile(dst / cache.RESPONSE_FILE, cache_resp)
    assert os.stat(dst / cache.RESPONSE_FILE).st_nlink >= 2
    assert not os.path.samefile(dst / cache.STATUS_FILE, cache_status)
    for name in (cache.RESPONSE_FILE, cache.STATUS_FILE):
        assert (dst / name).exists() and not (dst / name).is_symlink()
        assert (dst / name).read_bytes() == (tmp_path / "c" / "k" / name).read_bytes()


def test_save_response_over_a_hardlinked_design_never_touches_the_cache(tmp_path):
    cache.store("k", tmp_path / "c", _full_response(), {"ok": True})
    dst = cache.copy_entry("k", tmp_path / "c", tmp_path / "run" / "designs" / "h")
    cache_npz = tmp_path / "c" / "k" / cache.RESPONSE_FILE
    before = cache_npz.read_bytes()
    other = make_fake_response()
    other.spl_h_db = other.spl_h_db + 12.0
    cache.save_response(dst / cache.RESPONSE_FILE, other)
    assert cache_npz.read_bytes() == before
    assert (dst / cache.RESPONSE_FILE).read_bytes() != before
    assert not os.path.samefile(dst / cache.RESPONSE_FILE, cache_npz)
