"""Stage 5 (2026-11-17): geometric identifiability, feasibility and space proposals."""
import json
from pathlib import Path

import numpy as np
import pytest
import yaml

from hornlab_search.config import load_config
from hornlab_search.design.space import DesignSpace
from hornlab_search.geometry import sensitivity as S

ROOT = Path(__file__).resolve().parents[1]
GRID = ROOT / "examples" / "typologies" / "grid_ellipse_mod.yaml"     # 2 knobs, ~5 ms records


def _cfg(path=GRID, mutate=None, tmp_path=None):
    if mutate is None:
        return load_config(path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    raw["brief_file"] = str((path.parent / raw["brief_file"]).resolve())
    mutate(raw)
    p = tmp_path / "c.yaml"
    p.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return load_config(p)


def test_jacobian_columns_match_a_direct_difference():
    cfg = _cfg()
    sp = DesignSpace.from_config(cfg)
    x0 = S.seed_unit(sp)
    J = S.jacobian(sp, cfg, x0, h=0.02)
    k = 0
    xa, xb = x0.copy(), x0.copy()
    xa[k] = max(0.0, x0[k] - 0.02)
    xb[k] = min(1.0, x0[k] + 0.02)
    ra, _ = S.record_at(sp, cfg, xa)
    rb, _ = S.record_at(sp, cfg, xb)
    direct = (rb.inner - ra.inner).reshape(-1) / (xb[k] - xa[k])
    assert np.allclose(J.surface[:, k], direct)
    assert J.col_rms_mm[k] > S.INACTIVE_MM and J.col_max_mm[k] >= J.col_rms_mm[k]


def test_mouth_radius_knob_drives_mouth_width_descriptor():
    cfg = _cfg()
    sp = DesignSpace.from_config(cfg)
    J = S.jacobian(sp, cfg, S.seed_unit(sp))
    i = J.keys.index("h_rm_mm")
    b = sp.bounds["h_rm_mm"]
    dw = J.desc[S.DESCRIPTOR_KEYS.index("mouth_width_mm"), i]
    assert dw == pytest.approx(2.0 * (b.hi - b.lo), rel=0.05)      # width = 2 x mouth radius


def test_analyze_space_labels_and_effective_dimension():
    cfg = _cfg()
    sp = DesignSpace.from_config(cfg)
    r = S.analyze_space(sp, cfg, n_points=3)
    assert r["legal_points"] == r["n_points"] == 4
    assert all(v["label"] == "active" for v in r["knobs"].values())
    assert r["effective_dimension"]["searched"] == 2
    assert set(r["feasible_from_seed"]) == set(r["keys"])


def test_box_feasibility_and_margin_model_on_a_tight_envelope(tmp_path):
    cfg = _cfg()
    sp = DesignSpace.from_config(cfg)
    env = dict(cfg.brief["envelope"])
    cfg.brief["envelope"] = {**env, "max_mouth_w_mm": 300.0, "max_mouth_h_mm": 300.0}
    box = S.box_feasibility(sp, cfg, n=32)
    assert box["counts"]["outside"] > 0
    rates = box["per_knob"]["h_rm_mm"]["bad_rate_by_slice"]
    assert rates[-1] > rates[0]                                   # big mouths are the problem
    m = S.margin_model(sp, cfg, n=32)
    assert m["available"] and m["gradient"]["h_rm_mm"]["mm_per_range"] < 0 and m["r2"] > 0.6


def test_sigma_curve_is_monotone_enough_and_zero_at_tiny_sigma():
    cfg = _cfg()
    sp = DesignSpace.from_config(cfg)
    cfg.brief["envelope"] = {**cfg.brief["envelope"], "max_mouth_w_mm": 300.0, "max_mouth_h_mm": 300.0}
    c = S.sigma_refusal_curve(sp, cfg, sigmas=(0.01, 0.5), n=24)
    assert c["0.01"]["bad_rate"] <= c["0.50"]["bad_rate"]


def test_greedy_links_have_no_chains_and_pick_the_weaker_follower():
    class _B:
        def __init__(self, lo, hi):
            self.lo, self.hi = lo, hi

    class _Space:
        bounds = {"a": _B(0, 1), "b": _B(0, 2), "c": _B(0, 1)}
        seed = None
        def normalize(self, d): return np.array([0.5, 0.5, 0.5])

    base = np.array([1.0, 2.0, 3.0, 4.0])
    J = S.PointJacobian(x=np.zeros(3), keys=["a", "b", "c"],
                        surface=np.c_[base, 0.5 * base, 0.25 * base + 1e-3],
                        desc=np.zeros((len(S.DESCRIPTOR_KEYS), 3)),
                        col_rms_mm=np.array([3.0, 1.5, 0.75]), col_max_mm=np.ones(3))
    links = S.propose_links([J, J], ["a", "b", "c"], _Space())
    followers = {l["follower"] for l in links}
    leaders = {l["from"] for l in links}
    assert not followers & leaders                                # one level only
    assert "a" not in followers                                   # the strongest knob leads
    b = next(l for l in links if l["follower"] in ("b", "c"))
    assert b["median_abs_cos"] > 0.99


def test_space_card_and_proposal_round_trip(tmp_path):
    from tools.analysis import space_card, space_propose
    out = tmp_path / "cards"
    assert space_card.main(["--config", str(GRID), "--out", str(out), "--points", "2",
                            "--box", "8", "--sigma-n", "4"]) == 0
    card = json.loads((out / "grid_ellipse_mod.json").read_text())
    assert card["recommendations"] and card["geometry"]["legal_points"] >= 1
    card["recommendations"].append({"knob": "L_mm", "action": "rebound", "why": "test",
                                    "proposal": {"lower_hi_to_unit": 0.99}})
    (out / "grid_ellipse_mod.json").write_text(json.dumps(card))
    assert space_propose.main(["--card", str(out / "grid_ellipse_mod.json"), "--out",
                               str(tmp_path / "prop"), "--box", "4", "--sigma-n", "4"]) == 0
    rep = json.loads((tmp_path / "prop" / "grid_ellipse_mod__space_v1.report.json").read_text())
    assert rep["after"]["searched"] == 2 and "seed_shift_max_mm" in rep["after"]
    assert "__space_v1" not in (ROOT / "examples" / "typologies" / "grid_ellipse_mod.yaml").read_text()


def test_apply_card_links_fixes_and_skips_chains():
    from tools.analysis.space_propose import apply_card
    raw = {"seed_params": {"x": 1.0}, "bounds": {k: {"lo": 0, "hi": 10} for k in "abcx"}, "search": {"sigma0": 0.25}}
    card = {"recommendations": [
        {"knob": "b", "action": "link", "proposal": {"from": "a", "scale": 2, "offset": 1}},
        {"knob": "a", "action": "link", "proposal": {"from": "c", "scale": 1, "offset": 0}},
        {"knob": "c", "action": "fix", "why": "inert"},
        {"knob": "x", "action": "rebound", "why": "edge", "proposal": {"lower_hi_to_unit": 0.05}},
        {"knob": "*", "action": "sigma0", "why": "", "proposal": {"max_safe_sigma0": 0.1}}]}
    new, notes = apply_card(raw, card)
    assert new["search"]["links"] == {"b": {"from": "a", "scale": 2.0, "offset": 1.0}}
    assert new["bounds"]["c"]["search"] is False and new["search"]["sigma0"] == 0.1
    assert new["bounds"]["x"]["hi"] == 10                         # seed 1.0 above the cut: skipped
    assert any("skipped link a" in n for n in notes) and raw["search"]["sigma0"] == 0.25
