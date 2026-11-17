import json
r = json.load(open('scratch/fable_architecture/.p1/results.json'))
for k, v in r['support'].items():
    print('%-42s n=%3d out=%3d thr=%.2f med=%.2f max=%.2f' % (k, v['n'], v['outside'], v['threshold'], v['median_dist'], v['max_dist']))
