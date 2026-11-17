import pathlib, numpy as np, collections, json
from scipy.spatial import cKDTree

def patch_distance(pts,grid):
    a=grid[:-1,:-1].reshape(-1,3); b=grid[1:,:-1].reshape(-1,3)-a
    c=grid[:-1,1:].reshape(-1,3)-a; d=grid[1:,1:].reshape(-1,3)-a-b-c
    centres=a+.5*b+.5*c+.25*d
    inds=cKDTree(centres).query(pts,k=12)[1]
    out=[]
    for start in range(0,len(pts),1000):
        pp=pts[start:start+1000,None,:]; idx=inds[start:start+1000]
        A,B,C,D=a[idx],b[idx],c[idx],d[idx]
        u=np.full(idx.shape,.5); v=u.copy()
        for _ in range(14):
            res=A+u[...,None]*B+v[...,None]*C+(u*v)[...,None]*D-pp
            du=B+v[...,None]*D; dv=C+u[...,None]*D
            aa=np.sum(du*du,axis=-1); bb=np.sum(du*dv,axis=-1); cc=np.sum(dv*dv,axis=-1)
            rr=np.sum(du*res,axis=-1); ss=np.sum(dv*res,axis=-1); det=np.maximum(aa*cc-bb*bb,1e-14)
            u=np.clip(u-(cc*rr-bb*ss)/det,0,1); v=np.clip(v-(aa*ss-bb*rr)/det,0,1)
        err=np.linalg.norm(A+u[...,None]*B+v[...,None]*C+(u*v)[...,None]*D-pp,axis=-1)
        out.extend(err.min(axis=1))
    return np.array(out)

for f in sorted(pathlib.Path('scratch/fable_architecture/.x1').glob('*.npz')):
    rec=np.load(f); h=str(rec['design_hash']); lane=str(rec['lane']); run=str(rec['run']); mesh=pathlib.Path('runs')/run/'designs'/h/'mesh.msh'
    if not mesh.exists(): continue
    txt=mesh.read_text(); nt=txt.split('$Nodes\n',1)[1].split('$EndNodes',1)[0].splitlines(); nodes={int(z[0]):np.array(z[1:],float)*1000 for z in (x.split() for x in nt[1:] if x.strip())}
    entities=collections.defaultdict(set); et=txt.split('$Elements\n',1)[1].split('$EndElements',1)[0].splitlines()
    for line in et[1:]:
        p=line.split()
        if len(p)>=8 and p[1]=='2' and int(p[2])>=2 and p[3]=='1': entities[p[4]].update(map(int,p[-3:]))
    print(json.dumps({'lane':lane,'hash':h,'entities':{k:{'count':len(ids),'median_p99_mm':np.quantile(patch_distance(np.array([nodes[i] for i in sorted(ids)]),rec['inner']),[.5,.99]).tolist()} for k,ids in entities.items()}}),flush=True)
