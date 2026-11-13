"""C4 lane/cancellation invariants and C5 bounded GUI/dry-run behaviour."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import numpy as np
import pytest

from b8_fake_study import (CanonicalJournal, CoupledEvaluator, SNAPSHOT, canonical,
                           seeded_package)
from hornlab_search.dataset.store import DatasetStore
from hornlab_search.gui import data_studies
from hornlab_search.gui.server import App
from hornlab_search.studies import cli
from hornlab_search.studies.lanes import StudyLane
from hornlab_search.studies.runner import run_package
from hornlab_search.studies.service import StudyService

STUDY_MODULES = [
    Path('hornlab_search/studies/schema.py'),
    Path('hornlab_search/studies/store.py'),
    Path('hornlab_search/studies/service.py'),
    Path('hornlab_search/studies/runner.py'),
    Path('hornlab_search/studies/lanes.py'),
    Path('hornlab_search/studies/reconcile.py'),
    Path('hornlab_search/studies/package.py'),
    Path('hornlab_search/studies/cli.py'),
    Path('hornlab_search/gui/study_jobs.py'),
]
FORBIDDEN_CLEANUP = ('gpu-clean', 'clear_stale_hosts', 'taskkill',
                     'subprocess.Popen', 'subprocess.run', 'os.kill',
                     '.terminate(', '.kill(')


def _lane(tmp_path):
    return StudyLane(
        runs_root=tmp_path / 'runs',
        cpu_cache=tmp_path / 'cache' / 'cpu',
        gpu_cache=tmp_path / 'cache' / 'gpu',
        cpu_dataset=tmp_path / 'dataset' / 'cpu',
        gpu_dataset=tmp_path / 'dataset' / 'gpu',
    )


def test_cpu_lane_lock_ownership_and_env_restore(tmp_path):
    lane = _lane(tmp_path)
    package = {'study_id': 'study-cpu', 'lane': 'cpu'}
    before = {key: os.environ.get(key) for key in
              ('HORNLAB_BEAT_WORKER_DIR', 'JULIA_NUM_THREADS',
               'HORNLAB_CPU_LANE_LOCK_OWNER')}
    with lane.owned('cpu', package):
        assert lane.runtime['lane'] == 'cpu'
        assert lane.runtime['cache_dir'] == (tmp_path / 'cache' / 'cpu').resolve()
        assert lane.runtime['dataset_dir'] == (tmp_path / 'dataset' / 'cpu').resolve()
        assert (tmp_path / 'runs' / '.cpu.lane.lock').is_file()
        assert not (tmp_path / 'runs' / '.gpu.lock').exists()
        assert os.environ['HORNLAB_BEAT_WORKER_DIR'] == str(
            (tmp_path / 'runs' / 'lanes' / 'cpu' / 'workers').resolve())
        assert os.environ['JULIA_NUM_THREADS'] == '12'
        assert os.environ['HORNLAB_CPU_LANE_LOCK_OWNER'] == str(os.getpid())
    assert not (tmp_path / 'runs' / '.cpu.lane.lock').exists()
    for key, value in before.items():
        assert os.environ.get(key) == value


def test_no_nested_lane_lock_and_unknown_lane_refused(tmp_path):
    first = _lane(tmp_path / 'a')
    second = _lane(tmp_path / 'b')
    with first.owned('cpu', {'study_id': 's1', 'lane': 'cpu'}):
        with pytest.raises(RuntimeError, match='another study lane'):
            with second.owned('gpu', {'study_id': 's2', 'lane': 'gpu'}):
                pass
        with pytest.raises(RuntimeError, match='another study lane'):
            with first.owned('cpu', {'study_id': 's3', 'lane': 'cpu'}):
                pass
        assert not (tmp_path / 'a' / 'runs' / '.gpu.lock').exists()
    with pytest.raises(ValueError, match='explicit matching lane'):
        with first.owned('gpu', {'study_id': 's4', 'lane': 'cpu'}):
            pass


def test_cancellation_never_calls_gpu_clean_or_kills_processes(tmp_path, monkeypatch):
    service, sid, _, package = seeded_package(tmp_path / 'registry')
    journal = CanonicalJournal(service)
    evaluator = CoupledEvaluator()

    def cancel_after_evaluate(candidate, result):
        journal.cancel(package['package_id'], 'cancel-after-evaluate')
    evaluator.on_evaluate = cancel_after_evaluate

    spawned = []
    def forbidden(*args, **kwargs):
        spawned.append((args, kwargs))
        raise AssertionError('cancellation must not spawn or kill processes')
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    monkeypatch.setattr(subprocess, 'run', forbidden)
    monkeypatch.setattr(os, 'kill', forbidden)

    result = run_package(package, evaluator, _lane(tmp_path), journal)
    # The safety invariant is that cancellation stops work without host/process
    # cleanup, no extra attempt, and no respawn.  The exact stop label is covered
    # separately in test_b8_regressions.py (currently reported as "stale").
    assert result['status'] in {'cancelled', 'stale'}
    assert journal.cancelled(package['package_id']) is True
    assert evaluator.evaluate_calls == 1
    assert spawned == []


def test_study_modules_have_no_host_cleanup_or_process_kill_paths():
    root = Path(__file__).resolve().parents[1]
    hits = []
    for relative in STUDY_MODULES:
        text = (root / relative).read_text(encoding='utf-8')
        for token in FORBIDDEN_CLEANUP:
            if token in text:
                hits.append((relative.as_posix(), token))
    assert hits == [], f'study path can touch hosts/processes: {hits}'


def test_list_and_detail_endpoints_do_not_read_artifact_bytes(tmp_path, monkeypatch):
    service, sid, _ = seeded_package(tmp_path / 'registry')[:3]
    app = App(tmp_path, runs=tmp_path / 'runs', study_service=service)
    reads = []
    original = service.store.read_artifact

    def counted(sha):
        reads.append(sha)
        return original(sha)

    monkeypatch.setattr(service.store, 'read_artifact', counted)
    listing = app.get('/api/studies', {})
    assert listing['studies'][0]['id'] == sid
    assert set(listing['studies'][0]) <= {
        'id', 'study_id', 'name', 'question', 'revision', 'spec_revision', 'status', 'readiness'}
    assert 'spec' not in listing['studies'][0]
    detail = app.get(f'/api/studies/{sid}', {})
    assert detail['id'] == sid and detail['revision'] == 1
    assert reads == [], 'list/detail views must not load snapshot/model/proposal bytes'

    # A direct endpoint-ready summary also refuses to carry arbitrary artifact data.
    summaries = data_studies.study_summaries(
        [{'id': sid, 'name': 'fixture', 'revision': 1, 'readiness': {'stages': {}},
          'data': {'npz': 'must-not-appear'}, 'npz_arrays': [1, 2, 3]}])
    assert summaries == [{'id': sid, 'name': 'fixture', 'revision': 1,
                          'readiness': {'stages': {}}}]


def test_dry_run_spawns_zero_processes_and_writes_zero_acoustic_records(tmp_path, monkeypatch, capsys):
    root = tmp_path / 'run-root'
    root.mkdir()
    package = seeded_package(tmp_path / 'registry')[3]
    (root / 'package.json').write_text(canonical(package), encoding='utf-8')

    spawned = []
    def forbidden(*args, **kwargs):
        spawned.append((args, kwargs))
        raise AssertionError('dry-run must not spawn a solve process')
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    monkeypatch.setattr(subprocess, 'run', forbidden)
    monkeypatch.setattr(os, 'kill', forbidden)
    monkeypatch.setattr(DatasetStore, 'append', forbidden)
    monkeypatch.setattr(DatasetStore, 'append_traces', forbidden)
    monkeypatch.setattr(np, 'savez', forbidden)
    monkeypatch.setattr(np, 'savez_compressed', forbidden)

    code = cli.main(['run', '--root', str(root), '--package', 'package.json', '--dry-run'])
    captured = capsys.readouterr()
    assert code == 0, captured.out + captured.err
    payload = json.loads(captured.out.strip().splitlines()[-1])
    assert payload['ok'] is True and payload['status'] == 'dry_run'
    assert payload['package_id'] == package['package_id']
    assert spawned == []
    assert not (root / 'studies.sqlite3').exists()
    assert not (root / 'artifacts').exists()

    # The runner dry-run exits before any evaluator/lane capability is consulted.
    evaluator = CoupledEvaluator()
    result = run_package(package, evaluator, None, None, dry_run=True)
    assert result['status'] == 'dry_run'
    assert evaluator.evaluate_calls == 0


def test_study_page_disposal_and_stale_revision_response(tmp_path):
    module = Path(__file__).resolve().parents[1] / 'hornlab_search/gui/static/studies.js'
    script = tmp_path / 'b8_gui.mjs'
    script.write_text(r'''
import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
const src = await readFile(process.argv[2], "utf8");
const m = await import("data:text/javascript;base64," + Buffer.from(src).toString("base64"));

// ---- disposal clears the poll interval
let tick = null, cleared = 0, armed = 0;
const realSet = globalThis.setInterval, realClear = globalThis.clearInterval;
globalThis.setInterval = (fn, ms) => { armed++; tick = fn; return 41; };
globalThis.clearInterval = h => { assert.equal(h, 41); cleared++; };
const root = {innerHTML:"", addEventListener(){}, removeEventListener(){}, contains(){return true;}};
const api = {getStudy:async () => ({id:"study1", revision:1}),
             getPanel:async () => ({phase:"overview",status:"ready",revision:1,data:{}})};
const dispose = m.mountStudy(root,{studyId:"study1",phase:"overview",api,pollMs:0.5});
await new Promise(r => setImmediate(r));
assert.equal(armed, 1);
assert.equal(typeof tick, "function");
dispose();
assert.equal(cleared, 1);
globalThis.setInterval = realSet; globalThis.clearInterval = realClear;

// ---- a late stale response cannot overwrite the newer revision
const resolvers = [];
const call = kind => new Promise(resolve => resolvers.push({kind, resolve}));
let tick2 = null;
globalThis.setInterval = fn => { tick2 = fn; return 42; };
globalThis.clearInterval = () => {};
const mountRoot = {innerHTML:"", addEventListener(){}, removeEventListener(){}, contains(){return true;}};
const staleApi = {getStudy:() => call("study"), getPanel:() => call("panel")};
const dispose2 = m.mountStudy(mountRoot,{studyId:"study1",phase:"overview",api:staleApi,pollMs:5000});
await new Promise(r => setImmediate(r));   // refresh #1 pending at resolvers[0..1]
tick2();                                    // refresh #2 pending at resolvers[2..3]
await new Promise(r => setImmediate(r));
assert.equal(resolvers.length, 4);
resolvers[2].resolve({id:"study1", revision:4});
resolvers[3].resolve({phase:"overview",status:"ready",revision:4,data:{marker:"newer"}});
await new Promise(r => setImmediate(r));
resolvers[0].resolve({id:"study1", revision:3});
resolvers[1].resolve({phase:"overview",status:"ready",revision:3,data:{marker:"older"}});
await new Promise(r => setImmediate(r));
assert.ok(mountRoot.innerHTML.includes("Revision 4"), mountRoot.innerHTML);
assert.ok(mountRoot.innerHTML.includes("newer"), mountRoot.innerHTML);
assert.ok(!mountRoot.innerHTML.includes("older"), mountRoot.innerHTML);
dispose2();
console.log("b8 gui disposal ok");
''', encoding='utf-8')
    result = subprocess.run(['node', str(script), str(module)],
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'b8 gui disposal ok' in result.stdout
