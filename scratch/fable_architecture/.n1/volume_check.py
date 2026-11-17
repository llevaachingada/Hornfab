import sys, numpy as np
sys.path.insert(0, 'scratch/fable_architecture/.n1'); sys.path.insert(0, '.')


def tris(path):
    txt = open(path).read()
    a = txt.index('$Nodes') + 7
    b = txt.index('$EndNodes')
    blk = txt[a:b].strip().split('\n')
    nd = np.array(' '.join(blk[1:]).split(), float).reshape(-1, 4)
    ids = nd[:, 0].astype(int)
    xyz = nd[:, 1:] * 1000
    ix = {int(i): k for k, i in enumerate(ids)}
    e0 = txt.index('$Elements') + 10
    e1 = txt.index('$EndElements')
    out = []
    for line in txt[e0:e1].split('\n')[1:]:
        p = line.split()
        if len(p) >= 8 and p[1] == '2' and p[3] == '1':
            out.append([ix[int(x)] for x in p[-3:]])
    return xyz, np.array(out)


for h, run in [('64efc34b7396', '20261115T143219Z-screen-d3a1bb'),
               ('7b0a1988625d', '20261116T061215Z-screen-058f0d'),
               ('7f4c515cedd0', '20261116T065413Z-screen-a70423'),
               ('d99b73012d8e', '20261116T015510Z-screen-e75ec8'),
               ('149aca76074e', '20261116T205942Z-screen-8b22b5')]:
    xyz, T = tris(f'runs/{run}/designs/{h}/mesh.msh')
    vol = abs(np.einsum('ij,ij->i', xyz[T[:, 0]], np.cross(xyz[T[:, 1]], xyz[T[:, 2]])).sum() / 6) / 1000
    area = np.linalg.norm(np.cross(xyz[T[:, 1]] - xyz[T[:, 0]], xyz[T[:, 2]] - xyz[T[:, 0]]), axis=1).sum() / 2 / 100
    print(h, 'tris', len(T), 'volume_cm3', round(vol, 3), 'area_cm2', round(area, 2))
