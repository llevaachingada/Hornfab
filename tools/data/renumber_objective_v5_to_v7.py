"""Renumber the hardened-branch objective "v5" to v7 in stored data (2026-11-12).

Why: ``feat/hardened-plan-2026-10-29`` shipped its loading/flat_cv/8 kHz-floor/signed-V objective as
version 5 while main's version 5 became the MEH system objective (PR #18). Both were written as a bare
``5``. The integration merge of 2026-11-12 renumbered the hardened objective to 7
(``objective/scalar_v7.py``); this tool relabels the data that objective wrote, so a stored ``5``
means MEH and nothing else.

What is relabelled (5 -> 7), and how a row is recognised as hardened rather than MEH:
- dataset shards ``dataset/shard-*.jsonl``: ``objective_version == 5`` and either the terms carry
  ``flat_cv`` (a v7-only key) or the row has no MEH term (``lw_resid``/``notch``/``xo_lob``/
  ``headroom``) and was created before ``--meh-start`` (MEH runs began 2026-10-31).
- run dirs ``runs/*/``: ``run.json`` / ``config.yaml`` objective version 5 whose objective block
  carries a v7-only scoring constant (``loaded_re_z``, ``lfp_re_z``, ``lfp_crossover_ratio``,
  ``bw8k_floor``); then every ``objective_version: 5`` in that dir's ``search.ndjson`` too.

Safety: dry run by default (prints counts, writes nothing). ``--apply`` copies every file it will
change into ``--backup`` first, then writes via a temp file + ``os.replace`` so hardlinked copies
(tools/data/dedupe_runs.py) are never modified in place. Re-running is a no-op.

    .venv\\Scripts\\python.exe tools\\data\\renumber_objective_v5_to_v7.py            # dry run
    .venv\\Scripts\\python.exe tools\\data\\renumber_objective_v5_to_v7.py --apply
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path

V7_ONLY_BLOCK_KEYS = ("loaded_re_z", "lfp_re_z", "lfp_crossover_ratio", "bw8k_floor")
MEH_TERM_KEYS = ("lw_resid", "notch", "xo_lob", "headroom")
_V5_JSON = re.compile(r'("objective_version"\s*:\s*)5\b')
_V5_YAML = re.compile(r"^(\s*version:\s*)5\b", re.M)


def is_hardened_record(rec: dict, meh_start: str) -> bool:
    if rec.get("objective_version") != 5:
        return False
    terms = rec.get("terms") or {}
    if "flat_cv" in terms:
        return True
    if any(k in terms for k in MEH_TERM_KEYS):
        return False
    return str(rec.get("created_utc", "")) < meh_start


def _objective_block(run_dir: Path) -> dict | None:
    rj = run_dir / "run.json"
    if rj.is_file():
        try:
            data = json.loads(rj.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        for path in (("objective",), ("config", "objective"), ("brief", "objective")):
            node = data
            for k in path:
                node = node.get(k) if isinstance(node, dict) else None
            if isinstance(node, dict):
                return node
    cy = run_dir / "config.yaml"
    if cy.is_file():
        import yaml
        try:
            data = yaml.safe_load(cy.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            return None
        node = data.get("objective") if isinstance(data, dict) else None
        return node if isinstance(node, dict) else None
    return None


def is_hardened_run(run_dir: Path) -> bool:
    block = _objective_block(run_dir)
    return (isinstance(block, dict) and block.get("version") == 5
            and any(k in block for k in V7_ONLY_BLOCK_KEYS))


def _write(path: Path, text: str, backup_root: Path, repo: Path) -> None:
    dest = backup_root / path.resolve().relative_to(repo.resolve())
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        shutil.copy2(path, dest)
    tmp = path.with_name(path.name + ".renumber.tmp")
    tmp.write_text(text, encoding="utf-8", newline="")
    os.replace(tmp, path)                       # new inode: hardlinked siblings keep the old bytes


def plan_dataset(repo: Path, meh_start: str) -> dict[Path, tuple[str, int]]:
    out = {}
    for shard in sorted((repo / "dataset").glob("shard-*.jsonl")):
        lines = shard.read_text(encoding="utf-8").splitlines(keepends=True)
        n = 0
        for i, line in enumerate(lines):
            if '"objective_version"' not in line:
                continue
            rec = json.loads(line)
            if is_hardened_record(rec, meh_start):
                lines[i] = _V5_JSON.sub(r"\g<1>7", line, count=1)
                n += 1
        if n:
            out[shard] = ("".join(lines), n)
    return out


def plan_runs(repo: Path) -> dict[Path, tuple[str, int]]:
    out = {}
    for run_dir in sorted(p for p in (repo / "runs").glob("*") if p.is_dir()):
        if not is_hardened_run(run_dir):
            continue
        for name, rx in (("run.json", _V5_JSON), ("search.ndjson", _V5_JSON), ("config.yaml", _V5_YAML)):
            f = run_dir / name
            if not f.is_file():
                continue
            text = f.read_text(encoding="utf-8")
            if name == "run.json":
                text, n = re.subn(r'("version"\s*:\s*)5\b', r"\g<1>7", text)
                text, n2 = rx.subn(r"\g<1>7", text)
                n += n2
            else:
                text, n = rx.subn(r"\g<1>7", text)
            if n:
                out[f] = (text, n)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    ap.add_argument("--meh-start", default="2026-10-31T00:00:00Z",
                    help="rows created before this with no MEH term are hardened (default %(default)s)")
    ap.add_argument("--backup", type=Path, default=None,
                    help="backup root (default <repo>/runs/_backup_renumber_v5_v7)")
    ap.add_argument("--apply", action="store_true", help="write the changes (default: dry run)")
    a = ap.parse_args(argv)
    repo = a.repo
    backup = a.backup or repo / "runs" / "_backup_renumber_v5_v7"
    ds, rn = plan_dataset(repo, a.meh_start), plan_runs(repo)
    print(f"dataset: {sum(n for _, n in ds.values())} rows in {len(ds)} shard(s)")
    for p, (_, n) in ds.items():
        print(f"  {p.relative_to(repo)}: {n}")
    runs = sorted({p.parent for p in rn})
    print(f"runs: {len(runs)} dir(s), {sum(n for _, n in rn.values())} replacement(s)")
    for d in runs:
        print(f"  {d.relative_to(repo)}")
    if not a.apply:
        print("dry run: nothing written (pass --apply)")
        return 0
    for p, (text, _) in {**ds, **rn}.items():
        _write(p, text, backup, repo)
    print(f"applied; originals in {backup}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
