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
        t = cls(**kw)
        if not (t.band_lo_hz > 0 and t.band_hi_hz > t.band_lo_hz):
            raise ValueError("Target.from_dict: need 0 < band_lo_hz < band_hi_hz")
        if not (t.coverage_h_deg > 0 and t.coverage_v_deg > 0):
            raise ValueError("Target.from_dict: coverage angles must be positive")
        return t
