"""YAML -> Config.

Wave 0 keeps the design space and target as raw dicts (03_TASK_SCAFFOLD step 4, "the dict
approach"): this module imports nothing from Wave 1. The pipeline (task 08) builds the typed
DesignSpace and Target from `bounds_raw` and `target_raw`.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import yaml

from .types import MeshSpec, Mode, ObservationSpec, SolveSpec

log = logging.getLogger("hornlab_search.config")

# 01_CONTRACTS section 6: max_triangles = ceil(2 * dof_cap * quadrant_factor * 1.15)
QUADRANT_FACTOR = {"1234": 1, "12": 2, "14": 2, "1": 4}

# 01_CONTRACTS section 8: frozen grid shape per mode (f_low, f_high, points).
FREQ_GRIDS: dict[str, tuple[float, float, int]] = {
    "screen": (500.0, 10_000.0, 12),
    "verify": (300.0, 16_000.0, 25),
    "final": (250.0, 20_000.0, 36),
}

MODES = ("screen", "verify", "final")


def freq_grid(lo: float, hi: float, n: int) -> tuple[float, ...]:
    return tuple(round(float(f), 2) for f in np.geomspace(lo, hi, n))


# ------------------------------------------------------------------ settings

@dataclass
class MeshSettings:
    epw: float
    quadrants: str
    dof_cap_screen: int
    dof_cap_verify: int
    dof_cap_final: int
    dof_per_triangle: float
    max_triangle_slack: float = 1.15

    def dof_cap(self, mode: str) -> int:
        return int(getattr(self, f"dof_cap_{mode}"))


@dataclass
class SolveSettings:
    backend: str
    distance_m: float
    angle_count: int
    balloon: bool
    balloon_points_screen: int
    balloon_points_verify: int
    gmres_tol: float
    timeout_s: float

    def balloon_points(self, mode: str) -> int:
        if not self.balloon:
            return 0
        return int(self.balloon_points_screen if mode == "screen" else self.balloon_points_verify)


@dataclass
class SearchSettings:
    algorithm: str
    sigma0: float
    seed: int
    budget: int
    popsize: int | None
    tolfun: float


@dataclass
class Config:
    name: str
    family: str
    seed_params: dict
    bounds_raw: dict            # key -> {lo, hi, search, log}
    target_raw: dict
    weights: dict
    mesh: MeshSettings
    solve: SolveSettings
    search: SearchSettings
    raw: dict


# ------------------------------------------------------------------ loading

class ConfigError(ValueError):
    """A YAML config is missing a required key or has an illegal value."""


def _require(section: dict, key: str, where: str):
    if key not in section or section[key] is None:
        raise ConfigError(f"{where}: missing required key '{key}'")
    return section[key]


def _build(cls, section: dict, where: str, optional: tuple[str, ...] = ()):
    kwargs = {}
    for name in cls.__dataclass_fields__:
        if name in optional:
            if name in section:
                kwargs[name] = section[name]
            continue
        kwargs[name] = _require(section, name, where)
    unknown = set(section) - set(cls.__dataclass_fields__)
    if unknown:
        raise ConfigError(f"{where}: unknown key(s) {sorted(unknown)}")
    return cls(**kwargs)


def load_config(path) -> Config:
    path = Path(path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ConfigError(f"{path}: top level must be a mapping")
    where = path.name

    mesh = _build(MeshSettings, _require(raw, "mesh", where), f"{where}:mesh",
                  optional=("max_triangle_slack",))
    solve = _build(SolveSettings, _require(raw, "solve", where), f"{where}:solve")
    search = _build(SearchSettings, _require(raw, "search", where), f"{where}:search",
                    optional=("popsize",))
    if "popsize" not in raw["search"]:
        search.popsize = None

    if mesh.quadrants not in QUADRANT_FACTOR:
        raise ConfigError(f"{where}: mesh.quadrants must be one of {list(QUADRANT_FACTOR)}")
    if solve.angle_count % 2 != 1:
        raise ConfigError(f"{where}: solve.angle_count must be odd (exact on-axis sample)")

    bounds = _require(raw, "bounds", where)
    for k, b in bounds.items():
        if "lo" not in b or "hi" not in b:
            raise ConfigError(f"{where}: bounds.{k} needs lo and hi")

    return Config(
        name=str(_require(raw, "name", where)),
        family=str(_require(raw, "family", where)),
        seed_params=dict(_require(raw, "seed_params", where)),
        bounds_raw=dict(bounds),
        target_raw=dict(_require(raw, "target", where)),
        weights=dict(_require(raw, "weights", where)),
        mesh=mesh,
        solve=solve,
        search=search,
        raw=raw,
    )


# ------------------------------------------------------------------ specs

def mode_freqs(mode: str, cfg: Config) -> tuple[float, ...]:
    """The mode's frozen log grid, with its top edge clipped to the target band's upper
    edge so the mesh is never asked to resolve frequencies the objective ignores."""
    lo, hi, n = FREQ_GRIDS[mode]
    band_hi = cfg.target_raw.get("band_hi_hz")
    if band_hi is not None and float(band_hi) < hi:
        hi = float(band_hi)
    return freq_grid(lo, hi, n)


def mesh_spec(mode: Mode, cfg: Config) -> MeshSpec:
    if mode not in MODES:
        raise ConfigError(f"unknown mode {mode!r}")
    cap = cfg.mesh.dof_cap(mode)
    qf = QUADRANT_FACTOR[cfg.mesh.quadrants]
    max_tri = int(np.ceil(2 * cap * qf * cfg.mesh.max_triangle_slack))
    return MeshSpec(
        epw=float(cfg.mesh.epw),
        f_max_hz=float(max(mode_freqs(mode, cfg))),
        quadrants=cfg.mesh.quadrants,
        max_triangles=max_tri,
        allow_large_mesh=False,
    )


def solve_spec(mode: Mode, cfg: Config) -> SolveSpec:
    if mode not in MODES:
        raise ConfigError(f"unknown mode {mode!r}")
    s = cfg.solve
    obs = ObservationSpec(
        distance_m=float(s.distance_m),
        angle_count=int(s.angle_count),
        balloon=bool(s.balloon),
        balloon_points=s.balloon_points(mode),
    )
    return SolveSpec(
        mode=mode,
        freqs_hz=mode_freqs(mode, cfg),
        backend=str(s.backend),
        observation=obs,
        gmres_tol=float(s.gmres_tol),
    )
