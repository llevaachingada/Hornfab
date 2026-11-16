"""Warm-start a sequential CMA search from a finished BO study (preflight first)."""
from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
PYTHON = REPO / ".venv" / "Scripts" / "python.exe"
CLI = REPO / ".venv" / "Scripts" / "hornlab-search.exe"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study-root", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--budget", type=int, default=80)
    parser.add_argument("--out-config", required=True)
    parser.add_argument("--run-root", default=str(REPO / "runs"), help="directory holding study-<package-prefix> runs")
    args = parser.parse_args(argv)
    if args.budget < 1:
        parser.error("--budget must be positive")
    try:
        config_path = Path(args.config).resolve()
        output = Path(args.out_config).resolve()
        source = output.parent / (output.stem + "_study_source")
        if output.exists() or source.exists() or output == config_path:
            raise ValueError("output config or source snapshot already exists; choose fresh paths")
        package = json.loads((Path(args.study_root) / "package.json").read_text(encoding="utf-8"))
        package_id = package.get("package_id", "")
        if not isinstance(package_id, str) or not re.fullmatch(r"[0-9a-f]{64}", package_id):
            raise ValueError("invalid package_id")
        screen = Path(args.run_root).resolve() / ("study-" + package_id[:16]) / "screen"
        run = json.loads((screen / "run.json").read_text(encoding="utf-8"))
        if run.get("package_id") != package_id or not run.get("finished_utc"):
            raise ValueError("study screen is not finished or does not match package")
        rows_path = screen / "search.ndjson"
        rows = []
        for line in rows_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        valid = [r for r in rows if r.get("ok") is True and isinstance(r.get("params"), dict)
                 and isinstance(r.get("objective"), (int, float))
                 and not isinstance(r.get("objective"), bool) and math.isfinite(r["objective"])
                 and r["objective"] < 900]
        if not valid:
            raise ValueError("study screen has no valid scored rows")
        # The study snapshot has no CMA run.json config/family; construct a separate,
        # provenance-preserving adapter from its saved config without touching the study.
        sys.path.insert(0, str(REPO))
        from hornlab_search.config import _load_yaml_extends, _resolve_path, load_config
        cfg = _load_yaml_extends(config_path)
        resolved = load_config(config_path).raw
        prior = yaml.safe_load((screen / "config.yaml").read_text(encoding="utf-8"))
        if not isinstance(cfg, dict) or not isinstance(prior, dict):
            raise ValueError("config and study config must be mappings")
        for key in ("name", "family", "brief_file", "brief", "objective", "bounds"):
            if resolved.get(key) != prior.get(key):
                raise ValueError(f"study/config mismatch in {key}")
        extra_runs = []
        run_root = Path(args.run_root).resolve()
        for candidate in sorted(run_root.glob("*-screen-*"), key=lambda p: p.name, reverse=True):
            try:
                candidate_meta = json.loads((candidate / "run.json").read_text(encoding="utf-8"))
                candidate_cfg = candidate_meta.get("config") or {}
                if candidate_meta.get("config_name") != cfg.get("name"):
                    continue
                if any(candidate_cfg.get(k) != resolved.get(k) for k in
                       ("name", "family", "brief_file", "brief", "objective", "bounds")):
                    continue
                candidate_rows = [json.loads(line) for line in
                                  (candidate / "search.ndjson").read_text(encoding="utf-8").splitlines()
                                  if line.strip()]
                usable = [r for r in candidate_rows if r.get("ok") is True
                          and isinstance(r.get("params"), dict)
                          and isinstance(r.get("objective"), (int, float))
                          and not isinstance(r.get("objective"), bool)
                          and math.isfinite(r["objective"]) and r["objective"] < 900]
                if usable:
                    extra_runs.append((candidate, candidate_meta, candidate_cfg, usable))
                if len(extra_runs) >= 5:
                    break
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                continue
        brief = None
        if cfg.get("brief_file"):
            brief = _resolve_path(cfg["brief_file"], config_path.parent, REPO).resolve()
            if not brief.is_file():
                raise ValueError(f"brief file not found: {brief}")
            cfg["brief_file"] = str(brief)
            prior["brief_file"] = str(brief)
        search = cfg.setdefault("search", {})
        if not isinstance(search, dict):
            raise ValueError("search block must be a mapping")
        source_paths = [source] + [output.parent / (output.stem + "_cma_source_" + str(i))
                                   for i in range(len(extra_runs))]
        if any(path.exists() for path in source_paths[1:]):
            raise ValueError("CMA source snapshot already exists; choose fresh paths")
        best = min(valid + [row for _, _, _, usable in extra_runs for row in usable],
                   key=lambda row: row["objective"])
        cfg["seed_params"] = best["params"]
        if isinstance(cfg.get("generator"), dict):
            cfg["generator"]["seed_policy"] = "explicit"
        search.update({"budget": args.budget, "sigma0": 0.10, "budget_counts": "valid", "max_attempts": 180,
                       "warm_start": {"from_runs": [str(path) for path in source_paths], "top_k": 10,
                                      "sigma_from_spread": True}})
        output.parent.mkdir(parents=True, exist_ok=True)
        source.mkdir()
        (source / "search.ndjson").write_text(
            "".join(json.dumps(row, allow_nan=False) + "\n" for row in valid), encoding="utf-8")
        adapted = {**run, "family": prior.get("family"), "config": prior,
                   "source_study_screen": str(screen), "adapter": "completed-bo-screen-v1",
                   "source_rows": len(rows), "included_valid_rows": len(valid)}
        (source / "run.json").write_text(json.dumps(adapted, indent=2), encoding="utf-8")
        for path, (origin, meta, frozen, usable) in zip(source_paths[1:], extra_runs):
            path.mkdir()
            if brief is not None:
                frozen["brief_file"] = str(brief)
            meta.update({"config": frozen, "source_cma_screen": str(origin),
                         "adapter": "completed-cma-screen-v1"})
            (path / "run.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
            (path / "search.ndjson").write_text(
                "".join(json.dumps(row, allow_nan=False) + "\n" for row in usable), encoding="utf-8")
        output.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
        preflight = [str(PYTHON), str(REPO / "tools" / "search_preflight.py"), str(output),
                     "--from-runs", *map(str, source_paths), "--json"]
        for sigma in (0.10, 0.075, 0.05):
            search["sigma0"] = sigma
            output.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
            result = subprocess.run(preflight, cwd=REPO, check=False, capture_output=True, text=True)
            if result.stdout:
                print(result.stdout, flush=True)
            if result.stderr:
                print(result.stderr, file=sys.stderr, flush=True)
            if result.returncode:
                print(f"refusing: preflight returned {result.returncode}", file=sys.stderr, flush=True)
                return result.returncode
            try:
                report = json.loads(result.stdout)
                warnings = report["warnings"]
                if not isinstance(warnings, list):
                    raise ValueError("warnings must be a list")
                low_hits = any(isinstance(w, dict) and w.get("code") == "low_hits" for w in warnings)
            except (ValueError, KeyError, TypeError) as exc:
                raise ValueError(f"invalid preflight JSON: {exc}") from exc
            if not low_hits:
                break
        else:
            print("refusing: low_hits persists at minimum sigma 0.05", file=sys.stderr, flush=True)
            return 2
        command = [str(CLI), "search", "--config", str(output), "--mode", "screen", "--budget",
                   str(args.budget), "--cma-seed", str(args.seed), "--runs-dir", str(Path(args.run_root).resolve())]
        return subprocess.run(command, cwd=REPO, check=False).returncode
    except (OSError, ValueError, TypeError, json.JSONDecodeError, yaml.YAMLError) as exc:
        print(f"refusing CMA refinement: {exc}", file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
