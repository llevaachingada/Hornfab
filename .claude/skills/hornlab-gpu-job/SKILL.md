---
name: hornlab-gpu-job
description: The operational recipe for any GPU measurement or solve job in hornlab-search (selftest, run, search, verify, compare, campaign, pytest with the slow/gpu markers, ceiling re-measures) — pre-job hygiene (concurrent-session check, stale BEAT host scan, GPU lock and what exit code 3 "GPU busy" means, VRAM baseline), log capture (PS 5.1 Tee UTF-16 + pytest count-line gotcha), post-job verified shutdown. Use when running anything against this repo's GPU or when a GPU job refused/failed and needs the clean-state protocol; ONLY job mechanics — planning, briefs, interpreting results stay with the pass's instructions.
---

# hornlab GPU job

The "GPU / Julia hygiene" rules 1–7 (CLAUDE.md == AGENTS.md, same numbering) are LAW; this skill is the
operational recipe, not the rules. Fork installs follow `docs/FORKS.md`; machine numbers live in
`TOOLCHAIN.md`.

## 1. Pre-job (every GPU job)

- a. Concurrent lanes: know who else is writing/running: `git log --oneline -5`, `git status --porcelain`,
  recent `runs/` dirs. Another session mid-GPU = do NOT start (one job machine-wide). The CLI lock (below)
  only covers `hornlab-search` commands — ad-hoc python/pytest scripts bypass it, so this scan is not redundant.
- b. Stale hosts/orphans: list `julia` + BEAT worker-host processes; kill ONLY project-started BEAT hosts
  (check the command line first; leave unrelated python/GUI server.py processes alone). `hornlab-search
  gpu-clean` is the tool for BEAT hosts.
- c. Lock: `runs/.gpu.lock` — a lock whose holder process is DEAD is fine (the liveness check frees it on
  next acquire). NEVER take over a LIVE holder's lock by hand. A live holder makes every GPU command print
  "GPU busy: …" and **exit 3** — stop/wait, never retry-loop; `gpu-clean` refuses too (never `--force` past
  it; the flag is labeled DANGEROUS in its own help).
- d. Baseline: `nvidia-smi --query-gpu=memory.used --format=csv,noheader` immediately before the job; it
  rides next to every peak number.
- e. Fresh MEASUREMENT + fresh cache: one measurement per fresh process (rule 2); a search/campaign
  legitimately reuses its warm worker inside its own run. Any A/B or re-solve after a solver/SHA change gets
  a NEW `--cache-dir scratch\...` (the solve/mesh cache key is design-mesh-solve hash, NOT lib SHA — a stale
  entry silently serves old-solver responses as "new").
- f. Preflight: `hornlab-search doctor` (cheap) reports `gpu-hygiene` and `pinned-shas`. Installed SHA ≠
  pyproject pin on a fork lane ⇒ the pinned-shas WARNING and the `test_mesh_pin` failure are the INTENDED
  guard (docs/FORKS.md), not a regression — never "fix" them by hand.

## 2. Job execution

- a. Capture (PowerShell 5.1): `& ".venv\Scripts\<cmd>" ... 2>&1 | Tee-Object -FilePath
  "runs\<per-topic subfolder, convention mX_<topic>\<job>.log>"` — Tee-Object writes UTF-16; decode before
  quoting into evidence.
- b. pytest: add `--junitxml=<path>` — the Tee capture DROPS pytest's final count line; counters come from
  the XML, failures from the log's short-summary lines. Markers (pyproject, CI parity): offline
  `-m "not slow and not gpu and not crosscheck"`; GPU-marked `-m "slow or gpu or crosscheck"`.
- c. Generous timeouts: a cold Julia start is slow; large meshes can be memory-pressured (assembly takes
  minutes). Never kill mid-solve.
- d. Rules 4–5 bind here (no provisioning while measuring; VRAM polled from an external thread/process).

## 3. Post-job

- a. `hornlab-search gpu-clean`, then VERIFY: no julia remains, VRAM back to idle.
- b. If the job died: clear hosts, read the log tail (OOM/CRASH lines) — rule 7's clean-state reproduce comes
  first. A REFUSAL message naming gpu-clean (e.g. a flagged solve against a warm host predating its env) is a
  stale-host instruction, not a finding: clean and re-run once.
- c. The interrupted-job case: a stale lock from a killed holder does not block the next job; check orphans
  before restarting.