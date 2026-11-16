# Updated queue: held, bounded, no Bayesian jobs

2026-11-15. This replaces the **plan** for the unstarted E tail; it does not rewrite or resume historical D/E jobs. The owner authorized a few isolated diagnostic solves but not a full search on unresolved families. Two spiral diagnostics finished; no controller is running from this packet.

- `pilot_HELD.yaml` contains only the priority spiral, RNGseeds1234/5678,30 valid evaluations each. Structural runner dry-run passed. No old100-call, cohort, TuRBO, scalar/Pareto or other BO jobs are included.
- `configs/` contains26 flattened, inheritance-resolved config copies with budget30 and explicit45-draw ceiling; `briefs/` preserves referenced brief bytes. All26 configurations and seeds load using their appropriate bridge or native path; [check output](config_checks.json). This does not certify mesh/physics readiness of all26.
- `admission.json` has `full_search_released=false` and every cell held. Each command enters `reviewed_job.py`, checks pins/config/seed, and refuses to start a search until release and per-cell approval are recorded. A failing first job cannot expose an unguarded second job. No admission was granted by this pass.
-30 is the **valid-evaluation target**, not a guarantee of30 new physical calls. Caches and refusals are separately accounted; strict transient policy may retry a candidate. Draw ceiling45 bounds proposals, not a proven30-call ceiling. Before release the next senior must reconcile retries and finalist validation with the owner's desired total; the implementation slices propose24 discovery+6 validation within30. No verification expense is hidden in this draft.
- Only spiral is present in the night. The other25 files are prepared review copies, excluded from the solve list until their readiness gates pass. Their correct generators/bounds are preserved; no useful controls were frozen or enlarged to manufacture eligibility.

Safe inspection from canonical root:

```powershell
.venv\Scripts\python.exe tools/run_campaign_night.py --night docs/queue/rolled_readiness_2026-11-15/pilot_HELD.yaml --dry-run
.venv\Scripts\python.exe docs/queue/rolled_readiness_2026-11-15/reviewed_job.py --cell hl__rolled_es_spiral_v7 --check
```

Do not invoke a controller yet. [Senior findings](../../research/typologies/audit_2026-11-15/READINESS.md) and [handoff](../../research/typologies/audit_2026-11-15/HANDOFF.md) give the unresolved physical/objective decisions.

For eventual spiral verification use the existing direct helper `tools/geometry/verify_rolled_rect_night.py`, or the required bridge's normal `verify --run ...`. `rolled_rect_cli.py verify-night` is not implemented. Do not patch that old wrapper casually: its bytes are part of pinned recipe digests. The new guard is additive and preserves those old recipes.
