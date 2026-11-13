"""S7 surrogate_validation.py: fixture rows only, no solver, no torch."""
from __future__ import annotations

import json

import numpy as np
import pytest

from test_tools_analysis_common import load_tool

sv = load_tool("surrogate_validation")


def _rows(n=40, version=1, dup_hash_at=None):
    rows = []
    for i in range(n):
        x = [((i * 7) % n) / n, ((i * 3) % n) / n]
        rows.append({"row_id": f"r{i}", "design_hash": f"h{i}", "t": i, "objective_version": version,
                     "x": x, "ok": i % 9 != 0, "j": 1 + (x[0] - .3) ** 2 + (x[1] - .6) ** 2,
                     "metrics": {"ripple_db": 0.5 + x[0]}})
    if dup_hash_at is not None:
        rows[-1]["design_hash"] = rows[dup_hash_at]["design_hash"]
    return rows


def _v4_rows(n=40):
    rows = _rows(n=n, version=4)
    spec = {
        "brief": "native__ath_core_v4",
        "brief_hash": "brief-hash-v4",
        "objective_version": 4,
        "target": {"coverage_h_deg": 60.0, "coverage_v_deg": 40.0,
                   "band_lo_hz": 500.0, "band_hi_hz": 10000.0},
        "weights": {"cov": 1.0, "rip": 1.0, "diag": 0.5, "load": 0.25},
        "objective_block": {
            "version": 4,
            "tolerances": {"cov": 100.0, "rip": 3.0, "diag": 100.0, "load": 1.0},
            "cov_narrow_ratio": 2.0,
            "cov_below_f0": "mask",
            "diag_reference": "round",
        },
        "terms_keys": ["cov", "rip", "diag", "load", "total"],
        "score_schema_version": 1,
    }
    identity = sv._canonical_hash(spec)
    for i, row in enumerate(rows):
        row["score_spec"] = json.loads(json.dumps(spec))
        row["score_identity"] = identity
        if row["ok"]:
            row["label_evidence"] = {
                "source": "stored_evaluation",
                "status": "exact_complete",
                "complete": True,
                "objective_version": 4,
                "metrics_complete": True,
                "response_complete": True,
                "balloon_complete": True,
                "throat_impedance_complete": True,
                "score_id": f"per-design-score-{i}",
                "j": row["j"],
            }
    return rows


def _write(tmp_path, rows, name="rows.jsonl"):
    p = tmp_path / name
    p.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return p


def test_chronological_split_has_no_future_or_same_geometry_leak(tmp_path):
    out = sv.run(_write(tmp_path, _rows(dup_hash_at=2)), tmp_path / "o")
    assert out["status"] == "ok" and out["advisory_only"] and not out["changes_defaults"]
    c = out["split"]["checks"]
    assert c["no_future_rows_in_train"] and c["shared_design_hashes"] == 0
    assert c["same_geometry_removed_from_test"] == 1
    assert "r39" not in out["split"]["test_ids"]
    reg = out["evaluation"]["regression"]["targets"]["j"]
    assert reg["direction"] == "minimize" and 0 <= reg["topk_recall"] <= 1
    assert "ripple_db" in out["evaluation"]["regression"]["targets"]
    assert out["evaluation"]["feasibility"]["reliability_bins"]


def test_unsupported_or_mixed_versions_and_missing_inputs_refuse(tmp_path):
    assert sv.run(_write(tmp_path, _rows(version=4)), tmp_path / "a")["reason"] == "unsupported_objective_version"
    mixed = _rows(); mixed[0]["objective_version"] = 4
    assert sv.run(_write(tmp_path, mixed, "m.jsonl"), tmp_path / "b")["reason"] == "mixed_objective_versions"
    bad = _rows(); bad[3]["x"] = [float("nan"), 0.1]
    p = tmp_path / "bad.json"; p.write_text(json.dumps(bad).replace("NaN", "null"))
    assert sv.run(p, tmp_path / "c")["reason"] == "missing_inputs"


def test_v4_stored_label_mode_uses_common_spec_not_per_design_score_id(tmp_path):
    rows = _v4_rows()
    assert len({r["label_evidence"]["score_id"] for r in rows if r["ok"]}) > 1
    out = sv.run(_write(tmp_path, rows, "v4.jsonl"), tmp_path / "v4",
                 advisory_stored_j=True)
    assert out["status"] == "ok"
    assert out["objective_version"] == 4
    assert out["validation_mode"] == "advisory_stored_j"
    assert out["score_identity"] == rows[0]["score_identity"]
    assert out["advisory_only"] and not out["changes_defaults"]


def test_v4_stored_label_mode_refuses_mixed_brief_or_tolerance(tmp_path):
    for field in ("brief", "tolerance"):
        rows = _v4_rows()
        if field == "brief":
            rows[-1]["score_spec"]["brief_hash"] = "different-brief"
        else:
            rows[-1]["score_spec"]["objective_block"]["tolerances"]["cov"] = 99.0
        rows[-1]["score_identity"] = sv._canonical_hash(rows[-1]["score_spec"])
        out = sv.run(_write(tmp_path, rows, f"mixed-{field}.jsonl"),
                     tmp_path / f"mixed-{field}", advisory_stored_j=True)
        assert out["status"] == "refused"
        assert out["reason"] == "mixed_score_identities"


def test_v4_stored_label_mode_refuses_unproven_or_incomplete_label(tmp_path):
    rows = _v4_rows()
    first_ok = next(r for r in rows if r["ok"])
    first_ok["label_evidence"]["source"] = "synthetic_prediction"
    out = sv.run(_write(tmp_path, rows, "synthetic.jsonl"), tmp_path / "synthetic",
                 advisory_stored_j=True)
    assert out["reason"] == "incomplete_label_evidence"

    rows = _v4_rows()
    first_ok = next(r for r in rows if r["ok"])
    first_ok["label_evidence"]["throat_impedance_complete"] = False
    out = sv.run(_write(tmp_path, rows, "no-z.jsonl"), tmp_path / "no-z",
                 advisory_stored_j=True)
    assert out["reason"] == "incomplete_label_evidence"


def test_v4_stored_label_mode_checks_declared_identity_and_label_value(tmp_path):
    rows = _v4_rows()
    rows[0]["score_identity"] = "not-the-canonical-hash"
    out = sv.run(_write(tmp_path, rows, "bad-id.jsonl"), tmp_path / "bad-id",
                 advisory_stored_j=True)
    assert out["reason"] == "score_identity_mismatch"

    rows = _v4_rows()
    first_ok = next(r for r in rows if r["ok"])
    first_ok["label_evidence"]["j"] += 1.0
    out = sv.run(_write(tmp_path, rows, "bad-j.jsonl"), tmp_path / "bad-j",
                 advisory_stored_j=True)
    assert out["reason"] == "label_value_mismatch"


def test_resume_reuses_complete_result_and_ood_falls_back(tmp_path):
    rows = _rows()
    for i, row in enumerate(rows):
        row["x"] = [i / 200, i / 200]
    rows[-1]["x"] = [0.99, 0.99]   # in the unit cube, far outside training support
    p = _write(tmp_path, rows)
    first = sv.run(p, tmp_path / "o")
    assert first["evaluation"]["n_ood_fallback"] >= 1 and first["resumed"] is False
    again = sv.run(p, tmp_path / "o")
    assert again["resumed"] is True and again["input_key"] == first["input_key"]


def test_proposals_are_hypotheses_with_mixed_roles(tmp_path):
    pool = [{"candidate_id": f"c{i}", "x": [i / 10, 1 - i / 10]} for i in range(10)]
    out = sv.run(_write(tmp_path, _rows()), tmp_path / "o", pool_path=_write(tmp_path, pool, "pool.jsonl"))
    props = out["proposals"]["proposals"]
    assert {p["role"] for p in props} == {"exploit", "uncertainty", "diversity"}
    assert all(p["measured"] is False and p["status"] == "hypothesis" for p in props)


@pytest.mark.parametrize("mutate", [
    lambda rows: rows[0].__setitem__("ok", 1),
    lambda rows: rows[0].__setitem__("t", float("inf")),
    lambda rows: rows[0].__setitem__("x", [True, 0.2]),
    lambda rows: rows[0].__setitem__("x", [-0.1, 0.2]),
    lambda rows: rows[0].__setitem__("row_id", ""),
    lambda rows: rows[0].__setitem__("design_hash", ""),
    lambda rows: rows[1].__setitem__("row_id", rows[0]["row_id"]),
    lambda rows: rows[1]["metrics"].__setitem__("ripple_db", float("nan")),
])
def test_strict_row_contract_refuses_malformed_values(tmp_path, mutate):
    rows = _rows()
    mutate(rows)
    out = sv.run(_write(tmp_path, rows), tmp_path / "out")
    assert out["status"] == "refused"
    assert out["reason"] in {"missing_inputs", "duplicate_row_id"}


def test_degenerate_chronological_split_refuses_instead_of_crashing(tmp_path):
    rows = _rows()
    for row in rows:
        row["t"] = 1.0
    out = sv.run(_write(tmp_path, rows), tmp_path / "out")
    assert out["status"] == "refused"
    assert out["reason"] == "empty_chronological_split"


def test_spearman_uses_average_ranks_for_ties():
    assert sv._spearman(np.array([1.0, 1.0, 2.0, 3.0]),
                        np.array([4.0, 4.0, 5.0, 6.0])) == pytest.approx(1.0)
    # Swapping values only within a tie must not alter the coefficient.
    assert np.array_equal(sv._rankdata_average([1.0, 1.0, 2.0]), [0.5, 0.5, 2.0])


def test_regression_support_uses_successful_training_rows_only():
    rows = []
    xs = [0.00, 0.05, 0.10, 0.80, 0.90, 1.00, 0.82, 0.88, 0.94]
    oks = [True, True, True, False, False, False, True, True, True]
    for i, (x, ok) in enumerate(zip(xs, oks)):
        rows.append({"row_id": f"r{i}", "design_hash": f"h{i}", "t": i,
                     "objective_version": 1, "x": [x], "ok": ok,
                     "j": (x * x if ok else None), "metrics": {"m": x} if ok else {}})
    split = {"train": list(range(6)), "test": list(range(6, 9))}
    evaluation, _ = sv._fit_eval(rows, split, ["m"], k=2, topk=2)
    assert evaluation["n_ood_fallback"] == 0  # failures make feasibility support look local
    assert evaluation["regression"]["status"] == "insufficient_data"
    assert evaluation["regression"]["n_ood_fallback"] == 3


def test_ood_proposal_has_no_claimed_prediction_but_keeps_diversity_role():
    rows = [{"row_id": f"r{i}", "design_hash": f"h{i}", "t": i,
             "objective_version": 1, "x": [x], "ok": True, "j": 1 + x,
             "metrics": {}} for i, x in enumerate((0.0, 0.05, 0.1))]
    split = {"train": [0, 1, 2], "test": []}
    pool = [{"candidate_id": "near", "x": [0.05]},
            {"candidate_id": "far-a", "x": [0.8]},
            {"candidate_id": "far-b", "x": [1.0]}]
    result = sv.propose(rows, split, pool, n=3, k=2)
    ood = [p for p in result["proposals"] if not p["in_support"]]
    assert ood and any(p["role"] == "diversity" for p in ood)
    assert all(p["predicted_j"] is None and p["uncertainty"] is None for p in ood)


def test_live_output_root_is_refused_before_directory_creation(tmp_path):
    forbidden = sv.REPO / "runs" / "s7-test-must-not-exist"
    assert not forbidden.exists()
    out = sv.run(_write(tmp_path, _rows()), forbidden)
    assert out["status"] == "refused" and out["reason"] == "forbidden_output"
    assert out["path"] is None and not forbidden.exists()




