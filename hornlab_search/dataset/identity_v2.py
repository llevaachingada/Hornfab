"""Four identity layers (Rev2 6), additive and read-only over existing records.

physical_solve_id  = the M0 catalog formula (tools/analysis/catalog.py): sha16 of
                     [design_hash, mesh_hash, solve_hash]. Reused, not redefined, so cohorts agree.
                     ``response_sha256`` (bytes of response.npz) is carried beside it as the checksum.
analysis_id        = response checksum + metric method version + options (masks, quadrature,
                     thresholds, frequency grid). A new metric or target makes a new analysis_id.
score_id           = analysis ids + objective version + scorer code sha + resolved brief + weights,
                     tolerances, gates. Never overwrites an old objective; stored as a new row.
study_id           = optimizer/cohort/projection/model/acquisition/seeds. Never mixed with physics.

Nothing here writes to dataset/, cache/ or runs/. Old records and cache keys are unchanged.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

STATUSES = ("valid", "estimated", "censored", "missing", "invalid", "additional_physics_required")


def _canon(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def sha16(obj: Any) -> str:
    return hashlib.sha256(_canon(obj).encode()).hexdigest()[:16]


def file_sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def physical_solve_id(design_hash: str | None, mesh_hash: str | None, solve_hash: str | None) -> str:
    """Same formula as tools/analysis/catalog.py (M0), so ids join across tools."""
    return sha16([design_hash, mesh_hash, solve_hash])


def analysis_id(response_sha256: str, method: str, options: dict | None = None) -> str:
    return sha16({"layer": "analysis", "response": response_sha256, "method": method,
                  "options": options or {}})


def score_id(analysis_ids: Iterable[str], objective_version: Any, scorer_sha: str | None,
             brief: dict | None, weights: dict | None, gates: dict | None = None) -> str:
    return sha16({"layer": "score", "analyses": sorted(analysis_ids), "objective": objective_version,
                  "scorer": scorer_sha, "brief": brief or {}, "weights": weights or {},
                  "gates": gates or {}})


def study_id(spec: dict) -> str:
    return sha16({"layer": "study", **spec})


def compatibility(available: dict, required: Iterable[str]) -> dict:
    """``exact_complete`` | ``partial_unsupported`` | ``additional_data_or_solve_required``
    for a consumer that needs ``required`` keys of ``available`` (bool per field)."""
    req = list(required)
    missing = [k for k in req if not available.get(k)]
    if not missing:
        state = "exact_complete"
    elif len(missing) < len(req):
        state = "partial_unsupported"
    else:
        state = "additional_data_or_solve_required"
    return {"state": state, "missing": missing}


def append_jsonl(path: str | Path, row: dict) -> None:
    """Append-only manifest writer. Creates the parent dir; never rewrites earlier lines."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(_canon(row) + "\n")
