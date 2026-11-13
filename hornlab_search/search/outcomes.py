"""Pure typed outcome classification for CMA, QD and study adapters.

One classification adapter, no optimizer policy here.  The categories are the frozen
bo-study-v1.1 / hardening section 8 set:

* ``complete_score``       -- error-free evaluation of a complete canonical score;
* ``measured_gate``        -- error-free score whose terms record a measured acoustic gate
                              (``gate_failed`` plus the explicit ``gate_measured`` flag); a
                              gate penalty without that flag is a missing/unmeasurable input and
                              is classified as ``metric_error``, never admitted;
* ``geometry_refusal``     -- deterministic invalid geometry (``invalid_geometry``);
* ``envelope_refusal``     -- deterministic brief-envelope refusal (``invalid_envelope``);
* ``resource_refusal``     -- deterministic mesh/dof resource refusal (``mesh_too_large``);
* ``transient``            -- transient solve/worker infrastructure failure (``solve_failed``);
* ``metric_error``         -- metric/pipeline failure (``metrics_failed``);
* ``unknown_error``        -- unclassified exception or empty/unknown failure kind.

Nothing here inspects ``J``: a legitimate large objective is never re-labelled a failure.
Optimizers decide by :attr:`Outcome.strict_tell_eligible`, never by ``J >= 1000``.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..types import Evaluation

CATEGORY_COMPLETE = "complete_score"
CATEGORY_MEASURED_GATE = "measured_gate"
CATEGORY_GEOMETRY = "geometry_refusal"
CATEGORY_ENVELOPE = "envelope_refusal"
CATEGORY_RESOURCE = "resource_refusal"
CATEGORY_TRANSIENT = "transient"
CATEGORY_METRIC = "metric_error"
CATEGORY_UNKNOWN = "unknown_error"

CATEGORIES = (CATEGORY_COMPLETE, CATEGORY_MEASURED_GATE, CATEGORY_GEOMETRY,
              CATEGORY_ENVELOPE, CATEGORY_RESOURCE, CATEGORY_TRANSIENT, CATEGORY_METRIC,
              CATEGORY_UNKNOWN)

#: Deterministic refusals: the design/resource is refused, not the machine.
DETERMINISTIC_CATEGORIES = (CATEGORY_GEOMETRY, CATEGORY_ENVELOPE, CATEGORY_RESOURCE)

#: Infrastructure categories eligible for same-candidate retry then resumable stop.
INFRASTRUCTURE_CATEGORIES = (CATEGORY_TRANSIENT, CATEGORY_METRIC, CATEGORY_UNKNOWN)


def _kind(error: str) -> str:
    """The evaluator kind token (``invalid_geometry: ...`` -> ``invalid_geometry``)."""
    return (str(error or "").split(":", 1)[0] or "").strip()


@dataclass(frozen=True)
class Outcome:
    """Typed classification of one :class:`~hornlab_search.types.Evaluation`."""

    category: str
    kind: str
    error: str
    complete: bool
    measured_gate: bool
    deterministic_refusal: bool
    infrastructure: bool
    retry_same_candidate: bool

    @property
    def strict_tell_eligible(self) -> bool:
        """May a strict optimizer ``tell`` this outcome?

        Only an error-free complete score is eligible.  A fully measured acoustic gate
        penalty is a real declared constraint value, so it is eligible too; a missing
        input or fabricated infrastructure penalty is not.
        """
        return self.complete

    @property
    def budget_counts_valid(self) -> bool:
        return self.complete


def classify(ev: Evaluation) -> Outcome:
    """Classify one evaluation.  Pure; never raises on a malformed error string."""
    if not isinstance(ev, Evaluation):
        raise TypeError("Evaluation required")
    error = str(ev.error or "")
    if not error:
        terms = ev.terms if isinstance(ev.terms, dict) else {}
        gate_failed = bool(terms.get("gate_failed"))
        # A hard-gate penalty is tell-eligible ONLY when the scorer explicitly records that the
        # gate input was measured (``gate_measured``).  An error-free 1e3 gate penalty with a
        # missing/unmeasurable input (e.g. no z_throat_real, an empty loaded window, an
        # unresolved throat) must not be admitted as a measured acoustic observation.  v8 is
        # unregistered and does not yet emit ``gate_measured``, so its gate penalties stay
        # conservatively ineligible until that scorer is integrated with the flag.
        gate_measured = bool(gate_failed and terms.get("gate_measured") in (True, 1.0))
        if gate_measured:
            return Outcome(
                category=CATEGORY_MEASURED_GATE, kind="measured_gate", error="",
                complete=True, measured_gate=True, deterministic_refusal=False,
                infrastructure=False, retry_same_candidate=False,
            )
        if gate_failed:
            return Outcome(
                category=CATEGORY_METRIC, kind="gate_unmeasured",
                error="gate_unmeasured: gate input was not measured",
                complete=False, measured_gate=False, deterministic_refusal=False,
                infrastructure=True, retry_same_candidate=False,
            )
        return Outcome(
            category=CATEGORY_COMPLETE, kind="", error="",
            complete=True, measured_gate=False, deterministic_refusal=False,
            infrastructure=False, retry_same_candidate=False,
        )
    kind = _kind(error)
    if kind == "invalid_geometry":
        category = CATEGORY_GEOMETRY
    elif kind == "invalid_envelope":
        category = CATEGORY_ENVELOPE
    elif kind == "mesh_too_large":
        category = CATEGORY_RESOURCE
    elif kind == "solve_failed":
        category = CATEGORY_TRANSIENT
    elif kind == "metrics_failed":
        category = CATEGORY_METRIC
    else:
        category = CATEGORY_UNKNOWN
    deterministic = category in DETERMINISTIC_CATEGORIES
    return Outcome(
        category=category,
        kind=kind or "unknown",
        error=error,
        complete=False,
        measured_gate=False,
        deterministic_refusal=deterministic,
        infrastructure=category in INFRASTRUCTURE_CATEGORIES,
        retry_same_candidate=category == CATEGORY_TRANSIENT,
    )


def strict_tell_eligible(ev: Evaluation) -> bool:
    """Convenience predicate used by strict CMA/QD tell boundaries."""
    return classify(ev).strict_tell_eligible


__all__ = [
    "CATEGORIES", "CATEGORY_COMPLETE", "CATEGORY_MEASURED_GATE", "CATEGORY_GEOMETRY",
    "CATEGORY_ENVELOPE", "CATEGORY_RESOURCE", "CATEGORY_TRANSIENT", "CATEGORY_METRIC",
    "CATEGORY_UNKNOWN", "DETERMINISTIC_CATEGORIES", "INFRASTRUCTURE_CATEGORIES",
    "Outcome", "classify", "strict_tell_eligible",
]
