"""Offline (no solve) smoke of the tool's real-object path: load a run config, build the metadata
run dir, and build an EvalContext. Nothing is meshed or solved."""
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools" / "night_queue"))

import fidelity_pairs as fp
from hornlab_search.config import load_config
from hornlab_search.search import rundir
from hornlab_search.search.evaluate import make_context

cfg = load_config(REPO / "runs" / "20261116T130335Z-screen-ab4fb9" / "config.yaml")
with tempfile.TemporaryDirectory() as tmp:
    d = Path(tmp) / "run__verify"
    d.mkdir(parents=True)
    fp._write_mode_meta(d, cfg, REPO / "runs" / "20261116T130335Z-screen-ab4fb9", "verify", rundir)
    meta = (d / "run.json").read_text(encoding="utf-8")
    print("run.json keys:", sorted(__import__("json").loads(meta)))
    print("config snapshot:", (d / "config.yaml").is_file())
    ctx = make_context(cfg, None, ndjson=d / "search.ndjson")
    print("ctx target band:", ctx.provenance, "objective_version:", ctx.objective_version)
    print("solve_cache_root (no cache_dir):", ctx.solve_cache_root)
