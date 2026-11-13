"""Strict evidence gate between S0/R0 and the B2 training selector.

A caller supplies joined S0 catalog and R0 replay rows and independently evidenced,
namespace-qualified *policy* identities. R0 physical/metric/score IDs are per-row
provenance and are deliberately never used as cross-row policy identifiers. In
particular S0's short stored-brief fingerprint is not an R0 resolved-brief hash.
This module does not reconstruct missing evidence or read the dataset.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import math
from typing import Mapping

import numpy as np

from .data import TrainingObservation

POLICY_FIELDS = ("task", "resolved_brief", "target", "score_policy", "metric_policy",
                 "frequency_masks", "backend", "fidelity", "mesh_policy", "frequency_grid",
                 "dependencies", "excitation", "encoding")


@dataclass(frozen=True)
class CohortResult:
    status: str
    reasons: tuple[str, ...]
    observations: tuple[TrainingObservation, ...] = ()
    policy_identity: tuple[tuple[str, str, str], ...] = ()

    @property
    def ok(self):
        return self.status == "ok"


def _known(value):
    if value is None or isinstance(value, bool):
        return False
    if isinstance(value, str):
        return bool(value.strip()) and value.strip().lower() not in {"unknown", "none", "null", "missing"}
    if isinstance(value, (list, tuple, dict)):
        return bool(value)
    if isinstance(value, (int, float)):
        return math.isfinite(float(value))
    return False


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def validate_cohort(rows, *, d: int) -> CohortResult:
    """Validate the whole requested cohort, returning no observations on any refusal.

    Each row contains ``catalog`` (S0 full record), ``replay`` (R0 result with
    shard/row), ``replay_root`` (the root used by the R0 run), ``x`` (encoded
    vector), and ``policy``. Every policy field is a mapping with nonempty
    ``namespace``, ``value``, and ``evidence`` (a source locator). Its value must
    identify the *shared policy*, not a row-specific R0 identity. Evidence is an
    explicit caller attestation, not a claim this gate independently verified its
    underlying file. S0 root/shard/row and R0 root/shard/row must match.

    ``backend``, ``fidelity``, ``frequency_grid`` and ``dependencies`` identities
    must use namespaces ``s0.backend``, ``s0.fidelity``, ``s0.grid_hash`` and
    ``s0.dependency_hash`` respectively, with values equal to the S0 record.
    Any missing source is ``capability_missing``; a conflict is ``incompatible``.
    """
    if not isinstance(d, int) or isinstance(d, bool) or d < 1:
        return CohortResult("capability_missing", ("invalid encoding dimension",))
    rows = list(rows)
    if not rows:
        return CohortResult("capability_missing", ("empty cohort",))
    expected = None
    observations = []
    seen_ids = set()
    physical = {}
    for i, row in enumerate(rows):
        prefix = f"row {i}"
        if not isinstance(row, Mapping):
            return CohortResult("capability_missing", (f"{prefix}: row missing",))
        c, r, policy = row.get("catalog"), row.get("replay"), row.get("policy")
        if not all(isinstance(x, Mapping) for x in (c, r, policy)):
            return CohortResult("capability_missing", (f"{prefix}: S0, R0 or policy evidence missing",))
        source = c.get("source")
        if not isinstance(source, Mapping) or not _known(source.get("root")) or not _known(row.get("replay_root")):
            return CohortResult("capability_missing", (f"{prefix}: source root missing",))
        if any(k not in source or k not in r or source[k] is None or r[k] is None
               for k in ("row",)) or source.get("shard_index") is None or r.get("shard") is None:
            return CohortResult("capability_missing", (f"{prefix}: source join key missing",))
        if (str(source["root"]) != str(row["replay_root"]) or
                str(source["shard_index"]) != str(r["shard"]) or str(source["row"]) != str(r["row"])):
            return CohortResult("incompatible", (f"{prefix}: S0/R0 source join mismatch",))
        if r.get("status") != "exact_complete" or r.get("complete") is not True or c.get("ok") is not True:
            return CohortResult("incompatible", (f"{prefix}: replay or source is not complete",))
        if r.get("objective_version") != 4:
            return CohortResult("incompatible", (f"{prefix}: objective is not v4",))
        for key in ("physical_id", "metric_id", "score_id", "design_hash", "metric_source"):
            if not _known(r.get(key)):
                return CohortResult("capability_missing", (f"{prefix}: R0 {key} missing",))
        if not _known(c.get("design_hash")) or not _known(c.get("record_sha256")):
            return CohortResult("capability_missing", (f"{prefix}: S0 record/design provenance missing",))
        if r["design_hash"] != c["design_hash"]:
            return CohortResult("incompatible", (f"{prefix}: S0/R0 design mismatch",))
        diag = r.get("diagnostics")
        if not isinstance(diag, Mapping) or diag.get("ripple_used_response") is not True:
            return CohortResult("capability_missing", (f"{prefix}: response-detrended ripple not evidenced",))
        if not isinstance(r.get("target"), Mapping) or not r["target"] or not isinstance(r.get("weights"), Mapping) or not r["weights"]:
            return CohortResult("capability_missing", (f"{prefix}: resolved target/weights missing",))
        parts = []
        for key in POLICY_FIELDS:
            claim = policy.get(key)
            if not isinstance(claim, Mapping) or not all(_known(claim.get(k)) for k in ("namespace", "value", "evidence")):
                return CohortResult("capability_missing", (f"{prefix}: {key} policy evidence missing",))
            try:
                parts.append((key, str(claim["namespace"]), _canonical(claim["value"])))
            except (ValueError, TypeError):
                return CohortResult("capability_missing", (f"{prefix}: invalid {key} identity",))
        for key, catalog_key in (("backend", "backend"), ("fidelity", "fidelity"),
                                 ("frequency_grid", "grid_hash"), ("dependencies", "dependency_hash")):
            claim = policy[key]
            if not _known(c.get(catalog_key)):
                return CohortResult("capability_missing", (f"{prefix}: S0 {catalog_key} missing",))
            if claim["namespace"] != f"s0.{catalog_key}" or claim["value"] != c[catalog_key]:
                return CohortResult("incompatible", (f"{prefix}: {key} disagrees with S0",))
        for key, namespace, actual in (("task", "s0.config_name", c.get("config_name")),
                                       ("target", "r0.target", r.get("target")),
                                       ("excitation", "s0.excitation", c.get("excitation"))):
            if actual is None or actual == {} or actual == "":
                return CohortResult("capability_missing", (f"{prefix}: {key} source missing",))
            if policy[key]["namespace"] != namespace or policy[key]["value"] != actual:
                return CohortResult("incompatible", (f"{prefix}: {key} disagrees with source",))
        if policy["resolved_brief"]["namespace"] != "r0.resolved_brief_hash":
            return CohortResult("incompatible", (f"{prefix}: resolved brief namespace must be R0",))
        if any(x in set(c.get("unknowns") or ()) for x in ("lib_shas_missing", "dependency_sha_unknown", "solve_freq_grid_missing")):
            return CohortResult("capability_missing", (f"{prefix}: S0 dependency or grid evidence incomplete",))
        current = tuple(parts)
        if expected is None:
            expected = current
            target = _canonical(r["target"])
            weights = _canonical(r["weights"])
            metric_source = r["metric_source"]
        elif current != expected or _canonical(r["target"]) != target or _canonical(r["weights"]) != weights or r["metric_source"] != metric_source:
            return CohortResult("incompatible", (f"{prefix}: cross-row policy or replay mismatch",))
        try:
            x = np.asarray(row.get("x"), dtype=float)
            j = float(r["j"])
            if x.shape != (d,) or not np.all(np.isfinite(x)) or np.any(x < 0) or np.any(x > 1) or not math.isfinite(j):
                raise ValueError("invalid vector or score")
        except (ValueError, TypeError, KeyError):
            return CohortResult("capability_missing", (f"{prefix}: encoded vector or score missing/invalid",))
        oid = f'{source["root"]}:{source["shard_index"]}:{source["row"]}'
        if oid in seen_ids:
            return CohortResult("incompatible", (f"{prefix}: duplicate source row",))
        seen_ids.add(oid)
        signature = (r["metric_id"], r["score_id"], r["design_hash"], x.tobytes(), j)
        old = physical.setdefault(r["physical_id"], signature)
        if old != signature:
            return CohortResult("incompatible", (f"{prefix}: conflicting provenance for same physical solve",))
        observations.append(TrainingObservation(oid, x.copy(), j, geometry_hash=r["design_hash"],
                                                solve_hash=r["physical_id"]))
    return CohortResult("ok", (), tuple(observations), expected or ())
