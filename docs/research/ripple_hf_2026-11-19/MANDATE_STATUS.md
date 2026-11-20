# Mandate status — what is implemented, what is owner-gated

The handoff's §"Proposed Fable review mandate" has six items. This file tracks them, because the
handoff itself is preserved verbatim and must not be edited. Update this file, not the handoff.

| # | Item | State | Where |
|---|---|---|---|
| 1 | Reproduce and check the data audit (read-only, no BEM) | **DONE** — report-only tool + verified table | `hornlab_search/metrics/spectral.py`, `tools/analysis/spectral_ripple_audit.py`, [`evidence/spectral_ripple_audit_2026-11-19`](../../evidence/spectral_ripple_audit_2026-11-19/README.md) |
| 2 | Build a rigorous measurement taxonomy before writing weighted terms | **DONE (documents only)** | [`MEASUREMENT_TAXONOMY.md`](MEASUREMENT_TAXONOMY.md) |
| 3 | Validate the B3 2.3–3.0 kHz anomaly with a densely sampled re-solve | **STAGED, NOT LAUNCHED** — dense B3 at epw 6/9 in `docs/queue/fable_expand_2026-11-19.yaml`; the audit-stability night in `docs/queue/ripple_audit_2026-11-20.yaml` | §"Staged nights" below |
| 4 | Controlled HF-width experiment (Crowe X OSSE / R-OSSE rect / OSSE morph) | **NOT STARTED — owner GPU gate + new configs** | plan below |
| 5 | Check installed-source validity above the first transverse mode | **NOT STARTED — needs real-driver data or a modelled wavefront** | plan below |
| 6 | Then revise scoring if justified | **DELIBERATELY DEFERRED** — nothing to score until 1–3 produce rank reversals | — |

## Item 1 — what "done" means here, and what it does not mean

Implemented and measured:

- `metrics/spectral.py::fixed_angle_residual_db` — the handoff's exploratory quantity, exactly:
  normalise a fixed-angle cut to its 0° sample, restrict to `1065 ≤ f ≤ 4832.5 Hz` (10 stored
  samples), fit a quadratic in `log2(f)`, quote the RMS residual in dB. Population RMS, unlike the
  repo's `ddof` conventions, because this is a **new** report-only number and reusing the stored-score
  convention would invite somebody to compare it to `rip`.
- `tools/analysis/spectral_ripple_audit.py` — scans design dirs (or whole run dirs), writes
  `audit.json` + `disagreement.md`, and **refuses to pool ranks across objective versions or briefs**.
  It records the identity (`objective_version`, `config_name`, `family`, `design_hash`) next to every
  number.
- The agreement/disagreement table is generated from stored data only: zero solver calls.

What it still is not: a validated hearing-weighted score, a resonance detector, or a score term. A
quadratic in `log2(f)` over ten samples is a detrending *choice*; the tool reports the scan across
detrend orders 1–3 and a wider angle set so a reader can see when the ranking is an artefact of that
choice.

**What the measured run changed in the argument (read this before quoting the handoff).** Running the
audit over all 24 SCOUT40 best designs produced two results that a reader of the handoff alone would
not expect, and they are the reason nothing is promoted to a score term:

1. **The reference is not a detail — it decides the verdict.** The exploratory trend residual and the
   standards-backed band-mean residual rank the designs almost independently (Spearman ρ = −0.018).
   The band-mean reference charges a *smooth taper*, so the Le Cléac'h/Iwata/Lame designs (best on the
   trend variant at 0.04–0.12 dB) land at the bottom on band-mean (2.1–2.4 dB). A CD-shaped
   smoothness target would forbid those families. Use the trend variant cross-family, label it
   exploratory, and quote a band-mean number only inside one family.
2. **The number is largely redundant with `rip` here.** ρ(`rip`, trend +35°) = 0.885, i.e. the
   fixed-angle residual mostly re-orders designs `rip` already ranks. What it adds is degree and
   location, not a new axis. So the honest statement is "`J` under-charges a defect it partly sees",
   not "`J` is blind to a whole defect class" — and that is evidence **against** item 6 for now.

Detail, tables and provenance: [`evidence/spectral_ripple_audit_2026-11-19`](../../evidence/spectral_ripple_audit_2026-11-19/README.md).

## Items 3–5 — staged plans (each needs an owner decision before any GPU time)

### Staged nights (2026-11-20) — nothing here has been launched

- **`docs/queue/fable_expand_2026-11-19.yaml` (ids `x_r3_b3_dense_epw6` / `epw9`)** — item 3's dense
  re-solve of `ee85bcd2ad67` on 1.8–3.6 kHz at 25 Hz steps (73 extra frequencies), at `epw` 6.0 and
  9.0 to test convergence rather than interpolation. Configs in
  `examples/typologies/expand_2026-11-19/`, `budget: 1`, report-only.
- **`docs/queue/ripple_audit_2026-11-20.yaml` (new, 11 jobs, ~15–20 min GPU)** — tests the *audit*
  rather than the anomaly: ten already-solved bests spanning the measured range (B3 current/previous,
  C200, OSSE morph, ext-throat, R-OSSE rect, Crowe X OSSE, Tritonia v8, Lame, Le Cléac'h) are
  re-solved at **verify fidelity** (25 log frequencies instead of 18, balloon 1024) with
  `hornlab-search verify --designs <hash> --verify-dir runs/ripple_audit/<id>` — the source run's own
  config and brief are reused, so no config is authored and no brief is edited. The last job runs
  `tools/analysis/spectral_ripple_audit.py` over the ten verify responses.
  **Predeclared criterion**: Spearman(screen V+35, verify V+35) ≥ 0.8 over the ten designs, no design
  moving more than 0.5 dB, and the B3 notch still present once 25 frequencies sample it. A failure is
  the useful outcome: it would mean the 10-sample number is grid-limited and must never be quoted as
  a design property — and item 6 stays closed.
  Not launched: it is `lane: gpu`, and its per-job `gpu-clean --lane gpu` must not run beside another
  GPU night. Chain it behind the live runner (`-WaitPid`), never beside it.

**Item 3 — dense-frequency validation of the B3 vertical feature.** Re-solve one design
(`ee85bcd2ad67`, Klangfilm B3 current, `docs/evidence/runs/scout40_2026-11-19/20261119T073330Z-screen-723756/`)
on a uniform grid spanning roughly 1.8–3.6 kHz at ≈25 Hz steps, and the same design at a finer mesh,
so convergence is tested rather than interpolated. Success criterion is written down before the run:
the 2.27–3.31 kHz deviation must persist with a stable amplitude at both mesh densities and both
frequency steps. Owner cost: a handful of solves in one night slot, not a search.

**Item 4 — controlled HF-width experiment.** Preselect matched variants of Crowe X OSSE, R-OSSE
rectangular and OSSE morph, and vary **one** factor at a time (early flare angle/timing, then
source-to-horn transition, then mouth rollback, then aspect/morph), source-identical. Record 4, 6.2
and 8 kHz coverage with LF loading, fixed-angle residual and lobe/notch counts. This is a
`hornlab-shape-check` pass (config + mesh proof) before any `hornlab-search-economy` preflight, and
then a queue slot. Do not spend it on a single J.

**Item 5 — source validity above the first transverse mode.** The uniform-velocity cap is a modelling
choice, not a measured driver wavefront. Either (a) add a wavefront-shape option in the mesher's
source builder (fork work, needs its own validation ladder), or (b) measure a real 1.4" driver on the
intended horn and compare. Until one of those exists, any 8–16 kHz improvement is a **simulation
result about a uniform source**, not a claim about the horn in a room. See
[`MEASUREMENT_TAXONOMY.md`](MEASUREMENT_TAXONOMY.md) §"What the model cannot see".

## Human-review flags

These are the decisions this implementation deliberately did **not** make. Each one changes an
acoustic target or spends GPU time, so it belongs to the owner.

1. **H1 — Is fixed-angle spectral consistency a target for our briefs?** The metric measures a
   deviation, but the acceptable amount is a *target* decision per brief (a HOME living-room horn at
   a 700 Hz crossover vs a compact 400 mm cube may legitimately differ). Until a brief states a
   tolerance, the audit reports numbers with no pass/fail.
2. **H2 — Standardise or not.** Band `1065–4832 Hz`, quadratic detrend, `+25/+35°` vertical are
   the handoff's exploratory choices, chosen because they are the 10 stored samples of the SCOUT40
   grid. Committing them as a project standard is a decision; leaving them as tool defaults that every
   report must state is the conservative option taken here.
3. **H3 — GPU authorisation for items 3–5.** Nothing here ran on the GPU, and none of these items may
   start without an owner-approved slot: at the time of writing `tools/night_status.py --since-hours 48`
   reported the GPU lock **stale-held** (holder pid gone) after `p12_verify_2026-11-19` exited 1, so
   the lane needs a `gpu-clean` + owner go-ahead before any solve. Item 3 is the cheapest and the only
   one that can turn the finding from "measurement gap" into "acoustic fact or artifact".
4. **H4 — Crowe X OSSE is an HF direction, not a winner.** Its 8 kHz 74°/54° with `lfp50 ≈ 986 Hz`
   and `rez_min_from_fx ≈ 0.342` is a poor 700 Hz horn, and its `load` term (≈ 2.64 of `J ≈ 5.35`)
   is most of its score. Deciding whether to pursue "keep the HF, recover the LF" is a design
   priority, not a metric.
5. **H5 — Any promotion into scoring.** If items 1–3 produce a rank reversal, a new term must
   arrive as a **new objective version** with its own identity, published floor and no retroactive
   re-scoring — the same rule that produced v7/v9/v10. `docs/plan/01_CONTRACTS.md` is frozen; this
   cannot be an in-place edit.
6. **H6 — `load` weight and a Re(z) gate.** Crowe X OSSE scores well on J partly *because*
   `load` is weighted 1.0 and its RE deficit is charged once. Whether an explicit `rez` qualification
   gate is wanted (rather than a weighted penalty) is an objective-design decision, not a bug.
