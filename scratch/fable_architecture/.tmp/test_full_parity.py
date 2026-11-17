import sys, json, pathlib, numpy as np
sys.path.insert(0, r'C:\Users\hunte\Hrns\hornlab-search\scratch\fable_architecture\.tmp')
import fable_replay_harness as H
from hornlab_search.objective.scalar_v7 import V7Params, resolve_v7_weights, objective_v7

worst = 0.0
n = 0
for S in sorted(H.REPO.glob('runs/study-*')):
    sd, vd = S/'screen', S/'verify'
    if not (sd/'designs').is_dir() or not (vd/'designs').is_dir():
        continue
    bs = H.brief(sd/'config.yaml'); bv = H.brief(vd/'config.yaml')
    for h in sorted({p.name for p in (sd/'designs').iterdir() if p.is_dir()} &
                    {p.name for p in (vd/'designs').iterdir() if p.is_dir()}):
        for rd, bh in ((sd, bs), (vd, bv)):
            d = rd/'designs'/h
            st = H.json_load(d/'status.json')
            if not st.get('ok'):
                continue
            resp = H.load_response(d/'response.npz')
            m = H.metrics_parity(resp, bh.target)
            j, _ = objective_v7(m, resp, True, bh.target, bh.weights, bh.objective_params)
            delta = abs(j - float(st['objective']))
            worst = max(worst, delta); n += 1
            if delta > 1e-6:
                print('PARITY MISS', S.name, h, 'stored', st['objective'], 'regen', j, 'delta', delta)
print('n', n, 'worst |regen J - stored J|', worst)
