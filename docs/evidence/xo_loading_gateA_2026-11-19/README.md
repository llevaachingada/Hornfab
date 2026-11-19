# Evidence: score-term audit and Gate A crossover-loading diagnosis (2026-11-19)

These are CPU, read-only outputs from replaying stored solves. They are copied here from `runs/analysis/` so a reviewer without `runs/` can check the numbers. Absolute local paths were rewritten as repo-relative.

**Reports**
- [Score-term audit](../../../scratch/fable_architecture/score_term_audit_2026-11-19/REPORT.md). It carries a correction banner, because its F6 finding is superseded.
- [Gate A](../../../scratch/fable_architecture/xo_loading_gateA_2026-11-19/REPORT.md), the current verdict.

| folder | produced by | what it holds |
|---|---|---|
| `score_term_audit/` | `scratch/fable_architecture/score_term_audit_2026-11-19/score_term_audit.py --topn 10` | term decomposition of the top-10 per lane under 4 briefs (A); corridor miss for the whole fleet (B); outermost vs main-lobe beamwidth (C); screen→verify floor attribution (D); the variant briefs |
| `gate_a/` | `scratch/fable_architecture/xo_loading_gateA_2026-11-19/gate_a.py` | complex z, \|Γ\|, levels per unit acceleration and per unit velocity, energy balance, and the 32-member driver bracket for the six audit designs; the duplicate-hash census |
| `xo_loading_report_six/` | `tools/analysis/xo_loading_report.py` (the reusable report-only tool) | the same six designs; the numbers match `gate_a/` |

**Key facts**
- **Parity:** the audit reproduces the published v10 column with max |ΔJ| = 0.0 on 271 designs.
- **Source convention:** stored levels are per unit throat *acceleration*. Per unit *velocity*, fold_warm's power at 828 Hz relative to 2 kHz is +2.8 dB, which equals 10 log10 of its Re z ratio.
- **Data consistency:** energy balance is 0.95–1.00 on every design and grid.
- **Under-loaded horns:** rosse and tritonia are 5–8 dB below 2 kHz at 643–828 Hz. That ranking holds for all 32 bracket drivers.
- **Duplicate hashes:** 205 hashes appear in more than one design directory, and 9 of those are on different meshes. The same hash is not the same field.
