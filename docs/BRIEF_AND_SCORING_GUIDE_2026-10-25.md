# Brief and scoring guide — the S1a driver pass (2026-10-25)

Owner-directed finalization (Oracle decision pass; every number below was measured on the live
tree via march + envelope + real gmsh dry-runs — see the smoke-matrix evidence and the probe
outputs in that evidence's addendum). This doc answers the owner's two asks:

1. **Briefs**: which brief to run which typology under, for the 1-inch / 1.4-inch / 2-inch
   throat classes and custom sizes — and the physics behind every number in them.
2. **Scoring**: what the objective terms mean, how objective versions interact, and what to
   change when a run looks wrong.

## 1. The brief family

**Mechanism (uniform):** the driver class lives in the **brief** — `load_config` applies the
applied brief's driver pins over the config (WP2), and the K-law derivation reads coverage /
f0 / envelope from it. Pick a brief → pick a driver. **Custom = copy the nearest family brief**
and edit driver/envelope/f0 per §2 below. No per-driver config clones; no catalog driver ties
(all five S1a typologies are verified multi-driver, 12.7 → 25.4 mm).

| Family brief (shipped) | exit_radius_mm / angle | envelope W×H×D (mm) | coverage | band (Hz) | f0 (Hz) | objective | Family use |
|---|---|---|---|---|---|---|---|
| `hifi_90x60_1in` (revised) | 12.7 / 5° | 400×300×220 | 90×60 | 700–5500 | 1450 | v3 | biradial_keele, qtw_waveguide, classical/hybrid hifi configs |
| `hifi_90x60_14in` (new) | 17.78 / 5° | 420×320×230 | 90×60 | 700–5500 | 1450 | v3 | same family, 1.4-inch class |
| `hifi_90x60_2in` (new) | 25.4 / 4° | 640×460×340 | 90×60 | 600–5500 | 1000 | v3 | same family, 2-inch class (f11 caveat binds) |
| `organic_rollback_1in` (revised) | 12.7 / 5° | 520×420×260 | 90×60 | 700–5500 | 1900 | v3 | salmon_x_signed, salmon_ripple12 (+ the salmon rows family); `load 0.5` + `z_min 0.7` |
| `organic_rollback_14in` (new) | 17.78 / 5° | 540×440×280 | 90×60 | 700–5500 | 1800 | v3 | same, 1.4-inch class |
| `organic_rollback_2in` (new) | 25.4 / 4° | 680×500×340 | 90×60 | 500–5500 | 1550 | v3 | same, 2-inch class (f11 caveat binds) |
| `lecleach_rollback_1in` (new) | 12.7 / 5° | 520×420×260 | 90×60 | 700–5500 | 1200 | v3 | lecleach_asym_odd (+ lecleach rows); `load 0.5` + `z_min 0.7` |
| `lecleach_rollback_14in` (new) | 17.78 / 5° | 540×440×280 | 90×60 | 700–5500 | 1200 | v3 | same, 1.4-inch class |
| `lecleach_rollback_2in` (new) | 25.4 / 4° | 680×500×340 | 90×60 | 500–5500 | 1200 | v3 | same, 2-inch class (f11 caveat binds) |

**Why each f0:** the K-law `d = 25,400/(f0·coverage)` mm must fit the envelope per axis
(minus the two wall shells), with one family correction: the **salmon rows' rollback
y-extent ≈ 1.8× their −6 dB mouth** (measured extent×fc ≈ 3.3–3.4×10⁵ mm·Hz at stop
140–170), so the extent-limited mouth, not the bare K-law mouth, sets the f0 floor
(organic: f0 1900/1800/1550). The **Fourcade (JMLC) rows are extent-honest (~1.05×)**, but
the full ring's dof cost sets their floor instead: at f0 1100 the derived fc bills 5,059
dofs — over the 5,000 screen cap (measured); **f0 1200 derives fc 652.8 → 4,190 dofs**
(measured green at all three driver classes). The hifi family's f0 is the K-law break of
its binding axis at its envelope (V 300 mm holds 60° only above ~1,411 Hz → f0 1450).

**The measured green matrix** (gmsh dry-runs at the screen tier, this pass):

| Config | own (revised f0) | 1.4in brief | 2in brief | xx (8k band, user) |
|---|---|---|---|---|
| biradial_keele (L 195) | derived seed, 0.0 overshoot; 1,893 dofs | 0.0; ~2,000 | 0.0; ~2,200 | 4,444 dofs OK |
| qtw_waveguide (unchanged) | 1,616 | 1,764 | 1,990 | 4,040 |
| salmon_x_signed (stop 150, amp −0.15) | 1,792 | 1,887 | 2,504 | 4,046 |
| salmon_ripple12 (stop 150) | 2,567 | 2,804 | 3,636 | over by 1.4% (needs band_hi ≤ ~7,400) |
| lecleach_asym_odd (eps 0.20) | 4,190 | 4,152 | 4,141 | over cap at 8k (disclosed) |

All five configs march envelope-true under every family brief above (probe + tests) — an
f0-carrying brief can no longer produce an un-closeable biradial seed (see the derivation
note in `hornlab_search/config.py::_derive_generator_geometry`, the one owner-directed
`widened_to_closure` exception to the clamp-only contract, flagged per note).

### Custom-brief guidance (the "custom size" case)

1. **Throat:** any `exit_radius_mm` in (0, 100) loads; the five typology seeds are verified
   from 12.7 through 25.4 mm. Beyond ~30 mm an f0-carrying brief still loads (the biradial
   derivation widens `rm` to the closure line, flagged `widened_to_closure`).
2. **f0:** set `f0 = max(25,400/(cov_h·W_env), 25,400/(cov_v·H_env))` (Hz, mm) — the binding
   axis; for salmon-rows customs divide the V mouth by the 1.8 extent factor first (or copy
   the family brief and keep its f0 rule). Always pair `target.f0_hz` with
   `objective: {version: 3}`.
3. **band_hi:** keep ≤ ~5,500 on this GPU. Measured at band_hi 12,000 the screen mesh
   exceeds the caps for EVERY one of the five (biradial 12,321 tris vs the 11,275 limit;
   qtw 5,459 dofs vs 5,000; x_signed 11,858 tris; ripple est. 24,531 tris). `band_hi` also
   invalidates the plane-wave throat assumption above `f11 ≈ 100,250/r0` Hz (7,914 Hz at
   1-inch / ~5,640 at 1.4-inch / ~3,960 at 2-inch).
4. **The owner's current customs (disclosed, not edited):** `samonrip.yaml` says "90x60" but
   targets 75×30 — from its 500×390×300 envelope, 75° H is held only above ~677 Hz and 30° V
   only above ~2,171 Hz (the §13.5 impossibility — see the scoring guide below), and its
   500–12,000 band exceeds both f11 and the card. `75x35.yaml`'s description says "Eighty by
   40" (targets 75×35) with band 300–12,000 (same 12k problem). `xx.yaml` is the axi_2in_large
   copy with depth 400 and **no f0_hz** — v3 masks nothing there; biradial runs the YAML seed
   (safe at 25.4); ripple's 8k-band screen mesh is over the cap by 1.4%.

## 2. Scoring guide (plain language)

All terms are means over the in-band frequencies of the mode's frozen grid; lower J is better;
weights multiply then sum.

- **cov** — how far the measured −6 dB beamwidths (H and V) sit from the brief's coverage
  targets: mean over frequency of `(bw_h − target)² + (bw_v − target)²`, /100. The
  directivity contract; normally the dominant term.
- **rip** — mean polar ripple (dB) across H and V. Rewards smooth, non-lobed polars.
- **di** — squared error of the Directivity Index against the reference DI derived from the
  coverage targets (a brief `di_target_db` overrides), /10.
- **dislope** — squared slope of DI vs log-frequency (target 0 = constant directivity).
  **Hostile by construction over a wide band:** a horn always has rising DI below its K-law
  break. §13.5 measured 30–42% of J in the organic runs chasing an unattainable slope-0. The
  v3 below-f0 mask is the fix — not weights.
- **flat** — population std of the on-axis response (dB). Rewards flat power response.
- **load** — how far Re(throat impedance) falls below the brief's `z_min`, zero-padded above
  it. Only meaningful when `z_min > 0` **and** `load > 0` (the pair `z_min 0` + `load 0.5` is
  dead — the 75x35 finding).
- **Graded infeasible penalty** — designs that march but overshoot the envelope get a penalty
  scaling with the overshoot (points back toward feasibility); geometry/mesh refusals get the
  flat 1,000. Keep `infeasible_penalty: graded` on the organic rows configs.

**Objective versions:** v1 = the plain weighted sum. v2 = v1 + WP4 `target.freq_weights`
(applied to the ripple mean). v3 (S1a) = `freq_weights` also weight **cov**, and **cov and
dislope score only f ≥ target.f0_hz** (the below-f0 mask). Without f0_hz, v3 equals v2
bit-for-bit. Never re-score old runs with v3 — a run's embedded brief is authoritative on
resume, and runs scored under different f0/weights are different record groups.

**What NOT to tune first** (the §13.5 fix order, binding):
1. Do not raise the cov weight first — when the brief asks for coverage the envelope cannot
   hold, cov dominates (88% of J in the measured 110-eval run) and more weight chases the
   same wall.
2. Do not fight dislope with weights — mask below-f0 with v3 + an honest f0 instead.
3. Fix the brief first: coverage × band × envelope must satisfy the K-law per axis (§ rule 2
   above). Read the run's `feasibility` record (GUI: the seed-derivation card) before
   interpreting any J.
4. Weights come last — and only then, deliberately.

**Recommended scoring defaults per family** (exactly what the shipped briefs above carry —
no weight changes were made anywhere):

| Family | cov | rip | di | dislope | flat | load | z_min | objective |
|---|---|---|---|---|---|---|---|---|
| hifi (biradial, qtw, classical) | 1.0 | 1.0 | 0.3 | 0.5 | 0.5 | 0.0 | 0.0 | v3 + f0 |
| organic/salmon rows | 1.0 | 1.0 | 0.3 | 0.5 | 0.5 | 0.5 | 0.7 | v3 + f0 |
| lecleach rows | 1.0 | 1.0 | 0.3 | 0.5 | 0.5 | 0.5 | 0.7 | v3 + f0 |

Rationale: waveguides on compression drivers are not scored on loading; rollback/JMLC horns
earn their living by loading the driver. Nothing was flipped — §13.5-D contraindicates weight
tuning before brief honesty, and the briefs above now deliver that honesty.

## 3. Honesty notes

- **J comparability:** the revised briefs change scoring (f0 + v3) — new runs are new record
  groups; the GUI never ranks across differing solve groups (compare warns). Old runs keep
  their embedded briefs byte-for-byte.
- The 12k-band user customs cannot screen on the 8 GB 4060 (caps never raised); disclosed
  with the measured numbers above — copy a family brief with band_hi ≤ 5,500 instead.
- The 180° cap-area asymptote is live INSIDE the salmon rows' search bounds (stop ≤ 240 with
  |x_amp| ≤ 0.4 can cross it): those rows explode in size → graded infeasible — the intended
  penalty path, never a crash.
- `salmon_elliptical` (pre-existing family member) grades 4.2% over under the revised organic
  brief at its stop-170 seed (marches fine; graded points back). Same reseed recipe as the
  pair this pass fixed, available as a future owner-gated item.

## 4. How the size limits actually work (the plain-language layer model)

Added 2026-10-25 evening, owner-directed ("am I reading this right — is L_mm capping the depth
even though my brief says the horn can be 500×500?"). The answer: **yes, you read it right, and
yes it was over-constrained** — but by the typology's search box, not by your brief. There are
three different "size limits" in this tool, and only one of them comes from your brief:

1. **The search box (config `bounds:`) — what the Shape-parameters table shows.** Every knob a
   typology searches has a low and high (the `L_mm 90.000 / 140.000 / 139.279` row: box 90–140
   mm, the current design at 139.279, and the two right-hand columns are the at-limit counters —
   "of the 6 best designs, how many sit exactly at the low bound" and "…at the high bound").
   The optimizer (CMA-ES) samples ONLY inside this box. Your brief cannot move it. These numbers
   ship in the typology's YAML (`examples/typologies/<name>.yaml`, the `bounds:` block) and were
   authored per typology around the M4-era reference briefs — e.g. `perturbed_osse_hv` says its
   horn depth (`L_mm`, the profile length) may only vary between 90 and 140 mm. Your run proves
   the cost: 4 of the 6 best designs pressed the 140 mm wall (the GUI marks this in the At-limit
   KPI), and the brief allowed depth up to 600 mm — the box, not your brief, was the binding
   constraint.
2. **The brief envelope — a fence, not a target and not a box.** The brief's max mouth/depth
   (your 680×500×600) is a do-not-exceed guard: a design that marches past it is penalized
   (graded) or refused, but NOTHING pushes a design to use the space. A bigger envelope simply
   permits bigger horns; it never enlarges the search box. This is why "setting the horn size in
   the brief" doesn't make bigger horns appear: size ambition must live in the box or the seed.
3. **The machine caps (screen 5,000 / verify 7,000 / final 8,900 dofs) and the physics guards**
   (wall thickness, self-approach, the 180° asymptote, K-law feasibility). These bind every
   typology equally and are never raised by the owner's tooling.

**So who sets the low/high per typology?** Whoever authored that typology's config, from its
reference case and dossier sizes — verified where a dossier anchors it (biradial's claim-14 range,
the QTW arc rule; S1a driver pass re-anchored five configs this way and added the one
brief-aware widening: the biradial closure rule). The S1a derivation can re-aim SEEDS under
f0-carrying briefs but deliberately never widens the box (widening is owner-gated; the biradial
closure floor is the single dated exception).

**Is the box over-constrained? Evidence and the standing directive.** The at-limit counters are
the tell: any typology whose best designs repeatedly sit at a bound is asking for a wider box.
The owner's 2026-10-25 finding (`perturbed_osse_hv @ 7040use`: L_mm 90–140 with 4/6 at-limit
under a 600 mm-depth envelope) triggered the standing directive to RECONSIDER each typology's
bounds against realistic brief envelopes (see the W8 item in NEXT_DEV_PRIORITIES). Until the
audit lands, the practical rule for the owner: if the At-limit KPI shows a non-zero count on a
size knob, ask for that bound to be widened — that is exactly the "circle back later" item, now
promoted to a priority. Widening remains an owner-gated per-config change (with the mesher-cap
check attached), never automatic.

— Written 2026-10-25 (S1a driver pass; Oracle-decided, owner-directed). Companion docs:
`docs/TYPOLOGY_BASELINE_SETTINGS_2026-10-25.md` (the per-config parameter tables),
`docs/research/typologies/R9_AUDIT_2026-10-25.md` (the naming/R9 ledger),
`docs/evidence/TYPOLOGY_SMOKE_MATRIX_2026-10-25.md` + addendum (the GPU evidence).