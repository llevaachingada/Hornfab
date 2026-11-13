"""CMA-ME quality-diversity search (WP11b, ``search.algorithm: cma_me``).

CMA-ME (Fontaine 2020) runs a grid archive over a two-descriptor measure space; each emitter is a
CMA-ES instance whose ranking rewards *archive improvements* (new cells and better elites), so the
run fills a MAP of good designs instead of converging on one. This is a **search-only** feature:
the objective, the evaluator, the budget and the resume contract are exactly ``search.cma``'s.

Budget semantics (identical to ``search/cma.py``): ``budget`` caps NON-CACHED evaluations only (the
seed counts); a cache hit (in-run memo, resumed ndjson row, cross-run solve cache) does not consume
it. The budget is checked before every candidate, so a generation can be cut part-way; a partial
generation is NOT ``tell``-ed (a resume replays it from the cache and finishes it).

Resume is free and deterministic: the archive and the emitter are rebuilt from the same config and
seed, every replayed candidate is a cache hit, and the cached objective/measures are told back into
the scheduler in ask order. The archive therefore ends up byte-identical to an uninterrupted run's
— except ``solve_failed`` rows, which are never memoised (inherited from ``search/cma.py``) and
re-solve on a resume, so a run interrupted by a solver-unhealthy abort may legitimately diverge from
the uninterrupted replay.

Archive correctness (S1/F1)
---------------------------
* The seed is evaluated exactly once and archived at the **normalized geometry actually evaluated**
  (``space.normalize(space.seed)`` after ``search.links`` reduction), never at a warm-start mean.
  The emitter mean remains the warm x0. A failed/refused seed, or one without finite descriptors,
  is NOT archived and never invents a seed/corner descriptor.
* Both the scheduler search archive and its result archive are ``FailureExcludingGridArchive``
  instances. ``scheduler.tell`` still receives the full asked batch in ask order; a per-tell
  eligibility mask excludes every non-complete evaluation from ``GridArchive.add`` while stitching
  back full-batch ``add_info`` arrays (status 0, finite value strictly below every eligible value).
  Invalid rows therefore never become elites, and no row is dropped from ``tell`` or re-asked.
* A small ``RankerBase`` ranks excluded failures last through the supported ranker API, without
  setting ``status != 0`` (which would corrupt ribs' ``new_sols`` count). This changes invalid
  admission/ranks for runs with failures; it is NOT trajectory-neutral and it is NOT feasible-only
  learning (CMA-MAE threshold learning is unchanged).

ribs usage (installed 0.12.0, read-only; never edited):
- ``ribs.archives.GridArchive`` — ``threshold_min=-inf`` and ``learning_rate=1.0`` give CMA-ME's
  improvement values (``ribs/archives/_grid_archive.py``, ``add``: ``cur_threshold[is_new] = 0``
  and ``add_info["value"] = objective - cur_threshold``).
- ``ribs.emitters.EvolutionStrategyEmitter`` with ``ranker="2imp"``, ``es="cma_es"`` and
  ``selection_rule="mu"`` (``ribs/emitters/_evolution_strategy_emitter.py``): the canonical
  CMA-ME emitter (0.12.0 no longer ships ``CMAEvolutionEmitter``).
- ``ribs.schedulers.Scheduler``: strict ``ask``/``tell`` alternation in emitter order
  (``ribs/schedulers/_scheduler.py``). One emitter is used, so the batch is returned untouched.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

import numpy as np

from ..config import ConfigError, QD_DESCRIPTORS
from ..dataset.record import DEFAULT_TRACE_FRACTION
from ..design.space import DesignSpace
from ..mesh.build import MeshConsistencyError
from ..types import Evaluation
from . import rundir
from . import links as links_mod
from . import outcomes
from . import warmstart
from .cma import (MAX_CONSECUTIVE_SOLVE_FAILURES, SolverUnhealthyError, _detach, _prepare,
                  budget_count, budget_counts_block, budget_exhausted, budget_policy,
                  summarize, summarize_rows)
from .evaluate import error_kind, evaluate, read_ndjson
from .pipeline import CandidatePipeline

log = logging.getLogger("hornlab_search.search.cma_me")

#: A mean -6 dB beamwidth is an angle, so the archive's measure space is that physical interval in
#: both axes (the bins come from ``search.qd``). Fixed by descriptor UNITS, not by the data: an
#: archive whose ranges move with the run could not be compared or resumed reproducibly.
DESCRIPTOR_RANGE_DEG = (0.0, 180.0)

#: How many NEW evaluations may pass between archive.json / archive_heatmap.json refreshes. The
#: files are always rewritten at the end of a run, so this only bounds how stale a running run's
#: atlas may be.
ARCHIVE_REFRESH_EVALS = 25

#: Resume-protocol marker for the failure-excluding archive semantics (S1/F1). An existing
#: run.json carrying a different/missing marker is refused rather than silently reinterpreted.
QD_PROTOCOL = "cma-me-archive-v2"
QD_FAILURE_EXCLUSION_POLICY = "failure_excluding_grid_archive"
QD_FAILURE_EXCLUSION_VERSION = 1
QD_DETERMINISTIC_REFUSAL_POLICY = "legacy_finite_penalty_for_qd_v1"
QD_PENDING_BATCH = "pending_batch.json"
QD_STRICT_STATE = "strict_state.json"

#: Version pin for the strict-QD cumulative-counter checkpoint. Budget/attempt caps are excluded
#: from the spec hash (they are extended explicitly and recorded separately).
QD_STRICT_CODE = "hornlab_search.search.cma_me/strict/1"

#: Cumulative counters persisted across a strict-QD resume. Names are the artifact keys; the
#: in-memory ``state`` uses different ones for a few of them (mapped in ``_restore_counters``).
QD_COUNTER_KEYS = ("attempts", "new", "valid", "refused_free", "backend_calls", "retries",
                   "transient", "metric", "unknown")

#: descriptor name -> MetricSet field it averages over the in-band frequencies.
_DESCRIPTOR_FIELDS = {"mean_bw_h_deg": "bw_h_deg", "mean_bw_v_deg": "bw_v_deg"}

try:  # ribs is optional for importing this module; the search path requires it.
    from ribs.archives import GridArchive as _RibsGridArchive
    from ribs.emitters.rankers import (ImprovementRanker as _ImprovementRanker,
                                       RankerBase as _RankerBase,
                                       TwoStageImprovementRanker as _TwoStageImprovementRanker)
except Exception:  # pragma: no cover - only exercised without ribs installed
    _RibsGridArchive = None
    _RankerBase = None
    _ImprovementRanker = None
    _TwoStageImprovementRanker = None


def _mean_in_band(values, freqs, lo: float, hi: float) -> float | None:
    """Mean of ``values`` at the in-band frequencies, ignoring non-finite samples. None when the
    band has no finite sample (a NaN-only metric must not become a descriptor coordinate)."""
    v = np.asarray(values, dtype=float)
    f = np.asarray(freqs, dtype=float)
    if v.shape != f.shape:
        return None
    mask = (f >= lo) & (f <= hi) & np.isfinite(v)
    if not mask.any():
        return None
    return float(v[mask].mean())


def descriptor_values(ev: Evaluation, cfg, names: tuple[str, str]) -> tuple[float, float] | None:
    """(descriptor_h, descriptor_v) for one evaluation, or None when it has no metrics / no
    finite in-band samples. Never raises."""
    metrics = ev.metrics
    if metrics is None:
        return None
    try:
        lo = float(cfg.target_raw["band_lo_hz"])
        hi = float(cfg.target_raw["band_hi_hz"])
    except (KeyError, TypeError, ValueError):
        return None
    out = []
    for name in names:
        field = _DESCRIPTOR_FIELDS.get(name)
        if field is None:
            return None
        value = _mean_in_band(getattr(metrics, field), metrics.freqs_hz, lo, hi)
        if value is None:
            return None
        out.append(value)
    return (float(out[0]), float(out[1]))


def _describe_descriptor(name: str) -> str:
    return f"{name} (mean of MetricSet.{_DESCRIPTOR_FIELDS[name]} over the in-band frequencies)"


def _strict_error_policy(cfg) -> bool:
    """True only for the opt-in ``search.error_policy: retry_same_then_stop``. The key is added by
    the config lane; a missing/unknown value keeps today's legacy behaviour."""
    return str(getattr(cfg.search, "error_policy", None) or "legacy") == "retry_same_then_stop"


def _infrastructure_stop_reason(out: outcomes.Outcome) -> str:
    """The resumable stop token for an infrastructure/unknown outcome."""
    if out.category == outcomes.CATEGORY_TRANSIENT:
        reason = "qd_infrastructure"
    elif out.category == outcomes.CATEGORY_METRIC:
        reason = "qd_metric_error"
    else:
        reason = "qd_unknown_error"
    first = str(out.error or "").splitlines()[0][:200]
    return f"{reason}: {out.kind}: {first}"


def _evaluation_identity(design, space, cfg, mode: str):
    """(design_hash, mesh_hash, solve_hash, eval_key) for a candidate, mirroring
    ``evaluate.evaluate``'s identity exactly (links + throat derivation + mounting suffix).

    Used only to write/reconcile the opt-in pending-intent checkpoint; it never evaluates or
    mutates a design. Any failure is surfaced to the caller, which stores ``None`` identities.
    """
    from .. import config as config_mod
    from ..design import families
    from ..mesh.build import mounting_of
    from .evaluate import _derive_throat_coupling, _with_meh_source_tags, meh_block_of
    from .links import apply_links

    d = apply_links(design, space, cfg)
    d = _derive_throat_coupling(d, cfg)
    mspec = config_mod.mesh_spec(mode, cfg)
    sspec = config_mod.solve_spec(mode, cfg)
    meh = meh_block_of(cfg)
    if meh is not None:
        sspec = _with_meh_source_tags(sspec, meh)
    mkey = families.mounting_key(mounting_of(cfg))
    key = f"{d.hash()}-{mspec.hash()}-{sspec.hash()}" + (f"-{mkey}" if mkey else "")
    return d.hash(), mspec.hash(), sspec.hash(), key


def _qd_strict_identity(cfg, lib_shas) -> dict:
    """Pinned protocol/spec/code identity for a strict-QD resume artifact.

    The budget/attempt caps are deliberately excluded from the spec hash: they are extended
    explicitly and recorded in the artifact. Any other search/objective/mesh/solve knob (or a
    changed installed library) refuses the resume instead of reinterpreting a different run.
    """
    import json as _json
    from ..dataset.record import to_jsonable
    raw = _json.loads(_json.dumps(to_jsonable(cfg.raw)))
    s = raw.get("search")
    if isinstance(s, dict):
        s.pop("max_attempts", None)
        s.pop("budget", None)
    return {"protocol": QD_PROTOCOL,
            "code": QD_STRICT_CODE,
            "spec_sha": rundir.config_sha(raw),
            "algorithm": str(cfg.search.algorithm),
            "error_policy": str(getattr(cfg.search, "error_policy", None) or "legacy"),
            "qd_seed": int(cfg.search.seed),
            "lib_shas": {str(k): str(v) for k, v in (lib_shas or {}).items()}}


if _RibsGridArchive is not None:

    class FailureExcludingGridArchive(_RibsGridArchive):
        """A ``GridArchive`` whose ``add`` refuses non-complete evaluations by explicit mask.

        ``scheduler.tell(..., eligible=mask)`` passes the mask through to this archive. Only the
        eligible rows are handed to ``GridArchive.add``; the returned full-batch ``add_info`` keeps
        the original asked order and count: excluded rows get ``status=0`` and a finite ``value``
        strictly below every eligible value in that batch, so the emitter ranks them last without
        corrupting ribs' ``new_sols`` count. This is a supported subclass of the public archive API
        (no scheduler/emitter/private-state mutation), and it is the only archive admission policy
        change: the raw genotypes and tell order are untouched.

        With ``eligible=None`` or an all-eligible batch the behaviour is exactly ``GridArchive``'s,
        preserving the default cold trajectory byte-for-byte.
        """

        def add(self, solution, objective, measures, *, eligible=None, **fields):
            if eligible is None:
                return super().add(solution=solution, objective=objective, measures=measures,
                                   **fields)
            eligible_arr = np.asarray(eligible, dtype=bool).reshape(-1)
            obj = np.asarray(objective, dtype=float).reshape(-1)
            sol = np.asarray(solution)
            meas = np.asarray(measures)
            n = int(obj.size)
            if eligible_arr.size != n:
                raise ValueError(f"eligible has length {eligible_arr.size}, expected {n}")
            if sol.shape[0] != n or meas.shape[0] != n:
                raise ValueError("solution/objective/measures batch sizes disagree")
            if n == 0:
                return {"status": np.zeros(0, dtype=np.int32), "value": np.zeros(0, dtype=float)}
            if bool(eligible_arr.all()):
                return super().add(solution=solution, objective=objective, measures=measures,
                                   **fields)

            status = np.zeros(n, dtype=np.int32)
            value = np.zeros(n, dtype=float)
            selected = np.flatnonzero(eligible_arr)
            if selected.size:
                sub_fields = {name: np.asarray(arr)[selected] for name, arr in fields.items()}
                sub = super().add(solution=sol[selected], objective=obj[selected],
                                  measures=meas[selected], **sub_fields)
                status[selected] = np.asarray(sub["status"], dtype=np.int32)
                sub_value = np.asarray(sub["value"], dtype=float).reshape(-1)
                # A finite floor strictly below every eligible value in THIS batch. It is computed
                # from the real finite eligible values, so no NaN/Inf objective is fabricated.
                # A pathological all-NaN threshold (a config lane validation issue, not a normal
                # run) cannot provide a finite reference; sanitise both sides to a finite floor so
                # the emitter never receives NaN and excluded rows still rank last.
                finite = np.isfinite(sub_value)
                low = float(np.min(sub_value[finite])) if bool(finite.any()) else 0.0
                span = max(1.0, min(abs(low), 1.0e300))
                floor = low - span
                if not np.isfinite(floor):
                    floor = -1.0
                    span = 1.0
                value[selected] = np.where(finite, sub_value, floor)
                value[~eligible_arr] = floor - span
            return {"status": status, "value": value}
else:  # pragma: no cover
    class FailureExcludingGridArchive:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs):
            raise ImportError("FailureExcludingGridArchive requires the ribs package")


if _RankerBase is not None:

    class _FailureLastRanker(_RankerBase):
        """Ranks archive-excluded failures last, using ribs' supported ``RankerBase`` API.

        The wrapped ranker is the canonical ``2imp`` (CMA-ME) or ``imp`` (CMA-MAE) ranker. The
        archive's full-batch ``add_info`` already gives excluded rows ``status=0`` and a very low
        value; this wrapper additionally guarantees that any row the tell mask marks ineligible is
        ordered after every eligible row. It does not modify statuses or values.
        """

        def __init__(self, seed=None, *, maes: bool = False):
            super().__init__(seed)
            base_cls = _ImprovementRanker if maes else _TwoStageImprovementRanker
            self._base = base_cls(seed)

        def reset(self, emitter, archive):  # noqa: D102 - delegate
            self._base.reset(emitter, archive)

        def rank(self, emitter, archive, data, add_info):  # noqa: D102 - delegate + reorder
            indices, values = self._base.rank(emitter, archive, data, add_info)
            eligible = data.get("eligible")
            if eligible is not None:
                eligible_arr = np.asarray(eligible, dtype=bool).reshape(-1)
                indices = np.asarray(indices)
                keep = indices[eligible_arr[indices]]
                drop = indices[~eligible_arr[indices]]
                indices = np.concatenate([keep, drop])
            return indices, values
else:  # pragma: no cover
    _FailureLastRanker = None  # type: ignore[assignment]


def search(cfg, run_dir, mode="screen", resume=None, *, backend=None, budget: int | None = None,
           store=None, cache_dir=None, trace_fraction: float = DEFAULT_TRACE_FRACTION,
           command: str | None = None, config_path=None, lib_shas: dict | None = None,
           max_evals: int | None = None) -> Evaluation:
    """CMA-ME from the seed. Same argument surface and artifacts as ``search.cma.search``, plus
    ``archive.json`` / ``archive_heatmap.json`` and a ``qd`` block in run.json.

    ``budget`` caps NEW (non-cached) evaluations, exactly as in the single-ES path. Raises only for
    things that must stop a run (``MeshConsistencyError``, KeyboardInterrupt, an unusable backend,
    or the solver-unhealthy streak).
    """
    qd = getattr(cfg.search, "qd", None)
    if qd is None:
        raise ValueError("search.algorithm 'cma_me' needs search.qd (bins_h/bins_v have no default)")
    if _RibsGridArchive is None or _FailureLastRanker is None:
        raise ImportError("search.algorithm 'cma_me' requires the ribs package")
    from ribs.emitters import EvolutionStrategyEmitter
    from ribs.schedulers import Scheduler

    names = (str(qd["descriptor_h"]), str(qd["descriptor_v"]))
    for name in names:
        if name not in QD_DESCRIPTORS or name not in _DESCRIPTOR_FIELDS:
            raise ValueError(f"search.qd descriptor {name!r} is not supported by this build")
    bins = (int(qd["bins_h"]), int(qd["bins_v"]))

    run_dir = Path(resume if resume is not None else run_dir)
    # S1/F1: an old archive protocol cannot be silently reinterpreted.
    _refuse_incompatible_resume(run_dir)
    run_dir, backend, ctx = _prepare(cfg, run_dir, mode, backend, store, cache_dir, trace_fraction,
                                     command, config_path, lib_shas)
    policy = budget_policy(cfg, budget)         # B.4: shared budget accounting with cma.search
    max_new = policy["budget"]
    strict = _strict_error_policy(cfg)
    space = DesignSpace.from_config(cfg)
    space, linked = links_mod.reduce_space(space, cfg)   # B.2: absent search.links = same space
    if linked:
        log.info("search.links: %d linked knob(s) removed from the CMA-ME dimension: %s",
                 len(linked), sorted(linked))
    x_seed = space.normalize(space.seed)       # the geometry ACTUALLY evaluated first
    x0 = x_seed                                # emitter mean; replaced by the warm start below
    sigma0_eff = float(cfg.search.sigma0)      # B.1: sigma0_eff = warm-start sigma when configured
    warm_record = None
    try:
        warm_design, warm_record = warmstart.mean_and_sigma(cfg, space)   # (None, None) = absent
    except warmstart.WarmStartError as exc:
        raise ConfigError(str(exc)) from None   # a bad source is a CONFIG problem: refuse, don't solve
    if warm_design is not None:
        x0 = space.normalize(warm_design)
        sigma0_eff = float(warm_record["sigma0"])
        log.info("warm start (CMA-ME): mean = best valid design %s from %s (J=%.6g), sigma0 %.6g",
                 warm_record["mean_design_hash"], warm_record["from_runs"],
                 warm_record["mean_objective"], sigma0_eff)
    solution_dim = int(len(x0))

    # B.8 (opt-in): search.qd.maes turns the CMA-ME archive into a CMA-MAE soft archive
    # (Fontaine & Nikolaidis 2023): learning_rate in [0.01, 0.1] and threshold_min = the NEGATIVE
    # J threshold (the archive MAXIMISES -J = -(-1000) = 1000 for refusal-penalty rows), the
    # emitter ranks with "imp" and carries NO bounds (candidates are clipped in
    # DesignSpace.denormalize exactly like the plain CMA path). Absent maes = today's archive.
    maes = qd.get("maes") if isinstance(qd, dict) else None

    def make_archive() -> FailureExcludingGridArchive:
        kwargs = dict(solution_dim=solution_dim, dims=list(bins),
                      ranges=[DESCRIPTOR_RANGE_DEG, DESCRIPTOR_RANGE_DEG],
                      seed=int(cfg.search.seed))
        if maes:
            kwargs["learning_rate"] = float(maes["learning_rate"])
            kwargs["threshold_min"] = -float(maes["j_threshold"])
        return FailureExcludingGridArchive(**kwargs)

    if maes:
        log.info("CMA-MAE: archive learning_rate %.4g, threshold_min %.6g (J threshold %.6g)",
                 maes["learning_rate"], -maes["j_threshold"], maes["j_threshold"])
    archive = make_archive()
    result_archive = make_archive()            # Scheduler requires a distinct result archive
    emitter = EvolutionStrategyEmitter(
        archive, x0=np.asarray(x0, dtype=float), sigma0=sigma0_eff,
        ranker=(lambda seed: _FailureLastRanker(seed, maes=bool(maes))),
        es="cma_es", selection_rule="mu",
        bounds=None if maes else [(0.0, 1.0)] * solution_dim,
        batch_size=int(cfg.search.popsize) if cfg.search.popsize else None,
        seed=int(cfg.search.seed))
    scheduler = Scheduler(archive, [emitter], result_archive=result_archive)

    evals: list[Evaluation] = []
    wall: list[float] = []
    state = {"best": None, "best_no": None, "seed_ev": None, "n_new": 0, "stop": "",
             "solve_fail_streak": 0, "attempts": 0, "n_valid": 0, "n_refused_free": 0,
             "backend_calls": 0, "retries": 0, "transient_failures": 0,
             "metric_failures": 0, "unknown_failures": 0}
    hash_by_solution: dict[tuple, str] = {}
    seed_measures: np.ndarray | None = None
    rows0 = read_ndjson(run_dir / "search.ndjson")
    written_at = 0
    # Strict cumulative checkpoint (opt-in error policy only). ``replay`` is the deterministic
    # resume prefix: every non-cached attempt already on disk must replay without counting again.
    strict_state: dict | None = None
    replay = {"remaining": 0}
    hist_non_cached: set[tuple] = set()
    for _r in rows0:
        _t = (_r.get("design_hash"), _r.get("mesh_hash"), _r.get("solve_hash"))
        if None not in _t and not _r.get("cached"):
            hist_non_cached.add(_t)

    # On a resume the best so far is already on disk in search.ndjson: start from it, so a short
    # (or zero-budget) resume can never overwrite best.json with something worse.
    prior = [e for e in ctx.known.values() if not e.error]
    if prior:
        b0 = min(prior, key=lambda e: e.objective)
        state["best"] = b0
        state["best_no"] = next((r.get("n") for r in rows0
                                 if r.get("design_hash") == b0.design_hash), None)
        rundir.write_best(run_dir, b0, mode, state["best_no"])
    prior_best, prior_best_no = state["best"], state["best_no"]

    pipe = CandidatePipeline(cfg, mode, run_dir, ctx)      # inert unless pipeline_prefetch > 0

    def clip01(x) -> np.ndarray:
        return np.clip(np.asarray(x, dtype=float).reshape(-1), 0.0, 1.0)

    def consume_replay(ev: Evaluation) -> bool:
        """True when this evaluation is part of the deterministic resume prefix, i.e. it must not
        inflate the cumulative counters again.

        ``replay["remaining"]`` is the stored NON-CACHED attempt count. A cached replay of a row
        that was non-cached when first run consumes one attempt; a non-cached re-solve of a
        ``solve_failed``/metric/unknown row (never memoised) consumes one too. A cached row that was
        already cached historically cost nothing and consumes nothing. A non-cached evaluation with
        no non-cached history is genuinely new work and ends the replay window.
        """
        if replay["remaining"] <= 0:
            return False
        t = (ev.design_hash, ev.mesh_hash, ev.solve_hash)
        historical = t in hist_non_cached
        if not ev.cached and not historical:
            replay["remaining"] = 0
            return False
        if ev.cached and not historical:
            return False
        replay["remaining"] -= 1
        return True

    def run_one(design) -> tuple[Evaluation, int, outcomes.Outcome]:
        """Evaluate one candidate, retrying the SAME candidate/spec for a transient solve failure
        (opt-in strict policy, at most two total attempts). Only the final evaluation is recorded
        (budget/evals/best), so a retry is a backend attempt, not a new draw; the failed attempt's
        ndjson row is still written by ``evaluate`` and remains truthful evidence.

        A replayed resume-prefix evaluation is evaluated through the same path (so a non-memoised
        ``solve_failed`` really re-solves) but its counters are suppressed: the historical attempt
        already spent that budget/attempt, and re-counting it would double-charge a resume."""
        total = 0.0
        attempts = 0
        replaying: bool | None = None
        while True:
            attempts += 1
            t0 = time.perf_counter()
            ev = evaluate(design, space, cfg, mode, run_dir, store, backend, ctx=ctx)
            if replaying is None:
                replaying = consume_replay(ev)
            total += time.perf_counter() - t0
            out = outcomes.classify(ev)
            # F1: count actual backend dispatches. Cache hits never reach the backend; a
            # deterministic geometry/envelope/resource refusal never reaches the solver either
            # (the evaluator may still attach a synthetic failure outcome, so the classification
            # is checked as well). The transient first attempt and its same-candidate retry each
            # reach the solver and are both counted.
            if not replaying:
                if not ev.cached and ev.outcome is not None and not out.deterministic_refusal:
                    state["backend_calls"] += 1
                if out.category == outcomes.CATEGORY_TRANSIENT:
                    state["transient_failures"] += 1
                elif out.category == outcomes.CATEGORY_METRIC:
                    state["metric_failures"] += 1
                elif out.category == outcomes.CATEGORY_UNKNOWN:
                    state["unknown_failures"] += 1
            if strict and out.retry_same_candidate and attempts < 2 and not ev.cached:
                if not replaying:
                    state["retries"] += 1
                log.warning("transient solve failure for %s; retrying the same candidate "
                            "(attempt %d/2)", ev.design_hash, attempts + 1)
                continue
            break
        evals.append(ev)
        if not replaying:
            budget_count(state, ev)             # B.4: same counters as the single-ES path
        if not ev.cached:
            wall.append(total)
        b = state["best"]
        # A failed/refused/descriptorless evaluation is never a best baseline; only a complete
        # score may become best, so state["best"] stays None until the first complete candidate.
        if out.complete and (b is None or ev.objective < b.objective):
            state["best"], state["best_no"] = ev, len(evals) - 1
            rundir.write_best(run_dir, ev, mode, state["best_no"])
        if not ev.cached and error_kind(ev.error) == "solve_failed":
            state["solve_fail_streak"] += 1
            if state["solve_fail_streak"] >= MAX_CONSECUTIVE_SOLVE_FAILURES:
                raise SolverUnhealthyError(
                    f"{state['solve_fail_streak']} consecutive solve_failed evaluations (last: "
                    f"{ev.error.splitlines()[0][:200]}); the solver is unhealthy, not the designs. "
                    f"Clear hosts (gpu-clean) and continue with --resume")
        elif not ev.cached:
            state["solve_fail_streak"] = 0
        return ev, attempts, out

    def archive_payload() -> dict:
        """The pinned ``archive.json`` payload: occupied cells only, sorted by (bin_h, bin_v).

        Cells carry the MINIMISATION objective (``objective`` = -archive objective, i.e. the same J
        as best.json) and the ndjson row number (``eval_no``) of the design that owns the cell. The
        stats are cumulative over every resume (they are read back from search.ndjson); the archive
        itself is rebuilt deterministically by replaying the same tells, so a resumed run ends with
        the same cells / ranges as an uninterrupted one."""
        eval_no = {}
        rows = read_ndjson(run_dir / "search.ndjson")
        for r in rows:
            eval_no.setdefault(str(r.get("design_hash")), r.get("n"))
        cells: list[dict] = []
        bounds = archive.boundaries
        data = archive.data()
        ints = np.asarray(data.get("index", []), dtype=np.int64)
        if ints.size:
            grid = archive.int_to_grid_index(ints)
            objs = np.asarray(data["objective"], dtype=float)
            sols = np.asarray(data["solution"], dtype=float)
            for k in range(len(ints)):
                i, j = int(grid[k][0]), int(grid[k][1])
                key = tuple(float(v) for v in sols[k])
                dh = hash_by_solution.get(key)
                if dh is None:
                    dh = space.denormalize(sols[k]).hash()
                cells.append({
                    "bin": [i, j],
                    "center": [
                        float(bounds[0][i] + 0.5 * (bounds[0][i + 1] - bounds[0][i])),
                        float(bounds[1][j] + 0.5 * (bounds[1][j + 1] - bounds[1][j])),
                    ],
                    "objective": float(-objs[k]),
                    "design_hash": dh,
                    "eval_no": eval_no.get(dh),
                })
        cells.sort(key=lambda c: (c["bin"][0], c["bin"][1]))
        total_bins = int(archive.cells)
        occupied = int(len(cells))
        non_cached = sum(1 for r in rows if not r.get("cached"))
        return {
            "algorithm": "cma_me",
            "descriptors": {"h": names[0], "v": names[1]},
            "bins": [bins[0], bins[1]],
            "ranges": {"h": list(DESCRIPTOR_RANGE_DEG), "v": list(DESCRIPTOR_RANGE_DEG)},
            "cells": cells,
            "stats": {
                "total_bins": total_bins,
                "occupied_bins": occupied,
                "coverage": (occupied / float(total_bins)) if total_bins else 0.0,
                "total_evals": len(rows),
                "non_cached": non_cached,
            },
        }

    def write_archive() -> dict:
        payload = archive_payload()
        rundir.write_json_atomic(run_dir / "archive.json", payload)
        # GUI contract: archive_heatmap.json is the ONLY file the read-only atlas consumes, and its
        # schema is exactly {"bins", "ranges", "descriptors": {"h", "v"}, "cells": [{h_center,
        # v_center, objective, design_hash}]} (occupied cells only). The descriptors are the same
        # names archive.json carries, so the atlas labels its axes without parsing the full record.
        heat = {
            "bins": payload["bins"],
            "ranges": payload["ranges"],
            "descriptors": payload["descriptors"],
            "cells": [{"h_center": c["center"][0], "v_center": c["center"][1],
                       "objective": c["objective"], "design_hash": c["design_hash"]}
                      for c in payload["cells"]],
        }
        rundir.write_json_atomic(run_dir / "archive_heatmap.json", heat)
        return payload

    def finish(status: str) -> None:
        payload = write_archive()
        last = summarize(evals, wall)
        stats = summarize_rows(read_ndjson(run_dir / "search.ndjson")) \
            if (run_dir / "search.ndjson").exists() else last
        seed_ev = state["seed_ev"]
        best = state["best"]
        upd = {"status": status, "finished_utc": rundir.utc_now(), "stop_reason": state["stop"],
               "stats": stats, "last_invocation": last, "budget": max_new}
        if seed_ev is not None:
            upd["seed"] = {"design_hash": seed_ev.design_hash, "objective": seed_ev.objective,
                           "terms": seed_ev.terms}
        if best is not None:
            upd["best"] = {"design_hash": best.design_hash, "objective": best.objective,
                           "eval_no": state["best_no"]}
        # Present ONLY for cma_me runs; a plain cma run.json keeps exactly today's schema.
        upd["qd"] = {"algorithm": "cma_me", "protocol": QD_PROTOCOL,
                     "descriptors": payload["descriptors"],
                     "bins": payload["bins"], "ranges": payload["ranges"],
                     "total_bins": payload["stats"]["total_bins"],
                     "occupied_bins": payload["stats"]["occupied_bins"],
                     "coverage": payload["stats"]["coverage"],
                     "total_evals": payload["stats"]["total_evals"],
                     "non_cached": payload["stats"]["non_cached"],
                     "descriptor_h_meaning": _describe_descriptor(names[0]),
                     "descriptor_v_meaning": _describe_descriptor(names[1]),
                     "failure_exclusion": {
                         "policy": QD_FAILURE_EXCLUSION_POLICY,
                         "version": QD_FAILURE_EXCLUSION_VERSION,
                         "search_archive": True,
                         "result_archive": True,
                         "emitter_rank_treatment": "failure_last_ranker",
                         "mae_feasible_only": False,
                         "note": ("Archive admission excludes non-complete evaluations; CMA-MAE "
                                  "threshold learning is NOT feasible-only learning and the "
                                  "emitter is not isolated from invalid ranks. This correction "
                                  "changes invalid admission/ranks and is not trajectory-neutral."),
                     },
                     "deterministic_refusal_policy": QD_DETERMINISTIC_REFUSAL_POLICY}
        if strict:
            upd["qd"]["error_policy"] = "retry_same_then_stop"
            upd["qd"]["error_policy_stats"] = {
                "backend_calls": int(state["backend_calls"]),
                "retries": int(state["retries"]),
                "transient_failures": int(state["transient_failures"]),
                "metric_failures": int(state["metric_failures"]),
                "unknown_failures": int(state["unknown_failures"]),
            }
            # Cumulative strict ledger/caps. Present only for the opt-in strict policy, so a
            # legacy (non-strict) cma_me run.json keeps exactly today's schema.
            if strict_state is not None:
                upd["qd"]["strict"] = {
                    "code": QD_STRICT_CODE,
                    "counters": counters_snapshot(),
                    "caps": cumulative_caps(),
                    "extensions": list(strict_state.get("extensions") or []),
                    "stop_reason": state["stop"],
                }
        if maes:
            upd["qd"]["maes"] = dict(maes)      # B.8: record the CMA-MAE archive parameters
        if pipe.enabled:
            upd["pipeline_prefetch"] = pipe.stats()
        # B.4: present only for budget_counts: valid (or an explicit max_attempts), so a default
        # cma_me run.json keeps today's schema byte-for-byte.
        bc = budget_counts_block(state, policy)
        if bc is not None:
            upd["budget_counts"] = bc
        if linked:
            upd["links"] = linked               # B.2: run.json records the resolved links
        if warm_record is not None:
            upd["warm_start"] = warm_record     # B.1: the warm-start sources + sigma record
        rundir.update_run_json(run_dir, **upd)
        suffix = ""
        if bc is not None:
            cap_txt = "none" if bc["attempts_cap"] is None else str(bc["attempts_cap"])
            suffix = (f", valid {bc['valid']} (budget counts), refusals free {bc['refused_free']}"
                      f", attempts {bc['attempts']}/{cap_txt}")
        log.info("CMA-ME %s: %d evaluations (%d new, %d cached), archive %d/%d cells "
                 "(%.1f%% coverage), best J=%.4f, %d failures %s%s",
                 status, stats["evaluations"], stats["non_cached"], stats["cache_hits"],
                 payload["stats"]["occupied_bins"], payload["stats"]["total_bins"],
                 100.0 * payload["stats"]["coverage"],
                 float("nan") if best is None else best.objective,
                 stats["failures"], stats["failures_by_reason"], suffix)

    # ------------------------------------------------------------------ F1 checkpoints
    def qd_dir() -> Path:
        d = run_dir / "qd"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def counters_snapshot() -> dict:
        """Cumulative counters persisted across a strict-QD resume (never reset on resume).

        ``attempts``/``new``/``valid``/``refused_free`` are the budget_count ledger; the rest are
        the F1 dispatch/retry/failure ledger. They are the only source of truth for a resume, so a
        second invocation cannot hand itself a fresh budget or attempt allowance.
        """
        return {"attempts": int(state.get("attempts", 0)),
                "new": int(state.get("n_new", 0)),
                "valid": int(state.get("n_valid", 0)),
                "refused_free": int(state.get("n_refused_free", 0)),
                "backend_calls": int(state.get("backend_calls", 0)),
                "retries": int(state.get("retries", 0)),
                "transient": int(state.get("transient_failures", 0)),
                "metric": int(state.get("metric_failures", 0)),
                "unknown": int(state.get("unknown_failures", 0))}

    def cumulative_caps() -> dict:
        return {"budget": int(policy["budget"]), "attempts_cap": policy["attempts_cap"]}

    def new_pending_rows(generation: int, X) -> list[dict]:
        rows = []
        for i, x in enumerate(X):
            design = space.denormalize(clip01(x))
            try:
                dh, mh, sh, key = _evaluation_identity(design, space, cfg, mode)
            except Exception:  # noqa: BLE001 - identity is bookkeeping; reconciliation then refuses
                dh = mh = sh = key = None
            rows.append({"index": int(i),
                         "unit_vector": [float(v) for v in np.asarray(x).reshape(-1)],
                         "design_hash": dh, "mesh_hash": mh, "solve_hash": sh, "key": key,
                         "dispatched": False, "attempts": 0,
                         "attempt_id": f"g{generation}-i{i}"})
        return rows

    def write_pending(generation: int, rows: list[dict]) -> None:
        rundir.write_json_atomic(qd_dir() / QD_PENDING_BATCH, {
            "protocol": QD_PROTOCOL,
            "identity": (strict_state or {}).get("identity"),
            "generation": int(generation), "vectors": rows,
            "counters": counters_snapshot(), "cumulative_caps": cumulative_caps(),
            "extensions": list((strict_state or {}).get("extensions") or []),
            "stop_reason": state["stop"]})

    def remove_pending() -> None:
        try:
            (qd_dir() / QD_PENDING_BATCH).unlink()
        except FileNotFoundError:
            pass

    def persist_strict_state(generation: int, vectors: list | None = None) -> None:
        if strict_state is None:
            return
        strict_state["protocol"] = QD_PROTOCOL
        strict_state["generation"] = int(generation)
        if vectors is not None:
            strict_state["vectors"] = vectors
        strict_state["counters"] = counters_snapshot()
        strict_state["cumulative_caps"] = cumulative_caps()
        strict_state["stop_reason"] = state["stop"]
        rundir.write_json_atomic(qd_dir() / QD_STRICT_STATE, strict_state)

    def write_strict_state(generation: int, X, evs: list[Evaluation],
                           outs: list[outcomes.Outcome]) -> None:
        rows = []
        for x, ev, out in zip(X, evs, outs):
            rows.append({"unit_vector": [float(v) for v in np.asarray(x).reshape(-1)],
                         "design_hash": ev.design_hash, "objective": float(ev.objective),
                         "category": out.category, "kind": out.kind,
                         "eligible": bool(out.complete)})
        persist_strict_state(generation, rows)

    def restore_counters(counters: dict) -> None:
        """Restore the cumulative ledger from a prior strict artifact. Also seeds
        ``replay["remaining"]`` with the stored NON-CACHED attempt count, so replaying the prefix
        (which is re-solved only for non-memoised failures) never double-charges it."""
        state["attempts"] = int(counters.get("attempts", 0) or 0)
        state["n_new"] = int(counters.get("new", 0) or 0)
        state["n_valid"] = int(counters.get("valid", 0) or 0)
        state["n_refused_free"] = int(counters.get("refused_free", 0) or 0)
        state["backend_calls"] = int(counters.get("backend_calls", 0) or 0)
        state["retries"] = int(counters.get("retries", 0) or 0)
        state["transient_failures"] = int(counters.get("transient", 0) or 0)
        state["metric_failures"] = int(counters.get("metric", 0) or 0)
        state["unknown_failures"] = int(counters.get("unknown", 0) or 0)
        replay["remaining"] = int(state["attempts"])

    def strict_setup() -> None:
        """Create/restore the cumulative strict-QD checkpoint BEFORE any ask/evaluate.

        ``qd/strict_state.json`` is the last TOLD generation and ``qd/pending_batch.json`` the
        current incomplete generation; the freshest (larger cumulative attempt count) is the
        resume source, so a run stopped before its first tell still loads its pending counters.
        The protocol/spec identity must match, caps persist, and a cap shrink is refused. A
        configured cap increase is recorded as an explicit extension (the plain-CMA
        ``cma/strict_state.json`` pattern).
        """
        nonlocal strict_state
        identity = _qd_strict_identity(cfg, lib_shas)
        told = rundir.read_json(qd_dir() / QD_STRICT_STATE)
        pending = rundir.read_json(qd_dir() / QD_PENDING_BATCH)
        # Prefer the freshest checkpoint. ``strict_state.json`` is the last TOLD generation; a
        # pending batch only exists for the current incomplete generation (it is removed after a
        # tell), so when both exist the pending counters include later work. Taking the larger
        # cumulative attempt count also ignores the zero-counter strict_state written at a fresh
        # run's setup before its first tell.
        candidates = [x for x in (told, pending) if isinstance(x, dict)]
        if not candidates:
            source = None
        else:
            source = max(candidates,
                         key=lambda x: int((x.get("counters") or {}).get("attempts", 0) or 0))
        if source is None:
            if rows0:
                raise ConfigError(
                    f"{run_dir}: strict-QD resume requires qd/{QD_STRICT_STATE} (or "
                    f"qd/{QD_PENDING_BATCH} when no generation was told), but this run has "
                    f"search.ndjson history and no strict checkpoint; refusing to reset the "
                    f"cumulative counters")
            strict_state = {"protocol": QD_PROTOCOL, "identity": identity, "generation": 0,
                            "vectors": [], "counters": {k: 0 for k in QD_COUNTER_KEYS},
                            "cumulative_caps": cumulative_caps(), "extensions": [],
                            "stop_reason": ""}
            persist_strict_state(0)
            return
        have = source.get("identity")
        if not isinstance(have, dict):
            raise ConfigError(
                f"{run_dir}: strict-QD resume refused: qd artifact has no identity block; this "
                f"build cannot validate the protocol/spec identity")
        for key in ("protocol", "code", "spec_sha", "algorithm", "error_policy", "qd_seed"):
            if have.get(key) != identity.get(key):
                raise ConfigError(
                    f"{run_dir}: strict-QD resume refused: {key} changed "
                    f"({have.get(key)!r} -> {identity.get(key)!r}); the protocol/spec identity "
                    f"must match")
        if dict(have.get("lib_shas") or {}) != dict(identity.get("lib_shas") or {}):
            raise ConfigError(f"{run_dir}: strict-QD resume refused: installed library SHAs changed")
        restore_counters(source.get("counters") or {})
        old = source.get("cumulative_caps") or {}
        extensions = list(source.get("extensions") or [])
        for name, new_v in (("budget", int(policy["budget"])),
                            ("attempts_cap", policy["attempts_cap"])):
            old_v = old.get(name)
            if old_v is None or new_v is None:
                continue
            old_v, new_v = int(old_v), int(new_v)
            if new_v < old_v:
                raise ConfigError(
                    f"{run_dir}: strict-QD resume refused: cumulative {name} cap would shrink "
                    f"({old_v} -> {new_v}); caps persist unless explicitly extended")
            if new_v > old_v:
                extensions.append({"cap": name, "from": old_v, "to": new_v})
        strict_state = {"protocol": QD_PROTOCOL, "identity": identity,
                        "generation": int(source.get("generation", 0) or 0),
                        "vectors": list(source.get("vectors") or []),
                        "counters": dict(source.get("counters") or {}),
                        "cumulative_caps": cumulative_caps(),
                        "extensions": extensions, "stop_reason": ""}
        persist_strict_state(strict_state["generation"])

    def reconcile_pending() -> bool:
        """True when it is safe to proceed; False when an unresolved attempt blocks dispatch.

        A dispatched vector is resolved when its EXACT solve/design identity has a durable row in
        ``search.ndjson`` (``design_hash``+``mesh_hash``+``solve_hash``) or the stored pending
        ``key`` matches a durable row. That includes a durable ``solve_failed``/metric/unknown row:
        those rows are deliberately NOT memoised, so the deterministic replay re-enters the same
        candidate and re-solves it instead of refusing the run forever. Only a dispatched vector
        with no durable row at all is a true unknown attempt and stops the run *before* any new
        ``scheduler.ask``. The previous archive.json/heatmap are left untouched on this refusal:
        they are derived outputs and an empty rebuild here would destroy the last valid atlas.
        """
        payload = rundir.read_json(run_dir / "qd" / QD_PENDING_BATCH)
        if not isinstance(payload, dict):
            return True
        if payload.get("protocol") != QD_PROTOCOL:
            reason = (f"unknown_pending_attempt: pending protocol "
                      f"{payload.get('protocol')!r} != {QD_PROTOCOL!r}")
        else:
            durable_keys = set()
            durable_ids = set()
            for r in rows0:
                key = r.get("key")
                if key:
                    durable_keys.add(str(key))
                t = (r.get("design_hash"), r.get("mesh_hash"), r.get("solve_hash"))
                if None not in t:
                    durable_ids.add(t)
            unresolved = []
            for row in payload.get("vectors") or []:
                if not row.get("dispatched"):
                    continue
                key = row.get("key")
                t = (row.get("design_hash"), row.get("mesh_hash"), row.get("solve_hash"))
                resolved = bool(key and str(key) in durable_keys) or (
                    None not in t and t in durable_ids)
                if resolved:
                    continue
                unresolved.append(row.get("attempt_id") or row.get("design_hash") or "?")
            reason = ("" if not unresolved else
                      f"unknown_pending_attempt: {len(unresolved)} unresolved vector(s) "
                      f"{unresolved[:4]}")
        if not reason:
            return True
        state["stop"] = reason
        log.error("CMA-ME resume refused: %s", reason)
        rundir.update_run_json(run_dir, status="aborted", finished_utc=rundir.utc_now(),
                               stop_reason=reason)
        return False

    def tell_batch(X, evs, outs) -> None:
        """Feed the full ask() batch back to the scheduler.

        Every row is still told in ask order. ``eligible`` marks only error-free complete
        evaluations WITH finite descriptors: failures and missing-descriptor rows are excluded from
        archive admission by both archives, while the emitter sees the full batch and the custom
        ranker keeps those rows last. Their fallback measure is API filler, never archived.
        """
        objective = np.asarray([-float(ev.objective) for ev in evs], dtype=float)
        fallback = seed_measures if seed_measures is not None else np.zeros(2, dtype=float)
        measures = []
        eligible = np.zeros(len(evs), dtype=bool)
        for i, (ev, x, out) in enumerate(zip(evs, X, outs)):
            vals = descriptor_values(ev, cfg, names)
            measures.append(np.asarray(vals if vals is not None else fallback, dtype=float))
            eligible[i] = bool(out.complete and vals is not None)
            hash_by_solution[tuple(float(v) for v in x)] = ev.design_hash
        scheduler.tell(objective=objective, measures=np.asarray(measures, dtype=float),
                       eligible=eligible)

    # S1/F1: reconcile an opt-in pending-intent checkpoint before ANY ask or evaluate.
    if not reconcile_pending():
        return state["best"]
    # F1/cumulative: restore the strict ledger/caps before a seed or candidate can spend anything.
    if strict:
        strict_setup()

    try:
        # 1. the seed first: every later number is meaningless without the baseline it must beat.
        seed_ev, seed_attempts, seed_out = run_one(space.seed)
        state["seed_ev"] = seed_ev
        if strict and seed_out.infrastructure:
            state["stop"] = _infrastructure_stop_reason(seed_out)
            finish("aborted")
            return state["best"]
        seed_desc = descriptor_values(seed_ev, cfg, names)
        if seed_desc is None and state["best"] is seed_ev:
            # A complete-but-descriptorless seed is still not an archive baseline; restore the
            # pre-seed best (None on a fresh run) and remove the best.json this seed just wrote.
            state["best"], state["best_no"] = prior_best, prior_best_no
            if prior_best is None:
                try:
                    (run_dir / "best.json").unlink()
                except FileNotFoundError:
                    pass
            else:
                rundir.write_best(run_dir, prior_best, mode, prior_best_no)
        if seed_desc is not None and seed_out.complete:
            seed_measures = np.asarray(seed_desc, dtype=float)
            # S1 Bug 1: archive the normalized geometry ACTUALLY EVALUATED (space.seed), never the
            # warm-start mean x0. A failed/refused seed is the recorded baseline but not an elite.
            hash_by_solution[tuple(float(v) for v in np.asarray(x_seed).reshape(-1))] = \
                seed_ev.design_hash
            seed_solution = np.asarray(x_seed, dtype=float)[None]
            seed_objective = np.asarray([-float(seed_ev.objective)])
            seed_measures_row = seed_measures[None]
            seed_eligible = np.asarray([True])
            # The complete seed is the shared baseline of BOTH archives; a failed/descriptorless
            # seed is added to neither (the exclusion semantics apply to the baseline too).
            archive.add(solution=seed_solution, objective=seed_objective,
                        measures=seed_measures_row, eligible=seed_eligible)
            result_archive.add(solution=seed_solution, objective=seed_objective,
                               measures=seed_measures_row, eligible=seed_eligible)
        log.info("seed J=%.4f terms=%s descriptors=%s archived=%s", seed_ev.objective,
                 {k: round(v, 4) for k, v in seed_ev.terms.items()},
                 None if seed_desc is None else tuple(round(v, 2) for v in seed_desc),
                 bool(seed_desc is not None and seed_out.complete))
        cap = int(max_evals) if max_evals else None

        def exhausted() -> bool:
            return budget_exhausted(state, policy, cap, len(evals))

        def maybe_refresh() -> None:
            nonlocal written_at
            if state["n_new"] - written_at >= ARCHIVE_REFRESH_EVALS:
                write_archive()
                written_at = state["n_new"]

        generation = 0
        while not exhausted():
            X = scheduler.ask()
            if len(X) == 0:                       # a degenerate emitter: never spin forever
                state["stop"] = "cma_me: no solutions"
                break
            pending_rows = new_pending_rows(generation, X) if strict else None
            if strict:
                write_pending(generation, pending_rows)
            batch_evs: list[Evaluation] = []
            batch_outs: list[outcomes.Outcome] = []
            cut = False
            abort = False
            if pipe.enabled:
                # WP2 (opt-in): identical order/run_one/tell; only the NEXT candidates' meshes are
                # built on a background worker while this one solves.
                designs = [space.denormalize(clip01(x)) for x in X]
                pipe.begin_generation(designs)
                for i, d in enumerate(designs):
                    if exhausted():
                        cut = True
                        break
                    pipe.before(i)
                    if strict:
                        pending_rows[i]["dispatched"] = True
                        pending_rows[i]["attempts"] = 1
                        write_pending(generation, pending_rows)
                    ev, attempts, out = run_one(d)
                    if strict:
                        pending_rows[i].update({"attempts": int(attempts),
                                                "category": out.category, "kind": out.kind,
                                                "eligible": bool(out.complete)})
                        write_pending(generation, pending_rows)
                    if strict and out.infrastructure:
                        state["stop"] = _infrastructure_stop_reason(out)
                        abort = True
                        break
                    batch_evs.append(ev)
                    batch_outs.append(out)
            else:
                for i, x in enumerate(X):
                    if exhausted():
                        cut = True
                        break
                    x = clip01(x)
                    if strict:
                        pending_rows[i]["dispatched"] = True
                        pending_rows[i]["attempts"] = 1
                        write_pending(generation, pending_rows)
                    ev, attempts, out = run_one(space.denormalize(x))
                    if strict:
                        pending_rows[i].update({"attempts": int(attempts),
                                                "category": out.category, "kind": out.kind,
                                                "eligible": bool(out.complete)})
                        write_pending(generation, pending_rows)
                    if strict and out.infrastructure:
                        state["stop"] = _infrastructure_stop_reason(out)
                        abort = True
                        break
                    batch_evs.append(ev)
                    batch_outs.append(out)
            if cut:                               # budget ran out mid-generation: do not tell
                state["stop"] = "budget"
                break
            if abort:                             # F1: stop resumably BEFORE tell
                break
            tell_batch(X, batch_evs, batch_outs)
            if strict:
                try:
                    write_strict_state(generation, X, batch_evs, batch_outs)
                    remove_pending()
                except Exception as exc:  # noqa: BLE001 - bookkeeping must not kill a told run
                    log.warning("could not write QD strict-state checkpoint: %s", exc)
            generation += 1
            maybe_refresh()
            log.info("CMA-ME generation %d: %d solutions, archive %d/%d cells, best overall %.4f "
                     "(%d new evaluations)", generation, len(X), len(archive), int(archive.cells),
                     float("nan") if state["best"] is None else state["best"].objective,
                     state["n_new"])
        if not state["stop"]:
            state["stop"] = "budget"
        finish("aborted" if state["stop"].startswith("qd_") or
               state["stop"].startswith("unknown_pending_attempt") else "finished")
    except KeyboardInterrupt:
        state["stop"] = "interrupted"
        finish("interrupted")
        raise
    except (MeshConsistencyError, SolverUnhealthyError) as exc:
        state["stop"] = f"aborted: {type(exc).__name__}: {exc}"
        finish("aborted")
        raise
    finally:
        pipe.close()
        _detach(backend)
    return state["best"]


def _refuse_incompatible_resume(run_dir: Path) -> None:
    """Refuse an existing cma_me run.json whose archive protocol is missing/different.

    archive.json / archive_heatmap.json are derived outputs, but old rows were produced under
    different admission semantics; reinterpreting them silently would corrupt the archive identity.
    """
    prior = rundir.read_json(Path(run_dir) / "run.json")
    if not isinstance(prior, dict):
        return
    qd_block = prior.get("qd")
    if not isinstance(qd_block, dict):
        return
    protocol = qd_block.get("protocol")
    if protocol != QD_PROTOCOL:
        raise ConfigError(
            f"resume {run_dir}: existing run.json has qd.protocol={protocol!r}, which is "
            f"incompatible with this build's {QD_PROTOCOL!r} failure-excluding archive semantics. "
            f"archive.json/archive_heatmap.json are derived outputs; start a new run or resume an "
            f"artifact produced by this protocol rather than reinterpreting old archive rows.")
