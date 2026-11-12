"""Shared helpers for the `tools/analysis/` evolutionary-analysis toolkit (2026-11-12).

Pure offline, stdlib + numpy/scipy (+ matplotlib with the Agg backend, optional
sklearn is imported lazily and only where a tool says so). Reads run dirs
(``search.ndjson`` / ``config.yaml`` / ``run.json``) read-only; every output goes
to a caller-provided ``--out`` folder. Never imports from the GUI, never writes
into ``runs/``. Schema per report: ``tools/analysis/schema.md``.

Terminology lives in schema.md; the core ones again here because every tool uses
them: a *valid row* has ``ok == true``; a *new eval* is non-``cached``; the
convergence X axis counts *new valid* evaluations in file order.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import yaml

REPO = Path(__file__).resolve().parents[2]

#: matplotlib is chart-only and must never pop a window; force the Agg backend
#: before anything else imports pyplot.
import matplotlib  # noqa: E402

matplotlib.use("Agg")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _finite(x):
    """JSON-able float: non-finite -> None (report JSON is written with allow_nan=False)."""
    if x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def read_ndjson(path: Path) -> list[dict]:
    """Rows of a ``search.ndjson``; torn/truncated trailing lines are skipped, never fatal."""
    out: list[dict] = []
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return out
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict):
            out.append(row)
    return out


def read_json(path: Path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def read_yaml(path: Path):
    try:
        return yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def params_flat(row: dict) -> dict:
    """Flat numeric knob dict of a row; generator families nest theirs under ``grid.knobs``."""
    p = row.get("params")
    if not isinstance(p, dict):
        return {}
    if isinstance(p.get("grid"), dict) and isinstance(p["grid"].get("knobs"), dict):
        p = p["grid"]["knobs"]
    return {str(k): float(v) for k, v in p.items()
            if isinstance(v, (int, float)) and not isinstance(v, bool)
            and math.isfinite(float(v))}


def knobs_shared(rows: list[dict]) -> list[str]:
    keys: list[set] = [set(params_flat(r)) for r in rows]
    if not keys:
        return []
    inter = set.intersection(*keys)
    return sorted(inter)


def bounds_of(config: dict | None) -> dict:
    """``{key: (lo, hi)}`` numeric search bounds of a config (``search: false`` knobs excluded)."""
    out: dict[str, tuple[float, float]] = {}
    b = (config or {}).get("bounds") or {}
    for k, v in b.items():
        if not isinstance(v, dict) or v.get("search") is False:
            continue
        try:
            lo, hi = float(v["lo"]), float(v["hi"])
        except (KeyError, TypeError, ValueError):
            continue
        if math.isfinite(lo) and math.isfinite(hi) and hi > lo:
            out[str(k)] = (lo, hi)
    return out


def run_config(run_dir: Path) -> dict:
    """The run's effective config: run.json's snapshot first, else config.yaml. Read-only."""
    run_json = read_json(Path(run_dir) / "run.json") or {}
    cfg = run_json.get("config")
    if not isinstance(cfg, dict):
        cfg = read_yaml(Path(run_dir) / "config.yaml")
    return cfg if isinstance(cfg, dict) else {}


def run_meta(run_dir: Path, cfg: dict | None = None) -> dict:
    """``{brief, family, objective_version, mode}`` provenance of a run dir."""
    run_json = read_json(Path(run_dir) / "run.json") or {}
    cfg = cfg if cfg is not None else run_config(run_dir)
    rows = read_ndjson(Path(run_dir) / "search.ndjson")
    fam = run_json.get("family") or cfg.get("family")
    versions: dict[int, int] = {}
    modes: dict[str, int] = {}
    for r in rows:
        v = r.get("objective_version")
        if isinstance(v, int):
            versions[v] = versions.get(v, 0) + 1
        m = r.get("mode")
        if isinstance(m, str):
            modes[m] = modes.get(m, 0) + 1
    majority = lambda counts: (max(counts, key=counts.get) if counts else None)
    return {
        "brief": run_json.get("config_name") or cfg.get("name"),
        "family": fam,
        "objective_version": majority(versions),
        "mode": majority(modes),
        "cma_seed": run_json.get("cma_seed"),
        "has_rows": bool(rows),
    }


def load_run(run_dir: Path) -> dict:
    """Everything the tools need from one run dir, read-only."""
    run_dir = Path(run_dir)
    if not (run_dir / "search.ndjson").exists():
        raise FileNotFoundError(f"{run_dir}: no search.ndjson — not a run dir")
    cfg = run_config(run_dir)
    rows = read_ndjson(run_dir / "search.ndjson")
    meta = run_meta(run_dir, cfg)
    return {"run_dir": run_dir, "config": cfg, "rows": rows,
            "bounds": bounds_of(cfg), "meta": meta}


def valid_rows(rows: list[dict]) -> list[dict]:
    return [r for r in rows if r.get("ok") is True]


def new_rows(rows: list[dict]) -> list[dict]:
    return [r for r in rows if r.get("cached") is False]


def top_decile(rows: list[dict], n_min: int = 3) -> list[dict] | None:
    """The lowest-J ceil(n/10) valid rows (at least ``n_min``); None below 10 valid rows.

    Schema: the top decile is ``max(3, ceil(n_valid / 10))`` rows, and a run with
    < 10 valid rows has no top decile at all (tools degrade)."""
    valid = valid_rows(rows)
    if len(valid) < 10:
        return None
    n = max(n_min, math.ceil(len(valid) * 0.1))
    return sorted(valid, key=lambda r: float(r.get("objective", float("inf"))))[:n]


def best_so_far_curve(run: dict) -> list[dict]:
    """Best-so-far over *new valid* evaluations, in row order, with wall seconds.

    Wall seconds are the cumulative sum of the rows' ``seconds.total`` (each solved
    eval's own wall time; cached replays carry none of it) — always present; the
    ``created_utc`` timestamps alone would give only a coarse clock span.
    """
    out: list[dict] = []
    best = float("inf")
    wall = 0.0
    for r in run["rows"]:
        if r.get("ok") is not True or r.get("cached") is not False:
            continue
        try:
            obj = float(r["objective"])
        except (KeyError, TypeError, ValueError):
            continue
        if math.isfinite(obj) and obj < best:
            best = obj
        sec = (r.get("seconds") or {}).get("total")
        wall += float(sec) if isinstance(sec, (int, float)) and math.isfinite(sec) else 0.0
        out.append({"n": len(out) + 1, "best": best, "wall_s": wall})
    return out


def evals_to_within(curve: list[dict], final_best: float, rel: float) -> int | None:
    """First new-valid-eval index whose best-so-far is within ``rel`` of ``final_best``.

    The best-so-far decreases monotonically towards ``final_best``, so the distance that
    can shrink is ``best - final_best`` (schema: "best-so-far <= 1.01 * final_best")."""
    if not curve or not math.isfinite(final_best):
        return None
    thresh = abs(final_best) * rel
    for p in curve:
        if p["best"] - final_best <= thresh:
            return int(p["n"])
    return None


def last20_improvement(curve: list[dict]) -> tuple[bool, float | None]:
    """(flag, improvement %) — best improved by > 1% of the final best inside the last 20%."""
    n = len(curve)
    if n < 10:
        return False, None
    final = curve[-1]["best"]
    tail_start = curve[max(0, math.ceil(n * 0.8)) - 1]["n"]
    best_before = min((p["best"] for p in curve if p["n"] < tail_start), default=final)
    if not math.isfinite(final) or final <= 0:
        return False, None
    imp_pct = (best_before - final) / max(abs(final), 1e-12) * 100.0
    return imp_pct > 1.0, imp_pct


def refusal_windows(rows: list[dict], w: int = 50) -> list[dict]:
    """Refusal rate by kind per window of ``w`` non-cached rows (last window may be shorter)."""
    new = new_rows(rows)
    out = []
    for start in range(0, len(new), w):
        win = new[start:start + w]
        kinds: dict[str, int] = {}
        refused = 0
        for r in win:
            if r.get("ok") is not True:
                refused += 1
                kind = str(r.get("kind") or r.get("error") or "unknown")
                kinds[kind] = kinds.get(kind, 0) + 1
        out.append({"w": [start + 1, start + len(win)], "rate": refused / len(win),
                    "kinds": kinds})
    return out


# ------------------------------------------------------------------ stats


def spearman(x, y) -> float | None:
    """Spearman rho; scipy when present, else an equivalent hand-rolled rank formula."""
    xv = np.asarray(x, dtype=float)
    yv = np.asarray(y, dtype=float)
    good = np.isfinite(xv) & np.isfinite(yv)
    xv, yv = xv[good], yv[good]
    if xv.size < 3:
        return None
    try:
        import scipy.stats as sps  # type: ignore

        rho = float(sps.spearmanr(xv, yv).statistic)  # type: ignore[union-attr]
        return rho if math.isfinite(rho) else None
    except Exception:  # noqa: BLE001 - degrade to the hand-rolled formula
        rx = _ranks(xv)
        ry = _ranks(yv)
        dx = rx - rx.mean()
        dy = ry - ry.mean()
        den = math.sqrt(float(dx @ dx) * float(dy @ dy))
        return float(dx @ dy) / den if den > 0 else None


def _ranks(v: np.ndarray) -> np.ndarray:
    # Ties share the average rank (scipy-compatible).
    order = np.argsort(v, kind="stable")
    ranks = np.empty(v.size, dtype=float)
    sorted_v = v[order]
    i = 0
    while i < v.size:
        j = i
        while j + 1 < v.size and sorted_v[j + 1] == sorted_v[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2.0 + 1.0
        i = j + 1
    return ranks


def bootstrap_ci(values: list[float], n_boot: int = 2000, seed: int = 0) -> list[float] | None:
    """Percentile bootstrap 95% CI of the median (fixed seed = reproducible reports)."""
    if len(values) < 3:
        return None
    rng = np.random.default_rng(seed)
    arr = np.asarray(values, dtype=float)
    meds = np.median(arr[rng.integers(0, arr.size, size=(n_boot, arr.size))], axis=1)
    lo, hi = np.percentile(meds, [2.5, 97.5])
    return [float(lo), float(hi)]


def beats_rule(median_a: float, spread_a: float, median_b: float, spread_b: float,
               n_runs: int) -> str:
    """The 2026-10-23 rule: A beats B only when medians differ by more than both spreads.

    >= 5 runs -> a verdict; 3-4 (and 1-2, seed_variance only) -> 'indicative' when the
    rule holds (schema.md's seed_variance example). ``ab_compare`` floors < 3 to
    'no-verdict' itself before calling this, per its own schema section."""
    diff = abs(median_a - median_b)
    if not (diff > spread_a and diff > spread_b):
        return "no-verdict"
    if n_runs >= 5:
        return "a-beats-b" if median_a < median_b else "b-beats-a"
    return "indicative"


# ------------------------------------------------------------------ output


def chart_or_none(name: str):
    """Import pyplot on demand; a missing matplotlib degrades to 'no chart', never a failure."""
    try:
        import matplotlib.pyplot as plt  # type: ignore

        return plt
    except Exception:  # noqa: BLE001 - charts are best-effort
        print(f"warning: matplotlib unavailable, skipping chart {name}", file=sys.stderr)
        return None


def jsonable(obj) -> Any:
    """Deep-copy a payload into plain JSON types: numpy scalars -> Python, non-finite -> None
    (schema.md: every report is written with allow_nan=False and non-finite floats are null)."""
    if isinstance(obj, dict):
        return {str(k): jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [jsonable(v) for v in obj]
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, (float, np.floating)):
        v = float(obj)
        return v if math.isfinite(v) else None
    return obj


def write_report(out_dir: Path, tool: str, payload: dict, md: str,
                 charts: "dict[str, Callable[[object], object]] | None" = None) -> dict:
    """Write ``<tool>.json`` + ``<tool>.md`` (+ PNG charts) into ``out_dir``; return paths."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = dict(jsonable(payload), tool=tool, generated_utc=utc_now())
    jpath = out_dir / f"{tool}.json"
    jpath.write_text(json.dumps(payload, indent=1, allow_nan=False, default=str),
                     encoding="utf-8")
    (out_dir / f"{tool}.md").write_text(md, encoding="utf-8")
    written = {"json": str(jpath), "md": str(out_dir / f"{tool}.md")}
    for fname, fn in (charts or {}).items():
        plt = chart_or_none(fname)
        if plt is None:
            continue
        try:
            fig = fn(plt)
            if fig is None:
                continue
            fig.savefig(out_dir / fname, dpi=120)  # type: ignore[union-attr]
            plt.close(fig)  # type: ignore[arg-type]
        except Exception as exc:  # noqa: BLE001 - charts are best-effort, the JSON is the contract
            print(f"warning: chart {fname} failed ({type(exc).__name__}: {exc})", file=sys.stderr)
            plt.close("all")
            continue
        written[fname] = str(out_dir / fname)
    return written


def add_out_arg(ap: argparse.ArgumentParser) -> None:
    ap.add_argument("--out", required=True,
                    help="output dir for <name>.json/.md and PNG charts (never runs/)")


def fail(msg: str) -> "SystemExit":
    print(f"ERROR: {msg}", file=sys.stderr)
    return SystemExit(2)
