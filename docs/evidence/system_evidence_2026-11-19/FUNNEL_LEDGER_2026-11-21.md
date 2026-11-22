# System funnel ledger and G7 audit status (WP6, 2026-11-21)

**Scope.** WP6 asked for one deterministic command that joins the screen shortlist to BEM case
dirs, reports gate losses, and performs a false-negative audit against the installed references.
This is a read-only CPU recompute of the local store. No solve, no DSP sum, no ranking.

**Honest result.** The ledger exists and reproduces the store census, but the false-negative
audit has **insufficient paired data**: no shortlist candidate reaches a solved two-channel
(woofer + horn) case. The ledger emits
`FALSE_NEGATIVE_AUDIT_INSUFFICIENT_PAIRS` with `pair_count = 0` instead of inventing a decision
rule.

## Command

```powershell
.venv\Scripts\python.exe -m hornlab_search.system.cli funnel --root .
```

`--out DIR` writes `funnel_ledger.json` + `funnel_ledger.md`; without it the command only prints
the ledger. Module tests: `tests/system/test_funnel.py` (5 passed).

## Screen census [measured]

```text
files 6, unique_study_ids 2, duplicate_study_ids [27616eedee09009f, 65f6db3e8c8e8f86]
shortlist_rows 36, kept_rows 459, rejected_rows 141
distinct_shortlist_candidate_ids 10
```

The duplicate ids are the same two studies stored in three files each (original + replay/copy),
not three independent studies.

## Case census and join [measured]

```text
case_dirs 54: solved 22, staged 29, refused 3, invalid 0
with_join_key 2, without_join_key 52, two_channel 13
shortlist rows: matched 3, missing_case 33
matched rows resolved: solved 3, staged 0, refused 0
missing_channel_rows 3, band_miss_rows 0
solved_two_channel_pairs 0
```

- Only two case dirs carry a `seed.candidate_id` at all; the rest have no join key and are never
  guessed by asset or driver id. This is deliberate.
- The three matched shortlist rows resolve to the single solved `bl_motor12pr` case, which is
  **woofer-only**; all three therefore also count as missing-channel rows. There is no solved
  two-channel case for any shortlist candidate.
- The thirteen two-channel cases are measurement variants of one assembled #2 project (including
  the R5a balloon control), but they have no screen `candidate_id`. Asset-level similarity is not a
  candidate join.

## Tokens emitted

```text
NO_BEM_CASE_FOR_CANDIDATE
BEM_CHANNEL_MISSING
DSP_SUM_LOCKED_OWNER_DECISION_3
GUI_SOLVE_DISABLED_OWNER_DECISION_6
FALSE_NEGATIVE_AUDIT_INSUFFICIENT_PAIRS
```

The DSP-sum and GUI-solve tokens are declared stops, not scan conditions: the ledger stops before
the owner-gated sum/solve rather than implying a completed funnel. `BEM_BAND_OUT_OF_RANGE` did
not fire on this store (no solved two-channel case reaches the band test).

## What this closes and what it does not

Closes: WP6's deterministic ledger and the G7 audit **machinery**. The gate losses are now
reproducible and the store's pairing gap is explicit.

Does not close: G7's statistical conclusion. With zero shortlist → solved two-channel pairs (and
one woofer-only candidate), any false-negative rate would be vacuous. R7a (the calibration
record) is separate; R7b (threshold recalibration) still needs the real transducer shape (R2) and
a 5° or finer grid.

## Reproduce

```python
from pathlib import Path
from hornlab_search.system import funnel

ledger = funnel.build_ledger(Path("."))
print(ledger["screen_census"])
print(ledger["case_census"])
print(ledger["join"]["counts"])
print(ledger["false_negative_audit"])
print(ledger["tokens"])
```

The module reads only `system_runs/**/woofer_seed.json` and
`system_runs/system/<experiment>/<case>/`; `write_ledger` is the only writer. No GPU was used.
