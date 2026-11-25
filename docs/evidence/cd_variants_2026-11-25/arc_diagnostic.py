"""CPU diagnostic after batch 1: pre-roll arc length and H wall angle at ABSOLUTE arc distance from the throat.

The rolled/Lame finding located the 6-8 kHz lever at ~55-110 mm from the throat (20-40 % of the rolled arc). This
reports where that band sits on each parent and the wall there for control / bb_h 0.65 / 1.0 (throat .25, roll-in .30).

    .venv\Scripts\python.exe docs/evidence/cd_variants_2026-11-25/arc_diagnostic.py
"""
import json, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path.cwd()))
from hornlab_search.config import brief_for_envelope_adapter, load_config  # noqa: E402
from hornlab_search.design.generators import cd_backbone_family as bf, cd_backbone_rows_family as rf  # noqa: E402
from hornlab_search.design.space import DesignSpace  # noqa: E402

HERE = Path('docs/evidence/cd_variants_2026-11-25')
SETS = {'rolled (passed)': ('examples/typologies/cd_backbone_2026-11-25', 'rolled_bb_control',
                            ['rolled_bb_h065_th025', 'rolled_bb_h100']),
        'lame m0.40 (failed)': ('examples/typologies/cd_backbone_2026-11-25', 'lame_bb_control_m040',
                                ['lame_bb_h100_m040_t25_r20']),
        **{p: ('examples/typologies/cd_variants_2026-11-25', f'{p}_control',
               [f'{p}_bb_h065_v000_t25_r30', f'{p}_bb_h100_v000_t25_r30']) for p in ('lcar', 'lcl', 'iwar')}}
MM = [10, 25, 40, 55, 80, 110, 150]


def inner(folder, name):
    cfg = load_config(Path(folder) / f'{name}.yaml')
    block = DesignSpace.from_config(cfg).seed.params['grid']
    mod = rf if rf.is_family_spec(block) else bf
    return np.asarray(mod.resolve_grid(block, brief_for_envelope_adapter(cfg.brief))['inner_points'], float)


def profile(pts):
    r = pts[0]
    rho = np.hypot(r[:, 0], r[:, 1]); z = r[:, 2]
    f = int(np.argmax(z))
    s = np.r_[0.0, np.cumsum(np.hypot(np.diff(z[:f + 1]), np.diff(rho[:f + 1])))]
    ang = np.degrees(np.arctan2(np.gradient(rho[:f + 1]), np.gradient(z[:f + 1])))
    return s, ang, f


out = {}
for label, (folder, ctl, cands) in SETS.items():
    rec = {}
    for name in [ctl, *cands]:
        try:
            s, ang, f = profile(inner(folder, name))
        except FileNotFoundError:
            continue
        rec[name] = {'arc_mm': round(float(s[-1]), 1), 'stations': f + 1,
                     'u_at_55_110': [round(55 / s[-1], 2), round(110 / s[-1], 2)],
                     'wall_at_mm': {m: round(float(np.interp(m, s, ang)), 1) for m in MM}}
        print(f'{label:20s} {name:30s} arc {s[-1]:6.1f} mm ({f + 1} st)  u(55,110)={rec[name]["u_at_55_110"]}  '
              f'wall@{MM}mm = {list(rec[name]["wall_at_mm"].values())}')
    out[label] = rec
(HERE / 'arc_diagnostic.json').write_text(json.dumps(out, indent=1) + '\n', encoding='utf-8')
