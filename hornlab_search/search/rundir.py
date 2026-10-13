"""Run-directory helpers (01_CONTRACTS section 14), shared by ``run``, ``search`` and ``verify``.

    runs/<UTC timestamp>-<mode>-<short id>/
      run.json  config.yaml  search.ndjson  best.json  designs/<design_hash>/...  cma/  report.html
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

import yaml

from ..dataset.record import to_jsonable

REPO = Path(__file__).resolve().parents[2]
TOOLCHAIN_MD = REPO / "TOOLCHAIN.md"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_run_dir(runs_root: Path, mode: str) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    d = Path(runs_root) / f"{stamp}-{mode}-{uuid.uuid4().hex[:6]}"
    d.mkdir(parents=True, exist_ok=False)
    return d


def latest_run(runs_root: Path) -> Path | None:
    runs = sorted(p for p in Path(runs_root).glob("*") if p.is_dir() and (p / "run.json").exists())
    return runs[-1] if runs else None


def config_sha(raw: dict) -> str:
    blob = json.dumps(to_jsonable(raw), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()[:12]


def write_config_snapshot(run_dir: Path, cfg) -> Path:
    """The effective config (after any ``--backend`` override) as YAML, loadable by load_config."""
    raw = json.loads(json.dumps(to_jsonable(cfg.raw)))
    raw.setdefault("solve", {})["backend"] = cfg.solve.backend
    p = Path(run_dir) / "config.yaml"
    p.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return p


def toolchain_snapshot() -> dict:
    """The machine lines of TOOLCHAIN.md plus its hash, so a run records what it ran on."""
    snap: dict = {"present": TOOLCHAIN_MD.exists()}
    if not TOOLCHAIN_MD.exists():
        return snap
    text = TOOLCHAIN_MD.read_text(encoding="utf-8", errors="replace")
    snap["sha256"] = hashlib.sha256(text.encode()).hexdigest()[:16]
    for label, pat in (("os", r"^- OS:\s*(.+)$"), ("cpu", r"^- CPU:\s*(.+)$"),
                       ("ram", r"^- RAM:\s*(.+)$"), ("gpu", r"^- GPU:\s*(.+?)(?:\s+\*\*|$)"),
                       ("driver", r"^- NVIDIA driver:\s*(.+)$"), ("python", r"^- Python:\s*(.+)$"),
                       ("beat_status", r"^- `beat_engine_status\(\)`:\s*(.+)$")):
        m = re.search(pat, text, re.M)
        if m:
            snap[label] = m.group(1).strip()
    return snap


def read_json(path: Path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def write_json_atomic(path: Path, obj) -> None:
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(to_jsonable(obj), f, indent=1, sort_keys=True)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def update_run_json(run_dir: Path, **fields) -> dict:
    p = Path(run_dir) / "run.json"
    cur = read_json(p, {}) or {}
    cur.update(fields)
    write_json_atomic(p, cur)
    return cur


def write_best(run_dir: Path, ev, mode: str, eval_no: int | None) -> None:
    write_json_atomic(Path(run_dir) / "best.json", {
        "design_hash": ev.design_hash, "family": ev.design.family, "params": ev.design.params,
        "objective": ev.objective, "terms": ev.terms, "ok": not ev.error, "mode": mode,
        "eval_no": eval_no, "written_utc": utc_now(),
        "di_source": None if ev.metrics is None else ev.metrics.di_source})
