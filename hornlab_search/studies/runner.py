"""Adaptive serial runner core with injected durable and execution adapters.

No production adapter is provided here. journal.claim/begin/finish are REQUIRED
atomic durable operations; lane.owned must hold the explicit lane lock throughout
and configure lane-specific roots. evaluator.lookup and evaluator.evaluate must
use exact solve identities. The caller must reconcile before resuming. Adapters
must not treat a Python exception after dispatch as proof no call occurred.
"""
from __future__ import annotations

from datetime import datetime, timezone


class ContractError(ValueError):
    pass


def _validate(package, dry_run):
    if package.get('execution_mode') != 'adaptive_serial':
        raise ContractError('adaptive_serial required')
    if package.get('lane') not in ('cpu', 'gpu'):
        raise ContractError('explicit cpu or gpu lane required')
    for key in ('study_id', 'package_id', 'spec_revision'):
        if package.get(key) is None:
            raise ContractError(f'{key} required')
    budget = package.get('budget') or {}
    for key, cap in (('screen_calls', 18), ('verify_calls', 6), ('total_calls', 24), ('attempts', 120)):
        value = budget.get(key)
        if type(value) is not int or value < 0 or value > cap:
            raise ContractError(f'invalid {key} cap')
    if not dry_run:
        try:
            deadline = datetime.fromisoformat(str(package['deadline']).replace('Z', '+00:00'))
            if deadline.tzinfo is None:
                raise ValueError('timezone required')
        except (KeyError, ValueError) as exc:
            raise ContractError('real timezone-aware deadline required') from exc
        return deadline.astimezone(timezone.utc)
    return None


def run_package(package, evaluator_adapter, lane_adapter, journal, *, dry_run=False,
                clock=lambda: datetime.now(timezone.utc)):
    """Run serially; return explicit stop reasons, never claim exactly-once execution.

    Journal interface: claim(package) -> bool atomically validates revision and
    exclusive launch; state(package_id) -> dict with attempts, screen_calls,
    verify_calls, total_calls, reservations, consecutive_failures, unresolved;
    begin(package, candidate, reserve_call) -> attempt id atomically checks
    revision, budgets, attempts and reserves before dispatch; finish(attempt_id,
    result) atomically records result/observation and reconciles reservation;
    release(package_id, status). A failed/ambiguous begin raises and dispatches
    nothing. Failed finish leaves the attempt unresolved. Proposal/refit state
    and proposal cadence must be persisted by journal/proposer adapters.

    evaluator: next_candidate(state) -> candidate or None; lookup(candidate)
    returns an exact-identity cached result or None; preflight(candidate) returns
    refusal result or None; evaluate(candidate, attempt_id) performs at most one
    backend call and returns call_status called/not_called (otherwise unknown);
    observe(result) returns bool (false pauses on model failure).
    Candidate has kind screen/verify/audit and exact solve_id. Adapter must select
    verified finalists/audit under the frozen policy and persist its RNG state.
    """
    deadline = _validate(package, dry_run)
    if dry_run:
        return {'status': 'dry_run', 'deadline_required': not bool(package.get('deadline'))}
    # Production wiring must opt in only after implementing the documented atomic
    # revision, launch, reservation, recovery and budget contract. No implicit fallback.
    contract = getattr(journal, 'durable_contract', None)
    if contract not in ('b5-journal-v1', 'b5-journal-v2'):
        return {'status': 'capability_missing', 'reason': 'durable_attempt_journal_unavailable'}
    if getattr(lane_adapter, 'lane_contract', None) != 'b5-owned-lane-v1':
        return {'status': 'capability_missing', 'reason': 'owned_lane_adapter_unavailable'}
    if not journal.claim(package):
        return {'status': 'launch_conflict_or_stale'}
    status = 'interrupted'
    try:
        with lane_adapter.owned(package['lane'], package):
            if contract == 'b5-journal-v2':
                progress = journal.load_progress(package['package_id'])
                if not evaluator_adapter.restore_progress(progress):
                    status = 'model_unavailable'
                    return {'status': status}
            while True:
                state = journal.state(package['package_id'])
                if state.get('unresolved'):
                    status = 'unknown'; break
                if not journal.is_current(package):
                    status = 'stale'; break
                if clock() >= deadline:
                    status = 'deadline'; break
                if journal.cancelled(package['package_id']):
                    status = 'cancelled'; break
                if state.get('consecutive_failures', 0) >= 3:
                    status = 'infrastructure_failures'; break
                if state.get('attempts', 0) >= package['budget']['attempts']:
                    status = 'attempt_budget'; break
                progress = journal.load_progress(package['package_id']) if contract == 'b5-journal-v2' else None
                candidate = progress.get('pending_candidate') if progress else None
                if candidate is None:
                    candidate = evaluator_adapter.next_candidate(state)
                    if candidate is None:
                        status = 'pool_exhausted'; break
                    if candidate.get('kind') not in ('screen', 'verify', 'audit') or not candidate.get('solve_id'):
                        raise ContractError('candidate kind and exact solve_id required')
                    if progress is not None:
                        prior_index = progress['proposal_index']
                        staged = journal.stage_proposal(
                            package, candidate, prior_index, evaluator_adapter.proposal_rng_state(),
                            f"proposal:{package['package_id']}:{prior_index + 1}")
                        if not staged:
                            status = 'stale_or_proposal_conflict'; break
                if candidate.get('kind') not in ('screen', 'verify', 'audit') or not candidate.get('solve_id'):
                    raise ContractError('candidate kind and exact solve_id required')
                cached = evaluator_adapter.lookup(candidate)
                refusal = None if cached is not None else evaluator_adapter.preflight(candidate)
                # Preflight/cache inspection may take time; no dispatch after a stop boundary.
                if not journal.is_current(package):
                    status = 'stale'; break
                if clock() >= deadline:
                    status = 'deadline'; break
                if journal.cancelled(package['package_id']):
                    status = 'cancelled'; break
                reserve = cached is None and refusal is None
                # Atomic begin must recheck revision, call caps and attempts; cache
                # recheck happened while owning the lane. Unknown stays reserved.
                attempt_id = journal.begin(package, candidate, reserve)
                if attempt_id is None:
                    status = 'budget_exhausted_or_stale'; break
                if cached is not None:
                    result = cached
                elif refusal is not None:
                    result = refusal
                else:
                    try:
                        result = evaluator_adapter.evaluate(candidate, attempt_id)
                    except Exception:
                        status = 'unknown'; break
                # A malformed/ambiguous dispatched result cannot release the reservation.
                if reserve and (not isinstance(result, dict) or
                                result.get('call_status') not in ('called', 'not_called')):
                    status = 'unknown'; break
                journal.finish(attempt_id, result)
                if not evaluator_adapter.observe(result):
                    status = 'model_unavailable'; break
    finally:
        journal.release(package['package_id'], status)
    return {'status': status}


def select_verification(rows, *, mode, audit_seed, objective_box=None, limit=4):
    """Select actual eligible unique screens; unknown/already-verified specs excluded.

    Pareto objectives are minimization values in the fixed two-dimensional box.
    Audit sampling is uniform over remaining eligible geometries using a reserved
    seed. Missing/non-finite evidence is excluded rather than invented.
    """
    import math
    import random

    if mode not in ('scalar', 'pareto') or not 0 <= limit <= 4:
        raise ContractError('invalid verification policy')
    candidates = {}
    audit_candidates = {}
    seen = set()
    for row in rows:
        ident = row.get('geometry_id')
        if (not ident or row.get('eligible') is not True or row.get('measured_screen') is not True
                or row.get('already_verified') is not False):
            continue
        if ident in seen:
            # Ambiguous duplicates are excluded, rather than picking a favorable result.
            candidates[ident] = None
            audit_candidates[ident] = None
            continue
        seen.add(ident)
        if mode == 'scalar':
            v = row.get('j')
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
                continue
        else:
            v = row.get('objectives')
            if not isinstance(v, (list, tuple)) or len(v) != 2 or any(
                isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in v
            ):
                continue
        audit_candidates[ident] = row
        if mode == 'pareto' and row.get('feasible') is not True:
            continue
        candidates[ident] = row
    candidates = {k: v for k, v in candidates.items() if v is not None}
    if mode == 'scalar':
        ranked = sorted(candidates.values(), key=lambda r: (r['j'], r['geometry_id']))
    else:
        if (not isinstance(objective_box, (list, tuple)) or len(objective_box) != 2 or
            any(not isinstance(b, (list, tuple)) or len(b) != 2 or
                not all(isinstance(x, (float, int)) and math.isfinite(x) for x in b) or
                b[1] <= b[0] for b in objective_box)):
            raise ContractError('finite fixed reference-normalized objective box required')
        values = list(candidates.values())
        front = [r for r in values if not any(
            all(a <= b for a, b in zip(other['objectives'], r['objectives'])) and
            any(a < b for a, b in zip(other['objectives'], r['objectives']))
            for other in values if other is not r)]
        crowd = {r['geometry_id']: 0.0 for r in front}
        for dim, (lo, hi) in enumerate(objective_box):
            ordered = sorted(front, key=lambda r: (r['objectives'][dim], r['geometry_id']))
            if ordered:
                crowd[ordered[0]['geometry_id']] = float('inf')
                crowd[ordered[-1]['geometry_id']] = float('inf')
            for i in range(1, len(ordered) - 1):
                crowd[ordered[i]['geometry_id']] += (ordered[i+1]['objectives'][dim] -
                                                       ordered[i-1]['objectives'][dim]) / (hi-lo)
        ranked = sorted(front, key=lambda r: (-crowd[r['geometry_id']], r['geometry_id']))
    finalists = [r['geometry_id'] for r in ranked[:limit]]
    remaining = sorted(k for k, v in audit_candidates.items() if v is not None and k not in finalists)
    audits = random.Random(audit_seed).sample(remaining, min(2, len(remaining)))
    return {'finalists': finalists, 'audits': audits, 'shortfall': max(0, 4-len(finalists)),
            'audit_shortfall': max(0, 2-len(audits)), 'audit_seed': audit_seed}
