"""Thin argv bridge for Horn + woofer GUI system jobs.

The GUI launches system jobs through this one repo-relative script, exactly like the geometry
bridge CLIs under ``tools/geometry/``.  This file owns **no** logic: it prints the argv it received
(so the job log is self-describing) and forwards it to the package's own entry points.

Verbs
-----
``screen ...``                 -> ``hornlab_search.system.woofer_seed.main``
``reference prepare|validate|solve|report ...`` -> ``hornlab_search.system.cli``
``prepare|validate|solve|report ...``           -> the same, with ``reference`` inserted

Run it as ``python tools/system/gui_system_job.py <verb> ...`` from the repository root.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_REFERENCE_VERBS = ("prepare", "validate", "solve", "report")
_USAGE = (
    "usage: python tools/system/gui_system_job.py <verb> [args...]\n"
    "\n"
    "  screen ...                 CPU woofer/cabinet/XO/placement seed screen\n"
    "  reference <verb> ...       hornlab_search.system.cli reference subcommand\n"
    "  prepare|validate|solve|report ...  shorthand for reference <verb>\n"
)


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
