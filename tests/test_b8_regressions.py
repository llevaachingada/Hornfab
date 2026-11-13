"""Independent reproductions of defects found during B8 adversarial verification.

These are deliberately red until the owner/parent routes the source fix.  They are
not skipped: a failing verifier test is the evidence, and weakening it would hide
the defect.
"""
from __future__ import annotations

import json

from b8_fake_study import CoupledEvaluator, CanonicalJournal, seeded_package
from hornlab_search.studies.lanes import StudyLane
from hornlab_search.studies.runner import run_package
from hornlab_search.studies.service import DraftAttemptJournal


def test_registered_package_body_identity_is_accepted_by_journal_claim(tmp_path):
    """Regression guard: ``claim`` accepts a package from ``prepare_run_package``.

    At the c7dd6a3 start of this verification, ``prepare_run_package`` published
    the canonical body without ``package_id`` while ``_package`` compared the body
    with the full package dict, so every valid package was rejected
    (``tests/test_studies_package_b2.py`` failed).  Commit 9b798f5 reconstructs the
    body identifier before comparison; this test keeps that behaviour pinned.
    """
    service, sid, _, package = seeded_package(tmp_path / 'registry')
    stored = json.loads(service.store.read_artifact(package['package_id']))
    assert 'package_id' not in stored, 'published body must omit package_id'
    assert stored != package

    assert DraftAttemptJournal(service).claim(package) is True, (
        'DraftAttemptJournal rejects every registered package: service.py:390 '
        'compares the package body (package.py:219) to the full package dict')


def _lane(tmp_path):
    return StudyLane(
        runs_root=tmp_path / 'runs',
        cpu_cache=tmp_path / 'cache' / 'cpu',
        gpu_cache=tmp_path / 'cache' / 'gpu',
        cpu_dataset=tmp_path / 'dataset' / 'cpu',
        gpu_dataset=tmp_path / 'dataset' / 'gpu',
    )


def test_explicit_cancellation_is_reported_as_cancelled_not_stale(tmp_path):
    """An explicit cancel stops work but the runner reports ``stale``.

    Defect: the loop checks ``journal.is_current`` (which already returns False
    when ``cancelled=1``, service.py:427-434) before ``journal.cancelled``
    (runner.py:164-169), so a cancel issued while the package is running is
    reported as ``stale`` and the ``cancelled`` branch is unreachable.
    """
    service, sid, _, package = seeded_package(tmp_path / 'registry')
    journal = CanonicalJournal(service)
    evaluator = CoupledEvaluator()
    evaluator.on_evaluate = lambda candidate, result: journal.cancel(
        package['package_id'], 'cancel-regression')

    result = run_package(package, evaluator, _lane(tmp_path), journal)
    assert result['status'] == 'cancelled', (
        'explicit cancellation is mislabeled as stale: runner.py:164-169 checks '
        'is_current (service.py:427-434) before cancelled')
