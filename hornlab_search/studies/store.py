"""SQLite and immutable artifact primitives. Explicit local root required."""
from __future__ import annotations

import hashlib
import os
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile

from .schema import StudyError, Unavailable

MIGRATIONS = {1: '''
CREATE TABLE studies (id TEXT PRIMARY KEY, parent_id TEXT REFERENCES studies(id), spec_revision INTEGER NOT NULL, event_seq INTEGER NOT NULL DEFAULT 0);
CREATE TABLE revisions (study_id TEXT NOT NULL REFERENCES studies(id), revision INTEGER NOT NULL, spec_json TEXT NOT NULL, spec_hash TEXT NOT NULL, PRIMARY KEY(study_id,revision));
CREATE TABLE artifacts (study_id TEXT NOT NULL REFERENCES studies(id), revision INTEGER NOT NULL, kind TEXT NOT NULL, sha256 TEXT NOT NULL, dependencies_json TEXT NOT NULL, PRIMARY KEY(study_id,revision,kind), FOREIGN KEY(study_id,revision) REFERENCES revisions(study_id,revision));
CREATE TABLE events (study_id TEXT NOT NULL REFERENCES studies(id), seq INTEGER NOT NULL, kind TEXT NOT NULL, payload_json TEXT NOT NULL, PRIMARY KEY(study_id,seq));
CREATE TABLE decisions (study_id TEXT NOT NULL REFERENCES studies(id), seq INTEGER NOT NULL, revision INTEGER NOT NULL, outcome TEXT NOT NULL, rationale TEXT NOT NULL, PRIMARY KEY(study_id,seq));
CREATE TABLE idempotency (scope TEXT NOT NULL, key TEXT NOT NULL, payload_hash TEXT NOT NULL, response_json TEXT NOT NULL, PRIMARY KEY(scope,key));
CREATE TABLE jobs (id TEXT PRIMARY KEY, study_id TEXT NOT NULL REFERENCES studies(id), revision INTEGER NOT NULL, kind TEXT NOT NULL, request_hash TEXT NOT NULL, package_hash TEXT, status TEXT NOT NULL, fields_json TEXT NOT NULL);
CREATE TABLE proposals (id TEXT PRIMARY KEY, study_id TEXT NOT NULL REFERENCES studies(id), payload_json TEXT NOT NULL);
CREATE TABLE packages (id TEXT PRIMARY KEY, study_id TEXT NOT NULL REFERENCES studies(id), revision INTEGER NOT NULL, package_json TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 0, cancelled INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'prepared', observation_seq INTEGER NOT NULL DEFAULT 0);
CREATE TABLE attempts (id TEXT PRIMARY KEY, study_id TEXT NOT NULL REFERENCES studies(id), package_id TEXT NOT NULL REFERENCES packages(id), solve_id TEXT NOT NULL, kind TEXT NOT NULL, candidate_json TEXT NOT NULL, reserved INTEGER NOT NULL, status TEXT NOT NULL, result_json TEXT);
CREATE TABLE observations (study_id TEXT NOT NULL REFERENCES studies(id), package_id TEXT NOT NULL REFERENCES packages(id), observation_seq INTEGER NOT NULL, attempt_id TEXT NOT NULL UNIQUE REFERENCES attempts(id), physical_id TEXT NOT NULL, score_id TEXT NOT NULL, UNIQUE(study_id,physical_id), PRIMARY KEY(package_id,observation_seq));
CREATE TABLE proposal_state (package_id TEXT PRIMARY KEY REFERENCES packages(id), proposal_index INTEGER NOT NULL, rng_json TEXT, pending_json TEXT);
''',
# B4/B5: durable launch idempotency. One row per (study, package); the row is
# written BEFORE the launcher is called, so a restart can never re-dispatch a
# package whose launch outcome is unknown (status 'launching' or 'unknown').
2: '''
CREATE TABLE launches (study_id TEXT NOT NULL REFERENCES studies(id), package_id TEXT NOT NULL, idempotency_key TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('launching','launched','unknown')), result_json TEXT, error TEXT, PRIMARY KEY(study_id,package_id));
'''}


class StudyStore:
    def __init__(self, root):
        if root is None:
            raise StudyError('explicit local study root required')
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.artifacts = self.root / 'artifacts'
        self.artifacts.mkdir(exist_ok=True)
        self.db = self.root / 'studies.sqlite3'
        self._migrate()

    def connect(self):
        conn = sqlite3.connect(self.db, timeout=5, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys=ON')
        conn.execute('PRAGMA busy_timeout=5000')
        return conn

    def _migrate(self):
        conn = self.connect()
        try:
            conn.execute('PRAGMA journal_mode=WAL')
            version = conn.execute('PRAGMA user_version').fetchone()[0]
            if version > max(MIGRATIONS):
                raise StudyError(f'unsupported newer schema version {version}')
            for number in range(version + 1, max(MIGRATIONS) + 1):
                conn.executescript('BEGIN IMMEDIATE;\n' + MIGRATIONS[number] + f'\nPRAGMA user_version={number};\nCOMMIT;')
        finally:
            conn.close()

    def publish(self, content: bytes) -> str:
        """Publish complete bytes by content address; preserve incomplete/orphan files."""
        if not isinstance(content, bytes):
            raise StudyError('artifact content must be bytes')
        sha = hashlib.sha256(content).hexdigest()
        dest = self.artifacts / sha
        fd, name = tempfile.mkstemp(prefix='.incomplete-', dir=self.artifacts)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            if hashlib.sha256(Path(name).read_bytes()).hexdigest() != sha:
                raise Unavailable('artifact verification failed before publication')
            try:
                os.link(name, dest)
            except FileExistsError:
                pass
            if hashlib.sha256(dest.read_bytes()).hexdigest() != sha:
                raise Unavailable('existing content-addressed artifact is corrupt')
        except Exception:
            # Leave the incomplete file for diagnostics, not silent cleanup.
            raise
        else:
            os.unlink(name)
        return sha

    def read_artifact(self, sha: str) -> bytes:
        if len(sha) != 64 or any(c not in '0123456789abcdef' for c in sha):
            raise StudyError('invalid artifact hash')
        try:
            data = (self.artifacts / sha).read_bytes()
        except FileNotFoundError as exc:
            raise Unavailable('artifact missing') from exc
        if hashlib.sha256(data).hexdigest() != sha:
            raise Unavailable('artifact hash mismatch')
        return data

    def recovery_diagnostics(self):
        with closing(self.connect()) as conn:
            referenced = {row[0] for row in conn.execute('SELECT DISTINCT sha256 FROM artifacts')}
        present = {p.name for p in self.artifacts.iterdir() if p.is_file()}
        return {'unreferenced': sorted(x for x in present - referenced if not x.startswith('.incomplete-')),
                'incomplete': sorted(x for x in present if x.startswith('.incomplete-')),
                'missing': sorted(referenced - present)}
