r"""Soft size cost on the +-5 deg briefs (owner 2026-11-25 18:23 + 18:56 "the more strict one").

New briefs = the pm5const briefs + envelope.soft_penalty {weight 1.0, tolerance 0.05} (5 % over the product box =
+1.0 J, 10 % = +4.0) and the hard refusal moved from 1.15 to 1.30 x so the penalty, not the refusal, steers.
Repoints the pm5 family configs whose jobs have NOT started (identity is new; no rows yet) and writes
favl_pm5_size (favl_pm5_wide's box and seed on the size brief).

    .venv\Scripts\python.exe docs/evidence/cd_pm5const_2026-11-25/build_size.py
"""
from pathlib import Path

import yaml

CFG = Path('examples/typologies/cd_pm5const_2026-11-25')
BRIEFS = [Path('examples/briefs/home_xo900_2026-11-20/room_landscape_80x50_900_hf1440_v11cd_open115_pm5const_2026-11-25.yaml'),
          Path('examples/briefs/hf2in_2026-11-20/compact500_xo900_80x50_hf2in_v11cd_open115_pm5const_2026-11-25.yaml')]
NOT_STARTED = ['rolled_pm5', 'lcl_beak_pm5', 'iwar_beak_pm5', 'sculpted_beak_pm5', 'sculpted_sweep_pm5', 'klangfilm_pm5']


def size_brief(src):
    b = yaml.safe_load(src.read_text(encoding='utf-8'))
    b['name'] += '_size5'
    b['envelope'].update(max_utilization=1.30, soft_penalty={'weight': 1.0, 'tolerance': 0.05})
    b['description'] = (b['description'] + ' SIZE: soft cost on J past the product box, '
                        '((max W/H/D utilization - 1) / 0.05)^2 (5 % over = +1.0 J, 10 % = +4.0); hard refusal '
                        'at 1.30 x. hornlab_search/objective/size_penalty.py. NEW J/BO IDENTITY.')
    dst = src.with_name(src.name.replace('_pm5const_', '_pm5const_size5_'))
    dst.write_text(f'# 2026-11-25: {src.name} + soft size penalty; see description.\n'
                   + yaml.safe_dump(b, sort_keys=False), encoding='utf-8', newline='\n')
    return dst


def repoint(name, brief):
    p = CFG / f'{name}.yaml'
    cfg = yaml.safe_load(p.read_text(encoding='utf-8'))
    cfg['brief_file'] = (Path('../../briefs') / brief.parent.name / brief.name).as_posix()
    cfg['description'] += ' Brief: +-5 deg constant-directivity + soft size penalty (5 % over = +1 J).'
    p.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding='utf-8', newline='\n')


def main():
    room, c500 = (size_brief(b) for b in BRIEFS)
    for n in NOT_STARTED:
        repoint(n, room)
    cfg = yaml.safe_load((CFG / 'favl_pm5_wide.yaml').read_text(encoding='utf-8'))
    cfg['name'] = 'favl_pm5_size'
    cfg['search'] = {**cfg['search'], 'seed': 52612}
    (CFG / 'favl_pm5_size.yaml').write_text(yaml.safe_dump(cfg, sort_keys=False), encoding='utf-8', newline='\n')
    repoint('favl_pm5_size', c500)
    print('briefs', room, c500)


if __name__ == '__main__':
    main()
