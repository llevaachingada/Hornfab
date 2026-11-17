# Agent bootstrap for the `Hrns` umbrella workspace

**Why this file exists.** OpenCode discovers skills by walking from the active workspace **up toward
the project root / home directory**. It does not walk *down* into a child checkout. A session started
in `C:/Users/hunte/Hrns` therefore cannot see `hornlab-search/.claude/skills`, and it sees only the
globally installed skills. Measured 2026-11-17 with `opencode debug skill` (OpenCode 1.17.10):

| Workspace | Skills discovered | `hornlab-*` present |
|---|---|---|
| `C:/Users/hunte/Hrns` (before this bootstrap) | 18 | **0 of 8** |
| `C:/Users/hunte/Hrns/hornlab-search` | 26 | 8 of 8 |
| `C:/Users/hunte/Hrns` (after this bootstrap) | 26 | 8 of 8 |

A pointer `AGENTS.md` alone does **not** fix skill discovery. The fix is either to launch OpenCode in
the canonical checkout or to register the nested skill source explicitly.

## Canonical workspace

```
C:/Users/hunte/Hrns/hornlab-search
```

Launch OpenCode there whenever possible. The owner amendment in `AGENTS.md` names that path as the
one consolidated checkout. Worktrees, forks and backups under `Hrns/` are provenance.

## What the umbrella fallback consists of

Two files outside the repository, both machine-local (the `Hrns` directory is not a source-controlled
project):

### 1. `C:/Users/hunte/Hrns/AGENTS.md`

Thin umbrella contract: canonical checkout, no default sibling search, search-on-demand living logs,
one GPU solve, workspace-scoped skills, no cross-project rule import. It deliberately contains **no**
substantive project rules; those live in `hornlab-search/AGENTS.md`. Because OpenCode also loads
ancestor `AGENTS.md` files, this file is active inside the repository too — it must stay compatible
with that.

### 2. `C:/Users/hunte/Hrns/.opencode/opencode.jsonc`

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "skills": {
    "paths": ["C:/Users/hunte/Hrns/hornlab-search/.claude/skills"]
  }
}
```

**Schema note (OpenCode 1.17.10):** this build takes the **object** form (`skills.paths`) and rejects
the array form (`skills: ["…"]`) that newer documentation shows. Do not "modernise" this to an array
without checking the installed version first.

The path is absolute on purpose: relative `skills` entries resolve against the active working
directory, which differs between the umbrella root and subdirectories. If the repository moves,
update this one line.

## Active preset (`opencode-go-max`)

The active preset is **`opencode-go-max`**, a HornLab-specific copy of the `deepseek-flash-max`
tiers routed entirely to the OpenCode Go provider:

| Agent | Model (primary, fallback) | Variant |
|---|---|---|
| orchestrator | `opencode-go/deepseek-v4.1-flash`, `opencode-go/glm-5.3-flash` | max |
| oracle | `opencode-go/glm-5.3-flash`, `opencode-go/deepseek-v4.1-flash` | max |
| fixer / librarian / designer / council / observer | `opencode-go/deepseek-v4.1-flash`, `opencode-go/glm-5.3-flash` | high |
| explorer | `opencode-go/deepseek-v4.1-flash`, `opencode-go/glm-5.3-flash` | low |

It is defined in **two** files because OpenCode's project-config walk stops at the git boundary:

- `hornlab-search/.opencode/oh-my-opencode-slim.json` — canonical (applies when launched in the repo).
- `Hrns/.opencode/oh-my-opencode-slim.json` — umbrella mirror (applies when launched in `Hrns`).

**Keep the two preset blocks identical.** Root `agents.*` entries (`skills_remove`, fixer/designer
HornLab skill grants) belong in the canonical file; the umbrella copy carries the same
`skills_remove` so the isolation holds there too.

`opencode-go/deepseek-v4.1-flash` is the primary model. On 2026-11-17 the Go workspace refused it
with "hosted outside Europe and the United States"; the owner set **Settings › Privacy › Regions**
to **Global** in the Go console, and it now loads skills normally (verified with a live run). If the
region setting is ever reverted, the `glm-5.3-flash` fallback keeps the lanes alive.

Verify the active preset:

```powershell
opencode debug agent orchestrator   # expect providerID opencode-go, modelID deepseek-v4.1-flash, variant max
opencode run --dir C:\Users\hunte\Hrns\hornlab-search "PING: reply exactly PING-OK"
# the banner must read: > orchestrator · glm-5.3-flash
```

## Nested `AGENTS.md` timing (why the umbrella file front-loads orientation)

Starting in `Hrns`, OpenCode loads upward `AGENTS.md` files immediately but injects
`hornlab-search/AGENTS.md` only when the agent first reads a file **inside** `hornlab-search`. That
is late: planning and exploration have already started. The umbrella file exists to make the first
minutes correct; the repo file takes over once work begins.

## Verification (run these, do not assume)

```powershell
# From the umbrella root: expect 26 skills and all eight hornlab-* IDs.
Set-Location C:\Users\hunte\Hrns
opencode debug skill | Select-String "hornlab-"

# From the canonical checkout: expect the same eight IDs from native discovery.
Set-Location C:\Users\hunte\Hrns\hornlab-search
opencode debug skill | Select-String "hornlab-"

# Config must parse cleanly from both workspaces.
opencode debug config | Select-String "skills"
```

The eight IDs are `hornlab-acoustic-grounding`, `hornlab-evidence`, `hornlab-gpu-job`,
`hornlab-night-queue`, `hornlab-render`, `hornlab-search-economy`, `hornlab-shape-check`,
`hornlab-typology-research`.

## Cross-project isolation check

An umbrella session must not present rbassist-only rules as HornLab requirements. The global user
prompt appends are project-neutral; rbassist's PySide rules live in that workspace's
`.opencode/oh-my-opencode-slim/` prompt files. To confirm:

```powershell
Select-String -Path "$env:USERPROFILE\.config\opencode\oh-my-opencode-slim\*_append.md" `
  -Pattern "rbassist|PySide|_QtW"
# Expect: no matches.

Select-String -Path "C:\Users\hunte\Music\rbassist-merge-cloud-local\.opencode\oh-my-opencode-slim\*_append.md" `
  -Pattern "rbassist-real-pyside-validation"
# Expect: matches (required there).
```

## Failure modes

| Symptom | Cause | Fix |
|---|---|---|
| No `hornlab-*` skill in an umbrella session | `.opencode/opencode.jsonc` missing or invalid | restore the block above, re-run `opencode debug skill` |
| Config error `Expected object … got [ … ] skills` | array form used on OpenCode 1.17.10 | use `skills.paths` |
| Agent plans before reading repo rules | nested `AGENTS.md` not loaded yet | start in `hornlab-search`, or rely on the umbrella file's pointer |
| rbassist PySide rules appear in HornLab work | global append not yet split | see the isolation check above |
