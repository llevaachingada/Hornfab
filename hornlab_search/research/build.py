"""Build one frozen research snapshot: ``snapshot.json`` plus views rendered from it.

    .venv\\Scripts\\python.exe -m hornlab_search.research build --cutoff 2026-11-25T23:59:59Z

Writes ``runs/analysis/research_<cutoff-date>_<id8>/`` (served by the GUI's existing
``/analysis/<set>/index.html`` route) containing:

``snapshot.json``   the artifact (sorted keys; byte-identical for identical inputs)
``manifest.json``   sources with sha256/origin, cutoff, exclusions, snapshot id
``rows.ndjson``     one evidence row per line (agents)
``findings.ndjson`` one finding per line (agents)
``index.html``      the human view; embeds the exact ``snapshot.json`` bytes, computes nothing new

Read-only over the repository: no solver, no GPU, no write outside ``--out``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from . import findings as F
from . import sources as S
from .provenance import GENERATOR, Registry, iso, parse_utc

SCHEMA = "hornfab-research-snapshot-m1"
TEMPLATE = Path(__file__).with_name("template.html")
DEFAULT_CUTOFF = "2026-11-25T23:59:59Z"


def _dumps(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, indent=1, ensure_ascii=False, allow_nan=False) + "\n"


def resolve_commit(root: Path, ref: str = "HEAD") -> str:
    r = subprocess.run(["git", "rev-parse", ref], cwd=root, capture_output=True, text=True, check=True)
    return r.stdout.strip()


def _walk_status(obj: Any, path: str, out: list) -> None:
    if isinstance(obj, dict):
        st = obj.get("status")
        if st in ("missing", "unknown", "run_dir_missing") and ("v" in obj or "reason" in obj or st == "run_dir_missing"):
            out.append({"path": path, "status": st, "reason": obj.get("reason"), "src": obj.get("src")})
        for k, v in obj.items():
            _walk_status(v, f"{path}/{k}", out)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _walk_status(v, f"{path}/{i}", out)


def build_snapshot(root: Path, cutoff: str = DEFAULT_CUTOFF, commit: str | None = None) -> dict:
    root = Path(root)
    cut = parse_utc(cutoff)
    if cut is None:
        raise ValueError(f"bad cutoff {cutoff!r}")
    sha = commit or resolve_commit(root)
    reg = Registry(root, sha)

    dose = S.dose_experiment(reg, cut)
    inv = S.cohort_inventory(reg, cut)
    claims = S.handoff_claims(reg)
    recon = S.reconcile_claims(claims, inv)
    mesh = S.mesh_fidelity(reg)
    can = S.canary(reg, cut)

    finds = F.dose_findings(dose) + F.cohort_findings(inv, recon) + F.mesh_findings(mesh) \
        + F.canary_findings(can)
    order = {"decision": 0, "data_quality": 1, "control": 2, "info": 3}
    kinds = {"matched_pair": 0, "count_not_admission": 1, "mesh_scope": 2, "scalar_not_gate": 3}
    finds.sort(key=lambda f: (order.get(f["severity"], 9), kinds.get(f["kind"], 9), f["kind"], f["id"]))

    sources = [reg.sources[k] for k in sorted(reg.sources)]
    # Identity = what was USED: append-only counters (lines after the cutoff) stay in the manifest
    # but not in the id, so a night appending after the cutoff does not change the snapshot.
    volatile = ("lines_total", "lines_after_cutoff", "lines_unparseable")
    ident = {"schema": SCHEMA, "generator": GENERATOR, "cutoff_utc": iso(cut), "source_commit": sha,
             "sources": [{k: v for k, v in s.items() if k not in volatile} for s in sources]}
    snap_id = hashlib.sha256(_dumps(ident).encode()).hexdigest()[:16]
    manifest = dict(ident, sources=sources, snapshot_id=snap_id,
                    exclusions=sorted(reg.exclusions, key=lambda e: (e["what"], e["reason"])),
                    worktree_differs=[s["path"] for s in sources if s.get("worktree") == "differs"],
                    worktree_eol_only=[s["path"] for s in sources if s.get("worktree") == "eol_only"],
                    n_sources=len(sources),
                    reads="committed files via `git show <source_commit>:<path>`; runs/ from disk, "
                          "append-only logs pinned on the lines at or before the cutoff")
    snap = {"schema": SCHEMA, "generator": GENERATOR, "snapshot_id": snap_id, "cutoff_utc": iso(cut),
            "source_commit": sha,
            "scope": ("Read-only research view over committed 2026-11-21..25 evidence and the local run "
                      "archive at the cutoff. Simulated BEM results, not physical measurements. Never "
                      "compares J across score identities. No GPU authorization, no dispatch."),
            "dose": dose, "inventory": inv, "claims": claims, "reconciliation": recon,
            "mesh": mesh, "canary": can, "findings": finds, "manifest": manifest}
    gaps: list = []
    _walk_status({k: snap[k] for k in ("dose", "inventory", "mesh", "canary")}, "", gaps)
    snap["missing_evidence"] = {
        "cells": gaps,
        "unmeasured": list(mesh.get("unmeasured", [])) + [
            "physical-driver measurements: none in scope (all values are simulated BEM)",
            "GPU telemetry for the cohort inventory rows: not read in M1 (peak_vram_mb exists per row, unaggregated)"],
        "sources_missing": [s["path"] for s in sources if s.get("status") in ("missing", "unreadable")],
    }
    return snap


def _rows(snap: dict) -> list[dict]:
    out = []
    for r in snap["dose"]["rows"]:
        out.append({"section": "dose", **r})
    for c in snap["inventory"]["cohorts"]:
        out.append({"section": "cohort", **c})
    for r in snap["reconciliation"]:
        out.append({"section": "reconciliation", "id": f"recon:{r['config_name']}", **r})
    for r in snap["mesh"].get("rows", []):
        out.append({"section": "mesh", **r})
    can = snap["canary"]
    if can.get("status") == "ok":
        for p in can["verify_pairs"]:
            out.append({"section": "canary", "id": f"canary:{p['design']}", **p})
        for r in can["replicates"]:
            out.append({"section": "canary_replicate", "id": f"canary:{r['mode']}:{r['design']}", **r})
    return out


def render_html(snapshot_text: str) -> str:
    tpl = TEMPLATE.read_text(encoding="utf-8")
    embedded = snapshot_text.replace("</", "<\\/")
    return tpl.replace("/*__SNAPSHOT_JSON__*/null", embedded)


def write_snapshot(snap: dict, out: Path) -> dict:
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    text = _dumps(snap)
    files = {
        "snapshot.json": text,
        "manifest.json": _dumps(snap["manifest"]),
        "rows.ndjson": "".join(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n" for r in _rows(snap)),
        "findings.ndjson": "".join(json.dumps(f, sort_keys=True, ensure_ascii=False) + "\n"
                                   for f in snap["findings"]),
        "index.html": render_html(text),
    }
    digests = {}
    for name, body in files.items():
        data = body.encode("utf-8")
        (out / name).write_bytes(data)
        digests[name] = hashlib.sha256(data).hexdigest()
    return digests


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m hornlab_search.research")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="build one frozen research snapshot")
    b.add_argument("--root", default=".")
    b.add_argument("--cutoff", default=DEFAULT_CUTOFF)
    b.add_argument("--commit", default="HEAD", help="git ref the committed sources are read from")
    b.add_argument("--out", default=None, help="default runs/analysis/research_<date>_<id8>")
    a = ap.parse_args(argv)
    root = Path(a.root).resolve()
    snap = build_snapshot(root, a.cutoff, resolve_commit(root, a.commit))
    out = Path(a.out) if a.out else root / "runs" / "analysis" / \
        f"research_{snap['cutoff_utc'][:10]}_{snap['snapshot_id'][:8]}"
    digests = write_snapshot(snap, out)
    print(f"snapshot {snap['snapshot_id']} cutoff {snap['cutoff_utc']} commit {snap['source_commit'][:12]}")
    print(f"out {out}")
    print(f"sources {snap['manifest']['n_sources']} exclusions {len(snap['manifest']['exclusions'])} "
          f"findings {len(snap['findings'])} missing-cells {len(snap['missing_evidence']['cells'])}")
    for k, v in digests.items():
        print(f"  {k:16s} sha256 {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
