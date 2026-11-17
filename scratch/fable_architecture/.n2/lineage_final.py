import collections, json, pathlib, pickle
import yaml

root = pathlib.Path('scratch/fable_architecture')
rows = pickle.load(open(root / '.fable/rows.pkl', 'rb'))
runs = collections.defaultdict(list)
for r in rows:
    runs[r['run']].append(r)
for rr in runs.values():
    rr.sort(key=lambda r: (r['created'], r['n'] or 0))
first = {run: rr[0] for run, rr in runs.items()}
best = {}
first_valid = {}
for run, rr in runs.items():
    ok = [r for r in rr if r['ok']]
    best[run] = min(ok, key=lambda r: r['J']) if ok else None
    first_valid[run] = ok[0] if ok else None
allrows = sorted(rows, key=lambda r: (r['created'], r['run'], r['n'] or 0))


def num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def target_of(r):
    return r.get('knobs') or r.get('params') or {}


def match(seed, target):
    shared = [k for k, v in seed.items() if num(v) and k in target and num(target[k])]
    if not shared:
        return False, 0
    for k in shared:
        a, b = float(seed[k]), float(target[k])
        if abs(a - b) > 1e-6 * max(1.0, abs(b)):
            return False, len(shared)
    return True, len(shared)


# Documented provenance: run -> (parent_run, note, quote)
DOC = {
    '20261116T025728Z-screen-cd60f7': ('20261115T143219Z-screen-d3a1bb',
        'Seed = family best; new n at old fixed 6', 'examples/typologies/home_landscape_2026-11-15/hl__ext_throat_hvlaw_v8.yaml:6'),
    '20261116T030920Z-screen-5d1082': ('20261115T154322Z-screen-07bea2',
        'Seed = family best (J 3.992)', 'examples/typologies/home_landscape_2026-11-15/hl__osse_rrect_morph_v8.yaml:5-6'),
    '20261116T043544Z-screen-dd15d8': ('20261116T020629Z-screen-0d29d7',
        'Seed = 25x2 pilot best (J 17.397)', 'examples/typologies/rolled_family_2026-11-15/rf__section_axial_home_v8.yaml:7'),
    '20261116T035949Z-screen-3e49ce': ('20261116T034337Z-screen-eeef98',
        'seed = its best after widening', 'examples/typologies/home_landscape_2026-11-15/hl__lecleach_iwata_ar_landscape_smooth_v7.yaml:5'),
    '20261116T085415Z-screen-0a228d': ('20261115T154322Z-screen-07bea2',
        'WARM START: v7 best (J 3.992) with meridian fold added', 'examples/typologies/home_landscape_2026-11-15/hl__osse_rrect_fold_warm_v7.yaml:1-4'),
    '20261116T145634Z-screen-e4c778': ('20261116T093400Z-screen-56681d',
        'seed = best of 56681d (J 4.892)', 'examples/typologies/home_landscape_2026-11-15/hl__rosse_rect_cd_v7.yaml:12'),
    '20261116T150941Z-screen-0e777a': ('20261116T093400Z-screen-56681d',
        'reuses the same config seed = best of 56681d (J 4.892)', 'examples/typologies/home_landscape_2026-11-15/hl__rosse_rect_cd_v7.yaml:12'),
}

result = []
for run in sorted(runs):
    f = first[run]
    cfg = yaml.safe_load(open(pathlib.Path('runs') / run / 'config.yaml'))
    seedp = cfg.get('seed_params') or {}
    s = cfg.get('search') or {}
    ws = s.get('warm_start')
    earlier = [r for r in allrows if r['created'] < f['created'] and r['ok']]
    best_by_config = {}
    for r in earlier:
        c = r['config']
        if c not in best_by_config or r['J'] < best_by_config[c]['J']:
            best_by_config[c] = r
    matches = []
    for c, b in best_by_config.items():
        ok, shared = match(seedp, target_of(b))
        if ok:
            matches.append({'run': b['run'], 'config': c, 'J': b['J'], 'shared': shared})
    matches.sort(key=lambda m: (m['config'] != f['config'], m['J']))

    category = 'hand-written seed'
    parent = None
    basis = 'config seed_params (explicit authored seed; no earlier-run match)'
    quote = ''
    note = ''
    if ws:
        category = 'warm start from a named run'
        source_runs = [p.replace('runs/', '').replace('\\', '/').split('/')[-1] if '/' in p or '\\' in p else p for p in ws.get('from_runs', [])]
        parent = source_runs[0] if source_runs else None
        basis = 'search.warm_start.from_runs'
        quote = 'runs/' + run + '/config.yaml search.warm_start'
        note = 'top_k=%s, sigma_from_spread=%s; mean objective %s' % (ws.get('top_k'), ws.get('sigma_from_spread'), '')
    elif run in DOC:
        category = 'best design of an earlier run'
        parent = DOC[run][0]
        basis = 'config comment'
        note = DOC[run][1]
        quote = DOC[run][2]
    elif matches:
        m = matches[0]
        # A match is only a "search best" if the parent's best row is not simply its own authored seed.
        pb = best[m['run']]
        pseed = yaml.safe_load(open(pathlib.Path('runs') / m['run'] / 'config.yaml')).get('seed_params') or {}
        parent_best_is_seed = match(pseed, target_of(pb))[0] and abs((first_valid[m['run']]['J'] - pb['J'])) < 1e-9
        if parent_best_is_seed:
            category = 'hand-written seed'
            note = 'mechanical match is the parent run\'s own authored seed (%s), not a searched best' % m['run']
            basis = 'param match rejected (parent best = parent seed)'
        else:
            category = 'best design of an earlier run'
            parent = m['run']
            basis = 'seed_params match <= 1e-6'
            note = 'matched best row J %.4f' % m['J']
            quote = 'runs/%s/config.yaml vs runs/%s best row' % (run, m['run'])

    parent_best_J = None
    seeded = None
    if parent:
        # Use the parent's best as it stood when this run started (anachronism guard),
        # except documented seeds, where the comment states the J that was used.
        doc_J = {
            '20261115T143219Z-screen-d3a1bb': 3.102805201974035,
            '20261115T154322Z-screen-07bea2': 3.9917940069570292,
            '20261116T020629Z-screen-0d29d7': 17.397036998386138,
            '20261116T034337Z-screen-eeef98': 7.001970853055004,
            '20261116T093400Z-screen-56681d': 4.891541281798778,
        }
        if run in DOC and parent in doc_J:
            parent_best_J = doc_J[parent]
        elif matches and matches[0]['run'] == parent:
            parent_best_J = matches[0]['J']
        elif ws:
            eligible = [r for r in allrows if r['ok'] and r['run'] in
                        [p.replace('runs/', '').replace('\\', '/').split('/')[-1] if ('/' in p or '\\' in p) else p for p in ws.get('from_runs', [])]
                        and r['created'] < f['created']]
            if eligible:
                parent_best_J = min(r['J'] for r in eligible)
        if parent_best_J is not None:
            fv = first_valid[run]
            seeded = bool(fv and fv['J'] <= parent_best_J + 0.17)
    result.append({
        'run': run, 'config': f['config'], 'brief': f['brief'], 'start': f['created'],
        'seed': s.get('seed'), 'algorithm': s.get('algorithm'),
        'seed_param_count': len(seedp),
        'category': category, 'parent': parent, 'parent_best_J': parent_best_J,
        'basis': basis, 'note': note, 'quote': quote,
        'first_valid_J': first_valid[run]['J'] if first_valid[run] else None,
        'seeded': seeded,
        'matches': matches[:3],
    })

(root / '.n2/lineage_final.json').write_text(json.dumps(result, indent=1, default=str))
c = collections.Counter(x['category'] for x in result)
print('total', len(result))
for k, v in c.items():
    print(f'{k}: {v}')
print('with parent:', sum(1 for x in result if x['parent']))
print('seeded:', sum(1 for x in result if x['seeded'] is True))
print('not seeded:', sum(1 for x in result if x['seeded'] is False))
for x in result:
    print(f"{x['category'][:22]:22s} {x['run']} {x['config']:45s} parent={x['parent']} seeded={x['seeded']} basis={x['basis']} {x['note']}")
