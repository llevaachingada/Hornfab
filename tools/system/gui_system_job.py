"""Thin argv bridge for Horn + woofer GUI system jobs.

The GUI launches system jobs through this one repo-relative script, exactly like the geometry
bridge CLIs under ``tools/geometry/``.  It owns no acoustics or solver logic: it prints the argv it
received (so the job log is self-describing) and forwards it to the package's own entry points.  The
single write the handoff assigns to the job rather than the server is the solve preset request JSON
(``solve`` below); that file is produced by :mod:`hornlab_search.gui.data_hw_stage`.

Verbs
-----
``screen ...``                 -> ``hornlab_search.system.woofer_seed.main``
``stage ...``                  -> ``hornlab_search.system.cli reference prepare``
``validate ...``               -> ``hornlab_search.system.cli reference validate``
``solve <case> --preset P --authorized-by RECORD``
                               -> writes ``<case>/<preset>_request.json`` (the job, never the
                                  server) then ``hornlab_search.system.cli reference solve``
``reference prepare|validate|solve|report ...`` -> ``hornlab_search.system.cli``
``prepare|report ...``                          -> the same, with ``reference`` inserted

Run it as ``python tools/system/gui_system_job.py <verb> ...`` from the repository root.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_REFERENCE_VERBS = ("prepare", "validate", "report")
_USAGE = (
    "usage: python tools/system/gui_system_job.py <verb> [args...]\n"
    "\n"
    "  screen ...                 CPU woofer/cabinet/XO/placement seed screen\n"
    "  stage ...                  stage+validate a horn+vented project (reference prepare)\n"
    "  validate <exp>/<case> ...  BL's own validate verdict (reference validate)\n"
    "  solve <exp>/<case> --preset P --authorized-by RECORD\n"
    "                             write <case>/<P>_request.json then reference solve\n"
    "  reference <verb> ...       hornlab_search.system.cli reference subcommand\n"
    "  prepare|report ...         shorthand for reference <verb>\n"
)


def _solve(rest: list[str]) -> int:
    """Write the preset request into the case dir (the job's job), then BL's own solve path."""
    parser = argparse.ArgumentParser(prog="python tools/system/gui_system_job.py solve")
    parser.add_argument("case")
    parser.add_argument("--preset", required=True)
    parser.add_argument("--authorized-by", required=True)
    ns = parser.parse_args(rest)
    from hornlab_search.gui import data_hw_stage as HWS
    from hornlab_search.system import cli

    request = HWS.write_solve_request(ns.case, ns.preset, root=ROOT)
    return cli.main(["reference", "solve", ns.case, "--request", str(request),
                     "--backend", "beat_cpu", "--authorized-by", ns.authorized_by])


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    print("gui_system_job argv: " + " ".join(args), flush=True)

    if not args or args[0] in ("--help", "-h"):
        print(_USAGE, end="")
        return 0

    verb, rest = args[0], args[1:]
    if verb == "screen":
        from hornlab_search.system import woofer_seed
        return woofer_seed.main(rest)
    if verb == "stage":
        from hornlab_search.system import cli
        return cli.main(["reference", "prepare", *rest])
    if verb == "solve":
        return _solve(rest)
    if verb == "reference":
        from hornlab_search.system import cli
        return cli.main(["reference", *rest])
    if verb in _REFERENCE_VERBS:
        from hornlab_search.system import cli
        return cli.main(["reference", verb, *rest])

    print(f"gui_system_job: unknown verb {verb!r}\n{_USAGE}", file=sys.stderr, end="")
    return 2


if __name__ == "__main__":
    sys.exit(main())
