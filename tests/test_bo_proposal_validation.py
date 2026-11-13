from dataclasses import replace
import numpy as np
import pytest

from conftest import requires_mesher
from hornlab_search.bo.data import build_candidate_pool
from hornlab_search.bo.encoding import ActiveProjection
from hornlab_search.bo.propose import propose_one
from hornlab_search.config import load_config
from hornlab_search.design.space import DesignSpace


@requires_mesher
def test_real_selected_geometry_is_revalidated_and_tampering_refused():
    """Materializes real final-surface geometry through the installed mesher (no gmsh/BEM);
    without hornlab_mesher the cheap-check pool cannot produce candidates, so this test is
    environment-gated by the suite's shared ``requires_mesher`` mark."""
    cfg = load_config("examples/typologies/campaign_2026-10-26_v4/native__ath_core_v4.yaml")
    space = DesignSpace.from_config(cfg)
    encoding = ActiveProjection.from_space(space, no_ops={"morph_exponent": 4.0})
    pool = build_candidate_pool(space, encoding, cfg, n=4, seed=1234)
    assert pool.candidates
    result = propose_one(None, pool, encoding=encoding, config=cfg)
    assert result.candidate is not None, result.detail
    selected = next(c for c in pool.candidates if c.candidate_id == result.candidate_id)
    bad = replace(selected, geometry_hash="tampered")
    tampered = replace(pool, candidates=(bad,))
    refused = propose_one(None, tampered, encoding=encoding, config=cfg)
    assert refused.candidate is None and refused.reason == "capability_missing"
    assert refused.next_proposal_index == 0
    wrong = replace(selected, full_vector=selected.full_vector + 0.01)
    refused = propose_one(None, replace(pool, candidates=(wrong,)), encoding=encoding, config=cfg)
    assert refused.candidate is None and "projection" in refused.detail
