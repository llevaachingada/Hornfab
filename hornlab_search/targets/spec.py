"""The Target dataclass. 01_CONTRACTS.md section 11."""
from __future__ import annotations

from dataclasses import dataclass, fields


@dataclass(frozen=True)
class Target:
    coverage_h_deg: float          # TOTAL included angle
    coverage_v_deg: float
    band_lo_hz: float
    band_hi_hz: float
    di_target_db: float | None     # None -> derive from coverage
    di_slope_target: float = 0.0   # flat DI
    z_min: float = 0.0
    freq_weights: dict | None = None
    f0_hz: float | None = None     # 2026-10-25 owner amendment: the K-law pattern-control
                                   # design frequency (d = KEELE_K/(f0*coverage)); absent =
                                   # band_lo and every existing YAML behaves as before.
    f0_v_hz: float | None = None   # 2026-10-26 objective v3 amendment (owner-directed):
                                   # optional PER-PLANE vertical scoring frequency. When set,
                                   # cov scores the horizontal error only at f >= f0_hz and the
                                   # vertical error only at f >= f0_v_hz (f0_v_hz >= f0_hz).
                                   # Absent = the pre-amendment path, bit-identical.

    def f0_effective_hz(self) -> float:
        """The K-law design frequency in force (an explicit f0 wins over band_lo)."""
        return float(self.f0_hz) if self.f0_hz is not None else float(self.band_lo_hz)

    @classmethod
    def from_dict(cls, d: dict) -> "Target":
        """Build from a YAML `target:` block.

        The four coverage/band fields are required and must not be None. `di_target_db`
        may be absent or null (derive from coverage). Unknown keys raise ValueError, so a
        typo in a YAML file is an error and not a silently ignored setting.
        """
        if not isinstance(d, dict):
            raise ValueError(f"Target.from_dict: expected a mapping, got {type(d).__name__}")
        known = {f.name for f in fields(cls)}
        unknown = sorted(set(d) - known)
        if unknown:
            raise ValueError(f"Target.from_dict: unknown key(s) {unknown}")
        required = ("coverage_h_deg", "coverage_v_deg", "band_lo_hz", "band_hi_hz")
        for k in required:
            if k not in d or d[k] is None:
                raise ValueError(f"Target.from_dict: missing required key '{k}'")
        kw: dict = {k: float(d[k]) for k in required}
        kw["di_target_db"] = None if d.get("di_target_db") is None else float(d["di_target_db"])
        if d.get("di_slope_target") is not None:
            kw["di_slope_target"] = float(d["di_slope_target"])
        if d.get("z_min") is not None:
            kw["z_min"] = float(d["z_min"])
        if d.get("freq_weights") is not None:
            kw["freq_weights"] = dict(d["freq_weights"])
            kw["freq_weights"] = validate_freq_weights(kw["freq_weights"])
        if d.get("f0_hz") is not None:
            kw["f0_hz"] = float(d["f0_hz"])
        if d.get("f0_v_hz") is not None:
            kw["f0_v_hz"] = float(d["f0_v_hz"])
        t = cls(**kw)
        if not (t.band_lo_hz > 0 and t.band_hi_hz > t.band_lo_hz):
            raise ValueError("Target.from_dict: need 0 < band_lo_hz < band_hi_hz")
        if not (t.coverage_h_deg > 0 and t.coverage_v_deg > 0):
            raise ValueError("Target.from_dict: coverage angles must be positive")
        if t.f0_hz is not None and not (t.f0_hz > 0 and t.f0_hz <= t.band_hi_hz):
            raise ValueError(
                f"Target.from_dict: f0_hz must be in (0, band_hi_hz], got {t.f0_hz!r} "
                f"(band_hi {t.band_hi_hz:g})")
        if t.f0_v_hz is not None:
            if not (t.f0_v_hz > 0 and t.f0_v_hz <= t.band_hi_hz):
                raise ValueError(
                    f"Target.from_dict: target.f0_v_hz must be in (0, band_hi_hz], got "
                    f"{t.f0_v_hz!r} (band_hi {t.band_hi_hz:g})")
            if t.f0_hz is not None and t.f0_v_hz < t.f0_hz:
                raise ValueError(
                    f"Target.from_dict: target.f0_v_hz must be >= target.f0_hz, got "
                    f"f0_v_hz={t.f0_v_hz!r} < f0_hz={t.f0_hz!r}")
        return t


# ------------------------------------------------------------------ freq_weights validation
# Appended for WP4 (senior pass 2026-10-24). ``freq_weights`` stays OPTIONAL; absent means no
# weighting and every existing YAML behaves exactly as before. Only a PROVIDED value is checked,
# so the typo that used to be silently ignored (Report 1 F6/B1) is now a clear error.

import math  # noqa: E402  (appended section; keeps the frozen block untouched)


def validate_freq_weights(value) -> dict:
    """Validate and normalise a ``Target.freq_weights`` mapping.

    Accepted schema (01_CONTRACTS section 11, WP4)::

        freq_weights:
          band_hz:
            - [lo_hz, hi_hz, weight]
            - ...

    Every interval must be ``0 < lo < hi`` with finite endpoints, and ``weight`` must be finite
    and strictly positive. A frequency gets the PRODUCT of every interval that contains it
    (default 1.0). Returns a normalised ``{"band_hz": [[float, float, float], ...]}`` dict.

    Raises ``ValueError`` with a message naming the offending entry. Unknown top-level keys are
    rejected so a misspelt ``band_hz`` is not silently ignored.
    """
    if not isinstance(value, dict):
        raise ValueError(
            "Target.freq_weights: expected a mapping like {band_hz: [[lo_hz, hi_hz, weight], "
            f"...]}}, got {type(value).__name__}")
    unknown = sorted(set(value) - {"band_hz"})
    if unknown:
        raise ValueError(f"Target.freq_weights: unknown key(s) {unknown}; only 'band_hz' is allowed")
    if "band_hz" not in value:
        raise ValueError("Target.freq_weights: missing required key 'band_hz'")
    bands = value["band_hz"]
    if not isinstance(bands, (list, tuple)):
        raise ValueError(
            "Target.freq_weights.band_hz: expected a list of [lo_hz, hi_hz, weight] rows, got "
            f"{type(bands).__name__}")
    out: list[list[float]] = []
    for i, row in enumerate(bands):
        where = f"Target.freq_weights.band_hz[{i}]"
        if not isinstance(row, (list, tuple)) or len(row) != 3:
            raise ValueError(f"{where}: expected [lo_hz, hi_hz, weight], got {row!r}")
        try:
            lo, hi, w = float(row[0]), float(row[1]), float(row[2])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{where}: lo, hi and weight must be numbers, got {row!r}") from exc
        if not (math.isfinite(lo) and math.isfinite(hi) and math.isfinite(w)):
            raise ValueError(f"{where}: lo, hi and weight must be finite, got {row!r}")
        if not (lo > 0.0 and hi > lo):
            raise ValueError(f"{where}: need 0 < lo_hz < hi_hz, got lo={lo}, hi={hi}")
        if not w > 0.0:
            raise ValueError(f"{where}: weight must be > 0, got {w}")
        out.append([lo, hi, w])
    return {"band_hz": out}
