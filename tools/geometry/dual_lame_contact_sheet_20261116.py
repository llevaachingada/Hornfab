"""Render supplied dual-family seed surfaces; no meshing or acoustic solves."""
from pathlib import Path
import hashlib, json, sys, traceback
import numpy as np
import yaml
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.geometry import klangfilm_lame as K
from hornlab_search.design.generators import lecleach_swept_hv as L
D = ROOT / 'docs/research/typologies/dual_lame_2026-11-16'
OUT = D / 'render'
OUT.mkdir(parents=True, exist_ok=True)
kfile = D / 'k_visual_seeds_supplied.yaml'
lfile = D / 'L/seeds.yaml'
basefile = ROOT / 'examples/typologies/home_landscape_2026-11-15/hl__klangfilm_lame_curved_v1.yaml'
read = lambda p: yaml.safe_load(p.read_text(encoding='utf-8'))
base = read(basefile)
brief_file = (basefile.parent / base['brief_file']).resolve()
brief = read(brief_file)
kdefaults = {k[2:]: v for k, v in base['seed_params'].items()}
kdefaults.update({k: base['generator'][k] for k in ('n_phi', 'n_s', 'wall_thickness_mm')})
rows = []
for family, path in [('K', kfile), ('L', lfile)]:
    for sample in read(path)['samples']:
        row = {'family': family, 'id': sample['id'], 'style': sample['style'], 'source_sample': sample,
               'status': 'SURFACE_ONLY_UNVALIDATED'}
        try:
            if family == 'K':
                p = dict(sample['params']); p['rim_sweep_ratio'] = p.pop('rim_sweep')
                p = dict(kdefaults, **p)
                pts, meta = K.make_grid(p, brief)
            else:
                p = dict(sample['core_existing_iwata_ar'])
                p.update({'g_' + k: v for k, v in sample['proposed_extension'].items()})
                pts, meta = L.make_grid(p, throat_radius_mm=18., throat_half_angle_deg=2., n_phi=25, n_s=96, dl_mm=1.)
            pts = np.asarray(pts, dtype='<f8')
            if not np.isfinite(pts).all(): raise ValueError('nonfinite surface')
            dims = [float(2*pts[:,:,0].max()), float(2*pts[:,:,1].max()), float(np.ptp(pts[:,:,2]))]
            row.update(params=p, dimensions_mm=dict(zip(('width','height','depth'), dims)),
                       sampled_envelope_exceeded=any(a>b for a,b in zip(dims,(600,480,480))),
                       grid_sha256=hashlib.sha256(pts.tobytes()).hexdigest(), grid_shape=list(pts.shape),
                       generated=True, points=pts)
        except Exception as e:
            row.update(generated=False, error=f'{type(e).__name__}: {e}', traceback=traceback.format_exc())
        rows.append(row)

def render(family, view):
    cases = [r for r in rows if r['family'] == family]
    fig = plt.figure(figsize=(18, 16 if family == 'K' else 12), facecolor='#f5f3ef')
    for i, row in enumerate(cases):
        ax = fig.add_subplot(4 if family == 'K' else 3, 4, i+1, projection='3d')
        ax.set_facecolor('#f5f3ef')
        ax.set_proj_type('ortho')
        ax.set_xlim(-350,350); ax.set_ylim(-350,350); ax.set_zlim(-150,550)
        ax.set_box_aspect((1,1,1)); angles = {'oblique': (18, -58), 'front': (90, -90), 'top': (0, -90), 'side': (0, 0)}; ax.view_init(*angles[view])
        ax.set_axis_off()
        if row['generated']:
            pts=row['points'].copy(); pts[:,:,2]-=pts[:,:,2].min()
            for sx,sy in ((1,1),(-1,1),(-1,-1),(1,-1)):
                ax.plot_surface(sx*pts[:,:,0], sy*pts[:,:,1], pts[:,:,2], rstride=2, cstride=3,
                                color='#c58155', edgecolor='#614634', linewidth=.12, shade=True, antialiased=True)
            d=row['dimensions_mm']; flag=' | ENVELOPE EXCEEDED' if row['sampled_envelope_exceeded'] else ''
            subtitle=f"{d['width']:.0f} x {d['height']:.0f} x {d['depth']:.0f} mm{flag}"
        else:
            subtitle='GENERATION FAILED: '+row['error']
        ax.text2D(.03,.97, f"{row['id']}  {row['style']}", transform=ax.transAxes, va='top', fontsize=10, weight='bold')
        ax.text2D(.03,.04, subtitle, transform=ax.transAxes, va='bottom', fontsize=8, color='#a3261b' if not row['generated'] or row['sampled_envelope_exceeded'] else '#333333')
    fig.suptitle(f'{family} supplied seeds — {view} view | SURFACE ONLY / UNVALIDATED', fontsize=18, weight='bold')
    fig.text(.5,.015,'Fixed orthographic camera and 700 mm cubic axes for all panels. W x H x D are sampled inner surface bounds; 3 mm wall NOT SHOWN; 36 mm modeled source; no validity assessment.',ha='center',fontsize=10)
    fig.subplots_adjust(left=.01,right=.99,bottom=.035,top=.94,wspace=.01,hspace=.01)
    fig.savefig(OUT / f'{family}_{view}.png',dpi=150,facecolor=fig.get_facecolor())
    plt.close(fig)
def sections(family):
    cases = [r for r in rows if r['family'] == family]
    fig, axes = plt.subplots(4 if family == 'K' else 3, 4, figsize=(18,16 if family == 'K' else 12), facecolor='#f5f3ef')
    for ax,row in zip(axes.flat,cases):
        ax.set_facecolor('#f5f3ef')
        if row['generated']:
            pts=row['points']; z=pts[:,:,2]-pts[:,:,2].min()
            for idx, color, label in ((0,'#a34221','H'),(-1,'#245b96','V')):
                radius=pts[idx,:,0] if idx == 0 else pts[idx,:,1]
                ax.plot(z[idx],radius,color=color,linewidth=1.5,label=label)
                ax.plot(z[idx],-radius,color=color,linewidth=1.5)
            d=row['dimensions_mm']; flag=' | ENVELOPE EXCEEDED' if row['sampled_envelope_exceeded'] else ''
            label=f"{d['width']:.0f} x {d['height']:.0f} x {d['depth']:.0f} mm{flag}"
        else: label='GENERATION FAILED: '+row['error']
        ax.set_xlim(-50,650); ax.set_ylim(-350,350); ax.set_aspect('equal'); ax.grid(alpha=.2)
        ax.set_title(row['id']+' '+row['style'],fontsize=10,weight='bold')
        ax.text(.02,.03,label,transform=ax.transAxes,fontsize=7,color='#a3261b' if row.get('sampled_envelope_exceeded') or not row['generated'] else '#333')
        ax.tick_params(labelsize=7)
    fig.suptitle(f'{family} supplied seeds — H / V meridian sections | SURFACE ONLY / UNVALIDATED',fontsize=18,weight='bold')
    fig.text(.5,.015,'Horizontal section: rust; vertical section: blue. Axial and radial axes in mm; all panels use identical 700 mm ranges. Shell not shown.',ha='center',fontsize=10)
    fig.subplots_adjust(left=.04,right=.99,bottom=.05,top=.93,wspace=.18,hspace=.35)
    fig.savefig(OUT/f'{family}_sections.png',dpi=150,facecolor=fig.get_facecolor()); plt.close(fig)

for family in ('K','L'):
    for view in ('oblique','front','top','side'): render(family,view)
    sections(family)
files=[kfile,lfile,basefile,brief_file,Path(__file__), ROOT/'tools/geometry/klangfilm_lame.py',ROOT/'tools/geometry/lame_cap.py',ROOT/'hornlab_search/design/generators/lecleach_swept_hv.py',ROOT/'hornlab_search/design/generators/section_lame.py',ROOT/'hornlab_search/design/generators/profiles.py']
report={'scope':'Sampled inner quarter surfaces mirrored for display; no shell, mesh, intersection, curvature, acoustic, or readiness validation.',
        'render':'Orthographic fixed camera; all panels x,y = -350..350 mm and z = -150..550 mm after z minimum shift; dimensions sampled before shift.',
        'envelope_mm': {'width':600,'height':480,'depth':480},
        'input_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
        'driver_assumptions': {'K':brief['driver'], 'L':'18 mm throat radius and 2 degree half angle, legacy assumptions'},
        'wall': '3 mm modeled wall context; inner surface only, shell not shown or assessed',
        'cases':[{k:v for k,v in r.items() if k!='points'} for r in rows]}
(OUT/'metadata.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
print('Generated',sum(r['generated'] for r in rows),'/',len(rows),'surfaces')
print('Envelope exceeded:', ', '.join(r['id'] for r in rows if r.get('sampled_envelope_exceeded')))
print('Failures:', [(r['id'],r.get('error')) for r in rows if not r['generated']])
