# Rolled-body CD wall-angle law: research dossier and construction plan (2026-11-20)

Scope: a **new wall-angle law grafted onto the existing rolled rectangular body** so the family can
hold a true constant-directivity corridor (H 60-90 deg, V 40-60 deg, 1-8 kHz) in the 600 x 480 x 480 mm
box. This is a typology/construction change, not a config edit: the parent kernel `_rolled_rect_v1.py`
is frozen and the v10 brief/objective is unchanged.

**Status:** labeled hypothesis; CPU ladder V0-V6 passed; three single-design screen solves run
(section 13); the target corridor was **not** met. The tables reuse the existing sourced dossiers
(citations in the source table); the construction itself is **[original-hypothesis]**. No published
name is attached to it. Nothing here re-verifies a source that a prior dossier already verified; see
the notes on lineage in `docs/knowledge/contracts/rolled_section_pucker.md` s2.

Owner hold note: `ROLLED_FAMILY_EVIDENCE_HANDOFF_2026-11-15.md` recorded a hold on new solves while
the brief/DI-slope question was open. That question is now settled by the shipped v10 corridor brief
(`examples/briefs/home_landscape_2026-11-18_v10/`), and the owner's 2026-11-20 request supersedes the
hold for this bounded proof-of-concept (3 single solves, not a search night).

## 1. Sources

| Source | What it gives us | Status |
|---|---|---|
| [OS-SE Waveguide paper](https://at-horns.eu/release/OS-SE%20Waveguide.pdf), via `ROLLED_FAMILY_MASTER_RESEARCH_2026-11-15.md` | r(z,phi) construction, source matching, smooth termination | primary (author) |
| [R-OSSE rev7 paper](https://at-horns.eu/release/R-OSSE%20Waveguide%20rev7.pdf), via `MESHER_TYPOLOGIES.md` s2 and `ROLLED_FAMILY_MASTER_RESEARCH_2026-11-15.md` | Separate axial/radial foldback profile; why a returned lip needs its own treatment | primary (author) |
| [Ath user guide 4.8.2](https://at-horns.eu/release/Ath-4.8.2-UserGuide.pdf), via the master research | No-shrink morph policy; rounded-rectangle dimensions; physical sampling | primary (author) |
| [Tritonia page and public script](https://at-horns.eu/tritonia.html), via the master research | alpha(p)=48.5-7cos(2p)^5-16sin(p)^12; azimuth-dependent coverage is an Ath construction | primary (author) |
| `docs/knowledge/contracts/rolled_section_pucker.md` | Exact operator order, zero controls, lineage limits of the current rolled family | code-verified contract (frozen review) |
| `docs/knowledge/typologies/experimental_morphs.md` | Radial vs axial relief are different mechanisms; visual similarity is not proof | family card |
| `docs/knowledge/typologies/osse_ath.md` | OSSE/R-OSSE scope and non-transferable CD targets | family card |
| `docs/knowledge/claims/KH-001_keele_mouth_heuristic.md` | Keele mouth sizing is a scoped biradial heuristic, not a universal gate | source-verified claim |
| `docs/research/typologies/FABLE_V2_KLANGFILM_ROLLED_2026-11-19.md` | Measured baselines and the v10 corridor rationale for the rolled lane | repo evidence (labels inside) |
| `docs/research/typologies/ROLLED_FAMILY_MASTER_RESEARCH_2026-11-15.md` | Original-hypothesis relief law; correction that axial != radial | repo research |
| `docs/research/typologies/SPIRAL_PUCKER_VS_RADIAL_RIDGE_2026-11-15.md` | Why the axial pucker bows the H/V faces; radial ridge behaviour | repo research |
| Tractrix section in `docs/research/typologies/MESHER_TYPOLOGIES.md` s1/s2 | Exponential/tractrix wall law and its length-vs-angle behaviour | repo synthesis of primaries |

Rule applied: a hybrid is never attributed to a parent beyond the parent's law. The chosen
construction below is neither Crowe, Tritonia, nor R-OSSE.

## 2. Measured baseline and the actual defect

Same v10 brief, same objective, balloon DI (`runs/.../metrics.json`):

| Design | J (v10) | H 1.07 / 2.27 / 4.26 / 8 kHz | V 1.07 / 2.27 / 4.26 / 8 kHz | dislope |
|---|---|---|---|---|
| rolled hybrid best `96790c88352e` | 9.305 | 113.4 / 93.6 / 69.3 / 50.4 deg | 130.0 / 69.8 / 56.9 / 42.8 deg | 7.32 |
| OSSE ext-throat `925868ab64d9` | 1.792 | 67.4 / 80.4 / 81.5 / 70.8 deg | 67.5 / 62.3 / 62.3 / 61.2 deg | 0.0004 |

The rolled body is **wide at 1-2 kHz and beaming at 8 kHz**, in both planes. Its wall-angle schedule
(measured from the actual grid, H meridian) reaches 45 deg at 50 % of the pre-roll arc and 90 deg at
the roll-on point; V reaches 45 deg later but the same 90 deg lip. The OSSE target sustains roughly
43 deg on H and 28 deg on V across the body and only turns over at its termination. The defect is the
**flare timing**, not the mouth size (the mouth is already 576 x 344 mm, and Keele sizing is not a
valid gate here per KH-001) and not the relief amplitude (the stored family caps at ~51-54 deg H at
8 kHz across 218 evals, i.e. the mid-body law is shared).

## 3. Mechanisms compared

| Mechanism | How it changes the wavefront | Keeps the returned lip + rect section? | Why not chosen |
|---|---|---|---|
| OSSE a(z)/a(phi) wall angle (Ath CORE/Tritonia) | Nominal coverage angle varies with azimuth in a single-valued r(z); termination morph gives the mouth | No returned lip in the parent law; R-OSSE is required for rollback | Would be a whole-body replacement, not additive |
| R-OSSE rolled profile | Separate axial/radial foldback with an explicit `t` parameter and a terminal radius | Yes, that is its purpose | Replaces the frozen v1 profile; cannot be neutral == v1 |
| Tractrix | Wall angle falls from the throat on a fixed law; length set by cutoff | Single-valued, no foldback | Different profile family; not additive |
| **Explicit H/V wall-angle schedule before the rolled return** | Keeps the v1 spiral/roll and imposes an additive, windowed angle schedule on the pre-roll meridians only | Yes, by construction: the schedule is zero at the throat and at the roll-on point | **Chosen** (minimal, additive, testable) |

### Chosen construction (LABELED HYPOTHESIS, no published name)

**Windowed flare-timing law.** The parent pre-roll meridian is parameterised by its arc fraction
`u in [0,1]`, ending at the forward (roll-on) station `f = argmax z`. A C2 window
`B(u) = S((u-a)/(b-a)) S((c-u)/(c-b))` (same quintic `S` as `_rolled_rect_v1.smoothstep`) is placed on
the body, strictly after the throat and strictly before the roll. The law prescribes a **zero-mean
wall-angle increment**

```
delta_p(u) = D_p * B'(u) / max|B'|,          p = H, V
```

so the wall relaxes through the first half of the window and steepens through the second half (for
`D < 0`), with `int delta_p ds = 0`. The surface is displaced along each row's unit normal in the
`(z, rho)` plane by the integrated offset

```
n_p(u) = D_p * L_p / max|B'| * B(u),          L_p = pre-roll arc length
```

which is **exactly zero at u<=a and at u>=c**. Consequence, by construction:

- throat tangent unchanged (`B=0` through the source region);
- roll-on point, returned lip and every station after `c` are **bit-identical** to v1;
- mouth outline, mouth plane and envelope depth unchanged;
- `D_H = D_V = 0` skips the operation entirely -> v1 geometry bit-for-bit.

The H/V split uses `w_H = cos^2 psi_f`, `w_V = sin^2 psi_f` at the roll-on station, so diagonals get
the mean and both mirror planes are preserved. `D < 0` = **back-load** (shallower body, later
flare); `D > 0` = **front-load**. This is our hypothesis; the sign/utility is what the solves test.

Why this is a wall-angle law and not a relief: the relief in `rolled_family.py` moves `rho` and `z`
after a `rho`-referenced window and does not change the local tangent systematically. Here the
quantity prescribed is the tangent angle itself, and the normal offset is its integral.

## 4. Numerical reference case (checkable)

Parent: `96790c88352e` shape (width 575.662, height 344.061, depth 228.243, depth_h_ratio 0.88277,
decay 0.79726, rect_exponent 8.8735, rect/throat/terminal 60.98/15.75/266.83 deg, inward 0.1577/1.1748,
axial -7.414/11.669). Grid 65 x 129, wall 3 mm, driver r=18 mm / 2 deg.

Law: a=0.30, b=0.60, c=0.88; `max|B'| = 6.696428571`; `D_H = -10 deg`, `D_V = -6 deg`.
Pre-roll arc lengths: H `L=302.730 mm`, V `L=282.346 mm`; mouth radii H 202.456 mm, V 131.278 mm.

| meridian | u | parent wall deg | delta deg | scheduled deg | normal offset n mm |
|---|---|---|---|---|---|
| H | 0.303 | 22.12 | -0.02 | 22.10 | 0.000 |
| H | 0.404 | 32.83 | -7.63 | 25.20 | -1.795 |
| H | 0.503 | 45.41 | -7.18 | 38.23 | -6.334 |
| H | 0.595 | 55.75 | -0.04 | 55.71 | -7.890 |
| H | 0.705 | 63.65 | +8.80 | 72.45 | -5.711 |
| H | 0.799 | 72.55 | +6.73 | 79.28 | -1.165 |
| H | 0.872 | 80.50 | +0.11 | 80.61 | -0.001 |
| V | 0.404 | 15.78 | -4.58 | 11.20 | -1.005 |
| V | 0.503 | 21.10 | -4.33 | 16.76 | -3.532 |
| V | 0.595 | 27.58 | -0.00 | 27.58 | -4.415 |
| V | 0.705 | 36.73 | +5.19 | 41.92 | -3.251 |
| V | 0.802 | 42.93 | +3.89 | 46.82 | -0.603 |

Checks to assert in the test: `n(u>=c) == 0` exactly; lip station displacement `0`; `delta` peak
`<= |D_p|`; the realized finite-difference angle change matches `delta` within one station; pre-roll
`z` strictly increasing; post-window stations `array_equal` to the neutral control.

## 5. Strengths

- Additive and versioned: neutral is an exact zero-control, so the whole existing rolled family and
  its 218 archived evals remain valid and replayable.
- Keeps the owner-approved look: rectangular section, returned lip, mouth plane, envelope.
- Directly targets the measured defect (flare timing), with independent H/V authority so the
  landscape aspect can be shaped.
- Small knob surface (5 numeric keys), easy to seed from any existing winner.

## 6. Weaknesses and limits

- **Cannot fix low-frequency under-control**: V control below ~1.5 kHz is set by mouth height
  (`Keele estimate 25,400/(0.344*50) = 1.48 kHz`; heuristic only, KH-001). A V corridor starting at
  1 kHz may stay unreachable in the 480 mm box with a 344 mm mouth. Expected honest outcome: V at
  1.07 kHz stays > 60 deg.
- The schedule is geometry, not frequency-selective: a single window trades one band against another.
  It may widen 8 kHz at the cost of 2-4 kHz, or vice versa.
- Zero-mean means the mouth point and depth are held; a sustained *different* average angle is not
  representable without changing mouth/depth. That is deliberate.
- One-parameter H/V split (`cos^2/sin^2`) cannot make a sharp petal/crease; that is a separate law.
- No acoustic evidence yet; this dossier plus one proof-of-concept solve is not a convergence claim.

## 7. Knobs and ranges

| Knob | Meaning | Seed | Range | Notes |
|---|---|---|---|---|
| `g_cd_h_deg` | H wall-angle schedule amplitude, deg | 0 | [-20, 20] | negative = back-load; 0 = neutral |
| `g_cd_v_deg` | V wall-angle schedule amplitude, deg | 0 | [-20, 20] | independent |
| `g_cd_start_s` | window start, pre-roll arc fraction | 0.30 | [0.15, 0.55] | must stay after the source region |
| `g_cd_peak_s` | window peak | 0.60 | [0.35, 0.80] | start < peak < end |
| `g_cd_end_s` | window end | 0.88 | [0.70, 0.94] | <= 0.94 so the last stations stay untouched |

Hard guards: `0 <= start < peak < end <= 0.94`; `|D| <= 20 deg`; the offset must leave pre-roll `z`
strictly increasing and must not create a radial constriction; the outermost mouth/lip stations must
be unchanged.

## 8. How practitioners measure (honest objectives)

Coverage half-angle from the -6 dB balloon cut in the H and V planes, tracked per octave, is the
industry convention (and exactly what `metrics` already records as `bw_h_deg` / `bw_v_deg`). DI slope
and DI roughness are the honest CD proxies; `dislope` is already in v10. Do **not** compare a rolled
horn's J against a different objective version, and do not treat a Keele mouth estimate as a validity
gate (KH-001). The corridor form (a range, not a point) is the right acceptance shape for a family
that naturally narrows with frequency.

## 9. Validation ladder

1. **Analytic**: window is C2; `B=0` at `u<=a` and `u>=c`; `int delta ds = 0`.
2. **Zero-control (CPU)**: `D_H=D_V=0` -> `array_equal` to the current `rolled_family.resolve_grid`
   inner and outer surfaces, and identical design hash.
3. **Schema/digest (CPU)**: new kind has its own schema + implementation SHA; a corrupted digest or
   driver is refused; the parent block still validates under the parent digest.
4. **Lip/throat (CPU)**: source tangent = 2 deg; lip station and all stations at/after `c` exactly
   equal to neutral; pre-roll `z` monotone; no constriction; `delta` peak <= `|D|`.
5. **Envelope/mesh (CPU)**: `extents <= 600 x 480 x 480`; `tools/shape_check.py` builds the seed at
   the screen cap with a round driver coupling.
6. **Proof-of-concept BEM (GPU, 3 single solves)**: control replay, candidate, sign variant. Read H/V
   at 643/1065/2268/4260/8000 Hz, DI slope, J (v10), dof/envelope. A single solve is not a search and
   not a convergence claim.
7. **If the mechanism pays**: a bounded search over the 5 knobs (not this task).

## 10. Versioned kernel + adapter plan (digest-bound, additive)

- **`hornlab_search/design/generators/_rolled_rect_cd_v1.py`** (new, versioned kernel): imports the
  frozen `_rolled_rect_v1` for `smoothstep`; exports `SCHEMA="rolled-rect-cd-v1"`, `CD_KEYS`,
  `validate_cd`, and `apply_wall_angle_law(inner_points, shape)` implementing the math above. It never
  edits or re-derives the parent surface; it post-processes the parent inner grid.
- **`hornlab_search/design/generators/rolled_cd_family.py`** (new adapter, new kind
  `rolled_family_rect_cd_v1`):
  - `implementation_digest()` hashes this adapter + the CD kernel + the **byte-identical** parent
    `rolled_family.py` + `_rolled_rect_v1.py`, so the parent lineage is pinned;
  - `resolve_grid` delegates everything to `rolled_family.resolve_grid` with the CD knobs stripped,
    then (only when `D_H` or `D_V` is nonzero) applies the kernel to the inner sheet, rebuilds the
    outer shell with `grid.grid_outer_points`, and re-runs the finite/normal/self-approach/envelope
    guards;
  - neutral `D_H=D_V=0` returns the parent result **unchanged** (no copy, no float round-trip);
  - `validate_search_config` mirrors the parent's rules and adds the CD window/amplitude rules.
- Wiring: append `rolled_cd_family` to the existing family tuples in
  `generators/grid.py`, `design/generated.py`, and `mesh/build.py`. These are one-word additive edits;
  the parent `rolled_family.py` byte content is **not** changed, so no existing saved recipe's digest
  changes.
- Seeds: `examples/typologies/rolled_cd_2026-11-20/` with control (CD neutral, exact best-design
  knobs), candidate (`g_cd_h_deg=-10`, `g_cd_v_deg=-6`), and variant (`+10`, `+6`). All use the
  unchanged v10 brief and objective.

## 11. Open risks and stop conditions

- If the control replay's J moves by more than solver noise from 9.305, the adapter is not neutral:
  stop and fix before reading the candidate.
- If the candidate exceeds the envelope or forces a dof above the screen cap: reject the seed, not
  the law.
- If both signs fail to move H/V at 8 kHz in the predicted direction, the flare-timing mechanism is
  not the lever; the next minimal change is a **terminal mouth-angle law** (a second window at
  `c..1` that changes the lip angle itself), which is a separate dossier pass.
- Two unresolved source conflicts -> `NOTES_FOR_SENIOR.md` + stop that line (rule 8).

## 12. Reading path

`docs/knowledge/README.md`; `docs/knowledge/contracts/rolled_section_pucker.md`;
`docs/knowledge/typologies/experimental_morphs.md`; `docs/knowledge/typologies/osse_ath.md`;
`docs/research/typologies/ROLLED_FAMILY_MASTER_RESEARCH_2026-11-15.md`;
`docs/research/typologies/FABLE_V2_KLANGFILM_ROLLED_2026-11-19.md`;
`docs/research/typologies/MESHER_TYPOLOGIES.md` s1-s2.

## 13. Results addendum (2026-11-20, three single-design screen solves)

| design | run id | J | H 643/1065/2268/4260/8000 | V 643/1065/2268/4260/8000 | dislope (J term) |
|---|---|---|---|---|---|
| control (neutral) | `20261120T162245Z-screen-151617` | 9.3054 | 101.4/112.9/93.6/69.3/50.4 | 138.4/114.8/69.9/56.9/42.8 | 7.322 |
| candidate (back-load -10/-6) | `20261120T162620Z-screen-5a23c5` | 11.0171 | 103.8/121.0/87.6/58.7/49.6 | 139.3/116.1/77.0/61.3/39.3 | 8.961 |
| variant (front-load +10/+6) | `20261120T162808Z-screen-accb39` | 8.3264 | 99.4/105.5/100.7/76.6/50.8 | 137.6/113.7/64.1/54.1/47.8 | 5.981 |

Reading: neutral control reproduces the stored geometry bit-for-bit and J to 3e-6; the law has real
authority. **Back-load** widened H at 1-2 kHz and V mid-band but worsened J/dislope (rejected).
**Front-load** tightened V (V 8 kHz 47.8 deg, in corridor) and lowered J to 8.326 (the useful sign),
but the corridor is still missed: H is 105.5 at 1.07 kHz, 100.7 at 2.27 kHz and 50.8 at 8 kHz; V is
113.7 at 1.07 kHz. The low band is mouth-size limited, and the H 8 kHz miss is the mechanism's limit:
the flare-timing shear cannot change the roll-on/lip angle (~90 deg) that dominates HF. Next minimal
change: a **terminal mouth-angle law** (a second window on the last ~10 % before the roll-on) under
the same additive, digest-bound pattern; do not widen this kernel's range or queue a search on this
mechanism alone. CPU: 15 focused tests passed; `shape_check` dofs 4456/4810/4769 (cap 6000), envelope
fits.

## 13. Results addendum (2026-11-20, [measured], screen tier)

CPU: `pytest tests/test_rolled_cd_geometry.py` -> 15 passed; `tools/shape_check.py` -> exit 0;
dofs 4456 / 4810 / 4769 (cap 6000); mouth 576 x 344 x 242 mm, envelope fits, round driver coupling.

GPU: one single-design screen solve per design, `HORNLAB_GPU_LOCK=refuse`, gpu-clean before and after,
baseline VRAM 713-722 MiB. v10 brief/objective unchanged; balloon DI.

| Design | run id | J (v10) | H 643/1065/2268/4260/8000 | V 643/1065/2268/4260/8000 | J-term dislope | rip |
|---|---|---|---|---|---|---|
| control (CD neutral) | `20261120T162245Z-screen-151617` | 9.3054 | 101.4/112.9/93.6/69.3/50.4 | 138.4/114.8/69.9/56.9/42.8 | 7.32 | 0.033 |
| candidate (back-load, H-10/V-6) | `20261120T162620Z-screen-5a23c5` | 11.0171 | 103.8/121.0/87.6/58.7/49.6 | 139.3/116.1/77.0/61.3/39.3 | 8.96 | 0.055 |
| variant (front-load, H+10/V+6) | `20261120T162808Z-screen-accb39` | 8.3264 | 99.4/105.5/100.7/76.6/50.8 | 137.6/113.7/64.1/54.1/47.8 | 5.98 | 0.094 |

Reference ext-throat `925868ab64d9`: J 1.792; H 67.4/80.4/81.5/62.3/70.8; V 67.5/62.3/62.3/62.3/61.2.

Reading:

- The neutral control reproduces the stored best (J to 3e-6) and the exact geometry: the adapter is
  additive.
- **Sign is identified:** back-load widens H/V mid-band and narrows V at 8 kHz (J 11.02, rejected);
  front-load tightens V and pushes V 8 kHz into the corridor (47.8 deg), giving the best J (8.326)
  and dislope (5.98).
- **Corridor not met:** H is 105.5 deg at 1.07 kHz, 100.7 at 2.27 kHz and 50.8 at 8 kHz; V is
  113.7 at 1.07 kHz and 64.1 at 2.27 kHz. The low band is mouth-size limited. The mechanism failure
  is specific: a pre-roll flare-timing shear cannot change the roll-on/lip angle (still 90 deg), so
  the 8 kHz H beam stays ~51 deg.
- **Next minimal change:** a terminal mouth-angle law (second window on the last ~10 % before the
  roll-on) or a mouth-width/termination morph; keep the additive/digest-bound pattern. Do not widen
  this kernel's range to chase H 8 kHz.

No search/campaign was queued. One solve per design; this is a proof of concept, not a convergence
claim.

## 13. Results addendum (2026-11-20, three single-design screen solves)

Status change: the CPU ladder (V0-V6) passed and three screen solves were run (one at a time, v10
brief, balloon DI). This is a proof of concept, not a search and not a convergence claim.

Commands (exact): `.venv\Scripts\python.exe -m pytest tests/test_rolled_cd_geometry.py -q -p no:cacheprovider`
-> 15 passed, exit 0; `.venv\Scripts\python.exe tools/shape_check.py examples/typologies/rolled_cd_2026-11-20/control.yaml .../candidate.yaml .../variant.yaml`
-> exit 0, dofs 4456 / 4810 / 4769 (cap 6000), envelope fits; `gpu-clean` exit 0 before and after.

| design | run | J | H 643/1065/2268/4260/8000 | V 643/1065/2268/4260/8000 | dislope (J term) | rip | load |
|---|---|---|---|---|---|---|---|
| control (neutral) | `20261120T162245Z-screen-151617` | 9.3054 | 101.4/112.9/93.6/69.3/50.4 | 138.4/114.8/69.9/56.9/42.8 | 7.322 | 0.0326 | 0.5228 |
| candidate (back-load -10/-6) | `20261120T162620Z-screen-5a23c5` | 11.0171 | 103.8/121.0/87.6/58.7/49.6 | 139.3/116.1/77.0/61.3/39.3 | 8.961 | 0.0549 | 0.4065 |
| variant (front-load +10/+6) | `20261120T162808Z-screen-accb39` | 8.3264 | 99.4/105.5/100.7/76.6/50.8 | 137.6/113.7/64.1/54.1/47.8 | 5.981 | 0.0938 | 0.6129 |

Readings:

- Neutral control reproduces the stored best geometry bit-for-bit and J to 3e-6 -> the additive claim holds
  acoustically as well as geometrically.
- **Back-load (D<0)** widened H at 1-2 kHz and V mid-band, narrowed V at 8 kHz, and worsened J/dislope
  (11.02 / 8.96): rejected.
- **Front-load (D>0)** tightened V at 1-4.3 kHz, brought V 8 kHz into 40-60 deg (47.8), lowered dislope to
  5.98 and J to 8.326: the useful sign for this body.
- The corridor is still **not met**: H 105.5 at 1.07 kHz, 100.7 at 2.27 kHz and 50.8 at 8 kHz; V 113.7 at
  1.07 kHz and 64.1 at 2.27 kHz. The low band is mouth-size limited; the H 8 kHz miss is the mechanism's
  limit, not a tuning miss.
- Mechanism conclusion: the flare-timing shear moves the mid-band but cannot change the roll-on/lip angle
  (~90 deg), which dominates H at 8 kHz. Next minimal change: a **terminal mouth-angle law** (a second
  window on the last ~10 % before the roll-on, or a controlled lip angle) under the same additive,
  digest-bound pattern. Do not widen this kernel's range; do not queue a search on this mechanism alone.


## 14. Terminal-law addendum (2026-11-20, [measured], screen tier)

Second construction for the same body: an **H-only terminal roll-onset / C-return law**
(`rolled-family-term-v1`, new kernel `_rolled_rect_terminal_v1.py`, adapter
`rolled_terminal_family.py`). It keeps the width-500 maximum (half-width 249.96 mm) and replaces the
H meridian's terminal return after the max-radius station with a C-shaped return; the V cut is
bit-identical (the azimuthal blend is a C2 smoothstep exactly zero at and beyond 40 deg from H).
Neutral `g_tm_roll_frac = 0` returns the delegated (plain or CD) result unchanged.

Knobs: `g_tm_roll_frac`, `g_tm_lip_frac`, `g_tm_max_drop_mm`, `g_tm_roll_drop_mm`,
`g_tm_lip_drop_mm`, `g_tm_lip_angle_deg`; bounds fixed in the candidate (0.88 / 0.76 / 20 / 35 / 70 /
180), validated ranges in the kernel.

H cut vs the yellow sketch: max 249.96 @ z 174.8; roll onset 219.96 @ z 159.8; lip 189.97 @ z 124.8
(width 500, depth 239.4). CPU: 12 focused tests; `shape_check` 4036 (neutral) / 5760 (candidate, epw
5.9, cap 6000).

Screen: control `20261120T165651Z-screen-6a36c3` J 9.0033 (4036 dofs), candidate
`20261120T165805Z-screen-01eebe` J 9.6015 (5760 dofs). The geometry matches the sketch, but the C is
an **acoustic reject**: ripple 0.159 vs 0.029, H 8 kHz 48.8 vs 49.2 (no HF widening), H 1.07 kHz 111
and V 1.07 kHz 138 still outside the corridor. Next minimal step: soften the C (larger bend radius /
smaller lip drop) and re-mesh at epw 6.0, or keep the C as a look-only variant and score the width-500
control. No search was queued.
