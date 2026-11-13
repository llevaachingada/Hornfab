from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
STUDIES = ROOT / "hornlab_search/gui/static/studies.js"
APP = ROOT / "hornlab_search/gui/static/app.js"
FIXTURE = Path(__file__).with_name("gui_study_lifecycle.mjs")


def test_gui_study_lifecycle_dom_stub():
    result = subprocess.run(
        ["node", str(FIXTURE), str(STUDIES), str(APP)],
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "study lifecycle ok" in result.stdout
