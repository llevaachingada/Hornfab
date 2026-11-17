# Adaptive unknowns: questions whose answers would change the architecture

- Repo: `C:\Users\hunte\Hrns\hornlab-search`; HEAD at final write
  `601be8ceeb48f1750bb4f3f6c1fdc682967c8b94` (`2026-11-16T20:38:46-05:00`); files read at
  `13b47632`, byte-identical at cited SHAs. Read-only; every test below is **proposed**, not run.
- "Low-cost" means existing artifacts or CPU-only; "expensive" means new BEM solves. A question is
  here only if a different answer changes a later choice.

## Q1. Does screen J rank the same designs as verify J?

**Why it matters.** A supervisor switching on screen J assumes it is a useful proxy for the
verified/acoustic ranking; if not, the switch is noise.

**Falsifying test (zero GPU).** On the 42 existing pairs in
`docs/status/2026-11-15-bo-vs-cma/data.json`, compute Spearman/Kendall rank correlation overall and
in the top quartile (where a supervisor acts), arm by arm. Predeclare failure at top-quartile
correlation <0.5 or a sign flip in the best-3 ordering. Data: `data.json`, `study-*/screen/` and
`study-*/verify/search.ndjson`; no new solves.

**Counterfactual left unknown.** A good correlation does not show a *switch* would have improved the
final verified design; it only shows the signal is usable.

## Q2. Is a 100-231-row GP good enough to rank held-out designs?

**Why it matters.** The 100-row floor is a spend heuristic, not a demonstrated sufficiency threshold
(`tools/bo_compare/prepare_study.py:76-77,163-169`). If held-out ranking is poor, more BO arms are
not justified.

**Falsifying test (zero GPU).** Time-blocked or leave-one-arm-out validation with the locked model
(`bo/model.py:204-413`): fit on rows before a held-out block, predict that block, report rank
correlation and calibration. Use the 185-row prior, 231-row cov cohort and 60-row BO arms. Data:
`runs/bo_multityp_2026-11-16/*/cohort`, training manifests, `study-*/screen/search.ndjson`.

**Counterfactual left unknown.** Retrospective rank correlation does not prove the next adaptive pick
is better; it only removes one failure mode.

## Q3. Are geometry refusals a learnable margin or a binary pre-solve event?

**Why it matters.** A separate feasibility GP (Gardner-style) needs a signed constraint value at
infeasible points. If refusals are binary, a geometry filter/box repair is the better intervention.

**Falsifying test (zero GPU).** For historical accepted and refused designs, compute the cheap
envelope/throat diagnostics (`bo/data.py:871-953,1219-1278`), fit a simple classifier/GP to predict
refusal, and report AUC/calibration. AUC near 0.5 falsifies "learned feasibility"; high AUC makes a
margin model worth wiring. Data: stored params/configs and `search.ndjson` reasons; no meshing/BEM.

**Counterfactual left unknown.** A high historical AUC may reflect the old box; a prospective test is
still needed before spending solves.

## Q4. Does mixed fidelity preserve the J ranking?

**Why it matters.** The native builder allows mixed screen/verify fidelity by default
(`bo/data.py:380-387,744-747`), while study prep requires one fidelity
(`tools/bo_compare/prepare_study.py:163`). If ranks differ, a mixed cohort needs a fidelity term.

**Falsifying test (zero GPU).** On existing screen/verify pairs, compute rank correlation and top-k
ordering by design; reuse Q1 data. Admit a mixed cohort only if the ranking is stable above the
measured drift. Data: `data.json` and verify ndjson; no new solves.

**Counterfactual left unknown.** It does not show whether a fidelity-aware GP would fix a broken
ranking; it only shows the current pooling is unsafe.

## Q5. Is the historical gap prior/refusal handling, and would a switch help under equal cost?

**Why it matters.** BO had 60/60/60 valid rows and 185 prior rows; CMA had 31/44/46 valid rows, one
starting design, and 29/16/14 "too large" refusals (`docs/status/2026-11-15-bo-vs-cma/data.json`;
`README.md:15-22,30-37`). If that explains the gap, "switch to BO" is the wrong lesson.

**Falsifying test.** First a zero-GPU common-successful-query-prefix comparison, counting the 185
prior rows as shared prior. Then, only if a switch is still plausible, a predeclared two-arm A/B:
fixed policy vs a frozen switch rule, same cohort, same **valid-row** budget, same refusal handling,
2 seeds, fixed stop, censored-arm reporting (`docs/queue/MATCHED_HOME_PROTOCOL_2026-11-16.md:5-20`;
`tools/night_queue/run_matched_home.py:112-123`). The GPU part is expensive; the first pass is not.

**Counterfactual left unknown.** Without the A/B, the causal effect of the optimizer label (or the
switch rule) remains unidentified; only the association is known.

## Q6. Does the cheap candidate-pool pass predict acoustic eligibility/success?

**Why it matters.** BO's pool is "cheap-check-passed; mesh/acoustic eligibility unknown"
(`bo/data.py:33,1152-1153`). If the pass is unrelated to success, BO's low refusal rate is a
selection bias, not a better search.

**Falsifying test (zero GPU).** Replay the cheap checks (`bo/data.py:1068-1180`) on historical rows
and compare pass/fail to actual success/refusal; report AUC and refusal-rate difference. Data:
stored params/configs + `search.ndjson` outcomes; no new solves.

**Counterfactual left unknown.** A good historical AUC does not prove the pool helps in a new region
of the box; a prospective sample would be needed.

## Q7. Is the v7 score stable enough to optimize, or is the objective still moving?

**Why it matters.** v7 is under review (`docs/queue/BO_MULTITYPOLOGY_PLAN_2026-11-16.md:9-11,200-204`),
and the code has a v4-only cohort gate beside a v7-capable native builder (`bo/cohort.py:96-97`;
`bo/data.py:657-665`). A switch on a contested score is not stable.

**Falsifying test (zero GPU).** Rescore existing rows under v4/v7 (and the documented DSP rescore)
and compare ranks, not absolute J; use `docs/queue/HOME_SCORE_AUDIT_2026-11-16.*` and
`tools/analysis/hifi_rescore.py`. Allow a switch decision only if top-quartile ordering is stable
across accepted score versions.

**Counterfactual left unknown.** A stable rescore does not validate the brief against acoustic intent; it only rules out a rank-changing scoring bug.

## Cross-cutting: unchosen counterfactuals

- **Prior vs algorithm:** without a cold-start/equal-prior test, the BO win is compatible with "BO
  used 185 rows and a pre-checked pool" as well as "BO searches better".
- **Refusal handling:** without equal filtering, CMA's 14-29 lost attempts are a confound.
- **Switching vs fixed policy:** without a predeclared A/B, the value of O3/O4 is unknown; a shadow
  advisor only records an opinion.
- **QD / robustness / cost:** a flat J can coexist with a useful archive; robust design and cost-aware
  acquisition remain proposals without an uncertainty model or >=30 uncached timings.

## Priority if only three tests run first

1. **Q1 + Q4 (zero GPU):** screen/verify rank stability; if it fails, every screen-J switch rule is
   invalid.
2. **Q2 (zero GPU):** held-out GP ranking at 100-231 rows; if it fails, more BO arms are not the next
   spend.
3. **Q3 (zero GPU):** refusal-margin learnability; if it fails, a geometry/box filter beats a
   feasibility GP or a policy switch.
