"""Rebuild exact anchors and existing-law controls. CPU only; no solver calls."""
import copy, json, math, sys
from pathlib import Path
import numpy as np
import yaml
sys.path.insert(0, str(Path.cwd()))
from hornlab_search.design.generators import rolled_family, rolled_cd_family, klangfilm_lame_family, klangfilm_lame_hv_family
from hornlab_search.design.generators import _klangfilm_lame_hv_v1 as hv_kernel

DEST=Path('docs/evidence/size_aware_2026-11-24')
CASES=[('rolled','20261124T000037Z-screen-f8a896','fa5b207bca6d',rolled_family,rolled_cd_family),
       ('lame','20261123T235306Z-screen-0a4f8a','0782945027ae',klangfilm_lame_family,klangfilm_lame_hv_family)]
report={}
for label, run, design, parent, adapter in CASES:
    root=Path('runs')/run
    config=json.loads((root/'run.json').read_text(encoding='utf-8'))['config']
    brief=config['brief']
    stored=json.loads((root/'designs'/design/'design.json').read_text(encoding='utf-8'))['params']['grid']
    assert stored['rows']['implementation_sha256']==parent.implementation_digest(), 'saved parent digest differs'
    ref=parent.resolve_grid(stored,brief)
    spec={k:copy.deepcopy(stored[k]) for k in ('n_phi','n_s','span','wall_thickness_mm')}
    spec['name']='grid'; spec['rows']={'type':adapter.KIND}
    knobs=copy.deepcopy(stored['knobs'])
    if label=='rolled':
        spec['rows']['mode']=stored['rows']['mode']
        extra={'g_cd_h_deg':0.,'g_cd_v_deg':0.,'g_cd_start_s':.3,'g_cd_peak_s':.6,'g_cd_end_s':.88}
        variant={'g_cd_h_deg':10.,'g_cd_v_deg':6.}
    else:
        shape={k[2:]:v for k,v in knobs.items()}; shape.update({k:spec[k] for k in ('n_phi','n_s','wall_thickness_mm')})
        from hornlab_search.design.generators import _klangfilm_lame_v1 as pk
        tab=pk.profile(shape,brief['driver']['exit_radius_mm'])
        h=hv_kernel._chord_deg(tab['z'],tab['a']); v=hv_kernel._chord_deg(tab['z'],tab['b'])
        extra={'g_cd_core_blend':0.,'g_theta_h0_deg':h,'g_theta_v0_deg':v,'g_h_mid_gain_mm':0.,'g_v_mid_gain_mm':0.,'g_core_join_fraction':.65}
        variant={'g_cd_core_blend':1.,'g_h_mid_gain_mm':2.}
    knobs.update(extra)
    zero=adapter.resolve_grid(adapter.design_params(spec,knobs,brief)['grid'],brief)
    assert np.array_equal(ref['inner_points'],zero['inner_points']) and np.array_equal(ref['outer_points'],zero['outer_points']), 'zero control is not bit-identical'
    candidate={**knobs,**variant}
    try:
        tested=adapter.resolve_grid(adapter.design_params(spec,candidate,brief)['grid'],brief)
        a,b=ref['inner_points'],tested['inner_points']
        def angles(p, axis):
            row=p[0 if axis=='H' else -1]; rad=row[:,0 if axis=='H' else 1]; z=row[:,2]
            dr=np.gradient(rad); dz=np.gradient(z)
            return [round(float(math.degrees(math.atan2(dr[i],dz[i]))),3) for i in [1,len(z)//4,len(z)//2,3*len(z)//4,len(z)-2]]
        diff=np.linalg.norm(b-a,axis=2)
        info={'zero_inner_outer_bit_equal':True,'variant':variant,'inner_max_delta_mm':float(diff.max()),
              'lip_max_delta_mm':float(diff[:,-1].max()),'final_10pct_max_delta_mm':float(diff[:,int(.9*diff.shape[1]):].max()),
              'sample_station_fraction':[round(i/(a.shape[1]-1),3) for i in [1,a.shape[1]//4,a.shape[1]//2,3*a.shape[1]//4,a.shape[1]-2]],
              'parent_h_tangent_deg':angles(a,'H'),'variant_h_tangent_deg':angles(b,'H'),
              'parent_v_tangent_deg':angles(a,'V'),'variant_v_tangent_deg':angles(b,'V'),
              'parent_extents_mm':[ref['meta'][x] for x in ('mouth_w_mm','mouth_h_mm','x_span_mm')],
              'variant_extents_mm':[tested['meta'][x] for x in ('mouth_w_mm','mouth_h_mm','x_span_mm')],
              'source_parent_digest':parent.implementation_digest(),'variant_digest':adapter.implementation_digest()}
        if label=='lame': info['phase_a_core_info']=tested['meta']['core_info']
        # Self-contained run configs use the exact saved effective configuration and brief.
        for suffix,params in [('neutral',knobs),('variant',candidate)]:
            cfg=copy.deepcopy(config); cfg['name']=f'anchor_{label}_{suffix}_2026_11_24'; cfg['generator']=copy.deepcopy(spec)
            cfg['generator']['seed_policy']='explicit'; cfg['seed_params']=params
            cfg['bounds']={k:{'lo':v,'hi':v,'search':False} for k,v in params.items()}
            cfg['brief_file']=None
            (DEST/f'anchor_{label}_{suffix}.yaml').write_text(yaml.safe_dump(cfg,sort_keys=False),encoding='utf-8')
        report[label]=info
    except Exception as exc:
        report[label]={'zero_inner_outer_bit_equal':True,'variant':variant,'refused':f'{type(exc).__name__}: {exc}'}
(DEST/'anchor_geometry.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2))
