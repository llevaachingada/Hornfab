"""Evidence-gated B2-to-B3 advisory fit, with no dataset or solver access.

Input is the joined, policy-evidenced row format of ``cohort.validate_cohort``;
do not pass a preconstructed TrainingSet or a fabricated CohortResult. Policy
evidence remains caller-attested, not independently validated source files.
"""
from __future__ import annotations

from dataclasses import dataclass

from .cohort import validate_cohort
from .data import DataError, TrainingSet, build_training_set
from .model import MODEL_POLICY, ModelFitResult, fit_model


@dataclass(frozen=True)
class PipelineResult:
    status: str
    reasons: tuple[str, ...]
    policy_identity: tuple = ()
    training: TrainingSet | None = None
    model: ModelFitResult | None = None


def fit_validated_cohort(rows, *, d: int, encoding=None, seed: int = 0,
                         _fit=fit_model) -> PipelineResult:
    """Validate every row, select the frozen subset, and fit only that subset.

    ``_fit`` is a trusted test seam with the same signature as ``fit_model``.
    No custom subset, model policy or numerical noise is accepted here. Selected
    and excluded IDs are exposed on ``training``. Actual source evidence and
    encoded-vector provenance must be verified by the caller before supplying
    the joined rows; no result from this function alone establishes M2 readiness.
    """
    if encoding is not None and getattr(encoding, 'd', None) != d:
        return PipelineResult('capability_missing', ('encoding dimension mismatch',))
    if not callable(_fit):
        return PipelineResult('capability_missing', ('model fitter unavailable',))
    cohort = validate_cohort(rows, d=d)
    if not cohort.ok:
        return PipelineResult(cohort.status, cohort.reasons)
    try:
        training = build_training_set(cohort.observations, encoding=encoding, d=d)
    except (DataError, TypeError, ValueError) as exc:
        return PipelineResult('capability_missing', (str(exc),), cohort.policy_identity)
    if training.status != 'ok':
        return PipelineResult(training.status, ('insufficient eligible unique geometries',),
                              cohort.policy_identity, training)
    result = _fit(training, model_policy=MODEL_POLICY, seed=seed)
    if getattr(result, 'status', None) != 'ok':
        reason = getattr(result, 'reason', None) or 'model_unavailable'
        return PipelineResult('unavailable', (str(reason),), cohort.policy_identity, training, result)
    return PipelineResult('ok', (), cohort.policy_identity, training, result)
