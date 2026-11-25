"""CPU preflight of each cohort search space (no solver): BO encoding round trip of the seed, and the fraction of
uniform random draws that materialise to a valid design inside the candidate envelope (resample_strict has a
500-attempt cap for 100 valid solves, i.e. it needs >= 20 % admission).

    .venv\Scripts\python.exe docs/evidence/cd_bo_cohort_2026-11-25/space_preflight.py [n_draws]
"""
import collections
import glob
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path.cwd()))
from hornlab_search.bo.encoding import ActiveProjection  # noqa: E402
from hornlab_search.config import load_config  # noqa: E402
from hornlab_search.design.space import DesignSpace  # noqa: E402
from hornlab_search.design.generated import GENERATOR_OVERSHOOT_KEY  # noqa: E402,F401

N = int(sys.argv[1]) if len(sys.argv) > 1 else 60
out = {}
for p in sorted(glob.glob('examples/typologies/cd_bo_cohort_2026-11-25/*.yaml')):
    name = Path(p).stem
    cfg = load_config(p)
    space = DesignSpace.from_config(cfg)
    proj = ActiveProjection.identity(space)
    v = proj.normalize_design(space.seed, verify_round_trip=True)
    rt = proj.denormalize(v).hash() == space.seed.hash()
    rng = np.random.default_rng(1)
    kinds = collections.Counter()
    for _ in range(N):
        try:
            d = space.denormalize(rng.random(len(space.keys())))
            kinds['ok'] += 1
        except Exception as exc:  # noqa: BLE001
            msg = str(exc)
            kinds['invalid_envelope' if 'invalid_envelope' in msg else msg.split(':')[0][:60] + ' | ' +
                  (msg.split(':')[1][:50] if ':' in msg else '')] += 1
    out[name] = {'encoding_dims': proj.d, 'seed_round_trip': rt, 'admission': kinds['ok'] / N,
                 'refusals': {k: c for k, c in kinds.items() if k != 'ok'}}
    print(f'{name:22s} enc d={proj.d} round-trip {rt} admission {kinds["ok"]}/{N}  {dict(kinds)}')
Path('docs/evidence/cd_bo_cohort_2026-11-25/space_preflight.json').write_text(json.dumps(out, indent=1) + '\n',
                                                                             encoding='utf-8')
