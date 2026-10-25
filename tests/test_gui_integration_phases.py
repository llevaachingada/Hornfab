"""GUI integration phases G1-G4 (reader/route layer): the frozen contracts from
``docs/GUI_INTEGRATION_PLAN_2026-10-25.md`` §5, exercised offline (no browser, no GPU, no CLI jobs).

  C-1  ``GET /api/run/<id>`` additive ``restarts``/``qd``/``restart_dirs`` + ``step_files`` inventory.
  C-2  ``GET /api/compare`` additive ``group_a``/``group_b``/``mixed_keys`` (solve-group fingerprint).
  C-5  ``GET /runs/<id>/cma[/restart_k]/<name>`` raw pycma log serving by strict name allow-list.
  G-1  jobs ``verify`` kind (argv shape, bounds, GPU lock inheritance).

Fixture conventions mirror ``tests/test_gui.py``: synthetic run dirs under ``tmp_path`` and a real
``ThreadingHTTPServer`` bound to 127.0.0.1:0; the app.js ES-module ``node --check`` gate is copied so
the view lane's syntax stays gated.
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest
import yaml

from hornlab_search.gui import data as D
from hornlab_search.gui import jobs as J
from hornlab_search.gui.server import App, make_handler

ROOT = Path(__file__).resolve().parents[1]

RUN_A = "20261025T000000Z-screen-aaa111"       # restarts/qd/restart dirs/STEP sidecar
RUN_B = "20261025T000001Z-screen-bbb222"       # plain run (no WP11 keys, no sidecar)
RUN_C = "20261025T000002Z-screen-ccc333"       # identical to B except mesh.rear_res_factor
RUN_D = "20261025T000003Z-screen-ddd444"       # identical to B (empty mixed_keys)

HASH = "aaaaaaaaaaaa"
STEP = "fake_rank1_aaaaaaaaaaaa.step"
F = [500.0, 1000.0, 2000.0, 4000.0, 5500.0]

RESTARTS = [{"index": 0, "popsize": 8, "sigma0": 0.25, "n_new_in_restart": 5,
             "evals_in_restart": 5, "stop": "small_run"}]
QD = {"algorithm": "cma_me", "descriptors": {"h": "mean_bw_h_deg", "v": "mean_bw_v_deg"},
      "bins": [4, 3], "coverage": {"occupied": 1, "total": 12}}
INVENTORY = {"tool": "tools/cad/multicell.py", "tool_sha": "deadbeef",
             "faces": [{"label": "driver", "count": 1}, {"label": "wall", "count": 4}],
             "solids": 1, "closed": True, "grid": ["3x3"]}


def _cfg(mesh_extra: dict | None = None, solve_extra: dict | None = None,
         search_extra: dict | None = None) -> dict:
    cfg = {
        "name": "fake", "family": "FREEFORM",
        "mesh": {"epw": 8.0, "quadrants": "1", "dof_cap_screen": 5000, "dof_cap_verify": 7000,
                 "dof_cap_final": 8900, "dof_per_triangle": 0.51, "max_triangle_slack": 1.15},
        "solve": {"backend": "beat_cuda", "distance_m": 2.0, "angle_count": 73, "balloon": True,
                  "balloon_points_screen": 512, "balloon_points_verify": 1024,
                  "gmres_tol": 1e-5, "timeout_s": 900},
        "search": {"algorithm": "cma", "sigma0": 0.25, "seed": 1234, "budget": 60,
                   "popsize": None, "tolfun": 1e-3},
        "target": {"band_lo_hz": 300, "band_hi_hz": 12000, "coverage_h_deg": 90,
                   "coverage_v_deg": 60, "di_target_db": None, "di_slope_target": 0, "z_min": 0},
        "weights": {"cov": 1.0},
    }
    cfg["mesh"].update(mesh_extra or {})
    cfg["solve"].update(solve_extra or {})
    cfg["search"].update(search_extra or {})
    return cfg


def _metrics(shift: float = 0.0) -> dict:
    n = len(F)
    return {"freqs_hz": F, "bw_h_deg": [90.0 + shift] * n, "bw_v_deg": [60.0] * n,
            "di_db": [9.0] * n, "di_source": "balloon",
            "on_axis_db": [1.0, 2.0, 3.0, 2.0, 1.5], "ripple_h_db": [0.5] * n,
            "ripple_v_db": [0.4] * n, "z_throat_real": [0.5] * n, "scalars": {}}


def _write_run(runs: Path, rid: str, *, mesh_extra: dict | None = None,
               solve_extra: dict | None = None, search_extra: dict | None = None,
               run_json_extra: dict | None = None, restart_dirs: tuple[str, ...] = (),
               inventory: dict | None = None, with_step: bool = True) -> Path:
    run = runs / rid
    run.mkdir(parents=True)
    (run / "config.yaml").write_text(
        yaml.safe_dump(_cfg(mesh_extra, solve_extra, search_extra)))
    design = run / "designs" / HASH
    design.mkdir(parents=True)
    (design / "metrics.json").write_text(json.dumps(_metrics()))
    row = {"n": 0, "design_hash": HASH, "ok": True, "objective": 9.0, "mode": "screen",
           "family": "FREEFORM", "error": None, "metrics": _metrics()}
    (run / "search.ndjson").write_text(json.dumps(row) + "\n")
    run_json = {"backend": "beat_cuda", "mode": "screen"}
    run_json.update(run_json_extra or {})
    (run / "run.json").write_text(json.dumps(run_json))
    for name in restart_dirs:
        (run / "cma" / name).mkdir(parents=True)
        (run / "cma" / name / "fit.dat").write_text("1 2 3\n")
    if with_step:
        step = run / "step"
        step.mkdir()
        (step / STEP).write_text("ISO-10303-21;")
        if inventory is not None:
            (step / (Path(STEP).stem + ".inventory.json")).write_text(json.dumps(inventory))
    return run


@pytest.fixture()
def repo(tmp_path):
    root = tmp_path / "repo"
    runs = root / "runs"
    _write_run(runs, RUN_A, run_json_extra={"restarts": RESTARTS, "qd": QD},
               restart_dirs=("restart_0",), inventory=INVENTORY,
               mesh_extra={"rear_res_factor": 2.0},
               solve_extra={"cuda_fused": True, "near_correction": True,
                            "near_correction_cutoff": 500.0, "near_correction_order": 6,
                            "solve_precision": "double"},
               search_extra={"restarts": {"mode": "ipop", "max": 3}})
    _write_run(runs, RUN_B)
    _write_run(runs, RUN_C, mesh_extra={"rear_res_factor": 2.0})
    _write_run(runs, RUN_D)
    examples = root / "examples"
    (examples / "briefs").mkdir(parents=True)
    shutil.copy(ROOT / "examples" / "briefs" / "axi_90x90_1in.yaml", examples / "briefs")
    (examples / "cfg.yaml").write_text("name: x\n")
    return root


# ------------------------------------------------------------------ C-1 run_detail


def test_run_detail_carries_wp11_provenance_and_step_inventory(repo):
    d = D.run_detail(repo / "runs", RUN_A)
    assert d["restarts"] == RESTARTS                       # the array as written, verbatim
    assert d["qd"] == QD
    assert d["restart_dirs"] == ["cma/restart_0"]          # run-relative directory names, sorted
    assert d["step_files"] == [STEP]                       # legacy name list stays byte-identical
    [step] = d["step_files_detail"]
    assert step["name"] == STEP and step["inventory"] == INVENTORY
    # WP11a schedule read from config.yaml (the run.json restart rows stay a separate key).
    assert d["search_restarts"] == {"mode": "ipop", "max": 3}
    # G1 badge strip: the compare fingerprint is on every run detail; this run's non-defaults show.
    g = d["solve_group"]
    assert g["backend"] == "beat_cuda" and "freqs_hz" in g
    assert g["rear_res_factor"] == 2.0 and g["cuda_fused"] is True
    assert g["near_correction"] is True and g["near_correction_cutoff"] == 500.0
    assert g["near_correction_order"] == 6 and g["solve_precision"] == "double"
    json.dumps(d, allow_nan=False)                         # honesty: JSON-safe end to end


def test_run_detail_omits_absent_provenance_and_null_inventory(repo):
    d = D.run_detail(repo / "runs", RUN_B)
    assert "restarts" not in d and "qd" not in d           # absent in run.json -> absent here
    assert d["restart_dirs"] == []                         # no cma/restart_* dirs
    assert d["step_files"] == [STEP]
    [step] = d["step_files_detail"]
    assert step["name"] == STEP and step["inventory"] is None   # no sidecar -> null, never invented
    assert "search_restarts" not in d                      # no search.restarts block -> absent
    # solve_group is always present, but carries no non-default keys for this plain run.
    assert set(d["solve_group"]) == {"backend", "freqs_hz"}
    assert d["solve_group"]["backend"] == "beat_cuda"
    json.dumps(d, allow_nan=False)


def test_run_detail_never_fabricates_a_malformed_search_restarts_block(repo):
    run = repo / "runs" / RUN_B
    cfg = yaml.safe_load((run / "config.yaml").read_text())
    cfg["search"]["restarts"] = {"mode": "ipop"}           # missing `max`: invalid -> absent
    (run / "config.yaml").write_text(yaml.safe_dump(cfg))
    assert "search_restarts" not in D.run_detail(repo / "runs", RUN_B)


def test_run_detail_route_serves_the_additive_keys(server):
    code, body = _req(server + f"/api/run/{RUN_A}")
    assert code == 200 and body["restarts"] == RESTARTS and body["qd"] == QD
    assert body["restart_dirs"] == ["cma/restart_0"]
    assert body["step_files_detail"][0]["inventory"] == INVENTORY
    assert body["search_restarts"] == {"mode": "ipop", "max": 3}
    assert body["solve_group"]["rear_res_factor"] == 2.0 and body["solve_group"]["backend"] == "beat_cuda"
    code, body = _req(server + f"/api/run/{RUN_B}")
    assert "restarts" not in body and "qd" not in body and body["restart_dirs"] == []
    assert body["step_files_detail"][0]["inventory"] is None
    assert "search_restarts" not in body and body["solve_group"]["backend"] == "beat_cuda"


# ------------------------------------------------------------------ C-5 raw pycma logs


def _get_raw(url):
    with urllib.request.urlopen(url, timeout=20) as resp:
        return resp.status, resp.read(), dict(resp.headers)


def test_cma_log_route_serves_pycma_logs_by_strict_name(server, repo):
    run = repo / "runs" / RUN_A
    (run / "cma").mkdir(exist_ok=True)
    (run / "cma" / "version.txt").write_bytes(b"3.3.0\n")
    (run / "cma" / "x0.q").write_text("q\n")
    (run / "cma" / "restart_0").mkdir(exist_ok=True)
    (run / "cma" / "restart_0" / "parameters.json2").write_text('{"a": 1}')

    status, body, headers = _get_raw(server + f"/runs/{RUN_A}/cma/restart_0/parameters.json2")
    assert status == 200 and body == b'{"a": 1}'
    assert headers["Content-Type"].startswith("text/plain") and headers["Cache-Control"] == "no-store"
    assert "attachment" in headers["Content-Disposition"]
    assert _get_raw(server + f"/runs/{RUN_A}/cma/version.txt")[:2] == (200, b"3.3.0\n")
    assert _get_raw(server + f"/runs/{RUN_A}/cma/x0.q")[0] == 200     # .q is in the whitelist


def test_cma_log_route_refuses_missing_executables_and_traversal(server, repo):
    run = repo / "runs" / RUN_A
    (run / "cma").mkdir(exist_ok=True)
    (run / "cma" / "evil.exe").write_bytes(b"MZ")
    (run / "cma" / "evil.py").write_text("print(1)")
    assert _req(server + f"/runs/{RUN_A}/cma/nope.dat")[0] == 404
    assert _req(server + f"/runs/{RUN_A}/cma/evil.exe")[0] == 404  # exists, but not whitelisted
    assert _req(server + f"/runs/{RUN_A}/cma/evil.py")[0] == 404
    assert _req(server + f"/runs/{RUN_A}/cma/..%2F..%2Fconfig.yaml")[0] in (400, 404)
    assert _req(server + f"/runs/{RUN_A}/cma/restart_0/..%2F..%2Frun.json")[0] in (400, 404)


# ------------------------------------------------------------------ C-2 solve-group fingerprint


def test_compare_groups_flag_exactly_the_differing_mesh_key(server, repo):
    runs = repo / "runs"
    ga, gb, mixed = D.solve_group_fingerprints(runs / RUN_B, runs / RUN_C)
    assert mixed == ["rear_res_factor"]
    assert ga["backend"] == gb["backend"] == "beat_cuda"        # identity key, always present
    assert "rear_res_factor" not in ga and gb["rear_res_factor"] == 2.0
    # every other key is identical (backend + the solved-grid identity are the identity keys)
    assert set(ga) - {"backend", "freqs_hz"} == set()
    assert set(gb) - {"backend", "freqs_hz"} == {"rear_res_factor"}

    code, body = _req(server + f"/api/compare?a={RUN_B}&b={RUN_C}")
    assert code == 200
    assert body["mixed_keys"] == ["rear_res_factor"]
    assert body["group_a"] == ga and body["group_b"] == gb
    assert "rows" in body and "a" in body and "b" in body       # existing response keys intact


def test_compare_groups_are_empty_when_the_configs_match(server, repo):
    runs = repo / "runs"
    assert D.solve_group_fingerprints(runs / RUN_B, runs / RUN_D)[2] == []
    code, body = _req(server + f"/api/compare?a={RUN_B}&b={RUN_D}")
    assert code == 200 and body["mixed_keys"] == []
    assert body["group_a"] == body["group_b"]
    assert body["group_a"]["backend"] == "beat_cuda"


def test_solve_group_fingerprint_reads_the_wip_solve_mesh_and_objective_keys(repo):
    run = repo / "runs" / RUN_B
    cfg = yaml.safe_load((run / "config.yaml").read_text())
    cfg["mesh"]["rear_res_factor"] = 1.5
    cfg["mesh"]["band_split"] = {"edges_hz": [2000.0, 4000.0]}
    cfg["solve"].update({"near_correction": True, "near_correction_cutoff": 500.0,
                         "near_correction_order": 6, "solve_precision": "double"})
    cfg["objective"] = {"version": 2}
    (run / "config.yaml").write_text(yaml.safe_dump(cfg))

    g = D._solve_group_fingerprint(run)
    assert g["backend"] == "beat_cuda"
    assert g["rear_res_factor"] == 1.5
    assert g["mesh_policy"] == "band_split_v1" and g["band_edges_hz"] == [2000.0, 4000.0]
    assert g["near_correction"] is True and g["near_correction_cutoff"] == 500.0
    assert g["near_correction_order"] == 6 and g["solve_precision"] == "double"
    assert g["objective_version"] == 2
    assert "cuda_fused" not in g and "source_motion" not in g   # defaults stay absent
    json.dumps(g, allow_nan=False)


# ------------------------------------------------------------------ G-1 verify job kind


def test_verify_kind_argv_bounds_and_brief(repo):
    jm = J.JobManager(repo, repo / "runs")
    assert "verify" in J.GPU_KINDS
    argv, gpu = jm.build_argv("verify", {"run": RUN_B, "top": 12})
    assert gpu is True
    assert argv == ["verify", "--run", str((repo / "runs").resolve() / RUN_B), "--top", "12"]
    argv, gpu = jm.build_argv("verify", {"run": RUN_B, "top": 5,
                                         "brief": "examples/briefs/axi_90x90_1in.yaml"})
    assert gpu is True and argv[-2:] == ["--brief", "examples/briefs/axi_90x90_1in.yaml"]
    assert argv[:4] == ["verify", "--run", str((repo / "runs").resolve() / RUN_B), "--top"]
    for bad in ({"run": RUN_B, "top": 0}, {"run": RUN_B, "top": 26}, {"run": RUN_B, "top": "x"},
                {"run": "not-a-run", "top": 3},
                {"run": RUN_B, "top": 3, "brief": "../outside.yaml"},
                {"run": RUN_B, "top": 3, "brief": "examples/nope.yaml"}):
        with pytest.raises(J.JobError):
            jm.build_argv("verify", bad)


def test_verify_preview_marks_it_gpu(server):
    code, body = _req(server + "/api/preview", data=json.dumps(
        {"kind": "verify", "args": {"run": RUN_B, "top": 5}}).encode())
    assert code == 200 and body["gpu"] is True and body["gpu_busy"] is None
    assert body["command"].startswith("hornlab-search verify --run ")


def test_verify_is_refused_while_the_gpu_lock_is_held(repo):
    from hornlab_search.search.gpulock import _lock_path
    lk = _lock_path(repo / "runs")
    lk.parent.mkdir(parents=True, exist_ok=True)
    lk.write_text(json.dumps({"pid": os.getpid(), "user": "u", "command": "search x",
                              "start_time": "t"}))
    jm = J.JobManager(repo, repo / "runs")
    with pytest.raises(J.JobError, match="GPU busy"):
        jm.launch("verify", {"run": RUN_B, "top": 3})
    assert not jm.jobs


# ------------------------------------------------------------------ server fixture


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


# ------------------------------------------------------------------ view syntax gate


def test_static_app_js_parses_as_an_es_module(tmp_path):
    """A syntax error in app.js blanks every view; catch it offline (same gate as tests/test_gui.py)."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not installed")
    src = ROOT / "hornlab_search" / "gui" / "static" / "app.js"
    mjs = tmp_path / "app.mjs"
    mjs.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    r = subprocess.run([node, "--check", str(mjs)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
