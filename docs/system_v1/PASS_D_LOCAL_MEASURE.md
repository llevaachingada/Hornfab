# Pass D: local CPU measurements through the funnel (BL `beat_cpu`, no GPU)

**Depends on:** Pass A + B3 (funnel) merged locally; Pass 0 done. **Owner approval required** for
each solve batch (an `AuthorizationRecord`, contract §4; a legacy string is acceptable here until
decision 6 is final, and is recorded as `legacy_free_string: true`).
**One BL job at a time.** The CPU lane lock (`runs\.cpu.lane.lock`) is held for the whole pass; do
not start while another CPU-lane search is live. GPU is untouched.

## Order (cheapest unknowns first; handbook §7.4 steps 3-6)

| Step | Work | Cases | Acceptance |
|---|---|---|---|
| D1 | WP2 matrix: solve #6 (real motor x default box) + demo motor x default box | 2 solves on identical geometry columns to #4/#5 | 4/4 cells solved; 2x2 delta table (complex, per excitation) recorded |
| D2 | WP1 LF band: 20-200 Hz request overlay on #4, #5 (+ default-box cell from D1) | 3 solves, log-spaced, include Fb region (~30-53 Hz) | complete low-freq manifests; Fb and port-velocity check vs `bass_reference`; R17 end-correction note |
| D3 | WP3 real-motor assembled R2 vs demo A/B | 1-2 solves | BL validate rc 0, 25/25 freqs, deltas recorded |
| D4 | WP5 convergence on R2: one mesh refinement + frequency densification near crossover; one `float64` control (B9) | 2-3 solves | predeclared tolerance (write it **before** solving): complex-pressure delta at XO and null depth delta |

Each step:

1. `python -m hornlab_search.system.cli funnel --plan ...` -> review the plan ledger.
2. Owner signs the authorization record for exactly those case keys.
3. `funnel --execute --allow-bl --authorization <file>`.
4. Evidence doc per `hornlab-evidence` skill; run `tools/evidence/verify_evidence_quotes.py` on it.
5. Regenerate `docs/system_data/`; readiness.yaml gets declarations for the new cases.
6. Commit with CONTINUITY/ISSUES.

## Paste-ready brief

```
You are the local operator for HornFab System v1 Pass D. Read docs/system_v1/README.md sections 1,
3 and 6 and docs/system_v1/PASS_D_LOCAL_MEASURE.md. Run steps D1-D4 in order, one BL CPU job at a
time, each through the funnel command with an owner-signed authorization record for exactly the
planned case keys. Write tolerances before D4 solves. After each step: evidence doc, byte-check,
regenerate docs/system_data, readiness declarations, one commit with CONTINUITY and ISSUES. Stop and
report on any BL refusal, validate rc != 0, or a result that contradicts the 2x2 expectation.
```
