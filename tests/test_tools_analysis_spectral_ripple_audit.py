"""spectral_ripple_audit CLI: smoke output and non-empty --out refusal."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.analysis import spectral_ripple_audit as A

REPO = Path(__file__).resolve().parents[1]
DESIGN = (REPO / "docs/evidence/runs/scout40_2026-11-19"
          / "20261119T073330Z-screen-723756/designs/ee85bcd2ad67")


def test_cli_smoke_writes_audit_and_markdown(tmp_path):
    assert (DESIGN / "response.npz").is_file()
    out = tmp_path / "spectral_audit"
    assert A.main([str(DESIGN), "--out", str(out)]) == 0
    assert (out / "audit.json").is_file()
    assert (out / "disagreement.md").is_file()

    audit = json.loads((out / "audit.json").read_text(encoding="utf-8"))
    assert audit["provenance"]["band_hz"] == [1065.0, 4832.5]
    row = audit["rows"][0]
    assert row["design_hash"] == "ee85bcd2ad67"
    assert row["fixed_angle_rms_db"]["25.0"] == pytest.approx(1.151, abs=2e-3)
    assert row["fixed_angle_rms_db"]["35.0"] == pytest.approx(1.441, abs=2e-3)
    assert "25.0" in row["fixed_angle_band_mean_db"]
    # the objective's own weighted rip term for this design (the number J charged)
    assert row["objective_rip"] == pytest.approx(0.408, abs=2e-3)
    md = (out / "disagreement.md").read_text(encoding="utf-8")
    assert "rip(term)" in md and "rip(metrics)" in md


def test_cli_refuses_non_empty_out(tmp_path):
    (tmp_path / "occupied.txt").write_text("x", encoding="utf-8")
    with pytest.raises(SystemExit):
        A.main([str(DESIGN), "--out", str(tmp_path)])
