"""Offline exploratory size/J summaries; run from the repository root."""
import collections
import hashlib
import json
import math
import sys
from pathlib import Path

from hornlab_search.design.size import full_bbox_extents_mm

RUNS = {
    "home_fold": "20261123T204853Z-screen-fe8efb",
    "compact500_crowe": "20261122T223153Z-screen-98b41d",
    "photo_rolled": "20261124T000037Z-screen-f8a896",
}
PRODUCT_LIMITS = {
    "home_fold": (600, 480, 480),
    "compact500_crowe": (500, 500, 500),
    "photo_rolled": (600, 480, 480),
}
EPSILONS = (1.0, 1.05, 1.15, 1.25)
out = {}
for name, run in RUNS.items():
    path = Path('runs') / run / 'search.ndjson'
    raw = path.read_bytes()
    run_config = json.loads((path.parent / 'run.json').read_text(encoding='utf-8'))['config']
    brief = run_config.get('brief') or {}
    brief_snapshot_sha = hashlib.sha256(json.dumps(brief,sort_keys=True,default=str).encode()).hexdigest()
    counts = collections.Counter()
    groups = collections.defaultdict(dict)
    for line in raw.splitlines():
        row = json.loads(line)
        counts['rows'] += 1
        if not row.get('ok') or not isinstance(row.get('objective'), (float, int)):
            counts[f"excluded:{row.get('kind') or 'unmeasured'}"] += 1
            continue
        b = row.get('bbox_m'); g = row.get('generator') or {}; m = row.get('metrics') or {}
        if not b or len(b) != 6 or str(row.get('quadrants')) != '1' or not brief or not m.get('freqs_hz'):
            counts['missing_bbox_quarter_brief_or_grid'] += 1; continue
        dims = full_bbox_extents_mm(b, row.get('symmetry_plane'))
        if not all(math.isfinite(x) and x > 0 for x in dims):
            counts['bad_bbox'] += 1; continue
        identity = {'brief':g.get('brief') or brief.get('name'), 'brief_hash_recorded':g.get('brief_hash'), 'brief_snapshot_sha256':brief_snapshot_sha, 'objective_version':row.get('objective_version'),
                    'mode':row.get('mode'), 'backend':row.get('backend'), 'freqs_hz':m['freqs_hz'],
                    'source_cap':(g.get('recipe_meta') or {}).get('source_cap'), 'source_config':brief.get('source'), 'driver':brief.get('driver'), 'mount':(g.get('recipe_meta') or {}).get('mode'),
                    'res_mm':row.get('res_mm'), 'generator_rows':(row.get('params',{}).get('grid',{}).get('rows'))}
        key=json.dumps(identity,sort_keys=True)
        utilization = max(actual / limit for actual, limit in zip(dims, PRODUCT_LIMITS[name]))
        item = {'design': row['design_hash'], 'j': row['objective'], 'bbox_mm': dims,
                'litres': math.prod(dims) / 1e6, 'utilization': utilization}
        if item['design'] in groups[key]: counts['duplicate_design'] += 1
        else: groups[key][item['design']]=item
    entries=[]
    for key, values in groups.items():
        items=list(values.values()); best=min(items,key=lambda x:x['j'])
        frontier=[]; lowest=float('inf')
        for x in sorted(items,key=lambda x:(x['litres'],x['j'])):
            if x['j'] < lowest: frontier.append(x); lowest=x['j']
        bins={}
        for label,lo,hi in [('under_50L',0,50),('50_to_75L',50,75),('75_to_100L',75,100),('100L_plus',100,float('inf'))]:
            subset=[x for x in items if lo<=x['litres']<hi]
            bins[label]={'n':len(subset),'best':min(subset,key=lambda x:x['j']) if subset else None}
        limits = PRODUCT_LIMITS[name]
        fitting = [x for x in items if x['utilization'] <= 1.0]
        epsilon_results = {}
        for epsilon in EPSILONS:
            subset = [x for x in items if x['utilization'] <= epsilon]
            epsilon_results[str(epsilon)] = {
                'n': len(subset), 'best': min(subset, key=lambda x: x['j'], default=None)}
        utilization_frontier = []
        lowest = float('inf')
        for item in sorted(items, key=lambda x: (x['utilization'], x['j'])):
            if item['j'] < lowest:
                utilization_frontier.append(item)
                lowest = item['j']
        entries.append({'identity':json.loads(key),'unique_designs':len(items),'best':best,'nominal_box_mm':limits,
                        'nominal_box_fit_count':len(fitting),'nominal_box_fit_best':min(fitting,key=lambda x:x['j']) if fitting else None,
                        'volume_regions': bins, 'pareto_volume_vs_j': frontier, 'observations': items,
                        'cumulative_epsilon_results': epsilon_results,
                        'pareto_utilization_vs_j': utilization_frontier})
    out[name]={'run':run,'search_ndjson_sha256':hashlib.sha256(raw).hexdigest(),'counts':dict(counts),'identity_groups':entries}
Path('docs/evidence/size_aware_2026-11-24/baseline.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')

if "--plot" in sys.argv:
    import matplotlib.pyplot as plt

    panels = [(name, group) for name, result in out.items() for group in result["identity_groups"]]
    fig, axes = plt.subplots(len(panels), 1, figsize=(7, 2.6 * len(panels)), squeeze=False,
                             layout="constrained")
    for axis, (name, group) in zip(axes[:, 0], panels):
        points = group["observations"]
        frontier = group["pareto_utilization_vs_j"]
        axis.scatter([x["utilization"] for x in points], [x["j"] for x in points],
                     s=13, alpha=0.45, color="#225784", label="Saved screen")
        axis.step([x["utilization"] for x in frontier], [x["j"] for x in frontier], where="post",
                  color="#9a4c16", label="Observed frontier")
        axis.axvline(1.0, color="#525863", linestyle="--", label="Nominal product box")
        axis.set_title(name.replace("_", " "))
        axis.set(xlabel="Maximum axis utilization R", ylabel="Screen J")
        axis.spines[["top", "right"]].set_visible(False)
    axes[0, 0].legend(frameon=False)
    fig.savefig(Path(__file__).with_name("frontier.png"), dpi=160)
