"""W6 Balloon view: the /api/balloon endpoints (reader + routes). Offline, no GPU.

Covers the served contract: freqs, the theta-major [nTheta, nPhi] balloon_grid, the stored
layout string, n_dof, design label, run id + design hash, and per-frequency SPL normalised to
on-axis, Float32-rounded, and clipped into the [-30, 0] dB window (BL's Balloon Plot window).
Non-finite samples pass through clean() as null (never invented values). Strict paths: a bad
run id / design hash can never traverse; missing payloads are 404.
"""
from __future__ import annotations

import json
import shutil
import socket
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import numpy as np
import pytest
import yaml

from hornlab_search.gui import data as D
from hornlab_search.gui.server import App, make_handler

RID = "20261025T090000Z-screen-abc123"
N_T, N_P = 9, 13            # 9 theta rows (0..180 inclusive, poles at both ends), 13 phi columns
F = [500.0, 1000.0, 2000.0]
BEST = "bee000bad001"
BEST_J = 17.0
OTHER = "aabbccdd0000"


def _balloon() -> np.ndarray:
    """(F, N_T*N_P) dB, exactly one design's worth: flat index i*N_P + j (theta-major)."""
    g = np.zeros((len(F), N_T * N_P))
    g[0, :] = 2.0                                        # freq 0: uniform 2 dB (pole row = ref)
    for j in range(N_P):                                 # freq 1: -4 dB per theta row (i ramp)
        for i in range(N_T):
            g[1, i * N_P + j] = 2.0 - 4.0 * i
    g[1, 1 * N_P + 0] = -35.0                            # one interior sample below the floor
    g[1, 5 * N_P + 0] = np.nan                           # one non-finite sample
    g[2, :] = 0.0                                        # freq 2: uniform 0 dB
    return g


def _write_design(d: Path, balloon: bool) -> None:
    d.mkdir(parents=True)
    payload = dict(
        freqs_hz=np.array(F),
        h_angles_deg=np.linspace(-90, 90, 73),
        v_angles_deg=np.linspace(-90, 90, 73),
        spl_h_db=np.zeros((len(F), 73)),
        spl_v_db=np.zeros((len(F), 73)),
        z_throat=np.zeros(len(F), complex),
        n_dof=np.int64(1013),
        meta=json.dumps({"balloon_grid": [N_T, N_P],
                         "balloon_layout": "theta-major; theta 0..180 from +Z, phi 0..360; NOT equal-area",
                         "distance_m": 2.0}),
    )
    if balloon:
        payload["balloon_dirs"] = np.zeros((N_T * N_P, 3))
        payload["spl_balloon_db"] = _balloon()
    np.savez(d / "response.npz", **payload)
    (d / "design.json").write_text(json.dumps({}))


@pytest.fixture()
def repo(tmp_path):
    root = tmp_path / "repo"
    run = root / "runs" / RID
    run.mkdir(parents=True)
    (run / "config.yaml").write_text(yaml.safe_dump({"name": "fake", "family": "FREEFORM"}))
    rows = [{"n": 0, "design_hash": OTHER, "ok": True, "objective": 30.0, "mode": "screen",
             "family": "FREEFORM", "error": None, "quadrants": "1"},
            {"n": 1, "design_hash": BEST, "ok": True, "objective": BEST_J, "mode": "screen",
             "family": "FREEFORM", "error": None, "quadrants": "1"}]
    (run / "search.ndjson").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    _write_design(run / "designs" / BEST, balloon=True)
    _write_design(run / "designs" / OTHER, balloon=False)   # a pre-balloon (old-format) npz
    return root


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


def _get(url):
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            return resp.status, json.loads(resp.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


# --------------------------------------------------------------- reader


def test_balloon_reader_shape_and_window(repo):
    b = D.balloon(repo / "runs", RID, BEST)
    assert b["run_id"] == RID and b["design"] == BEST and b["n_dof"] == 1013
    assert b["balloon_grid"] == [N_T, N_P] and "theta-major" in b["layout"]
    assert b["distance_m"] == 2.0 and b["min_db"] == D.BALLOON_MIN_DB == -30.0
    assert len(b["freqs_hz"]) == len(F)
    rows = b["spl"]                                      # (F, N_T*N_P) clipped, rounded dB
    assert len(rows) == len(F) and all(len(r) == N_T * N_P for r in rows)
    for r in rows:
        assert all(-30.0 <= v <= 0.0 for v in r if v is not None)   # clipped into BL's window
    assert rows[0][0] == 0.0                             # on-axis pole row normalised to exactly 0
    assert rows[1][N_P] == -30.0                         # -35 dB sample clipped onto the floor (i=1)
    assert rows[1][2 * N_P + 3] == float(np.float32(-8.0))   # theta-major: i=2 row carries -8 dB
    assert rows[2][7 * N_P + 11] == float(np.float32(0.0))    # uniform-0 freq reads 0 everywhere
    json.dumps(b, allow_nan=False)                       # the payload is JSON-safe as served


def test_balloon_nonfinite_sample_passes_through_as_null(repo):
    b = D.balloon(repo / "runs", RID, BEST)
    assert b["spl"][1][5 * N_P + 0] is None              # NaN -> null (never a made-up number)


def test_balloon_designs_reader_ranks_best_first(repo):
    lst = D.balloon_designs(repo / "runs", RID)
    assert lst["run_id"] == RID and lst["name"] == "fake"
    assert [d["hash"] for d in lst["designs"]] == [BEST, OTHER]      # lowest objective first
    assert lst["designs"][0]["objective"] == BEST_J and lst["designs"][0]["has_balloon"] is True
    assert lst["designs"][1]["has_balloon"] is True      # existence probe: file is there, content differs


# --------------------------------------------------------------- routes


def test_balloon_endpoint_contract(server):
    code, body = _get(server + f"/api/balloon/{RID}/{BEST}")
    assert code == 200
    assert body["balloon_grid"] == [N_T, N_P] and body["design"] == BEST
    assert isinstance(body["n_dof"], int) and body["n_dof"] == 1013
    assert len(body["spl"]) == len(F) and len(body["spl"][0]) == N_T * N_P
    assert all(-30.0 <= v <= 0.0 for v in body["spl"][0])
    json.dumps(body, allow_nan=False)                    # NaN-safe JSON, always


def test_balloon_design_list_endpoint(server):
    code, body = _get(server + f"/api/balloon/{RID}")
    assert code == 200 and body["designs"][0]["hash"] == BEST
    assert all("has_balloon" in d for d in body["designs"])


def test_balloon_endpoint_missing_is_404_and_ids_are_strict(server):
    assert _get(server + f"/api/balloon/{RID}/ffffff000000")[0] == 404       # no such design
    assert _get(server + "/api/balloon/nope-run-id/x1234567890")[0] == 400   # not a run id
    assert _get(server + f"/api/balloon/{RID}/..%2F..%2Fconfig.yaml")[0] == 400   # not a hash
    assert _get(server + f"/api/balloon/{RID}")[0] == 200                # the list still answers


def test_balloon_on_an_old_format_npz_is_an_honest_error(server, repo):
    """A design whose response.npz predates balloons: a concrete client-visible error, never a
    crash and never fabricated data."""
    assert "spl_balloon_db" not in np.load(repo / "runs" / RID / "designs" / OTHER / "response.npz",
                                           allow_pickle=False).files
    shutil.rmtree(repo / "runs" / RID / "designs" / OTHER)
    code, body = _get(server + f"/api/balloon/{RID}/{OTHER}")
    assert code == 404                                   # the npz removed above: plain 404
    # an npz present but balloon-less: ValueError (400) naming the missing piece
    d = repo / "runs" / RID / "designs" / OTHER
    d.mkdir()
    np.savez(d / "response.npz", freqs_hz=np.array(F))
    (d / "design.json").write_text("{}")
    code, body = _get(server + f"/api/balloon/{RID}/{OTHER}")
    assert code == 400 and "balloon payload" in body["error"]


def test_balloon_reader_rejects_a_mismatched_grid(repo):
    d = repo / "runs" / RID / "designs" / BEST
    tmp = d / "response.tmp.npz"
    with np.load(d / "response.npz", allow_pickle=False) as z:
        body = {k: z[k] for k in z.files if k != "meta"}
    body["meta"] = json.dumps({})                        # the reader demands a matching grid
    np.savez(tmp, **body)
    shutil.move(str(tmp), str(d / "response.npz"))
    with pytest.raises(ValueError, match="balloon_grid"):
        D.balloon(repo / "runs", RID, BEST)