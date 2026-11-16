"""Exercise the public geometry route, saved identity and replay, without solving."""
from pathlib import Path

import numpy as np
import pytest

from hornlab_search.config import load_config
from hornlab_search.design.generated import GeneratedSpace
from hornlab_search.design.generators import grid
from hornlab_search.design.generators.registry import GeneratorError
from hornlab_search.types import Design


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('name', ['k01_geometry_only', 'l01_geometry_only'])
def test_config_materializes_and_replays_bound_geometry(name):
    cfg = load_config(ROOT / 'examples/typologies/dual_lame_2026-11-16' / f'{name}.yaml')
    space = GeneratedSpace.from_config(cfg)
    block = space.seed.params['grid']
    grid.validate_grid_params(block)
    inner, meta = grid.rows_grid_points(block, block['knobs'], cfg.brief)
    assert np.isfinite(inner).all()
    assert meta['implementation_sha256'] == block['rows']['implementation_sha256']
    reloaded = Design('FREEFORM', space.seed.params)
    independent = GeneratedSpace.from_config(cfg)
    assert independent.knobs_for(reloaded) == space.seed_knobs
    corrupt = dict(block, rows={**block['rows'], 'implementation_sha256': '0' * 64})
    with pytest.raises(GeneratorError, match='implementation'):
        grid.validate_grid_params(corrupt)
