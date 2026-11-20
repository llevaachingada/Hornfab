# Favorite FAV-001 — Crowe-X on OS-SE CD (`4140768780f0`): why it scores 5.0, and how to improve it

**2026-11-20, senior research pass, owner request.** CPU only in this document. The GPU follow-up is
queued as night `fav_crowe_2026-11-20` (see §7); its results are not reported here.

- Run: `runs/20261120T084006Z-screen-fc4e18` (GUI `#/run/20261120T084006Z-screen-fc4e18`), config
  `examples/typologies/cd_v11_completion_2026-11-20/cd11c__crowe_x_osse_cd.yaml`, brief
  `examples/briefs/cd_v11_2026-11-20/room_landscape_80x50_700_hf1440_v11cd.yaml` (objective v11, CD identity).
- Screen J 4.9965 (eval 44). Verify-grid J **4.9939** (`runs/20261120T185832Z-verify-e5de4a`,
  `docs/evidence/cd_v11_2026-11-20/VERIFY.md`), so the screen held up.
- Outer size 587 × 450 × 264 mm (W × H × D), 1.4" (36 mm) round coupling, quarter-model 4,487 dofs at verify.
- Construction: `grid` / `rows.type: osse_rollback`. Contract: `docs/knowledge/contracts/crowe_v2a_and_crowe_x_osse.md`
  Contract B, an [original-hypothesis] hybrid, **not** Crowe geometry and not a published construction.
- Labels: [measured] = read from stored run files; [derived] = computed here from stored data or closed-form
  physics; [proxy] = CPU plane-wave Webster estimate (relative trends only); [practitioner] = forum
  statement by a named designer; [in-repo] = existing dossier.

---

## 1. What the owner saw, in numbers [measured, verify grid]

The owner's read was "best directivity plots and aesthetics so far, and it flares immediately where the
throat-extension horns' H and V charts look alike." The verify-grid metrics back that read:

| lane (v11 verify finalists) | LW dev dB | DI std dB | NACC | off-axis dB | H range 700–8k | V range 1k–8k | H/V ≥ 2 kHz | J |
|---|---|---|---|---|---|---|---|---|
| **crowe_x_osse (FAV-001)** | **0.318** | **0.462** | **0.9954** | **0.419** | **67–82°** | 57–67° | 1.21 | 4.994 |
| ext_throat_hvlaw | 0.618 | 0.655 | 0.9895 | 0.641 | 59–72° | 47–69° | 1.30 | 3.341 |
| osse_fold_warm | 0.430 | 0.629 | 0.9902 | 1.493 | 52–80° | 47–64° | 1.16 | 3.615 |
| osse_morph | 0.339 | 0.771 | 0.9913 | 1.394 | 51–74° | 49–68° | 1.15 | 3.665 |
| ath_core_petal | 0.357 | 0.908 | 0.9923 | 1.544 | 49–70° | 44–65° | 1.15 | 4.444 |

FAV-001 is **best on all four CD-matrix metrics** (listening-window deviation, DI flatness, normalised
cross-correlation, off-axis smoothness) and has the steadiest horizontal beamwidth of the group. In the
throat-extension lane, H and V really do merge between about 1.0 and 1.35 kHz (H 58.6–62.2° vs V 55.8–69.3°).
H also dips below the 60° corridor there. That is the "they look the same" effect the owner noticed.

Honest weak points of FAV-001 itself:
- It is really a ~69 × 58° horn above 3 kHz, not 80 × 50°: H sits ~11° under target and V ~8° over.
  Both stay inside the v11 corridors (H 60–90, V 40–60), so `cov_profile` is ~0.
- **Throat loading.** Re z (normalised to ρc) is 0.21 at 682 Hz, 0.30 at 782, 0.38 at 896, 0.52 at 1028 Hz and
  reaches 1.0 only at 1.55 kHz. `lfp20_hz` = 674 Hz, `lfp50_hz` = 995 Hz (screen).

## 2. Why J is 5.0: one term is 53 % of it [measured + derived]

Screen `best.json` terms × brief weights (they sum to `total` 4.9965):

| term | raw | weight | contribution |
|---|---|---|---|
| **load** | 2.645 | 1.0 | **2.645** |
| cd_offaxis | 0.543 | 1.0 | 0.543 |
| flat (unit-acceleration on-axis) | 0.888 | 0.5 | 0.444 |
| cd_lw | 0.231 | 1.5 | 0.346 |
| cd_di_std | 0.425 | 0.75 | 0.319 |
| flat_cv | 0.553 | 0.5 | 0.276 |
| cd_nacc | 0.203 | 0.75 | 0.153 |
| dislope / di_roughness / rip / cov_profile | — | — | 0.111 / 0.108 / 0.047 / 0.005 |

`load` is the v7 C1 term (`hornlab_search/objective/scalar_v7.py::_load_v7`, reused by v10/v11):
`lfp_pen = max(0, log2(LFP20 × 1.6 / F_X))` + `rez_pen = max(0, 0.5 − min Re z over [F_X, f11])`, ÷ tolerance 0.3.
With F_X = 700: lfp_pen = log2(674 × 1.6 / 700) = 0.62, rez_pen = 0.5 − 0.33 = 0.17, giving (0.79)/0.3 = **2.645**.
The rule requires Re z ≥ 0.2 by 437 Hz and ≥ 0.5 from 700 Hz up. This horn gets there about 0.6 octave late.

**GUI defect found:** the run page's "Score breakdown" lists only six terms (load, flat, dislope, rip, cov, di).
It omits `flat_cv`, `di_roughness` and all four v11 CD terms. Those are 1.54 of the 5.0, and they are the
terms FAV-001 wins on. Logged as an issue (§8).

### 2.1 CPU rescore of the five verify finalists (zero GPU) [derived]

`hornlab_search.objective.replay.replay_run_dir` on the stored verify responses, against copies of the
v11 brief that differ ONLY in F_X (= `target.f0_hz`/`f0_v_hz`, the first H corridor anchor and the CD band
start) or in the load weight. The `as_brief` row reproduces the stored verify J exactly (parity check).
These are **diagnostic identities**, not a re-ranking of stored runs.

| variant | crowe_x_osse | ext_throat | osse_fold | osse_morph | ath_core_petal |
|---|---|---|---|---|---|
| as brief (F_X 700) | 4.994 (load 2.73) | **3.341** | 3.615 | 3.665 | 4.444 |
| F_X 800 | 3.821 (1.83) | **2.973** | 3.361 | 3.173 | 3.593 |
| F_X 900 | 2.608 (0.85) | 2.774 | 3.216 | 2.997 | 3.327 |
| F_X 1000 | **2.101** (0.35) | 2.774 | 3.216 | 2.997 | 3.327 |
| load weight 0 | **2.265** | 3.341 | 3.548 | 3.485 | 4.164 |

**Answer to "why isn't it scoring higher":** the low loading below ~1 kHz is the only reason. With a 900 Hz
crossover floor it is 0.17 J behind the leader. At 1 kHz, or with loading ignored, it is **#1 by 0.67–1.08 J**.

## 3. Is throat loading "even really an issue"? Partly real, partly a scoring artefact

**Real part** [in-repo + derived]:
- With an ideal velocity source, radiated power ∝ Re z (`docs/research/SIM_VS_REAL_HORN_2026-10-27.md` §3).
  Against ext_throat at the same diaphragm velocity, FAV-001 radiates 12 dB less at 682 Hz (0.21 vs 3.23),
  8 dB less at 782 Hz, 4.8 dB less at 896 Hz and 1.4 dB less at 1028 Hz. Above ~1.1 kHz it loads **better**
  (0.68–0.83 vs 0.58–0.60 at 1.18–1.35 kHz).
- Making that up with EQ costs diaphragm velocity: ~2.5× at 780 Hz, i.e. excursion, heat and distortion
  headroom near the crossover. For the loud-home 110 dB brief, the driver audit
  (`docs/research/BUDGET_DRIVER_SHORTLIST_AUDIT_2026-11-19.md`) already reads 1.4" drivers as "800 Hz minimum"
  class parts. A 700 Hz crossover on this horn is the most demanding case. **At ~900–1000 Hz the deficit is small.**
- The ideal-source BEM cannot predict the driver's own response or distortion. Only the throat load itself is real BEM physics.

**Artefact part** [measured + derived]:
- The v7/v10/v11 `load` term is **one-sided**. It charges a shortfall below 0.5 ρc and never charges an excess.
  The designs that score `load` ≈ 0 mostly do it with a **throat resonance**: peak Re z 3.23 ρc at 682 Hz
  (ext_throat), 1.95 at 782 (fold), 1.71 at 896 (morph), 1.39 at 896 (ath_core_petal). Each is followed by a dip
  (ext_throat 0.58 at 1.35 kHz). Their LFP20 crossings sit on the rising flank of that peak.
  FAV-001's Re z rises monotonically with no peak: the smoothest impedance of the five.
- A resonant throat is a standing wave: stored energy, ripple and ringing (the v6 `z_smooth` term was built to
  catch exactly this, `docs/research/LOADING_OBJECTIVES_RECONCILED_2026-11.md` §1.3). v11 does not carry it.
- Weighting: SIM_VS_REAL §3 recommended a CD-class load weight of 0.3–0.5 at z_min 0.5. v11 uses weight 1.0
  with tolerance 0.3, so loading outweighs any single CD term.
- [practitioner] Geddes on OS waveguides: there is no predicted "cutoff", the low end is set mostly by the
  driver, and "loading and cutoff" are not the relevant factors for a device meant to control directivity
  ([diyAudio, "Geddes on waveguides"](https://www.diyaudio.com/community/threads/geddes-on-waveguides.103872/)).
  That is one designer's position, not a law. It supports treating loading as a crossover-placement
  constraint rather than a co-equal score.

**Verdict:** loading is a real constraint on **how low you can cross this horn** (~900 Hz+ comfortably).
It is not evidence that the competitors are better horns, because the ranking rewards their throat
resonances. No objective change is made here (v11 is frozen as an identity). §8 lists proposals.

## 4. Improvement levers, ranked

### 4.1 OS throat expansion `k`: the lever never tried (frozen at 1.0 in every Crowe-X lane)

The wall is the ATH OS-SE law per azimuth (`hornlab_mesher.profile_formulas`; OS part
`r = sqrt((k r0)² + 2 k r0 z tan a0 + z² tan² a) + r0 (1 − k)`). [practitioner] Batík (ATH author):
k > 1 uses the OS profile of a k-times-larger virtual throat. It is less curved near the throat, so it
expands more slowly and pushes the higher throat impedance lower in frequency. The price is
"some of the constant directivity" for overall smoothness and somewhat more loading
([ATH4 thread](https://diyaudio.com/community/threads/acoustic-horn-design-the-easy-way-ath4.338806/page-228)).
The repo's own shape-check rule says the same: "extra depth helps via OS `k` (slower throat), not narrower walls."

[derived] Local Webster cutoff at the throat, k_c² = r''/r. For the OS part this gives
**f_c ≈ c·tan a / (2π r0 √k)**: about 2.1 kHz (H, a ≈ 35°) and 1.5 kHz (V, a ≈ 27°) at k = 1, falling as 1/√k.
This is the "starts to flare immediately" property, made quantitative. It is the same throat curvature
that gives the clean early H/V split.

[proxy] Plane-wave Webster TMM on the generator's own wall grid (quarter cross-section area by shoelace,
flanged-piston mouth). It reproduces the measured LFP20 (674 Hz) at k = 1. It overstates mouth ripple,
so use it for trends only. With depth re-solved so the mouth stays 587 mm wide:

| k | L mm | mouth W × H | LFP20 | LFP50 | Re z at 682 / 782 / 896 / 1028 Hz |
|---|---|---|---|---|---|
| 1.0 (FAV-001) | 260.3 | 587 × 450 | 674 | 1144 | 0.21 / 0.36 / 0.26 / 0.30 |
| 2.0 | 274.2 | 587 × 448 | 627 | 775 | 0.33 / 0.51 / 0.37 / 0.54 |
| 3.0 | 286.7 | 587 × 446 | 601 | 673 | 0.54 / 0.63 / 0.49 / 0.91 |
| 4.0 | 298.2 | 587 × 445 | 567 | 631 | 0.83 / 0.67 / 0.62 / 1.42 |

So k ≈ 3 plus 26 mm more depth should roughly halve the load penalty at the same mouth. Reaching LFP20 ≤ 437 Hz
(F_X 700) without a resonance is not available from k alone. A cone that loads to 0.2 at 437 Hz needs a
virtual apex ~62 mm behind an 18 mm throat, i.e. a ~17° initial half-angle. That is a throat extension,
with the H/V-merging cost the owner saw. **What k costs in directivity is unknown until BEM**: the queued
k-attribution solves (§7) measure it directly.

### 4.2 Rebalance coverage toward 80 × 50
Under the load-dominated J, CMA pushed `g_a_v` high (ρ −0.60, 26.8° of a 28° bound) and kept `g_a_h` low
(34.9°, near the 33° bound). That trades coverage accuracy for loading. Once k carries the loading, a_h can
rise and a_v fall. The k-home search box widens a_h to [32, 42] and a_v to [20, 30].

### 4.3 Depth and mouth flare
`g_L_mm` was the most influential knob (ρ −0.72), `g_s` sat at 0.437 of a 0.45 bound, and the brief allows
480 mm depth (the favorite uses 264). The search box allows L 220–340 and s to 0.55. Width is the binding
envelope (587 of 600 mm), so extra depth must come with k or smaller angles, not a bigger mouth.

### 4.4 Lip wrap
`g_wrap_deg` sat on its 80° lower bound in 1 of the top 6. The box now opens it to 50°.

## 5. Compact variant: 500 mm cube, 900 Hz crossover (owner request mid-pass)

New brief `examples/briefs/compact500_xo900_2026-11-20/compact500_xo900_80x50_hf1440_v11cd.yaml`. It is the v11
CD brief with only these keys changed: envelope 500 × 500 × 500, F_X 900 (`f0_hz`/`f0_v_hz`), first H anchor
900 Hz, CD band 900–8000 Hz. The key mapping follows `docs/research/compact_horn_system_2026-11-19/compact_xo900_identity.md` §1.1.
The priority (crossover-aware compact horn) was already grounded there, and that dossier is cited, not redone.
**Own J identity: never ranked against the 700 Hz home brief.** At F_X 900 the rule is LFP20 ≤ 562.5 Hz and
Re z ≥ 0.5 from 900 Hz.

[proxy] Seed fit with the mouth held at 484 mm wide (inside 500 with the 3 mm shell):
k 1.0 gives a load-raw estimate of ~0.50. **k 3.0, L 264.5, s 0.30** gives 484 × 361 × 265 mm and ~0.09 (LFP20 600,
LFP50 706, min Re z ≥ 900 Hz 0.74). That is the seed. `tools/shape_check.py`: 3,327 dofs, 484 × 360 × 268 mm, fits.

## 6. Applicability (grounding skill)

Family: OS-SE per-azimuth wall + superformula morph + curled lip (Contract B). The cone/OS loading rule and
the OS-k behaviour apply to this OS wall. They are **not** transferred to the ext-throat, Le Cléac'h or
biradial families. CD scoring is intended here: the brief and the construction are CD by design. Keele mouth
sizing is not used. The Webster numbers are plane-wave proxies, not BEM. Gap: the effect of the superformula
morph and curled lip on CD after a k change is untested (Contract B §B4 already notes CD is unproven after
morph + lip).

## 7. Queued GPU follow-up: night `fav_crowe_2026-11-20`

`docs/queue/fav_crowe_2026-11-20.yaml` (live copy `runs/nights/fav_crowe_2026-11-20.yaml`), chained behind
`cd_v11_verify_and_expand_2026-11-20` (queue.ps1 controller pid 52188, `-WaitPid 26752`), cutoff 23:30.

| # | job | what | read it as |
|---|---|---|---|
| 1–3 | `favk__k3/k2/k4_hold_mouth` | FAV-001 knobs with k = 3 / 2 / 4, depth re-solved for the same mouth; one screen solve each | **clean attribution**: what k buys in `load` and costs in the CD terms, same brief as FAV-001 (screen J 4.9965) |
| 4 | `fav__crowe_k_home` | CMA, 60 valid, home v11 brief, k unlocked [1, 5] + wider box, seed k 3 / L 286.7 | comparable with the cd11c screen lanes (ext_throat 3.294 screen) |
| 5 | `fav__crowe_c500_xo900` | CMA, 60 valid, compact500_xo900 brief, seed k 3 / L 264.5 / s 0.30 | own identity; compare only within it |
| 6 | `fav_verify_top3` | `verify_night_jobs.py --top 3` on jobs 4 and 5 | verify grid; rank within each brief only |

Preflight (`tools/search_preflight.py --samples 64`): no HARD. Uniform-box valid fraction 45 % (home)
and 33 % (compact, after tightening L to [190, 330], a_h to [32, 39], s to [0.2, 0.45]). Refusals are
envelope-only, free under `budget_counts: valid`, `max_attempts` 300.

**Success test for the owner's question:** a k > 1 design whose CD-matrix terms stay within ~10 % of
FAV-001's while `load` falls below ~1.0. If the CD terms degrade as fast as load improves, the answer is
"cross it at 900–1000 Hz and keep k = 1". The compact lane answers that directly.

## 8. Proposals (owner-gated; nothing changed)

1. **Loading excess/resonance term.** v11's one-sided `load` scores a 3 ρc throat resonance as perfect. Candidate:
   carry v6 `z_smooth` (std Re z above F_X) or a peak-to-trough ratio into a future CD identity. Rescore
   offline first, as v7 was.
2. **Crossover-aware F_X.** If the system crossover will be ≥ 900 Hz, a 900 Hz home identity (envelope unchanged)
   ranks the finalists by what the system will use (§2.1).
3. **GUI score breakdown** must list every weighted term of the run's objective version (v11 CD terms and
   `flat_cv`/`di_roughness` are missing). Issue logged.
4. **Favorites in the GUI**: a star toggle on the run page that writes `docs/favorites/FAVORITES.yaml`.

Sources: [diyAudio "Geddes on waveguides"](https://www.diyaudio.com/community/threads/geddes-on-waveguides.103872/) ·
[diyAudio "Acoustic Horn Design – The Easy Way (Ath4)" p. 228](https://diyaudio.com/community/threads/acoustic-horn-design-the-easy-way-ath4.338806/page-228)
· in-repo dossiers cited inline.

---

## Addendum 2026-11-20 15:23: k-attribution measured [measured, screen grid, same v11 home brief]

Night `fav_crowe_2026-11-20` jobs 1–3: FAV-001 knobs, only `g_k` changed (depth re-solved so the mouth holds 587 mm).
Weighted contributions; "non-load" = J − load.

| design | J | load | LFP20 / LFP50 Hz | min Re z ≥ 700 | cd_lw | cd_di_std | cd_nacc | off-axis | dislope | flat | non-load |
|---|---|---|---|---|---|---|---|---|---|---|---|
| FAV-001 (k 1) | 4.996 | 2.645 | 674 / 995 | 0.33 | 0.346 | 0.319 | 0.153 | 0.543 | 0.111 | 0.444 | **2.352** |
| k 2 (L 274.2) | **4.800** | 1.508 | 595 / 832 | 0.49 | 0.304 | 0.519 | 0.193 | 1.142 | 0.313 | 0.324 | 3.292 |
| k 3 (L 286.7) | 5.177 | 1.039 | 543 / 728 | 0.68 | 0.375 | 0.685 | 0.259 | 1.541 | 0.536 | 0.243 | 4.138 |
| k 4 (L 298.2) | 5.603 | 0.792 | 516 / 665 | 0.86 | 0.454 | 0.811 | 0.324 | 1.808 | 0.745 | 0.198 | 4.812 |

Read: the Webster proxy's loading prediction held (k 3: LFP50 728 vs proxy 673; min Re z 0.68). The ATH warning
also held. **Every step in k costs about as much directivity as it buys loading:** off-axis smoothness ×2–3,
DI std ×1.6–2.5, DI slope ×3–7. Only k 2 is a net J gain (−0.20), and it is a weaker horn on every CD-matrix
metric except listening-window deviation. With the other knobs frozen, k is not a free improvement. Whether
re-balancing the other knobs recovers the directivity is what `fav__crowe_k_home` (CMA, k ∈ [1, 5]) answers.
Practical reading for the owner: if FAV-001's directivity is the point, **keep k ≈ 1–1.5 and cross ≥ 900 Hz**
rather than buy 700 Hz loading with k.
