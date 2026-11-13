"""Group E view pure-helper guards, executed for real through node (test_gui_views_l2.py style).
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
APPJS = ROOT / "hornlab_search" / "gui" / "static" / "app.js"

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
globalThis.location = { hash: "#/elites" };
globalThis.requestAnimationFrame = () => 0;
globalThis.localStorage = { getItem: () => null, setItem() {}, removeItem() {} };
globalThis.fetch = () => Promise.reject(new Error("offline shim"));

const app = await import(pathToFileURL(process.argv[2]).href);
const { lanesPanelHtml, verdictChipHtml, eliteGateChips, cpuRunningCardHtml, cpuLaneCardHtml,
        laneChipsHtml } = app;

// E.2 lanes panel: pure over /api/lanes, empty/absent payload renders nothing
assert.equal(lanesPanelHtml(null), "");
assert.equal(lanesPanelHtml({}), "");
const ok = lanesPanelHtml({ alert: false, lanes: [{
  lane: "gpu", lock: { pid: 1, alive: true },
  job: { name: "g1_running", started: "2026-11-11T09:00:06" },
  run: { id: "20261111T000000Z-screen-aaaaaa", n_rows: 12, best_j: 4.5, newest_row_age_min: 2.0 },
  alert: null, last_job: null }] });
assert.ok(ok.includes("GPU") && ok.includes("g1_running"), ok);
assert.ok(ok.includes("#/run/20261111T000000Z-screen-aaaaaa"), ok);
assert.ok(ok.includes("pill good"), "a fresh row lane is ok");
const alert = lanesPanelHtml({ alert: true, alert_lanes: ["gpu"], lanes: [{
  lane: "gpu", lock: null, job: { name: "g1_running" }, run: { n_rows: 12, newest_row_age_min: 34.1 },
  alert: { job: "g1_running", age_min: 34.1, reason: "newest row 34.1 min old while job g1_running is running" } }] });
assert.ok(alert.includes("alert error") && alert.includes("ALERT") && alert.includes("34.1 min"), alert);

// verdict chips per the seed-variance schema
assert.equal(verdictChipHtml("a-beats-b"), '<span class="pill good">A beats B</span>');
assert.equal(verdictChipHtml("b-beats-a"), '<span class="pill good">B beats A</span>');
assert.ok(verdictChipHtml("indicative").includes("indicative") && verdictChipHtml("indicative").includes("&lt; 5 seeds"));
assert.ok(verdictChipHtml(null).includes("muted"));
assert.ok(verdictChipHtml("no-verdict").includes("no-verdict"));

// elite gate chips: pass/fail strictly from the audit columns
const chips = eliteGateChips({ gates: { throat: true, load: false } },
                             { throat: "round throat", load: "loading" });
assert.ok(chips.includes("round throat") && chips.includes('pill good'), chips);
assert.ok(chips.includes("loading fail") && chips.includes('pill bad'), chips);
assert.equal(eliteGateChips({ gates: {} }, {}), "");

// CPU lane running card: parity with the GPU current-run card, never inventing numbers
const cpuSearch = {
  cpu_lock: { pid: 4321, alive: true, command: "hornlab-search search --backend bempp" },
  cpu_job: { name: "cpu_screen_20261113", started: "2026-11-13T09:50:00",
             target: 120, run_id: "20261113T095000Z-screen-bb" },
  cpu_current: {
    kind: "search", run_id: "20261113T095000Z-screen-bb", mode: "screen", n: 42,
    last: "2026-11-13T09:58:00",
    session: { n: 42, budget: 120, resumed: false, n_resumes: 0, started: "2026-11-13T09:50:00" },
    rate_per_h: 40, eta_min: 12, best_j: 3.4, seed_j: 5.1, session_best_j: 3.4,
    failures_session: 2, backend: "bempp" } };
const sc = cpuRunningCardHtml(cpuSearch);
assert.ok(sc.includes("progress-bar"), sc);
assert.ok(sc.includes("this session"), sc);
assert.ok(sc.includes("/h"), sc);
assert.ok(sc.includes("min left"), sc);
assert.ok(sc.includes("Open run") && sc.includes("#/run/20261113T095000Z-screen-bb"), sc);
assert.ok(!sc.includes("verified"), sc);
assert.ok(!sc.includes("no verify output yet"), sc);
const scCompact = cpuLaneCardHtml(cpuSearch);
assert.ok(scCompact.includes("evals") && !scCompact.includes("verified"), scCompact);
assert.ok(scCompact.includes("42 / 120") && scCompact.includes("(35%)"), scCompact);

const cpuVerify = {
  cpu_lock: { pid: 99, alive: true, command: "hornlab-search verify --backend bempp" },
  cpu_job: { name: "cpu_verify_20261113", started: "2026-11-13T09:55:00",
             kind: "verify", target: 4, run_id: "20261113T095500Z-verify-cc" },
  cpu_current: {
    kind: "verify", run_id: "20261113T095500Z-verify-cc", mode: "verify", n: 2,
    last: "2026-11-13T09:59:00",
    session: { n: 2, budget: 4, resumed: false, n_resumes: 0, started: "2026-11-13T09:55:00" },
    rate_per_h: null, eta_min: null, best_j: 2.7, seed_j: null, session_best_j: 2.7,
    failures_session: 0, backend: "bempp" } };
const vc = cpuRunningCardHtml(cpuVerify);
assert.ok(vc.includes("2 / 4 verified"), vc);
assert.ok(vc.includes("progress-bar"), vc);
assert.ok(vc.includes("Best score"), vc);
assert.ok(!vc.includes("Started score"), vc);
const vcCompact = cpuLaneCardHtml(cpuVerify);
assert.ok(vcCompact.includes("2 / 4 verified"), vcCompact);

// lock alive, no first evaluation row yet: honest starting card, no progress bar
const cpuStarting = {
  cpu_lock: { pid: 77, alive: true, command: "hornlab-search verify" },
  cpu_job: { name: "cpu_verify_warm", started: new Date(Date.now() - 90000).toISOString(), target: 4 } };
const starting = cpuRunningCardHtml(cpuStarting);
assert.ok(starting.includes("waiting for the first"), starting);
assert.ok(starting.includes("PID 77"), starting);
assert.ok(!starting.includes("progress-wrap"), starting);

// idle: Home keeps a Free card, Status renders nothing
const idleHome = cpuRunningCardHtml({ cpu_lock: null, cpu_job: null }, { home: true });
assert.ok(idleHome.includes("Free"), idleHome);
assert.ok(!idleHome.includes("progress-wrap"), idleHome);
assert.equal(cpuRunningCardHtml({ cpu_lock: null, cpu_job: null }), "");

// older-server shape: no session -> n vs cpu_job.target; no rate/ETA is invented
const cpuOld = {
  cpu_lock: { pid: 5, alive: true, command: "hornlab-search search" },
  cpu_job: { name: "cpu_old_screen", target: 120 },
  cpu_current: { n: 12, last: "2026-11-13T09:59:00", rate_per_h: null, eta_min: null,
                 best_j: 4.2, seed_j: 5.0 } };
const old = cpuRunningCardHtml(cpuOld);
assert.ok(old.includes("width:10%"), old);
assert.ok(old.includes("–"), old);
assert.ok(!old.includes("/h"), old);

// E.2 lanes panel: rate/ETA append only when the payload carries them
const withSpeed = lanesPanelHtml({ alert: false, lanes: [{
  lane: "cpu", lock: { pid: 9, alive: true }, job: null,
  run: { id: "r", n_rows: 20, best_j: 3, newest_row_age_min: 1, rate_per_h: 40, eta_min: 12 },
  alert: null, last_job: null }] });
assert.ok(withSpeed.includes("40/h") && withSpeed.includes("ETA 12 min"), withSpeed);

// sidebar lane chip: /api/lanes run carries n_rows (and optional session_n), never `n`
const chip = laneChipsHtml({ lanes: [{
  lane: "cpu", lock: { pid: 9, alive: true }, job: { name: "cpu_screen" }, last_job: null,
  run: { session_n: 42, n_rows: 60, rate_per_h: 40, eta_min: 12 } }] });
assert.ok(chip.includes("42 evals"), chip);
assert.ok(!chip.includes("60 evals"), chip);
assert.ok(chip.includes("40/h") && chip.includes("ETA 12 min"), chip);
assert.ok(chip.includes("CPU"), chip);
const chipBare = laneChipsHtml({ lanes: [{
  lane: "cpu", lock: null, job: null, last_job: null, run: null }] });
assert.ok(!chipBare.includes("evals") && !chipBare.includes("/h") && !chipBare.includes("ETA"), chipBare);
assert.ok(chipBare.includes("CPU"), chipBare);

console.log("E GUARD OK");
'''


def test_group_e_view_helpers_guard(tmp_path: Path):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not installed")
    script = tmp_path / "guard_under_test.mjs"
    script.write_text(_GUARD_SCRIPT, encoding="utf-8")
    r = subprocess.run([node, str(script), str(APPJS)],
                       capture_output=True, text=True, cwd=str(tmp_path))
    assert "E GUARD OK" in r.stdout, f"node test failed:\nstdout: {r.stdout}\nstderr: {r.stderr}"
