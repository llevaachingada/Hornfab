"""Validate the PRODUCTION warm-start path for every config referenced by the live night.

Read-only, CPU. Prints config -> OK (mean hash, sigma) or the WarmStartError/ConfigError.
This is the exact check the search CLI performs before solving (cma.py raises ConfigError).
"""
from pathlib import Path

import yaml

from hornlab_search.config import load_config
from hornlab_search.design.space import DesignSpace
from hornlab_search.search import warmstart

ROOT = Path(__file__).resolve().parents[1]
night = yaml.safe_load((ROOT / "runs/nights/fable_scout40_2026-11-19.yaml").read_text(encoding="utf-8"))

seen = set()
for job in night["jobs"]:
    cfg_rel = job.get("config")
    if not cfg_rel or cfg_rel in seen:
        continue
    seen.add(cfg_rel)
    path = ROOT / cfg_rel
    try:
        cfg = load_config(path)
    except Exception as exc:  # noqa: BLE001
        print(f"{job['id']}: CONFIG LOAD FAILED: {type(exc).__name__}: {exc}")
        continue
    ws = getattr(cfg.search, "warm_start", None)
    if not ws or not ws.get("from_runs"):
        print(f"{job['id']}: no warm_start")
        continue
    try:
        space = DesignSpace.from_config(cfg)
        design, record = warmstart.mean_and_sigma(cfg, space)
        print(f"{job['id']}: OK mean={record['mean_design_hash']} J={record['mean_objective']:.6g} "
              f"sigma0={record['sigma0']:.4g} from={record['from_runs']}")
    except Exception as exc:  # noqa: BLE001
        print(f"{job['id']}: WARM START REFUSED: {type(exc).__name__}: {exc}")
