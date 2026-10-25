"""Brief authoring (GUI Briefs page: new-brief-from-scratch + exposed controls) and the
Compose wizard (typology-first run builder).

Offline reader-level pins:
  (a) the server's own ``load_brief`` (via D.save_user_brief) accepts EVERY key the new editor
      saves — verify_only, objective.version, driver.throat_angle_policy, target.freq_weights,
      and axisymmetric with a w != h envelope (mirroring examples/briefs/user/7040.yaml) — and
      nothing the editor sends is silently dropped on the round trip;
  (b) the shipped-name collision and bad-name refusals still hold;
  (c) list_briefs sees the saved user brief;
  (d) the Compose wizard's POST bodies map 1:1 onto jobs.build_argv's allow-listed kinds, and
      the campaign kind's budget/seeds reality (the GUI allow-list plumbs neither) is pinned so
      the wizard's no-override-fields choice stays honest.

Plus the app.js ES-module syntax gate, copied from tests/test_gui.py
(test_static_js_parses_as_an_es_module) so a syntax error is caught offline.

Also appended: the provenance-strip view layer of the GUI integration plan phases G1-G4
(docs/GUI_INTEGRATION_PLAN_2026-10-25.md, contracts C-1/C-2) - badge builder + run extractor +
restarts card + STEP inventory chips + qd caption + f11 caveat, executed for real via node (the
app.js import runs under the same DOM-shim pattern the mesh-quadrants tests use for view3d.js),
plus the view call-site wiring pinned by source checks (test_compose_view_is_wired style).
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

from hornlab_search.gui import jobs as J
from hornlab_search.gui.data import list_briefs, save_user_brief

ROOT = Path(__file__).resolve().parents[1]

# The exact shape the reworked Briefs editor builds (app.js ::showBriefDetail save payload):
# every schema key the form carries, left at defaults or edited, round-trips through the
# server-authoritative validation in config.py::load_brief.
FULL_EDITOR_PAYLOAD = {
    "name": "authoring_check",              # save_user_brief re-sets it from the name argument
    "description": "editor-built authoring smoke",
    "driver": {"exit_radius_mm": 12.7, "exit_angle_deg": 0, "throat_angle_policy": "pin"},
    "envelope": {"max_mouth_w_mm": 500, "max_mouth_h_mm": 400, "max_depth_mm": 250},  # w != h
    "symmetry": "axisymmetric",
    "source": {},
    "target": {
        "coverage_h_deg": 50, "coverage_v_deg": 50,
        "band_lo_hz": 500, "band_hi_hz": 12000,     # no 5500 clamp anywhere in the schema
        "di_target_db": None, "di_slope_target": 0, "z_min": 0,
        "freq_weights": {"band_hz": [[700.0, 1200.0, 1.5], [2000.0, 4000.0, 2.0]]},
    },
    "weights": {"cov": 1.0, "rip": 1.0, "di": 0.3, "dislope": 0.5, "flat": 0.5, "load": 0.5},
    "verify_only": True,
    "objective": {"version": 2},
}


@pytest.fixture()
def brief_root(tmp_path):
    root = tmp_path / "repo"
    (root / "examples" / "briefs").mkdir(parents=True)
    return root


def test_save_user_brief_round_trips_every_editor_key(brief_root):
    """(a) The schema accepts ALL the editor keys — including axisymmetric with a w != h envelope
    like the shipped examples/briefs/user/7040.yaml — and nothing is silently dropped."""
    p = save_user_brief(brief_root, "authoring_check", FULL_EDITOR_PAYLOAD)
    assert p == brief_root / "examples" / "briefs" / "user" / "authoring_check.yaml"
    # save_user_brief validated the bytes through the CLI's real load_brief; assert the file
    # also lists and reads back key-for-key through the GUI reader.
    [saved] = [b for b in list_briefs(brief_root) if b["name"] == "authoring_check"]
    br = saved["brief"]
    assert saved["kind"] == "user"
    assert br["name"] == "authoring_check"
    assert br["description"] == "editor-built authoring smoke"
    assert br["verify_only"] is True
    assert br["objective"] == {"version": 2}
    assert br["driver"] == {"exit_radius_mm": 12.7, "exit_angle_deg": 0, "throat_angle_policy": "pin"}
    assert br["envelope"]["max_mouth_w_mm"] == 500 and br["envelope"]["max_mouth_h_mm"] == 400
    assert br["symmetry"] == "axisymmetric"          # legal with the w != h envelope above
    assert br["target"]["band_hi_hz"] == 12000       # saved exactly as typed, never clamped
    assert br["target"]["freq_weights"] == {"band_hz": [[700.0, 1200.0, 1.5], [2000.0, 4000.0, 2.0]]}
    assert br["target"]["z_min"] == 0 and br["target"]["di_target_db"] is None


def test_list_briefs_sees_the_saved_user_brief(brief_root):
    """(c) A brief saved through the editor's payload appears in the Briefs list as a user brief."""
    save_user_brief(brief_root, "authoring_check", FULL_EDITOR_PAYLOAD)
    names = {b["name"]: b for b in list_briefs(brief_root)}
    assert "authoring_check" in names
    assert names["authoring_check"]["kind"] == "user"
    assert names["authoring_check"]["path"] == "examples/briefs/user/authoring_check.yaml"
    assert names["authoring_check"]["brief"]["verify_only"] is True


def test_save_user_brief_refusals_still_hold(brief_root):
    """(b) Shipped-name collision and illegal names are refused; nothing is written."""
    shutil.copy(ROOT / "examples" / "briefs" / "axi_90x90_1in.yaml",
                brief_root / "examples" / "briefs" / "axi_90x90_1in.yaml")
    with pytest.raises(ValueError, match="is a shipped brief"):
        save_user_brief(brief_root, "axi_90x90_1in", dict(FULL_EDITOR_PAYLOAD, name="axi_90x90_1in"))
    with pytest.raises(ValueError, match="brief name"):
        save_user_brief(brief_root, "bad name!", dict(FULL_EDITOR_PAYLOAD))
    user_dir = brief_root / "examples" / "briefs" / "user"
    assert not user_dir.exists() or not list(user_dir.iterdir())


@pytest.mark.parametrize("name", ["app.js"])
def test_static_js_parses_as_an_es_module(name, tmp_path):
    """Same offline gate as test_gui.py: a syntax error in app.js blanks every view."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not installed")
    src = ROOT / "hornlab_search" / "gui" / "static" / name
    mjs = tmp_path / (name + ".mjs")                    # .mjs: parse as a module, not CommonJS
    mjs.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    r = subprocess.run([node, "--check", str(mjs)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]


def _job_root(tmp_path):
    """A minimal repo: one loadable config, one loadable brief (build_argv resolves --config and
    --brief to real files inside the repository — a path that does not exist is refused)."""
    root = tmp_path / "repo"
    (root / "examples" / "briefs").mkdir(parents=True)
    (root / "examples" / "typologies").mkdir(parents=True)
    (root / "examples" / "cfg.yaml").write_text("name: cfg\n")
    (root / "examples" / "typologies" / "conical.yaml").write_text("name: conical\n")
    shutil.copy(ROOT / "examples" / "briefs" / "axi_90x90_1in.yaml",
                root / "examples" / "briefs" / "axi_90x90_1in.yaml")
    return root, "examples/typologies/conical.yaml", "examples/briefs/axi_90x90_1in.yaml"


def test_compose_wizard_argv_shapes(tmp_path):
    """(d) The compose wizard's POST bodies map 1:1 onto the allow-listed kinds it uses
    (single config: dry-run/run/search; 2+ picks: campaign), read back from jobs.build_argv."""
    root, cfg, brf = _job_root(tmp_path)
    jm = J.JobManager(root, root / "runs")
    # single-config dry-run: {config, brief} -> run --config ... --dry-run --brief ... ; no GPU
    argv, gpu = jm.build_argv("dry-run", {"config": cfg, "brief": brf})
    assert argv == ["run", "--config", cfg, "--dry-run", "--brief", brf] and gpu is False
    # single-config run with an optional seed: {config, brief, cma_seed}
    argv, gpu = jm.build_argv("run", {"config": cfg, "brief": brf, "cma_seed": "7"})
    assert argv == ["run", "--config", cfg, "--brief", brf, "--cma-seed", "7"] and gpu is True
    # single-config search: {config, budget?, brief, cma_seed?} (blank budget -> engine default 60)
    argv, gpu = jm.build_argv("search", {"config": cfg, "brief": brf})
    assert argv == ["search", "--config", cfg, "--budget", "60", "--brief", brf] and gpu is True
    argv, _ = jm.build_argv("search", {"config": cfg, "budget": "120", "brief": brf})
    assert argv == ["search", "--config", cfg, "--budget", "120", "--brief", brf]
    # campaign: {brief, families, tier}; families come from the picked CATALOG names, comma-joined
    argv, gpu = jm.build_argv("campaign", {"brief": brf, "families": "conical,hypex", "tier": "screen"})
    assert argv == ["campaign", "--brief", brf, "--families", "conical,hypex", "--tier", "screen"] and gpu is True
    argv, gpu = jm.build_argv("campaign", {"brief": brf, "families": "conical", "tier": "dry-run"})
    assert gpu is False and argv[-2:] == ["--tier", "dry-run"]
    # engine refusals the wizard surfaces verbatim: bad families spec, missing brief
    with pytest.raises(J.JobError, match="families"):
        jm.build_argv("campaign", {"brief": brf, "families": "Conical X", "tier": "screen"})
    with pytest.raises(J.JobError, match="campaign needs a brief"):
        jm.build_argv("campaign", {"families": "conical", "tier": "screen"})


def test_campaign_budget_and_seeds_are_not_gui_plumbed(tmp_path):
    """Pins the allow-list reality behind the wizard's UI choice: jobs.build_argv("campaign")
    plumbs ONLY brief/families/tier, so --seeds/--budget overrides CANNOT reach the engine from
    the GUI — campaign runs use the engine's budget_for_tier defaults. The compose wizard
    therefore ships budget_for_tier captions and NO override fields (fields that silently
    vanish would lie). If a later lane plumbs seeds/budget, update this pin and the wizard
    together."""
    root, cfg, brf = _job_root(tmp_path)
    jm = J.JobManager(root, root / "runs")
    argv, _ = jm.build_argv("campaign", {"brief": brf, "families": "conical", "tier": "screen",
                                         "budget": 99, "seeds": 3, "cma_seed": 5})
    assert argv == ["campaign", "--brief", brf, "--families", "conical", "--tier", "screen"]
    assert not any(v in {"--budget", "--seeds", "--cma-seed"} for v in argv)


def test_compose_view_is_wired():
    """The wizard is reachable: route + nav item + view function all exist in the static files."""
    app = (ROOT / "hornlab_search" / "gui" / "static" / "app.js").read_text(encoding="utf-8")
    idx = (ROOT / "hornlab_search" / "gui" / "static" / "index.html").read_text(encoding="utf-8")
    assert "function viewCompose" in app
    assert re.search(r"re: /\^#\\/compose\$/", app)          # route registered
    assert 'href="#/compose"' in idx and 'aria-label="Compose"' in idx
    assert re.search(r'h === "#/compose" && hash === "#/compose"', app)   # nav highlight
    # the wizard reuses the briefs editor (mount) and the stem-matching loader, not copies
    assert "opts.mount" in app and "function findBriefByFile" in app and "function newBriefDraft" in app


# ── Provenance strips (GUI plan phases G1–G4; contracts C-1/C-2) ─────────────────────────
# app.js renders the badge matrix (§7 badges, non-default only, key-path tooltips), the restart
# schedule card (C-1 restarts/restart_dirs), the qd atlas caption (C-1 qd), the compare mixed_keys
# banner + DI guard twin (C-2 group_a/group_b) and the STEP inventory chips (C-1 step_files_detail).
# Branch behavior is executed for real by node (below), the same module-import pattern
# tests/test_gui_mesh_quadrants.py uses for view3d.js::mirrorMesh; the view call sites are pinned
# by source checks (test_compose_view_is_wired style) since the views need the browser DOM.

APPJS = ROOT / "hornlab_search" / "gui" / "static" / "app.js"


def test_provenance_views_are_wired():
    """Every strip lives inside its committed view — no new nav item, no new route, index.html
    untouched by these phases."""
    src = APPJS.read_text(encoding="utf-8")
    # G1 run detail: header badge strip fed by the reader's solve_group + f11 caveat (§3.4)
    assert "function runProvenanceGroup(d)" in src and "function renderProvenanceBadges(group" in src
    assert 'renderProvenanceBadges(prov.group, "", prov.tips)' in src
    assert "typeof d.solve_group" in src and 'tips[k] = "solve_group." + k' in src
    assert "typeof d.search_restarts" in src and '"run_detail.search_restarts.mode"' in src
    assert "f11CaveatHtml(d)" in src and "best.scalars.f11_hz" in src
    # G2: restart card below the KPIs, header reads search_restarts, honest empty state kept
    assert "restartScheduleHtml(d, id)" in src
    assert "run.json predates the restarts block" in src
    assert "carries no valid" in src                      # fallback only for the absent case
    # G2 atlas: qd caption read from the run payload, rendered in the header (canvas untouched)
    assert "qdProvenanceCaption(QD)" in src
    assert '"/api/run/" + encodeURIComponent(id)' in src
    # G3 compare: server group objects through the same builder, mixed banner, DI guard twin
    assert "renderProvenanceBadges(grp, prefix)" in src
    assert 'sideBadgeRow("A", gA, "group_a.")' in src and 'sideBadgeRow("B", gB, "group_b.")' in src
    assert "const mixedBanner = mixed.length" in src and "These runs differ in:" in src
    assert "const dsA = dA.di_source, dsB = dB.di_source;" in src
    assert 'dsA !== "balloon"' in src and 'dsB !== "balloon"' in src
    assert "DI: cuts estimate — not comparable" in src
    # G4 chips: the UNCHANGED step_files name list + step_files_detail matched by name
    assert "function stepInvByName(detail)" in src and "function stepChipHtml(name, inv, id)" in src
    assert "stepInvByName(detail)" in src and "renderFiles(d.step_files, d.step_files_detail)" in src
    # the pure helpers are exported for the offline node test (view3d.js::mirrorMesh precedent)
    assert "export { runProvenanceGroup, renderProvenanceBadges, restartScheduleHtml, stepChipHtml," in src
    assert "stepInvByName, qdProvenanceCaption, f11CaveatHtml };" in src


# The node script: imports app.js under an import-time DOM shim (app.js touches document/window at
# module scope; location stays on the synchronous view so no fetch happens), then executes every
# badge/card/chip branch. Same wrapper approach as tests/test_gui_mesh_quadrants.py.
_PROV_SCRIPT = r'''
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
const { runProvenanceGroup, renderProvenanceBadges, restartScheduleHtml, stepChipHtml,
        stepInvByName, qdProvenanceCaption, f11CaveatHtml } = app;
assert.equal(typeof renderProvenanceBadges, "function");

// badge builder: non-default only + exact key-path tooltips
assert.equal(renderProvenanceBadges({}), "");
assert.equal(renderProvenanceBadges(null), "");
let h = renderProvenanceBadges({ backend: "bempp_cpu" });
assert.ok(h.includes(">bempp_cpu</span>"), h);
assert.ok(h.includes(`title="backend = bempp_cpu"`), h);
h = renderProvenanceBadges({ backend: "beat_cuda" }, "group_a.");
assert.ok(h.includes(`title="group_a.backend = beat_cuda"`), h);
// C-2 identity baseline: backend + freqs_hz always render on compare group sides
h = renderProvenanceBadges({ backend: "beat_cuda", freqs_hz: { mode: "screen", band_lo_hz: 300, band_hi_hz: 12000 } }, "group_b.");
assert.match(h, /grid screen 300–12000 Hz/);
assert.ok(h.includes("group_b.freqs_hz = ") && h.includes("&quot;mode&quot;:&quot;screen&quot;"), h);
h = renderProvenanceBadges({ freqs_hz: { mode: "screen", band_lo_hz: 300, band_hi_hz: 12000, verify_points_per_octave: 8 } });
assert.match(h, /8\/oct verify/);
assert.equal(renderProvenanceBadges({ freqs_hz: {} }), "");       // partial identity: no badge
h = renderProvenanceBadges({ cuda_fused: true });
assert.ok(h.includes(">fused CUDA</span>") && h.includes(`title="cuda_fused = true"`), h);
h = renderProvenanceBadges({ near_correction: true, solve_precision: "double" });
assert.match(h, /near-corrected · double/);
h = renderProvenanceBadges({ near_correction: true });
assert.match(h, /near-corrected/);
assert.ok(!h.includes("· double"));                  // precision never claimed when absent
h = renderProvenanceBadges({ solve_precision: "double" });
assert.match(h, /double precision/);
h = renderProvenanceBadges({ source_profile_alpha: 0.5, source_profile: "j0_radial" });
assert.match(h, /source plug α=0\.5 \(j0_radial\)/);
assert.ok(h.includes(`title="source_profile_alpha = 0.5"`), h);
assert.equal(renderProvenanceBadges({ source_profile_alpha: 0 }), "");  // α=0 is the default
h = renderProvenanceBadges({ mesh_policy: "band_split_v1", band_edges_hz: [3000, 6000] });
assert.match(h, /band-split 3\/6 k/);
assert.ok(h.includes(`title="mesh_policy = band_split_v1"`), h);
h = renderProvenanceBadges({ rear_res_factor: 2 });
assert.match(h, /rear ×2/);
assert.equal(renderProvenanceBadges({ rear_res_factor: 1 }), "");   // default: no badge
h = renderProvenanceBadges({ mounting: { type: "enclosure", depth_mm: 250 } });
assert.match(h, /enclosure d=250 mm/);
h = renderProvenanceBadges({ objective_version: 2 });
assert.match(h, /J v2/);
assert.equal(renderProvenanceBadges({ objective_version: 1 }), ""); // v1 default: unlabelled
h = renderProvenanceBadges({ qd_algorithm: "cma_me" });
assert.match(h, /CMA-ME/);
h = renderProvenanceBadges({ restarts_count: 3, restarts_mode: "bipop" });
assert.match(h, /BIPOP ×3/);
h = renderProvenanceBadges({ restarts_count: 3 });
assert.match(h, /restarts ×3/);
assert.ok(!h.includes("IPOP"));                      // the mode is never invented when unknown
assert.match(renderProvenanceBadges({ source_motion: "axial" }), /source motion axial/);

// run-provenance extraction: read straight from the reader's solve_group (the same fingerprint
// /api/compare exposes) + the C-1 restarts array + the live search_restarts schedule
let p = runProvenanceGroup({});
assert.deepEqual(p.group, {});                       // older payload / no solve_group: nothing fabricated
assert.deepEqual(p.tips, {});
const RE = { index: 0, popsize: 10, sigma0: 0.25, n_new_in_restart: 59, evals_in_restart: 59, stop: "budget" };
// identity-only solve_group (a plain beat_cuda run): exactly the two baseline keys
const IDENTITY = { backend: "beat_cuda", freqs_hz: { mode: "screen", band_lo_hz: 300, band_hi_hz: 12000 } };
p = runProvenanceGroup({ solve_group: { backend: IDENTITY.backend, freqs_hz: IDENTITY.freqs_hz } });
assert.deepEqual(Object.keys(p.group), ["backend", "freqs_hz"]);
assert.equal(p.group.backend, "beat_cuda");
assert.deepEqual(p.group.freqs_hz, IDENTITY.freqs_hz);
assert.equal(p.tips.backend, "solve_group.backend");
assert.equal(p.tips.freqs_hz, "solve_group.freqs_hz");
// the schedule: restarts array -> count; search_restarts -> mode/max (absent = no invented mode)
p = runProvenanceGroup({ solve_group: IDENTITY, restarts: [RE], search_restarts: { mode: "ipop", max: 3 } });
assert.equal(p.group.restarts_count, 1);
assert.equal(p.group.restarts_mode, "ipop");
assert.equal(p.group.restarts_max, 3);
assert.equal(p.tips.restarts_mode, "run_detail.search_restarts.mode");
assert.equal(p.tips.restarts_count, "run.json.restarts");
p = runProvenanceGroup({ solve_group: IDENTITY, restarts: [RE] });
assert.equal(p.group.restarts_count, 1);
assert.ok(!("restarts_mode" in p.group) && !("restarts_max" in p.group));
// qd_algorithm arrives inside solve_group now (the raw qd block stays the atlas caption's source)
p = runProvenanceGroup({ solve_group: { backend: "beat_cuda", qd_algorithm: "cma_me" } });
assert.equal(p.group.qd_algorithm, "cma_me");
// every non-default fingerprint key reaches the badge group, tooltip naming solve_group.<key>:
p = runProvenanceGroup({ solve_group: { backend: "beat_cpu", cuda_fused: true, source_motion: "axial",
                       source_profile_alpha: 0.5, near_correction: true, solve_precision: "double",
                       rear_res_factor: 2, mesh_policy: "band_split_v1", band_edges_hz: [3000, 6000],
                       mounting: { type: "enclosure", depth_mm: 250 }, objective_version: 2,
                       qd_algorithm: "cma_me" } });
const rg2 = p.group;
assert.equal(rg2.backend, "beat_cpu");
assert.equal(rg2.cuda_fused, true);
assert.equal(rg2.source_motion, "axial");
assert.equal(rg2.source_profile_alpha, 0.5);
assert.equal(rg2.near_correction, true);
assert.equal(rg2.solve_precision, "double");
assert.equal(rg2.rear_res_factor, 2);
assert.equal(rg2.mesh_policy, "band_split_v1");
assert.deepEqual(rg2.band_edges_hz, [3000, 6000]);
assert.deepEqual(rg2.mounting, { type: "enclosure", depth_mm: 250 });
assert.equal(rg2.objective_version, 2);
assert.equal(rg2.qd_algorithm, "cma_me");
for (const k of Object.keys(rg2)) assert.ok(p.tips[k].startsWith("solve_group."), k);

// restart schedule card branches (honest empty states; nothing invented)
assert.equal(restartScheduleHtml({}, "R"), "");
assert.equal(restartScheduleHtml({ restart_dirs: [] }, "R"), "");
let c = restartScheduleHtml({ id: "R", restart_dirs: ["cma/restart_0"] }, "R");
assert.match(c, /Restart schedule/);
assert.match(c, /run\.json predates the restarts block/);
assert.match(c, /cma\/restart_0/);
assert.match(c, /\/runs\/R\/cma\//);
c = restartScheduleHtml({ id: "R", restarts: [RE] }, "R");
assert.match(c, /restart 0/);
assert.match(c, /popsize 10/);
assert.match(c, /σ0 0\.25/);
assert.match(c, /evals 59/);
assert.match(c, /stop budget/);
assert.match(c, /run\.json\.restarts/);              // rows named with their source path
assert.match(c, /carries no valid/);                 // absent search_restarts: the honest fallback
assert.ok(!c.includes("mode ipop"));                 // no invented mode/max
c = restartScheduleHtml({ id: "R", restarts: [RE], search_restarts: { mode: "ipop", max: 2 } }, "R");
assert.match(c, /mode ipop · max 2/);
assert.match(c, /search_restarts/);                  // header names its read path
assert.ok(!c.includes("carries no valid"));
assert.match(c, /run\.json\.restarts\[0\]\.popsize/);

// STEP chips: step_files stays the name list; inventory matched by name from step_files_detail
const INV = { tool: "tools/cad/multicell.py", tool_sha: "0123456789abcdef0123456789abcdef01234567",
              faces: [{ label: "driver", count: 1 }, { label: "wall", count: 9 }],
              solids: 2, closed: true, grid: ["3x3"] };
assert.equal(stepInvByName(undefined).size, 0);
assert.equal(stepInvByName(null).size, 0);
const mInv = stepInvByName([{ name: "horn_rank1_0001.step", inventory: INV },
                            { name: "plain.step", inventory: null }, { junk: 1 }]);
assert.equal(mInv.get("horn_rank1_0001.step"), INV);
assert.equal(mInv.get("plain.step"), null);
assert.equal(mInv.size, 2);
const plain = stepChipHtml("horn_rank1_0001.step", null, "R");
assert.ok(plain.includes('href="/runs/R/step/horn_rank1_0001.step"'), plain);
assert.match(plain, /↓ rank1/);
assert.ok(!plain.includes("driver="));               // no inventory: chip unchanged (silent absence)
const chip = stepChipHtml("horn_rank1_0001.step", INV, "R");
assert.match(chip, /3×3 STEP/);
assert.match(chip, /driver=1/);
assert.match(chip, /wall=9/);
assert.match(chip, /tool 01234567/);                 // short sha on the face
assert.ok(chip.includes('href="/runs/R/step/horn_rank1_0001.step"'), chip);
assert.ok(chip.includes("horn_rank1_0001.step.inventory.json"), chip);  // tooltip names the sidecar

// qd provenance caption: every known key, meanings as tooltips, honest absences
assert.equal(qdProvenanceCaption(null), "");
assert.equal(qdProvenanceCaption(undefined), "");
assert.equal(qdProvenanceCaption({}), "");
const QD = { algorithm: "cma_me", bins: [16, 16], coverage: 0.05078125,
             descriptors: { h: "mean_bw_h_deg", v: "mean_bw_v_deg" },
             descriptor_h_meaning: "mean of MetricSet.bw_h_deg",
             descriptor_v_meaning: "mean of MetricSet.bw_v_deg",
             non_cached: 60, occupied_bins: 13, ranges: { h: [0, 180], v: [0, 180] },
             total_bins: 256, total_evals: 60 };
const cap = qdProvenanceCaption(QD);
assert.match(cap, /atlas provenance \(run\.json\.qd\)/);
assert.match(cap, /cma_me/);
assert.match(cap, /coverage 13\/256 bins/);
assert.match(cap, /60 evaluations \(60 non-cached\)/);
assert.ok(cap.includes("mean of MetricSet.bw_h_deg"), cap);

// f11 caveat: the fixed sentence, ONLY when band_hi > f11 AND f11 is known; n_hz fallback named
assert.equal(f11CaveatHtml({ target: { band_hi_hz: 12000 } }), "");
assert.equal(f11CaveatHtml({ target: { band_hi_hz: 5500 }, best: { scalars: { f11_hz: 7914 } } }), "");
let note = f11CaveatHtml({ target: { band_hi_hz: 12000 }, best: { scalars: { f11_hz: 7914 } } });
assert.ok(note.includes("8–12 kHz compares GEOMETRIES, not drivers (above f11 the source is an idealized rigid cap)"), note);
assert.match(note, /7\.9 kHz/);
assert.ok(note.includes("best.scalars.f11_hz"), note);
assert.ok(note.includes("target.band_hi_hz"), note);
note = f11CaveatHtml({ target: { band_hi_hz: 12000 }, best: { scalars: { n_hz: 7914 } } });
assert.ok(note.includes("best.scalars.n_hz"), note);
assert.ok(!note.includes("f11_hz"), note);

console.log("PROV OK");
'''


def test_provenance_helpers_behave_offline(tmp_path):
    """Executes every badge/card/chip/caption branch of app.js's provenance layer for real:
    badges appear only for non-default keys with key-path tooltips, absences stay silent, the
    restart card has its honest empty states, STEP chips upgrade only with a matched sidecar
    inventory, and the f11 caveat needs BOTH numbers (C-1/C-2 view contract)."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not installed")   # same environment gate as test_gui.py's ES-module check
    script = tmp_path / "prov_under_test.mjs"
    script.write_text(_PROV_SCRIPT, encoding="utf-8")
    r = subprocess.run([node, str(script), str(APPJS)],
                       capture_output=True, text=True, cwd=str(tmp_path))
    assert "PROV OK" in r.stdout, f"node test failed:\nstdout: {r.stdout}\nstderr: {r.stderr}"


# ── Inline 3D + 3D time-lapse (owner requests, views only) ───────────────────────────────
# Run detail carries a lazy embedded 3D viewer for the best design (data-v3d tagged, disposed by
# route()'s marker sweep); the evolution page gains a lazy "3D" mode playing the frames3d
# improvement frames through view3d.js::init3dFrames. Source wiring here; the pure per-frame
# preparation runs for real in node below.

def test_inline_3d_and_disposal_are_wired():
    """The inline viewer exists below the wall cross-section, is lazy (fetch after render, staleness
    guard, failure note), carries the [data-v3d] marker, and route() sweeps every marked container."""
    src = APPJS.read_text(encoding="utf-8")
    # route() disposal: the marker sweep replaces the old single-id dispose
    assert 'document.querySelectorAll("[data-v3d]")' in src
    assert 'if (el._dispose3d) el._dispose3d();' in src
    assert re.search(r'querySelectorAll\("\[data-v3d\]"\)\.forEach\(el => \{ if \(el\._dispose3d\) el\._dispose3d\(\); \}\);', src)
    # the dedicated 3D page container is marked too (same sweep covers it)
    assert 'id="view3d-wrap" data-v3d' in src
    # inline viewer inside viewRunDetail: marked container + lazy loader
    assert 'id="inline-3d" data-v3d' in src
    assert 'api("/api/mesh/" + id + "/" + inlineHash)' in src      # fetched only after render
    assert "if (!inline3d.isConnected) return;" in src             # navigated away -> no scene
    assert "init3d(inline3d" in src                                # existing init3d, container-fitted
    assert "Could not load the mesh for this design" in src        # fetch failure -> honest note
    assert "No best design hashed yet" in src                      # no best design -> honest note
    # shadows default on, persisted with the SAME toggle key as the 3D page
    assert src.count('localStorage.getItem("hl-v3d-shadows")') >= 2
    assert "inline3d-shadows" in src
    # no second auto-loaded scene for the same design: the inline loader's start() serves both its
    # initial build and its shadow re-init, so app.js holds exactly three init3d call sites
    # (3D page: initial + shadow toggle; inline: start, shared by its initial build and toggle)
    assert src.count("init3d(") == 3


def test_evolution_3d_mode_is_wired():
    """The evolution page gains the lazy 3D toggle: frames3d fetched ONLY on use, improvements-only
    rule enforced both ways and disclosed, player container marked [data-v3d], honest unavailable
    branches, and view3d.js exports the frame player."""
    evo = (ROOT / "hornlab_search" / "gui" / "static" / "evolution.js").read_text(encoding="utf-8")
    v3d = (ROOT / "hornlab_search" / "gui" / "static" / "view3d.js").read_text(encoding="utf-8")
    # toggle + container + player wiring
    assert 'id="evo-3d"' in evo and 'id="evo-3d" data-v3d' in evo
    assert 'fetch("/api/evolution/" + encodeURIComponent(runId) + "/frames3d")' in evo
    assert "init3dFrames(cv, frames3d" in evo and 'import { init3dFrames } from "./view3d.js";' in evo
    # lazy: the fetch lives inside the enable path, not at view load
    assert "async function enable3d" in evo and "Loading 3D time-lapse" in evo
    # the single rule: one source-of-truth constant, disclosed 3+ places (toggle note, build note,
    # re-enable note, mode-select note)
    assert 'const RULE3D = "3D shows improvement frames only' in evo
    assert evo.count("RULE3D") >= 4
    assert 'mode !== "best"' in evo                     # checking 3D forces improvements-only
    assert "'every candidate' plays in 2D" in evo       # selecting every-candidate turns 3D off
    # honest branches: no frames / fetch failure / CDN failure all stay on 2D
    assert "R.available === false" in evo and "the 2D time-lapse stays." in evo
    assert "staying on the 2D panels." in evo
    assert 'if (!root.isConnected) return;' in evo      # navigation during the lazy build bails
    # view3d.js: exported player + disposal contract + lazy THREE (no top-level WebGL need)
    assert "export async function init3dFrames" in v3d
    assert "container._dispose3d = dispose" in v3d
    assert "mesh.geometry = built.geo;" in v3d          # hot-swap, no scene rebuild


# Node-exercisable core of the frame player (view3d.js top level stays DOM/THREE-free — the same
# direct-import pattern as tests/test_gui_mesh_quadrants.py; the WebGL scene assembly itself needs
# a browser, so prepareFrames is the executed part and the swap paths are source-wired above).
_FRAMES_SCRIPT = r'''
import { pathToFileURL } from "node:url";
import assert from "node:assert/strict";
const v3d = await import(pathToFileURL(process.argv[2]).href);
const { prepareFrames, init3dFrames, mirrorMesh } = v3d;
assert.equal(typeof prepareFrames, "function");
assert.equal(typeof init3dFrames, "function");          // exported; scene half needs a browser
assert.equal(typeof mirrorMesh, "function");            // the per-frame mirroring it reuses
// improvement frames as the reader keys them: eval number n, objective, hash, quadrants, decimation
const quarter = { n: 3, objective: 22.5, mesh_hash: "aaaa11112222", quadrants: "1",
  verts: [0, 0, 0, 1, 0, 0, 0, 1, 0], tris: [0, 1, 2], decimated: true, n_tris_full: 400 };
const half = { n: 7, objective: 18.4, quadrants: "14",
  verts: [0, 0, 0, 1, 0, 0, 0, 1, 0], tris: [0, 1, 2], decimated: false, n_tris_full: 3 };
const empty = { n: 9, objective: null, quadrants: "", verts: [], tris: [] };   // no mesh saved
const pf = prepareFrames([quarter, half, empty, null]);
assert.equal(pf.length, 2, "mesh-less frames are skipped, never fabricated");
// frame 1: quarter '1' -> 4 mirrored copies (12 verts); bounds extend symmetric to -1
assert.equal(pf[0].verts.length, 36);                   // 12 mirrored verts x 3 floats
assert.equal(pf[0].tris.length, 12);                    // 4 copies of the one triangle
assert.deepEqual([pf[0].bounds.x0, pf[0].bounds.x1, pf[0].bounds.y0, pf[0].bounds.y1,
                  pf[0].bounds.z0, pf[0].bounds.z1], [-1, 1, -1, 1, 0, 0]);
assert.equal(pf[0].n, 3);                               // eval identity carried for playback mapping
assert.equal(pf[0].objective, 22.5);
assert.equal(pf[0].mesh_hash, "aaaa11112222");
assert.equal(pf[0].decimated, true);                    // disclosure flag rides the frame
assert.equal(pf[0].n_tris_full, 400);
// frame 2: half '14' -> 2 copies, one reflection = winding flip, exactly like mirrorMesh
assert.equal(pf[1].verts.length, 18);                   // 6 mirrored verts x 3 floats
assert.deepEqual([...pf[1].tris], [0, 1, 2, 3, 5, 4]);
assert.equal(pf[1].decimated, false);
assert.equal(pf[1].objective, 18.4);
// union bounds across frames (the player's fixed camera) is derivable, and garbage never throws
const union = [-Math.min(pf[0].bounds.x0, pf[1].bounds.x0), Math.max(pf[0].bounds.x1, pf[1].bounds.x1)];
assert.deepEqual(union, [1, 1]);
assert.deepEqual(prepareFrames(undefined), []);
assert.deepEqual(prepareFrames({}), []);
assert.deepEqual(prepareFrames([{ n: 1, verts: [0, 0, 0], tris: [0, 0, 0] }]).length, 0);  // degenerate
console.log("FRAMES OK");
'''


def test_3d_frames_prepare_offline(tmp_path):
    """Executes the pure per-frame core of init3dFrames: mirrorMesh per frame (quarter/half handedness
    bounds), the honest skips (no mesh saved), the decimation disclosure flags and the eval-identity
    carry that the playback mapping keys on."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not installed")
    script = tmp_path / "frames_under_test.mjs"
    script.write_text(_FRAMES_SCRIPT, encoding="utf-8")
    r = subprocess.run([node, str(script), str(ROOT / "hornlab_search" / "gui" / "static" / "view3d.js")],
                       capture_output=True, text=True, cwd=str(tmp_path))
    assert "FRAMES OK" in r.stdout, f"node test failed:\nstdout: {r.stdout}\nstderr: {r.stderr}"