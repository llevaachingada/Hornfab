# Evaluation protocol: from watchdog to adaptive experiment allocation

This is a **proposed evaluation contract** for Fable to revise or reject, not a frozen plan or permission to run GPU studies.

## What success must mean

Primary: achieve a **verified** improvement in useful horn acoustic behavior at lower cumulative actual GPU-hours (or more verified designs under fixed GPU-hours). Secondary: increase reusable, correctly identified physical observations; discover acoustically excellent alternatives across coverage/frequency/size; reduce wasted refusals and infrastructure overhead; preserve stable results for future rescores. A smaller raw `J` in a changing scorer or a greater number of attempts is not sufficient.

A fair adaptive campaign must include a fixed-policy control that has access to **equivalent historical data** and receives the same physical-source/brief/mesh/verify conditions. Record compute for BO model training, candidate geometry preflight, resource and cache behavior, test setup and aborted attempts separately. Track time-to-verified-target, best verified acoustic metrics, archive/coverage diversity, and total physical solver time. Historical BO-vs-CMA differences are suggestive, not definitive.

## Minimal offline test suite before any automatic action

1. **Replay parity:** existing watchdog produces the same first-stop row and reason from version-pinned historical logs. Changing observation times/cached statuses does not use future results.
2. **Failure classification:** deliberately mixed geometry, product-envelope, resource, backend-transient and score-error fixtures cannot be interpreted as an acoustic surrogate training set; reported denominators are correct.
3. **Bound interpretation:** hard physical bound, soft experiment box, inactive/conditional gene and manufacturing envelope produce distinct recommendations. An intentionally hard boundary does not prompt auto-widening.
4. **Resume and checkpoint:** interrupted and resumed runs keep current historical identities and progress; stale/duplicate records don't cause a false stop or duplicate data.
5. **Optimizer admission:** advisory switch is refused when cohort has insufficient eligible rows, mixed objective/fidelity, unsupported CAD/GRID projection, mismatched hashes, invalid generated parameters or unverified candidate pool.
6. **QD semantics:** improvement in archive quality/filled cells may justify continued exploration even when best scalar `J` doesn't improve. No fixed 0.5% rule applies across goals.
7. **Queue durability:** simulate invalid YAML, mid-save, agent interruption, duplicate job IDs, simultaneous proposed writes, lock contention, STOP/PAUSE, changing admission manifests and regression to last-good plan. The existing runner's tests must still pass.
8. **Policy noninterference:** shadow mode cannot write to the queue, code, cache or physical study data. Active run settings, source and library pins are immutable under observation.
9. **Approval boundary:** a policy cannot silently alter a validated product brief, source geometry, scoring version, input bounds, target frequency, hardware caps or GPU budget; any new config is a separately identified proposed experiment.
10. **Anytime/censoring:** stopped jobs count consumed resource; unrun alternative jobs are unknown outcomes. No post-hoc cherry-picking of method/seed without disclosure.

## Staged choices Fable should consider

- **No new code:** just more accurate failure labels and human-facing action review.
- **Cheap prototype:** read-only notebook/report that derives alternative next action and uncertainty from historical logs.
- **Shadow service:** persistent but non-actuating advisory alongside existing night runner, with versioned policy and recommendations, until a sufficiently long real-world calibration set exists.
- **Bounded autonomy:** between-job insertion/reordering only for *preapproved, already validated* job IDs and immutable config hashes; no live worker takeover. Owner explicitly authorizes the policy and max time/budget before enabling.
- **Formal adaptive portfolio:** only if simple policy proves insufficient and the data support a defensible reward, uncertainty and exploration model.

For every stage provide what result would make Fable stop development. Controller complexity, latency, maintainability and distraction from source/scoring validity are real costs.
