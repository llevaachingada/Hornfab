"""Boundary Lab machine smoke: read-only probe (default) or a real vented generation.

Usage (from the worktree, HornLab venv only for non-probe actions):
    .venv/Scripts/python.exe tools/system/bl_smoke.py                 # probe JSON, exit 0
    .venv/Scripts/python.exe tools/system/bl_smoke.py --generate-smoke --real \
        --override width_m=0.30 --override mesh_size_m=0.05

Probe is purely read-only and deterministic. A REAL generation runs Boundary Lab's own
generator in BL's own environment (CPU Gmsh meshing only — no solver), writes artifacts to
the isolated system store, and prints the NDJSON tail plus artifact hashes. It is refused
unless the probe verifies the install.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from hornlab_search.system.boundarylab.generate import generate_vented, runner_path  # noqa: E402
from hornlab_search.system.boundarylab.probe import BL_CAPABILITY_MISSING, probe_boundarylab  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Boundary Lab probe / vented generation smoke")
    parser.add_argument("--extra-root", action="append", default=[],
                        help="additional candidate directory (repeatable)")
    parser.add_argument("--probe-only", action="store_true", help="never run the generator")
    parser.add_argument("--generate-smoke", action="store_true",
                        help="run one REAL vented generation after a verified probe")
    parser.add_argument("--real", action="store_true",
                        help="required together with --generate-smoke (explicit opt-in)")
    parser.add_argument("--override", action="append", default=[],
                        metavar="KEY=VALUE", help="SI source override (e.g. width_m=0.30)")
    parser.add_argument("--timeout", type=float, default=1800.0)
    args = parser.parse_args(argv)

    probe = probe_boundarylab(extra_roots=args.extra_root)
    print(json.dumps({"probe": probe.to_dict(), "runner": str(runner_path())},
                     sort_keys=True, indent=2))
    if not args.generate_smoke:
        return 0
    if not args.real:
        print("[smoke] refusing: --generate-smoke requires --real", file=sys.stderr)
        return 2
    root = probe.verified_root
    if root is None:
        print(f"[smoke] {BL_CAPABILITY_MISSING}: no verified BL root; generation refused",
              file=sys.stderr)
        return 3
    overrides: dict[str, float] = {}
    for item in args.override:
        key, _, value = item.partition("=")
        overrides[key] = float(value)
    result = generate_vented(root, overrides, timeout_s=args.timeout)
    print(json.dumps({
        "ok": result.ok,
        "case_dir": str(result.case_dir),
        "output_dir": None if result.output_dir is None else str(result.output_dir),
        "meshes": [
            {"id": m.get("id"), "purpose": m.get("purpose"), "path": m.get("path"),
             "bytes": None if not m.get("path") else Path(m["path"]).stat().st_size,
             "sha256": m.get("sha256")}
            for m in result.meshes
        ],
        "port_mouth_diameter_m": result.port_mouth_diameter_m,
        "manifest": None if result.manifest_path is None else str(result.manifest_path),
        "returncode": result.returncode,
        "log_tail": list(result.captured_log_tail[-12:]),
    }, indent=2, sort_keys=True))
    return 0 if result.ok else 4


if __name__ == "__main__":
    raise SystemExit(main())
