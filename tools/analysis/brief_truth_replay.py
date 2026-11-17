"""Brief-truth replay and frequency-fidelity laboratory (master plan WP3, 2026-11-17).

Read-only, zero-GPU, zero-solver. Three cleanly separated uses:

1. ``identity`` - legacy identity replay. Load the stored CROWE and Klangfilm-Lame BEM
   responses (``designs/<hash>/response.npz``), re-derive metrics through the canonical run
   pathway (``search.evaluate.metrics_from_response`` via ``objective.replay.replay_run_dir``)
   and prove the captured J / weighted terms match the run's stored ``best.json`` at floating
   precision. Also reproduces the 2x2 November-17 brief re-score matrix.
2. ``scenarios`` - experimental v9 scoring view. Score stored designs under OFFLINE /
   NOT-QUEUED v9 corridor briefs (``scratch/home_v9_offline_2026-11-17``). The briefs are
   loaded only through the real config loader (``config.load_brief`` -> ``Target.from_dict``);
   nothing is queued and no production default changes.
3. ``grid`` - frequency-grid stability. Reuse ``tools/analysis/rescore_identity`` machinery
   (its ``floor_stats``) on stored screen/verify same-mesh pairs, then repeat each score on a
   common PCHIP-interpolated log grid (58 / 116 points, FABLE N3 method, through the canonical
   v9 ``objective.score_grid``). Interpolation does NOT create acoustic resolution.

Scoring rules enforced here (not re-implemented: every J is dispatched to the canonical scorer
by the replay adapter):

* ``pooled_ranking`` refuses to rank raw J across objective versions or across briefs
  (``CrossVersionRankingRefused``). Cross-target rescoring always regenerates target-dependent
  metrics from the response under the *new* target; stored ripple/diag/floor values are never
  reused (a dirty reuse raises ``ScoreRuleError``).
* ``refuse_bw8k_floor_under_v9`` refuses ``objective.bw8k_floor`` under v9 (typed
  ``ScoreRuleError``); an explicit ``hf_floor`` is a separate weighted term.
* No stored run/result is written. Every file read for a score is hashed before and after.

Usage::

    .venv\\Scripts\\python.exe tools/analysis/brief_truth_replay.py identity --out <dir>
    .venv\\Scripts\\python.exe tools/analysis/brief_truth_replay.py scenarios \\
        --briefs scratch/home_v9_offline_2026-11-17/*.yaml --out <dir>
    .venv\\Scripts\\python.exe tools/analysis/brief_truth_replay.py grid \\
        --brief scratch/home_v9_offline_2026-11-17/home_v9_corridor_h90_70_v1000.yaml \\
        --runs runs/study-* --out <dir>
"""
from __future__ import annotations

import argparse
import csv
import dataclasses
import hashlib
import json
import math
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

TOOL = "brief_truth_replay"
TOOL_VERSION = "1.0.0"

BRIEF_DIR = REPO_ROOT / "examples" / "briefs" / "home_landscape_2026-11-15"
BASE_BRIEF = BRIEF_DIR / "room_landscape_80x50_700_hf1440_v7.yaml"
SMOOTH_BRIEF = BRIEF_DIR / "room_landscape_80x50_700_hf1440_v7_smooth.yaml"
CANDIDATE_DIR = REPO_ROOT / "scratch" / "home_v9_offline_2026-11-17"

#: The two named best non-CD designs (docs/evidence/CROWE_KLANGFILM_BRIEF_RESCORE_2026-11-17.md).
LEGACY_DESIGNS = (
    {"label": "crowe_es600", "run": "runs/20261115T205453Z-screen-32f7c4",
     "design_hash": "22365b569be9", "own_cell": "base"},
    {"label": "klangfilm_lame", "run": "runs/20261116T225543Z-screen-6acf41",
     "design_hash": "491efb2132b8", "own_cell": "smooth"},
)

#: Rounded J values printed in the November-17 report (section 1); the two own-brief cells are
#: the identity replays. Used only as a provenance cross-check.
NOV17_REPORT_J = {
    ("crowe_es600", "base"): 16.918176,
    ("crowe_es600", "smooth"): 6.836182,
    ("klangfilm_lame", "base"): 22.782312,
    ("klangfilm_lame", "smooth"): 8.923617,
}
NOV17_J_TOL = 1.0e-5

#: Relative J tolerance for the identity replay (the report achieved an exact zero delta).
IDENTITY_REL_TOL = 1.0e-9
#: Term-level tolerance for the identity replay.
IDENTITY_TERM_TOL = 1.0e-9

BW8K_HZ = 8000.0


# ------------------------------------------------------------------ typed refusals


class ScoreRuleError(RuntimeError):
    """A requested score would violate a pinned scoring rule (e.g. bw8k_floor under v9)."""


class CrossVersionRankingRefused(RuntimeError):
    """Raw J is not a common ranking across objective versions or across different briefs."""


class IdentityReplayError(RuntimeError):
    """The canonical pathway did not reproduce a stored captured J."""


def refuse_bw8k_floor_under_v9(version: int, objective_block: dict | None) -> None:
    """Refuse ``objective.bw8k_floor`` under v9 (amended RFC 2026-11-17, section C).

    v9's coverage-profile ``min_deg`` is the narrow-side HF constraint; a second
    ``0.75 * flat`` floor would double-charge narrowing. The explicit, independently weighted
    ``hf_floor`` mapping is the only HF penalty v9 accepts.
    """
    if int(version) != 9 or not isinstance(objective_block, dict):
        return
    if "bw8k_floor" in objective_block:
        raise ScoreRuleError(
            "objective.bw8k_floor is refused under objective v9: the coverage-profile min_deg is "
            "the narrow-side HF constraint. Declare objective.hf_floor "
            "{hz, h_deg, v_deg, weight, tolerance} for a separate HF penalty.")
    allowed = {"version", "tolerances", "cov_narrow_ratio", "cov_below_f0", "cov_v_weight",
               "flat_band", "loaded_re_z", "lfp_re_z", "lfp_crossover_ratio", "hf_floor",
               "constancy", "score_grid", "ripple_window", "oa_excess_tol"}
    unknown = set(objective_block) - allowed
    if unknown:
        raise ScoreRuleError(f"objective v9 block carries unknown key(s) {sorted(unknown)} "
                             f"(allowed: {sorted(allowed)})")


def pooled_ranking(rows: list[dict]) -> list[dict]:
    """Rank rows by raw J WITHIN ONE brief and ONE objective version, or refuse.

    A cross-version or cross-brief "leaderboard" is a different objective, not a ranking:
    tolerances, weights, targets and slope goals all move. Use one brief's column per
    comparison. This is the only ranking entry point in this tool.
    """
    usable = [r for r in rows if r.get("J") is not None]
    if not usable:
        return []
    versions = sorted({int(r["objective_version"]) for r in usable})
    briefs = sorted({str(r["brief_hash"]) for r in usable})
    if len(versions) > 1 or len(briefs) > 1:
        names = sorted({str(r.get("brief_name")) for r in usable})
        raise CrossVersionRankingRefused(
            "raw J is not a common ranking across objective versions or briefs: "
            f"versions={versions}, {len(briefs)} distinct brief hash(es), names={names}. "
            "Compare only the same-brief column, or decompose the terms.")
    return sorted(usable, key=lambda r: (float(r["J"]), str(r.get("design_hash") or "")))


def rank_within_brief(rows: list[dict]) -> None:
    """Attach ``rank_in_brief`` to each scored row; refuses a mixed version within one brief."""
    groups: dict[str, list[dict]] = {}
    for r in rows:
        if r.get("J") is None:
            continue
        groups.setdefault(str(r["brief_hash"]), []).append(r)
    for group in groups.values():
        if len({int(r["objective_version"]) for r in group}) > 1:
            raise CrossVersionRankingRefused("one brief hash maps to several objective versions")
        for i, r in enumerate(sorted(group, key=lambda x: float(x["J"])), start=1):
            r["rank_in_brief"] = i


# ------------------------------------------------------------------ zero-backend guard


class BackendGuard:
    """Patch every solver/backend factory and store writer so a call raises and is counted."""

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

    def __init__(self) -> None:
        self.calls = 0
        self.names: list[str] = []
        self.installed: list[str] = []
        self._stack: list = []

    def _forbidden(self, name: str):
        def _raise(*_args, **_kwargs):
            self.calls += 1
            self.names.append(name)
            raise RuntimeError(f"{TOOL}: forbidden backend/store call: {name}")
        return _raise

    @contextmanager
    def active(self):
        import importlib
        import unittest.mock as mock

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
        try:
            yield self
        finally:
            for patcher in reversed(self._stack):
                patcher.stop()
            self._stack = []


# ------------------------------------------------------------------ provenance / io


def _git(*args: str) -> str | None:
    import subprocess

    try:
        out = subprocess.run(["git", *args], cwd=str(REPO_ROOT), capture_output=True,
                             text=True, check=False)
    except Exception:  # noqa: BLE001 - provenance is best-effort, never fatal
        return None
    return out.stdout if out.returncode == 0 else None


def provenance() -> dict:
    head = _git("rev-parse", "HEAD")
    porcelain = _git("status", "--porcelain")
    return {
        "tool": TOOL,
        "tool_version": TOOL_VERSION,
        "captured_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repo_head": None if head is None else head.strip(),
        "dirty_tree": [] if porcelain is None else porcelain.splitlines(),
        "labels": "[measured] stored BEM responses; [derived] recomputed metrics/scores; "
                  "[proposed] v9 candidate briefs; [unavailable] anything not stored",
    }


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _source_hashes(paths) -> dict[str, str]:
    out: dict[str, str] = {}
    for p in sorted({Path(x) for x in paths}):
        if p.is_file():
            try:
                key = str(p.relative_to(REPO_ROOT))
            except ValueError:                 # a caller-supplied temp run outside the repo
                key = str(p)
            out[key] = _sha256(p)
    return out


def _assert_sources_unchanged(before: dict[str, str]) -> dict:
    after = _source_hashes([REPO_ROOT / Path(k) for k in before])
    changed = sorted(k for k in before if before[k] != after.get(k))
    if changed:
        raise RuntimeError(f"{TOOL}: stored source file(s) changed during the read-only run: "
                           f"{changed}")
    return {"files": len(before), "unchanged": True, "sha256": before}


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _clean(obj):
    if isinstance(obj, dict):
        return {str(k): _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return _clean(obj.tolist())
    if isinstance(obj, (np.floating, np.integer, np.bool_)):
        return _clean(obj.item())
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    return obj


def _finite(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _config_for_response(path: Path):
    """The ``config.yaml`` that a stored response belongs to, if any (read-only lookup)."""
    for parent in (path.parent, path.parent.parent, path.parent.parent.parent):
        cand = parent / "config.yaml"
        if cand.is_file():
            return cand
    return None


def _run_read_paths(run_dir: Path, design_hash: str) -> list[Path]:
    """Every stored manifest/result this tool may read for one run-dir design.

    Hashed BEFORE any of them is opened, so the zero-write guard genuinely covers the run.
    """
    paths = [run_dir / "best.json", run_dir / "run.json", run_dir / "config.yaml"]
    ddir = _design_dir(run_dir, design_hash)
    if ddir is not None:
        for name in ("response.npz", "metrics.json", "design.json", "status.json",
                     "mesh_meta.json", "mesh.msh"):
            paths.append(ddir / name)
    return [p for p in paths if p.is_file()]


def _term_residuals(stored_terms: dict, result_terms: dict) -> dict[str, float]:
    """Per-term identity residuals; refuses a vacuous pass when nothing is comparable.

    A stored ``best.json`` with no ``terms`` block (or one whose keys do not overlap the replay
    result) must fail loudly.  ``max(|residual|)`` over an empty set is 0.0, which would otherwise
    look like an exact reproduction without comparing a single term.
    """
    compared = {
        str(k): float(v) for k, v in stored_terms.items()
        if k in result_terms and _finite(v) is not None and _finite(result_terms[k]) is not None
    }
    if not compared:
        raise IdentityReplayError(
            "stored best.json carries no comparable term (expected a non-empty `terms` block "
            "overlapping the replay terms); refusing a vacuous identity pass")
    return {k: float(result_terms[k]) - v for k, v in compared.items()}


# ------------------------------------------------------------------ brief + design loading


def _load_brief(path):
    from hornlab_search.objective.replay import load_brief_context

    brief = load_brief_context(path)
    refuse_bw8k_floor_under_v9(brief.objective_version, brief.objective_block)
    return brief


def _brief_target_raw(brief) -> dict:
    raw = brief.raw or {}
    if isinstance(raw.get("brief"), dict):
        raw = raw["brief"]
    target = raw.get("target") if isinstance(raw, dict) else None
    return dict(target) if isinstance(target, dict) else dataclasses.asdict(brief.target)


def _resolve_weights(brief) -> dict:
    from hornlab_search.objective.scalar_v7 import resolve_v7_weights
    from hornlab_search.objective.scalar_v9 import resolve_v9_weights

    if brief.objective_version == 9:
        return resolve_v9_weights(brief.weights, brief.objective_params)
    if brief.objective_version == 7:
        return resolve_v7_weights(brief.weights)
    raise ScoreRuleError(f"brief_truth_replay scores objective v7 and v9 only; got "
                         f"v{brief.objective_version}")


def _weighted_keys(brief) -> tuple[str, ...]:
    from hornlab_search.objective.scalar_v7 import V7_WEIGHTED_KEYS

    if brief.objective_version == 9:
        return tuple(brief.objective_params.weighted_keys())
    if brief.objective_version == 7:
        return tuple(V7_WEIGHTED_KEYS)
    raise ScoreRuleError(f"unsupported objective version {brief.objective_version}")


def _tolerance(brief, key: str):
    params = brief.objective_params
    if key == "hf_floor" and getattr(params, "hf_floor", None) is not None:
        return float(params.hf_floor["tolerance"])
    if key == "constancy" and getattr(params, "constancy", None) is not None:
        return float(params.constancy["tolerance"])
    tol = getattr(params, "tolerances", {}) or {}
    return None if tol.get(key) is None else float(tol[key])


def _design_dir(run_dir: Path, design_hash: str):
    for cand in (run_dir / "designs" / design_hash, run_dir / "verify" / "designs" / design_hash):
        if cand.is_dir():
            return cand
    return None


def _response_path(run_dir: Path, design_hash: str):
    ddir = _design_dir(run_dir, design_hash)
    if ddir is None:
        return None
    rp = ddir / "response.npz"
    return rp if rp.is_file() else None


def _parse_design_spec(spec: str) -> dict:
    label, sep, rest = spec.partition("=")
    run, sep2, h = rest.rpartition(":")
    if not sep or not sep2 or not label or not run or not h:
        raise ScoreRuleError(f"--design expects LABEL=RUN_DIR:DESIGN_HASH, got {spec!r}")
    return {"label": label, "run": run, "design_hash": h, "own_cell": None}


def _default_designs() -> list[dict]:
    return [dict(d) for d in LEGACY_DESIGNS]


# ------------------------------------------------------------------ metrics / facts


def _metrics_for_facts(resp, brief):
    """Metrics on the scored grid, through the canonical production entry point."""
    from hornlab_search.search.evaluate import metrics_from_response

    return metrics_from_response(resp, brief.target)


def _bw8k_measured(metrics, target):
    f = np.asarray(metrics.freqs_hz, dtype=float)
    cap = min(BW8K_HZ, float(target.band_hi_hz))
    below = np.nonzero(f <= cap)[0]
    if below.size == 0:
        return None
    i = int(below[-1])
    return {
        "hz": float(f[i]),
        "bw_h_deg": _finite(np.asarray(metrics.bw_h_deg, dtype=float)[i]),
        "bw_v_deg": _finite(np.asarray(metrics.bw_v_deg, dtype=float)[i]),
    }


def _bw8k_condition(version: int, floor, bw8k) -> str:
    if version == 9:
        base = ("objective.bw8k_floor refused under v9; the corridor min_deg is the HF "
                "narrow-side constraint; no hf_floor declared")
        if bw8k is None:
            return base
        return (f"{base}; measured (unscored) BW @ {bw8k['hz']:g} Hz = "
                f"{bw8k['bw_h_deg']:.2f} H / {bw8k['bw_v_deg']:.2f} V deg")
    if floor is None:
        return "no bw8k_floor in this objective block"
    return (f"floor {floor['floor_h_deg']:.2f}/{floor['floor_v_deg']:.2f} deg at "
            f"{floor['floor_hz']:g} Hz vs measured {floor['min_bw_h_deg']:.2f}/"
            f"{floor['min_bw_v_deg']:.2f} deg; raw penalty {floor['penalty_raw']:.6f} rides "
            "inside cov")


def target_facts(metrics, brief) -> dict:
    """Read-only restatement of the scoring truth via ``targets.scoring_view``."""
    from hornlab_search.targets import scoring_view as sv

    version = brief.objective_version
    raw_t = _brief_target_raw(brief)
    raw_o = brief.objective_block or {}
    target = brief.target
    params = brief.objective_params
    weights = _resolve_weights(brief)

    win = sv.score_window(raw_t, raw_o, version)
    di = sv.di_summary(raw_t, brief.weights, version)
    diag = sv.diag_summary(raw_t, brief.weights)
    floor = None
    if version != 9:
        floor = sv.bw8k_floor(raw_t, raw_o, version, metrics.freqs_hz, metrics.bw_h_deg,
                              metrics.bw_v_deg)

    f = np.asarray(metrics.freqs_hz, dtype=float)
    band = (f >= target.band_lo_hz) & (f <= target.band_hi_hz)
    lo = None if win is None else win["h_lo_hz"]
    measured_slope = sv.measured_di_slope(f[band], np.asarray(metrics.di_db, dtype=float)[band], lo)

    profile_at_freq = None
    if version == 9 and target.coverage_profile_h and target.coverage_profile_v:
        from hornlab_search.targets.profile import profile_onset_hz, profile_value

        f0 = target.f0_effective_hz()
        f0_v = float(target.f0_v_hz) if target.f0_v_hz is not None else f0
        onset_h = profile_onset_hz(target.coverage_profile_h, f0)
        onset_v = profile_onset_hz(target.coverage_profile_v, f0_v)
        profile_at_freq = []
        for fq in f[band]:
            ph, h_lo, h_hi = profile_value(target.coverage_profile_h, float(fq))
            pv, v_lo, v_hi = profile_value(target.coverage_profile_v, float(fq))
            profile_at_freq.append({
                "hz": float(fq),
                "h_pref_deg": float(ph) if float(fq) >= onset_h else None,
                "h_min_deg": None if h_lo is None else float(h_lo),
                "h_max_deg": None if h_hi is None else float(h_hi),
                "v_pref_deg": float(pv) if float(fq) >= onset_v else None,
                "v_min_deg": None if v_lo is None else float(v_lo),
                "v_max_deg": None if v_hi is None else float(v_hi),
            })

    bw8k = _bw8k_measured(metrics, target)
    return {
        "score_window": win,
        "cov_v_weight": float(getattr(params, "cov_v_weight", 1.0)),
        "flat_band": getattr(params, "flat_band", None),
        "cov_narrow_ratio": None if win is None else win["narrow_ratio"],
        "below_mode": None if win is None else win["below_mode"],
        "onset_h_hz": None if win is None else win["h_lo_hz"],
        "onset_v_hz": None if win is None else win["v_lo_hz"],
        "di": di,
        "diag": diag,
        "diag_scored": bool(diag["scored"]) if diag else False,
        "distd_weighted": float(weights.get("distd", 0.0)),
        "measured_di_slope_db_per_dec": measured_slope,
        "di_slope_target": None if di is None else di["slope_db_per_dec"],
        "bw8k": bw8k,
        "bw8k_floor": floor,
        "bw8k_condition": _bw8k_condition(version, floor, bw8k),
        "n_solved_in_band": int(band.sum()),
        "n_scored_cov_h": (None if win is None
                           else int((band & (f >= win["h_lo_hz"])).sum())),
        "n_scored_cov_v": (None if win is None
                           else int((band & (f >= win["v_lo_hz"])).sum())),
        "solved_freqs_in_band_hz": f[band].tolist(),
        "n_solved_total": int(f.size),
        "solved_freqs_hz": f.tolist(),
        "target_profile_at_solved_hz": profile_at_freq,
    }


def term_table(brief, terms: dict) -> list[dict]:
    """Raw / weight / tolerance / normalized / contribution for every scored key."""
    version = brief.objective_version
    weights = _resolve_weights(brief)
    rows = []
    for key in _weighted_keys(brief):
        norm = _finite(terms.get(key))
        tol = _tolerance(brief, key)
        w = float(weights.get(key, 0.0))
        raw = None if (norm is None or tol is None) else norm * tol
        rows.append({
            "key": key, "raw": raw, "weight": w, "tolerance": tol,
            "normalized": norm, "contribution": None if norm is None else w * norm,
            "unweighted_raw": False,
        })
    for key in ("diag", "distd"):
        if version == 9 and key in terms:
            rows.append({"key": key, "raw": _finite(terms.get(key)), "weight": 0.0,
                         "tolerance": None, "normalized": None, "contribution": 0.0,
                         "unweighted_raw": True})
    return rows


# ------------------------------------------------------------------ replay cell


def _replay(run_dir: Path, design_hash: str, brief, *, config_path=None):
    from hornlab_search.objective.replay import replay_run_dir

    cfg = Path(config_path) if config_path is not None else run_dir / "config.yaml"
    result = replay_run_dir(run_dir, design_hash, brief=brief,
                            config_path=(cfg if cfg.is_file() else None),
                            regenerate_metrics=True)
    if result.diagnostics.get("target_changed") and result.diagnostics.get("stored_metrics_used"):
        raise ScoreRuleError(
            "refusing a cross-target cell that reused stored ripple/diag/floor metrics")
    return result


def build_cell(resp, brief, result, *, label: str, design_hash: str, run_dir: Path,
               source: str, grid: str = "solved", stored_j=None) -> dict:
    metrics = _metrics_for_facts(resp, brief)
    facts = target_facts(metrics, brief)
    return {
        "label": label,
        "design_hash": design_hash,
        "run_dir": str(Path(run_dir)),
        "source": source,
        "brief_name": brief.name,
        "brief_path": brief.source_path,
        "brief_hash": brief.brief_hash()[:16],
        "objective_version": int(brief.objective_version),
        "grid": grid,
        "grid_points": None,
        "status": result.status,
        "reasons": list(result.reasons),
        "J": _finite(result.j),
        "stored_J": _finite(stored_j if stored_j is not None else result.stored_j),
        "parity_delta": _finite(result.parity_delta),
        "metrics_recomputed": not bool(result.diagnostics.get("stored_metrics_used")),
        "target_changed": bool(result.diagnostics.get("target_changed")),
        "score_id": result.score_id,
        "terms": term_table(brief, dict(result.terms or {})),
        "facts": facts,
    }


def _cell_rank_rows(cell: dict) -> dict:
    """Flat CSV row (one per design x brief x grid)."""
    f = cell["facts"]
    di = f["di"] or {}
    return {
        "brief": cell["brief_name"],
        "brief_hash": cell["brief_hash"],
        "objective_version": cell["objective_version"],
        "design": cell["label"],
        "design_hash": cell["design_hash"],
        "run_dir": cell["run_dir"],
        "source": cell["source"],
        "grid": cell["grid"],
        "grid_points": cell["grid_points"],
        "status": cell["status"],
        "J": cell["J"],
        "stored_J": cell["stored_J"],
        "parity_delta": cell["parity_delta"],
        "rank_in_brief": cell.get("rank_in_brief"),
        "metrics_recomputed": cell["metrics_recomputed"],
        "target_changed": cell["target_changed"],
        "cov_v_weight": f["cov_v_weight"],
        "flat_band": f["flat_band"],
        "cov_narrow_ratio": f["cov_narrow_ratio"],
        "below_mode": f["below_mode"],
        "onset_h_hz": f["onset_h_hz"],
        "onset_v_hz": f["onset_v_hz"],
        "di_source": di.get("level_source"),
        "di_level_db": _finite(di.get("level_db")),
        "di_level_scored": bool(di.get("level_scored")),
        "di_slope_target_db_per_dec": f["di_slope_target"],
        "measured_di_slope_db_per_dec": f["measured_di_slope_db_per_dec"],
        "diag_reference_deg": None if not f["diag"] else f["diag"]["reference_deg"],
        "diag_scored": f["diag_scored"],
        "distd_weight": f["distd_weighted"],
        "bw8k_hz": None if not f["bw8k"] else f["bw8k"]["hz"],
        "bw8k_h_deg": None if not f["bw8k"] else f["bw8k"]["bw_h_deg"],
        "bw8k_v_deg": None if not f["bw8k"] else f["bw8k"]["bw_v_deg"],
        "bw8k_condition": f["bw8k_condition"],
        "n_solved_total": f["n_solved_total"],
        "n_solved_in_band": f["n_solved_in_band"],
        "n_scored_cov_h": f["n_scored_cov_h"],
        "n_scored_cov_v": f["n_scored_cov_v"],
    }


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_clean(payload), indent=2, sort_keys=True), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _print_cell(cell: dict) -> None:
    f = cell["facts"]
    di_src = (f["di"] or {}).get("level_source")
    print(f"{cell['label']:<16} {cell['brief_name']:<42} v{cell['objective_version']} "
          f"J={cell['J']!s:<20} status={cell['status']}")
    print(f"  cov_v_weight={f['cov_v_weight']:g} flat_band={f['flat_band']} "
          f"below={f['below_mode']} narrow={f['cov_narrow_ratio']} "
          f"onsetH={f['onset_h_hz']} onsetV={f['onset_v_hz']} "
          f"di_src={di_src if di_src else 'none(v9 has no scored DI level)'} "
          f"di_slope_tgt={f['di_slope_target']} measured_slope="
          f"{_finite(f['measured_di_slope_db_per_dec'])}")
    print(f"  diag_scored={f['diag_scored']} distd_weight={f['distd_weighted']:g} "
          f"n_in_band={f['n_solved_in_band']} n_cov_H={f['n_scored_cov_h']} "
          f"n_cov_V={f['n_scored_cov_v']}")
    print(f"  8k: {f['bw8k_condition']}")
    contrib = {r["key"]: r["contribution"] for r in cell["terms"]}
    print("  contributions: " + json.dumps(
        {k: (None if v is None else round(float(v), 6)) for k, v in contrib.items()},
        sort_keys=True))


# ------------------------------------------------------------------ identity


def _load_best(run_dir: Path) -> dict:
    for name in ("best.json", "run.json"):
        payload = _read_json(run_dir / name)
        if payload:
            return payload
    return {}


def identity(out: Path, designs: list[dict], prov: dict | None = None) -> dict:
    from hornlab_search.objective.replay import brief_from_config
    from hornlab_search.solve.cache import load_response

    prov = prov or provenance()
    briefs = {"base": _load_brief(BASE_BRIEF), "smooth": _load_brief(SMOOTH_BRIEF)}

    loaded, identity_rows = {}, []
    planned, read_paths = [], []
    for design in designs:
        run_dir = (REPO_ROOT / design["run"]).resolve()
        h = design["design_hash"]
        rp = _response_path(run_dir, h)
        if rp is None:
            raise FileNotFoundError(f"identity: no stored response for {design['label']} "
                                    f"({run_dir} / {h})")
        read_paths.append(rp)
        read_paths.extend(_run_read_paths(run_dir, h))
        planned.append((design, run_dir, h, rp))

    # Snapshot EVERY stored file before any response/best/config read.  A post-hoc hash cannot
    # prove the read-only guard held during the run.
    before = _source_hashes(read_paths)
    for design, run_dir, h, rp in planned:
        resp = load_response(rp)
        if resp.spl_balloon_db is None or resp.balloon_dirs is None:
            raise IdentityReplayError(f"{design['label']}: stored response carries no balloon; "
                                      "balloon-derived DI is required")
        loaded[design["label"]] = (run_dir, h, resp, rp)

    for design in designs:
        run_dir, h, resp, rp = loaded[design["label"]]
        best = _load_best(run_dir)
        stored_j = _finite(best.get("objective"))
        if stored_j is None:
            raise IdentityReplayError(f"{design['label']}: stored best.json carries no objective")
        stored_terms = dict(best.get("terms") or {})
        if not stored_terms:
            raise IdentityReplayError(
                f"{design['label']}: stored best.json carries no `terms` block; identity would "
                "pass vacuously without comparing a term")
        own = brief_from_config(run_dir / "config.yaml")
        result = _replay(run_dir, h, own, config_path=run_dir / "config.yaml")
        if result.status != "exact_complete" or result.j is None:
            raise IdentityReplayError(f"{design['label']}: own-brief replay status "
                                      f"{result.status} ({result.reasons})")
        delta = float(result.j) - float(stored_j)
        rel = abs(delta) / max(abs(float(stored_j)), 1.0)
        term_resid = _term_residuals(stored_terms, dict(result.terms or {}))
        max_term = max(abs(x) for x in term_resid.values())
        ok = abs(delta) <= IDENTITY_REL_TOL * max(abs(float(stored_j)), 1.0) \
            and max_term <= IDENTITY_TERM_TOL
        print(f"[identity] {design['label']}: recomputed J = {float(result.j):.15f}  "
              f"stored = {float(stored_j):.15f}  delta = {delta:+.3e} "
              f"(rel {rel:.3e})  max|term delta| = {max_term:.3e}  -> "
              f"{'PASS' if ok else 'FAIL'}")
        if not ok:
            raise IdentityReplayError(
                f"identity replay FAILED for {design['label']}: delta {delta:+.3e}, "
                f"max term delta {max_term:.3e}. Diagnose provenance; never paper over it.")
        identity_rows.append({
            "design": design["label"], "design_hash": h, "run_dir": str(run_dir),
            "own_brief": own.name, "recomputed_J": float(result.j),
            "stored_J": float(stored_j), "delta": delta, "relative_delta": rel,
            "max_abs_term_delta": max_term, "term_deltas": term_resid,
            "status": result.status, "metrics_recomputed": True, "passed": ok,
            "response_sha256": before[str(rp.relative_to(REPO_ROOT))],
        })

    # ---- 2x2 reproduction of the November-17 report -------------------------------------
    matrix: dict = {}
    cells: list[dict] = []
    for design in designs:
        run_dir, h, resp, _rp = loaded[design["label"]]
        stored_j = _finite(_load_best(run_dir).get("objective"))
        for key, brief in briefs.items():
            result = _replay(run_dir, h, brief, config_path=run_dir / "config.yaml")
            cell = build_cell(resp, brief, result, label=design["label"], design_hash=h,
                              run_dir=run_dir, source=f"nov17:{key}", stored_j=stored_j)
            cells.append(cell)
            matrix.setdefault(design["label"], {})[key] = cell
            expected = NOV17_REPORT_J[(design["label"], key)]
            if abs(float(result.j) - expected) > NOV17_J_TOL:
                raise IdentityReplayError(
                    f"does not reproduce the Nov-17 report for {design['label']}/{key}: "
                    f"{float(result.j):.6f} vs {expected:.6f} (> {NOV17_J_TOL:.0e}). "
                    "Stop and diagnose provenance.")

    for design in designs:
        own_cell = design.get("own_cell")
        if own_cell:
            cell = matrix[design["label"]][own_cell]
            if abs(float(cell["J"]) - float(_finite(_load_best((REPO_ROOT / design["run"]).resolve())
                                                     .get("objective")))) > IDENTITY_REL_TOL:
                raise IdentityReplayError(f"2x2 own cell {design['label']}/{own_cell} drifted")
    rank_within_brief(cells)

    print()
    print("=" * 104)
    print("2x2 NOVEMBER-17 BRIEF RE-SCORE (J per design x brief; a same-brief column is the only "
          "rank)")
    print("=" * 104)
    print(f"{'design':<16} {'base':>16} {'smooth':>16}   {'own cell':>10}")
    for design in designs:
        by = matrix[design["label"]]
        print(f"{design['label']:<16} {by['base']['J']:>16.6f} {by['smooth']['J']:>16.6f}   "
              f"{(design.get('own_cell') or '-'):>10}")

    guard = _assert_sources_unchanged(before)

    term_rows = [{**_cell_rank_rows(c), **row} for c in cells for row in c["terms"]]
    payload = {
        "provenance": prov,
        "identity_tolerance_relative": IDENTITY_REL_TOL,
        "identity_tolerance_term": IDENTITY_TERM_TOL,
        "identity": identity_rows,
        "reproduced_nov17": True,
        "matrix": {label: {k: {"J": v["J"], "status": v["status"]} for k, v in by.items()}
                   for label, by in matrix.items()},
        "cells": cells,
        "source_guard": guard,
    }
    _write_json(out / "identity_replay.json", payload)
    _write_csv(out / "identity_terms.csv", term_rows)
    _write_csv(out / "identity_cells.csv", [_cell_rank_rows(c) for c in cells])
    print(f"\nwrote {out / 'identity_replay.json'}")
    return payload


# ------------------------------------------------------------------ scenarios


def _replay_response_file(path: Path, brief):
    """Score one bare ``response.npz`` through the canonical run-dir replay adapter.

    The stored response arrays carry ``meta['balloon_grid']``; replaying through the canonical
    adapter keeps the production sin(theta) DI quadrature (calling ``compute_metrics`` on the raw
    theta-phi balloon would be ~7 dB wrong). The file is copied into a temporary run-dir layout
    and never written in place; a bare response has no stored J, so the cell is diagnostic.
    """
    import shutil
    import tempfile

    from hornlab_search.objective.replay import replay_run_dir

    cfg = _config_for_response(path)
    with tempfile.TemporaryDirectory(prefix="btr_response_") as tmp:
        ddir = Path(tmp) / "designs" / path.parent.name
        ddir.mkdir(parents=True)
        shutil.copy2(path, ddir / "response.npz")
        return replay_run_dir(Path(tmp), path.parent.name, brief=brief,
                              config_path=cfg, regenerate_metrics=True)


def scenarios(brief_paths, designs: list[dict], out: Path, prov: dict | None = None) -> dict:
    from hornlab_search.solve.cache import load_response

    prov = prov or provenance()
    briefs = [_load_brief(p) for p in brief_paths]

    # ---- hash every store BEFORE opening any response / best.json / metrics.json
    prepared, read_paths, cells = [], [], []
    for design in designs:
        bare = design.get("response")
        if bare:
            rp = Path(bare)
            if not rp.is_file():
                raise FileNotFoundError(f"scenarios: no response file at {rp}")
            read_paths.append(rp)
            cfg = _config_for_response(rp)
            if cfg is not None:
                read_paths.append(cfg)
            prepared.append({"kind": "bare", "design": design, "rp": rp,
                             "run_dir": rp.parent,
                             "design_hash": str(design.get("design_hash") or rp.parent.name)})
            continue
        run_dir = (REPO_ROOT / design["run"]).resolve()
        h = design["design_hash"]
        rp = _response_path(run_dir, h)
        if rp is None:
            raise FileNotFoundError(f"scenarios: no stored response for {design['label']}")
        read_paths.append(rp)
        read_paths.extend(_run_read_paths(run_dir, h))
        prepared.append({"kind": "run", "design": design, "rp": rp, "run_dir": run_dir,
                         "design_hash": h})

    before = _source_hashes(read_paths)

    for item in prepared:
        design, rp = item["design"], item["rp"]
        run_dir, h = item["run_dir"], item["design_hash"]
        resp = load_response(rp)
        if item["kind"] == "bare":
            for brief in briefs:
                result = _replay_response_file(rp, brief)
                cells.append(build_cell(resp, brief, result, label=design["label"],
                                        design_hash=h, run_dir=run_dir,
                                        source="v9-scenario-file", stored_j=None))
            continue
        stored_j = _finite(_load_best(run_dir).get("objective"))
        for brief in briefs:
            result = _replay(run_dir, h, brief, config_path=run_dir / "config.yaml")
            cells.append(build_cell(resp, brief, result, label=design["label"], design_hash=h,
                                    run_dir=run_dir, source="v9-scenario",
                                    stored_j=stored_j))

    rank_within_brief(cells)
    print("=" * 104)
    print("v9 OFFLINE / NOT-QUEUED SCENARIO MATRIX (stored responses unchanged)")
    print("=" * 104)
    for cell in cells:
        _print_cell(cell)

    # Never pool across briefs: demonstrate the typed refusal on this very matrix.
    refused = None
    if len(briefs) > 1:
        try:
            pooled_ranking(cells)
        except CrossVersionRankingRefused as exc:
            refused = str(exc)
        if refused is None:
            raise ScoreRuleError("cross-brief pooling was not refused; this is a tool bug")
        print("\n[cross-brief pooled ranking] REFUSED: " + refused)
    else:
        print("\n[cross-brief pooled ranking] single brief: same-brief ranking only")

    term_rows = [{**_cell_rank_rows(c), **row} for c in cells for row in c["terms"]]
    guard = _assert_sources_unchanged(before)
    _write_json(out / "replay_matrix.json", {"provenance": prov, "cells": cells,
                                             "cross_brief_ranking_refused": refused,
                                             "source_guard": guard})
    _write_csv(out / "replay_matrix.csv", [_cell_rank_rows(c) for c in cells])
    _write_csv(out / "replay_terms.csv", term_rows)
    print(f"\nwrote {out / 'replay_matrix.json'}, replay_matrix.csv, replay_terms.csv")
    return {"cells": cells, "source_guard": guard,
            "cross_brief_ranking_refused": refused}


# ------------------------------------------------------------------ grid stability


def _pair_sides(run_dir: Path):
    """Return (screen_dir, verify_dir) for a run, supporting both stored layouts."""
    if (run_dir / "designs").is_dir() and (run_dir / "verify" / "designs").is_dir():
        return run_dir, run_dir / "verify"
    if (run_dir / "screen" / "designs").is_dir() and (run_dir / "verify" / "designs").is_dir():
        return run_dir / "screen", run_dir / "verify"
    return None


def discover_pairs(runs) -> list[dict]:
    pairs = []
    for run in runs:
        run = Path(run)
        sides = _pair_sides(run)
        if sides is None:
            continue
        screen, verify = sides
        for ddir in sorted((verify / "designs").glob("*")):
            if (screen / "designs" / ddir.name).is_dir():
                pairs.append({"run": run, "screen": screen, "verify": verify,
                              "design_hash": ddir.name})
    return pairs


def _grid_brief(brief, points: int):
    if brief.objective_version != 9:
        raise ScoreRuleError(
            "the common interpolated analysis grid is implemented through the canonical "
            "objective.score_grid (v9 only); pass a v9 brief for 58/116-point analysis")
    from hornlab_search.objective.scalar_v9 import V9Params

    block = dict(brief.objective_block or {})
    block["version"] = 9
    block["score_grid"] = {"kind": "dense_log", "points": int(points)}
    return dataclasses.replace(brief, objective_block=block,
                               objective_params=V9Params.from_block(block))


def _config_for(side: Path):
    for cand in (side / "config.yaml", side.parent / "config.yaml"):
        if cand.is_file():
            return cand
    return None


def _mesh_side_record(side: Path, design_hash: str) -> dict:
    """Stored-manifest evidence that a pair really is the same mesh (no inherited claim).

    ``mesh_hash`` is the SHA-256 of the mesh file the design's own ``mesh_meta.json`` points at.
    ``n_dof`` comes from that manifest's ``result`` block and ``mesh_epw`` from the run's stored
    ``run.json``; a missing value is the typed string ``"unavailable"``, never a fabricated number.
    """
    ddir = side / "designs" / design_hash
    meta_path = ddir / "mesh_meta.json"
    meta = _read_json(meta_path)
    result = meta.get("result") if isinstance(meta.get("result"), dict) else {}
    mesh_path = result.get("path")
    mp = Path(str(mesh_path)) if mesh_path else (ddir / "mesh.msh")
    if not mp.is_absolute():
        mp = REPO_ROOT / mp
    if not mp.is_file():
        fallback = ddir / "mesh.msh"
        mp = fallback if fallback.is_file() else mp

    n_dof = result.get("n_dof")
    run_dir = side.parent if side.name in ("screen", "verify") else side
    run_meta = _read_json(run_dir / "run.json")
    mesh_block = run_meta.get("mesh") if isinstance(run_meta.get("mesh"), dict) else {}
    if not mesh_block and isinstance(run_meta.get("config"), dict):
        cfg_mesh = run_meta["config"].get("mesh")
        mesh_block = cfg_mesh if isinstance(cfg_mesh, dict) else {}
    epw = mesh_block.get("epw")
    return {
        "mesh_meta": str(meta_path) if meta_path.is_file() else "unavailable",
        "mesh_meta_key": meta.get("key") or "unavailable",
        "mesh_path": str(mp) if mp.is_file() else "unavailable",
        "mesh_hash": _sha256(mp) if mp.is_file() else "unavailable",
        "n_dof": (int(n_dof) if isinstance(n_dof, (int, float))
                  and not isinstance(n_dof, bool) else "unavailable"),
        "mesh_epw": (float(epw) if isinstance(epw, (int, float))
                     and not isinstance(epw, bool) else "unavailable"),
    }


def grid_stability(brief_path, runs, out: Path, points=(58, 116), top: int = 28,
                   prov: dict | None = None) -> dict:
    from hornlab_search.solve.cache import load_response
    from tools.analysis.rescore_identity import floor_stats

    prov = prov or provenance()
    brief = _load_brief(brief_path)
    if brief.objective_version != 9:
        raise ScoreRuleError("grid: pass a v9 brief (the dense analysis grid is v9 score_grid)")
    dense_briefs = {int(n): _grid_brief(brief, int(n)) for n in points}
    pair_runs = [Path(r) if Path(r).is_absolute() else (REPO_ROOT / r) for r in runs]
    pairs = discover_pairs(pair_runs)
    if not pairs:
        raise FileNotFoundError("grid: no screen/verify same-mesh pairs found in the given runs")

    grids = ["solved"] + [f"dense_{int(n)}" for n in points]
    sides: dict[str, dict] = {}
    read_paths, skipped_pairs, planned = [], [], []
    for pair in pairs:
        run, h = pair["run"], pair["design_hash"]
        available: dict[str, tuple[Path, Path]] = {}
        missing: list[str] = []
        for side_name, side in (("screen", pair["screen"]), ("verify", pair["verify"])):
            rp = side / "designs" / h / "response.npz"
            if not rp.is_file():
                missing.append(side_name)
                continue
            available[side_name] = (side, rp)
            read_paths.append(rp)
            for name in ("metrics.json", "design.json", "status.json",
                         "mesh_meta.json", "mesh.msh"):
                p = side / "designs" / h / name
                if p.is_file():
                    read_paths.append(p)
        read_paths.extend(_run_read_paths(run, h))
        if missing:
            # A pair with one absent response is a typed skip: it stays in the report and never
            # aborts the command (previously the unconditional dict index raised KeyError).
            skipped_pairs.append({
                "run": run.name,
                "design_hash": h,
                "missing_response_sides": missing,
                "note": ("typed skip: no response.npz on "
                         f"{'/'.join(missing)}; this pair contributes no J and is not scored"),
            })
            continue
        planned.append((pair, available))

    # Snapshot EVERY read source before the first response/best/metrics read.
    before = _source_hashes(read_paths)

    pair_rows = []
    for pair, available in planned:
        run, h = pair["run"], pair["design_hash"]
        for side_name in ("screen", "verify"):
            side, rp = available[side_name]
            resp = load_response(rp)
            cfg = _config_for(side)
            record = {
                "solved_freqs_hz": np.asarray(resp.freqs_hz, dtype=float).tolist(),
                "mesh": _mesh_side_record(side, h),
            }
            for label in grids:
                active = brief if label == "solved" else dense_briefs[int(label.split("_")[1])]
                result = _replay(side, h, active, config_path=cfg)
                record[label] = {
                    "J": _finite(result.j),
                    "status": result.status,
                    "terms": dict(result.terms or {}),
                }
            # Facts only on the native solved grid: the dense labels are the same physical
            # response re-scored, so their per-term table carries the sensitivity information.
            record["solved"]["facts"] = target_facts(_metrics_for_facts(resp, brief), brief)
            sides[f"{run.name}/{h}/{side_name}"] = record
        pair_rows.append({
            "run": run.name, "design_hash": h,
            "screen_freqs": len(sides[f"{run.name}/{h}/screen"]["solved_freqs_hz"]),
            "verify_freqs": len(sides[f"{run.name}/{h}/verify"]["solved_freqs_hz"]),
        })

    # ---- per-grid screen-vs-verify statistics --------------------------------------------
    def _pairs_for(grid_label: str):
        out_pairs = []
        for name, rec in sides.items():
            if not name.endswith("/screen"):
                continue
            verify_name = name[: -len("/screen")] + "/verify"
            other = sides.get(verify_name)
            if other is None:
                continue
            out_pairs.append((rec[grid_label]["J"], other[grid_label]["J"]))
        return out_pairs

    stats = {label: floor_stats(_pairs_for(label), top) for label in grids}

    # ---- per-term weighted sensitivity (screen - verify) ---------------------------------
    weighted_keys = _weighted_keys(brief)
    weights = _resolve_weights(brief)
    term_stats = {}
    for label in grids:
        diffs: dict[str, list[float]] = {k: [] for k in weighted_keys}
        for name, rec in sides.items():
            if not name.endswith("/screen"):
                continue
            other = sides.get(name[: -len("/screen")] + "/verify")
            if other is None:
                continue
            for k in weighted_keys:
                a = _finite(rec[label]["terms"].get(k))
                b = _finite(other[label]["terms"].get(k))
                if a is None or b is None:
                    continue
                diffs[k].append(float(weights.get(k, 0.0)) * (a - b))
        term_stats[label] = {
            k: {"mean": float(np.mean(v)) if v else None,
                "sd": float(np.std(v, ddof=1)) if len(v) > 1 else None, "n": len(v)}
            for k, v in diffs.items()}

    # ---- definition change: solved grid -> common interpolated grid, and 58 -> 116 ----------
    definition = {}
    for label in grids[1:]:
        for side in ("screen", "verify"):
            names = [n for n in sides if n.endswith(f"/{side}")]
            dense = [_finite(sides[n][label]["J"]) for n in names]
            native = [_finite(sides[n]["solved"]["J"]) for n in names]
            definition[f"{label}_minus_solved/{side}"] = floor_stats(
                list(zip(dense, native)), top)
    for lower, higher in zip(grids[1:], grids[2:]):
        for side in ("screen", "verify"):
            names = [n for n in sides if n.endswith(f"/{side}")]
            definition[f"{higher}_minus_{lower}/{side}"] = floor_stats(
                list(zip([_finite(sides[n][higher]["J"]) for n in names],
                         [_finite(sides[n][lower]["J"]) for n in names])), top)

    rank_shift = {}
    for side in ("screen", "verify"):
        names = [n for n in sides if n.endswith(f"/{side}")]
        base = np.array([_finite(sides[n]["solved"]["J"]) for n in names], dtype=float)
        for label in grids[1:]:
            dense = np.array([_finite(sides[n][label]["J"]) for n in names], dtype=float)
            ok = np.isfinite(base) & np.isfinite(dense)
            if ok.sum() < 3:
                rank_shift[f"{side}/solved->{label}"] = {"n": int(ok.sum())}
                continue
            rb = np.argsort(np.argsort(base[ok]))
            rd = np.argsort(np.argsort(dense[ok]))
            shift = np.abs(rb - rd)
            k = max(1, min(int(top), shift.size))
            rank_shift[f"{side}/solved->{label}"] = {
                "n": int(ok.sum()),
                "spearman": float(np.corrcoef(rb, rd)[0, 1]),
                "max_rank_shift": int(shift.max()),
                "top_max_shift": int(np.sort(shift)[k - 1]),
            }

    solved_n = {
        "screen": sorted({len(rec["solved_freqs_hz"]) for n, rec in sides.items()
                          if n.endswith("/screen")}),
        "verify": sorted({len(rec["solved_freqs_hz"]) for n, rec in sides.items()
                          if n.endswith("/verify")}),
    }
    print("=" * 104)
    print(f"FREQUENCY-GRID STABILITY under {brief.name} (v9)")
    print("=" * 104)
    print(f"[pairs] {len(pairs)} discovered, {len(planned)} scored, "
          f"{len(skipped_pairs)} skipped; solved freqs: screen "
          f"{solved_n['screen']} samples, verify {solved_n['verify']} samples")
    for skip in skipped_pairs:
        print(f"[skip] {skip['run']}/{skip['design_hash']}: {skip['note']}")
    for label in grids:
        s = stats[label]
        print(f"[{label:<10}] n={s['n_pairs']} mean(screen-verify)="
              f"{_fmt(s.get('mean_diff_all'))} sd_all={_fmt(s.get('sd_diff_all'))} "
              f"spearman_all={_fmt(s.get('spearman_all'), 4)} "
              f"sd_top{top}={_fmt(s.get('sd_diff_top'))} "
              f"spearman_top={_fmt(s.get('spearman_top'), 4)}")
    print("NOTE: the dense grid is PCHIP interpolation of the stored solved response; it does "
          "NOT create acoustic resolution.")
    print(f"      dense analysis points = {[int(n) for n in points]} vs solved "
          f"{solved_n['screen']}/{solved_n['verify']} samples. Only a future denser SOLVED pass "
          "can confirm missing narrow resonances.")

    guard = _assert_sources_unchanged(before)
    payload = {
        "provenance": prov,
        "brief": {"name": brief.name, "path": brief.source_path,
                  "objective_version": brief.objective_version,
                  "brief_hash": brief.brief_hash()},
        "pairs": len(pairs),
        "processed_pairs": len(planned),
        "skipped_pairs": skipped_pairs,
        "grid_labels": grids,
        "dense_points": [int(n) for n in points],
        "solved_samples_per_side": solved_n,
        "per_grid": stats,
        "definition_change": definition,
        "rank_shift": rank_shift,
        "per_term_weighted_diff_screen_minus_verify": term_stats,
        "interpolation_is_not_resolution": (
            "58/116 dense points are PCHIP interpolation of the stored solved response. They "
            "reduce grid-definition noise; they do not add acoustic information and cannot "
            "reveal an unsolved narrow resonance."),
        "pairs_detail": pair_rows,
        "sides": {k: {"J": {g: rec[g]["J"] for g in grids},
                      "status": {g: rec[g]["status"] for g in grids},
                      "mesh": rec["mesh"],
                      "solved_freqs_hz": rec["solved_freqs_hz"]}
                  for k, rec in sides.items()},
        "source_guard": guard,
    }
    _write_json(out / "grid_stability.json", payload)
    _write_csv(out / "grid_pairs.csv", [
        {"run": k.rsplit("/", 2)[0], "design": k.rsplit("/", 2)[1],
         "side": k.rsplit("/", 1)[1],
         **{f"J_{g}": rec[g]["J"] for g in grids},
         "n_solved": len(rec["solved_freqs_hz"]),
         "mesh_hash": rec["mesh"]["mesh_hash"],
         "n_dof": rec["mesh"]["n_dof"],
         "mesh_epw": rec["mesh"]["mesh_epw"]}
        for k, rec in sides.items()])
    _write_csv(out / "grid_term_sensitivity.csv", [
        {"grid": g, "term": k, "mean_diff": v["mean"], "sd_diff": v["sd"], "n": v["n"]}
        for g, terms in term_stats.items() for k, v in terms.items()])
    print(f"\nwrote {out / 'grid_stability.json'}, grid_pairs.csv, grid_term_sensitivity.csv")
    return payload


def _fmt(x, digits: int = 5) -> str:
    v = _finite(x)
    return "n/a" if v is None else f"{v:.{digits}f}"


# ------------------------------------------------------------------ cli


def _designs_from_args(args) -> list[dict]:
    given = getattr(args, "design", None) or getattr(args, "response", None)
    designs = [] if given else _default_designs()
    for spec in (getattr(args, "design", None) or []):
        designs.append(_parse_design_spec(spec))
    for run in (getattr(args, "runs", None) or []):
        run_path = Path(run)
        for ddir in sorted((run_path / "designs").glob("*")):
            designs.append({"label": ddir.name, "run": str(run_path),
                            "design_hash": ddir.name, "own_cell": None})
    for rp in (getattr(args, "response", None) or []):
        rp = Path(rp)
        designs.append({"label": rp.parent.name or rp.stem, "run": str(rp.parent),
                        "design_hash": rp.parent.name, "response": str(rp),
                        "own_cell": None})
    return designs


def main(argv=None) -> int:
    from hornlab_search.config import ConfigError

    ap = argparse.ArgumentParser(description="Brief-truth replay + frequency-fidelity lab (WP3)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("identity", help="legacy identity replay + Nov-17 2x2 matrix")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--design", action="append", default=None,
                   help="LABEL=RUN_DIR:DESIGN_HASH (default: the two named legacy designs)")

    p = sub.add_parser("scenarios", help="score stored designs under one or more v9 briefs")
    p.add_argument("--briefs", nargs="+", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--design", action="append", default=None,
                   help="LABEL=RUN_DIR:DESIGN_HASH (default: the two legacy designs)")
    p.add_argument("--runs", nargs="+", default=None,
                   help="extra run dirs; every designs/<hash> is scored")
    p.add_argument("--response", action="append", default=None,
                   help="a bare response.npz (diagnostic: no stored J to compare against)")

    p = sub.add_parser("grid", help="screen/verify frequency-grid stability under one v9 brief")
    p.add_argument("--brief", type=Path, required=True)
    p.add_argument("--runs", nargs="+", required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--points", nargs="+", type=int, default=[58, 116])
    p.add_argument("--top", type=int, default=28)

    args = ap.parse_args(argv)
    out = args.out if args.out.is_absolute() else (REPO_ROOT / args.out).resolve()
    prov = provenance()          # before the guard: uses subprocess for the git snapshot
    guard = BackendGuard()
    rc = 0
    try:
        with guard.active():
            if args.cmd == "identity":
                identity(out, _designs_from_args(args), prov)
            elif args.cmd == "scenarios":
                scenarios(args.briefs, _designs_from_args(args), out, prov)
            elif args.cmd == "grid":
                grid_stability(args.brief, args.runs, out, args.points, args.top, prov)
            else:  # pragma: no cover - argparse enforces the choices
                raise ScoreRuleError(f"unknown command {args.cmd!r}")
    except ConfigError as exc:
        # A bad brief is a typed input refusal, not an internal traceback.
        print(f"{TOOL}: ConfigError: {exc}", file=sys.stderr)
        return 2
    if guard.calls:
        print(f"ERROR: {guard.calls} forbidden backend call(s): {guard.names}", file=sys.stderr)
        rc = 3
    print(f"BACKEND_GUARD installed={len(guard.installed)} calls={guard.calls}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
