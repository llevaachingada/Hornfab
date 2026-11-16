"""GUI preview for the opt-in bridge typologies (2026-11-15 home landscape).

The bridge cells are not in the stock campaign catalog because their custom rows kinds only
load after their own CLI installs a process-local adapter. The GUI's typology sandbox must still
render them; ``preview_shape`` dispatches them to ``tools/geometry/gui_preview.py`` in a fresh
process. These tests exercise that real path, not a mock.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from hornlab_search.gui import data as D

ROOT = Path(__file__).resolve().parents[1]
BRIEF = "room_landscape_80x50_700_hf1440_v7"
BRIDGE_CELLS = (
    "hl__rosse_rect_cd_v7",
    "hl__rolled_es_spiral_v7",
    "hl__crowe_panel_home_v7",
)


@pytest.mark.parametrize("name", BRIDGE_CELLS)
def test_bridge_cell_preview_2d_has_sections_and_mouth(name):
    payload = D.preview_shape(ROOT, name, {"detail": ["2d"], "brief": BRIEF})
    assert payload.get("available") is True, payload.get("notes")
    assert payload.get("kind") == "rows"
    assert len(payload["section"]["h"]["inner"]) > 0
    assert len(payload["section"]["v"]["inner"]) > 0
    assert len(payload["mouth"]["inner"]) > 0
    assert payload["shape3d"]["available"] is False
    assert payload["shape3d"]["reason"] == "detail=2d"


@pytest.mark.parametrize("name", BRIDGE_CELLS)
def test_bridge_cell_preview_3d_has_vertices(name):
    payload = D.preview_shape(ROOT, name, {"detail": ["3d"], "brief": BRIEF})
    assert payload.get("available") is True, payload.get("notes")
    shape = payload.get("shape3d") or {}
    assert shape.get("available") is True, shape.get("reason")
    assert len(shape.get("verts") or []) > 0
    assert len(shape.get("tris") or []) > 0


def test_bridge_cells_are_visible_but_preview_only():
    rows = {r["name"]: r for r in D.typologies(ROOT, ROOT / "runs")}
    for name in BRIDGE_CELLS:
        row = rows.get(name)
        assert row is not None, f"{name} is missing from the GUI typology list"
        assert row["preview_only"] is True
        # Launch stays disabled: the stock campaign path cannot materialize the custom rows kind.
        assert row["disabled"] is True
