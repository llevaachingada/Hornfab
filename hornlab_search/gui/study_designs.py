"""Read-only bridge from BoTorch study observations to their persisted solve artifacts.

``studies/production.py`` writes ordinary physical artifacts to
``runs/study-<package16>/{screen|verify}/designs/<design_hash>/`` but the ordinary GUI run
resolver only accepts timestamp run ids.  This module is the single, explicit resolver that
maps a study observation to that already-persisted directory, using :class:`StudyIndex`:

    (study_id, root_id) -> owning registry  -> current ``package`` artifact sha
        -> ``<repo>/runs/study-<sha[:16]>/{screen|verify}/designs/<design_hash>/``

It never accepts a user-supplied filesystem path.  Every step is validated: the study id and
root, the package artifact identity (including each tier's ``run.json``), candidate membership,
the tier allowlist, canonical path containment (no traversal or root collision) and the
mesh/solve/physical identity recorded by the search.

The endpoints are GET-only and never solve, verify, mesh or queue anything.  When a
``mesh.msh`` is missing but the design/config is pinned, a geometry-only no-BEM preview is
offered through the existing canonical ``bo/data.py::materialize_geometry`` API and is labelled
as a preview, not as the stored solved surface.  CAD/point-grid families that the canonical
sampler refuses return ``unsupported_geometry`` rather than a fabricated radial horn.
"""
from __future__ import annotations

import json
import math
import re
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from hornlab_search.studies.schema import NotFound, StudyError

from . import data as D

#: Allowed design tiers (the only folders ``production.py`` writes).
TIERS = ("screen", "verify")
#: Typed observation states returned by every endpoint.
STATES = ("measured", "geometry_only", "predicted_only", "missing_artifact",
          "unsupported_geometry", "stale")
#: Payload bound for the small observation listing.
MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 25
#: Sorting keys accepted by the listing endpoint.  ``verified_j`` prefers recorded verify/audit
#: evidence (null last); ``screen_j`` ranks eligible screen scores only.
SORTS = ("best_j", "worst_j", "screen_j", "verified_j", "attempt", "seq")
#: Bound on any convergence series (identities stay parallel).
MAX_SERIES = 500
UNRECORDED = "not_recorded"

_SOLVE_ID_RE = re.compile(r"^[0-9a-f]{64}$")
_PACKAGE_ID_RE = re.compile(r"^[0-9a-f]{64}$")
_REFUSAL_OUTCOMES = frozenset({"cheap_refusal", "refused", "refusal"})


# --------------------------------------------------------------------------- small helpers


def _finite(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _mapping(value) -> Mapping:
    return value if isinstance(value, Mapping) else {}


def _contained(path: Path, base: Path) -> bool:
    """True when ``path`` resolves inside ``base`` (no traversal, no root collision)."""
    try:
        resolved = Path(path).resolve()
        root = Path(base).resolve()
    except OSError:
        return False
    return resolved == root or root in resolved.parents


def _pareto_units(result: Mapping) -> tuple[float | None, float | None]:
    """Physical coverage/ripple only (never dimensionless objective contributions)."""
    for key in ("pareto_metric", "pareto"):
        value = result.get(key)
        if isinstance(value, Mapping) and value.get("status", "complete") == "complete":
            return (_finite(value.get("coverage_deg")), _finite(value.get("ripple_db")))
    objectives = result.get("objectives")
    if isinstance(objectives, (list, tuple)) and len(objectives) == 2:
        return _finite(objectives[0]), _finite(objectives[1])
    return None, None


# --------------------------------------------------------------------------- context


@dataclass(frozen=True)
class Context:
    """The validated owning registry, package and run folder for one study."""

    repo_root: Path
    runs_root: Path
    root: dict
    service: Any
    study: dict
    study_id: str
    package_sha: str | None
    package_data: dict
    run_root: Path | None
    state: str                       # "ok" | "missing_artifact" | "stale"
    reason: str | None


@dataclass(frozen=True)
class Attempt:
    """One durable attempt row (and its observation row, when it has one)."""

    attempt_id: str
    solve_id: str
    kind: str
    status: str
    candidate: dict
    result: dict
    observation: dict | None
    design_hash: str | None
    tier: str
    identity_reason: str | None


def _package_rows(service, study_id: str) -> dict[str, dict]:
    rows: dict[str, dict] = {}
    with closing(service.store.connect()) as conn:
        for row in conn.execute(
                "SELECT id,study_id,revision,package_json,status,active,cancelled "
                "FROM packages WHERE study_id=? ORDER BY rowid", (study_id,)):
            item = dict(row)
            try:
                item["package_json"] = json.loads(item["package_json"])
            except (TypeError, ValueError):
                item["package_json"] = None
            rows[str(item["id"])] = item
    return rows


def _context(index, study_id: str, root_id, runs_root) -> Context:
    """Resolve ``(study_id, root)`` to a validated package run folder, never a client path."""
    if runs_root is None:
        raise StudyError("run folder is not configured")
    repo_root = Path(index.root).resolve()
    runs_root = Path(runs_root).resolve()
    root, service, study = index.resolve(study_id, root_id)
    if study.get("id") != study_id:
        raise NotFound(f"study {study_id!r} is not registered at that root")

    def _ctx(package_sha, package_data, run_root, state, reason):
        return Context(repo_root, runs_root, root, service, study, study_id,
                       package_sha, package_data, run_root, state, reason)

    meta = service.get_artifact_metadata(study_id, "package")
    status = meta.get("status")
    if status == "missing":
        return _ctx(None, {}, None, "missing_artifact",
                    "This study has no prepared run package, so it has no physical artifacts.")
    if status == "stale":
        return _ctx(meta.get("sha256"), {}, None, "stale",
                    "The run package was prepared at an older study revision; its artifacts are stale.")
    if status != "available":
        return _ctx(meta.get("sha256"), {}, None, "missing_artifact",
                    meta.get("reason") or "The study run package is not available.")
    sha = str(meta.get("sha256") or "")
    if not _PACKAGE_ID_RE.match(sha):
        return _ctx(None, {}, None, "stale", "The package artifact identity is not a sha256.")

    try:
        view = service.artifact_view(study_id, "package", max_bytes=4_000_000)
    except Exception as exc:  # noqa: BLE001 - a vanished artifact is a typed missing state
        return _ctx(sha, {}, None, "missing_artifact",
                    f"The package artifact is unreadable: {type(exc).__name__}")
    data = view.get("data") if isinstance(view, Mapping) else None
    if not isinstance(data, dict):
        return _ctx(sha, {}, None, "missing_artifact", "The package artifact is unreadable.")
    if data.get("study_id") not in (None, study_id):
        return _ctx(sha, data, None, "stale",
                    "The package artifact belongs to a different study.")

    row = _package_rows(service, study_id).get(sha)
    if row is not None:
        if row.get("study_id") != study_id:
            return _ctx(sha, data, None, "stale",
                        "The package row belongs to a different study.")
        body = row.get("package_json")
        if isinstance(body, Mapping) and body.get("study_id") not in (None, study_id):
            return _ctx(sha, data, None, "stale",
                        "The package body belongs to a different study.")

    run_root = runs_root / ("study-" + sha[:16])
    if not _contained(run_root, runs_root):
        return _ctx(sha, data, None, "stale",
                    "The resolved run folder escapes the configured runs root.")
    if not run_root.is_dir():
        return _ctx(sha, data, run_root, "missing_artifact",
                    "The run package exists but its solve run folder was never created.")
    return _ctx(sha, data, run_root, "ok", None)


def _load_attempts(service, study_id: str) -> list[Attempt]:
    rows = []
    with closing(service.store.connect()) as conn:
        for row in conn.execute(
                "SELECT a.id AS attempt_id, a.solve_id, a.kind, a.status, "
                "a.candidate_json, a.result_json, "
                "o.observation_seq, o.physical_id AS obs_physical_id, o.score_id AS obs_score_id "
                "FROM attempts a "
                "LEFT JOIN observations o ON o.attempt_id=a.id AND o.study_id=a.study_id "
                "WHERE a.study_id=? ORDER BY a.rowid", (study_id,)):
            rows.append(dict(row))
    out: list[Attempt] = []
    for row in rows:
        try:
            candidate = json.loads(row["candidate_json"])
        except (TypeError, ValueError):
            candidate = None
        try:
            result = json.loads(row["result_json"]) if row["result_json"] else {}
        except (TypeError, ValueError):
            result = {}
        if not isinstance(candidate, dict) or not isinstance(result, dict):
            continue
        solve_id = str(row["solve_id"] or "")
        identity_reason = None
        if not _SOLVE_ID_RE.match(solve_id):
            identity_reason = "The attempt solve_id is not a sha256."
        if result.get("solve_id") not in (None, solve_id):
            identity_reason = "The result solve_id does not match the attempt."
        if candidate.get("solve_id") not in (None, solve_id):
            identity_reason = "The candidate solve_id does not match the attempt."
        design_hash = (candidate.get("design_hash") or result.get("design_hash")
                       or candidate.get("geometry_hash"))
        if design_hash is not None and not D.HASH.match(str(design_hash)):
            identity_reason = "The design hash is not a legal design id."
            design_hash = None
        if (candidate.get("design_hash") and result.get("design_hash")
                and candidate["design_hash"] != result["design_hash"]):
            identity_reason = "Candidate and result design hashes disagree."
        observation = None
        if row.get("observation_seq") is not None:
            observation = {"observation_seq": row["observation_seq"],
                           "physical_id": row.get("obs_physical_id"),
                           "score_id": row.get("obs_score_id")}
            if (result.get("physical_id") and observation["physical_id"]
                    and result["physical_id"] != observation["physical_id"]):
                identity_reason = "The observation physical_id does not match the result."
            if (result.get("score_id") and observation["score_id"]
                    and result["score_id"] != observation["score_id"]):
                identity_reason = "The observation score_id does not match the result."
        kind = str(row["kind"] or "")
        tier = "verify" if kind in ("verify", "audit") else "screen"
        out.append(Attempt(str(row["attempt_id"]), solve_id, kind, str(row["status"] or ""),
                           candidate, result, observation,
                           str(design_hash) if design_hash is not None else None,
                           tier, identity_reason))
    return out


def _attempt_for(service, study_id: str, solve_id: str) -> Attempt:
    if not _SOLVE_ID_RE.match(str(solve_id or "")):
        raise NotFound(f"unknown solve id {solve_id!r}")
    for attempt in _load_attempts(service, study_id):
        if attempt.solve_id == solve_id:
            return attempt
    raise NotFound(f"solve {solve_id!r} is not an attempt of this study")


# --------------------------------------------------------------------------- containment


def _tier_dir(ctx: Context, tier: str) -> Path | None:
    if tier not in TIERS:
        raise ValueError(f"unknown tier {tier!r}; must be 'screen' or 'verify'")
    if ctx.run_root is None:
        return None
    tier_dir = ctx.run_root / tier
    if not _contained(tier_dir, ctx.run_root):
        raise ValueError("resolved tier folder escapes the study run folder")
    return tier_dir


def _design_dir(ctx: Context, tier_dir: Path, design_hash: str) -> Path:
    if not D.HASH.match(str(design_hash or "")):
        raise ValueError(f"not a design hash: {design_hash!r}")
    design_dir = tier_dir / "designs" / design_hash
    if not _contained(design_dir, tier_dir):
        raise ValueError("resolved design folder escapes the tier folder")
    return design_dir


def _run_identity(ctx: Context, tier_dir: Path | None, tier: str) -> tuple[str, str | None]:
    """Validate that a tier folder really belongs to this study's package."""
    if ctx.state != "ok":
        return ctx.state, ctx.reason
    if tier_dir is None or not tier_dir.is_dir():
        return "missing_artifact", f"No {tier} solve folder exists for this package."
    run_json = D._read_json(tier_dir / "run.json") or {}
    if isinstance(run_json, dict):
        if run_json.get("package_id") not in (None, ctx.package_sha):
            return "stale", "The tier run.json names a different package."
        if run_json.get("study_id") not in (None, ctx.study_id):
            return "stale", "The tier run.json names a different study."
        if run_json.get("mode") not in (None, tier):
            return "stale", "The tier run.json names a different mode."
    return "ok", None


def _artifact_flags(design_dir: Path | None) -> dict:
    if design_dir is None or not design_dir.is_dir():
        return {"design_dir": False, "mesh": False, "metrics": False,
                "response": False, "design": False, "mesh_meta": False}
    return {
        "design_dir": True,
        "mesh": (design_dir / "mesh.msh").is_file(),
        "metrics": (design_dir / "metrics.json").is_file(),
        "response": (design_dir / "response.npz").is_file(),
        "design": (design_dir / "design.json").is_file(),
        "mesh_meta": (design_dir / "mesh_meta.json").is_file(),
    }


# --------------------------------------------------------------------------- preview capability


def _config_path(ctx: Context, tier_dir: Path | None) -> Path | None:
    """The immutable job config: the tier snapshot first, then the study's pinned task config."""
    if tier_dir is not None and (tier_dir / "config.yaml").is_file():
        return tier_dir / "config.yaml"
    meta = ctx.service.get_artifact_metadata(ctx.study_id, "snapshot")
    if meta.get("status") != "available":
        return None
    try:
        view = ctx.service.artifact_view(ctx.study_id, "snapshot", max_bytes=4_000_000)
    except Exception:  # noqa: BLE001 - a missing snapshot cannot enable a preview
        return None
    task = _mapping(_mapping(view.get("data")).get("task"))
    raw = task.get("config")
    if not isinstance(raw, str) or not raw:
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = ctx.repo_root / path
    path = path.resolve()
    return path if _contained(path, ctx.repo_root) and path.is_file() else None


def _pinned_design(ctx: Context, attempt: Attempt, tier_dir: Path | None):
    """``(family, params, design_dir)`` of the pinned candidate (never fabricated)."""
    design_dir = None
    if tier_dir is not None and attempt.design_hash:
        design_dir = _design_dir(ctx, tier_dir, attempt.design_hash)
    record = D._read_json(design_dir / "design.json") if design_dir is not None else None
    record = record if isinstance(record, dict) else {}
    params = record.get("params") if isinstance(record.get("params"), dict) else None
    if params is None and isinstance(attempt.candidate.get("params"), dict):
        params = attempt.candidate["params"]
    family = record.get("family") or attempt.candidate.get("family")
    if not family and tier_dir is not None:
        family = D._config(tier_dir).get("family")
    return family, params, design_dir


def _grid_is_rolled_family(grid) -> bool:
    """The exact rolled-family predicate ``materialize_geometry`` accepts (no meshing)."""
    try:
        from hornlab_search.design.generators import rolled_family
        return bool(rolled_family.is_family_spec(grid))
    except Exception:  # noqa: BLE001 - an absent helper means the grid is not previewable
        return False


def _preview_capability(ctx: Context, attempt: Attempt, tier_dir: Path | None) -> tuple[bool, str | None]:
    """Whether a no-BEM preview *could* be materialized (no mesher call happens here)."""
    family, params, _design_dir = _pinned_design(ctx, attempt, tier_dir)
    if not isinstance(params, dict) or not params:
        return False, "No pinned design parameters are recorded."
    if "cad" in params:
        return False, ("CAD geometry is unsupported by the canonical preview API.")
    grid = params.get("grid")
    if isinstance(grid, dict) and not _grid_is_rolled_family(grid):
        return False, ("Point-grid geometry is unsupported by the canonical preview API.")
    if not family:
        return False, "The geometry family is not recorded."
    if _config_path(ctx, tier_dir) is None:
        return False, "No pinned config is available for a geometry preview."
    return True, None


def _materialize_preview(ctx: Context, attempt: Attempt, tier_dir: Path | None):
    """Materialize the pinned geometry without any BEM call; returns ``(state, payload, reason)``."""
    config_path = _config_path(ctx, tier_dir)
    if config_path is None:
        return "missing_artifact", None, "No pinned config is available for a geometry preview."
    family, params, _design_dir = _pinned_design(ctx, attempt, tier_dir)
    if not isinstance(params, dict) or not params or not family:
        return "missing_artifact", None, "The pinned design/config cannot be materialized."
    try:
        from hornlab_search.bo.data import materialize_geometry
        from hornlab_search.config import load_config
        from hornlab_search.types import Design
        from .preview import tessellate

        config = load_config(config_path)
        mat = materialize_geometry(Design(str(family), dict(params)), config)
        mesh = tessellate(mat["inner_points"])
    except Exception as exc:  # noqa: BLE001 - a preview must never break the read-only route
        name = type(exc).__name__
        if name == "UnsupportedGeometryError" or "UnsupportedGeometryError" in name:
            return "unsupported_geometry", None, str(exc)
        return "missing_artifact", None, f"Geometry preview unavailable: {name}: {exc}"
    positions = mesh.get("positions")
    indices = mesh.get("indices")
    positions = [] if positions is None else positions
    indices = [] if indices is None else indices
    positions = D.clean(positions)
    indices = D.clean(indices)
    try:
        n_tris = len(indices) // 3
    except TypeError:
        n_tris = 0
    payload = {
        "quadrants": str(mat.get("quadrants") or "1234"),
        "n_tris": int(n_tris),
        "verts": positions,
        "tris": indices,
        "roles": D.clean(mesh.get("roles") or []),
        "warnings": D.clean(mesh.get("warnings") or []),
        "formula": mat.get("formula"),
        "resolution_mm": mat.get("resolution_mm"),
    }
    return "geometry_only", payload, None


# --------------------------------------------------------------------------- observation state


def _observation_state(ctx: Context, attempt: Attempt, tier: str) -> tuple[str, str | None, dict]:
    """Typed state of one attempt at one tier, with explicit artifacts and reason."""
    tier_dir = _tier_dir(ctx, tier)
    state, reason = _run_identity(ctx, tier_dir, tier)
    flags = _artifact_flags(None)
    if tier_dir is not None and attempt.design_hash:
        try:
            flags = _artifact_flags(_design_dir(ctx, tier_dir, attempt.design_hash))
        except ValueError as exc:
            return "stale", str(exc), flags
    if state != "ok":
        return state, reason, flags
    if attempt.identity_reason:
        return "stale", attempt.identity_reason, flags
    if attempt.design_hash is None:
        return "missing_artifact", "The attempt carries no resolvable design identity.", flags

    record = D._read_json(Path(tier_dir) / "designs" / attempt.design_hash / "design.json") \
        if flags["design"] else None
    if isinstance(record, dict) and record.get("design_hash") not in (None, attempt.design_hash):
        return "stale", "The stored design.json belongs to a different design hash.", flags

    physical = attempt.result.get("physical_measurement") is True
    if physical and flags["metrics"] and flags["response"]:
        return "measured", None, flags
    if not physical:
        predicted = isinstance(attempt.candidate.get("predicted"), Mapping)
        outcome = attempt.result.get("outcome")
        if predicted:
            return "predicted_only", ("The candidate has a prediction but no stored physical "
                                      "measurement."), flags
        if outcome in _REFUSAL_OUTCOMES:
            return "missing_artifact", "The attempt was refused before a physical solve.", flags
        if attempt.status in ("reserved", "unknown"):
            return "predicted_only", "The attempt is reserved; no result is stored yet.", flags
        return "missing_artifact", "No physical measurement was recorded for this attempt.", flags
    # A physical measurement is expected but the acoustic artifacts are missing.
    if flags["mesh"]:
        return "geometry_only", ("The stored mesh exists but the acoustic arrays are missing."), flags
    capable, why = _preview_capability(ctx, attempt, tier_dir)
    if capable:
        return "geometry_only", ("No stored acoustic artifacts; a no-BEM geometry preview is "
                                 "available from the pinned design."), flags
    if why and "CAD" in why:
        return "unsupported_geometry", why, flags
    return "missing_artifact", why or "The stored acoustic artifacts are missing.", flags


# --------------------------------------------------------------------------- listing


def _artifact_data(service, study_id: str, kind: str, *, max_bytes: int = 4_000_000):
    """Bounded artifact body, or None when it is absent/unreadable (never fatal)."""
    meta = service.get_artifact_metadata(study_id, kind)
    if meta.get("status") != "available":
        return None
    try:
        view = service.artifact_view(study_id, kind, max_bytes=max_bytes)
    except Exception:  # noqa: BLE001 - a missing artifact is an honest absent fact
        return None
    data = view.get("data") if isinstance(view, Mapping) else None
    return data if isinstance(data, Mapping) else None


def _study_policy(study) -> str:
    policy = _mapping(_mapping(study).get("spec")).get("policy")
    policy = _mapping(policy)
    return str(policy.get("proposal_policy") or policy.get("mode") or "scalar")


def _nondominated_designs(points: Mapping[str, Mapping]) -> set[str]:
    """Design hashes on the 2-D (coverage error, ripple) minimisation frontier."""
    keys = list(points)
    out: set[str] = set()
    for key in keys:
        p = points[key]
        cov, rip = p.get("coverage_deg"), p.get("ripple_db")
        dominated = False
        for other in keys:
            if other == key:
                continue
            q = points[other]
            qcov, qrip = q.get("coverage_deg"), q.get("ripple_db")
            if qcov is None or qrip is None or cov is None or rip is None:
                continue
            if (qcov <= cov and qrip <= rip) and (qcov < cov or qrip < rip):
                dominated = True
                break
        if not dominated:
            out.add(key)
    return out


class _Facts:
    """Per-request recorded facts, cached so a 219-row page does not re-read files per row.

    Every value is read from a recorded artifact/design/config file; nothing is inferred from a
    config name or typology string.  Missing facts answer ``None`` + a reason.
    """

    def __init__(self, ctx: Context, attempts: list[Attempt]):
        self.ctx = ctx
        self.attempts = attempts
        self.study = ctx.study
        self.policy = _study_policy(ctx.study)
        self._snapshot_cache = None
        self._config_cache: dict = {}
        self._meta_cache: dict = {}
        self._record_cache: dict = {}
        self._search_cache: dict = {}
        self.identities = self._manifest_identities()
        self.pareto_points, self.nondominated, self.pareto_reason = self._pareto(attempts)
        self.incumbent = self._incumbents(attempts)

    # ---- recorded artifact/config reads (cached)
    def _artifact(self, kind: str, max_bytes: int = 4_000_000):
        return _artifact_data(self.ctx.service, self.ctx.study_id, kind, max_bytes=max_bytes)

    def snapshot_task(self) -> dict:
        if self._snapshot_cache is None:
            snapshot = self._artifact("snapshot", 4_000_000) or {}
            self._snapshot_cache = dict(_mapping(snapshot.get("task")))
        return self._snapshot_cache

    def config(self, tier_dir: Path | None) -> dict:
        if tier_dir is None:
            return {}
        key = str(tier_dir)
        if key not in self._config_cache:
            self._config_cache[key] = D._config(tier_dir)
        return self._config_cache[key]

    def design_record(self, tier_dir: Path | None, design_hash: str | None) -> dict:
        if tier_dir is None or not design_hash:
            return {}
        key = (str(tier_dir), design_hash)
        if key not in self._record_cache:
            record = D._read_json(Path(tier_dir) / "designs" / design_hash / "design.json")
            self._record_cache[key] = record if isinstance(record, dict) else {}
        return self._record_cache[key]

    def mesh_meta(self, tier_dir: Path | None, design_hash: str | None) -> dict:
        if tier_dir is None or not design_hash:
            return {}
        key = ("mesh", str(tier_dir), design_hash)
        if key not in self._meta_cache:
            meta = D._read_json(Path(tier_dir) / "designs" / design_hash / "mesh_meta.json")
            self._meta_cache[key] = meta if isinstance(meta, dict) else {}
        return self._meta_cache[key]

    def search_row(self, tier_dir: Path | None, design_hash: str | None):
        if tier_dir is None or not design_hash:
            return None
        key = str(tier_dir)
        if key not in self._search_cache:
            path = Path(tier_dir) / "search.ndjson"
            rows = D.read_ndjson(path) if path.is_file() else []
            self._search_cache[key] = {
                str(row.get("design_hash")): row for row in rows
                if isinstance(row, Mapping) and row.get("design_hash")}
        return self._search_cache[key].get(design_hash)

    def _manifest_identities(self) -> dict:
        manifest = self._artifact("training_manifest", 2_000_000) or {}
        identities = _mapping(_mapping(manifest.get("meta")).get("identities"))
        return dict(identities)

    # ---- derived per-design facts
    def _pareto(self, attempts: list[Attempt]):
        points: dict[str, dict] = {}
        for attempt in attempts:
            if attempt.tier != "screen" or not attempt.design_hash:
                continue
            cov, rip = _pareto_units(attempt.result)
            if cov is None or rip is None:
                continue
            points.setdefault(attempt.design_hash,
                              {"coverage_deg": cov, "ripple_db": rip,
                               "solve_id": attempt.solve_id})
        payload = self._artifact("pareto_metrics", 4_000_000)
        if payload is not None:
            for oid, item in _mapping(payload.get("observations")).items():
                item = _mapping(item)
                if item.get("status") != "complete":
                    continue
                cov, rip = _finite(item.get("coverage_deg")), _finite(item.get("ripple_db"))
                if cov is None or rip is None:
                    continue
                identity = _mapping(self.identities.get(str(oid)))
                design = identity.get("design_hash")
                if isinstance(design, str) and design:
                    points.setdefault(design, {"coverage_deg": cov, "ripple_db": rip,
                                               "observation_id": str(oid)})
        nondominated = _nondominated_designs(points)
        if points:
            reason = None
        elif self.policy == "pareto":
            reason = ("the pareto policy is recorded but no complete coverage/ripple metric "
                      "is available")
        else:
            reason = (f"the study policy is {self.policy}; no complete coverage/ripple metric "
                      "is recorded")
        return points, nondominated, reason

    def _incumbents(self, attempts: list[Attempt]) -> dict[str, tuple[bool, str | None]]:
        out: dict[str, tuple[bool, str | None]] = {}
        best: float | None = None
        for attempt in attempts:
            if attempt.tier != "screen" or attempt.result.get("kind") != "screen":
                continue
            eligible = attempt.result.get("eligible") is True
            j = _finite(attempt.result.get("observed_j"))
            if eligible and j is not None:
                if best is None or j < best:
                    out[attempt.solve_id] = (True, None)
                    best = j
                else:
                    out[attempt.solve_id] = (False, "did not improve the running best")
            else:
                out[attempt.solve_id] = (False, "not an eligible measured screen solve")
        return out

    def row_facts(self, tier_dir: Path | None, attempt: Attempt) -> dict:
        record = self.design_record(tier_dir, attempt.design_hash)
        family = record.get("family") or self.config(tier_dir).get("family")
        meta = self.mesh_meta(tier_dir, attempt.design_hash)
        result = _mapping(meta.get("result"))
        summary = _mapping(meta.get("summary"))
        bbox = result.get("bbox_m") or summary.get("bbox_m")
        dimensions = None
        if bbox:
            dimensions = D.horn_dims({"bbox_m": bbox, "quadrants": result.get("quadrants")})
        if dimensions is None:
            search = self.search_row(tier_dir, attempt.design_hash)
            if search:
                dimensions = D.horn_dims(search)
        dimensions_reason = (None if dimensions is not None
                             else "no recorded mesh bounding box for this design")
        descriptors = attempt.candidate.get("descriptors")
        if not isinstance(descriptors, Mapping):
            descriptors = attempt.result.get("descriptors")
        descriptors = descriptors if isinstance(descriptors, Mapping) else None
        descriptors_reason = (None if descriptors is not None
                              else "no descriptors are recorded for this candidate")
        if family:
            typology_reason = ("typology is not a separately recorded field; the recorded "
                               f"geometry family is {family}")
        else:
            typology_reason = "neither a geometry family nor a typology is recorded"
        return {
            "dimensions": dimensions, "dimensions_reason": dimensions_reason,
            "descriptors": descriptors, "descriptors_reason": descriptors_reason,
            "family": family, "typology": None, "typology_reason": typology_reason,
        }


def _program_identity(ctx: Context, tier_dir: Path | None) -> dict:
    """Resolved objective/brief/config identities, or nulls with an explicit reason."""
    run_json = D._read_json(Path(tier_dir) / "run.json") if tier_dir is not None else {}
    run_json = run_json if isinstance(run_json, Mapping) else {}
    config = D._config(tier_dir) if tier_dir is not None else {}
    task = _mapping((_artifact_data(ctx.service, ctx.study_id, "snapshot", max_bytes=4_000_000)
                     or {}).get("task"))
    objective_version = (run_json.get("objective_version")
                         or task.get("objective_version"))
    config_name = (run_json.get("name") or config.get("name") or task.get("config_name"))
    brief_name = (task.get("brief_name") or _mapping(config.get("brief")).get("name"))
    brief_sha256 = task.get("brief_sha256")
    fields = {"objective_version": objective_version, "brief_name": brief_name,
              "brief_sha256": brief_sha256, "config_name": config_name}
    missing = [name for name, value in fields.items() if value in (None, "")]
    return {**fields,
            "identity_reason": (None if not missing
                                else "not recorded in the tier run.json/snapshot: "
                                     + ", ".join(missing))}


def _bounded_series(values: list, identities: list, cap: int = MAX_SERIES):
    """Downsample a numeric series and its parallel identity array together."""
    if len(values) <= cap:
        return list(values), list(identities), False
    step = max(1, math.ceil((len(values) - 1) / (cap - 1)))
    keep = list(range(0, len(values), step))
    if keep[-1] != len(values) - 1:
        keep.append(len(values) - 1)
    keep = keep[:cap]
    return [values[i] for i in keep], [identities[i] for i in keep], True


def _convergence(facts: _Facts) -> dict:
    """BO convergence series with a parallel identity per marker (additive to data_bo's shape)."""
    solves, solve_ids, points, point_ids, refusals = [], [], [], [], []
    exploration, exploration_points, exploration_ids = [], [], []
    verify_points, verify_ids = [], []
    best: float | None = None
    screens = 0
    for index, attempt in enumerate(facts.attempts):
        result = attempt.result
        kind = result.get("kind")
        j = _finite(result.get("observed_j"))
        if kind == "screen" and attempt.tier == "screen":
            screens += 1
            if (result.get("outcome") in _REFUSAL_OUTCOMES
                    or result.get("eligible") is False):
                refusals.append(index)
            if j is not None and result.get("eligible") is True:
                ident = {"solve_id": attempt.solve_id, "design_hash": attempt.design_hash}
                solves.append([index, j])
                solve_ids.append(ident)
                best = j if best is None else min(best, j)
                points.append([index, best])
                point_ids.append(ident)
            reason = attempt.candidate.get("selection_reason")
            if (reason in ("maximin_exploration", "exploration", "exploration_fallback")
                    or attempt.candidate.get("exploration") is True):
                exploration.append(index)
                if j is not None:
                    exploration_points.append([index, j])
                    exploration_ids.append({"solve_id": attempt.solve_id,
                                            "design_hash": attempt.design_hash})
        elif kind in ("verify", "audit") or attempt.tier == "verify":
            if j is not None:
                verify_points.append([index, j, kind])
                verify_ids.append({"solve_id": attempt.solve_id,
                                   "design_hash": attempt.design_hash})
    values, ids, truncated_solves = _bounded_series(solves, solve_ids)
    vvalues, vids, truncated_verify = _bounded_series(verify_points, verify_ids)
    pvalues, pids, _ = _bounded_series(points, point_ids)
    evalues, eids, _ = _bounded_series(exploration_points, exploration_ids)
    program = _program_identity(facts.ctx, _tier_dir(facts.ctx, "screen"))
    return {
        "objective_version": program.get("objective_version"),
        "policy": facts.policy,
        "arms": [{
            "id": "bo", "label": "BO", "method": "bo", "policy": facts.policy,
            "solves": values, "identities": ids,
            "points": pvalues, "point_identities": pids,
            "refusals": refusals[:MAX_SERIES],
            "exploration": exploration[:MAX_SERIES],
            "exploration_points": evalues, "exploration_identities": eids,
            "verify_points": vvalues, "verify_identities": vids,
            "screens": screens, "best_j": best,
            "truncated": bool(truncated_solves or truncated_verify),
        }],
        "notes": ["One BO arm is recorded for this study; matched CMA arms live on the Method board.",
                  "Identities are parallel to solves/verify_points and never replace the numeric series."],
    }


def _verify_by_design(attempts: list[Attempt]) -> dict[str, dict]:
    """The best recorded verify/audit result per design hash (physical rows only)."""
    found: dict[str, dict] = {}
    for attempt in attempts:
        if attempt.tier != "verify" or not attempt.design_hash:
            continue
        if attempt.result.get("physical_measurement") is not True:
            continue
        j = _finite(attempt.result.get("observed_j"))
        current = found.get(attempt.design_hash)
        if current is None or (j is not None and (current["j"] is None or j < current["j"])):
            found[attempt.design_hash] = {"available": True, "j": j,
                                          "solve_id": attempt.solve_id,
                                          "kind": attempt.kind}
    return found


def _row(ctx: Context, attempt: Attempt, verify: dict, facts: _Facts,
         tier: str = "screen") -> dict | None:
    if attempt.design_hash is None:
        return None
    state, reason, flags = _observation_state(ctx, attempt, tier)
    tier_dir = _tier_dir(ctx, tier)
    coverage, ripple = _pareto_units(attempt.result)
    predicted = attempt.candidate.get("predicted")
    params = attempt.candidate.get("params") if isinstance(attempt.candidate.get("params"), dict) \
        else attempt.result.get("params")
    facts_row = facts.row_facts(tier_dir, attempt)
    new_incumbent, incumbent_reason = facts.incumbent.get(
        attempt.solve_id, (False, "not an eligible measured screen solve"))
    design = attempt.design_hash
    pareto = design in facts.pareto_points
    nondominated = design in facts.nondominated
    pareto_reason = None if pareto else (
        facts.pareto_reason or "no complete coverage/ripple metric is recorded for this design")
    bound_preview = bool(state == "predicted_only" and not flags.get("design_dir"))
    screen_j = (_finite(attempt.result.get("observed_j"))
                if attempt.result.get("kind") == "screen"
                and attempt.result.get("eligible") is True else None)
    verify_entry = verify.get(design)
    verified_j = verify_entry.get("j") if isinstance(verify_entry, Mapping) else None
    return D.clean({
        "solve_id": attempt.solve_id,
        "attempt_id": attempt.attempt_id,
        "observation_seq": (attempt.observation or {}).get("observation_seq"),
        "tier": tier,
        "kind": attempt.kind,
        "design_hash": design,
        "state": state,
        "reason": reason,
        "j": _finite(attempt.result.get("observed_j")),
        "screen_j": screen_j,
        "verified_j": verified_j,
        "eligible": attempt.result.get("eligible") is True,
        "outcome": attempt.result.get("outcome") if isinstance(attempt.result.get("outcome"), str) else None,
        "coverage_deg": coverage,
        "ripple_db": ripple,
        "params": params if isinstance(params, Mapping) else None,
        "predicted": predicted if isinstance(predicted, Mapping) else None,
        "artifact": flags,
        "verify": verify_entry,
        "dimensions": facts_row["dimensions"],
        "dimensions_reason": facts_row["dimensions_reason"],
        "descriptors": facts_row["descriptors"],
        "descriptors_reason": facts_row["descriptors_reason"],
        "family": facts_row["family"],
        "typology": facts_row["typology"],
        "typology_reason": facts_row["typology_reason"],
        "new_incumbent": bool(new_incumbent),
        "incumbent_reason": incumbent_reason,
        "pareto": bool(pareto),
        "nondominated": bool(nondominated),
        "pareto_reason": pareto_reason,
        "bound_preview": bound_preview,
    })


def _sort_key(row: Mapping, sort: str):
    j = row.get("j")
    seq = row.get("observation_seq")
    seq_key = seq if isinstance(seq, int) else 10 ** 12
    if sort == "best_j":
        return (j is None, j if j is not None else 0.0, seq_key)
    if sort == "worst_j":
        return (j is None, -(j if j is not None else 0.0), seq_key)
    if sort == "screen_j":
        value = row.get("screen_j")
        return (value is None, value if value is not None else 0.0, seq_key)
    if sort == "verified_j":
        value = row.get("verified_j")
        return (value is None, value if value is not None else 0.0, seq_key)
    return (seq_key, j if j is not None else math.inf)


def _normalize_states(state):
    """``state=`` accepts one value, a comma list, or repeated query values."""
    if state is None:
        return None
    values: list[str] = []
    if isinstance(state, str):
        values = state.split(",")
    elif isinstance(state, (list, tuple)):
        for item in state:
            values.extend(str(item).split(","))
    else:
        raise ValueError("state filter must be a string or a list")
    out: list[str] = []
    for value in values:
        value = str(value).strip()
        if not value:
            continue
        if value not in STATES:
            raise ValueError(f"unknown state {value!r}; must be one of {STATES}")
        if value not in out:
            out.append(value)
    return out or None


def _optional_bool(name: str, value):
    if value is None:
        return None
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be a boolean")
    return value


def observations(index, study_id: str, *, root_id=None, runs_root=None, page: int = 1,
                 page_size: int = DEFAULT_PAGE_SIZE, sort: str = "best_j", q: str | None = None,
                 state=None, verified=None, new_incumbent=None, pareto=None,
                 nondominated=None, include_predicted: bool = False) -> dict:
    """Small, paginated listing of a study's physical observations.

    Rows are the registry's observations (one per unique physical identity) plus any screen
    attempt that has not yet been observed.  Verify and audit attempts are attached to their
    design as ``verify`` evidence rather than duplicated as candidates.  No mesh, curve or
    balloon payload is loaded here.

    Filters compose with pagination and are echoed in ``filters``.  ``include_predicted``
    defaults to false (bound-preview/predicted markers are never rendered as candidates); when
    true, such rows carry ``bound_preview: true`` so a browser can filter them.  ``pareto=true``
    filters the recorded-metric participation flag; ``nondominated=true`` selects the measured
    coverage/ripple frontier.
    """
    if isinstance(page, bool) or not isinstance(page, int) or page < 1:
        raise ValueError("page must be a positive integer")
    if isinstance(page_size, bool) or not isinstance(page_size, int) or not 1 <= page_size <= MAX_PAGE_SIZE:
        raise ValueError(f"page_size must be in 1..{MAX_PAGE_SIZE}")
    if sort not in SORTS:
        raise ValueError(f"unknown sort {sort!r}; must be one of {SORTS}")
    state_filter = _normalize_states(state)
    verified_filter = _optional_bool("verified", verified)
    incumbent_filter = _optional_bool("new_incumbent", new_incumbent)
    pareto_filter = _optional_bool("pareto", pareto)
    nondominated_filter = _optional_bool("nondominated", nondominated)
    if not isinstance(include_predicted, bool):
        raise ValueError("include_predicted must be a boolean")
    if q is not None:
        if not isinstance(q, str):
            raise ValueError("q must be a string")
        q = q.strip() or None
    applied = {"q": q, "state": state_filter or [], "verified": verified_filter,
               "new_incumbent": incumbent_filter, "pareto": pareto_filter,
               "nondominated": nondominated_filter,
               "include_predicted": include_predicted}
    ctx = _context(index, study_id, root_id, runs_root)
    if ctx.state != "ok":
        return D.clean({
            "study_id": study_id, "root": ctx.root.get("id"), "tiers": list(TIERS),
            "page": page, "page_size": page_size, "sort": sort, "n_total": 0,
            "n_unfiltered": 0, "n_pages": 0, "states": {}, "rows": [],
            "filters": applied, "convergence": None,
            "status": ctx.state, "reason": ctx.reason,
        })
    attempts = _load_attempts(ctx.service, study_id)
    facts = _Facts(ctx, attempts)
    verify = _verify_by_design(attempts)
    rows = []
    for attempt in attempts:
        if attempt.observation is None and attempt.tier != "screen":
            continue          # only pending *screen* picks are listed before they are observed
        if attempt.observation is None and attempt.design_hash is None:
            continue          # a bound pool preview is not a candidate
        row = _row(ctx, attempt, verify, facts, tier=attempt.tier)
        if row is not None:
            rows.append(row)
    n_unfiltered = len(rows)
    if not include_predicted:
        rows = [row for row in rows
                if row["state"] != "predicted_only" and not row["bound_preview"]]
    if state_filter:
        selected = set(state_filter)
        rows = [row for row in rows if row["state"] in selected]
    if verified_filter is not None:
        rows = [row for row in rows if (row["verify"] is not None) is verified_filter]
    if incumbent_filter is not None:
        rows = [row for row in rows if bool(row["new_incumbent"]) is incumbent_filter]
    if pareto_filter is not None:
        rows = [row for row in rows if bool(row["pareto"]) is pareto_filter]
    if nondominated_filter is not None:
        rows = [row for row in rows if bool(row["nondominated"]) is nondominated_filter]
    if q:
        needle = q.lower()

        def _matches(row):
            haystack = [row.get("solve_id"), row.get("attempt_id"), row.get("design_hash"),
                        row.get("reason") or "",
                        json.dumps(row.get("params") or {}, sort_keys=True, default=str)]
            return any(needle in str(value).lower() for value in haystack)

        rows = [row for row in rows if _matches(row)]
    applied["state"] = state_filter or []
    rows.sort(key=lambda row: _sort_key(row, sort))
    counts: dict[str, int] = {state_name: 0 for state_name in STATES}
    for row in rows:
        counts[row["state"]] = counts.get(row["state"], 0) + 1
    n_total = len(rows)
    n_pages = (n_total + page_size - 1) // page_size
    start = (page - 1) * page_size
    return D.clean({
        "study_id": study_id,
        "root": ctx.root.get("id"),
        "root_label": ctx.root.get("label"),
        "tiers": list(TIERS),
        "page": page,
        "page_size": page_size,
        "sort": sort,
        "n_total": n_total,
        "n_unfiltered": n_unfiltered,
        "n_pages": n_pages,
        "states": counts,
        "filters": applied,
        "rows": rows[start:start + page_size],
        "convergence": _convergence(facts),
        "status": "ok",
        "reason": None,
    })


# --------------------------------------------------------------------------- detail


def _tier_availability(ctx: Context, design_hash: str | None) -> dict:
    out = {}
    for tier in TIERS:
        tier_dir = _tier_dir(ctx, tier)
        state, reason = _run_identity(ctx, tier_dir, tier)
        flags = _artifact_flags(None)
        if state == "ok" and design_hash:
            try:
                flags = _artifact_flags(_design_dir(ctx, tier_dir, design_hash))
            except ValueError:
                pass
        out[tier] = {"state": state, "reason": reason, **flags}
    return out


def observation_detail(index, study_id: str, solve_id: str, *, root_id=None,
                       runs_root=None) -> dict:
    """One observation's identity, typed state and artifact availability (no heavy payload)."""
    ctx = _context(index, study_id, root_id, runs_root)
    attempt = _attempt_for(ctx.service, study_id, solve_id)
    state, reason, flags = _observation_state(ctx, attempt, attempt.tier)
    verify = _verify_by_design(_load_attempts(ctx.service, study_id)).get(attempt.design_hash)
    return D.clean({
        "study_id": study_id,
        "root": ctx.root.get("id"),
        "root_label": ctx.root.get("label"),
        "solve_id": attempt.solve_id,
        "attempt_id": attempt.attempt_id,
        "observation_seq": (attempt.observation or {}).get("observation_seq"),
        "tier": attempt.tier,
        "kind": attempt.kind,
        "design_hash": attempt.design_hash,
        "state": state,
        "reason": reason,
        "j": _finite(attempt.result.get("observed_j")),
        "eligible": attempt.result.get("eligible") is True,
        "outcome": attempt.result.get("outcome"),
        "coverage_deg": _pareto_units(attempt.result)[0],
        "ripple_db": _pareto_units(attempt.result)[1],
        "params": attempt.candidate.get("params") if isinstance(attempt.candidate.get("params"), Mapping) else None,
        "predicted": attempt.candidate.get("predicted") if isinstance(attempt.candidate.get("predicted"), Mapping) else None,
        "acquisition": attempt.candidate.get("acquisition") if isinstance(attempt.candidate.get("acquisition"), Mapping) else None,
        "selection_reason": attempt.candidate.get("selection_reason"),
        "fallback": attempt.candidate.get("fallback"),
        "identities": {
            "solve_id": attempt.solve_id,
            "design_hash": attempt.design_hash,
            "geometry_hash": attempt.candidate.get("geometry_hash") or attempt.result.get("geometry_hash"),
            "geometry_id": attempt.candidate.get("geometry_id") or attempt.result.get("geometry_id"),
            "physical_id": attempt.result.get("physical_id"),
            "score_id": attempt.result.get("score_id"),
            "metric_id": attempt.result.get("metric_id"),
            "mesh_hash": attempt.result.get("mesh_hash"),
            "solve_hash": attempt.result.get("solve_hash"),
        },
        "artifact": flags,
        "tiers": _tier_availability(ctx, attempt.design_hash),
        "verify": verify,
    })


# --------------------------------------------------------------------------- payload endpoints


def _envelope(ctx: Context, attempt: Attempt, tier: str, state: str, reason: str | None) -> dict:
    return {
        "study_id": ctx.study_id,
        "root": ctx.root.get("id"),
        "root_label": ctx.root.get("label"),
        "solve_id": attempt.solve_id,
        "attempt_id": attempt.attempt_id,
        "tier": tier,
        "kind": attempt.kind,
        "design_hash": attempt.design_hash,
        "state": state,
        "reason": reason,
    }


def _wall_profile(ctx: Context, tier_dir: Path | None, attempt: Attempt, flags: dict):
    """The stored wall ``profile`` polyline when acoustics curves exist for this tier."""
    if attempt.design_hash is None or tier_dir is None or not flags.get("metrics"):
        return None, "no acoustics curves are recorded for this design tier"
    try:
        design_dir = _design_dir(ctx, tier_dir, attempt.design_hash)
        curves = D.design_curves_at(design_dir, tier_dir, attempt.design_hash)
    except ValueError as exc:
        return None, str(exc)
    profile = curves.get("profile") if isinstance(curves, Mapping) else None
    if profile:
        return profile, None
    return None, "the stored wall profile is unavailable"


def geometry(index, study_id: str, solve_id: str, *, root_id=None, runs_root=None,
             tier: str = "screen") -> dict:
    """Stored solved mesh, or a clearly-labelled geometry-only no-BEM preview (GET only)."""
    ctx = _context(index, study_id, root_id, runs_root)
    attempt = _attempt_for(ctx.service, study_id, solve_id)
    tier_dir = _tier_dir(ctx, tier)
    state, reason, flags = _observation_state(ctx, attempt, tier)

    if state == "stale":
        # Identity validation failed: never serve a payload as if it were this observation's.
        out = _envelope(ctx, attempt, tier, "stale", reason)
        out.update({"source": None, "preview": False, "geometry": None,
                    "profile": None, "profile_reason": "identity validation failed"})
        return D.clean(out)

    if attempt.design_hash and tier_dir is not None:
        try:
            design_dir = _design_dir(ctx, tier_dir, attempt.design_hash)
        except ValueError as exc:
            out = _envelope(ctx, attempt, tier, "stale", str(exc))
            out.update({"source": None, "preview": False, "geometry": None,
                        "profile": None, "profile_reason": str(exc)})
            return D.clean(out)
    else:
        design_dir = None

    profile, profile_reason = _wall_profile(ctx, tier_dir, attempt, flags)

    if flags["mesh"]:
        try:
            mesh = D.mesh_surface_at(design_dir, tier_dir, attempt.design_hash)
        except (FileNotFoundError, ValueError, OSError) as exc:
            out = _envelope(ctx, attempt, tier, "missing_artifact", f"Stored mesh unreadable: {exc}")
            out.update({"source": "stored_mesh", "preview": False, "geometry": None,
                        "profile": None, "profile_reason": f"Stored mesh unreadable: {exc}"})
            return D.clean(out)
        out = _envelope(ctx, attempt, tier, state, reason)
        out.update({"source": "stored_mesh", "preview": False, "notice": None,
                    "geometry": mesh, "profile": profile, "profile_reason": profile_reason})
        return D.clean(out)

    capable, why = _preview_capability(ctx, attempt, tier_dir)
    if capable:
        pstate, payload, preason = _materialize_preview(ctx, attempt, tier_dir)
        out = _envelope(ctx, attempt, tier, pstate,
                        preason if pstate != "geometry_only" else reason)
        out.update({
            "source": "preview",
            "preview": True,
            "notice": ("Geometry-only preview from the pinned design/config; this is NOT the "
                       "stored solved surface and no BEM was run."),
            "geometry": payload,
            "profile": profile,
            "profile_reason": profile_reason,
        })
        return D.clean(out)

    final = "unsupported_geometry" if why and "CAD" in why else "missing_artifact"
    out = _envelope(ctx, attempt, tier, final, why or "No stored mesh or preview is available.")
    out.update({"source": None, "preview": False, "geometry": None,
                "profile": None, "profile_reason": profile_reason})
    return D.clean(out)


def acoustics(index, study_id: str, solve_id: str, *, root_id=None, runs_root=None,
              tier: str = "screen") -> dict:
    """Stored per-frequency/polar curves for one design (no BEM, no re-scoring)."""
    ctx = _context(index, study_id, root_id, runs_root)
    attempt = _attempt_for(ctx.service, study_id, solve_id)
    tier_dir = _tier_dir(ctx, tier)
    state, reason, flags = _observation_state(ctx, attempt, tier)
    out = _envelope(ctx, attempt, tier, state, reason)
    program = _program_identity(ctx, tier_dir)
    if state == "stale":
        out.update({"objective_version": None, "brief_name": None, "brief_sha256": None,
                    "config_name": None,
                    "identity_reason": "identity is not served for a stale observation",
                    "curves": None})
        return D.clean(out)
    out.update(program)
    curves = None
    if attempt.design_hash and tier_dir is not None:
        try:
            design_dir = _design_dir(ctx, tier_dir, attempt.design_hash)
            curves = D.design_curves_at(design_dir, tier_dir, attempt.design_hash)
        except ValueError as exc:
            out["state"], out["reason"] = "stale", str(exc)
    if curves is None:
        if out["state"] == "measured":
            out["state"] = "missing_artifact"
        out["reason"] = out["reason"] or "metrics.json is missing for this design."
    elif out["state"] not in ("measured",):
        # metrics.json exists: report the missing acoustics array explicitly without inventing it.
        if not flags["response"]:
            out["state"] = "missing_artifact"
            out["reason"] = "metrics.json exists but response.npz is missing."
    out["curves"] = curves
    return D.clean(out)


def balloon(index, study_id: str, solve_id: str, *, root_id=None, runs_root=None,
            tier: str = "screen") -> dict:
    """Stored balloon for one design, or an explicit missing-artifact state (no BEM)."""
    ctx = _context(index, study_id, root_id, runs_root)
    attempt = _attempt_for(ctx.service, study_id, solve_id)
    tier_dir = _tier_dir(ctx, tier)
    state, reason, flags = _observation_state(ctx, attempt, tier)
    out = _envelope(ctx, attempt, tier, state, reason)
    if state == "stale":
        out["balloon"] = None
        return D.clean(out)
    payload = None
    if attempt.design_hash and tier_dir is not None and flags["response"]:
        try:
            design_dir = _design_dir(ctx, tier_dir, attempt.design_hash)
            payload = D.balloon_at(design_dir / "response.npz", design_dir,
                                   run_id=None, design=attempt.design_hash)
            # Keep a non-measured attempt's typed state; a cached payload is not a measurement.
            if attempt.result.get("physical_measurement") is True:
                out["state"], out["reason"] = "measured", None
        except ValueError as exc:
            payload = None
            out["state"], out["reason"] = "missing_artifact", f"Stored balloon absent: {exc}"
        except (OSError, KeyError) as exc:
            payload = None
            out["state"], out["reason"] = "missing_artifact", f"Stored balloon unreadable: {exc}"
    elif out["state"] == "measured":
        out["state"] = "missing_artifact"
        out["reason"] = "response.npz is missing for this design."
    out["balloon"] = payload
    return D.clean(out)


__all__ = [
    "STATES", "TIERS", "acoustics", "balloon", "geometry", "observation_detail", "observations",
]
