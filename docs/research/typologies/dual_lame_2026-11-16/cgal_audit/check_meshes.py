import hashlib, json, os, sys, tempfile
from pathlib import Path
from CGAL.CGAL_Polyhedron_3 import Polyhedron_3
from CGAL.CGAL_Polygon_mesh_processing import does_self_intersect

def check(path):
 raw=path.read_bytes(); lines=raw.decode('ascii').splitlines()
 ni=lines.index('$Nodes'); n=int(lines[ni+1]); nodes={}
 for line in lines[ni+2:ni+2+n]:
  a=line.split(); nodes[int(a[0])]=tuple(map(float,a[1:4]))
 ei=lines.index('$Elements'); count=int(lines[ei+1]); faces=[]; types={}
 for line in lines[ei+2:ei+2+count]:
  a=list(map(int,line.split())); typ=a[1]; tags=a[2]; ids=a[3+tags:]; types[typ]=types.get(typ,0)+1
  if typ==2:faces.append(ids)
  else: raise ValueError(f'unsupported element type {typ}')
 ids=sorted(nodes); index={v:i for i,v in enumerate(ids)}
 with tempfile.NamedTemporaryFile(mode='w',suffix='.off',delete=False) as f:
  f.write(f'OFF\n{len(ids)} {len(faces)} 0\n')
  for i in ids:f.write(' '.join(format(x,'.17g') for x in nodes[i])+'\n')
  for face in faces:f.write('3 '+' '.join(str(index[x]) for x in face)+'\n')
  filename=f.name
 try:
  m=Polyhedron_3(filename)
  valid=m.is_valid() and m.is_pure_triangle() and m.size_of_facets()==len(faces) and m.size_of_vertices()==len(nodes)
  result={'file':str(path),'sha256':hashlib.sha256(raw).hexdigest(),'nodes':len(nodes),'triangles':len(faces),
          'element_types':types,'cgal_vertices':m.size_of_vertices(),'cgal_faces':m.size_of_facets(),
          'valid_polyhedron':bool(valid),'closed':bool(m.is_closed()),
          'self_intersects':bool(does_self_intersect(m)) if valid else None}
  return result
 finally:os.unlink(filename)

results=[check(Path(p)) for p in sys.argv[1:]]
print(json.dumps(results,indent=2))
with open(Path(__file__).with_name('meshes.json'),'w') as f:json.dump(results,f,indent=2)
