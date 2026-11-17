"""Range-plus-constancy coverage scoring, replayed on stored rows (read-only, zero GPU).
H range 60-80 deg, V range 40-60 deg. Compares three coverage costs:
  point    : v7 style, distance to 80 / 50 at every frequency
  corridor : v9 style, zero inside the range at each frequency (no constancy requirement)
  constant : zero only if INSIDE the range AND constant: mean_f (bw - c*)^2, c* = clip(mean bw, lo, hi)
"""
import pickle, numpy as np, collections
from scipy.stats import spearmanr
rows=[r for r in pickle.load(open('scratch/fable_architecture/.fable/rows.pkl','rb')) if r['ok'] and r['f'] and len(r['f'])==18]
f=np.array(rows[0]['f'])
def costs(bw,lo,hi,pt,band):
    b=np.asarray(bw,float)[band]
    point=np.mean((b-pt)**2)/100
    corr=np.mean(np.where(b<lo,(lo-b)**2,np.where(b>hi,(b-hi)**2,0.0)))/100
    c=np.clip(b.mean(),lo,hi); const=np.mean((b-c)**2)/100
    return point,corr,const,b.mean(),b.std(),b.min(),b.max()
for v_on in (700,1000):
    bh=f>=700; bv=f>=v_on
    T=[]
    for r in rows:
        h=costs(r['bwh'],60,80,80,bh); v=costs(r['bwv'],40,60,50,bv)
        T.append((h[0]+0.5*v[0],h[1]+0.5*v[1],h[2]+0.5*v[2],h[3],h[4],v[3],v[4],r['J'],r['config'],r['brief'],h[1],h[5],h[6]))
    A=np.array([t[:8] for t in T],float)
    print(f'\n=== vertical scored from {v_on} Hz (H from 700 Hz); n={len(rows)} ===')
    print('rank correlation between coverage costs: point vs corridor %.2f, point vs constant %.2f, corridor vs constant %.2f'%(spearmanr(A[:,0],A[:,1])[0],spearmanr(A[:,0],A[:,2])[0],spearmanr(A[:,1],A[:,2])[0]))
    inH=np.array([t[10]==0 for t in T]); print('designs whose H beamwidth is inside 60-80 at EVERY scored frequency (corridor cost 0 in H): %d ; of those, H spread (max-min) > 10 deg: %d, > 15 deg: %d'%(inH.sum(), sum(1 for t in T if t[10]==0 and t[12]-t[11]>10), sum(1 for t in T if t[10]==0 and t[12]-t[11]>15)))
    zero=(A[:,1]==0).sum(); print('designs with corridor cost exactly 0 in BOTH planes (ties the corridor cannot rank):',zero)
    top_pt=set(np.argsort(A[:,0])[:50]); top_c=set(np.argsort(A[:,2])[:50]); top_co=set(np.argsort(A[:,1])[:50]); topJ=set(np.argsort(A[:,7])[:50])
    print('top-50 overlap: point&constant %d, corridor&constant %d, v7-J&constant %d'%(len(top_pt&top_c),len(top_co&top_c),len(topJ&top_c)))
    print('best 10 by CONSTANT-in-range cost:  cost | H level, H std | V level, V std | v7 J | lane')
    seen=collections.Counter()
    for i in np.argsort(A[:,2]):
        t=T[i]
        if seen[t[8]]>=2: continue
        seen[t[8]]+=1
        print(f'   {t[2]:.3f} | H {t[3]:4.0f} ±{t[4]:3.1f} | V {t[5]:4.0f} ±{t[6]:3.1f} | J {t[7]:5.2f} | {t[8][:38]} ({t[9]})')
        if sum(seen.values())>=10: break
    i=int(np.argmin(A[:,7])); t=T[i]; print(f'the v7 winner under this cost: {t[2]:.3f} (rank {int((A[:,2]<t[2]).sum())+1} of {len(T)}), H {t[3]:.0f} ±{t[4]:.1f}, V {t[5]:.0f} ±{t[6]:.1f}')
