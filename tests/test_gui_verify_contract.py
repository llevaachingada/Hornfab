"""WP0 contract tests: fixture builder, frozen example JSON, and JS syntax.

These tests are offline and use only the synthetic run folders from
``tests/gui_verify_fixtures.py``.  No solver, no GPU.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
VERIFY_JS = ROOT / "hornlab_search" / "gui" / "static" / "verify.js"
APPJS = ROOT / "hornlab_search" / "gui" / "static" / "app.js"
EXAMPLE_JSON = ROOT / "tests" / "fixtures" / "gui" / "verify_report_example.json"

# ── Section 6 required top-level keys ──────────────────────────────────────────
REQUIRED_TOP_KEYS = {
    "run_id", "name", "kind", "redirect_to", "parent_missing",
    "objective_version", "band_hz", "sources", "state", "comparable",
    "comparable_reason", "latest_only", "fidelity", "summary",
    "gate_audit", "rows",
}

REQUIRED_FIDELITY_KEYS = {"n_freqs", "balloon_grid", "n_points", "dof_range"}

REQUIRED_SUMMARY_KEYS = {
    "n_verified", "n_failed", "n_pairs", "n_worse", "bias_median_pct",
    "spearman_all", "spearman_top5", "top5_overlap",
    "best_verify_hash", "best_verify_j", "screen1_hash", "screen1_verify_rank",
}

REQUIRED_ROW_KEYS = {
    "hash", "family", "screen_j", "verify_j", "delta_j", "delta_pct",
    "screen_rank", "verify_rank", "ok", "error", "n", "created_utc",
    "lane", "backend", "n_dof", "n_triangles",
    "density", "gates", "source_kind", "source_run_id",
    "has_balloon", "has_mesh",
}


# ── Fixture builder ────────────────────────────────────────────────────────────

def test_fixture_builder_creates_expected_dirs(tmp_path):
    """make_runs() creates all expected run folders without raising."""
    from tests.gui_verify_fixtures import make_runs, R_SCREEN, R_LINKED, R_ORPHAN
    from tests.gui_verify_fixtures import R_STANDALONE, R_XBAND

    ids = make_runs(tmp_path)

    runs = tmp_path / "runs"
    for rid in (R_SCREEN, R_LINKED, R_ORPHAN, R_STANDALONE, R_XBAND):
        assert (runs / rid).is_dir(), f"missing run dir: {rid}"
        assert (runs / rid / "search.ndjson").is_file(), f"missing ndjson: {rid}"

    assert ids["R_SCREEN"] == R_SCREEN
    assert ids["R_LINKED"] == R_LINKED


def test_fixture_screen_run_has_inline_verify(tmp_path):
    from tests.gui_verify_fixtures import make_runs, R_SCREEN

    make_runs(tmp_path)
    verify_ndjson = tmp_path / "runs" / R_SCREEN / "verify" / "search.ndjson"
    assert verify_ndjson.is_file()
    rows = [json.loads(ln) for ln in verify_ndjson.read_text().splitlines() if ln.strip()]
    assert len(rows) >= 4


def test_fixture_linked_run_has_verify_of(tmp_path):
    from tests.gui_verify_fixtures import make_runs, R_LINKED

    make_runs(tmp_path)
    rj = json.loads((tmp_path / "runs" / R_LINKED / "run.json").read_text())
    assert rj["mode"] == "verify"
    assert "verify_of" in rj
    assert "run" in rj["verify_of"]


def test_fixture_standalone_run_no_verify_of(tmp_path):
    from tests.gui_verify_fixtures import make_runs, R_STANDALONE

    make_runs(tmp_path)
    rj = json.loads((tmp_path / "runs" / R_STANDALONE / "run.json").read_text())
    assert rj["mode"] == "verify"
    assert "verify_of" not in rj


def test_fixture_gate_audit_csv_exists(tmp_path):
    from tests.gui_verify_fixtures import make_runs

    make_runs(tmp_path)
    csv_path = tmp_path / "docs" / "data" / "gate_audit_test" / "gate_audit.csv"
    assert csv_path.is_file()
    text = csv_path.read_text()
    assert "throat" in text
    assert "verify" in text


def test_fixture_response_npz_shape_screen(tmp_path):
    """Screen designs have 16×32 balloon grid = 512 points."""
    import numpy as np
    from tests.gui_verify_fixtures import make_runs, R_SCREEN, H

    make_runs(tmp_path)
    p = tmp_path / "runs" / R_SCREEN / "designs" / H["a1"] / "response.npz"
    assert p.is_file()
    with np.load(str(p), allow_pickle=False) as z:
        spl = z["spl_balloon_db"]
        freqs = z["freqs_hz"]
        meta = json.loads(str(z["meta"]))
    assert spl.shape[0] == 12
    assert spl.shape[1] == 16 * 32
    assert meta["balloon_grid"] == [16, 32]
    assert len(freqs) == 12


def test_fixture_response_npz_shape_verify(tmp_path):
    """Inline verify designs have 23×45 balloon grid = 1035 points."""
    import numpy as np
    from tests.gui_verify_fixtures import make_runs, R_SCREEN, H

    make_runs(tmp_path)
    p = tmp_path / "runs" / R_SCREEN / "verify" / "designs" / H["a1"] / "response.npz"
    assert p.is_file()
    with np.load(str(p), allow_pickle=False) as z:
        spl = z["spl_balloon_db"]
        freqs = z["freqs_hz"]
        meta = json.loads(str(z["meta"]))
    assert spl.shape[0] == 29
    assert spl.shape[1] == 23 * 45
    assert meta["balloon_grid"] == [23, 45]
    assert len(freqs) == 29


# ── Frozen example JSON ────────────────────────────────────────────────────────

def test_example_json_exists():
    assert EXAMPLE_JSON.is_file(), f"missing: {EXAMPLE_JSON}"


def test_example_json_valid():
    data = json.loads(EXAMPLE_JSON.read_text())
    assert isinstance(data, dict)


def test_example_json_top_level_keys():
    data = json.loads(EXAMPLE_JSON.read_text())
    missing = REQUIRED_TOP_KEYS - set(data.keys())
    assert not missing, f"missing top-level keys: {missing}"


def test_example_json_fidelity_keys():
    data = json.loads(EXAMPLE_JSON.read_text())
    for tier in ("verify", "screen"):
        assert tier in data["fidelity"], f"fidelity missing tier: {tier}"
        tier_data = data["fidelity"][tier]
        missing = REQUIRED_FIDELITY_KEYS - set(tier_data.keys())
        assert not missing, f"fidelity.{tier} missing keys: {missing}"


def test_example_json_summary_keys():
    data = json.loads(EXAMPLE_JSON.read_text())
    summary = data["summary"]
    missing = REQUIRED_SUMMARY_KEYS - set(summary.keys())
    assert not missing, f"summary missing keys: {missing}"


def test_example_json_rows_keys():
    data = json.loads(EXAMPLE_JSON.read_text())
    assert data["rows"], "rows must be non-empty"
    for i, row in enumerate(data["rows"]):
        missing = REQUIRED_ROW_KEYS - set(row.keys())
        assert not missing, f"row[{i}] missing keys: {missing}"


def test_example_json_no_nan():
    """The frozen JSON must be parseable with strict=True (no NaN/Inf)."""
    text = EXAMPLE_JSON.read_text()
    # json.loads will raise on NaN; also check for the string "NaN"
    assert "NaN" not in text and "Infinity" not in text
    json.loads(text)  # raises if malformed


def test_example_json_kind_values():
    data = json.loads(EXAMPLE_JSON.read_text())
    assert data["kind"] in ("pairs", "standalone", "redirect", "none")


# ── JS syntax checks ───────────────────────────────────────────────────────────

@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_node_check_verify_js():
    r = subprocess.run(["node", "--check", str(VERIFY_JS)],
                       capture_output=True, text=True)
    assert r.returncode == 0, f"node --check verify.js failed:\n{r.stderr}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_node_check_app_js():
    r = subprocess.run(["node", "--check", str(APPJS)],
                       capture_output=True, text=True)
    assert r.returncode == 0, f"node --check app.js failed:\n{r.stderr}"


# ── viewVerify export smoke ───────────────────────────────────────────────────

_VERIFY_EXPORT_SCRIPT = r'''
import { pathToFileURL } from "node:url";
import assert from "node:assert/strict";

const esc = s => String(s ?? "").replace(/[&<>"']/g, c =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const fakeEl = () => ({
  className: "", id: "", style: {}, dataset: {}, innerHTML: "", textContent: "",
  setAttribute() {}, getAttribute: () => null, replaceWith() {}, appendChild() {},
  addEventListener() {}, removeEventListener() {}, closest: () => null,
  classList: { toggle() {}, add() {}, remove() {} },
  querySelector: () => null, querySelectorAll: () => [],
});

globalThis.document = {
  getElementById: () => fakeEl(), createElement: () => fakeEl(),
  createElementNS: () => fakeEl(),
  querySelector: () => null, querySelectorAll: () => [], addEventListener() {},
  documentElement: { hasAttribute: () => true, setAttribute() {}, getAttribute: () => null, style: {} },
  body: { appendChild() {} },
};
globalThis.window = { innerWidth: 1280, addEventListener() {}, scrollTo() {} };
globalThis.matchMedia = () => ({ matches: true, addEventListener() {} });
globalThis.MutationObserver = class { observe() {} };
globalThis.location = { hash: "#/" };
globalThis.requestAnimationFrame = () => 0;
globalThis.localStorage = { getItem: () => null, setItem() {}, removeItem() {} };
globalThis.fetch = () => Promise.reject(new Error("offline shim"));

const mod = await import(pathToFileURL(process.argv[2]).href);
assert.ok(typeof mod.viewVerify === "function", "viewVerify must be exported");

// Calling viewVerify with a fake root should not throw synchronously.
const root = { innerHTML: "" };
// viewVerify is async; just verify it returns a Promise.
const p = mod.viewVerify(root, "20261112T120000Z-screen-aaa111", "table", "");
assert.ok(p instanceof Promise, "viewVerify must return a Promise");

console.log("VERIFY EXPORT OK");
'''


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_verify_js_exports_view_verify(tmp_path):
    script = tmp_path / "verify_export_test.mjs"
    script.write_text(_VERIFY_EXPORT_SCRIPT, encoding="utf-8")
    r = subprocess.run(["node", str(script), str(VERIFY_JS)],
                       capture_output=True, text=True, cwd=str(tmp_path))
    assert "VERIFY EXPORT OK" in r.stdout, (
        f"verify.js export test failed:\nstdout: {r.stdout}\nstderr: {r.stderr}"
    )
