import pathlib, json, yaml, collections
root = pathlib.Path(r'C:\Users\hunte\Hrns\hornlab-search\runs')
tot_pairs = 0
for S in sorted(root.glob('study-*')):
    sd = S/'screen'; vd = S/'verify'
    if not (sd/'designs').is_dir() or not (vd/'designs').is_dir():
        continue
    sh = {p.name for p in (sd/'designs').iterdir() if p.is_dir()}
    vh = {p.name for p in (vd/'designs').iterdir() if p.is_dir()}
    common = sorted(sh & vh)
    tot_pairs += len(common)
    # freq counts for a common design
    freqs = []
    for h in common[:3]:
        import numpy as np
        a = np.load(sd/'designs'/h/'response.npz', allow_pickle=False)['freqs_hz']
        b = np.load(vd/'designs'/h/'response.npz', allow_pickle=False)['freqs_hz']
        freqs.append((len(a), len(b), bool(np.array_equal(a,b))))
    print(S.name, 'common', len(common), 'freqs(screen,verify,equal)', freqs)
print('TOTAL common pairs', tot_pairs)
