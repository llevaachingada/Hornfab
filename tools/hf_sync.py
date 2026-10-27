"""Package runs / solve cache / dataset into tar shards and sync them to a Hugging Face dataset repo.

Why shards: GitHub cannot hold this data (~22 GB, ~250k files); a Hugging Face dataset repo can, and
many tiny files upload far faster as a few large tars. A collaborator without CUDA can download the
shards, untar them next to a checkout, and re-score the cached responses (the solve cache is keyed on
geometry + solver settings, NOT the objective, so ``hornlab-search`` re-scores it offline).

Groups (``--groups``): ``text`` runs/**/ *.json *.ndjson *.yaml *.html (small, the readable results),
``solve`` cache/solve, ``dataset`` dataset/, ``meshes`` cache/mesh + runs/**/*.msh (largest; optional).

Usage (python 3.13 with huggingface_hub, or the venv after ``pip install huggingface_hub``)::

    python tools/hf_sync.py pack   --out D:/hf_stage [--groups text,solve,dataset]   # no network
    python tools/hf_sync.py upload --out D:/hf_stage --repo chingadalleva/hornlab-search-data [--public]
    python tools/hf_sync.py pull   --repo ... --dest .      # collaborator side

``upload`` needs ``hf auth login`` (a WRITE token the owner enters themselves). The repo is created
PRIVATE unless ``--public`` is given. Do not pack while a GPU night is writing to runs/ or cache/.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import tarfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SHARD_BYTES = 2 * 1024**3
TEXT_EXT = {".json", ".ndjson", ".yaml", ".yml", ".html", ".md"}


def _files(group: str) -> list[Path]:
    if group == "text":
        return [p for p in (REPO / "runs").rglob("*") if p.is_file() and p.suffix in TEXT_EXT]
    if group == "solve":
        return [p for p in (REPO / "cache" / "solve").rglob("*") if p.is_file()]
    if group == "dataset":
        return [p for p in (REPO / "dataset").rglob("*") if p.is_file()]
    if group == "meshes":
        return ([p for p in (REPO / "cache" / "mesh").rglob("*") if p.is_file()]
                + [p for p in (REPO / "runs").rglob("*.msh") if p.is_file()])
    raise SystemExit(f"unknown group {group!r}")


def pack(out: Path, groups: list[str], dry_run: bool) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for g in groups:
        files = sorted(_files(g))
        total = sum(p.stat().st_size for p in files)
        print(f"{g}: {len(files)} files, {total / 1e9:.2f} GB")
        if dry_run:
            continue
        shard, size, tf = 0, 0, None
        for p in files:
            if tf is None or size >= SHARD_BYTES:
                if tf:
                    tf.close()
                tf = tarfile.open(out / f"{g}-{shard:03d}.tar", "w")
                shard, size = shard + 1, 0
            tf.add(p, arcname=p.relative_to(REPO).as_posix())
            size += p.stat().st_size
        if tf:
            tf.close()
        print(f"  wrote {shard} shard(s) to {out}")


def upload(out: Path, repo: str, public: bool) -> None:
    cmd = ["hf", "repos", "create", repo, "--repo-type", "dataset", "--exist-ok"]
    if not public:
        cmd.append("--private")
    subprocess.run(cmd, check=True)
    subprocess.run(["hf", "upload-large-folder", repo, str(out), "--repo-type", "dataset"], check=True)


def pull(repo: str, dest: Path) -> None:
    stage = dest / ".hf_stage"
    subprocess.run(["hf", "download", repo, "--repo-type", "dataset", "--local-dir", str(stage)], check=True)
    for t in sorted(stage.glob("*.tar")):
        print("extracting", t.name)
        with tarfile.open(t) as tf:
            tf.extractall(dest, filter="data")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("pack")
    a.add_argument("--out", type=Path, required=True)
    a.add_argument("--groups", default="text,solve,dataset")
    a.add_argument("--dry-run", action="store_true")
    b = sub.add_parser("upload")
    b.add_argument("--out", type=Path, required=True)
    b.add_argument("--repo", required=True)
    b.add_argument("--public", action="store_true")
    c = sub.add_parser("pull")
    c.add_argument("--repo", required=True)
    c.add_argument("--dest", type=Path, default=Path("."))
    args = ap.parse_args(argv)
    if args.cmd == "pack":
        pack(args.out, args.groups.split(","), args.dry_run)
    elif args.cmd == "upload":
        upload(args.out, args.repo, args.public)
    else:
        pull(args.repo, args.dest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
