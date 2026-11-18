"""Canonical reader for a real Boundary Lab (BL) headless solve result directory.

BL is read-only research here: this module never imports ``blab``, never starts a solve and
never writes into a result directory. It parses the *output files* BL documents and writes,
into the frozen ``hornlab_search.system.contracts`` v1 basis form.

Documented artifact (BL 0.5.0, git ``15f9a89245a9adfec8c2f0006c164953ce381e58``)
------------------------------------------------------------------------------
``HeadlessResultWriter`` (``src/blab/headless.py:399-541``) writes one self-describing
directory per run::

    <run>/
      manifest.json                 schema/version/status/phasor convention/frequency axis/
                                    excitation ids/completion mask/results index/meshes
      project.snapshot.blab.json    project copy at run start
      request.json                  public request overlay
      compiled-system.json          compiled system incl. excitation_ports[].kind
      domains.json                  result-domain metadata (frequency invariant)
      domains.npz                   result-domain coordinate/topology arrays
      frequencies/
        000000.json                 freq_hz, excitation ids, quantity -> npz key map
        000000.npz                  arrays keyed q0000, q0001, ... (one per quantity)

Per frequency, ``write_result`` (``headless.py:451-501``) stores one complex array per
quantity, and the JSON side records ``{key, id, quantity, unit, target_id, axes, shape,
dtype, metadata}``. ``canonicalize_observation_result``
(``src/blab/system_solve.py:442-471``) splits the compact ``ui:exterior-pressure`` block
(shape ``(excitation, observation)``, verified at ``system_solve.py:452-453``) into named
observation quantities whose ``target_id`` is a domain id in ``domains.json``.

Established units / convention / provenance
-------------------------------------------
* Pressure quantity: ``quantity == "exterior_pressure"``, ``unit == "Pa"``; array axes
  ``("excitation", "observation")`` (``docs/Coupled Solver.md:516-524``).
* Phasors: ``exp(+i omega t)``, RMS (``docs/advanced/Phasor Convention.md:1-21``,
  ``docs/advanced/cli-workflow.md:254-260,284-289``). Canonical contract token is
  ``exp(+jomega_t)``; the mapping is recorded per excitation. Legacy
  ``exp(-i omega t)`` is conjugated exactly once, as BL itself documents
  (``src/blab/phasor.py:7-17``).
* Per-input normalisation: ``1 m/s`` for ``normal_velocity`` ports and ``2.83 V`` for
  ``voltage`` ports (``docs/Physical System Model.md:357-389``); port kind comes from
  ``compiled-system.json`` ``excitation_ports[].kind``. These are carried **per
  excitation**: ``Pa / V_rms`` and ``Pa / (m/s)`` are not comparable sensitivity
  references, and :func:`BLHeadlessResult.assert_shared_sensitivity_reference` refuses to
  pretend otherwise.
* Observation frame: points are metres in the project global frame
  (``docs/advanced/cli-workflow.md:124-126``); this reader declares that frame origin
  ``(0, 0, 0)`` and records the source of every observation field. ``SourceBasis.angular_frame``
  carries the BL domain id (e.g. ``bl_polar_observation:observation:horizontal-polar``) because
  two result domains can share a kind but are different observation sets.

What cannot be verified without a real run
------------------------------------------
The literal ``axes`` values written for ``exterior_pressure`` are copied verbatim from the
BEAT engine result (``headless.py:469`` copies ``combined.axes``; the Python source never
defines their labels). The documented order is ``excitation, observation``
(``docs/Coupled Solver.md:516-524``); this reader prefers the JSON labels and falls back to
the documented shape order, recording ``BLOCKED_BY_BL_RESULT_FORMAT`` in provenance when it
must.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Mapping

import numpy as np

from hornlab_search.system import contracts as C

__all__ = [
    "BL_HEADLESS_SCHEMA",
    "BL_HEADLESS_SCHEMA_VERSION",
    "BL_INSTALL_COMMIT",
    "BL_PHASOR_CONVENTION",
    "BL_PRESSURE_QUANTITY",
    "BL_PRESSURE_UNIT",
    "BL_SOURCE_PINS",
    "BL_RESULT_TOKENS",
    "BLObservationSet",
    "BLPressureBasis",
    "BLUnitConversion",
    "BLResultProvenance",
    "BLHeadlessResult",
    "is_bl_headless_result_dir",
    "read_bl_headless_result",
    "to_system_response",
]

# --------------------------------------------------------------------------- BL schema constants

BL_HEADLESS_SCHEMA = "boundary-lab-headless-result"
BL_HEADLESS_SCHEMA_VERSION = 2
BL_PRESSURE_QUANTITY = "exterior_pressure"
BL_PRESSURE_UNIT = "Pa"

#: Installed BL clone HEAD the schema below was read from (read-only research).
BL_INSTALL_COMMIT = "15f9a89245a9adfec8c2f0006c164953ce381e58"

#: BL's canonical phasor label (``src/blab/phasor.py:8``). Canonical contract label is
#: ``contracts.TIME_CONVENTION``; the two differ only in spelling and are mapped below.
BL_PHASOR_CONVENTION = "exp(+i omega t)"
BL_LEGACY_PHASOR_CONVENTION = "exp(-i omega t)"

#: ``(path, lines read, sha256)`` for every BL file this schema is grounded in.
BL_SOURCE_PINS: tuple[tuple[str, str, str], ...] = (
    ("src/blab/headless.py", "392-396,399-449,451-501,510-541",
     "8eed65739086d7d865c5296e2ce4040e322ab84be257e58bb8d5adcf1c923fee"),
    ("src/blab/system_solve.py", "215-230,442-471",
     "8ac0b7177b7c7c1ee7c03c9bc37579c23c8474170664128c900dbfe3696008b2"),
    ("src/blab/system_contract.py", "66-83,329-336",
     "027bdb1d627cd48492f34bf49c97b3080f3d983126e4b8c2178d81e6e9d740a4"),
    ("src/blab/phasor.py", "7-17",
     "7541a55057758573a6c89a7c54c13ae1dfcff033cdd47d48601bc45027878d3f"),
    ("src/blab/solvers/coupled_backend.py", "210-222",
     "e6122aa57b09170406702b9088a2afcfc8d5da9411893312ff50a8bfcb5930ba"),
    ("src/blab/solve_results/model.py", "29-48,91-103",
     "81263bd97577f295b03b32993d1aa3e7b60f18badaeb7e76bcb999cbc73cd007"),
    ("src/blab/physical_model.py", "51-62",
     "28edb2fd3068eb0a52256e524988103a2f8a9e149511bde4fce753de30c3a05b"),
    ("docs/advanced/cli-workflow.md", "124-126,254-260,266-294",
     "85a03b8f48426d8041c79e1f5949f1e3dbb9e993a2bba3fafa740d76a98f18a0"),
    ("docs/advanced/Phasor Convention.md", "1-21",
     "ce3b252f44d51c9714256f7190569fa334679450d5258cbf79a3b4e0b987222d"),
    ("docs/Physical System Model.md", "357-389",
     "79f4677b371842c43648288bf6095cd762ea3bccebad16945303876e54f79858"),
    ("docs/Coupled Solver.md", "500-528",
     "a1ad6751ea6ca809635d90ec795556d3b3b046cf037955fe804edaf813ff6412"),
    ("docs/Model Assumptions.md", "35-46",
     "cd8c45f1e889544a010678eeed0bc5db6896a3c3ab4ff9b7e8504bbb06d66271"),
    ("docs/Inputs and Outputs.md", "112-117,150-152",
     "2f16f5ce4b1d9c59644e2a3e849749f0174a4c73b2aca66584e1bdd802f3cb0a"),
)

#: Error tokens emitted by this module (``"<TOKEN>: detail"`` message form).
BL_RESULT_TOKENS: tuple[str, ...] = (
    "BL_RESULT_NOT_FOUND",
    "SCHEMA_MISMATCH",
    "MAGNITUDE_ONLY",
    "PHASE_ALIGNMENT_UNAVAILABLE",
    "PHASOR_CONVENTION_UNSUPPORTED",
    "EXCITATION_BASIS_UNKNOWN",
    "OBSERVATION_METADATA_MISSING",
    "UNITS_UNSUPPORTED",
    "INCOMPLETE_RUN",
    "FREQUENCY_AXIS_MISMATCH",
    "SENSITIVITY_REFERENCE_MISMATCH",
    "BLOCKED_BY_BL_RESULT_FORMAT",
)

#: Domain kind -> declared sampling-frame prefix. The domain id is appended because two BL result
#: domains (e.g. the horizontal and vertical polar planes) can share one kind but are different
#: observation sets; ``SourceBasis.compatible_for_sum_with`` compares this string alone, so keeping
#: the id in it refuses a geometrically meaningless cross-plane sum. Prefixes are deliberately
#: distinct from the HornFab tokens (``hornfab_cuts_hv`` / ``cartesian_dirs``).
_ANGULAR_FRAME_BY_KIND: Mapping[str, str] = {
    "polar_observation": "bl_polar_observation",
    "spherical_observation": "bl_spherical_observation",
    "point_probe": "bl_point_probe",
}

#: The project global frame is the declared observation frame (BL docs, all coordinates in
#: metres). The origin value is the frame origin, not an acoustic source centre.
_FRAME_ORIGIN_XYZ_M: tuple[float, float, float] = (0.0, 0.0, 0.0)
_FRAME_ORIGIN_SOURCE = (
    "BL project global frame origin (0,0,0); all result-domain points_m are metres in that "
    "frame (docs/advanced/cli-workflow.md:124-126)"
)

_PER_INPUT_BY_PORT_KIND: Mapping[str, Literal["V_rms", "normal_velocity_mps"]] = {
    "normal_velocity": "normal_velocity_mps",
    "voltage": "V_rms",
}
_PER_INPUT_DECLARATION: Mapping[str, str] = {
    "normal_velocity_mps": "1 m/s normal-velocity reference (BL canonical basis)",
    "V_rms": "2.83 V voltage reference, RMS phasors (BL canonical basis)",
}


# --------------------------------------------------------------------------- errors / helpers

def _error(token: str, detail: str) -> C.DataQualityError:
    if token not in BL_RESULT_TOKENS:
        raise AssertionError(f"undeclared BL result token {token!r}")
    return C.DataQualityError(f"{token}: {detail}")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path, token: str, what: str) -> Any:
    if not path.is_file():
        raise _error(token, f"{what} not found: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise _error(token, f"unreadable {what} {path}: {exc}") from None


def _require_mapping(value: Any, what: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise _error("SCHEMA_MISMATCH", f"{what} must be a JSON object, got {type(value).__name__}")
    return value


def _require_key(mapping: Mapping[str, Any], key: str, what: str) -> Any:
    if key not in mapping:
        raise _error("SCHEMA_MISMATCH", f"{what} is missing required key {key!r}")
    return mapping[key]


def is_bl_headless_result_dir(path: str | Path) -> bool:
    """True when ``path`` looks like the documented BL headless result directory."""
    manifest = Path(path) / "manifest.json"
    if not manifest.is_file():
        return False
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return (isinstance(payload, dict)
            and payload.get("schema") == BL_HEADLESS_SCHEMA
            and isinstance(payload.get("schema_version"), int))


# --------------------------------------------------------------------------- value records

@dataclass(frozen=True)
class BLObservationSet:
    """One BL result domain's observation coordinates, in the project global frame (metres).

    ``distance_m`` is the common radius when every sample is equidistant from the frame
    origin, else ``None`` (a mixed-radius domain cannot be summed as one field). It is
    derived from ``|points_m|`` and the derivation source is recorded.
    """

    domain_id: str
    kind: str
    points_m: np.ndarray                     # (nobs, 3) float64
    angles_deg: np.ndarray | None            # (nobs,) when the domain declares angle_deg
    distance_m: float | None
    origin_xyz_m: tuple[float, float, float]
    angular_frame: str
    metadata: Mapping[str, Any]
    source: str

    @property
    def count(self) -> int:
        return int(self.points_m.shape[0])

    def unit_directions(self) -> np.ndarray | None:
        """``(nobs, 3)`` unit vectors from the frame origin, or ``None`` if any is zero."""
        norms = np.linalg.norm(self.points_m, axis=1)
        if norms.size == 0 or np.any(norms <= 0.0):
            return None
        return self.points_m / norms[:, None]

    def describe(self) -> Mapping[str, Any]:
        return {
            "domain_id": self.domain_id,
            "kind": self.kind,
            "count": self.count,
            "distance_m": self.distance_m,
            "origin_xyz_m": list(self.origin_xyz_m),
            "angular_frame": self.angular_frame,
            "has_angles_deg": self.angles_deg is not None,
            "source": self.source,
        }


@dataclass(frozen=True)
class BLPressureBasis:
    """One excitation's complex pressure basis over one observation domain.

    ``p_pa`` is ``(nf, nobs)`` complex128, Pa RMS per the excitation's declared
    :attr:`basis.per_input` (``V_rms`` or ``normal_velocity_mps``).
    """

    excitation_id: str
    observation: BLObservationSet
    p_pa: np.ndarray
    basis: C.SourceBasis
    quantity_id: str
    unit: str
    per_input_declaration: str

    def __post_init__(self) -> None:
        if self.p_pa.ndim != 2:
            raise _error("SCHEMA_MISMATCH",
                         f"excitation {self.excitation_id!r} pressure array must be (nf, nobs), "
                         f"got {self.p_pa.shape}")
        if self.p_pa.shape[1] != self.observation.count:
            raise _error("SCHEMA_MISMATCH",
                         f"excitation {self.excitation_id!r} pressure array has "
                         f"{self.p_pa.shape[1]} observations, domain "
                         f"{self.observation.domain_id!r} declares {self.observation.count}")
        if self.unit != BL_PRESSURE_UNIT:
            raise _error("UNITS_UNSUPPORTED", f"pressure unit {self.unit!r} is not {BL_PRESSURE_UNIT!r}")

    @property
    def max_abs_pa(self) -> float:
        return float(np.max(np.abs(self.p_pa))) if self.p_pa.size else 0.0


@dataclass(frozen=True)
class BLUnitConversion:
    """Recorded BL -> canonical mapping for one excitation's pressure basis.

    ``factor`` is the numeric scale applied to the stored values (``1.0``: BL already
    stores Pa RMS per its declared reference). The phasor conjugation is separate and
    recorded, never folded into a magnitude "fix".
    """

    excitation_id: str
    from_quantity: str
    from_unit: str
    from_per_input: str
    to_quantity: str
    to_unit: str
    to_per_input: str
    factor: float
    phasor_from: str
    phasor_to: str
    conjugated: bool
    basis_declared_by: str

    def as_dict(self) -> Mapping[str, Any]:
        return {
            "excitation_id": self.excitation_id,
            "from_quantity": self.from_quantity,
            "from_unit": self.from_unit,
            "from_per_input": self.from_per_input,
            "to_quantity": self.to_quantity,
            "to_unit": self.to_unit,
            "to_per_input": self.to_per_input,
            "factor": self.factor,
            "phasor_from": self.phasor_from,
            "phasor_to": self.phasor_to,
            "conjugated": self.conjugated,
            "basis_declared_by": self.basis_declared_by,
        }


@dataclass(frozen=True)
class BLResultProvenance:
    """Everything needed to reproduce and audit one read, without BL installed."""

    output_dir: str
    manifest_path: str
    manifest_sha256: str
    project_sha256: str | None
    compiled_system_sha256: str | None
    domains_json_sha256: str | None
    result_schema: str
    result_schema_version: int
    status: str
    backend_id: str | None
    solve_kind: str | None
    phasor_convention: str
    phasor_conversion: str
    quantity_unit_source: str
    per_input_source: str
    observation_source: str
    frame_origin_source: str
    source_geometry_hash: str
    source_geometry_hash_kind: str
    frequency_files: tuple[str, ...]
    frequency_indices: tuple[int, ...]
    frequency_artifact_sha256: tuple[tuple[str, str], ...]
    bl_install_commit: str
    source_pins: tuple[tuple[str, str, str], ...]
    notes: tuple[str, ...]

    def as_dict(self) -> Mapping[str, Any]:
        return {
            "output_dir": self.output_dir,
            "manifest_path": self.manifest_path,
            "manifest_sha256": self.manifest_sha256,
            "project_sha256": self.project_sha256,
            "compiled_system_sha256": self.compiled_system_sha256,
            "domains_json_sha256": self.domains_json_sha256,
            "result_schema": self.result_schema,
            "result_schema_version": self.result_schema_version,
            "status": self.status,
            "backend_id": self.backend_id,
            "solve_kind": self.solve_kind,
            "phasor_convention": self.phasor_convention,
            "phasor_conversion": self.phasor_conversion,
            "quantity_unit_source": self.quantity_unit_source,
            "per_input_source": self.per_input_source,
            "observation_source": self.observation_source,
            "frame_origin_source": self.frame_origin_source,
            "source_geometry_hash": self.source_geometry_hash,
            "source_geometry_hash_kind": self.source_geometry_hash_kind,
            "frequency_files": list(self.frequency_files),
            "frequency_indices": list(self.frequency_indices),
            "frequency_artifact_sha256": [list(item) for item in self.frequency_artifact_sha256],
            "bl_install_commit": self.bl_install_commit,
            "source_pins": [list(item) for item in self.source_pins],
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class BLHeadlessResult:
    """A complete or explicitly partial read of one BL headless result directory."""

    output_dir: str
    frequencies_hz: np.ndarray
    excitation_ids: tuple[str, ...]
    observation_sets: Mapping[str, BLObservationSet]
    fields: tuple[BLPressureBasis, ...]
    provenance: BLResultProvenance
    conversion: tuple[BLUnitConversion, ...]
    data_quality: Mapping[str, Any]

    # ------------------------------------------------------------------ views

    def domain_ids(self) -> tuple[str, ...]:
        """Domain ids in first-seen order."""
        seen: list[str] = []
        for field in self.fields:
            if field.observation.domain_id not in seen:
                seen.append(field.observation.domain_id)
        return tuple(seen)

    def fields_for(self, domain_id: str, *, quantity_id: str | None = None
                   ) -> tuple[BLPressureBasis, ...]:
        fields = tuple(f for f in self.fields if f.observation.domain_id == domain_id
                       and (quantity_id is None or f.quantity_id == quantity_id))
        if not fields:
            raise _error("OBSERVATION_METADATA_MISSING",
                         f"no complex pressure basis for domain {domain_id!r}; "
                         f"available: {sorted(set(self.domain_ids()))}")
        return fields

    def per_excitation_bases(self, domain_id: str, *, quantity_id: str | None = None
                             ) -> dict[str, np.ndarray]:
        """``{excitation_id: (nf, nobs) complex128 Pa}`` in declared excitation order."""
        found = {f.excitation_id: f.p_pa for f in self.fields_for(domain_id,
                                                                  quantity_id=quantity_id)}
        return {name: found[name] for name in self.excitation_ids if name in found}

    def basis_for(self, excitation_id: str, domain_id: str) -> C.SourceBasis:
        for field in self.fields_for(domain_id):
            if field.excitation_id == excitation_id:
                return field.basis
        raise _error("EXCITATION_BASIS_UNKNOWN",
                     f"excitation {excitation_id!r} has no field in domain {domain_id!r}")

    def conversion_record(self, excitation_id: str) -> BLUnitConversion:
        for record in self.conversion:
            if record.excitation_id == excitation_id:
                return record
        raise _error("EXCITATION_BASIS_UNKNOWN",
                     f"no recorded conversion for excitation {excitation_id!r}")

    def require_phase(self) -> None:
        """Raise the canonical phase token when this artifact cannot support phase claims."""
        if self.data_quality.get("quality") != "EXACT_COMPLEX":
            raise C.PhaseUnavailable(
                "MAGNITUDE_ONLY / PHASE_ALIGNMENT_UNAVAILABLE: this BL result has no complete "
                "complex per-excitation pressure basis; level-only screening remains allowed "
                "and coherent sum/delay claims are refused")
        if not self.fields:
            raise C.PhaseUnavailable(
                "MAGNITUDE_ONLY / PHASE_ALIGNMENT_UNAVAILABLE: no complex pressure fields were read")

    # ------------------------------------------------------------------ superposition guards

    def assert_per_excitation_independence(self, domain_id: str) -> Mapping[str, Any]:
        """Structural guard for the later superposition checks.

        What is asserted: exactly one complex block per declared excitation id, in manifest
        order, each finite, and each containing at least one non-zero value (a bitwise-zero
        block cannot come from a BEM solve and means a port was not actually driven).

        What is **not** asserted: numerical rank/linear independence across excitations.
        Two identical or symmetric ports can produce legitimately collinear observation
        vectors; claiming independence beyond "one independently solved column per port"
        would be false. Independence of the *solve* is a BL provenance property, recorded
        here, not a rank test.
        """
        fields = self.fields_for(domain_id)
        missing_frequencies = tuple(self.data_quality.get("missing_frequency_indices") or ())
        if missing_frequencies:
            raise _error("INCOMPLETE_RUN",
                         f"domain {domain_id!r} is a partial read (missing frequency indices "
                         f"{list(missing_frequencies)}); superposition and independence require a "
                         "complete frequency axis")
        by_id = {field.excitation_id: field for field in fields}
        missing = [name for name in self.excitation_ids if name not in by_id]
        extra = [name for name in by_id if name not in self.excitation_ids]
        if missing or extra:
            raise _error("SCHEMA_MISMATCH",
                         f"domain {domain_id!r} excitation set mismatch: missing {missing}, "
                         f"extra {extra}")
        observed_order = tuple(field.excitation_id for field in fields)
        if observed_order != self.excitation_ids:
            raise _error("SCHEMA_MISMATCH",
                         f"domain {domain_id!r} excitation order {observed_order} != manifest "
                         f"{self.excitation_ids}")
        summary: dict[str, Any] = {}
        for name in self.excitation_ids:
            values = by_id[name].p_pa
            if values.ndim != 2 or values.shape[0] != self.frequencies_hz.size:
                raise _error("SCHEMA_MISMATCH",
                             f"excitation {name!r} has shape {values.shape}, expected "
                             f"({self.frequencies_hz.size}, {by_id[name].observation.count})")
            if not np.all(np.isfinite(values)):
                raise _error("SCHEMA_MISMATCH",
                             f"excitation {name!r} contains non-finite pressure values")
            if not np.any(values != 0):
                raise _error("SCHEMA_MISMATCH",
                             f"excitation {name!r} pressure block is exactly zero; the port was "
                             "not driven (independence of the solved columns is not established)")
            summary[name] = {"max_abs_pa": by_id[name].max_abs_pa,
                             "per_input": by_id[name].basis.per_input}
        return {
            "domain_id": domain_id,
            "excitations": list(self.excitation_ids),
            "frequency_count": int(self.frequencies_hz.size),
            "observation_count": int(fields[0].observation.count),
            "per_excitation": summary,
            "independence_claim": "one independently solved column per declared excitation "
                                  "port (BL provenance); no numerical rank claim",
        }

    def assert_shared_sensitivity_reference(self, domain_id: str) -> str:
        """Require one comparable per-input reference across the domain's excitations."""
        fields = self.fields_for(domain_id)
        reference = fields[0].basis.per_input
        for field in fields[1:]:
            if field.basis.per_input != reference:
                raise C.IncompatibleBasis(
                    "SENSITIVITY_REFERENCE_MISMATCH: excitation "
                    f"{fields[0].excitation_id!r} is Pa per {reference!r} but "
                    f"{field.excitation_id!r} is Pa per {field.basis.per_input!r}; these are not "
                    "comparable sensitivity references. Apply the electrodynamic model for the "
                    "voltage port (or drive both as normal velocity) before any coherent sum.")
        return reference


# --------------------------------------------------------------------------- domain reading

class _DomainStore:
    """Lazy access to ``domains.json`` + ``domains.npz`` (no topology is loaded)."""

    def __init__(self, output_dir: Path) -> None:
        self._json_path = output_dir / "domains.json"
        self._npz_path = output_dir / "domains.npz"
        if not self._json_path.is_file() or not self._npz_path.is_file():
            raise _error("OBSERVATION_METADATA_MISSING",
                         "a headless result must carry domains.json and domains.npz to declare "
                         f"observation coordinates; missing under {output_dir}")
        payload = _require_mapping(_read_json(self._json_path, "SCHEMA_MISMATCH",
                                              "domains.json"), "domains.json")
        entries = payload.get("domains")
        if not isinstance(entries, list) or not entries:
            raise _error("OBSERVATION_METADATA_MISSING",
                         f"domains.json has no domain list in {self._json_path}")
        self._entries: dict[str, Mapping[str, Any]] = {}
        for entry in entries:
            record = _require_mapping(entry, "domains.json entry")
            domain_id = record.get("id")
            if not isinstance(domain_id, str) or not domain_id:
                raise _error("SCHEMA_MISMATCH", "domains.json entry has no string id")
            self._entries[domain_id] = record
        try:
            self._arrays = np.load(self._npz_path, allow_pickle=False)
        except (OSError, ValueError) as exc:
            raise _error("SCHEMA_MISMATCH", f"unreadable domains.npz {self._npz_path}: {exc}") from None
        self._cache: dict[str, BLObservationSet] = {}

    def close(self) -> None:
        close = getattr(self._arrays, "close", None)
        if callable(close):
            close()

    def has(self, domain_id: str) -> bool:
        return domain_id in self._entries

    def get(self, domain_id: str) -> BLObservationSet:
        if domain_id in self._cache:
            return self._cache[domain_id]
        entry = self._entries.get(domain_id)
        if entry is None:
            raise _error("OBSERVATION_METADATA_MISSING",
                         f"quantity targets domain {domain_id!r}, which domains.json does not "
                         f"declare; available: {sorted(self._entries)}")
        coordinates = entry.get("coordinates")
        if not isinstance(coordinates, Mapping) or "points_m" not in coordinates:
            raise _error("OBSERVATION_METADATA_MISSING",
                         f"domain {domain_id!r} has no points_m coordinate")
        points = self._array(str(coordinates["points_m"]), domain_id)
        points = np.asarray(points, dtype=np.float64)
        if points.ndim != 2 or points.shape[1] != 3 or points.shape[0] == 0:
            raise _error("SCHEMA_MISMATCH",
                         f"domain {domain_id!r} points_m must be (n, 3), got {points.shape}")
        if not np.all(np.isfinite(points)):
            raise _error("SCHEMA_MISMATCH", f"domain {domain_id!r} points_m contains non-finite values")
        angles = None
        if "angle_deg" in coordinates:
            angles = np.asarray(self._array(str(coordinates["angle_deg"]), domain_id),
                                dtype=np.float64).reshape(-1)
            if angles.size != points.shape[0]:
                raise _error("SCHEMA_MISMATCH",
                             f"domain {domain_id!r} angle_deg has {angles.size} values for "
                             f"{points.shape[0]} points")
        kind = str(entry.get("kind", "unknown"))
        radii = np.linalg.norm(points, axis=1)
        distance: float | None = None
        if radii.size and float(np.max(radii)) > 0.0:
            spread = float(np.max(radii) - np.min(radii))
            if spread <= max(1e-9, 1e-6 * float(np.max(radii))):
                distance = float(np.mean(radii))
        raw_metadata = entry.get("metadata")
        metadata: dict[str, Any] = dict(raw_metadata) if isinstance(raw_metadata, dict) else {}
        frame_prefix = _ANGULAR_FRAME_BY_KIND.get(kind)
        observation = BLObservationSet(
            domain_id=domain_id,
            kind=kind,
            points_m=points,
            angles_deg=angles,
            distance_m=distance,
            origin_xyz_m=_FRAME_ORIGIN_XYZ_M,
            angular_frame=(f"{frame_prefix}:{domain_id}" if frame_prefix is not None
                           else "unknown"),
            metadata=metadata,
            source=f"domains.json+domains.npz (domain kind {kind!r})",
        )
        self._cache[domain_id] = observation
        return observation

    def _array(self, key: str, domain_id: str) -> np.ndarray:
        try:
            return self._arrays[key]
        except KeyError:
            raise _error("OBSERVATION_METADATA_MISSING",
                         f"domain {domain_id!r} coordinate key {key!r} is absent from domains.npz")


# --------------------------------------------------------------------------- per-frequency reading

@dataclass(frozen=True)
class _FrequencyBlock:
    index: int
    freq_hz: float
    meta_path: Path
    arrays_path: Path
    #: (domain_id, quantity_id, per-excitation (ne, nobs) complex array)
    pressure: tuple[tuple[str, str, np.ndarray], ...]
    axes_source: str
    phasor_convention: str


def _frequency_tolerance(expected_hz: float) -> float:
    # Same tolerance BL itself uses to match a streamed result to the requested axis
    # (src/blab/headless.py:456-460).
    return max(1e-5, abs(expected_hz) * 2e-6)


def _select_pressure_quantity(quantities: list[Mapping[str, Any]], meta_path: Path
                              ) -> tuple[Mapping[str, Any], ...]:
    chosen = tuple(q for q in quantities if q.get("quantity") == BL_PRESSURE_QUANTITY)
    if chosen:
        return chosen
    magnitude_markers = ("spl", "magnitude", "db")
    for quantity in quantities:
        identifier = str(quantity.get("id", "")).lower()
        unit = str(quantity.get("unit", "")).lower()
        if unit.startswith("db") or any(marker in identifier for marker in magnitude_markers):
            raise _error("MAGNITUDE_ONLY",
                         f"{meta_path} stores magnitude-only quantity "
                         f"{quantity.get('id')!r} ({quantity.get('unit')!r}) and no complex "
                         f"{BL_PRESSURE_QUANTITY!r}; phase cannot be imputed")
    raise _error("PHASE_ALIGNMENT_UNAVAILABLE",
                 f"{meta_path} has no {BL_PRESSURE_QUANTITY!r} quantity; available: "
                 f"{[str(q.get('id')) for q in quantities]}")


def _read_frequency_block(
    *,
    index: int,
    expected_freq_hz: float,
    meta_path: Path,
    arrays_path: Path,
    excitation_ids: tuple[str, ...],
    domains: _DomainStore,
    expected_convention: str,
) -> _FrequencyBlock:
    meta = _require_mapping(_read_json(meta_path, "SCHEMA_MISMATCH", "frequency metadata"),
                            "frequency metadata")
    freq = float(_require_key(meta, "freq_hz", str(meta_path)))
    if abs(freq - expected_freq_hz) > _frequency_tolerance(expected_freq_hz):
        raise _error("FREQUENCY_AXIS_MISMATCH",
                     f"{meta_path} declares {freq:g} Hz but manifest index {index} is "
                     f"{expected_freq_hz:g} Hz")
    declared_ids = tuple(str(value) for value in meta.get("excitation_port_ids") or ())
    if declared_ids != excitation_ids:
        raise _error("SCHEMA_MISMATCH",
                     f"{meta_path} excitation ids {declared_ids} != manifest {excitation_ids}")

    diagnostics = meta.get("diagnostics")
    diagnostics = diagnostics if isinstance(diagnostics, Mapping) else {}
    convention = str(diagnostics.get("phasor_convention", expected_convention))

    quantities = meta.get("quantities")
    if not isinstance(quantities, list):
        raise _error("SCHEMA_MISMATCH", f"{meta_path} has no quantity list")
    selected = _select_pressure_quantity([_require_mapping(q, "quantity entry")
                                          for q in quantities], meta_path)

    if not arrays_path.is_file():
        raise _error("SCHEMA_MISMATCH", f"frequency arrays file not found: {arrays_path}")
    try:
        arrays = np.load(arrays_path, allow_pickle=False)
    except (OSError, ValueError) as exc:
        raise _error("SCHEMA_MISMATCH", f"unreadable {arrays_path}: {exc}") from None
    blocks: list[tuple[str, str, np.ndarray]] = []
    axes_sources: set[str] = set()
    try:
        for quantity in selected:
            quantity_id = str(quantity.get("id", ""))
            unit = str(quantity.get("unit", ""))
            if unit != BL_PRESSURE_UNIT:
                raise _error("UNITS_UNSUPPORTED",
                             f"{meta_path} quantity {quantity_id!r} declares unit {unit!r}; "
                             f"only {BL_PRESSURE_UNIT!r} pressure is imported")
            target = quantity.get("target_id")
            if not isinstance(target, str) or not target:
                raise _error("OBSERVATION_METADATA_MISSING",
                             f"{meta_path} quantity {quantity_id!r} has no target_id; observation "
                             "coordinates cannot be attached (domains.json is authoritative)")
            key = str(_require_key(quantity, "key", f"{meta_path} quantity"))
            if key not in arrays:
                raise _error("SCHEMA_MISMATCH",
                             f"{meta_path} quantity {quantity_id!r} references missing array {key!r}")
            values = np.asarray(arrays[key])
            declared_shape = tuple(int(v) for v in quantity.get("shape", ()))
            if declared_shape != tuple(values.shape):
                raise _error("SCHEMA_MISMATCH",
                             f"{meta_path} quantity {quantity_id!r} declares shape {declared_shape}, "
                             f"npz array is {tuple(values.shape)}")
            declared_dtype = quantity.get("dtype")
            if declared_dtype is not None and str(declared_dtype) != str(values.dtype):
                raise _error("SCHEMA_MISMATCH",
                             f"{meta_path} quantity {quantity_id!r} declares dtype {declared_dtype}, "
                             f"npz array is {values.dtype}")
            if values.dtype.kind != "c":
                raise _error("MAGNITUDE_ONLY",
                             f"{meta_path} quantity {quantity_id!r} is {values.dtype} (real); a "
                             "complex pressure basis is required and phase is never imputed")
            observation = domains.get(target)
            axes = tuple(str(axis) for axis in quantity.get("axes") or ())
            if axes:
                if len(axes) != 2 or "excitation" not in axes:
                    raise _error("SCHEMA_MISMATCH",
                                 f"{meta_path} quantity {quantity_id!r} has axes {axes}; expected "
                                 "two axes including 'excitation'")
                excitation_axis = axes.index("excitation")
                axes_source = "json_axes"
            else:
                excitation_axis = 0
                axes_source = "shape_inferred"
            if values.ndim != 2:
                raise _error("SCHEMA_MISMATCH",
                             f"{meta_path} quantity {quantity_id!r} is {values.ndim}-D; expected "
                             "(excitation, observation)")
            if values.shape[excitation_axis] != len(excitation_ids):
                raise _error("SCHEMA_MISMATCH",
                             f"{meta_path} quantity {quantity_id!r} excitation axis has "
                             f"{values.shape[excitation_axis]} entries, manifest declares "
                             f"{len(excitation_ids)}")
            observation_axis = 1 - excitation_axis
            if values.shape[observation_axis] != observation.count:
                raise _error("SCHEMA_MISMATCH",
                             f"{meta_path} quantity {quantity_id!r} observation axis has "
                             f"{values.shape[observation_axis]}, domain {target!r} declares "
                             f"{observation.count}")
            ordered = values if excitation_axis == 0 else values.swapaxes(0, 1)
            blocks.append((target, quantity_id, np.ascontiguousarray(ordered,
                                                                      dtype=np.complex128)))
            axes_sources.add(axes_source)
    finally:
        close = getattr(arrays, "close", None)
        if callable(close):
            close()

    seen: set[tuple[str, str]] = set()
    for target, quantity_id, _values in blocks:
        pair = (target, quantity_id)
        if pair in seen:
            raise _error("SCHEMA_MISMATCH",
                         f"{meta_path} declares quantity {quantity_id!r} twice for domain {target!r}")
        seen.add(pair)
    return _FrequencyBlock(
        index=index,
        freq_hz=freq,
        meta_path=meta_path,
        arrays_path=arrays_path,
        pressure=tuple(blocks),
        axes_source=";".join(sorted(axes_sources)),
        phasor_convention=convention,
    )


# --------------------------------------------------------------------------- excitation basis

def _excitation_per_input(compiled_path: Path, excitation_ids: tuple[str, ...]
                          ) -> tuple[dict[str, Literal["V_rms", "normal_velocity_mps"]], str]:
    if not compiled_path.is_file():
        raise _error("EXCITATION_BASIS_UNKNOWN",
                     f"compiled-system.json not found ({compiled_path}); the per-input "
                     "normalisation of every excitation is declared only there")
    compiled = _require_mapping(_read_json(compiled_path, "SCHEMA_MISMATCH",
                                          "compiled-system.json"), "compiled-system.json")
    ports = compiled.get("excitation_ports")
    if not isinstance(ports, list):
        raise _error("EXCITATION_BASIS_UNKNOWN",
                     "compiled-system.json has no excitation_ports list")
    port_kind: dict[str, str] = {}
    for port in ports:
        if not isinstance(port, Mapping):
            continue
        identifier = port.get("id")
        if isinstance(identifier, str):
            port_kind[identifier] = str(port.get("kind", ""))
    resolved: dict[str, Literal["V_rms", "normal_velocity_mps"]] = {}
    for excitation_id in excitation_ids:
        kind = port_kind.get(excitation_id)
        if kind is None:
            raise _error("EXCITATION_BASIS_UNKNOWN",
                         f"manifest excitation {excitation_id!r} is not declared in "
                         f"compiled-system.json (declared: {sorted(port_kind)})")
        per_input = _PER_INPUT_BY_PORT_KIND.get(kind)
        if per_input is None:
            raise _error("EXCITATION_BASIS_UNKNOWN",
                         f"excitation {excitation_id!r} port kind {kind!r} has no canonical "
                         f"per-input mapping; supported: {sorted(_PER_INPUT_BY_PORT_KIND)}")
        resolved[excitation_id] = per_input
    return resolved, "compiled-system.json excitation_ports[].kind"


def _source_geometry_identity(manifest: Mapping[str, Any], compiled_sha256: str | None
                              ) -> str:
    mesh_entries = manifest.get("meshes")
    meshes: list[Mapping[str, Any]] = []
    if isinstance(mesh_entries, list):
        for entry in mesh_entries:
            if not isinstance(entry, Mapping):
                continue
            identifier = str(entry.get("id", ""))
            digest = entry.get("sha256") or entry.get("digest")
            if digest:
                meshes.append({"id": identifier, "sha256": str(digest)})
    payload = {"compiled_system_sha256": compiled_sha256, "meshes": meshes}
    return C.domain_sha16("system.bl_source_geometry_v1", payload)


# --------------------------------------------------------------------------- public reader

def read_bl_headless_result(
    output_dir: str | Path,
    *,
    allow_partial: bool = False,
) -> BLHeadlessResult:
    """Read one BL headless result directory into canonical per-excitation bases.

    Refusals (never imputations): missing manifest/domains/compiled system, unknown schema,
    non-``Pa`` units, real (magnitude-only) arrays, a changing excitation/quantity set,
    unrequested frequencies, and incomplete runs unless ``allow_partial=True``. A partial
    read records the missing frequency indices and its ``assert_per_excitation_independence``
    still runs on what exists, so callers can gate superposition explicitly.
    """
    root = Path(output_dir)
    if not root.is_dir():
        raise _error("BL_RESULT_NOT_FOUND", f"BL result directory not found: {root}")
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        raise _error("BL_RESULT_NOT_FOUND",
                     f"{root} has no manifest.json; a BL headless result directory is required "
                     "(docs/advanced/cli-workflow.md:266-294)")

    manifest = _require_mapping(_read_json(manifest_path, "SCHEMA_MISMATCH", "manifest.json"),
                                "manifest.json")
    schema = str(manifest.get("schema", ""))
    if schema != BL_HEADLESS_SCHEMA:
        raise _error("SCHEMA_MISMATCH",
                     f"manifest schema {schema!r} != {BL_HEADLESS_SCHEMA!r}; this reader imports "
                     "BL headless result directories only")
    version = manifest.get("schema_version")
    if not isinstance(version, int) or version != BL_HEADLESS_SCHEMA_VERSION:
        raise _error("SCHEMA_MISMATCH",
                     f"manifest schema_version {version!r} is not the documented "
                     f"{BL_HEADLESS_SCHEMA_VERSION} (src/blab/headless.py:57)")

    status = str(manifest.get("status", ""))
    frequencies = np.asarray(manifest.get("frequencies_hz") or (), dtype=np.float64)
    if frequencies.ndim != 1 or frequencies.size == 0:
        raise _error("SCHEMA_MISMATCH", "manifest frequencies_hz must be a non-empty 1-D array")
    if not np.all(np.isfinite(frequencies)) or np.any(frequencies <= 0.0):
        raise _error("SCHEMA_MISMATCH", "manifest frequencies_hz must be finite and > 0")
    if np.unique(frequencies).size != frequencies.size:
        raise _error("SCHEMA_MISMATCH", "manifest frequencies_hz must be unique")

    excitation_ids = tuple(str(value) for value in manifest.get("excitation_port_ids") or ())
    if not excitation_ids:
        raise _error("SCHEMA_MISMATCH", "manifest excitation_port_ids is empty")
    if len(set(excitation_ids)) != len(excitation_ids):
        raise _error("SCHEMA_MISMATCH", "manifest excitation_port_ids contains duplicates")

    completion_raw = manifest.get("completion_mask")
    completion = np.asarray(completion_raw if completion_raw is not None else (),
                            dtype=bool).reshape(-1)
    if completion.size != frequencies.size:
        raise _error("SCHEMA_MISMATCH",
                     f"manifest completion_mask has {completion.size} entries for "
                     f"{frequencies.size} frequencies")
    completed = np.flatnonzero(completion)
    missing_indices = tuple(int(i) for i in np.flatnonzero(~completion))
    if missing_indices and not allow_partial:
        raise _error("INCOMPLETE_RUN",
                     f"run status {status!r} with {len(missing_indices)} unsolved frequencies "
                     f"{list(missing_indices)}; pass allow_partial=True for an explicit partial read")
    if status != "complete" and not missing_indices and not allow_partial:
        # status is the only record of a crash after the last frequency was committed.
        raise _error("INCOMPLETE_RUN", f"run status {status!r} is not 'complete'")

    results = manifest.get("results")
    if not isinstance(results, list) or len(results) != frequencies.size:
        raise _error("SCHEMA_MISMATCH",
                     "manifest results must be a list aligned with frequencies_hz "
                     "(src/blab/headless.py:447,495-499)")

    expected_convention = str(manifest.get("phasor_convention", ""))
    if expected_convention not in (BL_PHASOR_CONVENTION, BL_LEGACY_PHASOR_CONVENTION):
        raise _error("PHASOR_CONVENTION_UNSUPPORTED",
                     f"manifest phasor_convention {expected_convention!r} is not "
                     f"{BL_PHASOR_CONVENTION!r} or {BL_LEGACY_PHASOR_CONVENTION!r}")
    conjugated = expected_convention == BL_LEGACY_PHASOR_CONVENTION

    per_input_by_excitation, per_input_source = _excitation_per_input(
        root / "compiled-system.json", excitation_ids)
    compiled_sha = (_sha256_file(root / "compiled-system.json")
                    if (root / "compiled-system.json").is_file() else None)
    domains_sha = (_sha256_file(root / "domains.json")
                   if (root / "domains.json").is_file() else None)
    geometry_hash = _source_geometry_identity(manifest, compiled_sha)

    notes: list[str] = []
    if missing_indices:
        notes.append(f"partial read: {len(missing_indices)} frequency indices missing "
                     f"{list(missing_indices)}")

    domains = _DomainStore(root)
    try:
        blocks: list[_FrequencyBlock] = []
        artifact_hashes: list[tuple[str, str]] = []
        frequency_files: list[str] = []
        for index in completed:
            index = int(index)
            entry = results[index]
            entry = _require_mapping(entry, f"manifest results[{index}]")
            meta_rel = entry.get("metadata_file")
            arrays_rel = entry.get("arrays_file")
            if not isinstance(meta_rel, str) or not isinstance(arrays_rel, str):
                meta_rel = f"frequencies/{index:06d}.json"
                arrays_rel = f"frequencies/{index:06d}.npz"
                notes.append(f"manifest results[{index}] lacked file names; used the documented "
                             f"frequencies/{index:06d}.* layout")
            meta_path = (root / meta_rel).resolve()
            arrays_path = (root / arrays_rel).resolve()
            if root.resolve() not in meta_path.parents or root.resolve() not in arrays_path.parents:
                raise _error("SCHEMA_MISMATCH",
                             f"manifest result path escapes the result directory: {meta_rel}, "
                             f"{arrays_rel}")
            block = _read_frequency_block(
                index=index,
                expected_freq_hz=float(frequencies[index]),
                meta_path=meta_path,
                arrays_path=arrays_path,
                excitation_ids=excitation_ids,
                domains=domains,
                expected_convention=expected_convention,
            )
            if (block.phasor_convention != BL_PHASOR_CONVENTION
                    and block.phasor_convention != BL_LEGACY_PHASOR_CONVENTION):
                raise _error("PHASOR_CONVENTION_UNSUPPORTED",
                             f"{meta_path} diagnostics phasor_convention "
                             f"{block.phasor_convention!r} is unsupported")
            if block.phasor_convention != expected_convention:
                raise _error("PHASOR_CONVENTION_UNSUPPORTED",
                             f"{meta_path} declares {block.phasor_convention!r} but the manifest "
                             f"declares {expected_convention!r}; refusing to convert twice")
            blocks.append(block)
            for relative, path in ((meta_rel, meta_path), (arrays_rel, arrays_path)):
                frequency_files.append(Path(relative).as_posix())
                artifact_hashes.append((Path(relative).as_posix(), _sha256_file(path)))

        # ---- assemble (nf, nobs) bases per (domain, quantity, excitation)
        keys: list[tuple[str, str]] = []
        observed_order: list[tuple[str, str, int]] = []
        for block in blocks:
            for target, quantity_id, values in block.pressure:
                pair = (target, quantity_id)
                if pair not in keys:
                    keys.append(pair)
                observed_order.append((target, quantity_id, values.shape[1]))
        if not keys:
            raise _error("PHASE_ALIGNMENT_UNAVAILABLE",
                         f"no complex {BL_PRESSURE_QUANTITY!r} quantities found under {root}")
        shapes_by_key: dict[tuple[str, str], set[int]] = {key: set() for key in keys}
        for target, quantity_id, count in observed_order:
            shapes_by_key[(target, quantity_id)].add(count)
        for (target, quantity_id), counts in shapes_by_key.items():
            if len(counts) != 1:
                raise _error("SCHEMA_MISMATCH",
                             f"domain {target!r} quantity {quantity_id!r} changed observation "
                             f"count across frequencies: {sorted(counts)}")

        fields: list[BLPressureBasis] = []
        conversion: list[BLUnitConversion] = []
        conventions_seen: set[str] = set()
        axes_sources: set[str] = set()
        observation_sets: dict[str, BLObservationSet] = {}
        for block in blocks:
            conventions_seen.add(block.phasor_convention)
            axes_sources.update(block.axes_source.split(";"))
            for target, quantity_id, values in block.pressure:
                observation_sets.setdefault(target, domains.get(target))
        for target, quantity_id in keys:
            observation = observation_sets[target]
            nobs = observation.count
            # Missing (not committed) frequencies stay NaN, never zero: a partial read must not
            # look like a solved row with a null in the field.
            stacked = np.full((frequencies.size, len(excitation_ids), nobs),
                              complex(np.nan, np.nan), dtype=np.complex128)
            filled = np.zeros(frequencies.size, dtype=bool)
            for block in blocks:
                for block_target, block_quantity, values in block.pressure:
                    if block_target == target and block_quantity == quantity_id:
                        stacked[block.index] = values
                        filled[block.index] = True
            if not bool(np.all(filled[completed])):
                raise _error("INCOMPLETE_RUN",
                             f"domain {target!r} quantity {quantity_id!r} is missing at completed "
                             f"frequency indices {[int(i) for i in completed[~filled[completed]]]}")
            if conjugated:
                stacked = np.conjugate(stacked)
            for excitation_index, excitation_id in enumerate(excitation_ids):
                per_input = per_input_by_excitation[excitation_id]
                p = np.ascontiguousarray(stacked[:, excitation_index, :])
                basis = C.SourceBasis(
                    per_input=per_input,
                    distance_m=observation.distance_m,
                    origin_xyz_m=observation.origin_xyz_m,
                    angular_frame=observation.angular_frame,
                    source_geometry_hash=geometry_hash,
                )
                fields.append(BLPressureBasis(
                    excitation_id=excitation_id,
                    observation=observation,
                    p_pa=p,
                    basis=basis,
                    quantity_id=quantity_id,
                    unit=BL_PRESSURE_UNIT,
                    per_input_declaration=_PER_INPUT_DECLARATION[per_input],
                ))
                conversion.append(BLUnitConversion(
                    excitation_id=excitation_id,
                    from_quantity=BL_PRESSURE_QUANTITY,
                    from_unit=BL_PRESSURE_UNIT,
                    from_per_input=_PER_INPUT_DECLARATION[per_input],
                    to_quantity="pressure_pa",
                    to_unit=BL_PRESSURE_UNIT,
                    to_per_input=per_input,
                    factor=1.0,
                    phasor_from=expected_convention,
                    phasor_to=C.TIME_CONVENTION,
                    conjugated=conjugated,
                    basis_declared_by=per_input_source,
                ))
    finally:
        domains.close()

    if "shape_inferred" in axes_sources:
        notes.append(
            "BLOCKED_BY_BL_RESULT_FORMAT: per-frequency quantity.axes is copied verbatim from "
            "the BEAT engine result (src/blab/headless.py:463-478, src/blab/system_solve.py:442-471); "
            "the labels are not defined in BL's Python source. Orientation was taken from the "
            "documented (excitation, observation) shape (docs/Coupled Solver.md:516-524); the "
            "JSON axes were absent/empty for every other quantity.")
    if expected_convention == BL_LEGACY_PHASOR_CONVENTION:
        notes.append("legacy BL result: exp(-i omega t) conjugated once to exp(+jomega_t) "
                     "(src/blab/phasor.py:12-17)")
    for observation in observation_sets.values():
        if observation.distance_m is None:
            notes.append(f"domain {observation.domain_id!r} samples multiple radii; "
                         "distance_m is None and coherent summation with it is refused by "
                         "SourceBasis.compatible_for_sum_with")
        if observation.kind not in _ANGULAR_FRAME_BY_KIND:
            notes.append(f"domain {observation.domain_id!r} kind {observation.kind!r} has no "
                         "declared sampling-frame mapping; angular_frame='unknown'")

    provenance = BLResultProvenance(
        output_dir=str(root),
        manifest_path=str(manifest_path),
        manifest_sha256=_sha256_file(manifest_path),
        project_sha256=(None if manifest.get("project_sha256") is None
                        else str(manifest.get("project_sha256"))),
        compiled_system_sha256=compiled_sha,
        domains_json_sha256=domains_sha,
        result_schema=schema,
        result_schema_version=int(version),
        status=status,
        backend_id=(None if manifest.get("backend_id") is None else str(manifest.get("backend_id"))),
        solve_kind=(None if manifest.get("solve_kind") is None else str(manifest.get("solve_kind"))),
        phasor_convention=expected_convention,
        phasor_conversion=f"{expected_convention} -> {C.TIME_CONVENTION}",
        quantity_unit_source="per-frequency JSON quantity.unit (BL writes the solver's unit; "
                             "docs/Coupled Solver.md:516-524 declares Pa)",
        per_input_source=per_input_source,
        observation_source="domains.json + domains.npz (frequency-invariant BL result domains)",
        frame_origin_source=_FRAME_ORIGIN_SOURCE,
        source_geometry_hash=geometry_hash,
        source_geometry_hash_kind="domain_sha16('system.bl_source_geometry_v1', "
                                  "{compiled_system_sha256, meshes[].sha256})",
        frequency_files=tuple(frequency_files),
        frequency_indices=tuple(int(i) for i in completed),
        frequency_artifact_sha256=tuple(artifact_hashes),
        bl_install_commit=BL_INSTALL_COMMIT,
        source_pins=BL_SOURCE_PINS,
        notes=tuple(notes),
    )

    data_quality: dict[str, Any] = {
        "quality": "EXACT_COMPLEX",
        "time_convention": C.TIME_CONVENTION,
        "bl_phasor_convention": expected_convention,
        "phasor_conjugated": conjugated,
        "unit": BL_PRESSURE_UNIT,
        "rms_phasors": True,
        "per_input_by_excitation": dict(per_input_by_excitation),
        "sensitivity_referenced_per_excitation": True,
        "phasor_conventions_observed": sorted(conventions_seen),
        "completed_frequencies": int(completed.size),
        "missing_frequency_indices": list(missing_indices),
        "axes_source": "+".join(sorted(axes_sources)),
        "phase_qualified": True,
        "claims_allowed": (
            "per_excitation_complex_pressure_basis",
            "coherent_sum_within_one_declared_frame_and_per_input",
            "absolute_pa_per_declared_input",
        ),
        "claims_refused": (
            "sum_across_different_per_input_without_an_electrodynamic_model",
            "cross_fidelity_numeric_comparison",
            "phase_imputation_for_missing_frequencies",
        ),
    }

    return BLHeadlessResult(
        output_dir=str(root),
        frequencies_hz=frequencies,
        excitation_ids=excitation_ids,
        observation_sets=observation_sets,
        fields=tuple(fields),
        provenance=provenance,
        conversion=tuple(conversion),
        data_quality=data_quality,
    )


# --------------------------------------------------------------------------- contract assembly

def to_system_response(
    result: BLHeadlessResult,
    domain_id: str,
    *,
    fidelity: str,
) -> C.SystemResponse:
    """Assemble one domain's per-excitation bases into the canonical ``SystemResponse``.

    ``fidelity`` is required, never guessed: the reader can see the solve kind but not the
    driver-geometry completeness that an installed/coupled fidelity label claims.
    ``p_total`` stays ``None`` because combining excitations is the DSP layer's decision.
    """
    fields = result.fields_for(domain_id)
    observation = fields[0].observation
    names = tuple(field.excitation_id for field in fields)
    directions = observation.unit_directions()
    return C.SystemResponse(
        frequencies_hz=np.asarray(result.frequencies_hz, dtype=np.float64),
        excitation_names=names,
        p_by_excitation={field.excitation_id: field.p_pa for field in fields},
        excitation_bases={field.excitation_id: field.basis for field in fields},
        p_total=None,
        magnitude_screen=None,
        observation_directions=directions,
        observation_angles_deg=(("angle_deg",) if observation.angles_deg is not None else None),
        fidelity=fidelity,
        physics_provenance={
            "source": "boundary_lab_headless_result",
            "domain": observation.describe(),
            "bl_result": result.provenance.as_dict(),
            "unit_conversion": [record.as_dict() for record in result.conversion
                                if record.excitation_id in names],
        },
        data_quality={**dict(result.data_quality), "domain_id": domain_id},
    )
