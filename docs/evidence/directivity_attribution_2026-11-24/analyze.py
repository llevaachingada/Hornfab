"""Matched readout of the fixed-candidate verifies against their anchors. No solver calls.

    .venv\\Scripts\\python.exe docs/evidence/directivity_attribution_2026-11-24/analyze.py [--night NAME ...]

Reads each night's summary.jsonl (job id -> run dir), the anchor verifies, and the saved metrics/response
files. Writes results.json and PNG figures next to this script. Widths are full -6 dB widths at the saved
verify frequencies; the diagonal width comes from the 1024-point balloon (directions within 6 deg of the
45-deg azimuth plane, any quadrant), so it is coarser than the 2.5-deg H/V cuts.
"""
import argparse, glob, json, math, sys

import matplotlib
import matplotlib.ticker
from pathlib import Path

import numpy as np
import yaml

sys.path.insert(0, str(Path.cwd()))
HERE = Path('docs/evidence/directivity_attribution_2026-11-24')
ANCHORS = {'rolled': 'runs/rolled_lame_anchor_verify_2026-11-24/rolled',
           'lame': 'runs/rolled_lame_anchor_verify_2026-11-24/lame'}
PRIOR = {'rolled_h10_v6': 'runs/20261124T222433Z-verify-4617d0', 'lame_hmid_p2': 'runs/20261124T222525Z-verify-b5497c'}
HF = [6085, 6325, 6977, 7113, 8000]
CORR = {'H': (60.0, 90.0, 900.0), 'V': (40.0, 60.0, 1000.0)}
COLORS = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#6250d6', '#e34948']
GRAY = '#52514e'
ISOBARS = {'rolled': ['rolled_h10_v0', 'rolled_h0_v6', 'rolled_h10_early', 'rolled_h20_early'],
           'lame': ['lame_morph_040', 'lame_hmid_m2', 'lame_morph_085']}
EPW9 = ('_epw9', '_src10')


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
    return {'J': rec['J'], 'terms': rec['terms'], 'freqs': f.round(2).tolist(), 'H': m['bw_h_deg'], 'V': m['bw_v_deg'],
            'D': diag.round(2).tolist(), 'DI': m['di_db'], 'on_axis': m['on_axis_db'], 're_z': m['z_throat_real'],
            'min_re_z_from_900': float(re[f >= 880].min()), 'on_axis_1_8k_std_db': smooth,
            'multilobe_h': m['scalars']['n_multilobe_h'], 'multilobe_v': m['scalars']['n_multilobe_v'],
            'ripple_mean_db': m['scalars']['ripple_mean_db'], 'n_dof': int(z['n_dof']),
            'H_misses': misses(f, m['bw_h_deg'], 'H'), 'V_misses': misses(f, m['bw_v_deg'], 'V')}


def deltas(a, b):
    f = a['freqs']
    pick = [i for i, x in enumerate(f) if x >= 880]
    return {k: {f'{f[i]:.0f}': round(b[k][i] - a[k][i], 2) for i in pick} for k in ('H', 'V', 'D', 'DI')}


def hf_rule(d, plane, thresh):
    vals = [d[plane][str(x)] for x in HF]
    return sum(v >= thresh for v in vals), vals


def jobs_from(nights):
    out = {}
    for night in nights:
        p = Path('runs/nights') / night / 'summary.jsonl'
        if not p.exists():
            continue
        for line in p.read_text(encoding='utf-8').splitlines():
            r = json.loads(line)
            if r.get('status') == 'ok' and r.get('run_dir'):
                out[r['id']] = {'run': r['run_dir'], 'seconds': r.get('seconds'), 'vram_baseline_mb': r.get('vram_baseline_mb'),
                                'note': r.get('note', '')[:160]}
    return out


def figures(results, recs):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    for family in ('rolled', 'lame'):
        labels = [k for k in results[family]['runs'] if k != 'anchor' and not k.endswith(EPW9)]
        fig, axes = plt.subplots(2, 2, figsize=(13, 8.5), sharex=True)
        for ax, (key, title) in zip(axes.flat, (('H', 'Horizontal −6 dB width'), ('V', 'Vertical −6 dB width'),
                                                ('D', 'Diagonal (45°) −6 dB width, balloon'), ('DI', 'Directivity index (balloon)'))):
            a = results[family]['runs']['anchor']
            f = np.array(a['freqs'])
            sel = f >= 880
            if key in CORR:
                lo, hi, f0 = CORR[key]
                ax.axhspan(lo, hi, color='#d9d8d3', alpha=0.5, lw=0)
            ax.plot(f[sel], np.array(a[key])[sel], color=GRAY, lw=2.4, label='anchor')
            for i, lab in enumerate(labels):
                r = results[family]['runs'][lab]
                ax.plot(f[sel], np.array(r[key])[sel], color=COLORS[i % len(COLORS)], lw=1.8, label=lab)
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
        # isobars: anchor and up to three candidates, H and V
        show = ['anchor'] + [k for k in ISOBARS[family] if k in recs[family]]
        fig, axes = plt.subplots(len(show), 2, figsize=(12, 2.6 * len(show)), sharex=True, sharey=True)
        for row, lab in enumerate(show):
            z = recs[family][lab]['z']
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
        fig.colorbar(cs, ax=axes, shrink=0.6, label='dB re on-axis')
        fig.savefig(HERE / f'{family}_isobars.png', dpi=100, bbox_inches='tight')
        plt.close(fig)


def profiles(results):
    """Same-scale H and V meridian sections and the mouth outline, anchor vs candidates (CPU geometry),
    plus the station wall angle (deg) against arc fraction to the forward station."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from hornlab_search.design.generators import rolled_cd_family, klangfilm_lame_hv_family
    sys.path.insert(0, str(HERE))
    import station_map as sm
    adapters = {'rolled': rolled_cd_family, 'lame': klangfilm_lame_hv_family}
    fig, axes = plt.subplots(2, 4, figsize=(19, 9.2), gridspec_kw={'width_ratios': [260, 260, 620, 420]})
    for r, family in enumerate(('rolled', 'lame')):
        cfg0 = yaml.safe_load(Path(f'docs/evidence/size_aware_2026-11-24/anchor_{family}_neutral.yaml').read_text(encoding='utf-8'))
        g = cfg0['generator']
        spec = {k: g[k] for k in ('name', 'n_phi', 'n_s', 'span', 'wall_thickness_mm', 'rows')}
        labels = ['anchor'] + [k for k in results[family]['runs'] if k != 'anchor' and not k.endswith(EPW9) and (HERE / f'{k}.yaml').exists()]
        for i, lab in enumerate(labels):
            cfg = cfg0 if lab == 'anchor' else yaml.safe_load((HERE / f'{lab}.yaml').read_text(encoding='utf-8'))
            ad = adapters[family]
            pts = ad.resolve_grid(ad.design_params(spec, cfg['seed_params'], cfg['brief'])['grid'], cfg['brief'])['inner_points']
            col = GRAY if lab == 'anchor' else COLORS[(i - 1) % len(COLORS)]
            lw = 2.6 if lab == 'anchor' else 1.3
            h, v = pts[0], pts[-1]
            for sgn in (1, -1):
                axes[r, 0].plot(h[:, 2], sgn * h[:, 0], color=col, lw=lw, label=lab if sgn == 1 else None)
                axes[r, 1].plot(v[:, 2], sgn * v[:, 1], color=col, lw=lw)
            rim = pts[:, -1]
            for sx, sy in ((1, 1), (-1, 1), (-1, -1), (1, -1)):
                axes[r, 2].plot(sx * rim[:, 0], sy * rim[:, 1], color=col, lw=lw)
            for plane, ls in (('H', '-'), ('V', '--')):
                u, ang = sm.wall(pts, plane)
                axes[r, 3].plot(u, ang, color=col, lw=lw if lab == 'anchor' else 1.2, ls=ls)
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
    fig.suptitle('Same scale (mm) in the three geometry columns. Grey = exact anchor; candidates change only the named knobs',
                 fontsize=11, x=0.01, ha='left')
    fig.tight_layout()
    fig.savefig(HERE / 'profiles_same_scale.png', dpi=100)
    plt.close(fig)


def mesh_gate(results):
    """Predeclared refined-mesh gate: candidate-minus-anchor deltas at epw 9 vs epw 6 (HF bins + 2 kHz H)."""
    out = {}
    for family in ('rolled', 'lame'):
        runs = results[family]['runs']
        a9 = runs.get(f'{family}_anchor_epw9')
        if not a9:
            continue
        a6 = runs['anchor']
        fam = {'anchor_epw9_minus_epw6': {k: {str(x): round(a9[k][i] - a6[k][i], 2) for i, x in enumerate(a6['freqs'])
                                                  if round(x) in HF or round(x) == 2037} for k in ('H', 'V')},
               'anchor_J': {'epw6': a6['J'], 'epw9': a9['J']}}
        for lab, r9 in runs.items():
            if not lab.endswith('_epw9') or lab == f'{family}_anchor_epw9':
                continue
            base = lab[:-5]
            r6 = runs.get(base)
            if not r6:
                continue
            row = {'J': {'epw6': r6['J'], 'epw9': r9['J'], 'anchor_epw6': a6['J'], 'anchor_epw9': a9['J']}}
            ok = True
            for k in ('H', 'V'):
                cmp = {}
                for i, x in enumerate(a6['freqs']):
                    if round(x) in HF or (k == 'H' and round(x) == 2037):
                        d6 = r6[k][i] - a6[k][i]
                        d9 = r9[k][i] - a9[k][i]
                        cmp[str(round(x))] = {'epw6': round(d6, 2), 'epw9': round(d9, 2)}
                        if k == 'H' and abs(d6) >= 1.5 and (np.sign(d6) != np.sign(d9) or abs(d9) < 0.5 * abs(d6)):
                            ok = False
                row[k] = cmp
            row['passes_predeclared_mesh_rule'] = ok
            fam[base] = row
        out[family] = fam
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--night', action='append', default=['directivity_attribution_2026-11-24', 'directivity_attribution_b2_2026-11-24'])
    ap.add_argument('--no-fig', action='store_true')
    args = ap.parse_args()
    jobs = jobs_from(args.night)
    results, recs = {}, {}
    for family in ('rolled', 'lame'):
        recs[family] = {'anchor': load(ANCHORS[family])}
        for k, run in PRIOR.items():
            if k.startswith(family):
                recs[family][k] = load(run)
        for jid, info in jobs.items():
            if jid.startswith(family):
                recs[family][jid] = load(info['run'])
        runs = {k: summarize(v) for k, v in recs[family].items()}
        a = runs['anchor']
        dl = {k: deltas(a, v) for k, v in runs.items() if k != 'anchor'}
        results[family] = {'runs': runs, 'deltas_vs_anchor': dl,
                           'jobs': {k: v for k, v in jobs.items() if k.startswith(family)}}
    results['mesh_gate'] = mesh_gate(results)
    (HERE / 'results.json').write_text(json.dumps(results, indent=1) + '\n', encoding='utf-8')
    for family, fam in results['mesh_gate'].items():
        print(f'\n## mesh gate {family}: anchor J epw6 {fam["anchor_J"]["epw6"]:.4f} epw9 {fam["anchor_J"]["epw9"]:.4f}')
        for k in ('H', 'V'):
            print(f'   anchor epw9-epw6 {k}', fam['anchor_epw9_minus_epw6'][k])
        for lab, row in fam.items():
            if lab in ('anchor_epw9_minus_epw6', 'anchor_J'):
                continue
            print(f'  {lab:18s} J6 {row["J"]["epw6"]:.4f} J9 {row["J"]["epw9"]:.4f}  pass {row["passes_predeclared_mesh_rule"]}')
            for k in ('H', 'V'):
                print(f'     d{k}', ' '.join(f'{f}:{v["epw6"]:+.1f}/{v["epw9"]:+.1f}' for f, v in row[k].items()))
    for family in ('rolled', 'lame'):
        print(f'\n## {family}')
        a = results[family]['runs']['anchor']
        f = a['freqs']
        idx = [i for i, x in enumerate(f) if x >= 880]
        print(f'{"":22s}' + ' '.join(f'{f[i]:6.0f}' for i in idx))
        for lab, r in results[family]['runs'].items():
            print(f'{lab:22s} J {r["J"]:.4f}  dof {r["n_dof"]}  minRe {r["min_re_z_from_900"]:.3f}  on-axis std {r["on_axis_1_8k_std_db"]:.2f} dB  '
                  f'lobes {r["multilobe_h"]}/{r["multilobe_v"]}  H-miss {len(r["H_misses"])} V-miss {len(r["V_misses"])}')
            for key in ('H', 'V', 'D'):
                print(f'   {key:19s}' + ' '.join(f'{r[key][i]:6.1f}' for i in idx))
        for lab, d in results[family]['deltas_vs_anchor'].items():
            for key in ('H', 'V', 'D'):
                print(f' d{key} {lab:18s}' + ' '.join(f'{v:+6.1f}' for v in d[key].values()))
    if not args.no_fig:
        figures(results, recs)
        profiles(results)


if __name__ == '__main__':
    main()
