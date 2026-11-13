"""Conservative reconciliation of externally persisted attempt evidence.

The journal/probe are injected. The journal must make each resolution atomic and
idempotent; the probe must identify an exact attempt and solve identity. Unknown
is never interpreted as absent and no process or host is terminated here.
"""
from __future__ import annotations


def reconcile_study(study_id, process_and_artifact_probe, journal):
    resolved, unknown = [], []
    for attempt in journal.unresolved(study_id):
        evidence = process_and_artifact_probe.inspect(attempt)
        if (evidence.get("state") == "result" and
                evidence.get("attempt_id") == attempt["attempt_id"] and
                evidence.get("solve_id") == attempt["solve_id"] and
                isinstance(evidence.get("result"), dict) and
                evidence["result"].get("call_status") in ("called", "not_called") and
                evidence["result"].get("solve_id", attempt["solve_id"]) == attempt["solve_id"]):
            # Bind the already checked outer identity into the persisted result.
            result = {**evidence["result"], "solve_id": attempt["solve_id"]}
            journal.resolve(attempt["attempt_id"], result)
            resolved.append(attempt["attempt_id"])
        else:
            # Includes live/unknown process, ambiguous identity and absent artifacts.
            # Retain the reservation: absence of evidence is not evidence of no call.
            unknown.append(attempt["attempt_id"])
    return {"status": "unknown" if unknown else "reconciled",
            "resolved": resolved, "unknown": unknown}
