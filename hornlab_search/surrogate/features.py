"""Design vector -> model input. Baseline encoding only: the unit-cube vector of
``DesignSpace.normalize`` (already ``[0,1]^k``, alphabetical). Anything fancier must beat it."""
from __future__ import annotations

import numpy as np


def unit_matrix(X: np.ndarray, key_names: list[str], space) -> np.ndarray:
    """Raw parameter matrix (n, len(key_names)) from ``to_training_arrays`` -> (n, k) in [0,1]
    for ``space.keys()``. Raises if a searchable key is missing; clips like ``Bound.to_unit``."""
    cols = {k: i for i, k in enumerate(key_names)}
    keys = space.keys()
    missing = [k for k in keys if k not in cols]
    if missing:
        raise KeyError(f"training arrays lack searchable keys {missing}; pass keys=space.keys() "
                       "to to_training_arrays")
    U = np.empty((X.shape[0], len(keys)), dtype=np.float32)
    for j, k in enumerate(keys):
        b = space.bounds[k]
        U[:, j] = [b.to_unit(float(v))[0] if np.isfinite(v) else 0.5 for v in X[:, cols[k]]]
    return U


def cluster_holdout(U: np.ndarray, frac: float = 0.15, n_clusters: int = 40,
                    seed: int = 0) -> np.ndarray:
    """Boolean mask of held-out rows. Whole clusters (nearest of random centres) are held out so
    test designs are not near neighbours of training designs (plan section 4)."""
    rng = np.random.default_rng(seed)
    n = len(U)
    m = min(n_clusters, max(2, n // 5))
    centres = U[rng.choice(n, size=m, replace=False)]
    lab = np.argmin(((U[:, None, :] - centres[None]) ** 2).sum(-1), axis=1)
    order = rng.permutation(m)
    held = np.zeros(n, bool)
    for c in order:
        if held.sum() >= frac * n:
            break
        held |= lab == c
    return held
