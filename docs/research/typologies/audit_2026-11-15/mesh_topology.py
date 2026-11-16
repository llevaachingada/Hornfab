from pathlib import Path
import numpy as np, meshio, json, csv, collections, hashlib, math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

ROOT=Path('.'); OUT=ROOT/'docs/research/typologies/audit_2026-11-15'; B=ROOT/'scratch/2026-11-15_biradial_audit'
FILES={'crowe_seed':B/'seed_meshes/hl__crowe_panel_home_v7/mesh.msh','crowe_winner':ROOT/'runs/20261115T205453Z-screen-32f7c4/designs/22365b569be9/mesh.msh','ext_throat_seed':B/'seed_meshes/hl__ext_throat_hvlaw_v7/mesh.msh','es_spiral_seed':B/'es_meshes/hl__rolled_es_spiral_v7_seed/mesh.msh','rosse_seed':B/'rosse_rect_meshes/hl__rosse_rect_cd_v7_seed/mesh.msh','crowe_x_seed':B/'crowe_x_meshes/hl__crowe_x_osse_cd_v7_seed/mesh.msh','biradial_seed':B/'corner_meshes/hl__biradial_es_style_v7_seed/mesh.msh'}

def witness(label,pts,tris,normals,edge,triids):
 fig=plt.figure(figsize=(14,9)); ax=fig.add_subplot(221,projection='3d'); face=pts[tris]; ax.add_collection3d(Poly3DCollection(face,facecolor='#bf9267',edgecolor='none',alpha=1)); ax.auto_scale_xyz(*[(pts[:,i].min(),pts[:,i].max()) for i in range(3)]); ax.set_box_aspect(np.ptp(pts,axis=0)); ax.view_init(22,-55); ax.set_title('Original quarter mesh (flat facets)');ax.set_xlabel('x m');ax.set_ylabel('y m');ax.set_zlabel('z m')
 ax=fig.add_subplot(222,projection='3d',computed_zorder=False); center=pts[list(edge)].mean(0); radius=max(np.linalg.norm(pts[edge[0]]-pts[edge[1]])*8,0.008); select=np.flatnonzero(np.linalg.norm(face.mean(axis=1)-center,axis=1)<radius); poly=Poly3DCollection(face[select],facecolor='#e2bc91',edgecolor='#6f625a',linewidth=.22,alpha=.5,zorder=1);ax.add_collection3d(poly); ax.plot(*pts[list(edge)].T,color='red',linewidth=4,zorder=10)
 for tid,col in zip(triids,['blue','green']):
  c=face[tid].mean(axis=0);v=normals[tid]*radius*.55;ax.quiver(*c,*v,color=col,linewidth=2,arrow_length_ratio=.2,zorder=11)
 for i in range(3):getattr(ax,['set_xlim','set_ylim','set_zlim'][i])((center[i]-radius,center[i]+radius))
 ax.set_box_aspect((1,1,1));ax.view_init(25,-45);ax.set_title('Worst shared edge; red edge, blue/green raw normals');ax.set_xlabel('x');ax.set_ylabel('y');ax.set_zlabel('z')
 for idx,deg in enumerate((22.5,45),start=3):
  ax=fig.add_subplot(2,2,idx); ang=math.radians(deg); h=pts[:,1]*math.cos(ang)-pts[:,0]*math.sin(ang)
  for tri in tris:
   pp=pts[tri]; hh=h[tri]; intersections=[]
   for j in range(3):
    a,b=j,(j+1)%3
    if hh[a]*hh[b]<0:
     q=pp[a]+(-hh[a]/(hh[b]-hh[a]))*(pp[b]-pp[a]);intersections.append(q)
   if len(intersections)==2:
    q=np.array(intersections);ax.plot(q[:,2],np.hypot(q[:,0],q[:,1]),color='black',lw=.3)
  ax.set_title(f'Original triangles, radial plane {deg}°');ax.set_xlabel('z m');ax.set_ylabel('radius m');ax.axis('equal')
 fig.suptitle(label+' — raw saved mesh; no normal orientation correction');fig.tight_layout();fig.savefig(OUT/f'mesh_witness_{label}.png',dpi=160);plt.close(fig)

results=[]
for label,path in FILES.items():
 m=meshio.read(path); pts=np.asarray(m.points,dtype=float); groups=[i for i,c in enumerate(m.cells) if c.type=='triangle']; tris=np.vstack([m.cells[i].data for i in groups]); tags={k:np.concatenate([np.asarray(v[i]) for i in groups]) for k,v in m.cell_data.items() if len(v)==len(m.cells)}
 crosses=np.cross(pts[tris[:,1]]-pts[tris[:,0]],pts[tris[:,2]]-pts[tris[:,0]]); length=np.linalg.norm(crosses,axis=1); degenerate=np.flatnonzero(length<=1e-18); norms=np.divide(crosses,length[:,None],out=np.zeros_like(crosses),where=length[:,None]>1e-18); edges=collections.defaultdict(list)
 for i,(a,b,c) in enumerate(tris):
  for u,v in ((a,b),(b,c),(c,a)):edges[tuple(sorted((int(u),int(v))))].append((int(u),int(v),i))
 cnt=collections.Counter(len(x) for x in edges.values()); boundaries=collections.Counter(); same=0; angle=[]
 for (a,b),inc in edges.items():
  if len(inc)==1:
   x=bool(np.all(np.abs(pts[[a,b],0])<=1e-8));y=bool(np.all(np.abs(pts[[a,b],1])<=1e-8));boundaries['both' if x and y else 'x=0' if x else 'y=0' if y else 'other']+=1
  if len(inc)!=2:continue
  aa,bb,i=inc[0];cc,dd,j=inc[1]; same+=int(aa==cc and bb==dd)
  if length[i]<=1e-18 or length[j]<=1e-18:continue
  n1,n2=norms[i],norms[j]; dot=float(np.clip(np.dot(n1,n2),-1,1)); v=pts[bb]-pts[aa]; v=v/np.linalg.norm(v); raw=math.degrees(math.acos(dot)); signed=math.degrees(math.atan2(np.dot(v,np.cross(n1,n2)),dot));angle.append((raw,signed,(aa,bb),i,j))
 angle.sort(reverse=True,key=lambda x:x[0]); faces=collections.Counter(tuple(sorted(map(int,t))) for t in tris);duplicate_faces=sum(c-1 for c in faces.values() if c>1); _,coordcounts=np.unique(pts,axis=0,return_counts=True)
 def detailed(a):
  raw,signed,edge,i,j=a
  return {'raw_deg':raw,'signed_deg':signed,'edge_vertex_ids':edge,'edge_xyz_m':pts[list(edge)].tolist(),'triangle_indices':[i,j],'triangle_vertex_ids':tris[[i,j]].tolist(),'normals':[norms[i].tolist(),norms[j].tolist()],'tags':{k:[int(v[i]),int(v[j])] for k,v in tags.items()}}
 vals=np.array([a[0] for a in angle]);r={'label':label,'path':str(path).replace('\\','/'),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'points':len(pts),'triangles':len(tris),'degenerate_cross_m2_le_1e-18':len(degenerate),'duplicate_index_faces':duplicate_faces,'duplicate_exact_coordinate_points':int(np.sum(coordcounts-1)),'edge_incidence_counts':{str(k):v for k,v in sorted(cnt.items())},'same_directed_shared_edges':same,'opposite_directed_shared_edges':cnt[2]-same,'boundary_edges_by_plane_tol_1e-8m':dict(boundaries),'angle_counts_gt_90_150_170':{str(t):int(np.sum(vals>t)) for t in (90,150,170)},'max_raw_angle_deg':float(vals.max()),'worst_edges':list(map(detailed,angle[:10]))};results.append(r)
 if label in ('crowe_seed','crowe_winner'):witness(label,pts,tris,norms,angle[0][2],angle[0][3:])
 print(label,'tri',len(tris),'inc',dict(cnt),'same',same,'boundary',dict(boundaries),'degenerate',len(degenerate),'duplicates',duplicate_faces,'rawmax',round(float(vals.max()),3),'gt150',int(np.sum(vals>150)))
(OUT/'mesh_topology.json').write_text(json.dumps({'method':'Original index connectivity; no welding or reorientation; cross norm <=1e-18 m^2 degenerate. acos(n1 dot n2) is 0 smooth and 180 opposed; signed atan2(edge1 dot cross(n1,n2), n1 dot n2), edge1 from triangle1. Sign depends on orientation and triangle order, not a universal convexity convention. No intersection or clearance test performed.','meshes':results},indent=2)+'\n')
with (OUT/'mesh_topology.csv').open('w',newline='') as f:
 fields=['label','path','sha256','points','triangles','degenerate_cross_m2_le_1e-18','duplicate_index_faces','duplicate_exact_coordinate_points','edge_incidence_counts','same_directed_shared_edges','opposite_directed_shared_edges','boundary_edges_by_plane_tol_1e-8m','angle_counts_gt_90_150_170','max_raw_angle_deg'];w=csv.DictWriter(f,fields,extrasaction='ignore');w.writeheader();w.writerows(results)

