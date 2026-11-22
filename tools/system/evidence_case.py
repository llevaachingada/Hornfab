"""Derive a fresh, provenance-recorded system case from an existing staged project.

The reference workflow intentionally refuses to rerun into an existing case directory:
``reference.solve`` writes an immutable ``reference_solve.json`` and a BL ``run/`` tree.  New
evidence therefore needs a **new case** that points at the same physical project.

This tool is the narrow, auditable bridge for that:

* it copies the source ``case.blab.json`` byte-identically into a fresh case dir;
* it copies and validates the BL request overlay;
* it writes a self-checksummed manifest naming the source case, source project hash, request
  hash, Boundary Lab root and authorization record;
* optional ``--motor-patch`` applies the same ``component_parameters`` fields used by the sanctioned
  motor staging path to the copied project, then runs BL validate before solving;
* optional ``--project-preferences`` / ``--balloon-deg`` merge keys into the copied project's
  top-level ``project_preferences`` block (other keys are preserved), write the copied project
  deterministically and record the applied patch plus its sha256 in the derived manifest; BL's own
  validate runs before any ``--solve``;
* with ``--solve`` it invokes the existing authorized ``reference.solve`` path on the new case.

It owns no acoustics and no solver logic.  ``--dry-run`` prints the exact plan and writes nothing.
The source case must live under the configured store; a project recorded outside the store (for
example an older worktree project) is copied into the new case and its original path/hash is
recorded, but it is never modified.

Usage:
    .venv\\Scripts\\python.exe tools/system/evidence_case.py `
      --source-case system_runs/system/bl_motor12pr/<case> `
      --experiment-id ev_lf_motor_real --tag lf_20_200 `
      --request docs/queue/system_evidence_2026-11-19/requests/lf_vented_20_200.json `
      --prepare-only
    ... --solve --authorized-by "owner handoff 2026-11-19: ..."
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hornlab_search.system import provenance  # noqa: E402
from hornlab_search.system import reference  # noqa: E402
from hornlab_search.system.contracts import canonical_json  # noqa: E402

#: Boundary Lab 0.5.0 clamps the balloon sampling resolution to this inclusive range
#: (project preferences: ``balloon_angle_precision_deg``). Outside it BL silently clamps;
#: record the refusal here instead of reporting a precision the solve did not use.
BALLOON_DEG_MIN = 0.5
BALLOON_DEG_MAX = 15.0


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_source(value: str, store: Path) -> Path:
    candidate = Path(value)
    if not candidate.is_absolute():
        if candidate.exists():
            candidate = candidate.resolve()
        else:
            candidate = (store / "system" / value).resolve()
    else:
        candidate = candidate.resolve()
    if not candidate.is_dir():
        raise SystemExit(f"source case not found: {candidate}")
    store_resolved = store.resolve()
    if not candidate.is_relative_to(store_resolved):
        raise SystemExit(
            f"source case {candidate} is outside the system store {store_resolved}; "
            "refusing to derive from an uncontained path")
    return candidate


def _source_payload(source: Path) -> dict[str, Any]:
    manifest = source / "manifest.json"
    if not manifest.is_file():
        raise SystemExit(f"source case has no manifest.json: {source}")
    try:
        return provenance.load_manifest(manifest)["payload"]
    except (OSError, ValueError, KeyError) as exc:
        raise SystemExit(f"source manifest is unreadable or fails its checksum: {exc}") from None


def _project_for(source: Path, payload: Mapping[str, Any]) -> Path:
    local = source / "case.blab.json"
    if local.is_file():
        return local.resolve()
    recorded = payload.get("project") or payload.get("project_path")
    if isinstance(recorded, str) and recorded.strip():
        candidate = Path(recorded)
        if not candidate.is_absolute():
            candidate = (ROOT / candidate).resolve()
        if candidate.is_file():
            return candidate
    raise SystemExit(
        f"source case {source} has no case.blab.json and no readable recorded project")


def _bl_root(payload: Mapping[str, Any]) -> str | None:
    raw = payload.get("bl_root")
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except ValueError:
            return raw  # a plain path string is also accepted by reference._coerce_root
    else:
        parsed = raw
    if isinstance(parsed, Mapping):
        value = parsed.get("path")
        return str(value) if value else None
    return str(parsed) if parsed else None


def _project_preferences_patch(args: argparse.Namespace) -> tuple[dict[str, Any] | None,
                                                                  str | None, str | None]:
    """Build the ``project_preferences`` merge patch from the CLI options.

    Returns ``(patch, patch_file, patch_file_sha256)``. ``--project-preferences`` supplies a
    JSON object of keys; ``--balloon-deg`` is a convenience that adds BL's two balloon keys
    (and wins if the file also sets them). ``None`` means "copy the project byte-identically".
    """
    if args.balloon_deg is not None:
        value = float(args.balloon_deg)
        if not (BALLOON_DEG_MIN <= value <= BALLOON_DEG_MAX):
            raise SystemExit(
                f"--balloon-deg {value:g} is outside Boundary Lab's "
                f"{BALLOON_DEG_MIN:g}-{BALLOON_DEG_MAX:g} deg clamp")
    patch: dict[str, Any] = {}
    patch_file: str | None = None
    patch_file_sha256: str | None = None
    if args.project_preferences:
        path = Path(args.project_preferences).resolve()
        if not path.is_file():
            raise SystemExit(f"project preferences patch not found: {path}")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except ValueError as exc:
            raise SystemExit(f"project preferences patch is not valid JSON: {exc}") from None
        if not isinstance(payload, Mapping):
            raise SystemExit("project preferences patch must be a JSON object")
        patch.update(dict(payload))
        patch_file = str(path)
        patch_file_sha256 = _sha256(path)
    if args.balloon_deg is not None:
        patch["spherical_sampling_enabled"] = True
        patch["balloon_angle_precision_deg"] = float(args.balloon_deg)
    return (patch or None), patch_file, patch_file_sha256


def _plan(args: argparse.Namespace) -> dict[str, Any]:
    store = Path(args.store).resolve()
    source = _resolve_source(args.source_case, store)
    payload = _source_payload(source)
    project = _project_for(source, payload)
    request = Path(args.request).resolve()
    loaded = reference.load_request(request)
    motor_patch = Path(args.motor_patch).resolve() if args.motor_patch else None
    if motor_patch is not None:
        if not motor_patch.is_file():
            raise SystemExit(f"motor patch not found: {motor_patch}")
        try:
            patch_payload = json.loads(motor_patch.read_text(encoding="utf-8"))
        except ValueError as exc:
            raise SystemExit(f"motor patch is not valid JSON: {exc}") from None
        if not isinstance(patch_payload, Mapping) or not isinstance(
                patch_payload.get("component_parameters"), Mapping):
            raise SystemExit("motor patch must contain a 'component_parameters' object")
    preferences_patch, preferences_file, preferences_file_sha = _project_preferences_patch(args)
    return {
        "source_case": str(source),
        "source_manifest_sha256": _sha256(source / "manifest.json"),
        "source_project": str(project),
        "source_project_sha256": _sha256(project),
        "bl_root": _bl_root(payload),
        "request": str(request),
        "request_sha256": loaded.sha256,
        "frequencies_hz": list(loaded.frequencies_hz),
        "excitation_port_ids": list(loaded.excitation_port_ids),
        "motor_patch": None if motor_patch is None else str(motor_patch),
        "motor_patch_sha256": None if motor_patch is None else _sha256(motor_patch),
        "project_preferences_patch": preferences_patch,
        "project_preferences_patch_file": preferences_file,
        "project_preferences_patch_file_sha256": preferences_file_sha,
        "project_preferences_patch_sha256": (
            None if preferences_patch is None
            else hashlib.sha256(canonical_json(preferences_patch).encode()).hexdigest()),
        "balloon_deg": None if args.balloon_deg is None else float(args.balloon_deg),
        "experiment_id": args.experiment_id,
        "tag": args.tag,
        "solve": bool(args.solve),
        "authorized_by": args.authorized_by or os.environ.get("HORNLAB_EVIDENCE_AUTHORIZED_BY"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python tools/system/evidence_case.py",
        description="Derive a fresh system case from an existing project and optionally solve it")
    parser.add_argument("--source-case", required=True,
                        help="existing case dir under the store (or system/<experiment>/<case>)")
    parser.add_argument("--experiment-id", required=True,
                        help="new experiment id; a fresh case dir is created under it")
    parser.add_argument("--tag", default="evidence",
                        help="case tag (default: evidence)")
    parser.add_argument("--request", required=True,
                        help="BL headless request overlay JSON")
    parser.add_argument("--store", default="system_runs",
                        help="system store root (default: system_runs)")
    parser.add_argument("--authorized-by", default=None,
                        help="required with --solve; recorded in the derived-case manifest")
    parser.add_argument("--solve", action="store_true",
                        help="solve the derived case after preparing it (requires --authorized-by)")
    parser.add_argument("--prepare-only", action="store_true",
                        help="explicit no-solve flag (default behaviour; kept for readable queues)")
    parser.add_argument("--timeout-s", type=float, default=None,
                        help="BL solve timeout in seconds (default: reference default)")
    parser.add_argument("--notes", default="", help="free-text provenance note")
    parser.add_argument("--motor-patch", default=None, metavar="JSON",
                        help="optional {component_parameters: {id: {...}}} patch applied to the "
                             "copied project (the same fields BL's component_parameters patch uses); "
                             "the derived case is validated before solving")
    parser.add_argument("--project-preferences", default=None, metavar="JSON",
                        help="optional JSON object merged into the copied project's top-level "
                             "project_preferences block (other keys preserved); the project is "
                             "rewritten deterministically and the derived case is validated before "
                             "solving")
    parser.add_argument("--balloon-deg", type=float, default=None, metavar="FLOAT",
                        help="convenience for --project-preferences "
                             "{spherical_sampling_enabled: true, balloon_angle_precision_deg: "
                             "FLOAT}; refused outside 0.5-15 deg (BL's clamp)")
    parser.add_argument("--dry-run", action="store_true", help="print the plan; write nothing")
    args = parser.parse_args(argv)
    # The queue file deliberately carries no standing authorization.  The owner/operator sets
    # this env var at launch time (or passes --authorized-by explicitly); the record is then
    # copied verbatim into the derived-case manifest.
    authorized = args.authorized_by or os.environ.get("HORNLAB_EVIDENCE_AUTHORIZED_BY")

    if args.solve and args.prepare_only:
        print("evidence_case: --solve and --prepare-only are mutually exclusive", file=sys.stderr)
        return 2

    try:
        plan = _plan(args)
    except SystemExit as exc:
        print(f"evidence_case: {exc}", file=sys.stderr)
        return 2
    except reference.ReferenceError as exc:
        print(f"evidence_case: {exc}", file=sys.stderr)
        return 2

    if args.dry_run:
        print(json.dumps({**plan, "case_dir": None, "would_create": True}, indent=2,
                         sort_keys=True))
        return 0

    if args.solve and not plan["authorized_by"]:
        print("evidence_case: --solve requires --authorized-by or "
              "HORNLAB_EVIDENCE_AUTHORIZED_BY", file=sys.stderr)
        return 2

    store = Path(args.store).resolve()
    source = Path(plan["source_case"])
    project = Path(plan["source_project"])
    request = Path(plan["request"])

    case = provenance.new_case_dir(args.experiment_id, store_root=store, tag=args.tag)
    shutil.copyfile(project, case / "case.blab.json")
    shutil.copyfile(request, case / "request.json")

    patched_components: list[str] = []
    preferences_patch = plan["project_preferences_patch"]
    project_rewritten = bool(args.motor_patch) or preferences_patch is not None
    if project_rewritten:
        case_project = json.loads((case / "case.blab.json").read_text(encoding="utf-8"))
        if args.motor_patch:
            patch_path = Path(plan["motor_patch"])
            patch_payload = json.loads(patch_path.read_text(encoding="utf-8"))
            components = (case_project.get("physical_system") or {}).get("components") or []
            by_id = {str(c.get("id")): c for c in components if isinstance(c, Mapping)}
            for component_id, values in patch_payload["component_parameters"].items():
                component = by_id.get(str(component_id))
                if component is None:
                    raise SystemExit(
                        f"motor patch component {component_id!r} is not in the copied project; "
                        f"available: {sorted(by_id)}")
                params = component.setdefault("parameters", {})
                if not isinstance(params, dict):
                    raise SystemExit(f"component {component_id!r} parameters are not an object")
                params.update(dict(values))
                patched_components.append(str(component_id))
            shutil.copyfile(patch_path, case / "motor_patch.json")
        if preferences_patch is not None:
            existing = case_project.get("project_preferences", {})
            if existing is None:
                existing = {}
            if not isinstance(existing, Mapping):
                raise SystemExit(
                    "copied project's project_preferences is not a JSON object; refusing to "
                    "overwrite it with a merge patch")
            merged = dict(existing)
            merged.update(dict(preferences_patch))
            case_project["project_preferences"] = merged
            if plan["project_preferences_patch_file"]:
                shutil.copyfile(Path(plan["project_preferences_patch_file"]),
                                case / "project_preferences_patch.json")
        # deterministic write: sorted keys, two-space indent, LF, one trailing newline
        (case / "case.blab.json").write_text(
            json.dumps(case_project, indent=2, sort_keys=True) + "\n",
            encoding="utf-8", newline="\n")
    derived_project_sha256 = _sha256(case / "case.blab.json")
    # BL generator documents store mesh paths RELATIVE to the project's directory.  A byte copy
    # of only the project would leave those paths dangling in the new case, so copy the
    # project's bl_output tree when present.  Imported absolute horn meshes are read-only and
    # stay referenced by their recorded absolute path (BL reads them; we never modify them).
    copied_artifacts: list[str] = []
    source_bl_output = project.parent / "bl_output"
    if source_bl_output.is_dir():
        shutil.copytree(source_bl_output, case / "bl_output")
        copied_artifacts.append("bl_output")

    payload = {
        "kind": "bl_derived_request_case",
        "schema_version": 1,
        "source_case": str(source.relative_to(store)) if source.is_relative_to(store) else str(source),
        "source_manifest_sha256": plan["source_manifest_sha256"],
        "source_project_path": str(project),
        "source_project_sha256": plan["source_project_sha256"],
        "bl_root": plan["bl_root"],
        "request_file": "request.json",
        "request_sha256": plan["request_sha256"],
        "frequencies_hz": plan["frequencies_hz"],
        "excitation_port_ids": plan["excitation_port_ids"],
        "authorized_by": plan["authorized_by"],
        "notes": args.notes,
        "derivation": ("project and request copied byte-identically; source hashes recorded"
                       if not project_rewritten else
                       "project copied then rewritten deterministically after the recorded "
                       "patches; source hashes recorded"),
        "copied_artifacts": copied_artifacts,
        "derived_project_sha256": derived_project_sha256,
        "motor_patch_file": "motor_patch.json" if args.motor_patch else None,
        "motor_patch_sha256": plan["motor_patch_sha256"],
        "motor_patch_component_ids": patched_components,
        "project_preferences_patch_file": plan["project_preferences_patch_file"],
        "project_preferences_patch_file_sha256":
            plan["project_preferences_patch_file_sha256"],
        "project_preferences_patch": plan["project_preferences_patch"],
        "project_preferences_patch_sha256": plan["project_preferences_patch_sha256"],
        "balloon_deg": plan["balloon_deg"],
    }
    provenance.write_manifest(case, payload)
    print(f"evidence_case: prepared {case}")
    print(json.dumps({"case_dir": str(case), **plan}, indent=2, sort_keys=True))

    if not args.solve:
        return 0

    if project_rewritten:
        # The copied project was edited, so BL's own validate is the authority before any solve.
        try:
            validation = reference.validate(case, case / "request.json")
        except reference.ReferenceError as exc:
            print(f"evidence_case: VALIDATE FAILED: {exc}", file=sys.stderr)
            return 1
        (case / "reference_validate.json").write_text(
            json.dumps(validation.as_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8", newline="\n")
        if not validation.valid:
            print("evidence_case: BL validate refused the patched project", file=sys.stderr)
            return 1

    from hornlab_search.search.gpulock import GpuBusyError, cpu_lane_lock

    try:
        # F6: a manual evidence solve takes the CPU-lane marker like a queued night does, so a
        # GUI hw-* job (which reads the same lock) refuses while this solve is live, and this
        # solve refuses/warns per the shared lock policy while a night holds it. No bypass.
        with cpu_lane_lock(f"evidence_case {plan['experiment_id']}"):
            result = reference.solve(case, case / "request.json", backend="beat_cpu",
                                     authorized_by=plan["authorized_by"], timeout_s=args.timeout_s)
    except GpuBusyError as exc:
        print(f"evidence_case: CPU LANE BUSY: {exc}", file=sys.stderr)
        return 1
    except reference.ReferenceError as exc:
        print(f"evidence_case: SOLVE FAILED: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({
        "case_dir": str(case),
        "run_dir": str(result.run_dir),
        "status": result.status,
        "returncode": result.returncode,
        "record": str(result.record_path),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
