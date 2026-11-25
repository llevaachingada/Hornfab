# Senior handoff: make existing tools, research and evidence findable (2026-11-25)

**For:** cheap parallel sub-agents, run in waves by one integrator. **Owner request (2026-11-25 17:43):**
"a lot of information that is not found in terms of tools that we already have, research we've already done …
allow our existing tools and research and documents to be found and actually utilized by other agents, as well as
potentially culling or archiving old information."

**Scope:** documentation, skills, agent instructions and file layout only. **No code changes, no objective/config
changes, no GPU.** Everything here is reversible (`git mv`, never `rm`).

---

## 1. Diagnosis (brief skim, measured 2026-11-25)

| Surface | Size | Problem |
|---|---|---|
| `docs/CONTINUITY.md` | 10,077 lines | Living log. Agents are told not to read it, so whatever exists only here is lost. |
| `docs/ISSUES.md` | 4,346 lines | Same. |
| `NOTES_FOR_SENIOR.md` | 1,357 lines | Append-only. Its resolved items sit next to open ones. |
| `docs/INDEX.md` | 555 lines | A newest-first **feed**, not an index. You can't look up "the tool/doc for X" without reading all of it. |
| `docs/` top level | ~60 files | Dated plans and handoffs (`GUI_*`, `HANDOFF_*`, `IMPLEMENTATION_PLAN_*`, `SENIOR_*`) mixed with live guides. Nothing marks which are current. |
| `docs/research/` | 55 entries, 525 files | ~40 loose dated `.md` files plus topic folders. No per-topic "current answer". |
| `docs/evidence/` | 122 folders, 4,382 files (2,346 tracked) | No catalog with a one-line outcome. The best results are found only by grepping. |
| `docs/queue/` | 149 entries | Copies of night files; the live ones are in `runs/nights/` (ignored by git). Two sources of truth. |
| `tools/` | 46 entries, 365 files | No task→tool catalog. `CODE_MAP.md` lists modules, not "how do I …". |
| `examples/briefs/` | 45 entries | No table of brief → objective version → identity → current or legacy. |
| Repo root | 4 dated handoff files, 6 `scratch_*.json` | Clutter at the most-read level. |
| Skills (`.claude/skills/`, 8) | 32–122 lines each | Good core set, but missing the newest working knowledge (below). |
| `AGENTS.md` (342) + `CLAUDE.md` (173) | — | Large overlap. Historical wave plan and file-ownership tables still take up prime space. |

**Discoverability probe.** Each concept below was needed on 2026-11-25 and had to be rediscovered from code.
Columns count mentions in the navigation surfaces an agent actually reads:

| Concept | INDEX | CODE_MAP | AGENTS | skills | knowledge |
|---|---:|---:|---:|---:|---:|
| `objective.constancy` (flat-beamwidth term, opt-in) | 1 | 0 | 0 | 0 | 1 |
| watchdog `pin_ignore` / `no_gain_valid` | 0 | 0 | 0 | 0 | 0 |
| `replay_run_dir` (offline re-score) | 0 | 1 | 0 | 0 | 0 |
| `bo_sensitivity` / `parameter_activity` | 0 | 1–2 | 0 | 0 | 0–1 |
| `ActiveProjection` (BO encoding, round trip) | 0 | 0 | 0 | 0 | 0 |
| implementation digest (editing a hashed file orphans recipes) | 0 | 0 | 0 | 0 | 2 |

### Lessons from this session (2026-11-25): what an agent needed and could not find

1. **Scorer semantics.** Nothing an agent reads says that corridor mode charges **zero** anywhere in
   [min, max] and never uses `preferred_deg`, or that beamwidth flatness at a chosen angle (the owner's intent)
   needs the opt-in `objective.constancy` term. Result: favL optimized to a flat ~66 × 62° for a day under an
   "80 × 50" brief. Evidence: `docs/evidence/coverage_pull_2026-11-25/`, `docs/evidence/cd_pm5const_2026-11-25/`.
   `BRIEF_AND_SCORING_GUIDE_2026-10-25.md` predates v9–v11 (0 mentions of v11).
2. **Family laws.** Joint validity rules live only in code, for example rolled
   `hornlab_search/design/generators/rolled_family.py`: axial relief ≤ 10 % of depth, inward relief ≤ 15 % of
   height, relief window disjoint and non-dormant, `width_lo > height_hi`, throat-turn box below rect-turn box,
   and every bound endpoint checked against the seed's other values. Inert knobs per mode (Klangfilm `hv_core`,
   OSSE `aspect_ratio`/`exponent` = throat coupling, `r_lip_mm` legal only 0–2.1 mm) are also code-only.
   The 10 % / 15 % limits have no recorded rationale (commit `c2c91905`). Agents hit them one error at a time.
3. **Generator identity.** Editing any file in a family's implementation digest orphans every saved recipe. New
   behaviour goes in a new module, registered byte-wise (CRLF) in the dispatch lists of `grid.py`,
   `mesh/build.py` and `generated.py`. Example: `cd_backbone_rows_family.py`, `rim_beak_family.py`.
4. **Watchdog.** Default bound-pinned / no-gain / stall / refusal stops (exit 75) cut campaigns at 25–85 rows
   (6 of 6 v3 jobs today), well below the ≥ 100 rows metric-BO needs. Exploration jobs need
   `no_gain_valid: 0`, `stall_valid: 0`, `pin_ignore: [...]` and `refusal_max` raised. Neither the
   `hornlab-night-queue` skill nor AGENTS mentions these keys.
5. **BO identity and starts.** Identity = brief + bounds. Sobol/scrambled starts must be snapped so
   `ActiveProjection` round-trips the seed hash. Use one box per family so runs pool.
   See `docs/evidence/cd_bo_cohort_2026-11-25/snap_starts.py` and `check_explore.py`.
6. **Live night file.** `runs/nights/<night>.yaml` is re-read before each job. Insert jobs by text splice after
   the running job and validate with `tools/run_campaign_night.py --night … --dry-run`.
   See `docs/evidence/cd_pm5const_2026-11-25/queue_pm5.py`.

---

## 2. Target shape (decided here; agents do not redesign it)

```
AGENTS.md                ≤ 150 lines: rules that bind every agent + a routing table to the files below
CLAUDE.md                ≤ 30 lines: "read AGENTS.md" + Claude-specific notes only
docs/
  START_HERE.md          NEW: task → where to look (the routing table, one screen)
  INDEX.md               REWRITTEN: topic catalog (sections below), each entry = link + 1 line + status
  CODE_MAP.md            unchanged role; gaps filled
  TOOLS.md               NEW: task → tool/command catalog ("re-score offline" → replay_run_dir …)
  ACTIVE_STATE.md        pointer, refreshed by the integrator
  CONTINUITY.md / ISSUES.md   rotated (only the last ~14 days stay; older → docs/history/)
  guides/                NEW: current how-to guides moved from docs/ top level (brief/scoring, BO runbook,
                         cloud GPU runbook, driver model, forks, horn-woofer handbook, …)
  handoffs/              NEW: all dated HANDOFF_/HANDBACK_/prompt docs (this file is the first)
  knowledge/             acoustic truth hub (existing) + new family cards + SCORING_REFERENCE.md + FAMILY_LAWS.md
  research/              unchanged layout; gets research/README.md = topic → current dossier → superseded ones
  evidence/              unchanged paths (citations point here); gets evidence/CATALOG.md
  queue/                 unchanged; gets queue/README.md explaining runs/nights vs docs/queue
  archive/               existing; superseded plans/handoffs moved here by year-month
  history/               existing; rotated living logs
```

**Path stability rule.** `docs/evidence/**`, `docs/research/**` folders, `docs/knowledge/**`, `docs/plan/**`
and `examples/**` **do not move**. Run records, configs and commits cite them. Only `docs/` top-level files and
repo-root clutter move. Every move is a `git mv` followed by a repo-wide link rewrite, in the same commit.

---

## 3. Ground rules for every sub-agent

- **Read budget:** this handoff, `AGENTS.md` sections "Precedence" and "Start here", and your workstream's
  inputs only. Never read `CONTINUITY.md`, `ISSUES.md` or `NOTES_FOR_SENIOR.md` in full: use `grep -n` and read
  windows.
- **No code, config or brief edits.** Not under `hornlab_search/**`, `tools/**/*.py`, `examples/**`, `tests/**`
  or `runs/**`. Editing a generator file changes an implementation digest. Editing a config or brief changes a
  BO identity.
- **Never delete.** Archive with `git mv`. Mark superseded material in place with a one-line banner
  (`> Superseded by [X](path) on 2026-11-2x.`) when it cannot move.
- **Preserve line endings.** Check `file <path>` first. On CRLF files, edit byte-wise (Python
  `read_bytes`/`replace`), never `sed -i`.
- **Own only your workstream's paths** (table in §4). Need another path? Write the change into your report;
  the integrator applies it.
- **No GPU, no queue edits, no `gpu-clean`.** A night is running (`runs/nights/cd_bo_cohort_2026-11-25.yaml`).
- **No git commits or pushes.** Leave changes in the working tree, plus a report at
  `docs/handoffs/repo_findability_2026-11-25/reports/<WS>.md` (what changed, what was left, open questions).
- **Facts, not guesses.** Every "what this does" line comes from opening the file (module docstring, CLI
  `--help`, README first paragraph). If you can't tell, write `unclear`, don't invent.
- **Do not edit frozen files.** `docs/plan/**` and `docs/meh/**` are frozen.

---

## 4. Workstreams

### Wave 1: inventories (parallel, read-only, cheap model)

Each writes one manifest to `docs/handoffs/repo_findability_2026-11-25/inventory/`. Columns are fixed so the
wave-2 writers can consume them mechanically.

| WS | Inputs | Output | Columns |
|---|---|---|---|
| **I1 docs-top** | `docs/*.md` (top level), repo-root `*.md`/`*.json` except AGENTS/CLAUDE/README/CONTRIBUTING/TOOLCHAIN | `I1_docs_top.csv` | path, title, date, kind (guide/plan/handoff/report/proposal/log), status (CURRENT/REFERENCE/SUPERSEDED/HISTORICAL), superseded_by, proposed_dest (`guides/`, `handoffs/`, `archive/2026-1x/`, stay), inbound_links (count from `grep -rl`), one_line |
| **I2 research** | `docs/research/**` (top-level files + each folder's README or newest file) | `I2_research.csv` | path, topic, date, status, superseded_by, one_line, key_conclusion (≤ 25 words, quoted or paraphrased from the doc) |
| **I3 evidence** | each `docs/evidence/<folder>/` (README.md, else PREDECLARED/COMPLETION/newest .md) and `docs/queue/*` | `I3_evidence.csv` | folder, date, topic/family, question, outcome (≤ 25 words: pass/fail, best J, decision), status (current/superseded/negative-result), linked_from_INDEX (y/n), queue_files |
| **I4 tools** | `tools/**` entry points (`*.py`, `*.ps1` with `__main__`/param block), `hornlab_search/cli.py` subcommands, `hornlab_search/{bo,geometry,objective/replay.py}` public entry points | `I4_tools.csv` | path, invocation (exact command line), task it answers ("re-score a run under another brief"), inputs, outputs, GPU (y/n), in CODE_MAP (y/n), last commit date (`git log -1 --format=%cs`), status (live/one-off/dead) |
| **I5 instructions** | `AGENTS.md`, `CLAUDE.md`, `.claude/CLAUDE.md`, `CONTRIBUTING.md`, `.claude/skills/*/SKILL.md`, `../.opencode/opencode.jsonc`, `../AGENTS.md`, `docs/AGENT_BOOTSTRAP_CONTAINER.md` | `I5_instructions.md` | per rule: where stated (all places), duplicate/contradiction, still true? (check against code), keep/move/delete-candidate |
| **I6 briefs+configs** | `examples/briefs/**`, `examples/typologies/*/` (folder level + one config each) | `I6_briefs_configs.csv` | path, name, objective version, coverage mode + corridor + constancy (y/n), envelope policy (closed / open115), driver exit, identity status (current/legacy), used by (folders) |

Acceptance for every inventory: one row per item, no blank status, `unclear` allowed. A 10-row spot check by
the integrator against the files must find no invented facts.

### Wave 2: writers (parallel, disjoint ownership)

| WS | Owns (only these paths) | Do | Done when |
|---|---|---|---|
| **W1 moves** | `git mv` of docs/ top-level and root files per I1 `proposed_dest`; creating `docs/guides/`, `docs/handoffs/`, `docs/archive/2026-10/`, `docs/archive/2026-11/`; link rewrites in **any** `.md` (link text/targets only) | Move. Rewrite every inbound relative link (script: walk `*.md`, resolve each link against its file, remap moved targets). Do not move AGENTS, CLAUDE, README, CONTRIBUTING, TOOLCHAIN, INDEX, CODE_MAP, ACTIVE_STATE, CONTINUITY or ISSUES. | Link checker (W1 writes `docs/handoffs/repo_findability_2026-11-25/check_links.py`, stdlib only) reports 0 broken links that were not already broken before (record the before-count). `docs/` top level ≤ 15 files. |
| **W2 family cards + laws** | `docs/knowledge/typologies/{rolled,klangfilm_lame,sculpted_rosse_crowe,cd_backbone,rim_beak,favl_canonical}.md` (new), `docs/knowledge/FAMILY_LAWS.md` (new) | Use `docs/knowledge/templates/typology.md`. Per family: what it is, kinds/generators, knobs with legal ranges, **joint laws with file:line**, inert knobs per mode, implementation-digest files, best known designs (from I3), open questions. In FAMILY_LAWS.md, mark rationale `documented` (with link) or `undocumented (code only, commit X)`. | Every law in `rolled_family.py` validate path, `_rolled_rect_v1.py` limits, Klangfilm inert list, OSSE throat-coupling locks and the beak/backbone limits appears with file:line. |
| **W3 scoring reference** | `docs/knowledge/SCORING_REFERENCE.md` (new); a one-line superseded banner at the top of the old brief/scoring guide (after W1 moves it) | Versions v1→v11 (what each added, identity rules, `versions.py`). Coverage: **corridor** (zero cost inside, `preferred_deg` unused), **target**, the opt-in **constancy** term (strict/slope, clamp into corridor, tolerance meaning), `hf_floor`, `ripple_region`, the v11 `cd` block (what `cd_lw`/`cd_di_std`/`cd_nacc`/`offaxis_smooth` measure: level/DI, not beamwidth angle), envelope/size policy (`enforce`, `max_utilization`, `resample_strict`, no soft size term), `cov_v_weight`, `cov_narrow_ratio`, tolerances. Worked example: the favL 66 × 62 case with replay numbers. "How to re-score offline" (`replay_run_dir`, `load_brief_context`). | Each claim cites `file:line` in `hornlab_search/objective/`. The integrator spot-checks 5. |
| **W4 tools catalog** | `docs/TOOLS.md` (new); additive lines in `docs/CODE_MAP.md` for modules I4 found missing | Group by task: plan a search · check a config/shape · queue/monitor a night · re-score/replay · analyse a cohort (knob effects, sensitivity, convergence) · BO (identity, encoding, metric BO) · verify/compare · render/report · data/archive. Each entry: exact command, one line, GPU y/n, link to source. Mark dead/one-off tools in a final "historical" section; don't delete them. | Every I4 row with status `live` appears. Every task in §1 "Lessons" has a tool line. |
| **W5 skills** | `.claude/skills/**` | (a) `hornlab-night-queue`: watchdog keys (`pin_ignore`, `no_gain_valid`, `stall_valid`, `refusal_max`, `min_attempts`), exit 75, exploration presets, live-night splice + `--dry-run`. (b) `hornlab-search-economy`: BO identity = brief + bounds, ≥ 100 rows / ≥ 5 groups, one box per family, snapped starts and the round-trip check, explore-first. (c) `hornlab-shape-check`: point to FAMILY_LAWS.md; read all of a family's laws before choosing bounds. (d) NEW `hornlab-brief-scoring`: choosing/authoring a brief, corridor vs target vs constancy, new-identity consequences, offline replay before any GPU. (e) NEW `hornlab-generator-family`: digest rule, new-module + registration sites, CRLF byte edits, parity test, digest-unchanged guard test. (f) NEW `hornlab-find` (routing): "before writing a tool or doing research, search START_HERE → TOOLS → knowledge → research/README → evidence/CATALOG", with grep recipes. Keep each SKILL.md ≤ 120 lines. Each description says when to trigger. | Each skill names concrete files/commands that exist (W5 runs `test -e` on every path it cites). |
| **W6 catalogs** | `docs/research/README.md`, `docs/evidence/CATALOG.md`, `docs/queue/README.md` (all new) | From I2/I3: topic → **current** answer (link + key conclusion) → superseded/negative results. Evidence catalog grouped by family/topic, newest first, one-line outcome each. Queue README: `runs/nights/` = live (gitignored, re-read per job), `docs/queue/` = committed copies; how to find a night's summary. | Every I2/I3 row appears exactly once. |
| **W7 log rotation** | `docs/history/CONTINUITY_*.md`, `docs/history/ISSUES_*.md` (new); the rotated-away parts of `CONTINUITY.md` / `ISSUES.md` | Implement the existing proposal `LOG_ARCHIVAL_PROPOSAL_2026-11-17.md` (needs owner approval; see §6). Verbatim rotation of entries older than 14 days by month. Live files keep the status block + last 14 days + a link list to the rotations. Byte-exact: rotated text concatenated == removed text. | `wc -l` of the live CONTINUITY ≤ 1,500. A byte-equality check script is in the report. |

### Wave 3: integrator (one agent, serial, stronger model)

1. **Rewrite `docs/INDEX.md` as a topic catalog** from I1/I2/I3 plus W2–W6 outputs. Sections: Start · Acoustic
   knowledge · Scoring & briefs · Families (one line each → card) · Search & BO · Nights/GPU · Tools ·
   Evidence by family · Research by topic · GUI · Data/archive · Historical. Keep the old feed verbatim as
   `docs/history/INDEX_feed_through_2026-11-25.md`.
2. **Write `docs/START_HERE.md`** (≤ 80 lines): task → first file to open.
3. **Slim `AGENTS.md`** to binding rules + routing table. Move the historical wave plan, checkpoint map and
   file-ownership tables to `docs/history/AGENTS_historical_2026-11.md`. **Slim `CLAUDE.md`** to a pointer
   plus Claude-only notes. (Orchestrator-owned: owner sign-off required, §6.)
4. Refresh `ACTIVE_STATE.md`.
5. Run W1's link checker, `pytest -q tests -k "index or docs or agents"` (if any such tests exist), and
   `git diff --stat`.
6. One commit per workstream, each with a CONTINUITY/ISSUES entry (push rule).

---

## 5. Suggested agent dispatch

| Wave | Agents | Model | Est. effort |
|---|---|---|---|
| 1 | I1, I2, I3, I4, I5, I6 in parallel | cheap (Haiku/Sonnet-class) | 15–40 min each; I3 is the largest (122 folders) and can be split by date halves |
| 2 | W2, W3, W4, W5, W6 in parallel, then W1 alone (moves touch links everywhere), then W7 | W3 and W5 on a mid model (semantic accuracy); others cheap | 20–60 min each |
| 3 | integrator | strong | 1–2 h |

Prompt template for each sub-agent: "You are WS <id> of `docs/handoffs/REPO_FINDABILITY_HANDOFF_2026-11-25.md`.
Read §3 and your row in §4 only. Own only the listed paths. Write your report to
`docs/handoffs/repo_findability_2026-11-25/reports/<id>.md`. Do not commit."

---

## 6. Decisions reserved for the owner (do not act without a yes)

1. **Log rotation (W7):** approve `LOG_ARCHIVAL_PROPOSAL_2026-11-17.md` (pending since 11-17).
2. **AGENTS.md / CLAUDE.md slimming:** orchestrator-owned files.
3. **Moving docs top-level files:** breaks external bookmarks; in-repo links are rewritten.
4. **`scratch/`:** 706 tracked files despite `/scratch/` in `.gitignore`. Leave as is, or move the tracked
   remainder to `docs/archive/scratch_tracked/`? Untracked scratch (~17.7k files) is not part of this effort.
5. **Rolled relief limits** (axial ≤ 10 % depth, inward ≤ 15 % height; undocumented): keep, or open a
   versioned kind with relaxed limits (geometry work, not part of this effort).

## 7. Out of scope

Code refactors; deleting evidence; changing briefs, objectives or configs; the GUI; untracked `runs/` and
`scratch/` contents; anything in `forks/` or the `*-wt/` provenance trees (umbrella `AGENTS.md`).
