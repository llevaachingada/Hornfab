# Budget compression-driver shortlist — audit against the HornFab evidence base

**Date:** 2026-11-19
**Status:** audit complete; no solves run, no config, generator, objective or contract changed.
**Scope:** judge a third-party budget driver shortlist (FaitalPRO HF146R, Beyma CD14Fe,
RCF ND850-2.0, SB Audience BIANCO-75CD-T, PRV D2200Ph/D2200Py) against what this repo already
records, and state which picks survive.

**Why this is not a typology-research task.** This audits an existing shortlist against recorded
evidence. It adds no typology, construction law, mounting concept or objective term, so
`hornlab-typology-research` is not triggered. It is an applicability check under
`hornlab-acoustic-grounding` plus a citation audit.

**Evidence labels used throughout:** `[in-repo]` verified in this checkout; `[published]`
manufacturer datasheet as recorded in-repo; `[retail]` retailer price as recorded in-repo (dated);
`[third-party claim]` asserted by the audited text and **not** verifiable here; `[computed]`
arithmetic from `hornlab_search/constants.py`.

---

## 1. Verdict

| Candidate | Claimed (audited text) | Repo grounding | Verdict |
|---|---|---|---|
| **FaitalPRO HF146R** | $195, 1.4", 700 Hz–18 kHz, "manufacturer recommends 900 Hz" | **Absent from the corpus.** No HF146R/HF146 entry anywhere; every `HF146*` hit is the unrelated HF1460 | Best *structural* fit (same 1.4" class), zero evidence. Unproven, not disproven |
| **Beyma CD14Fe** | $167.95, 1.4", "800 Hz minimum" | **Absent.** Sibling **CD14Nd** recorded at $262.95, 36 mm, min XO 800 Hz | Fails a 700 Hz objective. Acceptable only at 800–900 Hz |
| **RCF ND850-2.0** | $142.99 (Zoro), "independently measured, excellent to 8 kHz" | Recorded at **MAP $569 / MSRP $819**; 50.8 mm; **datasheet-only, no measurement** | Price is a 4× outlier; 2" exit cuts the model-valid band to ~4 kHz. Worst fit here |
| **SB Audience BIANCO-75CD-T** | $168.60, out of stock, "1 kHz recommended" | Absent | Self-excluding: 1 kHz XO vs a 700 Hz objective |
| **PRV D2200Ph / D2200Py** | ~$69.91, "~7 kHz top, budget a tweeter" | Absent (only D4400Ti / D3500TiH-Nd recorded) | Throwaway experiment only |

**Recommendation:** none of the five is evidenced. If the driver, exit class and 700 Hz crossover
stay as they are, **HF146R is the only pick that preserves the horn architecture** — and it must be
datasheet-verified and re-meshed, not assumed. If a *measured* driver is required, the only one this
repo can defend is the **HF1460**.

---

## 2. Four recorded facts that reframe the question

1. **Driver choice is not in the objective.** Owner addendum 2026-11-19: *"The real-driver owner
   decision is retired. Driver choice now matters only for absolute level and headroom, and that
   needs an impedance fit whichever driver is chosen."* (`NOTES_FOR_SENIOR.md:1277` `[in-repo]`)
   The Gate A bracket is a synthetic Sd/Mmd/Bl/fs/chamber sweep, not real drivers, and is
   report-only: *"REPORT-ONLY; never a score term"* (`tools/analysis/xo_loading_report.py:1`
   `[in-repo]`).
2. **700 Hz success is judged on the horn, not the driver.** v7 `load` is the lowest frequency where
   the *horn's* BEM throat resistance Re(z) reaches the target (`hornlab_search/objective/scalar_v7.py`,
   load term `[in-repo]`). The driver's own T/S loading is report-only
   (`docs/DRIVER_MODEL.md:9-13` `[in-repo]`). "This driver loads better at 700 Hz" is therefore not a
   quantity this toolchain measures or scores.
3. **Exit geometry is pinned to the driver and is not portable.** `r0` is pinned to
   `exit_radius_mm` (`hornlab_search/config.py:1254-1279` `[in-repo]`); the round-throat gate refuses
   a mesh whose driven patch is not round at 2×exit (`hornlab_search/mesh/throat_check.py:1-11,54-64`
   `[in-repo]`). Similarity scaling requires the source to scale too — *"keeping HF1440 throat fixed
   breaks similarity"* (`docs/knowledge/imported/HornFab_Research_Knowledge_Base_2026-11-16.md:464`
   `[in-repo]`).
4. **The 2° exit tangent is a simulation assumption, not a datasheet value.** *"Older 2° is a
   source-model assumption ... use round 35.8 mm exit at z=0"*
   (`docs/knowledge/imported/HornFab_Research_Knowledge_Base_2026-11-16.md:455` `[in-repo]`;
   `docs/research/HORNFAB_ACOUSTIC_TRUTH_MASTER_PLAN_2026-11-17.md:27,51` `[in-repo]`).

### 2.1 The measured driver basis is thinner than the audited text assumes

The audited text treats the HF1440 as the measured benchmark ("not established to the same degree as
the HF1440"). The repo says the opposite: HF1440 is itself unmeasured —
*"an unmeasured HF1440 interface"* (`docs/knowledge/contracts/crowe_v2a_and_crowe_x_osse.md:98`
`[in-repo]`), and *"A datasheet minimum is not a guarantee of every horn's 700-Hz headroom"*
(`docs/research/HORNFAB_ACOUSTIC_TRUTH_MASTER_PLAN_2026-11-17.md:51` `[in-repo]`). The only
**measured** compression driver in the corpus is the **HF1460**, on Crowe's ES-600:
*"loading from ~500 Hz ... Very low distortion"*
(`docs/research/typologies/SCORING_NON_CD_SOURCES_2026-11-15.md:81` `[in-repo]`). No number transfers
from HF1460 to HF146R.

---

## 3. Exit diameter sets the model-valid upper band `[computed]`

The v7 loading window ends at the driver-exit first cross-mode
(`hornlab_search/objective/scalar_v7.py:302-331` `[in-repo]`), and the solver's source is ideal only
below f11 (`docs/HIGH_FREQUENCY_OPTIONS.md:64` `[in-repo]`:

> "The solver drives a uniform plane source on the throat ... Above f11 a real compression-driver
> exit is not a uniform piston").

With `C_AIR = 343.0` and `BESSEL_J1P_11 = 1.8412` (`hornlab_search/constants.py:3,16` `[in-repo]`),
`f11 = 1.8412·343 / (2πa)`:

| Exit | Radius a | f11 |
|---|---|---|
| 1" (25.4 mm) | 12.70 mm | **7.91 kHz** |
| 1.4" HF1440 real (35.8 mm) | 17.90 mm | **5.62 kHz** |
| 1.4" modelled (36.0 mm) | 18.00 mm | **5.58 kHz** |
| 2" (50.8 mm) | 25.40 mm | **3.96 kHz** |

Consequence for the shortlist: choosing the 2" RCF moves the trust boundary from ~5.6 kHz to
**~4.0 kHz**. The 8 kHz response praised in the audited text lies *outside* what this solver models
with a uniform source — so that praise cannot be used to justify the pick in this toolchain, and a
700 Hz two-way handing off near 8 kHz would spend its top octave in the unmodelled region.

---

## 4. Candidate audit

### 4.1 FaitalPRO HF146R — $195 `[third-party claim]`

- **Repo:** no entry. HF146R/HF146 absent from
  `docs/research/COMPRESSION_DRIVER_LIBRARY_2026-10-28.md` (which covers 17 drivers) and from the
  2026-11-19 published-min-XO table (`NOTES_FOR_SENIOR.md:1268-1275` `[in-repo]`).
- **Structural fit:** 1.4" class, so it lands on the same `r0 ≈ 17.8–18.0 mm` cell. A re-mesh with
  the real exit radius, not a new architecture. This is its only per-by-current-design advantage.
- **Unverified:** exit dimension, diaphragm material, minimum crossover (the "900 Hz recommended,
  650 Hz with lower power" split), price. The audited text's *"ketone-polymer diaphragm"* is the
  repo's recorded **HF1440** attribute (`docs/research/typologies/mini_meh_2026-10-29/appendix_A_web_survey_raw.md:424`
  `[in-repo]`); it is not recorded for the HF146R and must not be transferred.
- **Verdict:** the only candidate that keeps the current horn geometry. Gate: datasheet exit
  diameter + published min XO, then re-mesh and fresh solves.

### 4.2 Beyma CD14Fe — $167.95 `[third-party claim]`

- **Repo:** CD14Fe absent. Sibling **CD14Nd** `[primary/retail]`:
  exit 36 mm (`COMPRESSION_DRIVER_LIBRARY:145`), PM-4 polymer, neodymium, 108 dB,
  600–17000 Hz, **min crossover 800 Hz @ 12 dB/oct** (`:160`), ~$263 US Speaker (`:163-164`), and the
  family judgement *"Cannot reliably cross below 800 Hz"* (`:696`), *"borderline for a 600 Hz horn"*
  (`:167`).
- **Nearest recorded 700 Hz ferrite sibling:** the 2026-11-19 table lists **CD-1114Fe at a published
  min XO of 0.7 kHz** alongside the HF1440 (`NOTES_FOR_SENIOR.md:1272` `[in-repo]`), exit class 1.4".
  That driver — not CD14Fe — is the family member the repo can cite for a 700 Hz target.
- **Verdict:** CD14Fe does not meet a 700 Hz objective on the family pattern. At 800–900 Hz it is a
  conservative value pick. If a Beyma ferrite is wanted for 700 Hz, audit **CD-1114Fe** instead.

### 4.3 RCF ND850-2.0 — $142.99 `[third-party claim]`

- **Repo:** exit 50.8 mm (2"), 3" Ti, neodymium, 110 dB, 220 W program, 500–20000 Hz, copper
  demodulation ring (`COMPRESSION_DRIVER_LIBRARY:371-400` `[published]`). **Price recorded at
  MAP $569 / MSRP $819** from SoundPro (`:396`, source row `:739` `[retail]`).
- **The audited $142.99 is a 4× outlier** against the recorded MAP, from a listing the audited text
  itself admits has inconsistent metadata (wrong weight). It is unverifiable here: `zoro.com`
  returned HTTP 403 to a direct fetch. Treat as a mislabeled SKU until a second retailer and the
  exact RCF model number confirm it. The derived "$286/pair" claim inherits the defect.
- **Measurement claim fails:** the repo records **no** ND850 measurement; the distortion remark is a
  datasheet claim about the copper ring (`:400` `[published]`). The one Crowe measurement in the repo
  is the HF1460 (§2.1). If a Crowe ND850 measurement exists externally it must be cited directly —
  it is not project evidence today.
- **Band cost:** §3 — 2" exit drops the model-valid band to ~3.96 kHz.
- **Verdict:** worst fit for a 700 Hz two-way in this toolchain, on unverified pricing.

### 4.4 SB Audience BIANCO-75CD-T — $168.60 `[third-party claim]`

- **Repo:** absent (`BIANCO`, `SB Audience`, `75CD` — no hits).
- **Self-excluding:** the audited text itself records a 1 kHz manufacturer recommendation and
  out-of-stock status. A 1 kHz minimum crossover cannot serve a 700 Hz objective, and the repo
  already has a 1.0 kHz datapoint in the same class (CDX14-3040, `NOTES_FOR_SENIOR.md:1274`
  `[in-repo]`).
- **Verdict:** excluded on its own quoted spec.

### 4.5 PRV D2200Ph / D2200Py — ~$69.91 `[third-party claim]`

- **Repo:** absent (`D2200` — no hits). The library's PRV entries are D4400Ti (~$120–130) and
  D3500TiH-Nd (~$180, 1 kHz min XO) (`COMPRESSION_DRIVER_LIBRARY:27-28,720` `[retail]`).
- **Verdict:** cheapest, tweeter-mandatory (~7 kHz top, per the audited text), no `Bl`/`Re`/`T/S`.
  Sensible only as a sacrificial prototype driver, not as the system driver.

---

## 5. Claims in the audited text that fail or remain unverified

| Claim | Status | Basis |
|---|---|---|
| "HF146R's lower-frequency distortion not established to the same degree as the HF1440" | **Fails** — inverts the repo. HF1440 is also unmeasured | `crowe_v2a_and_crowe_x_osse.md:98` `[in-repo]` |
| "RCF ND850-2.0 independently measured, low distortion to ~8 kHz" | **Unverified in-repo**; nearest Crowe measurement is HF1460 | `SCORING_NON_CD_SOURCES_2026-11-15.md:81` `[in-repo]` |
| "RCF ND850-2.0 at $143 — the deal to investigate first" | **Outlier** — 4× under recorded MAP $569; listing metadata inconsistent; 403 on fetch | `COMPRESSION_DRIVER_LIBRARY:396,739` `[retail]` |
| "Best for a loading-oriented horn" | **Category error** — loading is the horn's Re(z), not the driver | `scalar_v7.py` load term; `DRIVER_MODEL.md:9-13` `[in-repo]` |
| "HF146R ketone-polymer diaphragm" | **Unverified** — that is the recorded HF1440 attribute | `appendix_A_web_survey_raw.md:424` `[in-repo]` |
| "CD14Fe, 800 Hz minimum" | **Consistent with family**, but CD14Fe itself is absent; only CD14Nd is recorded | `COMPRESSION_DRIVER_LIBRARY:160,696` `[in-repo]` |
| "The existing HF1440 throat model should not simply be reused unchanged" | **Correct, and the repo is stricter** — similarity scaling requires the source to scale | KB `:464` `[in-repo]` |
| All five prices | **Unverified** — none checked against a fetched listing in this session | this audit |

---

## 6. Recommendation and gates

1. **Do not order on the RCF price.** A 4× MAP outlier with admitted bad metadata is a
   identification problem, not a bargain. Confirm model number + a second retailer first.
2. **If the architecture stays 1.4" / 700 Hz:** gate on **HF146R** — obtain datasheet exit diameter
   and published min XO, set `exit_radius_mm` to the real value, re-mesh (round-throat gate), and
   re-solve. Expect **no score change attributable to the driver**; expect level/headroom to be
   unresolved without an impedance curve (`NOTES_FOR_SENIOR.md:1267,1277` `[in-repo]`).
3. **If a 700 Hz Beyma ferrite is preferred:** audit **CD-1114Fe** — the only ferrite in the family
   the repo can cite at 0.7 kHz.
4. **If a measured driver is required:** the defensible candidate in-repo is the **HF1460**
   (Crowe ES-600, very low distortion, loading from ~500 Hz). It is the only measured CD the project
   holds, and it is not on the audited shortlist.
5. **No absolute level, headroom or "loads better at 700 Hz" claim** is supportable for any candidate
   until an impedance-curve fit or a measurement exists.

---

## 7. Source table

| Source | Used for | Provenance |
|---|---|---|
| `docs/research/COMPRESSION_DRIVER_LIBRARY_2026-10-28.md` | CD14Nd specs/price/XO (`:140-167`, `:696`, `:722`); ND850-2.0 specs/price (`:371-400`, `:710`, `:739`) | `[published]` + `[retail]`, access 2026-10-28 |
| `NOTES_FOR_SENIOR.md:1260-1277` | driver-open addendum; published min-XO table incl. CD-1114Fe 0.7 kHz; level/headroom-only conclusion | `[in-repo]` owner addendum 2026-11-19 |
| `hornlab_search/objective/scalar_v7.py:302-331` | exit-f11 as loading-window upper bound | `[in-repo]` read directly |
| `hornlab_search/constants.py:3,16` | `C_AIR = 343.0`, `BESSEL_J1P_11 = 1.8412` | `[in-repo]` read directly |
| `hornlab_search/mesh/throat_check.py:1-11,54-64`; `hornlab_search/config.py:1254-1279` | round-throat gate; `r0` pinned to exit radius | `[in-repo]` |
| `docs/DRIVER_MODEL.md:9-13` | driver model report-only; ideal throat source | `[in-repo]` |
| `docs/HIGH_FREQUENCY_OPTIONS.md:64` | uniform plane source; f11 ≈ 5.65 kHz for 17.78 mm throat | `[in-repo]` |
| `docs/knowledge/contracts/crowe_v2a_and_crowe_x_osse.md:98` | "unmeasured HF1440 interface" | `[in-repo]` |
| `docs/knowledge/imported/HornFab_Research_Knowledge_Base_2026-11-16.md:455,464` | 2° is an assumption; similarity requires source scaling | `[in-repo]` |
| `docs/research/typologies/SCORING_NON_CD_SOURCES_2026-11-15.md:81` | HF1460 measured: loading ~500 Hz, very low distortion | `[in-repo]` |
| `docs/research/HORNFAB_ACOUSTIC_TRUTH_MASTER_PLAN_2026-11-17.md:27,51` | 18.0 vs 35.8 mm mismatch; source fixed for geometry work | `[in-repo]` |
| `tools/analysis/xo_loading_report.py:1`; `docs/evidence/xo_loading_gateA_2026-11-19/` | bracket report-only, synthetic | `[in-repo]` |
| Audited text (chat, 2026-11-19) | candidate list, prices, claims | `[third-party claim]`; zoro.com fetch HTTP 403 |

---

## 8. What this document does not do

- It does not add or remove candidates from the repo's driver library, and it does not edit
  `COMPRESSION_DRIVER_LIBRARY_2026-10-28.md`.
- It does not run a solve, mesh or GPU job; the f11 figures are arithmetic, not BEM.
- It does not establish a driver preference for scoring: none of this enters `J`.
- It does not certify any price. Every price above is either `[in-repo]` dated 2026-10-28 or
  `[third-party claim]`.
