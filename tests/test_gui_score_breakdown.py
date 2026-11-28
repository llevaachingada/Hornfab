"""Run page "Score breakdown: start vs best" lists every weighted term of the run's objective
version and sums to the stored J (2026-11-20 FAV-001: the v11 CD terms were missing).

The v11 fixture is the FAV-001 screen run's own numbers (runs/20261120T084006Z-screen-fc4e18:
config weights/objective block and best.json/seed terms, copied verbatim), so the test pins the
real case without needing the gitignored runs/ folder. Offline; node tests skip without node.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from hornlab_search.gui import data as D
from hornlab_search.gui.data_breakdown import score_breakdown

ROOT = Path(__file__).resolve().parents[1]
APPJS = ROOT / "hornlab_search" / "gui" / "static" / "app.js"
RID = "20261120T084006Z-screen-fc4e18"

V11_WEIGHTS = {"cov_profile": 1.0, "di_roughness": 0.5, "dislope": 0.5, "flat": 0.5, "flat_cv": 0.5,
               "load": 1.0, "rip": 0.5}
V11_OBJECTIVE = {
    "cov_below_f0": "one_sided", "cov_narrow_ratio": 2.0, "cov_v_weight": 0.5,
    "flat_band": "scored", "lfp_crossover_ratio": 1.6, "lfp_re_z": 0.2, "loaded_re_z": 0.5,
    "tolerances": {"cov_profile": 3.0, "di_roughness": 1.0, "dislope": 9.0, "flat": 1.5,
                   "flat_cv": 1.5, "load": 0.3, "rip": 1.0},
    "version": 11, "ripple_region": "preferred_edge",
    "cd": {"band_hz": [700.0, 8000.0], "window_h_deg": 30.0, "window_v_deg": 10.0,
           "lw": {"weight": 1.5, "tolerance_db": 1.5},
           "di_std": {"weight": 0.75, "tolerance_db": 1.0},
           "nacc": {"weight": 0.75, "tolerance": 0.02},
           "offaxis": {"weight": 1.0, "tolerance_db": 1.0, "reference": "band_mean",
                       "band_hz": [2500.0, 8000.0], "angles_h_deg": [-40, -30, 30, 40],
                       "angles_v_deg": [-25, -10, 10, 25]},
           "report": {"omega": True, "contour": False}},
}
#: best.json "terms" of FAV-001 (eval 44), verbatim.
BEST_TERMS = {
    "cd_di_std": 0.4253050294642921, "cd_lw": 0.23063677466770635, "cd_nacc": 0.20335074636844142,
    "cd_omega_2pi": 0.724854191990218, "cd_status_code": 0.0, "constancy": 0.0,
    "cov_profile": 0.005359047549871544, "di_estimated": 0.0, "di_roughness": 0.21591922522230808,
    "diag": 0.2010653900542653, "dislope": 0.2213337896650769, "distd": 0.4538835077946186,
    "f11_hz": 5600.0, "flat": 0.8883355772601959, "flat_cv": 0.5525458991905337, "hf_floor": 0.0,
    "lfp20_hz": 674.0824515394638, "lfp50_hz": 994.8436820864767, "load": 2.644557169543657,
    "loaded_hi_hz": 5600.0, "n_in_band": 16, "n_nan": 0, "oa_excess_raw": 30.0,
    "offaxis_smooth": 0.5428726725796293, "penalty": 0.0, "rez_min_from_fx": 0.33027490008552046,
    "rip": 0.09432123956949674, "total": 4.996463749003073,
}
BEST_J = 4.996463749003073
V11_KEYS = {"cov_profile", "rip", "flat", "load", "dislope", "di_roughness", "flat_cv",
            "cd_lw", "cd_di_std", "cd_nacc", "offaxis_smooth"}


def _seed_terms() -> dict:
    """A start row with different values; its stored total is computed from the v11 rule."""
    t = {k: (v * 1.1 if isinstance(v, float) else v) for k, v in BEST_TERMS.items()}
    w = dict(V11_WEIGHTS, cd_lw=1.5, cd_di_std=0.75, cd_nacc=0.75, offaxis_smooth=1.0)
    t["total"] = sum(w[k] * t[k] for k in V11_KEYS)
    return t


@pytest.fixture()
def v11_run(tmp_path):
    runs = tmp_path / "repo" / "runs"
    run = runs / RID
    run.mkdir(parents=True)
    (run / "config.yaml").write_text(yaml.safe_dump({
        "name": "cd11c__crowe_x_osse_cd", "family": "FREEFORM", "weights": V11_WEIGHTS,
        "objective": V11_OBJECTIVE, "target": {"coverage_h_deg": 80, "coverage_v_deg": 50}}))
    seed = _seed_terms()
    rows = [
        {"n": 0, "design_hash": "4be8fdb4b00d", "ok": True, "objective": seed["total"], "mode": "screen",
         "family": "FREEFORM", "created_utc": "2026-11-20T08:40:30Z", "terms": seed},
        {"n": 44, "design_hash": "4140768780f0", "ok": True, "objective": BEST_J, "mode": "screen",
         "family": "FREEFORM", "created_utc": "2026-11-20T08:55:00Z", "terms": BEST_TERMS},
    ]
    (run / "search.ndjson").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    (run / "run.json").write_text(json.dumps({"objective_version": 11, "mode": "screen"}))
    return runs


def _assert_v11(bd: dict) -> None:
    assert bd["available"] is True and bd["version"] == 11
    assert set(bd["keys"]) == V11_KEYS                       # every weighted v11 term, no extras
    assert {"cov", "di"}.isdisjoint(bd["keys"])              # the legacy v1 names are gone
    assert bd["weights"]["cd_lw"] == 1.5 and bd["weights"]["offaxis_smooth"] == 1.0
    assert bd["weights"]["flat_cv"] == 0.5 and bd["weights"]["di_roughness"] == 0.5
    best_sum = sum(r["best"] for r in bd["rows"])
    assert best_sum == pytest.approx(BEST_J, abs=1e-12)      # bars add up to the stored J
    assert bd["best"]["total"] == BEST_J and bd["best"]["unattributed"] == 0.0
    assert all(r["key"] != "unattributed" for r in bd["rows"])
    cd = sum(r["best"] for r in bd["rows"] if r["key"] in ("cd_lw", "cd_di_std", "cd_nacc", "offaxis_smooth"))
    assert cd == pytest.approx(1.5*0.23063677466770635 + 0.75*0.4253050294642921
                               + 0.75*0.20335074636844142 + 0.5428726725796293)


def test_v11_breakdown_sums_to_stored_j(v11_run):
    d = D.run_detail(v11_run, RID)
    bd = d["score_breakdown"]
    _assert_v11(bd)
    assert sum(r["seed"] for r in bd["rows"]) == pytest.approx(d["terms_seed"]["total"], abs=1e-12)
    json.dumps(d, allow_nan=False)


def test_v11_fallback_without_scalar_v11_matches(v11_run, monkeypatch):
    """Checkouts without objective/scalar_v11.py use the documented v10 + objective.cd rule."""
    monkeypatch.setitem(sys.modules, "hornlab_search.objective.scalar_v11", None)
    bd = D.run_detail(v11_run, RID)["score_breakdown"]
    _assert_v11(bd)
    assert "scalar_v11 not importable" in bd["source"]


def test_gap_to_stored_total_is_an_explicit_row():
    """A v7-style add-on or failure penalty never vanishes: it shows as 'unattributed'."""
    terms = {"cov": 1.0, "rip": 2.0, "di": 0.0, "dislope": 0.0, "flat": 0.0, "load": 0.0,
             "total": 3.0 + 1000.0}
    bd = score_breakdown({"weights": {"cov": 1.0, "rip": 1.0}}, 1, None, terms)
    assert bd["available"] and bd["keys"] == ["cov", "rip", "di", "dislope", "flat", "load"]
    assert bd["rows"][-1]["key"] == "unattributed" and bd["rows"][-1]["best"] == pytest.approx(1000.0)
    assert sum(r["best"] for r in bd["rows"]) == pytest.approx(terms["total"])
    assert bd["seed"] is None and bd["rows"][0]["seed"] is None


def test_unreadable_objective_block_degrades():
    bd = score_breakdown({"objective": {"version": 9, "tolerances": "nope"}}, 9, None, {"total": 1.0})
    assert bd["available"] is False and bd["reason"]


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
const d = JSON.parse(process.argv[3]);

// server breakdown: every row drawn, unattributed last, labels for the CD terms, Σ line names J
const out = app.scoreBreakdownRows(d, {});
assert.equal(out.rows.length, d.score_breakdown.rows.length);
const keys = out.rows.map(r => r.key);
for (const k of ["cd_lw", "cd_di_std", "cd_nacc", "offaxis_smooth", "flat_cv", "di_roughness"])
  assert.ok(keys.includes(k), k);
assert.equal(out.rows[0].key, "load");                       // the largest best contribution first
const lw = out.rows.find(r => r.key === "cd_lw");
assert.equal(lw.label, "CD listening window"); assert.equal(lw.wLabel, "×1.5");
const sum = out.rows.reduce((a, r) => a + (r.best || 0), 0);
assert.ok(Math.abs(sum - 4.996463749003073) < 1e-9, String(sum));
assert.match(out.sumLine, /best Σ 4\.9965 \(stored J 4\.9965\)/);
assert.match(out.sumLine, /11 weighted terms, J v11/);

// with a gap row it stays last whatever its size
const gap = structuredClone(d);
gap.score_breakdown.rows.push({ key: "unattributed", weight: null, seed: 0, best: 99 });
const g = app.scoreBreakdownRows(gap, {});
assert.equal(g.rows.at(-1).key, "unattributed"); assert.equal(g.rows.at(-1).wLabel, "not a term");

// an older server (no score_breakdown) keeps the legacy six-term chart
const legacy = app.scoreBreakdownRows({ terms_seed: { cov: 2 }, terms_best: { cov: 1 } }, { cov: 1 });
assert.deepEqual(legacy.rows.map(r => r.key).sort(), ["cov", "di", "dislope", "flat", "load", "rip"]);
assert.match(legacy.sumLine, /legacy/);
console.log("BREAKDOWN JS OK");
'''


def test_breakdown_rows_js(v11_run, tmp_path):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not installed")
    d = D.run_detail(v11_run, RID)
    script = tmp_path / "breakdown_under_test.mjs"
    script.write_text(_NODE, encoding="utf-8")
    r = subprocess.run([node, str(script), str(APPJS),
                        json.dumps({"score_breakdown": d["score_breakdown"]})],
                       capture_output=True, text=True, encoding="utf-8", cwd=str(tmp_path))
    assert "BREAKDOWN JS OK" in r.stdout, f"stdout: {r.stdout}\nstderr: {r.stderr}"


def test_size_penalty_is_its_own_row_and_sums_to_the_row_j():
    """Brief envelope.soft_penalty (2026-11-25) adds to J after the objective; terms.total stays
    acoustic, so the breakdown must show size_penalty and reconcile to J_acoustic + size_penalty."""
    w = dict(V11_WEIGHTS, cd_lw=1.5, cd_di_std=0.75, cd_nacc=0.75, offaxis_smooth=1.0)
    best = dict(BEST_TERMS, size_penalty=0.36, size_utilization=1.03, J_acoustic=BEST_J)
    seed = dict(BEST_TERMS)          # an unpenalised start row (inside the box)
    cfg = {"weights": V11_WEIGHTS, "objective": V11_OBJECTIVE}
    bd = score_breakdown(cfg, 11, seed, best)
    assert bd["keys"][-1] == "size_penalty" and bd["weights"]["size_penalty"] == 1.0
    row = next(r for r in bd["rows"] if r["key"] == "size_penalty")
    assert row["best"] == pytest.approx(0.36) and row["seed"] is None
    assert sum(r["best"] for r in bd["rows"] if r["best"] is not None) == pytest.approx(BEST_J + 0.36)
    assert bd["best"]["total"] == pytest.approx(BEST_J + 0.36) and bd["best"]["unattributed"] == 0.0
    assert bd["seed"]["unattributed"] == 0.0
    assert all(r["key"] != "unattributed" for r in bd["rows"])
    del w
