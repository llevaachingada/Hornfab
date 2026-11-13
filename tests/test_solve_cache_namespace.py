"""A1: physics-library provenance namespaces for the shared solve/mesh caches. Offline."""
from __future__ import annotations

import hashlib
from pathlib import Path

from conftest import make_fake_response
from hornlab_search.search.evaluate import EvalContext
from hornlab_search.solve import cache

SHAS = {"hornlab_beat_bem": "b" * 40, "hornlab_bempp_bem": "c" * 40, "hornlab_mesher": "d" * 40,
        "hornlab_plots": "e" * 40, "hornlab_search": "f" * 40}


def _ctx(tmp_path, **over):
    return EvalContext(target=None, weights={}, lib_shas={**SHAS, **over}, cache_dir=tmp_path)


def _tree_hashes(d: Path) -> dict:
    return {str(p.relative_to(d)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(d.rglob("*")) if p.is_file()}


def test_same_shas_same_namespace_and_roundtrip_hits(tmp_path):
    a, b = _ctx(tmp_path), _ctx(tmp_path)
    assert a.solve_cache_root == b.solve_cache_root
    assert a.solve_cache_root.parent == tmp_path / "solve"
    assert a.solve_cache_root.name.startswith("p2-")
    assert a.mesh_cache_root.parent == tmp_path / "mesh"
    k = cache.key("d", "m", "s")
    cache.store(k, a.solve_cache_root, make_fake_response(), {})
    assert cache.lookup(k, b.solve_cache_root) is not None
    assert cache.lookup_status(k, b.solve_cache_root)["cache_schema"] == cache.CACHE_SCHEMA


def test_physics_lib_change_misses(tmp_path):
    base = _ctx(tmp_path)
    k = cache.key("d", "m", "s")
    cache.store(k, base.solve_cache_root, make_fake_response(), {})
    beat = _ctx(tmp_path, hornlab_beat_bem="1" * 40)
    mesher = _ctx(tmp_path, hornlab_mesher="2" * 40)
    assert beat.solve_cache_root != base.solve_cache_root
    assert mesher.solve_cache_root != base.solve_cache_root
    assert mesher.mesh_cache_root != base.mesh_cache_root
    assert beat.mesh_cache_root == base.mesh_cache_root     # mesh depends on the mesher only
    assert cache.lookup(k, beat.solve_cache_root) is None
    assert cache.lookup(k, mesher.solve_cache_root) is None


def test_non_physics_lib_change_still_hits(tmp_path):
    base = _ctx(tmp_path)
    k = cache.key("d", "m", "s")
    cache.store(k, base.solve_cache_root, make_fake_response(), {})
    other = _ctx(tmp_path, hornlab_search="9" * 40, hornlab_plots="8" * 40)
    assert other.solve_cache_root == base.solve_cache_root
    assert cache.lookup(k, other.solve_cache_root) is not None


def test_legacy_entry_untouched_and_unknown_disables(tmp_path):
    k = cache.key("d", "m", "s")
    legacy = tmp_path / "solve"
    cache.store(k, legacy, make_fake_response(), {})
    before = _tree_hashes(legacy / k)
    ctx = _ctx(tmp_path)
    cache.store(k, ctx.solve_cache_root, make_fake_response(), {})
    assert _tree_hashes(legacy / k) == before
    assert cache.lookup(k, legacy) is not None              # still readable
    assert _ctx(tmp_path, hornlab_beat_bem="unknown").solve_cache_root is None
    assert _ctx(tmp_path, hornlab_mesher="unknown").mesh_cache_root is None
    assert EvalContext(target=None, weights={}, lib_shas=SHAS).solve_cache_root is None
