"""Agent-bench scorer: pure-Python grader for agent answer fixtures.

No model calls, no network, no GPU, no solver imports.

Usage:
    python tests/agent_bench/scorer.py <answers.json>

answers.json schema:
    { "<id>": {"text": "<answer text>", "cited": ["<path>", ...]}, ... }

where <id> is the integer case id as a string key.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Case loading
# ---------------------------------------------------------------------------

def load_cases(directory: str | Path) -> list[dict]:
    """Load all case_NN.yaml files from *directory*, sorted by id."""
    try:
        import yaml  # type: ignore[import]
    except ImportError:
        raise ImportError("pyyaml is required: pip install pyyaml")

    directory = Path(directory)
    cases = []
    for path in sorted(directory.glob("case_*.yaml")):
        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        cases.append(data)
    cases.sort(key=lambda c: int(c["id"]))
    return cases


# ---------------------------------------------------------------------------
# Single-case grading
# ---------------------------------------------------------------------------

_DEFERRAL_RE = re.compile(
    r"\b(defer|cannot verify|insufficient evidence|refuse|incomplete)\b",
    re.IGNORECASE,
)


def _ci_search(pattern: str, text: str) -> bool:
    """Case-insensitive regex search."""
    try:
        return bool(re.search(pattern, text, re.IGNORECASE))
    except re.error:
        return bool(re.search(re.escape(pattern), text, re.IGNORECASE))


def grade(case: dict, answer_text: str, cited_paths: list[str]) -> dict:
    """Grade one answer against *case*.

    Returns::

        {
            "passed": bool,
            "reasons": list[str],           # why it passed or the first failure
            "case_id": int,
            "deferral_detected": bool,
        }
    """
    ak = case["answer_key"]
    defer_ok: bool = bool(ak.get("defer_ok", False))
    must_include: list[str] = ak.get("must_include") or []
    must_not_include: list[str] = ak.get("must_not_include") or []
    must_cite_any: list[str] = ak.get("must_cite_any") or []

    reasons: list[str] = []
    failures: list[str] = []

    # Check for explicit deferral
    deferral_detected = bool(_DEFERRAL_RE.search(answer_text))

    # Grounding check: at least one must_cite_any path must appear in cited_paths
    # or be mentioned anywhere in the answer text
    if must_cite_any:
        cited_set = set(cited_paths or [])
        # Normalise to forward slashes and strip leading ./ for loose matching
        def _norm(p: str) -> str:
            return p.replace("\\", "/").lstrip("./")

        norm_cited = {_norm(p) for p in cited_set}
        norm_answer_lower = answer_text.lower()

        grounded = False
        for path in must_cite_any:
            np = _norm(path)
            # Match if the normalised path appears in cited_paths or in answer text
            if np in norm_cited:
                grounded = True
                break
            if np.lower() in norm_answer_lower:
                grounded = True
                break
            # Partial basename match (e.g. "scalar_v9.py" matches "hornlab_search/objective/scalar_v9.py")
            basename = np.split("/")[-1].lower()
            if basename and basename in norm_answer_lower:
                grounded = True
                break
        if not grounded:
            failures.append(
                f"grounding: answer does not cite any of {must_cite_any}"
            )

    # If defer_ok and deferral detected: relax must_include to only the verdict
    if defer_ok and deferral_detected:
        # Only check that the deferral is present (already detected) and grounding
        reasons.append("deferral accepted (defer_ok=true)")
        if not failures:
            return {
                "passed": True,
                "reasons": reasons,
                "case_id": case["id"],
                "deferral_detected": True,
            }
        else:
            return {
                "passed": False,
                "reasons": reasons + failures,
                "case_id": case["id"],
                "deferral_detected": True,
            }

    # must_include checks
    for pattern in must_include:
        if not _ci_search(pattern, answer_text):
            failures.append(f"missing required phrase: {pattern!r}")

    # must_not_include checks
    for pattern in must_not_include:
        if _ci_search(pattern, answer_text):
            failures.append(f"contains forbidden phrase: {pattern!r}")

    passed = len(failures) == 0
    if passed:
        reasons.append("all checks passed")
    return {
        "passed": passed,
        "reasons": reasons + failures if not passed else reasons,
        "case_id": case["id"],
        "deferral_detected": deferral_detected,
    }


# ---------------------------------------------------------------------------
# Batch grading
# ---------------------------------------------------------------------------

def grade_run(
    cases: list[dict],
    answers: dict[str, dict[str, Any]],
) -> dict:
    """Grade all answers in *answers* against *cases*.

    ``answers`` maps str(id) -> {"text": ..., "cited": [...]}.

    Returns a summary dict::

        {
            "total_cases": int,
            "total_answered": int,
            "total_passed": int,
            "per_case": {id: grade_result, ...},
        }
    """
    case_map = {str(c["id"]): c for c in cases}
    per_case: dict[str, dict] = {}
    total_passed = 0
    total_answered = 0

    for sid, answer_data in answers.items():
        if sid not in case_map:
            per_case[sid] = {
                "passed": False,
                "reasons": [f"no case with id={sid}"],
                "case_id": sid,
                "deferral_detected": False,
            }
            continue
        total_answered += 1
        text = answer_data.get("text", "")
        cited = answer_data.get("cited", [])
        result = grade(case_map[sid], text, cited)
        per_case[sid] = result
        if result["passed"]:
            total_passed += 1

    return {
        "total_cases": len(cases),
        "total_answered": total_answered,
        "total_passed": total_passed,
        "per_case": per_case,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(
            "Usage: python tests/agent_bench/scorer.py <answers.json>",
            file=sys.stderr,
        )
        return 2

    answers_path = Path(argv[1])
    if not answers_path.exists():
        print(f"Error: {answers_path} not found", file=sys.stderr)
        return 1

    # Locate cases dir relative to this file
    cases_dir = Path(__file__).parent / "cases"
    if not cases_dir.is_dir():
        print(f"Error: cases dir not found at {cases_dir}", file=sys.stderr)
        return 1

    cases = load_cases(cases_dir)
    with open(answers_path, encoding="utf-8") as fh:
        answers = json.load(fh)

    summary = grade_run(cases, answers)
    print(json.dumps(summary, indent=2))
    return 0 if summary["total_passed"] == summary["total_answered"] else 1


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
