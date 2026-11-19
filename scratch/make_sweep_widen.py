"""Build temporary config copies sweeping the bound-pinned fc keys, for tools/shape_check.py.

Read-only on the repo configs; writes throwaway copies under scratch/sweep_widen_2026-11-19/.
"""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "scratch" / "sweep_widen_2026-11-19"
OUT.mkdir(parents=True, exist_ok=True)

CASES = [
    ("examples/typologies/scout40_2026-11-19/scout40__lecleach_hv_smooth_v7.yaml", "g_fc_v_hz",
     [450, 420, 400, 380, 360, 340, 320, 300]),
    ("examples/typologies/scout40_2026-11-19/scout40__lecleach_iwata_ar_smooth_v7.yaml", "g_fc_hz",
     [420, 400, 380, 360, 340, 320, 300]),
]

for rel, key, values in CASES:
    src = ROOT / rel
    cfg = yaml.safe_load(src.read_text(encoding="utf-8"))
    brief = (src.parent / cfg["brief_file"]).resolve()
    stem = src.stem
    for v in values:
        c = yaml.safe_load(yaml.safe_dump(cfg, sort_keys=False))
        c["name"] = f"sweep__{stem}__{key}_{v}"
        c["seed_params"][key] = float(v)
        c["brief_file"] = str(brief)
        (OUT / f"{stem}__{key}_{v}.yaml").write_text(yaml.safe_dump(c, sort_keys=False), encoding="utf-8")
print(f"wrote {len(list(OUT.glob('*.yaml')))} sweep configs to {OUT}")
