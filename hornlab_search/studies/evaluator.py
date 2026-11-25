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


def record_metric_measurement(result, terms, replay, *, brief, dataset_record=None):
    """Attach canonical metric labels to a freshly measured screen for journal/refit."""
    from hornlab_search.bo.metric_contracts import parity_tolerance
    from hornlab_search.bo.metric_training import extract_contributions

    if (result.get("kind") != "screen" or result.get("call_status") != "called"
            or result.get("eligible") is not True):
        return {**result, "eligible": False, "metric_refusal": "not_new_eligible_screen"}

    version = brief.objective_version
    if (not replay.complete or replay.objective_version != version
            or replay.design_hash != result.get("design_hash")
            or not all((replay.physical_id, replay.score_id, replay.metric_id))):
        return {**result, "eligible": False, "metric_refusal": "replay_identity_mismatch"}

    j, live_j, stored_j = map(_finite, (replay.j, result.get("observed_j"), replay.stored_j))
    if (j is None or live_j is None or stored_j is None
            or max(abs(j - live_j), abs(j - stored_j)) > parity_tolerance(j)):
        return {**result, "eligible": False, "metric_refusal": "replay_score_mismatch"}

    labels = extract_contributions(terms, objective_version=version,
                                   weights=brief.weights, params=brief.objective_params)
    replay_labels = extract_contributions(replay.terms, objective_version=version,
                                          weights=brief.weights, params=brief.objective_params)
    for source, row in (("live", labels), ("replay", replay_labels)):
        if not row.ok:
            return {**result, "eligible": False, "metric_refusal": f"{source}:{row.reason}"}
        if abs(j - row.j) > parity_tolerance(j):
            return {**result, "eligible": False, "metric_refusal": f"{source}:component_total_mismatch"}
    if (labels.cd_status != replay_labels.cd_status or labels.quality_flags != replay_labels.quality_flags
            or any(abs(a - b) > parity_tolerance(j)
                   for a, b in zip(labels.components, replay_labels.components, strict=True))):
        return {**result, "eligible": False, "metric_refusal": "replay_component_mismatch"}

    record = {**result, "observed_j": j, "stored_j": stored_j, "objective_version": version,
              "physical_id": replay.physical_id, "score_id": replay.score_id, "metric_id": replay.metric_id,
              "components": labels.components.tolist(), "component_names": list(labels.component_names),
              "component_schema_hash": labels.schema_hash, "cd_status": labels.cd_status,
              "quality_flags": list(labels.quality_flags)}
    if dataset_record is not None:
        record["metric_dataset_record"] = dataset_record
    return record


def load_metric_dataset_record(store, position, result, *, run_id, version):
    """Read back the exact record committed by this attempt and bind its catalog physical ID."""
    from hornlab_search.bo.metric_contracts import parity_tolerance
    from hornlab_search.dataset.identity_v2 import physical_solve_id

    if position is None:
        raise ValueError("dataset_record_missing")
    shard, row = position
    meta, arrays = store.read(shard, row)
    full_key = tuple(meta.get(k) for k in ("design_hash", "mesh_hash", "solve_hash"))
    expected_key = tuple(result.get(k) for k in ("design_hash", "mesh_hash", "solve_hash"))
    if (not all(full_key) or full_key != expected_key or meta.get("run_id") != run_id
            or meta.get("objective_version") != version or (meta.get("solve") or {}).get("mode") != "screen"
            or meta.get("ok") is not True or not arrays):
        raise ValueError("dataset_record_identity_mismatch")
    stored_j, replay_j = map(_finite, (meta.get("objective"), result.get("observed_j")))
    if stored_j is None or replay_j is None or abs(stored_j - replay_j) > parity_tolerance(replay_j):
        raise ValueError("dataset_record_score_mismatch")
    return meta, {"root": str(store.root), "shard": shard, "row": row,
                  "physical_solve_id": physical_solve_id(*full_key)}


def bind_metric_record_identity(meta, result, *, expected, encoding, bounds_hash):
    """Validate task and active-space identity before a measured row can enter a refit."""
    from hornlab_search.bo.metric_training import bounds_identity
    from hornlab_search.dataset.catalog_identity import catalog_identity_from_record
    from hornlab_search.types import Design

    actual = catalog_identity_from_record(meta)
    changed = [key for key, value in expected.items() if not value or actual.get(key) != value]
    if changed:
        raise ValueError("metric_task_identity_mismatch:" + ",".join(sorted(changed)))
    if not bounds_hash or bounds_identity(encoding) != bounds_hash:
        raise ValueError("metric_bounds_identity_mismatch")
    design = Design(meta["family"], meta["params"])
    if design.hash() != result.get("design_hash"):
        raise ValueError("metric_materialized_design_mismatch")
    measured = encoding.normalize_design(design, verify_round_trip=True)
    proposed = np.asarray(result.get("x"), dtype=np.float64)
    if (measured.shape != proposed.shape or not np.isfinite(proposed).all()
            or np.max(np.abs(measured - proposed)) > 1e-6):
        raise ValueError("metric_proposal_projection_mismatch")
    return {**expected, "bounds_hash": bounds_hash, "active_keys": list(encoding.active_keys)}


def _engine_available() -> bool:
    return all(importlib.util.find_spec(name) is not None
               for name in ("torch", "botorch", "gpytorch"))


def _family_geometry_hash(candidate):
    """Return a proposal's surface identity only for the versioned grid family."""
    params = candidate.get("params") or {}
    grid = params.get("grid") if isinstance(params, dict) else None
    if not isinstance(grid, dict):
        return None
    from hornlab_search.design.generators.rolled_family import is_family_spec
    value = candidate.get("geometry_hash")
    return value if is_family_spec(grid) and isinstance(value, str) and value else None


class PipelineStudyEvaluator:
    """Evaluator protocol implementation with dependency-injected side effects."""

    adapter_contract = "b5-pipeline-evaluator-v1"

    def __init__(self, service, package, *, config=None, space=None, encoding=None,
                 training_set=None, pool=None, policy="scalar", evaluate_fn=None,
                 lookup_fn=None, fit_fn=None, propose_fn=None, preflight_fn=None,
                 run_root=None, resolution_mm=30.0, audit_seed=0, seed=0,
                 pipeline_factory=None, pareto_training=None):
        self.service = service
        self.package = package
        self.config = config
        self.space = space
        self.encoding = encoding
        self.training_set = training_set
        # The immutable historical cohort remains the base of every adaptive refit.
        self._initial_training = training_set
        self._initial_observations = self._training_observations(training_set)
        self.pool = pool
        self.policy = policy
        # turbo: durable trust-region state (spec 3.6); pareto: frozen-reference metric rows.
        self.turbo_state = None
        if policy == "turbo" and training_set is not None and training_set.X is not None:
            from hornlab_search.bo.turbo import initial_state
            self.turbo_state = initial_state(training_set)
        self.pareto_training = pareto_training
        self._pareto_rows = {}
        self.pareto_excluded = {}
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
        identities = (getattr(training_set, "meta", {}) or {}).get("identities") or {}
        self._family_history_hashes = tuple(dict.fromkeys(
            str(identity["geometry_hash"]) for identity in identities.values()
            if identity.get("geometry_hash")))
        self.history = ProposalHistory(excluded_geometry_hashes=self._family_history_hashes)
        # Journal staging counts all candidates; BO exploration cadence counts screens only.
        self._proposal_sequence = 0
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

    @staticmethod
    def _training_observations(training):
        from hornlab_search.bo.data import TrainingObservation
        if training is None or training.X is None or training.J is None:
            return {}
        if training.status != "ok":
            raise ContractError("historical training cohort is not eligible")
        identities = (training.meta or {}).get("identities", {})
        rows = {}
        for i, oid in enumerate(training.ids):
            identity = identities.get(oid, {})
            rows[oid] = TrainingObservation(
                observation_id=oid, x=np.asarray(training.X[i], dtype=float).copy(),
                J=float(np.asarray(training.J).reshape(-1)[i]),
                geometry_hash=identity.get("geometry_hash") or identity.get("design_hash"),
                solve_hash=identity.get("solve_hash"),
                y_phys=(tuple(np.asarray(training.Y_phys[i]).reshape(-1))
                        if training.Y_phys is not None else None))
        return rows

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
            "selection_reason": raw.get("selection_reason"),
            "acquisition": raw.get("acquisition"),
            "trust_region": raw.get("trust_region"),
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
        extra = {}
        if self.policy == "turbo":
            extra["turbo_state"] = self.turbo_state
        elif self.policy == "pareto":
            current = self.current_pareto_training()
            if current is None:
                self.last_outcome = None
                return None
            extra["pareto_training"] = current
        outcome = policy_mod.fit_and_propose(
            self.policy, training_set=self.training_set, pool=self.pool,
            history=self.history, seed=self.seed, encoding=self.encoding,
            config=self.config, resolution_mm=self.resolution_mm, **extra)
        self.last_outcome = outcome
        if self.policy == "turbo":
            self.adopt_trust_region(getattr(outcome, "trust_region", None))
        if outcome.status != "ok" or outcome.proposal is None:
            return None
        if not isinstance(outcome.proposal, dict):
            return outcome.proposal
        proposal = dict(outcome.proposal)
        # Persist the model's own statement with the candidate.  Without this the run
        # results only carry the initial proposal's prediction, so calibration and the
        # trust-region history cannot be reconstructed after the fact.
        proposal["predicted"] = outcome.predicted
        proposal["selection_reason"] = outcome.selection_reason
        proposal["acquisition"] = outcome.acquisition
        if outcome.trust_region is not None:
            proposal["trust_region"] = outcome.trust_region
        return proposal

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
        self._proposal_sequence += 1
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

    def _verify_capacity_used(self, state):
        """Verification calls already spent plus those currently reserved."""
        reservations = state.get("reservations") or {}
        return (int(state.get("verify_calls", 0) or 0)
                + int(reservations.get("verify_calls", 0) or 0))

    def _build_verification_plan(self, state=None):
        # A profile may budget zero verification calls (owner decision 2026-11-15: exploratory
        # arms skip verification). Never emit a candidate the journal will refuse: report the
        # full shortfall and stop cleanly instead.
        remaining = None if state is None else (
            int(self._budget().get("verify_calls", 6)) - self._verify_capacity_used(state))
        if remaining is not None and remaining <= 0:
            self.selection = {"finalists": [], "audits": [], "shortfall": 4,
                              "audit_shortfall": 2, "audit_seed": self.audit_seed}
            self._plan = []
            return
        rows = self._verification_rows()
        if not rows:
            self._plan = []
            return
        mode = "pareto" if self.policy == "pareto" else "scalar"
        objective_box = None
        if mode == "pareto":
            values = [r["objectives"] for r in rows if r.get("objectives") is not None]
            limits = ((self.pareto_training.reference or {}).get("limits")
                      if self.pareto_training is not None else None)
            if values and limits is not None:
                # Fixed reference-normalised box (spec 3.5): [0, frozen limit] per error.
                objective_box = [[0.0, max(float(limits[i]), max(v[i] for v in values))]
                                 for i in range(2)]
            elif values:
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
        plan = [(kind, gid) for kind, gid in plan if gid not in self._issued]
        if remaining is not None:
            # Never propose more verification than the profile budgets (2 in comparison-25x2).
            kept = plan[:max(0, remaining)]
            dropped = plan[len(kept):]
            if dropped:
                self.selection["shortfall"] = int(self.selection.get("shortfall") or 0) + sum(
                    1 for kind, _ in dropped if kind == "verify")
                self.selection["audit_shortfall"] = int(
                    self.selection.get("audit_shortfall") or 0) + sum(
                    1 for kind, _ in dropped if kind == "audit")
            plan = kept
        self._plan = plan

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
            self._build_verification_plan(state)
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
            self._proposal_sequence += 1
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
        result = {
            "solve_id": candidate["solve_id"],
            "kind": candidate.get("kind"),
            "call_status": "not_called" if cached else "called",
            "outcome": label,
            "eligible": eligible and label != "unknown",
            "physical_id": physical_id,
            "score_id": score_id,
            "observed_j": objective if outcome.complete and objective is not None else None,
            # v4/v7 terms are tolerance-normalised objective contributions,
            # never physical degrees or dB. Physical curves live in metrics.json.
            "normalized_terms": {key: _finite(terms.get(key)) for key in ("cov", "rip")},
            "units": {"j": "dimensionless", "normalized_terms": "dimensionless"},
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
        family_hash = _family_geometry_hash(candidate)
        if family_hash:
            result["geometry_hash"] = family_hash
        return result

    # ------------------------------------------------------------------ learning

    def _observation_vectors(self, result):
        solve_id = result.get("solve_id")
        vector = self._vectors.get(solve_id)
        if vector is None and isinstance(result.get("x"), (list, tuple)):
            vector = result["x"]
        return vector

    def _add_observation(self, result):
        if result.get("kind") in ("verify", "audit"):
            return False
        if result.get("outcome") not in ("success", "cached"):
            return False
        if result.get("eligible") is not True:
            return False
        j = _finite(result.get("observed_j"))
        physical_id = result.get("physical_id")
        if j is None or not isinstance(physical_id, str) or not physical_id:
            return False
        if physical_id in self._initial_observations or physical_id in self.observations:
            return False
        vector = self._observation_vectors(result)
        if vector is None:
            return False
        from hornlab_search.bo.data import TrainingObservation
        self.observations[physical_id] = TrainingObservation(
            observation_id=physical_id, x=np.asarray(vector, dtype=float), J=j,
            status="ok", eligible=True,
            geometry_hash=(_family_geometry_hash(result) or result.get("design_hash")
                           or result.get("geometry_id")),
            solve_hash=result.get("solve_hash") or physical_id)
        return True

    # ------------------------------------------------------------------ turbo / pareto state

    def adopt_trust_region(self, record):
        """Adopt ``record['state_after']`` from a turbo proposal (artifact or live)."""
        if not isinstance(record, dict) or record.get("state_after") is None:
            return
        from hornlab_search.bo.turbo import TurboState
        self.turbo_state = TurboState.from_dict(record["state_after"])

    def _turbo_observe(self, result):
        """Update the trust region once per completed screen; infra/unknown never update it."""
        if self.policy != "turbo" or self.turbo_state is None or result.get("kind") != "screen":
            return
        from hornlab_search.bo.turbo import OUTCOME_MEASURED, OUTCOME_REFUSAL, update_state
        solve_id = result.get("solve_id")
        outcome = result.get("outcome")
        j = _finite(result.get("observed_j"))
        if outcome in ("success", "cached") and result.get("eligible") is True and j is not None:
            vector = self._observation_vectors(result)
            if vector is None:
                return
            self.turbo_state = update_state(self.turbo_state, outcome=OUTCOME_MEASURED,
                                            candidate=[float(v) for v in vector], J=j,
                                            solve_id=solve_id)
        elif outcome == "cheap_refusal":
            self.turbo_state = update_state(self.turbo_state, outcome=OUTCOME_REFUSAL,
                                            solve_id=solve_id)

    def _pareto_observe(self, result):
        """Bind the screen's measured physical errors (same frozen policy) or record exclusion."""
        if self.policy != "pareto" or self.pareto_training is None:
            return
        physical_id = result.get("physical_id")
        if (result.get("kind") != "screen" or result.get("eligible") is not True
                or not physical_id or physical_id not in self.observations):
            return
        metric = result.get("pareto_metric")
        expected = self.pareto_training.metric_spec_hash
        reason = None
        if not isinstance(metric, dict):
            reason = "metric observation missing"
        elif metric.get("status") != "complete":
            reason = f"metric observation {metric.get('status')}: {metric.get('reason')}"
        elif metric.get("physical_metric_spec_hash") != expected:
            reason = "metric observation uses a different metric spec hash"
        else:
            cov, rip = _finite(metric.get("coverage_deg")), _finite(metric.get("ripple_db"))
            if cov is None or rip is None or cov < 0 or rip < 0:
                reason = "metric observation is non-finite or negative"
        if reason is not None:
            self.pareto_excluded[physical_id] = reason
            return
        obs = self.observations[physical_id]
        self._pareto_rows[physical_id] = (np.asarray(obs.x, dtype=float), cov, rip, float(obs.J),
                                          str(obs.geometry_hash or physical_id))
        result["objectives"] = [cov, rip]

    def current_pareto_training(self):
        """Historical rows + this run's measured rows; the reference stays frozen."""
        base = self.pareto_training
        if base is None:
            return None
        if not self._pareto_rows:
            return base
        from hornlab_search.bo.pareto import ParetoTraining
        ids = list(base.ids)
        geo = list(base.geometry_ids)
        X = [np.asarray(base.X, dtype=float)]
        errors = [np.asarray(base.errors, dtype=float)]
        J = [np.asarray(base.J, dtype=float).reshape(-1)]
        for oid, (x, cov, rip, j, g) in self._pareto_rows.items():
            if oid in ids or g in geo:
                continue
            ids.append(oid)
            geo.append(g)
            X.append(x.reshape(1, -1))
            errors.append(np.asarray([[cov, rip]]))
            J.append(np.asarray([j]))
        return ParetoTraining(X=np.vstack(X), errors=np.vstack(errors), J=np.concatenate(J),
                              ids=tuple(ids), geometry_ids=tuple(geo),
                              reference=dict(base.reference),
                              metric_spec_hash=base.metric_spec_hash)

    def _refit(self):
        from hornlab_search.bo.data import build_training_set
        if self.policy == "pareto" and self._pareto_rows and not callable(self.fit_fn):
            from hornlab_search.bo.pareto import fit_pareto_training
            fitted = fit_pareto_training(self.current_pareto_training(), seed=self.seed)
            self._last_pareto_fit = fitted
            reason = str(getattr(fitted, "reason", "") or "")
            if getattr(fitted, "status", None) != "ok" and any(
                    reason.startswith(r) for r in _NUMERICAL_MODEL_FAILURES):
                return False
        if not self.observations:
            return True
        d = getattr(self.encoding, "d", None)
        if d is None:
            d = getattr(self.training_set, "d", None)
        if d is None:
            first = next(iter(self.observations.values()))
            d = int(np.asarray(first.x).reshape(-1).size)
        training = build_training_set(
            [*self._initial_observations.values(), *self.observations.values()],
            encoding=self.encoding, d=d, seed=self.seed,
            n_max=getattr(self._initial_training, "n_max", 256))
        training = replace(training, meta={
            **getattr(self._initial_training, "meta", {}), **training.meta,
            "adaptive_historical_ids": list(self._initial_observations),
            "adaptive_observation_ids": list(self.observations),
        })
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
            if (geometry and result.get("outcome") in ("success", "cached")
                    and _finite(result.get("observed_j")) is not None):
                self._verified_geometry_ids.add(str(geometry))
            return True
        self._turbo_observe(result)
        if any(r.get("physical_id") == result.get("physical_id")
               for r in self._measured if result.get("physical_id")):
            return True
        if self._add_observation(result):
            self._pareto_observe(result)
            self._measured.append(result)
            return self._refit()
        if result.get("eligible") is True and result.get("outcome") == "success":
            self._measured.append(result)
        return True

    # ------------------------------------------------------------------ resume

    def restore_progress(self, progress):
        if not isinstance(progress, dict):
            raise ContractError("journal progress must be an object")
        stored = progress.get("rng_state")
        extra = stored.get("rng_state") if isinstance(stored, dict) else None
        sequence = extra.get("proposal_sequence") if isinstance(extra, dict) else None
        if sequence is not None:
            if (type(sequence) is not int or sequence < 0
                    or (progress.get("proposal_index") is not None
                        and sequence != progress["proposal_index"])):
                raise ContractError("persisted candidate sequence disagrees with the journal")
            self._proposal_sequence = sequence
            self.history = decode_proposal_history(stored)
        else:
            # Older checkpoints used one shared screen/journal index.
            self.history = decode_proposal_history(stored, progress.get("proposal_index"))
            self._proposal_sequence = self.history.proposal_index
        self.history = replace(self.history, excluded_geometry_hashes=tuple(dict.fromkeys(
            (*self.history.excluded_geometry_hashes, *self._family_history_hashes))))
        if isinstance(stored, dict):
            extra = stored.get("rng_state")
            if isinstance(extra, dict):
                self.screen_index = int(extra.get("screen_index", self.screen_index))
                self._verified_geometry_ids = set(
                    str(x) for x in (extra.get("verified_geometry_ids") or ()))
                if extra.get("screens_exhausted"):
                    self._screens_exhausted = True
                if self.policy == "turbo" and extra.get("turbo_state") is not None:
                    from hornlab_search.bo.turbo import TurboState
                    self.turbo_state = TurboState.from_dict(extra["turbo_state"])
        self._pareto_rows = {}
        self.pareto_excluded = {}
        self.observations = {}
        self.training_set = self._initial_training
        self._vectors = {}
        self._issued = set()
        self._plan = None
        self._measured = []
        for item in progress.get("observations") or ():
            result = item.get("result") or {}
            candidate = item.get("candidate") or {}
            if isinstance(candidate, dict) and candidate.get("solve_id") and result.get("x") is None:
                result = {**result, "x": candidate.get("x"), "params": candidate.get("params")}
            # Old journals recorded the design hash in results, but retain the
            # validated proposal and its complete-surface identity separately.
            family_hash = _family_geometry_hash(candidate) if isinstance(candidate, dict) else None
            if family_hash:
                result = {**result, "params": candidate.get("params"), "geometry_hash": family_hash}
            if result.get("kind") in ("verify", "audit"):
                self.observe(result)
                continue
            # Already-applied solve IDs are skipped, so replay after a staged state is exact.
            self._turbo_observe(result)
            if self._add_observation(result):
                self._pareto_observe(result)
                self._measured.append(result)
        return self._refit()

    def proposal_rng_state(self):
        extra = {
            "audit_seed": self.audit_seed,
            "policy": self.policy,
            "screen_index": self.screen_index,
            "proposal_sequence": self._proposal_sequence,
            "screens_exhausted": self._screens_exhausted,
            "verified_geometry_ids": sorted(self._verified_geometry_ids),
            "verification_selection": self.selection,
        }
        if self.policy == "turbo" and self.turbo_state is not None:
            extra["turbo_state"] = self.turbo_state.to_dict()
        if self.policy == "pareto":
            extra["pareto_excluded"] = dict(sorted(self.pareto_excluded.items()))
        return encode_proposal_history(self.history, extra)


class MetricPipelineStudyEvaluator(PipelineStudyEvaluator):
    """Production metric-composite evaluator: strict binding, four-screen refit, durable replay.

    The evaluation itself is still injected (``measure_fn`` for a fake canary dispatch, the real
    pipeline adapter's ``evaluate`` in production).  What this class owns is the *learning* half:
    it accepts only canonical fresh screens, publishes an immutable training snapshot and moves the
    refit pointer after every four newly accepted unique screens, and restores that exact state
    from the journal without repeating a backend call.
    """

    adapter_contract = "b5-metric-pipeline-evaluator-v1"

    def __init__(self, service, package, *, metric_artifact, metric_manifest, metric_ledger,
                 metric_brief=None, initial_proposal=None, measure_fn=None, **kwargs):
        from hornlab_search.bo.policy import POLICY_METRIC_COMPOSITE

        metric_mode = kwargs.get("policy") == POLICY_METRIC_COMPOSITE
        if metric_mode and (metric_artifact is None or metric_manifest is None
                            or metric_ledger is None):
            raise ContractError("metric training artifact, manifest and refit ledger are required")
        super().__init__(service, package, **kwargs)
        self._metric_base_artifact = metric_artifact
        self._metric_manifest = dict(metric_manifest or {})
        self._metric_ledger = metric_ledger
        self._metric_brief = metric_brief
        self.initial_proposal = initial_proposal
        self.measure_fn = measure_fn
        self._metric_artifact = (metric_ledger.current_artifact if metric_ledger is not None
                                 else metric_artifact)
        self._metric_seen = set(str(v) for v in (
            getattr(metric_artifact, "observation_ids", None) or ()))
        self._metric_accepted = []
        self._metric_attempt_ids = []
        self._metric_items = {}
        self._metric_excluded = {}
        self._metric_refit_log = []
        self._metric_error = None

    # -- binding / proposal --------------------------------------------------
    def metric_binding(self):
        from hornlab_search.bo.policy import MetricTrainingBinding

        manifest = self._metric_manifest
        return MetricTrainingBinding(
            artifact=self._metric_artifact,
            encoding=self.encoding,
            expected_bounds_hash=str((manifest.get("bounds") or {}).get("hash") or ""),
            expected_score=dict((manifest.get("score") or {}).get("payload") or {}),
            expected_task={k: (manifest.get("task") or {}).get(k) for k in
                           ("task_identity", "backend", "fidelity", "grid_hash",
                            "dependency_hash", "mesh_hash")},
            component_schema=str(manifest.get("component_schema_hash") or ""),
        )

    def _propose_through_policy(self):
        from hornlab_search.bo import policy as policy_mod
        from hornlab_search.bo.policy import POLICY_METRIC_COMPOSITE

        if self.policy != POLICY_METRIC_COMPOSITE:
            return super()._propose_through_policy()
        if self.history.proposal_index == 0 and self.initial_proposal is not None:
            return dict(self.initial_proposal)
        outcome = policy_mod.fit_and_propose(
            self.policy, metric_training=self.metric_binding(), pool=self.pool,
            seed=self.seed, encoding=self.encoding, config=self.config,
            resolution_mm=self.resolution_mm, metric_history=self.history)
        self.last_outcome = outcome
        if getattr(outcome, "status", None) != "ok" or outcome.proposal is None:
            return None
        if not isinstance(outcome.proposal, dict):
            return outcome.proposal
        proposal = dict(outcome.proposal)
        proposal["predicted"] = outcome.predicted
        proposal["selection_reason"] = outcome.selection_reason
        proposal["acquisition"] = outcome.acquisition
        return proposal

    # -- evaluation ----------------------------------------------------------
    def evaluate(self, candidate, attempt_id):
        if callable(self.measure_fn):
            result = self.measure_fn(candidate, attempt_id)
            if not isinstance(result, dict):
                raise ContractError("metric measure_fn must return a result dict")
            return dict(result)
        return super().evaluate(candidate, attempt_id)

    # -- learning ------------------------------------------------------------
    def _add_observation(self, result):
        from hornlab_search.bo.policy import POLICY_METRIC_COMPOSITE
        from .metric_refit import MetricRefitError, metric_candidate_from_result

        if self.policy != POLICY_METRIC_COMPOSITE:
            return super()._add_observation(result)
        try:
            candidate = metric_candidate_from_result(
                result, artifact=self._metric_artifact, seen_ids=self._metric_seen)
        except MetricRefitError as exc:
            self._metric_excluded[str(result.get("solve_id") or "")] = str(exc)
            return False
        self._metric_seen.add(candidate.observation_id)
        self._metric_accepted.append(candidate)
        attempt_id = result.get("attempt_id")
        self._metric_attempt_ids.append(None if attempt_id is None else str(attempt_id))
        self._metric_items[candidate.observation_id] = candidate
        return True

    def _refit(self):
        from hornlab_search.bo.policy import POLICY_METRIC_COMPOSITE
        from .metric_refit import MetricRefitError

        if self.policy != POLICY_METRIC_COMPOSITE:
            return super()._refit()
        try:
            record = self._metric_ledger.refit(
                self._metric_accepted, self._metric_attempt_ids, self.proposal_rng_state())
        except MetricRefitError as exc:
            self._metric_error = str(exc)
            return False
        if record is not None:
            self._metric_artifact = self._metric_ledger.current_artifact
            self._metric_refit_log.append(record)
        return True

    # -- resume --------------------------------------------------------------
    def restore_progress(self, progress):
        from hornlab_search.bo.policy import POLICY_METRIC_COMPOSITE

        if self.policy != POLICY_METRIC_COMPOSITE:
            return super().restore_progress(progress)
        self._metric_accepted = []
        self._metric_attempt_ids = []
        self._metric_items = {}
        self._metric_excluded = {}
        self._metric_seen = set(str(v) for v in (self._metric_base_artifact.observation_ids or ()))
        self._metric_error = None
        if not super().restore_progress(progress):
            return False
        # Re-derive the current artifact from the durable pointer after the journal replay; an
        # ambiguous pointer (generation ahead of, or a different prefix than, the replay) refuses.
        self._metric_artifact = self._metric_ledger.current_artifact
        return True

    def proposal_rng_state(self):
        from hornlab_search.bo.policy import POLICY_METRIC_COMPOSITE

        encoded = super().proposal_rng_state()
        if self.policy == POLICY_METRIC_COMPOSITE:
            extra = encoded.get("rng_state") if isinstance(encoded, dict) else None
            if isinstance(extra, dict):
                extra["metric"] = {
                    "refit_generation": int(self._metric_ledger.generation),
                    "artifact_bytes_sha256": (
                        self._metric_ledger.pointer or {}).get("artifact_bytes_sha256"),
                    "accepted_ids": [c.observation_id for c in self._metric_accepted],
                }
        return encoded


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
