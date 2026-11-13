"""Transactional, offline study registry service; no dispatch or solver calls."""
from __future__ import annotations

import hashlib
import json
import math
from contextlib import closing
from datetime import datetime, timezone
from uuid import uuid4

from .schema import Conflict, DECISIONS, NotFound, StudyError, Unavailable, canonical, digest, validate_spec
from .store import StudyStore

# Conservative artifact prerequisites. Presence/hash validity is evidence of
# storage only; semantic/schema validation and the M2 gate remain independent.
ARTIFACT_DEPS = {
    'snapshot': (), 'cohort': ('snapshot',), 'analysis': ('snapshot', 'cohort'),
    'training': ('snapshot', 'cohort'), 'model': ('training',), 'pool': ('snapshot',),
    'proposal': ('model', 'training', 'pool'), 'package': ('snapshot', 'model', 'proposal'),
    'results': ('package',), 'verification': ('results',), 'decision': ('verification',),
}

class StudyService:
    def __init__(self, root):
        self.store = StudyStore(root)

    def _mutate(self, scope, key, payload, action):
        if not isinstance(key, str) or not key.strip():
            raise StudyError('idempotency key required')
        payload_hash = digest(payload)
        conn = self.store.connect()
        try:
            conn.execute('BEGIN IMMEDIATE')
            prior = conn.execute('SELECT payload_hash,response_json FROM idempotency WHERE scope=? AND key=?', (scope, key)).fetchone()
            if prior:
                if prior['payload_hash'] != payload_hash:
                    raise Conflict('idempotency key reused with different payload')
                conn.commit()
                return json.loads(prior['response_json']), False
            result = action(conn)
            conn.execute('INSERT INTO idempotency VALUES (?,?,?,?)', (scope, key, payload_hash, canonical(result)))
            conn.commit()
            return result, True
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def _study(conn, study_id):
        row = conn.execute('SELECT * FROM studies WHERE id=?', (study_id,)).fetchone()
        if row is None:
            raise NotFound('study not found')
        return row

    @classmethod
    def _revision(cls, conn, study_id, expected):
        study = cls._study(conn, study_id)
        if study['spec_revision'] != expected:
            raise Conflict('stale study revision')
        return study

    @staticmethod
    def _event(conn, study_id, kind, payload):
        conn.execute('UPDATE studies SET event_seq=event_seq+1 WHERE id=?', (study_id,))
        seq = conn.execute('SELECT event_seq FROM studies WHERE id=?', (study_id,)).fetchone()[0]
        conn.execute('INSERT INTO events VALUES (?,?,?,?)', (study_id, seq, kind, canonical(payload)))
        return seq

    def create_study(self, spec, key, parent_id=None):
        spec = validate_spec(spec)
        payload = {'spec': spec, 'parent_id': parent_id}
        def action(conn):
            if parent_id is not None:
                self._study(conn, parent_id)
            sid = uuid4().hex
            conn.execute('INSERT INTO studies(id,parent_id,spec_revision) VALUES (?,?,1)', (sid, parent_id))
            conn.execute('INSERT INTO revisions VALUES (?,?,?,?)', (sid, 1, canonical(spec), digest(spec)))
            self._event(conn, sid, 'created', {'parent_id': parent_id})
            return {'id': sid, 'revision': 1, 'parent_id': parent_id}
        return self._mutate('create', key, payload, action)[0]

    def get_study(self, study_id):
        conn = self.store.connect()
        try:
            conn.execute('BEGIN')
            row = self._study(conn, study_id)
            spec = conn.execute('SELECT spec_json,spec_hash FROM revisions WHERE study_id=? AND revision=?',
                                (study_id, row['spec_revision'])).fetchone()
            result = {'id': study_id, 'parent_id': row['parent_id'], 'revision': row['spec_revision'],
                      'event_seq': row['event_seq'], 'spec': json.loads(spec['spec_json']),
                      'spec_hash': spec['spec_hash']}
            conn.commit()
            return result
        finally:
            conn.close()

    def list_studies(self, limit=100):
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise StudyError('limit must be in 1..1000')
        with closing(self.store.connect()) as conn:
            rows = conn.execute('SELECT s.id,s.parent_id,s.spec_revision AS revision,s.event_seq,r.spec_hash,r.spec_json '
                                'FROM studies s JOIN revisions r ON r.study_id=s.id AND r.revision=s.spec_revision '
                                'ORDER BY s.rowid DESC LIMIT ?', (limit,)).fetchall()
            result = []
            for row in rows:
                item = dict(row)
                spec = json.loads(item.pop('spec_json'))
                item['name'] = spec.get('name') if isinstance(spec.get('name'), str) else None
                item['question'] = spec.get('question') if isinstance(spec.get('question'), str) else None
                result.append(item)
            return result

    def get_artifact_metadata(self, study_id, kind, revision=None):
        if not isinstance(kind, str) or not kind:
            raise StudyError('artifact kind required')
        with closing(self.store.connect()) as conn:
            conn.execute('BEGIN')
            study = self._study(conn, study_id)
            rev = study['spec_revision'] if revision is None else revision
            row = conn.execute('SELECT * FROM artifacts WHERE study_id=? AND revision=? AND kind=?',
                               (study_id, rev, kind)).fetchone()
            if row is None:
                conn.commit()
                return {'study_id': study_id, 'revision': rev, 'kind': kind, 'status': 'missing'}
            result = {'study_id': study_id, 'revision': rev, 'kind': kind, 'sha256': row['sha256'],
                      'dependencies': json.loads(row['dependencies_json']),
                      'status': 'stale' if rev != study['spec_revision'] else 'available',
                      'dependency_status': 'unverified'}
            try:
                self.store.read_artifact(row['sha256'])
            except Unavailable as exc:
                result['status'] = 'unavailable'
                result['reason'] = str(exc)
            conn.commit()
            return result

    def revise(self, study_id, spec, expected_revision, key):
        spec = validate_spec(spec)
        payload = {'spec': spec, 'expected_revision': expected_revision}
        def action(conn):
            self._revision(conn, study_id, expected_revision)
            revision = expected_revision + 1
            conn.execute('INSERT INTO revisions VALUES (?,?,?,?)', (study_id, revision, canonical(spec), digest(spec)))
            conn.execute('UPDATE studies SET spec_revision=? WHERE id=?', (revision, study_id))
            seq = self._event(conn, study_id, 'revised', {'revision': revision})
            return {'id': study_id, 'revision': revision, 'event_seq': seq}
        return self._mutate(f'{study_id}:revise', key, payload, action)[0]

    def append_event(self, study_id, kind, payload, key):
        if not isinstance(kind, str) or not kind or not isinstance(payload, dict):
            raise StudyError('event kind and object payload required')
        def action(conn):
            self._study(conn, study_id)
            seq = self._event(conn, study_id, kind, payload)
            return {'study_id': study_id, 'event_seq': seq}
        return self._mutate(f'{study_id}:event', key, {'kind': kind, 'payload': payload}, action)[0]

    def attach_artifact(self, study_id, revision, kind, content, dependencies, key):
        if not isinstance(kind, str) or not kind or not isinstance(content, bytes) or not isinstance(dependencies, dict):
            raise StudyError('artifact kind, bytes and dependency mapping required')
        sha = hashlib.sha256(content).hexdigest()
        payload = {'revision': revision, 'kind': kind, 'sha256': sha, 'dependencies': dependencies}
        # Publication precedes the DB transaction; a crash here produces a reported orphan.
        published = self.store.publish(content)
        def action(conn):
            self._revision(conn, study_id, revision)
            self.store.read_artifact(published)
            existing = conn.execute('SELECT 1 FROM artifacts WHERE study_id=? AND revision=? AND kind=?', (study_id, revision, kind)).fetchone()
            if existing:
                raise Conflict('artifact kind already bound for this revision')
            conn.execute('INSERT INTO artifacts VALUES (?,?,?,?,?)', (study_id, revision, kind, published, canonical(dependencies)))
            seq = self._event(conn, study_id, 'artifact_attached', {'kind': kind, 'sha256': published})
            return {'study_id': study_id, 'revision': revision, 'kind': kind, 'sha256': published, 'event_seq': seq}
        return self._mutate(f'{study_id}:artifact', key, payload, action)[0]

    def decide(self, study_id, revision, outcome, rationale, key):
        if outcome not in DECISIONS or not isinstance(rationale, str) or not rationale.strip():
            raise StudyError('decision requires accept/reject/inconclusive and rationale')
        payload = {'revision': revision, 'outcome': outcome, 'rationale': rationale}
        def action(conn):
            self._revision(conn, study_id, revision)
            seq = self._event(conn, study_id, 'decision', payload)
            conn.execute('INSERT INTO decisions VALUES (?,?,?,?,?)', (study_id, seq, revision, outcome, rationale))
            return {'study_id': study_id, 'event_seq': seq, **payload}
        return self._mutate(f'{study_id}:decision', key, payload, action)[0]

    def readiness(self, study_id):
        """Derive storage readiness for each stage, never execution authorization.

        Each artifact must declare exact hashes for its named prerequisites.
        Completeness means only all dependencies/hash bytes are present; semantic
        validation remains pending and is not represented as a completed stage.
        """
        study = self.get_study(study_id)
        rev = study['revision']
        with closing(self.store.connect()) as conn:
            rows = conn.execute('SELECT * FROM artifacts WHERE study_id=? AND revision=?', (study_id, rev)).fetchall()
        artifacts = {row['kind']: row for row in rows}
        stages = {}
        integrity_ready = set()
        for kind, required in ARTIFACT_DEPS.items():
            row = artifacts.get(kind)
            if row is None:
                stages[kind] = {'status': 'not_started', 'missing': [kind], 'semantic_validation': 'unverified'}
                continue
            try:
                self.store.read_artifact(row['sha256'])
            except Unavailable as exc:
                stages[kind] = {'status': 'failed', 'reason': str(exc), 'semantic_validation': 'unverified'}
                continue
            declared = json.loads(row['dependencies_json'])
            missing = [dep for dep in required if dep not in artifacts]
            mismatch = [dep for dep in required if dep in artifacts and declared.get(dep) != artifacts[dep]['sha256']]
            broken = [dep for dep in required if dep not in integrity_ready]
            if missing or mismatch or broken:
                stages[kind] = {'status': 'stale', 'missing': missing, 'mismatched_dependencies': mismatch,
                                'unready_dependencies': broken, 'semantic_validation': 'unverified'}
            else:
                integrity_ready.add(kind)
                stages[kind] = {'status': 'unknown', 'sha256': row['sha256'],
                                'integrity': 'verified', 'semantic_validation': 'unverified'}
        spec = study['spec']
        missing_spec = [k for k in ('task', 'cohort', 'policy', 'pins') if not spec.get(k)]
        return {'status': 'partial', 'revision': rev, 'stages': stages,
                'missing_spec_sections': missing_spec,
                'reason': 'artifact integrity does not validate schemas, policies, M2 gate or dispatch authorization',
                'dispatch_authorized': False}

    def prepare_run_package(self, study_id, **kwargs):
        """Bind the current revision/artifacts into an immutable run package."""
        from .package import prepare_run_package
        return prepare_run_package(self, study_id, **kwargs)

    def export_study(self, study_id):
        """Return a durable, artifact-reference-only study record for export.

        Response arrays and artifact bytes stay in their own stores; this record
        contains identities, revisions, hashes, events, decisions and lineage.
        """
        with closing(self.store.connect()) as conn:
            conn.execute('BEGIN')
            study = self._study(conn, study_id)
            revisions = [dict(r) for r in conn.execute(
                'SELECT revision,spec_hash FROM revisions WHERE study_id=? ORDER BY revision',
                (study_id,))]
            artifacts = [dict(r) for r in conn.execute(
                'SELECT revision,kind,sha256,dependencies_json FROM artifacts '
                'WHERE study_id=? ORDER BY revision,kind', (study_id,))]
            decisions = [dict(r) for r in conn.execute(
                'SELECT seq,revision,outcome,rationale FROM decisions '
                'WHERE study_id=? ORDER BY seq', (study_id,))]
            events = [dict(r) for r in conn.execute(
                'SELECT seq,kind,payload_json FROM events WHERE study_id=? ORDER BY seq',
                (study_id,))]
            children = [r[0] for r in conn.execute(
                'SELECT id FROM studies WHERE parent_id=? ORDER BY rowid', (study_id,))]
            current = conn.execute('SELECT spec_json FROM revisions WHERE study_id=? AND revision=?',
                                   (study_id, study['spec_revision'])).fetchone()
            conn.commit()
        for item in artifacts:
            item['dependencies'] = json.loads(item.pop('dependencies_json'))
        for item in events:
            item['payload'] = json.loads(item.pop('payload_json'))
        return {
            'protocol': json.loads(current['spec_json']).get('protocol'),
            'study': {'id': study_id, 'parent_id': study['parent_id'],
                      'revision': study['spec_revision'], 'event_seq': study['event_seq'],
                      'spec': json.loads(current['spec_json'])},
            'parent_id': study['parent_id'],
            'children': children,
            'revisions': revisions,
            'artifacts': artifacts,
            'decisions': decisions,
            'events': events,
            'artifact_directory': str(self.store.artifacts),
            'recovery_diagnostics': self.store.recovery_diagnostics(),
        }

    @staticmethod
    def _job(row):
        if row is None:
            raise NotFound('job not found')
        result = dict(row)
        result['fields'] = json.loads(result.pop('fields_json'))
        return result

    def reserve_cpu_job(self, study_id, expected_revision, idempotency_key, request_hash, kind, package_hash=None):
        if kind not in {'analyze', 'propose'} or not isinstance(request_hash, str) or not request_hash:
            raise StudyError('CPU job requires analyze/propose kind and request hash')
        payload = {'expected_revision': expected_revision, 'request_hash': request_hash, 'kind': kind, 'package_hash': package_hash}
        def action(conn):
            self._revision(conn, study_id, expected_revision)
            if package_hash is not None:
                package = conn.execute('SELECT sha256 FROM artifacts WHERE study_id=? AND revision=? AND kind=?',
                                       (study_id, expected_revision, 'package')).fetchone()
                if package is None or package['sha256'] != package_hash:
                    raise Unavailable('current package artifact is missing or mismatched')
                self.store.read_artifact(package_hash)
            job_id = uuid4().hex
            conn.execute('INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?)', (job_id, study_id, expected_revision, kind, request_hash, package_hash, 'queued', '{}'))
            self._event(conn, study_id, 'cpu_job_reserved', {'job_id': job_id})
            return self._job(conn.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone())
        return self._mutate(f'{study_id}:cpu_job', idempotency_key, payload, action)

    def get_cpu_job(self, study_id, job_id):
        with closing(self.store.connect()) as conn:
            return self._job(conn.execute('SELECT * FROM jobs WHERE study_id=? AND id=?', (study_id, job_id)).fetchone())

    def list_cpu_jobs(self, study_id, limit=100):
        if not isinstance(limit, int) or not 1 <= limit <= 1000:
            raise StudyError('limit must be in 1..1000')
        with closing(self.store.connect()) as conn:
            self._study(conn, study_id)
            return [self._job(r) for r in conn.execute('SELECT * FROM jobs WHERE study_id=? ORDER BY rowid DESC LIMIT ?', (study_id, limit))]

    def compare_and_set_cpu_job(self, study_id, job_id, expected_states, new_state, fields, idempotency_key):
        transitions = {'queued': {'running', 'interrupted', 'unknown'},
                       'running': {'running', 'complete', 'failed', 'interrupted', 'unknown'},
                       'unknown': {'complete', 'failed', 'interrupted'}}
        if not isinstance(fields, dict) or set(fields) - {'process_identity', 'artifact_identity', 'error'}:
            raise StudyError('invalid CPU job fields')
        expected_states = sorted(set(expected_states))
        if not expected_states or any(new_state not in transitions.get(state, set()) for state in expected_states):
            raise StudyError('invalid CPU job transition')
        payload = {'job_id': job_id, 'expected_states': expected_states, 'new_state': new_state, 'fields': fields}
        def action(conn):
            job = self._job(conn.execute('SELECT * FROM jobs WHERE study_id=? AND id=?', (study_id, job_id)).fetchone())
            if job['status'] not in expected_states:
                raise Conflict('job status changed')
            if job['status'] == 'queued' and new_state == 'running':
                self._revision(conn, study_id, job['revision'])
                if job['package_hash'] is not None:
                    package = conn.execute('SELECT sha256 FROM artifacts WHERE study_id=? AND revision=? AND kind=?',
                                           (study_id, job['revision'], 'package')).fetchone()
                    if package is None or package['sha256'] != job['package_hash']:
                        raise Unavailable('current package artifact is missing or mismatched')
                    self.store.read_artifact(job['package_hash'])
            merged = dict(job['fields'])
            merged.update(fields)
            conn.execute('UPDATE jobs SET status=?,fields_json=? WHERE id=?', (new_state, canonical(merged), job_id))
            self._event(conn, study_id, 'cpu_job_state', {'job_id': job_id, 'status': new_state})
            return self._job(conn.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone())
        return self._mutate(f'{study_id}:job:{job_id}', idempotency_key, payload, action)[0]


class DraftAttemptJournal:
    """Durable attempt mechanics for testing; not an execution authorization adapter.

    Deliberately has no ``durable_contract`` marker: package schema, execution
    authorization and dependency readiness remain unfrozen and must be gated by
    the parent before connecting this to an evaluator.
    """
    def __init__(self, service):
        self.service = service
        self.store = service.store

    @staticmethod
    def _validate_package(package):
        if not isinstance(package, dict) or package.get('execution_mode') != 'adaptive_serial' or package.get('lane') not in ('cpu', 'gpu'):
            raise StudyError('invalid adaptive serial package')
        if any(not package.get(k) for k in ('study_id', 'package_id', 'spec_revision', 'deadline')):
            raise StudyError('package identity, revision and deadline required')
        try:
            deadline = datetime.fromisoformat(package['deadline'].replace('Z', '+00:00'))
            if deadline.tzinfo is None:
                raise ValueError('timezone required')
        except (AttributeError, ValueError) as exc:
            raise StudyError('timezone-aware deadline required') from exc
        budget = package.get('budget')
        if not isinstance(budget, dict):
            raise StudyError('budget required')
        for name, maximum in (('screen_calls', 18), ('verify_calls', 6), ('total_calls', 24), ('attempts', 120)):
            if type(budget.get(name)) is not int or not 0 <= budget[name] <= maximum:
                raise StudyError(f'invalid {name} budget')
        return deadline

    def _package(self, conn, package):
        self._validate_package(package)
        self.service._revision(conn, package['study_id'], package['spec_revision'])
        ref = conn.execute('SELECT sha256 FROM artifacts WHERE study_id=? AND revision=? AND kind=?',
                           (package['study_id'], package['spec_revision'], 'package')).fetchone()
        if ref is None:
            raise Unavailable('registered immutable package artifact required')
        try:
            stored = json.loads(self.store.read_artifact(ref['sha256']))
        except (ValueError, UnicodeDecodeError) as exc:
            raise Unavailable('package artifact must contain JSON') from exc
        if isinstance(stored, dict) and 'package_id' not in stored:
            # Prepared packages publish only the canonical body; the identifier is
            # its content hash. Reconstruct before comparing to the caller object.
            from .package import package_hash
            stored = {'package_id': package_hash(stored), **stored}
        if canonical(stored) != canonical(package):
            raise Conflict('package differs from registered artifact')

    def claim(self, package):
        conn = self.store.connect()
        try:
            conn.execute('BEGIN IMMEDIATE')
            try:
                self._package(conn, package)
            except (Conflict, Unavailable, NotFound):
                conn.rollback()
                return False
            pid, sid = package['package_id'], package['study_id']
            existing = conn.execute('SELECT * FROM packages WHERE id=?', (pid,)).fetchone()
            if existing and (existing['study_id'] != sid or existing['package_json'] != canonical(package)):
                raise Conflict('package ID reused with different payload')
            if (existing and (existing['active'] or existing['cancelled'])) or conn.execute(
                    'SELECT 1 FROM packages WHERE study_id=? AND active=1', (sid,)).fetchone():
                conn.rollback()
                return False
            if conn.execute("SELECT 1 FROM attempts WHERE study_id=? AND status='unknown'", (sid,)).fetchone():
                conn.rollback()
                return False
            if not existing:
                conn.execute('INSERT INTO packages(id,study_id,revision,package_json,active,status) VALUES (?,?,?,?,1,?)',
                             (pid, sid, package['spec_revision'], canonical(package), 'running'))
            else:
                conn.execute("UPDATE packages SET active=1,status='running' WHERE id=?", (pid,))
            self.service._event(conn, sid, 'package_claimed', {'package_id': pid})
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def is_current(self, package):
        with closing(self.store.connect()) as conn:
            try:
                self._package(conn, package)
                row = conn.execute('SELECT active,cancelled FROM packages WHERE id=? AND study_id=?', (package['package_id'], package['study_id'])).fetchone()
                return bool(row and row['active'] and not row['cancelled'])
            except (Conflict, Unavailable, NotFound):
                return False

    def cancelled(self, package_id):
        with closing(self.store.connect()) as conn:
            row = conn.execute('SELECT cancelled FROM packages WHERE id=?', (package_id,)).fetchone()
            return not row or bool(row['cancelled'])

    def cancel(self, package_id, idempotency_key):
        def action(conn):
            row = conn.execute('SELECT * FROM packages WHERE id=?', (package_id,)).fetchone()
            if not row:
                raise NotFound('package not found')
            conn.execute('UPDATE packages SET cancelled=1 WHERE id=?', (package_id,))
            seq = self.service._event(conn, row['study_id'], 'package_cancelled', {'package_id': package_id})
            return {'package_id': package_id, 'cancelled': True, 'event_seq': seq}
        return self.service._mutate(f'package:{package_id}:cancel', idempotency_key,
                                    {'package_id': package_id}, action)[0]

    def state(self, package_id):
        with closing(self.store.connect()) as conn:
            rows = conn.execute('SELECT * FROM attempts WHERE package_id=? ORDER BY rowid', (package_id,)).fetchall()
        calls = {'screen_calls': 0, 'verify_calls': 0, 'total_calls': 0}
        reservations = {'screen_calls': 0, 'verify_calls': 0, 'total_calls': 0}
        consecutive = 0
        for row in rows:
            field = 'screen_calls' if row['kind'] == 'screen' else 'verify_calls'
            if row['status'] == 'unknown' and row['reserved']:
                reservations[field] += 1
                reservations['total_calls'] += 1
            if row['result_json']:
                result = json.loads(row['result_json'])
                if result.get('call_status') == 'called':
                    calls[field] += 1
                    calls['total_calls'] += 1
                consecutive = consecutive + 1 if result.get('outcome') in ('infrastructure_failure', 'solver_failure') else 0
        return {'attempts': len(rows), **calls, 'reservations': reservations,
                'verify_candidates': len({row['solve_id'] for row in rows if row['kind'] in ('verify', 'audit')}),
                'consecutive_failures': consecutive,
                'unresolved': any(row['status'] == 'unknown' for row in rows)}

    def begin(self, package, candidate, reserve_call):
        if not isinstance(candidate, dict) or candidate.get('kind') not in ('screen', 'verify', 'audit') or not candidate.get('solve_id') or type(reserve_call) is not bool:
            raise StudyError('candidate kind, solve ID and reservation flag required')
        conn = self.store.connect()
        try:
            conn.execute('BEGIN IMMEDIATE')
            try:
                self._package(conn, package)
            except (Conflict, Unavailable, NotFound):
                conn.rollback()
                return None
            p = conn.execute('SELECT * FROM packages WHERE id=? AND study_id=?', (package['package_id'], package['study_id'])).fetchone()
            if not p or not p['active'] or p['cancelled'] or datetime.now(timezone.utc) >= self._validate_package(package):
                conn.rollback()
                return None
            progress = conn.execute('SELECT pending_json FROM proposal_state WHERE package_id=?', (package['package_id'],)).fetchone()
            if progress and progress['pending_json'] is not None and progress['pending_json'] != canonical(candidate):
                raise Conflict('candidate differs from persisted pending proposal')
            # Read on this transaction to serialize budget checks with inserts.
            rows = conn.execute('SELECT * FROM attempts WHERE package_id=?', (package['package_id'],)).fetchall()
            if any(r['status'] == 'unknown' for r in rows) or len(rows) >= package['budget']['attempts']:
                conn.rollback()
                return None
            verified_candidates = {r['solve_id'] for r in rows if r['kind'] in ('verify', 'audit')}
            if (candidate['kind'] in ('verify', 'audit') and candidate['solve_id'] not in verified_candidates
                    and len(verified_candidates) >= 6):
                conn.rollback()
                return None
            if reserve_call:
                def consumed(row):
                    return bool((row['status'] == 'unknown' and row['reserved']) or
                                (row['result_json'] and json.loads(row['result_json']).get('call_status') == 'called'))
                used = [r for r in rows if consumed(r)]
                field = 'screen_calls' if candidate['kind'] == 'screen' else 'verify_calls'
                same = sum(1 for r in used if ('screen_calls' if r['kind'] == 'screen' else 'verify_calls') == field)
                if len(used) >= package['budget']['total_calls'] or same >= package['budget'][field]:
                    conn.rollback()
                    return None
            aid = uuid4().hex
            conn.execute('INSERT INTO attempts VALUES (?,?,?,?,?,?,?,?,NULL)',
                         (aid, package['study_id'], package['package_id'], candidate['solve_id'], candidate['kind'], canonical(candidate), int(reserve_call), 'unknown'))
            self.service._event(conn, package['study_id'], 'attempt_intent', {'attempt_id': aid, 'package_id': package['package_id'], 'reserved': reserve_call})
            conn.commit()
            return aid
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def finish(self, attempt_id, result):
        if not isinstance(result, dict):
            raise StudyError('result must be an object')
        conn = self.store.connect()
        try:
            conn.execute('BEGIN IMMEDIATE')
            row = conn.execute('SELECT * FROM attempts WHERE id=?', (attempt_id,)).fetchone()
            if not row:
                raise NotFound('attempt not found')
            if result.get('solve_id', row['solve_id']) != row['solve_id']:
                raise Conflict('result solve identity mismatch')
            encoded = canonical(result)
            if row['result_json'] is not None:
                if row['result_json'] != encoded:
                    raise Conflict('attempt resolved with different result')
                conn.commit()
                return
            call = result.get('call_status')
            if row['reserved'] and call not in ('called', 'not_called'):
                raise Unavailable('unknown call status retains reservation')
            if not row['reserved'] and call == 'called':
                raise Conflict('unreserved attempt cannot claim a backend call')
            if call not in (None, 'called', 'not_called'):
                raise Unavailable('unknown call status retains reservation')
            conn.execute("UPDATE attempts SET status='resolved',result_json=? WHERE id=?", (encoded, attempt_id))
            score = result.get('observed_j')
            qualifies = (call == 'called' and result.get('outcome') == 'success' and result.get('eligible') is True
                         and isinstance(result.get('physical_id'), str) and bool(result['physical_id'])
                         and isinstance(result.get('score_id'), str) and bool(result['score_id'])
                         and type(score) in (int, float) and math.isfinite(score))
            duplicate = qualifies and conn.execute('SELECT 1 FROM observations WHERE study_id=? AND physical_id=?',
                                                   (row['study_id'], result['physical_id'])).fetchone()
            if qualifies and not duplicate:
                conn.execute('UPDATE packages SET observation_seq=observation_seq+1 WHERE id=?', (row['package_id'],))
                seq = conn.execute('SELECT observation_seq FROM packages WHERE id=?', (row['package_id'],)).fetchone()[0]
                conn.execute('INSERT INTO observations VALUES (?,?,?,?,?,?)',
                             (row['study_id'], row['package_id'], seq, attempt_id, result['physical_id'], result['score_id']))
            if result.get('outcome') in ('success', 'cached', 'cheap_refusal'):
                conn.execute('UPDATE proposal_state SET pending_json=NULL WHERE package_id=? AND pending_json=?',
                             (row['package_id'], row['candidate_json']))
            self.service._event(conn, row['study_id'], 'attempt_resolved', {'attempt_id': attempt_id, 'call_status': call})
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def resolve(self, attempt_id, result):
        if not isinstance(result, dict) or not result.get('solve_id'):
            raise StudyError('reconciliation requires exact solve_id in result')
        return self.finish(attempt_id, result)

    def unresolved(self, study_id):
        with closing(self.store.connect()) as conn:
            rows = conn.execute("SELECT * FROM attempts WHERE study_id=? AND status='unknown' ORDER BY rowid", (study_id,)).fetchall()
            return [{'attempt_id': r['id'], 'solve_id': r['solve_id'], 'package_id': r['package_id'],
                     'kind': r['kind'], 'reserved': bool(r['reserved'])} for r in rows]

    def observations(self, package_id, after_seq=0):
        if type(after_seq) is not int or after_seq < 0:
            raise StudyError('invalid observation sequence')
        with closing(self.store.connect()) as conn:
            rows = conn.execute('SELECT o.observation_seq,o.attempt_id,a.candidate_json,a.result_json '
                                'FROM observations o JOIN attempts a ON a.id=o.attempt_id '
                                'WHERE o.package_id=? AND o.observation_seq>? ORDER BY o.observation_seq',
                                (package_id, after_seq)).fetchall()
            return [{'observation_seq': r['observation_seq'], 'attempt_id': r['attempt_id'],
                     'candidate': json.loads(r['candidate_json']), 'result': json.loads(r['result_json'])}
                    for r in rows]

    def load_progress(self, package_id):
        with closing(self.store.connect()) as conn:
            package = conn.execute('SELECT id FROM packages WHERE id=?', (package_id,)).fetchone()
            if not package:
                raise NotFound('package not found')
            row = conn.execute('SELECT * FROM proposal_state WHERE package_id=?', (package_id,)).fetchone()
            stored = json.loads(row['rng_json']) if row and row['rng_json'] else None
            history = (stored.get('proposal_history')
                       if isinstance(stored, dict) and 'proposal_history' in stored else None)
            return {'proposal_index': row['proposal_index'] if row else 0,
                    # Whole persisted proposal state (history + RNG streams), when the
                    # caller staged it with ``encode_proposal_history``.
                    'rng_state': stored,
                    'proposal_history': history,
                    'pending_candidate': json.loads(row['pending_json']) if row and row['pending_json'] else None,
                    'observations': self.observations(package_id)}

    def stage_proposal(self, package, candidate, prior_index, next_rng_state, idempotency_key):
        if (not isinstance(candidate, dict) or candidate.get('kind') not in ('screen', 'verify', 'audit')
                or not candidate.get('solve_id') or type(prior_index) is not int or prior_index < 0
                or next_rng_state is None):
            raise StudyError('candidate identity, proposal index and RNG state required')
        payload = {'package': package, 'candidate': candidate, 'prior_index': prior_index, 'rng_state': next_rng_state}
        def action(conn):
            self._package(conn, package)
            row = conn.execute('SELECT * FROM packages WHERE id=?', (package['package_id'],)).fetchone()
            if not row or not row['active'] or row['cancelled']:
                raise Conflict('package is not active')
            state = conn.execute('SELECT * FROM proposal_state WHERE package_id=?', (package['package_id'],)).fetchone()
            if state and (state['pending_json'] is not None or state['proposal_index'] != prior_index):
                raise Conflict('pending proposal or stale proposal index')
            if not state and prior_index != 0:
                raise Conflict('stale initial proposal index')
            conn.execute('INSERT INTO proposal_state VALUES (?,?,?,?) ON CONFLICT(package_id) DO UPDATE SET '
                         'proposal_index=excluded.proposal_index,rng_json=excluded.rng_json,pending_json=excluded.pending_json',
                         (package['package_id'], prior_index + 1, canonical(next_rng_state), canonical(candidate)))
            self.service._event(conn, package['study_id'], 'proposal_staged',
                                {'package_id': package['package_id'], 'proposal_index': prior_index})
            return {'proposal_index': prior_index + 1, 'rng_state': next_rng_state, 'pending_candidate': candidate}
        return self.service._mutate(f"package:{package['package_id']}:proposal", idempotency_key, payload, action)[0]

    def release(self, package_id, status):
        conn = self.store.connect()
        try:
            conn.execute('BEGIN IMMEDIATE')
            row = conn.execute('SELECT * FROM packages WHERE id=?', (package_id,)).fetchone()
            if not row:
                raise NotFound('package not found')
            if row['active']:
                conn.execute('UPDATE packages SET active=0,status=? WHERE id=?', (status, package_id))
                self.service._event(conn, row['study_id'], 'package_released', {'package_id': package_id, 'status': status})
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
