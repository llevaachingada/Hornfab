"""L2 view smoke tests: Design cloud, Boundary Lab A/B report, 3D evolution.

All three are headless and offline: a synthetic run folder (search.ndjson + tiny saved meshes +
config.yaml + a committed gate-audit CSV), and the compare package's own fake data for the A/B
report. No solver is imported and no solve runs.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from hornlab_search.gui import data as D
from hornlab_search.gui.server import App

ROOT = Path(__file__).resolve().parents[1]
APPJS = ROOT / "hornlab_search" / "gui" / "static" / "app.js"

RID = "20261112T120000Z-screen-abc111"
HASHES = ["aaaaaaaaaaaa", "bbbbbbbbbbbb", "cccccccccccc"]
F = [500.0, 1000.0, 2000.0, 4000.0, 5500.0]

_CONFIG = {
    "name": "l2_smoke",
    "family": "OSSE",
    "bounds": {
        "L_mm": {"lo": 100.0, "hi": 200.0},
        "a_deg": {"lo": 30.0, "hi": 50.0},
        "n": {"lo": 3.0, "hi": 7.0, "search": False},
    },
    "search": {"algorithm": "cma", "budget": 20, "seed": 1, "sigma0": 0.2},
    "mesh": {"epw": 6.0, "quadrants": "1"},
    "solve": {"backend": "beat_cpu"},
    "target": {"band_lo_hz": 300, "band_hi_hz": 5000},
    "weights": {"cov": 1.0},
    "objective": {"version": 7},
}


def _write_mesh(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "$MeshFormat\n2.2 0 8\n$EndMeshFormat\n$Nodes\n3\n"
        "1 0 0 0\n2 0.1 0 0.05\n3 0 0.08 0.05\n$EndNodes\n"
        "$Elements\n1\n1 2 2 1 1 1 2 3\n$EndElements\n",
        encoding="utf-8",
    )


def _row(n: int, h: str, objective: float, L: float, a: float) -> dict:
    return {
        "n": n,
        "design_hash": h,
        "ok": True,
        "objective": objective,
        "mode": "screen",
        "family": "OSSE",
        "params": {"L_mm": L, "a_deg": a, "n": 5.0},
        "created_utc": f"2026-11-12T00:00:{n:02d}Z",
    }


@pytest.fixture()
def repo(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "repo"
    runs = root / "runs"
    run = runs / RID
    run.mkdir(parents=True)
    (run / "config.yaml").write_text(yaml.safe_dump(_CONFIG), encoding="utf-8")
    # 5.0 -> 4.0 are strictly improving; 9.0 is not, so the 3D view has exactly two frames.
    rows = [
        _row(0, HASHES[0], 5.0, 110.0, 32.0),
        _row(1, HASHES[1], 4.0, 140.0, 40.0),
        _row(2, HASHES[2], 9.0, 170.0, 47.0),
    ]
    (run / "search.ndjson").write_text(
        "\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    (run / "run.json").write_text(
        json.dumps({"backend": "beat_cpu", "objective_version": 7}), encoding="utf-8")
    for h in HASHES[:2]:
        _write_mesh(run / "designs" / h / "mesh.msh")
    # A committed gate audit: only the gates actually in this header may surface in the GUI.
    audit = root / "docs" / "data" / "gate_audit_smoke"
    audit.mkdir(parents=True)
    (audit / "gate_audit.csv").write_text(
        "run,tier,design,J,throat,load,h,v,di,bw8k,pass_all\n"
        f"{RID},verify,{HASHES[0]},4.0,True,False,True,False,True,False,False\n"
        f"{RID},screen,{HASHES[1]},5.0,False,True,False,False,True,True,False\n"
        "20260101T000000Z-screen-ffffff,verify,deadbeef0001,1.0,True,True,True,True,True,True,True\n",
        encoding="utf-8",
    )
    return root, runs


def test_design_cloud_view_smoke(repo):
    """The Design cloud payload names its objective version and carries only the audit's gates."""
    root, runs = repo
    d = D.run_umap_cloud(runs, RID, method="pca", root=root)
    assert d["objective_version"] == 7
    assert d["gate_audit"]["source"] == "docs/data/gate_audit_smoke/gate_audit.csv"
    assert d["gate_audit"]["gates"] == ["throat", "load", "h", "v", "di", "bw8k"]
    assert d["gate_audit"]["labels"]["throat"] == "round throat"
    assert d["gate_audit"]["labels"]["h"] == "CD H"
    assert d["gate_audit"]["labels"]["v"] == "CD V"
    pts = {p["hash"]: p for p in d["points"]}
    assert pts[HASHES[0]]["gates"] == {
        "throat": True, "load": False, "h": True, "v": False, "di": True, "bw8k": False}
    assert "gates" not in pts[HASHES[2]]          # no audit row -> no chips, never an invented pass
    # The HTTP route must pass the repo root through or the committed audit is invisible.
    app = App(root, runs)
    api = app.get(f"/api/umap/{RID}", {"method": ["pca"]})
    assert api["objective_version"] == 7
    assert api["gate_audit"]["source"] == d["gate_audit"]["source"]
    detail = app.get(f"/api/run/{RID}", {})
    assert detail["objective_version"] == 7
    assert set(detail["gate_audit"]["designs"]) == {HASHES[0], HASHES[1]}


def test_boundary_lab_ab_report_smoke(tmp_path):
    """PR #23's A/B report builds its self-contained HTML/summary/verdict offline."""
    from hornlab_search.compare import analysis as an, bl_import as bi, fake, hornfab_side as hs
    from hornlab_search.compare.report import build_report

    sides = tmp_path / "ab"
    sides.mkdir()
    fake.write_hornfab_side(sides / "a", fake.FAKE_FREQS[::2])
    fake.write_bl_gui_side(sides / "b", fake.FAKE_FREQS[::2], inject="offset6")
    cmp = an.compare(hs.load_hornfab(sides / "a"), bi.import_bl(sides / "b"))

    out = sides / "report"
    res = build_report(cmp, out, backend="builtin", provenance={"source": "gui-smoke"})
    for name in ("report.html", "summary.json", "verdict.txt", "comparison_arrays.npz"):
        assert (out / name).is_file(), name
    html = (out / "report.html").read_text(encoding="utf-8")
    assert "<svg" in html and "Verdict table" in html and "Provenance" in html
    assert res["overall"] in ("pass", "warn", "fail")
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert summary["overall"] == res["overall"]


def test_evolution_3d_view_smoke(repo):
    """The time-lapse and its per-improved-frame 3D geometry both serve without a solve."""
    root, runs = repo
    evo = D.evolution(runs, RID)
    assert [f["n"] for f in evo["frames"]] == [0, 1, 2]
    assert evo["n_improvements"] == 2

    frames = D.evolution_frames3d(runs, RID)
    assert frames["available"] is True
    assert [f["n"] for f in frames["frames"]] == [0, 1]
    assert frames["frames"][0]["n_verts"] == 3
    assert len(frames["frames"][0]["tris"]) == 3

    app = App(root, runs)
    api = app.get(f"/api/evolution/{RID}/frames3d", {})
    assert api["available"] is True and [f["n"] for f in api["frames"]] == [0, 1]
    assert [f["n"] for f in app.get(f"/api/evolution/{RID}", {})["frames"]] == [0, 1, 2]


# ── Objective-version guard helpers (L2.2/L2.3): executed for real through node ─────────────

_GUARD_SCRIPT = r'''
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
globalThis.location = { hash: "#/glossary" };
globalThis.requestAnimationFrame = () => 0;
globalThis.localStorage = { getItem: () => null, setItem() {}, removeItem() {} };
globalThis.fetch = () => Promise.reject(new Error("offline shim"));

const app = await import(pathToFileURL(process.argv[2]).href);
const { objectiveVersionOf, jVersionLabel, objectiveVersions, objectiveVersionBannerHtml,
        sortRunsForTable, gateAuditHtml, J_VERSION_BANNER } = app;

assert.equal(objectiveVersionOf(null), 1);
assert.equal(objectiveVersionOf(undefined), 1);
assert.equal(objectiveVersionOf({}), 1);
assert.equal(objectiveVersionOf({ objective_version: 7 }), 7);
assert.equal(objectiveVersionOf("4"), 4);
assert.equal(jVersionLabel({ objective_version: 7 }), "J v7");
assert.equal(jVersionLabel({}), "J v1");
assert.deepEqual(objectiveVersions([{ objective_version: 4 }, { objective_version: 7 },
                                    { objective_version: 4 }]), [7, 4]);
assert.equal(objectiveVersionBannerHtml([{ objective_version: 7 }]), "");
const banner = objectiveVersionBannerHtml([{ objective_version: 7 }, { objective_version: 4 }]);
assert.ok(banner.includes("alert warn"), banner);
assert.equal(J_VERSION_BANNER, "J from different objective versions is not comparable");
assert.ok(banner.includes(J_VERSION_BANNER), banner);

const runs = [
  { name: "v4-a", best_j: 5, started: "2026-01-01", objective_version: 4 },
  { name: "v7-b", best_j: 9, started: "2026-01-02", objective_version: 7 },
  { name: "v7-c", best_j: 1, started: "2026-01-03", objective_version: 7 },
];
assert.deepEqual(sortRunsForTable(runs, "best_j").map(r => r.name), ["v7-c", "v7-b", "v4-a"]);
assert.deepEqual(sortRunsForTable(runs.slice(1), "best_j").map(r => r.name), ["v7-c", "v7-b"]);

assert.equal(gateAuditHtml(null), "");
assert.equal(gateAuditHtml({ available: false }), "");
const audit = {
  available: true, source: "docs/data/gate_audit_x/gate_audit.csv",
  gates: ["throat", "load"], labels: { throat: "round throat", load: "loading" },
  designs: {
    aaa: { gates: { throat: true, load: false }, J: 3.2, tier: "verify" },
    bbb: { gates: { throat: false, load: true }, J: 4.0, tier: "screen" },
  },
};
const gate = gateAuditHtml(audit);
assert.ok(gate.includes("Gate audit"), gate);
assert.ok(gate.includes("round throat") && gate.includes("loading"), gate);
assert.ok(gate.includes("pass") && gate.includes("fail"), gate);
assert.ok(gate.includes("docs/data/gate_audit_x/gate_audit.csv"), gate);
assert.ok(!gate.includes("CD H"), "gates absent from the audit must not be invented");

console.log("L2 GUARD OK");
'''


def test_objective_version_guard_helpers(tmp_path):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not installed")
    script = tmp_path / "guard_under_test.mjs"
    script.write_text(_GUARD_SCRIPT, encoding="utf-8")
    r = subprocess.run([node, str(script), str(APPJS)],
                       capture_output=True, text=True, cwd=str(tmp_path))
    assert "L2 GUARD OK" in r.stdout, f"node test failed:\nstdout: {r.stdout}\nstderr: {r.stderr}"
