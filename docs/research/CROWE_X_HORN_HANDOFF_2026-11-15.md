# Handoff: design the owner's "Crowe-style X" landscape home horn cells (2026-11-15)

**For:** the next agent. **From:** a session that made too many wrong guesses on this. Read all of it before you
touch a config. The owner is (rightly) out of patience: every shape you show must already have been compared,
side by side, against Joseph Crowe's actual images, and must pass the checks in §6.

---

## 1. What we are designing (the target)

**Purpose.** A printed compression-driver horn for the owner's **home hi-fi** living room (two horns, front
corners, toed in; DSP available). Driver: **FaitalPRO HF1440, 1.4-inch, exit radius 18 mm** (round throat, no
adapter). Crossover **700 Hz**.

**Brief (use it, don't edit it):** `examples/briefs/home_landscape_2026-11-15/room_landscape_80x50_700_hf1440_v7.yaml`
- Target **80° H × 50° V**. The owner's acceptable range is **60-90 H, 40-60 V**. **Vertical matters less than
  horizontal** (the brief has `objective.cov_v_weight: 0.5`).
- Envelope **600 mm W × 480 mm H × 480 mm deep (LANDSCAPE)**. 780 mm tall is too big.
- Objective v7 with `flat_band: scored` (on-axis flatness from the crossover up).

**The look the owner wants (owner's words 2026-11-15, paraphrased):**
1. **Like Joseph Crowe's ES Bi-Radial horns** (ES-450 / ES-600). Photos and drawings: §2.
2. An **"X" shape**: between the first (too extreme) and the mild (too round) versions this session made.
3. **More pucker** in the mouth: ATH-style creases/ridges from the throat toward the mouth corners.
4. **Straighter sides**: the owner does NOT like curved/bulging sides.
5. **More roundover** (a thick rolled lip all round, like Crowe's 270° wrap-around mouth).
6. **Landscape** (wider than tall). Never portrait.
7. Not spiky, not flower-like, not stars. Smooth surfaces (diffraction ∝ surface 2nd derivative: Geddes).

## 2. The reference: Joseph Crowe's ES Bi-Radials (study these, don't guess)

Downloaded locally for study (copyrighted; **do not commit**): `scratch/crowe_ref/` (28 images). Contact sheet:
`scratch/crowe_x_attempts/crowe_reference_contact_sheet.png`. Most useful:

| File | What it shows |
|---|---|
| `es450_1939_008.png` | ES-450 straight-on front: the **X / bow-tie of creases** from the throat to the four corners; top and bottom walls are two big lens/eye-shaped surfaces spanning almost the full width; the side walls are narrow wedges at the far ends |
| `es450_1939_007.png`, `_006`, `_001` | 3/4 views: **waisted (concave) body sides**, thick rolled top/bottom lips, X creases |
| `es450_1939_005.png` | cut-away of one half: wall thickness, the lip roll, the throat region |
| `es450_1939_016.png`, `_015` | **dimensioned drawing**: **542 W × 299 H**, horn depth **238** (337 incl. driver). Roughly 1.8 : 1 |
| `es450_prod_1..5.png` | rendered on a cabinet: overall proportions, the rolled mouth |
| `es600_Section.JPG` | **horizontal section** of the ES-600: a narrow throat whose walls curve continuously outward (exponential "ES flare") and **roll back past 180°** into a thick lip; no straight cone, no flat flange |
| `es600_section_iso.JPG`, `es600_front.JPG` | ES-600 3D section and front |

**Published facts** (josephcrowe.com technical library; browser pane works, WebFetch gets HTTP 429):
- **ES-600:** 417 W × 203 H × 198 D, 1.4" throat, 600 Hz-20 kHz, "ES flare" = exponential, "full 270 degree wrap
  around horn mouth", golden-ratio proportions.
- **ES-450:** 450 Hz cutoff, crossover 600-800 Hz, throat matched to the driver (no conical adapter).
- **Measured on the ES-600 with a Faital HF1460** (1.4"; report page "Faital HF1460 ... ES-600 Biradial Measurement
  Report"):
  - loading from ~500 Hz;
  - 0°/15° nearly identical, 30° -2..3 dB, 45° -4..10 dB above 2 kHz;
  - treble falls ~6 dB/oct from 5-10 kHz;
  - very low distortion.

His exact geometry is unpublished. Label cells **"Crowe ES-style"**, never as his design (R9 rule in `CLAUDE.md`).

**Anatomy, as seen in his images.** Use this as the checklist your render must match:
- (a) Rectangular-ish ~1.8:1 mouth.
- (b) Four creases running from the round throat diagonally to the four mouth corners (the X).
- (c) Corners pushed out, so the middles of the top, bottom and sides are relatively pulled in: a gently waisted /
  bow-tie outline.
- (d) Walls that are a continuous exponential-like curve from the throat, curving out and **rolling back** into a
  thick rounded lip all round.
- (e) Near-straight edges between the corners. No bulging.
- (f) Depth ≈ 0.45 × width (238 of 542).

## 3. Mistakes this session made: don't repeat them

1. **Keele / K-law mouth sizing produced portrait horns.** The old 80×60 cells used `25.4e6/(angle·f)` as the morph
   target (500 W × 660 H) with one wall angle all round, so the vertical pattern came out wider than the horizontal.
   **Never size the mouth with the K-law.** For `typology` / `grid` generators set **`generator.seed_policy: explicit`**
   (it must be INSIDE the `generator:` block; at the top level it is silently ignored and the brief's f0 re-derives
   the mouth with the K-law; that turned a landscape Bi-Radial square).
2. **Matched specs, not shape.** The first "ES-style" cells copied size/aspect/rollback (Le Cléac'h `iwata_ar`
   rows: elliptical section) and looked nothing like Crowe. Elliptical/round cross-sections can never make his
   corner creases.
3. **Extreme first seeds:** 8-lobe ridges, salmon X flutes, sharp superformula X stars. The owner rejected them.
   Then **over-corrected** to mild, round, bulgy shapes, which were also rejected (no pucker, curved sides).
4. **Straight cone + flat lip** (`osse_rollback` with `s = 0`): reads as a funnel with a flange, not Crowe's
   continuous flare.
5. **`s` too large** (0.8-1.2) fixed the front view but made the side a flat disc on a short funnel, and the mouth
   **too wide** (625-780 mm > 600).
6. Showed shapes without a side-by-side reference comparison. **Always compare to §2 before showing the owner.**

## 4. Where it stands: best leads

Generator that has all the needed controls: **`grid` rows type `osse_rollback`** (`hornlab_search/design/generators/
grid.py`, `ROWS_OSSE_ROLL_KNOB_DEFAULTS`, `_rows_osse_rollback_knobs`, `_rows_osse_rollback_marches`). Per azimuth φ:
an OSSE wall `a(φ) = a_h cos²φ + a_v sin²φ` (Magnus's `profile_points`), an optional superformula radius morph
`r *= 1 + sf_amt · w(s) · (sf(φ)/mean(sf) − 1)` with `sf(φ) = (|cos(mφ/4)|^n2 + |sin(mφ/4)/ab|^n2)^(−1/n1)` ramping in
after `sf_start` (fraction of arc length), then a tangent-continuous curled lip (`r_lip_mm`, `wrap_deg`, max wrap 200).

| knob (prefix `g_`) | effect seen in renders |
|---|---|
| `a_h_deg` / `a_v_deg` | wall angles H / V; set the overall width/height (H > V for landscape) |
| `s`, `n`, `q`, `k` | OSSE termination. **`s` = 0 → straight cone** (wrong). `s` 0.8-1.2 → strong outward curve near the mouth (Crowe-like front, but disc-like side and too wide). Try **0.3-0.6 with a longer `L_mm` (260-320)** |
| `sf_m` 4 | four corners (X) |
| `sf_n1` | corner sharpness / waist: 1.2 = spiky star (too extreme); 3 = round; **~1.6-2.0** = the in-between X |
| `sf_n2` | edge straightness: 4 = rounder/bulgy, **6-8 = straighter edges** |
| `sf_amt` | X strength: 0.6 extreme, 0.25 too mild, **~0.35-0.45** good |
| `sf_start` | where the X begins along the wall: **0.2-0.25** gives creases running from near the throat |
| `sf_ab` | stretch: < 1 = wider (landscape). 0.8 ≈ 1.5:1; **0.6-0.65 ≈ 1.8:1** (Crowe) but watch the 600 mm limit |
| `r_lip_mm`, `wrap_deg` | roundover: 30 / 90 = thin; **40-50 / 130-150** = thick Crowe-like roll |
| `L_mm` | depth; Crowe depth/width ≈ 0.45 |

Evidence on disk (configs keep absolute brief paths; renders = front 3/4, straight front, side, with the Crowe
reference in row 1):
- `scratch/crowe_x_attempts/x_round1/` + `x_round1_sheet.png`: `s = 0` cones. **x6** (`n1 1.8, n2 7, amt 0.45,
  start 0.2, wrap 140, lip 45, a_v 22`) and **x3** had the best X and pucker, but a cone side and ~1.5:1.
- `scratch/crowe_x_attempts/y_round2/` + `y_round2_sheet.png`: x6 + `s` 0.8-1.2, `a_h` 28-32, `ab` 0.6-0.7.
  **y2 / y4 fronts are the closest yet to Crowe** (bow-tie, waisted, X creases, thick roll), BUT the side is a flat
  disc and the mouths are **625-780 mm wide** (over the 600 envelope).
- `scratch/crowe_x_attempts/z_round3_unchecked/`: the next planned step (`s` 0.4-0.6, `a_h` 22-26 / `a_v` 13-15,
  `L` 280-320, `ab` 0.6-0.65). **Written, never checked or rendered** (the owner stopped the session). Start here.
  Some z meshes were partly written to `scratch/zv_mesh/` before the stop; re-run, don't trust them.

Other cells in `examples/typologies/home_landscape_2026-11-15/`:
- In git: `hl__ext_throat_hvlaw_v7` (the BoTorch task, running in nights A/B; **don't edit it**),
  `hl__ath_core_petal_hvlaw_v7`, `hl__osse_rrect_morph_v7`, `hl__es_style_rollback_v7`, `hl__biradial_es_style_v7`,
  `hl__lecleach_iwata_ar_landscape_v7`.
- Untracked, from the late iterations: `hl__crowe_es_biradial_rr_v7` (typology generator, round → rounded-rectangle
  mouth with hypex walls; right 2:1 rectangle and corner creases, no lip, plain walls) and the mild
  `hl__ath_ridge8_hvlaw_v7`, `hl__petal_os_x4_landscape_v7`, `hl__chanterelle_sf_x4_stretch_v7`. The owner judged
  all of these "nothing like Crowe" or too plain. Treat them as material, not answers.
- Dropped: R-OSSE rounded-rect (mesh bore/shell crossing); salmon flutes (lumpy even when subtle).

## 5. Suggested approach

1. Base on `scratch/crowe_x_attempts/x_round1/x6...yaml` / `y_round2/y2...yaml` (`osse_rollback` + superformula X).
2. Fit 600 W first:
   - lower `a_h_deg`;
   - keep `sf_ab` ≈ 0.62-0.7;
   - lengthen `L_mm` (260-320) with moderate `s` (0.3-0.6) so the wall curves gradually, like `es600_Section.JPG`,
     instead of flaring into a disc;
   - target roughly **540-590 W × 300-330 H × 240-300 D** (Crowe's 542 × 299 × 238 fits the envelope almost exactly).
3. Pucker/X: `sf_n1` 1.6-2.0, `sf_n2` 6-8, `sf_amt` 0.35-0.45, `sf_start` 0.2. Roundover: `r_lip` 40-50,
   `wrap` 130-160.
4. If the side profile still can't match his continuous exponential-into-rollback curve, the generator may need a
   change. Two options: add the superformula X morph to the Le Cléac'h rollback rows (`iwata_ar` / `lecleach`, whose
   march IS an exponential-family curve that rolls past 180°), or add an exponential wall option to `osse_rollback`.
   Do it in a **worktree** with tests (§7).
5. Then make the cell searchable: bounds that keep the look; no star corners (`sf_n1` ≥ 1.5), `sf_amt` ≤ 0.5, `ab`
   0.6-0.8, W > H across the box. Budget 80, `sigma0` 0.2, `mesh.rear_res_factor: 1.5` (coarser outer shell only).

## 6. Checks before showing the owner (all required)

1. Shape check (CPU only):
   `.venv\Scripts\python.exe tools/shape_check.py --save-mesh scratch/<dir> <configs>`.
   Must read: `ok yes`, the envelope fits (W ≤ 600, H ≤ 480, D ≤ 480), `round, matches the exit`, W > H. Seeds
   should stay ≤ ~6k DOFs (cap 24k).
2. Render: `"%LOCALAPPDATA%/hornlab/vizenv/Scripts/python.exe" tools/render/render_views.py --out scratch/<r>
   --views a,c,s name=<dir>/<cell>/mesh.msh ...`.
3. Compose a sheet with **Crowe's `es450_1939_007`, `_008` and `es600_Section` in row 1** and your candidates below
   (the snippet that builds it is in this session's history; matplotlib + PIL, crop to bbox). **Look at it and check
   §2 (a)-(f) honestly** before sending it to the owner (SendUserFile).
4. Only after owner approval: add the cell(s) to night C (below) and queue.

## 7. Operating rules (they bite)

- **A GPU night is running from the main checkout `C:\Users\hunte\Hrns\hornlab-search`.**
  - Night A (`home_landscape_a_2026-11-15`) is running. Night B (`home_landscape_b_2026-11-15`, BoTorch scalar /
    TuRBO / Pareto studies) waits on A.
  - **Never** start a GPU job, `gpu-clean`, `hornlab-search search/run/verify` or `studies.cli run --execute`
    yourself.
  - `shape_check.py` and rendering are CPU-only and fine.
- **BoTorch studies pin a sha256 of every `hornlab_search/**/*.py`.** Any generator/code change must go in a git
  worktree and be merged only after night B finishes (check `runs/nights/queue_home_landscape_b.log` /
  `tools/night_status.py`). Config files (`examples/`) are not pinned.
- **Night C** (`docs/queue/home_landscape_c_2026-11-15.yaml`, copied to `runs/nights/`) is **stopped / not queued**.
  The owner must approve the new cells first. Then edit the night file's jobs, copy it to `runs/nights/`, run
  `run_campaign_night.py --night ... --dry-run` and launch it detached behind night B:
  `tools/night_queue/launch_detached.ps1 -Script tools/night_queue/queue.ps1 -ScriptArgs "-Nights home_landscape_c_2026-11-15
  -WaitPid <night B controller or runner pid> -WaitMatch home_landscape_b -Log runs\nights\queue_home_landscape_c.log"`.
  Skill: `.claude/skills/hornlab-night-queue`.
- Branch: `feat/sab-home-2026-11-14` (local, not pushed). Another session has uncommitted edits in `AGENTS.md`,
  `.claude/skills/*`, `docs/CODE_MAP.md`, `docs/INDEX.md` and `tools/search_preflight.py`: don't commit those. Every
  pushed commit updates `docs/CONTINUITY.md` + `docs/ISSUES.md`.
- Owner plot style: rainbow 3 dB isobar bands with hairline contours.

## 8. Related context
- `docs/queue/HOME_LANDSCAPE_PLAN_2026-11-15.md`: the senior review. Covers why portrait happened, the queue
  surgery, the landscape brief, BoTorch > CMA (`docs/status/2026-11-15-bo-vs-cma/`), and the ATH law's useful part
  (the H/V cosine term, not the petal).
- `docs/research/ONAXIS_WEIGHTING_2026-11-14.md`: hi-fi scoring (`tools/analysis/hifi_rescore.py`).
- `docs/research/BO_GUI_HANDOFF_2026-11-15.md`: the separate BoTorch GUI handoff.
