# Contract: Klangfilm-Lame H/V (Phase A) and H/V core (Phase B)

Status: draft for senior review, 2026-11-18, HornFab main @1d6ebc8. Not a generator spec. Labels: [published] [derived] [reconstruction] [original-hypothesis] [code-verified] [unverified]. Code cites are `file:line` under `hornlab_search/design/generators/` (abbrev `G/`). I could not run the tests (no scipy in this sandbox); only numpy snippets were run. Family and YAML names are not evidence of any construction.

## 1. Identity

| construction_id | `rows.type` / schema | frozen kernel (G/) | adapter | origin |
|---|---|---|---|---|
| KL-parent | `klangfilm_lame_v1`, `klangfilm-lame-v1` (legacy bridge type `klangfilm_lame`) | `_klangfilm_lame_v1.py`, `_lame_cap_v1.py` | `klangfilm_lame_family.py:26` | derived/reconstruction of published Kolbrek/Ahlswede 2018 parent + our Lame section. NOT Ahlswede 2019 (`_klangfilm_lame_v1.py:3`, `_lame_cap_v1.py:3`) |
| KL-HV-A | `klangfilm_lame_hv_cd`, `klangfilm-lame-hv-v1` | `_klangfilm_lame_hv_v1.py` | `klangfilm_lame_hv_family.py:33` | original-hypothesis (entrance deformation of the parent) |
| KL-HV-B | `klangfilm_lame_hv_core`, `klangfilm-lame-hv-core-v1` | `_klangfilm_lame_hv_core_v1.py` | `klangfilm_lame_hv_core_family.py:33` | original-hypothesis; not a spherical-wave horn at all when enabled |

Research sources (unfrozen, tested): `tools/geometry/klangfilm_lame{,_hv,_hv_core}.py`. Dates: 2026-11-16 (parent, Phase A), 2026-11-17 (Phase A/B BEM A/B). Each adapter hashes adapter+kernel+parent+cap+shell+numpy/scipy versions into `implementation_sha256` (`klangfilm_lame_hv_core_family.py:49`).
Drift [code-verified]: the "Frozen copy ... SHA256" docstrings (`_hv_v1.py:42`, `_hv_core_v1.py:46`) do not match `sha256sum` of the current tools files (7fc93d63..., 214d4f15...; line-ending normalised). Today the core copy differs from tools only by docstring+imports (diff), the Phase A copy by BOM/docstring/imports. Only the v1 parent has a frozen-vs-research parity test (`tests/test_klangfilm_lame_family.py:47`); none for the H/V kernels.

## 2. Lineage (claim supported by each ancestor, and no more)

- Kolbrek 2007 / Ahlswede 2018 xlsm macro [published]: spherical-wave horn `R0=c/(pi fc)`, `S=2 pi R0 h`, wall `y=sqrt(2R0h-h^2)`, `z=ln(h/h0)/m-h+h0`, rollback inherent. Port matched stored workbook to 0.001 mm at 9 stations (`KLANGFILM_ELLIPSE_HANDOFF_2026-11-16.md`); that port is `tools/geometry/klangfilm_ellipse.py`, a different, frozen construction (planar ellipse, `stretch`).
- Ahlswede 2019 post/article [published, partial]: Lame contour, ellipsoid cap area. Full 2019 calculator is unpublished [unverified]; our `superellipsoid_cap_v1` is a generalisation that reduces to the ellipsoid cap at p=2 (`_lame_cap_v1.py:3`, test `test_p2_matches_independent_ellipsoid_integrand`). Claim supported: p=2 limit only.
- Lame/superellipse planar area `C(p)ab`, `C=4 Gamma(1+1/p)^2/Gamma(1+2/p)` [published math] (`_lame_cap_v1.py:38`). Used here only as a report in KL-HV-B.
- Le Cleac'h/Fourcade 2015 [published] supports the axisymmetric JMLC parent only. The planar-area Lame section `a b = pi r^2 / C(p)` belongs to the separate, unregistered L prototype (`lecleach_swept_hv.py:1`, `DUAL_LAME_INTEGRATION_2026-11-16.md`): "planar section area preserved, curved wavefront not". Nothing in KL-* is attributed to Le Cleac'h.
- Throat angle: HF1440 publishes no numeric exit angle; brief `exit_angle_deg 2` is a simulation assumption; 10.617 deg (560 Hz) / 9.3669 deg (494.44 Hz, recomputed here) is the raw horn wall half-angle, not a driver value (`_klangfilm_lame_hv_v1.py:38`; `03_THROAT_COUPLING_SENIOR_ADDENDUM.md`).
- Phase A/B A/B decision and everything about H/V wall angles, blend, beak: our own [original-hypothesis].

## 3. Operator order (coordinate space)

KL-parent (`_klangfilm_lame_v1.py`):
1. Parent station table in cap height `h` in [h0, end_frac R0], 160 geom + 160 lin pts (:73-79); wall `(z(h), y(h))` (:81-82); arc length `arc` of that wall.
2. Shared C2 gate `g=Q(arc/(morph_frac s_ap))` (:86-87); `q=exp(ln(aspect) g)`, `p=2+(lame_p-2)g` (:88-89). One gate drives both q and p.
3. Per station: Lame axes `a=q b` with superellipsoid-cap area locked to `2 pi R0 h` (brentq, :99); sections scaled by `sin(th)`, `th=acos(1-h/R0)` (:90,101). g<=0 stays exact round parent (:96).
4. Optional source blend (default OFF): per-axis C2 tangent splice on the forward branch only (:106-115).
5. Arc-length resample on mid radius `(a+b)/2`, `n_s+1` stations (:141-148); azimuth phi fixed rays, `n_phi` on [0,pi/2] (:149); `rho(phi)` Lame radius; then z-shift `-D_edge cos^2(phi) W` with `D_edge=rim_sweep_ratio*max(a)` and gate W over pre-shoulder arc (:151-159). Rollback is part of the profile (turn at h=R0/4).

KL-HV-A inserts between steps 3-4 and 5: forward-branch deformation of `a` and `b` in z (`_deform`, :142-166) on `0<=z<=z_join`, `z_join=core_join_fraction*z_turn` (z_turn = z at max z). At fc 494.44 mm: z_turn=184.0, join 0.65 -> 119.6 mm [derived, hand-computed]. Rollback untouched; Lame p, h, cap solve unchanged; q recomputed.

KL-HV-B replaces steps 1-5 entirely when `cd_core_blend != 0` (`make_grid`, :164-206):
1. Slope law in z (not arc, not h): `theta_i(z)`, integrate `r_i=r0+int tan(theta_i) dz` on 1201-pt shared grid (:120-125). r0 = brief driver radius.
2. Resample to `n_s+1` UNIFORM z stations on [0, core_length] (:177-180) (not arc-length).
3. `p(z)` own gate on `u=z/L` (:141-146); Lame section with `a=r_H`, `b=r_V` at each station (:185).
4. Beak: axial offset after `beak_start_frac` (:149-161), added to z (:188). Meridians pinned at phi=0 (y=0) and pi/2 (x=0) (:189-190).
5. Refusal checks, no clamping (:223-244): monotone radii, <=2 axial reversals, setback fold, lip clearance >= 2 mm.
Section psi: every station is a planar Lame section normal to z (no section-normal spine; no returning lip). Wavefront station: none modelled in KL-HV-B.

## 4. Mathematics as implemented

Units mm, deg for YAML angles, rad inside. `Q(t)=10t^3-15t^4+6t^5` clipped (`_lame_cap_v1.py:27`); Q'(0)=Q''(0)=Q'(1)=Q''(1)=0 [code-verified, numeric slope ~1e-7 at t=1e-4].
- Lame radial form `rho=((cos phi/a)^p+(sin phi/b)^p)^(-1/p)` (`_lame_cap_v1.py:44`). At phi=0, pi/2 it returns exactly a, b for any p, so H/V meridians are independent of p [derived; tested allclose 1e-12, `test_lame_exponent_is_independent_of_the_flare`]. p is superelliptic exponent of the SECTION only (not the OS-SE termination exponent).
- Curved-cap area (KL-parent, derived): `P(th,phi)=(rho sin th cos phi, rho sin th sin phi, R0 cos th)`; area of this cap (`lame_cap_area`, order-24 Gauss-Legendre, :56-69) is locked to `2 pi R0 h`. Section planar area is therefore NOT locked; planar area `C(p) a b sin^2(th)` is a by-product.
- KL-HV-A: `delta_i(z)=blend*[dm_i L B1(t)+gain_i B2(t)]`, `B1=t(1-t)^3`, `B2=64t^3(1-t)^3`, `t=z/L`, `dm=tan(theta_target)-tan(theta_base)` (:98-121). `theta_base` is the CHORD of the first dense interval (:124,151), not an analytic r'(0). delta(0)=0, delta'(0)=blend*dm, delta,delta',delta'' = 0 at join (C2 at join). B1''(0)=-6 so curvature jumps at the throat (admitted, :26). B2~t^3: mid gain does not change entrance slope; peak = gain at z=join/2. Blend scales delta linearly (continuous).
- Area meaning KL-HV-A: cap lock solved BEFORE deformation, not re-solved; `area_mode='deformed_after_cap_lock'` (:231). `meta.cap_area_resid_max` is the pre-deformation parent residual (`_deform` never updates it; :165, :237), so it does NOT measure the lost lock [code-verified]. The true post-deformation curved-cap residual is not reported anywhere [unverified].
- KL-HV-B: `theta_i(z)=th0+(th1-th0)Q(z/L)` per axis, `r_i=18+int tan theta_i`; angles are TRUE wall half-angles from the axis (not beamwidth). `theta'(0)=0`, so the throat wall angle is exactly theta_i0 and mouth angle exactly theta_i1 (test pins both, `test_core_is_monotone...`). Beak: `dz=eta(u)[-D_H cos^2 phi + D_V sin^2 phi + D_D sin^2(2phi)]`, eta=Q((u-u0)/(1-u0)). Setback = H lip moves toward throat.
- Area meaning KL-HV-B: reports planar `C(p)ab` per station only (`diagnostics`, :258); `wavefront_model='independent_hv_core'`, `area_mode='flat_lame_area_reported'`. No curved-cap lock, no Webster/exponential area law, no cutoff `fc` (fc/aspect/lame_p/end_frac/morph/rim_sweep inert). Throat->mouth planar area 1018 -> 1.07e5..1.31e5 mm^2 (PHASE_B_GEOMETRY.md). Three different "areas" must not be mixed: curved cap `2 pi R0 h` (parent), planar `C(p)ab` (core, and the L prototype's `pi r^2` constraint), and the real BEM wavefront (unmodelled).
- Endpoint: both axes start at r0 (round, `a=b=18`, p=2); source cap is the brief's `exit_angle_deg` assumption (`angle_provenance='assumed_legacy'`) and changes no wall (test `test_driver_angle_is_not_used_as_a_wall_tangent`).

## 5. Parameter ownership

Bounds origin codes: H = historically tested in a solved run/config; G = geometry-valid (code refusal); P = proposed constant with no derivation found; M = measured by preflight.

| YAML key | operator | effect | status | bounds (origin) |
|---|---|---|---|---|
| fc_hz | parent R0,h0,m | size, depth, curl | searched in parent configs; INERT in KL-HV-B | 150-3000 (G, `_v1.py:36`); curved configs 300/480-800 (H: owner edits in seed headers) |
| aspect | parent q gate | mouth H/V of cap-locked axes (not envelope/beamwidth) | searched / inert in B | 1-4 (G); 1.15-2.3 (H) |
| lame_p | parent p gate | section squareness | searched / inert in B | 2-8 (G); 2-6 (H) |
| end_frac | parent stop h/R0 | truncation/rollback depth | searched / inert in B | 0.3-1.9 (G); 1.05-1.8 (H) |
| rim_sweep_ratio | parent step 5 | H lip setback | searched / inert in B | -0.6..0.6 (G); 0-0.3 (H) |
| morph_frac | parent gate length | where q,p saturate | fixed | 0.05-0.9 (G); pinned 0.3 (H, "stalled V wall" note in seed headers) |
| source_blend_ratio, entry_half_angle_deg | parent blend | CAD entrance splice, both axes same tangent | fixed 0 (OFF) | 0-2, 0-20 (G) |
| cd_core_blend | A: delta scale; B: class switch | A: linear; B: 0 = parent, any >0 = full core (never scaled; `==0.0` test only, :167) | fixed in every config; B adapter refuses to search it (`_core_family.py:169`) | 0-1 (G) |
| theta_h0/v0_deg | A: target first chord; B: throat wall angle | entrance wall per axis | A: searched in Stage A box 6-17/3-13 (M, SEARCH_BOX.md); B: fixed | 0-25 (P, `_hv_v1.py:67`) |
| h/v_mid_gain_mm | A B2 term | interior radial offset at join/2 | A: searched 0-20 / 0-3.75 (M); negative refused | -80..80 (P); lawful box positive-only (M) |
| core_join_fraction | A | join of deformation, fraction of forward span | fixed 0.65 (0.75 in a3b) | 0.05-0.95 (P); no zero-join exists |
| theta_h1/v1_deg | B slope law | mouth wall angle | fixed (seeds) | 5-60, <89 (P) |
| core_length_mm | B | axial length of monotone core = depth | fixed | 30-480 (P; depth envelope 480 from brief) |
| lame_p_mouth, lame_start/end_frac | B p gate | mouth squareness, independent of flare | fixed | p 2-8, fracs 0-1, start<end (P) |
| beak_h_setback/v_projection/diagonal_mm, beak_start_frac | B beak | H setback, V forward, 45-deg scoop; late axial only | fixed | 0-60 / 0-45 / -20..20 / 0.50-0.99 (P); refusal walls (G) |
| wall_thickness_mm, n_phi, n_s | shell/mesh | normal-offset shell; 3/19/64 | fixed | wall>0, n_phi>=7, n_s>=24 (G) |

Adapter rule: knobs of the inactive class must be fixed at seed (`_core_family.py:173-177`); A adapter only dormancy-checks Phase A keys (`_hv_family.py`), i.e. in A with blend fixed 0 the A keys must be fixed.
All B keys have bounds P only: no document derives them; `_CORE_BOUNDS` provenance is unknown [unverified].

## 6. Zero-control identities

| setting | recovers | exactness | test |
|---|---|---|---|
| A: `cd_core_blend=0` (join/theta/gains inert) | KL-parent grid | bit-exact `np.array_equal` | `test_a0_is_bit_identical_to_the_legacy_parent`, `test_a0_ignores_inert_angle_and_gain_values`, family `test_a0_parity_with_legacy_kernel` |
| B: `cd_core_blend=0` | KL-parent | bit-exact | `test_disabled_is_bit_identical_to_v1`, `test_blend_zero_is_bit_identical_to_v1` |
| A: blend=1, theta=measured chord base, gains 0 | parent forward branch | float tolerance only (dm=0 needs exact base value) | none; a1/a2 configs rely on it ("V deformation identically zero") [derived] |
| A: join fraction 0 | none: not representable | refused (<0.05) | `test_deterministic_and_validated` rejects 0.01 |
| parent `source_blend_ratio=0` ("zero blend length") | no splice | exact (`Lb<=0` returns r, :107) | `test_source_blend_off_by_default...` |
| parent q=1, p=2 | round Klangfilm parent | tolerance | `test_p2_q1_reduces_to_round_parent`; sphere cap `test_sphere_cap_analytic` |
| parent p=2 | published ellipsoid-cap area | quadrature | `test_p2_matches_independent_ellipsoid_integrand` |
| parent `rim_sweep_ratio=0` | planar lip | exact z (D_edge=0) | `test_rim_sweep_sets_back_h_side_only` (partial) |
| B: all beak mm = 0 | no beak | exact zeros (:154) | weak: `test_beak_is_exact_noop...` compares pre-gate only |
| B: `lame_p_mouth=2` | elliptic sections | meridians unchanged (1e-12) | `test_lame_exponent_is_independent_of_the_flare` |
| B: theta0=theta1, H=V | straight cone r=18+z tan(theta) | derived, exact in math | NO test |
| B: any nonzero blend -> parent | NOT possible | core never reduces to the rollback parent (different class) | n/a; `blend` is a switch, not a homotopy |

## 7. Seeds (all geometry-only; Phase A and B seeds were later BEM-solved in the A/B lane, none queued, none approved)

`examples/typologies/klangfilm_hv_2026-11-16/configs/` (18 files): a0 (blend 0, canonical genes from `runs/20261116T205942Z-screen-8b22b5/best.json`, fc 494.44, aspect 2.076, p 5.006, end 1.795), a0_epw9, a1, a2 (10/5 and 14/5 deg), a1_h_only/a2_v_only (single-axis, base-chord pinned), a3/a4 (negative V gain, expected refusal), a3b/a4b (respec to 0), a5 (fc 400, over envelope, `report_only`), stage_a_search (4 knobs), b1_balanced..b4_wide_h, b3_epw9, ab_cd_policy (never solved, policy resolution only, points at BASE v7 brief). README states "Geometry-only hypotheses ... not acoustic winners" and that H/V are true wall half-angles. Seeds b1-b4 are our hypotheses; the Phase B `SEEDS` dict (`_hv_core_v1.py:286`) is the same set.
Stale seed comments [code-verified by recomputing the slope law]: `_hv_core_v1.py:287-298` say b1 mouth ~521x262, b2 ~561x244, b3 ~498x258; the law gives W/H 479.6/239.7, 595.0/232.8, 472.5/266.1 (b4 562.5/261.6), matching PHASE_B_GEOMETRY.md (480/240, 595/233, 473/266, 563/262). Trust the table, not the comments.
Parent configs (not this contract's family): `home_landscape_2026-11-15/hl__klangfilm_lame_curved_v1*.yaml` (base, c200, seeds B,D,E,E2,E3,P1-P4,S1-S4,V5) and `walls_relieved/*curved_v1{,_c200}`; provenance in headers: owner-directed seeds 2026-11-16, end_frac box 1.0-1.6 and fc floor 300 by owner edit, "NOT Ahlswede 2019 exact", not queued. `dual_lame_2026-11-16/k01` uses `klangfilm_lame_v1` with imported seed manifests, "unvalidated and unsolved" per `DUAL_LAME_INTEGRATION_2026-11-16.md`.

## 8. Objective fit (read from configs, not family)

17 of 18 H/V configs and all curved/c200/walls_relieved configs: `brief_file: briefs/home_landscape_2026-11-15/room_landscape_80x50_700_hf1440_v7_smooth.yaml` -> 80H x 50V target, 700 Hz XO, band 350-8000 Hz, loaded_hi 5600, envelope 600x480x480, objective version 7, `di_slope_target 5` dB/dec, `di` weight 0, tol cov 8, `cov_narrow_ratio 1`, `cov_v_weight 0.5`. `ab_cd_policy.yaml` points to `..._v7.yaml` (base CD: slope 0, di weight 0.3, cov tol 3, per `CROWE_KLANGFILM_BRIEF_RESCORE_2026-11-17.md`). J is comparable only inside one policy; lower J is better (Stage A "worse" = higher J). Neither family contains any 80x50 constant-directivity construction; Phase A explicitly "not a claim of 80x50 CD". H/V wall angles are not beamwidth: A2 changed V wall -4.44 deg for 0.00 deg V beamwidth (1.2-5.6 kHz); B-series wall half-angles 48-53 deg H / 24.5-30 deg V gave BW_H 62-65, BW_V 41-47 (outermost -6 dB crossings; saturation at cut limit in low bins) (`STAGE_A_VS_B_DECISION.md`).

## 9. Verification status

| level | evidence | gap |
|---|---|---|
| analytic | tests above pin slope law, C2 gates, tangent hit, monotonicity, bit-identity (not re-run by me) | no test for cone limit, A zero-delta limit, b4 monotone test (`test_core_is_monotone` parametrises b1-b3), frozen-copy parity |
| sampled | `PREFLIGHT.md`, `PHASE_B_GEOMETRY.md`, `SEARCH_BOX.md` (200/200 LHS, 16/16 corners lawful), `lame_shell` + `check_self_approach` in adapter | lip clearance and shell are sampled, not certificates |
| meshed | A0,A1,A2,B1-B4 meshed 3087-7464 dof; epw9 re-solve A0 (16394 dof), B3 (6757) | convergence checked for A0,B3 only; B seeds have ~2.4x fewer dof |
| BEM | `AB_REPORT.md`, `AB_REPORT_B.md`, `AB_REPORT_CONV.md`: Stage A authority <=2.74 deg and both policies worse; B3 Var(DI) -45%, smooth J 6.570 vs A0 8.438 but BW_H 65.2 < 70 floor; B1,B2,B4 worse | single mesh policy, source cap `auto` (assumed 2 deg), A0 library SHA differed (re-solve reproduced J to 0.011%) |
| measured | none | no driver CAD/exit-field, no prototype |

Known construction gaps: no returning lip/rollback in KL-HV-B (docs say beak is the only terminator; recommended next module is a section-normal spine); no biaxial source landing; Phase A post-deformation curved-cap residual unreported (Sec. 4); B1-B4 not "meets 80x50". Phase B gate result: FAIL on H coverage, pass on DI constancy for B3 only.

## 10. Proposed CPU-first checks and open questions

Checks (numpy only, minutes): (1) add `cd_core_blend` in (0,1) assertion that B is a switch, or document it; (2) test A with blend=1, theta=chord base, gains 0 equals parent to 1e-12; (3) test B cone limit and `|rho(phi=0,pi/2)|` equals a,b for p up to 8; (4) recompute the post-deformation curved-cap residual of A seeds with `lame_cap_area` and report it; (5) hash-parity test frozen vs tools H/V kernels, refresh docstring SHAs and seed comments; (6) sampled planar-section area table `C(p)ab` vs cap area for B seeds to quantify "wavefront area" mismatch; (7) mesh-resolution sweep on beak/lip (dz vs n_s) because B stations are uniform in z, not arc; (8) extend the monotone test to b4.
Questions for senior review: Are `_CORE_BOUNDS` (theta1<=60, beak ranges) to be promoted from P to a stated basis? Should the beak be treated as a lip (current evidence: H coverage missing without a rolled lip, widening the mouth did not help)? Is `cd_core_blend` as a class switch acceptable vs an honest `core_class` key? Is any claim allowed that Phase A H/V angles "control" beamwidth given A2 0.00 deg? Is a single smooth-brief BEM at the assumed 2 deg source cap enough to rank B3?

## Senior review (2026-11-18): REVIEWED

- Confirmed [code-verified, re-run]: the stale SEEDS mouth comments. The kernel today gives b1
  479.6x239.7, b2 595.0x232.8, b3 472.5x266.1 and b4 562.5x261.6 mm (`make_grid`, driver 18 mm /
  2 deg). Corrected in the comments-only patch `W5code_0005` (owner-gated: it changes the family
  implementation digests).
- Confirmed: the frozen-copy SHA docstrings are stale. The tools files now hash to `7fc93d63...` and
  `214d4f15...`. The docstrings are corrected in the same patch to record both SHAs; no parity test
  exists yet.
- Open: (1) the `cd_core_blend` switch-vs-blend semantics; (2) the post-deformation curved-cap
  residual of the A seeds; (3) a frozen-vs-tools parity test; (4) the mesh-resolution sweep on the
  beak/lip. These are checks 1, 4, 5 and 7 of section 9, unchanged.
