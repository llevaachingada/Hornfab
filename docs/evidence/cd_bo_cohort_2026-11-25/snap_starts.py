"""Snap every exploration start onto the search space's own rounding grid (normalize -> denormalize once) so its
design hash round-trips through the BO encoder. Sobol starts are generated at full float precision; the space
rounds knobs on denormalize, so an unsnapped start is 'not representable' (HashMismatchError). CPU only.

    .venv\Scripts\python.exe docs/evidence/cd_bo_cohort_2026-11-25/snap_starts.py
"""
import glob
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path.cwd()))
from hornlab_search.bo.encoding import ActiveProjection  # noqa: E402
from hornlab_search.config import load_config  # noqa: E402
from hornlab_search.design.space import DesignSpace  # noqa: E402

for p in sorted(glob.glob('examples/typologies/cd_explore_2026-11-25/*.yaml')):
    space = DesignSpace.from_config(load_config(p))
    proj = ActiveProjection.identity(space)
    snapped = proj.denormalize(proj.normalize_design(space.seed, verify_round_trip=False))
    if snapped.hash() == space.seed.hash():
        continue
    raw = yaml.safe_load(Path(p).read_text(encoding='utf-8'))
    params = snapped.params['grid']['knobs'] if isinstance(snapped.params.get('grid'), dict) else snapped.params
    raw['seed_params'] = {k: params[k] for k in raw['seed_params']}
    Path(p).write_text(yaml.safe_dump(raw, sort_keys=False), encoding='utf-8', newline='\n')
    print('snapped', Path(p).stem, space.seed.hash()[:12], '->', snapped.hash()[:12])
