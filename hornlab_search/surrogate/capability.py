"""Scoring-capability declaration for the legacy metric surrogate.

The surrogate predicts metric curves and scores them with the v1
``objective.scalar`` path. It cannot produce v4 tolerances / target terms / gates
and it has no throat impedance, so it must refuse -- explicitly -- any objective
version it cannot actually score. Nothing here fabricates metrics.

Pure module: no torch, no solver, no config or default changes.
"""
from __future__ import annotations

#: Objective versions whose scoring math this surrogate actually implements.
SUPPORTED_OBJECTIVE_VERSIONS = (1,)

REASON_UNSUPPORTED_OBJECTIVE_VERSION = "unsupported_objective_version"
REASON_MISSING_THROAT_IMPEDANCE = "missing_throat_impedance"
REASON_MISSING_COMPLETE_METRIC_INPUTS = "missing_complete_metric_inputs"

#: Versions whose real scorers need throat impedance the surrogate cannot predict.
#: Version 2/3 are still refused as unsupported, but they are not throat-load terms.
_VERSIONS_NEEDING_THROAT_IMPEDANCE = (4, 5, 6, 7, 8)

#: The MetricSet inputs ``objective.scalar`` (v1) needs to score a row.
REQUIRED_METRIC_INPUTS = (
    "freqs_hz", "bw_h_deg", "bw_v_deg", "di_db",
    "ripple_h_db", "ripple_v_db", "on_axis_db",
)

#: The MetricSet field that carries measured throat impedance.
THROAT_IMPEDANCE_INPUT = "z_throat_real"


class UnsupportedObjectiveError(ValueError):
    """The requested objective version/input set cannot be scored by this surrogate."""

    def __init__(self, reason_code: str, message: str, *,
                 objective_version: int | None = None,
                 reason_codes: tuple[str, ...] | None = None):
        super().__init__(message)
        self.reason_code = str(reason_code)
        self.reason_codes = tuple(reason_codes or (self.reason_code,))
        self.objective_version = objective_version


def _as_version(objective_version):
    """``None``/unknown stays ``None`` -- never silently coerced to v1."""
    if objective_version is None or isinstance(objective_version, bool):
        return None
    try:
        return int(objective_version)
    except (TypeError, ValueError):
        return None


def _present_inputs(metric_inputs) -> set[str] | None:
    """Names of the supplied metric inputs, or ``None`` when the input set is unknown.

    Accepts a mapping (keys are names) or a sequence of names. ``None`` means "not
    supplied", which is deliberately *unknown*, not "complete".
    """
    if metric_inputs is None:
        return None
    if isinstance(metric_inputs, type):
        return set()
    if isinstance(metric_inputs, dict):
        return {str(k) for k, v in metric_inputs.items() if v is not None}
    if hasattr(metric_inputs, "__dict__"):
        return {str(k) for k, v in vars(metric_inputs).items() if v is not None}
    try:
        names = iter(metric_inputs)
    except TypeError:
        return set()
    return {str(k) for k in names}


def capability_status(objective_version, *, metric_inputs=None) -> dict:
    """Declare whether this surrogate can score ``objective_version`` with ``metric_inputs``.

    Returns a deterministic dict: ``supported``/``unsupported`` status, the version, and
    the applicable reason codes. ``None`` and unknown versions are unsupported.
    """
    v = _as_version(objective_version)
    reasons: list[str] = []
    details: list[str] = []

    present = _present_inputs(metric_inputs)

    if v not in SUPPORTED_OBJECTIVE_VERSIONS:
        reasons.append(REASON_UNSUPPORTED_OBJECTIVE_VERSION)
        shown = "unknown" if objective_version is None else repr(objective_version)
        details.append(
            f"objective version {shown} is not supported by the legacy surrogate "
            f"(supported: {list(SUPPORTED_OBJECTIVE_VERSIONS)})")
        if v is not None and v in _VERSIONS_NEEDING_THROAT_IMPEDANCE:
            # No supplied metric set, or a supplied one without measured impedance: the
            # surrogate predicts curves only and must not invent z_throat_real.
            if present is None or THROAT_IMPEDANCE_INPUT not in present:
                reasons.append(REASON_MISSING_THROAT_IMPEDANCE)
                details.append(
                    "the surrogate predicts metric curves only; it cannot supply measured "
                    "z_throat_real for loading/throat terms")
    elif present is not None:
        missing = [k for k in REQUIRED_METRIC_INPUTS if k not in present]
        if missing:
            reasons.append(REASON_MISSING_COMPLETE_METRIC_INPUTS)
            details.append(f"missing metric inputs: {missing}")

    return {
        "objective_version": v if v is not None else None,
        "status": "supported" if not reasons else "unsupported",
        "supported": not reasons,
        "reason_codes": reasons,
        "reasons": details,
        "supported_versions": list(SUPPORTED_OBJECTIVE_VERSIONS),
        "scorer": "objective.scalar" if v in SUPPORTED_OBJECTIVE_VERSIONS else None,
        "throat_impedance_available": False,
    }


def require_supported(objective_version, *, context: str = "surrogate") -> dict:
    """Return the capability status or raise :class:`UnsupportedObjectiveError`.

    ``None``/unknown is refused; it is never assumed to be v1.
    """
    status = capability_status(objective_version)
    if status["supported"]:
        return status
    codes = tuple(status["reason_codes"])
    detail = "; ".join(status["reasons"]) or "unsupported objective capability"
    raise UnsupportedObjectiveError(
        codes[0],
        f"{context} refuses objective version "
        f"{'unknown' if objective_version is None else objective_version!r}: {detail}",
        objective_version=status["objective_version"],
        reason_codes=codes,
    )
