"""The MLP (needs torch) and a frozen save/load format."""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import torch
from torch import nn

FORMAT_VERSION = 1


class MetricMLP(nn.Module):
    """k in -> ``n_out`` metric values (z-scored) plus one validity logit."""

    def __init__(self, k: int, n_out: int, hidden: int = 256, layers: int = 3):
        super().__init__()
        blocks, d = [], k
        for _ in range(layers):
            blocks += [nn.Linear(d, hidden), nn.LayerNorm(hidden), nn.GELU()]
            d = hidden
        self.trunk = nn.Sequential(*blocks)
        self.reg = nn.Linear(d, n_out)
        self.cls = nn.Linear(d, 1)

    def forward(self, x):
        h = self.trunk(x)
        return self.reg(h), self.cls(h).squeeze(-1)


def save_bundle(path, *, states, meta: dict, mu: np.ndarray, sd: np.ndarray) -> None:
    """``meta``: family, keys, freqs_hz, metric_names, hidden, layers, lib_sha, n_train.

    Written atomically (tmp file + ``os.replace``): a half-written bundle at ``path`` is never
    observable, so an interrupted train cannot corrupt the previously good bundle."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    torch.save({"format": FORMAT_VERSION, "states": states, "meta": meta,
                "mu": np.asarray(mu), "sd": np.asarray(sd)}, tmp)
    os.replace(tmp, path)


def load_bundle(path) -> dict:
    d = torch.load(Path(path), map_location="cpu", weights_only=False)
    if d.get("format") != FORMAT_VERSION:
        raise ValueError(f"surrogate format {d.get('format')!r} != {FORMAT_VERSION}")
    return d


def bundle_gates_passed(path) -> bool:
    """True iff ``path`` holds a bundle whose stored gate verdict says PASSED. Any read error, a
    missing verdict, or ``gates_passed`` False is treated as NOT passing (used to avoid
    overwriting a known-good bundle with a failed retrain)."""
    try:
        b = load_bundle(path)
    except Exception:  # noqa: BLE001 - absent/corrupt destination is simply "not passing"
        return False
    gr = (b.get("meta") or {}).get("gate_report") or {}
    return bool(gr.get("gates_passed"))


def build_models(bundle: dict) -> list[MetricMLP]:
    m = bundle["meta"]
    out = []
    for st in bundle["states"]:
        net = MetricMLP(len(m["keys"]), len(m["metric_names"]) * len(m["freqs_hz"]),
                        m["hidden"], m["layers"])
        net.load_state_dict(st)
        net.eval()
        out.append(net)
    return out
