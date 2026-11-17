"""Diagnose the WL-2 control vs .x3/augment.py base difference for GEN-FF."""
import numpy as np, pickle
from sklearn.ensemble import ExtraTreesRegressor
D = np.load('scratch/fable_architecture/.x3/extended.npz')
X, Y, E, ids = D['X'], D['Y'], D['E'], D['ids']
data, _ = pickle.load(open('scratch/fable_architecture/.e1/descriptors.pkl', 'rb'))
f = np.array(data[0][0]['f']); nf = len(f); band = np.where(f >= 600)[0]


def pack(x, y, scale, indices):
    fs = f[indices] / scale
    a = np.repeat(x[:, None, :] * scale, len(indices), axis=1)
    fq = np.broadcast_to(np.log(fs)[None, :, None], (len(x), len(indices), 1))
    Yc = np.stack([y[:, i * nf:(i + 1) * nf][:, indices] for i in range(3)], axis=2)
    return np.concatenate((a, fq), axis=2).reshape(-1, 28), Yc.reshape(-1, 3)


e = 'GEN-FF'
te = E == e
tr = (~te) & (~np.isin(ids, ids[te]))
xt, yt = pack(X[tr], Y[tr], 1, np.arange(nf))
xe, ye = pack(X[te], Y[te], 1, band)
m = ExtraTreesRegressor(n_estimators=40, min_samples_leaf=3, random_state=0, n_jobs=4,
                        max_features=1.0).fit(xt, yt)
p = m.predict(xe)
base = Y[tr, :54].reshape(-1, 3, nf)[:, :, band].mean(axis=0).T
base = np.tile(base, (int(te.sum()), 1))
print('augment.py code skills', [round(1 - np.sum((ye[:, i] - p[:, i]) ** 2) /
                                      np.sum((ye[:, i] - base[:, i]) ** 2), 4) for i in range(3)])
print('shapes', xt.shape, xe.shape, 'tr', tr.sum())
# now the same without the fq channel's extra constant path, using KREF broadcast
KREF = 2 * np.pi * 1000.0 / 343.0
a = np.concatenate([np.broadcast_to((X[tr][:, None, :] * KREF), (tr.sum(), nf, 27)),
                    np.broadcast_to(np.log(f)[None, :, None], (tr.sum(), nf, 1))], axis=2).reshape(-1, 28)
a2 = np.concatenate([np.broadcast_to((X[te][:, None, :] * KREF), (te.sum(), len(band), 27)),
                     np.broadcast_to(np.log(f)[band][None, :, None], (te.sum(), len(band), 1))], axis=2).reshape(-1, 28)
b = np.stack([Y[tr][:, i * nf:(i + 1) * nf] for i in range(3)], axis=2).reshape(-1, 3)
m2 = ExtraTreesRegressor(n_estimators=40, min_samples_leaf=3, random_state=0, n_jobs=4,
                         max_features=1.0).fit(a, b)
p2 = m2.predict(a2).reshape(int(te.sum()), len(band), 3)
P = np.zeros((int(te.sum()), 54)); B = np.zeros((int(te.sum()), 54))
bm = b.reshape(-1, nf, 3).mean(axis=0)
for i in range(3):
    P[np.ix_(np.arange(int(te.sum())), i * nf + band)] = p2[:, :, i]
    B[np.ix_(np.arange(int(te.sum())), i * nf + band)] = bm[band, i]
Yte = Y[te]
print('wl2 code skills', [round(1 - np.sum((Yte[:, i * nf + band] - P[:, i * nf + band]) ** 2) /
                                np.sum((Yte[:, i * nf + band] - B[:, i * nf + band]) ** 2), 4) for i in range(3)])
print('max abs feature diff', np.abs(xt - a).max(), 'pred diff', np.abs(p.reshape(int(te.sum()), len(band), 3) - p2).max())
