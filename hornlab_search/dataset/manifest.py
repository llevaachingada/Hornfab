"""Write ``<dataset_root>/MANIFEST.json``: a read-only, deterministic census of the shards.

The manifest is the one file a collaborator can read before downloading 10+ GB: record-schema
version, row totals, every grouping that matters for comparison (objective version x family x
backend x mode, plus typology), the distinct library SHAs, the record time span, and one
sha256 + row count per shard. It is derived data; regenerate it, never hand-edit it.

Read-only over the dataset: only ``shard-*.jsonl`` files are opened (no arrays, no index), and
the only write is the manifest itself. Output is deterministic for a given shard set: every dict
is serialised with sorted keys and every list is sorted.

Usage (from the repo root)::

    .venv\\Scripts\\python.exe -m hornlab_search.dataset.manifest --dataset-root dataset
    .venv\\Scripts\\python.exe -m hornlab_search.dataset.manifest --dataset-root dataset --lab collin

``tools/hf_sync.py pack`` calls :func:`write_manifest` first, so a packed dataset snapshot always
carries a manifest describing exactly the shards in that snapshot.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

from .record import SCHEMA_VERSION, lib_sha_key, typology_name

MANIFEST_VERSION = 1
DEFAULT_LAB = "hunter-4060"
MANIFEST_NAME = "MANIFEST.json"
_SHARD_RE = re.compile(r"^shard-\d+\.jsonl$")

#: One line per objective dispatch version, derived from the comments in
#: ``hornlab_search/objective/versions.py`` (the single source of truth for the supported set).
OBJECTIVE_LEGEND = {
    1: "original objective",
    2: "detrended terms (2026-10-24)",
    3: "per-plane f0_v plus the K-law f0 mask (2026-10-26)",
    4: "tolerance-normalised terms, asymmetric coverage, DI standard deviation, "
       "diagonal term (2026-10-27)",
    5: "MEH system objective: v4 pattern terms on the synthesised response plus lw_resid, "
       "notch, xo_lob and headroom (2026-10-30)",
    6: "loading_smooth (Le Cleac'h / rollback class): load_near, z_smooth, cov_pat, "
       "di_rise (2026-11-05)",
    7: "v4 plus the combined loading-frequency penalty, constant-velocity flatness, the "
       "8 kHz one-sided floor and signed V coverage (2026-10-29; written as 5 on "
       "feat/hardened-plan-2026-10-29, renumbered 2026-11-12)",
}

#: The relabel an older dataset needs before v5 and v7 rows can be compared.
RELABEL_NOTE = "hardened rows dated 2026-10-29 were renumbered 5 -> 7 on 2026-11-12"


def _supported_versions() -> tuple[int, ...]:
    try:
        from ..objective.versions import SUPPORTED_OBJECTIVE_VERSIONS
        return tuple(int(v) for v in SUPPORTED_OBJECTIVE_VERSIONS)
    except Exception:  # noqa: BLE001 - the manifest must stay readable without the package
        return tuple(sorted(OBJECTIVE_LEGEND))


def shard_paths(dataset_root: Path) -> list[Path]:
    """Every ``shard-*.jsonl`` directly under ``dataset_root``, sorted by name."""
    try:
        return sorted(p for p in Path(dataset_root).glob("shard-*.jsonl")
                      if p.is_file() and _SHARD_RE.match(p.name))
    except OSError:
        return []


def _read_shard(path: Path) -> tuple[list[dict], int, str]:
    """Parse one shard. Returns ``(records, malformed_lines, sha256_hex)``.

    A malformed line is counted and skipped, never raised: a manifest of 99 good rows plus one
    torn tail is more useful than no manifest. The sha256 is over the exact file bytes.
    """
    data = path.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    records: list[dict] = []
    malformed = 0
    for line in data.decode("utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError:
            malformed += 1
            continue
        if not isinstance(row, dict):
            malformed += 1
            continue
        records.append(row)
    return records, malformed, sha


def _record_typology(record: dict) -> str:
    value = record.get("typology")
    if value:
        return str(value)
    provenance = record.get("provenance")
    generator = provenance.get("generator") if isinstance(provenance, dict) else None
    family = record.get("family")
    return typology_name(generator, family if isinstance(family, str) else None) or ""


def _objective_version(record: dict) -> int:
    value = record.get("objective_version", 1)
    return value if isinstance(value, int) and not isinstance(value, bool) else 1


def _solve_value(record: dict, key: str) -> str:
    solve = record.get("solve")
    if isinstance(solve, dict) and solve.get(key):
        return str(solve[key])
    return ""


def _composite(parts: list[str]) -> str:
    return "|".join(parts)


def build_manifest(dataset_root: str | Path, *, lab: str = DEFAULT_LAB) -> dict:
    """Build the manifest document for ``dataset_root`` (pure; no writes)."""
    root = Path(dataset_root)
    rows_by_objective: Counter[int] = Counter()
    rows_by_family: Counter[str] = Counter()
    rows_by_backend: Counter[str] = Counter()
    rows_by_mode: Counter[str] = Counter()
    rows_by_typology: Counter[str] = Counter()
    rows_by_lib_sha: Counter[str] = Counter()
    grid_counter: Counter[str] = Counter()
    grid_typology_counter: Counter[str] = Counter()

    shards: list[dict] = []
    created: list[str] = []
    total_rows = 0
    ok_rows = 0
    malformed_total = 0

    for shard in shard_paths(root):
        records, malformed, sha = _read_shard(shard)
        malformed_total += malformed
        shards.append({"name": shard.name, "sha256": sha, "rows": len(records),
                       "malformed_lines": malformed})
        for record in records:
            total_rows += 1
            if record.get("ok"):
                ok_rows += 1
            version = _objective_version(record)
            family = str(record.get("family") or "")
            backend = _solve_value(record, "backend")
            mode = _solve_value(record, "mode")
            typology = _record_typology(record)
            lib_shas = record.get("lib_shas")
            lib_sha = lib_sha_key(lib_shas) if isinstance(lib_shas, dict) else ""

            rows_by_objective[version] += 1
            rows_by_family[family] += 1
            rows_by_backend[backend] += 1
            rows_by_mode[mode] += 1
            rows_by_typology[typology] += 1
            if lib_sha:
                rows_by_lib_sha[lib_sha] += 1
            grid_counter[_composite([str(version), family, backend, mode])] += 1
            grid_typology_counter[_composite([str(version), family, backend, mode, typology])] += 1

            stamp = record.get("created_utc")
            if isinstance(stamp, str) and stamp:
                created.append(stamp)

    versions = _supported_versions()
    legend = {str(v): OBJECTIVE_LEGEND.get(v, "unclassified") for v in versions}

    return {
        "manifest_version": MANIFEST_VERSION,
        "schema_version": SCHEMA_VERSION,
        "lab": str(lab),
        "dataset_root": root.name,
        "total_rows": total_rows,
        "ok_rows": ok_rows,
        "failed_rows": total_rows - ok_rows,
        "malformed_lines": malformed_total,
        "rows_by_objective_version": {str(k): v for k, v in sorted(rows_by_objective.items())},
        "rows_by_family": dict(sorted(rows_by_family.items())),
        "rows_by_backend": dict(sorted(rows_by_backend.items())),
        "rows_by_mode": dict(sorted(rows_by_mode.items())),
        "rows_by_typology": dict(sorted(rows_by_typology.items())),
        "rows_by_objective_version_family_backend_mode": dict(sorted(grid_counter.items())),
        "rows_by_objective_version_family_backend_mode_typology":
            dict(sorted(grid_typology_counter.items())),
        "rows_by_lib_sha": dict(sorted(rows_by_lib_sha.items())),
        "distinct_lib_sha": sorted(rows_by_lib_sha),
        "created_utc_min": min(created) if created else None,
        "created_utc_max": max(created) if created else None,
        "shards": sorted(shards, key=lambda item: item["name"]),
        "objective_versions": legend,
        "relabel_note": RELABEL_NOTE,
    }


def write_manifest(dataset_root: str | Path, *, lab: str = DEFAULT_LAB,
                   out: str | Path | None = None) -> tuple[Path, dict]:
    """Build and write the manifest atomically. Returns ``(path, document)``."""
    root = Path(dataset_root)
    doc = build_manifest(root, lab=lab)
    path = Path(out) if out is not None else root / MANIFEST_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(doc, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="")
    tmp.replace(path)
    return path, doc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m hornlab_search.dataset.manifest",
        description="Write a deterministic MANIFEST.json census of a dataset root (read-only "
                    "over shards).",
    )
    parser.add_argument("--dataset-root", required=True,
                        help="dataset root holding shard-*.jsonl")
    parser.add_argument("--lab", default=DEFAULT_LAB,
                        help=f"lab label written into the manifest (default: {DEFAULT_LAB})")
    parser.add_argument("--out", default=None,
                        help="manifest path (default: <dataset-root>/MANIFEST.json)")
    args = parser.parse_args(argv)
    path, doc = write_manifest(args.dataset_root, lab=args.lab, out=args.out)
    print(f"manifest: {path}")
    print(f"  rows={doc['total_rows']} shards={len(doc['shards'])} lab={doc['lab']} "
          f"versions={sorted(doc['rows_by_objective_version'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
