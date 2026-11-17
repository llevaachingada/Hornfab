"""X4 completion: signed envelope and wall-gap margins for every sampled design.

Scans `.x4c/build` (65 x 61 contract-v2 records) and reports, per lane, the minimum signed
margin to the brief envelope (W <= 600 + 0.5, H <= 480 + 0.5, depth <= 480 + 15 mm) and the
minimum measured non-adjacent wall gap.  The gap limit (2 t + 2 mm) is a configured constraint
only on the grid route; native lanes have no configured gap limit, so their gap is reported
without a pass line.

Writes `.x4c/margins_sampled.json` and `.x4c/margins_sampled.txt`.
"""
import sys, json, pathlib
import numpy as np

sys.path.insert(0, 'scratch/fable_architecture/.n1')
sys.path.insert(0, '.')
from hornlab_search.design.generators import grid

ROOT = pathlib.Path('scratch/fable_architecture')
LIM = dict(W=600.0 + 0.5, H=480.0 + 0.5, D=480.0 + 15.0)


def box(inner, outer):
    pts = inner if outer is None or outer.size == 0 else np.vstack(
        [inner.reshape(-1, 3), outer.reshape(-1, 3)])
    return (2.0 * float(np.max(np.abs(pts[:, 0]))),
            2.0 * float(np.max(np.abs(pts[:, 1]))),
            float(np.ptp(pts[:, 2])))


def main():
    out = {}
    for f in sorted((ROOT / '.x4c/build').glob('*.npz')):
        z = np.load(f)
        lane = str(z['lane'])
        inner, outer = z['inner'], z['outer']
        t = float(z['wall_thickness_mm'] or 3.0)
        W, H, D = box(inner, outer)
        gap = grid.min_self_approach_mm(inner, None if outer.size == 0 else outer,
                                        limit_mm=2.0 * t + 2.0)
        rec = dict(h=str(z['design_hash']), mode=str(z['mode']), wall_thickness_mm=t,
                   W_mm=W, H_mm=H, D_mm=D,
                   W_margin=LIM['W'] - W, H_margin=LIM['H'] - H, D_margin=LIM['D'] - D,
                   gap_mm=float(gap), gap_limit_mm=2.0 * t + 2.0,
                   gap_margin=float(gap) - (2.0 * t + 2.0))
        out.setdefault(lane, []).append(rec)
    (ROOT / '.x4c/margins_sampled.json').write_text(json.dumps(out, indent=1))

    lines = []
    for lane, rs in out.items():
        lines.append('=' * 78)
        lines.append('%s  n=%d  route=%s' % (lane, len(rs), rs[0]['mode']))
        for ax in ('W', 'H', 'D'):
            r = min(rs, key=lambda x: x[ax + '_margin'])
            lines.append('  min %s margin %+.2f mm (%s: %.2f mm)' %
                         (ax, r[ax + '_margin'], r['h'], r[ax + '_mm']))
        r = min(rs, key=lambda x: x['gap_margin'])
        lines.append('  min gap %.2f mm (limit %.2f, margin %+.2f) at %s' %
                     (r['gap_mm'], r['gap_limit_mm'], r['gap_margin'], r['h']))
    (ROOT / '.x4c/margins_sampled.txt').write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
