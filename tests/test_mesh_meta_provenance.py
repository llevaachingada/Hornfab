"""Offline tests for the additive mesher provenance in mesh_meta.json (mesh/build.py)."""
from __future__ import annotations

from types import SimpleNamespace

from hornlab_search.mesh.build import _mesher_provenance


def test_mesher_provenance_keeps_the_known_blocks():
    built = SimpleNamespace(metadata={
        "outerWallClearance": {"capActive": True, "cappedSizeAtMinRadiusMm": 8.0},
        "quality": {"min_angle_deg": 22.0},
        "meshTriangleCount": 6721,
        "someUnrelatedKey": {"huge": [1, 2, 3]},
    })
    out = _mesher_provenance(built)
    assert out["outerWallClearance"]["capActive"] is True
    assert out["quality"]["min_angle_deg"] == 22.0
    assert out["meshTriangleCount"] == 6721
    assert "someUnrelatedKey" not in out


def test_mesher_provenance_never_raises_on_unserialisable_metadata():
    # A set as a whole block is not a JSON value: it is filtered out, not fabricated.
    assert _mesher_provenance(SimpleNamespace(metadata={"quality": {1, 2, 3}})) == {}
    # A dict block that still contains a set survives the type filter but not json.dumps.
    out = _mesher_provenance(SimpleNamespace(metadata={"quality": {"bad": {1, 2, 3}}}))
    assert out == {"note": "mesher metadata was not JSON-safe"}


def test_mesher_provenance_empty_without_metadata():
    assert _mesher_provenance(SimpleNamespace(metadata={})) == {}
    assert _mesher_provenance(SimpleNamespace()) == {}
