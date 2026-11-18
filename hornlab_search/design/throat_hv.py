"""Shared near-throat H/V block (owner-approved 2026-11-18).

Three knobs with ONE meaning in every family that adopts them. Each family maps them onto its own
published law. This is shared vocabulary, not a universal generator. Research basis:
``docs/knowledge/claims/KH-002_*``, ``KH-003_*`` and ``docs/knowledge/THROAT_HV_CONTROL_AUDIT_2026-11-18.md``.

``throat_hv_ratio`` (rho, 1 = neutral)
    H/V asymmetry of the throat expansion. rho > 1 opens the horizontal plane sooner than the
    vertical one. The per-azimuth scale is ``rho ** (+-cos(2p)/2)``: it equals ``rho**(1/2)`` on the
    H axis (p = 0) and ``rho**(-1/2)`` on the V axis (p = 90 deg). The geometric mean is preserved,
    the mirror planes are kept, and rho = 1 is exactly 1 at every azimuth. Families use
    :func:`hv_scale` (larger = faster throat growth) or :func:`hv_scale_inverse` (for a parameter
    where larger = slower growth, e.g. OS ``k``).

``hv_onset_frac`` (s_on) and ``section_exp_ramp`` (gamma)
    Where the H/V or section-shape departure starts (0 = at the throat) and its ramp exponent, via
    the ATH morph factor ``w(t) = clamp((t - s_on) / (1 - s_on), 0, 1) ** gamma`` (Ath user guide,
    cross-section morphing). ``t`` is the family's own axial or arc fraction.

Neutrality contract: absent keys = today's geometry byte-for-byte; rho = 1 = the parent law.
"""

from __future__ import annotations

import math

import numpy as np

KEYS = ("throat_hv_ratio", "hv_onset_frac", "section_exp_ramp")
RATIO_RANGE = (0.25, 4.0)
ONSET_RANGE = (0.0, 0.9)
RAMP_RANGE = (0.5, 8.0)
ATH_DEFAULT_RAMP = 3.0

#: Provenance label per family mapping (verdicts from KH-003 plus the primary OS-SE check).
STATUS = {
    "OSSE": ("throat_hv_ratio -> per-azimuth k(p): WITHIN the OS-SE parent (Batik 2020 s5: profile "
             "parameters may vary around the device); k keeps the driver-exit slope tan(a0). "
             "hv_onset_frac/section_exp_ramp -> morph_fixed/morph_rate: the published Ath morph."),
    "osse_rollback": ("throat_hv_ratio -> per-azimuth k: within OS-SE for the wall; the superformula "
                      "window remap is a LABELED HYBRID (HornFab construction)."),
    "lecleach_hv": ("throat_hv_ratio -> per-plane march flare T: each plane is still a JMLC march; "
                    "the H/V pairing and onset ramp are a LABELED HYBRID."),
    "iwata_ar": ("hv_onset_frac / section_exp_ramp -> onset and exponent of the AR law "
                 "AR(l) = 1 + (AR_m - 1) w(l): LABELED HYBRID on the iwata_ar reconstruction "
                 "(no published onset term); throat_hv_ratio is not mapped."),
    "rolled": ("all three knobs: LABELED HYBRID (rolled family is an original HornFab "
               "construction; no published parent for near-throat H/V terms). throat_hv_ratio -> "
               "radial scale rho**(cos(2psi)/2 * w) inside the relief window w (zero at the "
               "source match and the mouth attachment)."),
}


class ThroatHVError(ValueError):
    """Illegal shared-block value."""


def parse(params: dict, prefix: str = "") -> dict:
    """Validated block values; absent keys are ``None`` (meaning: keep the family's own default)."""
    out: dict = {}
    for key, (lo, hi) in zip(KEYS, (RATIO_RANGE, ONSET_RANGE, RAMP_RANGE)):
        raw = params.get(prefix + key)
        if raw is None:
            out[key] = None
            continue
        v = float(raw)
        if not math.isfinite(v) or not lo <= v <= hi:
            raise ThroatHVError(f"{prefix}{key} must be in [{lo:g}, {hi:g}], got {raw!r}")
        out[key] = v
    return out


def is_active(block: dict) -> bool:
    """True when the block can change geometry (a non-neutral ratio or any onset/ramp value)."""
    rho = block.get("throat_hv_ratio")
    return (rho is not None and rho != 1.0) or block.get("hv_onset_frac") is not None \
        or block.get("section_exp_ramp") is not None


def hv_scale(rho: float | None, phi):
    """``rho ** (cos(2 phi) / 2)``: sqrt(rho) on H, 1/sqrt(rho) on V, exactly 1 when rho is 1/None."""
    if rho is None or rho == 1.0:
        return np.ones_like(np.asarray(phi, dtype=float)) if np.ndim(phi) else 1.0
    val = float(rho) ** (0.5 * np.cos(2.0 * np.asarray(phi, dtype=float)))
    return val if np.ndim(phi) else float(val)


def hv_scale_inverse(rho: float | None, phi):
    """Reciprocal of :func:`hv_scale` (for a parameter where larger = slower throat growth)."""
    s = hv_scale(rho, phi)
    return 1.0 / s


def ath_ramp(t, onset: float | None, gamma: float | None):
    """Ath morph factor ``clamp((t - s_on)/(1 - s_on), 0, 1) ** gamma`` (s_on 0, gamma 3 default)."""
    s_on = 0.0 if onset is None else float(onset)
    g = ATH_DEFAULT_RAMP if gamma is None else float(gamma)
    x = np.clip((np.asarray(t, dtype=float) - s_on) / (1.0 - s_on), 0.0, 1.0)
    return x ** g


def mesher_k_expression(k: float, rho: float) -> str:
    """Mesher p-expression for the per-azimuth OS-SE ``k(p) = k * rho ** (-cos(2p)/2)``."""
    return f"{float(k)!r}*{float(rho)!r}**(-0.5*cos(2*p))"
