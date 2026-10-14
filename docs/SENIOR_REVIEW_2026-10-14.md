# Senior review, 2026-10-14: PR #12 (`claude/wave-3-implementation-review-2dk4qe`)

Reviewer: senior reviewer (cloud, read-only on code). Base `main` = `2a7bafb`, unchanged.
Head reviewed: `caa5438` (CP-8c run 2/4). **CP-8c runs 3-4 were still running when this was
written; section D's data numbers stop at run 2.** No GPU runs, no code edits, no thresholds touched.

## Verdict: CONTINUE WITH FIXES

CP-8c can finish as it is. **Before `surrogate train` / `propose` for CP-8d**, land fixes F1-F5
below. None of them changes a gate threshold. The physics and dataset side is sound.

## Checklist

| # | Item | Status | One line |
|---|---|---|---|
| A | Alignment with plan | DEVIATION-OK (2 harmful, listed) | `git diff main -- docs/plan` empty; `01_CONTRACTS.md` unchanged; gate thresholds match `11_PHASE2` section 4 exactly |
| B | Silent killers | PASS, one gap | `mesh_scale=1.0` everywhere; quadrants from `sizing.py` only; DI provenance gap on the surrogate path |
| C | Issue #13 | ISSUE | 1, 2, 3 confirmed HIGH; 4, 5, 9 MED; 6 downgraded to LOW (wrong as stated); 7, 8, 10 LOW |
| D | Data integrity | PASS with 2 doc errors | counts add up exactly; 0 torn; ticks-log hash stale; ICW warning evidence is thin |
| E | Grid / label space | ISSUE (MED) | family + freq grid filter works; skipped counts not printed; epw / cap / quadrants not in the label key |
| F | Bounds | ISSUE (doc) | `n` and `hold_end` pinned (confirmed); `q` is crowded near lo but top-6 is 0/6 within 2 %, weaker than docs say |
| G | Tests / CI | PASS (CI); local run blocked | CI `test` green on `caa5438`; I could not run pytest here (sandbox permission denied) |
| H | Docs hygiene | PASS, one flag | all 11 branch commits touch CONTINUITY + ISSUES; ISSUES mirrors GitHub; NN-idea credit sits in frozen plan files |
| I | Open user decisions | listed | see the end |

## A. Alignment (deviations from `docs/plan`)

`git diff origin/main..HEAD -- docs/plan` is empty: frozen files untouched.

| Deviation | Where | Verdict |
|---|---|---|
| `config.QUADRANT_FACTOR` now aliases `sizing.QUADRANT_FACTOR` | `config.py:23` | justified-positive |
| `a_deg` lo 25 to 5, `exponent` lo 2 to 1 (OSSE configs) | `examples/*.yaml` | justified-positive (CP-8b, probed against the mesher, recorded) |
| CI installs CPU torch | `.github/workflows/ci.yml` | justified-positive |
| Ownership row for `surrogate/**` | `CLAUDE.md` | neutral (orchestrator file, orchestrator edit) |
| Gate thresholds and the 500 floor | `surrogate/gates.py:14-21` | aligned with `11_PHASE2` lines 108-117 |
| `Surrogate.metric_set` stamps every prediction `di_source="balloon"` | `surrogate/predict.py:46` | **harmful**: launders DI provenance (see B) |
| HANDOFF tells CP-8d to "pool `osse_baseline` and `search_smoke`" | `docs/HANDOFF_LOCAL.md:95` | **harmful (minor)**: the two are on different grids (5.5 vs 4.5 kHz), so `search_smoke` is silently dropped |
| Monotonic gate allows one turn per sweep, applied to J | `gates.py:61-86` | neutral, but see question Q3 |

## B. Silent killers

1. **mesh_scale**: PASS. `solve/beat.py:360`, `solve/bempp.py:170` hard-set `1.0`; `mesh/build.py:223`
   guard is [0.02, 5.0] m (task 04 spec). A mm mesh (1000x) cannot pass it.
2. **Quadrants vs symmetry flag**: PASS. `config.py:23` is `sizing.QUADRANT_FACTOR`; `build.py:300-319`
   takes the flag from `sizing.SYMMETRY_PLANE` and asserts the mesher agrees. Evidence: all 787 ICW
   rows are quadrants `"1"` with `yz+xz`.
3. **DI provenance**: PASS on the BEM path (`objective/scalar.py:128` sets `di_estimated`; report marks
   estimates). **Gap on the surrogate path**: `to_training_arrays` returns `di_source` but `train.py`
   never reads it, and `predict.py:46` labels every prediction `"balloon"`. Today's data is safe (OSSE
   pool: 1406 balloon, 95 failed with empty source; ICW: 787 balloon), so this is latent. Fix F5.

## C. Issue #13, verified against the code and ranked

| Rank | #13 item | My finding | Severity |
|---|---|---|---|
| 1 | 1 verdict not persisted | Confirmed. `train.py:64-65` saves before gates run; `cli.py:678` loads any bundle. CP-8d WILL fail the gates (225 held out), so the file on disk will be a failed model that `propose` accepts. | HIGH |
| 2 | 3 bundle does not freeze bounds | Confirmed. `train.py:59-62` meta has keys and freqs, no bounds; `ismo.py:25,34` and `predict.py:65` re-normalize with the current YAML. A bounds widening (F section) after training silently re-maps every input. | HIGH |
| 3 | 2 stored vs current weights | Confirmed in code (`train.py:73`). Not active for CP-8d (whole kept pool came from `osse_baseline.yaml`, same weights and target), active the moment weights, target or band change. | HIGH (latent) |
| 4 | 9 degenerate propose exits 0 | Confirmed: an empty list prints "propose OK". `round_report` takes finite 1e3 penalties into medians if the caller passes `Evaluation.objective`. | MED |
| 5 | 4 grid drops not printed | Confirmed. `meta['skipped_grid_mismatch']` exists (133 for OSSE) but `_cmd_surrogate` never prints it. | MED |
| 6 | 5 no di_source guard | Confirmed, plus the `predict.py:46` hard-code. | MED |
| 7 | 7 non-atomic writes | Confirmed (`model.py:33`, `cli.py:681`, `nsga.py:141`). | LOW-MED |
| 8 | 6 dup seed straddles holdout | **Not as stated.** Identical design rows give identical `U` rows, and `cluster_holdout` assigns by `argmin` to the same centres (`features.py:32`), so exact copies always land on the SAME side. Only effect: the seed counts twice. OSSE pool has 1 duplicate (the seed). | LOW |
| 9 | 8 NaN in NSGA | No real path: `objective()` never returns NaN (contract), penalties are 1e3. Defensive only. | LOW |
| 10 | 10 grab bag | Confirmed; the one that matters: `n_heldout` counts failed rows, while the plan says "500 BEM-solved designs". Counting ok rows only would be STRICTER, not looser. | LOW |

## D. Data integrity (evidence folder, head `caa5438`)

- Row arithmetic checks out exactly. OSSE 1634 = 134 (pre-CP-8b) + 1500 (run 1); ICW 800; total 2434.
  ok 2311 = 119 + 1405 + 787; failed 123 = 15 + 95 + 13. One lib SHA (`b922e807a5+38544d214b`), one
  backend. Torn lines 0 in all 5 runs; ok rows with null metrics 0; X NaN 0.
- OSSE training pool: kept 1501 (1500 run 1 + the 05:37 seed record), skipped 133 on grid. Held out
  at 15 % = 225 < 500, so "indicative only" is correct and expected.
- Manifest: `cp8c_watchdog.txt` matches after converting git's LF back to CRLF (Windows checkout).
  **`cp8c_ticks.txt` does not match** (manifest 33,286 B; committed file 33,008 B LF / 33,496 B CRLF):
  the hash was taken from a different copy of the log. Raw `runs/` and `dataset/` cannot be checked
  from here (gitignored, local only).
- Run 1 records `hornlab_search` SHA `ab24579`, i.e. it ran with the widened bounds committed. Good.
- **ICW "outer wall self-intersects" warning: evidence is thin.** The only evidence that the inner
  surface is unaffected is the mesher's own message. Two problems: (1) for an exterior BEM solve the
  outer shell is part of the radiating closed surface, so a flipped outer normal can change the
  result even if the inner surface is fine; (2) the warning is not linked to a `design_hash`, so the
  affected rows cannot be found or excluded. The three lines in the tick log share one timestamp
  (17:06:25 local, about 20 min into the run), so it may be a few early, wide-sigma CMA designs, but
  that is inferred. Recommendation: before any ICW training, re-mesh the 800 ICW designs on CPU only
  (mesher, no solve), record which hashes emit the warning, and decide with the user whether to
  exclude them. Do not trust ICW exterior physics until then (CP-7 was OSSE-only).
- Doc error: CONTINUITY / ICW evidence say `kappa0` 0.0 "is already the schema floor". It is not:
  `families.py:125` declares `kappa0` with no lower limit; 0.0 is only the YAML bound.

## E. Grid / label-space hygiene

- `to_training_arrays` filters by family, then keeps only the majority frequency grid and counts
  the rest (`store.py:521-541`). OSSE and ICW grids differ (5.5 vs 7 kHz) but never mix because the
  CLI always passes `family=cfg.family`. OK.
- Gaps: (1) the counts are not printed (F4); (2) the label key is the frequency grid only. Two runs
  on the same grid but different `epw`, dof cap, `quadrants` or balloon points would be pooled
  silently. Not active today (all kept OSSE rows are one config). Propose (not a code change by me,
  `dataset/**` is task 07's): treat any change to band_hi, caps, epw, quadrants or balloon points as
  a new dataset family/tag, and print `n_considered / n_selected / skipped_*` in `surrogate train`.

## F. Bounds

| Family | Key | Final digest (top-6 at lo) | Mesher / repo limit | Recommendation |
|---|---|---|---|---|
| OSSE | `n` | top-6 6/6 at lo 2.0; ok median 2.036; 63 % of ok rows within 2 % of lo; Spearman +0.62 | `n > 0` while `s != 0` (`families.py:306`) | Widen down, but probe first like CP-8b (repo check is not the mesher's real limit) |
| OSSE | `q` | top-6 **0/6** within 2 % of lo; ok median 0.903; 23 % within 2 % of lo; Spearman +0.49 | `q > 0` while `s != 0` | Weaker case than `n`. Widen only together with `n`, after a probe; docs' "5/6 near lo" uses a looser test than the digest's 2 % column |
| ICW | `hold_end` | top-6 6/6 at lo 0.55; ok median 0.5507; 75 % within 2 % of lo; Spearman +0.64 | `hold_start < hold_end` (`families.py:323`); `hold_start` hi is 0.45 | Widen down; keeping `hold_end` lo > `hold_start` hi (0.45) means the rule can never fire, anything lower needs the joint check |
| ICW | `kappa0` | 4/6 near 0.0 | no schema floor | Question Q4 (negative curvature is a physics choice, not mine) |

All widening: separate recorded commit, after CP-8c closes, never mid-run, and it starts a new
dataset tag for training purposes (old rows stay valid labels; only the unit-cube encoding changes,
which is why F2 must land first).

## G. Tests / CI

- CI: both `test` check runs on `caa5438` are `success` (2026-10-13 23:47-23:49 UTC).
- Local: the sandbox refused to run pytest in this session, so I have no pasted local count. The
  local agent's CP-8a paste (480 passed, 18 deselected, exit 0) stands as the last real-box run.

## H. Docs hygiene

- All 11 commits on the branch touch both `docs/CONTINUITY.md` and `docs/ISSUES.md`.
- `docs/ISSUES.md` table matches GitHub (#1-#11 closed, #13 open; #12 is the PR).
- **NN-surrogate credit**: every place that credits the idea is in FROZEN files:
  `docs/plan/README.md:69` ("Collin's proposal"), `docs/plan/11_PHASE2_SURROGATE.md:11,61,67,159`,
  `docs/plan/12_RESEARCH_BASIS.md:240-275,383`. The quote in `11` section 1 itself says "as he
  described", i.e. it refers to someone else. Non-frozen docs do not repeat the credit. I did not
  edit anything; who to credit is question Q1.
- Claims to correct in the next CONTINUITY entry: `q` "5/6 near lo" (digest top-6 column says 0/6
  within 2 %; state which test); `kappa0` "schema floor"; HANDOFF line 95 pooling advice.

## Fix list (F1-F7 IMPLEMENTED 2026-10-14 on `ccr-455d2184-yj5zk4`; F5 implemented as refuse; F8 open; do not change any threshold in `gates.py`)

**F1. Persist and enforce the gate verdict (HIGH).** Owner: phase 2.
- `surrogate/train.py:63-66`: compute `rep = evaluate_heldout(...)` FIRST, then
  `meta.update(gates=rep["gates"], passed=bool(rep["pass"]), warnings=rep["warnings"])`, then save.
- `surrogate/model.py:31-34`: write to `path.with_suffix(".tmp")` then `os.replace`. In
  `train_surrogate`, if `out_path` exists and its meta has `passed=True` and the new one is not,
  do not overwrite: write `<out>.failed.pt` and say so.
- `cli.py:678`: after `Surrogate.load(out)`, if `not sur.meta.get("passed")`: print
  `surrogate propose FAILED: bundle did not pass its gates` and return 1.
- Tests (`tests/test_surrogate_stage_a.py`): (a) scrambled-labels bundle, then `propose` exits 1;
  (b) passing bundle on disk, failing retrain to the same `--out`, the passing file's bytes unchanged.

**F2. Freeze bounds/keys/family/freqs in the bundle (HIGH).**
- `train.py:59-62`: add `"bounds": {k: [space.bounds[k].lo, space.bounds[k].hi, space.bounds[k].log] for k in space.keys()}`.
- New check in `predict.py` (`Surrogate.check_space(space, freqs)`), called in `cli.py` before
  `ismo.propose`: raise if family, `space.keys()` order, any bound, or the config's frequency grid
  differs from meta.
- Test: train on space A, edit one bound, `propose` exits 1 naming the key.

**F3. Recompute true objectives under the current weights/target (HIGH, latent).**
- `train.py:73`: replace the stored scalar with, for each held-out ok row,
  `objective(MetricSet(freqs, y_metrics rows..., di_source=arrays["di_source"][i], z_throat_real=y_metrics["z_throat_real"][i]), True, target, weights)[0]`; NaN for failed rows.
- Test: synthetic arrays whose stored `objective` uses weights W1; evaluate with W2; the gate's
  `obj_true` equals the W2 recomputation, not the stored column.

**F4. Print pool counts (MED).** `cli.py:667`: print `n_considered`, `n_selected`,
`skipped_grid_mismatch`, `skipped_bad_arrays`; WARNING when skipped > 5 % of considered.
Test: capsys sees the counts with a mixed-grid store.

**F5. DI provenance on the surrogate path (MED).** `train.py` (start): refuse (raise) if any ok row
has `di_source != "balloon"`, or drop them and print the count, user's choice (Q2). Then
`predict.py:46` may keep `"balloon"` because training guaranteed it. Test: one `cuts_estimate` row
in synthetic arrays, train refuses.

**F6. Degenerate propose (MED).** `cli.py:680`: if `len(props) == 0`, print FAILED and return 1.
Write `proposals.json` via tmp + `os.replace`. Test: bundle whose `p_ok` is all < 0.5, exit 1.

**F7. Docs (now).** Clarify `q`, correct `kappa0` and HANDOFF-line-95 claims in the next CONTINUITY/ISSUES
update; refresh the `cp8c_ticks.txt` hash in `manifest.sha256` and note that hashes are of the CRLF
Windows files.

**F8. ICW warning triage (before any ICW training).** CPU-only re-mesh of the 800 ICW designs,
list hashes that emit the warning, record in evidence. No GPU.

## Questions for the user

1. **NN-surrogate credit**: the frozen plan credits Collin (`docs/plan/README.md:69`, `11` section 1,
   `12` section 8). You say that is wrong. Who should be credited, and may the orchestrator add an
   erratum (frozen files cannot be edited)?
2. **cuts_estimate rows in training**: refuse the whole train, or drop and count them?
3. **Monotonic gate**: the code allows one turn per sweep of J (an optimum) and fails on two or more.
   The plan's example ("narrows and widens") is one turn on a pattern metric. Keep the code's
   reading, or also sweep beamwidth with zero turns allowed? (Either is stricter or equal, not looser.)
4. **ICW `kappa0` below 0**: allowed physically for this family, or keep 0 as the floor?
5. **`n_heldout`**: count only ok (BEM-solved) rows toward the 500 floor? Stricter; I recommend yes.
6. **Propose on an indicative-only model**: with F1, CP-8d stops at train (HANDOFF already says
   propose only if the gates pass). Confirm you do not want an "explore anyway" override.

## Addendum (~04:00 UTC): FREEFORM and further hardening

Implemented on `ccr-455d2184-yj5zk4`: FREEFORM sculpt config (11 knobs), training-export dotted-key bug fix, NaN refusal
in `unit_matrix`, FREEFORM throat radius, `compare` command, symmetry-check configs, HANDOFF section 6b. Details and the
two open rulings (FREEFORM full-vs-quarter bar; author naming) in `NOTES_FOR_SENIOR.md` 2026-10-14.

## Addendum (~05:00 UTC): reconciliation with the local issue-#13 set

The local agent implemented issue #13 independently (e0b9b61, 11304f6) and ran CP-8d on it (gates FAILED twice; model
not used). The cloud fix list F1-F4, F6 and F7 is therefore SUPERSEDED by the local set and was dropped from PR #14. Kept:
F5 (DI provenance), the NaN refusal, empty-propose failure, and the FREEFORM work (sculpt config, training-export
dotted-key fix, throat radius, `compare`, symmetry-check configs). See NOTES_FOR_SENIOR 2026-10-14 senior reviewer block.
