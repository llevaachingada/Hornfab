# HANDOFF FOR THE LOCAL AGENT (Windows GPU box) — start here

Written 2026-10-13 by the cloud orchestrator. Audience: an AI agent on the user's Windows machine
with the RTX 4060. Follow the steps IN ORDER. Do not improvise. If a step fails twice, stop and
append a dated block to `NOTES_FOR_SENIOR.md` (hard rule 8 in CONTRIBUTING.md).

## 0. Where we are (read this, then stop re-deriving it)
- Waves 0-3 are DONE. CP-0..CP-7 green (CP-7 noise floor 0.039 dB). Source of truth: `docs/CONTINUITY.md`.
- The cloud session (Linux, no GPU, no mesher) added PHASE 2 STAGE A code on branch
  `claude/wave-3-implementation-review-2dk4qe`, draft PR #12 into `main`:
  `hornlab_search/surrogate/{gates,features,model,train,predict,ismo}.py`, a real NSGA-II in
  `hornlab_search/search/nsga.py`, a `hornlab-search surrogate train|propose` CLI, report fixes,
  CI that installs CPU torch. Offline tests there: 450 passed, 30 skipped (the skips need the mesher,
  which only exists on this box). CI was green on the first push.
- NOTHING GPU-side was run in the cloud. The surrogate was tested on SYNTHETIC labels only. Its real
  accuracy is unknown. Do not report it as validated.

## 1. Rules that always apply (CLAUDE.md / CONTRIBUTING.md, short form)
1. Interpreter: `C:\Users\hunte\Hrns\hornlab-search\.venv\Scripts\python.exe`. Never bare `python`.
2. Every pushed commit updates `docs/CONTINUITY.md` (new dated entry at top, newest first, refresh the
   Status block) AND `docs/ISSUES.md` in the same commit.
3. Check the REAL pytest exit code (`$LASTEXITCODE`) before committing. Never pipe pytest into `tail`.
4. One GPU job at a time. Before ANY GPU run: `Get-Process julia` (expect none; if some, check the command
   line is ours, then `taskkill /F /IM julia.exe`), then
   `nvidia-smi --query-gpu=memory.used --format=csv` (expect ~0.15-0.5 GB). After the run, confirm no
   julia process remains. If you see `ConnectionResetError 10054` on warm-up, set
   `$env:HORNLAB_BEAT_WORKER_DIR` to a fresh empty folder (stale BEAT registry).
5. Never loosen a tolerance, skip a test, or edit `docs/plan/**` (frozen). Horn numbers live in
   `examples/*.yaml`, never in code.
6. Train the surrogate on CPU only (default Windows PyPI torch is CPU). Never touch the GPU for training.

## 2. Get the code (PowerShell)
```
cd C:\Users\hunte\Hrns\hornlab-search
git status                      # must be clean; if not, stop and ask the user
git fetch origin
git checkout claude/wave-3-implementation-review-2dk4qe
git pull origin claude/wave-3-implementation-review-2dk4qe
.venv\Scripts\python.exe -m pip install -e ".[dev,crosscheck,surrogate]"
```
Backup first: copy `dataset\` to `dataset_backup_YYYYMMDD\` (it is precious and gitignored).

## 3. Verify on the real machine (this is the first local checkpoint, "CP-8a")
```
.venv\Scripts\python.exe -m pytest -m "not slow and not gpu and not crosscheck"
$LASTEXITCODE                   # must be 0; expect ~480 passed with the mesher tests NOT skipped
.venv\Scripts\hornlab-search.exe doctor
```
All PASS expected. If a mesher-gated test fails that was skipped in the cloud (most likely area:
`tests/test_mesh_*`, `tests/test_search_cli.py`), that is a real finding: fix it if it is a one-line
cause, else write it to NOTES_FOR_SENIOR and stop. Paste the pytest tail and `doctor` output into your
report. Then run the GPU-marked tests once (GPU hygiene first):
`.venv\Scripts\python.exe -m pytest -m "slow or gpu or crosscheck"` and paste the summary.

## 4. Widen the two bounds (CP-8b)
Finding: in the 60-evaluation `search_smoke` run the best design sat at the LOWER bounds of
`a_deg` (25.0) and `exponent` (2.0). Files: `examples/search_smoke.yaml` and `examples/osse_baseline.yaml`
(both have `a_deg: {lo: 25.0, hi: 55.0}` and `exponent: {lo: 2.0, hi: 8.0}`). `freeform_hv.yaml` has
`exponent` only. `throat_adapter.yaml` pins both: leave it.
Do NOT guess new numbers. First read the mesher's own validation:
`Select-String -Path .venv\Lib\site-packages\hornlab_mesher\*.py -Pattern "exponent|coverage|a_deg" `
and find the accepted range for the OSSE coverage half-angle `a_deg` (must keep `a_deg > a0_deg`;
check how the mesher enforces it) and the superellipse `exponent`. Set the new `lo` to the lowest value
the mesher accepts with margin (e.g. lo = mesher minimum + 10 %), and keep `hi` unchanged. Then:
1. `.venv\Scripts\hornlab-search.exe run --config examples\search_smoke.yaml --mode screen --dry-run`
   (must still mesh; a refused corner is fine, a crash is not).
2. Run `search_smoke` again (GPU hygiene first): 
   `.venv\Scripts\hornlab-search.exe search --config examples\search_smoke.yaml --budget 60`
3. Open the run's `report.html` (or `hornlab-search report runs\<dir> --out report.html`) and read the
   bound-pinning section: pass = the best design is no longer pinned at the new lower bounds, or if it is,
   record that in CONTINUITY and widen once more (max two widenings, then stop and report).
Record old/new numbers, the mesher limits you found, and the J before/after in CONTINUITY.

## 5. Build the multi-family dataset (CP-8c)
Purpose: the surrogate needs thousands of records per family. Measured throughput: ~4.25 s/candidate
for `search_smoke` (about 847 per hour); `osse_baseline` is slower per candidate (seed alone 18 s).
Run these one at a time, each with GPU hygiene before and a julia-process check after. Use bigger
budgets than 60. Suggested order and budget (tell the user the expected hours before starting):
```
hornlab-search.exe search --config examples\osse_baseline.yaml   --budget 1500
hornlab-search.exe search --config examples\icw_termination.yaml --budget 800
hornlab-search.exe search --config examples\freeform_hv.yaml     --budget 800
hornlab-search.exe search --config examples\throat_adapter.yaml  --budget 400
hornlab-search.exe dataset stats      # paste output
hornlab-search.exe dataset verify     # must say OK
```
A run can be stopped and continued with `search --resume runs\<dir>`. After each run update CONTINUITY
(records per family, ok vs failed, hours). Pass for CP-8c: `dataset verify` OK and `dataset stats`
shows all four families present (the stats print a family-balance warning if not).

## 6. Train and gate the Stage A surrogate (CP-8d) — the real answer
IMPORTANT arithmetic: the held-out set is 15 % of a family's records, and the plan requires >= 500
held-out designs for the gates to count. So ONE family needs about 3,400 records (ok + failed) before
a gate can pass; the code refuses to pass below 500 held-out and prints a WARNING. Start with the
family that has the most records (OSSE: pool `osse_baseline` and `search_smoke` runs). If you have fewer,
the run is still worth doing: it shows trends, but report "indicative only".
```
hornlab-search.exe surrogate train --config examples\osse_baseline.yaml --out surrogate_osse.pt
```
Read the printed gate table: Spearman > 0.90, top-20 overlap >= 12, beamwidth MAE < 2 deg, DI MAE < 0.3 dB,
invalid-design accuracy > 0.85, 0 monotonic sign flips. Exit code 1 means NOT PASSED: then do NOT use
the model. Paste the table. Possible fixes, in order: more records; more epochs (`--epochs 600`);
`--lib-sha` to filter to one library version. Do not edit gate thresholds (`surrogate/gates.py`).
If the gates pass:
```
hornlab-search.exe surrogate propose --config examples\osse_baseline.yaml --out surrogate_osse.pt --proposals proposals.json
```
This writes 30 "exploit" + 10 "explore" designs. Solve EACH with real BEM through the normal path
(`hornlab_search.search.evaluate.evaluate(...)`, mode `screen`; look at how `_cmd_verify` in
`hornlab_search/cli.py` does it and copy that pattern; one GPU solve at a time) so they enter the
dataset. Then call `hornlab_search.surrogate.ismo.round_report(pred_J, true_J, random_true_J)` where
`random_true_J` = objectives of the first ~40 evaluations of the search (those were not
surrogate-picked). Pass for CP-8d: `round_report["working"]` is True. If False, say so plainly:
more iterations will not fix it; collect more data instead.

## 7. Finish
1. Commit in small commits (conventional commits: `feat(...)`, `fix(...)`, `docs: ...`), each with the
   CONTINUITY + ISSUES update. Push to the SAME branch. Do not merge PR #12 yourself; tell the user it is
   ready for review.
2. Add a CONTINUITY entry: what passed, what failed, numbers, hours used, what is next.
3. Leave no julia process running; confirm `nvidia-smi` is back near idle.

## 8. Report format (paste to the user)
For each of CP-8a..CP-8d: PASS / FAIL / PARTIAL, the pasted terminal output, and one line on what is
next. Never write "tests pass" without the pasted output.

## 9. Where things are
| Need | File |
|---|---|
| State, numbers, history | `docs/CONTINUITY.md` |
| Rules | `CLAUDE.md`, `CONTRIBUTING.md`, `AGENTS.md` |
| Measured machine numbers | `TOOLCHAIN.md` |
| Senior rulings, residual risks | `NOTES_FOR_SENIOR.md` (task-09 block at the end) |
| Phase 2 plan and gates | `docs/plan/11_PHASE2_SURROGATE.md` (frozen) |
| Surrogate code | `hornlab_search/surrogate/`, `hornlab_search/search/nsga.py` |
| Surrogate CLI | `_cmd_surrogate` in `hornlab_search/cli.py` |
| Surrogate tests (synthetic) | `tests/test_surrogate_stage_a.py`, `test_surrogate_ismo.py`, `test_search_nsga.py` |
| Older runbook / loose ends | `docs/HANDOFF.md` |
