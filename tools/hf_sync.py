"""Two-way Hugging Face sync between labs: pack / push / pull (+ legacy whole-repo upload).

Why shards: GitHub cannot hold this data (~22 GB, ~250k files); a Hugging Face dataset repo can, and
many tiny files upload far faster as a few large tars. A collaborator without CUDA can download the
shards, untar them next to a checkout, and re-score the cached responses (the solve cache is keyed on
geometry + solver settings, NOT the objective, so ``hornlab-search`` re-scores it offline).

Labs flow (2026-11-12; each lab pushes its own tree, nobody ranks across labs):

* ``pack``   -- ALWAYS regenerates ``<dataset>/MANIFEST.json`` first (that is
   ``hornlab_search.dataset.manifest``, the L5 census: schema version, row groups, per-shard
   sha256), so any packed snapshot carries a manifest describing exactly the shards in it. Read-only
   over the shards; the manifest itself is the only file written into the dataset root.
* ``push --lab <name>`` -- pack into a staging dir, then upload it under the ``labs/<name>/`` prefix
   of a dataset repo (default ``chingadalleva/hornlab-search-data``, override with ``--repo``).
* ``pull --lab <name> --into dataset_ext/<name>`` -- download one lab's shards + run dirs and extract
   them under ``dataset_ext/<name>/`` (the tool REFUSES any ``--into`` inside the local ``dataset/``:
   foreign rows are validated and tagged by ``tools/data/ingest_foreign.py`` and never merge).

Legacy single-owner flow (predates the labs prefix; still works, documented in
``docs/COLLABORATOR_PULL_RUNBOOK_2026-11-02.md``): ``upload`` pushes a pack stage to the repo ROOT
and ``pull-all`` downloads everything. Use the labs flow for per-lab data.

Groups (``--groups``): ``text`` runs/**/ *.json *.ndjson *.yaml *.html (small, the readable results),
``solve`` cache/solve, ``dataset`` dataset/, ``meshes`` cache/mesh + runs/**/*.msh (largest; optional).

Usage (python 3.13 with huggingface_hub, or the venv after ``pip install huggingface_hub``)::

    python tools/hf_sync.py pack   --out D:/hf_stage [--groups text,solve,dataset]   # no network
    python tools/hf_sync.py push   --lab hunter-4060 --out D:/hf_stage [--repo chingadalleva/hornlab-search-data]
    python tools/hf_sync.py pull   --lab collin --into dataset_ext/collin [--repo ...]
    python tools/hf_sync.py upload --out D:/hf_stage --repo chingadalleva/hornlab-search-data [--public]
    python tools/hf_sync.py pull-all --repo ... --dest .      # legacy collaborator side

Auth: ``hf auth login`` with a WRITE token, entered by the owner. The repo is created PRIVATE unless
``--public`` is given. Do not pack or push while a GPU night is writing to runs/ or cache/.

CLI notes (checked against huggingface_hub docs 2026-11-02): ``hf upload`` replaced the deprecated
``hf upload-large-folder`` (removed in v2.x) and is itself resumable — re-run the same command after
an interruption and already-uploaded shards are skipped. ``hf_transfer`` no longer exists; the speed
knob is ``HF_XET_HIGH_PERFORMANCE=1`` (set here automatically). Uploads always set
``HF_HUB_DISABLE_XET=1``: measured on the owner machine 2026-11-02, the Xet upload path stalls
(0.1-1.2 MB/s, zero commits after 25 min) while the classic LFS path pushes 2 GB in ~3.4 min.
Downloads are unaffected (Xet stays enabled for them).
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tarfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from hornlab_search.dataset.manifest import DEFAULT_LAB as DEFAULT_MANIFEST_LAB  # noqa: E402
from hornlab_search.dataset.manifest import build_manifest, write_manifest  # noqa: E402

DEFAULT_REPO = "chingadalleva/hornlab-search-data"
SHARD_BYTES = 2 * 1024**3
TEXT_EXT = {".json", ".ndjson", ".yaml", ".yml", ".html", ".md"}
MANIFEST_ARCNAME = "dataset/MANIFEST.json"

#: Overridable roots (tests point these at fixtures; the real run reads the repo tree).
RUNS_ROOT = REPO / "runs"


def _run(cmd: list[str], *, env: dict[str, str] | None = None) -> None:
    """One hf CLI call. Tests replace this with a recorder / fake downloader."""
    subprocess.run(cmd, check=True, env=env)


def _env(disable_xet: bool = False) -> dict[str, str]:
    env = {**os.environ, "HF_XET_HIGH_PERFORMANCE": "1"}
    if disable_xet:
        env["HF_HUB_DISABLE_XET"] = "1"
    return env


def _files(group: str, *, dataset_root: Path | None = None) -> list[Path]:
    if group == "text":
        return [p for p in RUNS_ROOT.rglob("*") if p.is_file() and p.suffix in TEXT_EXT]
    if group == "solve":
        return [p for p in (REPO / "cache" / "solve").rglob("*") if p.is_file()]
    if group == "dataset":
        return [p for p in (dataset_root or REPO / "dataset").rglob("*") if p.is_file()]
    if group == "meshes":
        return ([p for p in (REPO / "cache" / "mesh").rglob("*") if p.is_file()]
                + [p for p in RUNS_ROOT.rglob("*.msh") if p.is_file()])
    raise SystemExit(f"unknown group {group!r}")


def pack(out: Path, groups: list[str], dry_run: bool, *,
         dataset_root: Path | None = None, lab: str = DEFAULT_MANIFEST_LAB) -> None:
    """Pack the groups into ``out`` as tar shards. Runs the L5 manifest census FIRST, always.

    The census is read-only over the shards; it writes exactly one file, ``dataset/MANIFEST.json``
    (regenerated, never hand-edited), which the ``dataset`` group then packs automatically. If the
    ``dataset`` group is NOT packed, the manifest still ships: a standalone ``manifest-000.tar``
    carries it as ``dataset/MANIFEST.json``. ``--dry-run`` computes and prints the census without
    writing anything.
    """
    out.mkdir(parents=True, exist_ok=True)
    root = Path(dataset_root) if dataset_root is not None else REPO / "dataset"
    if root.is_dir():
        if dry_run:
            doc = build_manifest(root, lab=lab)
            print(f"[manifest dry-run] rows={doc['total_rows']} shards={len(doc['shards'])} "
                  f"lab={doc['lab']}")
        else:
            _path, doc = write_manifest(root, lab=lab)
            print(f"[manifest] {doc['total_rows']} rows, {len(doc['shards'])} shard(s) -> {_path}")
    else:
        print(f"[manifest] no dataset root at {root}; packing without a manifest")

    manifest_file = root / "MANIFEST.json"
    for g in groups:
        files = sorted(_files(g, dataset_root=root))
        total = sum(p.stat().st_size for p in files)
        print(f"{g}: {len(files)} files, {total / 1e9:.2f} GB")
        if dry_run:
            continue
        shard, size, tf = 0, 0, None
        for p in files:
            if tf is None or size >= SHARD_BYTES:
                if tf:
                    tf.close()
                    shard += 1          # rotate: never reopen the same tar (it truncated at 2 GB)
                tf = tarfile.open(out / f"{g}-{shard:03d}.tar", "w")
                size = 0
            arcname = (p.relative_to(REPO).as_posix() if dataset_root is None
                       else p.relative_to(root.parent).as_posix())
            tf.add(p, arcname=arcname)
            size += p.stat().st_size
        if tf:
            tf.close()
        print(f"  wrote {shard + 1} shard(s) to {out}")
    if not dry_run and "dataset" not in groups and manifest_file.is_file():
        # The dataset group was not packed; the manifest must still travel (spec: "always includes").
        with tarfile.open(out / "manifest-000.tar", "w") as tf:
            tf.add(manifest_file, arcname=MANIFEST_ARCNAME)
        print("  added dataset/MANIFEST.json to the stage (manifest-000.tar)")


def push(lab: str, repo: str, out: Path, groups: list[str], *, public: bool = False,
         dry_run: bool = False, dataset_root: Path | None = None) -> None:
    """One lab's data: pack (manifest first, always), then upload under ``labs/<lab>/``.

    Uploads set ``HF_HUB_DISABLE_XET=1`` (see module docstring). ``--dry-run`` packs nothing and
    uploads nothing; it prints what would be done.
    """
    prefix = f"labs/{lab}"
    print(f"push {lab} -> {repo} under {prefix}/")
    pack(out, groups, dry_run, dataset_root=dataset_root, lab=lab)
    if dry_run:
        print(f"dry run: would upload {out} to {repo}:{prefix} (HF_HUB_DISABLE_XET=1)")
        return
    create = ["hf", "repos", "create", repo, "--repo-type", "dataset", "--exist-ok"]
    create.append("--public" if public else "--private")
    _run(create, env=_env(disable_xet=True))
    _run(["hf", "upload", repo, str(out), prefix, "--repo-type", "dataset"],
         env=_env(disable_xet=True))


def pull(lab: str, repo: str, into: Path) -> None:
    """Download one lab's shards + run dirs and extract them under ``into``.

    Refuses any ``--into`` inside this checkout's ``dataset/``: foreign rows never merge into the
    local dataset. They land in ``dataset_ext/<lab>/`` and are checked + tagged by
    ``tools/data/ingest_foreign.py``.
    """
    into = into.resolve()
    _guard_not_dataset(into)
    stage = into / "_hf_stage"
    print(f"pull {lab} from {repo} (labs/{lab}/*) -> {into}")
    _run(["hf", "download", repo, "--repo-type", "dataset", "--include", f"labs/{lab}/**/*",
          "--local-dir", str(stage)], env=_env())
    tars = sorted(stage.rglob("*.tar"))
    if not tars:
        print(f"no tars found in the repo for {lab}; nothing extracted")
        return
    into.mkdir(parents=True, exist_ok=True)
    for t in tars:
        print("extracting", t.name)
        with tarfile.open(t) as tf:
            tf.extractall(into, filter="data")
    print(f"extracted {len(tars)} shard(s) under {into}; validate with "
          f"tools/data/ingest_foreign.py --lab {lab}")


def _guard_not_dataset(path: Path) -> None:
    """Foreign data never touches the live dataset/ (or anything else critical)."""
    parts = {p.lower() for p in path.parts}
    dataset = (REPO / "dataset").resolve()
    if path == dataset or dataset in path.parents:
        raise SystemExit(f"refusing to write inside the live dataset/ ({path}); "
                         "use dataset_ext/<lab>/ instead")
    if "dataset_ext" not in parts:
        raise SystemExit(f"{path} is not a dataset_ext/<lab>/ directory; "
                         "pull/ingest data lives under dataset_ext/")


def upload(out: Path, repo: str, public: bool) -> None:
    """LEGACY whole-repo upload: push a stage to the repo ROOT (no labs/ prefix)."""
    create = ["hf", "repos", "create", repo, "--repo-type", "dataset", "--exist-ok"]
    create.append("--public" if public else "--private")
    _run(create, env=_env(disable_xet=True))
    # ``hf upload`` (not the deprecated ``hf upload-large-folder``): resumable, auto-splits commits.
    # The trailing "." keeps the shards at the repo root.
    _run(["hf", "upload", repo, str(out), ".", "--repo-type", "dataset"],
         env=_env(disable_xet=True))


def pull_all(repo: str, dest: Path) -> None:
    """LEGACY whole-repo download: everything (old collaborator flow, no labs/ prefix)."""
    stage = dest / ".hf_stage"
    _run(["hf", "download", repo, "--repo-type", "dataset", "--include", "*.tar",
          "--local-dir", str(stage)], env=_env())
    for t in sorted(stage.glob("*.tar")):
        print("extracting", t.name)
        with tarfile.open(t) as tf:
            tf.extractall(dest, filter="data")


def _groups(raw: str | None, default: str) -> list[str]:
    return [g for g in (raw or default).split(",") if g]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__ or "two-way HF sync between labs")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("pack", help="tar the groups into a stage dir; manifest FIRST, always")
    a.add_argument("--out", type=Path, required=True)
    a.add_argument("--groups", default="text,solve,dataset")
    a.add_argument("--dataset-root", type=Path, default=None,
                   help="dataset root for the manifest census (default <repo>/dataset)")
    a.add_argument("--lab", default=DEFAULT_MANIFEST_LAB,
                   help=f"lab label for the manifest (default {DEFAULT_MANIFEST_LAB})")
    a.add_argument("--dry-run", action="store_true")
    b = sub.add_parser("push", help="pack + upload this lab's data under labs/<lab>/")
    b.add_argument("--lab", required=True)
    b.add_argument("--repo", default=DEFAULT_REPO)
    b.add_argument("--out", type=Path, required=True, help="staging directory for the tars")
    b.add_argument("--groups", default="text,dataset")
    b.add_argument("--dataset-root", type=Path, default=None)
    b.add_argument("--public", action="store_true")
    b.add_argument("--dry-run", action="store_true")
    c = sub.add_parser("pull", help="download one lab's shards + run dirs into dataset_ext/<lab>/")
    c.add_argument("--lab", required=True)
    c.add_argument("--repo", default=DEFAULT_REPO)
    c.add_argument("--into", type=Path, required=True, help="target dir (must be dataset_ext/<lab>/)")
    d = sub.add_parser("upload", help="LEGACY: push a stage to the repo ROOT")
    d.add_argument("--out", type=Path, required=True)
    d.add_argument("--repo", default=DEFAULT_REPO)
    d.add_argument("--public", action="store_true")
    e = sub.add_parser("pull-all", help="LEGACY: download the whole repo (no labs/ prefix)")
    e.add_argument("--repo", default=DEFAULT_REPO)
    e.add_argument("--dest", type=Path, default=Path("."))
    args = ap.parse_args(argv)
    if args.cmd == "pack":
        pack(args.out, _groups(args.groups, "text,solve,dataset"), args.dry_run,
             dataset_root=args.dataset_root, lab=args.lab)
    elif args.cmd == "push":
        push(args.lab, args.repo, args.out, _groups(args.groups, "text,dataset"),
             public=args.public, dry_run=args.dry_run, dataset_root=args.dataset_root)
    elif args.cmd == "pull":
        pull(args.lab, args.repo, args.into)
    elif args.cmd == "upload":
        upload(args.out, args.repo, args.public)
    else:
        pull_all(args.repo, args.dest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
