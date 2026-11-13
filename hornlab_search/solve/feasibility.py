"""Dense-memory feasibility preflight (plan A5).

Pure arithmetic: estimates whether a dense N x N solve fits in the memory
budget of the chosen backend. Imports nothing from ``solve/beat.py`` and
nothing that loads Julia. Warning-only in this wave; never a refusal path
by itself.

All calibration constants are module-level and named so that a recalibration
(for example after the G2 fork A/B) touches one place.
"""

from __future__ import annotations

GIB = 1024**3

# Fused CUDA: calibrated from docs/evidence/FUSED_CUDA_2026-10-24.md
# (12,183 DOF ~4.7 GB incremental; 15,984 DOF hit the pressure cliff).
FUSED_CUDA_FACTOR = 4.0

# Non-fused CUDA: provisional.
NONFUSED_CUDA_FACTOR = 6.0

# CPU: complex128 (16 bytes) N x N, LU in place plus workspace. Provisional.
CPU_COMPLEX_BYTES = 16
CPU_FACTOR = 3.0

# Fit / risky thresholds as fractions of the budget.
FIT_FRACTION = 0.8
RISKY_FRACTION = 1.0

CUDA_BACKENDS = frozenset({"beat_cuda"})
CPU_BACKENDS = frozenset({"beat_cpu", "bempp_cpu"})


def dense_bytes_lower_bound(n_dof: int, dtype_bytes: int = 8) -> int:
    """Bytes of one dense N x N matrix (default complex64, 8 bytes)."""
    return int(dtype_bytes) * int(n_dof) ** 2


def _verdict(need_gib: float, budget_gib: float) -> str:
    if need_gib <= FIT_FRACTION * budget_gib:
        return "fit"
    if need_gib <= RISKY_FRACTION * budget_gib:
        return "risky"
    return "refuse"


def assess(
    n_dof: int,
    backend: str,
    *,
    cuda_fused: bool = True,
    vram_gib: float = 8.0,
    vram_baseline_gib: float = 1.5,
    ram_gib: float = 32.0,
    ram_reserve_gib: float = 8.0,
) -> dict:
    """Assess dense-memory feasibility for one solve.

    Returns ``{"verdict", "need_gib", "budget_gib", "reason", "basis"}`` where
    verdict is ``"fit"``, ``"risky"`` or ``"refuse"`` and basis is
    ``"calibrated"`` or ``"provisional"``.

    Raises ValueError for a backend this module does not know.
    """
    if backend in CUDA_BACKENDS:
        budget_gib = float(vram_gib) - float(vram_baseline_gib)
        if cuda_fused:
            factor, basis, label = FUSED_CUDA_FACTOR, "calibrated", "fused CUDA"
        else:
            factor, basis, label = NONFUSED_CUDA_FACTOR, "provisional", "non-fused CUDA"
        need_gib = factor * dense_bytes_lower_bound(n_dof) / GIB
        mem_name = "VRAM"
    elif backend in CPU_BACKENDS:
        budget_gib = float(ram_gib) - float(ram_reserve_gib)
        need_gib = CPU_FACTOR * CPU_COMPLEX_BYTES * int(n_dof) ** 2 / GIB
        basis, label, mem_name = "provisional", "CPU", "RAM"
    else:
        raise ValueError(f"unknown backend for feasibility: {backend!r}")

    verdict = _verdict(need_gib, budget_gib)
    reason = (
        f"{label} dense solve at {int(n_dof)} DOF needs ~{need_gib:.2f} GiB "
        f"of {mem_name} against a budget of {budget_gib:.2f} GiB: {verdict}"
    )
    return {
        "verdict": verdict,
        "need_gib": round(need_gib, 4),
        "budget_gib": round(budget_gib, 4),
        "reason": reason,
        "basis": basis,
    }
