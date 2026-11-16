"""Build local review artifacts from this audit's saved evidence. No production mutation."""
import copy
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FixedLocator, FuncFormatter, NullLocator

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]

COMMON = [
 'All resolved physical values finite; every seed present and inside its own declared domain; fixed values equal both endpoints.',
 'Finished inner+outer+closure envelope W<=600 mm,H<=480 mm,D<=480 mm and W>H; nominal dimensions are not the test.',
 'Driver connection radius18 mm; physical tangent/source-cap policy must be resolved per family, including R-OSSE and extended-throat cases.',
 'Reject nonpositive radius, degeneracy, nonmanifold connectivity, unintended intersections/clearance failure and invalid source cap before acoustics; preserve refusal records.',
 'No silent clipping onto another candidate; canonical full-boundary duplicate identity and inherited config/source/recipe/brief/mesh/solve hashes required.',
 'No acoustic launch under this document; separate objective, geometry, replay and validation gates apply.'
]


def constraints(c):
    n = c['name']
    more = []
    if 'biradial_es_style' in n:
        more += ['For j=H,V: rm_j >= 18+L*tan(a_j*pi/180); n_j>=1 and finite derived c=(rm_j-18-L*tan(a_j))/L**n_j. This is construction closure, not a beamwidth prediction.',
                 'Resolve actual 25 mm throat blend in both planes; check its endpoint derivatives and full-body envelope. Preserve stock corrected config separately from failed old runs.']
    if 'crowe_es_biradial_rr' in n:
        more += ['This is Hypex, not the Crowe spiral or Keele bi-radial. Use actual hypex inversion/finite-curvature/max-wall-angle guards for both planes; rounded mouth corner <=min(half-width,half-height).',
                 'No acoustic domain proposed under Crowe attribution; retain numeric box for neutral Hypex CPU reference only.']
    if 'crowe_panel' in n or 'sp__' in n or 'rf__section' in n:
        more += ['0.9<=h_depth_scale<=1.1; 0<=crown<0.2*height;16<=junction_power<=48;0<throat_blend<0.2*depth.',
                 'Use actual _sweep tests: max(zH)<max(zV),positive pivot,single-peaked sweep radius,compatible return domains,real radicand and source blend after inverse exists. Do not substitute empirical depth<=0.57*width for these exact tests.',
                 'Outer return/closure needs off-axis tangent,intersection and clearance audit; consistent winding alone is insufficient.']
    if 'rr__' in n and 'crowe' not in n or 'rolled_es_spiral' in n or 'rf__rect' in n:
        more += ['width>height>36;0<throat_turn<rect_turn<90 degrees;180<terminal<=280 degrees;0.5<=depth_h_ratio<=1.2;2<=rect_exponent<=16;decay>0.',
                 'Original axial law only: throat_turn<pucker_start<180 degrees and max(abs(H),abs(V))<=0.15*depth. No replacement with ATH radial morph.',
                 'Shared normalized spiral law lacks separate H/V flare-rate/angle controls; box retained for CPU hypothesis study, not broad coverage optimization.']
    if n.startswith('sp__'):
        more += ['Window onset<peak<end and onset beyond actual throat blend; end before returned attachment; z-only signed relief, preserve x/y.']
    if n.startswith('rf__'):
        more += ['Inactive axial/radial controls exactly0; start_hi<peak_lo<end_lo and window starts after source neighbourhood; end before final2 grid stations.',
                 'With active amplitude domains including0, keep window placement fixed for this matched amplitude experiment. This is an identifiability rule, not proof placement never matters.',
                 'Positive rho-relief, no pre-roll radial constriction, nondegenerate inner+outer sheets and native self-approach guard. Reference arc station is not axial-depth fraction.']
    if 'rosse_rect' in n:
        more += ['R(phi)=(|cos(phi)/(W/2)|**p+|sin(phi)/(H/2)|**p)**(-1/p), a(phi)=aV+(aH-aV)*cos(phi)**2+aDiag*sin(2*phi)**2.',
                 'Use actual R-OSSE domain at EVERY azimuth; fixed r0=18 mm; r and m are dimensionless; depth and terminal radius follow parametric law+tmax, not W/H labels alone.',
                 'Resolve physical tangent: for unstretched q>1,k>0, initial dr/dz=tan(a0)*sqrt(r*r+m*m)/m. Raw a0=driver2deg does not guarantee2deg spatial tangent.',
                 'Current m=.85,q=3,aDiag=0 are a reference slice, not evidence they should remain fixed in final optimization. Their future domains need source/domain/control experiments.']
    if 'crowe_x' in n:
        more += ['Evaluate actual OSSE+superformula+lip+outer shell extents; existing corners exceed600 mm. Reject combinations before meshing; do not shrink aH/aV merely to fit.',
                 'Positive k,n,L; s>=0;0<q<=1; mirror-safe fixed sf_m=4; all polar angles in supported range; check lip/corner clearance and actual tangent return.',
                 'Fixed k=1,q=.996 and superformula shape are reference restrictions. Do not claim independent loading/pucker optimization until those controls are audited; do not blindly widen them.']
    if n in ('hl__ath_core_petal_hvlaw_v7','hl__ext_throat_hvlaw_v7','hl__osse_rrect_morph_v7'):
        more += ['Evaluate complete azimuth functions a(phi),n(phi),s(phi); require valid OSSE at every azimuth, round driver and quarter symmetry (superformula m multiple4 when required).',
                 'Morph target0 makes target dimensions/rate/corner/exponent inactive; use per-law activity mapping, never count inactive dimensions as distinct physical observations.']
    if 'ext_throat' in n:
        more += ['Derive main r0=18+extension_length*tan(extension_angle*pi/180),main a0=extension_angle. The source connection and extension entrance policy need explicit checking; these are not two additional independent knobs.']
    if 'lecleach' in n or 'es_style_rollback' in n:
        more += ['LeCleach march validity and circular throat before aspect stretch; terminal curve coordinate is not a Crowe wrap angle. Check aspect progression+return+outer-body envelope jointly.']
    return COMMON + more


def domains():
    current=json.loads((HERE/'domains_current.json').read_text())
    out={'kind':'proposed_cpu_review_domains_not_launch_configuration',
         'acoustic_search_authorized':False,'reason':'Law/objective/body and convergence gates unresolved; no arbitrary larger replacement boxes.',
         'configs':[]}
    lines=['# Exact proposed review domains\n',
     'Every range below is a **CPU review domain**, intersected with the listed physical/construction constraints. No family receives an approved acoustic optimization domain from this audit. A source law or capability gap cannot be repaired by choosing a larger box. Original files and recipes stay unchanged. Numeric domains, seeds, transforms, activity and nominal initial physical steps are carried verbatim from the resolved inventory; fixed controls are explicit. This is a bounded proposal to test or reject current domains before any future short pilot.\n',
     'For linear bounds the nominal starting step is sigma0*(hi-lo); fixed step0. Log bounds use the recorded asymmetric steps. These are current, unbounded initial standard deviations, not promises that they fit a useful acoustic basin. A later30-call pilot must set its step using measured local feasibility and incumbent spread, retaining all useful controls. No invented uniform small sigma is approved.\n',
     'Per-key meanings and activity: [semantics](domains_semantics.md). Current evidence: [inventory JSON](domains_current.json). The generator/sampling/driver fixed rows below are physical identity inputs, not searched controls. Untraced dependency defaults remain a blocking inventory gap, rather than fabricated values.\n']
    for c in current['configs']:
        proposal=copy.deepcopy(c)
        proposal['domain_status']='CPU review only; acoustic optimization blocked'
        proposal['coupled_constraints']=constraints(c)
        proposal['approved_acoustic_domain']=None
        for p in proposal['parameters']:
            if not p.get('search'):
                p['nominal_sigma_step']=0
                p['nominal_sigma_minus']=p['nominal_sigma_plus']=0
        out['configs'].append(proposal)
        lines += ['\n## '+c['name']+'\n',
                  f"Source `{c['path']}`, SHA256 `{c['sha256']}`. Starting unit sigma `{c['sigma0']}`; blocked for acoustics.\n",
                  '| Key | Physical meaning / unit | Seed | Proposed bounds | Transform / activity | Initial physical step |',
                  '|---|---|---|---|---|---|']
        for p in proposal['parameters']:
            value=str(p.get('seed')).replace('|','\\|')
            bounds=(str(p.get('lo'))+' .. '+str(p.get('hi'))) if p.get('search') else 'fixed '+value
            lines.append(f"| `{p['key']}` | {p.get('meaning','')} / {p.get('units','')} | {value} | {bounds} | {p.get('transform','')} / {p.get('activity','')} | {p.get('nominal_sigma_step',0)} |")
        lines += ['\nCoupled constraints:\n']+['- '+s for s in proposal['coupled_constraints']]
    (HERE/'domains_proposed.json').write_text(json.dumps(out,indent=2)+'\n')
    (HERE/'PARAMETER_DOMAINS.md').write_text('\n'.join(lines)+'\n')


def plots():
    data=json.loads((HERE/'objective_ablation.json').read_text())
    selected=[('d3a1bb','OSSE extended throat'),('07bea2','OSSE rounded rectangle'),('32f7c4','Crowe home sections'),('d4a7c4','Original spiral control'),('e31b23','Le Cleach aspect family')]
    fig,axs=plt.subplots(1,3,figsize=(16,4.6),layout='constrained')
    for suffix,label in selected:
        r=next(r for r in data['runs'] if r['run'].endswith(suffix))
        c=min(r['response_checks'],key=lambda c:c['stored_J'])
        for ax,key in zip(axs,('bw_h_deg','bw_v_deg','di_db')):
            ax.semilogx(c['freqs_hz'],c[key],marker='.',ms=3,label=label)
    for ax,title in zip(axs,('Horizontal beamwidth','Vertical beamwidth','Balloon DI')):
        ax.set_title(title);ax.set_xlabel('Frequency (Hz)');ax.grid(alpha=.22);ax.axvline(700,color='gray',ls=':',lw=1)
        ax.set_xlim(350,8000)
        ax.xaxis.set_major_locator(FixedLocator([400,700,1000,2000,4000,8000]))
        ax.xaxis.set_minor_locator(NullLocator())
        ax.xaxis.set_major_formatter(FuncFormatter(lambda x,pos: f'{int(x):,}'))
    axs[0].axhline(80,color='gray',ls='--',lw=1);axs[1].axhline(50,color='gray',ls='--',lw=1)
    axs[0].set_ylabel('Total half-pressure crossings (deg)');axs[1].set_ylabel('Total half-pressure crossings (deg)');axs[2].set_ylabel('dB: axis / full-sphere mean power')
    axs[0].legend(fontsize=7)
    fig.suptitle('Saved original-v7 winners: stored acoustic data, no new solves; Crowe junction unresolved',fontsize=12)
    fig.savefig(HERE/'objective_curves.png',dpi=160)
    plt.close(fig)


if __name__=='__main__':
    domains();plots()
    print('WROTE PARAMETER_DOMAINS.md, domains_proposed.json, objective_curves.png')
