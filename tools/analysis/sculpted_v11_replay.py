"""Replay a saved sculpted BEM response under the home-900 V11 briefs."""
import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from hornlab_search.objective.replay import load_brief_context, _dispatch
from hornlab_search.objective.scalar_v11 import resolve_v11_weights
from hornlab_search.search.evaluate import metrics_from_response
from hornlab_search.solve.cache import load_response

BRIEFS = ROOT / "examples/briefs/home_xo900_2026-11-20"
PRIMARY = BRIEFS / "room_landscape_80x50_900_hf1440_v11cd.yaml"
ADVISORY = BRIEFS / "room_landscape_80x50_900_hf1440_v11cd_packaging_advisory.yaml"
STAGED = BRIEFS / "room_landscape_80x50_900_hf1440_v11cd_staged_exp.yaml"
RESPONSE = ROOT / "runs/nights/sculpted_home900_2026-11-21/R2/response.npz"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def evaluate(response, path):
    brief = load_brief_context(path)
    if brief.objective_version != 11:
        raise ValueError(f"{path}: expected objective version 11")
    metrics = metrics_from_response(response, brief.target)
    score, terms = _dispatch(11, metrics, response, brief.target, brief.weights, brief.objective_params)
    weights = resolve_v11_weights(brief.weights, brief.objective_params)
    weighted = {key: weights[key] * terms[key] for key in weights}
    required = ("cd_lw", "cd_di_std", "cd_nacc", "offaxis_smooth")
    if not all(key in weighted and math.isfinite(weighted[key]) for key in required):
        raise ValueError("missing or non-finite CD contributions")
    if not math.isfinite(score) or not math.isclose(sum(weighted.values()), score, abs_tol=1e-10):
        raise ValueError("weighted contributions do not reproduce score")
    status = {0.0: "balloon", 1.0: "cuts_fallback", 2.0: "unmeasurable"}.get(terms["cd_status_code"])
    if status is None:
        raise ValueError("unknown CD status")
    return {"brief": str(path.relative_to(ROOT)), "brief_sha256": digest(path), "name": brief.name,
            "objective_version": 11, "J": score, "weighted": weighted,
            "terms": terms, "cd_status": status}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--response", type=Path, default=RESPONSE)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    response = load_response(args.response)
    primary, advisory, staged = [evaluate(response, path) for path in (PRIMARY, ADVISORY, STAGED)]
    if primary["J"] != advisory["J"] or primary["terms"] != advisory["terms"]:
        raise ValueError("primary and advisory scores differ")
    result = {"response": str(args.response), "response_sha256": digest(args.response),
              "backend": response.backend, "n_dof": response.n_dof,
              "frequencies_hz": response.freqs_hz.tolist(),
              "balloon_available": response.balloon_dirs is not None and response.spl_balloon_db is not None,
              "complex_pressure_saved": response.p_h is not None and response.p_v is not None and response.p_balloon is not None,
              "primary": primary, "packaging_advisory": advisory, "staged_secondary": staged,
              "exact_score_and_terms_parity": True}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Stored response J={primary['J']:.12f} status={primary['cd_status']} advisory parity exact")
    print("weighted CD terms:", {key: primary["weighted"][key] for key in
          ("cd_lw", "cd_di_std", "cd_nacc", "offaxis_smooth")})
    print("complex pressure saved:", result["complex_pressure_saved"])


if __name__ == "__main__":
    main()

