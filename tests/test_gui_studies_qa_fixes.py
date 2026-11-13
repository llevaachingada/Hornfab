"""Regressions found in the 2026-11-13 S10/B6 headless visual QA of the Studies workspace.

1. ``studies.js``: ``RegExp.test(undefined)`` is true, so panels without a run id rendered
   "Open run" / "Open verification" links to ``#/run/undefined``.
2. ``data_studies.bounded_preview``: a real snapshot artifact (>50 catalog configs) made the
   Data panel fail with HTTP 400 "list exceeds view limit"; the server now shows an
   explicitly truncated preview while ``build_study_view`` keeps refusing raw oversize data.
"""
from pathlib import Path
import json
import subprocess

import pytest

from hornlab_search.gui.data_studies import MAX_BYTES, MAX_ITEMS, bounded_preview, build_study_view

MODULE = Path(__file__).resolve().parents[1] / "hornlab_search/gui/static/studies.js"


def test_missing_run_ids_render_no_run_links(tmp_path):
    script = tmp_path / "links.mjs"
    script.write_text(r'''
import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
const src = await readFile(process.argv[2], "utf8");
const m = await import("data:text/javascript;base64," + Buffer.from(src).toString("base64"));
assert.equal(m.studyRunLink(undefined, "study1"), null);
assert.equal(m.studyRunLink(null, "study1"), null);
assert.equal(m.studyRunLink("run1", undefined), null);
assert.throws(() => m.studyRoute(undefined));
const study = {id:"study1", revision:1, status:"draft"};
const html = m.renderStudyPanel(study, {phase:"propose", status:"unknown", revision:1, data:{}});
assert.ok(!html.includes("#/run/undefined"));
assert.ok(!html.includes("Open run"));
const linked = m.renderStudyPanel(study, {phase:"execute", status:"unknown", revision:1, data:{run_id:"r1"}});
assert.ok(linked.includes("#/run/r1?"));
console.log("links ok");
''', encoding="utf-8")
    result = subprocess.run(["node", str(script), str(MODULE)], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "links ok" in result.stdout


def test_bounded_preview_marks_every_truncation_and_fits_the_panel():
    content = {"cohort": {"catalog": {"configs": [f"cfg{i}" for i in range(120)]}},
               "ids": [f"{i:064x}" for i in range(400)],
               "wide": {f"k{i}": i for i in range(70)},
               "note": "x" * 5000}
    preview, truncated = bounded_preview(content)
    assert truncated == 4
    configs = preview["cohort"]["catalog"]["configs"]
    assert len(configs) == MAX_ITEMS and configs[:3] == ["cfg0", "cfg1", "cfg2"]
    assert configs[-1] == "... 71 more items not shown"
    assert preview["wide"]["_truncated_keys"] == 21 and len(preview["wide"]) == MAX_ITEMS
    assert preview["note"].endswith("(1000 more characters not shown)")
    assert len(json.dumps(preview).encode()) <= MAX_BYTES
    study = {"id": "s", "revision": 1}
    panel = build_study_view(study, "data", {"revision": 1, "status": "unknown", "data": preview})
    assert panel.status == "unknown"
    # The adapter contract is unchanged: raw oversize data is still refused.
    with pytest.raises(ValueError):
        build_study_view(study, "data", {"revision": 1, "status": "unknown", "data": content})


def test_bounded_preview_leaves_small_artifacts_untouched():
    content = {"a": [1, 2, 3], "b": {"c": "d"}, "e": 1.5}
    assert bounded_preview(content) == (content, 0)


def test_bounded_preview_shrinks_caps_to_fit_the_byte_budget():
    content = {f"k{i}": [f"{'v' * 3000}{j}" for j in range(60)] for i in range(60)}
    preview, truncated = bounded_preview(content)
    assert truncated > 0
    assert len(json.dumps(preview).encode()) <= MAX_BYTES


def test_decide_panel_reads_recorded_decisions_honestly():
    from hornlab_search.gui.data_studies import decision_panel_artifact

    study = {"id": "s", "revision": 2}
    assert decision_panel_artifact(study, {"decisions": []}) is None
    record = {"decisions": [{"seq": i, "revision": 1, "outcome": "reject", "rationale": "r"}
                            for i in range(25)]
              + [{"seq": 30, "revision": 2, "outcome": "inconclusive", "rationale": "why"}],
              "artifacts": [{"kind": "proposal", "sha256": "a" * 64, "revision": 2}],
              "children": []}
    artifact = decision_panel_artifact(study, record)
    panel = build_study_view(study, "decide", artifact)
    assert panel.status == "partial"  # never "ready": not a validated decision artifact
    assert len(panel.data["recorded_decisions"]) == 20
    assert panel.data["recorded_decisions"][-1]["outcome"] == "inconclusive"
    assert panel.data["current_revision_decided"] is True
    assert any("latest 20 of 26" in r for r in panel.reasons)
