# Handoff for the collaborator: pulling the repo and finding the optimization data

Written 2026-10-27. Everything below is already on `main` of https://github.com/llevaachingada/Hornfab (commit `9bc046f`).

## 1. Get the code

```bash
git clone https://github.com/llevaachingada/Hornfab.git hornlab-search   # first time
cd hornlab-search
git checkout main && git pull origin main                                # if you already have it
```

`main` is the current branch; `unified-typologies` is identical to it right now. Start with `docs/CONTINUITY.md` (newest entry first) and `docs/INDEX.md` (every doc, one line each).

## 2. The data, no CUDA needed: `docs/data/campaign_v4_2026-10-27/`

| File | What it is |
|---|---|
| `evals.csv` | One row per evaluation (about 4,000). Columns: `cell`, `eval`, `ok`, `cached`, `J` (objective), `term_cov/rip/di/dislope/flat/load/distd/diag/penalty/total` (the tolerance-normalised terms), `p_*` (design parameters), and JSON arrays `freqs_hz`, `bw_h_deg`, `bw_v_deg`, `di_db`, `ripple_*`, `on_axis_db` (12-point grid, 500 Hz to 10 kHz). Refused candidates have blank J. |
| `cells_summary.csv` | One row per typology cell: family, seed J, best J, refusal rate, best eval number. |
| `best_designs.json` | Best parameters and terms for each cell. |
| `README.md` | Column definitions and caveats. |

Quick start:

```python
import pandas as pd, json
df = pd.read_csv("docs/data/campaign_v4_2026-10-27/evals.csv")
ok = df[df.ok]
print(ok.groupby("cell").J.min())                       # best J per cell
bw = ok.bw_h_deg.apply(json.loads)                      # horizontal -6 dB beamwidth per frequency
```

## 3. How to read it

- **J = sum(weight x term) + penalty.** Stored terms are normalised: raw value = term x tolerance. Tolerances are in `docs/evidence/OBJECTIVE_V4_TOLERANCES.md`; weights are in each cell's brief (`examples/briefs/campaign_2026-10-26_v4/*_v4.yaml`); design bounds are in the cell's config (`examples/typologies/campaign_2026-10-26_v4/*_v4.yaml`).
- **J is comparable only within a cell.** Each brief weights the terms differently.
- **Search method:** CMA-ES, one fixed seed per cell. Rows are in order, so you can plot J against `eval` for convergence. A "resume" extends the same run, so rows past about 100 are the second night.
- **Refusals:** many cells refuse 20-50% of candidates (invalid geometry); `b1w__biradial_keele` and `b3bw__biradial_keele` refuse about 90%, so their best J rests on very few valid designs.
- **Scoring code:** `hornlab_search/objective/scalar_v4.py` (terms), `hornlab_search/metrics/diagonal.py` (diagonal term). Why these terms and tolerances: `docs/research/V4_SCORING_REVIEW_2026-10-27.md` and `docs/research/V4_TOLERANCE_RESEARCH_2026-10-27.md`.

## 4. What is NOT in git

The raw material is about 22 GB (`runs/` 11 GB, solve cache 8 GB, dataset 2.4 GB): meshes, full acoustic responses, 3D renders. The solve cache is what would let you re-score the same designs under a different objective without CUDA. Sharing it needs a Hugging Face dataset repo (`tools/hf_sync.py`, tabled as P11 in `docs/NEXT_DEV_PRIORITIES.md`). Ask the owner.

## 5. Things still changing

- A second 100-evaluation resume night is still running. Re-run `tools/export_campaign_tables.py` (or pull again later) for the final numbers.
- Two cells need a re-run (`crease__osse_b1w`, `b2t__rosse_morph`), so their rows are short.
