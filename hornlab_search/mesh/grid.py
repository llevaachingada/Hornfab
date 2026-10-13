"""Single seam over the mesher's structured-grid builder (issue #9 resolution).

`hornlab_mesher`'s ``config_builder.build_point_grid`` is not stable public API, but it is the
only way to regenerate the recorded structured grid for phase 2. Route it through exactly one
function here so a mesher change is contained in one place. The mesher is pinned in
pyproject.toml and guarded by tests/test_mesh_pin.py; this module only adds a clear error when
the function is genuinely unavailable.
"""
from __future__ import annotations

from typing import Any, Mapping


def build_point_grid(
    params: Mapping[str, Any], *, defer_osse_offset_repair: bool = False
) -> dict[str, Any]:
    """Regenerate the structured point grid for a recorded design.

    Thin delegate over ``hornlab_mesher.config_builder.build_point_grid``. Returns the mesher's
    grid dict unchanged (``inner_points`` / ``outer_points`` plus grid metadata); phase 2 owns
    how that dict is consumed. Raises ``RuntimeError`` with a pointer to the pin guard if the
    mesher is missing or the function moved, so a bump cannot silently change the label space.
    """
    try:
        from hornlab_mesher.config_builder import build_point_grid as _mesher_build
    except Exception as exc:  # noqa: BLE001 - any import shape change is the same failure
        raise RuntimeError(
            "hornlab_mesher.config_builder.build_point_grid is unavailable; the mesher pin may "
            "have changed (see tests/test_mesh_pin.py and TOOLCHAIN.md C4)."
        ) from exc
    return _mesher_build(params, defer_osse_offset_repair=defer_osse_offset_repair)
