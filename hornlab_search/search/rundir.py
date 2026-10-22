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


def package_source_fingerprint(module_name: str) -> dict:
    """Content identity of an installed package's source files (idea after Boundary Lab's BEAT run
    provenance): sha256 over sorted records ``relative/path NUL file_sha256 NEWLINE`` of every
    ``.py``/``.jl``/``.toml``/``.json`` file under the package directory. Distinguishes modified
    trees that share a git commit (hornlab-beat-bem vendors a patched engine). Best effort:
    ``{"module", "sha256", "n_files"}`` or ``{"module", "error"}``; never raises."""
    import importlib.util
    try:
        spec = importlib.util.find_spec(module_name)
        if spec is None or not spec.submodule_search_locations:
            return {"module": module_name, "error": "not installed"}
        root = Path(list(spec.submodule_search_locations)[0])
        files = sorted(p for p in root.rglob("*")
                       if p.is_file() and p.suffix in (".py", ".jl", ".toml", ".json")
                       and "__pycache__" not in p.parts)
        h = hashlib.sha256()
        for p in files:
            rel = p.relative_to(root).as_posix()
            h.update(f"{rel}\0{hashlib.sha256(p.read_bytes()).hexdigest()}\n".encode())
        return {"module": module_name, "sha256": h.hexdigest(), "n_files": len(files)}
    except Exception as exc:  # noqa: BLE001 - provenance is best effort
        return {"module": module_name, "error": f"{type(exc).__name__}: {exc}"}


def _run_quiet(cmd: list[str], timeout: float = 10.0) -> str | None:
    import subprocess
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else None
    except Exception:  # noqa: BLE001 - provenance is best effort
        return None


def runtime_provenance() -> dict:
    """What this run ACTUALLY ran on, queried live at start (``toolchain_snapshot`` only copies
    TOOLCHAIN.md text). GPU via ``nvidia-smi`` (name, driver, total memory; a read-only query),
    Julia version, Python, platform, and source fingerprints of the solver and mesher packages.
    Every field is best effort and may be None; never raises."""
    import platform
    import shutil
    import sys
    gpu = _run_quiet(["nvidia-smi", "--query-gpu=name,driver_version,memory.total",
                      "--format=csv,noheader"]) if shutil.which("nvidia-smi") else None
    julia = _run_quiet(["julia", "--version"]) if shutil.which("julia") else None
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "gpu": gpu.splitlines() if gpu else None,
        "julia": julia,
        "sources": [package_source_fingerprint(m) for m in
                    ("hornlab_beat_bem", "hornlab_mesher", "hornlab_bempp_bem")],
    }


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
