"""Hornfab side of the A/B check.

* ``from_response``       ``types.Response`` -> ``AbData`` (drive and phasor converted to the canonical basis)
* ``load_hornfab``        a response.npz / cache entry / reference folder / ``AbData`` folder -> ``AbData``
* ``resolve_source``      a config, a run directory or a design directory -> (cfg, Design, label, mesh path or None)
* ``reference_freqs``     the dense frequency grid of the reference solve (default 1/12 octave, 100 Hz - 20 kHz)
* ``solve_reference``     the high-resolution full-band reference solve (existing mesh + backend code paths only)

Conversion (verified against the time domain in tests/test_solve_phasor.py and tests/test_compare_ab_model.py):
Hornfab drives a unit normal ACCELERATION and the solver's phasor is exp(-i w t). Boundary Lab drives a
1 m/s VELOCITY and uses exp(+i w t). With a = -i w v (exp(-i w t)) the pressure for 1 m/s is
``p_acc * (-i w)`` and the other convention is its complex conjugate. Magnitude therefore moves by exactly
+20 log10(2 pi f) dB.
"""
from __future__ import annotations

import dataclasses
import json
import logging
import time
from pathlib import Path

import numpy as np

from ..constants import C_AIR, RHO_AIR
from .model import CANON_DRIVE, CANON_TIME, AbData

log = logging.getLogger("hornlab_search.compare.hornfab_side")

DEFAULT_LO_HZ = 100.0
DEFAULT_HI_HZ = 20000.0
DEFAULT_PPO = 12.0
DEFAULT_ANGLE_COUNT = 73          # 2.5 degree steps over -90..+90
DEFAULT_BALLOON_POINTS = 2048

REFERENCE_FILE = "response.npz"          # same layout as solve/cache.py (full Response, complex included)
REFERENCE_META = "reference_meta.json"


# ------------------------------------------------------------------ conversion

def accel_to_canonical(p, freqs_hz):
    """Pressure per unit ACCELERATION in exp(-i w t) -> pressure per 1 m/s VELOCITY in exp(+i w t).

    ``freqs_hz`` broadcasts against the LEADING axis of ``p``."""
    p = np.asarray(p, dtype=complex)
    w = 2.0 * np.pi * np.asarray(freqs_hz, dtype=float).reshape((-1,) + (1,) * (p.ndim - 1))
    return np.conj(p * (-1j * w))


def canonical_to_accel(p, freqs_hz):
    """Inverse of ``accel_to_canonical`` (used by the synthetic data and by round-trip tests)."""
    p = np.asarray(p, dtype=complex)
    w = 2.0 * np.pi * np.asarray(freqs_hz, dtype=float).reshape((-1,) + (1,) * (p.ndim - 1))
    return np.conj(p) / (-1j * w)


def spl_accel_to_velocity_db(spl_db, freqs_hz):
    f = np.asarray(freqs_hz, dtype=float).reshape((-1,) + (1,) * (np.asarray(spl_db).ndim - 1))
    return np.asarray(spl_db, dtype=float) + 20.0 * np.log10(2.0 * np.pi * f)


def from_response(resp, label: str = "Hornfab", meta: dict | None = None) -> AbData:
    """``types.Response`` -> ``AbData`` in the canonical basis. Missing complex arrays degrade to SPL only."""
    f = np.asarray(resp.freqs_hz, dtype=float)
    ang = np.asarray(resp.h_angles_deg, dtype=float)
    if not np.array_equal(ang, np.asarray(resp.v_angles_deg, dtype=float)):
        raise ValueError("H and V angle grids differ; the A/B container needs one shared grid")
    rmeta = dict(getattr(resp, "meta", None) or {})
    m = {"drive_converted_from": "unit_normal_acceleration", "time_converted_from": "exp(-i omega t)",
         "drive": CANON_DRIVE, "time_convention": CANON_TIME, "backend": getattr(resp, "backend", ""),
         "n_dof": getattr(resp, "n_dof", None), "distance_m": rmeta.get("distance_m"),
         "sound_speed": C_AIR, "rho": RHO_AIR, "quadrants": rmeta.get("quadrants"),
         "symmetry_plane": rmeta.get("symmetry_plane"), "source_motion": rmeta.get("source_motion"),
         "notes": []}
    m.update(meta or {})
    kw: dict = {}
    if resp.p_h is not None:
        kw["p_h"] = accel_to_canonical(resp.p_h, f)
    else:
        kw["spl_h_db"] = spl_accel_to_velocity_db(resp.spl_h_db, f)
        m["notes"].append("no complex pressure: SPL only (phase comparisons are skipped)")
    if resp.p_v is not None:
        kw["p_v"] = accel_to_canonical(resp.p_v, f)
    else:
        kw["spl_v_db"] = spl_accel_to_velocity_db(resp.spl_v_db, f)
    if resp.spl_balloon_db is not None and resp.balloon_dirs is not None:
        if resp.p_balloon is not None:
            kw["balloon_spl_db"] = AbData._db_of(accel_to_canonical(resp.p_balloon, f))
        else:
            kw["balloon_spl_db"] = spl_accel_to_velocity_db(resp.spl_balloon_db, f)
        kw["balloon_dirs"] = np.asarray(resp.balloon_dirs, dtype=float)
        kw["balloon_kind"] = "theta_phi"      # Response.meta['balloon_grid']: sin(theta) weights
    if resp.z_throat is not None:
        kw["z_norm"] = np.conj(np.asarray(resp.z_throat, dtype=complex))
    return AbData(label=label, source="hornfab", freqs_hz=f, angles_deg=ang, level="absolute",
                  meta=m, **kw)


def load_hornfab(path, label: str | None = None) -> AbData:
    """Accepts: an ``AbData`` folder, a folder holding ``response.npz`` (reference folder, solve-cache entry,
    design folder), or the ``response.npz`` file itself."""
    from ..solve import cache as solve_cache
    p = Path(path)
    if p.is_dir() and (p / "abdata.json").exists():
        return AbData.load(p)
    npz = p if p.is_file() else p / REFERENCE_FILE
    if not npz.exists():
        raise FileNotFoundError(f"no {REFERENCE_FILE} (or abdata.json) under {p}")
    resp = solve_cache.load_response(npz)
    extra: dict = {}
    mp = npz.parent / REFERENCE_META
    if mp.exists():
        rm = json.loads(mp.read_text(encoding="utf-8"))
        extra = {k: rm[k] for k in ("distance_m", "design_hash", "family", "params", "mesh", "rho", "sound_speed",
                                    "source_motion", "quadrants", "mesh_scale") if k in rm}
        extra["reference_meta"] = rm
    return from_response(resp, label=label or "Hornfab", meta=extra)


# ------------------------------------------------------------------ grids

def reference_freqs(lo_hz: float = DEFAULT_LO_HZ, hi_hz: float = DEFAULT_HI_HZ,
                    points_per_octave: float = DEFAULT_PPO) -> tuple[float, ...]:
    """Log grid with both end points exact, rounded to 0.01 Hz like ``config.freq_grid``.

    ``geomspace(lo, hi, n)`` is also what Boundary Lab builds from ``freq_min_hz``/``freq_max_hz``/``freq_count``
    (``np.logspace(log10 lo, log10 hi, n)``), so both tools sample the SAME frequencies from the same three
    numbers when ``lo``/``hi`` are integers."""
    if not (0 < lo_hz < hi_hz):
        raise ValueError(f"need 0 < lo < hi, got {lo_hz}, {hi_hz}")
    if not (0 < points_per_octave <= 96):
        raise ValueError(f"points_per_octave must be in (0, 96], got {points_per_octave}")
    n = max(2, int(round(float(np.log2(hi_hz / lo_hz)) * points_per_octave)) + 1)
    return tuple(round(float(x), 2) for x in np.geomspace(lo_hz, hi_hz, n))


# ------------------------------------------------------------------ design / config resolution

def _rows(run_dir: Path):
    from ..search.evaluate import read_ndjson
    f = run_dir / "search.ndjson"
    return read_ndjson(f) if f.exists() else []


def resolve_source(source, *, config=None, design_hash: str | None = None, rank: int = 0):
    """-> (cfg, Design, label, existing_mesh_path_or_None, source_kind).

    ``source`` is a config YAML (seed design), a run directory (design chosen by ``design_hash`` or by
    ``rank`` among successful rows ordered by objective, rank 0 = best) or a design directory
    (``designs/<hash>/`` holding mesh.msh)."""
    from ..config import load_config
    from ..design.space import DesignSpace
    from ..types import Design
    p = Path(source)
    if p.is_file() and p.suffix.lower() in (".yaml", ".yml"):
        cfg = load_config(p)
        d = DesignSpace.from_config(cfg).seed
        return cfg, d, f"{cfg.name}-seed", None, "config"
    if not p.is_dir():
        raise FileNotFoundError(f"{p} is neither a config YAML nor a run / design directory")
    run_dir, mesh_path, want_hash = p, None, design_hash
    if (p / "mesh.msh").exists() and p.parent.name == "designs":
        run_dir, mesh_path, want_hash = p.parent.parent, p / "mesh.msh", p.name
    cfg_path = Path(config) if config else run_dir / "config.yaml"
    if not cfg_path.exists():
        raise FileNotFoundError(f"no config for {p}: pass --config (looked for {cfg_path})")
    cfg = load_config(cfg_path)
    rows = [r for r in _rows(run_dir) if r.get("ok")]
    pick = None
    if want_hash:
        pick = next((r for r in rows if r.get("design_hash") == want_hash), None)
        if pick is None:
            best = _read_json(run_dir / "best.json")
            if best and best.get("design_hash") == want_hash:
                pick = best
    else:
        seen, ranked = set(), []
        for r in sorted(rows, key=lambda r: r["objective"]):
            if r["design_hash"] not in seen:
                seen.add(r["design_hash"])
                ranked.append(r)
        if ranked and 0 <= rank < len(ranked):
            pick = ranked[rank]
        elif rank == 0:
            pick = _read_json(run_dir / "best.json")
    if not pick:
        raise ValueError(f"could not find a design in {run_dir} (hash={want_hash!r}, rank={rank}); "
                         "pass --design-hash or check that the run finished")
    design = Design(pick["family"], dict(pick["params"]))
    h = design.hash()
    if mesh_path is None:
        cand = run_dir / "designs" / h / "mesh.msh"
        mesh_path = cand if cand.exists() else None
    return cfg, design, f"{cfg.name}-{h}", mesh_path, ("design" if mesh_path else "run")


def _read_json(path: Path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


# ------------------------------------------------------------------ the reference solve

def load_mesh_result(msh_path, quadrants: str):
    """``MeshResult`` for an existing .msh (no mesher needed). Runs the same unit and fundamental-domain guards."""
    from ..mesh import build as mesh_build, sizing
    path = Path(msh_path)
    summary, xyz, tri = mesh_build.read_msh_summary(path, return_arrays=True)
    mesh_build._check_bbox(summary["bbox_m"])
    from ..mesh import topology
    topology.check_surface(xyz, tri, sizing.SYMMETRY_PLANE[quadrants])
    from ..types import MeshResult
    return MeshResult(path=str(path.resolve()), n_triangles=summary["n_triangles"], n_dof=None, quadrants=quadrants,
                      symmetry_plane=sizing.SYMMETRY_PLANE[quadrants], res_mm={}, bbox_m=tuple(summary["bbox_m"]),
                      seconds=0.0), summary


def make_solve_spec(cfg, freqs_hz, *, angle_count: int, balloon_points: int, distance_m: float | None = None,
                    mode: str = "final"):
    """The production ``solve_spec`` with ONLY the frequency list and the observation sampling replaced."""
    from .. import config as config_mod
    base = config_mod.solve_spec(mode, cfg)
    obs = dataclasses.replace(base.observation, angle_count=int(angle_count),
                              balloon=bool(balloon_points > 0), balloon_points=int(balloon_points),
                              distance_m=float(distance_m) if distance_m else base.observation.distance_m)
    return dataclasses.replace(base, freqs_hz=tuple(float(f) for f in freqs_hz), observation=obs)


def refuse_unsupported(cfg) -> None:
    """The A/B check is for ordinary single-source designs (one driven surface, tag 2)."""
    from ..search.evaluate import meh_block_of
    if meh_block_of(cfg) is not None:
        raise ValueError("multi-source (MEH) configs are not supported by the Boundary Lab A/B check: it compares one "
                         "driven surface (tag 2). Use a single-source config of the same horn.")


def solve_reference(*, cfg, design, out_dir, freqs_hz, angle_count: int = DEFAULT_ANGLE_COUNT,
                    balloon_points: int = DEFAULT_BALLOON_POINTS, distance_m: float | None = None,
                    mesh_path=None, quadrants: str | None = None, backend=None, max_dof: int | None = None,
                    dry_run: bool = False, build_mesh_fn=None, label: str = "hornfab", extra_meta: dict | None = None):
    """Mesh (or reuse ``mesh_path``) -> solve every frequency -> durable ``out_dir``.

    Writes ``response.npz`` (full ``Response`` incl. complex pressure; solve-cache layout), ``reference_meta.json``
    and ``abdata/`` (canonical form). Uses ``config.solve_spec`` and the backend's own ``solve`` - nothing is
    re-implemented. ``dry_run`` stops after the mesh and returns the estimate.

    * ``mesh_path`` given: that exact mesh, solved with ``quadrants`` ("1234" for the BL handoff mesh).
    * otherwise the production mesher builds the reduced mesh for ``cfg.mesh.quadrants`` at ``max(freqs)``.
    """
    from .. import config as config_mod
    from ..mesh import sizing
    refuse_unsupported(cfg)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    freqs = tuple(float(f) for f in freqs_hz)
    sspec = make_solve_spec(cfg, freqs, angle_count=angle_count, balloon_points=balloon_points,
                            distance_m=distance_m)
    if mesh_path is not None:
        q = quadrants or "1234"
        mesh, summary = load_mesh_result(mesh_path, q)
        n_nodes = int(summary["n_nodes_used"])
        est_dof = max(n_nodes, sizing.estimate_dofs(mesh.n_triangles, q, float(cfg.mesh.dof_per_triangle)))
        mesh_info = {"path": str(mesh.path), "source": "existing", "n_triangles": mesh.n_triangles,
                     "n_nodes_used": n_nodes, "est_dof": int(est_dof), "quadrants": q}
    else:
        build = build_mesh_fn
        if build is None:
            from ..mesh.build import build_mesh as build
        mspec = dataclasses.replace(config_mod.mesh_spec("final", cfg), f_max_hz=float(max(freqs)))
        if max_dof:
            mspec = dataclasses.replace(
                mspec, max_triangles=sizing.max_triangles_for(
                    int(max_dof), mspec.quadrants, cfg.mesh.dof_per_triangle, cfg.mesh.max_triangle_slack))
            cfg = dataclasses.replace(cfg, mesh=dataclasses.replace(cfg.mesh, dof_cap_final=int(max_dof)))
        mesh = build(design, mspec, cfg, out_dir / "mesh", mode="final")
        est_dof = sizing.estimate_dofs(mesh.n_triangles, mesh.quadrants, float(cfg.mesh.dof_per_triangle))
        mesh_info = {"path": str(mesh.path), "source": "built", "n_triangles": mesh.n_triangles,
                     "est_dof": int(est_dof), "quadrants": mesh.quadrants, "res_mm": dict(mesh.res_mm)}
    if mesh_path is not None and max_dof and est_dof > int(max_dof):
        raise ValueError(
            f"the mesh has ~{est_dof} dofs, over --max-dof {max_dof}. Options: solve the symmetric reduced mesh (--symmetric), "
            f"export a smaller mesh (lower --hi-hz / --mesh-f-max), or use the CPU backend which has no VRAM limit "
            f"(`ab-bl --backend beat_cpu solve --max-dof N`, roughly a minute per frequency above 9k dofs). Raise --max-dof on the "
            f"GPU only after checking VRAM (TOOLCHAIN.md: full-domain ceiling is about 5.5k dofs on the 8 GB card).")
    from ..cli import estimate_seconds_per_frequency
    est_s = estimate_seconds_per_frequency(est_dof) * len(freqs)
    report = {"n_freqs": len(freqs), "f_lo_hz": freqs[0], "f_hi_hz": freqs[-1], "est_dof": int(est_dof),
              "est_solve_minutes": est_s / 60.0, "mesh": mesh_info}
    if dry_run:
        return None, report
    if backend is None:
        raise ValueError("solve_reference needs a backend unless dry_run=True")
    t0 = time.perf_counter()
    outcome = backend.solve(mesh, sspec)
    if not outcome.ok or outcome.response is None:
        raise RuntimeError(f"reference solve failed: {outcome.message}")
    resp = outcome.response
    from ..solve import cache as solve_cache
    solve_cache.save_response(out_dir / REFERENCE_FILE, resp)
    meta = {"label": label, "design_hash": design.hash(), "family": design.family, "params": design.params,
            "config_name": getattr(cfg, "name", None), "mode": "ab_reference",
            "freqs_hz": list(freqs), "angle_count": int(angle_count), "balloon_points": int(balloon_points),
            "distance_m": float(sspec.observation.distance_m), "backend": sspec.backend,
            "gmres_tol": sspec.gmres_tol, "mesh": mesh_info, "quadrants": mesh_info["quadrants"],
            "rho": RHO_AIR, "sound_speed": C_AIR, "mesh_scale": 1.0,
            "source_motion": str((sspec.extra or {}).get("source_motion", "normal")),
            "solve_seconds": time.perf_counter() - t0, "peak_vram_mb": outcome.peak_vram_mb,
            "n_dof": resp.n_dof, "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "spl_reference": "absolute dB re 20 uPa for UNIT NORMAL ACCELERATION of tag 2 (Hornfab native); "
                             "abdata/ holds the 1 m/s velocity, exp(+i w t) form used for the A/B compare"}
    meta.update(extra_meta or {})
    (out_dir / REFERENCE_META).write_text(json.dumps(meta, indent=2, sort_keys=True, default=float), encoding="utf-8")
    ab = from_response(resp, label=label, meta={k: meta[k] for k in ("distance_m", "design_hash", "family", "quadrants",
                                                                        "source_motion") if k in meta})
    ab.meta["reference_meta"] = meta
    ab.save(out_dir / "abdata")
    report["solve_seconds"] = meta["solve_seconds"]
    return resp, report
