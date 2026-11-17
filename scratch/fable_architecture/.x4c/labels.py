"""X4 completion: stored-label agreement for the five sampled lanes.

Stored labels are read from the dataset (`dataset/shard-*.jsonl`): `family` and `typology`
(the latter written by `hornlab_search.dataset.record.typology_name`).  Mounting is read from the
record provenance / run brief, and termination from the recipe's rows token.  The derived label
is recomputed independently from the recipe on disk (the generator block and the design params)
and, for termination, from the contract-v2 sampled surface (z monotonicity).

Denominators are distinct designs (one label set per design hash), not repeated solve records;
the record-instance counts are reported alongside.  Writes `.x4c/labels.json` and
`.x4c/labels.txt`.
"""
import sys, json, collections, pickle, pathlib, glob
import numpy as np

sys.path.insert(0, '.')
from hornlab_search.dataset.record import typology_name

ROOT = pathlib.Path('scratch/fable_architecture')
LANES = ['hl__osse_rrect_fold_warm_v7', 'hl__ext_throat_hvlaw_v7',
         'hl__ath_tritonia_landscape_v9', 'hl__crowe_x_osse_cd_v7',
         'hl__biradial_es_style_v7']


def main():
    rows = pickle.load(open(ROOT / '.fable/rows.pkl', 'rb'))
    rowby = {}
    for r in rows:
        if r['ok']:
            rowby.setdefault((r['config'], r['h']), r)
    recs = collections.defaultdict(list)
    for f in glob.glob('dataset/shard-*.jsonl'):
        for line in open(f):
            rec = json.loads(line)
            cn = rec.get('config_name')
            if cn in LANES:
                recs[(cn, rec['design_hash'])].append(rec)

    # sampled surfaces for the termination check
    surf = {}
    for f in (ROOT / '.x4c/build').glob('*.npz'):
        z = np.load(f)
        s = z['inner']
        dz = np.diff(s[:, :, 2], axis=1)
        surf[(str(z['lane']), str(z['design_hash']))] = dict(
            z_monotone=bool(np.all(dz >= -1e-6)),
            min_dz_mm=float(dz.min()),
            nonmonotone_fraction=float((dz < -1e-6).sum()) / float(dz.size))

    rc = {}
    for (config, h), rs in recs.items():
        row = rowby.get((config, h))
        if row is None:
            rc[(config, h)] = None
            continue
        try:
            recipe = json.loads((pathlib.Path('runs') / row['run'] / 'designs' / h /
                                 'design.json').read_text())
        except Exception:
            rc[(config, h)] = None
            continue
        rc[(config, h)] = recipe

    out = {}
    for lane in LANES:
        fam_n = fam_ok = 0
        typ_n = typ_ok = 0
        rec_fam_n = rec_fam_ok = rec_typ_n = rec_typ_ok = 0
        dis = []
        designs = sorted([k for k in recs if k[0] == lane])
        for key in designs:
            recipe = rc.get(key)
            if recipe is None:
                continue
            fam_d = recipe.get('family')
            typ_d = typology_name(recipe.get('generator'), fam_d)
            labels = {r.get('typology') for r in recs[key]}
            fams = {r.get('family') for r in recs[key]}
            fam_n += 1
            if fams == {fam_d}:
                fam_ok += 1
            else:
                dis.append(dict(h=key[1], kind='family', stored=sorted(fams), derived=fam_d))
            typ_n += 1
            if labels == {typ_d}:
                typ_ok += 1
            else:
                dis.append(dict(h=key[1], kind='typology',
                                stored=sorted(x for x in labels if x is not None),
                                derived=typ_d,
                                runs=sorted({r.get('run_id') for r in recs[key]})))
            for r in recs[key]:
                rec_fam_n += 1; rec_typ_n += 1
                rec_fam_ok += int(r.get('family') == fam_d)
                rec_typ_ok += int(r.get('typology') == typ_d)

        # mounting: no positive label is stored in these records
        mount_present = sum(1 for k in designs for r in recs[k]
                            if (r.get('provenance') or {}).get('mounting') is not None)
        # termination: rows token on the recipe, class from the sampled surface
        term = []
        for key in designs:
            recipe = rc.get(key)
            if recipe is None:
                continue
            grid = recipe['params'].get('grid') or {}
            rows_meta = grid.get('rows') or {}
            token = rows_meta.get('type') or recipe['params'].get('termination')
            if not token:
                continue
            s = surf.get(key)
            if s is None:
                term.append(dict(h=key[1], token=token, sampled=False))
                continue
            kind = 'rollback' if not s['z_monotone'] else 'forward'
            term.append(dict(h=key[1], token=token, derived=kind, sampled=True,
                             agree=('rollback' in str(token)) == (kind == 'rollback'),
                             **s))
        term_testable = [t for t in term if t.get('sampled')]
        sampled_hashes = [x['h'] for x in json.loads(
            (ROOT / '.x4c/build.json').read_text())[lane]]
        s_fam = s_typ = s_both = s_any = 0
        for h in sampled_hashes:
            recs_h = recs.get((lane, h)) or []
            if not recs_h:
                continue
            row = rowby.get((lane, h))
            recipe = rc.get((lane, h)) if row is not None else None
            if recipe is None:
                continue
            fam_d = recipe.get('family')
            typ_d = typology_name(recipe.get('generator'), fam_d)
            fams = {r.get('family') for r in recs_h}
            typs = {r.get('typology') for r in recs_h}
            fam_ok_h = (fams == {fam_d})
            typ_ok_h = (typs == {typ_d})
            s_fam += int(fam_ok_h); s_typ += int(typ_ok_h)
            s_both += int(fam_ok_h and typ_ok_h)
            s_any += int((fam_d in fams) or (typ_d in typs))
        out[lane] = dict(
            design_hashes_with_records=len(designs),
            label_designs=fam_n,
            family=dict(agree=fam_ok, n=fam_n),
            typology=dict(agree=typ_ok, n=typ_n),
            family_instances=dict(agree=rec_fam_ok, n=rec_fam_n),
            typology_instances=dict(agree=rec_typ_ok, n=rec_typ_n),
            sampled=dict(n=len(sampled_hashes), family_agree=s_fam, typology_agree=s_typ,
                         both_agree=s_both, at_least_one_agrees=s_any),
            mounting=dict(agree=0, n=0, positive_labels=mount_present,
                          note='no mounting block stored; all briefs omit it -> freestanding default'),
            termination=dict(agree=sum(1 for t in term_testable if t.get('agree')),
                             n=len(term_testable),
                             tokens=len(term),
                             detail=term),
            disagreements=dis,
        )

    (ROOT / '.x4c/labels.json').write_text(json.dumps(out, indent=1))

    lines = []
    for lane, v in out.items():
        lines.append('=' * 78)
        lines.append('%s  label designs %d (of %d design hashes with records)' %
                     (lane, v['label_designs'], v['design_hashes_with_records']))
        lines.append('  family      %d/%d distinct   (%d/%d record instances)' %
                     (v['family']['agree'], v['family']['n'],
                      v['family_instances']['agree'], v['family_instances']['n']))
        lines.append('  typology    %d/%d distinct   (%d/%d record instances)' %
                     (v['typology']['agree'], v['typology']['n'],
                      v['typology_instances']['agree'], v['typology_instances']['n']))
        lines.append('  sampled 11  family %d/%d, typology %d/%d, both %d/%d, any %d/%d' %
                     (v['sampled']['family_agree'], v['sampled']['n'],
                      v['sampled']['typology_agree'], v['sampled']['n'],
                      v['sampled']['both_agree'], v['sampled']['n'],
                      v['sampled']['at_least_one_agrees'], v['sampled']['n']))
        lines.append('  mounting    %d/%d (no positive label stored; %s)' %
                     (v['mounting']['agree'], v['mounting']['n'], v['mounting']['note']))
        lines.append('  termination %d/%d sampled designs with a stored token' %
                     (v['termination']['agree'], v['termination']['n']))
        for d in v['disagreements']:
            lines.append('    DISAGREE %s %s stored=%s derived=%s' %
                         (d['h'], d['kind'], d.get('stored'), d.get('derived')))
        for t in v['termination']['detail']:
            if t.get('sampled'):
                lines.append('    term %s token=%s derived=%s min_dz=%.2f agree=%s' %
                             (t['h'], t['token'], t['derived'], t['min_dz_mm'], t.get('agree')))
    (ROOT / '.x4c/labels.txt').write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
