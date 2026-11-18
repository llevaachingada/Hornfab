"""Owner decision R7 (2026-11-18, cloud senior under delegation): the Klangfilm H/V kernel files are
FROZEN at their pre-b06a938 content, so every stored recipe keeps its geometry identity. b06a938
changed only comments but moved both `implementation_sha256` values; its code part is reverted and
the corrected facts live in docs/knowledge/contracts/klangfilm_lame_hv.md (errata section).

`implementation_digest()` folds `numpy=<ver>;scipy=<ver>` into the hash, so its absolute value is
environment-specific by construction (the owner box under numpy 2.5.4 / scipy 1.18.1 gives
1304dea3.../a032f660...; the cloud review container gave ee160698.../c65beb16...). Pinning those
absolute values would fail on every other dependency set, so this test pins the FROZEN FILE BYTES
and separately checks the digest recipe. If it fails, someone edited a frozen kernel file: revert
the edit, or ship the change as a NEW versioned kernel (new file + new schema) and leave these
files alone."""
import hashlib
from pathlib import Path

import numpy as np
import scipy

from hornlab_search.design.generators import _klangfilm_lame_hv_core_v1 as core_kernel
from hornlab_search.design.generators import _klangfilm_lame_hv_v1 as hv_kernel
from hornlab_search.design.generators import _klangfilm_lame_v1 as parent
from hornlab_search.design.generators import _lame_cap_v1 as lame_cap
from hornlab_search.design.generators import klangfilm_lame_hv_core_family as core
from hornlab_search.design.generators import klangfilm_lame_hv_family as hv
from hornlab_search.design.generators import lame_shell

CORE_CONTENT_DIGEST = "36d8bcbd159f776ce28866de25e66f4feef1a30c9db2a71eec48c0e1fc4c6905"
HV_CONTENT_DIGEST = "dee86bc1fee3b009ce61d3c1c137bd3735a4461320de5a1babb202c84a8df063"


def _files(adapter, kernel):
    return (Path(adapter.__file__), Path(kernel.__file__), Path(parent.__file__),
            Path(lame_cap.__file__), Path(lame_shell.__file__))


def _content_digest(adapter, kernel):
    digest = hashlib.sha256()
    for path in _files(adapter, kernel):
        data = path.read_bytes().replace(b"\r\n", b"\n")
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest()


def _digest_recipe(adapter, kernel):
    """Independent re-implementation of the adapter's digest recipe, version suffix included."""
    digest = hashlib.sha256()
    for path in _files(adapter, kernel):
        data = path.read_bytes().replace(b"\r\n", b"\n")
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    digest.update(f"numpy={np.__version__};scipy={scipy.__version__}".encode())
    return digest.hexdigest()


def test_klangfilm_hv_core_files_are_frozen():
    assert _content_digest(core, core_kernel) == CORE_CONTENT_DIGEST


def test_klangfilm_hv_files_are_frozen():
    assert _content_digest(hv, hv_kernel) == HV_CONTENT_DIGEST


def test_implementation_digest_uses_the_pinned_files_and_environment_suffix():
    assert core.implementation_digest() == _digest_recipe(core, core_kernel)
    assert hv.implementation_digest() == _digest_recipe(hv, hv_kernel)
