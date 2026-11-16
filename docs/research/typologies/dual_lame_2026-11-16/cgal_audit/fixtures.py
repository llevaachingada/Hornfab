import json, tempfile, os
from pathlib import Path
from CGAL.CGAL_Polyhedron_3 import Polyhedron_3
from CGAL.CGAL_Polygon_mesh_processing import does_self_intersect
A=[(0,0,0),(2,0,0),(0,2,0)]
cases={'cross':(A+[(.5,.5,-1),(.5,.5,1),(1,.5,0)], [[0,1,2],[3,4,5]],True),
'coplanar_containment':(A+[(.2,.2,0),(1,.2,0),(.2,1,0)], [[0,1,2],[3,4,5]],True),
'coplanar_cross':(A+[(1,-1,0),(3,1,0),(-1,1,0)], [[0,1,2],[3,4,5]],True),
'separate':(A+[(3,3,0),(4,3,0),(3,4,0)], [[0,1,2],[3,4,5]],False),
'near_parallel':(A+[(.2,.2,1e-12),(1,.2,1e-12),(.2,1,1e-12)], [[0,1,2],[3,4,5]],False),
'shared_edge':(A+[(1,-1,0)],[[0,1,2],[1,0,3]],False),
'adjacent_overlap':(A+[(.2,.2,0)],[[0,1,2],[1,0,3]],True)}
results={}
for name,(points,faces,expected) in cases.items():
 with tempfile.NamedTemporaryFile(mode='w',suffix='.off',delete=False) as f:
  f.write(f'OFF\n{len(points)} {len(faces)} 0\n')
  for v in points:f.write(' '.join(map(str,v))+'\n')
  for face in faces:f.write('3 '+' '.join(map(str,face))+'\n')
  path=f.name
 try:
  mesh=Polyhedron_3(path); valid=mesh.is_valid() and mesh.is_pure_triangle() and mesh.size_of_facets()==len(faces)
  actual=bool(does_self_intersect(mesh)) if valid else None
  results[name]={'expected':expected,'actual':actual,'valid_input':bool(valid),'pass':actual is expected}
 finally:os.unlink(path)
print(json.dumps(results,indent=2))
with open(Path(__file__).with_name('fixtures.json'),'w') as f:json.dump(results,f,indent=2)
