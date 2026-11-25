"""Immutable adaptive-serial run packages for Bayesian design studies.

A package is an authorization binding, not a claim that future candidates are
known.  Its bytes are canonical JSON and its identity is the SHA-256 of those
bytes (``package_id`` == published artifact hash).  The body deliberately does
not include ``package_id``; readers reconstruct the full object by adding it.

No solver, mesher, GPU, lane or job-manager call happens here.  Publication is
the existing atomic, hash-verified :meth:`StudyStore.publish` path through
``StudyService.attach_artifact``.
"""
from __future__ import annotations

import json
import hashlib
import os
import re
import sys
from pathlib import Path, PurePosixPath
from datetime import datetime, timezone

from .schema import PROTOCOL, Conflict, StudyError, Unavailable, canonical, digest

PACKAGE_SCHEMA = 'run-package-v1'
PACKAGE_KIND = 'package'
EXECUTION_MODE = 'adaptive_serial'
REAL_DATA_OFFLINE = 'real_data_offline_v1'
#: Versioned opt-in provenance mode for a REAL solver package.  Everything else in a
#: metric package stays synthetic/offline-only; this mode is the single exception and is
#: gated by a task-level approval record plus a parent release at execution time.
REAL_METRIC = 'real_metric_v1'

#: Fixed, versioned task-approval record schema.  The package body carries only the record's
#: repo-relative path and the six frozen approval fields; the record itself is re-read (and its
#: pinned files re-hashed) at prepare, dry-run and execute time.
METRIC_APPROVALS_SCHEMA = 'metric-real-approvals-v1'
METRIC_APPROVAL_REFIT_EVERY = 4
METRIC_REAL_PROFILES = ('metric-canary-8x2', 'metric-adaptive-20x2', 'metric-adaptive-30x2')
#: ``HELD_PENDING_PARENT_RELEASE`` may be prepared/dry-run but never executed; only the
#: explicit ``APPROVED_FOR_CANARY`` state (plus the CLI parent gate) can reach dispatch.
METRIC_APPROVAL_STATUSES = ('HELD_PENDING_PARENT_RELEASE', 'APPROVED_FOR_CANARY')
METRIC_EXECUTABLE_APPROVAL_STATUSES = ('APPROVED_FOR_CANARY',)

_HEX16 = re.compile(r'[0-9a-f]{16}')
_HEX40 = re.compile(r'[0-9a-f]{40}')
_HEX64 = re.compile(r'[0-9a-f]{64}')
_APPROVAL_IDENTITY_FIELDS = ('task_identity', 'backend', 'fidelity', 'grid_hash',
                             'dependency_hash', 'mesh_hash')


def repo_root() -> Path:
    """The canonical source checkout; approvals records are resolved relative to it."""
    return Path(__file__).resolve().parents[2]

#: Frozen baseline budget from protocol bo-study-v1.1 section 4.  A prepared
#: package must carry exactly these caps; callers cannot widen or shrink them.
EXECUTION_BUDGET = {
    'screen_calls': 18,
    'verify_calls': 6,
    'total_calls': 24,
    'attempts': 120,
}

#: Named budget profiles (2026-11-14, docs/queue/BO_VS_CMA_PLAN_2026-11-15.md). ``baseline`` IS the
#: frozen bo-study-v1.1 budget above and stays the default: a package without ``budget_profile``
#: must carry it exactly, as before. ``comparison-*`` profiles exist ONLY for matched BO-vs-CMA
#: campaigns at equal new-solve budget; a package selects one explicitly and the profile name is part
#: of the package body, so its identity hash records the choice. Unknown profiles are refused.
#: ``comparison-25``/``comparison-30`` are the small multi-typology campaign budgets. The frozen
#: verification rule selects up to 4 finalists + 2 audits; a profile with fewer ``verify_calls``
#: verifies fewer and the runner reports the shortfall (it never substitutes a predicted design).
#: Owner decisions 2026-11-15: ``comparison-25x2`` = 25 screens + 2 verify (two finalists, no audits);
#: ``comparison-25x0`` = 25 screens, NO verification at all (screen-only arm, cheapest). Neither can
#: evaluate the campaign rule "the improvement survives the audit pair"; use ``comparison-25`` when
#: the decision depends on a verified finalist.
BUDGET_PROFILES = {
    'baseline': dict(EXECUTION_BUDGET),
    'comparison-25': {'screen_calls': 25, 'verify_calls': 6, 'total_calls': 31, 'attempts': 150},
    'comparison-25x2': {'screen_calls': 25, 'verify_calls': 2, 'total_calls': 27, 'attempts': 150},
    'comparison-25x0': {'screen_calls': 25, 'verify_calls': 0, 'total_calls': 25, 'attempts': 150},
    'comparison-30': {'screen_calls': 30, 'verify_calls': 6, 'total_calls': 36, 'attempts': 180},
    'comparison-60': {'screen_calls': 60, 'verify_calls': 6, 'total_calls': 66, 'attempts': 300},
    'comparison-80x2': {'screen_calls': 80, 'verify_calls': 2, 'total_calls': 82, 'attempts': 400},
    'comparison-100x2': {'screen_calls': 100, 'verify_calls': 2, 'total_calls': 102, 'attempts': 500},
    'exploration-300x4': {'screen_calls': 300, 'verify_calls': 4, 'total_calls': 304, 'attempts': 1500},
    # WP 2.1 (fidelity ladder): B1 = ten designs at the screen cap plus the same ten at the finalist
    # tier (2x screen DOF cap, >= 29 frequencies). The finalist solves are counted in ``verify_calls``;
    # the runner's per-tier dispatch of those calls is the open wiring (see CONTINUITY).
    'fidelity-ladder-10': {'screen_calls': 10, 'verify_calls': 10, 'total_calls': 20, 'attempts': 60},
    # Real metric-composite canary (D1): 8 actual screen calls and a separately budgeted
    # verify pair.  ``metric-adaptive-30x2`` is the follow-up tranche and is refused until a
    # task approval record names an accepted canary package.
    'metric-canary-8x2': {'screen_calls': 8, 'verify_calls': 2, 'total_calls': 10, 'attempts': 60},
    'metric-adaptive-20x2': {'screen_calls': 20, 'verify_calls': 2, 'total_calls': 22, 'attempts': 140},
    'metric-adaptive-30x2': {'screen_calls': 30, 'verify_calls': 2, 'total_calls': 32, 'attempts': 180},
}


def budget_caps(package) -> dict:
    """The exact budget a package must carry: its named profile, ``baseline`` when absent."""
    profile = (package or {}).get('budget_profile', 'baseline')
    if profile not in BUDGET_PROFILES:
        raise StudyError(f'unknown budget_profile {profile!r} (known: {sorted(BUDGET_PROFILES)})')
    return dict(BUDGET_PROFILES[profile])


REQUIRED_ARTIFACTS = ('snapshot', 'model', 'proposal')
STATUS_NOTE = 'cheap-check-passed; mesh/acoustic eligibility unknown'
# Include every executable input: replay, metric/scoring helpers, configuration,
# geometry links and proposal policy all affect a resumed study's decisions.
EXECUTION_CODE_FILES = tuple(sorted({
    path.relative_to(Path(__file__).resolve().parents[2]).as_posix()
    for path in Path(__file__).resolve().parents[1].rglob('*.py')
} | {
    'hornlab_search/design/generators/rolled_family.py',
    'hornlab_search/design/generators/_rolled_rect_v1.py',
    'hornlab_search/design/generators/_crowe_section_v2.py',
    'hornlab_search/design/generators/data/crowe_section_reference_v1.yaml',
}))

STOP_RULES = (
    'stop on total/screen/verify/attempt budget exhaustion',
    'stop on the required timezone-aware deadline',
    'stop on explicit cancellation',
    'stop on pool exhaustion or stale/invalid package revision',
    'stop after three consecutive infrastructure/solver-host failures',
    'numerical model failure pauses BO and labels any exploration recommendation',
)

RECOVERY_RULES = (
    'persist attempt intent before dispatch and reconcile before any resume',
    'an unknown in-flight attempt cannot automatically relaunch or spend budget',
    'reconciliation or an explicit resolved package is required to continue',
    'reserve one conservative BEM-call unit before each backend invocation',
    'cache/already-verified identity is rechecked after lane ownership and before dispatch',
)

ADAPTIVE_POLICY = {
    'mode': EXECUTION_MODE,
    'permits_hash_linked_child_snapshots': True,
    'permits_hash_linked_child_models': True,
    'child_observations': 'only this run\'s compatible measured observations',
    'initial_snapshot_model_proposal_are_fixed': True,
    'manual_change_invalidates': ['spec', 'source', 'cohort', 'policy'],
    'display_only_selection_invalidates': False,
    'display_only_selection_may_append_events': True,
}

VERIFICATION_POLICY = {
    'finalists_max': 4,
    'scalar_rank': 'actual frozen J ascending',
    'pareto_rank': 'feasible nondominated by descending crowding distance in the fixed '
                   'reference-normalized box',
    'tie_break': 'geometry ID',
    'audit_samples': 2,
    'audit_sampling': 'uniform over remaining eligible screened designs',
    'audit_seed_source': 'reserved audit RNG',
    'duplicate_exclusion': 'duplicates and already-verified exact specs are excluded',
    'shortfall': 'verify fewer and report the shortfall; never substitute predicted designs',
}


def _timezone_deadline(value):
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise StudyError('deadline must be an ISO-8601 string')
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise StudyError('deadline must be ISO-8601') from exc
    if parsed.tzinfo is None:
        raise StudyError('deadline must be timezone-aware')
    return value


def _deadline_moment(value):
    """Parse a validated timezone-aware deadline string into an aware datetime."""
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def _is_hex(value, pattern):
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def _approval_record_path(record, *, root=None):
    """Normalize a repo-relative approvals path and refuse escapes/absolute forms."""
    if not isinstance(record, str) or not record.strip():
        raise StudyError('metric approvals record must be a repo-relative path')
    text = record.strip().replace('\\', '/')
    pure = PurePosixPath(text)
    if pure.is_absolute() or re.match(r'^[A-Za-z]:', text) or not pure.parts \
            or any(part in ('', '.', '..') for part in pure.parts):
        raise StudyError('metric approvals record must stay inside the repository')
    relative = pure.as_posix()
    base = Path(root) if root is not None else repo_root()
    return relative, base / pure


def _approval_caps(payload):
    profile = payload.get('profile')
    if profile not in BUDGET_PROFILES or profile not in METRIC_REAL_PROFILES:
        raise StudyError(f'unknown real metric approvals profile {profile!r}')
    caps = BUDGET_PROFILES[profile]
    for field in ('screen_cap', 'verify_cap'):
        value = payload.get(field)
        if type(value) is not int or value < 0:
            raise StudyError(f'metric approvals {field} must be a non-negative integer')
    if payload['screen_cap'] != caps['screen_calls'] or payload['verify_cap'] != caps['verify_calls']:
        raise StudyError('metric approvals caps must equal the named budget profile')
    if payload.get('refit_every') != METRIC_APPROVAL_REFIT_EVERY:
        raise StudyError(f'metric approvals refit_every must be {METRIC_APPROVAL_REFIT_EVERY}')
    if payload.get('lane') != 'gpu':
        raise StudyError('metric approvals must authorize the gpu lane')
    return profile, caps


def load_metric_approvals(record, *, root=None):
    """Read and structurally validate a task approval record; never touches a backend.

    Returns ``{'record', 'path', 'payload'}``.  ``HELD_PENDING_PARENT_RELEASE`` records are valid
    for rehearsal (prepare/dry-run); execution additionally requires ``APPROVED_FOR_CANARY``.
    """
    relative, path = _approval_record_path(record, root=root)
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise Unavailable(f'metric approvals record cannot be read: {exc}') from exc
    try:
        payload = json.loads(raw.decode('utf-8-sig'))
    except (UnicodeDecodeError, ValueError) as exc:
        raise StudyError('metric approvals record is not valid UTF-8 JSON') from exc
    if not isinstance(payload, dict):
        raise StudyError('metric approvals record must contain an object')
    if payload.get('schema') != METRIC_APPROVALS_SCHEMA:
        raise StudyError('unsupported metric approvals schema')
    if payload.get('status') not in METRIC_APPROVAL_STATUSES:
        raise StudyError('metric approvals status must be one of '
                         + ', '.join(METRIC_APPROVAL_STATUSES))
    profile, _ = _approval_caps(payload)
    if not _is_hex(payload.get('task_identity'), _HEX16):
        raise StudyError('metric approvals task_identity must be 16 lowercase hex')
    if not _is_hex(payload.get('artifact_sha256'), _HEX64):
        raise StudyError('metric approvals artifact_sha256 must be a sha256')
    identity = payload.get('identity')
    if not isinstance(identity, dict):
        raise StudyError('metric approvals identity must be an object')
    for field in _APPROVAL_IDENTITY_FIELDS:
        if not isinstance(identity.get(field), str) or not identity[field].strip():
            raise StudyError(f'metric approvals identity field {field!r} is required')
    if identity.get('task_identity') != payload['task_identity']:
        raise StudyError('metric approvals identity disagrees with its task_identity')
    if profile in ('metric-adaptive-20x2', 'metric-adaptive-30x2'):
        acceptance = payload.get('canary_acceptance')
        if not isinstance(acceptance, dict) or acceptance.get('accepted') is not True \
                or not _is_hex(acceptance.get('canary_package_id'), _HEX64):
            raise StudyError('the adaptive metric profile requires an accepted canary package')
    return {'record': relative, 'path': path, 'payload': payload}


def _check_approval_bindings(payload, *, task_identity, artifact_sha256, caps):
    """Cross-check approval constraints against the frozen metric artifact identity."""
    if payload.get('task_identity') != task_identity:
        raise Unavailable('metric approvals task_identity does not match the training artifact')
    if payload.get('artifact_sha256') != artifact_sha256:
        raise Unavailable('metric approvals artifact_sha256 does not match the training artifact')
    if payload.get('screen_cap') != caps['screen_calls'] \
            or payload.get('verify_cap') != caps['verify_calls']:
        raise StudyError('metric approvals caps must equal the package profile caps')


def _proposal_identity(service, study_id, revision, spec):
    """Read the current proposal policy (or the spec/default) for the package body.

    Older fixtures predate the explicit policy block; they default to ``scalar``
    so every existing package keeps working.  The value is descriptive of the
    verified selection rule and never grants new execution authority.
    """
    from hornlab_search.bo import policy as policy_mod

    source = 'default'
    policy = None
    detail = service.get_artifact_metadata(study_id, 'proposal', revision=revision)
    if detail.get('status') == 'available':
        sha = detail.get('sha256')
        try:
            proposal = service.store.read_artifact(sha)
            try:
                payload = json.loads(proposal.decode('utf-8'))
            except (UnicodeDecodeError, ValueError):
                payload = None
            if isinstance(payload, dict):
                policy = (payload.get('proposal_policy')
                          or payload.get('policy')
                          or (payload.get('selection') or {}).get('proposal_policy'))
                if policy:
                    source = 'proposal'
        except Unavailable:
            policy = None
    if not policy and isinstance(spec, dict):
        block = spec.get('policy') if isinstance(spec.get('policy'), dict) else {}
        policy = block.get('proposal_policy')
        if not policy and block.get('mode') in policy_mod.PROPOSAL_POLICIES:
            policy = block['mode']
        if policy:
            source = 'spec'
    if not policy:
        policy = policy_mod.POLICY_SCALAR
        source = 'default'
    if policy not in policy_mod.PROPOSAL_POLICIES:
        raise StudyError(f'unsupported proposal policy {policy!r}')
    return {'policy': policy,
            'verification_mode': policy_mod.verification_mode(policy),
            'source': source}


def package_hash(package):
    """Return the SHA-256 identity over the canonical package body.

    ``package_id`` itself is excluded so the identifier is not circular.
    """
    if not isinstance(package, dict):
        raise StudyError('package must be an object')
    body = {key: value for key, value in package.items() if key != 'package_id'}
    return digest(body)


def verify_candidate_policy(package, config, *, pool=None):
    """Check the separate candidate policy binding without changing solve identities.

    New scalar and TuRBO regional runs require a bound proposal and package.
    Other policies retain their existing admission contracts.
    """
    from hornlab_search.config import envelope_policy
    actual = envelope_policy(config.brief)
    bound = package.get('candidate_policy')
    if bound is None:
        policy = (package.get('proposal_policy') or {}).get('policy') or 'scalar'
        if policy in ('scalar', 'turbo') and actual.mode in ('exploration', 'discovery'):
            raise Unavailable('open or near-envelope execution requires a candidate-policy binding')
        return
    if not isinstance(bound, dict) or bound.get('policy_id') != actual.policy_id:
        raise Unavailable('candidate envelope policy changed since the proposal was frozen')
    if pool is not None:
        recorded = pool.get('candidate_policy') if isinstance(pool, dict) else None
        if not isinstance(recorded, dict) or recorded.get('policy_id') != actual.policy_id:
            raise Unavailable('candidate pool envelope policy differs from the package')


def verify_package(package):
    """Validate package identity/shape without publishing, dispatching or solving."""
    if not isinstance(package, dict):
        raise StudyError('package must be an object')
    pid = package.get('package_id')
    if not isinstance(pid, str) or not pid:
        raise StudyError('package_id required')
    if digest({key: value for key, value in package.items() if key != 'package_id'}) != pid:
        raise Unavailable('package content hash mismatch')
    if package.get('schema') != PACKAGE_SCHEMA:
        raise StudyError('unsupported package schema')
    if package.get('protocol') != PROTOCOL:
        raise StudyError('package protocol must be bo-study-v1.1')
    if package.get('execution_mode') != EXECUTION_MODE:
        raise StudyError('adaptive_serial execution mode required')
    if package.get('lane') not in ('cpu', 'gpu'):
        raise StudyError('package lane must be cpu or gpu')
    if not isinstance(package.get('study_id'), str) or not package['study_id']:
        raise StudyError('package study_id required')
    if type(package.get('spec_revision')) is not int or package['spec_revision'] < 1:
        raise StudyError('package spec_revision required')
    if package.get('deadline_required') is not True:
        raise StudyError('package deadline_required must be true')
    _timezone_deadline(package.get('deadline'))
    if package.get('budget') != budget_caps(package):
        raise StudyError('package budget must exactly match its budget profile '
                         '(the frozen execution budget unless budget_profile is set)')
    if package.get('status_note') != STATUS_NOTE:
        raise StudyError('package status_note must state cheap-check-only eligibility')
    proposal_policy = package.get('proposal_policy')
    candidate_policy = package.get('candidate_policy')
    if candidate_policy is not None and (not isinstance(candidate_policy, dict)
            or not isinstance(candidate_policy.get('policy_id'), str)
            or not candidate_policy['policy_id'].startswith('envelope-v1-')):
        raise StudyError('package candidate_policy must contain an envelope policy identity')
    if proposal_policy is not None:
        from hornlab_search.bo import policy as policy_mod
        if not isinstance(proposal_policy, dict):
            raise StudyError('package proposal_policy must be an object')
        policy = proposal_policy.get('policy')
        if policy not in policy_mod.PROPOSAL_POLICIES:
            raise StudyError('package carries an unsupported proposal policy')
        if proposal_policy.get('verification_mode') != policy_mod.verification_mode(policy):
            raise StudyError('package verification_mode disagrees with the proposal policy')
    metric = package.get('metric')
    if metric is not None:
        # Additive Pass-2 metric block.  Synthetic/offline packages can never authorize a real
        # solver; the single exception is the versioned, task-approved real_metric_v1 mode.
        if not isinstance(metric, dict):
            raise StudyError('package metric block must be an object')
        if metric.get('policy') != 'metric_composite_v1':
            raise StudyError('package metric block policy must be metric_composite_v1')
        mode = metric.get('provenance_mode')
        if mode is None:
            if metric.get('synthetic') is not True:
                raise StudyError('package metric block must declare synthetic provenance')
            if metric.get('real_solver_allowed') is not False:
                raise StudyError('metric packages may not authorize a real solver')
        elif mode == REAL_DATA_OFFLINE:
            if metric.get('synthetic') is not False or metric.get('no_backend_calls') is not True:
                raise StudyError('offline metric package requires real-data offline provenance')
            for key in ('training_artifact_sha256', 'training_manifest_sha256',
                        'proposal_sha256', 'model_sha256', 'source_provenance_sha256'):
                if not isinstance(metric.get(key), str) or not re.fullmatch(r'[0-9a-f]{64}', metric[key]):
                    raise StudyError(f'offline metric package requires valid {key}')
            if not isinstance(metric.get('source_provenance'), dict) or \
                    digest(metric['source_provenance']) != metric['source_provenance_sha256']:
                raise StudyError('offline metric source provenance hash mismatch')
            if not package.get('dependency_pins') or not package.get('code_pins'):
                raise StudyError('offline metric package requires code and dependency pins')
            if (package.get('proposal_policy') or {}).get('policy') != 'metric_composite_v1':
                raise StudyError('offline metric package requires metric proposal policy')
            if any(metric[k + '_sha256'] != package.get('artifacts', {}).get(k)
                   for k in ('proposal', 'model')):
                raise StudyError('offline metric package model/proposal bindings mismatch')
            if any(metric['training_' + suffix + '_sha256'] !=
                   package.get('artifacts', {}).get('metric_training' + extra)
                   for suffix, extra in (('artifact', ''), ('manifest', '_manifest'))):
                raise StudyError('offline metric package training bindings mismatch')
            if metric.get('real_solver_allowed') is not False:
                raise StudyError('metric packages may not authorize a real solver')
        elif mode == REAL_METRIC:
            _verify_real_metric_block(package, metric)
        else:
            raise StudyError('unsupported metric provenance mode')
        if not isinstance(metric.get('training_artifact_sha256'), str) or \
                not metric['training_artifact_sha256']:
            raise StudyError('package metric block needs the training artifact hash')
    return package


def _verify_real_metric_block(package, metric):
    """Structural real_metric_v1 rules; the approval record is re-read separately."""
    if metric.get('synthetic') is not False:
        raise StudyError('real metric package must declare non-synthetic provenance')
    if metric.get('real_solver_allowed') is not True:
        raise StudyError('real metric package must explicitly authorize the real solver')
    if metric.get('no_backend_calls') is True:
        raise StudyError('real metric package cannot claim zero backend calls')
    profile = package.get('budget_profile')
    if profile not in METRIC_REAL_PROFILES:
        raise StudyError('real metric package requires a metric budget profile')
    if package.get('lane') != 'gpu':
        raise StudyError('real metric package requires the gpu lane')
    deadline = package.get('deadline')
    if deadline is None:
        raise StudyError('real metric package requires a timezone-aware future deadline')
    if _deadline_moment(deadline) <= datetime.now(timezone.utc):
        raise StudyError('real metric package deadline must be in the future')

    approvals = metric.get('approvals')
    if not isinstance(approvals, dict):
        raise StudyError('real metric package requires an approvals block')
    _approval_record_path(approvals.get('record'))
    if not _is_hex(approvals.get('task_identity'), _HEX16):
        raise StudyError('metric approvals task_identity must be 16 lowercase hex')
    if not _is_hex(approvals.get('artifact_sha256'), _HEX64):
        raise StudyError('metric approvals artifact_sha256 must be a sha256')
    if approvals.get('refit_every') != METRIC_APPROVAL_REFIT_EVERY:
        raise StudyError(f'metric approvals refit_every must be {METRIC_APPROVAL_REFIT_EVERY}')
    caps = budget_caps(package)
    if approvals.get('screen_cap') != caps['screen_calls'] \
            or approvals.get('verify_cap') != caps['verify_calls']:
        raise StudyError('metric approvals caps must equal the package budget')

    for key in ('training_artifact_sha256', 'training_manifest_sha256', 'training_checksum',
                'proposal_sha256', 'model_sha256', 'source_provenance_sha256'):
        if not _is_hex(metric.get(key), _HEX64):
            raise StudyError(f'real metric package requires valid {key}')
    if not _is_hex(metric.get('task_identity'), _HEX16):
        raise StudyError('real metric package requires a 16-hex task_identity')
    if approvals['task_identity'] != metric['task_identity']:
        raise StudyError('metric approvals task_identity disagrees with the package')
    if approvals['artifact_sha256'] != metric['training_checksum']:
        raise StudyError('metric approvals artifact_sha256 disagrees with the training checksum')
    if not isinstance(metric.get('source_provenance'), dict) or \
            digest(metric['source_provenance']) != metric['source_provenance_sha256']:
        raise StudyError('real metric source provenance hash mismatch')
    if not package.get('code_pins') or not package.get('dependency_pins'):
        raise StudyError('real metric package requires code and dependency pins')
    if (package.get('proposal_policy') or {}).get('policy') != 'metric_composite_v1':
        raise StudyError('real metric package requires the metric proposal policy')
    artifacts = package.get('artifacts') or {}
    if _metric_pin_mismatch(metric, artifacts):
        raise StudyError('real metric package model/proposal/training bindings mismatch')


def _metric_pin_mismatch(metric, artifacts):
    pairs = (('training_artifact_sha256', 'metric_training'),
             ('training_manifest_sha256', 'metric_training_manifest'),
             ('proposal_sha256', 'proposal'),
             ('model_sha256', 'model'))
    return any(metric.get(key) != artifacts.get(kind) for key, kind in pairs)


def _validate_proposal_payload(raw):
    """A package may only bind a proposal that actually selected a candidate.

    Legacy fixtures predate the explicit ``status`` field and are accepted. New
    artifacts must be ``ok``, or an explicitly labelled non-BO fallback with a
    candidate; a capability/model/pool refusal must not be packaged as if it were
    a reviewable initial proposal.
    """
    try:
        payload = json.loads(raw.decode('utf-8'))
    except (UnicodeDecodeError, ValueError) as exc:
        raise Unavailable('current proposal artifact is not JSON') from exc
    if not isinstance(payload, dict):
        raise Unavailable('current proposal artifact must contain an object')
    status = payload.get('status')
    if status is None or status == 'ok':
        return
    if (status == 'model_unavailable' and payload.get('fallback') is True
            and isinstance(payload.get('candidate'), dict)):
        return
    reason = payload.get('reason')
    raise Unavailable(f'current proposal artifact is {status}'
                      + (f': {reason}' if reason else ''))


def _current_artifact(service, study_id, revision, kind):
    metadata = service.get_artifact_metadata(study_id, kind, revision=revision)
    status = metadata.get('status')
    if status == 'missing':
        raise Unavailable(f'current {kind} artifact is missing')
    if status != 'available':
        raise Unavailable(f'current {kind} artifact is {status}')
    sha = metadata.get('sha256')
    if not isinstance(sha, str) or not sha:
        raise Unavailable(f'current {kind} artifact has no hash')
    # Re-read the exact bytes so a corrupted file can never bind a package.
    raw = service.store.read_artifact(sha)
    if kind == 'proposal':
        _validate_proposal_payload(raw)
    return sha


def _pins(explicit, spec, key):
    if explicit is not None:
        if not isinstance(explicit, dict):
            raise StudyError(f'{key} must be an object')
        return explicit
    pins = spec.get('pins') if isinstance(spec, dict) else None
    if isinstance(pins, dict):
        nested = pins.get(key)
        if isinstance(nested, dict):
            return nested
        if key == 'code_pins' and all(isinstance(v, (str, int, float, bool)) for v in pins.values()):
            return pins
    return {}


def prepare_run_package(service, study_id, *, expected_revision=None, lane='cpu',
                        deadline=None, idempotency_key=None, code_pins=None,
                        dependency_pins=None, resolved_config=None, budget_profile='baseline',
                        metric=None):
    """Bind the current study revision and artifacts into an immutable package.

    ``expected_revision`` defaults to the current revision.  A concurrent manual
    edit raises ``Conflict`` at publication time.  ``idempotency_key`` follows
    the service rule: the same key and payload returns the original package;
    the same key with different inputs fails.

    ``metric`` is an optional, additive Pass-2 block (metric-composite training artifact hash +
    identity pins + synthetic flag).  When absent, the body and identity are exactly the historical
    scalar/turbo/pareto package; when present, the block is validated as synthetic-only and can
    never authorize a real solver run.
    """
    if lane not in ('cpu', 'gpu'):
        raise StudyError('lane must be cpu or gpu')
    if budget_profile not in BUDGET_PROFILES:
        raise StudyError(f'unknown budget_profile {budget_profile!r} (known: {sorted(BUDGET_PROFILES)})')
    deadline = _timezone_deadline(deadline)
    study = service.get_study(study_id)
    revision = study['revision'] if expected_revision is None else expected_revision
    if type(revision) is not int or revision < 1:
        raise StudyError('expected_revision must be a positive integer')
    if revision != study['revision']:
        raise Conflict('stale study revision')

    spec = study['spec']
    artifacts = {kind: _current_artifact(service, study_id, revision, kind)
                 for kind in REQUIRED_ARTIFACTS}
    dependencies = dict(artifacts)

    # Bind the execution stack even when a draft omitted explicit pins. Metadata
    # collection imports no Bayesian engine and performs no backend work.
    frozen_dependencies = _pins(dependency_pins, spec, 'dependency_pins')
    if not frozen_dependencies:
        from hornlab_search.search.evaluate import collect_lib_shas
        frozen_dependencies = {k: v for k, v in collect_lib_shas().items()
                               if k in ('hornlab_mesher', 'hornlab_beat_bem', 'hornlab_plots')}
    frozen_code = _pins(code_pins, spec, 'code_pins')
    if not frozen_code:
        repository = Path(__file__).resolve().parents[2]
        frozen_code = {name: hashlib.sha256((repository / name).read_bytes()).hexdigest()
                       for name in EXECUTION_CODE_FILES}

    body = {
        'schema': PACKAGE_SCHEMA,
        'protocol': PROTOCOL,
        'execution_mode': EXECUTION_MODE,
        'study_id': study_id,
        'spec_revision': revision,
        'spec_hash': study['spec_hash'],
        'deadline_required': True,
        'deadline': deadline,
        'budget': dict(BUDGET_PROFILES[budget_profile]),
        'lane': lane,
        'code_pins': frozen_code,
        'dependency_pins': frozen_dependencies,
        'resolved_config': ({} if resolved_config is None else resolved_config),
        'stop_rules': list(STOP_RULES),
        'recovery_rules': list(RECOVERY_RULES),
        'adaptive_policy': dict(ADAPTIVE_POLICY),
        'verification_policy': dict(VERIFICATION_POLICY),
        'proposal_policy': _proposal_identity(service, study_id, revision, spec),
        'artifacts': artifacts,
        'status_note': STATUS_NOTE,
    }
    proposal = json.loads(service.store.read_artifact(artifacts['proposal']).decode('utf-8'))
    candidate_policy = proposal.get('candidate_policy') if isinstance(proposal, dict) else None
    if candidate_policy is not None:
        snapshot = json.loads(service.store.read_artifact(artifacts['snapshot']).decode('utf-8'))
        pool_sha = _current_artifact(service, study_id, revision, 'pool')
        pool = json.loads(service.store.read_artifact(pool_sha).decode('utf-8'))
        from hornlab_search.config import load_config
        body['candidate_policy'] = candidate_policy
        verify_candidate_policy(body, load_config(snapshot['task']['config']), pool=pool)
    if budget_profile != 'baseline':     # baseline packages keep their exact historical body
        body['budget_profile'] = budget_profile
    if metric is not None:
        # Additive only: the metric block is part of the body/hash for metric packages and is
        # absent for every existing scalar/turbo/pareto package.
        if not isinstance(metric, dict):
            raise StudyError('metric block must be an object')
        body['metric'] = dict(metric)
        mode = metric.get('provenance_mode')
        if mode == REAL_DATA_OFFLINE:
            _verify_offline_metric_bindings(service, study_id, revision, body)
        if mode == REAL_METRIC:
            body['artifacts']['metric_training'] = metric.get('training_artifact_sha256')
            body['artifacts']['metric_training_manifest'] = metric.get('training_manifest_sha256')
        if mode in (REAL_DATA_OFFLINE, REAL_METRIC):
            dependencies.update({kind: body['artifacts'][kind] for kind in
                                 ('metric_training', 'metric_training_manifest')})
    if not isinstance(body['resolved_config'], dict):
        raise StudyError('resolved_config must be an object')

    # Identity is the content hash of the canonical body and also the artifact
    # address published by the store (``publish`` hashes these exact bytes).
    package_id = digest(body)
    package = {'package_id': package_id, **body}
    verify_package(package)

    key = idempotency_key or f'package:{revision}:{package_id}'
    artifact = service.attach_artifact(
        study_id, revision, PACKAGE_KIND, canonical(body).encode('utf-8'),
        dependencies, key)
    if artifact['sha256'] != package_id:
        raise Unavailable('published package hash disagrees with package_id')
    return package


def _verify_offline_metric_bindings(service, study_id, revision, body):
    """Re-read immutable study artifacts and pinned intake files; never invoke a backend."""
    from .metric_study import metric_bindings
    from .metric_intake import _pinned_file

    metric = body['metric']
    binding = metric_bindings(service, study_id)
    if binding.get('status') != 'ok':
        raise Unavailable('offline metric proposal binding invalid: ' + str(binding.get('detail')))
    manifest_sha = _current_artifact(service, study_id, revision, 'metric_training_manifest')
    training_sha = _current_artifact(service, study_id, revision, 'metric_training')
    if (metric.get('training_artifact_sha256') != training_sha or
            metric.get('training_manifest_sha256') != manifest_sha or
            binding.get('artifact_bytes_sha256') != training_sha or
            binding.get('manifest_sha256') != manifest_sha):
        raise Unavailable('offline metric training binding mismatch')
    try:
        manifest = json.loads(service.store.read_artifact(manifest_sha).decode('utf-8'))
        source = manifest['offline_intake']
        if manifest.get('synthetic') is not False or manifest.get('no_backend_calls') is not True:
            raise ValueError('manifest is not real-data offline intake')
        if (source != metric.get('source_provenance') or
                manifest.get('artifact_bytes_sha256') != training_sha or
                manifest.get('checksum') != binding.get('artifact_checksum')):
            raise ValueError('manifest provenance or training mismatch')
        if manifest.get('dependencies', {}).get('snapshot') != body['artifacts']['snapshot']:
            raise ValueError('manifest snapshot dependency mismatch')
        for key in ('config', 'brief', 'catalog', 'replay'):
            _pinned_file(source[key], key)
        shards = source['shards']
        if not isinstance(shards, dict) or not shards:
            raise ValueError('source shards required')
        for key, item in shards.items():
            _pinned_file(item, f'shard {key}')
    except (KeyError, ValueError, TypeError, UnicodeError) as exc:
        raise Unavailable(f'offline metric provenance invalid: {exc}') from exc
    body['artifacts']['metric_training'] = training_sha
    body['artifacts']['metric_training_manifest'] = manifest_sha


def prepare_real_data_offline_metric_package(service, study_id, **kwargs):
    """Package an existing validated offline intake for rehearsal, never real execution."""
    from .metric_study import metric_bindings

    binding = metric_bindings(service, study_id)
    if binding.get('status') != 'ok':
        raise Unavailable('offline metric proposal binding invalid: ' + str(binding.get('detail')))
    revision = service.get_study(study_id)['revision']
    manifest_sha = _current_artifact(service, study_id, revision, 'metric_training_manifest')
    try:
        manifest = json.loads(service.store.read_artifact(manifest_sha).decode('utf-8'))
        source = manifest['offline_intake']
    except (KeyError, ValueError, UnicodeError) as exc:
        raise Unavailable('offline intake provenance unavailable') from exc
    metric = {
        'policy': 'metric_composite_v1', 'provenance_mode': REAL_DATA_OFFLINE,
        'synthetic': False, 'real_solver_allowed': False, 'no_backend_calls': True,
        'training_artifact_sha256': binding['artifact_bytes_sha256'],
        'training_manifest_sha256': manifest_sha,
        'proposal_sha256': _current_artifact(service, study_id, revision, 'proposal'),
        'model_sha256': _current_artifact(service, study_id, revision, 'model'),
        'source_provenance': source, 'source_provenance_sha256': digest(source),
    }
    return prepare_run_package(service, study_id, metric=metric, **kwargs)


def _real_resolved_config(service, study_id, revision, *, lane, budget_profile, deadline,
                          approvals_record, overrides=None):
    """Pin the exact preparation/worker context that the package authorizes."""
    study = service.get_study(study_id)
    snapshot = json.loads(service.store.read_artifact(
        _current_artifact(service, study_id, revision, 'snapshot')).decode('utf-8'))
    task = snapshot.get('task') or {}
    source = (study.get('spec') or {}).get('source') or {}
    pythonpath = [entry for entry in os.environ.get('PYTHONPATH', '').split(os.pathsep) if entry]
    base = {
        'schema': 'metric-real-resolved-config-v1',
        'study_id': study_id,
        'spec_revision': revision,
        'spec_hash': study['spec_hash'],
        'interpreter': {
            'executable': str(Path(sys.executable).resolve()),
            'version': sys.version.split()[0],
            'implementation': sys.implementation.name,
            'prefix': str(Path(sys.prefix).resolve()),
            'pythonpath': pythonpath,
        },
        'config': {'path': task.get('config'), 'sha256': task.get('config_sha256')},
        'brief': {'path': task.get('brief'), 'sha256': task.get('brief_sha256')},
        'objective_version': task.get('objective_version'),
        'backend': 'beat_cuda',
        'fidelity': 'screen',
        'lane': lane,
        'budget_profile': budget_profile,
        'deadline': deadline,
        'dataset_root': source.get('dataset_root'),
        'approvals_record': approvals_record,
    }
    if overrides is not None:
        if not isinstance(overrides, dict):
            raise StudyError('resolved_config overrides must be an object')
        for key, value in overrides.items():
            if key == 'interpreter' and isinstance(value, dict) \
                    and isinstance(base.get('interpreter'), dict):
                base['interpreter'] = {**base['interpreter'], **value}
            else:
                base[key] = value
    return base


def _verify_real_metric_bindings(service, study_id, revision, approvals, caps):
    """Re-read the metric artifact/manifest and every pinned intake file."""
    from .metric_study import metric_bindings
    from .metric_intake import _pinned_file

    binding = metric_bindings(service, study_id)
    if binding.get('status') != 'ok':
        raise Unavailable('real metric proposal binding invalid: ' + str(binding.get('detail')))
    if binding.get('synthetic') is not False:
        raise Unavailable('real metric execution requires a measured (non-synthetic) artifact')
    training_sha = _current_artifact(service, study_id, revision, 'metric_training')
    manifest_sha = _current_artifact(service, study_id, revision, 'metric_training_manifest')
    proposal_sha = _current_artifact(service, study_id, revision, 'proposal')
    model_sha = _current_artifact(service, study_id, revision, 'model')
    if (binding.get('artifact_bytes_sha256') != training_sha
            or binding.get('manifest_sha256') != manifest_sha):
        raise Unavailable('real metric training binding mismatch')
    try:
        manifest = json.loads(service.store.read_artifact(manifest_sha).decode('utf-8'))
        source = manifest['offline_intake']
        if manifest.get('synthetic') is not False or manifest.get('no_backend_calls') is not True:
            raise ValueError('manifest is not measured offline intake')
        if manifest.get('artifact_bytes_sha256') != training_sha:
            raise ValueError('manifest training bytes mismatch')
    except (KeyError, ValueError, TypeError, UnicodeError) as exc:
        raise Unavailable(f'real metric provenance invalid: {exc}') from exc
    task = manifest.get('task') or {}
    score = (manifest.get('score') or {}).get('payload') or {}
    identity = {field: task.get(field) for field in _APPROVAL_IDENTITY_FIELDS}
    identity['brief_hash'] = score.get('brief_hash')
    identity['score_hash'] = score.get('score_hash')
    _check_approval_bindings(approvals['payload'], task_identity=identity['task_identity'],
                             artifact_sha256=manifest.get('checksum'), caps=caps)
    approved_identity = approvals['payload']['identity']
    for field in _APPROVAL_IDENTITY_FIELDS:
        if approved_identity[field] != identity[field]:
            raise Unavailable(f'metric approvals identity {field!r} differs from the artifact')
    for field in ('brief_hash', 'score_hash'):
        if approved_identity.get(field) not in (None, identity[field]):
            raise Unavailable(f'metric approvals identity {field!r} differs from the artifact')
    if manifest.get('dependencies', {}).get('snapshot') != \
            service.get_artifact_metadata(study_id, 'snapshot', revision=revision).get('sha256'):
        raise Unavailable('real metric manifest snapshot dependency mismatch')
    try:
        for key in ('config', 'brief', 'catalog', 'replay'):
            _pinned_file(source[key], key)
        shards = source['shards']
        if not isinstance(shards, dict) or not shards:
            raise ValueError('source shards required')
        for key, item in shards.items():
            _pinned_file(item, f'shard {key}')
    except (KeyError, ValueError, TypeError) as exc:
        raise Unavailable(f'real metric pinned file invalid: {exc}') from exc
    return {
        'training_artifact_sha256': training_sha,
        'training_manifest_sha256': manifest_sha,
        'training_checksum': binding.get('artifact_checksum') or manifest.get('checksum'),
        'proposal_sha256': proposal_sha,
        'model_sha256': model_sha,
        'source_provenance': source,
        'source_provenance_sha256': digest(source),
        'task_identity': identity['task_identity'],
        'identity': identity,
        'objective_version': binding.get('objective_version') or manifest.get('objective_version'),
    }


def prepare_real_metric_package(service, study_id, *, approvals_record, budget_profile,
                                lane='gpu', deadline=None, expected_revision=None,
                                idempotency_key=None, code_pins=None, dependency_pins=None,
                                resolved_config=None, approvals_root=None):
    """Prepare the opt-in, task-approved real metric package (no backend call is made).

    The package stays non-executable until the approval record is in
    ``APPROVED_FOR_CANARY`` *and* the parent sets the CLI release gate.  Publication is the
    ordinary immutable, content-addressed ``attach_artifact`` path.
    """
    if lane != 'gpu':
        raise StudyError('a real metric package requires the gpu lane')
    if budget_profile not in METRIC_REAL_PROFILES:
        raise StudyError('a real metric package requires a metric budget profile '
                         f'(known: {METRIC_REAL_PROFILES})')
    deadline = _timezone_deadline(deadline)
    if deadline is None:
        raise StudyError('a real metric package requires an explicit deadline')
    if _deadline_moment(deadline) <= datetime.now(timezone.utc):
        raise StudyError('a real metric package deadline must be in the future')

    approvals = load_metric_approvals(approvals_record, root=approvals_root)
    profile, caps = _approval_caps(approvals['payload'])
    if profile != budget_profile:
        raise StudyError('metric approvals profile must equal the selected budget profile')

    study = service.get_study(study_id)
    revision = study['revision'] if expected_revision is None else expected_revision
    if type(revision) is not int or revision < 1:
        raise StudyError('expected_revision must be a positive integer')
    if revision != study['revision']:
        raise Conflict('stale study revision')

    frozen_dependencies = dependency_pins
    if frozen_dependencies is None:
        from hornlab_search.search.evaluate import collect_lib_shas
        frozen_dependencies = {key: value for key, value in collect_lib_shas().items()
                               if key != 'hornlab_search'}
    if not isinstance(frozen_dependencies, dict) or not frozen_dependencies:
        raise StudyError('a real metric package requires dependency pins')
    for key, value in frozen_dependencies.items():
        # HornLab dependency pins are git commit IDs from ``direct_url.json`` (40 hex); a
        # shadowing/externally pinned dependency may legitimately be a 64-hex sha256.  Anything
        # else (notably the literal ``unknown``) is not a pin.
        if not (_is_hex(value, _HEX40) or _is_hex(value, _HEX64)):
            raise StudyError(f'dependency pin {key!r} is not a 40-hex git SHA or 64-hex sha256')

    frozen = _verify_real_metric_bindings(service, study_id, revision, approvals, caps)
    resolved = _real_resolved_config(
        service, study_id, revision, lane=lane, budget_profile=budget_profile,
        deadline=deadline, approvals_record=approvals['record'], overrides=resolved_config)
    metric = {
        'policy': 'metric_composite_v1',
        'provenance_mode': REAL_METRIC,
        'synthetic': False,
        'real_solver_allowed': True,
        'no_backend_calls': False,
        'approvals': {
            'record': approvals['record'],
            'task_identity': approvals['payload']['task_identity'],
            'artifact_sha256': approvals['payload']['artifact_sha256'],
            'screen_cap': caps['screen_calls'],
            'verify_cap': caps['verify_calls'],
            'refit_every': METRIC_APPROVAL_REFIT_EVERY,
        },
        'training_artifact_sha256': frozen['training_artifact_sha256'],
        'training_manifest_sha256': frozen['training_manifest_sha256'],
        'training_checksum': frozen['training_checksum'],
        'proposal_sha256': frozen['proposal_sha256'],
        'model_sha256': frozen['model_sha256'],
        'source_provenance': frozen['source_provenance'],
        'source_provenance_sha256': frozen['source_provenance_sha256'],
        'task_identity': frozen['task_identity'],
        'identity': frozen['identity'],
        'objective_version': frozen['objective_version'],
    }
    package = prepare_run_package(
        service, study_id, expected_revision=revision, lane=lane, deadline=deadline,
        idempotency_key=idempotency_key, code_pins=code_pins,
        dependency_pins=frozen_dependencies, resolved_config=resolved,
        budget_profile=budget_profile, metric=metric)
    verify_real_metric_package_files(package, root=approvals_root or repo_root())
    return package


def verify_real_metric_package_files(package, *, root=None):
    """Re-read and re-hash the approval record and every pinned intake file.

    Pure filesystem/JSON work: no study-registry write, no mesh/BEM/GPU/queue call.  The
    return value reports the record's *current* status so callers can refuse execution for a
    held record while still allowing prepare/dry-run rehearsal.
    """
    verify_package(package)
    metric = package.get('metric') or {}
    if metric.get('provenance_mode') != REAL_METRIC:
        raise StudyError('not a real metric package')
    approvals = load_metric_approvals(
        (metric.get('approvals') or {}).get('record'), root=root)
    payload = approvals['payload']
    caps = budget_caps(package)
    _check_approval_bindings(payload, task_identity=metric.get('task_identity'),
                             artifact_sha256=metric.get('training_checksum'), caps=caps)
    if payload.get('profile') != package.get('budget_profile'):
        raise StudyError('metric approvals profile differs from the package budget profile')
    source = metric.get('source_provenance')
    if not isinstance(source, dict) or digest(source) != metric.get('source_provenance_sha256'):
        raise StudyError('real metric source provenance hash mismatch')
    from .metric_intake import _pinned_file
    try:
        for key in ('config', 'brief', 'catalog', 'replay'):
            _pinned_file(source[key], key)
        shards = source['shards']
        if not isinstance(shards, dict) or not shards:
            raise ValueError('source shards required')
        for key, item in shards.items():
            _pinned_file(item, f'shard {key}')
    except (KeyError, ValueError, TypeError) as exc:
        raise Unavailable(f'real metric pinned file invalid: {exc}') from exc
    return {
        'status': 'ok',
        'approvals': {
            'record': approvals['record'],
            'status': payload.get('status'),
            'profile': payload.get('profile'),
            'task_identity': payload['task_identity'],
            'artifact_sha256': payload['artifact_sha256'],
            'payload_sha256': digest(payload),
        },
        'pinned_files': 4 + len(source.get('shards') or {}),
    }


__all__ = [
    'PACKAGE_SCHEMA',
    'PACKAGE_KIND',
    'EXECUTION_MODE',
    'BUDGET_PROFILES',
    'EXECUTION_BUDGET',
    'budget_caps',
    'STATUS_NOTE',
    'STOP_RULES',
    'RECOVERY_RULES',
    'ADAPTIVE_POLICY',
    'VERIFICATION_POLICY',
    'package_hash',
    'verify_package',
    'prepare_run_package',
    'prepare_real_data_offline_metric_package',
    'prepare_real_metric_package',
    'verify_real_metric_package_files',
    'load_metric_approvals',
    'repo_root',
    'REAL_DATA_OFFLINE',
    'REAL_METRIC',
    'METRIC_APPROVALS_SCHEMA',
    'METRIC_REAL_PROFILES',
    'METRIC_APPROVAL_STATUSES',
    'METRIC_EXECUTABLE_APPROVAL_STATUSES',
]
