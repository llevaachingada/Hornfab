# N1b — Test 2 and Test 3 under contract v2

Run: 2026-11-17, HEAD `caa37d0` (working tree also holds other lanes' uncommitted scratch edits). Read-only,
CPU only; no mesh build, no solve, no pytest, no git mutation. Scripts: `scratch/fable_architecture/.n1b/`
(`build.py`, `inner.py`, `envelope.py`, `lecleach_box.py`). Inputs: `.fable/rows.pkl` (3,802 rows, 75 runs);
the `.x1` samplers for five lanes; stored `runs/<run>/designs/<hash>/{design.json,mesh.msh,response.npz}`;
`.tmp/fable_replay_harness.py` for the §0 gate. Records: `.n1b/build/` (70 design records), `.n1b/*.json`,
`.n1b/*.log`.

§0 gate: `parity smoke: worst regenerated-vs-stored DI across study screen designs: 0.0 n 17`. Zero, so
the task proceeded. Contract v2 = `CANONICAL_SURFACE_CONTRACT.md` §12; sampling 65 stations × 61 azimuths
(1.5° step).

## Headline

1. **All six contract lanes pass v2 rule 2 at 65 × 61; the hand-back condition is not met.** Worst record
   p99: ext-throat 0.108 mm, ATH morph 0.247, Crowe 1.353 (native floor 1.160), rolled 0.856 (floor 0.555),
   Klangfilm 1.155 (floor 1.116), biradial 0.101. Every lane is 10/10 and every median is ≤ 0.14 mm. The
   61-azimuth record removes N1's failures (rolled 1.696 → 0.856; Crowe 1.870 → 1.353, now inside
   1.25 × its own mesher floor).
2. **The provenance gate removes the whole N1 Klangfilm sample.** HEAD's legacy-bridge digest is
   `ea5026…`; 72 distinct stored Klangfilm designs (all four runs before 11-16 20:30, including N1's ten)
   carry `e3a1f4a3…`, which no code in git history produces. Ten digest-verified replacements (one run,
   same brief and brief_hash) pass 10/10. Rolled stores `1879ad5a…`, which HEAD reproduces; Crowe and the
   three native lanes store no digest, so rule 4 is not applicable to them.
3. **Envelope: every depth difference is the rear closure, exactly.** Stored box = mesh used-node box in
   70/70 records. Biradial's +1.9…+3.5 mm is the generator's outward `outer_points` shell (1.0–1.5 mm/side
   W, 1.3–2.1 mm/side H), which is not in the meshed box — that box equals the inner-sheet box in 10/10.
   **0 of 309 stored biradial designs sit within 3.5 mm of the 600 W / 480 H limits** (max W 584.0, max H
   459.7), so the mismatch cannot change any size verdict on stored data.
4. **A seventh lane, lecleach (needed by N4), is not reproducible at HEAD and is excluded.** Its stored
   meshes differ from HEAD's generator by 0–69 mm in W/H and 9–231 mm in depth; the recipe stores no
   digest. Cause found below.

## Result table — Test 2 (inner-wall agreement, v2 rule 2)

Same node set per design: the topology-separated inner sheet (N1's sharp-crease rule, unchanged), measured
once against the generator's native points (floor) and once against the 65 × 61 record. Lane floor and
lane record p99 are both worst-of-ten, as the rule compares them.

| Lane | n | native floor p99 (mm) | record p99 (mm) | threshold max(1.0, 1.25×floor) | median-of-medians | worst max | verdict |
|---|---:|---:|---:|---:|---:|---:|---|
| `hl__ext_throat_hvlaw_v7` | 10 | 0.068 | 0.108 | 1.000 | 0.013 | 0.158 | **pass** 10/10 |
| `hl__ath_tritonia_landscape_v9` | 10 | 0.048 | 0.247 | 1.000 | 0.011 | 0.992 | **pass** 10/10 |
| `hl__crowe_x_osse_cd_v7` | 10 | 1.160 | 1.353 | 1.451 | 0.045 | 1.957 | **pass** 10/10 |
| `rf__section_axial_home_v7` | 10 | 0.555 | 0.856 | 1.000 | 0.043 | 1.498 | **pass** 10/10 |
| `hl__klangfilm_lame_curved_v1` | 10 | 1.116 | 1.155 | 1.395 | 0.097 | 1.371 | **pass** 10/10 |
| `hl__biradial_es_style_v7` | 10 | 0.047 | 0.101 | 1.000 | 0.005 | 0.331 | **pass** 10/10 |
| `hl__lecleach_hv_landscape_smooth_v7` | 10 | — | — | — | — | — | **not reproducible at HEAD** (9/10 no inner sheet within 0.5 mm; excluded) |

All medians are below 0.3 mm; per-design pass (each design against its own floor) is also 10/10 per lane.

**Which criterion binds.** Four lanes exceed 1.25 × their own floor while staying under 1.0 mm: ext-throat
0.108 vs 0.085, ATH 0.247 vs 0.060, rolled 0.856 vs 0.694, biradial 0.101 vs 0.058. The rule's `max(1.0,
…)` is what keeps them passing; at sub-0.1 mm floors the relative test alone would fail them, and the
1.0 mm absolute line is the meaningful one there. Crowe (1.353 vs 1.451) and Klangfilm (1.155 vs 1.395)
pass on the relative test.

**Change from N1 (31 azimuths → 61 azimuths, same lanes, same selection except Klangfilm):**

| Lane | N1 worst p99 (31 az) | N1 pass | N1b worst p99 (61 az) | N1b pass |
|---|---:|---:|---:|---:|
| ext-throat | 0.158 | 10/10 | 0.108 | 10/10 |
| ATH morph | 0.850 | 10/10 | 0.247 | 10/10 |
| Crowe | 1.870 | 0/10 | 1.353 | 10/10 |
| rolled | 1.696 | 0/10 | 0.856 | 10/10 |
| Klangfilm | 1.457 | 9/10 (unverified run) | 1.155 | 10/10 (verified run) |
| biradial | 0.142 | 10/10 | 0.101 | 10/10 |

The ATH improvement (0.850 → 0.247) is larger than azimuth chords alone would suggest; it is consistent
with N1's single design whose 31-azimuth p99 sat at 0.85 while its native floor was 0.048 — i.e. that
design's tail was record interpolation, not a surface difference.

## Provenance gate (v2 rule 4)

| Lane | stored identifier | HEAD value | designs affected | decision |
|---|---|---|---|---|
| rolled | `rows.implementation_sha256 = 1879ad5a…c95f7c` (51/51 recipes) | `rolled_family.implementation_digest()` = `1879ad5a…` | 0 | gate passes |
| Klangfilm | 344 rows `ea5026…`, 121 rows no digest, 73 rows (72 distinct designs) `e3a1f4a3…` | `klangfilm_lame_cli.implementation_digest()` = `ea5026…` | 72 excluded | ten digest-verified replacements used |
| Crowe | `rows.type: osse_rollback` only | no digest exists | — | rule 4 not applicable |
| ext / ATH / biradial | native recipe (no grid rows, no digest) | — | — | rule 4 not applicable |

The 72 excluded designs sit in four runs on 2026-11-16 between 20:59 and 21:18 (the 21:18 run carries
designs under both digests), including N1's ten (run `20261116T205942Z-screen-8b22b5`).
`tools/geometry/klangfilm_lame.py` first appears in commit `2c0e292`,
whose digest is already `ea5026…`; `e3a1f4a3…` therefore came from an intermediate, uncommitted
implementation and cannot be reproduced from history. N1's measured 1.457 mm for `b9ea3ad77e3f` is
superseded rather than contradicted: that design is not admitted here.

Replacement rule, fixed before measuring: from digest-verified Klangfilm rows with a stored mesh, sort by
`(run, design_hash)` and take the first ten distinct hashes. Result: ten designs from
`20261116T211824Z-screen-45c843`; its brief hash and envelope (600 × 480, quadrants `1`) equal the N1
run's. The other five lanes reuse the exact N1 selection.

## Result table — Test 3 (envelope, v2 rule 5)

Deltas are sampled (union of the 65 × 61 inner and outer records) minus the stored row `bbox_m`, in mm,
with the quarter model doubled in W and H. "D after closure" subtracts the measured tag-1 z-min shift.

| Lane | W delta | H delta | closure shift (tag-1 z min) | D after closure | cause | verdict |
|---|---|---|---:|---:|---|---|
| ext-throat | +0.65…+1.05 (1/10 >1) | +0.70…+1.41 (4/10 >1) | −4.75…−4.49 (at −5.0) | 0.00 | generator outer sheet +0.33…+1.11/side W and +0.37…+0.71/side H beyond the inner; meshed rim overshoot ≤1.37 on W | **partial** — pass on W, 4/10 above 1 mm on H, cause stated (rim), no closure contribution |
| ATH morph | +0.48…+0.83 | +0.25…+0.59 | −5.45…−4.95 (at −6.0) | 0.00 | closure; union stays inside 1 mm | **pass with stated cause** |
| Crowe | −1.01…−0.35 (1/10 >1) | −1.64…−0.26 (5/10 >1) | −2.45…−2.39 | −0.36…−0.03 | mesh extends beyond **both** generator sheets at the rectangular corner (mesh departs from design by up to 1.64 mm) | **fail at 1 mm — mesher fit, not sampler** (v2 rule 3 class) |
| rolled | −0.68…−0.41 | −0.38…0.00 | −3.00 | −0.05…+0.07 | mesh is 0.4–0.7 mm wider than the generator (same class, smaller) | **pass** |
| Klangfilm | −0.12…−0.02 | −0.12…−0.02 | −2.59…0.00 (rollback already below z = 0 on most) | −0.11…0.00 | closure where the sample starts at z = 0; none where rollback crosses it | **pass** |
| biradial | +1.94…+3.06 (10/10 >1) | +2.68…+3.45 (10/10 >1) | −2.92…−2.91 | 0.00 | generator `outer_points` shell, see below | **fail at 1 mm — shell-convention gap, cause established** |

### Biradial: what the stored box includes that the sampler does not

| Quantity | Finding |
|---|---|
| Stored box = mesh used-node box | 10/10, all three axes (atol 0.02 mm) |
| Stored box = generator's outward `outer` sheet | 0/10 |
| Stored W/H = generator's native **inner** box | 5/10 exactly; the other 5/10 the mesh rim exceeds the designed inner by +0.23…+1.42 mm |
| Stored depth = inner depth + wall thickness | 10/10 (+3.00 mm = closure at z = −t) |
| Generator outer minus inner, per side | W +0.97…+1.53 mm, H +1.34…+2.05 mm |

So the stored box is the **meshed acoustic inner surface plus the rear closure**. What it includes that the
sampler does not is the closure (depth, 3.0 mm) and, on half the designs, the mesher's own rim overshoot
(≤1.42 mm). What the sampler includes that the meshed box does not is the generator's `outer_points`
array, which adds 1.0–2.1 mm per side **outside** the inner sheet; the meshed box never reaches it (it
equals the inner-sheet box in 10/10). The +1.9…+3.5 mm is that shell plus the mesh rim excess.

### Biradial designs near the size limits

Over all 309 valid stored biradial rows (limit 600 W, 480 H, 480 D):

| Band | W | H | D |
|---|---:|---:|---:|
| within 3.5 mm below the limit | 0 | 0 | 0 |
| up to 3.5 mm above the limit | 0 | 0 | 0 |
| maximum stored | 584.00 (16.0 mm margin) | 459.74 (20.3 mm margin) | 308.56 |
| 99th percentile | 584.0 | 434.6 | — |

**No stored biradial design can have its envelope verdict changed** by the +1.9…+3.5 mm mismatch. The
risk the addendum names exists in principle but has no instance in this lane's stored data.

## The lecleach lane (added for N4, excluded here)

N4's five-lane list includes `hl__lecleach_hv_landscape_smooth_v7`, which N1 never tested. Ten of its
valid designs (first ten by `(run, hash)`) were built at HEAD through `grid.grid_points` (native 15 × 33):

| Evidence | Value |
|---|---|
| Stored mesh box vs HEAD generator box | 0–69 mm difference in W/H, 9–231 mm in depth, 10/10 designs |
| Example (`3d4731536ab0`) | generator 491.8 × 162.3 × 169.3 mm; mesh 491.8 × 231.0 × 400.4 mm |
| Inputs unchanged | `brief_hash(cfg.brief)` = `89e7b98566b5` = the stored design's `generator.brief_hash` |
| Implementation change | grid.py's lecleach H/V realization landed in `d6c9abd`, 2026-11-16 10:25; both stored runs are 04:01 / 04:06 |
| Stored digest | none (`rows.type: lecleach`) — rule 4 cannot flag it mechanically |

The isolation rule refuses on 9/10 designs (no component within 0.5 mm holding ≥10 % of the largest
component's area; the "closest" component is a dozen stray nodes). **Verdict: the lane's stored meshes are
not rebuildable from their recipes at HEAD.** This is not a sampler result; it is a provenance gap of the
same kind as Klangfilm's, but with no digest to detect it. N4 substitutes the rolled lane (see next
action).

## Verdict against the brief's lines

- **N1b hand-back:** "a lane's record p99 exceeds 1.25 × its native floor (and 1.0 mm)". **Not met.** No
  lane exceeds both; four exceed the relative part only, all below 1.0 mm.
- **N1b deliverable:** table with native floor, record p99, pass/fail per lane — above, plus the digest
  exclusions listed and the Klangfilm replacement rule.
- **Test 3 (v2 rule 5):** rear-closure and rim causes stated per lane. Pass with cause: ATH, rolled,
  Klangfilm. Partial: ext-throat (H). Fail with established cause: Crowe (mesher fit, up to 1.64 mm) and
  biradial (shell convention; inner-sheet envelope agrees to 0.02 mm W and ≤1.42 mm H).
- **Provenance (rule 4):** 72 Klangfilm designs excluded, ten verified replacements tested; rolled passes;
  Crowe and native lanes have nothing to verify. One extra lane (lecleach) found unreproducible.

## What failed / what is unknown

- **Le cleach is not rebuildable at HEAD.** Cause is the 11-16 H/V realization change; whether any stored
  lecleach run predates it cannot be tested — both runs in `rows.pkl` are earlier that morning, so the
  whole stored lane is affected.
- **Klangfilm's `e3a1f4a3…` implementation is not in git history.** Whether those 72 designs' meshes match
  any transcription of that intermediate code is unknown and cannot be settled from this checkout.
- **Which surface the mesher intends to build.** For biradial and ATH the meshed box equals the inner
  sheet while the generator also offers an outward `outer_points`; for rolled the outer sheet is 21 mm
  inside the inner at the mouth in W. The contract must state whether the envelope is the inner-sheet box
  (mesh-built) or the outer shell (generator), before T3 can reject a route. Not resolved here.
- **Crowe's 1.64 mm is not separated** into mesher corner fit and element size. N1's T2 floor (1.07 mm at
  native points) and this envelope excess (1.64 mm) are the same order but not the same measurement.
- **Native floor vs floor of a finer generator surface.** The floor uses the generator's own native points
  as v2 says; for lecleach and Klangfilm that sampling is coarse (azimuth chords), so the floor is a
  sampling floor as well as a fit floor. Not separated.

## What this does not prove

- Nothing about acoustic equality: no response, solve or score was compared.
- That a passing record predicts the solved surface's behaviour; the contract's tolerances are geometric.
- That lecleach or the excluded Klangfilm designs are geometrically wrong — only that HEAD does not
  rebuild them from their stored recipes.
- That the 61-azimuth step is minimal for each lane; only that it is sufficient for all six.

## Next action enabled

**N4 (U1) may proceed on five lanes:** `hl__ext_throat_hvlaw_v7`, `hl__biradial_es_style_v7`,
`hl__crowe_x_osse_cd_v7`, `rf__section_axial_home_v7`, `hl__klangfilm_lame_curved_v1`. **Rolled replaces
lecleach** (lecleach not reproducible at HEAD; rolled is the same kind of fixed-recipe section family and
passes N1b). Per the runbook addendum, Crowe and rolled are recorded as "mesh departs from design at
corners", so their layered rebuild is compared with the **generator's surface**, with the mesh difference
reported separately (Crowe ≤1.64 mm, rolled ≤0.70 mm at the envelope faces).

Two contract questions for the owner, not blocking N4: (1) define the envelope as the mesh-built inner
sheet or as the generator outer shell; (2) require `implementation_sha256` on every grid-row recipe so
rule 4 can act on lecleach-style changes.

## Reproduce

```powershell
# from C:\Users\hunte\Hrns\hornlab-search
git rev-parse --short HEAD                                   # caa37d0
.venv/Scripts/python.exe scratch/fable_architecture/.tmp/fable_replay_harness.py
.venv/Scripts/python.exe scratch/fable_architecture/.n1b/build.py scratch/fable_architecture/.n1b/build
.venv/Scripts/python.exe scratch/fable_architecture/.n1b/inner.py
.venv/Scripts/python.exe scratch/fable_architecture/.n1b/envelope.py
.venv/Scripts/python.exe scratch/fable_architecture/.n1b/lecleach_box.py
```

`build.py` skips records already on disk, so a re-run is a no-op. No file outside
`scratch/fable_architecture/` was written; `runs/`, `examples/`, `hornlab_search/` and `tools/` were read
only.
