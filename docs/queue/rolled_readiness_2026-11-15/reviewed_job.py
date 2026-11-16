"""Fail-closed entry for this review packet. --check performs no meshing or solving."""
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
HERE = Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--cell',required=True)
    p.add_argument('--seed',type=int,default=1234)
    p.add_argument('--check',action='store_true')
    a=p.parse_args()
    packet=json.loads((HERE/'admission.json').read_text())
    cell=packet['cells'][a.cell]
    config=ROOT/cell['config']
    for file,want in cell['pins'].items():
        if hashlib.sha256((ROOT/file).read_bytes()).hexdigest()!=want:
            raise SystemExit('HELD: pinned file changed: '+file)
    if cell['bridge']:
        importlib.import_module('tools.geometry.'+cell['bridge']).install()
    from hornlab_search.config import load_config
    from hornlab_search.design.space import DesignSpace
    cfg=load_config(config)
    space=DesignSpace.from_config(cfg)
    print(a.cell,'config/seed loaded;',len(space.keys()),'active dimensions; admission',cell['status'],flush=True)
    if a.check:
        return 0
    if not packet['full_search_released'] or cell['status']!='approved':
        raise SystemExit('HELD: resolve admission gates and explicit full-search release; no search launched')
    if a.seed not in (1234,5678):
        raise SystemExit('HELD: this packet admits only the two reviewed RNG seeds')
    cli=['tools/geometry/'+cell['bridge']+'.py'] if cell['bridge'] else ['-m','hornlab_search.cli']
    return subprocess.call([sys.executable,*cli,'search','--config',str(config),
        '--mode','screen','--budget','30','--cma-seed',str(a.seed)],cwd=ROOT)

if __name__=='__main__':
    raise SystemExit(main())
