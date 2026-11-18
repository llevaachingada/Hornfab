"""CI-safe tests for the agent-bench fixtures.

No model calls, no GPU, no network.  Pure Python + pyyaml.

Run:
    PYTHONPATH=<worktree> python -m pytest tests/test_agent_bench.py -q -p no:cacheprovider
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Import scorer without requiring agent_bench/ to have an __init__.py.
# tests/ is on sys.path (pytest prepend mode); agent_bench/ is a plain dir.
# ---------------------------------------------------------------------------
_BENCH = Path(__file__).parent / "agent_bench"
if str(_BENCH) not in sys.path:
    sys.path.insert(0, str(_BENCH))

from scorer import grade, grade_run, load_cases  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
CASES_DIR = REPO / "tests" / "agent_bench" / "cases"
ANSWERS_DIR = REPO / "tests" / "agent_bench" / "answers"

# Required schema keys that every case must carry
REQUIRED_TOP_KEYS = {"id", "title", "prompt", "allowed_read_paths", "answer_key"}
REQUIRED_AK_KEYS = {
    "verdict",
    "must_include",
    "must_not_include",
    "must_cite_any",
    "defer_ok",
    "key_source",
}

EXPECTED_NEGATIVE_CONTROLS = {
    "inactive_conditional_knob",
    "best_under_v7_not_v9",
    "mesh_fidelity_shift",
    "parallel_geometric_derivatives",
    "parent_novelty_off",
    "large_geom_weak_acoustic",
    "small_geom_strong_acoustic",
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def all_cases():
    return load_cases(CASES_DIR)


@pytest.fixture(scope="module")
def sample_good():
    path = ANSWERS_DIR / "sample_good.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def sample_bad():
    path = ANSWERS_DIR / "sample_bad.json"
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Structure tests
# ---------------------------------------------------------------------------


def test_exactly_24_cases(all_cases):
    assert len(all_cases) == 24, f"Expected 24 cases, got {len(all_cases)}"


def test_case_ids_are_1_through_24(all_cases):
    ids = sorted(c["id"] for c in all_cases)
    assert ids == list(range(1, 25)), f"Case IDs mismatch: {ids}"


def test_case_ids_are_unique(all_cases):
    ids = [c["id"] for c in all_cases]
    assert len(ids) == len(set(ids)), "Duplicate case IDs found"


@pytest.mark.parametrize("case", pytest.param(None, id="loaded-at-collection"))
def test_required_top_keys(all_cases, case):
    for c in all_cases:
        missing = REQUIRED_TOP_KEYS - set(c.keys())
        assert not missing, f"Case {c['id']} missing top-level keys: {missing}"


@pytest.mark.parametrize("case", pytest.param(None, id="loaded-at-collection"))
def test_required_answer_key_fields(all_cases, case):
    for c in all_cases:
        ak = c.get("answer_key", {})
        missing = REQUIRED_AK_KEYS - set(ak.keys())
        assert not missing, f"Case {c['id']} answer_key missing fields: {missing}"


def test_case_top_keys_all_cases(all_cases):
    for c in all_cases:
        missing = REQUIRED_TOP_KEYS - set(c.keys())
        assert not missing, f"Case {c['id']} missing top-level keys: {missing}"


def test_answer_key_fields_all_cases(all_cases):
    for c in all_cases:
        ak = c.get("answer_key", {})
        missing = REQUIRED_AK_KEYS - set(ak.keys())
        assert not missing, f"Case {c['id']} answer_key missing: {missing}"


# ---------------------------------------------------------------------------
# Path-existence tests
# ---------------------------------------------------------------------------


def test_allowed_read_paths_exist(all_cases):
    """Every allowed_read_path must resolve to an existing file or glob match."""
    missing = []
    for c in all_cases:
        for p in (c.get("allowed_read_paths") or []):
            path = REPO / p
            if not path.exists() and not list(REPO.glob(p)):
                missing.append(f"case {c['id']}: {p}")
    assert not missing, "Missing allowed_read_paths:\n" + "\n".join(missing)


def test_must_cite_any_paths_exist(all_cases):
    """Every must_cite_any path must resolve to an existing file or glob match."""
    missing = []
    for c in all_cases:
        for p in (c["answer_key"].get("must_cite_any") or []):
            path = REPO / p
            if not path.exists() and not list(REPO.glob(p)):
                missing.append(f"case {c['id']}: {p}")
    assert not missing, "Missing must_cite_any paths:\n" + "\n".join(missing)


# ---------------------------------------------------------------------------
# Regex-compilation tests
# ---------------------------------------------------------------------------


def test_must_include_regexes_compile(all_cases):
    errors = []
    for c in all_cases:
        for pat in (c["answer_key"].get("must_include") or []):
            try:
                re.compile(pat, re.IGNORECASE)
            except re.error as exc:
                errors.append(f"case {c['id']} must_include {pat!r}: {exc}")
    assert not errors, "Bad regexes:\n" + "\n".join(errors)


def test_must_not_include_regexes_compile(all_cases):
    errors = []
    for c in all_cases:
        for pat in (c["answer_key"].get("must_not_include") or []):
            try:
                re.compile(pat, re.IGNORECASE)
            except re.error as exc:
                errors.append(f"case {c['id']} must_not_include {pat!r}: {exc}")
    assert not errors, "Bad regexes:\n" + "\n".join(errors)


# ---------------------------------------------------------------------------
# Negative-control test
# ---------------------------------------------------------------------------


def test_all_seven_negative_controls_embedded(all_cases):
    """All 7 negative controls from the spec must appear in at least one case."""
    found = {
        c["answer_key"].get("negative_control")
        for c in all_cases
        if c["answer_key"].get("negative_control")
    }
    missing = EXPECTED_NEGATIVE_CONTROLS - found
    assert not missing, f"Negative controls not embedded: {missing}"


def test_no_unexpected_negative_controls(all_cases):
    """Negative controls must only be values from the spec (or null)."""
    allowed = EXPECTED_NEGATIVE_CONTROLS | {None}
    unexpected = []
    for c in all_cases:
        nc = c["answer_key"].get("negative_control")
        if nc not in allowed:
            unexpected.append(f"case {c['id']}: {nc!r}")
    assert not unexpected, f"Unexpected negative_control values: {unexpected}"


# ---------------------------------------------------------------------------
# Scorer smoke tests
# ---------------------------------------------------------------------------


def test_sample_good_all_pass(all_cases, sample_good):
    summary = grade_run(all_cases, sample_good)
    failures = {
        sid: res
        for sid, res in summary["per_case"].items()
        if not res["passed"]
    }
    assert not failures, (
        "sample_good.json cases that should pass but did not:\n"
        + json.dumps(failures, indent=2)
    )


def test_sample_bad_all_fail(all_cases, sample_bad):
    summary = grade_run(all_cases, sample_bad)
    passes = {
        sid: res
        for sid, res in summary["per_case"].items()
        if res["passed"]
    }
    assert not passes, (
        "sample_bad.json cases that should fail but passed:\n"
        + json.dumps(passes, indent=2)
    )


def test_sample_bad_case1_missing_phrase(all_cases, sample_bad):
    """Case 1 bad: fails because 'smootherstep' is absent."""
    result = grade(
        next(c for c in all_cases if c["id"] == 1),
        sample_bad["1"]["text"],
        sample_bad["1"].get("cited", []),
    )
    assert not result["passed"]
    reasons = " ".join(result["reasons"])
    assert "smootherstep" in reasons.lower() or "missing" in reasons.lower()


def test_sample_bad_case4_forbidden_phrase(all_cases, sample_bad):
    """Case 4 bad: fails because 'physically impossible' is present."""
    result = grade(
        next(c for c in all_cases if c["id"] == 4),
        sample_bad["4"]["text"],
        sample_bad["4"].get("cited", []),
    )
    assert not result["passed"]
    reasons = " ".join(result["reasons"])
    assert "forbidden" in reasons.lower() or "physically impossible" in reasons.lower()


def test_sample_bad_case6_no_citation(all_cases, sample_bad):
    """Case 6 bad: fails because no grounding citation is provided."""
    result = grade(
        next(c for c in all_cases if c["id"] == 6),
        sample_bad["6"]["text"],
        sample_bad["6"].get("cited", []),
    )
    assert not result["passed"]
    reasons = " ".join(result["reasons"])
    assert "grounding" in reasons.lower() or "cite" in reasons.lower()


def test_sample_bad_case14_grounding_on_deferral(all_cases, sample_bad):
    """Case 14 bad: a deferral without grounding fails even though defer_ok=True."""
    result = grade(
        next(c for c in all_cases if c["id"] == 14),
        sample_bad["14"]["text"],
        sample_bad["14"].get("cited", []),
    )
    assert not result["passed"]
    assert result["deferral_detected"]
    reasons = " ".join(result["reasons"])
    assert "grounding" in reasons.lower() or "cite" in reasons.lower()


# ---------------------------------------------------------------------------
# Determinism test
# ---------------------------------------------------------------------------


def test_scorer_is_deterministic(all_cases, sample_good, sample_bad):
    """Grading the same input twice must return the same result."""
    combined = {**sample_good, **sample_bad}
    r1 = grade_run(all_cases, combined)
    r2 = grade_run(all_cases, combined)
    for sid in r1["per_case"]:
        assert r1["per_case"][sid]["passed"] == r2["per_case"][sid]["passed"], (
            f"Non-deterministic result for case {sid}"
        )
