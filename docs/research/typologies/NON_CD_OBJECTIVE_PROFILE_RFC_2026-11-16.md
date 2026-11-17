# Non-CD objective profile — design RFC

**Date:** 2026-11-16
**Status:** PROPOSED — owner approval required section by section. Docs-only: no code, no tests, no
GPU, no queue change. This file is the only repo artifact written by this pass.
**Implements:** [`NON_CD_SCORING_TRUTH_HANDOFF_2026-11-16.md`](NON_CD_SCORING_TRUTH_HANDOFF_2026-11-16.md)
"Priority P1" (frequency-enveloped H/V scoring + DI roughness) and "Priority P2" (validation and
data continuity). It is the follow-on to the P0 GUI-truth pass, not a replacement.
**Labels:** `[verified]` = read from this checkout's code/docs this session; `[measured]` = an
in-repo evidence artefact; `[inferred]` = model/literature reasoning not re-fetched; `[proposed]` =
this RFC's recommendation. Numeric defaults in `[proposed]` bullets are owner decisions (§7).

Cross-references (reading order this RFC assumes):
[`SCORING_NON_CD_SOURCES_2026-11-15.md`](SCORING_NON_CD_SOURCES_2026-11-15.md),
[`audit_2026-11-15/ADMISSION_DECISIONS.md`](audit_2026-11-15/ADMISSION_DECISIONS.md),
[`audit_2026-11-15/READINESS.md`](audit_2026-11-15/READINESS.md),
[`LECLEACH_OBJECTIVE_V6_2026-11-05.md`](LECLEACH_OBJECTIVE_V6_2026-11-05.md),
`docs/plan/01_CONTRACTS.md` §11 (FROZEN — cited only, never edited),
`docs/CONTINUITY.md` 2026-10-26 `f0_v_hz` amendment entry (the additive-amendment template).

---

## 0. Bottom line

- Add an **opt-in, frequency-enveloped coverage profile** under `target.coverage_profile`, scored only
  by a **new objective version, v9**. v9 is the next free number: v8 already exists as an
  **unregistered, offline-only PROPOSAL** module (`hornlab_search/objective/scalar_v8.py`,
  `[verified]`, and `SUPPORTED_OBJECTIVE_VERSIONS` is still `(1,…,7)`, `objective/versions.py:20`).
- **Constant fallback = exact old behaviour.** Every existing version (1–7), every saved response,
  every stored J and every running queue snapshot is byte-identical when the key is absent. This is
  the repo's `f0_hz`/`f0_v_hz` additive-amendment pattern, not a redefinition.
- The profile is a **soft corridor**, not one forced curve: penalty is **zero inside `[min,max]`**
  and quadratic outside. It is a first-class scored input, never reverse-engineered from DI.
- **Never rank v9 J against v7/v6 J.** New score identity; cohort gate must refuse cross-pooling.
- `distd` keeps its exact v7 meaning (`std(DI)`, `[verified]` `scalar_v7.py:537-542`). The honest
  residual metric is a **new** `di_roughness` term. The analytic fixture `DI = 12 + 5·log10(f/700)`
  proves the old term is `> 0` and the new one is `0` within precision (§5).
- No classification by family name (`[verified]` handoff "User intent"; audit
  `READINESS.md:48`). `profile_mode` is advisory metadata only.

---

## 1. Goal and non-goals

### 1.1 Goal

1. Let a brief *declare*, per plane and per frequency, the coverage an owner actually wants — a
   preferred total included angle with a permitted min/max corridor that narrows with frequency.
   Score the measured H/V beamwidth against that declaration.
2. Preserve constant-directivity scoring as a *chosen goal*, not a default the search must obey:
   zero slope/constant width remains legitimate when constancy is the objective
   (`[measured]` `ADMISSION_DECISIONS.md:52-59`; `READINESS.md:48`).
3. Supply an honest DI **shape-smoothness** term that does not confuse "a straight non-zero slope"
   with "a bumpy response".
4. Make the 8 kHz floor, the ripple window, the diagonal reference and the feasibility preflight
   **coherent with the same profile** in v9, so no term contradicts another.
5. Keep everything additive and reversible: an owner can approve sections independently, and a
   deferred section leaves the rest optional.

### 1.2 Non-goals (hard boundaries)

- **Do not mutate v6/v7 semantics.** No existing `cov`, `dislope`, `distd`, `diag`, `di`, `rip`,
  `cov_pat`, `bw8k_floor` definition changes for versions ≤ 7. `[verified]` `scalar_v7.py:519-563`,
  `scalar_v6.py:193-343`.
- **No `J` value mutation for existing briefs.** Absent profile ⇒ bit-identical J, config/solve/target
  hashes and dataset record bytes (`[verified]` `spec.py:43-101`, `record.py:172-188`).
- **Opt-in only.** A v9 brief without `target.coverage_profile` is a config error. No silent
  typology→scorer switch, no automatic family classification (`[verified]` handoff line 7;
  `READINESS.md:48`).
- **No classification by family name.** `profile_mode: smooth_narrowing` is a human label; the
  scorer never reads it to choose a curve or a version.
- **Not a universal slope.** No single `di_slope_target` (0, 5, 6 dB/dec) is asserted as a home
  preference (`[measured]` `ADMISSION_DECISIONS.md:52-59`; `READINESS.md:40,48`).
- **Not v6's job.** v9 is for non-6 briefs. It does not absorb `load_near`/`z_smooth`/`cov_pat`/
  `di_rise`; a loading-first JMLC brief stays on v6 (§4.7).
- **No solver/mesher/metrics changes.** Only `targets/spec.py`, a new `objective/scalar_v9.py`, the
  version dispatch, config validation and the analysis identities (§3.5). No GPU, no queue edits.
- **`docs/plan/01_CONTRACTS.md` is FROZEN** (`[verified]`). This RFC amends behaviour by dated
  additive amendment recorded in `docs/CONTINUITY.md` + `NOTES_FOR_SENIOR.md`, exactly as the
  2026-10-26 `f0_v_hz` amendment did (`[verified]` `CONTINUITY.md:5368-5375`). It does not touch the
  contract file.

---

## 2. Proposed additive schema

### 2.1 YAML (illustrative, `[proposed]`)

```yaml
target:
  coverage_h_deg: 80            # STILL required; identity + DI Gaussian reference + legacy fallbacks
  coverage_v_deg: 50
  band_lo_hz: 350
  band_hi_hz: 8000
  f0_hz: 700                    # optional, existing key; the owner-declared H pattern onset
  f0_v_hz: 900                  # optional, existing key; the owner-declared V pattern onset
  coverage_profile:             # NEW, optional; present ⇒ this target is a profile target
    mode: frequency_envelope    # the only accepted mode today
    interpolation: log_frequency# the only accepted interpolation today
    h:                          # total included angle, degrees; >= 2 anchors, hz ascending
      - {hz: 700,   preferred_deg: 80, min_deg: 72, max_deg: 90}
      - {hz: 2000,  preferred_deg: 72, min_deg: 62, max_deg: 84}
      - {hz: 8000,  preferred_deg: 58, min_deg: 50, max_deg: 70}
    v:
      - {hz: 900,   preferred_deg: 50, min_deg: 44, max_deg: 58}
      - {hz: 8000,  preferred_deg: 38, min_deg: 32, max_deg: 46}
  profile_mode: smooth_narrowing  # OPTIONAL advisory label; NEVER used for classification
```

`[verified]` the shape of this block follows the handoff's `target.coverage_profile` sketch
(handoff lines 50-64); it is tightened here to this repo's strict-key, per-plane discipline. The
anchors are **deliberate, validated acoustic preferences**, not automatic geometry guarantees — the
comment is part of the schema's intent, not decoration.

### 2.2 Where it lives and why

- **Under `target`, not `objective`.** A profile is *target semantics* (what coverage is wanted),
  exactly like `coverage_h_deg`/`f0_hz`. Weights/tolerances that grade it belong in the `objective:`
  block. `[verified]` `Target` owns coverage/f0 today (`spec.py:8-40`).
- **A new dataclass field, appended last:**
  `coverage_profile: dict | None = None`. Appending keeps `Target` positional construction
  compatible with the historical `f0_hz`/`f0_v_hz` pattern (`[verified]` `spec.py:7-36`).

### 2.3 `Target.from_dict` strict unknown-key policy — how it is respected

`[verified]` `spec.py:52-55`: `known = {f.name for f in fields(cls)}`; any other key raises
`ValueError`. Adding the dataclass field automatically adds `coverage_profile` to `known`; we then
**explicitly parse and validate it** (never pass the raw dict through unvalidated) and the unknown-key
refusal remains fully strict:

```
if d.get("coverage_profile") is not None:
    kw["coverage_profile"] = validate_coverage_profile(d["coverage_profile"], t_band_lo, t_band_hi)
```

The check runs after the scalar band is known, so anchor-vs-band validation is possible in one
place. This is the **same additive-amendment pattern** as `f0_hz` (2026-10-25) and `f0_v_hz`
(2026-10-26): append a documented field with a `None` default, validate only when present, and keep
every absent-key path byte-identical (`[verified]` `CONTINUITY.md:5368-5375`, `spec.py:69-72`).
The **version stamp** is the RECORD's `objective_version` (v9) plus a dated `CONTINUITY.md` /
`NOTES_FOR_SENIOR.md` amendment; `Target` itself carries no schema-version integer today and this
RFC does not add one (`[proposed]`, avoiding a frozen-contract surface).

### 2.4 Validation rules (`[proposed]`, all `ValueError`/`ConfigError` naming the exact path)

A profile is valid iff **all** hold:

1. `mode` is present, is a string, equals `frequency_envelope`.
2. `interpolation` is present, is a string, equals `log_frequency`.
3. Unknown keys at profile / anchor level are **refused** (the repo's typo policy,
   `[verified]` `spec.py:52-55`, `config.py:240-243`).
4. Both `h` and `v` are present and are non-empty lists of mappings. Each anchor mapping has exactly
   the keys `{hz, preferred_deg, min_deg, max_deg}`.
5. **≥ 2 anchors** per plane.
6. `hz` is finite, `> 0`, and **strictly ascending** within each plane.
7. Every anchor `hz` is **within `[band_lo_hz, band_hi_hz]`** (no extrapolated control points).
8. `preferred_deg`, `min_deg`, `max_deg` are finite and `> 0`; `max_deg > min_deg`;
   `min_deg <= preferred_deg <= max_deg` (inclusive).
9. **Plane independence:** `h` and `v` may have different anchor frequencies and counts; each plane
   is interpolated and scored on its own. No cross-plane monotonicity is imposed.
10. If `f0_hz`/`f0_v_hz` are present they keep their existing validation
    (`[verified]` `spec.py:82-94`); the profile's lowest anchor need not equal them, but the
    feasibility record (§4.6) compares the two.
11. `profile_mode`, if present, is a non-empty string; it is **not** semantically validated against a
    scorer and never selects a curve. (Recommended values document intent only.)

`coverage_h_deg`/`coverage_v_deg` remain required and keep their current meaning: the DI Gaussian
reference (`[verified]` `scalar_v2.py:377-378`) and the legacy code path for versions ≤ 7. v9's
coverage term reads the **profile**, not these scalars; a brief should keep the scalars equal to the
profile's nominal centre (lowest-anchor `preferred_deg`) so reports and the DI reference stay honest.
This is documented, not enforced, to keep the amendment additive.

### 2.5 Constant fallback = exact old behaviour

- **Absent `coverage_profile`** on any version ⇒ no new field in the parsed target, no new keys in the
  terms dict, no new branch taken. `[verified]` the record writer must pop `coverage_profile` when
  `None` so pre-amendment record bytes stay identical — the exact rule `record.py:179-188` already
  applies to `f0_v_hz`/`loaded_hi_hz`/`driver_exit_radius_mm`.
- **Present on a version ≤ 7** ⇒ config load refuses it: those versions' `_BLOCK_KEYS` and the
  `Target` path must not silently accept a key they cannot score. Concretely, `Target.from_dict`
  accepts the field only when the scoring version is 9; the config loader raises
  `ConfigError("target.coverage_profile is only valid with objective.version 9")` otherwise.
  (Implementation detail: pass the resolved objective version into target validation; or reject the
  key in `_validate_objective_block`-adjacent loader logic. `[proposed]`.)
- **Present on v9** ⇒ full profile path.
- **Constant CD can still be expressed** as a profile with identical anchors
  (`preferred = min = max` per plane) **or** simply by staying on v7. The audit's point holds:
  a flat target is legitimate when constancy is chosen, so we neither forbid it nor force it.

---

## 3. Objective version vs opt-in-block — the decision

### 3.1 Recommendation: a new objective version, **v9**

`[proposed]` New version. Justification:

1. **Dispatch is single-source and strict.** `[verified]` `versions.py:10-20` is the only version
   source truth; `search/evaluate.py` asserts its dispatch table matches it, and
   `dataset/record.py:481-488` refuses any unsupported `objective_version`. A new version is the
   repo's designed seam; an opt-in block under an existing version would have to branch scoring
   inside v7 — forbidden by §1.2.
2. **Identity and replay stay legible.** A v9 record is unmistakably non-v7; offline rescore,
   surrogate training and cohort tooling already key on `objective_version`
   (`[verified]` `cohorts.py:66-69,304-306`). Silent in-version branching would let two physically
   different J's share a `score_identity` shape.
3. **No collision.** v8 is taken by an unregistered offline PROPOSAL (`[verified]`
   `scalar_v8.py:1-13`; `versions.py:20` = 1–7). v9 is the next number that is neither dispatched nor
   already used by a proposal.
4. **Rollback is trivial.** Delete/never register v9; old briefs are untouched.

`[proposed]` Registration checklist (mirrors v6's rollout, `[verified]` `LECLEACH_OBJECTIVE_V6_…:89-94`):
`objective/scalar_v9.py` (V9Params, `objective_v9`, defaults) · add `9` to
`SUPPORTED_OBJECTIVE_VERSIONS` · add the dispatch branch in `search/evaluate.py` · accept `9` in
`_validate_objective_block` with `V9Params.from_block` · add v9 to the dataset-record comment ·
new `examples/briefs/**/*_v9_profile.yaml`. **Do not register v9 until the owner approves §4 and §5
and the P2 gates in §6 are written.**

### 3.2 Identity treatment — the profile must ride the target hash

`[verified]` the semantic scoring target identity is `tools/analysis/catalog.py::_target_identity`
(lines 415-420), and `target_hash = _sha16(_target_identity(target))` (line 646). Today
`_target_identity` returns only the explicit scalar keys; `_target_block` (lines 395-412) whitelists
the keys it emits (plus `raw_keys`, which is provenance, **not** scoring — line 416).

**Requirement (`[proposed]`, mandatory):** add the profile to **both**:

- `_target_block(...)` return dict: `"coverage_profile": target.get("coverage_profile")`.
- `_target_identity(...)` key tuple: `..., "freq_weights", "coverage_profile")`.

If only `_target_block` changes, `raw_keys` (provenance) might differ but `_target_identity` would
not — and **two briefs differing only in their coverage profile would collide to the same
`target_hash`**, pooling unrelated scoring semantics in cohorts. Adding it to `_target_identity`
fixes that. Because `record._target_dict` lays the profile into the record's `target` block
(`[verified]` `record.py:172-188,385`), the catalog reads it through `meta["target"]` unchanged.

Also required so the gate sees it:

- `cohorts.py` `attach_score_spec` target sub-dict (lines 219-226) — add `coverage_profile`.
- `cohorts.py` `_spec_hash` key set (lines 247-250) — it hashes `spec["target"]`; adding the key to
  the target dict is sufficient, but name it explicitly in the docstring.
- `cohorts.py` `_task_compatible` per-key loop (lines 304-314) — add `coverage_profile` to the
  compared keys (full-object equality), so a profile-vs-flat brief mismatch returns
  `target_coverage_profile_mismatch` and is excluded rather than pooled.

`[verified]` a v9 brief also changes `config_sha` (file bytes) and the `score_identity`
(`objective_version` + `target_hash` + `brief_hash` + full spec + terms schema, `cohorts.py:274-280`),
so the run-level identity already separates; the target-hash amendment above closes the semantic gap.

### 3.3 J comparability rules (`[proposed]`, normative)

1. **Never rank v9 J against v6/v7 J.** Different terms, different normalisation, different target.
   Report a v9 J only beside another v9 J on the **same** profile/brief/weights/tolerances.
2. Within v9, comparability requires identical `target_hash` + `objective_version` + `brief_hash` +
   full score spec (`cohorts.py` already enforces this for `objective_version`, `brief`,
   `brief_hash`, `target_hash`, `score_identity`).
3. v9 and v7 may be **compared on separate, unweighted measured metrics** (beamwidth curves, DI,
   slope, loading, diagonal) — never on the scalar J (`[measured]` handoff line 85; audit
   `ADMISSION_DECISIONS.md:66-69` prescribe the same separate-metrics reporting).
4. A v9 brief that drops `di`/`distd` weight to zero is still identified by its **full spec**
   (`cohorts.py:247-250` hashes weights/tolerances), so "same J, different meaning" cannot pool.

### 3.4 Cohort gate behaviour to verify (`[verified]` current, `[proposed]` amendment)

- `TASK_FIELDS = ("brief","brief_hash","family","target_hash","objective_version")`
  (`cohorts.py:67`) already blocks cross-version and cross-target pooling.
- `attach_score_spec` marks `score_parameters_known` and computes `score_identity`; without a spec it
  warns `score_parameters_unknown` (`cohorts.py:25-27,273-281`). v9 rescores MUST pass the resolved
  spec so score identity is complete.
- After the §3.2 amendment, add a **gate test**: two briefs identical except for one profile anchor
  must yield different `target_hash` and be rejected with a target mismatch — not silently pooled.

---

## 4. Scored term definitions on the profile (v9)

All v9 terms reuse v4/v7 conventions: `J = Σ_k w_k · raw_k / tol_k + penalty`, `terms` stores
normalised values, unknown weight keys are warned-and-ignored as today (`[verified]`
`scalar_v7.py:195-204`). Tolerances have **no silent defaults** in the v9 block
(`[verified]` the v4/v6/v7 precedent). All means are frequency-weighted by `freq_weights` when set,
else plain, over the score band `f >= f0` (`[verified]` `scalar_v2.py:316-357`).

### 4.1 Per-frequency envelope evaluation

For a plane with anchors `(hz_i, pref_i, min_i, max_i)`:

```
x = log10(f)
pref(f), min(f), max(f) = piecewise-linear interpolation of the anchors in x
```

- **Clamp, do not extrapolate** outside the outer anchors (`[proposed]`): below the lowest anchor use
  the lowest anchor's values; above the highest use the highest. Anchors are guaranteed within the
  band (§2.4 rule 7), so scored frequencies outside the anchor span only occur between
  `band_lo`/`band_hi` and the outer anchors.
- H and V are interpolated independently (plane independence, §2.4 rule 9).

### 4.2 `cov_profile` term — soft corridor (`[proposed]`)

Per plane, per scored frequency `f`, with measured \(-6\) dB beamwidth `bw` (outermost crossings,
`[verified]` `metrics/polar.py:59-120` semantics; multilobe caveat honoured):

```
if bw < min(f):      d = min(f) - bw          # too narrow
elif bw > max(f):    d = bw - max(f)          # too wide
else:                d = 0                    # inside corridor: ZERO
cost_f = (narrow_ratio_if_too_narrow · d²) / 100
```

- **Penalty is zero inside `[min,max]`** — the corridor is a permitted envelope, not a point target.
- **Outside**, the quadratic `d²/100` matches v4/v7's per-frequency scale (`[verified]`
  `scalar_v2.py:332-333`), then the mean is normalised by the brief's `cov_profile` tolerance
  (`[proposed]` default `8.0`, matching the audit's widened non-CD `cov` tolerance,
  `[measured]` `SCORING_NON_CD_SOURCES_2026-11-15.md:153`).
- **`narrow_ratio_if_too_narrow` = 1.0 by default**, i.e. the corridor already encodes how much
  narrowing is acceptable, so going below `min` is not double-penalised. A brief may set
  `cov_narrow_ratio > 1` to charge extra below `min`; it is inert inside the corridor.
- Combine planes: `raw = mean_H(cost) + cov_v_weight · mean_V(cost)` (the v7 split,
  `[verified]` `scalar_v7.py:503-505`), normalised by one `cov_profile` tolerance.
- Below-onset rule: reuse `cov_below_f0` (`mask` default / `one_sided`) over the profile's per-plane
  onset (§4.6). `[verified]` `scalar_v7.py:410-449`.

### 4.3 `rip` on per-frequency envelope widths

`[verified]` current `rip` calls `ripple_detrended_db(ha, sh[j], target.coverage_h_deg)` with a
**fixed scalar width** at every frequency (`scalar_v2.py:140-152`). When H/V targets become functions
of frequency this is the second component the handoff flags (line 16).

`[proposed]` in v9: call the detrended ripple helper **per frequency** with the plane's envelope
outer width at that frequency, i.e. the total-window argument is `max_h(f)` for H and `max_v(f)` for
V. Rationale: ripple is an in-coverage quality measure; the honest window is the widest coverage the
owner permits at that frequency, so natural narrowing inside the corridor is not scored as a
taper artefact. `[inferred]` from the v2 detrended-ripple design (`scalar_v2.py:10-27`). Version ≤ 7
keeps the fixed scalar path exactly. Ripple remains over the full in-band set, not only `f>=f0`
(`[verified]` `scalar_v2.py:364-370`) — v9 preserves that choice.

### 4.4 `bw8k_floor` derived from the envelope min (`[proposed]`)

`[verified]` v7's floor is `bw8k_floor · coverage_h_deg` (and V) at the highest solved `f <=
min(8000, band_hi)`, one-sided narrow-only, raw `(dh²+dv²)/100` (`scalar_v7.py:384-407`). The handoff
requires the v9 floor to come from the profile, not `0.75·flat` (line 64).

v9 rule:

```
i8 = argmax{ f_j : f_j <= min(8000, band_hi) }
floor_h = min_h(f_i8)      # interpolated envelope MINIMUM at that frequency
floor_v = min_v(f_i8)
raw_floor = (max(0, floor_h - bw_h)² + max(0, floor_v - bw_v)²) / 100
```

- **Only narrowing is charged**, exactly v7's one-sided semantics.
- `[proposed]` a v9 tunable `bw8k_floor_mode: envelope_min` (default) with optional explicit
  overrides `bw8k_floor_h_deg`/`bw8k_floor_v_deg` for an owner who wants a stricter absolute seat
  minimum. Never `0.75 × flat`.
- The floor's frequency and values are reported as diagnostic keys so the GUI can mark them
  separately from the scored target (P0 requirement, handoff lines 43-45).

### 4.5 `diag` in v9 non-CD briefs — disable the flat round reference, keep diagnostics

`[verified]` v4/v7 `_diag_term` compares 45°/135° diagonal \(-6\) dB beamwidths to a **round
reference** `t_ref = (coverage_h + coverage_v)/2` at every scored frequency
(`scalar_v4.py:198-223`). The handoff calls this unfair for anisotropic/narrowing patterns and
instructs: disable the target-centred `diag` penalty in **new non-CD** briefs pending a better
full-pattern diagnostic, while continuing to **report** measured diagonal response and multilobe
flags (handoff line 68; `SCORING_NON_CD_SOURCES_2026-11-15.md:141` is the weaker "mostly fair"
reading — the handoff governs).

v9 rule (`[proposed]`):

- **`diag` default weight `0.0`** in v9 non-CD briefs; `diag_mode: off` default.
- `diag_mode: round` is available **only if explicitly written**, retains the exact old math, and is
  labelled in the brief as a CD-shape prior (the audit's "shape prior, not preference",
  `[measured]` `ADMISSION_DECISIONS.md:57-59`).
- **Always report** measured diagonal beamwidths (`w45`, `w135`), the number of polar crossings and
  multilobe flags as v9 **diagnostic keys** (never weighted). This keeps the information the owner
  needs without scoring a round ideal a rectangular non-CD horn was never designed to hit.

### 4.6 Feasibility: independent `f0_h` / `f0_v` from envelope + mouth physics

`[verified]` today `f0` is a single scalar with a per-plane `f0_v` (spec.py:17-24) and the campaign
derives required mouth `d = KEELE_K/(f0·coverage)` (config.py:1750-1757; `KEELE_K = 25400 m·deg·Hz`
in `constants.py:8-10`). The handoff demands independently derived per-plane onsets from **tested
physics/mounting**, and warns not to hide the conflict in J (line 70).

v9 feasibility (`[proposed]`):

- Define the owner-declared onset per plane = the **lowest anchor `hz`** (the profile's own statement
  of "from here down I accept widening").
- Compute the **physics-limited onset** per plane:
  `f_phys,plane = KEELE_K / (mouth_dim_m · envelope_width_at_lowest_anchor_deg)`.
- Report both `f0_h_declared`/`f0_v_declared`, `f0_h_physics`/`f0_v_physics`, the actual
  `mouth_w_mm`/`mouth_h_mm`, and a `feasible: true|false` flag with the per-plane shortfall. The
  config's existing `feasibility` record (config.py, S1a) is the natural carrier; v9 extends it, it
  does not replace it.
- **Do not silently clamp** the profile to what is feasible; report the conflict and let the owner
  widen `min_deg`/lower the anchor, or accept the penalty honestly.

**The handoff's Keele numbers and where they come from (`[verified]` handoff line 70):** "with a
600W × 480H mouth and target 80H × 50V to 700 Hz, empirical Keele sizing predicts ~**496 mm**
horizontal aperture and ~**794 mm** vertical aperture for the desired CD control." These are the
mouth dimensions the Keele pattern-control rule `f0 = K/(mouth · coverage)` needs to *hold* the angle
to 700 Hz. The vertical requirement (~794 mm) exceeds the actual 480 mm mouth, so strict 50° V at
700 Hz is likely physically unattainable for a stand-alone 480 mm-tall horn (baffle/complex profile
can shift onset). **Constant check:** the repo's `KEELE_K = 25,400 m·deg·Hz` gives
`25.4e6/(700·80) = 453.6 mm` H and `25.4e6/(700·50) = 725.7 mm` V — smaller than 496/794 but the same
conclusion (V far exceeds 480 mm). The discrepancy between the handoff's 496/794 and the repo
constant's 453.6/725.7 is an **open decision** (§7 #10): quote both, adopt one for the feasibility
gate.

### 4.7 v6 interplay — explicitly NOT required

v9 is for non-6 briefs. Do **not** import v6's `load_near`/`z_smooth`/`cov_pat`/`di_rise`
(`[verified]` `scalar_v6.py:34-66`, `LECLEACH_OBJECTIVE_V6_…:57-71`). A loading-first JMLC/Le Cléac'h
brief that wants near-corner loading stays on v6. v9 reuses v7's `flat`, `flat_cv`, `rip`, `load`
(combined loading) and the new profile/roughness terms; it does not merge the two class objectives.

### 4.8 v9 term set (summary)

| Key | Raw definition (v9) | Default w | Default tol | Notes |
|---|---|---|---|---|
| `cov_profile` | corridor H + `cov_v_weight`·corridor V (§4.2), zero inside `[min,max]` | 1.0 | 8.0 | new |
| `rip` | detrended H+V ripple on per-frequency envelope `max` width (§4.3) | 1.0 | 1.0 | inherits v7 scale |
| `di_roughness` | `std(DI − fitted(a+b·log10 f))` on score band (§5) | 1.0 | 1.0 dB | new |
| `dislope` | `(slope − di_slope_target)²` on score band, transparent target | 0.0–1.0 | 9.0 | slope not universal |
| `flat` | detrended on-axis flatness (`flat_band: scored`) | 0.5 | 1.5 | v7 |
| `flat_cv` | constant-velocity on-axis flatness | 1.0 | 1.5 | v7, optional |
| `load` | v7 combined loading penalty | 1.0 | 0.3 | v7 |
| `distd` | legacy `std(DI)` — **kept, weight 0 by default** | 0.0 | 2.0 | never redefined |
| `diag` | 45/135° vs round reference — **weight 0, `diag_mode: off`** | 0.0 | 2.0 | diagnostics only |

Diagnostics (never weighted): `bw8k_floor_h/v`, `bw45/bw135`, `n_crossings`, `multilobe`,
`f0_h/v_declared`, `f0_h/v_physics`, `di_roughness_slope`.

---

## 5. `di_roughness` — the detrended DI residual term

### 5.1 Definition (`[proposed]`)

Over the score band (`band & f >= f0`), using the **finite** DI samples `(f_k, DI_k)`:

1. Fit `a + b·log10(f)` by **ordinary least squares, unweighted** — the same regression convention
   `dislope` uses (`[measured]` `READINESS.md:40`: slope is an unweighted regression against
   `log10(f)`, dB/decade). Requires **≥ 3 finite samples** (two samples fit exactly ⇒ residual 0 by
   construction, so 2 is meaningless for a roughness term; report `NAN_TERM_FILL` below 3).
2. Residual `r_k = DI_k − (a + b·log10 f_k)`.
3. `di_roughness = std(r)` with **population std (`ddof=0`)**, matching `np.std` used by `distd`
   (`[verified]` `scalar_v7.py:540`). Units: dB.

Weights/tolerances are **brief fields** in the v9 objective block
(`weights.di_roughness`, `tolerances.di_roughness`); `[proposed]` default weight `1.0`, tolerance
`1.0 dB` (the audit's `distd` tolerance scale, `[measured]` `SCORING_NON_CD_SOURCES_…:22`). A brief
that wants a slope preference keeps `dislope` with its own explicit `di_slope_target` — the two terms
are orthogonal: `dislope` scores the slope, `di_roughness` scores the departure from a straight line.

### 5.2 It never redefines v7 `distd`

`[verified]` v7 `distd = std(DI)` over the score band (`scalar_v7.py:537-542`; `README` label already
honest that it is raw std, `[measured]` `READINESS.md:40`). v9 keeps the `distd` key with its exact
math available (default weight 0) and adds `di_roughness` as a **separate key**. No existing row,
terms schema for versions ≤ 7, or stored J changes.

### 5.3 Analytic fixture (the argument, per handoff P2 line 73)

`DI(f) = 12 + 5·log10(f/700)` on any band:

- `dislope` target-slope error: fitting `DI = a + b·log10 f` recovers `b = 5` exactly ⇒ error `0`.
- `di_roughness`: residuals are identically `0` ⇒ `std(r) = 0` within float precision.
- **v7 `distd` = `std(DI) > 0`** — a perfectly straight, monotonic rise has non-zero variance, so the
  old term charges it. This **documents the bug/misnomer** (handoff line 25, line 73) without changing
  v7: a smooth rise is *constancy* failure, not *roughness*. The AES constancy metric behaves exactly
  this way (§8 caveat).

`[proposed]` the P2 gate asserts: `v7.distd > 0` (e.g. `> 1e-3`), `v9.di_roughness <= 1e-12`,
`v9.dislope_error <= 1e-12` on this fixture.

---

## 6. Validation and rollout gates (P2) — ordered, checkable

`[proposed]` run in this order; a later gate does not excuse a skipped earlier one. All are offline
and non-GPU except where a stored solve is replayed. **Hygiene rule (binding, `[verified]`
`AGENTS.md`):** use the filtered non-GPU command
(`pytest -m "not slow and not gpu and not crosscheck" -n 6 --dist loadscope -p no:cacheprovider`)
under active GPU workloads; **do not run unfiltered tests**; **do not write to modules while any
BoTorch/BO study is pinned to current code hashes**; do not edit running queue/config snapshots.

| # | Gate | Pass condition | Evidence source |
|---|---|---|---|
| G0 | **Hygiene** | filtered command used; no module write while studies pinned; no queue/snapshot edits | `AGENTS.md` test-profile rules |
| G1 | **Old-J identity replay** | capture `config_sha`, seed hash, solve-spec hash, J for one v6 (`lecleach_rollback_1in_v6`) and one v7 (`room_landscape_80x50_700_hf1440_v7`) golden **before** the edit; **after** the edit all bytes/J identical; absent-profile dataset record bytes byte-identical | `CONTINUITY.md:5368-5375` template; `[verified]` `record.py:179-188` |
| G2 | **Analytic DI fixture** | `DI=12+5·log10(f/700)`: v7 `distd > 0`; v9 `di_roughness == 0` (≤1e-12); `dislope` error `== 0` | handoff P2 line 73 |
| G3 | **Synthetic flat-vs-narrowing scorer preference** | old v7 flat scorer favours 80×50 flat over a deliberate narrowing response; v9 corridor rewards the matching narrowing response and gives ~0 inside-corridor cost; **neither scorer changes class based on geometry ID / family name** (same response, two briefs; swap the config name, J unchanged) | handoff P2 line 74 |
| G4 | **Per-frequency polyline/curve equality** | for every **solved/scored** frequency, H/V target degrees used by the scorer equal (a) the BW-chart polylines and (b) the isobar ±half-angle curves, including one-sided below-onset windows and `f0_v`; unscored frequencies carry no phantom guide | handoff P2 line 75; P0 helper (handoff lines 40-47) |
| G5 | **v6 two-design different `fc`** | two designs sharing a v6 brief but different per-design `fc_hz` show **different** `f_pattern` onset guides (resolve via `fc_hz` → metrics scalar → `target.f0` → `band_lo`) | `[verified]` `scalar_v6.py:165-179`; handoff P2 line 75 |
| G6 | **v7 80×50 floor regression** | `bw8k_floor=0.75` on 80×50 gives floors **60° H / 37.5° V** and the raw one-sided floor penalty for narrower designs; **a v9 score test must make any changed floor explicit** (envelope-min) — no silent floor shift | `[verified]` `scalar_v7.py:384-407`; handoff lines 23, 76 |
| G7 | **Dispatch / weight–tolerance parity** | v9 weights/tolerances and version dispatch verified for **CMA, BoTorch, offline rescore, surrogate, GUI**; stored physical BEM responses reused without GPU where frequency/response fidelity suffice; **regenerate target-dependent metrics** (ripple, diag, roughness) rather than reusing old target-specific values | handoff P2 line 78; `[verified]` `versions.py`, `record.py:481-488` |
| G8 | **Cohort identity gate** | two briefs differing only in one profile anchor produce **different `target_hash`** and are rejected from a shared cohort (`target_coverage_profile_mismatch`), never pooled | §3.2/3.4; `[verified]` `catalog.py:415-420`, `cohorts.py:304-314` |
| G9 | **Comparability guard** | tooling refuses to rank a v9 J beside a v7/v6 J; mixed-version tables are marked descriptive-only | `[verified]` `cohorts.py:305-306`; §3.3 |
| G10 | **Rollback proof** | deleting v9 registration restores the pre-change suite/paths; no old brief or stored J touched | `[verified]` v6 rollout shape `LECLEACH_OBJECTIVE_V6_…:89-94` |

---

## 7. Open owner decisions (numbered, each with a recommended default)

1. **Soft-corridor strength / tolerance.** Recommend outside-corridor cost `d²/100` normalised by
   `tolerances.cov_profile = 8.0` (matches the audit's widened non-CD `cov`, `[measured]`
   `SCORING_NON_CD_SOURCES_…:153`). Alternatives: tighter `3.0` (near v7), or linear-outside for a
   flatter penalty. — *Default: quadratic, tol 8.0.*
2. **Does `cov_narrow_ratio` inherit below `min`?** Recommend **1.0** (the corridor already says how
   much narrowing is acceptable; do not double-charge). — *Default: 1.0; opt-in `>1` only.*
3. **HF floor policy origin.** Recommend **envelope `min` at `min(8000, band_hi)`**, one-sided,
   with optional explicit absolute overrides; **never `0.75 × flat`**. — *Default: envelope-min.*
4. **Does `diag` stay on via a flag?** Recommend **weight 0 / `diag_mode: off`** in v9 non-CD briefs;
   always **report** measured diagonal + multilobe; `diag_mode: round` only if explicitly written.
   — *Default: off, diagnostics on.*
5. **Brief naming / `profile_mode` semantics.** Recommend `profile_mode` be **advisory metadata only**
   (never selects a curve/version), and v9 briefs named `*_v9_profile.yaml`. — *Default: advisory.*
6. **Interpolation.** Recommend **piecewise-linear in `log10(f)`**, clamped (no extrapolation) beyond
   the outer anchors; H/V independent. — *Default: log-linear + clamp.*
7. **Anchor placement / onset.** Recommend **≥ 2 anchors**, lowest anchor = the owner-chosen pattern
   onset (not automatically `1.6·fc`), H and V may differ. — *Default: owner-declared onset.*
8. **`di_roughness` weight/tolerance/sample floor.** Recommend **weight 1.0, tolerance 1.0 dB,
   `ddof=0`, ≥ 3 finite samples** (else `NAN_TERM_FILL`). — *Default as stated.*
9. **Keep the `distd` key in v9?** Recommend **keep the key, default weight 0**, document it as
   legacy `std(DI)`; this preserves the terms-schema shape and dataset/cohort tooling, while
   `di_roughness` carries the honest signal. — *Default: keep, weight 0.*
10. **Keele constant for feasibility (496/794 vs 453.6/725.7).** Recommend the feasibility report use
    the repo's `KEELE_K = 25400 m·deg·Hz` (`[verified]` `constants.py:10`) and **quote the handoff's
    496/794 as a cross-check**; the owner picks which number gates `feasible`. Both reject strict
    50° V at 700 Hz for a 480 mm mouth. — *Default: repo constant + handoff cross-check.*
11. **Does a constant profile count as CD?** Recommend **yes**: identical anchors
    (`preferred=min=max`) express a constant target as a *chosen* goal, consistent with the audit
    (zero slope legitimate). — *Default: allowed.*
12. **Where does the profile appear in the GUI/report?** Recommend the P0 read-only helper renders
    the profile curve **only on scored frequencies**, as the scored target (not a hypothetical
    line); unscored regions carry no guide. — *Default: scored-only.*

---

## 8. Evidence sources

| Source | What it establishes | Label |
|---|---|---|
| Keele, **US4308932A** — <https://patents.google.com/patent/US4308932A/en> | Bi-Radial is a constant-directivity *invention*; CD is a design goal, not a property of a name | primary (patent) |
| Keele inventor list — <https://dbkeele.com/awards-and-recognition/> | Provenance of the CD patent corpus / pattern-control rule | primary |
| Crowe **ES-290** narrowing profile — <https://josephcrowe.com/products/es-290-biradial-wood-horn> | A deliberately narrowing biradial (non-CD by design) | primary (product page; live-fetch unverified this session) |
| Crowe **ES-800** CD comparator — <https://josephcrowe.com/blogs/news/es-800-biradial-wood-horn> | The CD counterpart used as a comparator | primary |
| Le Cléac'h, **ETF 2010 "Horn Profiles"** — <https://pearl-hifi.com/06_Lit_Archive/14_Books_Tech_Papers/LeCleac%27h_Jean-Michel/Horn_Profiles.pdf> | Smooth rising DI + loading are virtues; pattern starts ~1.5–1.8×fc; narrowing is by design | primary |
| Sridhar et al., **AES 2016 constant-directivity metrics** — <https://aes.org/publications/elibrary/elibrary-page/?id=18200> | **Caveat:** the paper makes `std(DI)` a metric for **constant** directivity. It is **not** a smooth-trend metric when a non-zero slope is intended — which is precisely why v9 needs a *detrended* `di_roughness` and why v7 `distd` is a constancy, not a roughness, measure | primary |
| `NON_CD_SCORING_TRUTH_HANDOFF_2026-11-16.md` (source-reviewed vs Hornfab `2c0e292…`) | P1 spec, the 496/794 Keele sizing, the P2 fixture list, user intent | in-repo primary |
| `audit_2026-11-15/ADMISSION_DECISIONS.md`, `READINESS.md` | No universal slope preference; zero slope legitimate as a chosen goal; `distd` replays a smooth-rise penalty; unweighted `log10(f)` slope | `[measured]` in-repo |
| `SCORING_NON_CD_SOURCES_2026-11-15.md` | Term-by-term non-CD assessment; `cov_narrow_ratio:1.0` + tolerance widening; Olive/Harman slope band (inferred) | mixed `[verified]`/`[inferred]` |
| `hornlab_search/objective/scalar_v7.py:384-407,519-563`; `scalar_v4.py:198-223`; `scalar_v2.py:140-152,316-357`; `scalar_v6.py:165-179` | Exact current term math this RFC must not mutate | `[verified]` code |
| `hornlab_search/targets/spec.py:7-101`; `config.py:240-243,325-369`; `record.py:172-188,481-488`; `versions.py:10-20`; `constants.py:8-10` | Strict-key target parsing, additive record emission, version dispatch, `KEELE_K` | `[verified]` code |
| `tools/analysis/catalog.py:395-420,646`; `tools/analysis/cohorts.py:66-69,219-281,304-314` | Target hash / identity and cohort gate mechanics | `[verified]` code |
| `docs/CONTINUITY.md:5368-5375` | The `f0_v_hz` additive-amendment precedent: absent = bit-identical, dated amendment, frozen contract untouched | `[verified]` in-repo |
| `LECLEACH_OBJECTIVE_V6_2026-11-05.md` | The versioned-objective rollout pattern v9 mirrors | `[verified]` in-repo |

**Caveat preserved from the AES source:** `std(DI)` is a *constancy* metric. A straight +5 dB/decade
rise passes "smooth" but fails "constant". v9 therefore scores *shape smoothness* only through
`di_roughness = std(DI − fitted line)`, and leaves any slope preference as an explicit,
brief-declared `dislope` target with a transparent weight — never a universal number.

---

## 9. Section approval checklist (owner)

- [ ] §1 Goal / non-goals (esp. "no family-name classification", "no v6/v7 mutation")
- [ ] §2 Schema + validation + constant fallback
- [ ] §3 v9 version decision + identity amendment (`_target_block` **and** `_target_identity`)
- [ ] §4 Corridor / rip / 8k floor / diag / feasibility term definitions
- [ ] §5 `di_roughness` definition + fixture
- [ ] §6 P2 ordered gates
- [ ] §7 Open decisions (12 defaults proposed)
