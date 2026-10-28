---
name: hornlab-evidence
description: How to write hornlab-search evidence documents that survive byte-level review — real terminal bytes quoted from DECODED run logs (UTF-16), junitxml counters, [measured]/[inferred]/provisional labeling, reconstructed-invocation and elision annotations, baseline+peak VRAM pairing, and the pre-publish byte-check against run logs. Use when assembling docs/evidence/*.md for checkpoints, pushes, or fork validation ladders; use ONLY for evidence assembly — running the jobs is hornlab-gpu-job's territory.
---

# hornlab evidence

Hard rules 6–7 (AGENTS.md) are law: pasted real bytes; never loosen. This skill = how evidence gets
assembled. What may be committed is governed by `docs/evidence/README.md` — evidence about the data, never
the data.

## 1. Honesty frame

- [measured] = observed in a log; [inferred] = scaling/estimate; PROVISIONAL = observed once, clean-state
  confirmation not completed (say exactly that).
- Every number in prose/tables must be traceable to a log file byte-for-byte. Never retype from memory.

## 2. Inputs

- Raw logs: `runs\mX_<topic>\*.log` — DECODE before quoting (Tee-Object = UTF-16). pytest counters: the
  `--junitxml` XML; failures: the log's short-summary lines. Raw data (CSVs, npz, response blobs) stays
  LOCAL/gitignored (`docs/evidence/README.md`); committed evidence = text.

## 3. Structure

- Header: scope, machine (one line; numbers live in TOOLCHAIN.md), date, what ran.
- Per-run section: the invocation line (label "RECONSTRUCTED" if it is not in the log), a verbatim fenced
  block, THEN interpretation. Tables after; each cell = a log number.
- Label every elision ("the X block elides its first MESH-CACHE-HIT line"); pair baseline+peak VRAM wherever
  a peak appears.
- File names carry the date (`NAME_YYYY-MM-DD.md`). When quoting numbers scoped by a mandatory caveat in a
  prior evidence doc, quote that caveat verbatim — never paraphrase. Fork-ladder evidence states the
  installed SHA and how it was proven (doctor pinned-shas / direct_url.json), per `docs/FORKS.md`.

## 4. Before publishing

- Byte check: decode, then compare EVERY quoted block against its source log (scripted, not by eye); fix any
  mismatch. If any block was left unverified, say so in the doc.
- New doc → `docs/INDEX.md` (+ `docs/CODE_MAP.md` if tooling) lines in the same commit; CONTINUITY + ISSUES
  updated in the same commit as any push (CLAUDE.md push rule).