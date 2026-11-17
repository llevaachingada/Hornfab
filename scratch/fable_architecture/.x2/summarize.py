import json,pathlib
root=pathlib.Path('scratch/fable_architecture/.x2'); d=json.load(open(root/'results.json'))
for name,b in d['bases'].items():
    print('\n',name,'distance',round(b['base_distance'],2),'threshold',round(b['distance95'],2))
    for m,a in b['modules'].items():
        z=a['raw']['10']; minus=a['raw']['-10']; control=a['bbox_control']['10']; zds=z['delta_deg']; mds=minus['delta_deg']; control=control['delta_deg']; print(m,'+10',[[round(x,2) for x in a] for a in zds],'-10',[[round(x,2) for x in a] for a in mds],'+10 fixed box',[[round(x,2) for x in a] for a in control],'outside95',minus['outside95'],z['outside95'])
