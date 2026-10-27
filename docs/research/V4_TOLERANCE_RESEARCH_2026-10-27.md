# V4 tolerance research: what matters per horn class (outside + in-repo sources)

Written 2026-10-27 at the owner's request, ahead of the objective-v4 tolerance choice. Companion to the Opus
scoring review (`V4_SCORING_REVIEW_2026-10-27.md`, in progress at the time of writing). Tags: **[S]** sourced
(URL below), **[R]** from our own research docs, **[E]** estimate / proposal, to be tested against stored data.
Owner priorities recorded in this session: even coverage across the band, not beamy, conforming to the
requested dispersion; the weighting depends on the brief class (constant-directivity vs horns that fall off).

## 1. What the outside sources say

1. **Pattern constancy is best measured by DI spread and by polar similarity, not by one slope number.**
   Princeton 3D3A, "Metrics for constant directivity": five metrics were tested on measured loudspeakers; only
   (4) standard deviation of the directivity index and (5) cross-correlation of polar responses scored well on
   both proposed definitions of constant directivity [S1]. Our v3 uses `dislope` (a straight-line fit of DI vs
   log f). A slope can be zero while DI wobbles, so it misses what the paper found most useful. (Only the abstract
   was read.)
2. **Listener preference (hi-fi / room listening): flat on-axis first, smooth off-axis second, DI/off-axis shaped
   like the on-axis response.** Toole/Olive/Harman: off-axis sound is about 88% of what is heard in a room (14%
   direct, 44% early reflections, 44% late) [S2]; the Olive preference model is built from smoothness / deviation
   metrics of on-axis and predicted-in-room responses, not from beamwidth numbers [S3]. Caveat: this is
   room-listening research on speakers, not PA coverage.
3. **Pro-audio horns are specified by -6 dB beamwidth over a stated band, with tolerance, and the tolerance is
   asymmetric.** Example datasheets: 60 deg (+10, -5) at -6 dB over 2-16 kHz [S4]. Wider than nominal is tolerated
   more than narrower, which matches "do not be beamy".
4. **Control is lost below a frequency set by mouth size, and the failure mode is a pattern flip.**
   `d = K / (angle x f0)`; a small-height horn loses vertical control and its vertical pattern can end up
   wider than its horizontal [S5]. Every spec sheet that quotes a nominal angle without its band is hiding this.
5. **Higher-order-mode (HOM) trouble shows up as discontinuities in the polar map.** The practical in-repo proxy
   is the variance of beamwidth vs frequency [R: appendix_B D2]. Geddes has no peer-reviewed single HOM metric
   (unverified there).

## 2. In-repo anchors for tolerance sizes

- Solver noise floor: beat vs bempp 0.039-0.055 dB; DI tolerance 0.3 dB; beamwidth 2 deg [R: 12_RESEARCH_BASIS,
  CONTINUITY]. Any tolerance below these is noise.
- CD working definition used in our survey: -6 dB beamwidth within +/-10-15 deg and DI flat to +/-2-3 dB over the
  band [R: appendix_B D3, forum-sourced -- treat as [E]].
- K-law break per axis already in the feasibility record; v3 masks cov+dislope below `f0` [R: scoring guide].

## 3. Proposed structure of the tolerances (hypotheses, to be tested on stored records)

The tolerance is "how big a miss counts as 1 unit of bad", so it should differ by horn class.

| Class | Brief examples | cov tolerance | cov shape | rip | di / DI spread | dislope | load |
|---|---|---|---|---|---|---|---|
| **A. Constant-directivity waveguide** | B1, B2' (1.4" hi-fi / PA 60x40) | ~10 deg | **asymmetric: narrow side counts ~2x the wide side** [E, from S4] | ~1.5 dB [E] | tight: DI std ~1.5-2 dB | ~3 dB/decade [E] | off |
| **B. Loading / rollback** | Le Cleac'h, salmon, B3b | ~15 deg [E] | asymmetric, same idea | ~2 dB [E] | looser (DI rises naturally) | ~6-8 dB/decade [E] | on, vs 0.7 z_min |
| **C. Low-reach PA ("falls off")** | B3a 90x90 @400, B3b | ~15 deg | **one-sided below f0**: penalize narrower-than-target everywhere, wider-than-target only at or above f0 [E] | ~2 dB | loose below f0 | scored from f0 only (already masked) | per brief |

Why the one-sided rule for class C: below the break frequency a horn cannot hold the pattern, so the true
behaviour is a widening beam; v3 penalizes that equally to being beamy, which is the "impossible band" problem
(61-87% of cov loss, 12_RESEARCH_BASIS 13.5). Being beamy is the real defect there.

## 4. Candidate scoring changes these sources point to (for v4, owner decision)

1. Asymmetric coverage error (penalize narrow more than wide).  [S4, owner priority]
2. Replace or supplement `dislope` with **DI standard deviation** (and optionally a **polar cross-correlation /
   beamwidth-variance** term for "even coverage across frequency").  [S1, R]
3. Diagonal (45/135 deg) term, option (b) "match intended coverage".  [R: P8b, owner]
4. Class-specific tolerance blocks in the brief, never a global default.  [owner]

## 4b. Owner field experience (recorded 2026-10-27): narrowing in the 2.5-5.5 kHz presence region is worst

Owner: narrowing around the mid-range / presence frequencies (~2.5-5.5 kHz), and anything that is good only
"in the middle" of the pattern, sounds definitely worse than the same error elsewhere. Consistent with the
search result that constant-directivity horns are preferred when upper-mid dispersion stays wide, and with a
"power suck-out" near 3 kHz being the audible failure [S: Toole as summarized in the Keele/CD search result;
ear sensitivity peaking in this region is general knowledge, not separately sourced here].
Implications for v4 (hypotheses):
1. **Frequency-weight the beaminess penalty**, heavier across ~2.5-5.5 kHz. Mechanism exists: objective v2/v3
   `freq_weights` already re-weight points the grid solves; v4 can make the narrow-side cov penalty carry them.
2. **Check grid coverage first**: the screen grid is 12 log points 500-10k, so only about 3 points fall in
   2.5-5.5 kHz. A heavy weight on 3 points is noisy; may need a denser screen grid there (owner decision,
   changes the solve group) or the weighting applied at verify only.
3. A "good only in the middle" pattern (on-axis fine, off-axis rolling off early) is the beamy failure the
   asymmetric cov term and the DI-spread term are meant to catch; test that they do on stored records.

## 5. What this note does NOT establish

- All numeric tolerances above are proposals [E]; only the structure is sourced. They must be checked by
  recomputing the weighted-share table on stored records (the Opus review does this).
- Toole/Olive was read via summaries, not the primary papers; the Princeton paper via its abstract only.
- The +10/-5 deg example is one vendor datasheet pattern, not a standard.

## Sources

- [S1] Princeton 3D3A, Metrics for constant directivity: https://collaborate.princeton.edu/en/publications/metrics-for-constant-directivity/
- [S2] Acoustic Frontiers summary of Harman off-axis research: https://www.acousticfrontiers.com/2013127speaker-off-axis-response-psychoacoustic-and-subjective-importance/
- [S3] Olive preference model patent US8311232: https://patents.google.com/patent/US8311232
- [S4] Beyma TD-series datasheet (example of -6 dB spec with asymmetric tolerance): https://www.Lautsprechershop.de/pdf/beyma/beyma_td365.pdf
- [S5] audioXpress, Understanding Horn Directivity Control: https://audioxpress.com/article/Understanding-Horn-Directivity-Control
- In-repo: `docs/plan/12_RESEARCH_BASIS.md`, `docs/research/senior_pass_2026-10-24/appendix_B_methods_survey_raw.md`,
  `docs/BRIEF_AND_SCORING_GUIDE_2026-10-25.md`
