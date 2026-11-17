"""N1 recon: lane designs, stored mesh metadata, tag-1 structure. Read-only."""
import pickle, json, pathlib, collections, sys
import numpy as np
import yaml

rows = pickle.load(open('scratch/fable_architecture/.fable/rows.pkl', 'rb'))
LANES = ['hl__ext_throat_hvlaw_v7', 'hl__ath_tritonia_landscape_v9', 'hl__crowe_x_osse_cd_v7',
         'rf__section_axial_home_v7', 'hl__klangfilm_lame_curved_v1', 'hl__biradial_es_style_v7']

def tag1_nodes(path):
    txt = pathlib.Path(path).read_text()
    a0 = txt.index('$Nodes') + 7
    a1 = txt.index('$EndNodes')
    lines = txt[a0:a1].split('\n', 1)[1]
    nd = np.array(lines.split(), float).reshape(-1, 4)[:, 1:] * 1000.0
    b0 = txt.index('$Elements') + 10
    b1 = txt.index('$EndElements')
    wall = set()
    ents = collections.Counter()
    for line in txt[b0:b1].split('\n')[1:]:
        z = line.split()
        if len(z) >= 8 and z[1] == '2' and z[3] == '1':
            wall.update((int(z[-3]) - 1, int(z[-2]) - 1, int(z[-1]) - 1))
            ents[z[4]] += 1
    return nd, sorted(wall), ents

for ln in LANES:
    r = [x for x in rows if x['config'] == ln and x['ok']][0]
    run = pathlib.Path('runs') / r['run']
    d = run / 'designs' / r['h']
    print('\n===', ln, r['run'], r['h'])
    j = json.load(open(d / 'design.json'))
    cfg = yaml.safe_load(open(run / 'config.yaml'))
    brief = cfg.get('brief') or {}
    print(' bbox_m', r['bbox'])
    print(' brief: sym', brief.get('symmetry'), 'driver', brief.get('driver'))
    print(' brief source', brief.get('source'))
    print(' brief grid keys', list((brief.get('grid') or {}).keys()))
    print(' family', cfg.get('family'), 'generator', cfg.get('generator'))
    if 'grid' in j['params']:
        b = j['params']['grid']
        print(' block keys', list(b.keys()))
        print(' block rows', b.get('rows'))
        print(' block wall_thickness_mm', b.get('wall_thickness_mm'),
              'knobs wall', {k: v for k, v in (b.get('knobs') or {}).items() if 'wall' in k or 'thick' in k})
    else:
        print(' params wall_thickness_mm', j['params'].get('wall_thickness_mm'))
        print(' param keys', list(j['params'].keys()))
    mm = d / 'mesh_meta.json'
    if mm.exists():
        m = json.load(open(mm))
        print(' mesh_meta', {k: m.get(k) for k in ('mode', 'quadrants', 'n_triangles', 'n_nodes', 'bbox_m',
                                                   'tags', 'res_mm')})
    nd, wall, ents = tag1_nodes(d / 'mesh.msh')
    w = nd[wall]
    print(' nodes', len(nd), 'tag1 nodes', len(wall), 'entities', dict(ents))
    print(' tag1 z range', w[:, 2].min().round(2), w[:, 2].max().round(2),
          'rho max', np.hypot(w[:, 0], w[:, 1]).max().round(2))
