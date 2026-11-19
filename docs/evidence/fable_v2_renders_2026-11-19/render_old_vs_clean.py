import sys,numpy as np; sys.path.insert(0,'.'); sys.path.insert(0,'tools/analysis')
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
import meridian_sanity as M
exec(open('/tmp/claude-0/render.py').read().split('def draw')[0].split('def edit')[0])
L='examples/typologies/fable_v2_2026-11-19/'
pairs=[('Klangfilm: c200 (old) vs Phase B core lane (new)',kl(),M.grid_for_config(L+'hl__klangfilm_hv_core_c200form_v10_v1.yaml')),
       ('Rolled rect: h12 (old) vs clean lane (new)',rr(),M.grid_for_config(L+'hl__rolled_rect_clean_v10_v1.yaml'))]
for title,old,new in pairs:
    fig=plt.figure(figsize=(16,9),facecolor='#1b232a')
    for i,(lab,q) in enumerate((('old best',old),('new lane seed',new))):
        ax=fig.add_subplot(2,2,i+1,projection='3d'); ax.set_facecolor('#1b232a')
        for P in (q,q*[-1,1,1],q*[-1,-1,1],q*[1,-1,1]): ax.plot_surface(P[:,:,0],P[:,:,2],P[:,:,1],color='#b8c4cc',linewidth=0,shade=True)
        ax.view_init(18,-58); ax.set_box_aspect((600,480,480)); ax.set_axis_off(); ax.set_title(lab,color='w')
    for j,(row,ttl,ix) in enumerate(((0,'horizontal section',0),(-1,'vertical section',1))):
        ax=fig.add_subplot(2,2,3+j); ax.set_facecolor('#1b232a')
        for c,lab,q in (('#e0a040','old',old),('#4fc3c7','new',new)):
            ax.plot(q[row,:,ix],q[row,:,2],color=c,lw=2,label=lab); ax.plot(-q[row,:,ix],q[row,:,2],color=c,lw=2)
        ax.set_aspect('equal'); ax.set_title(ttl,color='w'); ax.tick_params(colors='#aaa'); ax.set_xlabel('mm',color='#aaa'); ax.set_ylabel('z mm',color='#aaa')
        for s in ax.spines.values(): s.set_color('#555')
        if j==0: ax.legend(facecolor='#1b232a',labelcolor='w')
    fig.suptitle(title,color='w',fontsize=13); fig.tight_layout()
    out='docs/evidence/fable_v2_renders_2026-11-19/'+('klangfilm' if 'Klang' in title else 'rolled')+'_old_vs_clean.png'
    fig.savefig(out,dpi=110,facecolor=fig.get_facecolor()); print(out)
