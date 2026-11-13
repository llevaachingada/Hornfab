"""Independent, solver-free foundation checks for the M2 review."""
import json
import subprocess
import sys

import numpy as np
import pytest

from hornlab_search.bo.data import DataError, TrainingObservation, build_training_set


def test_bo_import_does_not_initialize_optional_engine():
    code = ("import json,sys; import hornlab_search.bo; "
            "print(json.dumps({k:k in sys.modules for k in ('torch','botorch','gpytorch')}))")
    run = subprocess.run([sys.executable, '-c', code], check=True, capture_output=True, text=True)
    assert json.loads(run.stdout) == {'torch': False, 'botorch': False, 'gpytorch': False}


def test_duplicate_solve_identity_does_not_inflate_observation_count():
    rows = [TrainingObservation(str(i), np.array([i / 20, .5]), float(i),
                                geometry_hash=str(i), solve_hash='same-spec') for i in range(15)]
    rows.append(TrainingObservation('duplicate', np.array([0., .5]), 0.,
                                    geometry_hash='0', solve_hash='same-spec'))
    training = build_training_set(rows, d=2)
    assert training.status == 'needs_initial_data'
    assert training.n_unique == 15


def test_failed_attempts_do_not_become_training_measurements():
    rows = [TrainingObservation(str(i), np.array([i / 20, .5]), float(i),
                                geometry_hash=str(i), solve_hash='same-spec') for i in range(15)]
    rows.append(TrainingObservation('error', np.array([.9, .5]), 1000.,
                                    status='infrastructure_failure', geometry_hash='error', solve_hash='same-spec'))
    assert build_training_set(rows, d=2).status == 'needs_initial_data'


@pytest.mark.parametrize('outside', [-0.0000001, 1.0000001])
def test_historical_out_of_domain_observation_is_refused(outside):
    rows = [TrainingObservation(str(i), np.array([i / 20, .5]), float(i),
                                geometry_hash=str(i), solve_hash='same-spec') for i in range(16)]
    rows[5] = TrainingObservation('outside', np.array([outside, .5]), 1.,
                                  geometry_hash='outside', solve_hash='same-spec')
    with pytest.raises(DataError, match='historical clipping is forbidden'):
        build_training_set(rows, d=2)


def test_unit_box_endpoints_are_accepted():
    rows = [TrainingObservation(str(i), np.array([i / 15, .5]), float(i),
                                geometry_hash=str(i), solve_hash='same-spec') for i in range(16)]
    assert build_training_set(rows, d=2).status == 'ok'
