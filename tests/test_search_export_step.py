"""`hornlab-search export-step`: STEP solids of a run's top designs or a config's seed."""
import json
import shutil

from conftest import EXAMPLES, requires_mesher
from hornlab_search.cli import main


def test_export_step_needs_exactly_one_source(tmp_path, capsys):
    assert main(["export-step"]) == 2                       # argparse: group is required
    assert main(["export-step", "--run", str(tmp_path)]) == 1
    assert "no config.yaml / search.ndjson" in capsys.readouterr().out


def test_export_step_run_without_successes(tmp_path, capsys):
    shutil.copy(EXAMPLES / "osse_baseline.yaml", tmp_path / "config.yaml")
    (tmp_path / "search.ndjson").write_text(json.dumps({"ok": False, "design_hash": "x"}) + "\n")
    assert main(["export-step", "--run", str(tmp_path)]) == 1
    assert "no successful design" in capsys.readouterr().out


@requires_mesher
def test_export_step_seed_writes_a_step_file(tmp_path, capsys):
    out = tmp_path / "step"
    assert main(["export-step", "--config", str(EXAMPLES / "osse_baseline.yaml"), "--out", str(out)]) == 0
    files = list(out.glob("osse_baseline_seed_*.step"))
    assert len(files) == 1 and files[0].stat().st_size > 10_000
    assert "export-step OK: 1 of 1" in capsys.readouterr().out


@requires_mesher
def test_export_step_run_ranks_distinct_designs(tmp_path, capsys):
    import yaml
    cfg = yaml.safe_load((EXAMPLES / "osse_baseline.yaml").read_text())
    (tmp_path / "config.yaml").write_text(yaml.safe_dump(cfg))
    seed = {"family": cfg["family"], "params": cfg["seed_params"], "ok": True}
    rows = [dict(seed, design_hash="aaa", objective=5.0), dict(seed, design_hash="aaa", objective=5.0),
            {"ok": False, "design_hash": "bad"}]
    (tmp_path / "search.ndjson").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    assert main(["export-step", "--run", str(tmp_path), "--top", "3"]) == 0
    assert len(list((tmp_path / "step").glob("*_rank1_aaa.step"))) == 1
    assert "1 of 1 written" in capsys.readouterr().out
