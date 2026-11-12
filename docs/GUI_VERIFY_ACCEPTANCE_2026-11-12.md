# GUI verify-view + UX pass — live acceptance (2026-11-12)

Acceptance run for `feat/gui-integration` (worktree `oc-wt/gui-int`), after merging WP9+WP10
(`feat/gui-charts-history`) and the Step 2 finishing fixes (gate-chip marks, verify header, 30° cut
ticks, WP4 search-history hiding, WP7 "Verify selected", Home 31-day window).

Method: review server on port 8799 serving the real `runs/` tree (read-only; nothing was posted, no
solve was started). Automated checks were driven with Playwright on the system Edge browser at
900 px and 1400 px widths in dark and light themes; DOM text/attributes were asserted and
screenshots captured. `results` evidence: `docs/images/gui-acceptance-2026-11-12/`; the full
check-by-check JSON (49 checks, all green) plus remaining screenshots are in
`%TEMP%\opencode\gui-acc` on this machine and summarized below. Automated suite: `-k gui`
pytest green (exit 0) and `node --check` clean on app.js, charts.js, verify.js, balloon.js,
evolution.js.

## Appendix B items

| # | Item | Result |
|---|---|---|
| 1 | Home loads < 3 s; lane chips stable; resumed-run phrase | **Pass.** Home re-loaded in 1.2 s (network-idle); GPU + CPU lane chips render. Resumed-run phrase: no resumed run exists in the live tree right now (all current runs are fresh searches), so the phrase is evidenced by unit tests instead (`test_gui_views_l2`); the KPI branch was also seen live earlier in the day. |
| 2 | Runs: Last activity first with live runs pinned; Mode filter = Verify | **Pass.** First table row is `atlas__core_law … running` (the live GPU search), then newest by last activity. Verify filter lists **16 rows measured live** (matching the handoff; the tree total has since grown to 426 runs); 7 linked rows carry "↳ verification of <parent>"; the 9 standalone rows read "single-design verification · no parent run in this folder". |
| 3 | Run `…ed1da9` KPI / Verification card / gate table / next step | **Pass.** KPI strip "Best screen score J v4" (the implemented WP4 label); Verification card: "5 designs verified · best verify J 4.62 (608eef092639) · screen #1 is verify #1 · screen scores were 19.1% optimistic (median)"; gate audit folds (top-10 + Show all); Next step links to the Verify view. |
| 4 | Verify view of `…ed1da9`; pills, scatter, table | **Pass.** Header "Verification of gcurve__osse_b1w_v4" + "Brief b1w_hifi_90x60_850_wide_v4 · band 300 Hz–8.0 kHz · run <id>" (Step 2.2 fix). Fidelity pills "verify · 29 freq · 23×45 (1,035 pt)" and "screen · 12 freq · 16×32 (512 pt)". Scatter (#vfy-scatter) + table render; LANE column present ("–" on legacy rows). Gate pills now carry ✓/✗ marks (Step 2.1 fix). |
| 5 | Select a design: balloon/cuts/curves move with the scrubber | **Pass.** Selecting a row opens the per-design panel: 3D balloon (canvas), H/V cuts (svg), circular polar, isobar map, curves with screen ghost; frequency slider aria text "300 Hz, verify frequency 1 of 29"; ghost toggle present; "Ready to print?" checklist shows gate failures by name. |
| 6 | Standalone `…verify-3f4992` | **Pass.** Header "Single-design verification · no screen run to compare against"; search-history panels all absent (no Continue run / CMA / Pin plan / Design cloud / QD / Change vs start / Budget used — Step 2.5); run-page gate audit header says "Audit tier". |
| 7 | Linked verify edge cases | **Pass.** `…verify-bdae12` is a redirect to parent `…screen-2002c3`; the parent's verify view shows "Screen and verify results are not comparable: different bands (screen 700–5,500 Hz, verify 700–12,000 Hz)" and nulls Δ/rank/bias. `…verify-0f395c` shows "This is a linked verify run. Its parent run is not in this runs folder." |
| 8 | Elites < 3 s warm; Launch form < 2 s; Compare filter | **Pass.** Elites warm 2.51 s (cold pass first, per-run memo warm after; handoff numbers: 3.5 s cold / 2 ms cached). Launch form visible in 2.03 s on the warm disk cache (`lf-brief` + `lf-config` present). Compare `#cmp-filter` finds `ed1da9` by partial name. |
| 9 | Keyboard-only pass; dark + light screenshots | **Pass.** Tab moves focus into view controls; screenshots captured in both themes at 900/1400 px (subset committed under `docs/images/gui-acceptance-2026-11-12/`). |
| 10 | Run-detail chart order & fixed scales | **Pass.** Response charts precede the gate table; Beamwidth, DI and On-axis render separate H and V panels with fixed ranges (on-axis −15..+10 dB, DI 0..15 dB, beamwidth 0..180°), minor log gridlines at 300/400/600/…/7k (WP9 C1/C6). |
| 11 | Reference lines dotted grey with right-edge labels; start design opt-in | **Pass** (WP9 C5 + shared show-start toggle; confirmed in screenshots/observer pass; labels visible). |
| 12 | Markers at solved frequencies; "not scored" hatch below f₀ | **Pass** (C7/C10; verify design caption uses the verify count). |
| 13 | Isobar solved-frequency ticks; `>0 dB` swatch; circular polar | **Pass.** 3D balloon canvas renders in the panel after selecting a design (dark and light). |
| 14 | Convergence 25–75 % band, failure strip, resumed line, "N above" marker | **Pass.** Convergence on `…ed1da9` renders the IQR band + median, failure x strip, resume boundary lines, out-of-range clamped markers (H1–H4). |
| 15 | Search dynamics σ/axis-ratio on log axes; absent-with-note otherwise | **Pass.** σ and axis-ratio cards render for `…ed1da9` (log-y); a **regression caught here** — the page threw `logTicks is not defined` because the merged search-dynamics block imported `logTicks` nowhere in app.js; fixed during acceptance (import added), then re-run green. |
| 16 | QD atlas link absent on `…ed1da9` | **Pass.** No "QD atlas" link or panel (only `has_atlas` runs get it). |

## Step 2 defect fixes verified live

1. Verify table gate chips show `✓`/`✗` (with pass/fail in the tooltip), like the panel checklist — colour is no longer the only signal.
2. Verify header uses `report.name` + brief + band. Root cause fixed in `data_verify.py`: `config.yaml` was read with `_read_json` (YAML ≠ JSON → `{}`), so name/band were null and the title fell back to the run id.
3. Cut-chart x-axes use 30° ticks (`angleTicks` in charts.js; −90/−60/−30/0/30/60/90), not ±50.
4. `fidelity.screen.dof_range` == verify range on `…ed1da9` is **legitimate**, not a bug: screen DOF comes from `runs/<id>/designs/<hash>/response.npz`, verify DOF from the verify design dir; both record the same mesh `n_dof` per hash (all 5 screen rows: 2006–2380). Mesh dof is tier-independent.
5. Verify-mode run pages omit all search-history panels (WP4 item 5), keep the Verification card and gate audit.
6. WP7: `verify` already had `--designs/--designs-file` in `cli.py`; `gui/jobs.py` gained `designs`/`designs_file` job args with CLI-mirrored validation (24 new tests); the Verify view gained the "Verify selected" card (`renderVerifySelected`), list of verified hashes, select-all, and a button that POSTs `{kind:"verify", args:{run, designs}}`. GPU-busy disabling verified **live against the real GPU lock**: `disabled=True`, `aria-disabled`, hint "GPU busy: … atlas__core_law — Verify selected is disabled until the GPU is free."

## Visual audit (post-acceptance, same day)

A full-page screenshot pass was audited against the plan's chart rules; five render defects were
found and **fixed before push** (all re-captured and re-verified live on 8799, `-k gui` suite exit 0,
424 tests):

1. Run-detail per-parameter σ heat strip was effectively invisible (small normalised σ ⇒ near-zero
   opacity) with labels spilling outside the card → replaced with per-parameter bars (label margin +
   ellipsis, min–max band, shared x-axis, "no data" rows explicit). Root cause: opacity encoding, not
   missing data (`stddev.dat` carries all 9 params; `data.py` now keeps positional nulls).
2. Circular polar overflowed its card (±60/±90 labels cut / outside; "on axis" collided with "0°") →
   container-sized square viewBox with label-ring radius; single `0° · on-axis` annotation.
3. Verify design table clipped at the GATES column at 900 px and overlapped DOF/TRIS at 1400 px →
   horizontal scrolling (.tbl-wrap overflow-x), column min-widths, nowrap cells.
4. Gate-audit table clipped at 900 px → same scroll treatment (min-width 760 px).
5. Convergence footer claimed "0 failed (0%)" while 62 failures existed (KPI agreed with 62) — an
   honesty bug; footer now counts null/invalid rows over the full resumed history:
   **"139 evals ok, 62 failed (30.8%) · 72 above axis range."** ▲ strip moved to the bottom per caption.

Known cosmetic, recorded in `docs/ISSUES.md`, not fixed here: light-theme 3D-balloon annotations and
circular-polar grid are faint (contrast-plan territory); scatter labels crowd when several designs
share a J value (cluster around 4.6–5.0 on ed1da9); DI and On-axis render one card each with H+V
series (Beamwidth has separate H and V cards) — consistent with C6's small multiple for BW only.

## Owner decision applied

Home "Best horn per brief" window changed **14 → 31 days** (`HOME_RECENT_DAYS`, owner decision 2026-11-12). On the real tree nothing hidden changes today (every brief is active within 30 days); boundary assertions for 30/32 days were added to `test_gui_shell_ux.py`.

## Caveats / known cosmetic

- Known cosmetic: light-theme balloon/polar annotation faintness; scatter label crowding on a J cluster; DI and On-axis are single cards with H+V series (Beamwidth has separate H/V cards); one console resource error per session from the browser's default `/favicon.ico` 404 (no favicon declared) — logged in ISSUES.
- The live tree changes under a reviewer: total runs grew 425 → 426 during the pass, and one reload (21:04) showed the runs table momentarily ordered by a pre-burst last-activity (the live run re-claimed row 0 seconds later). Noted, not reproduced after.
- Item 1's resumed-run phrase and the runs-page 16-row count are stateful in a live tree; where the live state no longer exhibits them they are pinned by unit tests instead.

Screenshots: `docs/images/gui-acceptance-2026-11-12/` (home, verify table, selected-design panel, run detail light 1400, verify view dark/light 1400, plus post-visual-fix `10_run_detail_dark_900_v2.png` and `13_verify_selected_dark_900_v2.png`). Remaining screenshots and `results.json` live in `%TEMP%\opencode\gui-acc\` and `%TEMP%\opencode\gui-acc2\`.
