"""Owner decision R7 (2026-11-18, cloud senior under delegation): the Klangfilm H/V kernel digests
are FROZEN at their pre-b06a938 values, so every stored recipe keeps rebuilding. b06a938 changed
only comments but moved both `implementation_sha256` values; its code part is reverted and the
corrected facts live in docs/knowledge/contracts/klangfilm_lame_hv.md (errata section).

If this test fails, someone edited a frozen kernel file. Revert the edit, or ship the change as a
NEW versioned kernel (new file + new schema) and leave these files alone."""
from hornlab_search.design.generators import klangfilm_lame_hv_core_family as core
from hornlab_search.design.generators import klangfilm_lame_hv_family as hv

CORE_DIGEST = "ee160698016206cd002a405d197f9eeb09413e941891e60b0f72cf06e725a4b6"
HV_DIGEST = "c65beb168733a06e2653edd90908d0b3f67b7018632e6f98d71a2816f8cb6bcb"


def test_klangfilm_hv_core_digest_is_frozen():
    assert core.implementation_digest() == CORE_DIGEST


def test_klangfilm_hv_digest_is_frozen():
    assert hv.implementation_digest() == HV_DIGEST
