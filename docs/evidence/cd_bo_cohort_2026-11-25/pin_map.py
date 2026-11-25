"""Pin map of the cohort campaigns (no solver): for each searched knob, how many of the top-10 designs sit within
3 % of the search box at the low / high side. Read with KERNEL_LIMITS to tell a search-box pin (widen) from a
family-law pin (cannot widen without a new construction).

    .venv\Scripts\python.exe docs/evidence/cd_bo_cohort_2026-11-25/pin_map.py
"""
import json
from pathlib import Path

NIGHT = Path('runs/nights/cd_bo_cohort_2026-11-25/summary.jsonl')
# Known law/kernel limits of the searched knobs (from the kernels' validators); None = no hard limit known.
KERNEL_LIMITS = {
    'g_depth_h_ratio': (0.5, 1.2), 'g_bb_h': (0.0, 1.0), 'g_bb_v': (0.0, 1.0), 'g_bb_throat_frac': (0.05, 0.30),
    'g_bb_rollin_frac': (0.15, 0.45), 'g_inward_h_mm': (0.0, '15% height'), 'g_inward_v_mm': (0.0, '15% height'),
    'g_axial_h_mm': ('-10% depth', '10% depth'), 'g_axial_v_mm': ('-10% depth', '10% depth'),
    'g_terminal_deg': ('>180', 280.0), 'g_rb_h_mm': (-60.0, 60.0), 'g_rb_v_mm': (-60.0, 60.0),
    'g_rb_d_mm': (-30.0, 30.0), 'g_rb_start_frac': (0.30, 0.90),
}


def main(top=10, tol=0.03):
    out = {}
    for line in NIGHT.read_text(encoding='utf-8').splitlines():
        job = json.loads(line)
        run = Path(job['run_dir'])
        cfg = json.loads((run / 'run.json').read_text(encoding='utf-8'))['config']
        bounds = {k: b for k, b in cfg['bounds'].items() if b.get('search', True) and b['lo'] != b['hi']}
        rows = [json.loads(x) for x in (run / 'search.ndjson').read_text(encoding='utf-8').splitlines() if x.strip()]
        rows = sorted((r for r in rows if r.get('ok')), key=lambda r: r['objective'])[:top]
        pins = {}
        for k, b in bounds.items():
            span = b['hi'] - b['lo']
            vals = [r['params']['grid']['knobs'][k] for r in rows]
            lo = sum(v <= b['lo'] + tol * span for v in vals)
            hi = sum(v >= b['hi'] - tol * span for v in vals)
            if lo or hi:
                pins[k] = {'box': [b['lo'], b['hi']], 'n_low': lo, 'n_high': hi, 'kernel': KERNEL_LIMITS.get(k),
                           'top_median': sorted(vals)[len(vals) // 2]}
        out[job['id']] = {'valid': len(rows), 'best_J': job.get('best_J'), 'pins': pins}
        print(f"\n{job['id']}  best J {job.get('best_J'):.3f}  (top {len(rows)})")
        for k, p in sorted(pins.items(), key=lambda kv: -(kv[1]['n_low'] + kv[1]['n_high'])):
            print(f"   {k:22s} box {p['box']}  low {p['n_low']:2d}  high {p['n_high']:2d}  median {p['top_median']:.3g}  kernel {p['kernel']}")
    Path('docs/evidence/cd_bo_cohort_2026-11-25/pin_map.json').write_text(json.dumps(out, indent=1) + '\n',
                                                                         encoding='utf-8')


if __name__ == '__main__':
    main()
