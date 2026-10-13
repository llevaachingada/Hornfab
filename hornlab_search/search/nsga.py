"""Multi-objective search. Phase 2.

NSGA-II needs roughly 100 individuals x 100 generations = 10,000 evaluations.
At the measured seconds per candidate (see run.json), that is impractical
against real BEM. It becomes the right algorithm the moment a surrogate can
evaluate a population in one batched forward pass. See 11_PHASE2_SURROGATE.md.
"""
from __future__ import annotations

from ..types import Evaluation


def search_pareto(cfg, run_dir, evaluator) -> list[Evaluation]:
    """``evaluator`` maps a batch of designs to Evaluations; phase 2 swaps a surrogate in here
    without touching the search code."""
    raise NotImplementedError("phase 2")
