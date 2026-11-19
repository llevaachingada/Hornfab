# Solver proposal — compact-horn / woofer-crossover slate, 2026-11-19

CPU-only scout (C-SCOUT-2026-11-19). **No GPU work was performed and none is authorised by this
document.** A live GPU night (`fable_priority10_2026-11-19`) owns the lane; everything below is a
*request* for the parent orchestrator to spend or refuse.

Floors used throughout: **v7 stored-grid 0.3105 J, v10 0.4677 J** (`docs/CODE_MAP.md` L282,
`docs/evidence/b1_mesh_2026-11-18/README.md`). J is never compared across identities.

---

## 0. Bottom line

| Ask | Count | Cost | Gate |
|---|---|---|---|
| New isolated-horn **screen** solves | **0 unconditional**, 1 conditional | ~23 min GPU | CPU v10 rescore of A1 must land within 0.4677 J of 1.4214 first |
| **Verify** solves | **0 unconditional**, 2 conditional | <2 min GPU | only if a promotion decision is opened |
| CPU-only rescoring / recipe repair | 4 items | 0 GPU | none — do these now |

Why zero unconditional new solves: of the ten candidates, two tie their own seeds (A1, C2) and the
K2/R1 record lanes are far below their floors with a measured construction/score mismatch; A2
regressed, A5 never really ran, and the rest are 2.3–15 J behind the v10 leader. A new screen solve
on any of them would re-measure a measured basin, not answer a question.

---

## 1. CPU-only steps that must precede any GPU ask (no GPU, do first)

These are the real next actions and none needs the GPU lane.

1. **CPU v10 rescore of the petal lane** (`scout40w3__petal_hvlaw_v7`, config_sha `2e79402be1ec`).
   Run `runs/analysis/v10_rescore`-style over `runs/20261119T155454Z-screen-d1a61d` (41 stored
   rows). Today the lane exists only on home-v7 (J 4.16163) and **has no v10 number**. This is the
   gate for §2.
2. **CPU v10 rescore of the tritonia v8/v9 lanes** (`55a3166ff16b`, `1c07945ab727`) from
   `runs/20261119T152446Z-screen-d98c8d` and `runs/20261119T153950Z-screen-5d766f`. Both W3s are home-v7 only; a
   v10 rank is needed to place the slate's only real W3 gain against the v10 leader.
3. **CPU v10 rescore of the Crowe-X square lane** (`37b03559e9db`) from
   `runs/20261119T161820Z-screen-9fda2a` (10 valid). Same reason.
4. **Re-emit the A5 recipe** (`e53a0c3ebe76`). Its archived grid rows no longer replay
   (`GeneratorError: rolled-family schema or implementation differs`). Rebuild the rows from the
   current `rolled_family` and write them to a *new versioned config*; do not edit the archived run.
   Until this is done A5 cannot be scored at all.

If step 1 returns a v10 J within 0.4677 of 1.4214, go to §2. If it does not, stop — the slate has
no GPU-worthy lane and the answer is "the compact shapes are 2+ J behind the leaders on v10".

---

## 2. Proposed screen solve (1, conditional) — A1 petal, matched v10 continuation

**Why it is not a duplicate.** It is new on all three legs of the identity triple:

| leg | existing | proposed |
|---|---|---|
| **config_sha** | `2e79402be1ec` (v7 home brief, seed from YAML) | a **new** sha (v10 brief + warm start); nothing in the queue or the archive has this sha |
| **design** | seed `c73a8ae29ccb` (J 8.683 v7); best `74d8eed97268` (J 4.16163) | warm start **from `74d8eed97268`**, not from the seed — a design hash no current seed config uses (`warm_start.from_runs` has only pointed at `…143027Z-screen-401992` before) |
| **mesh / solve** | same design+spec is a **mesh-cache hit**, not a new mesh | the solve is re-run under **v10**, a different objective identity, so the score is not a re-measure of the stored v7 score |

Contrast with the known trap: the PRIORITY10 B6 "s1" runs were *not* continuations because they were
seeded from the lane seed (`L_mm` 203.4 vs 311.6 on twinray). This proposal starts from the design
that actually scored, so the 0.4677 floor is the correct test.

**Exact config (PROPOSED — NOT CREATED).** It is the A1 file with only `name`, `brief_file`,
`search.warm_start` and `search.budget` changed. Every key already exists in
`examples/typologies/scout40w2_2026-11-19/scout40w3__petal_hvlaw_v7.yaml`.

```yaml
# PROPOSED ONLY - the parent integrator authors this file; the scout did not create it.
name: scout40w4__petal_hvlaw_v10_s1
family: OSSE
brief_file: ../../briefs/home_landscape_2026-11-18_v10/room_landscape_80x50_700_hf1440_v10.yaml
seed_params: <unchanged from scout40w3__petal_hvlaw_v7.yaml>
bounds:      <unchanged from scout40w3__petal_hvlaw_v7.yaml>
mesh:        <unchanged>
solve:       <unchanged>
search:
  algorithm: cma
  sigma0: 0.05
  seed: 1234
  budget: 40
  popsize: null
  tolfun: 0.001
  infeasible_penalty: resample_strict
  error_policy: retry_same_then_stop
  budget_counts: valid
  warm_start:
    from_runs:
      - runs/20261119T155454Z-screen-d1a61d
    top_k: 10
    sigma_from_spread: false
```

The `q` pin is a **queue** key, not a config key, so it goes in the night job exactly as the W3 job
did (`docs/queue/fable_scout40w2_2026-11-19.yaml` L60): `watchdog: {pin_ignore: [q]}`.

**Budget.** 40 valid evaluations, `budget_counts: valid`, max 160 attempts (the A1 W3 used 54
attempts for 40 valid; its refusal rate was 14/55 with 12 `invalid_geometry`). Add a 1 h per-job
watchdog, and let `no_gain_valid` close it early — measured behaviour on this lane family is ~30–45
valid before the watchdog fires.

**Baseline seed J and identity.** Seed = the v10 rescore of design `74d8eed97268`
(`NOT_YET_AVAILABLE` in this pass; step 1 produces it). Identity = **v10**. It is *not* the stored
home-v7 4.16163.

**Numerical success threshold.** `best J_v10 ≤ seed J_v10 − 0.4677` (**v10 floor**). Anything less
is a tie. A gain that only reproduces the seed on the v10 grid is a no-op, not a win.

**Cost, measured.** The same lane measured **34.2 s per valid eval** (1404.25 s / 41 valid,
`s40x3__petal_hvlaw_v7`). 40 × 34.2 s = **1368 s ≈ 22.8 min** of wall clock; budget **25 min**.

---

## 3. Proposed verify solves (2, conditional) — only if a promotion is opened

Verify is a reproduction test, not a search: same design and mesh, the verify grid
(`grid.verify_points_per_octave`, present in the source configs as 6.0) and `balloon_points_verify:
1024`, so the **solve hash differs** from the screen solve. Neither is a duplicate of a stored
screen solve.

| # | design | run | identity | measured cost | success gate |
|---|---|---|---|---|---|
| V1 | `74d8eed97268` (A1 petal best) | `runs/20261119T155454Z-screen-d1a61d` | home-v7 | 34.2 s/eval → <1 min | verify-grid J reproduces the screen J within the **v7 0.3105** floor, `di_source = balloon`, complete polar table emitted |
| V2 | `3545b3e078ac` (K1 b3_soft v10 best) | `runs/20261119T073330Z-screen-723756` | v10 | 15.1 s/eval → <1 min | verify-grid J reproduces the v10 rescore 3.7428 within the **v10 0.4677** floor, complete polar table emitted |

Both are cheap (~2 min total) but **not worth spending unless a promotion decision is actually
opened**; neither design is a leaderboard candidate today. Cost estimate uses the measured per-eval
times from `runs/nights/fable_scout40_2026-11-19/summary.jsonl` (K1 lane 15.06 s/candidate in
`run.json`) and the petal W3 lane (34.2 s/valid).

**Refused on purpose.** No screen solve for K1, K2, R1/R1b, C1, C2, A2, A3 or A4:
K1/C1 already have CPU v10 ranks 2.3/5.65 J off; K2/R1 are measured construction/score mismatches
(`dislope` 75 %/71 % of J, and the searched freedom moves the V plane); C2 ties and is box-limited;
A2 regressed; A3's gain is banked; A4 is reference-only and its campaign is not authorised.

---

## 4. Is a separate compact 900–1100 Hz brief identity justified?

**Conditionally yes, but it is a senior/owner decision, not a scout edit.** The measured evidence
for a new identity:

- No non-reference row reaches the 40–60° V corridor below ≈1.1 kHz (A1 88.8° @850 → 69.4° @1100;
  A2 69.0 → 56.3; K1 104.9 → 82.5; K2 163.9 → 123.9; R1b 128.4 → 112.1), and A5 never does
  (134.2° @1100). The v10 corridor only *starts* its V target at 1 kHz (40–60°) and its F_X is
  700 Hz, so a horn judged "good" by v10 can still be unusable as the top of a 900–1100 Hz two-way.
- The only compact row whose V knee is inside the corridor *at* the crossover is the **A4
  derivative** (V 64.6° @950, 56.5° @1100), and that is not one of the ten candidates.
- No existing brief scores a *crossover-band* V requirement or scores the horn knowing the woofer's
  crossover. Adding one is a **new acoustic priority** → `hornlab-typology-research` applies, and it
  creates a new identity that must never be ranked against v7/v10.

**Proposed name only (not authored):** `home_landscape_compact_xo900_1250_hf1440_v11` (a v11
objective, or a v10 sub-identity if the senior prefers to keep one floor).

**Registration steps (only if approved):**
1. Senior/owner decision that a new identity is opened (the alternative, used in this register, is a
   post-hoc screen of stored v10 metrics — §5).
2. Author the brief under a new dated `examples/briefs/…` folder: same driver block (HF1440, 18 mm,
   2.0°), same 600 × 480 × 480 envelope, band 350–8000 Hz, F_X 900–1100 Hz, V requirement moved into
   the crossover band.
3. **Publish the identity floor** with the `b1_mesh` top-28-pair protocol *before* any ranking; a new
   identity without a floor cannot be read.
4. Register it in `docs/CODE_MAP.md`, `docs/INDEX.md` and the identity table in the same commit.
5. Never rank the new J against v7/v10 stored J; carry the identity in every table.
6. Run `tools/search_preflight.py` sigma sweep before queueing any search on it.

---

## 5. Pareto shortlist (3–5, distinct shape mechanisms)

Fidelity is the screen solve's own level: **SCREEN_MAGNITUDE** = single-mesh screen solve, balloon
DI; **NOT_YET_AVAILABLE** = no valid measurement. Nothing here is INSTALLED_EXTERIOR_BEM — no BL
case id exists for any candidate.

| # | ID | Mechanism (why it is a *different shape*, not a different bound) | J (identity) | V @1100/1250 | λ spacing 10″ | Fidelity |
|---|---|---|---|---|---|---|
| 1 | **A1** petal_hvlaw_v7 | A localised **crease** (petal) added on top of a per-direction `a(phi)` OSSE law; the crease, not the mouth size, is the shape degree of freedom | 4.16163 (home-v7) | 69.4 / 61.7° | 0.78 / 1.04 | SCREEN_MAGNITUDE |
| 2 | **A3** tritonia v8 | A pure **per-direction `a(phi)` law** with an az fold and no crease — the ATH mechanism itself, not a crease on top of it | 4.89113 (home-v7, real +0.48 W3 gain) | 65.0 / 57.8° | 0.78 / 1.04 | SCREEN_MAGNITUDE |
| 3 | **K1** klangfilm b3_soft | A **frozen non-OSSE kernel** (Klangfilm Lamé: one area law, held aspect, returned lip + beak); a completely different construction lineage | 3.74283 (v10 rescore; 2.80022 smooth-v7) | 82.5 / 70.9° | 0.65 / 0.86 | SCREEN_MAGNITUDE |
| 4 | **R1b** rolled_rect hybrid | A **rolled-rectangle section on a log spiral**, 13-knob whole-family reshape with radial/axial relief — the only mechanism in the slate that measurably moved `dislope` (−3.79 J) | 9.30539 (v10) | 112.1 / 101.3° | 0.74 / 0.98 | SCREEN_MAGNITUDE |
| 5 | **A5** rf__rect_radial_wide_v7 | **In-plane radial relief**: pull the H/V wall centres inward and leave the diagonal, so the diagonal becomes a ridge (ATH-like) — explicitly *not* an axial corrugation and *not* a wall-angle law. Deliberately **exploratory** | 32.7379 (home-v7, 2 valid, aborted) | 134.2 / 124.9° | 0.68 / 0.90 | NOT_YET_AVAILABLE |

Read-out: the ordered pair (J, V-knee) has no dominant member. A1 and A3 buy pattern at ~4.2–4.9 J;
K1 is the best v10 J among the ten candidate rows but pays a V knee above 1.25 kHz; R1b is the only
proven DI-slope-mover and is 7.9 J off; A5 is the only *untested* mechanism and must not be ranked.

Not shortlisted: A2 (ties A3's mechanism, better load but regressed W3), A4 (reference only, no
candidate J), C1 (5.65 J off the v10 leader), C2 (ties and is box-limited; **no v10 rescore exists
yet**, so its home-v7 7.598 is not a comparable delta), K2/R1 (measured DI-slope-blind).

---

## 6. Proposed test diff (text only — no test file authored)

The scout owns no test file. Proposed addition to a future register/evidence test:

```diff
--- /dev/null
+++ b/tests/test_research_compact_horn_register.py
+import json
+from pathlib import Path
+
+from hornlab_search.config import load_config
+from hornlab_search.search.rundir import config_sha
+
+REG = Path("docs/research/compact_horn_system_2026-11-19/candidate_register.json")
+REQUIRED = {
+    "source_config_path", "repo_head", "config_sha", "family", "route", "source",
+    "geometry", "best_saved", "runs_recent", "further_gpu_needed",
+    "morphology_tags", "crossover", "driver_fit",
+}
+
+
+def test_register_has_exactly_ten_rows():
+    data = json.loads(REG.read_text(encoding="utf-8"))
+    assert set(data["candidates"]) == {
+        "A1", "A2", "A3", "A4", "A5", "C1", "C2", "K1", "K2", "R1"}
+    for row in data["candidates"].values():
+        assert REQUIRED <= set(row)
+        assert len(row["morphology_tags"]) == 4
+
+
+def test_config_sha_matches_the_real_loader():
+    data = json.loads(REG.read_text(encoding="utf-8"))
+    for cid, row in data["candidates"].items():
+        cfg = load_config(row["source_config_path"])
+        assert config_sha(cfg.raw) == row["config_sha"], cid
+
+
+def test_geometry_is_never_taken_from_a_seed_when_a_best_exists():
+    data = json.loads(REG.read_text(encoding="utf-8"))
+    for cid, row in data["candidates"].items():
+        best = row["best_saved"]
+        if best.get("design_hash"):
+            assert row["geometry"]["provenance"].startswith("[measured]"), cid
```

`test_geometry_is_never_taken_from_a_seed_when_a_best_exists` is the guard that matters: A1, C1 and
C2 would all fail it if someone pasted the `shape_check` seed row into the register.
