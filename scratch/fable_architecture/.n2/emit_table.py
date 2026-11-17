import json

d = json.load(open('scratch/fable_architecture/.n2/lineage_final.json'))
lines = []
lines.append('| Run | Config | Start came from | Parent (parent best J) | First valid J | Seeded? | Evidence |')
lines.append('|---|---|---|---|---:|---|---|')
cat_short = {
    'hand-written seed': 'hand-written seed',
    'best design of an earlier run': 'earlier run best',
    'warm start from a named run': 'warm start',
}
for x in d:
    cat = cat_short[x['category']]
    if x['category'] == 'warm start from a named run':
        parent = '12eb61 + 570bc6 (top-10 mean, sigma from spread)'
    elif x['parent']:
        parent = '`%s` (%.4f)' % (x['parent'], x['parent_best_J'])
    else:
        parent = '—'
    fv = '%.4f' % x['first_valid_J'] if x['first_valid_J'] is not None else 'n/a'
    seeded = '—' if x['seeded'] is None else ('yes' if x['seeded'] else 'no')
    if x['category'] == 'hand-written seed':
        ev = 'config `seed_params`, no earlier-run match'
        if x['note']:
            ev += '; ' + x['note']
    elif x['category'] == 'warm start from a named run':
        ev = '`search.warm_start.from_runs`'
    elif x['basis'] == 'config comment':
        ev = x['quote'] + ' — ' + x['note']
    else:
        ev = x['basis'] + '; ' + x['note']
    lines.append('| %s | `%s` | %s | %s | %s | %s | %s |' % (
        x['run'], x['config'], cat, parent, fv, seeded, ev.replace('|', '/')))
open('scratch/fable_architecture/.n2/lineage_table.md', 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
print('\n'.join(lines[:6]))
print('rows', len(lines) - 2)
