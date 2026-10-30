# Handoff: next runs after the 2026-10-30 coverage atlas

For the next agent running GPU jobs in hornlab-search. Read `CLAUDE.md`, then the skills
`hornlab-night-queue` and `hornlab-gpu-job`. **One GPU job at a time; launch detached; never start a runner
while another is live.**

## 1. The idea in one paragraph

Re-gating the 6,322 stored designs showed that the gates weren't wrong about quality. They were
asking for one exact angle. 45 designs pass all gates against the brief's nominal coverage, 118
pass at H ±25%, and **150 pass when each horn is judged against its own median in-band
beamwidth**. A manufacturer works the same way: build the horn, measure it, publish its
coverage. So the searches now **map coverage** with CMA-ME (quality-diversity,
`search.algorithm: cma_me`). The archive keeps the best design per 10°×10° cell of mean -6 dB
beamwidth (H, V) instead of converging on one brief.

## 2. Results so far (night of 2026-10-30)

| Atlas run | Family | Rows | Occupied cells | Self-referenced all-gate passes | Brief-gate passes (A1) |
|---|---|---|---|---|---|
| `runs/20261030T064105Z-screen-1206a5` | H-OSSE / V-hypex hybrid, 1.4" (b2w brief copy, 650×650×520 envelope) | 981 (timed out at 4.5 h) | 34 | **17** (49×40 … 90×61) | 16 |
| `runs/20261030T111108Z-screen-377bbe` | native ATH CORE, 2" | 501 | 43 (13 before) | **8** (39×44 … 73×73) | 12 |
| `runs/20261030T063601Z-screen-333d6d` | first hybrid launch, 380×300 envelope, stopped | 44 | merged into the hybrid row above | | |

For comparison, every earlier hybrid run together produced 3 brief-gate passes.

- Elites list: `scratch/atlas_2026-10-30/atlas_elites.csv`.
- Readout: `scratch/atlas_2026-10-30/readout.py`. It re-gates against each horn's own coverage;
  loading, DI and throat come from the A1 CSV unchanged.
- Configs: `examples/typologies/atlas_2026-10-30/`.
- Hybrid brief copy: `examples/briefs/atlas_2026-10-30/`.

## 3. Running now (day queue, launched 12:04 local, controller pid 22016, cutoff 16:15)

Log: `runs/nights/queue_2026-10-30_day.log`. Status: `.venv\Scripts\python.exe tools/night_status.py --since-hours 8`.

1. **`next1_verify_elites`** re-solves the 25 elites at verify fidelity. `runs/elites_20261030_hypex`
   (17) and `runs/elites_20261030_ath_core` (8) are elite-only run dirs: `config.yaml`, `run.json`,
   the elite rows, and hardlinked `designs/`. So `verify --top N` re-solves exactly those
   designs, and its output lands in `<dir>/verify/`.
2. **`next2_hypex_resume`** adds 400 new evaluations to the hybrid atlas (resume, so the replay is
   all cache hits).
3. **`next3_core_law_close`** runs the CORE-law atlas (300 evals), then the close-out:
   - A1 audit of `20261030T*-screen-*`, written to `scratch/gate_audit_atlas_2026-10-30/`;
   - A1 audit of `elites_20261030_*`, written to `scratch/gate_audit_elites_2026-10-30/`. Verify
     rows replace screen rows, so **this is the verified scorecard**;
   - `readout.py`, which refreshes `atlas_elites.csv`;
   - `export-step` STEP solids of both elite sets, written to `runs/elites_20261030_*/step/`.

If the cutoff drops night 3, run its close-out commands by hand. They're CPU only and safe when
no night is live.

## 4. What to do next, in order

1. **Read the verified scorecard** (`scratch/gate_audit_elites_2026-10-30/`). Last time, 6 of 10
   ath_core screen passes survived verify. Drop elites that fail at verify. Re-run `readout.py` if
   CORE-law finished.
2. **Render a coverage contact sheet** of the verified elites, one card per cell, using the
   `hornlab-render` skill. That's the "catalog" deliverable.
3. **Pick 1–2 print candidates.**
   - Prefer the hybrid 60×40 (`660c48c4dd7a`, J 2.75) or 61×38 (`d0409a2a7fe5`), and the ATH CORE
     50×50 (`28c0c6eff6c3`, J 2.44).
   - The STEP files are in `step/`. Check printer bed size; mouths run up to ~650 mm.
   - A measured print is worth more than another night of solves.
4. **Next GPU night: fill the gaps in the map.**
   - **Extend.** Resume the ATH CORE atlas (`runs/20261030T111108Z-screen-377bbe`, +400) and the
     CORE-law atlas, the same way as `next2`.
   - **New families.** Run new atlases on the families with self-referenced passers in the old
     audits: `osse_ext_throat` (20 passers; hardened v5 cells, 18-point grid at 10 m, ~46 s/eval,
     so budget 200) and `osse_morph_b1w_round` (4). Copy the cell into
     `examples/typologies/atlas_<date>/`, change only `name` and `search:`
     (`algorithm: cma_me`, `qd` mean_bw_h/mean_bw_v with 18×18 bins, sigma0 0.25). Shape-check it,
     dry-run it, and launch it detached.
   - **Envelope.** If a brief's envelope refuses more than about 30% of candidates, copy the brief
     with a bigger envelope (the owner accepts up to 650×650×520). Never edit a brief a queued
     night uses.
   - **Budget from measurement:** hybrid ~14 s/eval, ATH CORE ~16 s/eval at screen (12 freqs,
     ~700–5,000 dofs).
5. **Don't spend GPU on these:**
   - b3a 80×80: its 827 Hz Re z dip is structural;
   - salmon flutes, fold, union, trumpet, golden, clover, rosette or star: 0–3% H/V over about
     1,000 rows;
   - cone_plughorn pattern claims: blocked until the cone source model lands (NEXT_DEV_PRIORITIES
     P0b).

## 5. Known limits and open owner items

- **The GPU is mostly idle** (4% busy, ~140 MB VRAM per solve at screen size). More throughput
  needs code, not settings:
  - the CPU second lane (`docs/research/CPU_SECOND_LANE_HARDENING_2026-10-28.md`, ~1.5–1.7× per
    night, needs the lock/hygiene change and the §12 owner decisions);
  - batching several candidates per GPU job.
  - Don't run two searches at once until that lands: every search takes `runs/.gpu.lock`, and the
    night runner kills every `julia.exe` before each job.
- **"Self-referenced" gating isn't in `tools/rescore/gate_audit.py` yet.** It lives in the scratch
  readout. Promoting it to a `--nominal own` flag is a small, worthwhile code change.
- **`verify` can only re-solve a run's top N by J,** hence the elite-only run dirs. A
  `--designs <hash,...>` option would remove that workaround.
- **Nothing from 2026-10-30 is committed.** That covers the atlas configs, the brief copy, the
  CONTINUITY entries, this handoff and the INDEX line. `runs/`, `scratch/` and `runs/nights/` are
  gitignored. Commit per CONTRIBUTING, with CONTINUITY and ISSUES updated in the same commit.
