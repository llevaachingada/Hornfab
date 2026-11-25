"""CPU preflight for the cohort configs: space builds (every bound endpoint legal), envelope policy, active dims,
seed design hash, seed geometry extents and backbone body angle. No solver.

    .venv\Scripts\python.exe docs/evidence/cd_bo_cohort_2026-11-25/check_configs.py
"""
import glob
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
from hornlab_search.config import brief_for_envelope_adapter, envelope_policy, load_config  # noqa: E402
from hornlab_search.design.generators import cd_backbone_family as bf, cd_backbone_rows_family as rf  # noqa: E402
from hornlab_search.design.space import DesignSpace  # noqa: E402

for p in sorted(glob.glob('examples/typologies/cd_bo_cohort_2026-11-25/*.yaml')):
    name = Path(p).stem
    try:
        cfg = load_config(p)
        space = DesignSpace.from_config(cfg)
        pol = envelope_policy(cfg.brief)
        block = space.seed.params['grid']
        mod = rf if rf.is_family_spec(block) else bf
        meta = mod.resolve_grid(block, brief_for_envelope_adapter(cfg.brief))['meta']
        active = sorted(k for k, b in space.bounds.items() if b.search)
        print(f'{name:22s} OK policy {pol.mode} cand {pol.candidate_limits_mm} active {len(active)} '
              f'seed {space.seed.hash()[:12]} extents {meta["mouth_w_mm"]:.0f} x {meta["mouth_h_mm"]:.0f} x '
              f'{meta["x_span_mm"]:.0f} theta_c_h {meta["backbone_rows"]["theta_c_h_deg"]}')
    except Exception as exc:  # noqa: BLE001
        print(f'{name:22s} ERROR {type(exc).__name__}: {str(exc)[-200:]}')
