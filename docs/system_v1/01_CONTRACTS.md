# System v1 contracts (frozen for this effort, 2026-11-20)

Lanes implement these exactly. A lane that finds a contract does not fit the code **stops and
reports**; only the effort's senior amends this file, in writing, with a dated note at the bottom.

Conventions for every type below:

- Frozen `@dataclass(frozen=True, slots=True)`; `to_dict()` returns JSON-safe data with sorted keys;
  `from_dict()` validates and raises the module's error with a token.
- Ids: `contracts.domain_sha16(<domain>, canonical_json(payload_without_id))`. Domains are listed
  per type. Never hand-pick an id.
- Times: ISO-8601 UTC strings with `+00:00`.
- Paths inside records: **store-relative POSIX strings** (`bl_smoke/2026.../run/manifest.json`).
  Absolute paths are only kept as provenance in a field named `original_abs_path`.
- Errors: each new module defines one exception class carrying `.token` (UPPER_SNAKE) and `.detail`.

---

## 1. Path helper (`hornlab_search/system/paths.py`, lane A1)

```python
def split_any(path_text: str) -> tuple[str, ...]
    # Split on both "/" and "\\"; drop empty parts and a drive like "C:". Pure string op.
def to_store_relative(path_text: str, store_root_hints: Sequence[str]) -> str | None
    # If any hint (case-insensitive, separator-agnostic) is a prefix, return the rest as POSIX.
    # Also recognise the marker "system_runs" as a hint. None if no hint matches.
def leaf_dir_name(path_text: str) -> str | None   # parent dir of a file path, OS-agnostic
```

Used by `read_case`, the export (fixes N1) and `store_migrate`.

## 2. SystemCase (`hornlab_search/system/case_schema.py`, lane A1)

```python
CASE_SCHEMA = "hornlab.system.case.v1"
CaseStatus = Literal["solved", "staged", "refused", "invalid"]

@dataclass(frozen=True)
class CaseHeader:
    case_key: str            # "<experiment>/<case_dir_name>"
    experiment: str
    case: str
    kind: str | None         # manifest payload "kind"; None when no manifest
    created_utc: str | None
    status: CaseStatus       # rules identical to tools/data/system_cases.py (first match wins)
    status_reason: str       # token: RUN_COMPLETE | CASE_REFUSED | MANIFEST_ONLY | NO_MANIFEST | UNPARSEABLE
    manifest_integrity: Literal["verified", "mismatch", "unknown"]
    source_path: str         # store-relative

@dataclass(frozen=True)
class StageBlock:   ok: bool | None; error: str | None; project_rel: str | None; clearance: ClearanceBlock | None
@dataclass(frozen=True)
class ClearanceBlock: status: Literal["pass","violation","unproven","not_recorded"]; min_gap_mm: float | None; source: str
@dataclass(frozen=True)
class SolveBlock:   run_status: str | None; n_frequencies: int | None; freq_min_hz: float | None;
                    freq_max_hz: float | None; backend_id: str | None; solve_kind: str | None;
                    completion_done: int | None; completion_total: int | None;
                    authorized_by: str | None; run_manifest_integrity: str
@dataclass(frozen=True)
class GeometryBlock: box_mm: tuple[float|None,float|None,float|None]; net_volume_l: float | None;
                     net_volume_source: str | None; port_area_cm2: float | None; tuning_hz: float | None;
                     horn_mesh: str | None; horn_mesh_sha256: str | None;
                     horn_offset_mm_xyz: tuple[float,float,float] | None; driver_name: str | None
@dataclass(frozen=True)
class Declaration:  declared: bool; fidelity: str; motor: str; motor_source: str;
                    transducer_shape: str; gate: str | None; ref: str | None;
                    evidence: str | None; horn_source: str | None; pair_with: str | None
                    # from readiness.yaml only; "UNDECLARED" defaults

@dataclass(frozen=True)
class SystemCase:
    header: CaseHeader
    declaration: Declaration
    stage: StageBlock | None
    solve: SolveBlock | None
    geometry: GeometryBlock | None
    refusals: tuple[str, ...]        # tokens found (case-level only)
    diagnostics: tuple[str, ...]     # problems reading this case; never raises
    sources: tuple[str, ...]         # store-relative files walked, in order
    def to_dict(self) -> dict
```

`hornlab_search/system/read_case.py` (lane A1):

```python
def read_case(case_dir: Path, *, store_root: Path, readiness: Mapping | None = None) -> SystemCase
def iter_cases(store_root: Path, *, readiness: Mapping | None = None) -> Iterator[SystemCase]
    # walks <store_root>/system/<experiment>/<CASE_DIR_RE>; sorted by (experiment, case)
def load_readiness(repo_root: Path) -> Mapping | None   # docs/research/system_woofer_2026-11-18/readiness.yaml
```

Behaviour must match `tools/data/system_cases.py` status rules, metadata-walk order and
integrity checks (port them; the tool's docstring is the spec). `read_case` never raises on bad
data; it returns `status="invalid"` + diagnostics. It never imports BL, solver or GUI modules.

## 3. CalibrationRecord (`hornlab_search/system/calibration.py`, lane A2)

```python
CAL_SCHEMA = "hornlab.system.calibration.v1"; id domain "system.calibration"
CalMethod = Literal["measured_on_horn", "loaded_electroacoustic_model",
                    "unloaded_driver_model", "assumed_ideal"]
METHOD_FIDELITY_CAP = {  # the summed response's fidelity can never exceed this
  "measured_on_horn": "MEASURED_VALIDATED",
  "loaded_electroacoustic_model": "COUPLED_VENTED_FEM_BEM_LEM",
  "unloaded_driver_model": "SCREEN_COMPLEX_APPROX",
  "assumed_ideal": "SCREEN_COMPLEX_APPROX"}

@dataclass(frozen=True)
class ChannelCalibration:
    excitation: str                          # "horn" | "woofer" (excitation name in the response)
    from_per_input: Literal["V_rms", "normal_velocity_mps"]
    to_per_input: Literal["V_rms"]           # v1: everything is brought to Pa per V_rms
    frequencies_hz: tuple[float, ...]        # strictly increasing
    factor_re: tuple[float, ...]             # complex multiplier per frequency, same length
    factor_im: tuple[float, ...]
    method: CalMethod
    evidence_path: str                       # repo- or store-relative

@dataclass(frozen=True)
class CalibrationRecord:
    record_id: str; created_utc: str; approved_by: str; scope: tuple[str, ...]  # case_keys or ("*",)
    channels: tuple[ChannelCalibration, ...]; notes: str
    def fidelity_cap(self) -> str            # min over channel METHOD_FIDELITY_CAP (ladder order)

def apply_calibration(response: SystemResponse, record: CalibrationRecord, *, case_key: str) -> SystemResponse
```

Refusal tokens (`CalibrationError.token`): `CAL_SCOPE_MISMATCH`, `CAL_FREQ_GRID_MISMATCH` (no
interpolation in v1: grids must match the response's to 1e-9 relative), `CAL_CHANNEL_MISSING`,
`CAL_UNIT_MISMATCH` (`from_per_input` != the basis), `CAL_NONFINITE`.

`apply_calibration` multiplies each channel field by its factor, returns a new response whose
bases carry `per_input="V_rms"` and whose fidelity is `min(response.fidelity, record.fidelity_cap())`.
It does not touch distance/origin/frame/geometry-hash, so `compatible_for_sum_with` still guards them.

`combine.combine(..., calibration: CalibrationRecord | None = None, case_key: str | None = None)`:
`None` keeps today's behaviour byte-for-byte (mixed references refused). With a record, apply first,
then the existing checks. The R13 duplicate guard families are aliased, not removed: add a single
`REFERENCE_REFUSAL_TOKENS` tuple in `combine.py` listing both families; no token text changes.

## 4. AuthorizationRecord (`hornlab_search/system/authorization.py`, lane A3)

```python
AUTH_SCHEMA = "hornlab.system.authorization.v1"; id domain "system.authorization"
@dataclass(frozen=True)
class AuthorizationRecord:
    record_id: str; who: str; why: str
    scope_kind: Literal["case", "experiment", "funnel_run"]; scope: tuple[str, ...]
    actions: tuple[Literal["bl_solve"], ...]
    created_utc: str; expires_utc: str | None; legacy_free_string: bool = False
def from_legacy_string(text: str) -> AuthorizationRecord       # legacy_free_string=True, scope ("*",)
def load_authorization(path: Path) -> AuthorizationRecord
def check(record, *, action: str, case_key: str, now_utc: str) -> None
```

Tokens: `AUTH_MISSING`, `AUTH_EXPIRED`, `AUTH_SCOPE_MISMATCH`, `AUTH_ACTION_NOT_GRANTED`.
`reference.solve(...)` accepts `authorization: AuthorizationRecord | None` in addition to the
existing `authorized_by: str | None`; a string is wrapped with `from_legacy_string`. The manifest
records `authorization: record.to_dict()` and keeps `authorized_by` for back-compat. A legacy
string still works (no behaviour break), but the GUI (Pass E) will require a non-legacy record.

## 5. ObservationStandard (`hornlab_search/system/observation.py`, lane A3)

```python
@dataclass(frozen=True)
class ObservationStandard:
    standard_id: str; distance_m: float; angular_frame: str; h_angles_deg: tuple[float, ...]
    v_angles_deg: tuple[float, ...]; listening_window: tuple[tuple[float, float], ...] | None
    far_field_claimed: bool; approved_by: str | None
def label_for(basis: SourceBasis, standard: ObservationStandard | None) -> str
    # "near-field cuts (undeclared standard)" when standard is None or far_field_claimed is False
```

Schema only. No values committed. Used by read models to label curves.

## 6. JobSpec (`hornlab_search/system/jobs.py`, lane A5)

```python
@dataclass(frozen=True)
class JobSpec:
    kind: Literal["screen", "pilot", "portfolio", "bl_stage", "bl_validate", "bl_solve", "funnel"]
    argv: tuple[str, ...]; cwd_rel: str; env: tuple[tuple[str, str], ...]
    inputs_sha256: str; lane: Literal["cpu"]; authorization_id: str | None
def preview(job: JobSpec) -> str    # shlex-joined argv: exactly what launch would run
def build_job(kind, **kwargs) -> JobSpec   # the one place argv for each kind is built
```

`bl_solve` without `authorization_id` raises `JobError("AUTH_MISSING")` at build time. `lane` is
always `"cpu"` in v1; there is no GPU system job.

## 7. Funnel ledger (`hornlab_search/system/funnel.py`, lane B3)

```python
LEDGER_SCHEMA = "hornlab.system.funnel_ledger.v1"
def plan_funnel(spec_path, *, shortlist_n: int, store_root: Path) -> FunnelPlan   # pure, no execution
def run_funnel(plan, *, execute: bool, authorization: AuthorizationRecord | None) -> FunnelLedger
```

Ledger row: `step` (screen|stage|validate|solve|dsp), `job` (JobSpec dict), `case_key|None`,
`status` (planned|done|refused|failed|skipped), `token`, `fidelity`, `inputs_sha256`. Sorted by
(step order, shortlist rank). `execute=False` writes only the plan ledger. Solve rows without a
valid authorization are `refused` with `AUTH_MISSING`, never run.

## 8. CaseReadModel (GUI JSON, lane B2)

`{ "facts": SystemCase.to_dict() minus declaration, "declared": declaration dict,
   "derived": {...python-computed only...}, "refusals": [...], "links": {...},
   "labels": {"observation": label_for(...)} }`

Existing URL paths and existing top-level JSON keys of `/api/hw/*` stay; the read model is added
under the existing payload (additive). JS reads `facts/declared/derived`; it computes nothing.

---

## Amendments

(none)
