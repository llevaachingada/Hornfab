import json
import numpy as np
from sklearn.decomposition import PCA
from sklearn.neighbors import NearestNeighbors

d = np.load('scratch/fable_architecture/.fable/desc.npz')
X, Y, G = d['X'], d['Y'], d['G']
# Eight profile modes and depth; six response modes. Standardization defines
# the metric for both the neighbor search and the Jacobian condition number.
xp = PCA(n_components=8).fit_transform(X[:, 3:])
x = np.column_stack((X[:, 0], xp))
x = (x - x.mean(0)) / x.std(0)
yp = PCA(n_components=6).fit(Y)
y = yp.transform(Y)
y = (y - y.mean(0)) / y.std(0)
n = len(x)
nn = NearestNeighbors(n_neighbors=53).fit(x)
dist, ix = nn.kneighbors(x)
out = []
weak = []
row_norms = []
for i in range(n):
    # Exclude the centre and its held-out nearest distinct neighbor from fit.
    candidates = [j for j in ix[i, 1:] if np.linalg.norm(x[j]-x[i]) > 1e-8]
    if len(candidates) < 40: continue
    target = candidates[0]
    tr = np.array(candidates[1:41])
    dx, dy = x[tr] - x[i], y[tr] - y[i]
    J = np.linalg.lstsq(dx, dy, rcond=None)[0].T
    u, s, _ = np.linalg.svd(J, full_matrices=False)
    weak.append(np.abs(u[:, -1]))
    row_norms.append(np.linalg.norm(J, axis=1))
    actual = y[target]-y[i]
    pred = J @ (x[target]-x[i])
    inv = np.linalg.pinv(J, rcond=1e-8) @ actual
    true = x[target]-x[i]
    out.append([np.linalg.norm(actual-pred), np.linalg.norm(actual),
                np.linalg.norm(inv-true), np.linalg.norm(true),
                s[0]/s[-1] if s[-1] > 1e-12 else np.inf,
                *s, np.linalg.norm(J@inv-actual),
                np.linalg.matrix_rank(dx), int(G[target] == G[i])])
a=np.array(out)
def q(z): return np.quantile(z,[.1,.25,.5,.75,.9]).tolist()
result={'n':n,'usable':len(a),'lanes':len(set(G)),
 'shape_variance_8':float(PCA(n_components=8).fit(X[:,3:]).explained_variance_ratio_.sum()),
 'response_variance_6':float(yp.explained_variance_ratio_.sum()),
 'forward_error_norm_quantiles':q(a[:,0]), 'response_delta_norm_quantiles':q(a[:,1]),
 'forward_relative_error_quantiles':q(a[:,0]/np.maximum(a[:,1],1e-12)),
 'forward_skill_vs_no_change':float(1-np.sum(a[:,0]**2)/np.sum(a[:,1]**2)),
 'inverse_error_norm_quantiles':q(a[:,2]), 'geometry_delta_norm_quantiles':q(a[:,3]),
 'inverse_relative_error_quantiles':q(a[:,2]/np.maximum(a[:,3],1e-12)),
 'inverse_skill_vs_no_change':float(1-np.sum(a[:,2]**2)/np.sum(a[:,3]**2)),
 'condition_quantiles':q(a[:,4]), 'singular_value_medians':np.median(a[:,5:11],axis=0).tolist(),
 'weak_direction_abs_pc_loadings_median':np.median(weak,axis=0).tolist(),
 'response_pc_row_norm_median':np.median(row_norms,axis=0).tolist(),
 'inverse_response_residual_quantiles':q(a[:,11]), 'local_design_rank_counts':dict(zip(*[v.tolist() for v in np.unique(a[:,12],return_counts=True)])),
 'same_lane_fraction':float(np.mean(a[:,13]))}
print(json.dumps(result, indent=2))
