"""P4 — A/B compare for the Horn + woofer GUI (read-only, no solver, no channel sum).

Two solved cases are compared **per point-probe domain and per excitation**. Nothing is ever
summed across excitations: the woofer basis is Pa per ``V_rms`` and the horn basis is Pa per
``normal_velocity_mps``; mixing those into one number would be a calibration claim (R1) that has
not been decided. A pair that cannot be compared at the input level is refused with one token
per mismatch rather than silently coerced.

What comes from where (never mixed):

* **Facts** — frequency grids, excitation ids and per-input references, point-probe ids, the
  pressure bases, the source-geometry hash — are read from the solved ``run/`` directories with
  ``bl_results.read_bl_headless_result`` (the same reader the rest of ``data_hw`` uses).
* **Declarations / identity** — motor role/mapping presence, box dimensions, horn offset and
  scale, mesh size/name — are read from the case manifests via the ``data_hw`` helpers.

No solver, no Boundary Lab entry point beyond the ``bl_results`` file reader, no writes. Every
value returned is plain JSON.

Bands and the ``max_relative_delta_percent`` statistic
------------------------------------------------------
The band edges LF < 500 Hz / XO 500-1500 Hz / HF > 1500 Hz are **display choices** (labelled in
``band_note``). ``max_relative_delta_percent`` follows the *recorded evidence* definition in
``docs/research/system_woofer_2026-11-18/FIRST_BEM_EVIDENCE.md`` (``motor_axis_ab.json`` and
``g6_paired_delta.json``):

    max_relative_delta_percent = 100 * max_{f in band} |p_a(f) - p_b(f)| / max_{f in band} |p_b(f)|

That is the statistic the recorded numbers were computed with (max abs delta over the band,
normalised by the band's peak |p_b|). It is **not** the per-frequency symmetric ratio sketched by
the generic GUI brief, because that does not reproduce the recorded 120 % / 140-149 % motor A/B
figures or the G6 0.356-0.575 / 0.064-0.371 figures. The test module pins the reproduced values.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np

from hornlab_search.gui import data_hw as HW

#: Display band edges (see the module docstring): (name, low inclusive, high exclusive-ish).
#: LF is strictly < 500 Hz, XO is 500-1500 Hz inclusive, HF is strictly > 1500 Hz, so the three
#: bands partition every frequency the solver produced.
BANDS: tuple[tuple[str, float | None, float | None], ...] = (
    ("LF", None, 500.0),
    ("XO", 500.0, 1500.0),
    ("HF", 1500.0, None),
)

#: Recorded log grids may round to different decimal places (222.2 vs 222.195 Hz).
GRID_TOL_HZ = 0.01

BAND_NOTE = (
    "Band edges are display choices: LF < 500 Hz, XO 500-1500 Hz, HF > 1500 Hz. "
    "max_relative_delta_percent is the recorded-evidence statistic "
    "100 * max|p_a - p_b| / max|p_b| over the band (not a per-frequency ratio)."
)

_CAPTION_TAIL = "1-D cuts and point probes only; no DI or sound power."


# --------------------------------------------------------------------------- run access

def _run_dir(store: Path, key: str) -> tuple[Path, Path]:
    """(case dir, run dir) for a key with a solved ``run/``; FileNotFoundError otherwise."""
    case = HW._resolve_case(store, key)
    run = case / "run"
    if not (run / "manifest.json").is_file():
        raise FileNotFoundError(
            f"{key}: no solved run/ (run/manifest.json) under {case}; "
            "compare needs a completed Boundary Lab result")
    return case, run


def _read_run(key: str, case: Path):
    """Read one solved run, cached on the run manifest stamp (``data_hw._cached``)."""
    from hornlab_search.system.boundarylab import bl_results as R

    run = case / "run"
    stamp = HW._stamp(run / "manifest.json")
    return HW._cached(("cmp", "res", key) + stamp,
                      lambda: R.read_bl_headless_result(run))


# --------------------------------------------------------------------------- identity facts

def _facts(store: Path, key: str, case: Path, res) -> dict:
    """Identity facts from the case manifest + the run provenance (never inferred)."""
    payload, _ = HW._load_manifest(case)
    source, horn, parent = HW._source_params(store, payload)
    box = HW._box(source)
    mapping = payload.get("motor_mapping") if isinstance(payload.get("motor_mapping"), dict) else None
    hmesh = horn.get("mesh_path") if isinstance(horn, dict) else None
    return {
        "key": key,
        "kind": payload.get("kind"),
        "family": HW._family(payload.get("kind"), str(key).split("/")[0]),
        "parent": parent,
        "motor": {
            "role": payload.get("motor_role"),
            "mapping_present": mapping is not None,
            "driver_id": mapping.get("driver_id") if mapping else None,
        },
        "box": None if box is None else {k: box.get(k) for k in (
            "width_mm", "height_mm", "depth_mm", "wall_mm",
            "port_area_cm2", "port_length_mm")},
        "horn_offset_mm": None if not isinstance(horn, dict) else horn.get("translation_mm"),
        "scale": None if not isinstance(horn, dict) else horn.get("scale_factor"),
        "source_geometry_hash": res.provenance.source_geometry_hash,
        "project_sha256": payload.get("project_sha256"),
        "mesh": {
            "horn_mesh_name": None if not hmesh else Path(str(hmesh)).name,
            "horn_mesh_dir": None if not hmesh else Path(str(hmesh)).parent.name,
            "mesh_size_mm": None if box is None else box.get("mesh_size_mm"),
            "detail_size_mm": None if box is None else box.get("detail_size_mm"),
        },
    }


_DIFF_PATHS: tuple[tuple[str, ...], ...] = (
    ("motor", "role"), ("motor", "mapping_present"), ("motor", "driver_id"),
    ("box", "width_mm"), ("box", "height_mm"), ("box", "depth_mm"),
    ("horn_offset_mm",), ("scale",), ("source_geometry_hash",), ("project_sha256",),
    ("mesh", "horn_mesh_name"), ("mesh", "mesh_size_mm"), ("mesh", "detail_size_mm"),
)


def _get(facts: dict, path: tuple[str, ...]) -> Any:
    value: Any = facts
    for part in path:
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def _what_differs(fa: dict, fb: dict) -> dict:
    differs = [".".join(path) for path in _DIFF_PATHS if _get(fa, path) != _get(fb, path)]
    return {"a": fa, "b": fb, "differs": differs}


# --------------------------------------------------------------------------- refusal checks

def _first_diff(fa: np.ndarray, fb: np.ndarray) -> int | None:
    limit = min(len(fa), len(fb))
    for i in range(limit):
        f = float(fa[i])
        # Two solves of the same request are exact; two staging paths may round the stored log
        # grid differently (the #4 seed records 222.2 Hz where the #2-derived cases record
        # 222.195 Hz). 0.01 Hz cannot mask a physically different grid: lengths and endpoints
        # still have to match.
        tol = max(GRID_TOL_HZ, abs(f) * 1e-9)
        if abs(f - float(fb[i])) > tol:
            return i
    return None


def _grid_detail(fa: np.ndarray, fb: np.ndarray) -> str | None:
    """``None`` when every frequency matches tightly; else a length + first-difference note."""
    if len(fa) == len(fb):
        i = _first_diff(fa, fb)
        if i is None:
            return None
        return (f"lengths equal ({len(fa)}) but frequency {i} differs: "
                f"A={float(fa[i]):g} Hz B={float(fb[i]):g} Hz")
    i = _first_diff(fa, fb)
    parts = [f"lengths A={len(fa)} B={len(fb)}"]
    if i is not None:
        parts.append(f"first differing frequency at index {i}: "
                     f"A={float(fa[i]):g} Hz B={float(fb[i]):g} Hz")
    elif len(fa) > len(fb):
        parts.append(f"first differing frequency at index {len(fb)}: "
                     f"A={float(fa[len(fb)]):g} Hz B=<missing>")
    else:
        parts.append(f"first differing frequency at index {len(fa)}: "
                     f"A=<missing> B={float(fb[len(fa)]):g} Hz")
    return "; ".join(parts)


def _probe_signature(res) -> tuple[tuple[str, Any], ...]:
    """Sorted (domain id, probe id) for every point-probe domain."""
    out = []
    for domain_id in res.domain_ids():
        obs = res.observation_sets[domain_id]
        if obs.kind != "point_probe":
            continue
        out.append((domain_id, (obs.metadata or {}).get("probe_id")))
    return tuple(sorted(out))


def _probe_detail(sa: tuple, sb: tuple) -> str:
    only_a = [list(x) for x in sa if x not in sb]
    only_b = [list(x) for x in sb if x not in sa]
    return (f"point-probe domains/probe ids differ: only in A {only_a}; only in B {only_b}")


def _exc_signature(res) -> tuple[tuple[str, Any], ...]:
    """Ordered (port role, per-input reference) per excitation.

    The component namespace of an excitation id is allowed to differ: a real-motor case names its
    woofer port ``bl_motor12pr/voltage`` while the demo twin names the same physical port
    ``vented/voltage`` (FIRST_BEM_EVIDENCE.md motor A/B). What must match is the *role* and the
    per-input basis, because those decide whether the two bases are comparable. A different set
    of roles or per-input references (e.g. a woofer voltage port on one side and a horn
    normal-velocity port on the other) is refused, never summed.
    """
    conv = {c.excitation_id: c for c in res.conversion}
    out = []
    for excitation_id in res.excitation_ids:
        record = conv.get(excitation_id)
        per_input = None if record is None else record.to_per_input
        out.append((str(excitation_id).split("/")[-1], per_input))
    return tuple(out)


def _exc_detail(res_a, res_b) -> str:
    def show(res):
        conv = {c.excitation_id: c for c in res.conversion}
        return [{"id": e, "per_input": None if e not in conv else conv[e].to_per_input}
                for e in res.excitation_ids]
    return f"excitations differ: A={show(res_a)} B={show(res_b)}"


def _mismatches(res_a, res_b) -> list[dict]:
    out: list[dict] = []
    grid = _grid_detail(np.asarray(res_a.frequencies_hz), np.asarray(res_b.frequencies_hz))
    if grid:
        out.append({"token": "GRID_MISMATCH", "detail": grid})
    sa, sb = _probe_signature(res_a), _probe_signature(res_b)
    if sa != sb:
        out.append({"token": "PROBE_SET_MISMATCH", "detail": _probe_detail(sa, sb)})
    if _exc_signature(res_a) != _exc_signature(res_b):
        out.append({"token": "EXCITATION_MISMATCH", "detail": _exc_detail(res_a, res_b)})
    return out


# --------------------------------------------------------------------------- band statistics

def relative_delta_percent(p_a: np.ndarray, p_b: np.ndarray, frequencies_hz,
                           lo_hz: float | None = None, hi_hz: float | None = None) -> float | None:
    """``100 * max|p_a - p_b| / max|p_b|`` over a frequency band (the recorded-evidence statistic).

    ``lo_hz`` and ``hi_hz`` are both inclusive; pass ``(600, 1200)`` to reproduce the recorded
    motor/G6 XO band. ``None`` when the band is empty or the reference peak is zero/non-finite.
    """
    a = np.asarray(p_a, dtype=np.complex128).reshape(-1)
    b = np.asarray(p_b, dtype=np.complex128).reshape(-1)
    f = np.asarray(frequencies_hz, dtype=np.float64).reshape(-1)
    if not (a.size == b.size == f.size):
        raise ValueError("p_a, p_b and frequencies_hz must have the same length")
    mask = np.isfinite(f)
    if lo_hz is not None:
        mask &= f >= lo_hz
    if hi_hz is not None:
        mask &= f <= hi_hz
    if not np.any(mask):
        return None
    delta = np.abs(a[mask] - b[mask])
    ref = np.abs(b[mask])
    peak = float(np.max(ref))
    if not math.isfinite(peak) or peak <= 0.0:
        return None
    value = 100.0 * float(np.max(delta)) / peak
    return value if math.isfinite(value) else None


def _band_mask(frequencies_hz: np.ndarray, name: str) -> np.ndarray:
    """The display bands partition the grid: LF < 500, 500 <= XO <= 1500, HF > 1500."""
    if name == "LF":
        return frequencies_hz < 500.0
    if name == "XO":
        return (frequencies_hz >= 500.0) & (frequencies_hz <= 1500.0)
    return frequencies_hz > 1500.0


def _series(pa: np.ndarray, pb: np.ndarray) -> tuple[list, list]:
    """Per-frequency ``(ratio_db, delta_phase_deg)`` with ``None`` where undefined."""
    ra, rb = np.abs(pa), np.abs(pb)
    ok = np.isfinite(pa) & np.isfinite(pb) & (ra > 0.0) & (rb > 0.0)
    ratio = np.full(pa.shape, np.nan, dtype=np.float64)
    phase = np.full(pa.shape, np.nan, dtype=np.float64)
    ratio[ok] = 20.0 * np.log10(ra[ok] / rb[ok])
    phase[ok] = np.degrees(np.angle(pa[ok] * np.conj(pb[ok])))
    ratio_db = [None if not math.isfinite(v) else round(float(v), 6) for v in ratio]
    delta_phase_deg = [None if not math.isfinite(v) else round(float(v), 6) for v in phase]
    return ratio_db, delta_phase_deg


def _max_abs(values: list) -> float | None:
    finite = [abs(v) for v in values if v is not None]
    return round(max(finite), 6) if finite else None


def _max_abs_index(values: list) -> int | None:
    finite = [(abs(v), i) for i, v in enumerate(values) if v is not None]
    return max(finite)[1] if finite else None


def _band_rows(pa: np.ndarray, pb: np.ndarray, frequencies_hz: np.ndarray) -> list[dict]:
    rows = []
    for name, _lo_hz, _hi_hz in BANDS:
        mask = _band_mask(frequencies_hz, name)
        n = int(mask.sum())
        if n == 0:
            rows.append({"band": name, "n_freqs": 0, "max_abs_ratio_db": None,
                         "max_abs_ratio_at_hz": None,
                         "max_abs_delta_phase_deg": None, "max_relative_delta_percent": None,
                         "max_relative_delta_at_hz": None, "max_abs_delta_pa": None})
            continue
        ratio_db, phase = _series(pa[mask], pb[mask])
        delta = np.abs(pa[mask] - pb[mask])
        i = int(np.argmax(delta))
        j = _max_abs_index(ratio_db)
        rows.append({
            "band": name,
            "n_freqs": n,
            "max_abs_ratio_db": _max_abs(ratio_db),
            "max_abs_ratio_at_hz": None if j is None else round(float(frequencies_hz[mask][j]), 6),
            "max_abs_delta_phase_deg": _max_abs(phase),
            "max_relative_delta_percent": relative_delta_percent(
                pa[mask], pb[mask], frequencies_hz[mask]),
            "max_relative_delta_at_hz": round(float(frequencies_hz[mask][i]), 6),
            "max_abs_delta_pa": round(float(delta[i]), 9),
        })
    return rows


def _whole_grid(pa: np.ndarray, pb: np.ndarray, frequencies_hz: np.ndarray) -> dict:
    delta = np.abs(pa - pb)
    i = int(np.argmax(delta)) if delta.size else None
    ra, rb = np.abs(pa), np.abs(pb)
    ok = np.isfinite(pa) & np.isfinite(pb) & (ra > 0.0) & (rb > 0.0)
    ratio = np.full(pa.shape, np.nan, dtype=np.float64)
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio[ok] = 20.0 * np.log10(ra[ok] / rb[ok])
    j = int(np.nanargmax(np.abs(ratio))) if np.any(ok) else None
    return {
        "max_abs_ratio_db": None if j is None else round(abs(float(ratio[j])), 6),
        "max_abs_ratio_at_hz": None if j is None else round(float(frequencies_hz[j]), 6),
        "max_relative_delta_percent": relative_delta_percent(pa, pb, frequencies_hz),
        "max_relative_delta_at_hz": None if i is None else round(float(frequencies_hz[i]), 6),
        "max_abs_delta_pa": None if i is None else round(float(delta[i]), 9),
    }


# --------------------------------------------------------------------------- point series

def _excitation_series(pa: np.ndarray, pb: np.ndarray, frequencies_hz: np.ndarray,
                       eid_a: str, eid_b: str, per_input: Any) -> dict:
    common = {"id": eid_a, "b_id": eid_b, "per_input": per_input}
    if pa.ndim != 2:
        raise ValueError("pressure bases must be (nfreq, nobs)")
    if pa.shape[1] == 1:
        a1, b1 = pa[:, 0], pb[:, 0]
        ratio_db, delta_phase_deg = _series(a1, b1)
        common.update({
            "ratio_db": ratio_db,
            "delta_phase_deg": delta_phase_deg,
            "max_abs_ratio_db": _max_abs(ratio_db),
            "max_abs_delta_phase_deg": _max_abs(delta_phase_deg),
            **_whole_grid(a1, b1, frequencies_hz),
            "bands": _band_rows(a1, b1, frequencies_hz),
        })
        return common
    points = []
    for point_index in range(pa.shape[1]):
        a1, b1 = pa[:, point_index], pb[:, point_index]
        ratio_db, delta_phase_deg = _series(a1, b1)
        points.append({
            "point_index": point_index,
            "ratio_db": ratio_db,
            "delta_phase_deg": delta_phase_deg,
            "max_abs_ratio_db": _max_abs(ratio_db),
            "max_abs_delta_phase_deg": _max_abs(delta_phase_deg),
            **_whole_grid(a1, b1, frequencies_hz),
            "bands": _band_rows(a1, b1, frequencies_hz),
        })
    common["n_points"] = int(pa.shape[1])
    common["points"] = points
    return common


# --------------------------------------------------------------------------- public: compare

def hw_compare(root: Path, store: Path, a: str, b: str) -> dict:
    """A/B compare two solved cases per point-probe domain and per excitation, never summed.

    ``a`` and ``b`` are ``<experiment>/<case>`` keys with the same containment checks as
    ``data_hw._resolve_case``; both must have a solved ``run/``. Normal incomparabilities are
    refused as data (``ok: False`` with one token per mismatch), not raised.

    On success every point-probe domain carries, per excitation, ``ratio_db`` (20 log10 of the
    magnitude ratio, ``None`` where undefined) and ``delta_phase_deg`` (wrapped
    ``angle(p_a * conj(p_b))``), plus per-band and whole-grid maxima. ``max_relative_delta_percent``
    is the recorded-evidence statistic documented in the module docstring.
    """
    case_a, run_a = _run_dir(store, a)
    case_b, run_b = _run_dir(store, b)
    res_a = _read_run(a, case_a)
    res_b = _read_run(b, case_b)

    what_differs = _what_differs(_facts(store, a, case_a, res_a),
                                 _facts(store, b, case_b, res_b))
    mismatches = _mismatches(res_a, res_b)
    if mismatches:
        return {"ok": False, "a": a, "b": b,
                "mismatches": mismatches, "what_differs": what_differs}

    frequencies = np.asarray(res_a.frequencies_hz, dtype=np.float64)
    conv_a = {c.excitation_id: c for c in res_a.conversion}
    conv_b = {c.excitation_id: c for c in res_b.conversion}
    probes: list[dict] = []
    flat_bands: list[dict] = []

    for domain_id, probe_id in _probe_signature(res_a):
        obs = res_a.observation_sets[domain_id]
        bases_a = res_a.per_excitation_bases(domain_id)
        bases_b = res_b.per_excitation_bases(domain_id)
        excitations = []
        for eid_a, eid_b in zip(res_a.excitation_ids, res_b.excitation_ids):
            pa = np.asarray(bases_a[eid_a], dtype=np.complex128)
            pb = np.asarray(bases_b[eid_b], dtype=np.complex128)
            per_input = None if eid_a not in conv_a else conv_a[eid_a].to_per_input
            item = _excitation_series(pa, pb, frequencies, eid_a, eid_b, per_input)
            excitations.append(item)
            for point in (_point_bands(item)):
                for row in point["bands"]:
                    flat_bands.append({
                        "domain": domain_id, "probe_id": probe_id,
                        "point_index": point["point_index"],
                        "excitation": eid_a, "b_excitation": eid_b,
                        "per_input": per_input, **row,
                    })
        probes.append({
            "domain": domain_id,
            "probe_id": probe_id,
            "kind": obs.kind,
            "distance_m": obs.distance_m,
            "n_points": int(obs.count),
            "excitations": excitations,
        })

    return {
        "ok": True,
        "a": a,
        "b": b,
        "what_differs": what_differs,
        "probes": probes,
        "bands": flat_bands,
        "caption": _caption(probes),
        "band_note": BAND_NOTE,
    }


def _point_bands(item: dict) -> list[dict]:
    """Uniform ``[{point_index, bands}]`` view over a single-point or multi-point excitation."""
    if "points" in item:
        return item["points"]
    return [{"point_index": 0, "bands": item["bands"]}]


def _caption(probes: list[dict]) -> str:
    dists = sorted({round(float(p["distance_m"]), 2) for p in probes
                    if p.get("distance_m") is not None})
    where = " / ".join(f"{d:g} m" for d in dists) or "unknown distance"
    return (f"Observed at {where} point probes; not a far-field claim at the low end. "
            f"{_CAPTION_TAIL}")


# --------------------------------------------------------------------------- public: matrix

def _matrix_cell(root: Path, store: Path, key: str, declared: dict) -> dict:
    """One explicit matrix cell; a valid-format key with no case dir is ``missing``."""
    parts = str(key).strip("/").split("/")
    if len(parts) != 2 or not all(HW._KEY_PART.match(p) and ".." not in p for p in parts):
        raise ValueError(f"bad case key {key!r}: expected <experiment>/<case>")
    exp, name = parts
    base = HW.store_dir(store)
    candidate = (base / exp / name).resolve()
    decl = declared.get(key, {})
    cell = {
        "key": key,
        "state": "missing",
        "disk_state": "missing",
        "ref": decl.get("ref"),
        "gate": decl.get("gate"),
        "experiment": exp,
        "motor": decl.get("motor") or "UNDECLARED",
        "box": None,
        "horn_offset_mm": None,
    }
    if base not in candidate.parents or not candidate.is_dir():
        return cell
    row = HW._row(store, HW._resolve_case(store, key), declared)
    state = row["state"]
    cell.update({
        "state": "solved" if state == "solved" else "staged" if state == "staged" else "missing",
        "disk_state": state,
        "ref": row.get("ref") or decl.get("ref"),
        "gate": row.get("gate") or decl.get("gate"),
        "motor": row.get("motor") or decl.get("motor") or "UNDECLARED",
        "box": None if not row.get("box") else {k: row["box"].get(k) for k in (
            "width_mm", "height_mm", "depth_mm")},
        "horn_offset_mm": None if not row.get("horn") else row["horn"].get("translation_mm"),
    })
    return cell


def hw_compare_matrix(root: Path, store: Path, keys: list[str]) -> dict:
    """Adjacent-pair comparability for an explicit, ordered list of case keys.

    Cells are ``{key, state: solved|staged|missing, ref, gate, experiment, motor, box,
    horn_offset_mm}`` in the given order (``disk_state`` carries the richer ledger state). Each
    ``edges[i]`` describes the pair ``keys[i]``/``keys[i+1]`` by calling :func:`hw_compare`; the
    matrix never recomputes a delta itself. The view composes the grid; the payload stays plain.
    """
    if not isinstance(keys, (list, tuple)) or not all(isinstance(k, str) for k in keys):
        raise ValueError("keys must be a list of <experiment>/<case> strings")
    keys = list(keys)
    declared = HW._declared(HW.load_registry(root))
    cells = [_matrix_cell(root, store, key, declared) for key in keys]
    edges = []
    for left, right in zip(keys, keys[1:]):
        try:
            result = hw_compare(root, store, left, right)
        except (FileNotFoundError, ValueError) as exc:
            edges.append({"from": left, "to": right, "ok": False, "mismatches": [],
                          "error": f"{type(exc).__name__}: {exc}"})
            continue
        edges.append({
            "from": left,
            "to": right,
            "ok": bool(result.get("ok")),
            "mismatches": [m["token"] for m in result.get("mismatches", [])],
            "what_differs": result.get("what_differs"),
        })
    return {"keys": keys, "cells": cells, "edges": edges}
