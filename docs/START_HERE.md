# START HERE — task to first file

One-screen routing for hornlab-search. When a topic is unknown, search in this order:
[INDEX](INDEX.md) → [TOOLS](TOOLS.md) → [knowledge](knowledge/README.md) →
[research/README](research/README.md) → [evidence/CATALOG](evidence/CATALOG.md).

Before any acoustic, geometry, scoring or optimization decision, read the
[knowledge hub](knowledge/README.md) and the relevant family card. Never carry a formula, target
or heuristic across typologies.

## Task → first file

| I need to… | Open first |
|---|---|
| Start a session / find current work | [ACTIVE_STATE.md](ACTIVE_STATE.md), then [INDEX.md](INDEX.md) |
| Understand scoring v1–v11 and score identities | [SCORING_REFERENCE.md](knowledge/SCORING_REFERENCE.md) |
| Set coverage and avoid the corridor trap | [SCORING_REFERENCE §2](knowledge/SCORING_REFERENCE.md#2-coverage-modes) |
| Author or change a brief | [SCORING_REFERENCE §2–§6](knowledge/SCORING_REFERENCE.md#2-coverage-modes) (the old brief guide is historical) |
| Check family laws and knob ranges before bounds | [FAMILY_LAWS.md](knowledge/FAMILY_LAWS.md), then the [family cards](knowledge/typologies/) |
| Check a shape/config before spending GPU time | [TOOLS: check a config or shape](TOOLS.md#check-a-config-or-shape) + [shape_check.py](../tools/shape_check.py) |
| Plan or preflight a search | [TOOLS: plan a search](TOOLS.md#plan-a-search) + [search_preflight.py](../tools/search_preflight.py) |
| Queue, monitor or splice a night | [queue/README.md](queue/README.md) + [TOOLS: queue and monitor a night](TOOLS.md#queue-and-monitor-a-night) |
| Re-score offline under another brief | [SCORING_REFERENCE §7](knowledge/SCORING_REFERENCE.md#7-how-to-re-score-offline-no-gpu) + [TOOLS: re-score and replay](TOOLS.md#re-score-and-replay) |
| Understand BO identity and starts | [TOOLS: BO identity](TOOLS.md#bo-identity-encoding-and-metric-bo) + [research: BO studies](research/README.md#bo-studies-and-the-botorch-gui) |
| Find evidence for a family | [evidence/CATALOG.md](evidence/CATALOG.md) |
| Find the current research answer | [research/README.md](research/README.md) |
| Find a tool or exact command | [TOOLS.md](TOOLS.md) |
| Find the code behind a concept | [CODE_MAP.md](CODE_MAP.md) |
| Find a guide or a dated handoff | [INDEX.md](INDEX.md) sections “Guides” and “Handoffs” |
| Check the current GPU/queue state | [ACTIVE_STATE.md](ACTIVE_STATE.md) + [night_status.py](../tools/night_status.py) |

## The traps that cost time (2026-11-25 lessons)

1. **Corridor vs constancy.** In corridor mode, any beamwidth inside `[min,max]` costs exactly
   `0.0` and `preferred_deg` is never read. Flatness at a chosen angle is **not** measured unless
   the brief declares `objective.constancy`. Encode “80 ± 5° and flat” as a narrow corridor
   `[75,85]` plus constancy; constancy prices wobble but does not pull toward `preferred_deg`.
2. **Family laws before bounds.** Rolled axial relief ≤ 10 % depth and inward ≤ 15 % height
   (undocumented, code-only, commit `c2c91905`); relief windows disjoint and non-dormant;
   `width_lo > height_hi`; throat-turn box below rect-turn box. Inert knobs differ per mode —
   read [FAMILY_LAWS.md](knowledge/FAMILY_LAWS.md) before writing a box.
3. **Night watchdog / exit 75.** Default pin / no-gain / stall / refusal stops end exploration
   jobs at 25–85 rows. Exploration needs `no_gain_valid: 0`, `stall_valid: 0`,
   `pin_ignore: [...]` and a raised `refusal_max`. Exit 75 is the watchdog, not a crash.
4. **Live-night splice.** `runs/nights/<night>.yaml` is re-read before every job. Insert after
   the running job and validate with `tools/run_campaign_night.py --night <file> --dry-run`.
   `docs/queue/` is the committed copy, not the live plan. See
   [queue/README.md](queue/README.md).
5. **Offline re-score.** `replay_run_dir(run, hash, brief=...)` or
   `tools/analysis/rescore_identity.py rescore`. Only `exact_complete` rows may rank; never
   compare J across score identities. See [SCORING_REFERENCE §7](knowledge/SCORING_REFERENCE.md#7-how-to-re-score-offline-no-gpu).
6. **BO identity and starts.** Identity = brief + bounds. Snap Sobol/scrambled starts so
   `ActiveProjection` round-trips the seed hash; use one box per family so runs pool. See
   [TOOLS: BO identity](TOOLS.md#bo-identity-encoding-and-metric-bo).
7. **Generator identity.** Editing a family’s implementation-digest file orphans every saved
   recipe. New behaviour = new module plus byte-wise (CRLF) registration in `grid.py`,
   `mesh/build.py` and `generated.py`. See
   [hornlab-generator-family](../.claude/skills/hornlab-generator-family/SKILL.md).

## Current state

[ACTIVE_STATE.md](ACTIVE_STATE.md) is the pointer, not authority: verify it with
`tools/night_status.py --since-hours 48` and `git status`. Never treat a dated handoff as current
routing. Never rank J across objective versions; v7 is the night default, v10/v11 are opt-in
identities.

## Catalogs

- [INDEX.md](INDEX.md) — every doc by topic
- [TOOLS.md](TOOLS.md) — every live tool by task
- [knowledge/README.md](knowledge/README.md) — applicability hub
- [research/README.md](research/README.md) — current research answer by topic
- [evidence/CATALOG.md](evidence/CATALOG.md) — one-line outcome per evidence folder
- [queue/README.md](queue/README.md) — live versus committed nights
