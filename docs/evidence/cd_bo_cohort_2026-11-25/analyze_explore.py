"""Stage 2 of the exploration plan: which knob controls which acoustic result (CPU, no solver).

For every family's exploration cohort (all runs ``<family>_r<i>`` of the night, pooled; each run = one independent
group), each valid screen row gives knobs (normalised to the family box, [0, 1]) and acoustic outcomes read from the
row's stored response:

  H_hf      mean H -6 dB width at 6.2 / 8 kHz          V_hf    mean V width at 6.2 / 8 kHz
  H_mid     mean H width 2.27-4.26 kHz                  H_mid_min  min H width 2.27-4.26 kHz (waistband)
  V_mid     mean V width 1.07-4.26 kHz                  DI_mean, DI_slope (scalars)
  load      min Re(z) from the crossover (J term rez_min_from_fx)
  ripple    ripple_mean_db                               J and every J term

Per outcome: an ExtraTrees model with GROUP-held-out validation (leave-one-run-out); permutation importance of each
knob on the held-out folds; Spearman rho for the direction. An outcome whose held-out R^2 does not beat 0 (the
mean-baseline) gets NO attribution (reported as "not learnable from this cohort"), per bo-study-v1.1. This is an
association over the explored box, not a causal proof; partial-dependence checks and targeted A/B solves confirm.

    .venv\\Scripts\\python.exe docs/evidence/cd_bo_cohort_2026-11-25/analyze_explore.py --night cd_bo_cohort_2026-11-25
"""
import argparse
import json
import re
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.inspection import permutation_importance
from sklearn.metrics import r2_score
from sklearn.model_selection import LeaveOneGroupOut

HERE = Path(__file__).resolve().parent
HF, MID, VMID = (6000, 8100), (2200, 4300), (1000, 4300)
TERMS = ('cov_profile', 'rip', 'flat', 'load', 'dislope', 'di_roughness', 'flat_cv', 'diag', 'distd', 'cd_lw',
         'cd_di_std', 'cd_nacc', 'offaxis_smooth')


def band(freqs, vals, lo_hi, fn=np.mean):
    f = np.asarray(freqs)
    v = np.asarray(vals, dtype=float)
    sel = (f >= lo_hi[0]) & (f <= lo_hi[1]) & np.isfinite(v)
    return float(fn(v[sel])) if sel.any() else np.nan


def outcomes(row):
    m, t = row['metrics'], row.get('terms') or {}
    f = m['freqs_hz']
    out = {'H_hf': band(f, m['bw_h_deg'], HF), 'V_hf': band(f, m['bw_v_deg'], HF),
           'H_mid': band(f, m['bw_h_deg'], MID), 'H_mid_min': band(f, m['bw_h_deg'], MID, np.min),
           'V_mid': band(f, m['bw_v_deg'], VMID), 'DI_mean': m['scalars'].get('di_mean_db'),
           'DI_slope': m['scalars'].get('di_slope_db_per_dec'), 'load': t.get('rez_min_from_fx'),
           'ripple': m['scalars'].get('ripple_mean_db'), 'J': row['objective']}
    out.update({f'J_{k}': t.get(k) for k in TERMS if k in t})
    return {k: (float(v) if v is not None else np.nan) for k, v in out.items()}


def knobs_of(row):
    p = row['params']
    return p['grid']['knobs'] if isinstance(p.get('grid'), dict) else p


def load_family(night):
    fams = {}
    for line in (Path('runs/nights') / night / 'summary.jsonl').read_text(encoding='utf-8').splitlines():
        job = json.loads(line)
        m = re.fullmatch(r'(.+)_r(\d+)', job['id'])
        if not m or not job.get('run_dir') or not (Path(job['run_dir']) / 'search.ndjson').exists():
            continue
        run = Path(job['run_dir'])
        cfg = json.loads((run / 'run.json').read_text(encoding='utf-8'))['config']
        box = {k: (b['lo'], b['hi']) for k, b in cfg['bounds'].items() if b.get('search', True) and b['lo'] != b['hi']}
        fam = fams.setdefault(m.group(1), {'box': box, 'rows': []})
        if fam['box'] != box:
            raise SystemExit(f'{job["id"]}: search box differs from its family (identity split)')
        seen = {r[2] for r in fam['rows']}
        for x in (run / 'search.ndjson').read_text(encoding='utf-8').splitlines():
            if not x.strip():
                continue
            r = json.loads(x)
            if not r.get('ok') or r.get('metrics') is None or r['design_hash'] in seen:
                continue
            seen.add(r['design_hash'])
            fam['rows'].append((job['id'], knobs_of(r), r['design_hash'], outcomes(r)))
    return fams


def analyse(fam, data, min_rows=60):
    keys = sorted(data['box'])
    X = np.array([[(float(k[key]) - data['box'][key][0]) / (data['box'][key][1] - data['box'][key][0])
                   for key in keys] for _g, k, _h, _o in data['rows']])
    groups = np.array([g for g, *_ in data['rows']])
    names = sorted(data['rows'][0][3])
    res = {'n_rows': len(X), 'n_groups': int(len(set(groups))), 'knobs': keys, 'outcomes': {}}
    if len(X) < min_rows or len(set(groups)) < 3:
        res['status'] = f'insufficient: {len(X)} rows / {len(set(groups))} groups (need >= {min_rows} / 3)'
        return res
    for name in names:
        y = np.array([o[name] for *_x, o in data['rows']])
        ok = np.isfinite(y)
        if ok.sum() < min_rows or np.nanstd(y) == 0:
            continue
        Xo, yo, go = X[ok], y[ok], groups[ok]
        pred, imps = np.full_like(yo, np.nan), []
        for tr, te in LeaveOneGroupOut().split(Xo, yo, go):
            model = ExtraTreesRegressor(n_estimators=300, min_samples_leaf=3, random_state=0).fit(Xo[tr], yo[tr])
            pred[te] = model.predict(Xo[te])
            if len(te) >= 8:
                imps.append(permutation_importance(model, Xo[te], yo[te], n_repeats=5, random_state=0)
                            .importances_mean)
        r2 = float(r2_score(yo, pred))
        entry = {'heldout_r2': round(r2, 3), 'n': int(ok.sum()), 'range': [float(np.min(yo)), float(np.max(yo))]}
        if r2 > 0.0 and imps:
            imp = np.mean(imps, axis=0)
            rho = [spearmanr(Xo[:, i], yo).statistic for i in range(len(keys))]
            order = np.argsort(-imp)
            entry['top'] = [{'knob': keys[i], 'importance': round(float(imp[i]), 4),
                             'rho': round(float(rho[i]), 3)} for i in order[:5] if imp[i] > 0]
        else:
            entry['top'] = 'not learnable from this cohort (held-out R^2 <= 0)'
        res['outcomes'][name] = entry
    res['status'] = 'ok'
    return res


def report_md(results):
    lines = ['# Which knob controls what (exploration cohorts, screen fidelity)', '',
             'Association over each family\'s explored box (leave-one-run-out ExtraTrees, permutation importance, '
             'Spearman direction). Not a causal proof; held-out R^2 <= 0 means no attribution.', '']
    for fam, res in results.items():
        lines += [f'## {fam}', '', f"{res['n_rows']} unique valid designs, {res['n_groups']} independent runs, "
                                   f"{len(res['knobs'])} knobs. {res['status']}", '']
        if res['status'] != 'ok':
            continue
        lines += ['| outcome | held-out R² | top knobs (importance, direction) |', '|---|---:|---|']
        for name, e in res['outcomes'].items():
            top = e['top'] if isinstance(e['top'], str) else ', '.join(
                f"`{t['knob']}` {t['importance']:.3g} ({'+' if t['rho'] > 0 else '−'})" for t in e['top'][:4])
            lines.append(f"| {name} | {e['heldout_r2']:.2f} | {top} |")
        lines.append('')
    return '\n'.join(lines) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--night', required=True)
    args = ap.parse_args()
    results = {fam: analyse(fam, data) for fam, data in sorted(load_family(args.night).items())}
    (HERE / 'knob_effects.json').write_text(json.dumps(results, indent=1) + '\n', encoding='utf-8')
    (HERE / 'KNOB_EFFECTS.md').write_text(report_md(results), encoding='utf-8')
    for fam, res in results.items():
        print(fam, res['n_rows'], 'rows', res['n_groups'], 'groups', res['status'])


if __name__ == '__main__':
    main()
