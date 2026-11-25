"""Matched readout of the CD-backbone fixed candidates against their controls. No solver calls.

    .venv\\Scripts\\python.exe docs/evidence/cd_backbone_2026-11-25/analyze.py [--no-fig]

Reads the batch nights' summary.jsonl (job id -> run dir), the control verifies, and the saved
metrics/response files. Writes results.json and PNG figures next to this script. Widths are full
-6 dB widths at the saved verify frequencies; the diagonal width comes from the 1024-point balloon
(directions within 6 deg of the 45-deg azimuth plane, any quadrant), so it is coarser than the
2.5-deg H/V cuts.

Controls are the neutral adapters for this batch, whose meshes are byte-for-byte the saved verify
meshes (neutral_parity.json): rolled anchor `fa5b207bca6d` and `lame_morph_040` (`g_morph_frac` 0.40).
"""
import argparse, glob, json, sys
from pathlib import Path

import matplotlib
import matplotlib.ticker
import numpy as np

sys.path.insert(0, str(Path.cwd()))
HERE = Path('docs/evidence/cd_backbone_2026-11-25')
PRIOR_DIR = Path('docs/evidence/directivity_attribution_2026-11-24')
CFG_DIR = Path('examples/typologies/cd_backbone_2026-11-25')
NIGHT = 'cd_backbone_2026-11-25'
NIGHT_B2 = 'cd_backbone_b2_2026-11-25'
NIGHT_B3 = 'cd_backbone_b3_2026-11-25'
NIGHT_B4 = 'cd_backbone_b4_2026-11-25'
NIGHT_B5 = 'cd_backbone_b5_2026-11-25'
NIGHT_B6 = 'cd_backbone_b6_2026-11-25'
CONTROLS = {'rolled': 'runs/rolled_lame_anchor_verify_2026-11-24/rolled',
            'lame': 'runs/20261124T235357Z-verify-dd210e'}
CONTROL_EPW9 = {'rolled': 'rolled_anchor_epw9', 'lame': 'lame_morph_040_epw9'}
EPW9_PAIRS = {'rolled': [('rolled_bb_h050', 'rolled_bb_h050_epw9'),
                         ('rolled_bb_h065_th025', 'rolled_bb_h065_th025_epw9')], 'lame': []}
HF = [6085, 6325, 6977, 7113, 8000]
MID = [2037, 2335, 2678, 3070, 3520, 4037]
CORR = {'H': (60.0, 90.0, 900.0), 'V': (40.0, 60.0, 1000.0)}
COLORS = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#6250d6', '#e34948']
B4 = ('rolled_bb_h065_th025_epw9', 'rolled_bb_h050_th025', 'rolled_bb_h065_th025', 'rolled_bb_h065_th030', 'rolled_bb_h065_ri022',
      'rolled_bb_h065_ri038', 'rolled_bb_h080_th030')
GRAY = '#52514e'
LABELS = {
    'rolled': [('rolled_bb_control', 'control'), ('rolled_bb_h035', 'bb_h 0.35'),
               ('rolled_bb_h045', 'bb_h 0.45'), ('rolled_bb_h050', 'bb_h 0.5'),
               ('rolled_bb_h065', 'bb_h 0.65'), ('rolled_bb_h100', 'bb_h 1.0'),
               ('rolled_bb_h050_epw9', 'bb_h 0.5, epw 9'),
               ('rolled_bb_h050_th025', 'bb_h 0.5, throat 0.25'), ('rolled_bb_h065_th025', 'bb_h 0.65, throat 0.25'),
               ('rolled_bb_h065_th030', 'bb_h 0.65, throat 0.30'), ('rolled_bb_h065_ri022', 'bb_h 0.65, roll-in 0.22'),
               ('rolled_bb_h065_ri038', 'bb_h 0.65, roll-in 0.38'), ('rolled_bb_h080_th030', 'bb_h 0.8, throat 0.30'),
               ('rolled_bb_h065_th025_epw9', 'bb_h 0.65, throat 0.25, epw 9')],
    'lame': [('lame_bb_control_m040', 'control (m0.40)'), ('lame_bb_h050_m040', 'bb_h 0.5'),
             ('lame_bb_h100_m040', 'bb_h 1.0'),
             ('lame_bb_h100_m040_t25_r20', 'bb_h 1.0, t0.25 r0.20'), ('lame_bb_h100_m040_t25_r15', 'bb_h 1.0, t0.25 r0.15'),
             ('lame_bb_h075_m040_t25_r20', 'bb_h 0.75, t0.25 r0.20'), ('lame_bb_h100_m040_t30_r15', 'bb_h 1.0, t0.30 r0.15')],
}


def family_of(job_id):
    return 'rolled' if job_id.startswith('rolled') else 'lame' if job_id.startswith('lame') else None


def design_dir(run):
    return Path(glob.glob(f'{run}/designs/*/')[0])


def load(run):
    d = design_dir(run)
    m = json.loads((d / 'metrics.json').read_text(encoding='utf-8'))
    z = np.load(d / 'response.npz', allow_pickle=True)
    best = Path(run) / 'best.json'
    if best.exists():
        b = json.loads(best.read_text(encoding='utf-8'))
        J, terms = b['objective'], b.get('terms', {})
    else:                                     # anchor dirs carry only search.ndjson
        row = [json.loads(x) for x in (Path(run) / 'search.ndjson').read_text(encoding='utf-8').splitlines() if x.strip()][-1]
        J, terms = row.get('objective'), row.get('terms', {})
    return {'run': str(run), 'design': d.name, 'm': m, 'z': z, 'J': J, 'terms': terms}


def width(angles, spl, ref):
    """Full -6 dB width from a one-sided angle grid (0 = axis), linear interpolation."""
    rel = spl - ref
    for i in range(1, len(angles)):
        if rel[i] < -6.0:
            a0, a1, r0, r1 = angles[i - 1], angles[i], rel[i - 1], rel[i]
            return 2.0 * (a0 + (a1 - a0) * (-6.0 - r0) / (r1 - r0))
    return 2.0 * angles[-1]


def diagonal(z):
    dirs, spl = z['balloon_dirs'], z['spl_balloon_db']
    theta = np.degrees(np.arccos(np.clip(dirs[:, 2], -1, 1)))
    phi = np.degrees(np.arctan2(dirs[:, 1], dirs[:, 0])) % 90.0
    sel = (np.abs(phi - 45.0) < 6.0) | (theta < 1e-6)
    bins = np.arange(0.0, 92.5, 5.0)
    out_w, curves = [], []
    for k in range(spl.shape[0]):
        ref = float(np.mean(spl[k, theta < 1e-6]))
        prof = []
        for lo in bins:
            msk = sel & (theta >= lo - 2.5) & (theta < lo + 2.5)
            prof.append(float(np.mean(spl[k, msk])) if msk.any() else np.nan)
        prof = np.array(prof)
        prof[0] = ref
        good = ~np.isnan(prof)
        out_w.append(width(bins[good], prof[good], ref))
        curves.append(prof - ref)
    return np.array(out_w), bins, np.array(curves)


def misses(freqs, bw, plane):
    lo, hi, f0 = CORR[plane]
    return [round(float(f)) for f, b in zip(freqs, bw) if f >= f0 * 0.98 and (b < lo or b > hi)]


def summarize(rec):
    m, z = rec['m'], rec['z']
    f = np.array(m['freqs_hz'])
    diag, _, _ = diagonal(z)
    on = np.array(m['on_axis_db'])
    band = (f >= 1000) & (f <= 8000)
    fit = np.polyfit(np.log10(f[band]), on[band], 1)
    smooth = float(np.std(on[band] - np.polyval(fit, np.log10(f[band]))))
    re = np.array(m['z_throat_real'])
    return {'J': rec['J'], 'terms': rec['terms'], 'freqs': f.round(2).tolist(),
            'H': m['bw_h_deg'], 'V': m['bw_v_deg'], 'D': diag.round(2).tolist(), 'DI': m['di_db'],
            'on_axis': m['on_axis_db'], 're_z': m['z_throat_real'],
            'min_re_z_from_900': float(re[f >= 880].min()), 'on_axis_1_8k_std_db': smooth,
            'multilobe_h': m['scalars']['n_multilobe_h'], 'multilobe_v': m['scalars']['n_multilobe_v'],
            'ripple_mean_db': m['scalars']['ripple_mean_db'], 'n_dof': int(z['n_dof']),
            'H_misses': misses(f, m['bw_h_deg'], 'H'), 'V_misses': misses(f, m['bw_v_deg'], 'V'),
            'di_roughness': m['scalars'].get('di_roughness')}


def deltas(a, b):
    f = a['freqs']
    pick = [i for i, x in enumerate(f) if x >= 880]
    return {k: {f'{f[i]:.0f}': round(b[k][i] - a[k][i], 2) for i in pick} for k in ('H', 'V', 'D', 'DI')}


def jobs_from(nights):
    out = {}
    for night in nights:
        p = Path('runs/nights') / night / 'summary.jsonl'
        if not p.exists():
            continue
        for line in p.read_text(encoding='utf-8').splitlines():
            r = json.loads(line)
            if r.get('status') == 'ok' and r.get('run_dir'):
                out[r['id']] = {'run': r['run_dir'], 'seconds': r.get('seconds'),
                                'vram_baseline_mb': r.get('vram_baseline_mb'), 'night': night,
                                'note': r.get('note', '')[:160]}
    return out


def check(cand_id, cand, ctl):
    """Predeclared pass rule (PREDECLARED.md), bin by bin."""
    f = cand['freqs']
    idx = {round(x): i for i, x in enumerate(f)}
    hf_h = [cand['H'][idx[b]] for b in HF]
    mid_h = [cand['H'][idx[b]] for b in MID]
    dv = [cand['V'][idx[b]] - ctl['V'][idx[b]] for b in HF]
    return {
        'H_HF_min': round(min(hf_h), 2), 'H_HF_all_ge_62': bool(min(hf_h) >= 62.0),
        'H_MID_range': [round(min(mid_h), 2), round(max(mid_h), 2)],
        'H_MID_all_65_85': bool(min(mid_h) >= 65.0 and max(mid_h) <= 85.0),
        'dV_HF_min': round(min(dv), 2), 'V_HF_not_narrower': bool(min(dv) >= 0.0),
        'no_multilobe': bool(cand['multilobe_h'] == 0 and cand['multilobe_v'] == 0),
        'min_re_z': round(cand['min_re_z_from_900'], 3),
        'min_re_z_ok': bool(cand['min_re_z_from_900'] >= ctl['min_re_z_from_900'] - 0.1),
        'J': round(cand['J'], 4), 'J_ok': bool(cand['J'] <= ctl['J']),
    }


def figures(results, recs):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    for family in ('rolled', 'lame'):
        labels = [k for k in results[family]['runs'] if k != 'control' and k not in B4]
        fig, axes = plt.subplots(2, 2, figsize=(13, 8.5), sharex=True)
        for ax, (key, title) in zip(axes.flat, (('H', 'Horizontal −6 dB width'), ('V', 'Vertical −6 dB width'),
                                                ('D', 'Diagonal (45°) −6 dB width, balloon'), ('DI', 'Directivity index (balloon)'))):
            a = results[family]['runs']['control']
            f = np.array(a['freqs'])
            sel = f >= 880
            if key in CORR:
                lo, hi, f0 = CORR[key]
                ax.axhspan(lo, hi, color='#d9d8d3', alpha=0.5, lw=0)
            ax.plot(f[sel], np.array(a[key])[sel], color=GRAY, lw=2.4, label='control')
            for i, lab in enumerate(labels):
                r = results[family]['runs'][lab]
                ls = '--' if lab.endswith('epw9') else '-'
                ax.plot(f[sel], np.array(r[key])[sel], color=COLORS[i % len(COLORS)], lw=1.8, ls=ls, label=lab)
            ax.axvspan(6000, 8100, color='#2a78d6', alpha=0.05, lw=0)
            ax.set_xscale('log'); ax.set_title(title, fontsize=11, loc='left'); ax.grid(alpha=0.25, lw=0.6)
            ax.set_xticks([1000, 2000, 4000, 8000]); ax.set_xticklabels(['1k', '2k', '4k', '8k'])
            ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
            ax.set_ylabel('dB' if key == 'DI' else 'degrees')
        axes[0, 0].legend(fontsize=8, frameon=False, ncol=2)
        fig.suptitle(f'{family}: matched verify, epw 6 (grey band = corridor; blue tint = 6–8 kHz)', fontsize=12, x=0.01, ha='left')
        fig.tight_layout()
        fig.savefig(HERE / f'{family}_curves.png', dpi=110)
        plt.close(fig)
        # isobars: control and the two fixed candidates
        show = [('control', recs[family]['control'])] + [(k, recs[family][k]) for k, _ in LABELS[family]
                                                        if k.startswith(f'{family}_bb_h') and not k.endswith('epw9')]
        fig, axes = plt.subplots(len(show), 2, figsize=(12, 2.6 * len(show)), sharex=True, sharey=True)
        cs = None
        for row, (lab, rec) in enumerate(show):
            z = rec['z']
            f = z['freqs_hz']
            for col, (cut, ang) in enumerate((('spl_h_db', 'h_angles_deg'), ('spl_v_db', 'v_angles_deg'))):
                spl = z[cut] - z[cut][:, [np.argmin(np.abs(z[ang]))]]
                ax = axes[row, col]
                cs = ax.contourf(f, z[ang], spl.T, levels=[-30, -20, -12, -9, -6, -3, 0, 3], cmap='Blues_r', extend='both')
                ax.contour(f, z[ang], spl.T, levels=[-6], colors='#e34948', linewidths=1.2)
                ax.set_xscale('log'); ax.set_xlim(500, 8000); ax.set_ylim(-90, 90)
                ax.set_title(f'{lab} — {"H" if col == 0 else "V"} (red = −6 dB)', fontsize=9, loc='left')
                ax.set_xticks([500, 1000, 2000, 4000, 8000]); ax.set_xticklabels(['500', '1k', '2k', '4k', '8k'])
                ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
        if cs is not None:
            fig.colorbar(cs, ax=axes, shrink=0.6, label='dB re on-axis')
        fig.savefig(HERE / f'{family}_isobars.png', dpi=100, bbox_inches='tight')
        plt.close(fig)


def profiles():
    """Same-scale H/V sections, mouth rim, and wall angle against arc fraction (CPU geometry)."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import yaml
    from hornlab_search.design.generators import cd_backbone_family
    sys.path.insert(0, str(PRIOR_DIR))
    import station_map as sm
    fig, axes = plt.subplots(2, 4, figsize=(19, 9.2), gridspec_kw={'width_ratios': [260, 260, 620, 420]})
    for r, family in enumerate(('rolled', 'lame')):
        labels = LABELS[family]
        for i, (stem, title) in enumerate(labels):
            if stem.endswith('epw9') or stem in B4:
                continue
            cfg = yaml.safe_load((CFG_DIR / f'{stem}.yaml').read_text(encoding='utf-8'))
            g = cfg['generator']
            spec = {k: g[k] for k in ('name', 'n_phi', 'n_s', 'span', 'wall_thickness_mm', 'rows')}
            pts = cd_backbone_family.resolve_grid(
                cd_backbone_family.design_params(spec, cfg['seed_params'], cfg['brief'])['grid'], cfg['brief'])['inner_points']
            col = GRAY if i == 0 else COLORS[(i - 1) % len(COLORS)]
            lw = 2.6 if i == 0 else 1.3
            h, v = pts[0], pts[-1]
            for sgn in (1, -1):
                axes[r, 0].plot(h[:, 2], sgn * h[:, 0], color=col, lw=lw, label=title if sgn == 1 else None)
                axes[r, 1].plot(v[:, 2], sgn * v[:, 1], color=col, lw=lw)
            rim = pts[:, -1]
            for sx, sy in ((1, 1), (-1, 1), (-1, -1), (1, -1)):
                axes[r, 2].plot(sx * rim[:, 0], sy * rim[:, 1], color=col, lw=lw)
            for plane, ls in (('H', '-'), ('V', '--')):
                u, ang = sm.wall(pts, plane)
                axes[r, 3].plot(u, ang, color=col, lw=lw if i == 0 else 1.2, ls=ls)
        for c, t in enumerate(('H section', 'V section', 'mouth rim, front view')):
            ax = axes[r, c]
            ax.set_aspect('equal'); ax.grid(alpha=0.25, lw=0.6)
            ax.set_title(f'{family}: {t} (mm)', fontsize=10, loc='left')
            if c < 2:
                ax.set_xlim(-20, 240); ax.set_ylim(-310, 310); ax.set_xlabel('z from throat')
            else:
                ax.set_xlim(-310, 310); ax.set_ylim(-310, 310)
        ax = axes[r, 3]
        ax.set_title(f'{family}: wall angle vs arc fraction (H solid, V dashed)', fontsize=10, loc='left')
        ax.set_xlabel('arc fraction to forward (max-z) station'); ax.set_ylabel('deg from axis'); ax.grid(alpha=0.25, lw=0.6)
        ax.set_xlim(0, 1); ax.set_ylim(0, 95)
        axes[r, 0].legend(fontsize=7, frameon=False, loc='lower left')
    fig.suptitle('Same scale (mm) in the three geometry columns. Grey = exact control; candidates change the backbone blend only',
                 fontsize=11, x=0.01, ha='left')
    fig.tight_layout()
    fig.savefig(HERE / 'profiles_same_scale.png', dpi=100)
    plt.close(fig)


def figure_b4(results):
    """Batch 4: throat-transition vs roll-in at the loading boundary (references h050, h065)."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    runs = results['rolled']['runs']
    show = [k for k in ('rolled_bb_h050', 'rolled_bb_h065') + B4 if k in runs and not k.endswith('epw9')]
    if not any(k in runs for k in B4):
        return
    fig, axes = plt.subplots(2, 2, figsize=(13, 8.5), sharex=True)
    a = runs['control']
    f = np.array(a['freqs'])
    sel = f >= 880
    for ax, (key, title) in zip(axes.flat, (('H', 'Horizontal -6 dB width'), ('V', 'Vertical -6 dB width'),
                                            ('D', 'Diagonal (45 deg) -6 dB width, balloon'),
                                            ('re_z', 'Throat Re(z), normalized (loading)'))):
        if key in CORR:
            lo, hi, _ = CORR[key]
            ax.axhspan(lo, hi, color='#d9d8d3', alpha=0.5, lw=0)
        if key == 're_z':
            ax.axhline(a['min_re_z_from_900'] - 0.1, color=GRAY, lw=1.0, ls=':', label='rule-5 floor')
        ax.plot(f[sel], np.array(a[key])[sel], color=GRAY, lw=2.4, label='control')
        for i, lab in enumerate(show):
            ls = '--' if lab in ('rolled_bb_h050', 'rolled_bb_h065') else '-'
            ax.plot(f[sel], np.array(runs[lab][key])[sel], color=COLORS[i % len(COLORS)], lw=1.7, ls=ls,
                    label=lab.replace('rolled_bb_', ''))
        ax.set_xscale('log'); ax.set_title(title, fontsize=11, loc='left'); ax.grid(alpha=0.25, lw=0.6)
        ax.set_xticks([1000, 2000, 4000, 8000]); ax.set_xticklabels(['1k', '2k', '4k', '8k'])
        ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    axes[1, 1].set_ylim(0.4, 1.8)
    axes[0, 0].legend(fontsize=8, frameon=False, ncol=2)
    axes[1, 1].legend(fontsize=7, frameon=False, ncol=2, loc='lower right')
    fig.suptitle('rolled batch 4: throat-transition vs roll-in (dashed = measured references h050, h065)',
                 fontsize=12, x=0.01, ha='left')
    fig.tight_layout()
    fig.savefig(HERE / 'rolled_b4_curves.png', dpi=110)
    plt.close(fig)


def mesh_gate(results):
    """Predeclared refined-mesh gate: candidate-minus-control deltas at epw 9 vs epw 6."""
    out = {}
    for family, pairs in EPW9_PAIRS.items():
        if not pairs:
            continue
        a9 = results[family]['runs'].get('control_epw9')
        a6 = results[family]['runs']['control']
        if not a9:
            continue
        fam = {'control_epw9_minus_epw6': {k: {str(round(x)): round(a9[k][i] - a6[k][i], 2)
                                               for i, x in enumerate(a6['freqs'])
                                               if round(x) in HF or round(x) in MID} for k in ('H', 'V')},
               'control_J': {'epw6': a6['J'], 'epw9': a9['J']}}
        for base, lab in pairs:
            r6, r9 = results[family]['runs'].get(base), results[family]['runs'].get(lab)
            if not r6 or not r9:
                continue
            row = {'J': {'epw6': r6['J'], 'epw9': r9['J'], 'control_epw6': a6['J'], 'control_epw9': a9['J']}}
            ok = True
            for k in ('H', 'V'):
                cmp = {}
                for i, x in enumerate(a6['freqs']):
                    if round(x) in HF or (k == 'H' and round(x) in MID):
                        d6 = r6[k][i] - a6[k][i]
                        d9 = r9[k][i] - a9[k][i]
                        cmp[str(round(x))] = {'epw6': round(d6, 2), 'epw9': round(d9, 2)}
                        # Predeclared gate: HF deltas (H and V) keep sign and half their size;
                        # 2 kHz H keeps its sign. Other mid bins are reported only.
                        if k == 'H' and round(x) == 2037:
                            if abs(d6) >= 1.5 and np.sign(d6) != np.sign(d9):
                                ok = False
                        elif round(x) in HF:
                            if abs(d6) >= 1.5 and (np.sign(d6) != np.sign(d9) or abs(d9) < 0.5 * abs(d6)):
                                ok = False
                row[k] = cmp
            row['passes_predeclared_mesh_rule'] = ok
            fam[base] = row
        out[family] = fam
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--no-fig', action='store_true')
    args = ap.parse_args()
    jobs = jobs_from([NIGHT, NIGHT_B2, NIGHT_B3, NIGHT_B4, NIGHT_B5, NIGHT_B6, 'directivity_attribution_b2_2026-11-24'])
    results, recs = {}, {}
    for family in ('rolled', 'lame'):
        recs[family] = {'control': load(CONTROLS[family])}
        c9 = jobs.get(CONTROL_EPW9[family]) if EPW9_PAIRS[family] else None
        if c9:
            recs[family]['control_epw9'] = load(c9['run'])
        for jid, info in jobs.items():
            if family_of(jid) == family and jid.startswith(f'{family}_bb_'):
                recs[family][jid] = load(info['run'])
        runs = {k: summarize(v) for k, v in recs[family].items()}
        a = runs['control']
        dl = {k: deltas(a, v) for k, v in runs.items() if k != 'control'}
        checks = {k: check(k, v, a) for k, v in runs.items() if k.startswith(f'{family}_bb_')}
        results[family] = {'runs': runs, 'deltas_vs_control': dl, 'checks': checks,
                           'jobs': {k: v for k, v in jobs.items() if k in runs}}
    results['mesh_gate'] = mesh_gate(results)
    (HERE / 'results.json').write_text(json.dumps(results, indent=1) + '\n', encoding='utf-8')

    for family in ('rolled', 'lame'):
        print(f'\n## {family}')
        a = results[family]['runs']['control']
        f = a['freqs']
        idx = [i for i, x in enumerate(f) if x >= 880]
        print(f'{"":22s}' + ' '.join(f'{f[i]:6.0f}' for i in idx))
        for lab, r in results[family]['runs'].items():
            print(f'{lab:22s} J {r["J"]:.4f}  dof {r["n_dof"]}  minRe {r["min_re_z_from_900"]:.3f}  on-axis std {r["on_axis_1_8k_std_db"]:.2f} dB  '
                  f'lobes {r["multilobe_h"]}/{r["multilobe_v"]}  H-miss {len(r["H_misses"])} V-miss {len(r["V_misses"])}')
            for key in ('H', 'V', 'D'):
                print(f'   {key:19s}' + ' '.join(f'{r[key][i]:6.1f}' for i in idx))
        for lab, c in results[family]['checks'].items():
            print(f' CHECK {lab:16s} ' + '  '.join(f'{k}={v}' for k, v in c.items()))
    for family, fam in results['mesh_gate'].items():
        print(f'\n## mesh gate {family}: control J epw6 {fam["control_J"]["epw6"]:.4f} epw9 {fam["control_J"]["epw9"]:.4f}')
        for k in ('H', 'V'):
            print(f'   control epw9-epw6 {k}', fam['control_epw9_minus_epw6'][k])
        for lab, row in fam.items():
            if lab in ('control_epw9_minus_epw6', 'control_J'):
                continue
            print(f'  {lab:18s} J6 {row["J"]["epw6"]:.4f} J9 {row["J"]["epw9"]:.4f}  pass {row["passes_predeclared_mesh_rule"]}')
            for k in ('H', 'V'):
                print(f'     d{k}', ' '.join(f'{f}:{v["epw6"]:+.1f}/{v["epw9"]:+.1f}' for f, v in row[k].items()))
    if not args.no_fig:
        figures(results, recs)
        figure_b4(results)
        profiles()


if __name__ == '__main__':
    main()
