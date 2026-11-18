"""Boundary Lab (BL) external adapter — hornlab_search.system.boundarylab.

Boundary Lab is pinned, read-only, and runs in ITS OWN environment (never imported into the
HornLab venv). This package's job (Stage 1): discover the installed BL (:mod:`.probe`), drive
its ORIGINAL bundled vented-enclosure generator (:mod:`.generate`), and wrap its headless
``blab project validate --json`` (:mod:`.run`). Solver invocations are gated off by default.
"""
from hornlab_search.system.boundarylab.probe import (  # noqa: F401
    BLCapabilityError,
    BLRoot,
    BLProbeResult,
    probe_boundarylab,
)
from hornlab_search.system.boundarylab.run import BlockedByGate  # noqa: F401
from hornlab_search.system.boundarylab.generate import (  # noqa: F401
    GenerationResult,
    VENTED_PROVIDER_ID,
    generate_vented,
)

__all__ = [
    "BLCapabilityError", "BLRoot", "BLProbeResult", "probe_boundarylab",
    "BlockedByGate", "GenerationResult", "VENTED_PROVIDER_ID", "generate_vented",
]
