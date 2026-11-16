import csv, json, math, hashlib
from pathlib import Path
import yaml
from hornlab_search.config import _load_yaml_extends
root=Path.cwd(); out=root/'docs/research/typologies/audit_2026-11-15'
paths=[]
for d in ['home_landscape_2026-11-15','rolled_family_2026-11-15','rolled_rect_2026-11-15','section_pucker_2026-11-15']:
 paths += sorted((root/'examples/typologies'/d).glob('*.yaml'))
meaning={'az_n_cos2_amp':'azimuth profile exponent cosine amplitude','az_sf_a':'azimuth superformula scale a','az_sf_b':'azimuth superformula scale b','az_sf_m':'azimuth superformula symmetry order','az_sf_n1':'azimuth superformula exponent 1','az_sf_n2':'azimuth superformula exponent 2','az_sf_n3':'azimuth superformula exponent 3','pucker_start_s':'axial pucker window start station','pucker_peak_s':'axial pucker window peak station','pucker_end_s':'axial pucker window end station','s1':'OSSE profile parameter s1','s2':'OSSE profile parameter s2','width':'nominal width','height':'nominal height','depth':'nominal depth','depth_h_ratio':'horizontal/vertical depth ratio','h_depth_scale':'horizontal depth scale','decay':'curve decay','rect_exponent':'rectangular outline exponent','rect_turn':'rectangle onset turn','throat_turn':'throat transition turn','terminal':'terminal curve turn','inward_h':'horizontal radial inward relief amplitude','inward_v':'vertical radial inward relief amplitude','axial_h':'horizontal signed axial relief amplitude','axial_v':'vertical signed axial relief amplitude','relief_start_s':'relief window start in normalized station','relief_peak_s':'relief window peak in normalized station','relief_end_s':'relief window end in normalized station','crown':'section crown','throat_blend':'throat blend length','junction_power':'section junction exponent','pucker_h':'horizontal pucker amplitude','pucker_v':'vertical pucker amplitude','pucker_start':'pucker start turn','L':'axial profile length','r0':'throat radius','a0':'throat wall angle','a_h':'horizontal wall half-angle','a_v':'vertical wall half-angle','a_diag':'diagonal angular shaping','a':'profile wall angle (interpretation depends on profile)','rm':'mouth radius in plane','n':'profile exponent (law dependent)','T':'hyperbolic/exponential profile parameter','fc':'profile cutoff parameter','stop':'curve stop parameter','ar_m':'mouth aspect ratio','ar_p':'aspect ratio progression exponent','s':'OSSE termination strength','q':'OSSE profile parameter','k':'OSSE throat expansion parameter','r':'R-OSSE roll parameter','m':'R-OSSE profile parameter','b':'R-OSSE bend parameter','tmax':'R-OSSE terminal parameter','r_lip':'lip radius','wrap':'lip curve parameter','sf_m':'superformula symmetry order','sf_n1':'superformula exponent 1','sf_n2':'superformula exponent 2','sf_ab':'superformula aspect factor','sf_amt':'superformula shaping amount','sf_start':'superformula shaping start','mouth_corner':'mouth corner radius','mouth_exponent':'mouth outline superellipse exponent','morph_target':'mouth morph target selection','morph_width':'mouth morph target width','morph_height':'mouth morph target height','morph_corner':'mouth morph corner radius','morph_exponent':'mouth morph exponent','morph_rate':'mouth morph rate','morph_fixed':'mouth morph fixed factor','morph_allow_shrinkage':'mouth morph shrinkage flag','aspect_ratio':'cross section aspect ratio','exponent':'cross section exponent','az_a_cos_pow':'azimuth angle cosine exponent','az_a_cos_amp':'azimuth wall angle cosine amplitude','az_a_sf_amp':'azimuth superformula wall-angle amplitude','az_s_cos2_amp':'azimuth termination cosine amplitude','throat_ext_length':'throat extension length','throat_ext_angle':'throat extension wall angle','wall_thickness':'wall thickness','slot_length':'throat slot length'}
def desc(k):
 t=k.removeprefix('g_'); plane=''
 if t=='h_depth_scale': return 'horizontal section depth scale relative to reference vertical section'
 if t.startswith(('h_','v_')): plane={'h_':'horizontal ','v_':'vertical '}[t[:2]]; t=t[2:]
 raw=t
 for suffix in ('_mm','_deg','_hz'):
  if t.endswith(suffix): t=t[:-len(suffix)]; break
 return plane+meaning.get(t,meaning.get(raw,'parameter; see source config and generator for law-specific meaning'))
def unit(k):
 if k in ('az_a_cos_amp','az_a_sf_amp'): return 'deg'
 if k.endswith('_mm'):return 'mm'
 if k.endswith('_deg'):return 'deg'
 if k.endswith('_hz'):return 'Hz'
 return 'dimensionless / categorical'
rows=[]; configs=[]
for p in paths:
 raw=p.read_bytes(); declared=yaml.safe_load(raw); d=_load_yaml_extends(p); seed=d.get('seed_params') or {}; bounds=d.get('bounds') or {}; search=d.get('search') or {}; sigma=search.get('sigma0'); gen=d.get('generator') or {}; rt=(gen.get('rows') or {}).get('type') if isinstance(gen.get('rows'),dict) else None
 config={'path':p.relative_to(root).as_posix(),'sha256':hashlib.sha256(raw).hexdigest(),'extends':declared.get('extends'), 'parent_sha256':({str(e):hashlib.sha256((p.parent/e).read_bytes()).hexdigest() for e in ([declared['extends']] if isinstance(declared.get('extends'),str) else declared.get('extends',[]))}),'name':d.get('name',p.stem),'family':d.get('family'),'generator':gen,'sigma0':sigma,'search':search,'brief_file':d.get('brief_file'),'fixed_config':{'mesh':d.get('mesh'),'solve':d.get('solve')},'parameters':[]}
 for k in sorted(set(seed)|set(bounds)):
  b=bounds.get(k); b=b if isinstance(b,dict) else {}; v=seed.get(k); active=b.get('search',True) if b else False; lo=b.get('lo'); hi=b.get('hi'); log=b.get('log',False); step=None; neg=None; pos=None
  if active and sigma is not None and isinstance(v,(int,float)) and isinstance(lo,(int,float)) and isinstance(hi,(int,float)) and hi>lo:
   if log and lo>0 and v>0:
    step=None; factor=(hi/lo)**sigma; neg=v-v/factor; pos=v*factor-v
   else: step=sigma*(hi-lo); neg=pos=step
  activity='searched' if active else ('fixed bound' if b else 'seed fixed (no bound)')
  if rt in ('rolled_family_rect_v1','rolled_family_section_v1') and ('inward_' in k or 'axial_' in k): activity += '; mode '+str(gen['rows'].get('mode'))+'; neutral zero if inactive'
  rec={'config':config['path'],'name':config['name'],'family':config['family'],'rows_type':rt,'key':k,'meaning':desc(k),'units':unit(k),'seed':v,'lo':lo,'hi':hi,'search':bool(active),'activity':activity,'transform':('log10 unit interval' if log else 'linear unit interval') if active else 'fixed','sigma0':sigma,'nominal_sigma_step':step,'nominal_sigma_minus':neg,'nominal_sigma_plus':pos,'note':('inherited via extends; ' if k not in (declared.get('seed_params') or {}) and k not in (declared.get('bounds') or {}) else 'declared or overrides inherited; ')+('unclipped nominal one-sigma step; not a guarantee of realized change' if active else 'fixed')}
  config['parameters'].append(rec); rows.append(rec)
 configs.append(config)
# Add explicit per-config fixed construction inputs and identified resolver defaults.
# Values are not asserted to be extra optimizer dimensions.
for c in configs:
 gen=c['generator']; rt=(gen.get('rows') or {}).get('type') if isinstance(gen.get('rows'),dict) else None
 names={x['key'] for x in c['parameters']}; seeds={x['key']:x['seed'] for x in c['parameters']}
 def add(key,value,description,units='dimensionless / categorical',origin='declared',activity='fixed construction input'):
  rec={'config':c['path'],'name':c['name'],'family':c['family'],'rows_type':rt,'key':key,'meaning':description,'units':units,'seed':value,'lo':None,'hi':None,'search':False,'activity':activity,'transform':'fixed','sigma0':c['sigma0'],'nominal_sigma_step':None,'nominal_sigma_minus':None,'nominal_sigma_plus':None,'note':'origin: '+origin}
  c['parameters'].append(rec); rows.append(rec)
 def flatten(d,prefix):
  for k,v in d.items():
   path=prefix+'.'+str(k)
   if isinstance(v,dict): flatten(v,path)
   else:
    descriptions={'name':'generator construction route','type':'profile or rows construction kind','mode':'native rolled-family relief mode','n_phi':'number of azimuth samples','n_s':'number of curve stations','n_anchors':'number of meridian anchor stations','wall_thickness_mm':'outer wall thickness','span':'modeled azimuthal span and symmetry','seed_policy':'config-load seed derivation policy','max_wall_deg':'maximum meridian wall angle guard','mouth':'mouth cross-section law'}
    add(path,v,descriptions.get(k,'fixed generator construction field'),unit(k))
 if gen:
  flatten(gen,'generator')
  defaults={'seed_policy':('derive','config.load default seed derivation policy'),'wall_thickness_mm':(3.0,'resolver default wall thickness')}
  if gen.get('name')=='typology': defaults.update(n_anchors=(16,'typology default anchor count'),max_wall_deg=(80.0,'typology default maximum wall angle'),mouth=('ellipse','typology default cross-section'))
  elif rt and not rt.startswith('rolled_family_') and rt not in ('rolled_rect','rolled_rect_pucker','crowe_panel','section_pucker','rosse_rect'):
   defaults.update(n_phi=(13,'stock grid default azimuth count'),n_s=(32,'stock grid default station count'),span=('quarter','stock rows default span for this kind'))
  for k,(v,d) in defaults.items():
   if k not in gen: add('generator.'+k,v,d,unit(k),'resolver default')
  if rt=='osse_rollback':
   defaults2={'wrap_cos_amp':0.,'a_fold':2.,'a_union':0.,'union_blend_deg':0.,'ripple_lobes':0.,'ripple_amp_mm':0.,'ripple_start':0.}
   defs2={'wrap_cos_amp':'lip wrap azimuth modulation amplitude; inactive without ripple lobes','a_fold':'wall angle azimuth fold count','a_union':'enable union angle construction','union_blend_deg':'union angle smoothing; inactive when union is off','ripple_lobes':'even mouth ripple lobe count; 0 disables ripple','ripple_amp_mm':'mouth ripple radial amplitude; inactive at zero lobes','ripple_start':'mouth ripple window start; inactive at zero lobes'}
   for k,v in defaults2.items():
    if 'g_'+k not in names: add('g_'+k,v,defs2[k],unit(k),'grid.py osse rollback / ROWS_DEFAULTS','resolver default; '+defs2[k])
  if gen.get('name')=='typology':
   if 'morph_target' not in names: add('morph_target',0,'native mouth morph target (0 off)',origin='registry.DEFAULT_KNOBS',activity='fixed off; other morph controls inactive')
   for plane in ('h','v'):
    typ=(gen.get('profile_'+plane) or {}).get('type') if isinstance(gen.get('profile_'+plane),dict) else None
    key=plane+'_throat_blend_mm'
    if typ in ('conical','exponential','hypex','tractrix','biradial') and key not in names: add(key,0.0,plane+' throat blend length; zero skips blend','mm','registry.DEFAULT_KNOBS','fixed off')
 # Without a brief_file/embedded brief the CLI must supply one; do not invent it.
 source=root/c['path']; brief_file=c['brief_file']; brief=None
 if brief_file:
  bp=(source.parent/brief_file).resolve()
  if bp.exists(): brief=yaml.safe_load(bp.read_text(encoding='utf-8'))
 if brief is None:
  d=_load_yaml_extends(source); brief=d.get('brief')
 if isinstance(brief,dict):
  for k,v in (brief.get('driver') or {}).items(): add('brief.driver.'+k,v,{'exit_radius_mm':'driver coupling-plane radius','exit_angle_deg':'driver exit wall half-angle','throat_angle_policy':'brief policy for native throat angle'}.get(k,'brief driver field'),unit(k),'referenced or embedded brief')
 else:
  add('brief.driver',None,'driver exit radius and angle depend on externally supplied brief; not resolved from config',origin='brief absent',activity='unresolved: supply --brief or embedded brief')
 for x in c['parameters']:
  k=x['key']; activity=x['activity']
  if k in ('s1','s2'): x['units']='mm/deg' if k=='s1' else '1/mm'; x['meaning']='throat stretch coefficient: x_stretched = x + s1*degrees(atan(s2*x))'; x['activity'] += '; requires both s1 and s2 nonzero'
  if k.startswith('morph_') and k!='morph_target':
   x['activity'] += '; inactive if morph_target=0'
   if k=='morph_corner_mm': x['activity'] += '; corner applies to rectangular target only'
   if k=='morph_exponent': x['activity'] += '; exponent applies to superellipse target 3 only'
  if k.startswith('az_sf_'): x['activity'] += '; azimuth superformula affects wall only when az_a_sf_amp nonzero'
  if k=='az_a_cos_pow': x['activity'] += '; inactive when az_a_cos_amp=0'
  if k in ('r0_mm','a0_deg') and (seeds.get('throat_ext_length_mm') or 0)>0:
   x['activity'] += '; evaluated value derived from driver exit and extension, not independent: r0=exit_radius+length*tan(angle), a0=angle'
  elif k=='r0_mm' and c['family']=='OSSE': x['activity'] += '; fresh supplied brief pins radius to driver, unless extension active; embedded replay retains saved config'
  if k in ('n','s','k','q','g_n','g_s','g_k','g_q') and (c['family']=='OSSE' or rt=='osse_rollback'):
   x['meaning']={'n':'OSSE superellipse termination exponent','s':'OSSE termination amplitude','k':'OSSE base throat-to-wall shape factor','q':'OSSE normalized termination saturation'}[k.removeprefix('g_')]
   if k in ('n','q','g_n','g_q'): x['activity'] += '; termination term inactive when s=0'
  if rt=='rosse_rect' and k in ('g_k','g_q','g_m','g_r','g_b','g_tmax'):
   x['meaning']={'g_k':'R-OSSE throat radius-curve shape factor','g_q':'R-OSSE throat-to-mouth radius blend exponent','g_m':'R-OSSE dimensionless axial-map shoulder','g_r':'R-OSSE dimensionless axial-map rounding parameter, not physical radius','g_b':'R-OSSE secondary quadratic axial-map weight','g_tmax':'R-OSSE terminal parametric coordinate'}[k]
   if k=='g_b': x['activity'] += '; secondary axial term vanishes at zero'
  if k in ('h_n','v_n') and c['name']=='hl__biradial_es_style_v7': x['meaning']='plane-specific power n in r=r0+tan(a)z+c*z^n, with c constrained by mouth radius and length'
  if k in ('h_T','v_T'): x['meaning']='plane-specific hypex hyperbolic profile parameter T; T=1 gives exponential limit'
  if k=='g_T' and rt=='iwata_ar': x['meaning']='Le Cléach march hyperbolic profile parameter T in the Iwata aspect-stretch reconstruction'
  if k.startswith('g_sf_') and rt=='osse_rollback' and k not in ('g_sf_amt',): x['activity'] += '; superformula shape inactive when g_sf_amt=0'
(out/'domains_current.json').write_text(json.dumps({'scope':'YAML snapshot; see DOMAINS_AND_PATHS.md for coupling, identity and limitations','configs':configs},indent=2),encoding='utf-8')
with (out/'domains_current.csv').open('w',encoding='utf-8',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print('configs',len(configs),'parameter rows',len(rows),'searched',sum(r['search'] for r in rows))
for c in configs: print(c['name'],c['generator'].get('rows'),sum(x['search'] for x in c['parameters']))
