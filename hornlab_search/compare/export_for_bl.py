"""Write the "BL handoff" folder: everything a friend needs to solve ONE Hornfab design in Boundary Lab.

The folder is self-contained and uses only facts read from Boundary Lab's own docs and source
(docs/ab/BOUNDARY_LAB_AB.md section "What is verified"). Nothing here imports Boundary Lab.

Layout (``<workspace>/bl_handoff``)::

    FOR_YOUR_FRIEND.md          click-by-click steps + exactly which files to send back
    handoff.json                machine-readable: design, mesh (sha256, tag areas), frequencies, observation, conventions
    horn.blab.json              ready-to-open Boundary Lab project (schema 10, exterior BEM, metres, symmetry off)
    horn_symmetric.blab.json    same horn on the reduced mesh with Boundary Lab's own X/XY symmetry (smaller, faster) [if any]
    request.json                headless overlay (exact frequency list)      [optional route B]
    request_float64.json        same, double precision                       [optional]
    frequencies_hz.txt          one frequency per line
    mesh/horn_full_m.msh        FULL mesh (no symmetry), METRES, tags SD1G0=1 rigid / SD1D1001=2 driven
    mesh/hornfab_native_*.msh   the exact mesh Hornfab solved (reduced if Hornfab used symmetry)
    results_from_friend/        EMPTY drop folder: polar/, on_axis/, balloon/, impedance/, headless_run/
"""
from __future__ import annotations

import hashlib
import json
import shutil
import time
from pathlib import Path

import numpy as np

from ..constants import C_AIR, RHO_AIR
from ..mesh import sizing
from . import hornfab_side as hs
from .mshio import Mesh, blab_symmetry, mirror_to_full, read_msh, write_msh

SOURCE_TAG = 2                      # SD1D1001: the driven surface (mesher PRIMARY_SOURCE)
RIGID_TAG = 1                       # SD1G0
SOURCE_NAME = "SD1D1001"
RIGID_NAME = "SD1G0"
BL_SCHEMA_VERSION = 10              # tests/fixtures/remote-exterior.blab.json in Boundary Lab, physical model v1
BL_PIN = "JWSound/boundary-lab main 15f9a89 (2026-11-02), pyproject says version 0.5.0 and BEAT Engine 0.7.0"


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def balloon_angle_for_points(n_points: int) -> float:
    """BL derives its Fibonacci count as ``round(41253 / a^2)`` with ``a`` clamped to 0.5..15 degrees."""
    a = float(np.sqrt(41253.0 / max(int(n_points), 1)))
    return float(min(max(a, 0.5), 15.0))


def bl_balloon_count(angle_deg: float) -> int:
    a = min(max(float(angle_deg), 0.5), 15.0)
    return max(int(round(41253.0 / a ** 2)), 1)


def mesh_quality(mesh: Mesh, epw: float | None) -> dict:
    e = mesh.edge_lengths()
    out = {"edge_max_m": float(e.max()), "edge_p95_m": float(np.percentile(e, 95)), "edge_mean_m": float(e.mean())}
    if epw:
        out["epw_assumed"] = float(epw)
        out["f_valid_p95_hz"] = float(C_AIR / (epw * out["edge_p95_m"]))
        out["f_valid_max_edge_hz"] = float(C_AIR / (epw * out["edge_max_m"]))
    return out


def blab_project(*, mesh_file: str, name: str, freqs_hz, distance_m: float, angle_step_deg: float,
                 balloon_angle_deg: float, symmetry: str = "off", spl_min_db: float = -90.0,
                 spl_max_db: float = 30.0) -> dict:
    """Boundary Lab ``.blab.json`` (schema 10) for an exterior BEM model: ``bem_surface`` mesh in METRES, one
    ``unbounded_air`` region, rigid wall + ``moving`` source boundary, an ``ideal_velocity_source`` with a
    ``normal_velocity`` port. Keys follow tests/fixtures/remote-exterior.blab.json (verified) plus the GUI keys of
    examples/Simple_Sealed (imported_meshes, project_preferences, component_channel_by_id)."""
    f = [float(x) for x in freqs_hz]
    lo, hi = int(round(f[0])), int(round(f[-1]))
    if abs(lo - f[0]) > 1e-6 or abs(hi - f[-1]) > 1e-6:
        raise ValueError(f"Boundary Lab's GUI takes integer freq_min/freq_max; got {f[0]} - {f[-1]} Hz. "
                         "Use a grid whose end points are whole Hz (default 100 - 20000).")
    mesh_id = "mesh:exterior"
    system = {
        "id": "system:hornfab-ab", "name": name,
        "meshes": [{"id": mesh_id, "name": "Exterior", "file": mesh_file, "purpose": "bem_surface",
                    "scale_to_m": 1.0, "translation_m": [0.0, 0.0, 0.0]}],
        "regions": [{"id": "region:exterior", "name": "Exterior", "kind": "unbounded_air", "mesh_ids": [mesh_id],
                     "volume_groups": [], "sound_speed_m_per_s": C_AIR, "density_kg_per_m3": RHO_AIR,
                     "loss_model": {}}],
        "boundaries": [
            {"id": "boundary:rigid", "name": "Horn wall", "kind": "rigid", "region_id": "region:exterior",
             "group": {"mesh_id": mesh_id, "dimension": 2, "tag": RIGID_TAG, "name": RIGID_NAME}, "parameters": {}},
            {"id": "boundary:source", "name": "Throat source", "kind": "moving", "region_id": "region:exterior",
             "group": {"mesh_id": mesh_id, "dimension": 2, "tag": SOURCE_TAG, "name": SOURCE_NAME}, "parameters": {}},
        ],
        "interfaces": [],
        "components": [{"id": "component:source", "name": "Throat source", "kind": "ideal_velocity_source",
                        "boundary_ids": ["boundary:source"], "parameters": {}}],
        "excitation_ports": [{"id": "excitation:source", "name": "Throat source", "component_id": "component:source",
                              "kind": "normal_velocity"}],
        "model_version": 1,
    }
    return {
        "schema_version": BL_SCHEMA_VERSION,
        "generator_documents": [],
        "active_generator_document_id": None,
        "imported_meshes": [{"name": "Exterior", "source_file": mesh_file, "cleaned_file": None, "scale_factor": 1.0,
                             "translation_mm": [0, 0, 0], "enabled": True}],
        "stitch_exterior_meshes": False,
        "physical_system": system,
        "component_channel_by_id": {"component:source": "main"},
        "channel_config_by_name": {"main": {"delay_ms": 0.0, "hpf": {}, "level_db": 0.0, "lpf": {}, "polarity": 1}},
        "symmetry": symmetry,
        "project_preferences": {
            "freq_min_hz": lo, "freq_max_hz": hi, "freq_count": len(f),
            "polar_angle_step_deg": float(angle_step_deg), "polar_observation_distance_m": float(distance_m),
            # Without this BL divides each channel by its on-axis magnitude (flat target) BEFORE export, which
            # would flatten the very response we want to compare. channel_synthesis.flat_target_corrections.
            "normalized_channel_correction": False,
            "polar_smoothing": None,
            "horizontal_normalization_angle": 0.0, "vertical_normalization_angle": 0.0,
            "spin_horizontal_reference_angle": 0.0, "spin_vertical_reference_angle": 0.0,
            # exports clip to this range (Preferences: SPL Min/Max): keep it wide so DI is not biased
            "spl_max_db": float(spl_max_db), "spl_min_db": float(spl_min_db),
            "isobar_contour_step_db": 3.0, "stitch_tolerance_mm": 2.0,
            "spherical_sampling_enabled": True, "balloon_angle_precision_deg": float(balloon_angle_deg),
        },
    }


def overlay_request(freqs_hz, *, float64: bool = False) -> dict:
    out = {"schema_version": 1, "frequencies_hz": [float(x) for x in freqs_hz], "include_project_observations": True}
    if float64:
        out["solver_options"] = {"precision": "float64"}
    return out


def friend_markdown(h: dict) -> str:
    f = h["frequencies"]
    o = h["observation"]
    lines = f"""# Boundary Lab check: please solve this one horn and send back the result files

Thank you. This takes about 15 minutes of clicking plus the solve time. You do not need to understand the horn.
Nothing here needs programming. If a step does not look like what is written, take a screenshot and send it with
the results: that is useful too.

**What this is.** A horn designed in Hornfab was already solved there. We want to see whether Boundary Lab
(BEAT Engine) gives the same answer for the *same mesh*. Design `{h['design']['label']}`, mesh
`mesh/horn_full_m.msh` ({h['mesh']['n_triangles']} triangles, about {h['mesh']['approx_p1_dofs']} unknowns).
The mesh is **in metres** and is a **full mesh (no symmetry)**, so please leave symmetry **Off**.

## Before you start (2 minutes)
1. Copy this whole folder somewhere on your disk (not a zip you opened in place).
2. Use a Boundary Lab version you trust and write down its version (Help > About) and which BEM solver you use
   (CPU or Nvidia CUDA). We pinned our notes to: {BL_PIN}.
3. Make sure no other heavy GPU program is running. A full-band solve of this size can take a long time on the CPU;
   if your GPU runs out of memory, tell us, and do not change the mesh.

## Route A: Boundary Lab window (recommended)
1. **File > Open Project...** and choose `horn.blab.json` from this folder.
2. Open **Edit > Preferences** and check these numbers (the project file sets them, Boundary Lab may ask whether to
   apply them: say yes):
   - Frequency: min **{f['lo_hz']:g}** Hz, max **{f['hi_hz']:g}** Hz, count **{f['count']}** (log spaced).
   - Polar Angle Step **{o['polar_step_deg']:g}** degrees. Polar Observation Distance **{o['distance_m']:g}** m.
   - **Normalized Channel Correction: OFF** (very important: when it is on, Boundary Lab flattens the on-axis
     response before exporting and our comparison would be meaningless).
   - Horizontal and Vertical Normalization Angle **0**. SPL Min **-90**, SPL Max **30**.
   - **Balloon Sampling: ON**, Balloon Angle Precision **{o['balloon_angle_deg']:.3g}** degrees (about {o['balloon_points_bl']} points).
3. In the mesh window (**Meshes**) check there is one mesh, scale **1** (metres), and symmetry is **Off**. In the
   3D view the horn is grey with a blue disc at the throat. If the horn looks 1000 times too small or too big, stop:
   the scale is wrong. Tell us.
4. Choose your BEM solver in Preferences and press **Solve**. Wait until all {f['count']} frequencies are done.
5. Export (all into the folders named below, inside `results_from_friend/`):
   - **File > Export Polar Data** -> pick `results_from_friend/polar/` (it writes many files named like `H 0.txt`, `V 15.txt`).
     Tick phase if it asks.
   - **File > Export On-Axis Data** -> save as `results_from_friend/on_axis/on_axis.txt`.
   - **File > Export Balloon Data** -> pick `results_from_friend/balloon/` (writes `metadata.json`, `topology.npz`,
     `spl_db.npy`, `radius_norm.npy`).
   - **Acoustic Impedance** panel (View menu): use its save/export data button (if there is one) and save as
     `results_from_friend/impedance/impedance.txt`. If your version has no data export for this panel, take a
     screenshot of the panel instead and put it in the same folder. (This step is optional.)
6. Write a short `results_from_friend/NOTES.txt`: Boundary Lab version, solver (CPU/CUDA), computer, anything odd.
7. Zip the whole `results_from_friend/` folder and send it back.

## If the full project is too slow or runs out of memory
Open `horn_symmetric.blab.json` instead (same horn, same nodes, but only one quarter of the mesh and Boundary Lab's own
X/Y symmetry already set; check **Meshes: symmetry XY**). Tell us which project you used. Everything else is identical.

## Route B: command line (only if you are comfortable with it; gives the cleanest data)
From the Boundary Lab environment:
```
blab project validate horn.blab.json --json
blab project solve horn.blab.json --request request.json --backend beat_cuda --output results_from_friend/headless_run
```
(`--backend beat_cpu` if you have no Nvidia GPU. The output folder must not exist yet.) Then zip
`results_from_friend/` and send it. This writes raw complex pressure and the radiation impedance, so nothing is
clipped or normalized. Doing Route A as well is welcome but not required.

## What we will check, so you know what matters
- Frequency response on axis and at 15, 30, 45, 60, 90 degrees; horizontal and vertical polar maps; balloon and DI;
  beam width; throat impedance if your version exports it.
- Please do NOT change: mesh, scale, symmetry, frequencies, observation radius, the source (1 m/s normal velocity on
  the blue throat disc).

## Decisions only you can make (tell us what you chose in NOTES.txt)
- CPU or CUDA solver. Single or double precision (default single is fine).
- If Boundary Lab shows a warning about the mesh (open edges, tiny elements), do not repair it: send the warning text.
"""
    return lines


def export_for_bl(source, out_dir, *, config=None, design_hash: str | None = None, rank: int = 0,
                  lo_hz: float = hs.DEFAULT_LO_HZ, hi_hz: float | None = None,
                  points_per_octave: float = hs.DEFAULT_PPO, angle_count: int = hs.DEFAULT_ANGLE_COUNT,
                  balloon_points: int = hs.DEFAULT_BALLOON_POINTS, distance_m: float | None = None,
                  rebuild_mesh: bool = False, mesh_f_max_hz: float | None = None, max_dof: int | None = None,
                  keep_symmetry: bool = False, build_mesh_fn=None, mesh_path=None, quadrants: str | None = None,
                  cfg=None, design=None, label: str | None = None) -> dict:
    """Create ``out_dir`` (the handoff folder) and return the manifest dict (also written as handoff.json).

    ``hi_hz`` None = automatic: 20 kHz capped at what the mesh resolves (6 elements per wavelength at the p95 edge, rounded
    down to 100 Hz), or at ``mesh_f_max_hz`` when the mesh is rebuilt. Boundary Lab's GUI needs whole-Hz end points.

    ``source``: config YAML (seed design), run dir (``design_hash`` or ``rank``) or design dir. The mesh is the design's
    existing ``mesh.msh`` unless ``rebuild_mesh`` (needs the mesher): then it is rebuilt for ``mesh_f_max_hz`` (default
    ``hi_hz``) with the production mesher. A reduced mesh is mirrored to a FULL mesh unless ``keep_symmetry``.
    ``cfg``/``design``/``mesh_path``/``quadrants`` may be passed directly (tests, library use) instead of ``source``.
    """
    out = Path(out_dir)
    cfg_path = Path(config) if config else None
    if cfg_path is None and source is not None:
        sp = Path(source)
        if sp.is_file():
            cfg_path = sp
        elif sp.is_dir():
            run_dir = sp.parent.parent if ((sp / "mesh.msh").exists() and sp.parent.name == "designs") else sp
            cfg_path = run_dir / "config.yaml"
    if cfg is None or design is None:
        cfg, design, lab, found_mesh, kind = hs.resolve_source(source, config=config, design_hash=design_hash,
                                                               rank=rank)
        label = label or lab
        mesh_path = mesh_path or found_mesh
    else:
        label = label or f"{getattr(cfg, 'name', 'design')}-{design.hash()}"
        kind = "given"
    hs.refuse_unsupported(cfg)
    (out / "mesh").mkdir(parents=True, exist_ok=True)
    (out / "results_from_friend").mkdir(parents=True, exist_ok=True)
    for sub in ("polar", "on_axis", "balloon", "impedance", "headless_run"):
        (out / "results_from_friend" / sub).mkdir(exist_ok=True)

    work_q = quadrants or cfg.mesh.quadrants
    if rebuild_mesh:
        import dataclasses
        from .. import config as config_mod
        build = build_mesh_fn
        if build is None:
            from ..mesh.build import build_mesh as build
        mspec = dataclasses.replace(config_mod.mesh_spec("final", cfg),
                                    f_max_hz=float(mesh_f_max_hz or hi_hz))
        if max_dof:
            mspec = dataclasses.replace(mspec, max_triangles=sizing.max_triangles_for(
                int(max_dof), mspec.quadrants, cfg.mesh.dof_per_triangle, cfg.mesh.max_triangle_slack))
            cfg = dataclasses.replace(cfg, mesh=dataclasses.replace(cfg.mesh, dof_cap_final=int(max_dof)))
        built = build(design, mspec, cfg, out / "_mesh_build", mode="final")
        mesh_path, work_q = Path(built.path), built.quadrants
    elif mesh_path is None:
        raise ValueError("no existing mesh.msh for this design: pass --rebuild-mesh (needs the mesher) "
                         "or point at a design folder that holds mesh.msh")
    else:
        meta = hs._read_json(Path(mesh_path).parent / "mesh_meta.json")
        if meta and not quadrants:
            work_q = (meta.get("result") or {}).get("quadrants") or work_q

    native = read_msh(mesh_path)
    bb = native.bbox()
    extent = max(bb[3] - bb[0], bb[4] - bb[1], bb[5] - bb[2])
    if not 0.02 <= extent <= 5.0:
        raise ValueError(f"mesh bounding box {extent:.4g} m is outside 0.02-5 m: units are not metres (silent killer 1)")
    if SOURCE_TAG not in native.phys:
        raise ValueError(f"mesh has no triangles on tag {SOURCE_TAG} ({SOURCE_NAME}); tags present: "
                         f"{sorted(set(native.phys.tolist()))}")
    unknown = sorted(set(native.phys.tolist()) - {RIGID_TAG, SOURCE_TAG})
    if unknown:
        raise ValueError(f"unknown physical group(s) {unknown} in the mesh: Boundary Lab needs a role for every group; "
                         "this exporter only knows SD1G0 (rigid) and SD1D1001 (driven)")
    names = {RIGID_TAG: RIGID_NAME, SOURCE_TAG: SOURCE_NAME}
    native.names = {**native.names, **{t: n for t, n in names.items() if t in set(native.phys.tolist())}}

    full = native if keep_symmetry else mirror_to_full(native, work_q)
    symmetry = blab_symmetry(work_q) if keep_symmetry else "off"
    full.names = dict(native.names)
    q_tag = work_q if work_q else "1234"
    native_copy = out / "mesh" / f"hornfab_native_q{q_tag}.msh"
    shutil.copyfile(mesh_path, native_copy)
    mesh_file = "mesh/horn_full_m.msh"
    write_msh(full, out / mesh_file)

    epw = getattr(cfg.mesh, "epw", None)
    quality = mesh_quality(full, epw)
    if hi_hz is None:
        cap = float(mesh_f_max_hz) if (rebuild_mesh and mesh_f_max_hz) else quality.get("f_valid_p95_hz", hs.DEFAULT_HI_HZ)
        hi_hz = float(min(hs.DEFAULT_HI_HZ, max(np.floor(cap / 100.0) * 100.0, 2.0 * lo_hz)))
    freqs = hs.reference_freqs(lo_hz, hi_hz, points_per_octave)
    (out / "frequencies_hz.txt").write_text("\n".join(f"{x:.2f}" for x in freqs) + "\n", encoding="utf-8")
    dist = float(distance_m or cfg.solve.distance_m)
    step = 180.0 / (int(angle_count) - 1)
    a_bl = balloon_angle_for_points(balloon_points)
    project = blab_project(mesh_file=mesh_file, name=f"Hornfab A/B {label}", freqs_hz=freqs, distance_m=dist,
                           angle_step_deg=step, balloon_angle_deg=a_bl, symmetry=symmetry)
    (out / "horn.blab.json").write_text(json.dumps(project, indent=2), encoding="utf-8")
    sym_alt = None
    if not keep_symmetry:
        try:
            sym_alt = blab_symmetry(work_q)
        except ValueError:
            sym_alt = None
    if sym_alt not in (None, "off"):
        alt = blab_project(mesh_file=f"mesh/{native_copy.name}", name=f"Hornfab A/B {label} (symmetric)", freqs_hz=freqs,
                           distance_m=dist, angle_step_deg=step, balloon_angle_deg=a_bl, symmetry=sym_alt)
        (out / "horn_symmetric.blab.json").write_text(json.dumps(alt, indent=2), encoding="utf-8")
    (out / "request.json").write_text(json.dumps(overlay_request(freqs), indent=2), encoding="utf-8")
    (out / "request_float64.json").write_text(json.dumps(overlay_request(freqs, float64=True), indent=2),
                                              encoding="utf-8")

    areas = full.tag_areas()
    nat_areas = native.tag_areas()
    q_factor = sizing.QUADRANT_FACTOR.get(work_q, 1)
    n_nodes_full = int(np.unique(full.tri).size)
    manifest = {
        "format": 1, "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "design": {"label": label, "design_hash": design.hash(), "family": design.family, "params": design.params,
                   "config_name": getattr(cfg, "name", None), "source_kind": kind,
                   "config_path": None if cfg_path is None else str(Path(cfg_path).resolve()),
                   "source": None if source is None else str(Path(source).resolve())},
        "mesh": {
            "file": mesh_file, "sha256": sha256_file(out / mesh_file), "units": "metres", "scale_to_m": 1.0,
            "symmetry_in_blab": symmetry, "symmetric_alternative": None if sym_alt in (None, "off") else
            {"project": "horn_symmetric.blab.json", "mesh": f"mesh/{native_copy.name}", "blab_symmetry": sym_alt}, "n_triangles": int(full.tri.shape[0]), "n_nodes": n_nodes_full,
            "approx_p1_dofs": n_nodes_full, "bbox_m": list(full.bbox()),
            "tags": {str(t): n for t, n in names.items()},
            "driven_tag": SOURCE_TAG, "driven_name": SOURCE_NAME,
            "driven_area_m2_full": areas.get(SOURCE_TAG), "driven_area_m2_native": nat_areas.get(SOURCE_TAG),
            "tag_areas_m2_full": {str(k): v for k, v in areas.items()},
            "native": {"file": f"mesh/{native_copy.name}", "sha256": sha256_file(native_copy),
                       "quadrants": work_q, "solver_symmetry_plane": sizing.SYMMETRY_PLANE.get(work_q),
                       "quadrant_factor": q_factor, "n_triangles": int(native.tri.shape[0])},
            "quality": quality,
            "winding_note": "reflected copies have their winding reversed so outward normals stay outward",
        },
        "source": {"kind": "ideal normal velocity on tag 2", "amplitude": "1 m/s (Boundary Lab normal_velocity basis)",
                   "hornfab_drive": "unit normal ACCELERATION on tag 2 (docs/plan, Collin Q #10)",
                   "relation": "|p(1 m/s)| = 2 pi f |p(unit accel)|, i.e. +20 log10(2 pi f) dB",
                   "time_convention": {"boundary_lab": "exp(+i omega t)", "hornfab_native": "exp(-i omega t)"},
                   "phase_note": "convert by complex conjugation; BL on-axis phase has the propagation delay r/c removed",
                   "motion": "normal to the surface (Hornfab source_motion 'normal'; BL ideal_velocity_source default)"},
        "frequencies": {"lo_hz": freqs[0], "hi_hz": freqs[-1], "count": len(freqs), "points_per_octave": points_per_octave,
                        "list_file": "frequencies_hz.txt", "grid": "geomspace(lo, hi, count), rounded to 0.01 Hz",
                        "freqs_hz": list(freqs)},
        "observation": {"distance_m": dist, "polar_step_deg": step, "angle_count": int(angle_count),
                        "angles_deg": f"-90..+90 step {step:g} (BL writes -180..+180; the importer crops)",
                        "h_plane": "XZ (x = r sin a, z = r cos a), +angle toward +X",
                        "v_plane": "YZ (y = r sin a, z = r cos a), +angle toward +Y",
                        "balloon_points_hornfab": int(balloon_points), "balloon_angle_deg": a_bl,
                        "balloon_points_bl": bl_balloon_count(a_bl),
                        "balloon_layout": {"hornfab": "theta-phi grid (weight sin theta)",
                                           "boundary_lab": "Fibonacci sphere (equal area)"},
                        "direction_convention": "+Z forward, theta from +Z, phi from +X toward +Y (both tools)"},
        "material": {"rho_hornfab": RHO_AIR, "rho_boundary_lab_default": 1.21, "c": C_AIR,
                     "project_region_density_kg_m3": RHO_AIR,
                     "note": "the .blab.json sets the exterior region to Hornfab's rho and c; if the friend rebuilds the model by hand "
                             "Boundary Lab's default 1.21 applies and p changes by 20 log10(1.21/1.204) = 0.043 dB (harmless)"},
        "boundary_lab_notes": {"pinned_to": BL_PIN,
                               "project_schema": BL_SCHEMA_VERSION,
                               "verified": ["fixture schema 10 keys", "polar/on-axis/balloon export formats",
                                            "headless run folder layout", "phasor exp(+i omega t)", "polar H=XZ, V=YZ"],
                               "inferred": ["GUI opens this generated .blab.json without edits", "impedance dock text export"]},
        "workspace_hint": "run `hornlab-search ab-bl compare --workspace <parent of this folder>` after the results arrive",
    }
    (out / "handoff.json").write_text(json.dumps(manifest, indent=2, default=float), encoding="utf-8")
    (out / "FOR_YOUR_FRIEND.md").write_text(friend_markdown(manifest), encoding="utf-8")
    (out / "results_from_friend" / "README.txt").write_text(
        "Put Boundary Lab's exports here:\n  polar/       File > Export Polar Data\n  on_axis/     File > Export On-Axis Data\n"
        "  balloon/     File > Export Balloon Data\n  impedance/   impedance export or screenshot (optional)\n"
        "  headless_run/ the output folder of `blab project solve` (optional, best data)\n  NOTES.txt    version, solver, anything odd\n",
        encoding="utf-8")
    shutil.rmtree(out / "_mesh_build", ignore_errors=True)
    return manifest
