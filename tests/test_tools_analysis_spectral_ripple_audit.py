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


# --------------------------------------------------------------------------- compare

def _row(hash_, v25, v35, b25=None, b35=None):
    return {
        "design_hash": hash_,
        "fixed_angle_rms_db": {"25.0": v25, "35.0": v35},
        "fixed_angle_band_mean_db": {"25.0": v25 if b25 is None else b25,
                                     "35.0": v35 if b35 is None else b35},
    }


def _write_audit(path, rows):
    path.write_text(json.dumps({"rows": rows}), encoding="utf-8")
    return path


def test_compare_joins_by_hash_reports_deltas_and_spearman(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    a = _write_audit(tmp_path / "a" / "audit.json", [
        _row("h1", 1.0, 2.0, 10.0, 20.0),
        _row("h2", 2.0, 3.0, 11.0, 21.0),
        _row("h3", 3.0, 4.0, 12.0, 22.0),
        _row("only-a", 9.0, 9.0),
    ])
    b = _write_audit(tmp_path / "b" / "audit.json", [
        _row("h1", 1.5, 2.5, 10.5, 20.5),
        _row("h2", 2.5, 3.5, 11.5, 21.5),
        _row("h3", 3.5, 4.5, 12.5, 22.5),
        _row("only-b", 8.0, 8.0),
    ])
    out = tmp_path / "cmp"
    assert A.main(["--compare", str(a), str(b), "--out", str(out)]) == 0
    md = (out / "compare.md").read_text(encoding="utf-8")
    assert "1.441" in md and "1.908" in md and "1.313" in md
    assert "only rankings and deltas are quotable" in md
    assert "A rank correlation is not accuracy" in md
    assert "`only-a`" in md and "`only-b`" in md
    assert "| 0.500 |" in md          # every B-A trend delta is +0.5
    assert "| 1.0000 |" in md         # both V+25 and V+35 rank orders are perfect
    assert "| 3 |" in md              # n joined
    # band_mean values are carried from both sides
    assert "20.000" in md and "20.500" in md


def test_compare_below_three_joined_has_null_spearman_with_reason(tmp_path):
    a = _write_audit(tmp_path / "a.json", [_row("h1", 1.0, 2.0), _row("h2", 2.0, 3.0)])
    b = _write_audit(tmp_path / "b.json", [_row("h1", 1.5, 2.5), _row("h2", 2.5, 3.5)])
    out = tmp_path / "cmp"
    assert A.main(["--compare", str(a), str(b), "--out", str(out)]) == 0
    md = (out / "compare.md").read_text(encoding="utf-8")
    assert "null" in md
    assert "need n>=3 finite joined pairs" in md


def test_compare_missing_input_exits_2_and_names_it(tmp_path, capsys):
    b = _write_audit(tmp_path / "b.json", [_row("h1", 1.0, 2.0)])
    missing = tmp_path / "nope.json"
    out = tmp_path / "cmp"
    assert A.main(["--compare", str(missing), str(b), "--out", str(out)]) == 2
    assert str(missing) in capsys.readouterr().out
