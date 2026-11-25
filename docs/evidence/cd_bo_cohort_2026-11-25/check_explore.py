"""Exploration configs: load as the search will, BO encoding round trip, one search box per family.

    .venv\Scripts\python.exe docs/evidence/cd_bo_cohort_2026-11-25/check_explore.py
"""
import glob
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
from hornlab_search.bo.encoding import ActiveProjection  # noqa: E402
from hornlab_search.config import load_config  # noqa: E402
from hornlab_search.design.space import DesignSpace  # noqa: E402

boxes, bad = {}, []
for p in sorted(glob.glob('examples/typologies/cd_explore_2026-11-25/*.yaml')):
    name = Path(p).stem
    fam = re.sub(r'_r\d+$', '', name)
    try:
        space = DesignSpace.from_config(load_config(p))
        proj = ActiveProjection.identity(space)
        if proj.denormalize(proj.normalize_design(space.seed)).hash() != space.seed.hash():
            bad.append(f'{name}: round trip')
        boxes.setdefault(fam, {}).setdefault(
            tuple(sorted((k, b.lo, b.hi) for k, b in space.bounds.items() if b.search)), []).append((name, proj.d))
    except Exception as exc:  # noqa: BLE001
        bad.append(f'{name}: {type(exc).__name__}: {str(exc)[-160:]}')
for fam, by_box in boxes.items():
    runs = [n for v in by_box.values() for n in v]
    print(f'{fam:16s} runs {len(runs):2d}  dims {runs[0][1]:2d}  distinct boxes {len(by_box)}')
print('problems:', bad or 'none')
