"""Explicit entry point for the rectangular elliptical Klangfilm (Ahlswede calculator) family (``rows.type: klangfilm_ellipse``).

Rebinds the existing opt-in rolled-rectangle bridge to ``tools/geometry/klangfilm_ellipse.py`` in this process only,
like ``crowe_panel_cli.py``; installed packages and ``hornlab_search`` are unchanged. Subcommands: search,
verify, shape-check, preflight (bridge) and verify-night (serial verify of a night's jobs).
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.geometry import klangfilm_ellipse, rolled_rect_cli as bridge


def implementation_digest():
    h = hashlib.sha256()
    for path in (Path(klangfilm_ellipse.__file__), Path(bridge.__file__), Path(__file__)):
        data = path.read_bytes().replace(b"\r\n", b"\n")
        h.update(len(data).to_bytes(8, "big"))
        h.update(data)
    return h.hexdigest()


def install():
    if bridge._INSTALLED:
        if bridge.geometry is klangfilm_ellipse:
            return
        raise RuntimeError("cannot mix geometry entry points in the same process")
    bridge.geometry = klangfilm_ellipse
    bridge.KINDS = {"klangfilm_ellipse"}
    bridge.SHAPE_KNOBS = klangfilm_ellipse.SHAPE_KEYS - {"n_phi", "n_s", "wall_thickness_mm"}
    bridge.implementation_digest = implementation_digest
    bridge.install()


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "verify-night":
        from tools.geometry import verify_rolled_rect_night as verifier
        verifier.WRAPPER = Path(__file__).resolve()
        return verifier.main(argv[1:])
    install()
    return bridge.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
