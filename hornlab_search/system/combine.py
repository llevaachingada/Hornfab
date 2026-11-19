"""Coherent combination of independent source fields (Stage 1, Lane D).

The combination is deliberately narrow::

    p_total[f, obs] = sum_x  H_x[f, obs] * F_x[f] * L_x

where ``H_x = SystemResponse.p_by_excitation[x]`` is the complex field of source ``x`` in a
single declared observation frame, ``F_x`` is the DSP filter from
:func:`hornlab_search.system.dsp.filter_bank` and ``L_x`` is a **linear** input level.

Phase-once rule (binding)
-------------------------
``combine`` NEVER applies a propagation/spacing phase factor. The input arrays must already be
in one shared observation frame (the import adapter owns the spatial phase); the propagation
phase is therefore applied **at most once**, at the import boundary. Adding
``exp(-j k r)`` here would double-count it and is forbidden. The same rule is why the input
basis metadata must prove a shared frame: :meth:`SourceBasis.compatible_for_sum_with` is the
gate, and the combiner multiplies by DSP only.

Phase honesty
-------------
A magnitude-only response (or one with no ``p_by_excitation``) is refused with
:class:`contracts.PhaseUnavailable` carrying the contract wording
``MAGNITUDE_ONLY / PHASE_ALIGNMENT_UNAVAILABLE``. No phase is imputed and no delay claim is
derived from magnitude data.

Purity
------
Every public function here is pure: no file IO, no global state. That matters for SYS-15:
:func:`recombine_with_dsp` recomputes a total from the same cached basis fields for a new
:class:`contracts.DspPoint`, and :func:`recombine_cache_key` is the cache key.
"""
from __future__ import annotations

import hashlib
from dataclasses import asdict, replace
from itertools import combinations
from typing import Mapping

import numpy as np

from hornlab_search.system import contracts

__all__ = [
    "combine",
    "recombine_with_dsp",
    "recombine_cache_key",
]

#: Contract wording kept byte-exact so callers/tests can match on it.
PHASE_REFUSAL = (
    "coherent combination refused: MAGNITUDE_ONLY / PHASE_ALIGNMENT_UNAVAILABLE — "
    "a magnitude-only SystemResponse carries no complex fields, so phase-sensitive "
    "combination, delay optimisation and crossover claims are refused"
)


def _require_complex(response: contracts.SystemResponse) -> None:
    """Raise :class:`contracts.PhaseUnavailable` rather than imputing phase."""
    if response.p_by_excitation is None:
        raise contracts.PhaseUnavailable(PHASE_REFUSAL)
    if not response.excitation_names:
        raise contracts.PhaseUnavailable(PHASE_REFUSAL)
    quality = str(dict(response.data_quality).get("quality", "")).upper()
    if response.fidelity == "SCREEN_MAGNITUDE" or quality == "MAGNITUDE_ONLY":
        raise contracts.PhaseUnavailable(PHASE_REFUSAL)


def _require_compatible(bases: Mapping[str, contracts.SourceBasis],
                        names: tuple[str, ...]) -> None:
    """All stored fields must be pairwise sum-compatible, else ``IncompatibleBasis``."""
    for a, b in combinations(names, 2):
        try:
            basis_a = bases[a]
            basis_b = bases[b]
        except KeyError as exc:
            raise contracts.IncompatibleBasis(
                f"excitation {exc.args[0]!r} has no SourceBasis; cannot prove a shared frame"
            ) from None
        ok, reason = basis_a.compatible_for_sum_with(basis_b)
        if not ok:
            raise contracts.IncompatibleBasis(
                f"cannot coherently sum {a!r} and {b!r}: {reason}")


def combine(response: contracts.SystemResponse,
            filter_bank: Mapping[str, np.ndarray],
            input_levels: Mapping[str, float]) -> contracts.SystemResponse:
    """Return a new response whose ``p_total`` is the coherent DSP-weighted sum.

    ``filter_bank`` maps each excitation name (``"horn"`` / ``"woofer"``) to a ``(nf,)``,
    ``(nf, 1)`` or ``(nf, nobs)`` complex filter. ``input_levels`` maps each excitation to a
    **linear** multiplicative level (not dB). The input fields are not modified and no spatial
    phase factor is introduced (see the phase-once rule above).

    Refusals:

    * magnitude-only / no ``p_by_excitation`` -> :class:`contracts.PhaseUnavailable`;
    * basis metadata that does not prove a shared frame -> :class:`contracts.IncompatibleBasis`;
    * missing/shape-mismatched fields, filters or levels -> :class:`contracts.DataQualityError`.
    """
    _require_complex(response)
    names = tuple(response.excitation_names)
    p_by_excitation = response.p_by_excitation
    assert p_by_excitation is not None               # guaranteed by _require_complex
    fields: dict[str, np.ndarray] = {n: p_by_excitation[n] for n in names}
    bases = dict(response.excitation_bases)

    missing_fields = [n for n in names if n not in fields]
    if missing_fields:
        raise contracts.DataQualityError(
            f"p_by_excitation missing excitations {missing_fields}")
    _require_compatible(bases, names)

    n_f = int(response.frequencies_hz.shape[0])
    total: np.ndarray | None = None
    for name in names:
        if name not in filter_bank:
            raise contracts.DataQualityError(f"filter_bank has no entry for excitation {name!r}")
        if name not in input_levels:
            raise contracts.DataQualityError(f"input_levels has no entry for excitation {name!r}")

        h = np.asarray(fields[name], dtype=np.complex128)
        if h.ndim != 2:
            raise contracts.DataQualityError(
                f"excitation {name!r} field must be (nf, nobs), got shape {h.shape}")
        if h.shape[0] != n_f:
            raise contracts.DataQualityError(
                f"excitation {name!r} frequency axis {h.shape[0]} != {n_f}")

        f_x = np.asarray(filter_bank[name], dtype=np.complex128)
        if f_x.ndim == 1:
            if f_x.shape[0] != n_f:
                raise contracts.DataQualityError(
                    f"filter {name!r} length {f_x.shape[0]} != {n_f}")
            f_x = f_x[:, None]
        elif f_x.ndim == 2:
            if f_x.shape[0] != n_f or f_x.shape[1] not in (1, h.shape[1]):
                raise contracts.DataQualityError(
                    f"filter {name!r} shape {f_x.shape} is not broadcastable to {h.shape}")
        else:
            raise contracts.DataQualityError(
                f"filter {name!r} must be 1-D or 2-D, got shape {f_x.shape}")

        level = float(input_levels[name])
        if not np.isfinite(level):
            raise contracts.DataQualityError(
                f"input level for {name!r} must be finite, got {level!r}")

        term = h * f_x * level
        total = term if total is None else total + term

    if total is None:
        raise contracts.DataQualityError("combine needs at least one excitation")

    return replace(response, p_total=np.asarray(total, dtype=np.complex128))


def recombine_with_dsp(response_with_bases: contracts.SystemResponse,
                       new_point: contracts.DspPoint,
                       input_levels: Mapping[str, float]) -> contracts.SystemResponse:
    """Pure SYS-15 re-scoring: same basis fields, a new DSP point, a new coherent total.

    Builds the filter bank from :mod:`hornlab_search.system.dsp` (the only filter source) and
    calls :func:`combine`. No file IO and no mutation of ``response_with_bases``.

    This validates no DSP ranges: the caller owns range checks (``dsp.validate_dsp_point``).
    """
    from hornlab_search.system.dsp import filter_bank

    bank = filter_bank(new_point, response_with_bases.frequencies_hz)
    return combine(response_with_bases, bank, input_levels)


def _array_sha(array: np.ndarray) -> dict[str, object]:
    a = np.ascontiguousarray(np.asarray(array))
    return {
        "sha256": hashlib.sha256(a.tobytes()).hexdigest(),
        "shape": list(a.shape),
        "dtype": str(a.dtype),
    }


def recombine_cache_key(point: contracts.DspPoint,
                        input_levels: Mapping[str, float],
                        excitation_fields: Mapping[str, np.ndarray]
                        | contracts.SystemResponse) -> str:
    """SYS-15 cache key: hash of (DSP point, input levels, excitation field array shas).

    The returned 16-hex id is domain-separated by :func:`contracts.domain_sha16`; identical
    point + levels + field bytes give an identical key, and a new DSP point or changed field
    bytes change it. Accepts either a mapping of field arrays or a
    :class:`contracts.SystemResponse` (whose ``p_by_excitation`` is hashed).
    """
    if isinstance(excitation_fields, contracts.SystemResponse):
        if excitation_fields.p_by_excitation is None:
            raise contracts.PhaseUnavailable(PHASE_REFUSAL)
        fields: Mapping[str, np.ndarray] = excitation_fields.p_by_excitation
    else:
        fields = excitation_fields

    payload = {
        "point": asdict(point),
        "input_levels": {str(k): float(v) for k, v in input_levels.items()},
        "fields": {str(k): _array_sha(v) for k, v in sorted(fields.items())},
    }
    return contracts.domain_sha16("system.recombine_cache_v1", payload)
