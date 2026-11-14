"""Dense-memory feasibility preflight (plan A5).

Pure arithmetic: estimates whether a dense N x N solve fits in the memory
budget of the chosen backend. Imports nothing from ``solve/beat.py`` and
nothing that loads Julia. Warning-only in this wave; never a refusal path
by itself.

All calibration constants are module-level and named so that a recalibration
touches one place. The fused-CUDA model was RE-BASED on measured anchors
(2026-11-13 speed program, solver ``38e5b1f``; see
``docs/evidence/SPEED_ADOPTION_2026-11-14.md``): the pre-rebase
``FUSED_CUDA_FACTOR 4.0 x 8N**2`` arithmetic (from
``docs/evidence/FUSED_CUDA_2026-10-24.md``, 20,237-DOF refusal) was
pin-A arithmetic that G2 proved stale — the measured edge on the new solver
is beyond 25k quarter-DOF.
"""

from __future__ import annotations

GIB = 1024**3

# Fused CUDA: measured anchors (quarter DOF, conservative peak MiB), measured 2026-11-13 on the
# RTX 4060 8 GB at solver 38e5b1f. The first two anchors are the seed-design batch-1 arms
# (screen runs 20261114T012458Z/012724Z peaks, batch-1 = one request-at-a-time pool);
# the last four are the E6 ceiling-sweep points (single frequency, fresh process each; the
# 24,973 anchor uses the device-inclusive tool peak). Piecewise-linear between anchors,
# extrapolating the FINAL measured slope beyond the last anchor (that segment measured
# steeper than quadratic, so linear extension is the conservative direction).
FUSED_CUDA_MEASURED_ANCHORS: tuple[tuple[int, int], ...] = (
    (6262, 1256),
    (8007, 1426),
    (15878, 2186),
    (20152, 3402),
    (23850, 4682),
    (24973, 5822),
)

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


def fused_cuda_need_gib(n_dof: int) -> float:
    """Measured-envelope peak-VRAM estimate (GiB) for one fused-CUDA solve request.

    Piecewise-linear through :data:`FUSED_CUDA_MEASURED_ANCHORS`. Below the first
    anchor the chord from the origin is used (for a convex curve it lies above the
    measured curve, i.e. the conservative direction for a refusal model). Beyond the
    last anchor the final segment slope is extrapolated. Monotone increasing.
    """
    n = int(n_dof)
    if n <= 0:
        return 0.0
    anchors = FUSED_CUDA_MEASURED_ANCHORS
    xs = [a[0] for a in anchors]
    ys = [a[1] for a in anchors]
    if n >= xs[-1]:
        slope = (ys[-1] - ys[-2]) / (xs[-1] - xs[-2])
        peak_mib = ys[-1] + slope * (n - xs[-1])
    else:
        peak_mib = ys[0]
        for i in range(1, len(xs)):
            x0, y0 = xs[i - 1], ys[i - 1]
            x1, y1 = xs[i], ys[i]
            if n <= x1:
                if n < x0:
                    peak_mib = y0 * n / x0  # origin chord below the first anchor
                else:
                    peak_mib = y0 + (y1 - y0) * (n - x0) / (x1 - x0)
                break
    return peak_mib / 1024.0


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
            basis, label, mem_name = "calibrated", "fused CUDA", "VRAM"
            need_gib = fused_cuda_need_gib(n_dof)
        else:
            factor = NONFUSED_CUDA_FACTOR
            basis, label, mem_name = "provisional", "non-fused CUDA", "VRAM"
            need_gib = factor * dense_bytes_lower_bound(n_dof) / GIB
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
