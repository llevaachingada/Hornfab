"""Read-only: resolve every BoTorch study arm to its lane config."""
import sqlite3, pathlib, json, sys
REPO = pathlib.Path(r'C:\Users\hunte\Hrns\hornlab-search')
sys.path.insert(0, str(REPO))
from hornlab_search.studies import builders

for p in sorted((REPO / 'runs').rglob('studies.sqlite3')):
    arm = p.parent
    if arm.name == 'studies':
        continue
    con = sqlite3.connect('file:' + str(p.resolve()) + '?mode=ro', uri=True)
    try:
        row = con.execute('select spec_json from revisions order by revision desc limit 1').fetchone()
        if not row:
            print(arm.parent.name + '/' + arm.name, 'NO SPEC')
            continue
        spec = json.loads(row[0])
        task = spec.get('task') or {}
        cfg = None
        if 'name' in task:
            entry = builders._TASK_REGISTRY.get(task['name'])
            cfg = str(entry['config']) if entry else None
        else:
            cfg = task.get('config')
        name = None
        if cfg and pathlib.Path(cfg).is_file():
            import yaml
            try:
                name = yaml.safe_load(pathlib.Path(cfg).read_text()).get('name')
            except Exception as e:
                name = f'ERR {e}'
        nobs = con.execute('select count(*) from observations').fetchone()[0]
        print(arm.parent.name + '/' + arm.name, '| obs', nobs, '| task', json.dumps(task)[:90], '| config_name', name)
    finally:
        con.close()
