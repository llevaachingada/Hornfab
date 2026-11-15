#!/usr/bin/env python3
"""Build the standalone rolled-rectangle geometry comparison page."""
from __future__ import annotations

import argparse
import html
import json
import shutil
from pathlib import Path

import meshio
import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RENDERS = ROOT / "scratch/2026-11-15_rolled_rect/final-renders"
DEFAULT_OUT = ROOT / "docs/renders/2026-11-15-rolled-rect"
CONFIGS = ROOT / "examples/typologies/rolled_rect_2026-11-15"
MESHES = ROOT / "scratch/2026-11-15_rolled_rect/split-meshes"
BRIEF = ROOT / "examples/briefs/home_landscape_2026-11-15/room_landscape_80x50_700_hf1440_v7.yaml"
REPO = "https://github.com/llevaachingada/Hornfab/blob/main/"
VARIANTS = [("reference", "reference", "Reference", "A smooth baseline"),
            ("pucker_moderate", "pucker_hv_moderate", "Moderate", "A subtle four-wall relief"),
            ("pucker_strong", "pucker_hv_strong", "Strong", "A more pronounced relief")]
ANGLES = [("a", "Front angled"), ("b", "Rear angled"), ("c", "Front"),
          ("s", "Side"), ("u", "Below")]


def load_yaml(path):
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if "extends" in data:
        base = load_yaml(path.parent / data.pop("extends"))
        for key, value in data.items():
            if isinstance(value, dict) and isinstance(base.get(key), dict):
                base[key].update(value)
            else:
                base[key] = value
        return base
    return data


def build(renders, out):
    brief = load_yaml(BRIEF)
    assets = out / "images"
    assets.mkdir(parents=True, exist_ok=True)
    cards = []
    metrics = []
    for image_name, config_name, title, subtitle in VARIANTS:
        cfg = load_yaml(CONFIGS / f"rr__{config_name}_v7.yaml")
        mesh = meshio.read(MESHES / f"rr__{config_name}_v7/mesh.msh")
        # Input is a single positive-X, positive-Y quadrant, in metres.
        p = mesh.points
        if p[:, :2].min() < -1e-8:
            raise ValueError("Expected positive quadrant mesh")
        width, height = 2000 * p[:, 0].max(), 2000 * p[:, 1].max()
        depth = 1000 * (p[:, 2].max() - p[:, 2].min())
        params = cfg["seed_params"]
        images = []
        for suffix, angle in ANGLES:
            filename = f"{image_name}_{suffix}.png"
            shutil.copy2(renders / filename, assets / filename)
            images.append(f'<button class="thumb" type="button" data-src="images/{filename}" data-alt="{title}, {angle.lower()} view"><img src="images/{filename}" alt="{title}, {angle.lower()} view" loading="lazy"><span>{angle}</span></button>')
        cards.append(f'''<article class="card" data-variant="{image_name}"><div class="card-head"><div><span class="eyebrow">{subtitle}</span><h3>{title}</h3></div><span class="number">{len(cards)+1:02}</span></div>
        <button class="hero-image" type="button" data-src="images/{image_name}_a.png" data-alt="{title}, front angled view"><img src="images/{image_name}_a.png" alt="{title}, front angled view"><span>Enlarge ↗</span></button>
        <div class="stats"><div><b>{width:.0f} × {height:.0f} × {depth:.0f}</b><small>full bounding box · mm</small></div><div><b>{len(p):,}</b><small>quarter-mesh nodes / seed DOFs</small></div><div><b>{params['g_pucker_h_mm']:g} / {params['g_pucker_v_mm']:g} mm</b><small>H / V pucker parameters</small></div></div>
        <div class="thumbs">{''.join(images)}</div></article>''')
        metrics.append({"variant": title, "mesh": str(MESHES.relative_to(ROOT) / f"rr__{config_name}_v7/mesh.msh"), "quarter_mesh_nodes": len(p), "full_width_mm": width, "full_height_mm": height, "depth_mm": depth, "pucker_h_mm": params['g_pucker_h_mm'], "pucker_v_mm": params['g_pucker_v_mm']})
    target = brief["target"]
    throat = 2 * brief["driver"]["exit_radius_mm"]
    angles_json = json.dumps(dict(ANGLES))
    page = TEMPLATE.replace("@@CARDS@@", "\n".join(cards)).replace("@@ANGLES@@", angles_json)
    page = page.replace("@@THROAT@@", f"{throat:g}").replace("@@TARGET_H@@", f"{target['coverage_h_deg']:g}").replace("@@TARGET_V@@", f"{target['coverage_v_deg']:g}")
    page = page.replace("@@REPO@@", REPO)
    (out / "index.html").write_text(page, encoding="utf-8")
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    (out / "README.md").write_text(README, encoding="utf-8")
    print(f"Built {out / 'index.html'} with {len(VARIANTS) * len(ANGLES)} render assets")


README = '''# Rolled-rectangle gallery

Static, buildless comparison of three original geometry seeds. Acoustic performance is unmeasured; these images are geometry evidence only. Fine bands are screen-mesh artifacts, not a tooling surface.

From the repository root, with the project environment containing `meshio` and `PyYAML`:

```powershell
.\\.venv\\Scripts\\python.exe tools/geometry/build_rolled_rect_page.py --renders scratch/2026-11-15_rolled_rect/final-renders --out docs/renders/2026-11-15-rolled-rect
```

The script reads source configurations, brief and quarter meshes from their repository paths; `--renders` and `--out` can point elsewhere. It copies the 15 images and derives bounding spans and node counts into `metrics.json`. The width and height mirror the positive quarter-mesh bounds; depth includes the mesh's rear extent. Seed DOFs correspond to the quarter-mesh node counts. The source mesh and render inputs are local scratch artifacts and must be retained to regenerate. No external assets or build step are needed to view the generated page.
'''


TEMPLATE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#141d20"><title>Rolled rectangle · Geometry study</title><link rel="icon" href="data:,">
<style>
:root{color-scheme:light;--ink:#172429;--muted:#5b6d6f;--bg:#f3f3ed;--accent:#9d512e}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 system-ui,-apple-system,Segoe UI,sans-serif}a{color:inherit;text-underline-offset:4px}button{font:inherit;cursor:pointer}button:focus-visible,a:focus-visible{outline:3px solid #dc8d56;outline-offset:3px}.wrap{max-width:1500px;margin:auto;padding:0 4vw}.mast{background:#17282c;color:#f6f3e9;padding:24px 0 58px}.nav{display:flex;justify-content:space-between;gap:20px;align-items:center;font-size:.8rem;letter-spacing:.12em;text-transform:uppercase}.nav a{color:#e3ded1}.intro{display:grid;grid-template-columns:1.25fr 1fr;gap:6vw;align-items:end;padding-top:65px}.kicker,.eyebrow{font-size:.72rem;letter-spacing:.15em;text-transform:uppercase;font-weight:700}.kicker{color:#e8b899}h1{font:500 clamp(3rem,6.5vw,6.8rem)/.94 Georgia,serif;letter-spacing:-.045em;margin:12px 0 0}h2{font:500 clamp(2rem,3.2vw,3.4rem)/1.05 Georgia,serif;letter-spacing:-.035em;margin:.2em 0}h3{font:500 2rem/1 Georgia,serif;margin:8px 0}.intro p{font-size:1.05rem;max-width:42em;color:#dce1dd;margin:0}.status{display:inline-block;margin-top:24px;padding:7px 12px;border:1px solid #91aaa4;border-radius:30px;font-size:.78rem;letter-spacing:.06em}.section{padding:68px 0}.section.wrap{padding:68px 4vw}.section-title{display:flex;justify-content:space-between;gap:30px;align-items:end;margin-bottom:25px}.section-title p{max-width:38em;color:var(--muted);margin:0}.selector{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:20px}.selector button{border:1px solid #b7c1bb;background:transparent;border-radius:999px;padding:8px 16px;color:var(--ink)}.selector button[aria-pressed=true]{background:var(--ink);color:white;border-color:var(--ink)}.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px}.card{background:#fff;border:1px solid #dce2dc;border-radius:5px;overflow:hidden;min-width:0}.card-head{display:flex;justify-content:space-between;padding:22px 22px 10px}.eyebrow{color:var(--accent)}.number{font:italic 1.25rem Georgia,serif;color:#a8b5ad}.hero-image,.thumb{display:block;width:100%;border:0;background:#fff;padding:0;text-align:left;position:relative}.hero-image img{display:block;width:100%;height:auto}.hero-image span{position:absolute;right:12px;bottom:10px;background:#fff;border:1px solid #e5e8e3;padding:3px 8px;border-radius:4px;font-size:.75rem}.stats{display:grid;grid-template-columns:1fr 1fr;gap:14px;padding:14px 22px 18px;border-top:1px solid #edf0ec}.stats b,.stats small{display:block}.stats b{font-size:.94rem}.stats small{font-size:.68rem;color:var(--muted)}.thumbs{display:grid;grid-template-columns:repeat(5,1fr);border-top:1px solid #edf0ec}.thumb{border-right:1px solid #edf0ec;padding:5px}.thumb img{width:100%;display:block}.thumb span{display:block;font-size:.62rem;text-align:center;color:var(--muted);line-height:1.2;padding-bottom:5px}.notes{background:#e4eae3}.note-grid{display:grid;grid-template-columns:1fr 1fr;gap:4vw}.note-grid p{max-width:55em;color:#4d6060}.links{display:flex;flex-wrap:wrap;gap:18px;font-size:.9rem}footer{padding:30px 0;font-size:.8rem;color:var(--muted)}dialog{width:min(1100px,96vw);max-width:none;border:0;padding:0;background:#fff;border-radius:5px}dialog::backdrop{background:#111d20df}.dialog-head{display:flex;justify-content:space-between;align-items:center;padding:12px 18px}.dialog-head button{border:1px solid #b7c1bb;border-radius:4px;background:white;padding:5px 12px}dialog img{display:block;width:100%;height:auto;max-height:80vh;object-fit:contain}@media(max-width:950px){.grid{grid-template-columns:1fr}.intro,.note-grid{grid-template-columns:1fr}.intro{gap:30px}.card{max-width:760px}.section-title{display:block}.section-title p{margin-top:15px}}@media(max-width:520px){.mast{padding-bottom:38px}.intro{padding-top:45px}.nav{font-size:.67rem}.section{padding:45px 0}.thumb span{font-size:.55rem}}
</style></head><body><header class="mast"><div class="wrap"><nav class="nav"><span>Hornlab / Geometry study</span><a href="#comparison">Explore the variants ↓</a></nav><div class="intro"><div><div class="kicker">An original design study · November 2026</div><h1>Rolled<br>rectangle.</h1></div><div><p>Three rectangular, rolled-mouth horn geometries. A shared silhouette, a round driver interface, and a closer look at how four-wall relief changes the surface.</p><span class="status">Geometry study · acoustic performance unmeasured</span></div></div></div></header>
<main><section class="section wrap" id="comparison"><div class="section-title"><div><div class="eyebrow">01 / Compare</div><h2>One view, three surfaces.</h2></div><p>Choose an angle to update all three main views. Select any image to enlarge it; the five smaller views remain available for each variant.</p></div><div class="selector" role="group" aria-label="Synchronized comparison angle"><button type="button" data-angle="a" aria-pressed="true">Front angled</button><button type="button" data-angle="b" aria-pressed="false">Rear angled</button><button type="button" data-angle="c" aria-pressed="false">Front</button><button type="button" data-angle="s" aria-pressed="false">Side</button><button type="button" data-angle="u" aria-pressed="false">Below</button></div><div class="grid">@@CARDS@@</div></section>
<section class="section notes"><div class="wrap note-grid"><div><div class="eyebrow">02 / Read the geometry</div><h2>Shape first.<br>Sound comes next.</h2></div><div><p>The original surface uses a shrinking-curvature contour, independently shaped horizontal and vertical profiles, and a transition from a round throat to superellipse sections. Horizontal profile depth is 0.68 of vertical profile depth. The pucker figures are input amplitudes, not measured centre-to-diagonal relief.</p><p>The common design brief specifies a @@THROAT@@ mm circular throat and a target of @@TARGET_H@@° horizontal × @@TARGET_V@@° vertical coverage. These are design inputs, not demonstrated acoustic coverage. Bounding dimensions and quarter-mesh node counts are derived from the supplied meshes; the displayed render may show fine bands from the coarse screen mesh, not a finished tooling surface.</p><p>The geometry draws visual inspiration from Joseph Crowe's rolled-mouth horns and takes a separate idea from ATH's four-wall forms. It is an original construction, not a reproduction of Crowe ES or ATH Tritonia. Acoustic simulations and evaluation remain future work; no performance or ranking is implied here.</p><div class="links"><a href="https://josephcrowe.com/blogs/news/es-600-biradial-horn">Crowe ES-600 article ↗</a><a href="https://at-horns.eu/tritonia.html">ATH Tritonia ↗</a><a href="@@REPO@@docs/research/typologies/ROLLED_RECT_FAMILY_RESEARCH_2026-11-15.md">Research dossier ↗</a><a href="metrics.json">Mesh measurements ↗</a></div></div></div></section></main><footer class="wrap">Hornlab · Geometry comparison · Source images retain their original aspect ratios.</footer>
<dialog aria-label="Enlarged geometry image"><div class="dialog-head"><strong id="dialog-label"></strong><button type="button" id="close-dialog">Close</button></div><img alt="" id="dialog-image"></dialog><script>
const angles=@@ANGLES@@; const dialog=document.querySelector('dialog'); const enlarged=document.querySelector('#dialog-image'); const label=document.querySelector('#dialog-label');let returnFocus;
document.querySelectorAll('.selector button').forEach(button=>button.addEventListener('click',()=>{document.querySelectorAll('.selector button').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));document.querySelectorAll('.card').forEach(card=>{const view=card.querySelector('.hero-image'), title=card.querySelector('h3').textContent, src=`images/${card.dataset.variant}_${button.dataset.angle}.png`, alt=`${title}, ${angles[button.dataset.angle].toLowerCase()} view`;view.dataset.src=src;view.dataset.alt=alt;view.querySelector('img').src=src;view.querySelector('img').alt=alt;});}));
document.querySelectorAll('.hero-image,.thumb').forEach(button=>button.addEventListener('click',()=>{returnFocus=button;enlarged.src=button.dataset.src;enlarged.alt=button.dataset.alt;label.textContent=button.dataset.alt;dialog.showModal();document.querySelector('#close-dialog').focus();}));document.querySelector('#close-dialog').addEventListener('click',()=>dialog.close());dialog.addEventListener('close',()=>returnFocus?.focus());
</script></body></html>'''


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--renders", type=Path, default=DEFAULT_RENDERS)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    build(args.renders.resolve(), args.out.resolve())
