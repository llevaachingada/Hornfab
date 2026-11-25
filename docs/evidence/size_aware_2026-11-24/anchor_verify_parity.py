"""Fresh CPU meshes and production verify spec comparison; never invokes a solver."""
import dataclasses, hashlib, json, sys, tempfile
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from hornlab_search.config import load_config, mesh_spec, solve_spec
from hornlab_search.design.space import DesignSpace
from hornlab_search.mesh.build import build_mesh
from hornlab_search.types import Design

dest=Path('docs/evidence/size_aware_2026-11-24')
cases=[('rolled','20261124T000037Z-screen-f8a896','fa5b207bca6d'),('lame','20261123T235306Z-screen-0a4f8a','0782945027ae')]
report={}
def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def plain(x): return dataclasses.asdict(x) if dataclasses.is_dataclass(x) else x
for name,run,design in cases:
    root=Path('runs')/run
    paths=[root/'config.yaml',dest/f'anchor_{name}_neutral.yaml',dest/f'anchor_{name}_variant.yaml']
    configs=[load_config(p) for p in paths]
    specs=[{'mesh_spec':plain(mesh_spec('verify',c)), 'solve_spec':plain(solve_spec('verify',c)),
            'mesh_config':plain(c.mesh), 'target_raw':c.target_raw,'weights':c.weights,
            'objective_version':c.objective_version,'objective_params':c.objective_params,'brief':c.brief} for c in configs]
    diff={k:[specs[i][k]==specs[0][k] for i in (1,2)] for k in specs[0]}
    dj=json.loads((root/'designs'/design/'design.json').read_text(encoding='utf-8'))
    designs=[Design(family=dj['family'],params=dj['params']),DesignSpace.from_config(configs[1]).seed]
    with tempfile.TemporaryDirectory(prefix='anchor-verify-parity-') as td:
        built=[]
        for i in range(2):
            work=Path(td)/str(i); work.mkdir()
            mesh=build_mesh(designs[i],mesh_spec('verify',configs[i]),configs[i],work,mode='verify')
            built.append({'sha256':digest(mesh.path),'triangles':mesh.n_triangles,'res_mm':mesh.res_mm})
        ref=Path('runs/rolled_lame_anchor_verify_2026-11-24')/name/'designs'/design/'mesh.msh'
        report[name]={'spec_parity_neutral_variant':diff,'fresh_anchor':built[0],'fresh_neutral':built[1],
                      'saved_verify_mesh_sha256':digest(ref),'fresh_byte_identical':built[0]['sha256']==built[1]['sha256'],
                      'fresh_anchor_matches_saved_verify':built[0]['sha256']==digest(ref)}
(dest/'anchor_verify_parity.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2))
