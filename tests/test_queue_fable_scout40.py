"""The 2026-11-19 SCOUT40 night after the geometry pass: budgets, timeouts, brief groups, and every queued
config the offline checker can build passes tools/analysis/meridian_sanity.py (native mesher families are
checked on the owner box)."""
import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
NIGHT = ROOT / "docs/queue/fable_scout40_2026-11-19.yaml"
sys.path.insert(0, str(ROOT / "tools/analysis"))


def _cfg_path(job):
    if job["kind"] == "search":
        return ROOT / job["config"]
    argv = job["argv"]
    return ROOT / argv[argv.index("--config") + 1]


def test_scout40_jobs_budgets_groups_and_geometry():
    import meridian_sanity as M
    jobs = yaml.safe_load(NIGHT.read_text(encoding="utf-8"))["jobs"]
    ids = [j["id"] for j in jobs]
    assert len(ids) == 16 and len(set(ids)) == 16
    assert ids[:2] == ["fv2__klangfilm_hv_core", "fv2__rolled_clean"]
    for gone in ("s40__vt_v1", "s40__klangfilm_lame_c200w", "s40__klangfilm_lame_hv_stage_a", "s40__rf_section_axial_v7"):
        assert gone not in ids
    smooth = 0
    for j in jobs:
        p = _cfg_path(j)
        assert p.is_file(), p
        raw = yaml.safe_load(p.read_text(encoding="utf-8"))
        brief = str(raw["brief_file"])
        if j["id"].startswith("fv2__"):
            assert "v10" in brief
        else:
            budget = j["budget"] if j["kind"] == "search" else int(j["argv"][j["argv"].index("--budget") + 1])
            assert budget == 40 and j["timeout_s"] == 3600
            if "smooth" in brief:
                smooth += 1
                assert "warm_start" not in raw["search"]
        try:
            q = M.grid_for_config(p)
        except Exception:            # native mesher family or warm start needing runs/: owner box
            continue
        assert M.check_grid(q)["ok"], j["id"]
    assert smooth == 4
