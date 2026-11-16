"""Plot physical axis cuts and projected relief rings of the canonical family."""
from pathlib import Path
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from hornlab_search.config import load_config
from hornlab_search.design.space import DesignSpace
from hornlab_search.design.generators.rolled_family import resolve_grid


def plot(out):
    fig, axes = plt.subplots(2, 3, figsize=(16, 9), constrained_layout=True)
    for row, family in enumerate(('rect', 'section')):
        surfaces = []
        for suffix in ('control', 'axial', 'radial'):
            cfg = load_config(ROOT/f'examples/typologies/rolled_family_2026-11-15/rf__{family}_{suffix}_v7.yaml')
            resolved = resolve_grid(DesignSpace.from_config(cfg).seed.params['grid'], cfg.brief)
            surfaces.append(resolved)
        for geometry, label, colour, style in zip(surfaces, ('Base', 'Axial +3/+4 mm', 'Inward 3/4 mm'),
                                                 ('#606d75', '#c06e2d', '#127b86'), ('--', ':', '-')):
            pts = geometry['inner_points']
            for col, axis, rindex in ((0, 0, 0), (1, -1, 1)):
                axes[row, col].plot(pts[axis, :, rindex], pts[axis, :, 2], linestyle=style,
                                    color=colour, linewidth=2, label=label)
            stations = np.asarray(geometry['meta']['stations'])
            ring = np.array([[np.interp(.8, stations, line[:, c]) for c in (0, 1)] for line in pts])
            for sx, sy in ((1, 1), (-1, 1), (-1, -1), (1, -1)):
                axes[row, 2].plot(sx*ring[:, 0], sy*ring[:, 1], linestyle=style,
                                  color=colour, linewidth=2, label=label if sx == sy == 1 else None)
        prefix = 'Rolled rectangle' if family == 'rect' else 'Section reference'
        for col, title in enumerate(('Horizontal centre cut', 'Vertical centre cut', 'Projected station s=0.80')):
            ax = axes[row, col]
            ax.set_title(prefix+' / '+title, fontsize=11)
            ax.set_aspect('equal', adjustable='datalim')
            ax.set_xlabel('Horizontal / radial position (mm)' if col != 1 else 'Vertical radius (mm)')
            ax.set_ylabel('Forward depth z (mm)' if col < 2 else 'Vertical position (mm)')
            ax.grid(alpha=.2)
            ax.legend(fontsize=8)
    fig.get_layout_engine().set(rect=(0, .07, 1, .92))
    fig.suptitle('Radial inward relief changes radius; axial relief changes depth', fontsize=16)
    fig.text(.5, .012, 'Centre cuts are physical H/V sections. Right column projects a shared profile station; it is not a constant-z section.\nOriginal hybrid geometry; not a reproduction of the ATH formula. Source throat and returned attachment remain fixed.',
             ha='center', fontsize=10)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=170, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(out)


if __name__ == '__main__':
    plot(ROOT/'scratch/2026-11-15_family_master/radial-vs-axial.png')
