"""Read-only: inspect stored di/bw arrays and term arithmetic for one row."""
import pickle, pathlib, json
import numpy as np
REPO = pathlib.Path(r'C:\Users\hunte\Hrns\hornlab-search')
rows = [r for r in pickle.load(open(REPO / 'scratch/fable_architecture/.fable/rows.pkl', 'rb')) if r['ok']]
r = rows[0]
f = np.array(r['f'])
print('f', f)
print('di', r['di'])
print('bwh', r['bwh'])
print('bwv', r['bwv'])
band = f >= 700
print('band idx', np.where(band)[0], 'n', band.sum())
di = np.asarray(r['di'])[band]
print('di band', di)
for ref in (4.77, target if False else 0):
    pass
from hornlab_search.metrics.di import target_di_gaussian_db
for ref in (target_di_gaussian_db(80, 50), 4.77, float(np.mean(di))):
    print('ref', round(ref, 3), 'di term', np.mean((di - ref) ** 2) / 10)
print('terms di', r['terms']['di'])
e_h = np.asarray(r['bwh'])[band] - 80
e_v = np.asarray(r['bwv'])[band] - 50
print('e_h', e_h)
print('e_v', e_v)
print('mean side err2 /100 h', np.mean(np.where(e_h < 0, 2, 1) * e_h ** 2) / 100,
      'v', np.mean(np.where(e_v < 0, 2, 1) * e_v ** 2) / 100)
print('terms cov', r['terms']['cov'])
print('sum no weight', (np.mean(np.where(e_h < 0,2,1)*e_h**2)+np.mean(np.where(e_v<0,2,1)*e_v**2))/100)
