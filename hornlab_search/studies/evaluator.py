"""Production-shaped study evaluator adapter (B5 protocol, offline-testable).

The adapter performs no mesh, BEM, GPU or lane work itself.  The actual
single-attempt evaluation, cache lookup, model fit and proposal selection are
all injected callables so tests never need a real solver::

    evaluator = PipelineStudyEvaluator(
        service, package, config=cfg, space=space, encoding=encoding,
        training_set=training, pool=pool,
        evaluate_fn=fake_evaluate, lookup_fn=fake_lookup,
        fit_fn=fake_fit, propose_fn=fake_propose)

The runner (:func:`hornlab_search.studies.runner.run_package`) drives exactly
one candidate at a time via ``next_candidate/lookup/preflight/evaluate/observe``
and persists the proposal cadence through ``restore_progress`` /
``proposal_rng_state``.

Nothing here imports torch/botorch or starts a process at import time.  A
missing optional engine is reported as ``capability_missing``; it is never
papered over with a fabricated candidate or a zero prediction.
"""
from __future__ import annotations

import hashlib
import importlib.util
import math
from dataclasses import replace

import numpy as np

from hornlab_search.bo.propose import ProposalHistory

from .runner import (CAPABILITY_MISSING, CapabilityMissing, ContractError,
                     decode_proposal_history, encode_proposal_history,
                     select_verification)
from .schema import canonical

POOL_STATUS_NOTE = "cheap-check-passed; mesh/acoustic eligibility unknown"

_OUTCOME_LABELS = {
    "complete_score": "success",
    "measured_gate": "success",
    "geometry_refusal": "cheap_refusal",
    "envelope_refusal": "cheap_refusal",
    "resource_refusal": "cheap_refusal",
    "transient": "solver_failure",
    "metric_error": "metric_failure",
    "unknown_error": "unknown",
}

#: A numerical (not infrastructure) model failure pauses BO.
_NUMERICAL_MODEL_FAILURES = frozenset({
    "model_unavailable", "flat_training_response", "nonfinite_training_data",
})


def _sha(obj) -> str:
    return hashlib.sha256(canonical(obj).encode("utf-8")).hexdigest()


def _finite(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def _engine_available() -> bool:
    return all(importlib.util.find_spec(name) is not None
               for name in ("torch", "botorch", "gpytorch"))


class PipelineStudyEvaluator:
    """Evaluator protocol implementation with dependency-injected side effects."""

    adapter_contract = "b5-pipeline-evaluator-v1"

    def __init__(self, service, package, *, config=None, space=None, encoding=None,
                 training_set=None, pool=None, policy="scalar", evaluate_fn=None,
                 lookup_fn=None, fit_fn=None, propose_fn=None, preflight_fn=None,
                 run_root=None, resolution_mm=30.0, audit_seed=0, seed=0,
                 pipeline_factory=None):
        self.service = service
        self.package = package
        self.config = config
        self.space = space
        self.encoding = encoding
        self.training_set = training_set
        self.pool = pool
        self.policy = policy
        self.evaluate_fn = evaluate_fn
        self.lookup_fn = lookup_fn
        self.fit_fn = fit_fn
        self.propose_fn = propose_fn
        self.preflight_fn = preflight_fn
        self.run_root = run_root
        self.resolution_mm = float(resolution_mm)
        self.audit_seed = int(audit_seed)
        self.seed = int(seed)
        self.pipeline_factory = pipeline_factory
        self.runtime = None
        self.history = ProposalHistory()
        self.observations = {}
        self._vectors = {}
        self._measured = []
        self._verified_geometry_ids = set()
        self._issued = set()
        self.screen_index = 0
        self._screens_exhausted = False
        self.selection = None
        self._plan = None
        self.last_outcome = None
        self._last_fit = None

    # ------------------------------------------------------------------ capability

    def capability_status(self):
        missing = []
        if not callable(self.evaluate_fn):
            missing.append("evaluate_fn")
        if not callable(self.preflight_fn) and not callable(self.evaluate_fn):
            missing.append("preflight_fn")
        if self.pool is None and not callable(self.propose_fn):
            missing.append("pool")
        if not callable(self.fit_fn) and not _engine_available():
            missing.append("engine:fit")
        if (not callable(self.propose_fn) and self.policy not in ("exploration", "cma_seed")
                and not _engine_available()):
            missing.append("engine:propose")
        if self.package is None:
            missing.append("package")
        if missing:
            return {"status": CAPABILITY_MISSING,
                    "reason": "evaluator_adapter_unavailable",
                    "detail": "missing prerequisites: " + ", ".join(missing),
                    "missing": missing}
        return {"status": "ok", "reason": None, "detail": None, "missing": []}

    # ------------------------------------------------------------------ candidates

    def _budget(self):
        value = self.package.get("budget") if isinstance(self.package, dict) else None
        return value if isinstance(value, dict) else {}

    def _screen_capacity_used(self, state):
        reservations = state.get("reservations") or {}
        return (int(state.get("screen_calls", 0) or 0)
                + int(reservations.get("screen_calls", 0) or 0))

    def _normalise(self, raw, *, kind):
        if raw is None:
            return None
        if not isinstance(raw, dict):
            raw = getattr(raw, "proposal", None)
        if not isinstance(raw, dict):
            raise ContractError("proposal did not return a candidate object")
        vector = raw.get("active_vector", raw.get("vector"))
        if vector is not None:
            vector = [float(v) for v in np.asarray(vector, dtype=float).reshape(-1)]
        solve_id = (raw.get("solve_id") or raw.get("intended_solve_hash")
                    or raw.get("geometry_id") or raw.get("candidate_id")
                    or raw.get("design_hash"))
        if not isinstance(solve_id, str) or not solve_id:
            raise ContractError("every candidate needs an exact solve_id")
        geometry = str(raw.get("geometry_id") or raw.get("geometry_hash")
                       or raw.get("design_hash") or solve_id)
        candidate = {
            "kind": kind,
            "solve_id": solve_id,
            "candidate_id": raw.get("candidate_id"),
            "geometry_id": geometry,
            "geometry_hash": raw.get("geometry_hash", raw.get("geometry_id")),
            "design_hash": raw.get("design_hash"),
            "intended_solve_hash": raw.get("intended_solve_hash"),
            "params": dict(raw.get("params") or {}),
            "x": raw.get("x", vector),
            "vector": vector,
            "predicted": raw.get("predicted"),
            "status": raw.get("status") or POOL_STATUS_NOTE,
            "checks": dict(raw.get("checks") or {}),
            "descriptors": dict(raw.get("descriptors") or {}),
        }
        if vector is not None:
            candidate["active_vector"] = vector
        if candidate["params"] or candidate["x"] is not None:
            self._vectors[solve_id] = candidate["x"] if candidate["x"] is not None else vector
        return candidate

    def _propose_through_policy(self):
        from hornlab_search.bo import policy as policy_mod
        if self.policy == "exploration" or self.policy == "cma_seed":
            params = {}
        outcome = policy_mod.fit_and_propose(
            self.policy, training_set=self.training_set, pool=self.pool,
            history=self.history, seed=self.seed, encoding=self.encoding,
            config=self.config, resolution_mm=self.resolution_mm)
        self.last_outcome = outcome
        if outcome.status != "ok" or outcome.proposal is None:
            return None
        return outcome.proposal

    def _propose_screen(self, state):
        budget = self._budget()
        if self._screen_capacity_used(state) >= int(budget.get("screen_calls", 18)):
            return None
        raw = self.propose_fn(state) if callable(self.propose_fn) else self._propose_through_policy()
        if raw is None:
            return None
        candidate = self._normalise(raw, kind="screen")
        if candidate is None:
            return None
        index = int(self.history.proposal_index)
        exc_geo = list(self.history.excluded_geometry_hashes)
        exc_design = list(self.history.excluded_design_hashes)
        if candidate.get("geometry_hash") and candidate["geometry_hash"] not in exc_geo:
            exc_geo.append(str(candidate["geometry_hash"]))
        if candidate.get("design_hash") and candidate["design_hash"] not in exc_design:
            exc_design.append(str(candidate["design_hash"]))
        self.history = replace(
            self.history, proposal_index=index + 1,
            excluded_geometry_hashes=tuple(exc_geo),
            excluded_design_hashes=tuple(exc_design))
        self.screen_index += 1
        self._issued.add(candidate["solve_id"])
        return candidate

    def _verification_rows(self):
        rows = []
        for result in self._measured:
            geometry = result.get("geometry_id")
            j = _finite(result.get("observed_j"))
            if not geometry or j is None:
                continue
            row = {
                "geometry_id": geometry,
                "eligible": result.get("eligible") is True,
                "measured_screen": True,
                "already_verified": geometry in self._verified_geometry_ids,
                "j": j,
                "feasible": bool(result.get("feasible", True)),
                "solve_id": result.get("solve_id"),
            }
            if result.get("objectives") is not None:
                row["objectives"] = result["objectives"]
            rows.append(row)
        return rows

    def _build_verification_plan(self):
        rows = self._verification_rows()
        if not rows:
            self._plan = []
            return
        mode = "pareto" if self.policy == "pareto" else "scalar"
        objective_box = None
        if mode == "pareto":
            values = [r["objectives"] for r in rows if r.get("objectives") is not None]
            if values:
                objective_box = [[min(v[i] for v in values), max(v[i] for v in values)]
                                 for i in range(2)]
        try:
            self.selection = select_verification(
                rows, mode=mode, audit_seed=self.audit_seed, objective_box=objective_box)
        except ContractError:
            # A Pareto plan without a finite fixed reference is reported as a shortfall,
            # never replaced with predicted designs.
            self.selection = {"finalists": [], "audits": [], "shortfall": 4,
                              "audit_shortfall": 2, "audit_seed": self.audit_seed}
        plan = ([("verify", gid) for gid in self.selection["finalists"]]
                + [("audit", gid) for gid in self.selection["audits"]])
        self._plan = [(kind, gid) for kind, gid in plan if gid not in self._issued]

    def next_candidate(self, state):
        budget = self._budget()
        if not self._screens_exhausted:
            if self._screen_capacity_used(state) < int(budget.get("screen_calls", 18)):
                candidate = self._propose_screen(state)
                if candidate is not None:
                    return candidate
                self._screens_exhausted = True
            else:
                self._screens_exhausted = True
        if self._plan is None:
            self._build_verification_plan()
        while self._plan:
            kind, geometry = self._plan.pop(0)
            solve_id = f"{kind}:{geometry}"
            if solve_id in self._issued or geometry in self._verified_geometry_ids:
                continue
            vector = None
            params = {}
            for result in self._measured:
                if result.get("geometry_id") == geometry:
                    vector = result.get("x")
                    params = dict(result.get("params") or {})
                    break
            self._issued.add(solve_id)
            candidate = self._normalise({
                "solve_id": solve_id, "geometry_id": geometry,
                "geometry_hash": geometry, "x": vector, "params": params,
                "active_vector": vector, "status": "measured screen finalist",
            }, kind=kind)
            if candidate is None:
                continue
            candidate["solve_id"] = solve_id
            return candidate
        return None

    # ------------------------------------------------------------------ evaluation

    def lookup(self, candidate):
        if callable(self.lookup_fn):
            return self.lookup_fn(candidate)
        return None

    def preflight(self, candidate):
        if callable(self.preflight_fn):
            return self.preflight_fn(candidate)
        checks = candidate.get("checks") or {}
        if not checks:
            return None
        refused = []
        if checks.get("envelope_ok") is False:
            refused.append("invalid_envelope: brief envelope check failed")
        if checks.get("throat_ok") is False:
            refused.append("invalid_geometry: throat radius mismatch")
        if checks.get("schema_ok") is False:
            refused.append("invalid_geometry: schema check failed")
        if not refused:
            return None
        return self.cheap_refusal(candidate, refused[0])

    def cheap_refusal(self, candidate, error):
        return {
            "solve_id": candidate["solve_id"],
            "kind": candidate.get("kind"),
            "call_status": "not_called",
            "outcome": "cheap_refusal",
            "eligible": False,
            "error": str(error),
            "geometry_id": candidate.get("geometry_id"),
            "design_hash": candidate.get("design_hash"),
        }

    def _design(self, candidate):
        named = candidate.get("design")
        if named is not None:
            return named
        from hornlab_search.types import Design
        family = getattr(self.config, "family", None) or candidate.get("family") or "OSSE"
        params = dict(candidate.get("params") or {})
        return Design(str(family), params)

    def evaluate(self, candidate, attempt_id):
        if not callable(self.evaluate_fn):
            raise CapabilityMissing("no evaluate_fn injected")
        design = self._design(candidate)
        evaluation = self.evaluate_fn(design, attempt_id, self.runtime)
        return self.result_from_evaluation(candidate, evaluation)

    @staticmethod
    def result_from_evaluation(candidate, evaluation):
        """Map a normal ``Evaluation`` to the durable journal result shape."""
        from hornlab_search.search.outcomes import classify

        outcome = classify(evaluation)
        cached = bool(getattr(evaluation, "cached", False))
        label = "cached" if cached else _OUTCOME_LABELS.get(outcome.category, "unknown")
        objective = _finite(getattr(evaluation, "objective", None))
        eligible = bool(outcome.complete and not cached and objective is not None
                        and candidate.get("kind") == "screen")
        physical_identity = {
            "design_hash": getattr(evaluation, "design_hash", None),
            "mesh_hash": getattr(evaluation, "mesh_hash", None),
            "solve_hash": getattr(evaluation, "solve_hash", None),
        }
        physical_id = _sha(physical_identity)
        terms = getattr(evaluation, "terms", None) or {}
        score_id = _sha({"objective": objective, "terms": terms})
        metrics = getattr(evaluation, "metrics", None)
        coverage = _finite(terms.get("cov")) if isinstance(terms, dict) else None
        ripple = _finite(terms.get("rip")) if isinstance(terms, dict) else None
        result = {
            "solve_id": candidate["solve_id"],
            "kind": candidate.get("kind"),
            "call_status": "not_called" if cached else "called",
            "outcome": label,
            "eligible": eligible and label != "unknown",
            "physical_id": physical_id,
            "score_id": score_id,
            "observed_j": objective if outcome.complete and objective is not None else None,
            "coverage_deg": coverage,
            "ripple_db": ripple,
            "units": {"j": "dimensionless", "coverage_deg": "degree", "ripple_db": "dB"},
            "design_hash": getattr(evaluation, "design_hash", None),
            "geometry_hash": getattr(evaluation, "design_hash", None),
            "mesh_hash": getattr(evaluation, "mesh_hash", None),
            "solve_hash": getattr(evaluation, "solve_hash", None),
            "geometry_id": candidate.get("geometry_id"),
            "error": str(getattr(evaluation, "error", "") or ""),
            "metrics_present": metrics is not None,
            "x": candidate.get("x"),
            "params": candidate.get("params") or {},
            "physical_measurement": bool(outcome.complete),
        }
        return result

    # ------------------------------------------------------------------ learning

    def _observation_vectors(self, result):
        solve_id = result.get("solve_id")
        vector = self._vectors.get(solve_id)
        if vector is None and isinstance(result.get("x"), (list, tuple)):
            vector = result["x"]
        return vector

    def _add_observation(self, result):
        if result.get("outcome") not in ("success", "cached"):
            return False
        if result.get("eligible") is not True:
            return False
        j = _finite(result.get("observed_j"))
        physical_id = result.get("physical_id")
        if j is None or not isinstance(physical_id, str) or not physical_id:
            return False
        vector = self._observation_vectors(result)
        if vector is None:
            return False
        from hornlab_search.bo.data import TrainingObservation
        self.observations[physical_id] = TrainingObservation(
            observation_id=physical_id, x=np.asarray(vector, dtype=float), J=j,
            status="ok", eligible=True,
            geometry_hash=result.get("design_hash") or result.get("geometry_id"),
            solve_hash=physical_id)
        return True

    def _refit(self):
        from hornlab_search.bo.data import build_training_set
        if not self.observations:
            return True
        d = getattr(self.encoding, "d", None)
        if d is None:
            d = getattr(self.training_set, "d", None)
        if d is None:
            first = next(iter(self.observations.values()))
            d = int(np.asarray(first.x).reshape(-1).size)
        training = build_training_set(list(self.observations.values()),
                                      encoding=self.encoding, d=d)
        if training.status != "ok":
            # Below n_min is not a numerical failure; keep collecting observations.
            self.training_set = training
            return True
        self.training_set = training
        if callable(self.fit_fn):
            fitted = self.fit_fn(training, self.seed)
        else:
            from hornlab_search.bo.model import fit_model
            fitted = fit_model(training, seed=self.seed)
        self._last_fit = fitted
        status = getattr(fitted, "status", None)
        reason = getattr(fitted, "reason", None)
        if status == "ok":
            return True
        if reason == "capability_missing":
            return True
        return reason not in _NUMERICAL_MODEL_FAILURES

    def observe(self, result):
        if not isinstance(result, dict):
            return True
        kind = result.get("kind")
        if kind in ("verify", "audit"):
            geometry = result.get("geometry_id")
            if geometry:
                self._verified_geometry_ids.add(str(geometry))
            return True
        if self._add_observation(result):
            self._measured.append(result)
            return self._refit()
        if result.get("eligible") is True and result.get("outcome") == "success":
            self._measured.append(result)
        return True

    # ------------------------------------------------------------------ resume

    def restore_progress(self, progress):
        if not isinstance(progress, dict):
            raise ContractError("journal progress must be an object")
        self.history = decode_proposal_history(progress.get("rng_state"),
                                               progress.get("proposal_index"))
        stored = progress.get("rng_state")
        if isinstance(stored, dict):
            extra = stored.get("rng_state")
            if isinstance(extra, dict):
                self.screen_index = int(extra.get("screen_index", self.screen_index))
                self._verified_geometry_ids = set(
                    str(x) for x in (extra.get("verified_geometry_ids") or ()))
                if extra.get("screens_exhausted"):
                    self._screens_exhausted = True
        self.observations = {}
        self._measured = []
        for item in progress.get("observations") or ():
            result = item.get("result") or {}
            candidate = item.get("candidate") or {}
            if isinstance(candidate, dict) and candidate.get("solve_id") and result.get("x") is None:
                result = {**result, "x": candidate.get("x"), "params": candidate.get("params")}
            if self._add_observation(result):
                self._measured.append(result)
        return True

    def proposal_rng_state(self):
        extra = {
            "audit_seed": self.audit_seed,
            "policy": self.policy,
            "screen_index": self.screen_index,
            "screens_exhausted": self._screens_exhausted,
            "verified_geometry_ids": sorted(self._verified_geometry_ids),
            "verification_selection": self.selection,
        }
        return encode_proposal_history(self.history, extra)


def build_production_wiring(service, package, *, root, config_path, lane=None,
                            pipeline_factory=None, lane_factory=None):
    """Build the real evaluate function + owned lane **only** when fully wired.

    This helper performs no work at import time and no solve here.  It refuses
    with ``capability_missing`` when the production pipeline factory, engine
    modules, config or lane roots are unavailable, so an API launcher can map
    the refusal to HTTP 503 without pretending an adapter exists.
    """
    from pathlib import Path

    missing = []
    if not isinstance(package, dict) or not package.get("package_id"):
        missing.append("package")
    path = Path(str(config_path)) if config_path else None
    if path is None or not path.is_file():
        missing.append("config")
    if importlib.util.find_spec("hornlab_mesher") is None:
        missing.append("hornlab_mesher")
    if not callable(pipeline_factory):
        missing.append("pipeline_factory")
    if missing:
        return {"status": CAPABILITY_MISSING, "reason": "production_wiring_unavailable",
                "detail": "missing prerequisites: " + ", ".join(missing),
                "missing": missing}

    from hornlab_search.config import load_config
    from .lanes import StudyLane

    cfg = load_config(path)
    factory = lane_factory or StudyLane
    runs_root = Path(root).resolve()
    lane_adapter = factory(
        runs_root=runs_root / "runs",
        cpu_cache=runs_root / "cache_cpu", gpu_cache=runs_root / "cache",
        cpu_dataset=runs_root / "dataset_cpu", gpu_dataset=runs_root / "dataset")
    evaluate_fn, lookup_fn, preflight_fn = pipeline_factory(cfg, package, lane_adapter)
    return {"status": "ok", "config": cfg, "lane": lane_adapter,
            "evaluate_fn": evaluate_fn, "lookup_fn": lookup_fn,
            "preflight_fn": preflight_fn}


__all__ = ["PipelineStudyEvaluator", "build_production_wiring", "POOL_STATUS_NOTE"]
