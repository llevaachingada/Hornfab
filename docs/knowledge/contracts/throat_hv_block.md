# Contract: shared near-throat H/V block (`throat_hv`)

Date: 2026-11-18. Code: `hornlab_search/design/throat_hv.py` plus the family mappings below.
Status: **REVIEWED (senior, 2026-11-18)**; the open items are listed in section 6.
Labels: [published] [derived] [reconstruction] [original-hypothesis] [code-verified] [unverified].

## 1. Identity and vocabulary

The block has three knobs. Each has ONE meaning in every family that adopts it. The block is a
shared vocabulary, not a universal generator.

| Knob | Range | Meaning | Neutral value |
|---|---|---|---|
| `throat_hv_ratio` (rho) | [0.25, 4] | H/V asymmetry of the near-throat growth. The per-azimuth scale is `rho**(cos 2p / 2)`: sqrt(rho) on H, 1/sqrt(rho) on V, with the geometric mean preserved | 1 or absent |
| `hv_onset_frac` (s_on) | [0, 0.9] | where the H/V or section departure starts, as a fraction of the family's own axial or arc station | absent |
| `section_exp_ramp` (gamma) | [0.5, 8] | ramp exponent: `w(t) = clamp((t - s_on)/(1 - s_on), 0, 1)**gamma` (the Ath morph factor) [published: Ath user guide] | absent |

## 2. Family verdicts (KH-003, the OS-SE primary check, R-OSSE rev7)

| Family | rho | onset/ramp | Label |
|---|---|---|---|
| OSSE (native) | per-azimuth `k(p) = k rho**(-cos2p/2)`, sent to the mesher as an expression | alias of `morph_fixed` / `morph_rate` (needs `morph_target`) | rho is WITHIN the OS-SE parent [published: Batik 2020 s5, profile parameters may vary around the device]; the morph is [published Ath] |
| osse_rollback | per-azimuth k | drives the superformula window | wall: within OS-SE; window remap: LABELED HYBRID |
| lecleach H/V pair | per-plane march flare T (larger T = faster, eq. 42) | blends the round core into the H/V axes | each plane is a JMLC march [published]; the pairing and ramp are LABELED HYBRID |
| `lecleach_iwata_ar` (rows `iwata_ar`) | **refused** (not mapped: its H/V split is the AR law) | delays the AR law: `AR = 1 + (AR_m-1) w(s)`; ramp = alias of `ar_p` | LABELED HYBRID on an [original-hypothesis] reconstruction |
| rolled family | radial scale `rho**(cos2psi/2 * w)` inside the relief window | onset replaces `relief_start_s`; ramp shapes the window start | LABELED HYBRID (original HornFab construction) |
| R-OSSE | **not adopted** | not adopted | The rev7 source (at-horns.eu, p. 2) describes "an axisymmetric waveguide" with scalar parameters only. Per-azimuth k is not addressed, so adding it would be an unlabeled hybrid |

## 3. Invariants (every adopting family) [code-verified, tests named]

1. **Neutrality:** absent keys give byte-identical rows, meta and design hashes; rho = 1 gives the
   parent law exactly (`test_design_throat_hv_*::*absent*`, `*neutral*`; for iwata_ar, onset 0
   equals today's law to 1e-9).
2. **Round throat:** the s = 0 section is unchanged (all tests that compare station 0).
3. **Source matching respected:** the rolled family refuses a window that starts inside the
   source-matching region. OSSE-family k keeps the driver-exit slope tan(a0).
4. **Mirror planes kept:** the scale is even in p (cos 2p).
5. **No inactive knob is searched:** an onset or ramp without a live target is refused (OSSE
   without `morph_target`, rolled with zero relief and neutral rho, lecleach without the fc_h/fc_v
   pair, osse_rollback without the superformula).
6. **One onset knob:** `hv_onset_frac` refuses its native twin when both are given
   (`morph_fixed`, `sf_start`, `relief_start_s`, `ar_p` for the ramp).
7. **Provenance:** an active block writes `meta.throat_hv` plus the family `STATUS` label.

## 4. Local evidence (owner box, 2026-11-17/18)

- The pinned mesher accepts the per-azimuth k expression. rho = 1 reproduces the v8 incumbent's
  mesh to 0.01 mm. rho = 2 opens H sooner only after the 79.7 mm round extension [code-verified on
  the mesh: `LOCAL_RESULTS_2026-11-18.md` section 6].
- None of the 9 best historical ext-throat designs splits H/V before about 1/4 depth (part 2,
  Phase 0b).
- The "18 -> 14.2 mm pinch" is the domed source cap (tag 2), not the wall
  (`analysis_2026-11-18/W7_THROAT_PINCH_VERDICT.md`).
- No acoustic claim yet. The GPU phases 1-3 (part 2) are pending, so whether the block improves
  J is [unverified].

## 5. How to judge a block result

- Compare at the SAME score identity (brief, objective block, mesh epw); never pool across them.
- A B-onset variant "wins" only if it beats `B_ctl` by more than the Phase 2 mesh |dJ|.
- The rolled rho range is narrow on the v7 seeds (about 0.6-1.3); a refusal outside that range is
  the guards working, not a bug.

## 6. Open items

1. GPU Phase 1-3 results (part 3) decide whether the block is worth searching.
2. Rolled rho and iwata_ar onset have no shape_check or mesh yet [unverified on the mesher].
3. The owner decides whether hybrids may be published under the parent family name; currently they
   may not.
