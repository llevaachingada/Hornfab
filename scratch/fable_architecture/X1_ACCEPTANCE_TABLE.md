# X1_ACCEPTANCE_TABLE — the consolidated contract-test verdict for the six lanes

> **AUTHOR AND STATUS — READ FIRST.** Compiled by the **lower-cost continuation lane agent** —
> **not by Fable (the senior/high-thinking reviewer) and not by the owner** — from the measured
> results in `X1_CONTRACT_TESTS.md` (N1), `X1B_CONTRACT_V2.md` (N1b, contract v2) and
> `X4_COMPLETION.md` (A8). The per-test verdicts below are the measurements' own outputs; this
> table adds no measurement. The statement that X1's original pass line "is not met as written" is
> a bookkeeping consolidation, and the recipe-schema remedy it mentions is **a finding proposed to
> the senior reviewer and owner, not a decision**. No tolerance, pass line, or frozen contract is
> changed. It closes the naming split ("X1B_CONTRACT_V2.md" is titled "N1b") by making this file
> the single place the X1 acceptance verdict lives.

## Pass line being assessed

`VALIDATION_EXPERIMENTS.md` Part 1, X1: *"A, B: all five acceptance tests pass for at least five of
six lanes; every exact metadata field recovered for all."* The five tests are
`CANONICAL_SURFACE_CONTRACT.md` §8 (refinement; mesh agreement; envelope; exact metadata;
determinism), amended by contract v2 (§12) for sampling, tolerance-relative Test 2, provenance
gating, and cause-stated Test 3.

## Verdict

**X1's pass line is NOT met as written** — and the reason is a finding, not undone work: Test 4
(exact metadata) cannot be completed because several exact fields do not exist in any stored recipe
or config. Test 2 passes 6/6 under contract v2; Tests 1 and 5 pass; Test 3 passes with stated
causes on three lanes, partial on one, fails-with-established-cause on two. The X1 failure
condition from the brief ("a source or shell field cannot be recovered without meshing") was never
invoked; the exclusions that occurred are provenance-gate exclusions (contract v2 rule 4), which
are a different mechanism.

## Per-lane × per-test table

| Lane | T1 refinement | T2 mesh agreement (inner) | T3 envelope | T4 exact metadata | T5 determinism |
|---|---|---|---|---|---|
| `hl__ext_throat_hvlaw_v7` | **pass** (10/10, worst 0.112 mm; N1) | **pass** 10/10, record p99 0.108 mm, floor 0.068 (N1b) | **partial** — W 1/10 >1 mm, H 4/10 >1 mm; cause: generator outward shell at the rim + meshed-rim overshoot; no closure contribution (N1b) | **partial** — termination kind not recorded anywhere (N1) | **pass** 10/10 (N1) |
| `hl__ath_tritonia_landscape_v9` | **pass** (10/10, worst 0.198 mm; N1) | **pass** 10/10, p99 0.247, floor 0.048 (N1b) | **pass with stated cause** — depth = rear closure exactly (N1b) | **partial** — wall thickness (mesher default) and termination kind not found (N1) | **pass** 10/10 (N1) |
| `hl__crowe_x_osse_cd_v7` | not testable (fixed 25×41 recipe) | **pass** 10/10, p99 1.353 vs threshold 1.451 (floor 1.160 = mesher fit) (N1b) | **fail with established cause** — the mesh departs from the design by up to 1.64 mm at the rectangular corner (v2 rule 3 class, not a sampler failure) (N1b) | **pass** all fields (N1) | **pass** 10/10 (N1) |
| `rf__section_axial_home_v7` | not testable (fixed 49×97 recipe) | **pass** 10/10, p99 0.856, floor 0.555 (N1b) | **pass** (depth after closure −0.05…+0.07) (N1b) | **pass** all fields (N1) | **pass** 10/10 (N1) |
| `hl__klangfilm_lame_curved_v1` | not testable (fixed 19×65 recipe) | **pass** 10/10 on digest-verified replacements (p99 1.155 vs 1.395); N1's ten excluded (digest `e3a1f4a3…` not reproducible at HEAD; 72 designs) | **pass** (≤0.12 mm; depth = closure/rollback) (N1b) | **partial** — fields complete for the replacements, but the historical kernel behind `e3a1f4a3…` is not in git history (provenance irreducible from this checkout) | **pass** 10/10 (N1) |
| `hl__biradial_es_style_v7` | **pass** (10/10, worst 0.110 mm; N1) | **pass** 10/10, p99 0.101, floor 0.047 (N1b) | **fail with established cause** — the sampler's union includes the generator's outward `outer_points` shell (1.0–1.5 mm/side W, 1.3–2.1 mm/side H) that the meshed box never contains; inner-sheet envelope agrees to 0.02 mm W (N1b) | **partial** — termination kind not found (N1) | **pass** 10/10 (N1) |
| `hl__lecleach_hv_landscape_smooth_v7` *(added for N4, excluded)* | — | **not testable** — not rebuildable at HEAD (`d6c9abd` H/V realization change after both stored runs; no digest; mesh box differs by up to 69 mm W/H, 231 mm D) | — | — | — |

Reinforcing evidence: `X4_COMPLETION.md` rebuilds the five `.x4` lane selections (11 designs each)
at 65×61 — **55/55 design hashes reproduced, 55/55 pass v2 rule 2** (Crowe worst p99 1.646 vs
1.712; medians ≤ 0.051), including the native rounded-rectangle lane N1 never covered — and
resolves the ROSSE digest gap as validator-only (`a10e784`), 11/11 geometry-reproduced.

## Metadata findings (why T4 cannot be completed from stored data)

| Missing field | Where it would live | Status |
|---|---|---|
| ATH wall thickness | recipe or config | a mesher default; absent everywhere (N1) |
| Termination kind — ext-throat, ATH, biradial | recipe `params.grid.rows.type` | rows block does not exist for native lanes; measured surfaces are forward-only in z (N1) |
| Resolved source-cap radius/curvature/auto angle | recipe/config | only the `cap: auto` setting is stored (N1) |
| `implementation_sha256` on native/freeform and plain grid-row recipes | recipe `rows` | absent; the provenance gate (v2 rule 4) therefore cannot act mechanically — demonstrated by lecleach and ROSSE |

Proposed remedy (finding, not decision): require `implementation_sha256` on every recipe, split
kernel-vs-validator (or hash the generated point grid), so a validator-only code change cannot lock
a stored lane out of its own adapter, and a geometry change cannot pass silently.

## What this table does not claim

- Nothing acoustic: no response, solve or score was compared by these tests.
- That a passing record predicts the solved surface's behaviour; the tolerances are geometric.
- That the excluded Klangfilm designs or lecleach are geometrically wrong — only that HEAD does not
  rebuild them from their stored recipes.
