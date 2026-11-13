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

from datetime import datetime

from .schema import PROTOCOL, Conflict, StudyError, Unavailable, canonical, digest

PACKAGE_SCHEMA = 'run-package-v1'
PACKAGE_KIND = 'package'
EXECUTION_MODE = 'adaptive_serial'

#: Frozen baseline budget from protocol bo-study-v1.1 section 4.  A prepared
#: package must carry exactly these caps; callers cannot widen or shrink them.
EXECUTION_BUDGET = {
    'screen_calls': 18,
    'verify_calls': 6,
    'total_calls': 24,
    'attempts': 120,
}

REQUIRED_ARTIFACTS = ('snapshot', 'model', 'proposal')
STATUS_NOTE = 'cheap-check-passed; mesh/acoustic eligibility unknown'

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


def package_hash(package):
    """Return the SHA-256 identity over the canonical package body.

    ``package_id`` itself is excluded so the identifier is not circular.
    """
    if not isinstance(package, dict):
        raise StudyError('package must be an object')
    body = {key: value for key, value in package.items() if key != 'package_id'}
    return digest(body)


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
    if package.get('budget') != EXECUTION_BUDGET:
        raise StudyError('package budget must exactly match the frozen execution budget')
    if package.get('status_note') != STATUS_NOTE:
        raise StudyError('package status_note must state cheap-check-only eligibility')
    return package


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
    service.store.read_artifact(sha)
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
                        dependency_pins=None, resolved_config=None):
    """Bind the current study revision and artifacts into an immutable package.

    ``expected_revision`` defaults to the current revision.  A concurrent manual
    edit raises ``Conflict`` at publication time.  ``idempotency_key`` follows
    the service rule: the same key and payload returns the original package;
    the same key with different inputs fails.
    """
    if lane not in ('cpu', 'gpu'):
        raise StudyError('lane must be cpu or gpu')
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

    body = {
        'schema': PACKAGE_SCHEMA,
        'protocol': PROTOCOL,
        'execution_mode': EXECUTION_MODE,
        'study_id': study_id,
        'spec_revision': revision,
        'spec_hash': study['spec_hash'],
        'deadline_required': True,
        'deadline': deadline,
        'budget': dict(EXECUTION_BUDGET),
        'lane': lane,
        'code_pins': _pins(code_pins, spec, 'code_pins'),
        'dependency_pins': _pins(dependency_pins, spec, 'dependency_pins'),
        'resolved_config': ({} if resolved_config is None else resolved_config),
        'stop_rules': list(STOP_RULES),
        'recovery_rules': list(RECOVERY_RULES),
        'adaptive_policy': dict(ADAPTIVE_POLICY),
        'verification_policy': dict(VERIFICATION_POLICY),
        'artifacts': artifacts,
        'status_note': STATUS_NOTE,
    }
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


__all__ = [
    'PACKAGE_SCHEMA',
    'PACKAGE_KIND',
    'EXECUTION_MODE',
    'EXECUTION_BUDGET',
    'STATUS_NOTE',
    'STOP_RULES',
    'RECOVERY_RULES',
    'ADAPTIVE_POLICY',
    'VERIFICATION_POLICY',
    'package_hash',
    'verify_package',
    'prepare_run_package',
]
