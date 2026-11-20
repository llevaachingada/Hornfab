# System evidence queue — 2026-11-19 (CPU only, staged)

**Why this queue exists.** The senior decision report
(`docs/HORNFAB_SENIOR_DECISION_2026-11-19.md`) identified the evidence gaps that currently block a
defensible complete-system claim: no data below 200 Hz, an incomplete motor×box matrix, no
real-motor assembled case, no observation-distance/frequency-sampling control, and no calibration
record. This queue produces the **cheap, bounded data** that can guide those questions without
spending GPU time.

**What it is not.** It is not a system ranking, not a crossover optimization, not a real-driver
shape study, and not a substitute for calibration. It runs existing immutable Boundary Lab projects
through the existing CPU `beat_cpu` path; no solver/mesher code is changed.

## Jobs

| ID | Source project | Request | Question answered | Acceptance |
|---|---|---|---|---|
| `ev_lf_motor_real` | #4 real 12PR300, seed 115 L box | 20–200 Hz, 12 log freqs | Is the lumped F3/Fb/port-velocity model consistent with BL at LF for the real motor? | complete 12/12; deltas vs bassbox recorded |
| `ev_lf_demo_twin` | #5 demo-motor twin | 20–200 Hz, 12 log freqs | How much of the LF result is motor-model dependent? | complete 12/12; paired deltas vs #4 |
| `ev_lf_default_real` | #6 real motor, default box (staged) | 20–200 Hz, 12 log freqs | First real-motor default-box LF cell (2×2) | complete 12/12 |
| `ev_lf_default_demo` | R0 demo, default box (staged) | 20–200 Hz, 12 log freqs | Demo/default control cell (2×2) | complete 12/12 |
| `ev_lf_assembled_demo` | #2 assembled horn+woofer | 20–200 Hz, 12 log freqs, both ports | Does the installed horn load the woofer/port at LF? | complete 12/12; compare with vented-only |
| `ev_wide_default_real` | #6 real motor, default box | 200–2500 Hz, 25 freqs | Complete the 2×2 matrix on the same wide grid as #4/#5 | complete 25/25; paired deltas |
| `ev_wide_default_demo` | R0 demo, default box | 200–2500 Hz, 25 freqs | Complete the 2×2 matrix on the wide grid | complete 25/25; paired deltas |
| `ev_farfield_g4_10m` | #2 assembled project | 200–2500 Hz, 25 freqs, 10 m probes | How much do 2 m and 10 m observation distances differ? | complete 25/25; per-probe delta |
| `ev_dense_g4_49` | #2 assembled project | 200–2500 Hz, 49 freqs | How much of the interference structure is undersampled at 25 freqs? | complete 49/49; null-depth delta |
| `ev_screen_variety` | saved asset `0062fb59fbf63eae` | CPU seed screen, 8 boxes / 6 shortlist | Reproducible screen variety / replay identity | screen JSON + shortlist; no solver |
| `ev_export_system_data` | — | `tools/data/system_cases.py` | Refresh the reviewable case census including the new cases | JSON/CSV under `system_runs/evidence_export_2026-11-19` |

All solve jobs use `tools/system/evidence_case.py`, which copies the source `case.blab.json` and
its `bl_output/` tree into a **fresh** case, copies the request, validates the request shape, and
writes a self-checksummed manifest naming the source case, source project hash, request hash, BL
root and authorization record. `reference.solve` then owns the BL invocation. Nothing is solved
into an existing case.

## Authorization (mandatory)

The queue file deliberately contains **no standing authorization**. `--solve` refuses before
creating a case unless an authorization record is supplied. Set the owner's exact record at launch:

```powershell
$env:HORNLAB_EVIDENCE_AUTHORIZED_BY = "owner 2026-11-19: bounded CPU system evidence queue (beat_cpu only; no GPU); 8 solves"
```

This string is written into every derived-case manifest. If the owner wants a different record
shape, edit the env value — do not encode a generic "yes" in the queue.

## Validate first (writes nothing)

```powershell
.venv\Scripts\python.exe tools\run_campaign_night.py `
  --night docs\queue\system_evidence_2026-11-19.yaml --dry-run
```

The dry-run checks the 10 job definitions and argv. A second, per-job dry-run validates each
source project/request:

```powershell
.venv\Scripts\python.exe tools\system\evidence_case.py `
  --source-case system_runs/system/bl_motor12pr/20261119T010548Z-motor12pr-17944-fa37ab5e `
  --experiment-id ev_lf_motor_real --tag lf_20_200 `
  --request docs\queue\system_evidence_2026-11-19\requests\lf_vented_20_200.json --dry-run
```

## Launch (owner go)

```powershell
$env:HORNLAB_EVIDENCE_AUTHORIZED_BY = "owner 2026-11-19: bounded CPU system evidence queue (beat_cpu only; no GPU); 8 solves"
.venv\Scripts\python.exe tools\run_campaign_night.py `
  --night docs\queue\system_evidence_2026-11-19.yaml
```

- Lane: `cpu`. It holds `runs/.cpu.lane.lock`; it does **not** take `.gpu.lock` and does not start
  a hornlab Julia/CUDA host.
- One job at a time. Estimated wall time: 20–40 min total on this machine (BL `beat_cpu`, 25-freq
  solves were ~2.5 min each; 49-freq and assembled cases are longer).
- Do not launch while the CPU lane is live or while the GUI is running a system job.
- The stale GPU lock observed on 2026-11-20 is irrelevant to this CPU queue, but it must be cleaned
  before any future GPU solve.

## Readout after the run

```powershell
.venv\Scripts\python.exe tools\data\system_cases.py --root . --out docs\system_data --pretty
.venv\Scripts\python.exe -m hornlab_search.system.cli reference report <case> --json
```

Record, per pair:
- LF: BL vs bassbox F3, Fb, port-velocity peak, cone velocity/displacement, phase, and where the
  lumped model diverges.
- 2×2: real-vs-demo and seed-vs-default box deltas per probe; do not rank across references.
- 10 m vs 2 m: per-probe level/phase delta; whether 2 m cuts can support a far-field claim.
- 49 vs 25 freqs: null depth/frequency shift; the numerical floor for any later J comparison.
- Assembled LF: horn loading/port interaction, compared with vented-only.

## Deliberately not in this queue

- **Real-motor assembled case (WP3):** needs a motor-patched assembly project; not a simple
  project copy. Do it after `motor_map` has a supported assembled path or as a reviewed code change.
- **Mesh refinement (convergence WP5):** needs a new mesh (not a request overlay); a separate
  `reference.prepare` job with changed mesh sizes.
- **Real driver shape / panel fit (WP7):** needs maker CAD/measurements; cannot be generated by a
  solve request.
- **System ranking / delay optimization:** still blocked by calibration (decision 3) and the
  numerical floor. This queue supplies the floor and the LF evidence, not the policy.

## Owner gates

- CPU solve authorization: `HORNLAB_EVIDENCE_AUTHORIZED_BY` (this queue).
- Decision 3 (calibration) and decision 6 (authorization record shape) remain open.
- Any GPU horn queue is separate and needs the stale lock cleared plus owner GPU approval.
