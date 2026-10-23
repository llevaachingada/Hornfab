"""Local web GUI (hornlab_search/gui): readers, launcher allow-list, server safety. Offline, no GPU,
no real CLI jobs (the launcher is pointed at a harmless sleep script)."""
from __future__ import annotations

import json
import os
import shutil
import socket
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import numpy as np
import pytest
import yaml

from hornlab_search.gui import data as D
from hornlab_search.gui import jobs as J
from hornlab_search.gui.server import App, make_handler

ROOT = Path(__file__).resolve().parents[1]
RID = "20261023T010250Z-screen-abc123"
CID = "campaign_20261023T024453Z"
F = [500.0, 1000.0, 2000.0, 4000.0, 5500.0]


def _design(run: Path, h: str, shift: float) -> None:
    d = run / "designs" / h
    d.mkdir(parents=True)
    n = len(F)
    m = {"freqs_hz": F, "bw_h_deg": [90 + shift] * n, "bw_v_deg": [60.0] * n, "di_db": [9.0] * n,
         "di_source": "balloon", "on_axis_db": [1.0, 2.0, 3.0, 2.0, float("nan")],
         "ripple_h_db": [0.5] * n, "ripple_v_db": [0.4] * n, "z_throat_real": [0.5] * n, "scalars": {}}
    (d / "metrics.json").write_text(json.dumps(m))
    ang = np.linspace(-90, 90, 5)
    np.savez(d / "response.npz", freqs_hz=np.array(F), h_angles_deg=ang, v_angles_deg=ang,
             spl_h_db=np.zeros((n, 5)) - np.abs(ang) / 10, spl_v_db=np.zeros((n, 5)))
    (d / "mesh.msh").write_text("$MeshFormat\n2.2 0 8\n$EndMeshFormat\n$Nodes\n3\n"
                                "1 0 0 0\n2 0.1 0 0.05\n3 0 0.08 0.05\n$EndNodes\n"
                                "$Elements\n1\n1 2 2 1 1 1 2 3\n$EndElements\n")
    (d / "design.json").write_text(json.dumps({"family": "FREEFORM", "params": {"a": 1}}))


def _row(n, h, ok, J_, knob):
    return {"n": n, "design_hash": h, "ok": ok, "objective": J_ if ok else 1000.0, "mode": "screen",
            "family": "FREEFORM", "error": None if ok else "invalid_geometry: x",
            "created_utc": f"2026-10-23T00:00:{n:02d}Z", "terms": {"cov": J_},
            "generator": {"knobs": {"L_mm": knob}}}


@pytest.fixture()
def repo(tmp_path):
    root = tmp_path / "repo"
    runs = root / "runs"
    run = runs / RID
    run.mkdir(parents=True)
    (run / "config.yaml").write_text(yaml.safe_dump({
        "name": "fake", "family": "FREEFORM", "bounds": {"L_mm": {"lo": 90.0, "hi": 140.0}},
        "target": {"coverage_h_deg": 90}, "weights": {"cov": 1.0}}))
    rows = [_row(0, "aaaaaaaaaaaa", True, 20.0, 100.0)] + \
           [_row(i, f"{i:012x}", True, 20.0 - i, 139.9) for i in range(1, 8)] + \
           [_row(8, "ffffffffffff", False, 0, 120.0)]
    (run / "search.ndjson").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    _design(run, "aaaaaaaaaaaa", 0.0)
    _design(run, f"{7:012x}", 2.0)
    camp = runs / CID
    camp.mkdir()
    (camp / "campaign.json").write_text(json.dumps({"tier": "compare", "brief_name": "b", "seeds": [1, 2],
        "entries": [{"name": "fam", "group": "g", "jobs": [
            {"seed": 1, "best_j": 10.0, "run_dir": str(run), "stats": {"evaluations": 5}},
            {"seed": 2, "best_j": 10.5, "run_dir": str(run), "stats": {"evaluations": 5}}]}]}))
    briefs = root / "examples" / "briefs"
    briefs.mkdir(parents=True)
    shutil.copy(ROOT / "examples" / "briefs" / "axi_90x90_1in.yaml", briefs)
    (root / "examples" / "cfg.yaml").write_text("name: x\n")
    return root


# ------------------------------------------------------------------ readers


def test_run_summary_and_detail(repo):
    runs = repo / "runs"
    [s] = D.list_runs(runs)
    assert s["id"] == RID and s["n"] == 9 and s["n_ok"] == 8
    assert s["best_j"] == 13.0 and s["best_hash"] == f"{7:012x}" and s["failures"] == {"invalid_geometry": 1}
    d = D.run_detail(runs, RID)
    assert d["J"][-1] is None and d["J"][0] == 20.0
    [sens] = d["sens"]
    assert sens["key"] == "L_mm" and sens["at_hi"] == 6        # top-6 designs all at 139.9 >= 140 - 2 %
    assert d["best"]["on_axis"][-1] is None                     # NaN -> None, never invented
    assert d["best"]["profile"]["h"] and len(d["best"]["polar_h"]) == len(F)
    json.dumps(d, allow_nan=False)


def test_ids_are_validated(repo):
    with pytest.raises(ValueError):
        D.run_detail(repo / "runs", "../../etc")
    with pytest.raises(ValueError):
        D.campaign_detail(repo / "runs", "campaign_x/../..")


def test_campaign_median_and_spread(repo):
    c = D.campaign_detail(repo / "runs", CID)
    [e] = c["entries"]
    assert e["median_j"] == pytest.approx(10.25) and e["spread"] == pytest.approx(0.5) and e["evals"] == 10
    assert e["best"]["hash"] == f"{7:012x}"


def test_mesh_surface(repo):
    m = D.mesh_surface(repo / "runs", RID, "aaaaaaaaaaaa")
    assert m["n_tris"] == 1 and m["tris"] == [0, 1, 2] and m["verts"][3] == 100.0


def test_tail_text_reads_utf16(tmp_path):
    p = tmp_path / "q.log"
    p.write_bytes("a\nb\nc\n".encode("utf-16"))
    assert D.tail_text(p, 2) == ["b", "c"]


def test_user_brief_saved_validated_and_shipped_protected(repo):
    shipped = yaml.safe_load((repo / "examples/briefs/axi_90x90_1in.yaml").read_text())
    p = D.save_user_brief(repo, "my_brief", shipped)
    assert p == repo / "examples/briefs/user/my_brief.yaml" and yaml.safe_load(p.read_text())["name"] == "my_brief"
    with pytest.raises(ValueError, match="shipped"):
        D.save_user_brief(repo, "axi_90x90_1in", shipped)
    with pytest.raises(ValueError):
        D.save_user_brief(repo, "../evil", shipped)
    bad = dict(shipped, envelope={"max_mouth_w_mm": -1})
    with pytest.raises(Exception):
        D.save_user_brief(repo, "bad_brief", bad)
    assert not (repo / "examples/briefs/user/bad_brief.yaml").exists()
    assert not list((repo / "examples/briefs/user").glob(".*.tmp"))


# ------------------------------------------------------------------ launcher


def test_argv_allow_list(repo):
    jm = J.JobManager(repo, repo / "runs")
    argv, gpu = jm.build_argv("campaign", {"brief": "examples/briefs/axi_90x90_1in.yaml",
                                           "families": "conical, exponential", "tier": "dry-run"})
    assert argv == ["campaign", "--brief", "examples/briefs/axi_90x90_1in.yaml", "--families",
                    "conical,exponential", "--tier", "dry-run"] and gpu is False
    assert jm.build_argv("search", {"config": "examples/cfg.yaml", "budget": 40})[1] is True
    for kind, a in [("search", {"config": "../outside.yaml"}),
                    ("search", {"config": "examples/cfg.yaml", "budget": 0}),
                    ("campaign", {"brief": "examples/briefs/axi_90x90_1in.yaml", "families": "a;rm -rf"}),
                    ("campaign", {"brief": "examples/briefs/axi_90x90_1in.yaml", "families": "a", "tier": "x"}),
                    ("export-step", {"run": "nope", "top": 1}),
                    ("shell", {})]:
        with pytest.raises(J.JobError):
            jm.build_argv(kind, a)


def test_gpu_job_refused_while_lock_held(repo):
    from hornlab_search.search.gpulock import _lock_path
    lk = _lock_path(repo / "runs")
    lk.parent.mkdir(parents=True, exist_ok=True)
    lk.write_text(json.dumps({"pid": os.getpid(), "user": "u", "command": "search x", "start_time": "t"}))
    jm = J.JobManager(repo, repo / "runs")
    with pytest.raises(J.JobError, match="GPU busy"):
        jm.launch("search", {"config": "examples/cfg.yaml", "budget": 5})
    assert not jm.jobs


def test_launch_log_and_cancel(repo, monkeypatch):
    monkeypatch.setattr(J, "CLI_BOOT", "import sys, time; print('hello', sys.argv[1:], flush=True); time.sleep(60)")
    jm = J.JobManager(repo, repo / "runs")
    job = jm.launch("dry-run", {"config": "examples/cfg.yaml"})
    for _ in range(100):
        if "hello" in "".join(D.tail_text(job.log)):
            break
        time.sleep(0.1)
    assert "hello" in "".join(D.tail_text(job.log)) and job.status == "running"
    jm.cancel(job.id)
    job.proc.wait(timeout=20)
    for _ in range(50):
        if job.ended:
            break
        time.sleep(0.1)
    assert job.status == "cancelled" and job.proc.poll() is not None


# ------------------------------------------------------------------ server


@pytest.fixture()
def server(repo):
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), make_handler(App(repo), port))
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{port}"
    httpd.shutdown()
    httpd.server_close()


def _req(url, data=None, ctype="application/json", host=None):
    r = urllib.request.Request(url, data=data, method="POST" if data is not None else "GET")
    if data is not None:
        r.add_header("Content-Type", ctype)
    if host:
        r.add_header("Host", host)
    try:
        with urllib.request.urlopen(r, timeout=20) as resp:
            return resp.status, json.loads(resp.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


def test_api_runs_and_errors(server):
    code, body = _req(server + "/api/runs")
    assert code == 200 and body[0]["id"] == RID
    assert _req(server + f"/api/run/{RID}")[0] == 200
    assert _req(server + "/api/run/bad-id")[0] == 400
    assert _req(server + "/api/nothing")[0] == 404


def test_server_rejects_foreign_host_and_non_json_posts(server):
    assert _req(server + "/api/runs", host="evil.example:80")[0] == 403
    assert _req(server + "/api/gpu-clean", data=b"x=1", ctype="application/x-www-form-urlencoded")[0] == 415


def test_static_path_traversal_is_404(server):
    assert _req(server + "/../../pyproject.toml")[0] in (400, 404)
    assert _req(server + "/runs/x/../../config.yaml")[0] == 404


def test_post_job_with_bad_args_returns_error(server):
    code, body = _req(server + "/api/jobs", data=json.dumps({"kind": "shell", "args": {}}).encode())
    assert code == 200 and "unknown job kind" in body["error"]
