"""Render pinned J designs through current API, preserving explicit rejections."""
import copy, os, subprocess, sys
from pathlib import Path
import yaml
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from hornlab_search.design.generators import grid
from tools.geometry import hf1440_seed_gallery as gallery
out=ROOT/'docs/research/typologies/hf1440_diverse_2026-11-16'
fig=plt.figure(figsize=(17,19.2),dpi=110,layout='constrained')
gs=fig.add_gridspec(6,5)
for row, seed in enumerate(gallery.J_SEEDS):
    ident,label=seed[:2]; path=out/f'{ident}_PRE-FLIGHT_PINNED.yaml'
    cfg=yaml.safe_load(path.read_text(encoding='utf-8'))
    brief_path=(path.parent / cfg['brief_file']).resolve()
    brief=yaml.safe_load(brief_path.read_text(encoding='utf-8'))
    proc=subprocess.run([sys.executable,str(ROOT/'tools/shape_check.py'),str(path),'--mode','screen'],cwd=ROOT,capture_output=True,text=True)
    evidence=proc.stdout+'\n'+proc.stderr
    (out/f'{ident}_shape_check.txt').write_text(evidence,encoding='utf-8')
    axs=[fig.add_subplot(gs[row,k],projection='3d' if k<3 else None) for k in range(5)]
    if '| NO |' in evidence or 'CONFIG ERROR:' in evidence or proc.returncode:
        for ax in axs: ax.set_axis_off()
        reason=next((line.strip() for line in evidence.splitlines() if 'CONFIG ERROR:' in line),'shape check failed; see evidence')
        axs[0].text2D(0,.7,f'{ident} {label}\nREJECTED',transform=axs[0].transAxes,color='firebrick')
        axs[1].text2D(0,.5,reason.split('CONFIG ERROR:')[-1].strip(),transform=axs[1].transAxes,color='firebrick',wrap=True,fontsize=8)
        print(ident,'REJECTED',reason)
        continue
    spec=copy.deepcopy(cfg['generator']); spec.pop('seed_policy',None)
    q,meta=grid.rows_grid_points(spec,cfg['seed_params'],brief)
    dims=gallery.bbox(q); valid=all(v<=lim for v,lim in zip(dims,gallery.ENV))
    gallery.make_preview_row(axs,q,f'{ident} {label}',dims,valid)
    gallery.write_open_obj(q,out/f'{ident}_OPEN_SURFACE.obj')
    if row==0:
        for j,name in enumerate(('3/4','front','side','H section','V section')):
            axs[j].text2D(.5,1.12,name,transform=axs[j].transAxes,ha='center',fontsize=9) if j<3 else axs[j].set_title(name,fontsize=9)
    print(ident,'GENERATED',dims)
fig.suptitle('HF1440 J existing iwata_ar | geometry only; open inner surfaces; screen is not acoustic validation',fontsize=12)
fig.savefig(out/'01_IWATA_EXISTING_CODE.png',dpi=140);plt.close(fig)
