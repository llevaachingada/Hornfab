# One-command real-BL lane — exercised (R11, 2026-11-21)

**Scope.** Risk R11: BL-facing code had no scheduled real-path lane; two real `reference.solve`
bugs were caught only by a real run. This records the new one-command lane and its first
end-to-end exercise. CPU only (`beat_cpu`); no GPU flag, no GPU lock; the live favourite queue
held the GPU lane.

## Command

```powershell
.venv\Scripts\python.exe tools/system/real_bl_lane.py --real --solve --store system_runs
```

The lane is explicit-opt-in (`--real`), probes the installed BL, stages the vented-only reference
fixture through BL's own generator + `project validate`, then solves the committed 3-frequency
request (`docs/queue/system_evidence_2026-11-19/requests/real_bl_lane_vented_3f.json`) through
`reference.solve`. It always uses `backend="beat_cpu"` and holds the CPU-lane marker around the
solve.

## Result [measured]

- Probe: `BL_CAPABILITY_OK`, verified root `C:\Users\hunte\Github\boundary-lab`.
- Stage/validate: `ok true`, `valid true`, project sha256
  `bd2908ff8ec1e8951a03ecfaba6a69fc37b14d42b5298841c70f42ebe18dc03a`.
- Case: `system_runs/system/real_bl_lane/20261121T085619Z-ref_case-48668-1a90d92d/`
  (junction target `C:\Users\hunte\Hrns\hornlab-woofer-system-wt\system_runs\...`).
- Solve: `status complete`, `returncode 0`, 3/3 frequencies (250/700/1100 Hz), `backend beat_cpu`,
  85 s (08:56:19 → 08:57:44 UTC).
- Tests: `tests/system/test_real_bl_lane.py` — 8 passed (hermetic; the real lane is exercised
  separately by the command above).

Relevant run-manifest fields (UTF-8 JSON; the solve console is the `stdout_tail` recorded in
`reference_solve.json`):

<!-- evidence-quote: source=system_runs/system/real_bl_lane/20261121T085619Z-ref_case-48668-1a90d92d/run/manifest.json mode=lines decode=utf-8 -->
```
  "backend_id": "beat_cpu",
  ...
  "frequencies_hz": [
    250.0,
    700.0,
    1100.0
  ],
  ...
  "status": "complete",
```

## What this closes

R11's missing lane now exists and has run stage → BL validate → tiny CPU solve in one command.
Use it before pushes that touch `hornlab_search/system/boundarylab/**`, `system/reference.py`,
the staging runner, or the motor-map path; it is not a GPU measurement and does not replace the
GPU lane. The lane leaves its case under `system_runs` (gitignored), as intended.
