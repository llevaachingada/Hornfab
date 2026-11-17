"""P1: rebuild the 27-number shape descriptor for EVERY valid stored row (read-only).

Same descriptor as .fable/an3.py (12-bin H/V wall profiles + bounding size), but applied to all
3,414 valid rows rather than a 70-per-lane sample.  Cache: .p1/desc_all.npz keyed by row order.
"""
import pathlib, pickle, time, sys
import numpy as np

REPO = pathlib.Path(r'C:\Users\hunte\Hrns\hornlab-search')
OUT = REPO / 'scratch/fable_architecture/.p1/desc_all.npz'
NS = 12


def desc(path):
    txt = pathlib.Path(path).read_text()
    a = txt.index('$Nodes') + 7
    b = txt.index('$EndNodes')
    lines = txt[a:b].split('\n', 1)
    nd = np.array(lines[1].split(), float).reshape(-1, 4)[:, 1:] * 1000.0
    e0 = txt.index('$Elements') + 10
    e1 = txt.index('$EndElements')
    el = txt[e0:e1].split('\n')[1:]
    wall = set()
    for ln in el:
        p = ln.split()
        if len(p) >= 8 and p[1] == '2' and p[3] == '1':
            wall.update((int(p[-3]) - 1, int(p[-2]) - 1, int(p[-1]) - 1))
    w = nd[sorted(wall)]
    zmax = w[:, 2].max()
    tol = max(1.0, 0.004 * zmax)
    out = []
    for ax, other in ((0, 1), (1, 0)):
        pl = w[np.abs(w[:, other]) < tol]
        prof = []
        for i in range(NS):
            lo, hi = zmax * i / NS, zmax * (i + 1) / NS
            m = (pl[:, 2] >= lo) & (pl[:, 2] < hi) & (pl[:, ax] > 1.0)
            prof.append(pl[m, ax].min() if m.any() else np.nan)
        prof = np.array(prof)
        ok = np.isfinite(prof)
        if ok.sum() < 3:
            return None
        prof = np.interp(np.arange(NS), np.arange(NS)[ok], prof[ok])
        out.append(prof)
    return np.concatenate([[zmax, w[:, 0].max(), w[:, 1].max()], out[0], out[1]])


rows = [r for r in pickle.load(open(REPO / 'scratch/fable_architecture/.fable/rows.pkl', 'rb'))
        if r['ok'] and r['f'] and len(r['f']) == 18]
print('valid rows', len(rows), flush=True)
X = np.full((len(rows), 27), np.nan)
keep = np.zeros(len(rows), bool)
t0 = time.time()
for i, r in enumerate(rows):
    p = REPO / 'runs' / r['run'] / 'designs' / r['h'] / 'mesh.msh'
    if not p.is_file():
        continue
    try:
        d = desc(p)
    except Exception:
        d = None
    if d is None:
        continue
    X[i] = d
    keep[i] = True
    if (i + 1) % 400 == 0:
        print(i + 1, 'rows', round(time.time() - t0, 1), 's', flush=True)
np.savez_compressed(OUT, X=X, keep=keep)
print('done', keep.sum(), 'of', len(rows), 'in', round(time.time() - t0, 1), 's', flush=True)
