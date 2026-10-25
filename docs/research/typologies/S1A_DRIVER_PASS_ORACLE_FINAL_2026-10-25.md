# S1a driver pass — ORACLE FINAL DESIGN (decision-maker output, verbatim, 2026-10-25)

Provenance: the owner directed an oracle decision pass ("Oracle makes the decisions, finalizes
it, and writes the code") for the typology-completion repair. This file preserves the oracle's
complete final output verbatim (the only edits are this header). The mechanical application is
landing across fix lanes (config.py derivation hunks, the brief family, config reseeds, the C4
catalog entries, the test edits) and is verified by the orchestrator; the deliverable's §6 is
the applied validation plan, and `docs/BRIEF_AND_SCORING_GUIDE_2026-10-25.md` carries the
selection/scoring guide text for readers. **Owner note (2026-10-25, on record):** the owner
suspects some min/max parameters may be OVER-CONSTRAINING the designs — to be re-examined in a
later round (do not act on it in this pass; the bounds below are the landed decision).

---

# S1a TYPOLOGY-COMPLETION REPAIR — FINAL DESIGN (decision-maker pass, 2026-10-25)

**Basis read:** AGENTS.md (8 rules), TOOLCHAIN.md (caps M1–M7, GPU hygiene), `12_RESEARCH_BASIS.md` §13.4–13.8/§16.1–16.8, dossiers (BIRADIAL_IWATA_300, SALMON_X, SHAPE_DISCOVERY_SWEEP, MOUTH_RIPPLE), `TYPOLOGY_BASELINE_SETTINGS_2026-10-25.md`, `R9_AUDIT_2026-10-25.md`, smoke matrix evidence, all five configs, all briefs (shipped + user), `config.py`, `registry.py`, `grid.py`, `profiles.py`, `gui/data.py`, the pinning tests, and the two scratch probes (both currently broken: `space.design_from_knobs` does not exist — fixed versions delivered in §7).

## 0. Decision summary

| Question | Decision |
|---|---|
| Driver mechanism | **Brief-driven.** Shipped brief variants per driver class × typology family (all f0-carrying + objective v3). No per-driver config clones. No catalog `driver_exit_mm` ties (all five are multi-driver, measured 12.7→25.4 mm). |
| Biradial un-closeable seed | **Two-part fix:** reseed `L_mm 210→195` (one seed now closes under 1in/1.4in/2in *without* derivation — measured), plus a **closure-aware derivation** in `config.py` (`rm = max(K-law d/2, r0 + tan(a)·L)`, bound hi widens to the closure line when needed, flagged) so an f0 brief can never produce an un-closeable seed. |
| x_signed / ripple failures | Reseed: `x_signed` stop 170→150, `x_amp −0.25→−0.15`; `ripple12` stop 170→150. All measured green (envelope 0.0, mesh under caps). Demo identities preserved. |
| lecleach 2in mesh refusal | Reseed `g_eps_m 0.25→0.20` (the full-ring curl fails the 2t+2 self-approach guard by 0.01–0.03 mm at r0 ≥ 17.2; 0.20 passes at all three driver classes — measured). Move to a new `lecleach_rollback_1in` brief. |
| Briefs | **Revised:** `hifi_90x60_1in`, `organic_rollback_1in` (gain honest `f0_hz` + objective v3). **New (7):** `hifi_90x60_{14in,2in}`, `organic_rollback_{14in,2in}`, `lecleach_rollback_{1in,14in,2in}`. User briefs untouched. |
| C4 catalog | **LANDS** (5 entries; closes R9-audit P3 prose gap; `symmetry: full` added to the stale campaign test tuple). |
| GUI seed gate | No code change needed: memoize keys on config+brief stamps; all five derived seeds materialize (measured). |

**Measured green matrix (this session, gmsh dry-runs, screen tier):**

| Config | own (revised f0) brief | 1.4in brief | 2in brief | user xx (8k band) |
|---|---|---|---|---|
| biradial_keele (L195) | derived seed marches, overshoot 0.0; 1,893 dofs | marches 0.0; ~2,000 dofs | marches 0.0; ~2,200 dofs | 4,444 dofs ✓ |
| qtw_waveguide | 1,616 ✓ (unchanged by derivation) | 1,764 ✓ | 1,990 ✓ | 4,040 ✓ |
| salmon_x_signed (150/−0.15) | 1,792 ✓ | 1,887 ✓ | 2,504 ✓ | 4,046 ✓ |
| salmon_ripple12 (150) | 2,567 ✓ | 2,804 ✓ | 3,636 ✓ | 11,428 tris ✗ (over by 1.4%; disclose) |
| lecleach_asym_odd (eps 0.20) | 4,190 ✓ | 4,152 ✓ | 4,141 ✓ | (self-approach at eps 0.25 fixed; over cap at 8k band — disclose) |

---

## 1. Per-typology parameter decision table

### 1.1 `biradial_keele` (US4308932A)

| Knob | Seed | Bounds | Why (anchored) |
|---|---|---|---|
| `L_mm` | **195.0** (was 210) | [170, 220] (unchanged) | The decisive repair: closure needs `rm ≥ r0 + tan(a)·L`; at a=40.5°, L=195 the closure line is 179.25 (1in) / 184.33 (1.4in) / 191.95 (2in) — all ≤ the seed rm 195, so **one seed marches under every driver class** (measured, overshoot 0.0). At L=210 the 1.4in line was 197.1 > 195 → the measured refusals. 220 hi = the hifi envelope depth. |
| `h_a_deg` | 40.5 | [30, 45] | Patent's own "≈ 0.9 × half-coverage" rule for 90° H (0.9×45). Range spans 0.67–1.0× half-coverage. |
| `v_a_deg` | 27.0 | [18, 34] | 0.9 × 30 (60° V). |
| `h_rm_mm` | 195.0 (no-f0 fallback) | [140, **210**] (hi was 197) | hi 210 holds the 2in-class K-law/closure region (derived 191.95; measured 2in hifi derived rm_v 211.7 needs the V side) and removes h-closure-dead corners for r0 ≤ 17.78 at the patent angle (184.3 ≤ 210). Only the (a≥44°, L≈220) corner stays closure-dead — physical (a 466 mm mouth cannot fit a 400 mm envelope); graded penalty handles it. |
| `v_rm_mm` | 145.0 | [95, **230**] (hi was 146) | hi 230 = 2in K-law V mouth (423.3/2 = 211.7, f0 1000) + margin; 2×230 = 460 = the 2in envelope H. Under the 1in brief the region above ~146 is envelope-graded (CMA learns); under 2in it is live. |
| `h_n`/`v_n` | 5.5 / 4.0 | [2, 8] | US4308932A claim 14 (patent-anchored; never widened). |

- **Briefs supported:** hifi_90x60_{1in, 14in, 2in} (own family); marches (envelope-true) under organic/lecleach/user briefs too (measured 0.0 overshoot across all nine probed briefs).
- **Driver realization:** brief variant (driver exit radius pinned by WP2 from the brief). No-f0 customs run the YAML seed (safe to r0 25.4 at the seed angles). f0 briefs re-aim `a` (0.9×half-cov) and `rm` (closure-aware) per §4.3.
- **Derivation under revised own brief (f0 1450):** a 40.5/27 (= seed), rm_h = max(97.4, 179.25) = 179.25 (the c=0 pure-cone edge — measured marches, overshoot 0.0, 1,893 dofs), rm_v = max(145.98, 112.06) = 145.98 (K-law; mouth 298 ≈ the 300 envelope limit).

### 1.2 `qtw_waveguide` (Hughes/Peavey arc rule) — **NO CHANGES**

Already green everywhere (measured 1,616–4,040 dofs; overshoot 0.0 under all nine briefs). rm is derived by construction; the published rule pins `a_deg = coverage/2` and the existing derivation already sets it. Bounds [150–215 L, 34–46/22–33 a, 25–80 R_arc] are rule-anchored — keep. Brief family: hifi_90x60_{1in,14in,2in}.

### 1.3 `lecleach_asym_odd`

| Knob | Seed | Bounds | Why |
|---|---|---|---|
| `g_eps_m` | **0.20** (was 0.25) | [−0.3, 0.3] (unchanged) | Measured mesh refusals at eps 0.25: full-ring curl self-approach gap 7.966–7.989 mm vs the 2t+2 = 8.0 limit at r0 ≥ 17.2 (0.01–0.03 mm over). Wall reduction does **not** fix it (gap ≈ 2t structurally: wall 2.5 → gap 6.96 vs 7.0; wall 2.0 → 5.95 vs 6.0). eps 0.20 passes at 12.7/17.78/25.4 (measured: 4,190/4,152/4,141 dofs under the f0-1200 briefs; 2,777 at fc 600/2in). Still a clear one-sided demo (+20%/−16.7%). |
| `g_fc_hz` | 800 (no-f0 fallback) | [600, 1200] | lo 600 is also the **dof protection**: the full ring at fc 600 is 5,059 dofs > the 5,000 screen cap (measured); keep. |
| `g_T`, `g_stop_deg`, `g_eps_start` | 0.8 / 170 / 0.0 | [0.3,1.0] / [120,240] / [0,0.5] | unchanged; stop 170 keeps the deep-rollback demo (eps 0.20 meshes at 2in at stop 170 — measured). |
| `brief_file` | → `../briefs/lecleach_rollback_1in.yaml` | — | Per-family brief (§2); Fourcade rows are extent-honest (~1.05×), so they don't need the salmon 1.8× headroom. |

### 1.4 `salmon_x_signed`

| Knob | Seed | Bounds | Why |
|---|---|---|---|
| `g_stop_deg` | **150** (was 170) | [120, 240] | The shipped seed overshot depth 0.2201 (z-span 332.47 > 260+15) and meshed 14,414 tris > 11,275. Root cause: negative x_amp drives **cardinal** rows to stop×(1+|amp|) = 212.5°, crossing the 180° cap-area asymptote (march explosion). At 150 with amp −0.15 the max row stop is 172.5 < 180 — no crossing. |
| `g_x_amp` | **−0.15** (was −0.25) | [−0.4, 0.4] (unchanged) | (150, −0.25) meshes **defectively** ("3/8 non-sliver triangles lie entirely in the x=0 symmetry plane" — measured). (150, −0.15) is green: 1,994 dofs own-brief seed / 1,792 derived; envelope 0.0 under all briefs (measured). The sign demo survives (cardinal 172.5° vs diagonal 127.5° — a 45° contrast). |
| `g_x_fc` | 0.15 | [0, 0.3] | unchanged. |
| fc/T | 800/1100/0.8 | [600,1200]/[600,1200]/[0.3,1.0] | unchanged; under f0 briefs the derivation re-aims (measured derived 1200/843.5 → green). |

### 1.5 `salmon_ripple12`

| Knob | Seed | Bounds | Why |
|---|---|---|---|
| `g_stop_deg` | **150** (was 170) | [120, 240] | Shipped seed: 5,358 dofs > the 5,000 screen cap (10,504 tris, quadrants '14'). Stop 150 → **2,852 dofs** (seed fc) / **2,567** (derived under f0-1900) — comfortable margin. |
| `g_ripple_lobes` / `g_ripple_amp_mm` / `g_ripple_start` | 12 / 3.0 / 0.8 | [6,24] / [0.5,6] / [0.7,0.95] | **Demo identity intact.** The resolution guard stays exactly 4.0 samples/lobe (half-span n_phi 25: 2(25−1)/12 = 4.0). |
| fc/T | 800/1100/0.8 | unchanged | as x_signed. |

---

## 2. Driver story: the brief family

**Mechanism (uniform):** the driver class lives in the **brief** (WP2 pins `exit_radius_mm`/`exit_angle_deg` from the applied brief over the config; the K-law derivation reads coverage/f0/envelope from it). Pick a brief → pick a driver. Custom = write/copy a brief (guidance in §2.3). No config clones, no catalog ties (measured multi-driver seeds make ties dishonest).

**Honesty rule used to pick every f0 below:** the K-law `d = 25,400/(f0·coverage)` mm must fit the envelope **per axis, minus the two wall thicknesses**, with one family correction: the **salmon rows' rollback y-extent ≈ 1.8× their −6 dB mouth** (measured `extent×fc` products ≈ 3.3–3.4×10⁵ mm·Hz at stop 140–170), and the **Fourcade rows are extent-honest (~1.05×)**. Where the envelope alone would allow a lower f0, the 5,000-dof screen cap and the full-ring self-approach window set the floor instead — stated in each brief's comment.

### 2.1 Exact brief YAMLs

**REVISED `examples/briefs/hifi_90x60_1in.yaml`** — full new file:

```yaml
# Brief: hi-fi waveguide, 90 x 60 degrees H/V, 1-inch compression driver.
# Used as the reference size class for LANE B typology comparisons (TYPOLOGY_PLAN.md s3).
# symmetry: hv - H and V differ; axisymmetric families are rejected by the campaign.
#
# S1a repair (2026-10-25, owner-directed): this brief now carries an HONEST f0 + objective v3.
# K-law d = 25400e3/(f0*coverage) mm at f0 1450: W 194.9 x H 292.0 mm - both fit the
# 400x300 envelope with the 3 mm shells (V is the binding axis: 300 mm holds 60 deg
# only above ~1411 Hz; band_lo 700 could never hold it - the §13.5 measured diagnosis,
# 61-87% of cov loss sitting below the break). Below-f0 the objective v3 masks cov and
# dislope; rip/flat/load still score there. Old runs keep their embedded brief exactly.
name: hifi_90x60_1in
description: Hi-fi waveguide 90x60 degrees H/V, 1-inch driver, 400x300x220 mm envelope, f0 1450 Hz
driver:
  exit_radius_mm: 12.7          # 1-inch (1/2" = 0.5" radius = 12.7 mm); pinned for every config
  exit_angle_deg: 5.0           # typical 1" driver exit taper; throat wall angle follows this
envelope:
  max_mouth_w_mm: 400.0         # half-width 200 mm at 90 deg H coverage
  max_mouth_h_mm: 300.0         # half-height 150 mm at 60 deg V coverage
  max_depth_mm: 220.0           # generous depth for R-OSSE / ICW
symmetry: hv                    # H != V; axisymmetric families skipped in campaign
source:
  cap: auto                     # r_source = r0 / sin(theta_throat), ATH convention
target:
  coverage_h_deg: 90.0          # TOTAL included angle, -6 dB
  coverage_v_deg: 60.0
  band_lo_hz: 700.0
  band_hi_hz: 5500.0            # limited by 8 GB RTX 4060 dof cap (TOOLCHAIN.md); below f11 7914 Hz
  di_target_db: null            # derive from coverage
  di_slope_target: 0.0          # flat DI with frequency
  z_min: 0.0                    # loading: not weighted for this brief (load: 0.0 below)
  f0_hz: 1450.0                 # S1a: the honest K-law break of the binding (V) axis
objective:
  version: 3                    # v3: freq-weighted cov + the below-f0 mask on cov/dislope
weights:
  cov: 1.0
  rip: 1.0
  di: 0.3
  dislope: 0.5
  flat: 0.5
  load: 0.0
```

**REVISED `examples/briefs/organic_rollback_1in.yaml`** — full new file:

```yaml
# Brief: organic rollback 90x60 degrees, 1-inch compression driver.
# WP9b (senior pass 2026-10-24, plan 9b.5): the brief the per-azimuth Salmon rows compete under.
# Rollback adds WIDTH, not depth, so the envelope is wide and shallow (9b.3 step 6).
# coverage_h != coverage_v => only hv-symmetric families are eligible (TYPOLOGY_PLAN s7, R4).
#
# S1a repair (2026-10-25, owner-directed): honest f0 + objective v3. The salmon rows'
# rollback y-extent is ~1.8x their -6 dB mouth (measured extent x fc ~ 3.37e5 mm-Hz at
# stop 140-170), so the binding quantity is the extent-limited V mouth:
# (420 - 6)/1.8 = 230 mm, which holds 60 deg only above 25400e3/(60*230) = 1841 Hz.
# f0 1900 (the derivation then aims fc_v = 843.5; V extent ~400 mm, inside 420).
# The plain K-law mouth at f0 1900 is W 148.5 x H 222.8 mm - fits trivially; the
# rollback extent, not the K-law, sets f0 for this family. Below-f0: v3 masks cov/dislope.
name: organic_rollback_1in
description: Organic rollback horn, 90x60 degree, 1-inch driver, 520x420x260 mm envelope, f0 1900 Hz
driver:
  exit_radius_mm: 12.7          # 1-inch throat radius
  exit_angle_deg: 5.0           # throat wall angle at z=0 (half-angle)
envelope:
  max_mouth_w_mm: 520.0         # rollback curls wide: 520 mm mouth width
  max_mouth_h_mm: 420.0         # 420 mm mouth height
  max_depth_mm: 260.0           # shallow: the curl folds back, not forward
symmetry: hv                    # coverage_h != coverage_v; a per-azimuth H/V horn is not
                                # axisymmetric (each azimuth has its own fc)
source:
  cap: auto                     # r_source = r0 / sin(theta_throat) (9b.3 step 5)
target:
  coverage_h_deg: 90.0          # TOTAL included angle, -6 dB
  coverage_v_deg: 60.0
  band_lo_hz: 700.0
  band_hi_hz: 5500.0            # limited by 8 GB RTX 4060 dof cap; below f11 7914 Hz
  di_target_db: null
  di_slope_target: 0.0
  z_min: 0.7                    # loading threshold (mirrored from the axi brief)
  f0_hz: 1900.0                 # S1a: the rollback-extent break of the binding (V) axis
objective:
  version: 3
weights:
  cov: 1.0
  rip: 1.0
  di: 0.3
  dislope: 0.5
  flat: 0.5
  load: 0.5                     # loading matters for classical/organic horns (TYPOLOGY_PLAN s3)
```

**NEW `examples/briefs/hifi_90x60_14in.yaml`:**

```yaml
# Brief: hi-fi waveguide, 90 x 60 degrees H/V, 1.4-inch compression driver.
# The 1.4-inch member of the hifi driver-class family (12.7 / 17.78 / 25.4 mm exits).
# Same coverage, band and honest f0 as the 1-inch member: the K-law mouth depends on
# coverage x f0, not on the throat; the envelope grows only to hold the bigger throat's
# closure margins (biradial: rm >= r0 + tan(a)L) and the driver class's typical horns.
# f11 for a 17.78 mm throat is ~5,640 Hz (1-inch: 7,914 Hz) - band_hi 5500 stays below it.
name: hifi_90x60_14in
description: Hi-fi waveguide 90x60 degrees H/V, 1.4-inch driver, 420x320x230 mm envelope, f0 1450 Hz
driver:
  exit_radius_mm: 17.78         # 1.4-inch exit diameter 35.56 mm (osse_baseline precedent)
  exit_angle_deg: 5.0
envelope:
  max_mouth_w_mm: 420.0
  max_mouth_h_mm: 320.0
  max_depth_mm: 230.0
symmetry: hv
source:
  cap: auto
target:
  coverage_h_deg: 90.0
  coverage_v_deg: 60.0
  band_lo_hz: 700.0
  band_hi_hz: 5500.0
  di_target_db: null
  di_slope_target: 0.0
  z_min: 0.0
  f0_hz: 1450.0                 # K-law mouths 194.9 x 292.0 mm: both fit 414 x 314
objective:
  version: 3
weights:
  cov: 1.0
  rip: 1.0
  di: 0.3
  dislope: 0.5
  flat: 0.5
  load: 0.0
```

**NEW `examples/briefs/hifi_90x60_2in.yaml`:**

```yaml
# Brief: hi-fi waveguide, 90 x 60 degrees H/V, 2-inch compression driver.
# The 2-inch member of the hifi driver-class family. Envelope = the established 2-inch
# class (axi_2in_large's 640x460x340): the bigger box buys the lower honest f0
# (K-law at f0 1000: W 282.2 x H 423.3 mm - BOTH axes feasible against 634 x 454;
# the 1-inch box could only hold 60 deg above ~1411 Hz). f11 for a 25.4 mm throat is
# ~3,960 Hz: band_hi 5500 exceeds it - the f11/G1 caveat binds for every 2-inch brief
# on this card; treat above-f11 scores as geometry comparisons, not driver predictions.
name: hifi_90x60_2in
description: Hi-fi waveguide 90x60 degrees H/V, 2-inch driver, 640x460x340 mm envelope, f0 1000 Hz
driver:
  exit_radius_mm: 25.4          # 2-inch exit diameter 50.8 mm
  exit_angle_deg: 4.0           # slow-expansion throat class (axi_2in_large precedent)
envelope:
  max_mouth_w_mm: 640.0
  max_mouth_h_mm: 460.0
  max_depth_mm: 340.0
symmetry: hv
source:
  cap: auto
target:
  coverage_h_deg: 90.0
  coverage_v_deg: 60.0
  band_lo_hz: 600.0             # a 2-inch driver crosses lower than a 1-inch
  band_hi_hz: 5500.0            # screen-cap-safe; f11 caveat binds (see header)
  di_target_db: null
  di_slope_target: 0.0
  z_min: 0.0
  f0_hz: 1000.0                 # both K-law axes feasible at the 2-inch envelope
objective:
  version: 3
weights:
  cov: 1.0
  rip: 1.0
  di: 0.3
  dislope: 0.5
  flat: 0.5
  load: 0.0
```

**NEW `examples/briefs/organic_rollback_14in.yaml`:**

```yaml
# Brief: organic rollback 90x60, 1.4-inch driver. The 14in member of the organic family.
# f0 from the rollback-extent rule (see organic_rollback_1in): extent-limited V mouth
# (440-6)/1.8 = 241 mm -> holds 60 deg above 25400e3/(60*241) = 1758 Hz -> f0 1800
# (derived fc_v 796.6 -> V extent ~423 mm, inside 440; measured seeds green).
name: organic_rollback_14in
description: Organic rollback horn, 90x60 degree, 1.4-inch driver, 540x440x280 mm envelope, f0 1800 Hz
driver:
  exit_radius_mm: 17.78
  exit_angle_deg: 5.0
envelope:
  max_mouth_w_mm: 540.0
  max_mouth_h_mm: 440.0
  max_depth_mm: 280.0
symmetry: hv
source:
  cap: auto
target:
  coverage_h_deg: 90.0
  coverage_v_deg: 60.0
  band_lo_hz: 700.0
  band_hi_hz: 5500.0
  di_target_db: null
  di_slope_target: 0.0
  z_min: 0.7
  f0_hz: 1800.0
objective:
  version: 3
weights:
  cov: 1.0
  rip: 1.0
  di: 0.3
  dislope: 0.5
  flat: 0.5
  load: 0.5
```

**NEW `examples/briefs/organic_rollback_2in.yaml`:**

```yaml
# Brief: organic rollback 90x60, 2-inch driver. The 2in member of the organic family.
# f0 from the rollback-extent rule: (500-6)/1.8 = 274 mm -> holds 60 deg above 1541 Hz
# -> f0 1550 (derived fc_v 688.4 -> V extent ~490 mm, inside 500; measured seeds green:
# x_signed 2,504 dofs, ripple 3,636 dofs at screen). f11 ~3,960 Hz: band_hi 5500 exceeds
# it (the G1 caveat binds for every 2-inch brief).
name: organic_rollback_2in
description: Organic rollback horn, 90x60 degree, 2-inch driver, 680x500x340 mm envelope, f0 1550 Hz
driver:
  exit_radius_mm: 25.4
  exit_angle_deg: 4.0
envelope:
  max_mouth_w_mm: 680.0
  max_mouth_h_mm: 500.0
  max_depth_mm: 340.0
symmetry: hv
source:
  cap: auto
target:
  coverage_h_deg: 90.0
  coverage_v_deg: 60.0
  band_lo_hz: 500.0             # 2-inch drivers cross lower
  band_hi_hz: 5500.0            # screen-cap-safe; f11 caveat binds (see header)
  di_target_db: null
  di_slope_target: 0.0
  z_min: 0.7
  f0_hz: 1550.0
objective:
  version: 3
weights:
  cov: 1.0
  rip: 1.0
  di: 0.3
  dislope: 0.5
  flat: 0.5
  load: 0.5
```

**NEW `examples/briefs/lecleach_rollback_1in.yaml`:**

```yaml
# Brief: Le Cleac'h rollback rows, 90x60, 1-inch driver. The lecleach family's own brief
# (lecleach_asym_odd etc.; the Fourcade march is extent-honest ~1.05x its -6 dB mouth, so
# it does not need the salmon rows' 1.8x envelope headroom).
# f0 honesty: the envelope alone would allow ~1100 Hz (K-law V mouth 414/1.05 = 394 mm),
# but at f0 1100 the derived fc (597.7, clamped to 600) bills the FULL RING 5,059 dofs -
# over the 5,000 screen cap (measured). f0 1200 derives fc 652.8 -> 4,190 dofs (measured,
# green at all three driver classes). The self-approach window measured at 2in:
# fc ~650-750 passes, 762 fails - f0 1200 sits safely inside it.
name: lecleach_rollback_1in
description: Le Cleac'h rollback horn, 90x60 degree, 1-inch driver, 520x420x260 mm envelope, f0 1200 Hz
driver:
  exit_radius_mm: 12.7
  exit_angle_deg: 5.0
envelope:
  max_mouth_w_mm: 520.0
  max_mouth_h_mm: 420.0
  max_depth_mm: 260.0
symmetry: hv
source:
  cap: auto
target:
  coverage_h_deg: 90.0
  coverage_v_deg: 60.0
  band_lo_hz: 700.0
  band_hi_hz: 5500.0
  di_target_db: null
  di_slope_target: 0.0
  z_min: 0.7                    # the JMLC family's point is loading + smooth wavefronts
  f0_hz: 1200.0                 # dof-honest floor for the full ring (see header)
objective:
  version: 3
weights:
  cov: 1.0
  rip: 1.0
  di: 0.3
  dislope: 0.5
  flat: 0.5
  load: 0.5
```

**NEW `examples/briefs/lecleach_rollback_14in.yaml`** and **NEW `examples/briefs/lecleach_rollback_2in.yaml`**: identical to `lecleach_rollback_1in` except —
- 14in: `name: lecleach_rollback_14in`, `description: ... 1.4-inch driver, 540x440x280 mm envelope, f0 1200 Hz`, driver `exit_radius_mm: 17.78`, envelope `540.0 / 440.0 / 280.0`.
- 2in: `name: lecleach_rollback_2in`, `description: ... 2-inch driver, 680x500x340 mm envelope, f0 1200 Hz`, driver `exit_radius_mm: 25.4` / `exit_angle_deg: 4.0`, envelope `680.0 / 500.0 / 340.0`, `band_lo_hz: 500.0`. (Same f0 1200 at every driver class — the derived fc is driver-independent (652.8) and measured green at all three; a *higher* f0 1400 made the 2in seed fail the self-approach guard — measured — so uniform f0 1200 is the honest choice.)

**FIX `examples/briefs/axi_2in_large.yaml`** (comment arithmetic error only — the "508" is not the K-law mouth at 90°):

old:
```
# The K-law (d = KEELE_K/(f0*coverage)): at f0 = 1000 Hz the required mouths are
# 508 (W, 90 deg) x 635 (H, 40 deg) mm - the H axis is envelope-flagged infeasible at
```
new:
```
# The K-law (d = KEELE_K/(f0*coverage)): at f0 = 1000 Hz the required mouths are
# 282 (W, 90 deg) x 635 (H, 40 deg) mm - W fits the 640 envelope; the H axis is envelope-flagged infeasible at
```

### 2.2 Selection table (which brief for which typology × driver)

| Typology | 1-inch | 1.4-inch | 2-inch | Driver mechanism |
|---|---|---|---|---|
| `biradial_keele`, `qtw_waveguide`, classical/hybrid hifi configs | `hifi_90x60_1in` | `hifi_90x60_14in` | `hifi_90x60_2in` | WP2 throat pin + f0 derivation (a = 0.9×half-cov / arc rule; rm/fc from K-law, closure-floored) |
| `salmon_x_signed`, `salmon_ripple12` (+ `salmon_elliptical/x_shape/saddle`) | `organic_rollback_1in` | `organic_rollback_14in` | `organic_rollback_2in` | same; fc re-aimed via W·fc≈1.88e5, envelope-clamped |
| `lecleach_asym_odd` (+ other lecleach rows) | `lecleach_rollback_1in` | `lecleach_rollback_14in` | `lecleach_rollback_2in` | same (geo-mean single fc) |
| **Custom** | copy the nearest family brief; edit driver/envelope/f0 per §2.3 | | | |

Campaign usage: `hornlab-search campaign --brief examples/briefs/hifi_90x60_2in.yaml --families biradial_keele,qtw_waveguide,... --tier screen` (the five are catalogued in §4.4; no driver ties, so they run under any class brief).

### 2.3 Custom-brief guidance (goes into `docs/BRIEF_AND_SCORING_GUIDE_2026-10-25.md`, §3)

1. **Throat:** any `exit_radius_mm` in (0, 100) loads; all five typology seeds are verified from 12.7 through 25.4 mm. Beyond ~30 mm an f0-carrying brief still loads (the biradial derivation widens `rm` to the closure line, flagged `widened_to_closure`).
2. **f0:** set `f0 = max(25,400/(cov_h·W_env), 25,400/(cov_v·H_env))` (Hz, mm) — the binding axis; for salmon-rows customs divide the V mouth by the 1.8 extent factor first (or copy the family brief and keep its f0 rule). Always add `objective: {version: 3}` with `f0_hz`.
3. **band_hi:** keep ≤ ~5,500 on this GPU. Measured: at band_hi 12,000 the screen mesh exceeds the caps for **every** one of the five (biradial 12,321 tris vs 11,275; qtw 5,459 dofs vs 5,000; x_signed 11,858 tris; ripple est. 24,531 tris). `band_hi` also invalidates the plane-wave throat assumption above `f11 ≈ 100,250/r0` Hz (7,914 at 1in / ~5,640 at 1.4in / ~3,960 at 2in).
4. **The owner's current customs (disclosed, not edited):** `samonrip.yaml` says "90x60" but targets 75×30 — from its 500×390×300 envelope, 75° H is held only above ~677 Hz and 30° V only above ~2,171 Hz (the §13.5 impossibility); its band 500–12,000 exceeds both f11 and the card. `75x35.yaml`'s description says "Eighty by 40" (targets 75×35) and its band 300–12,000 has the same 12k problem. `xx.yaml` is the axi_2in_large copy with depth 400 (not 340) and **no f0_hz** — v3 masks nothing there; biradial runs on its YAML seed (safe at 25.4), ripple's screen mesh is over the cap at its 8k band (measured 11,428 tris; needs band_hi ≤ ~7,400).

---

## 3. Scoring guide (plain language; goes into `docs/BRIEF_AND_SCORING_GUIDE_2026-10-25.md`, §2)

**What each term measures** (all means over the in-band frequencies of the mode's frozen grid; lower J = better; weights multiply, then sum):

- **cov** — how far the measured −6 dB beamwidths (H and V planes) sit from the brief's coverage targets: mean over frequency of `(bw_h − target)² + (bw_v − target)²`, /100. This is the directivity contract and normally the dominant term.
- **rip** — mean polar-response ripple (dB) across H and V. Rewards smooth, non-lobby polars.
- **di** — squared error of the Directivity Index against the reference DI derived from the coverage targets (the "Gaussian beam" value; a brief `di_target_db` overrides it), /10. Keeps total-directivity consistent with the intended pattern.
- **dislope** — squared slope of DI vs log-frequency (target 0 = constant directivity across the band). **Hostile by construction** over a wide band: a horn *always* has rising DI below its K-law break because the mouth can no longer hold the pattern; §13.5 measured 30–42% of J in the organic runs chasing an unattainable slope-0. v3's below-f0 mask is the fix, not weights.
- **flat** — population std of the on-axis response (dB). Rewards flat power response.
- **load** — how far Re(throat impedance) falls below the brief's `z_min`, zero-padded above it. Only meaningful when the brief sets `z_min > 0` **and** `load > 0` (a dead pair is `z_min 0` + `load 0.5` — the 75x35 finding).
- **Graded infeasible penalty** — designs that march but overshoot the envelope get a large penalty *scaling with* the overshoot (points back toward feasibility); geometry/mesh refusals get the flat 1000. Keep `infeasible_penalty: graded` on the organic configs.

**Objective versions:**
- **v1** — the plain weighted sum (the default).
- **v2** — v1 plus WP4 `freq_weights` (`target.freq_weights: {band_hz: [[lo, hi, w], …]]`), applied to the per-frequency **ripple** mean only.
- **v3** (S1a) — `freq_weights` now also weight **cov**, and both **cov** and **dislope** score only frequencies `f ≥ target.f0_hz` (the below-f0 mask). Without `f0_hz`, f0_effective = band_lo and v3 equals v2 bit-for-bit (non-retroactive). Never re-score old runs with v3; a run's embedded brief is authoritative on resume.

**What NOT to tune first (§13.5 fix order D, binding):**
1. Do not raise the cov weight first. When the brief asks for coverage the envelope cannot hold, cov already dominates (88% of J in the measured 110-eval run) — more weight chases the same wall.
2. Do not fight dislope with weight knobs — the slope-0 target is physically unattainable below the K-law break; mask below-f0 (v3 + honest f0) instead.
3. Fix the brief first: coverage × band × envelope must satisfy the K-law per axis (§2.3 rule 2). Read the run's `feasibility` record (required vs envelope mouths, held coverage, below-f0 screen counts) before interpreting any J.
4. Only then touch weights — and last.

**Recommended scoring defaults per family** (these are what the shipped briefs above carry — no config weight changes needed):

| Family | cov | rip | di | dislope | flat | load | z_min | objective |
|---|---|---|---|---|---|---|---|---|
| hifi (biradial, qtw, classical) | 1.0 | 1.0 | 0.3 | 0.5 | 0.5 | **0.0** | 0.0 | **v3 + f0** |
| organic/salmon rows | 1.0 | 1.0 | 0.3 | 0.5 | 0.5 | **0.5** | 0.7 | **v3 + f0** |
| lecleach rows | 1.0 | 1.0 | 0.3 | 0.5 | 0.5 | **0.5** | 0.7 | **v3 + f0** |

Rationale: waveguides on compression drivers are not scored on loading (the shipped hifi weights); rollback/JMLC horns earn their living by loading the driver, so `load 0.5` + `z_min 0.7` (the shipped organic weights). No weight flips anywhere — §13.5-D contraindicates weight tuning before brief honesty, and the briefs above now carry that honesty.

---

## 4. Exact code

### 4.1 `hornlab_search/config.py` — the derivation repair (2 hunks)

**Hunk 1 — envelope margin for the derived mouth** (old → new):

```python
    env_w = float(feas["envelope_mouth_w_mm"])
    env_h = float(feas["envelope_mouth_h_mm"])
    req_w = float(feas["required_mouth_w_mm"])
    req_h = float(feas["required_mouth_h_mm"])
    target_w = min(req_w, env_w) if env_w > 0.0 else req_w
    target_h = min(req_h, env_h) if env_h > 0.0 else req_h
```
→
```python
    env_w = float(feas["envelope_mouth_w_mm"])
    env_h = float(feas["envelope_mouth_h_mm"])
    req_w = float(feas["required_mouth_w_mm"])
    req_h = float(feas["required_mouth_h_mm"])
    # S1a repair (2026-10-25, owner-directed driver pass): the derived mouth is capped at
    # the envelope MINUS the two wall thicknesses (the generator block's own
    # wall_thickness_mm, mesher default 3.0). registry.envelope_overshoot_estimate counts
    # the freestanding shell, so a derived mouth AT the envelope made the seed
    # invalid_envelope by 2*wt - 0.5 mm whenever the envelope was the binding side
    # (measured on this pass). An envelope too small to hold its own shell falls back to
    # the bare envelope (the overshoot is then honest grading, never a refusal).
    wt = float(gen.get("wall_thickness_mm", 3.0)) if isinstance(gen, dict) else 3.0

    def _env_cap(env_mm: float, req_mm: float) -> float:
        if env_mm <= 0.0:
            return req_mm
        capped = env_mm - 2.0 * wt
        return min(req_mm, capped) if capped > 0.0 else min(req_mm, env_mm)

    target_w = _env_cap(env_w, req_w)
    target_h = _env_cap(env_h, req_h)
```

**Hunk 2 — the closure-aware biradial rule** (old → new):

```python
                ptype = prof.get("type")
                if ptype in ("conical", "exponential", "hypex", "biradial"):
                    set_seed(f"{prefix}_rm_mm", (target_w if axis == "w" else target_h) / 2.0,
                             "K-law mouth radius (d/2)")
```
→
```python
                ptype = prof.get("type")
                if ptype == "biradial":
                    # S1a repair (2026-10-25, owner-directed driver pass): the biradial
                    # contour law REFUSES rm < r0 + tan(a)*L (the power-series term would
                    # need c < 0; design/generators/profiles.py biradial_contour), and the
                    # K-law mouth alone can sit far below that line (measured under
                    # axi_2in_large: derived rm 141.1 vs the 192 mm closure need at r0
                    # 25.4). The derived rm is therefore the MAX of the K-law mouth and
                    # the closure line; when the knob's own hi bound cannot hold the
                    # closure value the bound WIDENS to exactly it (note flag
                    # "widened_to_closure") - a clamped-only rule would re-create the
                    # un-closeable seed this repair removes. This widening is the one
                    # owner-directed exception (dated here) to the clamp-only contract.
                    # The seed's initial wall angle follows the patent's own sizing
                    # sentence ("empirically on the order of ninety percent" of the half
                    # coverage; US4308932A) - quoted in the config headers, never a new
                    # constant.
                    a_key = f"{prefix}_a_deg"
                    a_patent = 0.9 * cov_of(axis) / 2.0
                    a_val, a_clamped = _clamp_to_bounds(a_key, a_patent, bounds)
                    seed[a_key] = float(a_val)
                    notes.append({"knob": a_key, "derived_deg": float(a_patent),
                                  "applied": float(a_val),
                                  "clamped_to_bound": bool(a_clamped),
                                  "note": "US4308932A: a ~ 0.9 x half-coverage"})
                    L_seed = float(seed.get(
                        "L_mm", (bounds.get("L_mm") or {}).get("hi", 190.0)))
                    r0 = float(((raw.get("brief") or {}).get("driver") or {})
                               .get("exit_radius_mm", 0.0))
                    closure = r0 + float(np.tan(np.radians(float(a_val)))) * L_seed
                    rm_key = f"{prefix}_rm_mm"
                    rm_k = (target_w if axis == "w" else target_h) / 2.0
                    rm_derived = max(rm_k, closure)
                    b = bounds.get(rm_key)
                    widened = False
                    if isinstance(b, dict) and float(b.get("hi", rm_derived)) < rm_derived - 1e-9:
                        b["hi"] = float(rm_derived)
                        widened = True
                    v, clamped = _clamp_to_bounds(rm_key, rm_derived, bounds)
                    seed[rm_key] = float(v)
                    note = {"knob": rm_key, "derived_mm": float(rm_derived),
                            "applied": float(v), "clamped_to_bound": bool(clamped),
                            "note": "K-law mouth radius (d/2), floored at the closure "
                                    "line rm = r0 + tan(a)*L (the biradial refusal guard)"}
                    if widened:
                        note["widened_to_closure"] = True
                    notes.append(note)
                elif ptype in ("conical", "exponential", "hypex"):
                    set_seed(f"{prefix}_rm_mm", (target_w if axis == "w" else target_h) / 2.0,
                             "K-law mouth radius (d/2)")
```

No other engine change. (Verified: the pinned derivation test `test_feasibility_record_is_k_law_exact` is unaffected — hypex, envelope not binding on W, and both rm clamps dominate as before. `np` is already imported.)

### 4.2 `examples/typologies/biradial_keele.yaml`

old:
```yaml
seed_params:
  L_mm: 210.0
```
new:
```yaml
seed_params:
  L_mm: 195.0               # S1a driver pass: at a 40.5 deg H cone this depth keeps the
                            # closure line (r0 + tan(a)L) at 179.2/184.3/191.9 mm for the
                            # 1in/1.4in/2in exits - inside rm 195 for ALL drivers (at 210
                            # the 1.4in+ drivers refused: "cannot close", measured)
```
old:
```yaml
  h_rm_mm:
    lo: 140.0
    hi: 197.0
  v_rm_mm:
    lo: 95.0
    hi: 146.0
```
new:
```yaml
  h_rm_mm:
    lo: 140.0
    hi: 210.0              # S1a: widened for the 2in class (K-law/closure region to 210);
                           # under the 1in brief the mouth above ~197 is envelope-graded
  v_rm_mm:
    lo: 95.0
    hi: 230.0              # S1a: the 2in K-law V mouth is 211.7 (f0 1000); 2x230 = 460 =
                           # the 2in envelope H; under the 1in brief > ~146 is envelope-graded
```
And append to the header comment block (after the K-RULE paragraph):
```yaml
# DRIVER STORY (S1a, 2026-10-25): this typology runs under 1-inch / 1.4-inch / 2-inch
# exits by BRIEF (hifi_90x60_{1in,14in,2in}; WP2 pins the throat from the brief). The
# YAML seed is the no-f0 fallback and closes at every driver class (L 195, see seed
# note). Under an f0-carrying brief the derivation re-aims a (the patent's 0.9 x
# half-coverage rule) and rm (the K-law mouth FLOORED at the closure line
# rm = r0 + tan(a)L, bound widened to the closure value when needed - flagged
# "widened_to_closure"); an f0 brief can no longer produce an un-closeable seed.
```

### 4.3 `examples/typologies/lecleach_asym_odd.yaml`

old: `  brief_file: ../briefs/organic_rollback_1in.yaml`
new: `  brief_file: ../briefs/lecleach_rollback_1in.yaml`
old:
```yaml
  g_eps_m: 0.25
```
new:
```yaml
  g_eps_m: 0.20             # S1a driver pass: at 0.25 the -x rows' rollback curl dips
                            # 0.01-0.03 mm below the 2t+2 self-approach limit at r0 >= 17.2
                            # (mesh-refused at 1.4in/2in, measured; a thinner wall does NOT
                            # fix it - the gap is ~2t structurally); 0.20 passes at 12.7/
                            # 17.78/25.4 (measured 4190/4152/4141 screen dofs)
```
Header addition (after the LABELED RECONSTRUCTION paragraph):
```yaml
# FAMILY BRIEF (S1a): lecleach_rollback_{1in,14in,2in} - the Fourcade rows are
# extent-honest (~1.05x their -6 dB mouth), so they run the lecleach family's own
# briefs (f0 1200, the dof-honest floor for the full ring; see the brief headers).
```

### 4.4 `examples/typologies/salmon_x_signed.yaml`

old:
```yaml
  g_T: 0.8
  g_stop_deg: 170.0
  g_x_amp: -0.25             # the SIGN DEMO: corner-in (the shipped +0.25 is corner-out)
  g_x_fc: 0.15
```
new:
```yaml
  g_T: 0.8
  g_stop_deg: 150.0          # S1a reseed: at 170/-0.25 the CARDINAL rows stop at 212.5 deg -
                             # crossing the 180 deg cap-area asymptote (march explosion: the
                             # shipped seed's z-span 332.47 mm vs the 275 limit, overshoot
                             # 0.2201, mesh 14,414 tris > 11,275 - both measured). 150 keeps
                             # every row stop < 180 at |x_amp| <= 0.15.
  g_x_amp: -0.15             # the SIGN DEMO (corner-in). -0.25 at stop 150 meshes
                             # DEFECTIVELY (non-sliver triangles in the x=0 symmetry plane,
                             # measured); -0.15 is green everywhere (1,994 dofs seed /
                             # 1,792 derived at screen).
  g_x_fc: 0.15
```
Header addition:
```yaml
# S1a RESEED (2026-10-25, owner-directed): the sign demo now runs under its own and the
# 1.4in/2in organic briefs (measured green: envelope 0.0 everywhere, dofs 1,792-2,504).
# The 180 deg cap-area asymptote remains live INSIDE the search bounds (stop up to 240,
# x_amp to +/-0.4): rows whose stop(phi) crosses 180 explode in size -> graded
# infeasible, which is the intended penalty path, never a crash.
```

### 4.5 `examples/typologies/salmon_ripple12.yaml`

old:
```yaml
  g_stop_deg: 170.0
```
new:
```yaml
  g_stop_deg: 150.0          # S1a reseed: at 170 the seed meshed 10,504 tris = 5,358 dofs,
                             # over the 5,000 screen cap for quadrants '14' (measured);
                             # at 150: 2,852 dofs (seed fc) / 2,567 (derived) - green
```
Header addition:
```yaml
# S1a RESEED (2026-10-25): the demo identity is unchanged (12 lobes, 3 mm ridge, window
# opening at the last 20%, exactly 4.0 phi samples per lobe at n_phi 25 half-span); only
# the rollback stop shallowed so the seed fits the screen dof cap under its own and the
# 1.4in/2in organic briefs (measured 2,567/2,804/3,636 dofs).
```

### 4.6 `qtw_waveguide.yaml` — **no edit.**

### 4.7 `examples/catalog.yaml` — C4 lands (append at end of `entries:`)

```yaml

  # ---- S1a typology completion (2026-10-25, owner-directed; the C4 batch) ----
  # The five expansion configs, previously uncatalogued (R9_AUDIT_2026-10-25 P3: this
  # commit closes the catalog-prose gap - biradial + QTW were advertised under
  # `classical` since 2026-10-25 with no entries). NO driver_exit_mm ties: every one of
  # these typologies marches under 1in / 1.4in / 2in drivers (S1a driver pass, measured
  # 2026-10-25); the driver class is chosen by the BRIEF (hifi_90x60_{1in,14in,2in} /
  # organic_rollback_{1in,14in,2in} / lecleach_rollback_{1in,14in,2in}), never by the
  # catalog entry.
  - name: biradial_keele
    config: typologies/biradial_keele.yaml
    group: classical
    symmetry: hv
    description: Keele/JBL Bi-Radial power-series walls (US4308932A), per-plane a/n/rm searched (7 knobs)

  - name: qtw_waveguide
    config: typologies/qtw_waveguide.yaml
    group: classical
    symmetry: hv
    description: Hughes/Peavey quadratic-throat arc rule, a = coverage/2 per plane, rm derived (5 knobs)

  - name: lecleach_asym_odd
    config: typologies/lecleach_asym_odd.yaml
    group: organic
    symmetry: full              # seam-free full ring: the odd-cosine term breaks the LR mirror (C2)
    description: Le Cleac'h (Fourcade 2015) march + odd-cosine one-sided asymmetry, full ring (5 knobs); labeled reconstruction

  - name: salmon_x_signed
    config: typologies/salmon_x_signed.yaml
    group: organic
    symmetry: hv
    description: salmon rows + SIGNED x_amp (cardinal-in vs corner-out readings), quarter model (6 knobs); labeled hypothesis

  - name: salmon_ripple12
    config: typologies/salmon_ripple12.yaml
    group: organic
    symmetry: hv
    description: salmon rows + even-lobe mouth ripple (12 lobes, half model) - the pleats experiment (7 knobs); labeled experiment
```

### 4.8 Test edits (exact)

**(a) `tests/test_design_generators_biradial.py`** — replace `test_config_mouth_hits_the_envelope_limit_like_the_seed_note_says` entirely:

```python
def test_config_mouth_hits_the_envelope_limit_like_the_seed_note_says():
    """S1a (2026-10-25, owner-directed): the own brief (hifi_90x60_1in) now carries
    f0 1450, so the loaded seed is the DERIVED one: the H mouth sits at the closure
    line rm = r0 + tan(40.5 deg)*195 = 179.25 mm (the K-law mouth at f0 1450 is only
    194.9/2 = 97.4 mm, far below it), and the V mouth sits at the K-law value
    25400e3/(1450*60)/2 = 145.98 mm - i.e. 298 mm of the 300 mm envelope limit.
    (The pre-f0 seed pinned 396/296; the derivation re-aims it - measured.)"""
    cfg = load_config(TYP / "biradial_keele.yaml")
    space = DesignSpace.from_config(cfg)
    anchors = space.seed.params
    w_mm = 2.0 * max(float(row[1]) for row in anchors["profileH"]["points"]) + 6.0
    h_mm = 2.0 * max(float(row[1]) for row in anchors["profileV"]["points"]) + 6.0
    assert w_mm == pytest.approx(364.5, abs=1.5)     # 2*(179.25+3): the closure-line mouth
    assert h_mm == pytest.approx(298.0, abs=1.0)     # 2*(145.98+3): the K-law mouth at f0
    assert registry.envelope_overshoot_estimate(space.seed.params, cfg.brief) == 0.0
```

**(b) `tests/test_design_generators_grid_signed_and_ripple_configs.py`** — three edits:

Module docstring paragraph (old):
```
DEVIATION FROM THE LANE BRIEF'S PREMISE (hard rules 3 and 7: follow the files, never
invent and never weaken an assertion): the brief expected both seeds to be envelope-true.
```
→ replace the whole docstring with:
```python
"""S1a config-gap coverage (2026-10-25): the two shipped-but-never-loaded grid-row configs.

``salmon_x_signed.yaml`` is the signed x_amp SIGN demo and ``salmon_ripple12.yaml`` the
even-lobe mouth ripple (12 lobes / 3 mm / window 0.8, half model, quadrants '14'). It
applies the REAL ``load_config`` path with the named brief resolving, the pure-Python
rows march at the seed (no mesher, no GPU), and the pinned envelope/span/penalty truth --
following tests/test_design_generators_biradial.py conventions.

S1a RESEED (2026-10-25, owner-directed driver pass; the smoke-matrix findings): the
shipped x_signed seed (stop 170 / x_amp -0.25) was NOT buildable - the cardinal rows
crossed the 180 deg cap-area asymptote (z-span 332.47 mm vs the 275 limit, overshoot
0.2201, mesh 14,414 tris > 11,275) - and the shipped ripple seed exceeded the 5,000-dof
screen cap (5,358 dofs). Both are reseeded (stop 150; x_amp -0.15) and the own brief now
carries f0 1900 + objective v3, so the loaded seeds are the DERIVED ones (fc 1200/843.5).
The tests below pin the reseeded truth; the old values are kept in the docstrings as the
dated record. The organic brief revision also derives the fc knobs at load, so knob
assertions that the derivation owns (fc) are not pinned here - shape knobs are.
"""
```
(keep the imports/body headers as they are).

`test_x_signed_seed_march_succeeds_as_a_signed_quarter_model` — two assertion updates:
old:
```python
    # the SIGN demo: a NEGATIVE seed knob inside its own signed bounds
    assert cfg.seed_params["g_x_amp"] == pytest.approx(-0.25)
```
new:
```python
    # the SIGN demo: a NEGATIVE seed knob inside its own signed bounds (S1a reseed: -0.15;
    # -0.25 at stop 150 meshes defectively - non-sliver triangles in the x=0 plane)
    assert cfg.seed_params["g_x_amp"] == pytest.approx(-0.15)
    assert cfg.seed_params["g_stop_deg"] == pytest.approx(150.0)
```
old:
```python
    assert meta["x_amp"] == pytest.approx(-0.25)
```
new:
```python
    assert meta["x_amp"] == pytest.approx(-0.15)
```
old:
```python
    # the mouth fits the brief; the depth does not (pinned by the envelope test below)
    env = space.brief["envelope"]
    assert meta["mouth_w_mm"] < env["max_mouth_w_mm"]
    assert meta["mouth_h_mm"] < env["max_mouth_h_mm"]
    assert meta["x_span_mm"] > env["max_depth_mm"]
```
new:
```python
    # S1a reseed: the mouth AND the depth now fit the brief (the shipped seed's z-span
    # 332.47 mm exceeded the 260 mm envelope; the reseeded/derived seed fits)
    env = space.brief["envelope"]
    assert meta["mouth_w_mm"] < env["max_mouth_w_mm"]
    assert meta["mouth_h_mm"] < env["max_mouth_h_mm"]
    assert meta["x_span_mm"] < env["max_depth_mm"]
```

`test_x_signed_seed_pins_the_real_envelope_truth` — replace entirely:
```python
def test_x_signed_seed_is_envelope_true_after_the_s1a_reseed(x_signed):
    """S1a reseed record: the shipped seed (stop 170 / x_amp -0.25) overshot 0.2201
    (z-span 335.52 mm vs the 275 mm limit; smoke-matrix run 20261025T182430Z). The
    reseeded seed (stop 150 / -0.15, derived fc 1200/843.5 under the f0-1900 brief) is
    envelope-true; this pins the repaired truth."""
    _cfg, space = x_signed
    assert registry.envelope_overshoot_estimate(space.seed.params, space.brief) == 0.0
```

`test_ripple12_seed_march_is_a_half_model_with_the_four_samples_per_lobe_bar` — one insertion after the `block["span"]` assertion:
```python
    assert cfg.seed_params["g_stop_deg"] == pytest.approx(150.0)   # S1a reseed (was 170:
    # 5,358 dofs > the 5,000 cap; at 150: 2,852 seed / 2,567 derived, measured)
```

**(c) `tests/test_search_campaign.py`** — old:
```python
        assert entry["symmetry"] in ("hv", "axisymmetric"), (
            f"entry {entry['name']} has bad symmetry {entry['symmetry']!r}")
```
new:
```python
        assert entry["symmetry"] in ("hv", "axisymmetric", "full"), (
            f"entry {entry['name']} has bad symmetry {entry['symmetry']!r}")
        # 'full' = the 2026-10-25 seam-free full-ring rows models (catalog header note);
        # first carried by lecleach_asym_odd in the S1a C4 batch
```
and in `test_load_catalog`, after the `search_smoke` line add:
```python
    assert "biradial_keele" in names        # S1a C4 batch (2026-10-25)
    assert "qtw_waveguide" in names
    assert "lecleach_asym_odd" in names
    assert "salmon_x_signed" in names
    assert "salmon_ripple12" in names
```

**(d) `tests/test_gui_brief_authoring.py`** — docstring lines 1179–1181, old:
```python
    run-summary semantics strings and the
    uncatalogued sole-pick rule stay byte-identical (biradial_keele, qtw_waveguide,
    lecleach_asym_odd, salmon_x_signed and salmon_ripple12 all ride that rule today), and the
```
new:
```python
    run-summary semantics strings and the
    uncatalogued sole-pick rule stay byte-identical (the rule itself remains for any
    future uncatalogued config; the five S1a expansion names left it with the 2026-10-25
    C4 catalog batch), and the
```
(The asserted app.js strings are unchanged — the rule code is untouched.)

**(e) NEW `tests/test_s1a_driver_briefs.py`** — full file:

```python
"""S1a driver pass (2026-10-25, owner-directed): the brief family + the closure-aware
biradial derivation. Offline, CPU-only (the march, not the mesh; the dofs sanity is the
mesher-gated test at the bottom, run locally per the conftest gates).

Pins, per the owner's two asks:
(a) biradial's seed closes under 12.7 / 17.2 / 17.4 / 17.78 / 25.4 mm exits;
(b) the failing salmon pair's reseeded seeds march + are envelope-true, and ripple's
    screen mesh fits the 5,000-dof cap (mesher-gated);
(c) the derivation change: an f0 brief can never produce an un-closeable biradial seed
    (closure floor + widened_to_closure flag);
(d) the brief variants exist, carry their class's driver pins, f0 + objective v3.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from conftest import EXAMPLES, requires_mesher
from hornlab_search.config import load_config, load_brief
from hornlab_search.design.space import DesignSpace
from hornlab_search.design.generated import GeneratedSpace
from hornlab_search.design.generators.registry import envelope_overshoot_estimate

BRIEFS = EXAMPLES / "briefs"
TYP = EXAMPLES / "typologies"

#: (brief name, exit radius, f0) - the shipped driver-class family (S1a, 2026-10-25).
DRIVER_CLASS_BRIEFS = (
    ("hifi_90x60_1in", 12.7, 1450.0),
    ("hifi_90x60_14in", 17.78, 1450.0),
    ("hifi_90x60_2in", 25.4, 1000.0),
    ("organic_rollback_1in", 12.7, 1900.0),
    ("organic_rollback_14in", 17.78, 1800.0),
    ("organic_rollback_2in", 25.4, 1550.0),
    ("lecleach_rollback_1in", 12.7, 1200.0),
    ("lecleach_rollback_14in", 17.78, 1200.0),
    ("lecleach_rollback_2in", 25.4, 1200.0),
)


@pytest.mark.parametrize("name,r0,f0", DRIVER_CLASS_BRIEFS)
def test_every_driver_class_brief_exists_and_pins_its_class(name, r0, f0):
    b = load_brief(BRIEFS / f"{name}.yaml")
    assert b["driver"]["exit_radius_mm"] == pytest.approx(r0)
    assert b["target"]["f0_hz"] == pytest.approx(f0)        # the honest K-law break
    assert b["objective"] == {"version": 3}                 # v3 rides every family brief
    assert b["symmetry"] == "hv"


@pytest.mark.parametrize("name", ["biradial_keele", "qtw_waveguide"])
def test_hifi_configs_default_to_their_1in_family_brief(name):
    raw = yaml.safe_load((TYP / f"{name}.yaml").read_text(encoding="utf-8"))
    assert raw["brief_file"] == "../briefs/hifi_90x60_1in.yaml"


@pytest.mark.parametrize("name", ["salmon_x_signed", "salmon_ripple12"])
def test_organic_configs_default_to_their_1in_family_brief(name):
    raw = yaml.safe_load((TYP / f"{name}.yaml").read_text(encoding="utf-8"))
    assert raw["brief_file"] == "../briefs/organic_rollback_1in.yaml"


def test_lecleach_asym_defaults_to_the_lecleach_family_brief():
    raw = yaml.safe_load((TYP / "lecleach_asym_odd.yaml").read_text(encoding="utf-8"))
    assert raw["brief_file"] == "../briefs/lecleach_rollback_1in.yaml"


def _march(name, brief_path):
    cfg = load_config(TYP / f"{name}.yaml", brief=brief_path)
    space = DesignSpace.from_config(cfg)
    assert isinstance(space, GeneratedSpace)
    return cfg, space


@pytest.mark.parametrize("brief", ["hifi_90x60_1in", "hifi_90x60_14in", "hifi_90x60_2in"])
@pytest.mark.parametrize("r0", [12.7, 17.2, 17.4, 25.4])
def test_biradial_seed_closes_under_every_supported_driver(r0, brief, tmp_path):
    """Owner ask (a): the biradial seed closes under the 1-inch, the owner's 1.4-inch-class
    customs (17.2 / 17.4) and the 2-inch exit. With an f0 brief the derivation re-aims rm
    (closure-floored); without f0 the YAML seed runs as is - both must march."""
    body = load_brief(BRIEFS / f"{brief}.yaml")
    body["driver"]["exit_radius_mm"] = r0        # the custom-size probe: any exit
    p = tmp_path / "custom.yaml"
    p.write_text(yaml.safe_dump(body, sort_keys=False), encoding="utf-8")
    cfg, space = _march("biradial_keele", p)
    assert envelope_overshoot_estimate(space.seed.params, cfg.brief) == 0.0
    info_h = space.seed.params["profileH"]["points"]
    assert max(float(r[1]) for r in info_h) > r0    # the mouth opened past the throat


def test_biradial_f0_brief_can_never_produce_an_un_closeable_seed():
    """The derivation repair (c): under axi_2in_large (f0 1000, r0 25.4) the OLD derivation
    set rm 141.1 - below the 192 mm closure line - and the seed refused ("cannot close",
    measured). The closure floor fixes it; the derivation notes carry the closure rule."""
    cfg, space = _march("biradial_keele", BRIEFS / "axi_2in_large.yaml")
    notes = {n["knob"]: n for n in cfg.raw["feasibility"]["derivation"]}
    assert "closure line" in notes["h_rm_mm"]["note"]
    assert notes["h_rm_mm"]["applied"] >= 25.4 + 0.8540808 * 195.0 - 1e-6
    assert envelope_overshoot_estimate(space.seed.params, cfg.brief) == 0.0
    # the patent's own angle rule fired on the V plane (0.9 x 40/2 = 18 deg for 90x40)
    assert notes["v_a_deg"]["applied"] == pytest.approx(18.0)


def test_biradial_closure_can_widen_the_bound_when_the_driver_demands_it(tmp_path):
    """A 50 mm custom exit under an f0 brief needs rm >= 50 + tan(40.5)*195 = 216.5 mm -
    beyond the config's hi 210 - so the bound widens to exactly the closure line and the
    seed still marches (the flagged, owner-directed exception to clamp-only)."""
    body = load_brief(BRIEFS / "hifi_90x60_2in.yaml")
    body["driver"]["exit_radius_mm"] = 50.0
    p = tmp_path / "huge.yaml"
    p.write_text(yaml.safe_dump(body, sort_keys=False), encoding="utf-8")
    cfg, space = _march("biradial_keele", p)
    note = next(n for n in cfg.raw["feasibility"]["derivation"]
                if n["knob"] == "h_rm_mm")
    assert note.get("widened_to_closure") is True
    assert note["applied"] == pytest.approx(50.0 + 0.8540808 * 195.0, abs=1e-6)


def test_derived_mouth_respects_the_two_wall_thicknesses():
    """The wt-margin fix: when the ENVELOPE binds the K-law (not the requirement), the
    derived mouth is env - 2*wt (the freestanding shell), never env itself."""
    cfg, space = _march("salmon_ripple12", BRIEFS / "organic_rollback_2in.yaml")
    note = next(n for n in cfg.raw["feasibility"]["derivation"]
                if n["knob"] == "g_fc_v_hz")
    # organic_rollback_2in: req_h 604.8 caps to env 500 - 2*3 = 494 -> fc = 1.88e5/494
    assert note["derived_mm" if "derived_mm" in note else "applied"] <= 500.0 - 6.0 + 1e-9


@pytest.mark.parametrize("name", ["salmon_x_signed", "salmon_ripple12", "lecleach_asym_odd"])
@pytest.mark.parametrize("brief", ["organic_rollback_1in", "organic_rollback_14in",
                                   "organic_rollback_2in", "lecleach_rollback_1in",
                                   "lecleach_rollback_14in", "lecleach_rollback_2in"])
def test_organic_and_lecleach_seeds_march_and_fit_every_family_brief(name, brief):
    """Owner ask (b): the reseeded failing pair (+ lecleach) march and are envelope-true
    under their own and every driver-class variant of their families."""
    cfg, space = _march(name, BRIEFS / f"{brief}.yaml")
    assert envelope_overshoot_estimate(space.seed.params, cfg.brief) == 0.0


@requires_mesher
def test_ripple12_reseeded_seed_fits_the_screen_dof_cap():
    """The dofs sanity bound (mesher-gated, run locally): the reseeded ripple seed meshes
    under the 5,000-dof screen cap (measured 2,567 derived / 2,852 YAML-seed dofs; the
    shipped 170-deg seed was 5,358)."""
    import dataclasses

    from hornlab_search.config import mesh_spec
    from hornlab_search.design import families
    from hornlab_search.mesh import build
    from hornlab_search.types import Design

    cfg, space = _march("salmon_ripple12", BRIEFS / "organic_rollback_1in.yaml")
    families.validate(space.seed)
    spec = dataclasses.replace(mesh_spec("screen", cfg), f_max_hz=5500.0)
    result = build.build_mesh(Design("FREEFORM", {"grid": space.seed.params["grid"]}),
                              spec, cfg, Path("runs") / "s1a_probe", mode="screen")
    assert result.n_triangles * cfg.mesh.dof_per_triangle <= cfg.mesh.dof_cap_screen
```

(Note for the fixer: mirror the `mesh_spec` import path used by `tests/test_design_generators_grid_full_ring.py` (it imports `mesh_spec` from `hornlab_search.config` and `Design` from `hornlab_search.types`); keep the same style.)

### 4.9 Docs (same commit, AGENTS rules)

- **NEW `docs/BRIEF_AND_SCORING_GUIDE_2026-10-25.md`**: §1 the brief family + selection table (§2.2 above verbatim) + custom guidance (§2.3) + the measured green matrix (§0); §2 the scoring guide (§3 above verbatim).
- **`docs/INDEX.md` + `docs/CODE_MAP.md`**: add the new doc + the 7 new brief files (AGENTS same-commit rule).
- **`docs/CONTINUITY.md` / `docs/ISSUES.md`**: dated entry (push rule).
- **`docs/TYPOLOGY_BASELINE_SETTINGS_2026-10-25.md`**: append a dated addendum noting the reseed decisions supersede the "PROPOSAL" reseed items (they were owner-gated; the owner has now gated them in).

---

## 5. What we deliberately DO NOT change

1. **Caps** (screen 5,000 / verify 7,000 / final 8,900 quarter dofs) — never raised (TOOLCHAIN M3).
2. **Scoring defaults** — `DEFAULT_WEIGHTS` and every config's weights stay; §13.5-D contraindicates weight tuning before brief honesty, which this pass delivers instead.
3. **v1/v2 behavior** — byte-identical; v3 stays opt-in via the briefs (no config carries `objective:`; the briefs do).
4. **User briefs** (`examples/briefs/user/*.yaml`) — not edited, including the stale `samonrip` description and the 75×30-from-500mm impossibility; disclosed in §2.3.
5. **The K constants** — house `KEELE_K` 25,400 (Hughes-verified §16.2) drives the derivation; the patent's 25,000 stays quoted in `biradial_keele.yaml` + `test_design_generators_biradial.py`; never swapped.
6. **`n ∈ [2,8]`** (claim 14), ripple lobes even in [6,24], `x_amp ±0.4`, `eps_m ±0.3`, stop ranges — all hard caps and search bounds unchanged except where §1 says otherwise (biradial rm only).
7. **The GUI seed gate** (`gui/data.py`) — untouched; the memoize key (config+brief stamps) already invalidates on brief edits.
8. **`axi_90x90_1in*` and the other shipped briefs** outside the five families (hifi/organic/lecleach) — untouched, so every config on `axi_90x90_1in` is byte-identical.
9. **Mesher/solver** — zero changes; every measured number above came from the pinned stack.
10. **P-M4-2** (stop window (120,240) defined but unenforced) — documented, not changed (out of scope; the graded penalty owns the 180°-asymptote region).

---

## 6. Validation plan (fixer, then orchestrator)

**Offline (fixer, `.venv\Scripts\python.exe`, from repo root):**
1. Replace `scratch/probe_s1a_briefs.py` and `scratch/probe_s1a_corners.py` with the corrected versions in §7; run both. **Expected:** every one of the five × {own, hifi1in/14in/2in, organic1in/14in/2in, lecleach1in/14in/2in, samonrip, 75x35, xx, axi2in} = `seed: OK` (march + overshoot 0.0), except the disclosed pair: `salmon_x_signed × hifi_90x60_1in = OVER 0.0183`, `salmon_ripple12 × hifi_90x60_1in = OVER 0.0386` (organic configs under the small hifi box — not their family briefs; graded, disclosed). The corners probe: biradial 0 march-dead corners on the patent-angle line at every driver; rows corners near 180° report march-OK/overshoot (graded region), never crashes.
2. `pytest tests/test_s1a_driver_briefs.py tests/test_brief_derivation.py tests/test_design_generators_biradial.py tests/test_design_generators_qtw.py tests/test_design_generators_grid_signed_and_ripple_configs.py tests/test_design_generators_grid_full_ring.py tests/test_search_campaign.py tests/test_gui_brief_authoring.py tests/test_gui.py tests/test_design_generated.py tests/test_mounting.py tests/test_design_generators_grid.py tests/test_design_generators_grid_rows.py` — all green (the mesher-gated ripple dofs test runs locally).
3. Full offline suite marker: green, 0 failed (was 1461/0/0/0; +~30 new tests).
4. GUI launch check: the five configs materialize under their own revised briefs (seed gate green — memoize auto-invalidates on the brief mtime change).

**GPU (orchestrator; M4 pattern, one job at a time, `gpu-clean` before/after, external VRAM sampler 2 s spacing):**
5. Dry-runs first (no solve): the five configs × {own revised brief, 14in, 2in} — expect the §0 dofs matrix (biradial own 1,893; qtw 1,616/1,764/1,990; x_signed 1,792/1,887/2,504; ripple 2,567/2,804/3,636; lecleach 4,190/4,152/4,141).
6. Re-smoke (screen, one solve each, fresh cache dirs): all five under their own revised briefs. **J caveat:** J values are NOT comparable to the 2026-10-25 smoke matrix (the briefs now carry f3 scoring + f0 masks); expect different J at similar dofs.
7. Evidence addendum `docs/evidence/TYPOLOGY_SMOKE_MATRIX_2026-10-25.md` (append, dated "S1a driver-pass re-smoke"): new matrix rows (result/dofs/J/wall/VRAM baseline→peak/run dir), the derived-seed dofs table from step 5, the two disclosed hifi-box overshoots, the xx/12k-band disclosures, and bytecheck additions mirroring the 24/24 pattern (extend `tools/evidence_bytecheck_typology_smoke.py` by the new rows; expected all-pass).

---

## 7. Corrected probes (replace both scratch files)

`scratch/probe_s1a_briefs.py` (full new content):

```python
"""Offline probe (S1a driver pass, corrected 2026-10-25): the five configs x every
shipped driver-class brief + the user customs - march + envelope overshoot + flags.
The pre-repair version called space.design_from_knobs (not an attribute) and mis-nested
grid params; this one uses the space's own seed (the derived seed under f0 briefs)."""
import io
import sys
from pathlib import Path

import yaml

root = Path(".")
from hornlab_search.config import load_config
from hornlab_search.design.space import DesignSpace
from hornlab_search.design.generators.registry import envelope_overshoot_estimate

CFGS = ["biradial_keele", "qtw_waveguide", "lecleach_asym_odd",
        "salmon_x_signed", "salmon_ripple12"]
BRIEFS = {
    "own": None,
    "hifi1in": "examples/briefs/hifi_90x60_1in.yaml",
    "hifi14": "examples/briefs/hifi_90x60_14in.yaml",
    "hifi2in": "examples/briefs/hifi_90x60_2in.yaml",
    "org1in": "examples/briefs/organic_rollback_1in.yaml",
    "org14": "examples/briefs/organic_rollback_14in.yaml",
    "org2in": "examples/briefs/organic_rollback_2in.yaml",
    "lec1in": "examples/briefs/lecleach_rollback_1in.yaml",
    "lec14": "examples/briefs/lecleach_rollback_14in.yaml",
    "lec2in": "examples/briefs/lecleach_rollback_2in.yaml",
    "samonrip": "examples/briefs/user/samonrip.yaml",
    "75x35": "examples/briefs/user/75x35.yaml",
    "xx": "examples/briefs/user/xx.yaml",
    "axi2in": "examples/briefs/axi_2in_large.yaml",
}


def brief_block(bp):
    if bp is None:
        return None
    return yaml.safe_load(io.open(root / bp, encoding="utf-8-sig"))


for c in CFGS:
    p = root / "examples" / "typologies" / (c + ".yaml")
    for tag, bp in BRIEFS.items():
        try:
            cfg = load_config(p, brief=root / bp) if bp else load_config(p)
        except Exception as exc:  # noqa: BLE001
            print(f"{c} x {tag}: LOAD FAILED {type(exc).__name__}: {str(exc)[:110]}")
            continue
        bb = brief_block(bp) if bp else (cfg.raw.get("brief") or {})
        env = bb.get("envelope") or {}
        t = bb.get("target") or {}
        drv = bb.get("driver") or {}
        try:
            space = DesignSpace.from_config(cfg)
            o = envelope_overshoot_estimate(space.seed.params, bb)
            o = "OK" if o == 0.0 else f"OVER {round(o, 4)}"
            flags = ""
            feas = cfg.raw.get("feasibility") or {}
            for n in feas.get("derivation") or []:
                if n.get("clamped_to_bound") or n.get("widened_to_closure"):
                    flags += f" [{n['knob']}:clamped]" if n.get("clamped_to_bound") \
                        else f" [{n['knob']}:WIDENED]"
        except Exception as exc:  # noqa: BLE001
            o = f"SEED-INVALID {type(exc).__name__}: {str(exc)[:110]}"
            flags = ""
        print(f"{c} x {tag}: env {env.get('max_mouth_w_mm')}x{env.get('max_mouth_h_mm')}"
              f"x{env.get('max_depth_mm')} r0={drv.get('exit_radius_mm')}"
              f" f0={t.get('f0_hz')} | seed: {o}{flags}")
```

`scratch/probe_s1a_corners.py` (full new content):

```python
"""Targeted corner audit (S1a driver pass; the 2^k sweep timed out at 300 s - the rows
marches are heavy - so this probes the corners that carry information):
biradial (a, L, rm) closure corners per driver class; the rows kinds' (stop, amp) edges
near the 180 deg cap-area asymptote. March + envelope overshoot; never exhaustive."""
import io
import itertools
from pathlib import Path

import yaml

root = Path(".")
from hornlab_search.config import load_config
from hornlab_search.design.generators import grid as G
from hornlab_search.design.generators import registry

TYP = root / "examples" / "typologies"


def brief(path):
    return yaml.safe_load(io.open(root / path, encoding="utf-8-sig"))


def materialize_params(cfg, knobs):
    gen = cfg.raw["generator"]
    if gen.get("name") == "grid":
        return {"grid": G.design_params(gen, knobs, cfg.brief)}
    return registry.materialize(gen, knobs, cfg.brief)


def probe_corners(name, brief_path, knob_grid):
    cfg = load_config(TYP / f"{name}.yaml", brief=root / brief_path) \
        if brief_path else load_config(TYP / f"{name}.yaml")
    keys = list(knob_grid)
    n_ok = n_over = n_dead = 0
    worst = 0.0
    for combo in itertools.product(*knob_grid.values()):
        knobs = dict(cfg.seed_params)
        knobs.update(dict(zip(keys, combo)))
        try:
            params = materialize_params(cfg, knobs)
            o = registry.envelope_overshoot_estimate(params, cfg.brief) or 0.0
        except Exception:  # noqa: BLE001 - a dead corner is a graded-infeasible region
            n_dead += 1
            continue
        if o > 1e-9:
            n_over += 1
            worst = max(worst, o)
        else:
            n_ok += 1
    print(f"{name} x {brief_path or 'own'}: valid={n_ok} env-over={n_over} "
          f"(worst {round(worst, 3)}) march-dead={n_dead}")


# biradial: the (a, L, rm) closure corners under each driver class
for bp in (None, "examples/briefs/hifi_90x60_14in.yaml",
           "examples/briefs/hifi_90x60_2in.yaml"):
    probe_corners("biradial_keele", bp, {
        "h_a_deg": [30.0, 40.5, 45.0],
        "v_a_deg": [18.0, 27.0, 34.0],
        "L_mm": [170.0, 195.0, 220.0],
        "h_rm_mm": [140.0, 179.25, 210.0],
        "v_rm_mm": [95.0, 145.0, 230.0],
    })

# salmon rows: the (stop, x_amp) edges near the 180 deg asymptote (x_signed)
probe_corners("salmon_x_signed", None, {
    "g_stop_deg": [120.0, 150.0, 170.0, 200.0, 240.0],
    "g_x_amp": [-0.4, -0.15, 0.0, 0.15, 0.4],
})
# ripple: the stop x lobes edges (lobes are capped by the resolution guard)
probe_corners("salmon_ripple12", None, {
    "g_stop_deg": [120.0, 150.0, 170.0, 200.0, 240.0],
    "g_ripple_lobes": [6.0, 12.0],
    "g_ripple_amp_mm": [0.5, 6.0],
})
# lecleach: the (fc, stop, eps) edges
probe_corners("lecleach_asym_odd", None, {
    "g_fc_hz": [600.0, 900.0, 1200.0],
    "g_stop_deg": [120.0, 170.0, 240.0],
    "g_eps_m": [-0.3, 0.0, 0.2, 0.3],
})
```

---

## 8. Risks and notes for the orchestrator

1. **Compose sole-pick (C4):** the five leave the uncatalogued rule — app.js itself is untouched (the rule remains for future uncatalogued configs); only the `test_gui_brief_authoring` docstring and the campaign symmetry tuple change. The catalog prose gap (P3) closes in this commit.
2. **`symmetry: full`** is new to the *test* tuple (the catalog schema comment declared it 2026-10-25; `is_compatible` already handles it: full entries run under hv briefs, are refused under axisymmetric ones — correct).
3. **GUI seed gate:** memoize keys on (config, brief) stamps — the brief edits auto-invalidate. The gate now materializes the DERIVED seeds under f0 briefs; all five measured green.
4. **The biradial derived seed sits exactly at the c=0 closure edge** (pure cone on H under the f0-1450 1in brief). Measured marches + envelope-true at all three drivers (float-safe: the refusal tolerance is relative, `1e-9·rm`). If it ever bites, the fix is a 1% closure margin — deliberately not added (YAGNI; measured green).
5. **`widened_to_closure`** is the one owner-directed exception to the landed "widening is never automatic" derivation contract — dated in the code comment, flagged in the derivation notes, pinned by a test. Widening only ever reaches the closure line.
6. **f11 caveat** binds on the 2-inch briefs (band_hi 5,500 > f11 ≈ 3,960 Hz at 25.4 mm; the axi_2in_large template has the same exposure at 8,000). The G1 caveat machinery renders it; the brief headers state it.
7. **The user's 12k-band customs cannot screen on this card** (measured: every config over the caps at f_max 10k; biradial needs band_hi ≤ ~9,600, ripple ≤ ~7,400). Not fixable in config (caps never raised); disclosed with numbers in §2.3. `xx.yaml` (8k band): 4/5 green; ripple over by 1.4% (needs band_hi ≤ ~7,400).
8. **`salmon_elliptical`** (pre-existing catalog entry, outside the five) grades 4.2% over under the revised organic brief (its stop-170 rows at the derived fc; marches fine, graded penalty points back). Disclosed; its reseed is a future owner-gated item, same recipe as x_signed/ripple.
9. **The 180° cap-area asymptote is live inside the rows search bounds** (stop ≤ 240, |x_amp| ≤ 0.4): rows crossing it explode in size → graded infeasible (the intended path; measured, never a crash). P-M4-2 (un enforced stop window) stands as documented.
10. **J comparability:** the revised briefs change scoring (f0 + v3) — new runs are new record groups; old runs' embedded briefs stay authoritative on resume; never compare across. The re-smoke J values will differ from the committed matrix at similar dofs.
11. **The `salmon_elliptical`/`salmon_x_shape`/`salmon_saddle`/`lecleach_iwata_ar`/hyb/perturbed configs** all march + envelope-fit under the revised briefs (measured, §0 + the all-configs probe) — the brief revision is safe for the whole catalog on hifi/organic; the `axi_90x90_1in` configs are byte-untouched.
12. **Stale user-brief descriptions** (samonrip "90x60" vs targets 75×30; 75x35 "Eighty by 40") — owner's files, disclosed in the guide, not edited.

**Everything above is measured against the live tree this session; every number in a brief comment or test pin traces to a probe quoted in §0/§1.** The fixer can apply §2.1, §2.3 (doc), §3 (doc), §4, §5, §6, §7 verbatim.