"""N1b: lecleach lane reproducibility check.

The six contract lanes plus lecleach (needed for N4) were built at HEAD from their stored
recipes. For lecleach the stored mesh and the HEAD generator disagree by hundreds of
millimetres, so Test 2/3 cannot be applied. This records the disagreement per design:
mesh used-node box vs the generator's native box at the run's own brief (brief_hash checked).
Writes .n1b/lecleach_box.json.
"""
import sys, json, pathlib, numpy as np

sys.path.insert(0, 'scratch/fable_architecture/.n1'); sys.path.insert(0, '.')
import analyze as A

ROOT = pathlib.Path('scratch/fable_architecture')
LANE = 'hl__lecleach_hv_landscape_smooth_v7'


def ext(p):
    p = np.asarray(p, float).reshape(-1, 3)
    return np.array([2 * np.abs(p[:, 0]).max(), 2 * np.abs(p[:, 1]).max(), np.ptp(p[:, 2])])


out = []
for f in sorted((ROOT / '.n1b/build').glob('*.npz')):
    z = np.load(f)
    if str(z['lane']) != LANE:
        continue
    h, run = str(z['design_hash']), str(z['run'])
    xyz, t1, t2, ents = A.read_msh(pathlib.Path('runs') / run / 'designs' / h / 'mesh.msh')
    gen = ext(z['inner_native'])
    mesh = ext(xyz)
    out.append(dict(h=h, run=run, generator=gen.tolist(), mesh=mesh.tolist(),
                    delta=(gen - mesh).tolist(), native_shape=list(np.shape(z['inner_native']))))
    print(h, 'generator', np.round(gen, 1), 'mesh', np.round(mesh, 1),
          'delta', np.round(gen - mesh, 1), flush=True)
d = np.array([x['delta'] for x in out])
print('\nlecleach: %d designs; |W delta| %.0f..%.0f mm, |H| %.0f..%.0f, |D| %.0f..%.0f' %
      (len(out), np.abs(d[:, 0]).min(), np.abs(d[:, 0]).max(),
       np.abs(d[:, 1]).min(), np.abs(d[:, 1]).max(), np.abs(d[:, 2]).min(), np.abs(d[:, 2]).max()))
json.dump(out, open(ROOT / '.n1b/lecleach_box.json', 'w'), indent=1)
