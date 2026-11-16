# Home continuation through 2026-11-17 morning

Owner direction: review recent results before extending; grow useful CMA data, switch to
Bayesian refinement, then refresh the data before switching again. New BO arms use
`comparison-80x2`: **80 screen + 2 verify = 82 physical-call caps**, 400 attempt cap.
The historical 60+6 and other profiles and completed study packages remain unchanged.

## Evidence and choices

- Tritonia v8: first original seed delivered 73/74 valid rows and improved J 26.903 to
  5.692 (best at evaluation 62); second delivered 39/39 and improved to 6.603 at 35.
  Top designs pressed the historical morph-rate lower bound 1.2 and azimuth cosine
  amplitude lower bound -16. A separate v9 config reopens these to 1.0 and -18 while
  preserving the published fold and geometry hygiene. The current v8 file had already
  been widened further in place; v9 is deliberately narrower than that untested box.
- TwinRay v8 improved 11.400 to 5.517 and 6.035, but its 8 mm corner floor is a geometry
  hygiene limit. Do not automatically widen across that limit or erase its reference fold.
- Warm OSSE: two day seeds each delivered 30 valid rows and never beat seed J 3.762.
  More same-box CMA is not justified now; the queued data-gated Bayesian arm remains useful.
- New/changed config identity starts a fresh cohort. Previous-family raw counts do not
  satisfy the >=100 usable, matched, strict-training-row admission rule.
- Le Cleac'h remains excluded: the later saddle geometry is in its worktree, needs
  full-horn/reference reconciliation and a corrected research dossier, and is not the
  canonical construction. Entries appended to the already-finished night B are abandoned,
  not pending work. Do not relaunch them against the canonical config.

Detailed recent-run audit: [TRITONIA_V9_CMA_AUDIT_2026-11-16.md](TRITONIA_V9_CMA_AUDIT_2026-11-16.md).

## Operating sequence

Keep the existing useful day jobs; update only not-yet-started Bayesian arms to 80+2.
Then run the v9 two-seed CMA data-building block, rebuild its exact-config cohort, and
admit Bayesian work only if strict preparation accepts >=100 usable rows. Refresh
after completed studies so later arms can learn from their measured results. Existing
data-backed ATH core and corelaw arms provide a useful tail if new-cohort admission fails.
The extension YAML records the final concrete sequence; its jobs are appended to the
live day YAML, so the existing detached controller and keep-awake remain responsible.
Never start the extension as a second concurrent GPU runner.

Final extension: **12 jobs**, comprising two 120-valid Tritonia v9 CMA seeds, first TuRBO,
80-valid local CMA from the best compatible measured CMA/BO design, refreshed TuRBO,
refreshed scalar BO, and six frozen-cohort ATH-core/corelaw scalar/TuRBO arms. Each new
BO arm is 80+2. The frozen fallback pairs share seed and cohort; the refreshed v9 arms
are sequential learning stages, not a matched optimizer comparison. Fresh cohorts use
an explicit 1024-row limit so later results are not silently lost behind the default
oldest-256 selection. Seven-hour outer BO timeouts contain the six-hour internal deadline.
Remaining warm/TwinRay day arms now use the same fail-fast 80+2 wrapper, replacing their
separate cohort/prep/run steps. Completed Tritonia's 60+6 record remains unchanged.

Live 10:25 update: the warm cohort gate found only **90** eligible rows and refused BO
without solving. A new seed-85012, 60-valid CMA top-up (existing unchanged warm config,
200-attempt config cap, 90-minute timeout, watchdog explicitly off for data-building)
and fresh-cohort 80+2 retry are inserted after Crowe-X. This is GP data acquisition,
not a claim that same-box CMA will improve the converged seed. The combined live plan
now has **28 jobs** including completed steps. The active runner raced output EOF and
logged that refused arm as exit 0: the physical refusal is authoritative. Source now
waits for the actual child exit with timeout/watchdog intact; 20 focused offline tests
passed, but this already-running process retains its old reporting code.

The local refinement snapshots completed BO screen results and up to five matching CMA
runs, retaining provenance and selecting the best measured design as both seed and mean.
It tries sigma 0.10, 0.075 and 0.05 against the history-aware expected-hit check; persistent
low hits or a hard preflight fault skips refinement. Seven offline tests passed; a real
completed-v8 rehearsal with the solver suppressed selected 0.075 (5.14 expected hits).
Three BO-wrapper tests passed; its new success-path orchestration is mock-tested. A
CPU Tritonia preparation reached 110 usable rows but sandbox hard-link permission prevented
completion; the previous live v8 study independently demonstrates the underlying pipeline.

Allow roughly 15-20 hours for the extension plus the remaining day jobs: provisioned
to carry useful work into November 17 morning, approximately 07:00-13:00 Eastern under
the observed costs. Model fitting grows with cohort size; this is not a guaranteed finish.

The v9 cohort-building CMA jobs deliberately disable the runner's convergence/pin
watchdog: the existing process cannot selectively disable its implicit 30-row pin stop,
which would prevent building the required cohort. They remain bounded by 120 valid rows,
260 attempts per seed and a two-hour job timeout. These are data-building experiments,
not a promise of 120 successful new rows. All other existing search watchdog settings stay.

## Scoring integration review

The agent branch is not safe to cherry-pick wholesale: it includes copied main files.
Integrated deltas: GUI seed-policy display and offline directivity-tag preflight check.
The check only protects recognized explicit tags; untagged configs are not certified.
The proposed new penalty, command-job guard and automatic widening remain unintegrated:
missing arrays were treated as zero, score accounting was incomplete, command jobs were
missed, and widened configs/seeds lacked reliable physical bounds and validation.
Use manually reviewed config clones for this queue.

Offline DSP-aware rescore of the rejected OSSE v8 run `5d1082` (32 screen designs):
base winner `5c8864decc06` moves from #1 to DSP #12 (passive #11); seed `7de69ffa75e8`
moves from base #2 to DSP #3. This validates the ranking concern, not the proposed penalty.
The existing DSP-aware scorer is separate from the unchanged v7 queue objective; do not
compare J across briefs or present screen ranks as acoustic verification.
Full report: `scratch/hifi_2026-11-16_osse_5d1082/hifi_rescore.md`.
Committed report: [HOME_OSSE_HIFI_RERANK_2026-11-16.md](../evidence/HOME_OSSE_HIFI_RERANK_2026-11-16.md).

## Validation and limits

- 82 offline runner/live-reload/watchdog/lane/admission/fold/Le Cleac'h geometry tests passed.
- 21 budget-profile and preparation CLI tests passed for additive 80+2 support.
- 17 offline preflight tests passed. Targeted GUI/brief/range/tip/budget/preparation rerun:
  59 tests passed, including the previously timing-sensitive cancellation test.
- No solver tests or concurrent GPU solves were launched by this maintenance pass.
- Combined live day manifest dry-run passes (28 jobs including completed steps).
  BO wrapper and refinement tests cover fail-fast setup and immutable source handling.
- The live process does not import source changes made after startup. Future child
  study preparations use current code; their immutable packages are made at execution,
  avoiding expired deadlines and pre-integration code hashes.
- The schedule is an estimate, not a stop-at-clock-time promise. Cohort admission,
  refusals and family cost can shorten/extend it. Two verification calls permit up to
  two finalists, not the previous six-call finalist/audit allocation.

Primary method references: [BoTorch TuRBO](https://botorch.org/docs/v0.17.2/tutorials/turbo_1)
(normalized inputs, trust-region progress/restarts) and
[CMA-ES](https://cma-es.github.io/) (adaptive covariance and restarts).
