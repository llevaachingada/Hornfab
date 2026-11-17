import json,numpy as np
from hornlab_search.types import Design
from hornlab_search.config import load_config
from hornlab_search.bo.data import materialize_geometry
run='20261117T003115Z-screen-4f7cd5'; h='c535bbf5e771'; p=f'runs/{run}'
j=json.load(open(f'{p}/designs/{h}/design.json')); c=load_config(f'{p}/config.yaml'); d=Design(j['family'],j['params'])
for res in (10,5):
 a=materialize_geometry(d,c,resolution_mm=res)['inner_points']; print(res,a.shape, 'first/last phi mouth:',a[[0,-1],-1,:]); print('sample angles',np.degrees(np.arctan2(a[::max(1,len(a)//5),-1,1],a[::max(1,len(a)//5),-1,0])))
