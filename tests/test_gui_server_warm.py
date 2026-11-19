"""Background run-index warm-up (``server.warm_in_background``). Offline: no HTTP server, no GPU.

The warm-up exists only to move ``data.list_runs`` (which parses every ``search.ndjson`` and
memoizes each summary) off the owner's first Home load. These tests pin its contract: called
first with the app's runs path, daemon thread, and every failure swallowed.
"""
from __future__ import annotations

import threading

from hornlab_search.gui import data as D
from hornlab_search.gui.server import App, warm_in_background


def _app(tmp_path):
    root = tmp_path / "repo"
    (root / "runs").mkdir(parents=True)
    return App(root)


def test_warm_calls_list_runs_once_with_runs_path(tmp_path, monkeypatch):
    app = _app(tmp_path)
    calls = []

    def recorder(runs):
        calls.append(runs)
        return []

    monkeypatch.setattr(D, "list_runs", recorder)
    t = warm_in_background(app, delay_s=0)
    t.join(timeout=5)

    assert not t.is_alive()
    # the run index is warmed FIRST; the Home endpoints (campaigns, leaders) warm after it and
    # may re-enter the memoized list_runs, so pin the first call, not the total.
    assert calls and calls[0] == app.runs


def test_warm_swallows_list_runs_exception(tmp_path, monkeypatch):
    app = _app(tmp_path)
    seen = []

    def boom(runs):
        seen.append(runs)
        raise RuntimeError("warm-up exploded")

    monkeypatch.setattr(D, "list_runs", boom)

    raised = []
    original_hook = threading.excepthook

    def hook(args):
        raised.append(args.exc_value)

    threading.excepthook = hook
    try:
        t = warm_in_background(app, delay_s=0)
        t.join(timeout=5)
    finally:
        threading.excepthook = original_hook

    assert not t.is_alive()
    assert seen and seen[0] == app.runs, "the warm-up must actually have run"
    assert raised == [], f"warm-up thread leaked an exception: {raised!r}"


def test_warm_timer_is_daemon(tmp_path):
    app = _app(tmp_path)
    t = warm_in_background(app, delay_s=30)      # never fires; only the flag is under test
    try:
        assert t.daemon is True
    finally:
        t.cancel()


def test_identical_concurrent_gets_share_one_computation(tmp_path, monkeypatch):
    """Single-flight: N simultaneous identical GETs (browser reloads, several tabs) run the
    expensive handler once, and a failure is shared rather than retried N times."""
    import time
    app = _app(tmp_path)
    calls = []

    def slow(path, q):
        calls.append(path)
        time.sleep(0.4)
        return {"ok": path}

    monkeypatch.setattr(app, "_get_uncoalesced", slow)
    out = []
    threads = [threading.Thread(target=lambda: out.append(app.get("/api/runs", {}))) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)
    assert len(calls) == 1 and len(out) == 5 and all(o == {"ok": "/api/runs"} for o in out)
    assert app._inflight == {}, "the in-flight slot must be released"

    def boom(path, q):
        calls.append("boom")
        raise ValueError("nope")

    monkeypatch.setattr(app, "_get_uncoalesced", boom)
    try:
        app.get("/api/runs", {})
    except ValueError:
        pass
    assert app._inflight == {}
