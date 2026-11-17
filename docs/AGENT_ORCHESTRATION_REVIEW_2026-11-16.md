# Hornlab/HornFab — Agent Orchestration Performance Review

**Date:** 2026-11-16
**Reviewer:** Orchestrator (self-review; escalation of the owner's complaint)
**Scope:** OpenCode/oh-my-opencode-slim configuration, prompt overrides, skill wiring, and
session telemetry for the Hornlab/HornFab project (`C:\Users\hunte\Hrns` →
`C:\Users\hunte\Hrns\hornlab-search`).
**Explicitly out of scope:** rbassist. Its presets, append prompts, and skills are treated here
as *foreign config that leaks into Hornlab sessions* (finding F6), not as the subject.

**Purpose:** give a senior reviewing agent a single document with the evidence, the proposed
changes, the reasoning, the risks, and the validation plan. Nothing in this document has been
applied yet.

---

## 1. Executive summary

The complaint ("agents take too long, too many sub-agents, not reusing them, doing things a
sub-agent should not be needed for") is **confirmed by telemetry**, but the dominant cause is not
agent count. It is **prompt size**.

Five findings, ranked by measured impact:

1. **241 of the 244 steps with >600k-token prompts came from sessions launched in
   `C:/Users/hunte/Hrns`** — the container directory, not the repo. That directory has no
   `AGENTS.md` and no skill grants, so every session there explores blind across 10+ worktrees.
2. **The repo's own reading order mandates multi-hundred-KB documents.**
   `docs/CONTINUITY.md` is 844,727 bytes / 5,930 lines / 390 dated entries.
   `docs/ISSUES.md` is 407,673 bytes. `NOTES_FOR_SENIOR.md` is 125,130 bytes.
   `AGENTS.md` tells every agent to "start here". A single full read is ~210k tokens.
3. **Fan-out is high and mostly cold.** 191 child sessions in 7 days (110 fixer, 41 explorer);
   one root session spawned 27. Children average 111k input tokens to re-onboard
   (fixer 122k, designer 143k). `task_revive` is used 40 times per 30 days against 576 `task`
   calls — ~93% cold starts.
4. **rbassist rules are applied globally.** `orchestrator_append.md` (root scope, applies to every
   preset and every repo) is 100% rbassist/PySide content, ~950 tokens on every Hornlab turn.
5. **The model tiers are inverted at the top.** The shared preset runs the orchestrator and the
   `oracle` reviewer on `deepseek-flash` at `variant: max` — a cheap model with maximum reasoning
   tokens, which is slower without being more capable.

**Cheapest high-leverage fix:** a 40-line `AGENTS.md` at `C:\Users\hunte\Hrns` plus a reading-budget
amendment in `hornlab-search/AGENTS.md`. No model change, no behaviour change, no code change.
**Second:** move rbassist prompt blocks to rbassist project scope.
**Third:** dispatch discipline (direct-work threshold, lane cap, revive-first).

---

## 2. Method and evidence base

Everything below is from local files and the local OpenCode telemetry DB
(`~/.local/share/opencode/opencode.db`, queried read-only with `sqlite3`). Window = last 7 days
unless stated. The DB is 18 GB; queries were aggregate-only.

Files inspected:

| File | Size | Role |
|---|---|---|
| `~/.config/opencode/oh-my-opencode-slim.json` | 12,569 B | user config, 6 presets, ACP agents, council, fallback |
| `~/.config/opencode/opencode.jsonc` | 851 B | plugin registration |
| `~/.config/opencode/oh-my-opencode-slim/orchestrator_append.md` | 3,614 B | global prompt append (all presets) |
| `~/.config/opencode/oh-my-opencode-slim/fixer_append.md` | 3,492 B | global fixer append |
| `C:/Users/hunte/Hrns/.opencode/oh-my-opencode-slim.json` | 425 B | container project config |
| `C:/Users/hunte/Hrns/hornlab-search/.opencode/oh-my-opencode-slim.json` | 684 B | repo project config |
| `C:/Users/hunte/Hrns/hornlab-search/AGENTS.md` | 18,329 B | repo agent contract + reading order |
| `C:/Users/hunte/Hrns/hornlab-search/CLAUDE.md` | 9,815 B | binding rules |
| `C:/Users/hunte/Hrns/hornlab-search/docs/CONTINUITY.md` | 844,727 B | state log, 390 entries, newest first |
| `C:/Users/hunte/Hrns/hornlab-search/docs/ISSUES.md` | 407,673 B | issue log, newest first |
| `C:/Users/hunte/Hrns/hornlab-search/NOTES_FOR_SENIOR.md` | 125,130 B | append-only (newest last) |
| `C:/Users/hunte/Hrns/hornlab-search/docs/NEXT_DEV_PRIORITIES.md` | 60,638 B | work queue |
| `C:/Users/hunte/Hrns/hornlab-search/.claude/skills/*` | 8 skills | HornLab domain skills |

Measurement caveat used throughout: `session.tokens_input` counts **fresh (non-cached) input**,
not prompt size. Prompt size is `part.data.tokens.total` on `step-finish` parts. All "step context"
numbers below are the latter.

---

## 3. Findings

### F1 — Sessions run from the container, not the repo (highest impact)

| Directory | Root sessions (7d) | Fresh input tokens | Cost |
|---|---|---|---|
| `C:/Users/hunte/Hrns` | **53 of 58** | 61.4 M | $31.37 |
| `C:/Users/hunte/Music/rbassist-merge-cloud-local` | 4 | 27.6 M | $11.12 |
| `C:/Users/hunte/OneDrive/Documents/b` | 1 | 1.1 M | $0.55 |

And the sharpest single number in this review:

```
steps with prompt > 600k tokens, by session directory (last 7 days)
C:/Users/hunte/Hrns                              241
C:/Users/hunte/Music/rbassist-merge-cloud-local    3
```

**Mechanism.** `C:\Users\hunte\Hrns` contains no `AGENTS.md`, no `CLAUDE.md`, and no
`.claude/skills`. OpenCode therefore injects no project contract. The agent sees a directory with
`hornlab-search/`, ten `*-wt/` worktrees, `forks/`, `consolidation-backup-*`, `hf_stage_hunter*`,
`*.txt` scratch files, and must discover the real repo. `AGENTS.md` in the repo states the owner
amendment: *"all local HornLab work be consolidated into local `main` at
`C:/Users/hunte/Hrns/hornlab-search` … do not create new worktrees"*. From the container that
instruction is invisible.

Evidence of the resulting behaviour: one session titled **"Repo familiarization and status
research"** ran 490 hours of wall clock, 26 steps, 10 tools, and **10.2 M fresh input tokens**
(avg 543k, max 580k per step). Another, "Multiple-entry horn handoff execution", averaged
**829k tokens per step** across 8 steps.

**Why this matters more than the preset or the model:** every subsequent turn in such a session
re-processes that prompt. Prefill scales roughly with prompt length; at 500–800k tokens, each
step is minutes of prompt processing before any output. No model choice fixes that.

### F2 — The documented reading order mandates reading very large living documents

`hornlab-search/AGENTS.md` "Start here (reading order)" item 1 is `docs/CONTINUITY.md`,
described as "which wave we are in, last checkpoint passed, next step, blockers, measured
numbers." It does not say "read the newest entry". The file is 5,930 lines / 844,727 B.

Same class of file:

| Document | Size | Approx tokens | Ordering |
|---|---|---|---|
| `docs/CONTINUITY.md` | 844,727 B | ~210k | newest first, 390 entries |
| `docs/ISSUES.md` | 407,673 B | ~100k | newest first |
| `NOTES_FOR_SENIOR.md` | 125,130 B | ~31k | append-only, newest last |
| `docs/INDEX.md` | 85,409 B | ~21k | index |
| `docs/CODE_MAP.md` | 69,994 B | ~17k | map |
| `docs/NEXT_DEV_PRIORITIES.md` | 60,638 B | ~15k | priorities |

Read telemetry: `docs/CONTINUITY.md` was read 42 times in 7 days. Even at a modest average of
50k tokens per read, that is ~2.1 M tokens of prompt payload for one file.

**Step-size distribution, all sessions, last 7 days (16,887 steps with usage):**

| Prompt size | Steps | Share |
|---|---|---|
| < 200k | 9,698 | 57.4% |
| 200–400k | 5,285 | 31.3% |
| 400–600k | 1,660 | 9.8% |
| > 600k | 244 | 1.4% |

**42.6% of all steps ran above 200k tokens.** The 1,904 steps above 400k are the ones a human
experiences as "hanging".

**Why the fix belongs in `AGENTS.md`:** that is the one file both the orchestrator and every child
reads. One paragraph there ("read the first 40 lines of CONTINUITY, the first 40 of ISSUES, the last
60 of NOTES; never read these in full") propagates to all 191 child sessions without touching a
single prompt.

### F3 — Fan-out is high, and each child pays full onboarding cost

Last 7 days (children only):

| Agent | Sessions | Avg wall | Max wall | Avg input | Total input | Cost |
|---|---|---|---|---|---|---|
| fixer | 110 | 19.3 min | 318.1 min | 122k | 13.4 M | $11.15 |
| explorer | 41 | 10.0 min | 131.6 min | 111k | 4.6 M | $1.53 |
| observer | 14 | 3.1 min | 9.5 min | 14k | 0.2 M | $0.20 |
| oracle | 10 | 8.2 min | 31.8 min | 118k | 1.2 M | $1.06 |
| designer | 7 | 26.0 min | 63.0 min | 143k | 1.0 M | $0.99 |
| librarian | 4 | 14.7 min | 36.4 min | 83k | 0.3 M | $0.15 |
| council seats | 5 | — | — | — | 0.5 M | $3.61 |
| **total** | **191** | | | | **21.2 M** | **$18.69** |

Largest root sessions by `task` calls: 27, 16, 13, 12, 12, 11, 9, 8, 8, 8.
Task descriptions show the pattern explicitly: "Lane A/B/C/D/E/F/G", "Lane R3/R4", "Lane 1/1a/1b/2".
This is a standing four-to-seven-lane split, not an occasional fan-out.

**Cost mechanism:** a child cannot see the parent's context. It re-reads the files, re-derives the
contract, and re-runs orientation. 122k average input for a fixer is the price of that. Across
110 fixers that is 13.4 M tokens of repeated orientation per week.

### F4 — Children are almost never reused

30-day tool counts: `task` 576, `task_revive` 40, `task_message` 35, `task_cancel` 52.
Ratio: **~7% of dispatches follow up in the same child session**.

**Mechanism:** `orchestrator_append.md` never mentions `task_revive`. It says "EVERY independent
delegation MUST be background", "record each task ID", "before the final response, reconcile every
terminal job" — all of which encourage a *new* lane for each follow-up instead of continuing the
lane that already holds the files in context. A fixer that already read `gui/data.py` and
`gui/static/app.js` is discarded, and the next fixer re-reads both.

### F5 — Concurrency is set above what the machine can use

| Config | Value |
|---|---|
| `Hrns/.opencode/oh-my-opencode-slim.json` | `defaultConcurrency: 6`, provider `deepseek: 3`, `ollama-cloud: 6` |
| `hornlab-search/.opencode/*` | inherits (no concurrency block) |
| `.bak-2026-11-13` | same |

`hornlab-search/AGENTS.md` and `CLAUDE.md` both state: *"one GPU, one BEM solve at a time"*, and
`CLAUDE.md` repeats *"Never run two GPU jobs at once"*. Six concurrent fixers therefore either
serialize on the GPU lock (producing loud warnings, stalled lanes, and "slow solve" readings that
are actually host contention) or queue behind each other. `fallback.maxRetries` is 10 with a 3 s
delay, so provider-side throttling turns into minutes of silent retry.

### F6 — rbassist instructions are applied to Hornlab sessions

`~/.config/opencode/oh-my-opencode-slim/orchestrator_append.md` is root-scoped: it applies to
**every preset in every repository**. Its entire contents are rbassist:

- "rbassist PySide Validation Routing" (5 bullets about `rbassist/desktop/**`, `_QtW`, `qt_jobs`)
- "Persistent Workflow: Verification After Changes" (compileall on `rbassist/desktop/`)
- "Persistent Workflow: Migration Pattern for N2-style Refactors"
- plus the cross-project "Subagent Background Discipline"

The first three sections are inert in Hornlab — they never trigger — but they occupy ~950 tokens of
every system prompt and they bias the orchestrator toward "is this a PySide verification task?"
framing. `fixer_append.md` is the same: 34 of its 56 lines are rbassist-only.

The five rbassist skills installed at `~/.config/opencode/skills/`
(`rbassist-real-pyside-validation`, `rbassist-native-qt-design-contract`,
`rbassist-pyside-design-system-refactor`, `rbassist-pyside-gui-fixer`,
`rbassist-desktop-snapshot`) are also listed in the skill tool description on every Hornlab turn,
because the orchestrator has `skills: ["*"]`.

**Conversely, the HornLab skills are absent when working from `Hrns`.** OpenCode reads
`.claude/skills/` and `.opencode/skills/` at the *project root*. From `C:\Users\hunte\Hrns` there is
no `.claude/skills`; the eight HornLab skills live one level down in `hornlab-search/.claude/skills`
and are invisible. The orchestrator's `["*"]` therefore resolves to rbassist skills, not HornLab
skills — the exact inverse of what the work needs.

### F7 — The model tiers are inverted at the top

`presets.deepseek-flash-max` (the shared preset selected by both `Hrns/.opencode` and
`hornlab-search/.opencode`):

| Agent | Model | Variant | Assessment |
|---|---|---|---|
| orchestrator | `deepseek/deepseek-flash` | **max** | cheap model, maximum reasoning tokens — slower per turn, no capability gain |
| oracle | `ollama-cloud/glm-5.3-flash` | **max** | the physics/architecture gate on a flash model |
| fixer | `deepseek/deepseek-flash` | high | reasonable tier, too much thinking for mechanical edits |
| explorer | `deepseek/deepseek-flash` | low | correct |
| designer | `deepseek/deepseek-flash` | high | reasonable |
| council | `deepseek/deepseek-flash` | high | overridden by `council.presets.default` (glm-5.3 / minimax-m3 / kimi) |

"Max" variant on a flash model buys reasoning tokens, not judgement. It lengthens the planning
turn of the agent that runs most often, while the one reviewer whose job is to catch a wrong
acoustic or numeric decision runs on the weakest tier.

Note: the preset *choice* is deliberate and documented. `AGENTS.md` says: "All agents use the
shared `deepseek-flash-max` preset … `Hrns` and `hornlab-search` are one project; do not add a
separate preset here." This review does **not** propose replacing the preset; it proposes retiering
agents *inside* it.

### F8 — Polling

`task_status` was called 187 times from root sessions in 7 days, against 206 `task` launches.
Completion is push-based (job board + wake scheduler); polling adds full re-prefill turns for no
new information.

### F9 — The worktree instruction contradicts the filesystem

`AGENTS.md`: "do not create new worktrees or private working copies unless the owner explicitly
asks." Filesystem: `biradial-wt`, `bobudget-wt`, `boext-wt`, `bogui-wt`, `flatfix-wt`, `handoff-wt`,
`mild-wt`, `oc-wt`, `report-wt`, `shapes-wt`, plus `forks/` and `consolidation-backup-*`.
`NEXT_DEV_PRIORITIES.md` still directs work to `C:\Users\hunte\Hrns\bogui-wt`.

Read telemetry shows agents reading `oc-wt/gui-int/hornlab_search/gui/static/app.js` 41 times
alongside the canonical `hornlab-search/.../app.js` 122 times. Two copies of the same file in play
is a correctness risk, not just a speed problem.

### F10 — Dead skill names in the rbassist presets

Eight names referenced in `~/.config/opencode/oh-my-opencode-slim.json` have no directory under
`~/.config/opencode/skills/`:

`rbassist-testing`, `rbassist-gui`, `rbassist-design`, `rbassist-analysis`,
`rbassist-embeddings`, `rbassist-health`, `rbassist-rekordbox`, `rbassist-tagging`

Referenced at lines 224, 262–266, 278–279, 291, 342, 383–387, 400–401, 417. Low severity (the
affected presets are not active for Hornlab) but it means the rbassist profiles are not actually
loading what they claim.

### F11 — `verify-desktop` wraps one shell command in a full agent turn

`acpAgents.verify-desktop` runs `python -m compileall rbassist/desktop/ rbassist/ui_services/` with
`wrapperModel: deepseek/deepseek-flash`, `timeoutMs: 60000`. For Hornlab it is meaningless; for
rbassist it is a full agent round-trip for a command `bash` does in one step.

---

## 4. What should NOT change

Recorded explicitly so the reviewer does not "optimise" away deliberate decisions:

1. **The shared preset name and the one-project rule.** `AGENTS.md` mandates
   `deepseek-flash-max` for both `Hrns` and `hornlab-search`. Keep it; change only per-agent
   model/variant inside it.
2. **Cheap models for routine work.** The owner's instruction is to route routine work to cheap
   models. `explorer` at flash/low, `fixer` at flash/medium, `observer` at flash are correct.
3. **Background dispatch as the default.** It is the right default for independent lanes; the
   problem is the *absence of a threshold and a cap*, not the default itself.
4. **The anti-loop rules in `fixer_append.md`.** They are the best part of the current prompt set
   and should survive the rbassist move (they are cross-project).
5. **One GPU solve at a time.** Never relax this to gain agent parallelism.
6. **The append-only `NOTES_FOR_SENIOR.md` contract.** Read it less, never rewrite it.

---

## 5. Implementation plan

Ordered by (impact ÷ risk). Each item names the file, the change, the mechanism, the risk, and the
validation.

### P0-1 — Add a container-level `C:\Users\hunte\Hrns\AGENTS.md`

**Change:** new file, ~40 lines, pointer only. Contents:
- The canonical checkout is `hornlab-search` (owner amendment 2026-11-12); run repo commands with
  `workdir=hornlab-search`.
- `*-wt/`, `forks/`, `consolidation-backup-*`, `hf_stage_hunter*` are provenance. Do not read,
  search, or edit them unless the task names them explicitly.
- Read budget: `CONTINUITY.md` first 40 lines, `ISSUES.md` first 40, `NOTES_FOR_SENIOR.md` last 60.
  Never read any of them in full.
- Domain skills live in `hornlab-search/.claude/skills/`; load by name from there.
- One GPU solve at a time; `gpu-clean` before measurements.

**Why:** 53/58 root sessions and 241/244 oversized steps originate here. This is the only lever
that covers sessions the repo's own `AGENTS.md` cannot reach.

**Why not "just work in hornlab-search":** that is the better long-term habit and should be
stated as the preferred mode, but it is a human workflow change that cannot be enforced. The
container file works regardless of where the user launches.

**Risk:** duplicated guidance drifting from `hornlab-search/AGENTS.md`.
**Mitigation:** the container file is a pointer, never a copy; any rule with substance lives in the
repo file and is linked, not restated.

**Validation:** start a session in `Hrns`, ask for the current wave; confirm the agent cites
`docs/CONTINUITY.md` newest entry and does not enumerate worktrees.

### P0-2 — Amend the reading order in `hornlab-search/AGENTS.md`

**Change:** replace "1. `docs/CONTINUITY.md`" with an explicit budget:
- "`docs/CONTINUITY.md` — **first 40 lines only** (newest entry is at the top). Never read this
  file in full; it is an append-only history."
- "`docs/ISSUES.md` — **first 40 lines only**."
- "`NOTES_FOR_SENIOR.md` — **last 60 lines only** (append-only, newest at the end)."
- Add: "Any document over 100 KB is grep-only. Use `grep`/`offset` reads; never a whole-file read."

**Why:** one edit reaches every orchestrator and every child that follows the contract; it converts
a 210k-token read into a 10k-token read at the exact point the repository tells agents to spend it.

**Why not generate a new summary file first:** a hand-maintained brief drifts and creates a second
source of truth. The newest CONTINUITY entry already *is* a status brief; the defect is that the
instruction does not say to read only it.

**Risk:** an agent misses older history. **Mitigation:** older entries are provenance; live state is
the queue, `CONTINUITY` head, and `ISSUES` head, all of which remain readable on demand.

**Validation:** run one lane from `hornlab-search`; confirm no step exceeds ~200k and the agent
still names the correct wave/blockers.

### P1-1 — Move rbassist prompt blocks to rbassist project scope

**Change:**
- `~/.config/opencode/oh-my-opencode-slim/orchestrator_append.md`: delete the three rbassist
  sections (lines 1–22). Keep "Subagent Background Discipline" and the new dispatch rules.
- Create `C:\Users\hunte\rbassist\.opencode\oh-my-opencode-slim\orchestrator_append.md` with the
  removed rbassist sections.
- `fixer_append.md`: move the rbassist PySide validation block to
  `C:\Users\hunte\rbassist\.opencode\oh-my-opencode-slim\fixer_append.md`; keep "Anti-Loop
  Discipline" global.

**Why:** project prompt overrides have the highest precedence, and the rbassist repo currently has
no `.opencode/` at all, so it inherits the global append anyway. This removes ~950 tokens/turn and
a PySide-shaped bias from every Hornlab session while preserving rbassist behaviour exactly.

**Risk:** rbassist sessions lose the rules if the project override path is wrong.
**Validation:** open a session in `C:\Users\hunte\rbassist`, ask the agent to quote its PySide
validation rule; confirm it is present. Then do the same in `Hrns` and confirm it is absent.

### P1-2 — Rewrite the dispatch section of the global append

**Change** (replaces the current "Subagent Background Discipline"):

1. **Direct-work threshold.** If the change is ≤2 files, ≤20 lines, or a single verification
   command, do it yourself. Do not delegate a lookup you can answer with one `grep`.
2. **Lane cap.** At most 3 concurrent children; at most 1 recon child per open question. If more
   lanes are needed, run them in waves and report the wave boundary.
3. **Revive before re-dispatch.** If a child in the same lane/file cluster already ran, use
   `task_revive` with the delta. Require every child to end with a 5-line resume brief: state, files
   touched, next step, open question, command run.
4. **No polling.** Completion is push-based. Call `task_status` once only if a child looks stalled
   (>10 min past its expected step), never in a loop.
5. **Batch and keep working.** Launch all lanes in one message, then do local non-overlapping work
   in the same turn. Do not end a turn solely to announce launches.
6. **Prompt budget.** Child prompts ≤40 lines: goal, files, acceptance test, constraints. Pass
   paths, not pasted file contents.
7. **Read narrowly.** Never whole-file-read a document over 600 lines; use `grep` + `offset`.

**Why each maps to a measured failure:**
| Rule | Evidence |
|---|---|
| 1 | 1,175 root reads vs 3,180 child reads; small lookups are being delegated |
| 2 | 27 children in one session; 191/week |
| 3 | 7% revive rate; 122k avg fixer onboarding |
| 4 | 187 `task_status` calls |
| 5 | dispatch-then-stop produces extra wake cycles |
| 6 | 111k avg child input |
| 7 | 42.6% of steps >200k |

**Risk:** under-delegation on genuinely parallel multi-file work.
**Mitigation:** the cap is 3 lanes, not 1; the threshold is ≤2 files, not "do everything".

### P2-1 — Retier the shared preset (no preset rename, no new preset)

Edit `presets.deepseek-flash-max` in `~/.config/opencode/oh-my-opencode-slim.json`:

| Agent | From | To | Reason |
|---|---|---|---|
| orchestrator | flash / **max** | flash / **high** | `max` lengthens the most frequent turn without improving a flash model's planning |
| oracle | glm-5.3-flash / **max** | **ollama-cloud/glm-5.3** / high | the physics/architecture gate should not be the cheapest reviewer; 10 calls/week ≈ $1 today |
| fixer | flash / high + thinking | flash / **medium** | mechanical edits; thinking on every lane is latency |
| explorer | flash / low | unchanged | correct |
| designer | flash / high | **medium** | matching `fixer` |
| council | (config `council.presets.default`) | unchanged | already strong models |

**Why not put the orchestrator on `deepseek-v4-pro`:** it would help quality, but the owner asked
for cheap routine models and the measured problem is prompt size, not planning depth. Escalate to
`deepseek-v4-pro @ medium` only if the P0/P1 work does not remove the churn.
**Cost impact:** oracle upgrade is the only increase, roughly +$2–3/week at current usage; P1
should remove ≥$9/week of child onboarding.

### P2-2 — Concurrency

- `Hrns/.opencode/oh-my-opencode-slim.json`: `defaultConcurrency` 6 → **4**.
- Keep `providerConcurrency.deepseek: 3` (it matches the 3-lane cap) and `ollama-cloud: 6`.
- Add one line to the container `AGENTS.md` and the repo `AGENTS.md`: agent concurrency never
  authorises concurrent GPU solves.

**Why:** 6 concurrent children on one GPU and one provider produce lock contention and
fallback retries (`maxRetries: 10`, 3 s delay) that read as "slow agents".
**Validation:** one week of `runs/.gpu.lock` warnings at zero, and no `Warm BEAT Engine solver
exited` retries during a night.

### P3-1 — Fix the dead rbassist skill names

Either restore the eight skill directories or remove the names from `presets.deepseek`,
`presets.rbassist-ollama-cloud`, `presets.rbassist`, and `presets.opencode-go`. Decision needed:
were these skills deleted deliberately?

### P3-2 — Decide the worktree story

The canonical-checkout amendment and the existing `*-wt/` directories contradict each other, and
agents are editing both. Recommend documenting a read-only list in `Hrns/AGENTS.md` and updating
`NEXT_DEV_PRIORITIES.md` references that still point at `bogui-wt`. Do not delete anything without
the owner's explicit instruction.

### P3-3 — Stop wrapping `compileall` in an ACP agent

Replace `verify-desktop` delegations with a direct `bash` call in the rbassist workflow. Keep the
agent registered only if something outside the orchestrator uses it.

---

## 6. Expected impact (honest estimate)

Mechanism, not a promise: step latency at these sizes is dominated by prompt prefill, which scales
roughly with prompt length. The plan attacks prompt length at its source.

| Metric | Now (7d) | Target after P0+P1 | How measured |
|---|---|---|---|
| Steps >400k tokens | 1,904 (11.3%) | < 200 (<2%) | `part.data.tokens.total` buckets |
| Steps >600k tokens | 244 | 0–10 | same |
| Child sessions | 191 | 90–120 | `session.parent_id` count |
| Revive share | ~7% | >35% | `task_revive` / `task` |
| Children input | 21.2 M | ~12 M | sum of child `tokens_input` |
| Weekly cost | $61.7 | $45–50 | `session.cost` sum |
| Wall clock | not directly measurable from DB (sessions stay open between user turns) | qualitative: fewer multi-minute steps | stopwatch on a representative lane |

Wall-clock duration in the DB is not usable: several root sessions show 294–491 hours because they
were reopened across days. Do not quote those as runtime.

**Do not claim a percentage speed-up from this document.** The correct claim is: the steps that take
minutes are the >400k steps, they are 11.3% of all steps and 99% of them come from the container
directory, and the plan removes their cause.

---

## 7. Decisions required from the senior reviewer

1. Approve a container-level `Hrns/AGENTS.md` (P0-1), accepting one more agent-contract file?
2. Approve the reading-budget amendment to `hornlab-search/AGENTS.md` (P0-2) — the highest-leverage
   edit, and the only one that changes documented repo policy?
3. Approve moving rbassist prompt blocks into `C:\Users\hunte\rbassist\.opencode\` (P1-1) — i.e.
   accept that rbassist behaviour becomes dependent on project-scope prompt precedence?
4. Approve the dispatch rewrite (P1-2), specifically the 3-lane cap and the "do it yourself if ≤2
   files" threshold?
5. Approve retiering `oracle` from `glm-5.3-flash` to `glm-5.3` (P2-1) — the only cost increase?
6. Concurrency 6 → 4: accept, or keep 6 and rely on the prompt cap alone?
7. The eight missing rbassist skills (P3-1): restore, or delete the references?
8. Worktrees (P3-2): document read-only, archive, or leave as is?

---

## 8. Appendix — exact evidence

**Session aggregates (last 7 days, root sessions):**

```
roots  avg_ti_k  max_ti_k  cost_usd
58     1552.0    10197     43.01
```

**Largest root sessions by max step prompt (last 7 days):**

```
title                                   hrs    steps  avg_k  max_k
Multiple-entry horn handoff execution   294.0      8    829    832
Biradial and Crowe horn research hando    3.5    445    428    732
Day plan handoff 2026-11-12 execution     4.2    257    331    702
GUI handoff implementation from design   14.6    478    443    679
Day implementation plan execution        43.5    291    340    605
rbassist wave-3 lane dispatch           477.9    123    547    601
Repo familiarization and status resear  490.9     26    543    580
CROW spiral horn ridge curvature inves    2.2    259    368    568
GUI directivity slope targets for brie    3.1    232    360    542
Complete Bayesian study orchestrator s    7.4    253    342    533
Orchestrating BoTorch study workflow b   36.5    228    341    523
Move HornFab doc into repo and impleme    1.6    233    329    511
```

**Tool usage, root vs child (last 7 days):**

```
ROOT   bash 6843 · edit 1292 · read 1175 · write 399 · task 206 · task_status 187 · grep 104 · glob 41 · task_revive 27
CHILD  bash 6267 · read 3180 · edit 1928 · write 284 · grep 243 · glob 130
```

**Top files read (last 7 days):**

```
hornlab-search/hornlab_search/gui/static/app.js        122
hornlab-search/hornlab_search/gui/data.py               75
hornlab-search/hornlab_search/config.py                 54
~/.cache/.../oh-my-opencode-slim/dist/index.js          50
hornlab-search/hornlab_search/search/evaluate.py        47
hornlab-search/hornlab_search/gui/static/charts.js      42
hornlab-search/docs/CONTINUITY.md                       42
oc-wt/gui-int/hornlab_search/gui/static/app.js          41
```

**Queries used** (all read-only; replace `$db` with the DB path):

```sql
-- step prompt-size distribution
select case when t<200000 then 'a' when t<400000 then 'b'
            when t<600000 then 'c' else 'd' end bucket, count(*)
from (select json_extract(data,'$.tokens.total') t from part
      where json_extract(data,'$.type')='step-finish'
        and time_created > (strftime('%s','now')-604800)*1000) group by bucket;

-- child onboarding cost by agent
select agent, count(*), avg(tokens_input), sum(cost) from session
where parent_id is not null and time_created > (strftime('%s','now')-604800)*1000
group by agent order by count(*) desc;

-- oversized steps by launch directory
select s.directory, count(*) from part p join session s on s.id=p.session_id
where json_extract(p.data,'$.type')='step-finish'
  and json_extract(p.data,'$.tokens.total')>600000
  and p.time_created > (strftime('%s','now')-604800)*1000
group by s.directory;
```

**Environment:** OpenCode + `oh-my-opencode-slim@3.0.7`; active preset `deepseek-flash-max`
(selected by both `Hrns/.opencode` and `hornlab-search/.opencode`); 8 HornLab skills under
`hornlab-search/.claude/skills`; 5 rbassist skills under `~/.config/opencode/skills`.
