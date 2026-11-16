"""Study budget profiles (2026-11-14): ``baseline`` stays the frozen bo-study-v1.1 budget and the
default; ``comparison-25``/``comparison-30``/``comparison-60`` are explicit opt-ins for matched
BO-vs-CMA campaigns. Synthetic roots only."""
from __future__ import annotations

import json

import pytest

from hornlab_search.studies.package import (BUDGET_PROFILES, EXECUTION_BUDGET, budget_caps,
                                            verify_package)
from hornlab_search.studies.runner import ContractError, _validate as validate_package_contract
from hornlab_search.studies.schema import StudyError, digest
from hornlab_search.studies.service import DraftAttemptJournal
from test_studies_package_b2 import make_package, seed_study


def _reid(package: dict) -> dict:
    package = json.loads(json.dumps(package))
    package['package_id'] = digest({k: v for k, v in package.items() if k != 'package_id'})
    return package


def test_baseline_is_the_frozen_budget_and_the_default():
    assert BUDGET_PROFILES['baseline'] == EXECUTION_BUDGET
    assert budget_caps({}) == EXECUTION_BUDGET


def test_default_package_body_is_unchanged(tmp_path):
    service, sid, _ = seed_study(tmp_path)
    package = make_package(service, sid)
    assert 'budget_profile' not in package            # baseline packages keep their historical body
    assert package['budget'] == EXECUTION_BUDGET


def test_comparison_profile_is_explicit_and_recorded(tmp_path):
    service, sid, _ = seed_study(tmp_path)
    package = make_package(service, sid, budget_profile='comparison-60')
    assert package['budget_profile'] == 'comparison-60'
    assert package['budget'] == BUDGET_PROFILES['comparison-60']
    assert package['budget']['screen_calls'] == 60
    assert verify_package(package) is package


def test_unknown_profile_is_refused(tmp_path):
    service, sid, _ = seed_study(tmp_path)
    with pytest.raises(StudyError, match='budget_profile'):
        make_package(service, sid, budget_profile='unlimited')


@pytest.mark.parametrize('profile, caps', [
    ('comparison-25', {'screen_calls': 25, 'verify_calls': 6,
                       'total_calls': 31, 'attempts': 150}),
    ('comparison-25x2', {'screen_calls': 25, 'verify_calls': 2,
                         'total_calls': 27, 'attempts': 150}),
    ('comparison-25x0', {'screen_calls': 25, 'verify_calls': 0,
                         'total_calls': 25, 'attempts': 150}),
    ('comparison-30', {'screen_calls': 30, 'verify_calls': 6,
                       'total_calls': 36, 'attempts': 180}),
    ('comparison-80x2', {'screen_calls': 80, 'verify_calls': 2,
                         'total_calls': 82, 'attempts': 400}),
])
def test_new_comparison_profiles_are_exact_and_verifiable(tmp_path, profile, caps):
    assert BUDGET_PROFILES[profile] == caps
    assert budget_caps({'budget_profile': profile}) == caps
    service, sid, _ = seed_study(tmp_path)
    package = make_package(service, sid, budget_profile=profile)
    assert package['budget_profile'] == profile
    assert package['budget'] == caps
    assert verify_package(package) is package


def test_budget_caps_refuses_an_unknown_profile():
    with pytest.raises(StudyError, match='budget_profile'):
        budget_caps({'budget_profile': 'comparison-40'})


def test_a_baseline_package_cannot_carry_a_bigger_budget(tmp_path):
    service, sid, _ = seed_study(tmp_path)
    forged = _reid({**make_package(service, sid), 'budget': dict(BUDGET_PROFILES['comparison-60'])})
    with pytest.raises(StudyError):
        verify_package(forged)


def test_a_profile_package_must_carry_exactly_its_profile(tmp_path):
    service, sid, _ = seed_study(tmp_path)
    package = make_package(service, sid, budget_profile='comparison-60')
    forged = _reid({**package, 'budget': {**package['budget'], 'screen_calls': 61}})
    with pytest.raises(StudyError):
        verify_package(forged)
    forged = _reid({**package, 'budget_profile': 'nope'})
    with pytest.raises(StudyError):
        verify_package(forged)


def test_journal_counts_to_the_profile_cap(tmp_path):
    service, sid, _ = seed_study(tmp_path)
    package = make_package(service, sid, budget_profile='comparison-60')
    journal = DraftAttemptJournal(service)
    assert journal.claim(package)
    for index in range(60):
        attempt = journal.begin(package, {'kind': 'screen', 'solve_id': f's{index}'}, True)
        assert attempt, index
        journal.finish(attempt, {'solve_id': f's{index}', 'call_status': 'called', 'outcome': 'success'})
    assert journal.begin(package, {'kind': 'screen', 'solve_id': 'over'}, True) is None
    assert journal.state(package['package_id'])['screen_calls'] == 60


def test_runner_contract_uses_the_profile_caps(tmp_path):
    service, sid, _ = seed_study(tmp_path)
    package = make_package(service, sid, budget_profile='comparison-60')
    validate_package_contract(package, True)
    bad = {**package, 'budget_profile': 'nope'}
    with pytest.raises(ContractError):
        validate_package_contract(bad, True)
    over = {**package, 'budget': {**package['budget'], 'screen_calls': 61}}
    with pytest.raises(ContractError):
        validate_package_contract(over, True)
