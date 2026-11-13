"""Offline coverage/ripple Pareto primitives for bo-study-v1.1.

Inputs must already have passed cohort and physical-metric validation. This module
does not turn predictions into observations or perform a solve.
"""
from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
import numpy as np

from .model import fit_model

#: Frozen Pareto engine identity (B7 commit 1).  A study records this name so a different
#: reference/model policy cannot be silently substituted.
PARETO_POLICY = "pareto_pool_v1"


def frozen_reference(errors):
    """Freeze original-unit limits and the maximization-space reference."""
    a = np.asarray(errors, dtype=float)
    if a.ndim != 2 or a.shape[1] != 2 or len(a) == 0 or not np.isfinite(a).all():
        raise ValueError("complete finite coverage/ripple pairs required")
    hi, lo = a.max(axis=0), a.min(axis=0)
    limits = hi + np.maximum(0.1 * (hi - lo), [0.1, 0.01])
    return {"limits": limits.tolist(), "ref_point": (-limits).tolist(),
            "units": ["deg", "dB"], "direction": "minimize"}


def nondominated(errors):
    a = np.asarray(errors, dtype=float)
    if a.ndim != 2 or a.shape[1] != 2 or not np.isfinite(a).all():
        raise ValueError("complete finite coverage/ripple pairs required")
    return np.array([not np.any(np.all(a <= p, axis=1) & np.any(a < p, axis=1))
                     for p in a], dtype=bool)


def select_subset(X, errors, J, geometry_ids, *, cap=256):
    """Select physical frontier/crowding then scalar and unit-box diversity."""
    X, errors, J = np.asarray(X, float), np.asarray(errors, float), np.asarray(J, float).reshape(-1)
    ids = tuple(map(str, geometry_ids))
    n = len(ids)
    if (X.ndim != 2 or X.shape[0] != n or errors.shape != (n, 2) or len(J) != n
            or not np.isfinite(X).all() or np.any((X < 0) | (X > 1))
            or not np.isfinite(errors).all() or not np.isfinite(J).all()
            or len(set(ids)) != n or cap < 1 or cap > 256):
        raise ValueError("invalid or duplicate eligible observations")
    reference = frozen_reference(errors)
    front = np.flatnonzero(nondominated(errors)).tolist()
    crowd = {i: 0.0 for i in front}
    for axis in range(2):
        order = sorted(front, key=lambda i: (errors[i, axis], ids[i]))
        if len(order) <= 2:
            for i in order: crowd[i] = float("inf")
            continue
        crowd[order[0]] = crowd[order[-1]] = float("inf")
        span = reference["limits"][axis] - float(errors[:, axis].min())
        for k in range(1, len(order) - 1):
            crowd[order[k]] += (errors[order[k+1], axis] - errors[order[k-1], axis]) / span
    elite_cap = min(64, cap, n)
    selected = sorted(front, key=lambda i: (-crowd[i], ids[i]))[:elite_cap]
    remaining = [i for i in range(n) if i not in selected]
    selected.extend(sorted(remaining, key=lambda i: (J[i], ids[i]))[:elite_cap-len(selected)])
    remaining = [i for i in range(n) if i not in selected]
    while remaining and len(selected) < min(cap, n):
        if selected:
            dist = {i: float(np.min(np.linalg.norm(X[selected] - X[i], axis=1))) for i in remaining}
            pick = min(remaining, key=lambda i: (-dist[i], ids[i]))
        else:
            pick = min(remaining, key=lambda i: ids[i])
        selected.append(pick)
        remaining.remove(pick)
    return {"indices": selected, "ids": [ids[i] for i in selected],
            "excluded_ids": [ids[i] for i in remaining], "reference": reference,
            "front_ids": [ids[i] for i in front]}


@dataclass(frozen=True)
class ParetoFit:
    status: str
    reason: str
    model: object = None
    train_X: object = None
    reference: object = None
    outputs: tuple = ()
    note: str = "Independent coverage/ripple GPs; cross-output correlation is not modeled."


def fit_constrained_pareto(base, margin_observations, *, ids, seed=0):
    """Add measured signed loading margins; no Boolean or missing values are modeled."""
    from types import SimpleNamespace
    if base.status != "ok": return ParetoFit("unavailable", "constraint_model_unavailable")
    X = base.train_X
    ids = tuple(map(str, ids))
    if (not isinstance(margin_observations, dict) or set(margin_observations) != set(ids)
            or len(ids) != len(set(ids)) or tuple(base.outputs[0].train_ids) != ids):
        return ParetoFit("unavailable", "constraint_model_unavailable")
    rows = [margin_observations[i] for i in ids]
    if any(not isinstance(r, dict) or r.get("status") != "ok" or
           r.get("names") != ["g_lfp", "g_hold", "g_window"] for r in rows):
        return ParetoFit("unavailable", "constraint_model_unavailable")
    try:
        g = np.asarray([r["margins"] for r in rows], float)
    except (KeyError, TypeError, ValueError):
        return ParetoFit("unavailable", "constraint_model_unavailable")
    if (g.shape != (len(X), 3) or len(ids) != len(X) or not np.isfinite(g).all()
            or not np.any(np.all(g <= 0, axis=1))):
        return ParetoFit("unavailable", "constraint_model_unavailable")
    fits = list(base.outputs)
    for col in range(3):
        # fit_model models Y=-J, so J=-margin models signed, negative-feasible G.
        j = -g[:, col:col+1]
        data = SimpleNamespace(status="ok", d=X.shape[1], n=len(X), X=X, J=j, Y=-j,
                               ids=tuple(ids), n_min=max(16, 2*(X.shape[1]+1)))
        fit = fit_model(data, seed=seed)
        if fit.status != "ok": return ParetoFit("unavailable", "constraint_model_unavailable")
        fits.append(fit)
    try:
        from botorch.models import ModelListGP
        return ParetoFit("ok", "ok", ModelListGP(*(f.model for f in fits)), X.copy(),
                         dict(base.reference), tuple(fits),
                         "Independent objective and signed-margin GPs; cross-output correlation is not modeled.")
    except ImportError:
        return ParetoFit("unavailable", "capability_missing")


def _fit_pareto_numeric(X, errors, ids, *, reference, seed=0):
    """Fit independent locked models; reference must come from the full snapshot."""
    X, errors = np.asarray(X, float), np.asarray(errors, float)
    ids = tuple(ids)
    if (X.ndim != 2 or errors.shape != (len(X), 2) or len(ids) != len(X)
            or not np.isfinite(errors).all() or not isinstance(reference, dict)):
        return ParetoFit("unavailable", "invalid_inputs")
    try:
        ref = np.asarray(reference["ref_point"], float)
        if ref.shape != (2,) or not np.isfinite(ref).all() or not np.all(-errors > ref):
            raise ValueError("reference must be worse than all training observations")
    except (KeyError, TypeError, ValueError):
        return ParetoFit("unavailable", "invalid_reference")
    outputs = []
    for col in range(2):
        j = errors[:, col:col+1]
        training = SimpleNamespace(status="ok", d=X.shape[1], n=len(X), X=X, J=j,
                                   Y=-j, ids=ids, n_min=max(16, 2*(X.shape[1]+1)))
        result = fit_model(training, seed=seed)
        if result.status != "ok":
            return ParetoFit("unavailable", result.reason, outputs=tuple(outputs + [result]))
        outputs.append(result)
    try:
        from botorch.models import ModelListGP
        model = ModelListGP(*(o.model for o in outputs))
    except Exception as exc:
        return ParetoFit("unavailable", f"capability_missing: {exc}", outputs=tuple(outputs))
    return ParetoFit("ok", "ok", model, X.copy(), dict(reference), tuple(outputs))


def fit_pareto(cohort, metric_observations, *, seed=0, cap=256):
    """Fit only validated, ID-bound canonical complete physical observations.

    ``metric_observations`` maps each cohort observation ID to a MetricObservation.
    The cohort must explicitly identify both the metric policy and frequency masks
    by the same canonical physical metric spec hash. The frozen reference comes from
    all eligible cohort observations before the bounded training subset is selected.
    No individual design's metric or score identity is treated as policy identity.
    """
    from .cohort import CohortResult
    from .metrics import MetricObservation
    import json
    if not isinstance(cohort, CohortResult) or not cohort.ok or not cohort.observations:
        return ParetoFit("unavailable", "validated_cohort_required")
    if not isinstance(metric_observations, dict):
        return ParetoFit("unavailable", "metric_observation_bindings_required")
    claims = {key: (ns, value) for key, ns, value in cohort.policy_identity}
    try:
        metric_ns, metric_json = claims["metric_policy"]
        mask_ns, mask_json = claims["frequency_masks"]
        metric_hash = json.loads(metric_json)
        if (metric_ns != "bo.physical_metric_spec_hash" or mask_ns != metric_ns
                or json.loads(mask_json) != metric_hash or not isinstance(metric_hash, str)
                or len(metric_hash) != 64 or any(c not in "0123456789abcdef" for c in metric_hash)):
            raise ValueError("metric and support identities must name the same physical metric hash")
    except (KeyError, TypeError, ValueError):
        return ParetoFit("unavailable", "metric_policy_identity_missing")
    observations = cohort.observations
    ids = [o.observation_id for o in observations]
    if len(set(ids)) != len(ids) or set(metric_observations) != set(ids):
        return ParetoFit("unavailable", "metric_observation_binding_mismatch")
    values = []
    for oid in ids:
        item = metric_observations[oid]
        if (not isinstance(item, MetricObservation) or item.status != "complete"
                or item.physical_metric_spec_hash != metric_hash):
            return ParetoFit("unavailable", "metric_observation_incomplete_or_incompatible")
        try:
            pair = [float(item.coverage_deg), float(item.ripple_db)]
            if not np.isfinite(pair).all() or min(pair) < 0:
                raise ValueError("invalid physical errors")
        except (TypeError, ValueError):
            return ParetoFit("unavailable", "metric_observation_incomplete_or_incompatible")
        values.append(pair)
    try:
        X = np.vstack([o.x for o in observations])
        J = np.asarray([o.J for o in observations], dtype=float)
        errors = np.asarray(values, dtype=float)
        # Geometry IDs govern crowding/diversity ties. Refuse duplicate geometry
        # rather than silently picking a measurement or inflating its evidence.
        geometry_ids = [o.geometry_hash for o in observations]
        if any(not isinstance(g, str) or not g for g in geometry_ids):
            raise ValueError("geometry identity missing")
        subset = select_subset(X, errors, J, geometry_ids, cap=cap)
        indices = subset["indices"]
        return _fit_pareto_numeric(X[indices], errors[indices], [ids[i] for i in indices],
                                   reference=subset["reference"], seed=seed)
    except (ValueError, TypeError, IndexError) as exc:
        return ParetoFit("unavailable", f"invalid_cohort: {exc}")


def acquisition_scores(fit, candidates, *, seed=0, pending=None):
    """Evaluate locked qLogNEHVI in chunks of 64; values are technical rankings."""
    if fit.status != "ok":
        return {"status": "unavailable", "reason": fit.reason}
    try:
        import torch
        from botorch.acquisition.multi_objective.logei import qLogNoisyExpectedHypervolumeImprovement
        from botorch.acquisition.multi_objective.objective import IdentityMCMultiOutputObjective
        from botorch.sampling.normal import SobolQMCNormalSampler
        x = np.asarray(candidates, dtype=float)
        if x.ndim != 2 or x.shape[1] != fit.train_X.shape[1] or not np.isfinite(x).all():
            raise ValueError("invalid candidate pool")
        p = None if pending is None else torch.as_tensor(np.asarray(pending, float), dtype=torch.float64)
        constraints = ([lambda samples, i=i: samples[..., i] for i in range(2, 5)]
                       if len(fit.outputs) == 5 else None)
        if len(fit.outputs) not in (2, 5): raise ValueError("unexpected model outputs")
        acq = qLogNoisyExpectedHypervolumeImprovement(
            model=fit.model, ref_point=fit.reference["ref_point"],
            X_baseline=torch.as_tensor(fit.train_X, dtype=torch.float64),
            sampler=SobolQMCNormalSampler(torch.Size([128]), seed=int(seed)),
            objective=IdentityMCMultiOutputObjective(outcomes=[0, 1]),
            prune_baseline=False, X_pending=p, constraints=constraints, eta=1e-3)
        with torch.no_grad():
            values = np.concatenate([acq(torch.as_tensor(x[i:i+64], dtype=torch.float64).unsqueeze(-2))
                                     .detach().cpu().numpy().reshape(-1) for i in range(0, len(x), 64)])
        if not np.isfinite(values).all(): raise ValueError("nonfinite acquisition")
        return {"status": "ok", "values": values, "units": "log expected hypervolume improvement"}
    except ImportError as exc:
        return {"status": "unavailable", "reason": f"capability_missing: {exc}"}
    except Exception as exc:
        return {"status": "unavailable", "reason": f"model_unavailable: {type(exc).__name__}: {exc}"}


def propose_pareto(fit, pool, history, *, encoding, config, seed=0, resolution_mm=30.0):
    """Select, re-materialize and validate one candidate; no solve is dispatched."""
    from .propose import (ProposalPolicy, _filter_legal, _maximin_pick,
                          validate_selected_candidate)
    if fit.status != "ok":
        return {"status": "unavailable", "reason": fit.reason}
    if len(history.pending_identities) != len(history.pending_vectors):
        return {"status": "unavailable", "reason": "pending_identity_vector_mismatch"}
    if getattr(pool, "status", None) != "ok":
        return {"status": "unavailable", "reason": "pool_exhausted"}
    policy = ProposalPolicy(acq_seed=int(seed))
    legal, counts = _filter_legal(pool, history, fit, policy)
    if not legal:
        return {"status": "unavailable", "reason": "pool_exhausted", "counts": counts}
    x = np.vstack([v for _, v in legal])
    if policy.is_exploration(history.proposal_index):
        refs = list(np.asarray(fit.train_X, float)) + list(history.pending_vectors) + list(history.excluded_vectors)
        candidate, vector, _ = _maximin_pick(legal, refs)
        selection, value = "maximin_exploration", None
    else:
        scores = acquisition_scores(fit, x, seed=seed,
                                    pending=history.pending_vectors if history.pending_vectors else None)
        if scores["status"] != "ok": return scores
        values = scores["values"]
        best = min(range(len(legal)), key=lambda i: (-values[i], str(legal[i][0].geometry_hash)))
        candidate, vector = legal[best]
        selection, value = "qLogNEHVI", float(values[best])
    try:
        validate_selected_candidate(candidate, pool, encoding=encoding, config=config,
                                    resolution_mm=resolution_mm)
        from .model import predict_j
        predictions = [predict_j(output, vector.reshape(1, -1)) for output in fit.outputs]
        if any(p.status != "ok" for p in predictions): raise ValueError("physical posterior unavailable")
        physical = [{"mean": float(p.j_mean[0]), "lower": float(p.j_lower[0]),
                     "upper": float(p.j_upper[0]), "interval": p.interval_label}
                    for p in predictions]
    except Exception as exc:
        return {"status": "unavailable", "reason": f"validation_or_prediction_failed: {type(exc).__name__}: {exc}",
                "proposal_index": history.proposal_index}
    return {"status": "ok", "candidate": candidate.as_dict(include_vectors=True),
            "proposal_index": history.proposal_index, "next_proposal_index": history.proposal_index + 1,
            "selection_reason": selection, "acquisition_value": value,
            "physical_predictions": {"coverage_deg": physical[0], "ripple_db": physical[1]},
            "reference": dict(fit.reference), "counts": counts,
            "note": "Coverage/ripple trade-off frontier; cheap-check-passed, mesh/acoustic eligibility unknown."}
