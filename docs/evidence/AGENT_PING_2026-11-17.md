# Agent ping evidence — 2026-11-17

**What this proves.** After the P0/P1 orchestration changes, agents actually discover and load the
HornLab skills; the grant matrix is enforced; and no rbassist/PySide rule leaks into HornLab work.
[measured] All outputs below are captured process stdout with ANSI colour codes stripped. They are
not byte-checked `Tee-Object` logs, so treat them as console evidence, not as a UTF-16 run log.

Environment: OpenCode 1.17.10, `oh-my-opencode-slim@3.0.7`, preset `deepseek-flash-max`.

## Repeatable harness

```
.venv\Scripts\python.exe tools/agent/ping_agents.py            # static, free
.venv\Scripts\python.exe tools/agent/ping_agents.py --live --model ollama-cloud/deepseek-v4.1-flash:1017
```

Final run, verbatim:

```
[PASS] canonical: all 8 hornlab skills discoverable - 26 skills
[PASS] container: all 8 hornlab skills discoverable - 26 skills
[PASS] canonical: config parses - exit 0
[PASS] canonical: no rbassist skill granted to orchestrator - none granted
[PASS] container: no rbassist skill granted to orchestrator - none granted

Static checks done. Live checks: --live (costs tokens).

[PASS] live: orchestrator loads a hornlab skill - > orchestrator ? deepseek-v4.1-flash:1017 | ? Skill "hornlab-gpu-job"
[PASS] live: delegated fixer loads a hornlab skill - ? PING fixer skill load Fixer Agent | ? PING fixer skill load Fixer Agent
[PASS] live: no rbassist directive or skill in HornLab - PING-ISOLATION: (no); rbassist skills: (none) | > orchestrator ? deepseek-v4.1-flash:1017

8/8 checks passed
```

The `?` characters are the console's rendering of the tool-call glyphs and the em dash; the ASCII
markers (`PING-... OK`, `PING-ISOLATION: (no)`) are intact.

## Individual pings

Each row is a separate headless `opencode run` session. Delegation pings exercised the real
orchestrator → child path, not a direct agent override (subagents cannot be selected as primaries).

| # | Workspace | Agent path | Instruction | Verbatim result |
|---|---|---|---|---|
| A | `hornlab-search` | orchestrator | load `hornlab-gpu-job` | `→ Skill "hornlab-gpu-job"` then `PING-A OK: # Skill: hornlab-gpu-job — The GPU / Julia hygiene rules 1–7` |
| B | `hornlab-search` | orchestrator → fixer | load `hornlab-gpu-job` | **failed**: `Task … ended in error: Insufficient Balance … No model fallback chain for fixer.` |
| B2 | `hornlab-search` | orchestrator → fixer | same, after adding a fallback model | **failed**: `Model fallback did not recover from deepseek/deepseek-flash.` Child session switched to `ollama-cloud/deepseek-v4.1-flash` but produced no generation. |
| B3 | `hornlab-search` | orchestrator → fixer | same, after putting the working provider first | `PING-B3 OK: Skill: hornlab-gpu-job # hornlab GPU job The "GPU` |
| C | `hornlab-search` | orchestrator → oracle | load `simplify` | `PING-C OK: Simplify code by reducing complexity while preserving exact` |
| D | `Hrns` (container) | orchestrator | load `hornlab-acoustic-grounding` | `→ Skill "hornlab-acoustic-grounding"` then `PING-D OK: Read docs/knowledge/README.md, the relevant family card, and` |
| F | `hornlab-search` | orchestrator → explorer | attempt `hornlab-gpu-job` | `PING-F DENIED: no skill tool available in this agent's toolset` |
| G | `hornlab-search` | orchestrator → designer | load `hornlab-render` | `PING-G OK: Two steps, two environments (pyvista is not` |
| E | `rbassist-merge-cloud-local` | orchestrator | which skill is required for `rbassist/desktop/**` | `PING-E: rbassist-real-pyside-validation; FakeQt-only sufficient: no` |
| E2 | `rbassist-merge-cloud-local` | orchestrator → fixer | load `rbassist-real-pyside-validation` | **blocked**: `Insufficient Balance … Model fallback did not recover from deepseek/deepseek-flash.` (that workspace's presets still put deepseek first) |
| H | `hornlab-search` | orchestrator | is a PySide rule required? | `PING-H: no; PySide validation rules present: none (only the rbassist-* skill entries appear in the available-skills inventory; no instruction requires loading them for rbassist/desktop/**).` |
| H2 | `hornlab-search` | orchestrator | same, after `skills_remove` | `PING-H2: (no); rbassist skills listed: (none)` |

## Findings

1. **Provider outage, not a config regression.** The DeepSeek provider returned
   `Insufficient Balance` on every call. `deepseek-flash-max` had single-model agents, so delegated
   lanes had no fallback at all (`No model fallback chain for fixer`).
2. **Adding a fallback was not enough.** The plugin switched the child session's model to
   `ollama-cloud/deepseek-v4.1-flash` and then produced no generation; the board reported
   `Model fallback did not recover`. The direct model worked in isolation (plain and `--variant high`),
   so the failure is in the mid-run fallback path, not the model.
3. **Provider order fixed availability.** Reordering the same-tier arrays to put
   `ollama-cloud/deepseek-v4.1-flash:1017` first (deepseek kept as fallback) made delegation work
   (B3). No tier, variant or task routing changed.
4. **The grant matrix is real and enforced.** Explorer has no skill tool at all (F); fixer and
   designer load only their granted HornLab skills (B3, G); the orchestrator loads any (A, D).
5. **Container discovery now matches the repo.** `hornlab-acoustic-grounding` loads from `Hrns`
   (D), not just from the canonical checkout.
6. **Isolation is complete.** Before `skills_remove`, the HornLab orchestrator reported that
   `rbassist-*` entries appeared in its inventory; after it, it reports none (H → H2).
7. **rbassist delegated lanes remain blocked** by the same provider balance (E2). Its orchestrator
   prompt and skills are intact (E); only child model calls fail. Fixing it means the same reorder in
   that workspace's presets — deliberately not done here because rbassist is out of scope.

## Limitations

- Console captures, not run logs. A byte-checked copy would need `Tee-Object` and decoding.
- The ping prompts are deliberately tiny; they prove skill plumbing, not task quality.
- `--live` needs a funded provider and is not part of CI.
