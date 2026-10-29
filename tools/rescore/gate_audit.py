"""Audit stored hornlab-search runs against the canonical owner gates (zero GPU, zero solver).

Ported from the one-off ``cdaudit.py`` scratch script into a committed, deterministic tool. It walks
``runs/2026102[78]T*`` and audits every stored row:

* ``search.ndjson`` screen rows;
* ``verify/search.ndjson`` verify rows where the file exists.

Inside one run, a design's verify row replaces its screen row (the verify grid is denser); a design
without a verify row keeps its screen row. Rows are never deduped across runs, so the CSV reports
every audited stored row.

Gate definitions (canonical, 2026-10-29): H constant-directivity, V constant-directivity, DI rise,
8 kHz beamwidth floor, throat loading (LFP20 x 1.6 <= F_X and Re z >= 0.50 above the crossover) and
round throat at the driver exit. A gate that cannot be evaluated is UNRESOLVED and fails.

Per-run values (not module constants because they come from the brief):
``F_X = brief.target.f0_hz`` and ``BAND_HI = min(8000.0, brief.target.band_hi_hz)``.

Usage (from the repo root)::

    .venv\\Scripts\\python.exe tools/rescore/gate_audit.py
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np

# Runnable as a plain script: make the package importable from the repo root.
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from hornlab_search.mesh.throat_check import fits_exit, throat_shape  # noqa: E402

# ---------------------------------------------------------------- canonical constants

#: H gate: every solved H-plane sample in [F_X, BAND_HI] must be within this relative tolerance.
H_TOL = 0.20
#: V gate window on ``bw_v / coverage_v`` (deliberately asymmetric; the owner gate is not +/-20%).
V_LO = 0.60
V_HI = 1.25
#: DI-rise gate: max(di_db) - min(di_db) over [F_X, BAND_HI].
DI_RISE_MAX_DB = 5.0
#: BW8K floor: bw_h and bw_v at the top solved frequency >= this fraction of their targets.
BW8K_FLOOR = 0.75
#: Loading gate: Re z_throat at LFP20 and the crossover ratio.
LFP_RE_Z = 0.20
LFP_CROSSOVER_RATIO = 1.6
#: Loading gate: Re z_throat must stay at or above this for every solved f >= F_X.
LOADED_RE_Z = 0.50
#: Throat gate tolerances (``throat_check.fits_exit`` owns the same values; recorded here as the
#: canonical gate thresholds for this audit).
THROAT_TOL_MM = 0.5
ROUND_TOL = 0.03
#: The audit never looks above 8 kHz, whatever the brief says.
HARD_BAND_HI_HZ = 8000.0

GATE_KEYS = ("h", "v", "di", "bw8k", "load", "throat")
GATE_LABELS = {
    "h": "H",
    "v": "V",
    "di": "DI",
    "bw8k": "BW8K",
    "load": "Loading",
    "throat": "Throat",
}

DEFAULT_OUT_DIR = REPO_ROOT / "docs" / "data" / "gate_audit_2026-10-29"
DEFAULT_RUNS_DIR = REPO_ROOT / "runs"

CSV_FIELDS = (
    "brief", "cell", "run", "tier", "design", "family", "J",
    "f0", "f0_v", "band_hi", "coverage_h", "coverage_v",
    "h", "v", "di", "bw8k", "load", "throat", "pass_all",
    "unresolved", "unresolved_reasons", "flags", "gate_notes",
    "lfp20_hz", "lfp50_hz", "lfp70_hz", "lfp20_note",
    "rez_at_fx", "rez_min_from_fx", "di_rise_db",
    "bwh_at_8k", "bwv_at_8k", "bw8k_at_hz",
    "throat_w_mm", "throat_h_mm", "throat_round", "throat_reason",
    "n_dof", "seconds_total",
)


# ---------------------------------------------------------------- numeric helpers


def interp_log_f(freqs, values, x: float) -> float:
    """Linear interpolation in ``log(f)``; NaN outside the solved grid (never extrapolate)."""
    f = np.asarray(freqs, dtype=float)
    y = np.asarray(values, dtype=float)
    if f.size == 0 or f.size != y.size:
        return float("nan")
    try:
        x = float(x)
    except (TypeError, ValueError):
        return float("nan")
    if not math.isfinite(x) or x < f[0] or x > f[-1]:
        return float("nan")
    return float(np.interp(math.log(x), np.log(f), y))


def crossing_freq(freqs, values, level: float) -> tuple[float | None, str]:
    """First upward crossing of ``level``, linearly interpolated in ``log(f)``.

    Returns ``(frequency, note)``. A grid whose first sample is already at or above the level is
    resolved-low: the frequency is the grid start and the note is ``"<= <grid_start>"``. No upward
    crossing at or below the highest solved frequency is unresolved: ``(None, reason)``.
    """
    f = np.asarray(freqs, dtype=float)
    z = np.asarray(values, dtype=float)
    if f.size == 0 or f.size != z.size:
        return None, "no solved frequencies"
    if not np.isfinite(z).all():
        return None, "non-finite z_throat_real"
    if z[0] >= level:
        return float(f[0]), f"<= {f[0]:g}"
    for i in range(f.size - 1):
        if z[i] < level <= z[i + 1]:
            log_f = np.interp(
                level,
                [z[i], z[i + 1]],
                [math.log(f[i]), math.log(f[i + 1])],
            )
            return float(math.exp(log_f)), ""
    return None, (
        f"no upward crossing of {level:g} at or below the highest solved frequency {f[-1]:g} Hz"
    )


# ---------------------------------------------------------------- gate results


@dataclass(frozen=True)
class GateResult:
    """``passed`` is the gate outcome; ``unresolved`` means it could not be evaluated (and failed)."""

    passed: bool
    unresolved: bool = False
    reason: str = ""
    value: float | None = None


@dataclass(frozen=True)
class Bw8kResult:
    gate: GateResult
    freq_hz: float | None = None
    bw_h: float | None = None
    bw_v: float | None = None
    top_below_band_hi: bool = False


@dataclass(frozen=True)
class LoadResult:
    gate: GateResult
    lfp20_hz: float | None = None
    lfp50_hz: float | None = None
    lfp70_hz: float | None = None
    lfp20_note: str = ""
    rez_at_fx: float | None = None
    rez_min_from_fx: float | None = None


# ---------------------------------------------------------------- gates


def gate_h(freqs, bw_h, coverage_h: float, f_x: float, band_hi: float) -> GateResult:
    """H: every solved H sample in [F_X, BAND_HI] within ``H_TOL`` of the target coverage."""
    f = np.asarray(freqs, dtype=float)
    bw = np.asarray(bw_h, dtype=float)
    if f.size == 0:
        return GateResult(False, True, "no solved frequencies")
    if f_x < f[0]:
        return GateResult(
            False, True,
            f"F_X={f_x:g} Hz is below the lowest solved frequency {f[0]:g} Hz",
        )
    mask = (f >= f_x) & (f <= band_hi)
    if not mask.any():
        return GateResult(False, True, f"no solved sample in [{f_x:g}, {band_hi:g}] Hz")
    vals = bw[mask]
    if not np.isfinite(vals).all() or not math.isfinite(float(coverage_h)) or coverage_h == 0:
        return GateResult(False, False, "non-finite beamwidth or coverage")
    off = np.abs(vals / float(coverage_h) - 1.0)
    worst = float(off.max())
    if worst > H_TOL:
        n_bad = int((off > H_TOL).sum())
        return GateResult(
            False, False,
            f"{n_bad} of {vals.size} samples outside +/-{H_TOL:.0%}; worst deviation {worst:.3f}",
            worst,
        )
    return GateResult(True, False, "", worst)


def gate_v(
    freqs, bw_v, coverage_v: float, f_x: float, f0_v: float, band_hi: float,
) -> GateResult:
    """V: every solved V sample in [max(1.5*F_X, f0_v), BAND_HI] inside [V_LO, V_HI]."""
    f = np.asarray(freqs, dtype=float)
    bw = np.asarray(bw_v, dtype=float)
    if f.size == 0:
        return GateResult(False, True, "no solved frequencies")
    if f_x < f[0]:
        return GateResult(
            False, True,
            f"F_X={f_x:g} Hz is below the lowest solved frequency {f[0]:g} Hz",
        )
    lo = max(1.5 * f_x, float(f0_v))
    if lo > band_hi:
        return GateResult(False, True, f"V window starts at {lo:g} Hz, above BAND_HI={band_hi:g} Hz")
    mask = (f >= lo) & (f <= band_hi)
    if not mask.any():
        return GateResult(False, True, f"no solved sample in [{lo:g}, {band_hi:g}] Hz")
    vals = bw[mask]
    if not np.isfinite(vals).all() or not math.isfinite(float(coverage_v)) or coverage_v == 0:
        return GateResult(False, False, "non-finite beamwidth or coverage")
    ratio = vals / float(coverage_v)
    bad = (ratio < V_LO) | (ratio > V_HI)
    if bad.any():
        return GateResult(
            False, False,
            f"{int(bad.sum())} of {vals.size} samples outside [{V_LO:g}, {V_HI:g}]; "
            f"range {float(ratio.min()):.3f}..{float(ratio.max()):.3f}",
            float(ratio.min()),
        )
    return GateResult(True, False, "", float(ratio.min()))


def gate_di_rise(freqs, di_db, f_x: float, band_hi: float) -> GateResult:
    """DI: max(di_db) - min(di_db) over [F_X, BAND_HI] <= ``DI_RISE_MAX_DB``."""
    f = np.asarray(freqs, dtype=float)
    di = np.asarray(di_db, dtype=float)
    mask = (f >= f_x) & (f <= band_hi)
    if not mask.any():
        return GateResult(False, True, f"no solved sample in [{f_x:g}, {band_hi:g}] Hz")
    vals = di[mask]
    if not np.isfinite(vals).all():
        return GateResult(False, False, "non-finite di_db in band")
    rise = float(vals.max() - vals.min())
    if rise > DI_RISE_MAX_DB:
        return GateResult(
            False, False, f"DI rise {rise:.3f} dB > {DI_RISE_MAX_DB:g} dB", rise,
        )
    return GateResult(True, False, "", rise)


def gate_bw8k(
    freqs, bw_h, bw_v, coverage_h: float, coverage_v: float, band_hi: float,
) -> Bw8kResult:
    """BW8K: at the highest solved f <= BAND_HI both beamwidths clear ``BW8K_FLOOR`` x target."""
    f = np.asarray(freqs, dtype=float)
    bh = np.asarray(bw_h, dtype=float)
    bv = np.asarray(bw_v, dtype=float)
    mask = f <= band_hi
    if not mask.any():
        return Bw8kResult(GateResult(False, True, f"no solved frequency <= BAND_HI={band_hi:g} Hz"))
    idx = int(np.flatnonzero(mask)[-1])
    ftop = float(f[idx])
    top_below = bool(ftop < band_hi)
    vh = float(bh[idx])
    vv = float(bv[idx])
    if not (math.isfinite(vh) and math.isfinite(vv)):
        return Bw8kResult(
            GateResult(False, False, "non-finite beamwidth at the top solved frequency"),
            ftop, None, None, top_below,
        )
    bad = []
    if vh < BW8K_FLOOR * float(coverage_h):
        bad.append(f"bw_h {vh:.1f} < {BW8K_FLOOR:g} x {float(coverage_h):.1f}")
    if vv < BW8K_FLOOR * float(coverage_v):
        bad.append(f"bw_v {vv:.1f} < {BW8K_FLOOR:g} x {float(coverage_v):.1f}")
    reason = f"at {ftop:g} Hz: " + "; ".join(bad) if bad else ""
    return Bw8kResult(GateResult(not bad, False, reason), ftop, vh, vv, top_below)


def gate_loading(freqs, z_real, f_x: float) -> LoadResult:
    """Loading: LFP20 * 1.6 <= F_X, plus Re z >= 0.50 for every solved f >= F_X."""
    f = np.asarray(freqs, dtype=float)
    z = None if z_real is None else np.asarray(z_real, dtype=float)
    if z is None or z.size != f.size or f.size == 0:
        return LoadResult(GateResult(False, True, "no usable z_throat_real"))
    lfp20, note20 = crossing_freq(f, z, LFP_RE_Z)
    lfp50, _ = crossing_freq(f, z, 0.50)
    lfp70, _ = crossing_freq(f, z, 0.70)
    rez_at_fx = interp_log_f(f, z, f_x)
    above = f >= f_x
    if above.any() and np.isfinite(z[above]).all():
        rez_min = float(z[above].min())
    else:
        rez_min = float("nan")

    problems: list[str] = []
    unresolved = False
    if lfp20 is None:
        unresolved = True
        problems.append(f"LFP20 unresolved: {note20}")
    elif lfp20 * LFP_CROSSOVER_RATIO > f_x:
        problems.append(
            f"LFP20 {lfp20:.1f} Hz x {LFP_CROSSOVER_RATIO:g} = "
            f"{lfp20 * LFP_CROSSOVER_RATIO:.1f} Hz > F_X {f_x:g} Hz"
        )
    if not above.any():
        unresolved = True
        problems.append(f"no solved frequency >= F_X={f_x:g} Hz")
    elif not np.isfinite(z[above]).all():
        unresolved = True
        problems.append(f"non-finite Re z at a solved frequency >= F_X={f_x:g} Hz")
    elif rez_min < LOADED_RE_Z:
        problems.append(f"Re z {rez_min:.3f} < {LOADED_RE_Z:g} at a solved f >= F_X")

    return LoadResult(
        GateResult(not problems, unresolved, "; ".join(problems), lfp20),
        lfp20_hz=lfp20,
        lfp50_hz=lfp50,
        lfp70_hz=lfp70,
        lfp20_note=note20,
        rez_at_fx=rez_at_fx,
        rez_min_from_fx=rez_min,
    )


def gate_throat(shape: dict | None, exit_diameter_mm: float | None) -> GateResult:
    """Throat: ``fits_exit`` must return True; unknown/unreadable is UNRESOLVED."""
    if shape is None:
        return GateResult(False, True, "mesh not locatable")
    ok, reason = fits_exit(shape, exit_diameter_mm)
    if ok is None:
        return GateResult(False, True, f"throat unresolved: {reason}")
    return GateResult(bool(ok), False, "" if ok else reason)


# ---------------------------------------------------------------- stored-row parsing


def parse_stored_row(row: Any, tier: str) -> dict | None:
    """Parse one stored evaluation row without consulting its objective version.

    v3/v4/v5 rows share the stored ``metrics`` schema; this reader deliberately ignores
    ``objective_version`` and ``terms`` so a schema bump cannot silently drop rows.
    """
    if not isinstance(row, dict) or not row.get("ok"):
        return None
    metrics = row.get("metrics")
    if not isinstance(metrics, dict):
        return None
    try:
        freqs = np.asarray(metrics.get("freqs_hz"), dtype=float)
        bw_h = np.asarray(metrics.get("bw_h_deg"), dtype=float)
        bw_v = np.asarray(metrics.get("bw_v_deg"), dtype=float)
        di_db = np.asarray(metrics.get("di_db"), dtype=float)
    except (TypeError, ValueError):
        return None
    if freqs.ndim != 1 or freqs.size == 0:
        return None
    if not (bw_h.shape == freqs.shape and bw_v.shape == freqs.shape and di_db.shape == freqs.shape):
        return None
    if not np.isfinite(freqs).all():
        return None

    z_raw = metrics.get("z_throat_real")
    z = np.asarray(z_raw, dtype=float) if z_raw is not None else None
    if z is not None and z.shape != freqs.shape:
        z = None

    order = np.argsort(freqs, kind="stable")
    freqs = freqs[order]
    bw_h = bw_h[order]
    bw_v = bw_v[order]
    di_db = di_db[order]
    if z is not None:
        z = z[order]

    seconds = row.get("seconds")
    seconds_total = seconds.get("total") if isinstance(seconds, dict) else seconds

    j_raw = row.get("objective")
    if j_raw is None:
        j_raw = row.get("J")

    return {
        "tier": tier,
        "design": row.get("design_hash") or row.get("design") or "",
        "mesh_hash": row.get("mesh_hash") or "",
        "family": row.get("family"),
        "J": float(j_raw) if isinstance(j_raw, (int, float)) else float("nan"),
        "freqs": freqs,
        "bw_h": bw_h,
        "bw_v": bw_v,
        "di_db": di_db,
        "z_real": z,
        "n_dof": row.get("n_dof"),
        "seconds_total": float(seconds_total) if isinstance(seconds_total, (int, float)) else None,
    }


def select_rows(screen_raw: Iterable[Any], verify_raw: Iterable[Any]) -> list[tuple[str, dict]]:
    """Parse screen + verify rows, preferring verify rows for a design that was verified."""
    screen = [p for raw in screen_raw if (p := parse_stored_row(raw, "screen")) is not None]
    verify = [p for raw in verify_raw if (p := parse_stored_row(raw, "verify")) is not None]
    verified = {p["design"] for p in verify if p["design"]}
    out: list[tuple[str, dict]] = [("verify", p) for p in verify]
    out.extend(("screen", p) for p in screen if p["design"] not in verified)
    return out


def read_ndjson(path: Path) -> list[Any]:
    if not path.is_file():
        return []
    out: list[Any] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


# ---------------------------------------------------------------- run metadata


def read_run_meta(run_dir: Path) -> dict | None:
    """Return the brief/target values the audit needs, or ``None`` for an unusable run.json."""
    try:
        run = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 - a missing/corrupt run.json is a skip
        return None
    if not isinstance(run, dict):
        return None
    config = run.get("config") or {}
    brief = config.get("brief") or {}
    target = brief.get("target") or config.get("target") or {}
    driver = brief.get("driver") or {}
    try:
        f_x = float(target["f0_hz"])
        coverage_h = float(target["coverage_h_deg"])
        coverage_v = float(target["coverage_v_deg"])
    except (KeyError, TypeError, ValueError):
        return None
    f0_v = target.get("f0_v_hz")
    f0_v = float(f0_v) if isinstance(f0_v, (int, float)) else f_x
    band_hi_raw = target.get("band_hi_hz")
    band_hi = min(
        HARD_BAND_HI_HZ,
        float(band_hi_raw) if isinstance(band_hi_raw, (int, float)) else HARD_BAND_HI_HZ,
    )
    exit_radius = driver.get("exit_radius_mm")
    exit_diameter = 2.0 * float(exit_radius) if isinstance(exit_radius, (int, float)) else None
    name = brief.get("name") or config.get("name") or run.get("config_name") or run_dir.name
    return {
        "run": run_dir.name,
        "brief": name,
        "cell": run.get("config_name") or config.get("name") or name,
        "family": run.get("family") or config.get("family"),
        "f_x": f_x,
        "f0_v": f0_v,
        "band_hi": band_hi,
        "coverage_h": coverage_h,
        "coverage_v": coverage_v,
        "exit_diameter_mm": exit_diameter,
    }


# ---------------------------------------------------------------- mesh and audit row


def find_mesh(
    run_dir: Path, design: str, mesh_hash: str,
) -> tuple[Path | None, str]:
    """Return ``(path, source)`` using the canonical search order; source is ``missing`` if absent."""
    candidates = (
        ("design", run_dir / "designs" / design / "mesh.msh"),
        ("verify_design", run_dir / "verify" / "designs" / design / "mesh.msh"),
        ("cache", REPO_ROOT / "cache" / "mesh" / f"{design}-{mesh_hash}" / "mesh.msh"),
    )
    for source, path in candidates:
        if path.is_file():
            return path, source
    return None, "missing"


def audit_row(
    meta: dict,
    stored: dict,
    tier: str,
    run_dir: Path,
    shape_cache: dict,
    counters: Counter,
) -> dict:
    freqs = stored["freqs"]
    f_x = meta["f_x"]
    band_hi = meta["band_hi"]
    coverage_h = meta["coverage_h"]
    coverage_v = meta["coverage_v"]

    h = gate_h(freqs, stored["bw_h"], coverage_h, f_x, band_hi)
    v = gate_v(freqs, stored["bw_v"], coverage_v, f_x, meta["f0_v"], band_hi)
    di = gate_di_rise(freqs, stored["di_db"], f_x, band_hi)
    bw8k = gate_bw8k(freqs, stored["bw_h"], stored["bw_v"], coverage_h, coverage_v, band_hi)
    load = gate_loading(freqs, stored["z_real"], f_x)

    mesh_path, mesh_source = find_mesh(run_dir, stored["design"], stored["mesh_hash"])
    counters[f"mesh_source_{mesh_source}"] += 1
    shape = None
    if mesh_path is not None:
        cache_key = (
            (stored["design"], stored["mesh_hash"])
            if stored["design"] and stored["mesh_hash"]
            else str(mesh_path)
        )
        if cache_key in shape_cache:
            shape = shape_cache[cache_key]
        else:
            shape = throat_shape(mesh_path)
            shape_cache[cache_key] = shape
    throat = gate_throat(shape, meta["exit_diameter_mm"])

    results = {"h": h, "v": v, "di": di, "bw8k": bw8k.gate, "load": load.gate, "throat": throat}
    flags: list[str] = []
    if bw8k.top_below_band_hi:
        flags.append("top_below_band_hi")

    unresolved = [key for key, res in results.items() if res.unresolved]
    unresolved_reasons = [f"{key}={res.reason}" for key, res in results.items() if res.unresolved]
    gate_notes = [f"{key}={res.reason}" for key, res in results.items()
                  if not res.passed and res.reason]

    try:
        throat_w = float(shape["width_mm"]) if shape is not None else float("nan")
        throat_h = float(shape["height_mm"]) if shape is not None else float("nan")
        throat_round = float(shape["roundness"]) if shape is not None else float("nan")
    except (KeyError, TypeError, ValueError):
        throat_w = throat_h = throat_round = float("nan")

    return {
        "brief": meta["brief"],
        "cell": meta["cell"],
        "run": meta["run"],
        "tier": tier,
        "design": stored["design"],
        "family": stored["family"],
        "J": stored["J"],
        "f0": f_x,
        "f0_v": meta["f0_v"],
        "band_hi": band_hi,
        "coverage_h": coverage_h,
        "coverage_v": coverage_v,
        "h": h.passed,
        "v": v.passed,
        "di": di.passed,
        "bw8k": bw8k.gate.passed,
        "load": load.gate.passed,
        "throat": throat.passed,
        "pass_all": all(res.passed for res in results.values()),
        "unresolved": unresolved,
        "unresolved_reasons": unresolved_reasons,
        "flags": flags,
        "gate_notes": gate_notes,
        "lfp20_hz": load.lfp20_hz,
        "lfp50_hz": load.lfp50_hz,
        "lfp70_hz": load.lfp70_hz,
        "lfp20_note": load.lfp20_note,
        "rez_at_fx": load.rez_at_fx,
        "rez_min_from_fx": load.rez_min_from_fx,
        "di_rise_db": di.value if di.value is not None else float("nan"),
        "bwh_at_8k": bw8k.bw_h if bw8k.bw_h is not None else float("nan"),
        "bwv_at_8k": bw8k.bw_v if bw8k.bw_v is not None else float("nan"),
        "bw8k_at_hz": bw8k.freq_hz if bw8k.freq_hz is not None else float("nan"),
        "throat_w_mm": throat_w,
        "throat_h_mm": throat_h,
        "throat_round": throat_round,
        "throat_reason": throat.reason,
        "n_dof": stored["n_dof"],
        "seconds_total": stored["seconds_total"],
        # Internal arrays for the report table; ignored by the CSV writer.
        "_freqs": freqs,
        "_bw_h": stored["bw_h"],
        "_bw_v": stored["bw_v"],
    }


def collect(runs_root: Path, run_glob: str = "2026102[78]T*") -> tuple[list[dict], dict[str, int]]:
    """Walk the dated runs matching ``run_glob`` and audit every selected stored row.

    The default keeps the 2026-10-27/28 A1 evidence set; the D rerun passes
    ``--run-glob '20261029T*'`` so the new v5 runs are audited without mixing groups.
    """
    counters: Counter = Counter()
    shape_cache: dict = {}
    rows: list[dict] = []
    run_dirs = sorted(p for p in runs_root.glob(run_glob) if p.is_dir())
    counters["run_dirs"] = len(run_dirs)
    for run_dir in run_dirs:
        meta = read_run_meta(run_dir)
        if meta is None:
            counters["runs_without_meta"] += 1
            continue
        counters["runs"] += 1
        stored_rows = select_rows(
            read_ndjson(run_dir / "search.ndjson"),
            read_ndjson(run_dir / "verify" / "search.ndjson"),
        )
        counters[f"runs_with_verify" if (run_dir / "verify" / "search.ndjson").is_file()
                 else "runs_screen_only"] += 1
        for tier, stored in stored_rows:
            rows.append(audit_row(meta, stored, tier, run_dir, shape_cache, counters))
    counters["rows"] = len(rows)
    counters["unique_meshes_read"] = len(shape_cache)
    return rows, dict(counters)


def sort_rows(rows: list[dict]) -> list[dict]:
    """Deterministic order: brief, J, design (then run/tier to break duplicate-design ties)."""

    def key(r: dict):
        j = r.get("J")
        j_key = j if isinstance(j, (int, float)) and math.isfinite(j) else float("inf")
        return (r["brief"] or "", j_key, r["design"] or "", r["run"], r["tier"])

    return sorted(rows, key=key)


# ---------------------------------------------------------------- output


def _csv_cell(value: Any) -> Any:
    if isinstance(value, (list, tuple)):
        return ";".join(str(v) for v in value)
    if isinstance(value, bool):
        return "True" if value else "False"
    if value is None:
        return ""
    if isinstance(value, float) and not math.isfinite(value):
        return ""
    return value


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _csv_cell(row.get(field)) for field in CSV_FIELDS})


def _fmt(value: Any, digits: int = 3) -> str:
    try:
        x = float(value)
    except (TypeError, ValueError):
        return "n/a"
    return f"{x:.{digits}f}" if math.isfinite(x) else "n/a"


def _bw_at(row: dict, plane: str, hz: float) -> str:
    values = row["_bw_h"] if plane == "h" else row["_bw_v"]
    return _fmt(interp_log_f(row["_freqs"], values, hz), 1)


def _throat_str(row: dict) -> str:
    w, h = row.get("throat_w_mm"), row.get("throat_h_mm")
    if isinstance(w, (int, float)) and isinstance(h, (int, float)):
        if math.isfinite(float(w)) and math.isfinite(float(h)):
            return f"{float(w):.1f} x {float(h):.1f}"
    return "n/a"


def _unique_pass_all(rows: list[dict], limit: int = 10) -> tuple[list[dict], int]:
    """Best (lowest-J) row per design hash among pass_all rows, top ``limit`` by J."""
    best: dict[str, dict] = {}
    for row in rows:
        if not row["pass_all"]:
            continue
        design = row["design"]
        current = best.get(design)
        if current is None:
            best[design] = row
            continue
        candidate_key = (row["J"] if math.isfinite(row["J"]) else float("inf"),
                         row["run"], row["tier"])
        current_key = (current["J"] if math.isfinite(current["J"]) else float("inf"),
                       current["run"], current["tier"])
        if candidate_key < current_key:
            best[design] = row
    ordered = sorted(
        best.values(),
        key=lambda r: (r["J"] if math.isfinite(r["J"]) else float("inf"), r["design"],
                       r["run"], r["tier"]),
    )
    return ordered[:limit], len(ordered)


def write_readme(path: Path, rows: list[dict], counters: dict[str, int],
                 csv_path: Path) -> None:
    briefs = sorted({r["brief"] for r in rows})
    total_pass_all = sum(1 for r in rows if r["pass_all"])
    lines: list[str] = []
    lines.append("# Gate audit - stored runs 2026-10-27/28")
    lines.append("")
    lines.append("Generated by `tools/rescore/gate_audit.py` from `runs/2026102[78]T*` "
                 "(`search.ndjson`, plus `verify/search.ndjson` where present). Zero GPU, zero "
                 "solver. One row per audited stored row: inside a run, a design's verify rows "
                 "replace its screen rows; rows are never deduped across runs.")
    lines.append("")
    lines.append("## Canonical gates")
    lines.append("")
    lines.append(f"- `F_X` = the brief's `target.f0_hz`; `BAND_HI` = "
                 f"`min({HARD_BAND_HI_HZ:g}, target.band_hi_hz)`.")
    lines.append(f"- **H**: every solved f in [`F_X`, `BAND_HI`] has "
                 f"`|bw_h/coverage_h - 1| <= {H_TOL:g}`.")
    lines.append(f"- **V**: every solved f in [`max(1.5*F_X, f0_v)`, `BAND_HI`] has "
                 f"`{V_LO:g} <= bw_v/coverage_v <= {V_HI:g}`.")
    lines.append(f"- **DI**: `max(di_db) - min(di_db)` over [`F_X`, `BAND_HI`] <= "
                 f"{DI_RISE_MAX_DB:g} dB.")
    lines.append(f"- **BW8K**: at the highest solved f <= `BAND_HI`, "
                 f"`bw_h >= {BW8K_FLOOR:g}*coverage_h` and `bw_v >= {BW8K_FLOOR:g}*coverage_v`; "
                 "if `BAND_HI` is not solved the top frequency below it is used and "
                 "`top_below_band_hi` is flagged.")
    lines.append(f"- **Loading**: LFP20 (Re z crossing {LFP_RE_Z:g} from below, log-f "
                 f"interpolated) must satisfy `LFP20 * {LFP_CROSSOVER_RATIO:g} <= F_X`; Re z must "
                 f"stay >= {LOADED_RE_Z:g} at every solved f >= `F_X`. A grid whose first sample "
                 "is already above the threshold is resolved-low at the grid start.")
    lines.append(f"- **Throat**: `throat_check.throat_shape` + `fits_exit` on the solved mesh; "
                 f"width/height within {THROAT_TOL_MM:g} mm of the driver exit diameter and "
                 f"roundness within {ROUND_TOL:g} of 1.0. Missing/unreadable mesh is unresolved.")
    lines.append("- **pass_all** = H and V and DI and BW8K and Loading and Throat. "
                 "A gate with no evaluable sample/crossing/mesh is unresolved and FAILS.")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Count |")
    lines.append("|---|---:|")
    lines.append(f"| Dated run directories | {counters.get('run_dirs', 0)} |")
    lines.append(f"| Runs with a usable run.json | {counters.get('runs', 0)} |")
    lines.append(f"| Audited rows (CSV) | {len(rows)} |")
    lines.append(f"| Rows passing all gates | {total_pass_all} |")
    lines.append(f"| Unique pass_all designs | {len({r['design'] for r in rows if r['pass_all']})} |")
    lines.append(f"| Briefs | {len(briefs)} |")
    lines.append(f"| Meshes not locatable | {counters.get('mesh_source_missing', 0)} |")
    lines.append(f"| Meshes found via cache fallback | {counters.get('mesh_source_cache', 0)} |")
    lines.append(f"| Unique mesh shapes read | {counters.get('unique_meshes_read', 0)} |")
    lines.append(f"| CSV | `{csv_path.name}` |")
    lines.append("")
    if total_pass_all == 0:
        lines.append("**The overall pass_all set is empty.** No audited row passes all six gates.")
        lines.append("")

    lines.append("## Rows and gate passes per brief")
    lines.append("")
    lines.append("| Brief | Rows | Unique designs | H pass | V pass | DI pass | BW8K pass | "
                 "Loading pass | Throat pass | pass_all |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for brief in briefs:
        br = [r for r in rows if r["brief"] == brief]
        cells = [f"`{brief}`", str(len(br)), str(len({r['design'] for r in br}))]
        for key in GATE_KEYS:
            cells.append(str(sum(1 for r in br if r[key])))
        cells.append(str(sum(1 for r in br if r["pass_all"])))
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")

    lines.append("## Unresolved rows per gate")
    lines.append("")
    lines.append("| Gate | All rows | " + " | ".join(f"`{b}`" for b in briefs) + " |")
    lines.append("|---|---:|" + "---:|" * len(briefs))
    for key in GATE_KEYS:
        total = sum(1 for r in rows if key in r["unresolved"])
        per = [sum(1 for r in rows if r["brief"] == b and key in r["unresolved"]) for b in briefs]
        lines.append(f"| {GATE_LABELS[key]} | {total} | " + " | ".join(str(x) for x in per) + " |")
    lines.append("")
    lines.append("An unresolved gate has no evaluable sample, crossing or mesh, and therefore "
                 "fails. The reasons are in the CSV's `unresolved` / `unresolved_reasons` columns.")
    lines.append("")

    lines.append("## Top 10 unique pass_all designs by J, per brief")
    lines.append("")
    lines.append("Unique by `design` hash; when the same design appears in several runs the "
                 "lowest-J row is shown. Beamwidths are interpolated on the solved grid in log "
                 "frequency; `n/a` means outside the solved grid (no extrapolation).")
    lines.append("")
    for brief in briefs:
        br = [r for r in rows if r["brief"] == brief]
        top, n_unique = _unique_pass_all(br)
        lines.append(f"### `{brief}`")
        lines.append("")
        if not top:
            lines.append("_Empty set: no row for this brief passes all gates._")
            lines.append("")
            continue
        shown = "all" if len(top) == n_unique else f"top {len(top)} of {n_unique}"
        lines.append(f"{shown} unique pass_all designs (by J).")
        lines.append("")
        lines.append("| Rank | Design | J | LFP20 Hz | LFP50 Hz | LFP70 Hz | Re z @ f_x | "
                     "BW H f_x | BW H 2k | BW H 4k | BW H 8k | BW V f_x | BW V 2k | BW V 4k | "
                     "BW V 8k | DI rise dB | Throat W x H |")
        lines.append("|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
                     "---:|---:|---|")
        for rank, row in enumerate(top, 1):
            f_x = float(row["f0"])
            cells = [
                str(rank),
                f"`{row['design']}`",
                _fmt(row["J"], 4),
                _fmt(row["lfp20_hz"], 1),
                _fmt(row["lfp50_hz"], 1),
                _fmt(row["lfp70_hz"], 1),
                _fmt(row["rez_at_fx"], 3),
                _bw_at(row, "h", f_x),
                _bw_at(row, "h", 2000.0),
                _bw_at(row, "h", 4000.0),
                _bw_at(row, "h", 8000.0),
                _bw_at(row, "v", f_x),
                _bw_at(row, "v", 2000.0),
                _bw_at(row, "v", 4000.0),
                _bw_at(row, "v", 8000.0),
                _fmt(row["di_rise_db"], 3),
                _throat_str(row),
            ]
            lines.append("| " + " | ".join(cells) + " |")
        lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- CLI


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit stored runs against the canonical gates")
    parser.add_argument("--runs", type=Path, default=DEFAULT_RUNS_DIR,
                        help="runs directory (default: <repo>/runs)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_DIR,
                        help="output directory (default: docs/data/gate_audit_2026-10-29)")
    parser.add_argument("--run-glob", default="2026102[78]T*",
                        help="run-directory glob under --runs (default: 2026102[78]T*); "
                             "use '20261029T*' for the hardened D runs")
    args = parser.parse_args(argv)

    if not args.runs.is_dir():
        print(f"error: --runs {args.runs} is not a directory", file=sys.stderr)
        return 2

    rows, counters = collect(args.runs, args.run_glob)
    rows = sort_rows(rows)
    args.out.mkdir(parents=True, exist_ok=True)
    csv_path = args.out / "gate_audit.csv"
    readme_path = args.out / "README.md"
    write_csv(csv_path, rows)
    write_readme(readme_path, rows, counters, csv_path)

    per_brief = {}
    for brief in sorted({r["brief"] for r in rows}):
        br = [r for r in rows if r["brief"] == brief]
        per_brief[brief] = {
            "rows": len(br),
            "pass_all": sum(1 for r in br if r["pass_all"]),
            "pass": {k: sum(1 for r in br if r[k]) for k in GATE_KEYS},
            "unresolved": {k: sum(1 for r in br if k in r["unresolved"]) for k in GATE_KEYS},
        }
    summary = {
        "rows": len(rows),
        "runs": counters.get("runs", 0),
        "pass_all": sum(1 for r in rows if r["pass_all"]),
        "per_brief": per_brief,
        "unresolved": {k: sum(1 for r in rows if k in r["unresolved"]) for k in GATE_KEYS},
        "mesh": {k: counters.get(k, 0) for k in
                 ("mesh_source_design", "mesh_source_verify_design", "mesh_source_cache",
                  "mesh_source_missing", "unique_meshes_read")},
    }
    print(f"wrote {len(rows)} rows to {csv_path} and {readme_path}")
    print("SUMMARY " + json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
