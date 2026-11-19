"""Import boundary: saved horn solve -> canonical system basis (phase-honest conversion).

Stored HornFab complex fields are pressure per unit normal **acceleration** in the
``exp(-i omega t)`` convention (``solve/beat.py``; see BASELINE.md). The system contract basis is
Pa per 1 m/s velocity in ``exp(+j omega t)``. The conversion is the in-repo tested seam
``compare/hornfab_side.accel_to_canonical`` (``np.conj(p * (-1j * w))``; verified in
``tests/test_solve_phasor.py`` / ``tests/test_compare_ab_model.py`` with its round-trip inverse).

Honesty rules encoded here:
* A converted asset is ``SCREEN_COMPLEX_APPROX`` — never ``EXACT_COMPLEX``: it is an isolated-horn
  unsolved-for-installation basis whose stored metadata is thin (no origin declaration; distance
  when present). Delay/coherent claims are allowed ONLY as screening labels.
* Magnitude screens keep the stored ``spl_*`` arrays untouched (absolute dB SPL).
* Nothing in ``runs/`` is written; reads use ``solve/cache.load_response`` only.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from hornlab_search.compare.hornfab_side import accel_to_canonical
from hornlab_search.solve import cache as solve_cache
from hornlab_search.system import contracts as C
from hornlab_search.system import horn_assets as HA
from hornlab_search.system.compatibility import provenance_flags

__all__ = [
    "convert_asset",
    "find_asset",
    "ConvertedHorn",
]

CLAIMS_ALLOWED: tuple[str, ...] = (
    "level_only_cross_tier",
    "screen_complex_approx",
)
CLAIMS_REFUSED: tuple[str, ...] = (
    "absolute_pa_per_volt",
    "installed_directivity",
    "installed_system_score",
)


@dataclass(frozen=True)
class ConvertedHorn:
    """One imported horn: the canonical-basis response plus its provenance records."""

    asset: C.HornAsset
    response: C.SystemResponse
    conversion: Mapping[str, Any]
    data_quality: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset_id": self.asset.asset_id,
            "quality_stored": self.asset.quality,
            "fidelity": self.response.fidelity,
            "excitations": list(self.response.excitation_names),
            "freq_lo_hz": float(self.response.frequencies_hz[0]),
            "freq_hi_hz": float(self.response.frequencies_hz[-1]),
            "n_freqs": int(self.response.frequencies_hz.size),
            "conversion": dict(self.conversion),
            "data_quality": dict(self.data_quality),
        }


def _meta(resp: Any) -> Mapping[str, Any]:
    meta = getattr(resp, "meta", None)
    return meta if isinstance(meta, Mapping) else {}


def _freq_axis(resp: Any) -> np.ndarray:
    f = np.asarray(resp.freqs_hz, dtype=np.float64).reshape(-1)
    if f.size < 2 or not np.all(np.isfinite(f)) or np.any(f <= 0.0):
        raise C.DataQualityError(f"asset response has no usable frequency axis: {f[:5]!r}")
    return f


def _balloon_dirs(resp: Any) -> np.ndarray:
    dirs = getattr(resp, "balloon_dirs", None)
    if dirs is None:
        raise C.DataQualityError("no balloon_dirs in stored response")
    d = np.asarray(dirs, dtype=np.float64)
    if d.ndim != 2 or d.shape[1] != 3:
        raise C.DataQualityError(f"balloon_dirs must be (nb, 3), got {d.shape}")
    return d


def _basis(basis: C.SourceBasis | None, angular_frame: str) -> C.SourceBasis:
    if basis is None:
        return C.SourceBasis(
            per_input="normal_velocity_mps", distance_m=None, origin_xyz_m=None,
            angular_frame="unknown", source_geometry_hash=None)
    # Re-declare on the canonical side: the import itself proves per_input/time; stored
    # distance/origin are carried when present, else left None and recorded UNKNOWN.
    return C.SourceBasis(
        per_input="normal_velocity_mps",
        distance_m=basis.distance_m,
        origin_xyz_m=basis.origin_xyz_m,
        angular_frame=angular_frame,
        source_geometry_hash=basis.source_geometry_hash,
    )


def convert_asset(asset: C.HornAsset, *, mode: str = "balloon") -> ConvertedHorn:
    """Convert one inventoried asset into a canonical-basis SystemResponse.

    ``mode`` picks the observation set when several exist: ``"balloon"`` (full sphere,
    preferred for polar screening) or ``"cuts"`` (H/V angle cuts). A response with neither
    complex field returns a magnitude-only SystemResponse (``p_by_excitation=None``).
    """
    if mode not in ("balloon", "cuts"):
        raise C.SchemaError(f"mode must be 'balloon' or 'cuts', got {mode!r}")
    resp = solve_cache.load_response(Path(asset.response_path))
    f = _freq_axis(resp)
    meta = _meta(resp)
    flags = provenance_flags(asset)
    distance = HA._distance_m(meta)
    origin = HA._origin_xyz(meta)

    base_basis = C.SourceBasis(
        per_input="normal_velocity_mps",
        distance_m=distance,
        origin_xyz_m=origin,
        angular_frame=HA._angular_frame(frozenset(asset.available_fields)),
        source_geometry_hash=asset.design_hash,
    )
    conversion = {
        "from_drive": "unit_normal_acceleration",
        "from_time_exp(-i omega t)": True,
        "to_per_input": "normal_velocity_mps",
        "to_time": "exp(+jomega_t)",
        "via": "hornlab_search.compare.hornfab_side.accel_to_canonical",
        "magnitude_shift_db": "exact +20*log10(2*pi*f) built into the conversion",
        "origin_declared": origin is not None,
        "distance_m": distance,
    }
    data_quality = {
        "phase_qualified": False,
        "phase_basis": "converted_stored_accel",
        "stored_time_convention": asset.source_basis.time_convention
        if asset.source_basis is not None else "unknown",
        "provenance_stale": bool(flags.stale),
        "claims_allowed": CLAIMS_ALLOWED,
        "claims_refused": CLAIMS_REFUSED,
    }

    if mode == "balloon" and "p_balloon" in asset.available_fields:
        p_bal = accel_to_canonical(np.asarray(resp.p_balloon), f)
        dirs = _balloon_dirs(resp)
        response = C.SystemResponse(
            frequencies_hz=f,
            excitation_names=("horn",),
            p_by_excitation={"horn": np.asarray(p_bal, dtype=np.complex128)},
            excitation_bases={"horn": _basis(base_basis, "cartesian_dirs")},
            p_total=None,
            magnitude_screen=(None if resp.spl_balloon_db is None
                              else np.asarray(resp.spl_balloon_db, dtype=np.float64)),
            observation_directions=dirs,
            observation_angles_deg=None,
            fidelity="SCREEN_COMPLEX_APPROX",
            physics_provenance={"asset_id": asset.asset_id, **conversion},
            data_quality=data_quality,
        )
        return ConvertedHorn(asset=asset, response=response,
                             conversion=conversion, data_quality=data_quality)

    if "p_h" in asset.available_fields or "p_v" in asset.available_fields:
        ph = np.asarray(resp.p_h) if resp.p_h is not None else None
        pv = np.asarray(resp.p_v) if resp.p_v is not None else None
        na = 0 if ph is None else ph.shape[1]
        nv = 0 if pv is None else pv.shape[1]
        cols = []
        if ph is not None:
            cols.append(np.asarray(ph, dtype=np.complex128))
        if pv is not None:
            cols.append(np.asarray(pv, dtype=np.complex128))
        p = np.concatenate(cols, axis=1) if len(cols) > 1 else cols[0]
        p = accel_to_canonical(p, f)
        response = C.SystemResponse(
            frequencies_hz=f,
            excitation_names=("horn",),
            p_by_excitation={"horn": np.asarray(p, dtype=np.complex128)},
            excitation_bases={"horn": _basis(base_basis, "hornfab_cuts_hv")},
            p_total=None,
            magnitude_screen=None,
            observation_directions=None,
            observation_angles_deg=("h_deg_0_%d" % na, "v_deg_%d_%d" % (na, na + nv)),
            fidelity="SCREEN_COMPLEX_APPROX",
            physics_provenance={"asset_id": asset.asset_id, **conversion},
            data_quality=data_quality,
        )
        return ConvertedHorn(asset=asset, response=response,
                             conversion=conversion, data_quality=data_quality)

    # magnitude-only fallback: stored dB arrays as-is, no excitation fields
    screen = None
    for name in ("spl_balloon_db", "spl_h_db", "spl_v_db"):
        arr = getattr(resp, name, None)
        if arr is not None:
            screen = np.asarray(arr, dtype=np.float64)
            break
    response = C.SystemResponse(
        frequencies_hz=f,
        excitation_names=(),
        p_by_excitation=None,
        excitation_bases={},
        p_total=None,
        magnitude_screen=screen,
        observation_directions=(np.asarray(resp.balloon_dirs, dtype=np.float64)
                                if getattr(resp, "balloon_dirs", None) is not None else None),
        observation_angles_deg=None,
        fidelity="SCREEN_MAGNITUDE",
        physics_provenance={"asset_id": asset.asset_id},
        data_quality={**data_quality, "reason": "no complex fields stored"},
    )
    return ConvertedHorn(asset=asset, response=response,
                         conversion=conversion, data_quality=data_quality)


def find_asset(asset_id: str, root: str | os.PathLike[str] | None = None,
               *, scan_limit: int = 300) -> C.HornAsset:
    """Newest-first bounded scan for one asset id (read-only; early stop on match)."""
    if not asset_id:
        raise C.SchemaError("asset_id must be non-empty")
    runs = HA.default_runs_root() if root is None else Path(root)
    seen = 0
    # inventory_runs yields assets in run-dir order; use it in bounded chunks so a huge runs
    # root cannot stall the pilot. Re-instantiating per chunk is cheap relative to npz loads.
    chunk = 40
    run_dirs = HA._run_dirs(runs, scan_limit)
    for start in range(0, len(run_dirs), chunk):
        for run_dir in run_dirs[start:start + chunk]:
            seen += 1
            for asset in HA.inventory_run(run_dir):
                if asset.asset_id == asset_id:
                    return asset
    raise C.DataQualityError(
        f"asset_id {asset_id!r} not found in the newest {seen} run dirs under {runs}; "
        "raise --scan-limit or pass an explicit --runs-root")
