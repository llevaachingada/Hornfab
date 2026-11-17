"""A7 sibling lineage table for the sibling groups present in the 1,715-design base.

Sources (read-only): .n2/lineage_final.json (75 runs, A11 classification), .x3/seeds.json
(pairwise seed comparison produced by .x3/seeds.py), .fable/rows.pkl (run set per lane),
and the unchanged .x3/strict.py sibling() map.
"""
import json, pickle, sys, collections
sys.path.insert(0, 'scratch/fable_architecture/.x3c')
from a7_common import load_base, sibling

ROOT = 'scratch/fable_architecture'
X, Y, G, E, ids, rows, f = load_base()
lin = {r['run']: r for r in json.load(open(f'{ROOT}/.n2/lineage_final.json'))}
seeds = json.load(open(f'{ROOT}/.x3/seeds.json'))

run_cfg = {r['run']: r['config'] for r in rows}
lanes = sorted(set(G))
groups = collections.defaultdict(list)
for g in lanes:
    groups[sibling(g)].append(g)


def group_of(config):
    return sibling(config)


print('| sibling group | lanes (n designs) | engines | runs | start categories | cross-group lineage |')
print('|---|---|---|---|---|---|')
xcnt = 0
for s in sorted(groups):
    ls = groups[s]
    n = int(sum((G == g).sum() for g in ls))
    eng = sorted({E[G == g][0] for g in ls})
    runs = sorted({r['run'] for r in rows if r['config'] in ls})
    cats = collections.Counter(lin[r]['category'] for r in runs if r in lin)
    links = []
    for r in runs:
        if r in lin and lin[r]['parent']:
            p = lin[r]['parent']
            pc = run_cfg.get(p)
            if pc and group_of(pc) != s:
                links.append('%s <- %s (%s)' % (run_cfg.get(r, lin[r]['config']), p, pc))
                xcnt += 1
    print('| %s | %s | %s | %d | %s | %s |' % (
        s, '; '.join('%s (%d)' % (g, int((G == g).sum())) for g in ls), '/'.join(eng), len(runs),
        ', '.join('%s %d' % kv for kv in sorted(cats.items())),
        '; '.join(sorted(set(links))) if links else 'none within the group'))
print('\ndistinct cross-group parent links:', xcnt)

print('\nseed comparison inside groups (.x3/seeds.json):')
for s in sorted(groups):
    ls = groups[s]
    for row in seeds.get(s, []):
        if row['a'] in ls and row['b'] in ls:
            print('- %s / %s: generator_equal=%s, seed fields differing=%d %s'
                  % (row['a'], row['b'], row['generator_equal'],
                     len(row['seed_differences']), row['seed_differences'][:6]))
