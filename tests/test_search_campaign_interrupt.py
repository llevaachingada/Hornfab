"""Offline: Ctrl-C during a campaign (HANDOFF_BETA D3). The child search gets the same Ctrl-C and must
be allowed to clean up; the campaign writes a partial leaderboard marked INTERRUPTED; hosts are
cleared after every job (GPU rule 6)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from hornlab_search.search import campaign as camp

REPO = Path(__file__).resolve().parents[1]
BRIEF = REPO / "examples" / "briefs" / "axi_90x90_1in.yaml"


class FakeHyg:
    def __init__(self, procs=2):
        self.procs, self.cleared = procs, 0

    def hygiene_snapshot(self, label):
        return {"label": label, "julia_project_procs": self.procs, "julia_pids": [1, 2][: self.procs],
                "vram_used_mib": 700.0}

    def clear_julia(self):
        self.cleared += 1
        return [1, 2][: self.procs]


class FakePopen:
    """communicate() raises KeyboardInterrupt once (Ctrl-C in the parent), then returns the child's
    output, as a child that handled its own Ctrl-C would."""
    calls = []

    def __init__(self, argv, **kw):
        self.argv, self.returncode, self.n = argv, None, 0

    def communicate(self, timeout=None):
        self.n += 1
        FakePopen.calls.append(timeout)
        if self.n == 1:
            raise KeyboardInterrupt
        self.returncode = 1
        return "search INTERRUPTED: partial results are in nowhere (resume with --resume)\n", ""

    def kill(self):
        raise AssertionError("the child must get its grace period, not be killed")

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _entry():
    return next(e for e in camp.load_catalog() if e["name"] == "conical")


def test_run_job_gives_the_child_its_grace_period_and_raises_with_the_partial_job(monkeypatch, tmp_path):
    FakePopen.calls = []
    monkeypatch.setattr(camp.subprocess, "Popen", FakePopen)
    hyg = FakeHyg()
    with pytest.raises(camp.CampaignInterrupted) as ei:
        camp.run_job(_entry(), BRIEF, 1, 40, tmp_path, "screen", hygiene_module=hyg)
    job = ei.value.job
    assert job.error == "interrupted (Ctrl-C)" and job.returncode == 1
    assert FakePopen.calls == [None, camp.INTERRUPT_GRACE_S]
    assert hyg.cleared == 1 and job.hygiene_after["cleared_pids"] == [1, 2]


def test_campaign_interrupt_writes_a_partial_leaderboard_and_reraises(monkeypatch, tmp_path):
    def fake_run_job(entry, brief_path, seed, budget, runs_dir, tier, hygiene_module=None):
        job = camp.JobResult(entry_name=entry["name"], seed=seed)
        job.error = "interrupted (Ctrl-C)"
        raise camp.CampaignInterrupted(job)
    monkeypatch.setattr(camp, "run_job", fake_run_job)
    with pytest.raises(KeyboardInterrupt) as ei:
        camp.run_campaign(BRIEF, "conical,exponential", "screen", tmp_path, hygiene_module=FakeHyg())
    cdir = Path(str(ei.value))
    md = (cdir / "leaderboard.md").read_text(encoding="utf-8")
    assert "INTERRUPTED" in md and "conical" in md and "exponential" not in md
    cj = json.loads((cdir / "campaign.json").read_text(encoding="utf-8"))
    assert cj["interrupted"] is True and cj["entries"][0]["jobs"][0]["error"] == "interrupted (Ctrl-C)"


def test_hosts_are_cleared_after_every_job_and_not_when_none_are_left():
    hyg = FakeHyg(procs=2)
    assert camp._after_job_hygiene(hyg, {"name": "x"}, 1)["cleared_pids"] == [1, 2]
    hyg0 = FakeHyg(procs=0)
    snap = camp._after_job_hygiene(hyg0, {"name": "x"}, 1)
    assert hyg0.cleared == 0 and "cleared_pids" not in snap
