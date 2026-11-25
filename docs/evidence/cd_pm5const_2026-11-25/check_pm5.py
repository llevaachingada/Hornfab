r"""pm5 configs: load as the search will, brief identity, BO encoding round trip, same box as the source run-1.

    .venv\Scripts\python.exe docs/evidence/cd_pm5const_2026-11-25/check_pm5.py
"""
import glob
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
from hornlab_search.bo.encoding import ActiveProjection  # noqa: E402
from hornlab_search.config import load_config  # noqa: E402
from hornlab_search.design.space import DesignSpace  # noqa: E402

SRC = {'favl_pm5': 'examples/typologies/favL_2026-11-20/favL__2in_c500_open115.yaml'}
bad = []
for p in sorted(glob.glob('examples/typologies/cd_pm5const_2026-11-25/*.yaml')):
    name = Path(p).stem
    try:
        cfg = load_config(p)
        space = DesignSpace.from_config(cfg)
        proj = ActiveProjection.identity(space)
        if proj.denormalize(proj.normalize_design(space.seed)).hash() != space.seed.hash():
            bad.append(f'{name}: round trip')
        src = SRC.get(name, f'examples/typologies/cd_explore_2026-11-25/{name.replace("_pm5", "")}_r1.yaml')
        box = lambda s: sorted((k, b.lo, b.hi) for k, b in s.bounds.items() if b.search)  # noqa: E731
        same = box(DesignSpace.from_config(load_config(src))) == box(space)
        obj = cfg.brief['objective']
        print(f'{name:20s} dims {proj.d:2d} brief {cfg.brief["name"]} constancy {obj.get("constancy")} '
              f'H {cfg.brief["target"]["coverage_profile"]["h"][0]["min_deg"]}-'
              f'{cfg.brief["target"]["coverage_profile"]["h"][0]["max_deg"]} box==source {same}')
        if not same:
            bad.append(f'{name}: box differs from {src}')
    except Exception as exc:  # noqa: BLE001
        bad.append(f'{name}: {type(exc).__name__}: {str(exc)[-200:]}')
print('problems:', bad or 'none')
