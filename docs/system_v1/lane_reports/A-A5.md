# A5 - JobSpec + evidence byte-check (Pass A)

**Branch:** `claude/system-v1-pass-a` (clone `C:\Users\hunte\AppData\Local\Temp\opencode\hornlab-pass-a`).
**Contract:** `01_CONTRACTS.md` section 6 implemented as written; no amendments needed.

## Files

- `hornlab_search/system/jobs.py` (new): frozen `JobSpec` (kind/argv/cwd_rel/env/
  inputs_sha256/lane/authorization_id), `preview()`, `build_job()`, `JobError(token, detail)`.
- `tools/evidence/verify_evidence_quotes.py` (new, stdlib only): fenced quote blocks, UTF-16
  BOM / UTF-8 log decoding, per-line verbatim miss report, exit 1 on any miss.
- `tests/system/test_jobs.py` (new): every kind's preview equals the joined argv, CLI/seed
  routing, bl_solve `AUTH_MISSING`, authorization forwarding, sha determinism, env/cwd, refusals.
- `tests/test_tools_verify_evidence_quotes.py` (new): marker detection, UTF-16 decode, pass/miss
  exit codes, quotes split across several logs.

## Argv mapping (mirrors `tools/system/gui_system_job.py` routing)

- `screen` -> `sys.executable -m hornlab_search.system.woofer_seed ...`
- `bl_stage` -> `... -m hornlab_search.system.cli reference prepare ...`
- `bl_validate` -> `... reference validate ...`; `bl_solve` -> `... reference solve ...`
- `pilot`/`portfolio`/`funnel` -> the matching `cli` subcommand.
- `preview` = `shlex.join(argv)` on POSIX, `subprocess.list2cmdline(argv)` on Windows.
- `bl_solve` with no `authorization_id` raises `JobError("AUTH_MISSING")` before any argv exists;
  the id is recorded on the spec and forwarded as `--authorized-by` unless `authorized_by=` is given.
- `inputs_sha256` = sha256 of canonical JSON over the module+args, cwd_rel, env and kind.

## Quote convention matched (sampled `docs/evidence/`)

A fenced block is a quote when its closest preceding non-blank line carries a marker. The real
docs convention is **`verbatim`** on that line (e.g. `Final run, verbatim:` in
`AGENT_PING_2026-11-17.md`, `Verbatim tail from ...` in `BAYESIAN_STUDY_INTEGRATION_2026-11-14.md`;
34 such blocks across `docs/evidence/`). `quote:` and `[measured]` are accepted as the handoff
also specifies. Logs with a UTF-16 BOM (`Tee-Object`, as the handbook notes for
`blab_solve*.log.txt`) decode as UTF-16; otherwise UTF-8.

## Test command and counters

```
& "C:\Users\hunte\Hrns\hornlab-search\.venv\Scripts\python.exe" -m pytest -q -o addopts="" tests/system/test_jobs.py tests/test_tools_verify_evidence_quotes.py
.........................                                                [100%]
25 passed in 0.26s
```

## Requests for other lanes

- **B3 (funnel):** call `jobs.build_job("funnel", plan=..., execute=..., allow_bl=...,
  authorization=...)`; the `funnel` subcommand/argv is built ahead of that CLI existing.
- **B2/C:** `jobs.preview(job)` is the single command-line renderer; no need to re-implement quoting.

## Deferrals

None. No BL, GPU, network or `system_runs/` access; `gui_system_job.py`, `cli.py`,
`contracts.py` and the four shared docs were not edited.
