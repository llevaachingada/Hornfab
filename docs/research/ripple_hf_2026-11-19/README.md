# Data-backed off-axis ripple, resonance and HF coverage — working bundle

Entry point for the 2026-11-19 handoff that argues the horn objective is blind to a class of
defect it can now measure from stored solver data: **frequency-domain deviation at a fixed
listening angle**, as distinct from the angular ripple `rip` already charges at a fixed frequency.

Status: **partially implemented**. Item 1 of the handoff's mandate (reproduce and check the data
audit) is done as a report-only diagnostic; items 2–6 remain staged or owner-gated. See
[`MANDATE_STATUS.md`](MANDATE_STATUS.md) for the item-by-item state and the open questions that
need a human decision.

## Files

| File | What it is |
|---|---|
| [`HANDOFF_2026-11-19.md`](HANDOFF_2026-11-19.md) | The senior handoff, **verbatim** (SHA-256 `D2DE2A79…8D066`). Read-only audit of 16 `response.npz` archives in `docs/evidence/runs/scout40_2026-11-19/`. Do not edit: corrections belong in the docs below. |
| [`MANDATE_STATUS.md`](MANDATE_STATUS.md) | Item 1–6 status, what is implemented, what needs owner/GPU approval, and the human-review flags. |
| [`MEASUREMENT_TAXONOMY.md`](MEASUREMENT_TAXONOMY.md) | The measurement taxonomy the mandate asks for (item 2), grounded in primary sources, with applicability limits and the names we will and will not use. |

Measured audit output (item 1) is evidence, not research:
[`docs/evidence/spectral_ripple_audit_2026-11-19/`](../../evidence/spectral_ripple_audit_2026-11-19/README.md).

## The one-sentence finding

`rip` is a **quartic detrended angular** residual at each solved frequency
(`metrics/smoothness.py::ripple_detrended_db`), so a design whose polar cuts are smooth at every
frequency can still have large, audible structure along a fixed off-axis frequency response — and
`J` will not see it. That is a measurement gap, not yet a proved acoustic resonance.

Measured caveat (detail in [`MANDATE_STATUS.md`](MANDATE_STATUS.md) and the evidence bundle): across
the 24 SCOUT40 bests the gap is real but **partial** — the fixed-angle residual is largely redundant
with `rip` (ρ = 0.885), and the result flips depending on which reference (IEC band-mean vs
exploratory trend) is used (ρ = −0.018). Nothing here justifies a new weighted term yet.

Grid stability was then tested on hardware (2026-11-20): ten designs re-solved at verify fidelity
give **ρ = 0.964** against their screen values, max Δ 0.467 dB — the ranking survives the grid
change, absolute values do not. [`VERIFY_GRID_TEST.md`](../../evidence/spectral_ripple_audit_2026-11-19/VERIFY_GRID_TEST.md).

## Boundaries that bind this bundle

- **Report-only.** No new objective term, no change to any stored `J`, no re-scoring of history.
  The audit tool is explicitly *never a score term* (same posture as `tools/analysis/xo_loading_report.py`).
- **No GPU was used.** The mandate's items 3–5 (dense-frequency re-solve, controlled HF-width
  experiment, real-driver source validity) need owner approval and a free GPU lane.
- **18 stored frequencies cannot establish ringing.** Anything about time-domain behaviour must go
  through the dense-grid path already designed in [`../TIME_DOMAIN_RINGING.md`](../TIME_DOMAIN_RINGING.md).
- **Never rank `J` across objective versions or briefs.** All 24 SCOUT40 runs are `objective_version`
  7 (verified), and the B3/C200 variants use the `v7_smooth` brief while the rest use regular v7;
  the audit groups by identity and refuses a pooled rank.
