"""Owner favorites registry (docs/favorites/FAVORITES.yaml) behind the GUI star toggle.

Rules under test (docs/favorites/README.md): append-only, one entry per design hash, never delete
(un-star = ``status: retired`` + ``retired_note``), J read from best.json. Offline; the node
checks skip without node.
"""
from __future__ import annotations

import json
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

from hornlab_search.gui import favorites as FAV
from hornlab_search.gui.server import App, make_handler

ROOT = Path(__file__).resolve().parents[1]
APPJS = ROOT / "hornlab_search" / "gui" / "static" / "app.js"
FAV_RID = "20261120T084006Z-screen-fc4e18"
NEW_RID = "20261120T165805Z-screen-01eebe"

#: The real registry's shape: comment header, flow mappings, a folded owner_note.
REGISTRY = """\
# HornFab favorites registry: horns the OWNER has starred.
# Rules: append-only (retire with status: retired, never delete).
schema: hornlab-favorites-v1
favorites:
- id: FAV-001
  added: '2026-11-20'
  added_by: owner
  title: Crowe-X on OS-SE CD (v11 completion best)
  owner_note: >-
    "Some of the best directivity plots and esthetics of anything I've seen so far." Flares
    immediately at the throat.
  design_hash: 4140768780f0
  objective: v11 (CD identity; never rank against v7/v9/v10)
  runs:
    screen: {run_dir: runs/20261120T084006Z-screen-fc4e18, eval_no: 44, J: 4.996463749003073}
    verify: {run_dir: runs/20261120T185832Z-verify-e5de4a, J: 4.993881286003633, dofs: 4487}
  knobs: {g_L_mm: 260.313, g_n: 2.5627}
  status: active
"""


def _run(runs: Path, rid: str, h: str, J: float) -> None:
    d = runs / rid
    d.mkdir(parents=True)
    cfg_path = "examples/typologies/fav_test/fav__probe.yaml"
    (d / "config.yaml").write_text(yaml.safe_dump({
        "name": "fav__probe", "family": "FREEFORM",
        "brief_file": "../../briefs/fav_test/probe_brief.yaml",
        "generator": {"name": "grid", "rows": {"type": "osse_rollback"}},
        "objective": {"version": 11}}))
    (d / "run.json").write_text(json.dumps({"config_path": cfg_path, "objective_version": 11,
                                            "mode": "screen"}))
    (d / "best.json").write_text(json.dumps({
        "design_hash": h, "eval_no": 12, "objective": J, "family": "FREEFORM", "mode": "screen",
        "params": {"grid": {"knobs": {"g_L_mm": 230.123456789, "g_sf_m": 4.0}}}, "terms": {"total": J}}))
    (d / "search.ndjson").write_text(json.dumps({"n": 0, "design_hash": h, "ok": True, "objective": J}) + "\n")


@pytest.fixture()
def repo(tmp_path):
    root = tmp_path / "repo"
    runs = root / "runs"
    _run(runs, FAV_RID, "4140768780f0", 4.996463749003073)
    _run(runs, NEW_RID, "0123456789ab", 6.25)
    p = root / "docs" / "favorites" / "FAVORITES.yaml"
    p.parent.mkdir(parents=True)
    p.write_text(REGISTRY, encoding="utf-8", newline="\n")
    return root


def _text(root: Path) -> str:
    return FAV.favorites_path(root).read_text(encoding="utf-8")


def test_load_indexes_active_entries_by_run_and_hash(repo):
    f = FAV.load_favorites(repo)
    assert f["available"] and f["schema"] == "hornlab-favorites-v1"
    assert f["by_run"] == {FAV_RID: ["FAV-001"], "20261120T185832Z-verify-e5de4a": ["FAV-001"]}
    assert f["by_hash"] == {"4140768780f0": "FAV-001"}


def test_star_appends_an_entry_built_from_the_run(repo):
    before = _text(repo)
    r = FAV.star_run(repo, repo / "runs", NEW_RID, 'Lovely polars: "flat" H & V')
    assert r["ok"] and r["id"] == "FAV-002"
    after = _text(repo)
    assert after.startswith(before)                      # append-only: old bytes untouched
    doc = yaml.safe_load(after)
    assert [f["id"] for f in doc["favorites"]] == ["FAV-001", "FAV-002"]
    e = doc["favorites"][1]
    assert e["design_hash"] == "0123456789ab" and e["status"] == "active"
    assert e["owner_note"] == 'Lovely polars: "flat" H & V'
    assert e["runs"] == {"screen": {"run_dir": f"runs/{NEW_RID}", "eval_no": 12, "J": 6.25}}
    assert e["config"] == "examples/typologies/fav_test/fav__probe.yaml"
    assert e["brief"] == "examples/briefs/fav_test/probe_brief.yaml"   # resolved against the config
    assert e["objective"] == "v11" and e["family"] == "FREEFORM"
    assert e["generator"] == "grid / rows.type osse_rollback"
    assert e["knobs"] == {"g_L_mm": 230.123457, "g_sf_m": 4.0}
    assert FAV.load_favorites(repo)["by_run"][NEW_RID] == ["FAV-002"]


def test_star_refuses_duplicates_and_empty_notes(repo):
    with pytest.raises(ValueError, match="already favorite FAV-001"):
        FAV.star_run(repo, repo / "runs", FAV_RID, "again")
    with pytest.raises(ValueError, match="owner_note"):
        FAV.star_run(repo, repo / "runs", NEW_RID, "   ")
    assert _text(repo) == REGISTRY


def test_retire_changes_only_the_status_and_restar_reactivates(repo):
    FAV.star_run(repo, repo / "runs", NEW_RID, "probe")
    before = yaml.safe_load(_text(repo))["favorites"]
    r = FAV.retire_favorite(repo, "FAV-001", "changed my mind")
    assert r == {"ok": True, "action": "retired", "id": "FAV-001"}
    after = yaml.safe_load(_text(repo))["favorites"]
    assert len(after) == 2 and after[1] == before[1]     # never deleted, other entry untouched
    assert after[0]["status"] == "retired" and after[0]["retired_note"] == "changed my mind"
    assert {k: v for k, v in after[0].items() if k not in ("status", "retired", "retired_note")} == \
        {k: v for k, v in before[0].items() if k != "status"}
    f = FAV.load_favorites(repo)
    assert FAV_RID not in f["by_run"] and "4140768780f0" not in f["by_hash"]
    with pytest.raises(ValueError, match="already retired"):
        FAV.retire_favorite(repo, "FAV-001", "x")
    # starring the same design again re-activates FAV-001 instead of adding a duplicate entry
    r = FAV.star_run(repo, repo / "runs", FAV_RID, "back on the list")
    assert r["action"] == "reactivated" and r["id"] == "FAV-001"
    again = yaml.safe_load(_text(repo))["favorites"]
    assert len(again) == 2 and again[0]["status"] == "active"
    assert again[0]["reactivated_note"] == "back on the list"


def test_missing_registry_is_created_with_the_schema_header(tmp_path):
    root = tmp_path / "repo"
    _run(root / "runs", NEW_RID, "0123456789ab", 6.25)
    assert FAV.load_favorites(root)["available"] is False
    FAV.star_run(root, root / "runs", NEW_RID, "first star")
    doc = yaml.safe_load(_text(root))
    assert doc["schema"] == "hornlab-favorites-v1" and doc["favorites"][0]["id"] == "FAV-001"


def test_broken_registry_is_reported_and_never_overwritten(repo):
    p = FAV.favorites_path(repo)
    p.write_text("schema: something-else\nfavorites: []\n", encoding="utf-8")
    f = FAV.load_favorites(repo)
    assert "schema" in f["error"] and f["favorites"] == []
    with pytest.raises(ValueError):
        FAV.star_run(repo, repo / "runs", NEW_RID, "x")
    assert p.read_text(encoding="utf-8") == "schema: something-else\nfavorites: []\n"


def test_registry_whose_list_is_not_last_refuses_append(repo):
    p = FAV.favorites_path(repo)
    p.write_text(REGISTRY + "notes: trailing key\n", encoding="utf-8")
    with pytest.raises(ValueError, match="append check failed"):
        FAV.star_run(repo, repo / "runs", NEW_RID, "x")
    assert p.read_text(encoding="utf-8") == REGISTRY + "notes: trailing key\n"


# ------------------------------------------------------------------ HTTP


@pytest.fixture()
def server(repo):
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), make_handler(App(repo), port))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{port}"
    httpd.shutdown()
    httpd.server_close()


def _req(url, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method="POST" if data is not None else "GET")
    if data is not None:
        r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, timeout=20) as resp:
            return resp.status, json.loads(resp.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


def test_api_favorites_get_star_retire(server, repo):
    code, body = _req(server + "/api/favorites")
    assert code == 200 and body["by_hash"] == {"4140768780f0": "FAV-001"}
    code, body = _req(server + "/api/favorites", {"action": "star", "run_id": NEW_RID, "owner_note": "nice"})
    assert code == 200 and body["id"] == "FAV-002"
    code, body = _req(server + "/api/favorites", {"action": "star", "run_id": NEW_RID, "owner_note": "nice"})
    assert code == 400 and "already favorite" in body["error"]
    code, body = _req(server + "/api/favorites", {"action": "retire", "id": "FAV-002", "note": "meh"})
    assert code == 200 and body["action"] == "retired"
    assert _req(server + "/api/favorites", {"action": "delete", "id": "FAV-001"})[0] == 400
    assert _req(server + "/api/favorites", {"action": "star", "run_id": "../x", "owner_note": "n"})[0] == 400
    assert len(yaml.safe_load(_text(repo))["favorites"]) == 2


# ------------------------------------------------------------------ client helpers (node)

_NODE = r'''
import { pathToFileURL } from "node:url";
import assert from "node:assert/strict";
const fake = () => ({ className: "", id: "", style: {}, dataset: {}, innerHTML: "", textContent: "",
  setAttribute() {}, getAttribute: () => null, replaceWith() {}, appendChild() {},
  addEventListener() {}, removeEventListener() {}, closest: () => null,
  classList: { toggle() {}, add() {}, remove() {} }, querySelector: () => null, querySelectorAll: () => [] });
globalThis.document = {
  getElementById: () => fake(), createElement: () => fake(), createElementNS: () => fake(),
  querySelector: () => null, querySelectorAll: () => [], addEventListener() {},
  documentElement: { hasAttribute: () => true, setAttribute() {}, getAttribute: () => null, style: {} },
  body: { appendChild() {} },
};
globalThis.window = { innerWidth: 1280, addEventListener() {}, scrollTo() {} };
globalThis.matchMedia = () => ({ matches: true, addEventListener() {} });
globalThis.MutationObserver = class { observe() {} };
globalThis.location = { hash: "#/runs" };
globalThis.requestAnimationFrame = () => 0;
globalThis.localStorage = { getItem: () => null, setItem() {}, removeItem() {} };
globalThis.fetch = () => Promise.reject(new Error("offline shim"));
const app = await import(pathToFileURL(process.argv[2]).href);
const favs = JSON.parse(process.argv[3]);

// run lookup: by run id, by best hash (e.g. a later verify run of the same design), else null
assert.equal(app.favoriteForRun(favs, "20261120T084006Z-screen-fc4e18", "zzz").id, "FAV-001");
assert.equal(app.favoriteForRun(favs, "other-run", "4140768780f0").id, "FAV-001");
assert.equal(app.favoriteForRun(favs, "other-run", "nope"), null);
assert.equal(app.favoriteForRun(null, "x", "y"), null);
assert.match(app.favoriteMarkHtml({ id: "FAV-001", title: "Crowe-X" }), /class="fav-mark"[^>]*FAV-001/);
assert.equal(app.favoriteMarkHtml(null), "");

// elites: hash match (shortened card hashes too), marker on the card, favorites-only filter
assert.equal(app.eliteFavorite({ hash: "41407687" }, favs).id, "FAV-001");
assert.equal(app.eliteFavorite({ hash: "aaaaaaaa" }, favs), null);
const data = { available: true, labels: {}, cards: [
  { hash: "41407687", run: "r1", brief: "b", family: "FREEFORM", J: 5.0, pass_all: true },
  { hash: "aaaaaaaa", run: "r2", brief: "b", family: "OSSE", J: 1.0, pass_all: true } ] };
const all = app.renderElitesHtml(data, { favs, mode: "all" });
assert.match(all, /id="elites-fav"[^>]*aria-pressed="false"/);
assert.match(all, /Favorites \(1\)/);
assert.equal((all.match(/class="fav-mark" title/g) || []).length, 1);
const only = app.renderElitesHtml(data, { favs, mode: "all", favOnly: true });
assert.ok(only.includes("41407687") && !only.includes("aaaaaaaa"), "favorites-only hides the rest");
assert.match(only, /id="elites-fav"[^>]*aria-pressed="true"/);
console.log("FAVORITES JS OK");
'''


def test_favorite_helpers_js(repo, tmp_path):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not installed")
    script = tmp_path / "favorites_under_test.mjs"
    script.write_text(_NODE, encoding="utf-8")
    r = subprocess.run([node, str(script), str(APPJS), json.dumps(FAV.load_favorites(repo))],
                       capture_output=True, text=True, encoding="utf-8", cwd=str(tmp_path))
    assert "FAVORITES JS OK" in r.stdout, f"stdout: {r.stdout}\nstderr: {r.stderr}"
