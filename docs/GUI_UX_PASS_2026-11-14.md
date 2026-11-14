# GUI / data-viz pass — 2026-11-14

Owner-driven pass over the local GUI (`hornlab_search/gui/static/`). Front-end only: no server,
data, solver or scoring change. Every number the pages print still comes from stored artifacts;
new percentages / ratios / durations are plain arithmetic over stored fields.

## What changed

**Analysis report (`#/analysis/<set>`)** — decision-first:
header + 4 headline numbers → "What to change before the next run" (rule-built actions, each
naming its source run, with a follow-through link) → run scoreboard grouped by objective version
(log sparkline, seed → best J, settled / still improving, budget bar) → objective balance (share of
J vs tolerance) → search box (current vs proposed range, walls) → sensitivity (importance +
direction + best-10 % shift) → screen vs verify (square scatter) → link candidates → not computed →
technical appendix. Fixed a reversed headline ("screening overstates J" — screen J is *lower*,
i.e. optimistic) and a refusal strip whose segments summed past 100 %.

**Run detail (`#/run/<id>`)** — verdict first: key numbers (best score, change vs start
emphasised) → Next step → view tabs (Overview · 3D · Balloon · Evolution · Design cloud · QD
atlas · Compare) with Export STEP as the one primary action → charts. Seed derivation, restart
schedule and Continue-run moved into a collapsed "Run setup & controls" block below the charts.

**Directivity isobars** — Boundary Lab frame kept (grey grid over the data, ±90° labels,
"Frequency (Hz)", solved frequencies ticked below the axis, per-map 3 dB scale) with the classic
rainbow bands, hairline contours between bands and a slightly heavier −6 dB edge; thin dashed
coverage-target guides. Over-range flagged only above +1 dB (sub-dB excess is an on-axis dip,
measured max +0.32 dB on the reference run). New **Globe** view (`charts.js::globePlot`, polar
sonogram: direction around, log frequency outward) behind a Rectangular | Globe switch.

**New run** — one nav item for Compose (Guided) and Launch (Quick launch), with a mode switch on
both pages. Launch no longer silently falls back to the first brief when a `?brief=` is not a
saved brief file (typology-config briefs); it says so.

**App-wide** — long snake_case ids wrap (`brk()`), tables stop overflowing (Runs, Campaigns),
Briefs grouped by source with a filter, Typologies' per-brief launch lists collapsed, Home lane
cards paired, stale CPU lock no longer shown as "running", pills never wrap, version banner
copy fixed, brief-band chart panel 0.30 → 0.10 opacity (grid visible again), impedance axis ticks
capped, charts redraw when their own box resizes.

## Shared pieces (reuse these)

- `charts.js`: `catColor(i)` / `CAT_N` (validated categorical palette, never cycles),
  `fmtSmart`, `fmtLogTick`, `logNiceLimits`, `sparkline`, `stackBarHtml`, `isobarLegendHtml`,
  `globePlot`; `chart(..., { square: true })`; self-redraw via one ResizeObserver.
- `app.css`: `--cat-1..8` / `--cat-other` (both themes), `--control-border` (≥ 3:1 form edges),
  `.seg-toggle` (also styles `.toggle-row`, `.elites-mode`), `.btn-sm`, `.run-tab-link`.
- `app.js`: `brk(s)` (escape + break points after `_ - . /`), `newRunModeHtml(active)`.

## Owner preferences recorded

Keep the rainbow 3 dB isobar bands with thin lines between bands; no chunky lines or halos;
Boundary Lab is the reference for directivity layout.

## Tests

`tests/test_gui_report_v2.py` (new, node-executed: actions, scoreboard, palette, kit, isobar
legend). Four source-pin assertions updated to the new run-detail / nav structure
(`test_gui_brief_authoring.py`, `test_gui_shell_ux.py`, `test_gui_freq_range.py`).
`pytest tests -k gui -m "not slow and not gpu"`: all pass.
