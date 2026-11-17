# Klangfilm-Lame H/V throat audit and Phase A implementation record

**Date:** 2026-11-16 · **Repo:** `C:/Users/hunte/Hrns/hornlab-search` · **HEAD at audit time:** `3efe9be`
(a concurrent GUI/scoring lane advanced HEAD from `2c0e292` → `3efe9be` while this work was in progress;
none of its files are touched here)

**Status:** Gate 0 (evidence) complete. Gate 1 (Phase A geometry) **implemented, CPU-tested, preflighted**.
Gate 2 (Phase B CD core) **not started — gated on the Phase A acoustic A/B, per the handoff**. **No BEM/GPU
solve was run and no acoustic claim is made.** A GPU job from another lane was live during this work; it
was not disturbed.

This file is the evidence record requested by the 2026-11-16 handoff (§9.1). The machine-readable companion
is `docs/evidence/klangfilm_hv_2026-11-16/PREFLIGHT.md` / `preflight.json`, and the renders are in the same
folder. Where a screenshot value and a local record disagree, the local record wins.

---

## 1. What is actually implemented

| Item | State |
|---|---|
| Independent H/V throat wall tangents on a round 18 mm rim | implemented, `tools/geometry/klangfilm_lame_hv.py`, schema `klangfilm-lame-hv-v1` |
| Exact legacy nesting (`cd_core_blend = 0`) | bit-identical to `klangfilm_lame-v1` (tested, array hash below) |
| C²-at-the-join forward-core deformation, rollback untouched | implemented and tested |
| No-constriction / no-non-monotone-forward-radius refusal (no clamping) | implemented and tested |
| Canonical recipe adapter + registration (search/verify/preview/mesh) | implemented, digest-bound |
| Versioned report-only size policy for the new family only | implemented (`size_policy: report_only`) |
| Lamé exponent progression, rim sweep, curved-cap area lock | **unchanged from v1** by design in Phase A |
| Beak/lip, throat landing, monotonic Phase B CD core | **not implemented** (Phase B; see §8) |
| New BEM solves / polars / measured CD | **none** (no GPU work; §8 gate) |

The old files `tools/geometry/klangfilm_lame.py`, `tools/geometry/lame_cap.py`,
`hornlab_search/design/generators/{_klangfilm_lame_v1,_lame_cap_v1,klangfilm_lame_family}.py` are
**bit-unchanged**.

---

## 2. Resolved local evidence and hashes

| Fact | Value |
|---|---|
| Run | `runs/20261116T205942Z-screen-8b22b5` |
| Best design | `786caa6b08d7`, eval 27, `di_source = balloon`, `ok = true` |
| Best objective (`J`, v7 smooth policy) | **8.439049239022415** |
| Best genes | `fc_hz 494.4393461867`, `aspect 2.0759495982`, `lame_p 5.0063549541`, `end_frac 1.7953432921`, `rim_sweep_ratio 0.004898754`, `morph_frac 0.3`, `source_blend_ratio 0.0`, `entry_half_angle_deg 2.0` |
| Grid | `n_phi 19`, `n_s 64`, `wall_thickness_mm 3.0`, quarter symmetry |
| Sampled inner size | **541.27 W × 260.73 H × 233.68 D mm** (PDF said ≈541 × 261 × 234 — agrees) |
| Saved recipe digest | `e3a1f4a3182cd5405bc1a1fec469456c513a49da31d804bcae27f3a039909866` |
| `tools/geometry/klangfilm_lame.py` sha256 | `728615be…6d087e` (matches the frozen-kernel docstring) |
| `_lame_cap_v1.py` sha256 | `9f0f0609…4c9ae` (matches the frozen-kernel docstring) |
| A0 grid array sha256 (first 16) | `7e80214c3b280209` (new module zero-blend == legacy) |

**Digest drift found (recorded, not "fixed"):** `klangfilm_lame_family.implementation_digest()` now returns
`42110e4e…c79b`, not the saved `e3a1f4a3…`. All four digest source files are byte-identical to HEAD
(`git diff --quiet` clean) and the recorded kernel/cap hashes above still match. The only remaining digest
input is the runtime version string (`numpy=2.5.4;scipy=1.18.1`). So this is **environment drift bound into
the identity**, not a geometry change. Consequence: replaying that saved v1 recipe currently fails the
digest check and must be regenerated rather than trusted; mutating v1 to "fix" it would break its identity,
so it was left alone. The new family's digest additionally covers the parent kernel and the cap math.

**Screenshot vs local record:** the handoff quotes the 11007 screen at `fc 382.753` and the
`hornlab-search3.pdf` screen at `fc 494.439`. The local canonical winner is the **494.439** one. The
382.753 numbers are therefore *not* the incumbent and were not used for A0.

---

## 3. Why the old throat cannot differentiate H and V

Legacy gate (`lame_cap.quintic`, used for both `q(s)` and `p(s)`):

```text
q(s) = exp(ln(q_target) · Q(s/s_morph)),  p(s) = 2 + (p_target−2)·Q(s/s_morph),  Q(t)=10t³−15t⁴+6t⁵
Q(0)=0 and Q′(0)=0   ⇒   d(ln q)/dz |₀ = 0   ⇒   da/dz|₀ = db/dz|₀
```

Because `a=b=r0` at the throat, a zero initial derivative of `ln q` forces **equal H and V wall slopes**.
The mouth may be elongated; the entrance tangent cannot differ. Measured on the incumbent's own dense
station table:

| Quantity | Value |
|---|---|
| Raw parent half-angle (analytic, 494.439 Hz, r0 18 mm) | **9.3669°** |
| Legacy dense-table throat chord, H | **9.4631°** |
| Legacy dense-table throat chord, V | **9.4378°** |
| Difference | **0.025°** — numerical/area-solve residue, not an entrance law |
| `brief.driver.exit_angle_deg` | 2.0°, tagged `angle_provenance = assumed_legacy` (unchanged) |

So the metadata scalar `source_auto_angle_deg = 2.0` is an **assumption**, not an HF1440 fact and not a wall
tangent. The published HF1440 datasheet gives a 35.8 mm nominal throat and no numeric exit angle; nothing
here invents one.

---

## 4. Why the S / returning curves appear

Parent law: `R = c/(π f_c)`, `h0 = r0²/(R+√(R²−r0²))`, `z(h) = (R/4)ln(h/h0) − h + h0`. The axial forward
maximum is at `h = R/4`, **not** at the maximum radial width `h = R`. For the incumbent:

| Quantity | Value |
|---|---|
| `R` | 220.816 mm |
| `h0` | 0.734860 mm |
| axial turn `z(h=R/4)` | **183.962 mm** |
| `z(h=R)` | 94.88 mm |
| selected mouth station `h = 1.7953·R` | z = **−48.44 mm** (mouth plane behind the throat plane) |
| axial excursion (sampled depth) | **233.68 mm** |
| sign changes of `dz` on the dense profile | **1** (whole table) |
| sign changes of `dz` on the materialised H meridian (swept) | **1** |
| sign changes of `dz` on the materialised V meridian | **1** |
| `rim_sweep` axial setback for this seed (`ratio·a_max`) | ≈ **1.33 mm** |

So the observed S/return is **intrinsic Klangfilm rollback**, not a mesh or sweep bug: the wall keeps
growing radially while the axis has already turned, and the mouth of this winner genuinely wraps behind the
driver plane. The sweep contribution is small (≈1.3 mm) here. This is why Phase A deforms **only the
monotonic forward span** and leaves every rollback station untouched.

---

## 5. Failure accounting (local run only)

| Item | Value | Note |
|---|---|---|
| `search.ndjson` records | 30 | all `ok = true` |
| design dirs | 31 | `c83ca94a1cb2` has `mesh.msh` only — no `design.json`/`metrics.json`/`status.json` |
| `run.json` status | `running` | `best.json` final at 2026-11-16T21:14:18Z; no clean finalise record |
| Invalid-geometry count in this run | **0 recorded** | the screenshot's "15 invalid geometries" belongs to the 11007 screen, whose raw record is not in this checkout |

The 31st directory is an **incomplete/failed solve artifact**, not a recorded geometry rejection. No claim is
made about the 11007 run's 15 invalids beyond "not verifiable here".

---

## 6. Phase A geometry contract, as implemented

`tools/geometry/klangfilm_lame_hv.py` (parent imported read-only) adds, per axis `i ∈ {H,V}`:

```text
B1(t) = t(1−t)³                      B1(0)=B1(1)=0, B1′(0)=1, B1′(1)=B1″(1)=0
B2(t) = 64t³(1−t)³                   B2(0)=B2(1)=0, B2′(0)=B2′(1)=0, B2(1/2)=1
δᵢ(z) = blend·[Δmᵢ·L·B1(z/L) + gainᵢ·B2(z/L)],   Δmᵢ = tan θᵢ,target − tan θᵢ,base
rᵢ,new = rᵢ,base + δᵢ,   L = core_join_fraction · z_forward  (z_forward = 183.962 mm here)
```

Consequences, all tested:

* `δ(0)=0` ⇒ the modeled driver circle stays `r0 = 18 mm`, `p(0)=2`, aspect `q(0)=1`.
* `dδ/dz|₀ = blend·Δm` ⇒ the **first wall tangent is exactly the requested target** (verified to 1e-9 via
  the analytic model angle; the dense-table chord agrees within 0.6° because it is a finite difference over
  the first ~2.5 mm station).
* `δ, δ′, δ″ → 0` at `L` ⇒ C² recovery of the untouched v1 horn at the join; rollback stations stay
  bit-identical. A curvature jump at the *throat* is inherent to a finite tangent change on a round rim and
  is not hidden.
* Two-axis independence is structural, not approximate: changing `θ_H` leaves the V semi-axis array exactly
  equal, and vice versa.
* The curved-cap area lock (`S(h)=2πRh`, unswept spherical wavefront) is solved **first** and then deformed;
  the new meta says `area_mode = deformed_after_cap_lock`. The legacy invariant is not silently re-claimed.

**Refusal instead of clamping.** A negative `mid_gain` makes the B2 basis locally dominate the wall slope and
produces either a radius below the 18 mm throat radius or a non-monotone forward radius. Both are refused
with a `ValueError`. Concretely, the handoff's `−8 mm` V gain gives a minimum V semi-axis of **15.02 mm at
z ≈ 61.8 mm** and the `−14 mm` variant is far worse; the `−4 mm` variants still break monotonicity. This is
a real finding, not a tolerance problem: in Phase A the additive interior control can only **open** the
slow (V) axis. A genuinely tighter-but-monotone V path needs the Phase B integrated-slope representation.

---

## 7. Preflight results (Phase A)

Full table and per-frequency CD diagnostic: `docs/evidence/klangfilm_hv_2026-11-16/PREFLIGHT.md`.
Headline (all values computed, not estimated):

| seed | status | θ_H model / mesh | θ_V model / mesh | q(5 mm) | W/H/D inner (mm) | envelope |
|---|---|---|---|---|---|---|
| a0 (exact incumbent, blend 0) | accepted, **bit-exact legacy** | 9.463 / 9.770 | 9.438 / 9.408 | 1.0007 | 541.3 / 260.7 / 233.7 | OK |
| a1 (10/5) | accepted | 10.000 / 10.204 | 5.000 / 5.833 | 1.0217 | 541.3 / 260.7 / 233.7 | OK |
| a2 (14/5) | accepted | 14.000 / 13.438 | 5.000 / 5.831 | 1.0389 | 541.3 / 260.7 / 233.7 | OK |
| a3 (+18/−8 @ 0.75, as specified) | **refused** | — | — | — | — | V shrink below throat |
| a3b (+18/0 @ 0.75, feasible) | accepted | 9.000 / 10.771 | 6.000 / 6.553 | 1.0164 | 541.3 / 260.7 / 233.7 | OK |
| a4 (+8/−14 @ 0.65, as specified) | **refused** | — | — | — | — | V shrink below throat |
| a4b (+8/0 @ 0.65, feasible) | accepted | 9.000 / 10.321 | 4.000 / 5.028 | 1.0236 | 541.3 / 260.7 / 233.7 | OK |
| a5 (different parent, 11/6, +12/+6) | accepted, **OVER ENVELOPE** | 11.000 / 11.215 | 6.000 / 6.558 | 1.0226 | 622.6 / 377.3 / 256.0 | 622.6 > 600 (report-only) |

Notes that matter:

* A0's grid is `np.array_equal` with `klangfilm_lame-v1` (array sha256 prefix `7e80214c…`), and the **same
  A0 grid is reached regardless of the inert angle/gain values** stored in the config.
* `n_phi 19 → 37` does not move the wall field at all (analytic section, not a radial sample pattern).
  `n_s 64 → 128` halves the mesh-chord error toward the analytic model angle (e.g. a2 H 13.438 → 13.642 vs
  target 14.0; V 5.831 → 5.521 vs target 5.0). The residual is the known O(dz) chord bias, reported rather
  than tuned away.
* `q(5 mm)` and `q(15 mm)` respond to the entrance keys (a1 1.0217/1.0610 → a2 1.0389/1.0984), which is the
  plan's "activity test" for `d ln q/dz ≠ 0` at the throat.
* A5's over-envelope width (622.6 mm) is **not clipped**: the config carries the family's versioned
  `size_policy: report_only`, which records `meta.envelope_violations` and keeps
  `meta.envelope_ok = false`. `report_only` is refused for any searched knob, so it cannot be used to
  optimise past the manufacturing envelope; a real enlarged-envelope study needs a widened brief.

---

## 8. Cached CD baseline and what is deliberately not claimed

The incumbent run used the **smooth** brief: `di_slope_target = +5 dB/decade`, `weights.di = 0`,
`cov` tolerance 8°, `cov_v_weight 0.5`. Its `J = 8.439` is therefore **not a CD score** and is not
comparable to any CD-scored number. From the cached `metrics.json` (no new solve), a named diagnostic with an
explicit policy (`F_CD = 1200–5600 Hz`, τ = 8°, `J = mean(e_H²)+mean(e_V²)+Var(DI)`, population variance):

| Quantity | Value |
|---|---|
| `J_CD_cached` | **17.589** |
| mean `e_H²` / mean `e_V²` | 2.442 / 12.987 |
| Var(DI) over the band | 2.160 dB² |
| DI mean / range | 11.643 dB / 4.536 dB |
| BW_H at 1.37 / 3.31 / 4.83 kHz | 84.5° / 62.8° / 66.6° |
| BW_V at 1.37 / 3.31 / 4.83 kHz | 110.5° / 62.6° / 51.6° |
| DI slope (cached scalar) | 8.41 dB/decade (target 5) |

The V term dominates: the vertical pattern collapses from ~110° to ~52° across the band, and DI rises
4.5 dB — the opposite of constant directivity. That is the defect the H/V core is meant to attack, and it is
also why lowering the smooth `J` is not evidence of success.

**Not claimed:** 80°×50° CD; that `θ_H = 40°`/`θ_V = 25°` at the flange; that the mouth aspect equals
`tan40°/tan25°`; that a raw 2° metadata scalar is a manufacturer exit angle; that any Phase A shape sounds
better. No polars, no DI, no loading were measured for A1–A5.

**Gate 2 (Phase B) remains conditional**, as the handoff requires: build the monotonic integrated-slope CD
core (θᵢ(z) = θᵢ₀ + (θᵢ₁−θᵢ₀)Q(z/L_c), rᵢ = r0 + ∫tan θᵢ), a separate shoulder/rollback/beak terminator,
and an OS-SE/R-OSSE comparator with the same Lamé/beak terminator — **only if** the Phase A acoustic A/B
shows insufficient early H/V authority. The B1–B5 contact-sheet rows are not produced here because that
geometry does not exist yet; drawing them would be fiction.

---

## 9. Verification run for this change

```powershell
.venv\Scripts\python.exe -m pytest tests/test_tools_klangfilm_lame_hv.py `
  tests/test_klangfilm_lame_hv_family.py tests/test_klangfilm_hv_dispatch.py `
  tests/test_klangfilm_lame_family.py tests/test_dual_lame_dispatch.py `
  tests/test_tools_klangfilm_lame.py tests/test_lame_sections.py -q -p no:cacheprovider
```

Result: 71 passed, exit 0 (0 failed, 0 skipped). The new kernel tests cover: exact legacy parity, the pure
`cd_hv_delta` C1/C2/linearity/out-of-interval-zero properties, per-axis independence, mid-gain interior
locality, constriction refusal (including the `−4 mm` case), monotone forward branch + untouched rollback,
Lamé `p` unchanged, `n_phi`/`n_s` convergence, determinism, validation refusals, and that the driver
`exit_angle_deg` is **not** used as a wall tangent. The family tests cover recipe bind/replay, digest
sensitivity to the parent kernel and the cap math, both dormancy guards, and the report-only size policy.

Config-level end-to-end (`load_config → GeneratedSpace → grid.rows_grid_points → knobs_for` replay) verified
for a0, a1 and a5.

---

## 10. Sources

Primary literature was taken from the handoff's citation list and is **not** restated as measured fact here:
Keele (AES 1038, 1975); Kolbrek, *Horn Theory: An Introduction* (2008); Ahlswede/drba spherical-wave
elliptical calculator and the 2019 Lamé rollback thread (DIY, non-commercial); Batík, *R-OSSE Acoustic
Waveguide* (2022); Gu/You/Shen JASA 158:1962–1975 (2025); Udawalpola & Berggren (2007); COMSOL horn-shape
optimisation model; Makarski & Behler AES 6097/6188; FaitalPRO HF1440 datasheet; BoTorch TuRBO and
multi-objective docs. The H/V deformation basis, the report-only size policy and the CD diagnostic are
**ours**, not published formulas, and still require BEM validation.
