"""WP 0.6 restart idempotency and WP 0.7 watchdog stop truth (offline, synthetic ndjson)."""
from __future__ import annotations

import json
from pathlib import Path

import tools.run_campaign_night as night
from tests.test_night_runner_live import HookRunner, _run, _write


def _state(nd: Path) -> dict:
    return json.loads((nd / "queue_state.json").read_text(encoding="utf-8"))


def test_restart_after_finished_job_does_not_rerun_it(tmp_path):
    nf = tmp_path / "n.yaml"
    _write(nf, ["a", "b", "c"])
    first = HookRunner()
    nd = _run(tmp_path, nf, first)
    assert first.ran == ["a", "b", "c"]
    # simulate a crash after "a" finished: state says a done, b was running
    payload = _state(nd)
    payload.update(state="running", done=["a"], running="b", pending=["c"])
    (nd / "queue_state.json").write_text(json.dumps(payload), encoding="utf-8")
    second = HookRunner()
    _run(tmp_path, nf, second)
    assert second.ran == ["b", "c"]
    assert _state(nd)["done"] == ["a", "b", "c"]


def test_absent_or_unreadable_state_behaves_as_before(tmp_path, capsys):
    nf = tmp_path / "n.yaml"
    _write(nf, ["a", "b"])
    plan = night.load_night(nf, repo_root=tmp_path)
    nd = night.night_dir_for(plan, runs_root=tmp_path / "runs", repo_root=tmp_path)
    nd.mkdir(parents=True)
    assert night._load_done(nd, plan) == []          # absent: silent
    (nd / "queue_state.json").write_text("{not json", encoding="utf-8")
    runner = HookRunner()
    _run(tmp_path, nf, runner)
    assert runner.ran == ["a", "b"]
    assert "WARNING" in capsys.readouterr().err


def test_other_nights_state_is_ignored(tmp_path):
    nf = tmp_path / "n.yaml"
    _write(nf, ["a"])
    plan = night.load_night(nf, repo_root=tmp_path)
    nd = night.night_dir_for(plan, runs_root=tmp_path / "runs", repo_root=tmp_path)
    nd.mkdir(parents=True)
    (nd / "queue_state.json").write_text(json.dumps({"night": "other", "done": ["a"]}), encoding="utf-8")
    assert night._load_done(nd, plan) == []


ROWS = [
    {"n": 0, "ok": True, "objective": 3.5, "kind": ""},
    {"n": 1, "ok": True, "objective": 2.25, "kind": ""},
    {"n": 2, "ok": True, "objective": 1000.0, "kind": ""},
    {"n": 3, "ok": False, "objective": 1000.0, "kind": "invalid_geometry", "error": "invalid_geometry: x"},
    {"n": 4, "ok": False, "objective": 1000.0, "error": "invalid_envelope: mouth"},
    {"n": 5, "ok": False, "objective": 1000.0, "kind": "mesh_too_large"},
    {"n": 6, "ok": False, "objective": 1000.0, "kind": "solve_failed"},
    {"n": 7, "ok": False, "objective": 1000.0, "kind": "metrics_failed"},
]


def test_summarize_ndjson_best_and_counts():
    best, counts = night.summarize_ndjson(ROWS)
    assert best == 2.25
    assert counts == {"ok": 3, "invalid_geometry": 1, "invalid_envelope": 1,
                      "mesh_too_large": 1, "solve_failed": 1, "other": 1}
    assert night.summarize_ndjson([{"ok": False, "kind": "solve_failed"}])[0] is None
    assert night.summarize_ndjson([{"ok": True, "objective": float("nan")}])[0] is None


class StopRunner(HookRunner):
    """Writes a watchdog-stopped log and a synthetic run dir, as the real runner would."""

    def __init__(self, run_dir: Path):
        super().__init__()
        self.run_dir = run_dir

    def run(self, job, log_path):
        self.run_dir.mkdir(parents=True)
        (self.run_dir / "search.ndjson").write_text(
            "".join(json.dumps(r) + "\n" for r in ROWS) + '{"torn', encoding="utf-8")
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(f"\n=== WATCHDOG stalled; stopping job {job.id} (pid 1)\n"
                     f"search ABORTED: watchdog (partial results in {self.run_dir})\n")
        return night.WATCHDOG_EXIT, False


def test_watchdog_stop_record_has_best_j_and_outcome_counts(tmp_path):
    nf = tmp_path / "n.yaml"
    _write(nf, ["w"])
    runner = StopRunner(tmp_path / "runs" / "r1")
    nd = _run(tmp_path, nf, runner)
    rec = json.loads((nd / "summary.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert rec["status"] == "watchdog"
    assert rec["best_J"] == 2.25
    assert rec["evals_ndjson"] == 9          # historical count_evals (non-empty lines) unchanged
    assert rec["outcome_counts"]["ok"] == 3 and rec["outcome_counts"]["solve_failed"] == 1
    assert "outcomes ok=3" in rec["note"]


def test_non_watchdog_record_has_no_new_keys(tmp_path):
    nf = tmp_path / "n.yaml"
    _write(nf, ["a"])
    nd = _run(tmp_path, nf, HookRunner())
    rec = json.loads((nd / "summary.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert "outcome_counts" not in rec


# ------------------------------------------------------------------ WP 7.1 protected lanes

def test_protected_lanes_file_marks_jobs_and_false_turns_it_off(tmp_path):
    import yaml as _yaml
    from tools import run_campaign_night as rcn
    (tmp_path / "examples").mkdir()
    (tmp_path / "examples" / "protected_lanes.yaml").write_text(
        _yaml.safe_dump({"lanes": [{"lane": "hl__keep_me_v7"}, "other_v1"]}))
    assert rcn.load_protected_lanes(None, repo_root=tmp_path) == {"hl__keep_me_v7", "other_v1"}
    assert rcn.load_protected_lanes(False, repo_root=tmp_path) == frozenset()
    import pytest
    with pytest.raises(ValueError, match="not found"):
        rcn.load_protected_lanes("nope.yaml", repo_root=tmp_path)
    job = rcn.Job(id="j", kind="search", argv=("x",), timeout_s=1.0,
                  config="examples/typologies/hl__keep_me_v7.yaml")
    assert rcn._job_lane(job) == "hl__keep_me_v7"


def test_shipped_protected_list_parses_and_excludes_no_evidence_lanes():
    from pathlib import Path
    from tools import run_campaign_night as rcn
    root = Path(__file__).resolve().parents[1]
    lanes = rcn.load_protected_lanes(None, repo_root=root)
    assert "hl__biradial_es_style_v7" in lanes and "hl__klangfilm_lame_curved_v1" in lanes
    assert "hl__ext_throat_hvlaw_v7" not in lanes and "rf__rect_radial_wide_v7" not in lanes


def test_watchdog_on_a_protected_job_only_advises():
    import inspect
    from tools import run_campaign_night as rcn
    src = inspect.getsource(rcn)
    assert "WATCHDOG ADVISORY (protected lane)" in src
    i = src.index("WATCHDOG ADVISORY (protected lane)")
    assert "wd_reason = None" in src[i:i + 400]         # no kill path follows the advisory
