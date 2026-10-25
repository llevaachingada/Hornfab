"""Regression pin for the dead evolution 3D toggle (duplicate DOM id).

THE BUG: `evolution.js` gave the 3D checkbox `id="evo-3d"` and the canvas container the SAME
`id="evo-3d"`. The input came first in document order, so every `getElementById("evo-3d")` in
`build3d`/`disable3d` resolved the checkbox: `init3dFrames` cleared the input and appended the
WebGL canvas (and the render-settings chip) into it, while the visible div kept the template's
`3D off — flip the 3D toggle above.` placeholder; `container._dispose3d` landed on the input while
`[data-v3d]` was on the div, so `route()`'s disposal sweep never disposed the player (leaked rAF
loop + WebGL context per navigation); and the checkbox stayed visually "on".

WHY A SOURCE PIN (not a headless node import): `evolution.js` is a browser ES module that touches
`document`, `CSS.escape`, `location`, and `fetch("/api/evolution/…")`, and imports `charts.js`.
There is no jsdom (or any DOM shim) in this repo's test environment, so importing the module would
only prove a stub works — it would not prove the view builds. This repo already pins static GUI
sources by string where the browser is the only honest executor (see
`tests/test_gui_brief_authoring.py::test_evolution_3d_mode_is_wired` and `tests/test_gui.py`).
These assertions are on the real file, not on a harness. The one thing a source pin cannot show —
that WebGL actually paints — is stated as residual risk in the fix report.

Every assertion here fails if the duplicate-id bug returns: distinct ids, container-only
`getElementById` reads, the `[data-v3d]` tag is the exact node handed to `init3dFrames`, and the
toggle / placeholder states are reset together.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVO = ROOT / "hornlab_search" / "gui" / "static" / "evolution.js"

MARKER = "data-v3d"
PLACEHOLDER = "3D off — flip the 3D toggle above."
GET_BY_ID = re.compile(r'document\.getElementById\("([^"]+)"\)')
MARKED_TAG = re.compile(r"<[^>]*\b" + MARKER + r"\b[^>]*>")


def _src() -> str:
    return EVO.read_text(encoding="utf-8")


def _line_at(src: str, pos: int) -> str:
    return src[src.rfind("\n", 0, pos) + 1: src.find("\n", pos)]


def _container(src: str) -> tuple[str, str]:
    """(id, tag) of the one HTML tag the evolution template marks [data-v3d]."""
    tags = [t for t in MARKED_TAG.findall(src) if "evo-" in t or "id=" in t]
    assert len(tags) == 1, f"expected exactly one [data-v3d] tag in evolution.js, got {tags}"
    tag = tags[0]
    m = re.search(r'\bid="([^"]+)"', tag)
    assert m, f"the [data-v3d] tag must carry an id: {tag}"
    return m.group(1), tag


def _checkbox(src: str) -> tuple[str, str]:
    """(id, tag) of the 3D checkbox in the playback controls."""
    m = re.search(r'<input[^>]*\bid="([^"]+)"[^>]*>\s*3D', src)
    assert m, "the 3D checkbox (<input …> 3D</label>) is missing from evolution.js"
    return m.group(1), m.group(0)


def _func_body(src: str, header: str) -> str:
    start = src.index(header)
    end = src.index("\n  }", start)
    return src[start:end]


# ── 1. the two element ids are different strings (the root cause) ────────────────────────────────
def test_checkbox_and_container_have_distinct_ids():
    src = _src()
    container_id, container_tag = _container(src)
    checkbox_id, checkbox_tag = _checkbox(src)

    assert container_id != checkbox_id, (
        f"3D checkbox and 3D container share id={container_id!r}; getElementById would resolve the "
        "checkbox (first in document order) instead of the canvas container"
    )
    # data-v3d sits on the SAME tag as the container id — and not on the checkbox
    assert f'id="{container_id}"' in container_tag
    assert MARKER in container_tag
    assert MARKER not in checkbox_tag
    assert "view3d-fallback" in src[src.index(container_tag):src.index("</div>", src.index(container_tag))]


# ── 2. the [data-v3d] node is the exact node handed to the 3D player (disposal path) ─────────────
def test_container_is_the_element_handed_to_init3d_frames():
    src = _src()
    container_id, _ = _container(src)
    checkbox_id, _ = _checkbox(src)

    build = _func_body(src, "async function build3d() {")
    assert f'const cv = document.getElementById("{container_id}")' in build
    assert "init3dFrames(cv, frames3d" in build, (
        "init3dFrames must receive the container resolved from the [data-v3d] id "
        "(view3d.js attaches _dispose3d to that same container)"
    )
    # one player construction, and the checkbox id never reaches the renderer
    assert src.count("init3dFrames(") == 1
    assert f'init3dFrames(document.getElementById("{checkbox_id}")' not in src


# ── 3. every reader resolves the container; the checkbox is only ever the checkbox ───────────────
def test_readers_resolve_the_container_not_the_checkbox():
    src = _src()
    container_id, _ = _container(src)
    checkbox_id, _ = _checkbox(src)

    container_reads = [m for m in GET_BY_ID.finditer(src) if m.group(1) == container_id]
    assert len(container_reads) == 2, (
        "expected exactly the build3d and disable3d container lookups, got "
        f"{[m.group(0) for m in container_reads]}"
    )
    for m in container_reads:
        line = _line_at(src, m.start())
        assert "checked" not in line and "onchange" not in line, (
            f"container id is used as a toggle control: {line!r}"
        )

    checkbox_reads = [m for m in GET_BY_ID.finditer(src) if m.group(1) == checkbox_id]
    assert len(checkbox_reads) == 1, (
        f"the checkbox must be looked up once, got {[m.group(0) for m in checkbox_reads]}"
    )
    assert "const box3d = document.getElementById" in _line_at(src, checkbox_reads[0].start())

    # the old collision, written back as source: box3d must never resolve the container id
    assert f'const box3d = document.getElementById("{container_id}")' not in src
    # the player build and the off-state restore never touch the checkbox id
    for header in ("async function build3d() {", "function disable3d(reason) {"):
        assert checkbox_id not in _func_body(src, header)


# ── 4. one state: the box starts unchecked, off restores unchecked + placeholder, rules kept ─────
def test_toggle_state_and_off_placeholder_stay_coherent():
    src = _src()
    container_id, container_tag = _container(src)
    checkbox_id, _ = _checkbox(src)

    # initialise from the renderer's actual state (off) rather than trusting the template
    box_at = src.index(f'const box3d = document.getElementById("{checkbox_id}");')
    assert "box3d.checked = false" in src[box_at:box_at + 400], (
        "the toggle must start unchecked to match the built-off renderer"
    )

    disable = _func_body(src, "function disable3d(reason) {")
    assert "box3d.checked = false" in disable, "disable3d must reset the checkbox, not only the player"
    assert f'const cv = document.getElementById("{container_id}")' in disable
    assert "cv.innerHTML" in disable and PLACEHOLDER in disable, (
        "disable3d must restore the off placeholder on the CONTAINER"
    )

    # the placeholder exists only as the template's off-state and disable3d's restore
    assert src.count(PLACEHOLDER) == 2
    tag_start = src.index(container_tag)
    assert PLACEHOLDER in src[tag_start:src.index("</div>", tag_start)]

    # both directions of the improvements-only rule survive the fix
    assert 'mode !== "best"' in src                      # checking 3D forces improvements-only
    assert 'mode === "all" && box3d.checked' in src     # every-candidate turns 3D off
