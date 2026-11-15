"""Publish the section-based H/V relief seeds and measured feasibility evidence."""
from pathlib import Path
import json
import shutil
import meshio
import yaml

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT/'scratch/2026-11-15_section_pucker'
OUT = ROOT/'docs/renders/2026-11-15-rolled-rect/puckers'
ANGLES = {'c': 'Front', 'a': 'Angled', 'b': 'Rear', 's': 'Side', 'u': 'Below'}


def build():
    evidence = json.loads((ROOT/'docs/queue/section_pucker_validation_2026-11-15.json').read_text(encoding='utf-8'))
    required = [WORK/f'renders/{name}_{a}.png' for name in ['control', 'moderate', 'strong'] for a in ANGLES]
    if any(not p.is_file() for p in required):
        raise FileNotFoundError('Missing seed render')
    images = OUT/'images'
    images.mkdir(parents=True, exist_ok=True)
    cards, rows = [], []
    for name, title in [('control', 'Section reference'), ('moderate', 'Moderate H/V relief'), ('strong', 'Strong H/V relief')]:
        cfg = yaml.safe_load((ROOT/f'examples/typologies/section_pucker_2026-11-15/sp__{name}_v7.yaml').read_text(encoding='utf-8'))
        mesh = meshio.read(WORK/f'seed-meshes/sp__{name}_v7/mesh.msh')
        nodes = len(mesh.points)
        seed = cfg['seed_params']
        h, v = seed['g_pucker_h_mm'], seed['g_pucker_v_mm']
        thumbnails = []
        for a, label in ANGLES.items():
            file = f'{name}_{a}.png'
            shutil.copy2(WORK/'renders'/file, images/file)
            thumbnails.append(f'<button class="thumb" data-src="images/{file}" data-alt="{title}: {label}"><img src="images/{file}" alt="{title}: {label}"><span>{label}</span></button>')
        cards.append(f'<article data-name="{name}"><h2>{title}</h2><p>{h:g} mm H / {v:g} mm V seed inputs</p><button class="hero" data-src="images/{name}_c.png" data-alt="{title}: Front"><img src="images/{name}_c.png" alt="{title}: Front"></button><p>{nodes:,} / 6,000 screen DOFs</p><div class="thumbs">'+''.join(thumbnails)+'</div></article>')
        arm = next(x for x in evidence['arms'] if x['name'] == name)
        hs, vs = (cfg['bounds'][k] for k in ['g_pucker_h_mm', 'g_pucker_v_mm'])
        sampled = arm['preflight']['configs'][0]['sampling']
        rows.append(f'<tr><td>{title}</td><td>{hs["lo"]:g} to {hs["hi"]:g}</td><td>{vs["lo"]:g} to {vs["hi"]:g}</td><td>{sampled["valid"]}/64</td><td>{arm["corners"]["valid"]}/{arm["corners"]["corners"]}</td></tr>')
    page = TEMPLATE.replace('@@CARDS@@', ''.join(cards)).replace('@@ROWS@@', ''.join(rows))
    page = page.replace('@@ANGLES@@', ''.join(f'<button data-angle="{a}" aria-pressed="{str(a=="c").lower()}">{label}</button>' for a, label in ANGLES.items()))
    (OUT/'index.html').write_text(page, encoding='utf-8')
    (OUT/'validation.json').write_text(json.dumps(evidence, indent=2)+'\n', encoding='utf-8')
    (OUT/'README.md').write_text('Section-based H/V relief seeds. Rebuild with `.venv/Scripts/python.exe tools/geometry/build_section_pucker_page.py` after CPU seed meshing/rendering and box validation. Images are the actual screen meshes; fine bands are mesh artifacts. Acoustic results are separate.\n', encoding='utf-8')
    print(f'Built {OUT} with 15 renders')


TEMPLATE = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Section reference with H/V mouth relief</title><style>
*{box-sizing:border-box}body{margin:0;color:#172429;background:#f3f3ed;font:16px/1.6 system-ui}main{max-width:1500px;margin:auto;padding:30px 4vw}h1{font:500 clamp(2.4rem,5vw,5rem)/1.05 Georgia;max-width:950px}h2{font:500 1.8rem Georgia}a{color:inherit}p{max-width:950px}.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:20px}article{background:white;padding:18px;min-width:0}img{display:block;width:100%;height:auto}button{font:inherit;cursor:pointer;border:1px solid #b7c1bb;background:white;padding:8px}.hero,.thumb{padding:0;border:0;width:100%}.hero img{width:100%}.thumbs{display:grid;grid-template-columns:repeat(5,1fr);gap:5px}.thumb span{font-size:.7rem}.selector{display:flex;flex-wrap:wrap;gap:8px;margin:25px 0}button[aria-pressed=true]{background:#172429;color:white}button:focus-visible,a:focus-visible{outline:3px solid #9d512e;outline-offset:3px}.overflow{overflow:auto}table{border-collapse:collapse;width:100%;margin:25px 0}th,td{text-align:left;padding:12px;border-bottom:1px solid #bdc6bf}section{padding:30px 0}dialog{width:min(1200px,96vw);border:0;padding:15px}dialog::backdrop{background:#15282be0}dialog img{max-height:85vh;object-fit:contain}dialog button{float:right}@media(max-width:900px){.grid{grid-template-columns:1fr}article{max-width:750px}}@media(prefers-reduced-motion:no-preference){html{scroll-behavior:smooth}}</style>
<main><a href="../index.html">Back to section reference and original studies</a><h1>The section reference, with four-wall relief.</h1><p>Two new H/V puckered surfaces keep the reference's 417 x 203 mm front outline, round 36 mm driver interface, rolled lips and rear body. This is an original ATH-inspired deformation of our section reconstruction, not the ATH formula. The seeds below are the actual meshed geometry.</p><div class="selector" role="group" aria-label="Compare angle">@@ANGLES@@</div><div class="grid">@@CARDS@@</div>
<section><h2>Starting bounds, measured before launch</h2><p>All arms optimize depth from 192 to 204 mm, horizontal-profile depth scale from 0.98 to 1.02, and transverse crown from 18 to 22 mm. Seeds are 198 mm, 1.00 and 20 mm. Mouth dimensions, throat, wall thickness, join rounding and pucker location stay fixed.</p><div class="overflow"><table><thead><tr><th>Arm</th><th>H pucker bounds / mm</th><th>V pucker bounds / mm</th><th>Random box meshes</th><th>Extreme combinations</th></tr></thead><tbody>@@ROWS@@</tbody></table></div><p>Each arm receives 48 attempted evaluations, seed 1234, population 8 and normalized initial step 0.15. Initial physical steps are 1.8 mm depth, 0.006 profile scale, 0.6 mm crown; H/V steps are 0.9/1.2 mm for moderate relief and 0.9/0.9 mm for strong relief. Flat geometry penalties count against the budget. Measured random-box refusals were 1/64, 2/64 and 2/64; these are guarded failures, not unvalidated meshes. All tested extreme combinations passed, with at most 4,055 DOFs under the unchanged 6,000 cap.</p><p>Relief starts at 30%, peaks at 80% and ends at 96% of the reference vertical-profile arc. It vanishes around the throat and returned edge. The inputs describe wall-centre axial motion, not total ridge-to-diagonal distance: the strong seed's 7/9 mm inputs give 15/17 mm centre-to-diagonal relief at the window peak. Fine bands in the renders come from the screen mesh.</p><p>The common brief targets 700 Hz and 80 H x 50 V coverage. Shape feasibility does not demonstrate those acoustic targets. Each winner is queued for denser-frequency verification; spatial mesh convergence is a separate check.</p><p><a href="validation.json">Full configuration and validation evidence</a> &middot; <a href="https://github.com/llevaachingada/Hornfab/blob/main/docs/research/typologies/SECTION_PUCKER_RESEARCH_2026-11-15.md">Construction research</a> &middot; <a href="https://at-horns.eu/tritonia.html">ATH source</a></p></section></main>
<dialog><button class="close">Close</button><img alt=""></dialog><script>
const dialog=document.querySelector('dialog'),expanded=dialog.querySelector('img');
document.querySelectorAll('[data-angle]').forEach(button=>button.addEventListener('click',()=>{document.querySelectorAll('[data-angle]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));document.querySelectorAll('article').forEach(card=>{const hero=card.querySelector('.hero'),src='images/'+card.dataset.name+'_'+button.dataset.angle+'.png',alt=card.querySelector('h2').textContent+': '+button.textContent;hero.dataset.src=src;hero.dataset.alt=alt;hero.querySelector('img').src=src;hero.querySelector('img').alt=alt})}));
document.querySelectorAll('[data-src]').forEach(b=>b.addEventListener('click',()=>{expanded.src=b.dataset.src;expanded.alt=b.dataset.alt;dialog.showModal()}));dialog.querySelector('.close').addEventListener('click',()=>dialog.close());
</script></html>'''


if __name__ == '__main__':
    build()
