"""Package saved solved meshes in HornLab's browser playback format."""

import argparse
import json
from pathlib import Path

from hornlab_search.gui.data import mesh_surface_at, read_ndjson


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo', type=Path)
    parser.add_argument('out', type=Path)
    parser.add_argument('runs', nargs='+')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    for run in args.runs:
        run_dir = args.repo / 'runs' / run
        rows = read_ndjson(run_dir / 'search.ndjson')
        frames = []
        skipped = []
        best_so_far = float('inf')
        for row in rows:
            if not row.get('ok') or row.get('objective') is None:
                continue
            improved = row['objective'] < best_so_far
            best_so_far = min(row['objective'], best_so_far)
            if not improved:
                continue
            key = row['design_hash']
            design_dir = run_dir / 'designs' / key
            if not (design_dir / 'mesh.msh').is_file():
                skipped.append(row['n'])
                continue
            data = mesh_surface_at(design_dir, run_dir, key, max_tris=30000)
            frames.append(dict(
                n=row['n'], objective=row['objective'], improved=improved,
                quadrants=data['quadrants'], verts=data['verts'], tris=data['tris'],
                n_tris_full=data['n_tris'], decimated=data.get('decimated', False),
                n_verts=len(data['verts'])//3, design_hash=key,
            ))
        if not frames:
            raise RuntimeError(f'{run} has no solved meshes')
        payload = dict(
            run_id=run, available=True, frames=frames, total_evaluations=len(rows),
            missing_mesh_evaluations=skipped,
        )
        (args.out / f'{run}.json').write_text(json.dumps(payload, separators=(',', ':')), encoding='utf-8')
        print(f'{run}: {len(frames)} solved meshes, {sum(f["improved"] for f in frames)} records, '
              f'{len(rows)-len(frames)} with no solved mesh', flush=True)


if __name__ == '__main__':
    main()
