"""A7 shared definitions. Read-only CPU analysis.

Split definitions are copied verbatim from scratch/fable_architecture/.x3/strict.py.
Nothing here widens a split or changes a pass line.
"""
import numpy as np, pickle, re, sys

ROOT = 'scratch/fable_architecture'

# Replay rule: never score with plain compute_metrics.  This analysis uses only the stored
# archived curves (no metric is regenerated), so the parity harness is imported to keep the
# rule's import in force but no score is computed from a response here.
sys.path.insert(0, f'{ROOT}/.tmp')
import fable_replay_harness as H  # noqa: F401


def load_base():
    D = np.load(f'{ROOT}/.x3/extended.npz', allow_pickle=True)
    X, Y, G, E = D['X'], D['Y'], D['G'], D['E']
    ids = [str(h) for h in D['ids']]
    rows = pickle.load(open(f'{ROOT}/.fable/rows.pkl', 'rb'))
    f = np.array(next(r['f'] for r in rows if r['ok'] and r['f'] and len(r['f']) == 18), float)
    return X, Y, G, E, ids, rows, f


def sibling(g):
    """Verbatim from .x3/strict.py."""
    g = re.sub(r'_v\d+$', '', g).replace('_smooth', '')
    if g.startswith('sp__'):
        return 'sp__control_moderate_strong'
    if g.startswith('rr__pucker') or g == 'rr__reference':
        return 'rr__reference_pucker'
    if g.startswith('klangfilm_hv__a'):
        return 'klangfilm_hv__axis_variants'
    return g


def cov(y, band, nf=18):
    """Verbatim asymmetric 80x50 coverage proxy from .x3/strict.py (H block, V block)."""
    a = y[:, band]
    b = y[:, nf + band]
    return (np.mean(np.where(a < 80, 2, 1) * (a - 80) ** 2, axis=1) / 100
            + .5 * np.mean(np.where(b < 50, 2, 1) * (b - 50) ** 2, axis=1) / 100)


def skills(Y, P, B, band, nf=18, ntargets=3):
    out = []
    for k in range(ntargets):
        num = np.sum((Y[:, k * nf + band] - P[:, k * nf + band]) ** 2)
        den = np.sum((Y[:, k * nf + band] - B[:, k * nf + band]) ** 2)
        out.append(1 - num / den)
    return out
