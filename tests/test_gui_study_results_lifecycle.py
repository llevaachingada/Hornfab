from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
STUDY_RESULTS = ROOT / "hornlab_search/gui/static/study_results.js"
APP = ROOT / "hornlab_search/gui/static/app.js"
HARNESS = Path(__file__).with_name("gui_study_results_lifecycle.mjs")


def test_study_results_lifecycle_dom_stub():
    """The Results workspace lifecycle: mount, default selection, Inspect click -> detail fetch,
    pushState selection, inspector repaint; missing-artifact rows still state their reason."""
    result = subprocess.run(
        ["node", str(HARNESS), str(STUDY_RESULTS), str(APP)],
        capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "study results lifecycle ok" in result.stdout
