"""Readout for the CD variants of non-CD returned-lip horns (no solver calls).

Reuses ../cd_backbone_2026-11-25/analyze.py (load / summarize / check / deltas), i.e. the predeclared six rules,
each candidate against its own family's CD-brief control. Reads runs/nights/<night>/summary.jsonl for every night
listed in NIGHTS; writes results.json and curves.png.

    .venv\\Scripts\\python.exe docs/evidence/cd_variants_2026-11-25/analyze.py
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path.cwd()))
sys.path.insert(0, 'docs/evidence/cd_backbone_2026-11-25')
import analyze as A  # noqa: E402

HERE = Path('docs/evidence/cd_variants_2026-11-25')
NIGHTS = ['cd_variants_b1_2026-11-25', 'cd_variants_b2_2026-11-25', 'cd_variants_b3_2026-11-25']
FAMILIES = {'lcar': "Le Cleac'h AR + CD backbone", 'lcl': "Le Cleac'h H/V + CD backbone",
            'iwar': 'Iwata AR + CD backbone'}


def control_for(job):
    prefix = job.split('_')[0]
    return f'{prefix}_control_epw9' if job.endswith('_epw9') else f'{prefix}_control'


def main():
    jobs = A.jobs_from(NIGHTS)
    runs = {k: A.summarize(A.load(v['run'])) for k, v in jobs.items()}
    out = {'jobs': jobs, 'runs': runs, 'checks': {}, 'deltas_vs_control': {}}
    for k, r in runs.items():
        ctl = control_for(k)
        if k == ctl or ctl not in runs:
            continue
        c = A.check(k, r, runs[ctl])
        c['passes_all'] = all(c[x] for x in ('H_HF_all_ge_62', 'H_MID_all_65_85', 'V_HF_not_narrower',
                                              'no_multilobe', 'min_re_z_ok', 'J_ok'))
        out['checks'][k] = c
        out['deltas_vs_control'][k] = A.deltas(runs[ctl], r)
    (HERE / 'results.json').write_text(json.dumps(out, indent=1) + '\n', encoding='utf-8')
    for k in sorted(runs):
        r = runs[k]
        f = [round(x) for x in r['freqs']]
        g = lambda key, b: r[key][f.index(b)]  # noqa: E731
        print(f"{k:28s} J {r['J']:.3f} Re896 {g('re_z', 896):.3f} minRe {r['min_re_z_from_900']:.3f} DOF {r['n_dof']} "
              f"mid {[round(g('H', b), 1) for b in A.MID]} HF {[round(g('H', b), 1) for b in A.HF]} "
              f"V-HF {[round(g('V', b), 1) for b in A.HF]} lobes {r['multilobe_h']}/{r['multilobe_v']}")
    for k, c in out['checks'].items():
        print('CHECK', k, ' '.join(f'{a}={b}' for a, b in c.items()))
    figure(runs)


def figure(runs):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    prefixes = [p for p in FAMILIES if f'{p}_control' in runs]
    if not prefixes:
        return
    fig, axes = plt.subplots(2, len(prefixes), figsize=(5.2 * len(prefixes), 7.5), squeeze=False, sharey='row')
    for col, p in enumerate(prefixes):
        for row, plane in enumerate(('H', 'V')):
            ax = axes[row][col]
            lo, hi, f0 = A.CORR[plane]
            ax.axhspan(lo, hi, color='#dfe9f5', zorder=0)
            ax.axvspan(6000, 8000, color='#f5efe0', zorder=0)
            for k in sorted(x for x in runs if x.startswith(p + '_') and not x.endswith('_epw9')):
                r = runs[k]
                ctl = k == f'{p}_control'
                ax.semilogx(r['freqs'], r[plane], color='0.45' if ctl else None, lw=2.2 if ctl else 1.4,
                            label=k[len(p) + 1:])
            ax.set_xlim(500, 9000)
            ax.set_ylim(20, 140)
            ax.grid(True, which='both', alpha=0.3)
            ax.set_title(f'{FAMILIES[p]} — {plane}', fontsize=10)
            if col == 0:
                ax.set_ylabel(f'{plane} −6 dB width (deg)')
            if row == 1:
                ax.set_xlabel('Hz')
            ax.legend(fontsize=7)
    fig.suptitle('CD variants on room_landscape_80x50_900_hf1440_v11cd (simulated, 36 mm assumed source); '
                 'blue = corridor, tan = 6–8 kHz', fontsize=10)
    fig.tight_layout()
    fig.savefig(HERE / 'curves.png', dpi=130)


if __name__ == '__main__':
    main()
