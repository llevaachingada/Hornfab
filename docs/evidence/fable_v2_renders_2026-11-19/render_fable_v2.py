import sys,glob,json,yaml,copy,numpy as np; sys.path.insert(0,'.')
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from hornlab_search.design.generators import grid as G, record_body as RB, klangfilm_lame_family as KF, rolled_family as RF
def kl():
    d=glob.glob('docs/evidence/runs/*517217')[0]; b=yaml.safe_load(open(d+'/config.yaml'))['brief']
    gb=json.load(open(d+'/designs/88973b1e44e9/design.json'))['params']['grid']
    s={'name':'grid','rows':{'type':'klangfilm_lame_v1'},'n_phi':gb['n_phi'],'n_s':gb['n_s'],'wall_thickness_mm':3.0,'span':'quarter'}
    return np.asarray(KF.resolve_grid(G.design_params(s,gb['knobs'],b)['grid'],b)['inner_points'])
def rr():
    d=glob.glob('docs/evidence/runs/*643de7')[0]; src=yaml.safe_load(open(d+'/config.yaml'))
    k=json.load(open(d+'/designs/445dafb7e760/design.json'))['params']['grid']['knobs']; g=copy.deepcopy(src['generator']); g.pop('seed_policy',None)
    return np.asarray(RF.resolve_grid(G.design_params(g,k,src['brief'])['grid'],src['brief'])['inner_points'])
def edit(inner,kn):
    from hornlab_search.geometry import record as R
    rec=R.SurfaceRecord(inner,np.zeros(inner.shape[:2]),'h',wall_thickness_mm=3.0)
    sp=RB.spec_from_record(rec,wall_thickness_mm=3.0,source_auto_angle_deg=2.0)
    return np.asarray(RB.resolve_grid({**sp,'knobs':kn},{})['inner_points'])
def full(q):  # mirror quarter to full surface
    P=[q,q*[-1,1,1],q*[-1,-1,1],q*[1,-1,1]]
    return P
def draw(name,host,variants):
    fig=plt.figure(figsize=(16,9),facecolor='#1b232a')
    cols=['#e0a040','#4fc3c7','#c77dff']
    for i,(lab,q) in enumerate([('host (best so far)',host)]+variants):
        ax=fig.add_subplot(2,len(variants)+1,i+1,projection='3d'); ax.set_facecolor('#1b232a')
        for P in full(q): ax.plot_surface(P[:,:,0],P[:,:,2],P[:,:,1],color='#b8c4cc',linewidth=0,antialiased=True,shade=True,alpha=.95)
        ax.view_init(18,-58); ax.set_box_aspect((600,480,480)); ax.set_axis_off(); ax.set_title(lab,color='w',fontsize=10)
    for j,(plane,row,ttl) in enumerate([('x',0,'horizontal section'),('y',-1,'vertical section')]):
        ax=fig.add_subplot(2,2,3+j); ax.set_facecolor('#1b232a')
        for c,(lab,q) in zip(cols,[('host',host)]+variants):
            r=q[row,:,0 if plane=='x' else 1]; z=q[row,:,2]
            ax.plot(r,z,color=c,lw=2,label=lab); ax.plot(-r,z,color=c,lw=2)
        ax.axhline(0,color='#555',lw=.6); ax.set_aspect('equal'); ax.set_title(ttl,color='w'); ax.tick_params(colors='#aaa')
        ax.set_xlabel('mm',color='#aaa'); ax.set_ylabel('z mm (throat at 0)',color='#aaa')
        for s in ax.spines.values(): s.set_color('#555')
        if j==0: ax.legend(facecolor='#1b232a',labelcolor='w',fontsize=8)
    fig.suptitle(name,color='w',fontsize=13); fig.tight_layout(); out=f'/tmp/claude-0/r/{name.split()[0]}.png'; fig.savefig(out,dpi=110,facecolor=fig.get_facecolor()); print(out)
k=kl(); h=RB.host_mouth_height_mm(k)
draw('Klangfilm-Lame c200 -> vbeak lane',k,[('beak 35 mm',edit(k,{'g_beak_v_mm':35.,'g_beak_start':0.4})),('V mouth 400 mm + beak 25',edit(k,{'g_vt_mm':400.,'g_vt_hold':0.2,'g_beak_v_mm':25.,'g_beak_start':0.4}))])
r=rr()
draw('Rolled-rect h12 -> vbeak lane',r,[('beak 35 mm',edit(r,{'g_beak_v_mm':35.,'g_beak_start':0.4})),('V mouth 400 mm + beak 25',edit(r,{'g_vt_mm':400.,'g_vt_hold':0.2,'g_beak_v_mm':25.,'g_beak_start':0.4}))])
