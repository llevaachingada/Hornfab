"""`hornlab-search compare`: report metric differences between two solved runs (e.g. the
freeform_sculpt symmetry check, quarter vs full domain). Report only; no pass threshold."""
import json

import numpy as np
import pytest

from hornlab_search.cli import compare_metrics, main
from hornlab_search.search.evaluate import metrics_to_json
from hornlab_search.types import MetricSet

F = np.array([500.0, 1000.0, 2000.0, 3000.0])


def _ms(shift=0.0, src="balloon", freqs=F):
    n = len(freqs)
    return MetricSet(freqs, np.full(n, 90.0 + shift), np.full(n, 80.0), np.full(n, 9.0 + shift),
                     src, np.full(n, 1.0), np.full(n, 1.0), np.zeros(n), None)


def _run(tmp_path, name, m, quadrants="1", h="abc"):
    d = tmp_path / name
    d.mkdir()
    rows = [{"design_hash": h, "metrics": None, "mesh": None},             # a failed row first
            {"design_hash": h, "metrics": metrics_to_json(m), "mesh": {"quadrants": quadrants}}]
    (d / "search.ndjson").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    return d


def test_compare_metrics_values():
    r = compare_metrics(_ms(), _ms(0.02))
    assert r["di_db"]["max"] == pytest.approx(0.02) and r["bw_v_deg"]["max"] == 0.0
    with pytest.raises(ValueError, match="frequency grids differ"):
        compare_metrics(_ms(), _ms(freqs=F * 1.1))


def test_cli_compare_reports_and_refuses_bad_inputs(tmp_path, capsys):
    a = _run(tmp_path, "a", _ms(), "1")
    b = _run(tmp_path, "b", _ms(0.03), "1234")
    assert main(["compare", str(a), str(b)]) == 0
    out = capsys.readouterr().out
    assert "di_db" in out and "0.03" in out and "'1234'" in out and "compare OK" in out
    c = _run(tmp_path, "c", _ms(src="cuts_estimate"))
    assert main(["compare", str(a), str(c)]) == 1
    assert "balloon" in capsys.readouterr().out
    (tmp_path / "empty").mkdir()
    assert main(["compare", str(a), str(tmp_path / "empty")]) == 1
    assert "no solved row" in capsys.readouterr().out
