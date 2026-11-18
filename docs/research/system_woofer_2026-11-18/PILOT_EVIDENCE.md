# PILOT_EVIDENCE — Stage 2 fixed-horn CPU pilot (research-only, screen_only)

Date 2026-11-18, worktree `feat/woofer-system-v0`. Everything below was executed on this machine
from the worktree venv (`OMP_NUM_THREADS=1`), CPU-only, no GPU, no solver, no canonical writes.
All claims are labeled; the fidelity cap for this stage is **screen_only**.

## 1. What ran

```
python -m hornlab_search.system.cli pilot ^
  --spec examples/systems/two_way_80x50_700_research.yaml ^
  --driver-stem faitalpro_12pr300   --asset-id 0062fb59fbf63eae --limit-boxes 8 --out system_runs
python -m hornlab_search.system.cli pilot ... --driver-stem faitalpro_12pr320 ...
python -m hornlab_search.system.cli list-assets --limit 5
python -m hornlab_search.system.cli list-drivers
```

* Asset: `0062fb59fbf63eae` — real saved solve, family FREEFORM, brief `lecleach_rollback_1in_v6`,
  run `runs/20261118T200653Z-screen-31495a`, design `9e02db06ecc3`, 500–5500 Hz (12 solved
  frequencies), complex `p_balloon`/`p_h`/`p_v` present as stored (MAGNITUDE_ONLY quality under the
  system contract because the stored drive is unit normal acceleration in exp(−iωt)).
* Drivers: `faitalpro_12pr300` / `faitalpro_12pr320` — vendor-page machine-verified T/S
  (see `docs/research/system_woofer_2026-11-18/SOURCES.md`).

## 2. Import-boundary conversion result (the phase-honest seam)

`convert_asset` produced a `SCREEN_COMPLEX_APPROX` response with the conversion record:
`from_drive: unit_normal_acceleration → to_per_input: normal_velocity_mps`,
`from_time: exp(−iωt) → to: exp(+jωt)`, `via: compare.hornfab_side.accel_to_canonical`,
`distance_m: 2.0` (from stored meta), `origin_declared: false`, `phase_qualified: false`.
Claims allowed: `level_only_cross_tier`, `screen_complex_approx`. Claims refused:
`absolute_pa_per_volt`, `installed_directivity`, `installed_system_score`. No phase was imputed;
the conversion is the in-repo tested seam and its magnitude shift is exact (+20·log10(2πf)).

## 3. Deterministic pilot results (Pareto report rows; winner refused by design)

Both pilots: 8 box candidates spanning 35 L → 115 L (smallest half + largest half of the feasible
set), study ids **`783043edcbecf2fe`** (12PR300) and **`0352ca1af0532aba`** (12PR320) — reruns are
byte-identical (unit-tested). Markdown summary (both runs):

```
winner: (none)
winner_status: all non-dominated rows carry FAIL/REFUSED status; no sole winner
| box04 | PASS | PASS | FAIL | SCREEN | pareto |    (12PR300; larger boxes, F3 gate OK)
| box00 | PASS | FAIL | FAIL | SCREEN | pareto |    (12PR300; smallest boxes, F3 gate FAIL)
```

Key numbers:

| driver | LF gate (F3 ≤ 55 Hz) | best F3 (at 115 L) | crossover axis | horn BW (screen) | piston BW |
|---|---|---|---|---|---|
| 12PR300 | 4/8 rows PASS | 45.6 Hz | FAIL (all rows) | 78.0° @700, 57.7° @1000, 48.7° @1300 | NaN @700, 68.0° @1000, 45.5° @1300 |
| 12PR320 | 4/8 rows PASS | 46.0 Hz | FAIL (all rows) | same horn screen | NaN @700, 67.2° @1000, 45.2° @1300 |

**The crossover FAIL is the master-doc §4.3 finding reproduced from real data + closed form**: at
700 Hz the ideal-piston benchmark for a 12-inch effective piston (a = √(Sd/π) ≈ 13 cm) has **no
−6 dB crossing in the front half-space** (stored `NaN`), while the saved horn's screen shows 78°.
The screen flags "woofer directivity at the handoff is far wider than the horn; not a final system
verdict" instead of ranking a winner. DSP is fixed at gains 0/delay 0/LR4 by the claims-refused
list — delay optimization stays disabled without phase-qualified installed fields.

## 4. What this stage can and cannot claim

CAN claim (screen_only, report-only): box feasibility from the fixed lumped model (limits: Xmax /
P_AES / 17 m/s port convention, 1 m half space), F3-vs-target gates against the spec's own target,
noncoherent polar handoff flagging, deterministic reproducible reports with per-row provenance ids.

CANNOT claim (encoded as refs, not omissions): no coherent sum, no delay optimization, no
absolute Pa/Volts, no installed directivity, no system score, no port turbulence, no cone breakup,
no room. The horn side is an isolated-horn converted basis (approximation documented per row).

## 5. Fix discovered by the pilot run (recorded)

`contracts.canonical_json` stringified booleans and mis-sorted non-string dict keys (float keys
sorted numerically at write, lexicographically at reload) → manifest integrity refused its own
pilot manifest. Both fixed (bool passthrough; keys normalized + sorted by string) and covered by
the pilot round-trip test. The first broken pilot manifests remain in `system_runs/…`
(untouched, by immutability) as the failure record.

## 6. Provenance / reproduce

Every pilot writes an immutable case manifest under
`system_runs/system/two_way_80x50_700_pilot/<UTC>-pilot-<pid>-<uuid>/manifest.json`
(sha-self-checked; contains spec, study id, BL-asset provenance, full rows). Rerun the two
commands in §1; the unit test `tests/system/test_horn_import.py::test_pilot_manifest_round_trips`
pins the row↔manifest equivalence (canonical form).
