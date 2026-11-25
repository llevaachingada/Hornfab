"""Load every v4 config as the search will (family laws at each bound endpoint), check the BO encoding round trip
and that all seeds of a family share one search box (one BO identity).

    .venv\Scripts\python.exe docs/evidence/cd_bo_cohort_2026-11-25/check_v4.py
"""
import glob
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
from hornlab_search.bo.encoding import ActiveProjection  # noqa: E402
from hornlab_search.config import envelope_policy, load_config  # noqa: E402
from hornlab_search.design.space import DesignSpace  # noqa: E402

boxes = {}
for p in sorted(glob.glob('examples/typologies/cd_bo_cohort_2026-11-25/*_v4_s*.yaml')):
    name = Path(p).stem
    try:
        cfg = load_config(p)
        space = DesignSpace.from_config(cfg)
        proj = ActiveProjection.identity(space)
        rt = proj.denormalize(proj.normalize_design(space.seed)).hash() == space.seed.hash()
        fam = name.rsplit('_s', 1)[0]
        boxes.setdefault(fam, set()).add(tuple(sorted((k, b.lo, b.hi) for k, b in space.bounds.items() if b.search)))
        print(f'{name:22s} OK {envelope_policy(cfg.brief).mode} dims {proj.d:2d} round-trip {rt} '
              f'sigma {cfg.search.sigma0} seed {space.seed.hash()[:12]}')
    except Exception as exc:  # noqa: BLE001
        print(f'{name:22s} ERROR {type(exc).__name__}: {str(exc)[-220:]}')
print({f: len(v) for f, v in boxes.items()}, '<- distinct boxes per family (must all be 1)')
