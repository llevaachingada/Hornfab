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