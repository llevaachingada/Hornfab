"""Bounded, read-only offline re-scoring pilot (R0 / M0).

Purpose
-------
Exercise the canonical replay adapter (``hornlab_search.objective.replay``) against the real
archive **without touching a solver, GPU, mesh, dataset writer or live queue**. The dataset is
read with plain ``json``/``numpy`` file reads, never through ``DatasetStore`` (whose open path may
repair/truncate a torn tail). Output is written only under ``--out``.

Hard guarantees enforced by this tool
-------------------------------------
* **Zero backend calls.** Every solver/backend factory and store writer is monkeypatched to raise
  and count; a *single* guarded call fails the run. The JSON reports ``backend_guard.calls``.
* **No source mutation.** The dataset/brief/run/cache roots are hashed before and after the run;
  a mismatch is a hard failure (nonzero exit).
* **No Store recovery.** Rows are read line-by-line from ``shard-*.jsonl`` plus their ``.npz``;
  no ``DatasetStore`` is constructed.

Outputs
-------
``offline_scores.json`` and ``offline_scores.md`` with:
ATH-compatible counts, original-replay parity deltas, weight/tolerance/target variant deltas,
identity-hash counts, unsupported reasons, the three-identity preservation inventory, and the
legacy surrogate capability matrix.

If the archive has no rows for the candidate ATH task, the result is ``insufficient_evidence``
with honest counts; no other task is substituted.

Usage::

    .venv\\Scripts\\python.exe tools/analysis/offline_scores.py \\
        --dataset dataset --out scratch/bo_m0/r0/offline_scores

No commit, no upload, no writes outside ``--out``.
"""
from __future__ import annotations

import argparse
import csv
import dataclasses
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import unittest.mock as mock
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from hornlab_search.objective import replay  # noqa: E402
from hornlab_search.targets.spec import Target  # noqa: E402

TOOL = "offline_scores"
DEFAULT_BRIEF = (REPO_ROOT / "examples" / "briefs" / "campaign_2026-10-26_v4"
                 / "native_ath_core_2in_v4.yaml")
DEFAULT_OUT = REPO_ROOT / "scratch" / "bo_m0" / "r0" / "offline_scores"

#: The candidate task's target fields (parent resume brief). Compatibility is checked, never
#: assumed: the ATH cohort may genuinely be absent from this archive.
ATH_TARGET = {
    "coverage_h_deg": 50.0,
    "coverage_v_deg": 50.0,
    "band_lo_hz": 300.0,
    "band_hi_hz": 8000.0,
    "f0_hz": 1280.0,
    "z_min": 0.0,
    "di_slope_target": 0.0,
    "di_target_db": None,
}
ATH_FREQ_WEIGHTS = ((2500.0, 5500.0, 2.0),)

#: Single-task cohort filter (parent M0 freeze): the candidate task is this one config; the
#: other three families that share the brief are descriptive only and are never pooled.
NATIVE_CONFIG = "native__ath_core_v4"


def load_catalog_index(catalog_csv) -> dict:
    """Map ``(root, shard, row) -> catalog row`` from the S0 catalog export.

    Used to recover ``config_name``/``brief``/``run_id`` provenance the raw dataset records do
    not carry. Rows whose ``root`` matches the scanned dataset basename join; everything else is
    ignored (dataset_cpu etc. are separate physical roots)."""
    out: dict = {}
    with open(catalog_csv, encoding="utf-8", newline="") as fh:
        for rec in csv.DictReader(fh):
            # Two catalog export generations exist: ``shard`` numeric (v1) vs ``shard`` filename
            # with a numeric ``shard_index`` (v2). Key on the numeric shard id whichever column
            # carries it, so both exports join.
            shard_num = str(rec.get("shard_index") or "") or str(rec.get("shard") or "")
            key = (str(rec.get("root") or ""), shard_num, str(rec.get("row") or ""))
            out[key] = rec
    return out

#: Variant weights/tolerances chosen once, deterministically, for the pilot.
WEIGHT_VARIANT = {"di": 0.6}
TOLERANCE_VARIANT = {"cov": 3.0}


# ------------------------------------------------------------------ small helpers

def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _clean(obj):
    """JSON-safe copy: non-finite floats -> None, numpy scalars -> Python."""
    if isinstance(obj, dict):
        return {str(k): _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (float, np.floating)):
        return float(obj) if math.isfinite(float(obj)) else None
    if isinstance(obj, Path):
        return str(obj)
    return obj


def _sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            b = fh.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def hash_tree(root, *, max_files: int = 512) -> dict:
    """Counts/bytes for the whole tree + checksums for the first ``max_files`` files."""
    root = Path(root)
    if not root.exists():
        return {"root": str(root), "exists": False, "n_files": 0, "n_bytes": 0,
                "checksums": {}, "truncated": False}
    files: list[Path] = []
    total = 0
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            p = Path(dirpath) / name
            try:
                total += p.stat().st_size
                files.append(p)
            except OSError:
                continue
    files.sort(key=lambda p: str(p))
    checksums = {}
    for p in files[:max_files]:
        try:
            checksums[str(p.relative_to(root))] = _sha256_file(p)
        except OSError as exc:  # a file disappearing mid-read is a real change
            checksums[str(p.relative_to(root))] = f"ERROR:{type(exc).__name__}"
    return {
        "root": str(root),
        "exists": True,
        "n_files": len(files),
        "n_bytes": int(total),
        "checksums": checksums,
        "truncated": len(files) > max_files,
    }


def _trace_check(dataset_root: Path) -> dict:
    """Bounded required-traces check: count + one loadable sample (read-only)."""
    root = Path(dataset_root) / "traces"
    if not root.is_dir():
        return {"exists": False, "n_files": 0, "sample": None, "loadable": None}
    files = sorted(root.glob("*.npz"))
    sample = None
    loadable = None
    if files:
        p = files[0]
        sample = str(p.relative_to(dataset_root))
        try:
            with np.load(p, allow_pickle=False) as z:
                loadable = bool(list(z.files))
        except Exception:  # noqa: BLE001
            loadable = False
    return {"exists": True, "n_files": len(files), "sample": sample, "loadable": loadable}


def _runs_provenance(runs_root: Path) -> dict:
    """Bounded run/config/provenance counts (top-level run dirs only)."""
    root = Path(runs_root)
    if not root.is_dir():
        return {"exists": False, "n_runs": 0}
    run_dirs = sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith("."))
    n_config = n_run_json = n_search = n_designs = n_response = n_metrics = 0
    for d in run_dirs:
        n_config += int((d / "config.yaml").is_file())
        n_run_json += int((d / "run.json").is_file())
        n_search += int((d / "search.ndjson").is_file())
        designs = d / "designs"
        if designs.is_dir():
            for dd in designs.iterdir():
                if dd.is_dir():
                    n_designs += 1
                    n_response += int((dd / "response.npz").is_file())
                    n_metrics += int((dd / "metrics.json").is_file())
    return {
        "exists": True, "n_runs": len(run_dirs), "n_config": n_config,
        "n_run_json": n_run_json, "n_search_ndjson": n_search,
        "n_design_dirs": n_designs, "n_response_npz": n_response,
        "n_metrics_json": n_metrics,
    }


def preservation_inventory(roots: dict, *, max_files: int = 128) -> dict:
    """Counts/bytes/checksums for the data roots named by the parent contract."""
    out = {}
    for name, path in roots.items():
        inv = hash_tree(path, max_files=max_files)
        out[name] = inv
    ds = roots.get("dataset")
    out["traces"] = _trace_check(Path(ds)) if ds is not None else {
        "exists": False, "n_files": 0, "sample": None, "loadable": None}
    out["run_provenance"] = _runs_provenance(Path(roots["runs"])) if "runs" in roots else {
        "exists": False, "n_runs": 0}
    out["checksum_limit"] = int(max_files)
    return out


# ------------------------------------------------------------------ read-only dataset walk

def _shard_files(dataset_root: Path) -> list[tuple[int, Path]]:
    out = []
    for p in sorted(Path(dataset_root).glob("shard-*.jsonl")):
        try:
            out.append((int(p.stem.split("-")[1]), p))
        except (IndexError, ValueError):
            continue
    return out


def iter_dataset_rows(dataset_root, *, with_arrays: bool = False, shard: int | None = None):
    """Yield ``(shard, row, meta, arrays_or_None)`` read-only.

    Never constructs ``DatasetStore`` and never repairs/truncates anything. A torn/corrupt line is
    skipped; a corrupt ``.npz`` yields ``arrays=None``.
    """
    for shard_i, shard_path in _shard_files(Path(dataset_root)):
        if shard is not None and shard_i != shard:
            continue
        with open(shard_path, "r", encoding="utf-8") as fh:
            for row, line in enumerate(fh):
                line = line.strip()
                if not line:
                    continue
                try:
                    meta = json.loads(line)
                except ValueError:
                    continue
                arrays = None
                if with_arrays:
                    p = Path(dataset_root) / f"shard-{shard_i:04d}" / f"rec-{row:04d}.npz"
                    if p.is_file():
                        try:
                            with np.load(p, allow_pickle=False) as z:
                                arrays = {k: z[k] for k in z.files}
                        except Exception:  # noqa: BLE001 - corrupt file is a skip
                            arrays = None
                yield shard_i, row, meta, arrays


def _fw_signature(freq_weights) -> tuple | None:
    if not isinstance(freq_weights, dict):
        return None
    bands = freq_weights.get("band_hz")
    if not isinstance(bands, (list, tuple)):
        return None
    try:
        return tuple(sorted((float(row[0]), float(row[1]), float(row[2])) for row in bands))
    except (TypeError, ValueError, IndexError):
        return None


def ath_compatibility(target: dict | None) -> dict:
    """``core`` (coverage/band/f0) and ``full`` (also z_min/slope/weights) compatibility."""
    if not isinstance(target, dict):
        return {"core": False, "full": False}
    core = True
    for key, want in (("coverage_h_deg", ATH_TARGET["coverage_h_deg"]),
                      ("coverage_v_deg", ATH_TARGET["coverage_v_deg"]),
                      ("band_lo_hz", ATH_TARGET["band_lo_hz"]),
                      ("band_hi_hz", ATH_TARGET["band_hi_hz"]),
                      ("f0_hz", ATH_TARGET["f0_hz"])):
        try:
            if abs(float(target.get(key)) - float(want)) > 1e-9:
                core = False
                break
        except (TypeError, ValueError):
            core = False
            break
    full = core
    if full:
        try:
            if target.get("di_target_db") is not None:
                full = False
            if abs(float(target.get("z_min", 0.0)) - ATH_TARGET["z_min"]) > 1e-12:
                full = False
            if abs(float(target.get("di_slope_target", 0.0))
                   - ATH_TARGET["di_slope_target"]) > 1e-12:
                full = False
        except (TypeError, ValueError):
            full = False
    if full and target.get("freq_weights") is not None:
        full = _fw_signature(target.get("freq_weights")) == ATH_FREQ_WEIGHTS
    return {"core": bool(core), "full": bool(full)}


def scan_dataset(dataset_root, *, max_candidates: int = 10_000,
                 catalog_index: dict | None = None,
                 config_filter: str | None = None) -> dict:
    """Metadata-only scan: honest counts + the ATH-full candidate list (bounded).

    ``catalog_index`` (the S0 export) supplies ``config_name``/``run_id`` provenance the dataset
    records do not carry; ``config_filter`` restricts the candidate list to one recorded config
    (the single-task cohort) and never invents a config for an unknown row."""
    dataset_name = Path(dataset_root).name
    counters = {
        "rows_seen": 0, "rows_ok": 0, "rows_failed": 0, "rows_with_npz": 0,
        "rows_with_traces": 0,
        "ath_core": 0, "ath_full": 0, "ath_full_ok_with_npz": 0,
        "ath_full_stored_versions": {},
        "rows_native": 0,
        "ath_full_native": 0,
        "ath_full_native_ok_with_npz": 0,
        "config_unknown": 0,
    }
    candidates: list[tuple[int, int, dict]] = []
    for shard, row, meta, _arrays in iter_dataset_rows(dataset_root):
        counters["rows_seen"] += 1
        meta = dict(meta)
        if catalog_index is not None:
            rec = catalog_index.get((dataset_name, str(shard), str(row)))
            if rec is None:
                counters["config_unknown"] += 1
            else:
                meta["config_name"] = rec.get("config_name") or ""
                meta["catalog_run_id"] = rec.get("run_id") or ""
                meta["catalog_brief"] = rec.get("brief") or ""
        is_native = catalog_index is not None and meta.get("config_name") == NATIVE_CONFIG
        if catalog_index is not None and is_native:
            counters["rows_native"] += 1
        ok = bool(meta.get("ok"))
        counters["rows_ok" if ok else "rows_failed"] += 1
        if (meta.get("traces") or {}).get("captured"):
            counters["rows_with_traces"] += 1
        npz = Path(dataset_root) / f"shard-{shard:04d}" / f"rec-{row:04d}.npz"
        if npz.is_file():
            counters["rows_with_npz"] += 1
        compat = ath_compatibility(meta.get("target"))
        if compat["core"]:
            counters["ath_core"] += 1
        if compat["full"]:
            counters["ath_full"] += 1
            if ok and npz.is_file():
                counters["ath_full_ok_with_npz"] += 1
                ver = str(meta.get("objective_version", 1))
                counters["ath_full_stored_versions"][ver] = \
                    counters["ath_full_stored_versions"].get(ver, 0) + 1
                if is_native:
                    counters["ath_full_native"] += 1
                    counters["ath_full_native_ok_with_npz"] += 1
                if config_filter is not None and meta.get("config_name") != config_filter:
                    continue
                if len(candidates) < max_candidates:
                    candidates.append((shard, row, meta))
    return {"counters": counters, "candidates": candidates}


# ------------------------------------------------------------------ bounded restore helper

def copy_dataset_sample(src_root, dst_root, *, shard: int = 0, max_rows: int = 8) -> dict:
    """Copy a bounded, self-consistent sample of one shard into ``dst_root`` (temp-root test)."""
    src_root, dst_root = Path(src_root), Path(dst_root)
    src_jsonl = src_root / f"shard-{shard:04d}.jsonl"
    if not src_jsonl.is_file():
        raise FileNotFoundError(f"copy_dataset_sample: {src_jsonl} is missing")
    lines = src_jsonl.read_text(encoding="utf-8").splitlines()
    keep = lines[:max_rows]
    dst_root.mkdir(parents=True, exist_ok=True)
    dst_shard = dst_root / f"shard-{shard:04d}"
    dst_shard.mkdir(parents=True, exist_ok=True)
    (dst_root / f"shard-{shard:04d}.jsonl").write_text("\n".join(keep) + "\n", encoding="utf-8")
    copied = []
    for i in range(len(keep)):
        p = src_root / f"shard-{shard:04d}" / f"rec-{i:04d}.npz"
        if p.is_file():
            shutil.copy2(p, dst_shard / p.name)
            copied.append(i)
    return {"shard": shard, "rows": len(keep), "npz_copied": copied}


# ------------------------------------------------------------------ zero-backend guard

class BackendGuard:
    """Patch every solver/backend factory and store writer so any call raises and is counted."""

    _PATCHES = (
        ("hornlab_search.solve.base", "get_backend", "backend.get_backend"),
        ("hornlab_search.solve.beat", "BeatBackend", "backend.BeatBackend"),
        ("hornlab_search.solve.bempp", "BemppBackend", "backend.BemppBackend"),
        ("hornlab_search.solve.worker", "start_beat_worker", "worker.start_beat_worker"),
        ("hornlab_search.solve.worker", "warm", "worker.warm"),
        ("hornlab_search.solve.worker", "recover_after_failure", "worker.recover_after_failure"),
        ("hornlab_search.solve.cache", "store", "cache.store"),
        ("hornlab_search.dataset.store", "DatasetStore.append", "DatasetStore.append"),
        ("subprocess", "run", "subprocess.run"),
        ("subprocess", "Popen", "subprocess.Popen"),
        ("os", "system", "os.system"),
    )

    def __init__(self):
        self.calls = 0
        self.names: list[str] = []
        self.installed: list[str] = []
        self._stack = None

    def _forbidden(self, name: str):
        def _raise(*_args, **_kwargs):
            self.calls += 1
            self.names.append(name)
            raise RuntimeError(f"offline_scores: forbidden backend/store call: {name}")
        return _raise

    def __enter__(self):
        import importlib
        self._stack = []
        for module_name, attr, label in self._PATCHES:
            try:
                mod = importlib.import_module(module_name)
            except Exception:  # noqa: BLE001 - optional modules may be absent
                continue
            if "." in attr:
                owner_name, leaf = attr.split(".", 1)
                owner = getattr(mod, owner_name, None)
                if owner is None or not hasattr(owner, leaf):
                    continue
                patcher = mock.patch.object(owner, leaf, self._forbidden(label))
            else:
                if not hasattr(mod, attr):
                    continue
                patcher = mock.patch.object(mod, attr, self._forbidden(label))
            patcher.start()
            self._stack.append(patcher)
            self.installed.append(label)
        return self

    def __exit__(self, exc_type, exc, tb):
        for patcher in reversed(self._stack or []):
            patcher.stop()
        return False


# ------------------------------------------------------------------ surrogate audit (source-level)

def legacy_surrogate_audit(repo_root=REPO_ROOT) -> dict:
    """Exact source refs for the legacy surrogate's objective/input capability gap.

    Audit only: nothing is changed. The legacy surrogate (``surrogate/predict.py``,
    ``train.py``) calls ``objective.scalar`` (v1) and builds a ``MetricSet`` without predicted
    throat impedance/balloon/MEH inputs. It therefore cannot claim modern-score compatibility.
    """
    repo_root = Path(repo_root)
    files = {
        "predict": repo_root / "hornlab_search" / "surrogate" / "predict.py",
        "train": repo_root / "hornlab_search" / "surrogate" / "train.py",
        "model": repo_root / "hornlab_search" / "surrogate" / "model.py",
        "round": repo_root / "hornlab_search" / "surrogate" / "round.py",
    }
    evidence = []

    def scan(name: str, needles: tuple[str, ...], capability: str) -> None:
        p = files[name]
        if not p.is_file():
            return
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), start=1):
            s = line.strip()
            if any(n in s for n in needles):
                evidence.append({"file": str(p.relative_to(repo_root)).replace("\\", "/"),
                                 "line": i, "code": s, "capability": capability})

    scan("predict", ("from ..objective.scalar import",), "objective=scalar v1 import")
    scan("train", ("from ..objective.scalar import",), "objective=scalar v1 import")
    scan("predict", ("objective(self.metric_set", "objective(m, True"), "score=scalar v1 call")
    scan("train", ("objective(m, True", "pred_obj = sur.objective"), "score=scalar v1 call")
    scan("predict", ("def metric_set", "MetricSet(", "z_throat_real=None"),
         "MetricSet without predicted impedance")
    scan("train", ("MetricSet(", "z_throat_real"), "MetricSet impedance only if training arrays have it")
    scan("predict", ("def config_mismatch", "bounds = self.meta.get",
                     "exp_freqs = self.meta.get"),
         "guard checks bundle config geometry/grid only")
    scan("model", ("gate_report",), "guard checks bundle gate_report only")
    scan("round", ("gate_report",), "guard checks bundle gate_report only")

    return {
        "audit_only": True,
        "preserved_legacy_semantics": True,
        "objective_versions_supported": [1],
        "objective": "objective.scalar (v1): raw six terms; no tolerance normalisation, "
                     "distd/diag, v4 response ripple, loading/flat_cv/8k-floor or MEH terms",
        "predicted_impedance": False,
        "predicted_balloon": False,
        "predicted_meh_channels": False,
        "predicted_response_arrays": False,
        "gate_inputs": "bundle config geometry/grid + gate_report only; no per-row "
                       "objective-version/input contract",
        "adapter": "none; direct objective.scalar (v1) call on predicted metric curves",
        "refusal_gap": [
            "cannot claim objective v4+ compatibility (weights/tolerances/diag/distd/ripple)",
            "cannot predict or gate on throat impedance (z_throat_real=None)",
            "cannot predict balloon/MEH channel or impedance-matrix inputs",
            "a modern score table must use replay.py (canonical) or an explicit version-aware "
            "adapter; never fabricate the missing inputs",
        ],
        "evidence": evidence,
    }


# ------------------------------------------------------------------ replay variants

def _stored_j(meta: dict) -> float | None:
    raw = meta.get("objective")
    if isinstance(raw, (int, float)) and not isinstance(raw, bool) and math.isfinite(float(raw)):
        return float(raw)
    return None


def _variant_weights(weights: dict, delta: dict) -> dict:
    out = dict(weights)
    for k, v in delta.items():
        out[k] = float(v)
    return out


def _variant_block(block: dict | None, tolerance_delta: dict) -> dict:
    out = dict(block or {})
    tol = dict(out.get("tolerances") or {})
    for k, v in tolerance_delta.items():
        tol[k] = float(v)
    out["tolerances"] = tol
    out.setdefault("version", 4)
    return out


def _status_bucket(results: list) -> dict:
    out: dict[str, int] = {}
    for r in results:
        out[r.status] = out.get(r.status, 0) + 1
    return out


def _reason_bucket(results: list) -> dict:
    out: dict[str, int] = {}
    for r in results:
        for reason in r.reasons:
            key = reason.split(":", 1)[0]
            out[key] = out.get(key, 0) + 1
    return dict(sorted(out.items()))


def replay_candidates(candidates, *,
                      dataset_root, brief, limit: int) -> dict:
    """Replay original + variants for the bounded candidate list."""
    original, weight_var, tol_var, target_var = [], [], [], []
    for shard, row, meta in candidates[:limit]:
        npz = Path(dataset_root) / f"shard-{shard:04d}" / f"rec-{row:04d}.npz"
        if not npz.is_file():
            continue
        try:
            with np.load(npz, allow_pickle=False) as z:
                arrays = {k: z[k] for k in z.files}
        except Exception:  # noqa: BLE001
            continue

        r0 = replay.replay_record(meta, arrays, brief=brief)
        original.append((shard, row, r0))

        rw = replay.replay_record(meta, arrays, brief=brief,
                                  weights=_variant_weights(brief.weights, WEIGHT_VARIANT))
        weight_var.append((shard, row, r0, rw))

        rb = replay.replay_record(
            meta, arrays, brief=brief,
            objective_params=_variant_block(brief.objective_block, TOLERANCE_VARIANT))
        tol_var.append((shard, row, r0, rb))

        if r0.diagnostics.get("stored_target_verified") and brief.target is not None:
            t2 = dataclasses.replace(
                brief.target,
                coverage_h_deg=60.0,
                coverage_v_deg=45.0,
                band_hi_hz=min(6000.0, float(brief.target.band_hi_hz)),
            )
            rt = replay.replay_record(meta, arrays, brief=brief, target=t2)
            target_var.append((shard, row, r0, rt))

    return {"original": original, "weight": weight_var, "tolerance": tol_var,
            "target": target_var}


def _parity_block(rows) -> dict:
    deltas = []
    compared = 0
    for _s, _r, res in rows:
        if res.parity_delta is not None and res.stored_j is not None and res.j is not None:
            compared += 1
            deltas.append(abs(float(res.parity_delta)))
    if not deltas:
        return {"n": len(rows), "n_compared": 0, "max_abs_delta": None,
                "median_abs_delta": None, "within_1e-6": 0}
    arr = np.asarray(deltas, dtype=float)
    return {
        "n": len(rows),
        "n_compared": compared,
        "max_abs_delta": float(arr.max()),
        "median_abs_delta": float(np.median(arr)),
        "within_1e-6": int(np.sum(arr <= 1e-6)),
    }


def _identity_block(rows) -> dict:
    physical = {res.physical_id for _s, _r, res in rows}
    metric = {res.metric_id for _s, _r, res in rows}
    score = {res.score_id for _s, _r, res in rows}
    return {"n_rows": len(rows), "n_unique_physical": len(physical),
            "n_unique_metric": len(metric), "n_unique_score": len(score),
            "sample": [{"design_hash": res.design_hash, "physical_id": res.physical_id,
                        "metric_id": res.metric_id, "score_id": res.score_id,
                        "status": res.status} for _s, _r, res in rows[:5]]}


def _change_block(rows, *, expect_physical_same: bool) -> dict:
    n = 0
    physical_same = 0
    metric_changed = 0
    score_changed = 0
    j_changed = 0
    statuses = []
    reason_counts: dict[str, int] = {}
    for _s, _r, base, var in rows:
        n += 1
        physical_same += int(var.physical_id == base.physical_id)
        metric_changed += int(var.metric_id != base.metric_id)
        score_changed += int(var.score_id != base.score_id)
        if base.j is not None and var.j is not None and abs(var.j - base.j) > 1e-12:
            j_changed += 1
        statuses.append(var)
        for reason in var.reasons:
            key = reason.split(":", 1)[0]
            reason_counts[key] = reason_counts.get(key, 0) + 1
    return {
        "n": n,
        "physical_same": physical_same,
        "physical_same_expected": bool(expect_physical_same),
        "metric_changed": metric_changed,
        "score_changed": score_changed,
        "j_changed": j_changed,
        "statuses": _status_bucket(statuses),
        "reasons": dict(sorted(reason_counts.items())),
    }


# ------------------------------------------------------------------ output

def write_outputs(out_dir: Path, payload: dict) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "offline_scores.json").write_text(
        json.dumps(_clean(payload), indent=2, sort_keys=True), encoding="utf-8")
    (out_dir / "offline_scores.md").write_text(_markdown(payload), encoding="utf-8")


def _fmt(v, digits=6):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return "n/a"
    return f"{x:.{digits}g}" if math.isfinite(x) else "n/a"


def _markdown(payload: dict) -> str:
    c = payload["counts"]
    lines = [
        "# Offline re-scoring pilot (R0 / M0)",
        "",
        f"- generated: `{payload['generated_utc']}`",
        f"- brief: `{payload['brief']['path']}` ({payload['brief']['name']})",
        f"- **status: {payload['status']}**",
        f"- dataset: `{payload['inputs']['dataset']}`",
        "",
        "## Counts",
        "",
        "| metric | value |",
        "|---|---:|",
    ]
    for k in ("rows_seen", "rows_ok", "rows_failed", "rows_with_npz", "rows_with_traces",
              "ath_core", "ath_full", "ath_full_ok_with_npz", "scored", "exact_complete",
              "partial_unsupported", "additional_data_or_solve_required"):
        lines.append(f"| {k} | {c.get(k, 0)} |")
    lines += ["", "## Original replay parity", "",
              f"- compared: {payload['parity']['n_compared']} / {payload['parity']['n']}",
              f"- max |delta|: {_fmt(payload['parity']['max_abs_delta'])}",
              f"- median |delta|: {_fmt(payload['parity']['median_abs_delta'])}",
              f"- within 1e-6: {payload['parity']['within_1e-6']}",
              "", "## Score variants", "",
              "| variant | n | physical same | metric changed | score changed | J changed | statuses |",
              "|---|---:|---:|---:|---:|---:|---|"]
    for name in ("weight", "tolerance", "target"):
        b = payload["variants"][name]
        lines.append(f"| {name} | {b['n']} | {b['physical_same']} | {b['metric_changed']} | "
                     f"{b['score_changed']} | {b['j_changed']} | {b['statuses']} |")
    lines += ["", "## Unsupported reasons", ""]
    reasons = payload.get("unsupported_reasons") or {}
    if reasons:
        for k, v in reasons.items():
            lines.append(f"- `{k}`: {v}")
    else:
        lines.append("- none")
    lines += ["", "## Identities", "",
              f"- unique physical: {payload['identities']['n_unique_physical']}",
              f"- unique metric: {payload['identities']['n_unique_metric']}",
              f"- unique score: {payload['identities']['n_unique_score']}",
              "", "## Preservation inventory", "",
              "| root | exists | files | bytes | checksums | truncated |",
              "|---|---|---:|---:|---:|---|"]
    for name, inv in payload["preservation"].items():
        if not isinstance(inv, dict) or "n_files" not in inv:
            continue
        lines.append(f"| {name} | {inv.get('exists')} | {inv.get('n_files')} | "
                     f"{inv.get('n_bytes')} | {len(inv.get('checksums') or {})} | "
                     f"{inv.get('truncated')} |")
    tr = payload["preservation"].get("traces") or {}
    rp = payload["preservation"].get("run_provenance") or {}
    lines += ["", f"- traces: files {tr.get('n_files', 0)}, sample `{tr.get('sample')}`, "
                  f"loadable {tr.get('loadable')}",
              f"- run provenance: runs {rp.get('n_runs', 0)}, config {rp.get('n_config', 0)}, "
              f"run.json {rp.get('n_run_json', 0)}, search.ndjson {rp.get('n_search_ndjson', 0)}, "
              f"design dirs {rp.get('n_design_dirs', 0)}, response.npz {rp.get('n_response_npz', 0)}, "
              f"metrics.json {rp.get('n_metrics_json', 0)}",
              "", "## Legacy surrogate audit (source-level; audit only)", "",
              f"- objective versions supported: {payload['surrogate_audit']['objective_versions_supported']}",
              f"- predicted impedance: {payload['surrogate_audit']['predicted_impedance']}",
              f"- predicted balloon/MEH: {payload['surrogate_audit']['predicted_balloon']} / "
              f"{payload['surrogate_audit']['predicted_meh_channels']}",
              "", "| file | line | capability | code |", "|---|---:|---|---|"]
    for e in payload["surrogate_audit"]["evidence"]:
        code = str(e.get("code") or "").replace("|", "\\|")
        lines.append(f"| `{e['file']}` | {e['line']} | {e['capability']} | `{code}` |")
    g = payload["backend_guard"]
    s = payload["source_guard"]
    lines += ["", "## Guards", "",
              f"- backend guard installed: {len(g['installed'])}, calls: **{g['calls']}**",
              f"- read-source guard scope: {s['scope']}",
              f"- unchanged: **{s['unchanged']}**",
              ""]
    if s.get("problems"):
        lines += ["Source-guard problems:"] + [f"- {p}" for p in s["problems"]] + [""]
    return "\n".join(lines)


# ------------------------------------------------------------------ run

def _sha256_prefix(path: Path, size: int) -> str:
    h = hashlib.sha256()
    remaining = int(size)
    with open(path, "rb") as fh:
        while remaining > 0:
            b = fh.read(min(1 << 20, remaining))
            if not b:
                break
            h.update(b)
            remaining -= len(b)
    return h.hexdigest()


def _snapshot_read_sources(dataset_root: Path, candidates, brief_path: Path) -> dict:
    """Hash only the bytes this pilot actually reads.

    The GPU night queue may legitimately append to ``dataset``/``runs``/``cache`` while this
    read-only tool runs. We therefore assert immutability of the *read set* (the brief, the
    candidate shard prefixes and the candidate ``.npz`` files), not unrelated concurrent writes.
    """
    dataset_root = Path(dataset_root)
    shards = sorted({s for s, _r, _m in candidates})
    prefix = {}
    for shard in shards:
        p = dataset_root / f"shard-{shard:04d}.jsonl"
        if p.is_file():
            size = p.stat().st_size
            prefix[str(p.relative_to(dataset_root))] = {
                "size": size, "sha256": _sha256_prefix(p, size)}
    npz = {}
    for shard, row, _meta in candidates:
        p = dataset_root / f"shard-{shard:04d}" / f"rec-{row:04d}.npz"
        if p.is_file():
            npz[str(p.relative_to(dataset_root))] = _sha256_file(p)
    return {
        "brief": {"path": str(brief_path), "sha256": _sha256_file(Path(brief_path))},
        "shard_prefix": prefix,
        "npz": npz,
    }


def _verify_read_sources(snapshot: dict, dataset_root: Path, brief_path: Path) -> dict:
    dataset_root = Path(dataset_root)
    problems = []
    brief = snapshot["brief"]
    if not Path(brief_path).is_file():
        problems.append("brief file disappeared")
    elif _sha256_file(Path(brief_path)) != brief["sha256"]:
        problems.append("brief file content changed")
    for rel, rec in snapshot["shard_prefix"].items():
        p = dataset_root / rel
        if not p.is_file():
            problems.append(f"{rel} disappeared")
            continue
        if p.stat().st_size < rec["size"]:
            problems.append(f"{rel} shrank")
        elif _sha256_prefix(p, rec["size"]) != rec["sha256"]:
            problems.append(f"{rel} read prefix changed")
    for rel, digest in snapshot["npz"].items():
        p = dataset_root / rel
        if not p.is_file():
            problems.append(f"{rel} disappeared")
        elif _sha256_file(p) != digest:
            problems.append(f"{rel} content changed")
    return {"unchanged": not problems, "problems": problems}


def run(*, dataset, brief_path, out_dir, limit=200, dataset_cpu=None, cache_solve=None,
        cache_cpu_solve=None, runs=None, preservation_hash_files=128,
        max_candidates=10_000, catalog=None, config_filter=None, rows_cap=50) -> dict:
    dataset = Path(dataset)
    out_dir = Path(out_dir)
    brief_path = Path(brief_path)
    if not dataset.is_dir():
        raise FileNotFoundError(f"--dataset {dataset} is not a directory")
    if not brief_path.is_file():
        raise FileNotFoundError(f"--brief {brief_path} is not a file")

    roots = {
        "dataset": dataset,
        "dataset_cpu": Path(dataset_cpu) if dataset_cpu is not None else REPO_ROOT / "dataset_cpu",
        "cache/solve": Path(cache_solve) if cache_solve is not None
        else REPO_ROOT / "cache" / "solve",
        "cache_cpu/solve": Path(cache_cpu_solve) if cache_cpu_solve is not None
        else REPO_ROOT / "cache_cpu" / "solve",
        "runs": Path(runs) if runs is not None else REPO_ROOT / "runs",
    }
    for name, root in roots.items():
        try:
            if out_dir.resolve().is_relative_to(root.resolve()):
                raise ValueError(f"--out must not be inside the read-only {name} root: {root}")
        except (OSError, ValueError) as exc:
            if isinstance(exc, ValueError) and "must not be inside" in str(exc):
                raise

    brief = replay.load_brief_context(brief_path)
    catalog_index = load_catalog_index(catalog) if catalog is not None else None
    guard = BackendGuard()
    with guard:
        scan = scan_dataset(dataset, max_candidates=max_candidates,
                            catalog_index=catalog_index,
                            config_filter=config_filter)
        candidates = scan["candidates"]
        counters = scan["counters"]

        # Snapshot only the bytes we are about to read; the live queue may append elsewhere.
        read_set = candidates[:max(0, int(limit))]
        read_snapshot = _snapshot_read_sources(dataset, read_set, brief_path)

        replay_rows = replay_candidates(candidates, dataset_root=dataset, brief=brief,
                                        limit=int(limit))
        original = replay_rows["original"]

        status_counts = _status_bucket([r for _s, _r, r in original])
        counters.update({
            "scored": len(original),
            "exact_complete": status_counts.get(replay.STATUS_EXACT_COMPLETE, 0),
            "partial_unsupported": status_counts.get(replay.STATUS_PARTIAL_UNSUPPORTED, 0),
            "additional_data_or_solve_required":
                status_counts.get(replay.STATUS_ADDITIONAL_DATA_OR_SOLVE_REQUIRED, 0),
        })

        status = ("ok" if counters["ath_full_ok_with_npz"] > 0 and counters["scored"] > 0
                  else "insufficient_evidence")

        meta_by_key = {(s, r): m for (s, r, m) in candidates}

        payload = {
            "tool": TOOL,
            "generated_utc": _utc_now(),
            "status": status,
            "brief": {
                "name": brief.name,
                "path": str(brief_path),
                "target": replay._target_key(brief.target),
                "weights": brief.weights,
                "objective_version": brief.objective_version,
                "objective_block": brief.objective_block,
            },
            "inputs": {name: str(root) for name, root in roots.items()},
            "cohort": {
                "catalog": (str(catalog) if catalog is not None else None),
                "config_filter": config_filter,
                "native_config": NATIVE_CONFIG,
                "note": ("config-filter restricts the scored candidate list to one recorded "
                         "config; rows the catalog cannot name stay unfiltered and are counted "
                         "in config_unknown"),
            },
            "counts": counters,
            "parity": _parity_block(original),
            "variants": {
                "weight": _change_block(replay_rows["weight"], expect_physical_same=True),
                "tolerance": _change_block(replay_rows["tolerance"],
                                           expect_physical_same=True),
                "target": _change_block(replay_rows["target"], expect_physical_same=True),
            },
            "unsupported_reasons": _reason_bucket([r for _s, _r, r in original]),
            "identities": _identity_block(original),
            "rows": [
                {"shard": shard, "row": row,
                 "config_name": meta_by_key[(shard, row)].get("config_name") or "",
                 "catalog_run_id": meta_by_key[(shard, row)].get("catalog_run_id") or "",
                 "stored_objective_version": meta_by_key[(shard, row)].get(
                     "objective_version", 1),
                 **res.to_dict()}
                for (shard, row, res) in original[:max(0, min(rows_cap, len(original)))]
            ],
            "preservation": preservation_inventory(roots, max_files=preservation_hash_files),
            "surrogate_audit": legacy_surrogate_audit(REPO_ROOT),
            "backend_guard": {"installed": list(guard.installed), "calls": int(guard.calls),
                              "called_names": list(guard.names)},
        }

        after_check = _verify_read_sources(read_snapshot, dataset, brief_path)
        payload["source_guard"] = {
            "scope": "files read by the pilot (brief + candidate shard prefixes + candidate npz); "
                     "live queue appends to dataset/runs/cache are outside this assertion",
            "unchanged": bool(after_check["unchanged"]),
            "problems": after_check["problems"],
            "watched": read_snapshot,
            "excluded_roots": {
                "dataset_cpu": "inventory only",
                "cache/solve": "inventory only; may be written by the live queue",
                "cache_cpu/solve": "inventory only; may be written by the live queue",
                "runs": "inventory only; may be written by the live queue",
            },
        }

    if guard.calls:
        raise RuntimeError(f"offline_scores: {guard.calls} forbidden backend call(s): "
                           f"{guard.names}")
    if not payload["source_guard"]["unchanged"]:
        raise RuntimeError("offline_scores: a read source changed during the read-only pilot")

    write_outputs(out_dir, payload)
    return payload


# ------------------------------------------------------------------ CLI

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Bounded read-only ATH re-scoring pilot (zero backend calls)")
    ap.add_argument("--dataset", type=Path, default=REPO_ROOT / "dataset")
    ap.add_argument("--brief", type=Path, default=DEFAULT_BRIEF)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--limit", type=int, default=200,
                    help="max ATH-compatible rows to replay (default 200)")
    ap.add_argument("--dataset-cpu", type=Path, default=REPO_ROOT / "dataset_cpu")
    ap.add_argument("--cache-solve", type=Path, default=REPO_ROOT / "cache" / "solve")
    ap.add_argument("--cache-cpu-solve", type=Path, default=REPO_ROOT / "cache_cpu" / "solve")
    ap.add_argument("--runs", type=Path, default=REPO_ROOT / "runs")
    ap.add_argument("--preservation-hash-files", type=int, default=128)
    ap.add_argument("--max-candidates", type=int, default=10_000)
    ap.add_argument("--catalog", type=Path, default=None,
                    help="S0 catalog.csv join: attaches config_name/run_id provenance the raw "
                         "dataset records do not carry (rows_native / native counts)")
    ap.add_argument("--config-filter", default=None,
                    help="restrict the scored candidate list to one recorded config, e.g. "
                         f"{NATIVE_CONFIG} (the single-task cohort); requires --catalog")
    ap.add_argument("--rows-cap", type=int, default=50,
                    help="how many scored rows to expose in the payload's `rows` display list "
                         "(M1 joins want the full scored set, e.g. --rows-cap 200)")
    args = ap.parse_args(argv)
    try:
        payload = run(
            dataset=args.dataset, brief_path=args.brief, out_dir=args.out, limit=args.limit,
            dataset_cpu=args.dataset_cpu, cache_solve=args.cache_solve,
            cache_cpu_solve=args.cache_cpu_solve, runs=args.runs,
            preservation_hash_files=args.preservation_hash_files,
            max_candidates=args.max_candidates,
            catalog=args.catalog, config_filter=args.config_filter,
            rows_cap=args.rows_cap,
        )
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 - explicit nonzero on guard/source failure
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 3
    print(f"wrote {args.out / 'offline_scores.json'} and {args.out / 'offline_scores.md'}")
    print("COUNTS " + json.dumps(_clean(payload["counts"]), sort_keys=True))
    print(f"STATUS {payload['status']}  backend_calls={payload['backend_guard']['calls']}  "
          f"source_unchanged={payload['source_guard']['unchanged']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
