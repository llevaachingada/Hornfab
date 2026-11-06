"""Read Boundary Lab exports (and generic CSV) into ``AbData``. Boundary Lab is never imported; its files are data.

Formats, all read from Boundary Lab's own source and docs (pinned in export_for_bl.BL_PIN):

* Polar text   ``H <angle>.txt`` / ``V <angle>.txt`` per angle, tab separated: ``freq_hz  spl_norm_db  [phase_deg]``.
               Levels are NORMALIZED to the 0 degree sample (``horizontal_spl_norm_db``); phase is relative to
               on-axis. (``blab/exporting/polar.py``)
* On-axis text ``freq_hz  spl_db  phase_deg``: ABSOLUTE dB re 20 uPa for 1 m/s drive, phase with the propagation
               delay distance/c removed, exp(+i w t). (``blab/exporting/on_axis.py``, ``live.py``)
* Balloon dir  ``metadata.json`` + ``topology.npz`` (freq_hz, directions_xyz, ...) + ``spl_db.npy`` (nf, npoint),
               NORMALIZED and clipped to the preference range. (``blab/exporting/balloon.py``)
* Tabular txt  ``# Boundary Lab - <title>`` / ``# <tab separated headers>`` / rows (``exporting/tabular.py``).
* Headless run ``manifest.json`` + ``frequencies/NNNNNN.{json,npz}`` + ``domains.{json,npz}``: raw complex pressure
               (Pa, 1 m/s, exp(+i w t)) on the polar arcs and the Fibonacci sphere, and the generalized radiation
               impedance in N s / m. (``blab/headless.py``)
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

import numpy as np

from ..constants import C_AIR
from .model import CANON_DRIVE, CANON_TIME, AbData

BL_RHO_DEFAULT = 1.21
_POLAR_NAME = re.compile(r"^(?P<plane>[HV])\s+(?P<angle>-?\d+(?:\.\d+)?)\.txt$")
ANGLE_LIMIT_DEG = 90.0


class ImportProblem(ValueError):
    """The files are not what we expected. The message says which file and what to send instead."""


# ------------------------------------------------------------------ text helpers

def parse_table(path) -> tuple[list[str] | None, np.ndarray]:
    """Whitespace/tab/comma separated numeric table. ``#`` lines are comments; the LAST ``#`` line before the data
    is returned as the header (split on tabs, falling back to commas) when it has as many fields as the data."""
    path = Path(path)
    header_line, rows = None, []
    for ln in path.read_text(encoding="utf-8", errors="replace").splitlines():
        s = ln.strip()
        if not s:
            continue
        if s.startswith("#"):
            header_line = s.lstrip("#").strip()
            continue
        parts = re.split(r"[\t,; ]+", s)
        try:
            rows.append([float(x) for x in parts])
        except ValueError:
            if not rows:                           # a plain (non-# ) header line
                header_line = s
                continue
            raise ImportProblem(f"{path}: non-numeric row {s[:60]!r}") from None
    if not rows:
        raise ImportProblem(f"{path}: no numeric rows")
    width = len(rows[0])
    if any(len(r) != width for r in rows):
        raise ImportProblem(f"{path}: rows have different numbers of columns")
    headers = None
    if header_line:
        h = [x.strip() for x in (header_line.split("\t") if "\t" in header_line else header_line.split(","))]
        if len(h) == width:
            headers = h
    return headers, np.asarray(rows, dtype=float)


def _same_freqs(a: np.ndarray, b: np.ndarray, what: str) -> None:
    if a.shape != b.shape or not np.allclose(a, b, rtol=1e-4, atol=1e-6):
        raise ImportProblem(f"{what}: frequency list differs from the other files "
                            f"({a.size} vs {b.size} points); all exports must come from the same solve")


# ------------------------------------------------------------------ GUI exports

def import_polar_dir(folder) -> dict:
    """Per-angle ``H <a>.txt`` / ``V <a>.txt`` files -> {'freqs','angles','spl_h','spl_v','phase_h','phase_v'}."""
    folder = Path(folder)
    files = {"H": {}, "V": {}}
    for f in sorted(folder.glob("*.txt")):
        m = _POLAR_NAME.match(f.name)
        if m:
            files[m["plane"]][float(m["angle"])] = f
    if not files["H"] and not files["V"]:
        raise ImportProblem(f"{folder}: no files named like 'H 0.txt' / 'V 15.txt' (File > Export Polar Data)")
    freqs, angles_all = None, sorted(set(files["H"]) | set(files["V"]))
    kept = [a for a in angles_all if abs(a) <= ANGLE_LIMIT_DEG + 1e-9]
    if 0.0 not in kept:
        raise ImportProblem(f"{folder}: there is no 0 degree file ('H 0.txt'); the on-axis reference is required")
    out = {"angles": np.asarray(kept), "cropped_from_deg": (min(angles_all), max(angles_all))}
    for plane in "HV":
        cols_spl, cols_ph = [], []
        for a in kept:
            f = files[plane].get(a)
            if f is None:
                cols_spl = None
                break
            _, d = parse_table(f)
            if d.shape[1] < 2:
                raise ImportProblem(f"{f}: expected at least 2 columns (frequency, SPL)")
            if freqs is None:
                freqs = d[:, 0]
            else:
                _same_freqs(freqs, d[:, 0], str(f))
            cols_spl.append(d[:, 1])
            cols_ph.append(d[:, 2] if d.shape[1] >= 3 else None)
        if cols_spl is None:
            out[f"spl_{plane.lower()}"] = out[f"phase_{plane.lower()}"] = None
            continue
        out[f"spl_{plane.lower()}"] = np.stack(cols_spl, axis=1)
        out[f"phase_{plane.lower()}"] = (np.stack(cols_ph, axis=1) if all(c is not None for c in cols_ph) else None)
    out["freqs"] = np.asarray(freqs)
    return out


def import_on_axis_file(path) -> dict:
    headers, d = parse_table(path)
    if d.shape[1] < 2:
        raise ImportProblem(f"{path}: expected frequency, SPL[, phase]")
    return {"freqs": d[:, 0], "spl": d[:, 1], "phase": d[:, 2] if d.shape[1] >= 3 else None}


def import_balloon_dir(folder) -> dict:
    folder = Path(folder)
    meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    if meta.get("schema") != "boundary-lab-balloon-export":
        raise ImportProblem(f"{folder}/metadata.json is not a Boundary Lab balloon export")
    with np.load(folder / "topology.npz") as z:
        freq, dirs = np.asarray(z["freq_hz"], dtype=float), np.asarray(z["directions_xyz"], dtype=float)
    spl = np.load(folder / "spl_db.npy").astype(float)
    if spl.shape != (freq.size, dirs.shape[0]):
        raise ImportProblem(f"{folder}: spl_db.npy {spl.shape} does not match topology ({freq.size}, {dirs.shape[0]})")
    order = np.argsort(freq)
    rng = meta.get("db_range") or {}
    return {"freqs": freq[order], "dirs": dirs, "spl": spl[order],
            "clip_db": (rng.get("min_db"), rng.get("max_db")), "schema_version": meta.get("schema_version")}


def import_tabular_impedance(path, *, area_m2: float | None = None, rho: float = BL_RHO_DEFAULT,
                             c: float = C_AIR) -> dict:
    """Impedance text with Real / Imag columns. Normalizes Z / (rho c Sd) when the header unit is physical (N s/m)."""
    headers, d = parse_table(path)
    if headers is None:
        raise ImportProblem(f"{path}: needs a '# Frequency (Hz)<TAB>... Real ...<TAB>... Imag ...' header line "
                            "(use import --impedance-csv with freq_hz,z_real,z_imag for hand-made files)")
    re_i = next((i for i, h in enumerate(headers) if "real" in h.lower()), None)
    im_i = next((i for i, h in enumerate(headers) if "imag" in h.lower()), None)
    if re_i is None or im_i is None:
        raise ImportProblem(f"{path}: could not find Real and Imag columns in {headers}")
    z = d[:, re_i] + 1j * d[:, im_i]
    unit_raw = bool(re.search(r"N\s*\*?\s*s\s*/\s*m", headers[re_i])) or "n·s/m" in headers[re_i].lower()
    norm = "already normalized (dimensionless)"
    if unit_raw:
        if not area_m2:
            raise ImportProblem(f"{path}: impedance is in N s/m; pass the driven area (handoff.json) to normalize")
        z = z / (rho * c * area_m2)
        norm = f"divided by rho*c*Sd with Sd={area_m2:.6g} m^2"
    return {"freqs": d[:, 0], "z": z, "normalization": norm, "headers": headers}


# ------------------------------------------------------------------ headless run folder

def _find_key(obj, key):
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            r = _find_key(v, key)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = _find_key(v, key)
            if r is not None:
                return r
    return None


def import_headless_run(run_dir, *, area_m2: float | None = None, label: str = "Boundary Lab (headless)") -> AbData:
    run = Path(run_dir)
    man = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    if man.get("schema") != "boundary-lab-headless-result":
        raise ImportProblem(f"{run}/manifest.json is not a Boundary Lab headless result")
    conj = "exp(-i" in str(man.get("phasor_convention", "exp(+i omega t)")).replace("ω", "omega")
    results = [r for r in man.get("results", []) if r]
    if not results:
        raise ImportProblem(f"{run}: no completed frequency (status {man.get('status')!r}, error {man.get('error')!r})")
    dom_meta = json.loads((run / "domains.json").read_text(encoding="utf-8"))["domains"]
    with np.load(run / "domains.npz") as dz:
        dom = {d["id"]: {"kind": d["kind"], "coords": {n: np.asarray(dz[k]) for n, k in d["coordinates"].items()}}
               for d in dom_meta}
    hp, vp, sp = "observation:horizontal-polar", "observation:vertical-polar", "observation:sphere"
    if hp not in dom:
        raise ImportProblem(f"{run}: no horizontal polar observation domain (was 'include_project_observations' off?)")
    angles_all = np.asarray(dom[hp]["coords"]["angle_deg"], dtype=float)
    keep = np.abs(angles_all) <= ANGLE_LIMIT_DEG + 1e-9
    ordr = np.argsort(angles_all[keep])
    angles = angles_all[keep][ordr]
    freqs, ph_l, pv_l, ps_l, zr_l = [], [], [], [], []
    for r in sorted(results, key=lambda r: r["freq_hz"]):
        md = json.loads((run / r["metadata_file"]).read_text(encoding="utf-8"))
        with np.load(run / r["arrays_file"]) as az:
            q = {item["id"]: np.asarray(az[item["key"]]) for item in md["quantities"]}
        freqs.append(float(md["freq_hz"]))

        def pick(qid):
            v = q.get(qid)
            if v is None:
                return None
            v = np.asarray(v)
            return v[0] if v.ndim == 2 else v
        h = pick("acoustic:pressure:horizontal-polar")
        v = pick("acoustic:pressure:vertical-polar")
        s = pick("acoustic:pressure:sphere")
        if h is None:
            raise ImportProblem(f"{run}: frequency {md['freq_hz']} has no horizontal polar pressure")
        ph_l.append(h[keep][ordr])
        pv_l.append(None if v is None else v[keep][ordr])
        ps_l.append(s)
        z = pick("acoustic:radiation-impedance")
        zr_l.append(None if z is None else complex(np.asarray(z).ravel()[0]))
    f = np.asarray(freqs)
    ph = np.stack(ph_l).astype(np.complex128)
    pv = np.stack(pv_l).astype(np.complex128) if all(x is not None for x in pv_l) else None
    ps = np.stack(ps_l).astype(np.complex128) if all(x is not None for x in ps_l) else None
    if conj:
        ph, pv, ps = np.conj(ph), (None if pv is None else np.conj(pv)), (None if ps is None else np.conj(ps))
    dirs = None
    if ps is not None and sp in dom:
        th, phi = dom[sp]["coords"]["theta_polar_rad"], dom[sp]["coords"]["phi_azimuth_rad"]
        dirs = np.column_stack([np.sin(th) * np.cos(phi), np.sin(th) * np.sin(phi), np.cos(th)]).astype(float)
    # distance: project snapshot preferences, else the polar arc radius
    snap = run / man.get("project_file", "project.snapshot.blab.json")
    dist = None
    if snap.exists():
        pref = (json.loads(snap.read_text(encoding="utf-8")).get("project_preferences") or {})
        dist = pref.get("polar_observation_distance_m")
    if dist is None and "points_m" in dom[hp]["coords"]:
        dist = float(np.linalg.norm(dom[hp]["coords"]["points_m"], axis=1).mean())
    rho, cc = BL_RHO_DEFAULT, C_AIR
    csys = run / man.get("compiled_system_file", "compiled-system.json")
    if csys.exists():
        cj = json.loads(csys.read_text(encoding="utf-8"))
        rho = float(_find_key(cj, "density_kg_per_m3") or rho)
        cc = float(_find_key(cj, "sound_speed_m_per_s") or cc)
    z_norm = None
    if all(x is not None for x in zr_l):
        area = area_m2
        for d in dom.values():
            if "effective_area_m2" in d["coords"]:
                area = float(np.asarray(d["coords"]["effective_area_m2"]).ravel()[0])
        if area:
            z_norm = np.asarray(zr_l) / (rho * cc * area)
            if conj:
                z_norm = np.conj(z_norm)
    meta = {"drive": CANON_DRIVE, "time_convention": CANON_TIME, "distance_m": dist, "rho": rho, "sound_speed": cc,
            "bl_manifest": {k: man.get(k) for k in ("status", "backend_id", "solve_kind", "solver_options",
                                                    "project_sha256", "meshes")},
            "bl_engine_runs": man.get("engine_runs"), "route": "headless", "angles_cropped_from_deg":
            [float(angles_all.min()), float(angles_all.max())], "n_frequencies_completed": len(freqs),
            "n_frequencies_requested": len(man.get("frequencies_hz", [])), "notes": []}
    if meta["n_frequencies_completed"] < meta["n_frequencies_requested"]:
        meta["notes"].append("run is incomplete: only the completed frequencies are compared")
    kw = {}
    if dirs is not None:
        with np.errstate(divide="ignore"):
            kw.update(balloon_dirs=dirs, balloon_spl_db=20 * np.log10(np.abs(ps) / 20e-6), balloon_kind="fibonacci")
    if z_norm is not None:
        kw["z_norm"] = z_norm
    return AbData(label=label, source="boundary_lab", freqs_hz=f, angles_deg=angles, p_h=ph, p_v=pv,
                  level="absolute", meta=meta, **kw)


# ------------------------------------------------------------------ GUI folder / auto-detect

def import_gui_folder(root, *, handoff: dict | None = None, label: str = "Boundary Lab") -> AbData:
    """``results_from_friend``-style folder with polar/, on_axis/, balloon/, impedance/ (any subset), or one of those
    folders directly."""
    root = Path(root)
    polar_dir = next((d for d in (root / "polar", root) if d.is_dir() and any(_POLAR_NAME.match(f.name) for f in d.glob("*.txt"))), None)
    on_axis = None
    for d in (root / "on_axis", root):
        if d.is_dir():
            cands = sorted(d.glob("on_axis*.txt")) or ([] if d == root else sorted(d.glob("*.txt")))
            if cands:
                on_axis = cands[0]
                break
    balloon_dir = next((d for d in (root / "balloon", root) if (d / "metadata.json").exists() and (d / "topology.npz").exists()), None)
    imp = None
    for d in (root / "impedance", root):
        if d.is_dir():
            cands = sorted(d.glob("impedance*.txt")) + sorted(d.glob("*impedance*.txt"))
            if cands:
                imp = cands[0]
                break
    if polar_dir is None and on_axis is None and balloon_dir is None:
        raise ImportProblem(f"{root}: found no Boundary Lab polar / on-axis / balloon export")
    meta = {"drive": CANON_DRIVE, "time_convention": CANON_TIME, "route": "gui", "notes": [],
            "rho": BL_RHO_DEFAULT, "sound_speed": C_AIR, "axis_phase_aligned": True}
    if handoff:
        meta["distance_m"] = handoff.get("observation", {}).get("distance_m")
        meta["rho"] = float(handoff.get("material", {}).get("project_region_density_kg_m3", BL_RHO_DEFAULT))
    kw: dict = {}
    freqs = angles = None
    level = "normalized"
    if polar_dir is not None:
        pol = import_polar_dir(polar_dir)
        freqs, angles = pol["freqs"], pol["angles"]
        kw.update(spl_h_db=pol["spl_h"], spl_v_db=pol["spl_v"], phase_h_deg=pol["phase_h"], phase_v_deg=pol["phase_v"])
        meta["angles_cropped_from_deg"] = list(pol["cropped_from_deg"])
        meta["notes"].append("polar files are NORMALIZED to the 0 degree sample (absolute level is only in the on-axis file)")
        if pol["spl_h"] is not None and pol["spl_v"] is not None:
            ax = int(np.argmin(np.abs(angles)))
            if np.abs(pol["spl_h"][:, ax]).max() > 0.05:
                meta["notes"].append("H 0 is not 0 dB in the polar files: a normalization angle other than 0 was used")
    if on_axis is not None:
        oa = import_on_axis_file(on_axis)
        if freqs is None:
            freqs = oa["freqs"]
        else:
            _same_freqs(freqs, oa["freqs"], str(on_axis))
        kw["on_axis_spl_db"] = oa["spl"]
        kw["on_axis_phase_deg"] = oa["phase"]
    if balloon_dir is not None:
        bl = import_balloon_dir(balloon_dir)
        if freqs is None:
            freqs = bl["freqs"]
        else:
            _same_freqs(freqs, bl["freqs"], str(balloon_dir))
        kw.update(balloon_dirs=bl["dirs"], balloon_spl_db=bl["spl"], balloon_kind="fibonacci")
        meta["clip_db"] = list(bl["clip_db"])
        meta["notes"].append(f"balloon clipped to {bl['clip_db'][0]}..{bl['clip_db'][1]} dB by Boundary Lab's SPL Min/Max preference")
    if imp is not None:
        area = (handoff or {}).get("mesh", {}).get("driven_area_m2_full")
        zi = import_tabular_impedance(imp, area_m2=area)
        if freqs is not None and zi["freqs"].shape == freqs.shape and np.allclose(zi["freqs"], freqs, rtol=1e-4):
            kw["z_norm"] = zi["z"]
            meta["impedance_normalization"] = zi["normalization"]
        else:
            meta["notes"].append("impedance file has a different frequency list and was ignored")
    if angles is None:
        angles = np.array([0.0])
    if freqs is None:
        raise ImportProblem(f"{root}: could not determine the frequency list")
    return AbData(label=label, source="boundary_lab", freqs_hz=freqs, angles_deg=angles, level=level, meta=meta, **kw)


def import_bl(path, *, handoff: dict | None = None, label: str = "Boundary Lab") -> AbData:
    """Auto-detect: a headless run folder (manifest.json), a ``results_from_friend`` folder (prefers
    ``headless_run/`` when it holds a manifest, else the GUI exports), or an ``AbData`` folder."""
    p = Path(path)
    area = (handoff or {}).get("mesh", {}).get("driven_area_m2_full")
    if (p / "abdata.json").exists():
        return AbData.load(p)
    if (p / "manifest.json").exists():
        return import_headless_run(p, area_m2=area, label=label)
    hl = p / "headless_run"
    if (hl / "manifest.json").exists():
        d = import_headless_run(hl, area_m2=area, label=label)
        if (p / "polar").is_dir() and any(_POLAR_NAME.match(f.name) for f in (p / "polar").glob("*.txt")):
            d.meta["notes"].append("both headless_run and GUI polar exports exist; the headless run is used (raw complex data)")
        return d
    return import_gui_folder(p, handoff=handoff, label=label)


# ------------------------------------------------------------------ generic CSV

def import_generic_csv(*, polar_csv=None, on_axis_csv=None, impedance_csv=None, level: str = "absolute",
                       distance_m: float | None = None, label: str = "CSV", source: str = "csv",
                       drive_note: str = "assumed to be the canonical 1 m/s velocity basis") -> AbData:
    """Hand-made or other-tool data. Formats (header row required, names exact):

    * polar:     ``freq_hz,plane,angle_deg,spl_db[,phase_deg]``   plane is H or V
    * on-axis:   ``freq_hz,spl_db[,phase_deg]``
    * impedance: ``freq_hz,z_real,z_imag``    (Z / (rho c S), exp(+i w t))
    Rows are never interpolated or filled in; the frequency list is the union actually present and every table must
    use the same list.
    """
    kw: dict = {}
    freqs = angles = None
    if polar_csv:
        rows = list(csv.DictReader(Path(polar_csv).read_text(encoding="utf-8").splitlines()))
        need = {"freq_hz", "plane", "angle_deg", "spl_db"}
        if not rows or not need <= set(rows[0]):
            raise ImportProblem(f"{polar_csv}: header must contain {sorted(need)}")
        freqs = np.array(sorted({float(r["freq_hz"]) for r in rows}))
        angles = np.array(sorted({float(r["angle_deg"]) for r in rows if abs(float(r["angle_deg"])) <= ANGLE_LIMIT_DEG + 1e-9}))
        fi = {f: i for i, f in enumerate(freqs)}
        ai = {a: i for i, a in enumerate(angles)}
        for pl in "HV":
            spl = np.full((freqs.size, angles.size), np.nan)
            ph = np.full_like(spl, np.nan)
            for r in rows:
                if r["plane"].strip().upper() != pl or float(r["angle_deg"]) not in ai:
                    continue
                spl[fi[float(r["freq_hz"])], ai[float(r["angle_deg"])]] = float(r["spl_db"])
                if r.get("phase_deg") not in (None, ""):
                    ph[fi[float(r["freq_hz"])], ai[float(r["angle_deg"])]] = float(r["phase_deg"])
            if np.isfinite(spl).any():
                if not np.isfinite(spl).all():
                    raise ImportProblem(f"{polar_csv}: plane {pl} has missing (freq, angle) cells; no value is invented")
                kw[f"spl_{pl.lower()}_db"] = spl
                if np.isfinite(ph).all():
                    kw[f"phase_{pl.lower()}_deg"] = ph
    if on_axis_csv:
        headers, d = parse_table(on_axis_csv)
        if freqs is None:
            freqs = d[:, 0]
        else:
            _same_freqs(freqs, d[:, 0], str(on_axis_csv))
        kw["on_axis_spl_db"] = d[:, 1]
        if d.shape[1] >= 3:
            kw["on_axis_phase_deg"] = d[:, 2]
    if impedance_csv:
        headers, d = parse_table(impedance_csv)
        if freqs is None:
            freqs = d[:, 0]
        else:
            _same_freqs(freqs, d[:, 0], str(impedance_csv))
        kw["z_norm"] = d[:, 1] + 1j * d[:, 2]
    if freqs is None:
        raise ImportProblem("give at least one of polar_csv / on_axis_csv / impedance_csv")
    if angles is None:
        angles = np.array([0.0])
    meta = {"drive": CANON_DRIVE, "time_convention": CANON_TIME, "distance_m": distance_m, "route": "csv",
            "axis_phase_aligned": True, "notes": [drive_note]}
    return AbData(label=label, source=source, freqs_hz=freqs, angles_deg=angles, level=level, meta=meta, **kw)
