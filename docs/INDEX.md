# Docs index

Start here. Code map: [`CODE_MAP.md`](CODE_MAP.md). Rules for agents: [`../CLAUDE.md`](../CLAUDE.md), [`../AGENTS.md`](../AGENTS.md).
Keep this file current: a new doc gets a line here in the same commit.

## Read first (current state)
| Doc | What it is |
|---|---|
| [CONTINUITY.md](CONTINUITY.md) | Status block + dated log, newest first. The source of truth for "where are we". |
| [ISSUES.md](ISSUES.md) | Open issues and the TO-DO list (next-round priorities at the top). |
| [FORKS.md](FORKS.md) | How we change Magnus's solver/mesher: pinned forks in `..\forks`, install by SHA, validation ladder (owner decision 2026-10-24). |
| [NEXT_DEV_PRIORITIES.md](NEXT_DEV_PRIORITIES.md) | Post-beta priorities: P1 fused CUDA assembly, P2 12 kHz pass, P3 Metal backend. |
| [HANDOFF_BETA.md](HANDOFF_BETA.md) | Current agent handoff: beta-readiness pass, items A–G, stop conditions. |
| [HANDOFF_COLLABORATOR_2026-10-23.md](HANDOFF_COLLABORATOR_2026-10-23.md) | For the collaborator pulling `main` on 2026-10-23: setup, what runs on the GPU box, files the owner edits tonight, rules, open questions. |
| [BETA_QUICKSTART.md](BETA_QUICKSTART.md) | First loop for beta testers: brief → campaign → report → STEP. |
| [BETA_SESSION_PLAN.md](BETA_SESSION_PLAN.md) | Beta session agenda, GPU etiquette, known limits, what not to try. |
| [GUI_PLAN.md](GUI_PLAN.md) | Local web GUI: goals, constraints, views, API, prior art (waveguide-generator, Boundary Lab). |
| [BETA_SESSION_PLAN.md](BETA_SESSION_PLAN.md) | Beta-day agenda (if present; written by the beta pass). |

## Design and plans
| Doc | What it is |
|---|---|
| [plan/](plan/README.md) | **Frozen** original plan and contracts (`00_ORCHESTRATOR`, `01_CONTRACTS`, task files 02–12). Never edit. |
| [TYPOLOGY_PLAN.md](TYPOLOGY_PLAN.md) | v2: classical typologies as generators, hybrids, briefs, campaign tiers, verification ladder. |
| [SENIOR_ARCHITECTURE_REPORT_2026-10-22.md](SENIOR_ARCHITECTURE_REPORT_2026-10-22.md) | Where the repo sits vs Boundary Lab / HornLab; priority decisions. |
| [BOUNDARY_LAB_INTEGRATION_PLAN.md](BOUNDARY_LAB_INTEGRATION_PLAN.md) | Proposed Boundary Lab export / cross-check (not started). |
| [BL_LEARNINGS_IMPLEMENTATION.md](BL_LEARNINGS_IMPLEMENTATION.md) | Boundary Lab learnings implemented (mesh checks, phasor, provenance, SPDI). |
| [HIGH_FREQUENCY_OPTIONS.md](HIGH_FREQUENCY_OPTIONS.md) | Reaching 12 kHz on 8 GB: options and evidence. |
| [CLOUD_GPU_REPORT.md](CLOUD_GPU_REPORT.md) | Cloud GPU rental research. |
| [HANDOFF_LOCAL.md](HANDOFF_LOCAL.md), [HANDOFF.md](HANDOFF.md) | Older handoffs (CP-8, 6b test plan). Historical. |
| [SENIOR_REVIEW_2026-10-14.md](SENIOR_REVIEW_2026-10-14.md) | Surrogate-fix review. Historical. |

## Research
| Doc | What it is |
|---|---|
| [research/typologies/MESHER_TYPOLOGIES.md](research/typologies/MESHER_TYPOLOGIES.md) | What Magnus's mesher implements (OSSE, R-OSSE, ICW, FREEFORM, LOOKUP), file:line. |
| [research/typologies/SEARCH_LAYER_GAPS.md](research/typologies/SEARCH_LAYER_GAPS.md) | Search-layer coverage vs the mesher. |
| [research/senior_pass_2026-10-24/](research/senior_pass_2026-10-24/README.md) | Senior pass 2026-10-24: objective/assumption audit, new typologies + multi-cell, 12 kHz routes, implementation plan (WP1–WP14). |
| [research/TIME_DOMAIN_RINGING.md](research/TIME_DOMAIN_RINGING.md) | Ringing / waterfalls: what we can see, stage-2 design. |
| [BOUNDARY_LAB_0.5_RESEARCH.md](BOUNDARY_LAB_0.5_RESEARCH.md), [research/boundary_lab_0.5/](research/boundary_lab_0.5/) | Boundary Lab 0.5.0 findings and inventories. |

## Evidence (measured results; `evidence/README.md` explains the rules)
| Doc | What it is |
|---|---|
| [evidence/SOLVER_VERIFY_2026-10-22.md](evidence/SOLVER_VERIFY_2026-10-22.md) | GPU tests, analytic sphere, GPU vs CPU cross-check. |
| [evidence/TYPOLOGY_VERIFY.md](evidence/TYPOLOGY_VERIFY.md) | Typology ladder V1–V5. |
| [evidence/TYPOLOGY_SCREEN_2026-10-22.md](evidence/TYPOLOGY_SCREEN_2026-10-22.md) | First fair screen campaigns + reading. Raw: `evidence/campaigns/`. |
| [evidence/BETA_READINESS.md](evidence/BETA_READINESS.md) | Beta pass audits (if present). |
| `evidence/TYPOLOGY_COMPARE_2026-10-23.md` | Compare tier (2 seeds): rankings that stand, bound-limited families, bound proposals. |
| [evidence/HANDOFF_6b.md](evidence/HANDOFF_6b.md), [evidence/BL_LEARNINGS_GPU.md](evidence/BL_LEARNINGS_GPU.md), [evidence/EARLY_REJECTION_REPLAY.md](evidence/EARLY_REJECTION_REPLAY.md) | FREEFORM sculpt tests; PR #15 GPU plan; early-rejection replay. |
| [evidence/CP-8a.md](evidence/CP-8a.md) … [CP-8d.md](evidence/CP-8d.md), `CP-8c_*.md` | CP-8 checkpoint outputs (dataset campaign, surrogate gates). |
| `evidence/runs/` + `manifest.sha256` | Summary layers of GPU runs (logs, not raw data). |
| `evidence/BETA_READINESS.md` | Beta readiness pass: SHAs/upstream, data integrity, physics audit (C2 epw 6 vs 8). |
| [evidence/OBJECTIVE_V2_RESCORE.md](evidence/OBJECTIVE_V2_RESCORE.md) | WP1 re-score: v1 vs v2 objective over 18,059 stored records; Spearman rho 0.989; both compare-tier claims survive; v1 drift 0. Per-record CSV local (regenerate with tools/rescore). |
| [evidence/HF12K_VERIFY_2026-10-23.md](evidence/HF12K_VERIFY_2026-10-23.md) | P2 12 kHz finalist verify pass: epw check at 12 kHz, beamwidth/DI to 12 kHz, VRAM; cross-mode caveat. |
| [evidence/CP-8d_retrain_2026-10-23.md](evidence/CP-8d_retrain_2026-10-23.md) | Surrogate retrain after the OSSE top-up: every gate vs threshold, held-out 463 < 500; model not used. |

## Elsewhere in the repo
`../README.md` (install, commands, known limits) · `../TOOLCHAIN.md` (pinned SHAs, measured machine numbers) ·
`../CONTRIBUTING.md` · `../NOTES_FOR_SENIOR.md` (append-only rulings and questions) · `../examples/catalog.yaml`.
