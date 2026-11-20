from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
HARNESS = Path(__file__).with_name("gui_hw_lifecycle.mjs")


def test_hw_gui_lifecycle_dom_stub():
    """Every horn + woofer view mounts without throwing on a DOM stub, the geometry3d tab
    installs and clears its router dispose hook, 10 mount/dispose cycles leak no listeners,
    observers or timers, and the DSP page is fed per-channel arrays only (never a sum)."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not available; run `node tests/gui_hw_lifecycle.mjs` where it is")
    result = subprocess.run(
        [node, str(HARNESS)],
        capture_output=True, text=True, timeout=180, cwd=str(ROOT),
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "hw GUI lifecycle ok" in result.stdout
