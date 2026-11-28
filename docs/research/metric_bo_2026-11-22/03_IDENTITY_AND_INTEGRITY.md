# Pass 2 — metric artifact identity & replay integrity

- **Date:** 2026-11-22
- **Lane:** B (bounded identity, artifact integrity, cohort replay safety)
- **Worktree / branch:** `C:/Users/hunte/Hrns/hornfab-metric-bo-wt` /
  `feat/metric-aware-bo`
- **Depends on:** `01`/`ADR_metric_composite_v1.md` (Pass 1 contracts) and the frozen component
  schemas in `hornlab_search/bo/metric_contracts.py`.
- **Status:** implemented and tested with synthetic fixtures only. No real dataset was read or
  replayed; no solver, GPU or mesh call was made.

## 1. Why this pass exists

Pass 1 could compute and fit component contributions, but it had three integrity gaps:

1. A `metric-training-v1` artifact existed only as an in-memory dataclass; there was no
   deterministic on-disk form, so a reload could not be proven byte-identical or tamper-evident.
2. Bounds identity hashed only `active_keys`/projection version/raw transforms — two boxes with the
   same dimension could collide, and no artifact recorded a *recomputable* payload next to its
   hash.
3. `tools/analysis/study_cohort.py` silently replayed the whole compatible v10/v11 group when zero
   candidates were encodable, uncapped and indistinguishable from ranked selection. Stored `J` was
   treated as an equivalent label without establishing the score identity first.

This pass closes all three. A mismatch is always a typed refusal; nothing is repaired, clipped or
silently downgraded.

## 2. Frozen artifact format (`metric-training-npz-v1`)

`hornlab_search/bo/metric_artifact.py` owns serialization and integrity.

| Constant | Value |
|---|---|
| `ARTIFACT_FORMAT` | `metric-training-npz-v1` |
| `ARTIFACT_KIND` | `metric_training` |
| storage | ZIP_STORED `.npz`, no pickle, fixed member order |
| members | `X.npy`, `J.npy`, `Y_components.npy`, optional `Y_phys.npy`/`G.npy`, `manifest.json` |
| ZIP timestamp | `(1980, 1, 1, 0, 0, 0)` on every member |

`artifact_bytes(artifact) -> bytes` writes the fixed member order and a canonical-JSON manifest;
identical input produces byte-identical output. `artifact_from_bytes(blob, *, expected_checksum=None)
-> (artifact|None, ArtifactCheck)` is the only loader. It refuses truncated/garbage/foreign
payloads, non-`.npy` members, pickle-named members (`.pkl/.pickle/.pt/.pth/.joblib/.ckpt`), any
array whose dtype is not `float64`, any shape/sha256 disagreement with the manifest, non-finite
arrays, duplicate observation/selected IDs, and a manifest checksum mismatch. Arrays are copied to
read-only `float64`.

`load_artifact_file(path, ...)` is the path helper; it refuses a pickled-model extension before
opening the bytes.

### Manifest

Canonical JSON (`sort_keys`, compact separators, no NaN/Inf):

```
format, kind, version
objective_version, feature_names, component_names
component_schema, component_schema_hash
observation_ids, selected_ids, excluded
bounds_identity_payload, bounds_hash
score_identity_payload, score_identity
task_identity, backend, fidelity, grid_hash, dependency_hash, mesh_hash
arrays: {X|J|Y_components|Y_phys|G: {dtype, shape, sha256}}
source_checksum        # the build-time manifest checksum, preserved across a round trip
metadata               # the original artifact metadata (JSON-safe)
artifact_checksum      # sha256(canonical(core)) — recomputed on load
```

`artifact_checksum` covers every field above except itself. On load the loader recomputes it;
`validate_metric_training_artifact` recomputes it again from the artifact object (including array
digests) when `metadata["artifact_checksum"]` is present, so a tampered manifest or array is a typed
refusal.

## 3. Identity contracts

### 3.1 Bounds identity

`metric_training.bounds_identity(encoding)` now delegates to
`metric_identity.bounds_identity(encoding, strict=True)`. The hashed payload records
`version`, `projection_version`, the ordered `active_keys`, per-key `transforms` with physical
`lo`/`hi`, `log`, `transform` kind and `active` flag, and `fixed_values`. Consequences:

- same dimension, different physical box → different hash;
- `log10` vs `identity` transform → different hash;
- changed active-key order → different hash;
- changed fixed values → different hash;
- identical projections → identical hash.

Strict mode refuses an encoding with no active keys, no projection version, duplicate active keys,
missing `key_transforms()`, an empty physical box, or `log10` with `lo <= 0`.

### 3.2 Score identity

Score identity is `score_payload(objective_version, brief_hash, score_hash, score_module)` hashed
with SHA-256. `objective_version` alone is never sufficient. Artifact metadata carries
`objective_version`, `brief_hash`, `score_hash`, `score_identity` and
`score_identity_payload`; the payload is re-hashed on validation and compared with the recorded
hash and with `expected_score`.

### 3.3 Artifact stamping at build time

`metric_training.build_metric_training_artifact(..., require_identity=False)` keeps the Pass 1
signature and adds an opt-in identity gate:

- `require_identity=True` requires `objective_version`, `brief_hash`, `score_hash`, and a
  recomputable bounds source (`bounds_identity_payload`, or a live `encoding` object). It stamps
  `metadata["bounds_identity_payload"]`, `metadata["bounds_hash"]`,
  `metadata["score_identity_payload"]` and `metadata["score_identity"]`, and refuses on any
  missing/mismatched identity.
- `require_identity=False` preserves Pass 1 synthetic callers; any identity payload they *do*
  supply is still re-hashed and refused on mismatch, but no identity is invented.

Existing metadata fields are unchanged. Typed refusal reasons are prefixed `identity:` (see §6).

### 3.4 Validation

`validate_metric_training_artifact(artifact, *, encoding=None, expected_bounds_hash=None,
expected_score=None, expected_task=None) -> ArtifactCheck` (`ok` property, `status`
`ok|unavailable`, `reason`, `detail`, `reasons`, `checks`). It validates in this order:

1. status and `metric-training-v1` version; objective version must be 10 or 11;
2. required arrays present, `float64`, finite; shapes match;
3. component names/order equal the frozen schema tuple; schema id/hash agree when recorded (a
   missing hash is required only when an identity argument is supplied);
4. per-row `J == sum(components)` within `metric_contracts.parity_tolerance`; `X` finite and in
   `[0,1]`;
5. serialized `artifact_checksum` recomputation (arrays + manifest field subset);
6. bounds payload re-hash via `metric_identity.recompute_bounds_hash` and against
   `expected_bounds_hash`/live `encoding`; mismatch/missing is refused;
7. score payload re-hash and `metric_identity.check_score_identity` against `expected_score`;
8. exact identity fields (`task_identity`, `backend`, `fidelity`, `grid_hash`,
   `dependency_hash`, `mesh_hash`) against `expected_task`.

Identity arguments are opt-in so Pass 1 synthetic artifacts keep working; whenever a payload is
present it is re-hashed regardless.

## 4. Pass 1 seam wiring

- **`metric_model.fit_metric_model`** runs the artifact integrity gate before any Torch import or
  fit. A failed check returns the existing tagged `invalid_artifact` result with the specific
  reason in `detail`; no model is fitted on a corrupt artifact. Existing success fields are
  unchanged. (Component non-finiteness keeps its earlier, more specific
  `nonfinite_training_data:<component>` refusal.)
- **`metric_propose.propose_metric_candidate(..., require_identity=False,
  expected_bounds_hash=None)`** resolves every available `policy`/`pool`/`model` `bounds_hash`
  source. With `require_identity=True`, each available source must be non-empty and equal to the
  caller-recomputed `expected_bounds_hash`; an ok result can never emit `bounds_hash=""`. With the
  default `False`, Pass 1 behaviour is byte-for-byte preserved (`bounds_hash` still resolves from
  policy/pool/model, including `"bounds-v1"` in the existing test).

## 5. Cohort replay safety (`tools/analysis/study_cohort.py`)

The unsafe v10/v11 fallback is gone.

- **Default (no encodable candidate):** `prepare` returns a typed refusal in
  `selection.metric_selection` with `status="refused"`, `reason="metric_selection_unavailable"`,
  `n_records_considered`, `n_replayed=0`, per-record `excluded` provenance, and **no rows
  replayed**.
- **`allow_unranked_replay=True`:** the only way to replay such a group. The output records
  `status="replay_authorized"`, `basis="allow_unranked_replay"`, `n_replayed`, plus the same
  per-record provenance, so it can never masquerade as ranked selection.
- **Pre-replay score identity:** before ranking by stored `J`, every record must carry a non-empty
  catalog `score_identity` and provenance `brief_hash`; optional `expected_score_identity` /
  `expected_brief_hash` must match. A missing/ambiguous/mismatched group excludes records with
  reason `score_identity_unavailable`; if nothing remains, the typed refusal above applies. No
  extra replay is performed to compensate.
- **Provenance:** `selection.metric_selection` keeps the selector's `selected_ids`/`excluded` and
  adds `n_records_considered` and `identity_excluded`; `selection.excluded_reasons` carries the
  full merged exclusion list.
- **Legacy objective versions** (anything outside 10/11) keep the historical path exactly;
  `metric_selection` stays `{"status": "not_applicable"}`.

The CLI gains `--allow-unranked-replay`, `--expected-score-identity` and
`--expected-brief-hash`; the function signature adds the same keywords.

## 6. New refusal reasons

Artifact build (`build_metric_training_artifact`, `status="refused"`):

```
identity:objective_version_missing
identity:objective_version_mismatch:<declared>!=<version>
identity:bounds_payload_missing
identity:bounds_payload_invalid:<detail>
identity:bounds_hash_mismatch
identity:brief_hash_missing
identity:score_hash_missing
identity:score_payload_invalid:<detail>
identity:score_identity_mismatch
```

Artifact load/validate (`ArtifactCheck.reason`, first of `reasons`):

```
artifact_zip_invalid, artifact_zip_truncated, artifact_format_foreign
artifact_manifest_missing, artifact_manifest_invalid
artifact_member_missing, artifact_member_unexpected, artifact_pickle_refused
artifact_array_dtype, artifact_array_shape, artifact_array_sha256, artifact_array_nonfinite
artifact_checksum_mismatch, artifact_expected_checksum_mismatch
artifact_observation_ids_not_unique, artifact_status_invalid, artifact_version_mismatch
artifact_objective_version_unsupported
artifact_component_schema_mismatch, artifact_component_schema_hash_mismatch,
artifact_component_schema_hash_missing
artifact_j_row_mismatch, artifact_x_out_of_box, artifact_x_shape
bounds_identity_missing, bounds_identity_mismatch, bounds_identity_payload_missing,
bounds_identity_payload_invalid, artifact_encoding_bounds_invalid
score_identity_missing, score_identity_mismatch, objective_version_mismatch,
brief_identity_mismatch, score_module_mismatch
artifact_identity_mismatch, artifact_identity_missing
```

Proposal (`MetricProposalResult.reason`): `bounds_identity_missing`, `bounds_identity_mismatch`
(the `metric_identity` reason codes), in addition to the existing pool/model reasons.

Cohort: `metric_selection_unavailable` (group-level), `score_identity_unavailable` (record-level),
plus the existing `design_params_missing` / `encode_refused:<Exception>` encoding reasons.

## 7. Verification (synthetic only)

```
$env:PYTHONPATH="C:/Users/hunte/Hrns/hornfab-metric-bo-wt"
& C:/Users/hunte/Hrns/oc-wt/bo-study/bayes-venv/Scripts/python.exe -m pytest \
    tests/test_bo_metric_training.py tests/test_bo_metric_model.py \
    tests/test_bo_metric_propose.py tests/test_study_cohort_metric_selection.py \
    tests/test_study_cohort_intake.py tests/test_bo_metric_identity.py \
    tests/test_bo_metric_artifact.py tests/test_study_cohort_fallback_safety.py \
    -q -p no:cacheprovider
```

Result: **74 passed, 0 failed**. New files: `test_bo_metric_artifact.py` (12),
`test_bo_metric_identity.py` (10), `test_study_cohort_fallback_safety.py` (8). The four Pass 1
metric test files and `test_study_cohort_metric_selection.py` pass unchanged (no assertion was
weakened and no tolerance was loosened).

Negatives covered: missing/wrong bounds hash, same-`d` different physical box, changed transform,
changed active-key order, valid match, legacy scalar policy unaffected, tampered artifact byte,
NaN/Inf array, `J` row mismatch, component reorder, wrong/missing score identity, missing/
ambiguous score identity in a cohort, uncodable-only refusal, authorized replay, unencodable+one
encodable ranked path, legacy v7 path unchanged.

## 8. Cross-lane interface (Lane A)

Lane A may rely on these exact names and semantics:

```python
from hornlab_search.bo.metric_artifact import (
    artifact_bytes, artifact_from_bytes, load_artifact_file,
    validate_metric_training_artifact, ArtifactCheck,
)
from hornlab_search.bo.metric_propose import propose_metric_candidate

blob = artifact_bytes(artifact)
artifact2, check = artifact_from_bytes(blob, expected_checksum=artifact.checksum)
check2 = validate_metric_training_artifact(
    artifact2, encoding=projection, expected_bounds_hash=bounds_identity(projection),
    expected_score={...}, expected_task={...})
result = propose_metric_candidate(model, pool, require_identity=False,
                                  expected_bounds_hash=None)  # Pass 1 default
```

`artifact_from_bytes` never unpickles; `validate_metric_training_artifact` never repairs. Lane B
made no change outside its owned files.

## 9. Out of scope

No real historical replay, rescoring, BEM/GPU/mesh/solver call, queue change, optimizer default,
or score-version change. No `metric_identity` public-API change. `docs/INDEX.md`,
`docs/CODE_MAP.md`, `CONTINUITY.md`, `ISSUES.md` and `NOTES_FOR_SENIOR.md` were not edited.
