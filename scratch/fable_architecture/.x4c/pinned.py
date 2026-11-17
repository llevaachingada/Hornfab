"""X4 completion: top-decile bound concentration (pinned-at-edge evidence).

For each lane, over all ok stored designs: take the top decile by stored J (lower is better), and
for every searched knob report the fraction of those designs whose value lies within 3 % of the
knob's bound range of lo or hi.  Also report the minimum signed envelope margin among the same
top-decile designs from the stored mesh bounding box, so an edge concentration can be separated
from a real constraint.

No pass line is invented: the brief does not define how large "top-decile mass" must be, so the
masses are reported and only flagged at >= 0.50 (naming that threshold as a reporting choice).
Writes `.x4c/pinned.json` and `.x4c/pinned.txt`.
"""
import sys, json, pickle, pathlib
import numpy as np

ROOT = pathlib.Path('scratch/fable_architecture')
LANES = ['hl__osse_rrect_fold_warm_v7', 'hl__ext_throat_hvlaw_v7',
         'hl__ath_tritonia_landscape_v9', 'hl__crowe_x_osse_cd_v7',
         'hl__biradial_es_style_v7']
LIM = dict(W=600.5, H=480.5, D=495.0)


def knob_value(r, k):
    if r.get('knobs'):
        return r['knobs'].get(k)
    return (r.get('params') or {}).get(k)


def main():
    rows = pickle.load(open(ROOT / '.fable/rows.pkl', 'rb'))
    out = {}
    for lane in LANES:
        rs = [r for r in rows if r['ok'] and r['config'] == lane and r.get('J') is not None]
        J = np.array([float(r['J']) for r in rs])
        thr = float(np.quantile(J, 0.10))
        top = [r for r, j in zip(rs, J) if j <= thr]
        bounds = rs[0]['bounds'] if rs else {}
        knobs = []
        for k, b in bounds.items():
            if not (isinstance(b, dict) and b.get('search', True)
                    and isinstance(b.get('lo'), (int, float))
                    and isinstance(b.get('hi'), (int, float)) and b['hi'] > b['lo']):
                continue
            vals = [knob_value(r, k) for r in top]
            vals = [float(v) for v in vals if isinstance(v, (int, float))]
            if not vals:
                continue
            span = float(b['hi']) - float(b['lo'])
            near_lo = sum(1 for v in vals if v - b['lo'] <= 0.03 * span) / len(vals)
            near_hi = sum(1 for v in vals if b['hi'] - v <= 0.03 * span) / len(vals)
            knobs.append(dict(knob=k, lo=b['lo'], hi=b['hi'], n=len(vals),
                              top_decile_near_lo=near_lo, top_decile_near_hi=near_hi,
                              top_decile_edge=near_lo + near_hi))
        # constraint margins from stored mesh bbox in metres
        margins = []
        for r in top:
            b = r.get('bbox')
            if not b:
                continue
            W = 2.0 * (b[3] - b[0]) * 1000.0
            H = 2.0 * (b[4] - b[1]) * 1000.0
            D = (b[5] - b[2]) * 1000.0
            margins.append(dict(h=r['h'], W_margin=LIM['W'] - W, H_margin=LIM['H'] - H,
                                D_margin=LIM['D'] - D))
        out[lane] = dict(top_decile_threshold_J=thr, n=len(rs), n_top=len(top),
                         knobs=knobs,
                         constraint_margins=dict(
                             W=min((m['W_margin'] for m in margins), default=None),
                             H=min((m['H_margin'] for m in margins), default=None),
                             D=min((m['D_margin'] for m in margins), default=None)))
    (ROOT / '.x4c/pinned.json').write_text(json.dumps(out, indent=1))

    lines = []
    for lane, v in out.items():
        lines.append('=' * 78)
        lines.append('%s  n=%d  top decile J <= %.4f (n=%d)' %
                     (lane, v['n'], v['top_decile_threshold_J'], v['n_top']))
        lines.append('  top-decile min envelope margins: W %+.2f  H %+.2f  D %+.2f mm' %
                     (v['constraint_margins']['W'], v['constraint_margins']['H'],
                      v['constraint_margins']['D']))
        for k in sorted(v['knobs'], key=lambda x: -x['top_decile_edge']):
            if k['top_decile_edge'] >= 0.50:
                lines.append('  %-28s edge mass %.2f (lo %.2f hi %.2f)' %
                             (k['knob'], k['top_decile_edge'],
                              k['top_decile_near_lo'], k['top_decile_near_hi']))
    (ROOT / '.x4c/pinned.txt').write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
