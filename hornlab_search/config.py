"""YAML -> Config.

Wave 0 keeps the design space and target as raw dicts (03_TASK_SCAFFOLD step 4, "the dict
approach"). The only Wave-1 import is `mesh.sizing` (a pure numpy/math module) so the triangle
ceiling has a single source of truth (senior ruling 2026-10-13); the pipeline (task 08) builds
the typed DesignSpace and Target from `bounds_raw` and `target_raw`.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import yaml

from .mesh import sizing
from .types import MeshSpec, Mode, ObservationSpec, SolveSpec

log = logging.getLogger("hornlab_search.config")

# 01_CONTRACTS section 6: max_triangles = ceil(2 * dof_cap * quadrant_factor * 1.15)
QUADRANT_FACTOR = sizing.QUADRANT_FACTOR  # one source (silent-killer rule)

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
    brief: dict | None = None        # design brief (docs/TYPOLOGY_PLAN.md s3), if one was applied
    generator: dict | None = None    # typology generator block (s4); family is then FREEFORM


# ------------------------------------------------------------------ briefs

BRIEF_SYMMETRY = ("hv", "axisymmetric")


def _resolve_path(p, *bases) -> Path:
    p = Path(p)
    if p.is_absolute() or p.exists():
        return p
    for b in bases:
        if b is not None and (Path(b) / p).exists():
            return Path(b) / p
    return p


def load_brief(path) -> dict:
    """A design brief: driver exit, size envelope, symmetry class, source cap, target and weights
    (docs/TYPOLOGY_PLAN.md s3). It makes J comparable across typologies. Raises ConfigError."""
    path = Path(path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    where = f"brief {path.name}"
    if not isinstance(raw, dict):
        raise ConfigError(f"{where}: top level must be a mapping")
    allowed = {"name", "description", "driver", "envelope", "symmetry", "source", "target", "weights"}
    unknown = set(raw) - allowed
    if unknown:
        raise ConfigError(f"{where}: unknown key(s) {sorted(unknown)}")
    for k in ("name", "driver", "envelope", "symmetry", "target", "weights"):
        _require(raw, k, where)
    drv, env = raw["driver"], raw["envelope"]
    for k in ("exit_radius_mm", "exit_angle_deg"):
        if not isinstance(drv.get(k), (int, float)):
            raise ConfigError(f"{where}: driver.{k} must be a number")
    if not 0 < float(drv["exit_radius_mm"]) < 100 or not 0 <= float(drv["exit_angle_deg"]) < 45:
        raise ConfigError(f"{where}: driver exit radius must be in (0, 100) mm and angle in [0, 45) deg")
    for k in ("max_mouth_w_mm", "max_mouth_h_mm", "max_depth_mm"):
        if not isinstance(env.get(k), (int, float)) or not float(env[k]) > 0:
            raise ConfigError(f"{where}: envelope.{k} must be a positive number")
    if raw["symmetry"] not in BRIEF_SYMMETRY:
        raise ConfigError(f"{where}: symmetry must be one of {list(BRIEF_SYMMETRY)}")
    cap = (raw.get("source") or {}).get("cap", "auto")
    if not (cap == "auto" or (isinstance(cap, (int, float)) and float(cap) > 0)):
        raise ConfigError(f"{where}: source.cap must be 'auto' or a positive radius in mm")
    from .targets.spec import Target
    try:
        t = Target.from_dict(dict(raw["target"]))
    except ValueError as exc:
        raise ConfigError(f"{where}: {exc}") from None
    if raw["symmetry"] == "axisymmetric" and t.coverage_h_deg != t.coverage_v_deg:
        raise ConfigError(f"{where}: an axisymmetric brief needs coverage_h_deg == coverage_v_deg")
    out = dict(raw)
    out["source"] = {"cap": cap}
    out["path"] = str(path)
    return out


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


def load_config(path, *, brief=None, cma_seed: int | None = None) -> Config:
    """YAML -> Config. ``brief`` (a path; or the config's own ``brief:`` key) replaces the target
    and weights with the brief's and records the brief in ``raw`` so ``config_sha`` covers it.
    ``cma_seed`` overrides ``search.seed``. A ``generator:`` block makes this a typology config
    (family must be FREEFORM; ``seed_params``/``bounds`` then hold generator knobs)."""
    path = Path(path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ConfigError(f"{path}: top level must be a mapping")
    where = path.name

    brief_path = brief if brief is not None else raw.get("brief_file")
    brief_d = None
    if brief is None and isinstance(raw.get("brief"), dict):
        # A run directory's config.yaml already holds the merged brief (target/weights applied and
        # the brief embedded); use it as is, so resume/verify/report reproduce the run exactly.
        brief_d = dict(raw["brief"])
        brief_path = None
    if brief_path is not None:
        bp = _resolve_path(brief_path, path.parent, Path(__file__).resolve().parents[1])
        if not Path(bp).exists():
            raise ConfigError(
                f"{where}: brief_file {brief_path!r} could not be found; "
                f"tried relative to config dir ({path.parent}) and repo root. "
                f"Use an absolute path or a path relative to the config file."
            )
        brief_d = load_brief(bp)
        raw["target"] = dict(brief_d["target"])
        raw["weights"] = dict(brief_d["weights"])
        raw["brief"] = {k: v for k, v in brief_d.items() if k != "path"}
    if cma_seed is not None:
        raw.setdefault("search", {})
        raw["search"] = dict(raw["search"], seed=int(cma_seed))
    gen = raw.get("generator")
    if gen is not None:
        if not isinstance(gen, dict) or "name" not in gen:
            raise ConfigError(f"{where}: generator must be a mapping with a 'name'")
        if raw.get("family") != "FREEFORM":
            raise ConfigError(f"{where}: a generator config must have family: FREEFORM")
        if brief_d is None:
            raise ConfigError(f"{where}: a generator config needs a brief (brief_file: or --brief)")

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
        brief=brief_d,
        generator=None if gen is None else dict(gen),
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
    # Single source of truth for the triangle ceiling (senior ruling 2026-10-13): the section-6
    # literal ceil(2*cap*qf*slack) assumes dof_per_triangle == 0.5; the measured value is 0.51
    # (quarter), so use sizing.max_triangles_for to honour it instead of drifting 2% away.
    max_tri = sizing.max_triangles_for(
        cap, cfg.mesh.quadrants, cfg.mesh.dof_per_triangle, cfg.mesh.max_triangle_slack)
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
