"""Prepare and execute one BO arm, refusing changed cohort files and failed preflight."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser()
    for name in ("root", "cohort", "policy", "seed"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--scores-sha256")
    parser.add_argument("--catalog-sha256")
    parser.add_argument("--refresh-cohort", action="store_true")
    parser.add_argument("--budget-profile", default="comparison-80x2")
    parser.add_argument("--prepare-only", action="store_true")
    identity = parser.add_mutually_exclusive_group(required=True)
    identity.add_argument("--task")
    identity.add_argument("--config")
    args = parser.parse_args()
    cohort = REPO / args.cohort
    if args.refresh_cohort:
        if not args.config or args.scores_sha256 or args.catalog_sha256 or cohort.exists():
            print("refusing refresh: provide --config and a new cohort directory, without hashes", file=sys.stderr)
            return 2
        result = subprocess.call([sys.executable, "-m", "tools.analysis.study_cohort", "--config", args.config,
                                  "--dataset", "dataset", "--out", args.cohort, "--limit", "1024"], cwd=REPO)
        if result:
            return result
    else:
        if not args.scores_sha256 or not args.catalog_sha256:
            print("refusing frozen cohort without both hashes", file=sys.stderr)
            return 2
        for filename, expected in (("offline_scores.json", args.scores_sha256), ("catalog.csv", args.catalog_sha256)):
            path = cohort / filename
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected.lower():
                print(f"refusing changed or missing cohort: {path}", file=sys.stderr, flush=True)
                return 2
    prep = [sys.executable, "tools/bo_compare/prepare_study.py", "--root", args.root,
            "--cohort", args.cohort, "--policy", args.policy,
            "--seed", args.seed, "--label", Path(args.root).name, "--min-rows", "100",
            "--budget-profile", args.budget_profile, "--deadline-hours", "6"]
    prep.extend(["--task", args.task] if args.task else ["--config", args.config])
    proc = subprocess.run(prep, cwd=REPO, text=True, stdout=subprocess.PIPE)
    print(proc.stdout, end="", flush=True)
    if proc.returncode:
        return proc.returncode
    try:
        result = json.loads(proc.stdout.strip().splitlines()[-1])
        if result["preflight"]["status"] != "ok" or any(x != "ok" for x in result["steps"].values()):
            raise ValueError("preparation or execution capability is not ok")
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        print(f"refusing execution: {exc}", file=sys.stderr, flush=True)
        return 3
    if args.prepare_only:
        return 0
    return subprocess.call([sys.executable, "-m", "hornlab_search.studies.cli", "run", "--root", args.root,
                            "--package", "package.json", "--execute", "--project-root", str(REPO)], cwd=REPO)


if __name__ == "__main__":
    sys.exit(main())
