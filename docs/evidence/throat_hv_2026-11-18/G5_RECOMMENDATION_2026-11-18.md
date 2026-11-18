# Throat block follow-up: recommendation (Fable WP 4.4, stage 4; cloud senior 2026-11-18)

**Proposal for the owner. Nothing queued, no config written for GPU.**

## Recommendation

**Park the throat block on A as "inert in this envelope". Do not run the A_r15 + onset 0.32 /
ramp 2.16 test.** Record B as "authority in H, not competitive under v7".

## Why (each point labelled)

1. **A has no authority** [verified on the part3 CSVs with `u3_authority.authority()`; plan
   §10.2]: rho 1.5 → 2.0 moves no band more than 1.28°; vs v8 the whole-band means move 0.56° /
   0.95° (per-band confirmation command in plan §10.2, expected to agree [inferred]).
2. **A's J gain is a tie** [verified arithmetic]: A_r15 − v8 = −0.0192, A_r20 − v8 = +0.0243, both
   far below the v7 frequency floor ≈ 0.13 J (D8, invariant 7).
3. **A does not legally accept those keys** [code-verified + run in the cloud]: A_r15's seed carries
   `morph_target: 0`, `morph_fixed: 0.0`, `morph_rate: 4.1236`. `families._validate_throat_hv`
   (`hornlab_search/design/families.py:647-651`) refuses `hv_onset_frac` next to `morph_fixed`
   ("is an alias of morph_fixed; give one, not both"), and without the native keys refuses it
   because `morph_target` is 0 ("has no effect without morph_target (inactive knob)"). Setting
   `morph_fixed 0.32 / morph_rate 2.16` loads, but with `morph_target: 0` the morph does nothing:
   an inert knob. Making it live means switching A's mouth to a morph target, which is a
   different construction (new config version, `hornlab-typology-research` + shape check first),
   not "A plus onset".
4. **B1 cannot mesh-check the A family on this card** [primary: `b1_mesh_feasibility.md`; inferred
   for A_r15]: the ext-throat v8 parent refuses at epw 12 and is estimated at ~21 k DOF; A_r15
   (5 438 ref DOF) is the same parent. Any A result would have no mesh floor.

## What B tells us (keep, do not build further yet)

- The onset knob narrows H by up to ~10° above 1.1 kHz with V moving less than half [verified]:
  it is a real H-plane steering tool on a no-extension OSSE.
- B pays ~3.2 J of `load` under v7, so it cannot compete with A/v8 [primary: part3].
- **Free next look (CPU, no GPU):** the WP 1.4 rescore in
  `docs/evidence/v10_rescore_2026-11-18/README.md` already includes the throat runs (they carry the
  home brief stem). Read the B rows in the v10 column: if B still trails A by more than the v10
  floor there too, close the B line; if not, bring it back to the owner as a v10-identity question.

## If the owner still wants one A-family GPU test

Only after B1 batch 1 and only as a single `hornlab-search run` of a NEW `_v2` config that
declares a live morph target, shape-checked, with the ΔJ judged against the v7 floor and an
explicit note that no mesh floor exists for this parent on the 8 GB card. Cost: 1 solve. This
is weaker evidence than anything else in the GPU queue; it is listed only for completeness.
