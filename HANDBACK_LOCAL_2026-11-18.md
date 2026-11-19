# HANDBACK (local orchestrator, 2026-11-18 late evening): the Fable GPU chain landed — what the senior needs

For the cloud Fable senior session. Everything below is **on GitHub** (`main` @ merge of PR #72+
carry, `hornfab-all-2026-11-18` identical). Base a fresh session on `hornfab-all-2026-11-18` or
`main`; do NOT reuse the stale `cloud/fable-next-2026-11-18` branch (provenance). Decisions R1-R25:
`scratch/fable_architecture/OWNER_DECISIONS_RESOLVED_2026-11-18.md` (tracked). Pointers:
`docs/ACTIVE_STATE.md` (verified tonight) and the two evening sections of
`HANDOFF_2026-11-18.md`.

## 1. What landed (one line each; every claim has a committed evidence file)

| Item | Result | Committed evidence |
|---|---|---|
| Integration D10/R21 | PRs #69/#67/#70/#71/#72 merged; #68 closed superseded | GitHub PR ledger; `docs/CONTINUITY.md` 2026-11-18 entries |
| Rescore WP 1.4/1.5 | v7/v9/v10 full-fleet reused byte-identically; shipped≡offline v10 (max \|ΔJ\| = 0.0, n=122); `mixed_identity` tool bug fixed, false everywhere | `docs/evidence/v10_rescore_2026-11-18/results/` (README + summaries + floors + sample + scripts) |
| Floors | v7 **0.310** (top-28-pair protocol) vs **0.13** published (tension recorded); v10 **0.4677**; slope5 **0.4863** | `results/floor_*.json`; tension in `NOTES_FOR_SENIOR.md` item 3 |
| B1 (WP 2.2) | **8/8 probes exit 0, no Shared-Usage spill** (shared 80 MiB const; peaks ~2.6-3.0 GB dedicated); dJ −0.003…−0.0252; 6/8 mesh-sensitive; leaders 3a1038/9fcd21 still outside the mesh floor (geometry refusal) | `docs/evidence/b1_mesh_2026-11-18/README.md` + `b1_probes_table.json` + `raw/` (refine.json, 8 memwatch JSONs, the two night-queue logs) |
| WP 2.3 combined floor | mesh part **sd(dJ) 0.00768 J**; combined sqrt(freq²+mesh²): v7 0.1302 (D8 basis) / 0.3105 (protocol basis); v10 0.4677; slope5 0.4863 — frequency-dominated | `docs/evidence/b1_mesh_2026-11-18/floor_record.json` |
| WP 4.2 | record-route equivalence **PASS** on the biradial host (max band delta 0.76° of the 1° bound) | `docs/evidence/wp42_u3_biradial/equivalence.json` + CSVs |
| WP 4.3/B2 | 5 tool-valid variants solved; **vt_460: real V-plane authority +32.32° (1.1-2.5 kHz, H −5.1° secondary) at +2.30 J cost**; 4 freedoms inert; vt_480/term_sides excluded by the validity table | `docs/evidence/wp43_b2_authority/README.md` + authority.json + CSVs |
| WP 4.4 | vt-knob proposal recorded (gated: senior verdict + owner bounds/slot consent) | same README §proposal |
| D6 anchor | ST260 config corrected to the device STL (a0 9.45°, k 2.13, m 0.86, q 5.05; 0.08 mm RMS); **no admissible measured build** → R4 fallback recorded; ST260 not solved; 2 anchor solves unspent | `docs/evidence/anchor_st260_2026-11-18/README.md` + `measured/ST260-19.stl` + the dossier's outcome §6 |
| Throat (2b) | rho15 no-authority verified; **rho20 authority TRUE (3.12° H top band)** — CONTRADICTS §10.2's inferred row (senior item 1); Phase3 vs B_o50 verified no | `docs/evidence/throat_hv_2026-11-18/authority_*.json` + CSVs |
| Night causes (WP 0.7) | 9/9 ids decoded **UTF-8** (the §8 recipe's UTF-16 premise was wrong — corrected); klame/silent-exit classes; fix candidates → shipped | `docs/evidence/night_cd_rrect_2026-11-17_REVIEW_2026-11-18.md` §causes |
| WP 0.9/D9 | surfaceFit echo + fallback flag; `record_digest` block (gates); `build_box_m`; classify tool — real-tree counts 48,471 rebuildable / 3 bridge / 0 refused / 0 unverified | `docs/evidence/wp09_d9_provenance_2026-11-18/classify_summary.json`; code + tests merged |
| WP 0.7 hardening | unbuffered child env; prepare_study builders guard; run_bo_arm child tail; the two order-dependent wrapper tests fixed at the real Popen surface | code + tests; focused suites 55/55 |
| Queue state | cd_rrect drained; owner trimmed it to Fable-only; atlas BoTorch arms PAUSED (owner:BoTorch resumes only with a 100+ CMA cohort + approval); w-lane continuations removed (rows preserved) | `runs/nights/*.bak-20261119-fable-trim` (local); ledger quoted in CONTINUITY |
| Ext-throat w1 lane | resume2 finished (budget end): best J 5.7239 (`104ea26b21ca`, 135 rows) | `runs/20261118T212720Z-screen-c017db/` (local; the summary is in CONTINUITY) |

## 2. Senior review queue (data on disk, verdicts needed)

1. **rho20 vs the "rho inert" park (G5):** marginal single-band H authority (3.12°, 2500-5500).
    Decide the U3 borderline-band policy; §10.2 rows were intentionally NOT rewritten.
2. **v7 floor 0.310-vs-0.13 protocol reconciliation:** top-28-pair protocol vs the D8 record;
    every tie call downstream cites whichever you re-pin.
3. **Verify today's judgment calls** (each documented in its evidence README): mixed_identity
    semantics (= score payload minus per-design metric part); B1 mesh-part = sd(dJ) (not max) and
    the 0.0057 sensitivity reading; the 166-design stratified sample sufficing for the shipped v10
    column; the ST260 correction basis (device STL > rev7 paper); the legacy-schema
    `rebuildable` class for 30,147 pre-generator records; WP 4.4 vt bounds ~[440, 465].
4. **WP 4.3's steer_early/steer_late intent planes:** `INTENDED` maps them to ("h","v") both —
    confirm that matches your predeclaration (the tool's table was built from the senior plan).

## 3. Owner questions still open

B6 budget + lanes (fold_warm / morph / ext_throat_v7 under v10; R19 `__space_v1` at queue time;
record_gate shadow on ext_throat per R20b); WP 4.4 vt bounds + slot; BO `_r2` arms (R15 gate
unmet: the anchor failed); range15 brief migration (4 orphaned queued jobs — v10 re-home is
semantically exact); the fallback-anchor dossier (ATH CORE / Tritonia) which unblocks R1
(nights' score) and D6 step 2.

## 4. What is NOT on GitHub (owner-box only) and why

`runs/**` and most of `scratch/**` are gitignored by policy. The senior can verify every claim
against the COMMITTED summary/table artifacts listed above; full row files stay local
(rescore.jsonl quoted by row count instead of committed, per the v10 README acceptance). Raw B1
records + the two night-queue logs were copied into `docs/evidence/b1_mesh_2026-11-18/raw/` for
byte-level review. Anything else needs the owner box (runs/ reads, GPU, memwatch).

## 5. Critical path from here

Senior verdicts (§2.1-2.2) → owner (B6 budget; vt consent) → B6 matched reruns under v10 →
fallback-anchor dossier → R1 nights-score decision → D6 step 2 print plan unblocks → finalists
(6.3) → deliverable. WG 6.1 (BoTorch) parked per owner.
