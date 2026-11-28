---
name: hornlab-brief-scoring
description: Choose or author a hornlab-search brief and understand what its coverage mode does before spending GPU time. Use when picking a brief for a search, editing corridor/target/constancy or envelope fields, deciding whether a new brief makes old J comparable, or re-scoring an existing run under another brief offline. Scoring math and version history live in docs/knowledge/SCORING_REFERENCE.md; solver/night mechanics are other skills.
---

# hornlab brief & scoring

A brief fixes the **score identity**. Get it wrong and every J you compare is meaningless. Read
`docs/knowledge/SCORING_REFERENCE.md` first — it is the authority, with `file:line` for every term.

## Corridor vs target vs constancy (one paragraph each)

- **Corridor** (`target.coverage_profile.mode: corridor`, `[min_deg, max_deg]`): charges **zero** anywhere
  inside the window and pays only for leaving it. `preferred_deg` is validated (`min <= preferred <= max`)
  but **never used** by the cost (`targets/profile.py:81-84`; `objective/scalar_v9.py:437-447`). A wide
  corridor lets the beamwidth wander; flatness at one angle is not free.
- **Target** (`mode: target`, a single `preferred_deg`): charges distance from that angle. Use it when the
  owner names one angle, not a window.
- **Constancy** (opt-in `objective.constancy`, v9+): prices beamwidth **flatness across frequency** at
  whatever in-corridor level the design holds. Absent by default. `strict`/`slope` and a tolerance; in
  corridor mode the fitted centre is clamped into the corridor (`scalar_v9.py:583-609`). This is the term
  that encodes "80 ± 5° **and flat**"; the corridor alone does not.

Corridor-only refuses `ripple_region` (`scalar_v10.py:168-171`). `cov_v_weight` scales the V cost in both
coverage and constancy (`scalar_v9.py:164-167`, `455-460`, `614-620`). Worked example: the favL "80 × 50"
brief that optimised to a flat ~66 × 62° under a too-wide corridor — see `SCORING_REFERENCE.md` §6.

## Authoring a brief

1. **Copy an existing brief, never edit one a queued/running night uses.** A ready ±5° constancy example:
   `examples/briefs/hf2in_2026-11-20/compact500_xo900_80x50_hf2in_v11cd_open115_pm5const_2026-11-25.yaml`
   (corridor H 75-85 / V 45-55, `constancy: {mode: strict}`, `version: 11`).
2. Keep `objective.version` and the `target:` block internally consistent; `hornlab_search.config.load_brief`
   validates it. Missing/contradictory fields fail loudly — do not invent keys (hard rule 3).
3. State envelope policy explicitly (`envelope.enforce`, `max_utilization`, `resample_strict`); size is not a
   soft J term (`SCORING_REFERENCE.md` §5).

## New-identity consequences

**Identity = objective version + brief hash + weights/target + boxes** (`objective/replay.py:176-178`;
`bo/metric_identity.py:200-236`). Therefore:

- A new or edited brief is a **different score identity** — old J is not comparable, and rows do not pool
  into the same BO/cohort (`PREDECLARED.md` for the cohort-splitting precedent).
- Re-scoring old rows under a new brief is fine for diagnosis but does **not** convert them into training
  rows for the new identity unless the run is re-scored through the canonical path.
- Never rank J across objective versions or across briefs.

## Offline replay before any GPU

Validate the brief/scorer on an existing run first; this is CPU-only and catches a mis-specified term
before a night burns GPU hours. API and exact CLI:

```powershell
# Python: load a brief and re-score one design out of a run dir
.venv\Scripts\python.exe -c "from hornlab_search.objective.replay import load_brief_context, replay_run_dir; b=load_brief_context(r'examples/briefs/<dir>/<brief>.yaml'); print(replay_run_dir(r'runs/<run-dir>', '<design_hash>', brief=b))"

# CLI wrapper (rescore a run, or a cohort, under a brief)
.venv\Scripts\python.exe tools/analysis/rescore_identity.py rescore --brief <brief.yaml> --out runs\rescore_<name> runs\<run-dir>
```

`load_brief_context` resolves through the real loader and validates the scoring params
(`objective/replay.py:219-232`); `replay_run_dir` regenerates metrics exactly as production does
(`:980-1002`). Read the numbers before queueing: a change that only moves the corridor/constancy terms
should move J in the direction the brief intends.

## Hand-off

Queue with `hornlab-night-queue`; prove the box has somewhere to go with `hornlab-search-economy`.
