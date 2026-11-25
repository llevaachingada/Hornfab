"""Print the scoring identity every cohort/exploration config will actually use (objective version, brief name,
envelope policy, CD block present). CPU only.

    .venv\Scripts\python.exe docs/evidence/cd_bo_cohort_2026-11-25/check_versions.py
"""
import glob
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
from hornlab_search.config import envelope_policy, load_config  # noqa: E402

seen = Counter()
for p in sorted(glob.glob('examples/typologies/cd_bo_cohort_2026-11-25/*.yaml') +
                glob.glob('examples/typologies/cd_explore_2026-11-25/*.yaml')):
    cfg = load_config(p)
    obj = cfg.objective
    ver = getattr(obj, 'version', None) if not isinstance(obj, dict) else obj.get('version')
    key = (ver, cfg.brief.get('name'), envelope_policy(cfg.brief).mode, 'cd' in (cfg.brief.get('objective') or {}))
    seen[key] += 1
    if ver != 11:
        print('NOT v11:', p, key)
for k, n in seen.items():
    print(n, 'configs -> objective version', k[0], '| brief', k[1], '| policy', k[2], '| v11 CD block', k[3])
