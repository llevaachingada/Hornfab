# Stage A vs Phase B — compact comparison and recommendation (2026-11-17)

**Question.** Does the Phase A throat-only H/V core have enough acoustic authority to justify optimizing
four knobs, or does the family need the Phase B monotone core?

**Answer (measured, not predicted).** No: the throat-only offsets move the −6 dB pattern by at most
2.74° (and that in the wrong direction), score worse under both scoring policies, and leave the
frequency-dependent narrowing untouched. **Phase B is warranted.** No constant-directivity claim is made
for either stage.

---

## 1. What was actually run

Three BEM arms, one angle key apart, sharing the canonical genes, brief, mesh policy, source cap,
solver and 18-frequency grid. Executed from a **pinned HEAD snapshot** because the live working tree was
temporarily inconsistent (another lane was mid-way through the objective-v9 dispatch table); runs,
cache and dataset still live in this checkout, and no other lane's files were modified.

| arm | intent | run | design | config (sha256 prefix) | dofs | tris | solve |
|---|---|---|---|---|---|---|---|
| A0 | incumbent (blend 0, bit-identical to `klangfilm-lame-v1`) | `20261117T015442Z-screen-0afda0` | `a01be912716b` | `a0.yaml` `670aa89515987e8d` | 7449 | 14542 | 52.8 s |
| A1 | **H only**: θ_H 9.4631 → 14.0°, θ_V pinned at its measured base 9.4378° | `20261117T015600Z-screen-de1861` | `e40b381aa08a` | `a1_h_only_single_axis.yaml` `09218270259376bc` | 7435 | 14514 | 48.7 s |
| A2 | **V only**: θ_V 9.4378 → 5.0°, θ_H pinned at its measured base 9.4631° | `20261117T015658Z-screen-7ffaad` | `b6a2c90ee34d` | `a2_v_only_single_axis.yaml` `7070ce7584157b73` | 7464 | 14572 | 49.9 s |

Geometry equality for A0 was asserted (`np.array_equal` against the v1 kernel), and every mesh/solve/
target/weights/objective/grid block matched the cached incumbent. A0 was re-solved anyway because the
repo SHA differs from the cached run's (`reuse_a0 = false`); the re-solve reproduced the cached score to
0.011 % (8.4381 vs 8.4390), which is the reproducibility check for this comparison.

**Method gate found and fixed.** Replaying a stored response reproduces the stored J **exactly only**
through `brief_from_config` (parity 0.0). Passing the brief YAML directly drops the resolved target
(`driver_exit_radius_mm`, `diag_reference`) and produced 7.131 instead of 8.439 — a 1.3-point error that
would have silently invalidated every policy comparison. The report tool now resolves both policies
through `brief_from_config`.

## 2. Physical results

Full tables, per-frequency arrays and plots: [`AB_REPORT.md`](AB_REPORT.md),
[`ab_report.json`](ab_report.json), [`ab_plots/`](ab_plots/).

### 2.1 Axis authority (mean −6 dB beamwidth change vs A0)

| arm | band | ΔBW_H | ΔBW_V | max │ΔBW_H│ | max │ΔBW_V│ |
|---|---|---|---|---|---|---|
| A1 H-only | 700–1200 Hz | −0.0° | −0.0° | 0.0° | 0.0° |
| A1 H-only | 1.2–5.6 kHz | **−0.38°** | +0.00° | 1.8° | 0.0° |
| A1 H-only | 5.6–8 kHz | **−2.74°** | +0.36° | 4.0° | 0.8° |
| A2 V-only | 700–1200 Hz | +0.0° | +0.0° | 0.0° | 0.0° |
| A2 V-only | 1.2–5.6 kHz | −0.03° | **−0.00°** | 0.7° | 0.0° |
| A2 V-only | 5.6–8 kHz | −0.71° | **−0.25°** | 1.2° | 0.2° |

* The **intended** axis moves by ≤ 2.74°; the **cross axis** leaks ≤ 0.71°.
* Where the H axis does move it **narrows** at high frequency — the opposite of the 80°×50° target,
  which needs the pattern held *wider* up to 5.6 kHz.
* **A2 (V) is acoustically inert**: −4.44° of wall angle bought 0.00° of vertical beamwidth in the
  primary band.
* No new −6 dB lobes in any arm (0 multi-lobe bins); cut-limit saturation is unchanged (3 H bins, 5 V
  bins, i.e. the low-frequency bins are still ≥180° wide at the sampled limit).
* The 700–1200 Hz band contains only 2 stored bins (828 Hz, 1065 Hz) and both arms sit at the cut
  limit there, so that band cannot show authority at this fidelity.

### 2.2 Scores, each policy separately (same stored responses)

| policy | A0 | A1 | Δ | A2 | Δ |
|---|---|---|---|---|---|
| smooth (`v7_smooth`, slope +5 dB/dec, no DI weight) | 8.438 | 8.694 | **+0.256** | 8.567 | **+0.129** |
| base CD (`v7`, slope 0, DI weight 0.3, tighter coverage) | 14.208 | 14.548 | **+0.340** | 14.335 | **+0.127** |

Both policies agree: the arms are **worse**. Term-level detail shows why — `cov`, `diag` and `dislope`
all worsen; nothing improves enough to offset them. J is comparable only within a policy; the two
columns are not comparable to each other.

### 2.3 Loading and smoothness

Throat impedance magnitude stays in 0.9-1.0 (|Z|/ρc) in every band, `load` moves only 0.777 → 0.770 / 0.787,
and ripple stays 0.043–0.047 (smooth) — the throat offsets neither helped nor hurt loading. Off-axis
wobble is essentially unchanged (A0 0.98/0.78/0.98 dB per step vs A1 0.96/0.74/0.96).

## 3. Why Stage A cannot work (mechanism)

The Phase A basis adds a bounded radial offset (≤ ~1 mm here) that decays to zero at the join
(z ≈ 120 mm) and leaves the mouth, the rollback and the flare law untouched. A horn's pattern in the
1.2–8 kHz band is set by the aperture and the last third of the wall; a 1 mm perturbation at the throat
is a 0.2 % change of the mouth. The measured ≤2.7° response is what that predicts. Making the *throat*
anisotropic cannot make the *flare* constant-directivity.

## 4. Phase B: what was built

`tools/geometry/klangfilm_lame_hv_core.py` (schema `klangfilm-lame-hv-core-v1`,
`rows.type: klangfilm_lame_hv_core`), CPU geometry only:

```
theta_i(z) = theta_i0 + (theta_i1 - theta_i0) * Q(z / L_core),      i in {H, V}
r_i(z)     = r0 + integral_0^z tan(theta_i(u)) du
P(z, phi)  = (rho cos phi, rho sin phi, z + dz_beak(z, phi))
```

* both axes share one `z`, so every station is a real planar Lamé section;
* the flare is monotone by construction, and the axial turn is derived from the slope law;
* `p(z)` starts at 2 and follows its own late gate, so **mouth sculpting is independent of the flare**
  (changing `p` moves only diagonal/corner radius, never the H/V meridians — tested);
* a late **beak** (`−D_H cos²φ + D_V sin²φ + D_D sin²2φ`, C2 gate) gives an independently controlled swept
  lip; all three zero is an exact no-op, and a too-late/too-large setback is **refused** as a fold;
* `cd_core_blend = 0` returns the v1 grid **bit-for-bit** (tested).

Geometry preflight (CPU, no solve): [`PHASE_B_GEOMETRY.md`](PHASE_B_GEOMETRY.md),
[`phase_b_geometry.json`](phase_b_geometry.json), [`phase_b_sections.png`](phase_b_sections.png),
[`phase_b_laws.png`](phase_b_laws.png).

| seed | θ_H | θ_V | L mm | p mouth | area throat→mouth | W/H/D mm | turns | lip clear | envelope | grid sha256 |
|---|---|---|---|---|---|---|---|---|---|---|
| A0 (control) | 9.46 (parent) | 9.44 (parent) | – | 5.01 | 1018 → 48471 mm² † | 541/261/234 | 1 | – | OK | `7e80214c…` |
| B1 balanced | 8 → 48° | 5 → 24.5° | 380 | 4.0 | 1018 → 106551 mm² | 480/240/380 | 0 | 19.5 mm | OK | `416efc4b…` |
| B2 wide | 12 → 50.5° | 4 → 22° | 420 | 4.8 | 1018 → 131118 mm² | 595/233/420 | 0 | 19.5 mm | OK | `70cbde3d…` |
| B3 soft | 7 → 52.1° | 6 → 30.4° | 340 | 3.0 | 1018 → 111077 mm² | 473/266/345 | 0 | 19.6 mm | OK | `993aef1c…` |

† The area column is the **mouth-station** flat Lamé area. A0's mouth sits on its intrinsic rollback,
where the parent's section has already shrunk, so this is not a peak-area comparison.

12 focused tests pin the construction (`tests/test_tools_klangfilm_lame_hv_core.py`).

### 4.1 What Phase B does **not** have yet

* **No solve.** There is no BEM, polar, DI or loading result for any B seed, so nothing here may be
  described as constant-directivity. B1–B3 are geometry hypotheses with comparable mouth sizes.
* **No canonical family adapter.** `klangfilm_lame_hv_core` is a research kernel; registering it
  (digest-bound adapter + `size_policy: enforce|report_only`, as in Phase A) is a prerequisite for any
  queue/search use. Kernel-level code has no envelope check, so oversized exploration is already
  possible without being labelled invalid; the adapter will carry that policy explicitly.
* **No returning lip.** The core is monotone by design and the beak is the swept lip. A true
  arc-length rollback needs a section-normal (spine) parameterisation so one station still has one
  plane; that is a separate module, deliberately not faked here.
* **Source cap unchanged.** The driver exit wavefront remains the existing simulation assumption; a
  biaxial source ring or a common-tangent landing is not modelled.

## 5. Recommendation

1. **Do not optimize the Stage A box.** The pre-declared rule (≥3° intended-axis authority, <2° leak,
   no new lobes) failed by an order of magnitude, and both policies regress.
2. **Promote Phase B to the next acoustic gate**, in this order:
   a. register the digest-bound family adapter with `size_policy`;
   b. mesh-validate B1–B3 (`lame_shell` offset + self-approach + a real gmsh build);
   c. solve **A0 vs B1 vs B3** with the identical solver/grid/source used here, and score with the same
      two policies through `brief_from_config`;
   d. only if the H/V beamwidth is held near 80°/50° in 1.2–5.6 kHz **and** the DI variance falls, add
      B2 (wide) and start a small search over `theta_*1`, `L_core`, `p_mouth`, then the beak.
3. **Keep the returning-lip module and the source-cap study as separate, explicitly-gated items.** Both
   change the geometry class, and neither is needed to test whether the monotone core holds pattern.

**Decision rule for the next gate (fixed now):** Phase B is worth optimizing only if, at matched mouth
size, the mean BW_H and BW_V in 1.2–5.6 kHz both land within ±10° of 80°/50° and `Var(DI)` over that band
drops by at least 25 % versus A0, with no new −6 dB lobes and no worse `load`. Otherwise the problem is
the terminator/source model, not the flare law.

## 6. Evidence index

| item | path |
|---|---|
| A/B report (physical + both policies) | `docs/evidence/klangfilm_hv_2026-11-16/AB_REPORT.md` |
| A/B machine data | `ab_report.json`, `ab_manifest.json` |
| A/B plots | `ab_plots/bw_di_impedance.png`, `ab_plots/polar_cuts.png` |
| Phase A audit (incumbent, fault, rollback, digest) | `docs/evidence/KLANGFILM_HV_THROAT_AUDIT.md` |
| Phase A preflight / contact sheet | `PHASE_B_GEOMETRY.md` (B), `PREFLIGHT.md` + `SEARCH_BOX.md` (A) |
| Phase B kernel / tests | `tools/geometry/klangfilm_lame_hv_core.py`, `tests/test_tools_klangfilm_lame_hv_core.py` |
