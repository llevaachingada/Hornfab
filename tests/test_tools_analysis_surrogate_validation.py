"""S7 surrogate_validation.py: fixture rows only, no solver, no torch."""
from __future__ import annotations

import json

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
    rows[-1]["x"] = [9.0, 9.0]   # far outside the training support
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




