"""Horn + woofer system views for the GUI (G0) — read-only, no solver, no Boundary Lab import.

Reads the isolated system store (``<root>/system_runs/system/<experiment>/<case>/``) and the
committed registry ``docs/research/system_woofer_2026-11-18/readiness.yaml``.

What comes from where (never mixed):

* **Facts** — staged / validated / solved / refused, box dimensions, horn offset, clearance,
  frequency grid, per-excitation references — are read from the case dirs (integrity-checked
  manifests, BL headless results via ``bl_results.read_bl_headless_result``).
* **Declarations** — fidelity label, real-vs-demo motor and transducer shape, gate name — come
  only from the registry. A case missing from it is shown ``UNDECLARED``; nothing is inferred.

No endpoint sums channels: woofer bases are Pa per 2.83 V, horn bases Pa per 1 m/s, and the
system has no accepted calibration policy yet (risk R1). Mesh files are read only when they
resolve inside the store, so a manifest cannot point the GUI at an arbitrary file.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

import numpy as np

REGISTRY_REL = Path("docs/research/system_woofer_2026-11-18/readiness.yaml")
_KEY_PART = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,120}$")
_P_REF = 20e-6                                        # Pa, dB SPL reference
_CACHE: dict[tuple, Any] = {}
_CACHE_MAX = 64


# --------------------------------------------------------------------------- paths & cache

def store_dir(store: Path) -> Path:
    return (Path(store) / "system").resolve()


def _resolve_case(store: Path, key: str) -> Path:
    parts = str(key).strip("/").split("/")
    if len(parts) != 2 or not all(_KEY_PART.match(p) and ".." not in p for p in parts):
        raise ValueError(f"bad case key {key!r}: expected <experiment>/<case>")
    base = store_dir(store)
    case = (base / parts[0] / parts[1]).resolve()
    if base not in case.parents or not case.is_dir():
        raise FileNotFoundError(key)
    return case


def _inside(store: Path, path: str | Path | None) -> Path | None:
    """The resolved path when it is an existing file inside the store, else None."""
    if not path:
        return None
    p = Path(path).resolve()
    root = Path(store).resolve()
    return p if root in p.parents and p.is_file() else None


def _cached(key: tuple, fn):
    if key in _CACHE:
        return _CACHE[key]
    value = fn()
    if len(_CACHE) >= _CACHE_MAX:
        _CACHE.pop(next(iter(_CACHE)))
    _CACHE[key] = value
    return value


def _stamp(p: Path) -> tuple:
    st = p.stat()
    return (str(p), st.st_mtime_ns, st.st_size)


# --------------------------------------------------------------------------- registry

def load_registry(root: Path) -> dict[str, Any]:
    path = Path(root) / REGISTRY_REL
    if not path.is_file():
        return {"schema": None, "cases": [], "risks": [], "decisions": [],
                "error": f"registry not found: {REGISTRY_REL.as_posix()}"}

    def read():
        import yaml
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if data.get("schema") != "hw_readiness_v1":
            raise ValueError(f"{REGISTRY_REL.as_posix()}: schema must be hw_readiness_v1")
        return _plain(data)
    return _cached(("registry",) + _stamp(path), read)


def _plain(x: Any) -> Any:
    """YAML dates/datetimes -> ISO strings, so every registry value is JSON-serialisable."""
    import datetime as _dt
    if isinstance(x, dict):
        return {str(k): _plain(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_plain(v) for v in x]
    if isinstance(x, (_dt.date, _dt.datetime)):
        return x.isoformat()
    return x


def _declared(registry: dict) -> dict[str, dict]:
    return {str(c.get("key")): dict(c) for c in registry.get("cases") or []}


# --------------------------------------------------------------------------- manifests

def _load_manifest(case: Path) -> tuple[dict, str]:
    """(payload, integrity) — integrity is "ok", "failed: …" or "missing"."""
    path = case / "manifest.json"
    if not path.is_file():
        return {}, "missing"
    from hornlab_search.system import provenance

    try:
        return dict(provenance.load_manifest(path)["payload"]), "ok"
    except Exception as exc:  # noqa: BLE001 - shown, never hidden
        try:
            raw = json.loads(path.read_text(encoding="utf-8")).get("payload") or {}
        except Exception:  # noqa: BLE001
            raw = {}
        payload = {}
        for k, v in raw.items():
            if isinstance(v, str) and v[:1] in "{[":
                try:
                    v = json.loads(v)
                except json.JSONDecodeError:
                    pass
            payload[k] = v
        return payload, f"failed: {type(exc).__name__}: {str(exc)[:160]}"


def _family(kind: str | None, experiment: str = "") -> str:
    k = kind or ""
    if not k and experiment.startswith("bl_"):
        return "bl_case"
    if k.startswith(("bl_", "boundarylab_")):
        return "generation" if k == "boundarylab_vented_generation" else "bl_case"
    if k.startswith("system_"):
        return "screen"
    return "other"


def _run_manifest(case: Path) -> dict | None:
    p = case / "run" / "manifest.json"
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {"status": "unreadable"}


def _parent_key(store: Path, payload: dict) -> str | None:
    """Solve-only manifests (smoke/wide) name the staged project they solved."""
    proj = payload.get("project")
    if not isinstance(proj, str):
        return None
    p = Path(proj).resolve()
    base = store_dir(store)
    if base not in p.parents:
        return None
    rel = p.parent.relative_to(base).parts
    return "/".join(rel[:2]) if len(rel) >= 2 else None


def _source_params(store: Path, payload: dict) -> tuple[dict | None, dict | None, str | None]:
    """(BL vented source parameters, horn spec, key they were read from)."""
    spec = payload.get("spec") if isinstance(payload.get("spec"), dict) else None
    if spec is not None:
        return spec.get("source"), spec.get("horn"), None
    parent = _parent_key(store, payload)
    if parent:
        try:
            pp, _ = _load_manifest(_resolve_case(store, parent))
        except (FileNotFoundError, ValueError):
            return None, None, parent
        ps = pp.get("spec") if isinstance(pp.get("spec"), dict) else {}
        return ps.get("source"), ps.get("horn"), parent
    return None, None, None


def _box(source: dict | None) -> dict | None:
    if not isinstance(source, dict) or "width_m" not in source:
        return None
    f = lambda k: source.get(k)  # noqa: E731
    area = f("port_area_m2")
    return {
        "width_mm": _mm(f("width_m")), "height_mm": _mm(f("height_m")), "depth_mm": _mm(f("depth_m")),
        "wall_mm": _mm(f("wall_m")),
        "driver_diameter_mm": _mm(f("driver_diameter_m")), "driver_y_mm": _mm(f("driver_y_m")),
        "port_area_cm2": None if area is None else round(float(area) * 1e4, 3),
        "port_length_mm": _mm(f("port_length_m")), "port_y_mm": _mm(f("port_y_m")),
        "port_nfr": f("port_nfr"),
        "mesh_size_mm": _mm(f("mesh_size_m")), "detail_size_mm": _mm(f("detail_size_m")),
    }


def _mm(v) -> float | None:
    return None if v is None else round(float(v) * 1000.0, 3)


# --------------------------------------------------------------------------- clearance

def _clearance(store: Path, case: Path, payload: dict, horn: dict | None, parent: str | None) -> dict | None:
    if not isinstance(horn, dict):
        return None
    rec = payload.get("clearance")
    if isinstance(rec, dict):
        return dict(rec, source="manifest")
    try:
        owner = case if parent is None else _resolve_case(store, parent)
    except (FileNotFoundError, ValueError):
        return {"status": "NOT_CHECKED", "source": "replay", "reason": f"parent case {parent} not found"}
    exteriors = sorted(owner.glob("bl_output/*/exterior.msh"))
    horn_mesh = _inside(store, horn.get("mesh_path"))
    if not exteriors or horn_mesh is None:
        return {"status": "NOT_CHECKED", "source": "replay",
                "reason": "staged meshes not on disk inside the store"}
    stamps = tuple(_stamp(p) for p in [horn_mesh, *exteriors])

    def run():
        from hornlab_search.system.boundarylab.clearance import body_clearance
        rep = body_clearance(horn_mesh, exteriors,
                             translation_mm=horn.get("translation_mm", (0, 0, 0)),
                             scale_factor=float(horn.get("scale_factor", 1.0)))
        return dict(rep.to_dict(), source="replay")
    try:
        return _cached(("clear",) + stamps + (tuple(horn.get("translation_mm", ())),), run)
    except Exception as exc:  # noqa: BLE001
        return {"status": "NOT_CHECKED", "source": "replay", "reason": f"{type(exc).__name__}: {exc}"}


# --------------------------------------------------------------------------- one row

def _state(case: Path, payload: dict, integrity: str, run: dict | None) -> dict:
    result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
    validate = payload.get("validate") if isinstance(payload.get("validate"), dict) else {}
    clear = payload.get("clearance") if isinstance(payload.get("clearance"), dict) else {}
    tokens: list[str] = []
    if integrity.startswith("failed"):
        tokens.append("MANIFEST_INTEGRITY_FAILED")
    if result.get("ok") is False:
        # The stage runner reports BL generator/validator refusals and its own assertion or
        # adapter failures the same way; the error type is kept so they are not conflated.
        tokens.append(f"STAGE_FAILED[{result.get('error_type') or '?'}]: {result.get('error') or ''}".rstrip(": "))
    if clear and clear.get("status") not in (None, "PASS"):
        tokens.append(str(clear.get("status")))
    rc = validate.get("returncode") if validate else None
    if rc not in (None, 0, 0.0):
        tokens.append(f"BL_VALIDATE_FAILED[rc {int(rc) if isinstance(rc, (int, float)) else rc}]")
    # `valid` must be the JSON boolean true; older manifests stored it as the string "None".
    staged = bool(payload.get("project_sha256")) or validate.get("valid") is True
    solved = None
    if run is not None:
        freqs = run.get("frequencies_hz") or []
        mask = run.get("completion_mask") or []
        done = int(sum(1 for m in mask if m)) if mask else (len(freqs) if run.get("status") == "complete" else 0)
        solved = {"status": run.get("status"), "done": done, "total": len(freqs),
                  "fmin_hz": min(freqs) if freqs else None, "fmax_hz": max(freqs) if freqs else None,
                  "backend": run.get("backend_id"), "solve_kind": run.get("solve_kind")}
    elif (case / "run").is_dir():
        solved = {"status": "incomplete (no run manifest)", "done": 0, "total": None}
    if solved and solved.get("status") == "complete":
        state = "solved"
    elif result.get("ok") is False:
        state = "stage_failed"
    elif solved:
        state = "solve_failed"
    elif staged:
        state = "staged"
    elif payload:
        state = "recorded"
    else:
        state = "empty"
    return {"state": state, "tokens": tokens, "solve": solved,
            "validate_valid": validate.get("valid") if validate else None}


def _motor_fact(payload: dict) -> str | None:
    if isinstance(payload.get("motor_mapping"), dict) or payload.get("motor_role"):
        return "real"
    return None


def _row(store: Path, case: Path, declared: dict[str, dict]) -> dict:
    exp, name = case.parent.name, case.name
    key = f"{exp}/{name}"
    payload, integrity = _load_manifest(case)
    kind = payload.get("kind")
    run = _run_manifest(case)
    st = _state(case, payload, integrity, run)
    source, horn, parent = _source_params(store, payload)
    family = _family(kind, exp)
    clearance = _clearance(store, case, payload, horn, parent) if family == "bl_case" else None
    if clearance and clearance.get("status") not in ("PASS", "NOT_CHECKED") \
            and clearance["status"] not in st["tokens"]:
        st["tokens"].append(clearance["status"])
    decl = declared.get(key, {})
    motor_fact = _motor_fact(payload)
    return {
        "key": key, "experiment": exp, "case": name, "kind": kind, "family": family,
        "integrity": integrity, **st,
        "box": _box(source), "parent": parent,
        "horn": None if not isinstance(horn, dict) else {
            "mesh": Path(str(horn.get("mesh_path", ""))).parent.name or None,
            "translation_mm": horn.get("translation_mm"), "source_group": horn.get("source_group"),
            "mesh_role": horn.get("mesh_role")},
        "clearance": clearance,
        "declared": bool(decl),
        "ref": decl.get("ref"), "gate": decl.get("gate"), "note": decl.get("note"),
        "evidence": decl.get("evidence"),
        "fidelity": decl.get("fidelity") or "UNDECLARED",
        "motor": decl.get("motor") or motor_fact or "UNDECLARED",
        "motor_fact": motor_fact,
        "transducer_shape": decl.get("transducer_shape") or "UNDECLARED",
        "horn_source": decl.get("horn_source"),
        "pair_with": decl.get("pair_with"),
        "created_utc": name[:16] if re.match(r"^\d{8}T\d{6}Z", name) else None,
    }


# --------------------------------------------------------------------------- public views

def hw_cases(root: Path, store: Path) -> dict:
    registry = load_registry(root)
    declared = _declared(registry)
    base = store_dir(store)
    rows = []
    if base.is_dir():
        for exp in sorted(p for p in base.iterdir() if p.is_dir() and not p.name.startswith("_")):
            for case in sorted(p for p in exp.iterdir() if p.is_dir()):
                if _KEY_PART.match(case.name) and _KEY_PART.match(exp.name):
                    rows.append(_row(store, case, declared))
    on_disk = {r["key"] for r in rows}
    missing = [{"key": k, "ref": d.get("ref"), "gate": d.get("gate")}
               for k, d in declared.items() if k not in on_disk]
    rows.sort(key=lambda r: (r["created_utc"] or "", r["key"]), reverse=True)
    counts: dict[str, int] = {}
    for r in rows:
        if r["family"] == "bl_case":
            counts[r["state"]] = counts.get(r["state"], 0) + 1
    # P1: the ledger KPI strip shows recorded and empty too (hidden rows still counted).
    for k in ("solved", "staged", "stage_failed", "solve_failed", "recorded", "empty"):
        counts.setdefault(k, 0)
    return {"store": str(base), "registry": REGISTRY_REL.as_posix(),
            "registry_error": registry.get("error"), "fidelity_note": registry.get("fidelity_note"),
            "cases": rows, "declared_missing": missing, "counts": counts}


def _placeholders(row: dict, run_fmin: float | None) -> list[dict]:
    out = []
    if row["motor"] == "demo":
        out.append({"token": "DEMO_MOTOR", "text": "BL provider-default motor, not a real driver's T/S."})
    if row["transducer_shape"] != "real":
        out.append({"token": "DEMO_TRANSDUCER_SHAPE",
                    "text": "BL provider-default cone/surround/cap geometry (MOTOR_GEOMETRY_INCOMPLETE)."})
    if row.get("horn") is not None:
        out.append({"token": "IDEAL_HORN_SOURCE",
                    "text": "Horn throat driven as an ideal 1 m/s normal-velocity source, not a compression driver."})
    if run_fmin is not None and run_fmin > 20.0:
        out.append({"token": "LF_NOT_SOLVED",
                    "text": f"Nothing solved below {run_fmin:g} Hz; box tuning is not visible in this data."})
    if row["state"] == "solved":
        out.append({"token": "CONVERGENCE_UNCHECKED",
                    "text": "Single mesh; no refinement or frequency-densification record (R6)."})
    return out


def _outline(points: np.ndarray, axes: tuple[int, int]) -> list[list[float]]:
    pts = points[:, axes]
    try:
        from scipy.spatial import ConvexHull
        hull = ConvexHull(pts)
        return [[round(float(x) * 1000, 2), round(float(y) * 1000, 2)] for x, y in pts[hull.vertices]]
    except Exception:  # noqa: BLE001 - degenerate projection
        lo, hi = pts.min(0), pts.max(0)
        return [[lo[0] * 1000, lo[1] * 1000], [hi[0] * 1000, lo[1] * 1000],
                [hi[0] * 1000, hi[1] * 1000], [lo[0] * 1000, hi[1] * 1000]]


def _geometry(store: Path, case: Path, row: dict, horn: dict | None) -> dict | None:
    """Two to-scale elevations in mm: front (x-y) and side (z-y)."""
    try:
        owner = case if row["parent"] is None else _resolve_case(store, row["parent"])
    except (FileNotFoundError, ValueError):
        return None
    exteriors = sorted(owner.glob("bl_output/*/exterior.msh"))
    if not exteriors:
        return None
    import meshio

    def read(p: Path) -> np.ndarray:
        return _cached(("pts",) + _stamp(p), lambda: np.asarray(meshio.read(p).points, dtype=np.float64))
    box_pts = np.vstack([read(p) for p in exteriors])
    lo, hi = box_pts.min(0), box_pts.max(0)
    out: dict[str, Any] = {
        "units": "mm", "frame": "BL project frame: x width, y height, z forward (front face at max z)",
        "box_bbox_mm": [[round(v * 1000, 2) for v in lo], [round(v * 1000, 2) for v in hi]],
        "horn_front": None, "horn_side": None,
    }
    mesh = _inside(store, (horn or {}).get("mesh_path"))
    if mesh is not None:
        t = np.asarray(horn.get("translation_mm", (0, 0, 0)), dtype=np.float64) / 1000.0
        hp = read(mesh) * float(horn.get("scale_factor", 1.0)) + t
        out["horn_front"] = _outline(hp, (0, 1))
        out["horn_side"] = _outline(hp, (2, 1))
        hlo, hhi = hp.min(0), hp.max(0)
        out["horn_bbox_mm"] = [[round(v * 1000, 2) for v in hlo], [round(v * 1000, 2) for v in hhi]]
    elif horn:
        out["horn_missing"] = "horn mesh not on disk inside the store"
    return out


# --------------------------------------------------------------------------- 3-D mesh (P3)

_FRAME = "BL project frame: x width, y height, z forward (front face at max z)"
_TRI_CAP = 60000
_MESH_PARTS = ("box", "horn")


def _rel(p: Path, base: Path) -> str:
    """Store-relative posix name (the caller only ever passes contained files)."""
    try:
        return p.resolve().relative_to(base).as_posix()
    except ValueError:
        return p.name


def _mesh_arrays(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """(float64 points, int64 triangle indices) from ``meshio``, triangles only.

    A mesh with no triangle cells is refused by name, never silently returned empty.
    """
    def read():
        import meshio
        mesh = meshio.read(path)
        found: dict[str, int] = {}
        for cell in mesh.cells:
            found[cell.type] = found.get(cell.type, 0) + int(len(cell.data))
        tris = [np.asarray(c.data, dtype=np.int64) for c in mesh.cells if c.type == "triangle"]
        tris = [t for t in tris if len(t)]
        if not tris:
            types = ", ".join(f"{k} ({v})" for k, v in sorted(found.items())) or "no cells"
            raise ValueError(f"{Path(path).name}: no triangle cells (found: {types})")
        return np.asarray(mesh.points, dtype=np.float64), np.vstack(tris)
    return _cached(("meshio",) + _stamp(Path(path)), read)


def _surface_area(points: np.ndarray, tris: np.ndarray) -> float:
    a, b, c = points[tris[:, 0]], points[tris[:, 1]], points[tris[:, 2]]
    return float(0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1).sum())


def _cluster(points: np.ndarray, tris: np.ndarray, pitch: float,
             lo: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Vertex clustering: snap to a ``pitch`` grid anchored at ``lo``, merge, drop junk.

    Retained vertices keep their first-occurrence order from the input array; retained
    triangles likewise keep their original order.
    """
    grid = np.rint((points - lo) / pitch).astype(np.int64)
    uniq, first, inv = np.unique(grid, axis=0, return_index=True, return_inverse=True)
    inv = np.asarray(inv).reshape(-1)
    order = np.argsort(first, kind="stable")
    rank = np.empty(order.size, dtype=np.int64)
    rank[order] = np.arange(order.size, dtype=np.int64)
    verts = lo + uniq[order].astype(np.float64) * pitch
    t = rank[inv][tris]
    keep = (t[:, 0] != t[:, 1]) & (t[:, 1] != t[:, 2]) & (t[:, 0] != t[:, 2])
    t = t[keep]
    if t.size:
        _, idx = np.unique(np.sort(t, axis=1), axis=0, return_index=True)
        t = t[np.sort(idx)]
    return verts, t


def _decimate(points: np.ndarray, tris: np.ndarray,
              cap: int = _TRI_CAP) -> tuple[np.ndarray, np.ndarray, bool]:
    """Deterministic vertex clustering down to <= ``cap`` triangles.

    The pitch starts from the surface area and the bbox and grows until the clustered
    mesh fits: identical input always yields identical vertices and triangles.
    """
    lo = points.min(0)
    ext = float(np.max(points.max(0) - lo))
    area = _surface_area(points, tris)
    pitch = 1.4 * math.sqrt(area / cap) if area > 0.0 and cap > 0 else 0.0
    pitch = max(pitch, ext / 64.0, ext * 1e-6, 1e-9)
    verts, t = points, tris
    for _ in range(80):
        verts, t = _cluster(points, tris, pitch, lo)
        if len(t) <= cap:
            return verts, t, True
        pitch *= 1.25
    return verts, t, True                           # pitch > bbox: collapses to a handful


def _mesh_payload(key: str, part: str, verts: np.ndarray, tris: np.ndarray,
                  source_files: list[str], frame: str, decimated: bool) -> dict:
    if len(verts):
        lo, hi = verts.min(0), verts.max(0)
        bbox = [[round(float(v), 6) for v in lo], [round(float(v), 6) for v in hi]]
    else:
        bbox = [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]
    return {
        "key": key, "part": part, "units": "mm", "frame": frame,
        "verts": np.round(np.asarray(verts, dtype=np.float64), 6).reshape(-1).tolist(),
        "tris": np.asarray(tris, dtype=np.int64).reshape(-1).tolist(),
        "bbox": bbox, "triangle_count": int(len(tris)), "decimated": bool(decimated),
        "source_files": source_files,
    }


def hw_mesh(root: Path, store: Path, key: str, part: str) -> dict:
    """One part of a case's geometry in mm, flat arrays ready for a WebGL viewer.

    ``part="box"`` is the enclosure surface from the case's own ``bl_output/*/exterior.msh``
    (a solve-only case uses the staged parent it solved). ``part="horn"`` is the manifest's
    ``spec.horn.mesh_path``, scaled and translated into the BL project frame; a path outside
    the store is refused before any read. Triangle-only, no solver, no Boundary Lab import.
    """
    if part not in _MESH_PARTS:
        raise ValueError(f"bad mesh part {part!r}: expected one of {', '.join(_MESH_PARTS)}")
    case = _resolve_case(store, key)
    payload, _ = _load_manifest(case)
    _, horn, parent = _source_params(store, payload)
    base = Path(store).resolve()

    if part == "box":
        owner = case if parent is None else _resolve_case(store, parent)
        files = sorted(p for p in owner.glob("bl_output/*/exterior.msh")
                       if p.is_file() and base in p.resolve().parents)
        if not files:
            raise FileNotFoundError(
                f"{key}: no enclosure exterior mesh (bl_output/*/exterior.msh) inside the store")
        source_files = [_rel(p, base) for p in files]
        stamps = tuple(_stamp(p) for p in files)

        def build_box():
            chunks, off = [], 0
            for p in files:
                v, t = _mesh_arrays(p)
                chunks.append((v, t + off))
                off += len(v)
            verts = np.vstack([v for v, _ in chunks]) * 1000.0      # BL meshes are metres
            tris = np.vstack([t for _, t in chunks])
            dec = len(tris) > _TRI_CAP
            if dec:
                verts, tris, dec = _decimate(verts, tris)
            return _mesh_payload(key, "box", verts, tris, source_files, _FRAME, dec)

        return _cached(("hwmesh", "box", key, *stamps), build_box)

    horn = horn if isinstance(horn, dict) else {}
    mesh_path = horn.get("mesh_path")
    if not mesh_path:
        raise FileNotFoundError(f"{key}: no horn mesh recorded (spec.horn.mesh_path missing)")
    path = _inside(store, mesh_path)
    if path is None:
        resolved = Path(mesh_path).resolve()
        if base not in resolved.parents:
            raise FileNotFoundError(
                f"horn mesh {resolved} is outside the store {base}; refusing to read it")
        raise FileNotFoundError(f"horn mesh {resolved} is not a file inside the store")
    raw_scale = horn.get("scale_factor")
    scale = 1.0 if raw_scale is None else float(raw_scale)
    t_mm = np.asarray(horn.get("translation_mm") or (0.0, 0.0, 0.0), dtype=np.float64)
    if t_mm.shape != (3,):
        raise ValueError(f"{key}: horn translation_mm must be three numbers, "
                         f"got {horn.get('translation_mm')!r}")
    stamps = _stamp(path)

    def build_horn():
        pts, tris = _mesh_arrays(path)
        verts = (pts * scale + t_mm / 1000.0) * 1000.0
        dec = len(tris) > _TRI_CAP
        if dec:
            verts, tris, dec = _decimate(verts, tris)
        return _mesh_payload(key, "horn", verts, tris, [_rel(path, base)],
                             _FRAME + "; horn mesh scaled and translated into it", dec)

    return _cached(("hwmesh", "horn", key, stamps, scale, tuple(t_mm.tolist())), build_horn)


def _run_view(case: Path) -> dict | None:
    if not (case / "run" / "manifest.json").is_file():
        return None
    from hornlab_search.system.boundarylab import bl_results as R

    run_dir = case / "run"
    try:
        res = _cached(("res",) + _stamp(run_dir / "manifest.json"),
                      lambda: R.read_bl_headless_result(run_dir))
    except Exception as exc:  # noqa: BLE001 - refusal tokens are the point
        return {"error": f"{type(exc).__name__}: {exc}"}
    conv = {c.excitation_id: c.as_dict() for c in res.conversion}
    domains = []
    for d in res.domain_ids():
        o = res.observation_sets[d]
        domains.append({"id": d, "kind": o.kind, "count": o.count, "distance_m": o.distance_m,
                        "plane": (o.metadata or {}).get("plane"),
                        "probe_id": (o.metadata or {}).get("probe_id")})
    raw = _run_manifest(case) or {}
    return {
        "frequencies_hz": [float(f) for f in res.frequencies_hz],
        "excitations": [{"id": e, "per_input": conv.get(e, {}).get("to_per_input"),
                         "reference": conv.get(e, {}).get("from_per_input"),
                         "unit": "Pa"} for e in res.excitation_ids],
        "domains": domains,
        "data_quality": dict(res.data_quality),
        "provenance": dict(res.provenance.as_dict()),
        "solver_options": raw.get("solver_options"),
        "engine_runs": raw.get("engine_runs"),
        "started_at_utc": raw.get("started_at_utc"), "finished_at_utc": raw.get("finished_at_utc"),
    }


def hw_case(root: Path, store: Path, key: str) -> dict:
    case = _resolve_case(store, key)
    registry = load_registry(root)
    row = _row(store, case, _declared(registry))
    payload, _ = _load_manifest(case)
    _, horn, _ = _source_params(store, payload)
    run = _run_view(case)
    fmin = min(run["frequencies_hz"]) if run and run.get("frequencies_hz") else None
    result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
    highlights = {k: payload.get(k) for k in (
        "authorized_by", "gate", "motor_role", "experiment_id", "project_sha256",
        "configuration_patch_sha256", "spec_sha256") if payload.get(k) is not None}
    motor = payload.get("motor_mapping")
    if isinstance(motor, dict):
        highlights["motor_mapping"] = {k: motor.get(k) for k in (
            "driver_id", "dry_mass_kg", "cross_checks") if k in motor}
    geo_over = payload.get("geometry_overrides")
    if isinstance(geo_over, dict):
        highlights["transducer_geometry"] = {k: geo_over.get(k) for k in (
            "complete", "driver_id", "present_fields", "refusals", "values", "derived") if k in geo_over}
    validate = payload.get("validate")
    return {
        "row": row,
        "placeholders": _placeholders(row, fmin),
        "highlights": highlights,
        "validate": validate if isinstance(validate, dict) else None,
        "refusal": {k: result.get(k) for k in ("error_type", "error")} if result.get("ok") is False else None,
        "bl_root": payload.get("bl_root") if isinstance(payload.get("bl_root"), dict) else None,
        "files": sorted(p.name + ("/" if p.is_dir() else "") for p in case.iterdir()),
        "run": run,
        "geometry": _geometry(store, case, row, horn),
        "observation_caption": _observation_caption(run),
    }


def _observation_caption(run: dict | None) -> str | None:
    """R5: the observation limits travel with every plot (distance from the record)."""
    if not run or run.get("error"):
        return None
    dists = sorted({round(d["distance_m"], 2) for d in run.get("domains", []) if d.get("distance_m")})
    fmin = min(run["frequencies_hz"]) if run.get("frequencies_hz") else None
    where = " / ".join(f"{d:g} m" for d in dists) or "unknown distance"
    lam = f" (wavelength {343.0 / fmin:.2f} m at {fmin:g} Hz)" if fmin else ""
    return (f"Observed at {where}{lam}; not a far-field claim at the low end. "
            "1-D cuts and point probes only; no DI or sound power.")


def hw_basis(root: Path, store: Path, key: str, domain: str) -> dict:
    """One observation domain of a solved case, per excitation, never summed.

    Probe domains: |p| in dB SPL per declared input + wrapped phase (deg). Polar domains:
    dB normalised per frequency to that excitation's own 0-degree sample (heatmap rows).
    """
    case = _resolve_case(store, key)
    run_dir = case / "run"
    if not (run_dir / "manifest.json").is_file():
        raise FileNotFoundError(f"{key} has no solved run")
    from hornlab_search.system.boundarylab import bl_results as R

    res = _cached(("res",) + _stamp(run_dir / "manifest.json"), lambda: R.read_bl_headless_result(run_dir))
    if domain not in res.observation_sets:
        raise ValueError(f"unknown domain {domain!r}; available: {sorted(res.observation_sets)}")
    obs = res.observation_sets[domain]
    bases = res.per_excitation_bases(domain)
    conv = {c.excitation_id: c for c in res.conversion}
    out: dict[str, Any] = {"key": key, "domain": domain, "kind": obs.kind,
                           "frequencies_hz": [float(f) for f in res.frequencies_hz],
                           "distance_m": obs.distance_m, "excitations": []}
    angles = None if obs.angles_deg is None else [float(a) for a in obs.angles_deg]
    out["angles_deg"] = angles
    for ex, p in bases.items():
        c = conv.get(ex)
        item = {"id": ex, "per_input": None if c is None else c.to_per_input,
                "reference": None if c is None else c.from_per_input}
        mag = np.abs(p)
        if angles is None:
            # Point probes: one curve per observation point (real cases have one point each).
            item["spl_db"] = [_db(v) for v in mag[:, 0]]
            item["phase_deg"] = [float(np.degrees(np.angle(v))) for v in p[:, 0]]
            # Unwrapped in Python (never in JS): continuous phase for the wrapped/unwrapped toggle.
            item["phase_unwrapped_deg"] = [float(v) for v in
                                           np.degrees(np.unwrap(np.angle(p[:, 0])))]
            if obs.count > 1:
                item["spl_db_points"] = [[_db(v) for v in row] for row in mag]
                item["phase_deg_points"] = [[float(np.degrees(np.angle(v))) for v in row] for row in p]
        else:
            i0 = int(np.argmin(np.abs(np.asarray(angles))))
            ref = mag[:, i0:i0 + 1]
            with np.errstate(divide="ignore", invalid="ignore"):
                rel = 20.0 * np.log10(np.where(ref > 0, mag / ref, np.nan))
            item["rel_db"] = [[None if not math.isfinite(v) else round(float(v), 3) for v in row]
                              for row in rel]
            item["on_axis_spl_db"] = [_db(v) for v in ref[:, 0]]
            item["normalised_to_deg"] = angles[i0]
        out["excitations"].append(item)
    return out


def _db(v: float) -> float | None:
    v = float(v)
    return round(20.0 * math.log10(v / _P_REF), 3) if v > 0 and math.isfinite(v) else None


def hw_readiness(root: Path, store: Path) -> dict:
    registry = load_registry(root)
    cases = hw_cases(root, store)
    return {"registry": REGISTRY_REL.as_posix(), "registry_error": registry.get("error"),
            "updated": registry.get("updated"), "handoff": registry.get("handoff"),
            "risks": registry.get("risks") or [], "decisions": registry.get("decisions") or [],
            "counts": cases["counts"], "declared_missing": cases["declared_missing"]}


# --------------------------------------------------------------------------- overview (P8)

def overview_next_step(studies: list[dict], counts: dict) -> dict:
    """The one next action, computed from disk (never guessed in JS).

    Order: no studies -> start a new system; a shortlist with no Boundary Lab case -> check one
    in BL; two or more solved -> compare; one solved -> read it; staged only -> open a staged case
    (solving needs decision 6); otherwise run a screen.
    """
    solved = int(counts.get("solved") or 0)
    staged = int(counts.get("staged") or 0)
    shortlist = sum(int((s.get("counts") or {}).get("shortlist_rows") or 0) for s in studies)
    if not studies and not (staged or solved):
        return {"id": "new", "label": "Start a new system",
                "href": "#/hw/new",
                "why": "No screen study exists yet. Pick a horn, drivers and box limits, then screen."}
    if studies and shortlist and not (staged or solved):
        newest = studies[0]["study_id"]
        return {"id": "stage", "label": "Check a shortlisted design in Boundary Lab",
                "href": f"#/hw/screen/{newest}",
                "why": f"Shortlist ready ({shortlist} designs). Boundary Lab proves the box can be built."}
    if solved >= 2:
        return {"id": "compare", "label": "Compare two solved cases", "href": "#/hw/compare",
                "why": f"{solved} solved cases; A/B the differences on the shared grid."}
    if solved == 1:
        return {"id": "read", "label": "Read the solved results", "href": "#/hw/cases",
                "why": "One case is solved; open it for per-channel response, polars and provenance."}
    if staged:
        return {"id": "solve", "label": "Open a staged case", "href": "#/hw/cases",
                "why": f"{staged} staged and validated; solving needs owner approval (decision 6)."}
    return {"id": "screen", "label": "Run a screen", "href": "#/hw/new",
            "why": "A study exists but no shortlist rows were produced."}


def _case_row_brief(row: dict) -> dict:
    return {k: row.get(k) for k in (
        "key", "ref", "gate", "experiment", "case", "state", "solve", "box", "horn",
        "clearance", "fidelity", "motor", "transducer_shape", "created_utc", "tokens")}


def hw_overview(root: Path, store: Path) -> dict:
    """The Overview: KPIs + the next step + recents, all derived from disk/registry."""
    from . import data_hw_screen as SW          # lazy: data_hw_screen imports this module

    registry = load_registry(root)
    cases = hw_cases(root, store)
    try:
        screens = SW.hw_screens(root, store)
    except Exception as exc:  # noqa: BLE001 - an unreadable study list is shown, never hidden
        screens = {"studies": [], "errors": [f"{type(exc).__name__}: {exc}"]}
    studies = screens.get("studies") or []
    counts = cases.get("counts") or {}
    shortlist_total = sum(int((s.get("counts") or {}).get("shortlist_rows") or 0) for s in studies)
    decisions = [d for d in (registry.get("decisions") or [])
                 if str(d.get("status") or "").lower() == "open"]
    risks = registry.get("risks") or []
    by_level: dict[str, int] = {}
    for r in risks:
        key = str(r.get("level") or "UNKNOWN")
        by_level[key] = by_level.get(key, 0) + 1
    return {
        "store": cases.get("store"),
        "registry": REGISTRY_REL.as_posix(),
        "registry_error": registry.get("error"),
        "counts": counts,
        "kpis": {
            "screens": len(studies),
            "shortlisted": shortlist_total,
            "checked_in_bl": int(counts.get("staged") or 0) + int(counts.get("solved") or 0),
            "solved": int(counts.get("solved") or 0),
            "blocked_decisions": len(decisions),
        },
        "next_step": overview_next_step(studies, counts),
        "recent_screens": [{k: s.get(k) for k in (
            "study_id", "mtime_utc", "horn", "driver_count", "counts", "counts_missing",
            "claim", "replay_count", "byte_identical")} for s in studies[:3]],
        "recent_cases": [_case_row_brief(r) for r in (cases.get("cases") or [])[:5]],
        "readiness": {
            "updated": registry.get("updated"),
            "open_decisions": decisions,
            "risks_total": len(risks),
            "risks_by_level": by_level,
        },
        "screen_errors": screens.get("errors") or [],
        "declared_missing": cases.get("declared_missing") or [],
    }
