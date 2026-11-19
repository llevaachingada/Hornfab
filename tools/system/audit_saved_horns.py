"""Read-only saved-horn audit CLI (``hornlab_search.system`` Tier 0).

Prints an inventory of saved horn solves and the Tier-0 facts the system layer may use. It is a
strictly read-only observer: the runs tree is opened read-only through
:func:`hornlab_search.solve.cache.load_response`, nothing is written anywhere, and the machine
(``--json``) output contains no wall-clock fields, so two runs over the same inputs are
byte-identical.

Usage::

    .venv\\Scripts\\python.exe tools/system/audit_saved_horns.py --limit 60 --json
    .venv\\Scripts\\python.exe tools/system/audit_saved_horns.py --runs-root <dir> --md

Defaults:
    --runs-root  $HORNLAB_SYSTEM_RUNS_ROOT, else C:/Users/hunte/Hrns/hornlab-search/runs
    --limit      40 newest run directories by mtime
    output       --json (machine, sorted keys) unless --md is given
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from hornlab_search.system.horn_assets import (  # noqa: E402
    DEFAULT_RUNS_ROOT,
    RUNS_ROOT_ENV,
    InventoryResult,
    default_runs_root,
    inventory_runs,
)

PROG = "audit_saved_horns"


def render_json(result: InventoryResult) -> str:
    """Deterministic machine output (sorted keys, no timestamps)."""
    return json.dumps(result.to_dict(), sort_keys=True, indent=2) + "\n"


def render_markdown(result: InventoryResult) -> str:
    counts = result.quality_counts()
    lines = [
        "# Saved-horn inventory (Tier 0)",
        "",
        f"- runs root: `{result.runs_root}`",
        f"- run directories scanned: {result.runs_scanned}",
        f"- design directories scanned: {result.design_dirs_scanned}",
        f"- assets: {len(result.assets)} (duplicates collapsed: {result.duplicates_collapsed}; "
        f"skipped non-assets: {result.skipped_dirs})",
        f"- complex p_* fields: {result.with_complex_fields()} "
        f"(H/V {result.with_complex_hv()}, balloon {result.with_complex_balloon()})",
        "",
        "| quality | count |",
        "| --- | ---: |",
    ]
    lines.extend(f"| {name} | {counts.get(name, 0)} |" for name in sorted(counts))
    lines.extend([
        "",
        "| asset_id | quality | family | freqs (Hz) | brief |",
        "| --- | --- | --- | --- | --- |",
    ])
    for asset in result.assets:
        lo = f"{asset.freqs_hz[0]:g}" if asset.freqs_hz else "-"
        hi = f"{asset.freqs_hz[-1]:g}" if asset.freqs_hz else "-"
        band = f"{lo}-{hi}" if asset.freqs_hz else "-"
        lines.append(
            f"| {asset.asset_id} | {asset.quality} | {asset.geometry.family or '-'} | "
            f"{band} | {asset.geometry.brief_id or '-'} |")
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROG,
        description="Read-only inventory of saved horn solves (Tier-0 compatibility facts).")
    parser.add_argument(
        "--runs-root", default=None,
        help=f"runs tree to scan (default: ${RUNS_ROOT_ENV} or {DEFAULT_RUNS_ROOT})")
    parser.add_argument(
        "--limit", type=int, default=40,
        help="number of newest run directories to scan by mtime (default: 40)")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--json", action="store_true", help="machine output (default)")
    group.add_argument("--md", action="store_true", help="Markdown summary")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.limit < 0:
        raise SystemExit("--limit must be >= 0")
    root = Path(args.runs_root) if args.runs_root else default_runs_root()
    result = inventory_runs(root, limit=args.limit)
    sys.stdout.write(render_markdown(result) if args.md else render_json(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
