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

# WP4 (senior pass 2026-10-24): the verify grid's HF-density extension starts at 5 kHz — below
# that the frozen 25-point verify grid is already dense enough for every measured epw decision.
HF_VERIFY_LO_HZ = 5000.0


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
    rear_res_factor: float = 1.0       # WP7: scale ONLY the outer shell/rear-cap resolution
    band_split: dict | None = None     # WP8: {"edges_hz": [...]} -> one mesh per band (absent = today)

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
    cuda_fused: bool = False   # WP15: opt-in fused CUDA Burton-Miller assembly (beat_cuda only)
    source_motion: str = "normal"   # WP5: 'normal' (breathing cap, today) | 'axial' (rigid piston)

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
    infeasible_penalty: str = "flat"   # WP3: 'flat' (default, today) | 'graded'


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
    objective_version: int = 1       # WP1: brief/config `objective: {version: 2}` -> v2 objective
    grid: dict | None = None         # WP4: brief `grid: {verify_points_per_octave: N}` -> HF verify grid


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
    allowed = {"name", "description", "driver", "envelope", "symmetry", "source", "target", "weights",
               "verify_only", "objective", "grid"}
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
    pol = drv.get("throat_angle_policy")
    if pol is not None and pol not in ("pin", "free"):
        raise ConfigError(f"{where}: driver.throat_angle_policy must be 'pin' or 'free', got {pol!r}")
    if "objective" in raw and raw["objective"] is not None:
        _validate_objective_block(raw["objective"], where)
    if "grid" in raw and raw["grid"] is not None:
        _validate_grid_block(raw["grid"], where)
    for k in ("max_mouth_w_mm", "max_mouth_h_mm", "max_depth_mm"):
        if not isinstance(env.get(k), (int, float)) or not float(env[k]) > 0:
            raise ConfigError(f"{where}: envelope.{k} must be a positive number")
    if not isinstance(raw.get("verify_only", False), bool):
        raise ConfigError(f"{where}: verify_only must be true or false")
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


# ------------------------------------------------------------------ WP1/WP4 blocks (senior pass)

def _validate_objective_block(block, where: str) -> dict:
    """Brief/config ``objective: {version: 2}`` selects objective v2 (WP1). Default 1. Unknown
    keys are refused so a YAML typo is never silent."""
    if not isinstance(block, dict):
        raise ConfigError(f"{where}: objective must be a mapping")
    unknown = set(block) - {"version"}
    if unknown:
        raise ConfigError(f"{where}: objective unknown key(s) {sorted(unknown)} (allowed: version)")
    v = block.get("version", 1)
    if isinstance(v, bool) or not isinstance(v, int) or v not in (1, 2):
        raise ConfigError(f"{where}: objective.version must be 1 or 2, got {v!r}")
    return {"version": int(v)}


def _validate_grid_block(block, where: str) -> dict:
    """Brief ``grid: {verify_points_per_octave: N}`` (WP4): build the verify grid as the frozen
    grid PLUS extra log points in [5 kHz, band_hi] at that density. It forms a NEW grid group:
    records carry it via their own solve.freqs_hz, and comparisons against runs with a different
    grid refuse (intended separation)."""
    if not isinstance(block, dict):
        raise ConfigError(f"{where}: grid must be a mapping")
    unknown = set(block) - {"verify_points_per_octave"}
    if unknown:
        raise ConfigError(f"{where}: grid unknown key(s) {sorted(unknown)} "
                          f"(allowed: verify_points_per_octave)")
    ppo = block.get("verify_points_per_octave")
    if isinstance(ppo, bool) or not isinstance(ppo, (int, float)) or not ppo > 0:
        raise ConfigError(f"{where}: grid.verify_points_per_octave must be a positive number")
    return {"verify_points_per_octave": float(ppo)}


# ------------------------------------------------------------------ WP5/WP7/WP8 blocks

def _validate_rear_res_factor(value, where: str) -> float:
    """WP7: ``mesh.rear_res_factor`` scales ONLY the rear/outer-shell resolution. Any positive
    finite factor is legal (values > 1 coarsen); 1.0 is today's mesh."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) \
            or not np.isfinite(float(value)) or float(value) <= 0.0:
        raise ConfigError(f"{where}: rear_res_factor must be a finite positive number, got {value!r}")
    return float(value)


def _validate_band_split(block, where: str, band_lo: float, band_hi: float) -> dict | None:
    """WP8: ``mesh.band_split: {edges_hz: [...]}``. Edges are strictly increasing and lie strictly
    inside the target band; at least one edge. Absent/None keeps today's single-mesh policy."""
    if block is None:
        return None
    if not isinstance(block, dict):
        raise ConfigError(f"{where}: band_split must be a mapping")
    unknown = set(block) - {"edges_hz"}
    if unknown:
        raise ConfigError(f"{where}: band_split unknown key(s) {sorted(unknown)} (allowed: edges_hz)")
    edges = block.get("edges_hz")
    if not isinstance(edges, (list, tuple)) or not edges:
        raise ConfigError(f"{where}: band_split.edges_hz must be a non-empty list of numbers")
    vals = []
    for e in edges:
        if isinstance(e, bool) or not isinstance(e, (int, float)) or not np.isfinite(float(e)):
            raise ConfigError(f"{where}: band_split.edges_hz must contain finite numbers, got {e!r}")
        vals.append(float(e))
    if any(b <= a for a, b in zip(vals, vals[1:])):
        raise ConfigError(f"{where}: band_split.edges_hz must be strictly increasing, got {vals}")
    for e in vals:
        if not (band_lo < e < band_hi):
            raise ConfigError(
                f"{where}: band_split edge {e:g} Hz is outside the open target band "
                f"({band_lo:g}, {band_hi:g}) Hz")
    return {"edges_hz": vals}


def _validate_source_motion(value, backend: str, where: str) -> str:
    """WP5: ``solve.source_motion`` is 'normal' (today) or 'axial' (rigid piston). Only the beat
    adapter implements it; a non-beat backend with a non-default value is refused loudly."""
    if not isinstance(value, str) or value not in ("normal", "axial"):
        raise ConfigError(f"{where}: source_motion must be 'normal' or 'axial', got {value!r}")
    if value != "normal" and not str(backend).startswith("beat_"):
        raise ConfigError(
            f"{where}: source_motion={value!r} is only implemented for the beat backends "
            f"(beat_cuda/beat_cpu), got backend {backend!r}")
    return value


# ------------------------------------------------------------------ WP2 driver fairness

_PIN_FAMILIES = ("OSSE", "R-OSSE", "ICW")
_DRIVER_PIN_TOL = 0.01


def _force_pin(key: str, value: float, seed: dict, bounds: dict, where: str, unit: str,
               nested: bool = False) -> None:
    """WP2: force one design parameter onto the brief's driver value.

    A config that already PINS the parameter (``search: false``) at a different value raises
    ConfigError — silently rescaling a horn is worse. A searching bound is replaced by
    lo=hi=value, search: false, and the seed param is set to the same value so the seed design
    matches the brief's driver. For nested FREEFORM keys (``profileH.throatAngleDeg``) the bound
    keeps its flat dotted-path form and the seed param is set inside its plane node."""
    b = bounds.get(key)
    if isinstance(b, dict) and not b.get("search", True):
        lo, hi = float(b.get("lo", value)), float(b.get("hi", value))
        if abs(lo - value) > _DRIVER_PIN_TOL or abs(hi - value) > _DRIVER_PIN_TOL:
            raise ConfigError(
                f"{where}: bounds.{key} is pinned at [{lo}, {hi}] {unit} but the applied brief "
                f"pins the driver at {value} {unit}; rescale the horn explicitly or drop the pin "
                f"(WP2 driver fairness, senior pass 2026-10-24)")
        return
    bounds[key] = {"lo": value, "hi": value, "search": False}
    if nested:
        plane, _, leaf = key.partition(".")
        node = seed.get(plane)
        if isinstance(node, dict):
            node[leaf] = value
    else:
        seed[key] = value


def _apply_brief_driver_pins(raw: dict, brief_d: dict | None, where: str,
                             embedded: bool = False) -> None:
    """WP2 (senior pass 2026-10-24, fairness): when a brief is applied to a NATIVE family config
    (no ``generator:``), pin the horn's throat to the brief's driver, so every family competes on
    the same objective instead of each searching its own throat. Generator typologies already do
    this inside registry.materialize; their configs are untouched here.

    - OSSE / R-OSSE / ICW: ``r0_mm`` is pinned to ``driver.exit_radius_mm`` (always; the brief
      defines the throat size a design is allowed to use), and ``a0_deg`` is pinned to
      ``driver.exit_angle_deg`` ONLY when the brief says ``driver.throat_angle_policy: pin``.
    - Native FREEFORM: under ``pin``, ``profileH/V.throatAngleDeg`` are pinned to the exit angle.
    - A brief WITHOUT the policy key behaves exactly as before on throat angles, so every
      existing run reproduces bit-for-bit.
    - Oracle M1 ruling: ``embedded=True`` (a run directory's own merged config.yaml, the
      resume/verify/report path) SKIPS the pins entirely — a pre-WP2 run whose embedded brief
      conflicts with its pinned throat must stay loadable (bit-for-bit contract on old runs);
      fairness is enforced where the brief is applied fresh (``--brief`` or ``brief_file:``,
      including a NEW run's subprocess, which passes the brief freshly)."""
    if brief_d is None or embedded or raw.get("generator") is not None:
        return
    drv = brief_d.get("driver") or {}
    if not isinstance(drv.get("exit_radius_mm"), (int, float)):
        return  # a malformed driver was already refused inside load_brief
    exit_r = float(drv["exit_radius_mm"])
    exit_a = float(drv["exit_angle_deg"])
    policy = drv.get("throat_angle_policy")
    family = str(raw.get("family", ""))
    seed = raw.setdefault("seed_params", {})
    bounds = raw.setdefault("bounds", {})
    if family in _PIN_FAMILIES and ("r0_mm" in seed or "r0_mm" in bounds):
        _force_pin("r0_mm", exit_r, seed, bounds, where, "mm")
        if policy == "pin" and ("a0_deg" in seed or "a0_deg" in bounds):
            _force_pin("a0_deg", exit_a, seed, bounds, where, "deg")
    if family == "FREEFORM" and policy == "pin":
        for plane in ("profileH", "profileV"):
            node = seed.get(plane)
            if isinstance(node, dict) and "throatAngleDeg" in node:
                _force_pin(f"{plane}.throatAngleDeg", exit_a, seed, bounds, where, "deg",
                           nested=True)


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
    embedded_brief = False
    if brief is None and isinstance(raw.get("brief"), dict):
        # A run directory's config.yaml already holds the merged brief (target/weights applied and
        # the brief embedded); use it as is, so resume/verify/report reproduce the run exactly.
        brief_d = dict(raw["brief"])
        brief_path = None
        embedded_brief = True
    obj_cfg = None
    if raw.get("objective") is not None:
        obj_cfg = _validate_objective_block(raw["objective"], where)
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
    if brief_d is not None and brief_d.get("objective") is not None:
        # A brief's objective version wins over the config's own block (the brief replaces the
        # target/weights pair it belongs to); recorded in raw so config_sha covers it.
        raw["objective"] = dict(brief_d["objective"])
    elif obj_cfg is not None:
        raw["objective"] = obj_cfg
    if brief_d is not None and brief_d.get("grid") is not None:
        raw["grid"] = dict(brief_d["grid"])
    grid_cfg = _validate_grid_block(raw["grid"], where) if raw.get("grid") is not None else None
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

    _apply_brief_driver_pins(raw, brief_d, where, embedded=embedded_brief)

    mesh = _build(MeshSettings, _require(raw, "mesh", where), f"{where}:mesh",
                  optional=("max_triangle_slack", "rear_res_factor", "band_split"))
    solve = _build(SolveSettings, _require(raw, "solve", where), f"{where}:solve",
                   optional=("cuda_fused", "source_motion"))
    if solve.cuda_fused and str(solve.backend) != "beat_cuda":
        raise ConfigError(f"{where}: solve.cuda_fused is only implemented for backend: beat_cuda "
                          f"(got {solve.backend!r})")
    mesh.rear_res_factor = _validate_rear_res_factor(mesh.rear_res_factor, f"{where}:mesh")
    if mesh.band_split is not None:                    # absent = today, no target keys touched
        try:
            band_lo = float(raw["target"]["band_lo_hz"])
            band_hi = float(raw["target"]["band_hi_hz"])
        except (KeyError, TypeError, ValueError):
            raise ConfigError(f"{where}: target.band_lo_hz/band_hi_hz are required numbers") from None
        mesh.band_split = _validate_band_split(mesh.band_split, f"{where}:mesh", band_lo, band_hi)
    solve.source_motion = _validate_source_motion(
        solve.source_motion, str(solve.backend), f"{where}:solve")
    search = _build(SearchSettings, _require(raw, "search", where), f"{where}:search",
                    optional=("popsize", "infeasible_penalty"))
    if "popsize" not in raw["search"]:
        search.popsize = None
    if search.infeasible_penalty not in ("flat", "graded"):
        raise ConfigError(f"{where}: search.infeasible_penalty must be 'flat' or 'graded', "
                          f"got {search.infeasible_penalty!r}")
    objective_version = int((raw.get("objective") or {}).get("version", 1))

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
        objective_version=objective_version,
        grid=grid_cfg,
    )


# ------------------------------------------------------------------ specs

def mode_freqs(mode: str, cfg: Config) -> tuple[float, ...]:
    """The mode's frozen log grid, with its top edge clipped to the target band's upper
    edge so the mesh is never asked to resolve frequencies the objective ignores.

    WP4 (senior pass 2026-10-24): a brief with ``grid: {verify_points_per_octave: N}`` extends the
    VERIFY grid with extra log points in [5 kHz, band_hi] at that density. That is a NEW grid
    group — records carry it through their own solve.freqs_hz (and the solve-spec hash), so a
    comparison against runs on the frozen grid refuses rather than mixing grids."""
    lo, hi, n = FREQ_GRIDS[mode]
    band_hi = cfg.target_raw.get("band_hi_hz")
    if band_hi is not None and float(band_hi) < hi:
        hi = float(band_hi)
    base = [round(float(f), 2) for f in freq_grid(lo, hi, n)]
    if mode == "verify":
        ppo = ((cfg.grid or {}).get("verify_points_per_octave"))
        if ppo is not None and hi > HF_VERIFY_LO_HZ:
            n_oct = float(np.log2(hi / HF_VERIFY_LO_HZ))
            n_pts = max(1, int(round(n_oct * float(ppo))))
            extra = [round(float(f), 2) for f in np.geomspace(HF_VERIFY_LO_HZ, hi, n_pts + 1)]
            return tuple(sorted(set(base) | set(extra)))
    return tuple(base)


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
    # WP15: cuda_fused rides in `extra` so the solve-spec hash (cache key, dataset provenance)
    # changes ONLY when the opt-in is actually set; absent leaves every old hash untouched.
    extra: dict = {"cuda_fused": True} if bool(getattr(s, "cuda_fused", False)) else {}
    # WP5: 'normal' is today's beat source and must NOT enter `extra` (old hashes unchanged).
    if str(getattr(s, "source_motion", "normal")) != "normal":
        extra["source_motion"] = str(s.source_motion)
    # WP8: band-split rides in `extra` too (solve hash + Response.meta provenance via beat).
    band_split = getattr(cfg.mesh, "band_split", None)
    if band_split is not None:
        extra["mesh_policy"] = "band_split_v1"
        extra["band_edges_hz"] = [float(e) for e in band_split["edges_hz"]]
    # WP7: a non-1.0 rear_res_factor changes the MESH, so it must change the solve-spec hash too
    # (solve cache + failure markers + resume memo key off it); absent/1.0 leaves old hashes untouched.
    if float(getattr(cfg.mesh, "rear_res_factor", 1.0)) != 1.0:
        extra["rear_res_factor"] = float(cfg.mesh.rear_res_factor)
    return SolveSpec(
        mode=mode,
        freqs_hz=mode_freqs(mode, cfg),
        backend=str(s.backend),
        observation=obs,
        gmres_tol=float(s.gmres_tol),
        extra=extra,
    )
