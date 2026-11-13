"""Rebuild the native TrainingSet with the strict-policy builder; compare with committed hashes."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
from hornlab_search.bo.data import build_native_training_set  # noqa: E402

CONFIG = REPO / 'examples/typologies/campaign_2026-10-26_v4/native__ath_core_v4.yaml'
SCORES = REPO / 'scratch/bo_m0/r0/offline_scores_native_full/offline_scores.json'
CATALOG = REPO / 'scratch/bo_m0/s0/catalog/catalog.csv'
COMMITTED = REPO / 'docs/evidence/bo_study_2026-11-12/b2_native/native_trainingset.json'


def sha(a):
    return hashlib.sha256(np.ascontiguousarray(np.asarray(a, dtype=np.float64)).tobytes()).hexdigest()


out = {}
for strict in (False, True):
    ts = build_native_training_set(CONFIG, scores_json=SCORES, catalog_csv=CATALOG,
                                   require_single_fidelity=strict)
    out[f'require_single_fidelity={strict}'] = {
        'status': ts.status, 'n': ts.n, 'n_eligible': ts.n_eligible,
        'refusal_reasons': ts.meta['refusal_reasons'],
        'cohort_policy': ts.meta['cohort_policy'],
        'ids_sha256': hashlib.sha256('\n'.join(ts.ids).encode()).hexdigest(),
        'x_sha256': None if ts.X is None else sha(ts.X),
        'j_sha256': None if ts.J is None else sha(ts.J),
    }
committed = json.loads(COMMITTED.read_text(encoding='utf-8'))
out['committed_hashes'] = committed['hashes']
out['inputs_sha256'] = {str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in (CONFIG, SCORES, CATALOG, COMMITTED)}
print(json.dumps(out, indent=1, default=str))
