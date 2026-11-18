# Agent benchmark fixtures

Source: `docs/knowledge/AGENT_BENCHMARK_SPEC_2026-11-18.md` (WP-K1).

## What these fixtures are

Each YAML file under `cases/` encodes one probe question, the repo paths the agent is
allowed to read, and an answer key the scorer uses to grade the response. The benchmark
is purely structural: no model calls, no GPU, no network. A human (or CI) grades a saved
answer file against the keys.

## Arms

| Arm | Context |
|-----|---------|
| Baseline | Current agent + skills |
| Treatment | Same agent + skills + `docs/knowledge/contracts/` files |

Both arms use the same model, same permissions, same repo SHA, and the same frozen
prompt from each case YAML.

## Case schema

```yaml
id: <int>
title: <str>
prompt: <str>
allowed_read_paths:
  - <repo-relative path>   # the agent may read these (and only these)
answer_key:
  verdict: <str>            # human-readable summary of the correct answer
  must_include:             # list of case-insensitive regexes (all must match)
    - <pattern>
  must_not_include:         # list of regexes (none may match)
    - <pattern>
  must_cite_any:            # list of paths; at least one must appear in cited or answer text
    - <path>
  defer_ok: <bool>          # if true, a grounded deferral also passes
  key_source: repo|spec_only
  evidence:                 # human-readable pointers to the decisive lines
    - <file:section>
  negative_control: <tag|null>
```

## Saving agent answers

After running an agent against a case, save its response as:

```json
{
  "<case_id>": {
    "text": "<full agent response text>",
    "cited": ["<path cited by agent>", ...]
  }
}
```

Then grade with:

```
python tests/agent_bench/scorer.py <answers.json>
```

The scorer prints a JSON summary to stdout and exits 0 if all answered cases pass,
non-zero otherwise.

## Scorer API

```python
from tests.agent_bench.scorer import load_cases, grade, grade_run

cases = load_cases("tests/agent_bench/cases")
result = grade(cases[0], answer_text="...", cited_paths=["docs/..."])
# result = {"passed": bool, "reasons": [...], "case_id": int, "deferral_detected": bool}

summary = grade_run(cases, answers_dict)
# summary = {"total_cases": 24, "total_answered": N, "total_passed": M, "per_case": {...}}
```

## Grading rules

A case passes if and only if:

1. **Grounding**: at least one `must_cite_any` path appears in `cited` or answer text
   (basename match also accepted).
2. **Must-include**: every `must_include` regex matches the answer text
   (case-insensitive).
3. **Must-not-include**: no `must_not_include` regex matches the answer text.

If `defer_ok: true` and the answer contains a deferral marker
(`defer`, `cannot verify`, `insufficient evidence`, `refuse`, or `incomplete`),
grounding is still required but must-include is relaxed to the deferral itself.

## Adoption gate

The treatment arm must beat the baseline on correctness **without** a regression on
cases 15 and 16 (cost and over-activation). If it does not win, shrink the contracts
rather than adding more agents.

## Negative controls embedded in cases

| Tag | Case |
|-----|------|
| `inactive_conditional_knob` | 2 |
| `best_under_v7_not_v9` | 5 |
| `mesh_fidelity_shift` | 9 |
| `parallel_geometric_derivatives` | 20 |
| `parent_novelty_off` | 21 |
| `large_geom_weak_acoustic` | 23 |
| `small_geom_strong_acoustic` | 24 |

## Running the CI-safe pytest

```
PYTHONPATH=<worktree> python -m pytest tests/test_agent_bench.py -q -p no:cacheprovider
```

No model calls, no GPU, no network. All tests complete in under a second.
