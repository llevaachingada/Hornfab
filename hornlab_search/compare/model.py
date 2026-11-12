"""``AbData``: one normalized container for either side of the A/B check.

Canonical basis (everything is converted INTO it on import, the conversion is written to ``meta``):

* drive      1 m/s normal velocity on the driven surface (Boundary Lab's ``normal_velocity`` basis).
             Hornfab drives a unit normal ACCELERATION: |p_vel| = omega |p_acc| (``hornfab_side`` converts).
* phasor     exp(+i omega t) (Boundary Lab / standard audio). Hornfab's solver uses exp(-i omega t): conjugate.
* level      ``level == "absolute"``: dB re 20 uPa. ``"normalized"``: dB re the on-axis sample (BL polar and
             balloon exports are normalized; its on-axis export is absolute).
* angles     degrees, ascending, an exact 0. +angle on H is toward +X, on V toward +Y (both tools).
* balloon    unit direction vectors, theta from +Z, phi from +X toward +Y (both tools).

Arrays are the same shapes as ``types.Response`` so the existing metric code can be reused.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from ..constants import C_AIR, REF_P

CANON_DRIVE = "velocity_1_m_per_s"
CANON_TIME = "exp(+i omega t)"

_ARRAY_FIELDS = ("freqs_hz", "angles_deg", "spl_h_db", "spl_v_db", "p_h", "p_v", "phase_h_deg", "phase_v_deg",
                 "on_axis_spl_db", "on_axis_phase_deg", "balloon_dirs", "balloon_spl_db", "z_norm")


@dataclass
class AbData:
    label: str
    source: str
    freqs_hz: np.ndarray
    angles_deg: np.ndarray
    spl_h_db: np.ndarray | None = None
    spl_v_db: np.ndarray | None = None
    p_h: np.ndarray | None = None
    p_v: np.ndarray | None = None
    level: str = "absolute"
    phase_h_deg: np.ndarray | None = None
    phase_v_deg: np.ndarray | None = None
    on_axis_spl_db: np.ndarray | None = None
    on_axis_phase_deg: np.ndarray | None = None
    balloon_dirs: np.ndarray | None = None
    balloon_spl_db: np.ndarray | None = None
    balloon_kind: str = "unknown"          # "fibonacci" (equal area) | "theta_phi" (weight sin theta) | "unknown"
    z_norm: np.ndarray | None = None       # Z / (rho c), canonical phasor, per frequency
    meta: dict = field(default_factory=dict)

    # ------------------------------------------------------------------ validation
    def __post_init__(self):
        self.freqs_hz = np.asarray(self.freqs_hz, dtype=float)
        self.angles_deg = np.asarray(self.angles_deg, dtype=float)
        self.validate()

    def validate(self) -> None:
        f, a = self.freqs_hz, self.angles_deg
        if f.ndim != 1 or f.size == 0 or np.any(np.diff(f) <= 0) or np.any(f <= 0):
            raise ValueError(f"{self.label}: freqs_hz must be 1-D, positive and strictly ascending")
        if a.ndim != 1 or a.size < 1 or np.any(np.diff(a) <= 0):
            raise ValueError(f"{self.label}: angles_deg must be 1-D and strictly ascending")
        if self.level not in ("absolute", "normalized"):
            raise ValueError(f"{self.label}: level must be 'absolute' or 'normalized', got {self.level!r}")
        want = (f.size, a.size)
        for name in ("spl_h_db", "spl_v_db", "p_h", "p_v", "phase_h_deg", "phase_v_deg"):
            v = getattr(self, name)
            if v is not None:
                v = np.asarray(v)
                setattr(self, name, v)
                if v.shape != want:
                    raise ValueError(f"{self.label}: {name} has shape {v.shape}, expected {want} (n_freqs, n_angles)")
        for name in ("on_axis_spl_db", "on_axis_phase_deg", "z_norm"):
            v = getattr(self, name)
            if v is not None:
                v = np.asarray(v)
                setattr(self, name, v)
                if v.shape != (f.size,):
                    raise ValueError(f"{self.label}: {name} has shape {v.shape}, expected ({f.size},)")
        if self.balloon_spl_db is not None:
            b = np.asarray(self.balloon_spl_db, dtype=float)
            self.balloon_spl_db = b
            if self.balloon_dirs is None:
                raise ValueError(f"{self.label}: balloon_spl_db without balloon_dirs")
            d = np.asarray(self.balloon_dirs, dtype=float)
            self.balloon_dirs = d
            if d.ndim != 2 or d.shape[1] != 3 or b.shape != (f.size, d.shape[0]):
                raise ValueError(f"{self.label}: balloon shapes {b.shape} / {d.shape} do not match "
                                 f"({f.size}, n) / (n, 3)")

    # ------------------------------------------------------------------ accessors
    @property
    def axis_index(self) -> int:
        i = int(np.argmin(np.abs(self.angles_deg)))
        if abs(self.angles_deg[i]) > 1e-9:
            raise ValueError(f"{self.label}: no exact 0 degree sample in angles_deg")
        return i

    @staticmethod
    def _db_of(p: np.ndarray) -> np.ndarray:
        with np.errstate(divide="ignore"):
            return 20.0 * np.log10(np.abs(p) / REF_P)

    def db(self, plane: str) -> np.ndarray | None:
        """(nf, na) dB of plane 'H' or 'V' in this object's ``level`` (computed from p when only p is stored)."""
        s, p = (self.spl_h_db, self.p_h) if plane == "H" else (self.spl_v_db, self.p_v)
        if s is not None:
            return np.asarray(s, dtype=float)
        if p is not None:
            d = self._db_of(p)
            return d if self.level == "absolute" else d - d[:, [self.axis_index]]
        return None

    def normalized(self, plane: str) -> np.ndarray | None:
        """dB re the 0 degree sample of the same plane and frequency (works for either level)."""
        d = self.db(plane)
        if d is None:
            return None
        return d - d[:, [self.axis_index]]

    def axis_db_absolute(self) -> np.ndarray | None:
        """Absolute on-axis dB SPL, or None when this side only has normalized data."""
        if self.on_axis_spl_db is not None:
            return np.asarray(self.on_axis_spl_db, dtype=float)
        if self.level == "absolute":
            d = self.db("H")
            if d is None:
                d = self.db("V")
            if d is not None:
                return d[:, self.axis_index]
        return None

    def distance_m(self) -> float | None:
        v = self.meta.get("distance_m")
        return None if v is None else float(v)

    def sound_speed(self) -> float:
        return float(self.meta.get("sound_speed", C_AIR))

    def axis_phase_aligned_deg(self) -> np.ndarray | None:
        """On-axis phase with the propagation delay (distance / c) removed, degrees, wrapped to +-180.

        Boundary Lab's on-axis text export and this function use the same definition, so the two are comparable.
        Needs ``meta['distance_m']`` unless the phase is already aligned (``meta['axis_phase_aligned']``).
        """
        if self.on_axis_phase_deg is not None and self.meta.get("axis_phase_aligned", True):
            return np.asarray(self.on_axis_phase_deg, dtype=float)
        if self.on_axis_phase_deg is not None:
            ph = np.deg2rad(np.asarray(self.on_axis_phase_deg, dtype=float))
        else:
            src = self.p_h if self.p_h is not None else self.p_v
            if src is None:
                return None
            ph = np.angle(src[:, self.axis_index])
        r = self.distance_m()
        if r is None:
            return None
        ph = ph + 2.0 * np.pi * self.freqs_hz * r / self.sound_speed()      # exp(+i w t): propagation is -w r / c
        return np.rad2deg(np.angle(np.exp(1j * ph)))

    # ------------------------------------------------------------------ durable round trip
    def save(self, directory) -> Path:
        d = Path(directory)
        d.mkdir(parents=True, exist_ok=True)
        arrays = {k: np.asarray(getattr(self, k)) for k in _ARRAY_FIELDS if getattr(self, k) is not None}
        np.savez_compressed(d / "abdata.npz", **arrays)
        head = {"label": self.label, "source": self.source, "level": self.level,
                "balloon_kind": self.balloon_kind, "meta": _jsonable(self.meta), "format": 1,
                "canonical": {"drive": CANON_DRIVE, "time_convention": CANON_TIME}}
        (d / "abdata.json").write_text(json.dumps(head, indent=2, sort_keys=True), encoding="utf-8")
        return d

    @classmethod
    def load(cls, directory) -> "AbData":
        d = Path(directory)
        head = json.loads((d / "abdata.json").read_text(encoding="utf-8"))
        with np.load(d / "abdata.npz") as z:
            arrays = {k: z[k] for k in z.files}
        return cls(label=head["label"], source=head["source"], level=head.get("level", "absolute"),
                   balloon_kind=head.get("balloon_kind", "unknown"), meta=head.get("meta", {}), **arrays)


def _jsonable(o):
    if isinstance(o, dict):
        return {str(k): _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, np.generic):
        return o.item()
    if isinstance(o, float) and not np.isfinite(o):
        return None
    return o
