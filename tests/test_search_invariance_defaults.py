"""Day group B headline invariance test (IMPLEMENTATION_PLAN_2026-11-12-Day section 2, "Group B"):

absent new keys, every new behaviour is opt-in and the default path must be byte-identical to
origin/main. This file pins two goldens computed at origin/main tip (2ecbc69 lineage, worktree
branch day/B-search-features at the 2026-11-12 day, pycma 4.5.0, ribs 0.12.0):

  * config_sha of ``examples/osse_baseline.yaml`` with CMA seed 1234, and
  * the first 5 CMA-ES ask design hashes (normalized seed x0 = search x0, pycma popsize default,
    ``bounds=[0,1]``, ``seed=1234``) mapped through ``DesignSpace.denormalize`` -> Design.hash().

The goldens are literal constants: any change below that alters the default config hash or the
default ask/evaluate order fails here, so a reviewer can prove "defaults unchanged" without a
diff of the search loop. If a golden legitimately changes (e.g. an intentional default policy
change with owner sign-off), update the constants together with the PR body evidence.
"""
from __future__ import annotations

import cma as cma_lib
import numpy as np
import pytest

from hornlab_search.config import load_config
from hornlab_search.design.space import DesignSpace
from hornlab_search.search import cma as cma_mod
from hornlab_search.search import rundir

from test_search_support import LIBS, SyntheticBackend

CONFIG_PATH = "examples/osse_baseline.yaml"
CMA_SEED = 1234

# Goldens computed at origin/main tip (branch day/B-search-features == origin/main, 2026-11-12).
CONFIG_SHA_GOLDEN = "830f2877c73d"
FIRST_FIVE_ASKS_GOLDEN = ["c54661892c59", "16905720dfc2", "8f7d77bd7bfd",
                          "71eb65ed4c01", "a646a66242a9"]
SEED_DESIGN_HASH_GOLDEN = "8443a5763be5"
# The search loop evaluates the seed first, then the ask order above (a stub evaluator records
# designs in evaluation order), so the FIRST_FIVE_EVALUATED golden is derived, not free-floating.
FIRST_FIVE_EVALUATED_GOLDEN = [SEED_DESIGN_HASH_GOLDEN] + FIRST_FIVE_ASKS_GOLDEN[:4]


def _es_options() -> dict:
    """Exactly the options ``cma.search`` passes today for a plain default config (single ES,
    no ``search.restarts``, ``popsize`` None -> pycma's own default)."""
    return {"bounds": [0.0, 1.0], "seed": CMA_SEED, "tolfun": 1.0e-3,
            "verb_disp": 0, "verbose": -1}


def test_default_config_sha_and_first_five_asks_are_unchanged(tmp_path):
    cfg = load_config(CONFIG_PATH, cma_seed=CMA_SEED)
    assert rundir.config_sha(cfg.raw) == CONFIG_SHA_GOLDEN
    space = DesignSpace.from_config(cfg)
    x0 = list(map(float, space.normalize(space.seed)))
    es = cma_lib.CMAEvolutionStrategy(x0, float(cfg.search.sigma0), _es_options())
    # One draw at a time: the CMA RNG stream is shared, so the concatenated single draws are
    # the same samples, in the same order, as the popsize batches ``cma.search`` asks. No
    # tell() is involved, so the ES state stays untouched.
    hashes = []
    while len(hashes) < 5:
        x = es.ask(number=1)[0]
        hashes.append(space.denormalize(np.asarray(x, dtype=float)).hash())
    assert hashes == FIRST_FIVE_ASKS_GOLDEN


def test_default_search_loop_evaluates_the_same_first_five_designs(tmp_path, monkeypatch):
    """The full ``cma.search`` wiring (seed first, budget check, ask -> denormalize -> evaluate)
    with a stub evaluator that records the design order. With every new opt-in key absent, the
    order must equal the origin/main sequence."""
    cfg = load_config(CONFIG_PATH, cma_seed=CMA_SEED)
    seen: list[str] = []

    def stub(design, space, cfg, mode, run_dir, store, backend, **kw):
        seen.append(design.hash())
        # A constant objective keeps the real pycma tell() bookkeeping away from the golden:
        # the CMA state after gen-1 tell is irrelevant, the ASK/EVALUATE order is what we pin.
        from hornlab_search.types import Evaluation, SolveOutcome
        return Evaluation(design_hash=design.hash(), design=design, mesh_hash="m", solve_hash="s",
                          objective=1.0, terms={}, metrics=None, mesh=None,
                          outcome=SolveOutcome(True, None, 0.0, None, ""), cached=False, error="")

    monkeypatch.setattr(cma_mod, "evaluate", stub)
    best = cma_mod.search(cfg, tmp_path / "r", "screen", backend=SyntheticBackend(), budget=5,
                          store=None, lib_shas=LIBS)
    assert seen == FIRST_FIVE_EVALUATED_GOLDEN
    assert best is not None
