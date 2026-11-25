"""Full-identity numerical-floor registry for `tools/analysis` (P0b, 2026-11-21).

The old continuation rule matched a threshold to ``(objective_version, "slope5")``. That is
not an identity: two runs can share an objective version and brief name yet differ in resolved
brief content, score weights/tolerances, solver/backend, mesh fidelity or comparison grid. This
module keys every published floor to the *resolved identity* that produced it and refuses to
lend a threshold to a different identity.

Identity fields (see :func:`identity_from_run`):

* objective version;
* brief -- resolved brief sha256, or the exact resolved brief path + name with a match-quality
  label when the file cannot be resolved;
* score identity hash -- the replay/rescore score fields (score code version, weights,
  objective block, brief hash), built with ``rescore_identity._row_score_identity``;
* physical solver/backend and recorded library pins;
* mesh/fidelity identity (quadrants, mesh policy/epw when recorded);
* comparison grid (frequency-grid hash, angle/balloon grid, mode);
* test method + sample size (registry entries; a run itself has no floor test);
* uncertainty decomposition (deterministic fidelity bias, measured uncertainty, stochastic
  variability where the source provides them).

No GPU, no solve, no writes. Read-only over configs, run metadata and published evidence.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ANALYSIS = Path(__file__).resolve().parent
REPO = ANALYSIS.parents[1]
for _p in (str(ANALYSIS), str(REPO)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from _common import read_json, run_fingerprint  # noqa: E402

TOOL = "floor_registry"
REGISTRY_VERSION = 1
#: Declared "around the floor" band for a borderline continuation gain.
BORDERLINE_MULTIPLIER = 1.25

#: Mesh part of the B1 combined floor (`docs/evidence/b1_mesh_2026-11-18/floor_record.json`).
_MESH_SD_J = 0.007676441842658574
_MESH_MEAN_SIGNED_DJ = -0.012563779662985386
_MESH_PROBES = 8

_V7_BRIEF = "examples/briefs/home_landscape_2026-11-15/room_landscape_80x50_700_hf1440_v7.yaml"
_V10_CORRIDOR_BRIEF = (
    "docs/evidence/v10_rescore_2026-11-18/"
    "home_v10_corridor_preferred_edge_rescore.yaml"
)
_V10_SLOPE5_BRIEF = (
    "examples/briefs/home_landscape_2026-11-18_v10/"
    "room_landscape_80x50_700_hf1440_v10_slope5.yaml"
)
_V10_SHIPPED_BRIEF = (
    "examples/briefs/home_landscape_2026-11-18_v10/"
    "room_landscape_80x50_700_hf1440_v10.yaml"
)
_COMPACT400_BRIEF = (
    "examples/briefs/compact400_2026-11-19/"
    "compact400_xo1000_1400_hf1440_v10xo.yaml"
)


# ------------------------------------------------------------------ small helpers

def _hash(obj) -> str:
    text = json.dumps(obj, sort_keys=True, ensure_ascii=True, separators=(",", ":"),
                      default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canonical_path(path) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(REPO.resolve()).as_posix()
    except (OSError, ValueError):
        return p.as_posix()


def _same_path(a, b) -> bool:
    return _canonical_path(a) == _canonical_path(b)


def _strip_ephemeral(raw: dict | None) -> dict | None:
    """Drop the loader's absolute ``path`` key so the brief hash is location-independent."""
    if not isinstance(raw, dict):
        return None
    out = json.loads(json.dumps(raw, default=str))
    out.pop("path", None)
    return out


def _score_code_sha256(version: int | None) -> str | None:
    """sha256 of the current-checkout score dispatch/scorer files for ``version``.

    ``replay.SCORE_CODE_VERSION`` is the semantic score-code version; this sha pins the exact
    source bytes used for a *resolution in this checkout*. A historical run's own library pins
    live separately in ``solver.lib_shas``.
    """
    names = ["replay.py", "versions.py", "terms.py"]
    if isinstance(version, int):
        names.append("scalar.py" if version <= 1 else f"scalar_v{version}.py")
    base = REPO / "hornlab_search" / "objective"
    h = hashlib.sha256()
    found = False
    for name in sorted(set(names)):
        p = base / name
        if p.is_file():
            h.update(name.encode("utf-8"))
            h.update(p.read_bytes())
            found = True
    return h.hexdigest() if found else None


# ------------------------------------------------------------------ brief resolution

def _brief_from_file(path: Path):
    """Resolve a brief through the real loader and return a path-independent ``Brief``."""
    from hornlab_search.objective.replay import Brief, load_brief_context

    b = load_brief_context(str(path))
    raw = _strip_ephemeral(b.raw)
    if raw is None:
        raise ValueError(f"{path}: resolved brief has no raw mapping")
    return Brief(name=b.name, target=b.target, weights=dict(b.weights),
                 objective_version=b.objective_version,
                 objective_block=(dict(b.objective_block) if b.objective_block else None),
                 objective_params=b.objective_params, raw=raw,
                 source_path=b.source_path)


def _brief_from_raw(raw: dict | None, fallback_name: str | None = None):
    """Build a ``Brief`` from a run's resolved brief snapshot (no file on disk)."""
    raw = _strip_ephemeral(raw)
    if not isinstance(raw, dict):
        return None
    if not isinstance(raw.get("target"), dict) or not isinstance(raw.get("weights"), dict):
        return None
    from hornlab_search.objective.replay import Brief, _params_from_block
    from hornlab_search.targets.spec import Target

    block = dict(raw["objective"]) if isinstance(raw.get("objective"), dict) else None
    version = int((block or {}).get("version", 1))
    try:
        params = _params_from_block(version, block)
    except (TypeError, ValueError):
        params = None
    try:
        target = Target.from_dict(dict(raw["target"]))
    except (TypeError, ValueError):
        return None
    return Brief(name=str(raw.get("name") or fallback_name or ""), target=target,
                 weights=dict(raw["weights"]), objective_version=version,
                 objective_block=block, objective_params=params, raw=raw,
                 source_path=None)


def _component_tail(path, component: str) -> Path | None:
    """Path tail after the last ``component`` part (e.g. ``briefs/x.yaml``)."""
    try:
        parts = Path(path).resolve().parts
    except OSError:  # pragma: no cover - defensive for odd Windows paths
        parts = Path(path).parts
    idxs = [i for i, part in enumerate(parts) if str(part).lower() == component]
    if not idxs:
        return None
    tail = parts[idxs[-1] + 1:]
    return Path(*tail) if tail else None


def _candidate_brief_paths(run_dir: Path, run_json: dict, cfg: dict) -> list[Path]:
    bf = cfg.get("brief_file")
    if not bf:
        return []
    raw = Path(str(bf).replace("\\", "/"))
    out: list[Path] = []
    if raw.is_absolute():
        out.append(raw)
    else:
        cp = run_json.get("config_path")
        if isinstance(cp, str) and cp.strip():
            cpp = Path(cp.replace("\\", "/"))
            base = cpp if cpp.is_absolute() else REPO / cpp
            out.append(base.parent / raw)
        out.extend([run_dir / raw, REPO / raw, REPO / "examples" / raw])

    # A run copied under runs/<x>/ has its own config_path, so a brief_file such as
    # ``../../briefs/<date>/<name>.yaml`` normalizes to <repo>/briefs/... (the ``examples``
    # segment is lost). Re-root the tail after the last ``briefs``/``examples`` component at
    # the repo's examples tree. These are candidates only: resolution still requires is_file()
    # and the resolved brief must produce the matching sha/score identity.
    expanded = list(out)
    for cand in out:
        if cand.is_file():
            continue
        brief_tail = _component_tail(cand, "briefs")
        if brief_tail is not None:
            expanded.append(REPO / "examples" / "briefs" / brief_tail)
        examples_tail = _component_tail(cand, "examples")
        if examples_tail is not None:
            expanded.append(REPO / "examples" / examples_tail)

    seen: set[str] = set()
    dedup: list[Path] = []
    for p in expanded:
        key = _canonical_path(p)
        if key not in seen:
            seen.add(key)
            dedup.append(p)
    return dedup


def _run_brief_identity(run_dir: Path, run_json: dict, cfg: dict) -> dict:
    """Resolve the run's brief and return the brief identity fragment.

    Resolution order: the ``brief_file`` named by the config (when the file exists) -> the
    run's resolved brief snapshot (path/name recorded, sha unavailable) -> unavailable.
    """
    snapshot = cfg.get("brief") if isinstance(cfg.get("brief"), dict) else None
    expected = _candidate_brief_paths(run_dir, run_json, cfg)
    expected_path = _canonical_path(expected[0]) if expected else None
    for cand in expected:
        if cand.is_file():
            try:
                b = _brief_from_file(cand)
                return {"name": b.name, "sha256": b.brief_hash(),
                        "path": _canonical_path(cand), "match_quality": "resolved_file",
                        "_brief": b}
            except (OSError, ValueError, TypeError):
                continue
    name = None
    if snapshot is not None:
        name = snapshot.get("name")
    if not name:
        name = cfg.get("name")
    if snapshot is not None:
        b = _brief_from_raw(snapshot, fallback_name=name)
        if b is not None:
            return {"name": b.name or name, "sha256": None,
                    "path": expected_path, "match_quality": "snapshot_brief_unresolved",
                    "_brief": b}
    return {"name": name, "sha256": None, "path": expected_path,
            "match_quality": "unavailable", "_brief": None}


def _score_identity(version, weights, block, brief) -> dict:
    from rescore_identity import _row_score_identity
    from hornlab_search.objective.replay import SCORE_CODE_VERSION

    payload = {"objective_version": version, "weights": weights}
    score_hash = None
    if isinstance(version, int) and isinstance(weights, dict):
        r = type("_ScoreRow", (), payload)()
        score_hash = _row_score_identity(r, brief, block, SCORE_CODE_VERSION)
    return {
        "hash": score_hash,
        "score_code": SCORE_CODE_VERSION,
        "score_code_sha256": _score_code_sha256(version if isinstance(version, int) else None),
        "weights": weights,
        "weights_hash": _hash(weights) if weights is not None else None,
        "objective_block": block,
        "objective_block_hash": _hash(block) if block is not None else None,
        "brief_hash": brief.brief_hash() if brief is not None else None,
        "brief_name": brief.name if brief is not None else None,
    }


# ------------------------------------------------------------------ run identity

def identity_from_run(run: dict) -> dict:
    """Exact identity of one loaded run (``_common.load_run`` result). Read-only."""
    run_dir = Path(run["run_dir"])
    run_json = read_json(run_dir / "run.json") or {}
    cfg = run.get("config") or {}
    meta = run.get("meta") or {}
    fp = run_fingerprint(run)

    brief_frag = _run_brief_identity(run_dir, run_json, cfg)
    brief = brief_frag.pop("_brief", None)
    version = meta.get("objective_version")
    if not isinstance(version, int):
        version = run_json.get("objective_version")
    if not isinstance(version, int):
        version = (cfg.get("objective") or {}).get("version")
    version = int(version) if isinstance(version, int) else None

    weights = dict(brief.weights) if brief is not None else cfg.get("weights")
    block = (dict(brief.objective_block) if brief is not None and brief.objective_block
             else (dict(cfg["objective"]) if isinstance(cfg.get("objective"), dict) else None))
    if not isinstance(weights, dict):
        weights = None

    solve = (cfg.get("solve") if isinstance(cfg.get("solve"), dict) else None) or {}
    mesh = (cfg.get("mesh") if isinstance(cfg.get("mesh"), dict) else None) or {}
    search = (cfg.get("search") if isinstance(cfg.get("search"), dict) else None) or {}
    grid = dict(fp.get("grid") or {})
    grid.update({"hash": fp.get("grid_hash"), "mode": meta.get("mode")})
    identity = {
        "objective_version": version,
        "brief": {k: brief_frag.get(k) for k in ("name", "sha256", "path", "match_quality")},
        "score_identity": _score_identity(version, weights, block, brief),
        "solver": {
            "backend": grid.get("backend") or run_json.get("backend"),
            "software_hash": fp.get("software_hash"),
            "software_unknown": fp.get("software_unknown"),
            "lib_shas": run_json.get("lib_shas"),
        },
        "fidelity": {
            "quadrants": mesh.get("quadrants"),
            "epw": mesh.get("epw"),
            "rear_res_factor": mesh.get("rear_res_factor"),
            "dof_cap_screen": mesh.get("dof_cap_screen"),
            "dof_cap_verify": mesh.get("dof_cap_verify"),
            "mesh_policy": search.get("infeasible_penalty"),
            "recorded_in_source": any(mesh.get(k) is not None
                                      for k in ("quadrants", "epw", "rear_res_factor")),
        },
        "grid": grid,
        "test": {"method": None, "sample_size": None},
    }
    core = {
        "objective_version": version,
        "brief_sha256": identity["brief"].get("sha256"),
        "brief_name": identity["brief"].get("name"),
        "brief_path": identity["brief"].get("path"),
        "score_identity_hash": identity["score_identity"].get("hash"),
        "backend": identity["solver"].get("backend"),
    }
    identity["hash"] = _hash(core)
    return identity


# ------------------------------------------------------------------ registry entries

def _entry_identity(version: int, brief_path: str) -> tuple[dict, object | None, str | None]:
    path = REPO / brief_path
    try:
        brief = _brief_from_file(path)
    except (OSError, ValueError, TypeError) as exc:  # reported, never hidden
        return ({"objective_version": version,
                 "brief": {"name": Path(brief_path).stem, "sha256": None,
                           "path": brief_path, "match_quality": "unresolved"},
                 "score_identity": _score_identity(version, None, None, None),
                 "solver": {"backend": None, "software_hash": None,
                            "software_unknown": True, "lib_shas": None},
                 "fidelity": {"quadrants": None, "epw": None, "rear_res_factor": None,
                              "dof_cap_screen": None, "dof_cap_verify": None,
                              "mesh_policy": None, "recorded_in_source": False},
                 "grid": {"hash": None, "mode": ["screen", "verify"]},
                 "test": {"method": None, "sample_size": None}}, None,
                f"{type(exc).__name__}: {exc}")
    raw_grid = (brief.raw.get("grid")
                if isinstance(brief.raw.get("grid"), dict) else None) or {}
    identity = {
        "objective_version": version,
        "brief": {"name": brief.name, "sha256": brief.brief_hash(),
                  "path": brief_path, "match_quality": "resolved_file"},
        "score_identity": _score_identity(version, dict(brief.weights),
                                          (dict(brief.objective_block)
                                           if brief.objective_block else None), brief),
        "solver": {"backend": None, "software_hash": None, "software_unknown": True,
                   "lib_shas": None},
        "fidelity": {"quadrants": None, "epw": None, "rear_res_factor": None,
                     "dof_cap_screen": None, "dof_cap_verify": None,
                     "mesh_policy": ("screen->verify same-mesh frequency part; "
                                     "B1 epw x2 mesh part"),
                     "recorded_in_source": False},
        "grid": {
            "hash": None,
            "mode": ["screen", "verify"],
            "screen_extra_hz": raw_grid.get("screen_extra_hz"),
            "verify_points_per_octave": raw_grid.get("verify_points_per_octave"),
            "note": ("floor measured across the brief's screen->verify frequency grids; "
                     "an exact frequency-grid hash is not recorded in the floor artifact"),
        },
        "test": {"method": "screen->verify same-mesh pair difference (sd of screen - verify, "
                            "top-28 by verify J); mesh part = B1 epw x2 probe sd",
                 "sample_size": 257, "top_n": 28},
    }
    identity["hash"] = _hash({
        "objective_version": version,
        "brief_sha256": identity["brief"]["sha256"],
        "brief_name": identity["brief"]["name"],
        "brief_path": identity["brief"]["path"],
        "score_identity_hash": identity["score_identity"]["hash"],
        "backend": None,
    })
    return identity, brief, None


def _uncertainty(freq_mean, mesh_mean, freq_sd, mesh_sd, floor) -> dict:
    combined_bias = None
    if freq_mean is not None and mesh_mean is not None:
        combined_bias = float(freq_mean) + float(mesh_mean)
    return {
        "deterministic_fidelity_bias": {
            "value": combined_bias,
            "frequency_mean_dJ": freq_mean,
            "mesh_mean_dJ": mesh_mean,
            "scope": ("frequency: mean(screen - verify) over all pairs; "
                      "mesh: mean signed dJ over the B1 probes"),
        },
        "measured_uncertainty": {
            "value": floor,
            "frequency_sd_top_J": freq_sd,
            "mesh_sd_J": mesh_sd,
            "combined_J": floor,
            "method": ("sd of same-grid screen->verify J differences (top-28 by verify J) "
                       "combined in quadrature with the B1 mesh sd"),
        },
        "stochastic_variability": {
            "value": None,
            "note": ("not separated from the published screen->verify floor source; "
                     "the floor measures score/grid consistency, not seed-to-seed repeats"),
        },
    }


def _make_entry(entry_id, version, brief_path, floor, freq_sd, freq_mean, source,
                caveat=None) -> dict:
    identity, brief, brief_error = _entry_identity(version, brief_path)
    return {
        "id": entry_id,
        "objective_version": version,
        "floor_J": float(floor),
        "components": {
            "frequency_sd_top_J": float(freq_sd),
            "mesh_sd_J": _MESH_SD_J,
            "combined_J": float(floor),
        },
        "identity": identity,
        "source": source,
        "uncertainty": _uncertainty(freq_mean, _MESH_MEAN_SIGNED_DJ, freq_sd, _MESH_SD_J,
                                    float(floor)),
        "test_method": identity["test"]["method"],
        "sample_size": identity["test"]["sample_size"],
        "mesh_probes": _MESH_PROBES,
        "caveat": caveat,
        "brief_error": brief_error,
    }


def _build_entries() -> list[dict]:
    return [
        _make_entry(
            "v7_home_landscape_this_pass",
            7,
            _V7_BRIEF,
            0.3104791983512361,
            0.31038428576437704,
            -0.204934901864546,
            {
                "kind": "measured_floor",
                "artifacts": [
                    "docs/evidence/b1_mesh_2026-11-18/floor_record.json",
                    "docs/evidence/v10_rescore_2026-11-18/results/floor_v7_summary.json",
                ],
                "command": ("rescore_identity.py floor --brief examples/briefs/"
                            "home_landscape_2026-11-15/room_landscape_80x50_700_hf1440_v7.yaml "
                            "--runs-root runs --top 28"),
                "date": "2026-11-18",
                "note": ("v7 re-pinned to the this-pass stored-J protocol basis by senior "
                         "verdict 2; the published D8 0.13 J variant is recorded in the "
                         "floor record but is NOT a second registry identity"),
            },
        ),
        _make_entry(
            "v10_home_corridor_preferred_edge",
            10,
            _V10_CORRIDOR_BRIEF,
            0.46773899691673904,
            0.46767600053596237,
            0.09246973951521092,
            {
                "kind": "measured_floor",
                "artifacts": [
                    "docs/evidence/b1_mesh_2026-11-18/floor_record.json",
                    "docs/evidence/v10_rescore_2026-11-18/results/floor_v10_offline_summary.json",
                ],
                "command": ("rescore_identity.py floor --brief docs/evidence/"
                            "v10_rescore_2026-11-18/"
                            "home_v10_corridor_preferred_edge_rescore.yaml --runs-root runs "
                            "--top 28"),
                "date": "2026-11-18",
                "note": ("offline rescore-only brief identity that MEASURED the floor. The "
                         "shipped production brief is a separate exact identity and has its "
                         "own registry entry (v10_home_shipped_preferred_edge), never an "
                         "implicit borrow."),
            },
        ),
        _make_entry(
            "v10_home_shipped_preferred_edge",
            10,
            _V10_SHIPPED_BRIEF,
            0.46773899691673904,
            0.46767600053596237,
            0.09246973951521092,
            {
                "kind": "measured_floor",
                "artifacts": [
                    "docs/evidence/b1_mesh_2026-11-18/floor_record.json",
                    "docs/evidence/v10_rescore_2026-11-18/results/floor_v10_offline_summary.json",
                    "docs/evidence/v10_rescore_2026-11-18/README.md",
                ],
                "measured_on": ("examples/briefs/home_landscape_2026-11-18_v10/"
                                "room_landscape_80x50_700_hf1440_v10.yaml"),
                "measurement_brief": _V10_CORRIDOR_BRIEF,
                "command": ("rescore_identity.py floor --brief docs/evidence/"
                            "v10_rescore_2026-11-18/"
                            "home_v10_corridor_preferred_edge_rescore.yaml --runs-root runs "
                            "--top 28"),
                "date": "2026-11-18",
                "note": ("production identity. Its driver/envelope/symmetry/source/target/"
                         "weights/objective blocks are byte-identical to the offline rescore "
                         "brief that measured the floor; only the name/description differ and "
                         "the shipped brief adds the same grid block the stored home runs "
                         "used. The floor is therefore attached to this exact sha, not "
                         "borrowed by matching a brief name."),
            },
        ),
        _make_entry(
            "v10_home_slope5",
            10,
            _V10_SLOPE5_BRIEF,
            0.4863165895744908,
            0.4862562339550117,
            0.10665849520246241,
            {
                "kind": "measured_floor",
                "artifacts": [
                    "docs/evidence/b1_mesh_2026-11-18/floor_record.json",
                    "docs/evidence/v10_rescore_2026-11-18/results/"
                    "floor_v10_slope5_summary.json",
                ],
                "command": ("rescore_identity.py floor --brief examples/briefs/"
                            "home_landscape_2026-11-18_v10/"
                            "room_landscape_80x50_700_hf1440_v10_slope5.yaml "
                            "--runs-root runs --top 28"),
                "date": "2026-11-18",
                "note": "constancy (slope5) variant; its own frequency floor is required",
            },
        ),
        _make_entry(
            "compact400_v10xo",
            10,
            _COMPACT400_BRIEF,
            0.1293,
            0.1291110736609016,
            -0.012194236413658853,
            {
                "kind": "measured_floor",
                "artifacts": [
                    "runs/analysis/compact400_floor_2026-11-19/floor_summary.json",
                    "docs/research/compact400_2026-11-19/README.md",
                    "docs/evidence/b1_mesh_2026-11-18/floor_record.json",
                ],
                "command": ("rescore_identity.py floor --brief examples/briefs/"
                            "compact400_2026-11-19/"
                            "compact400_xo1000_1400_hf1440_v10xo.yaml --runs-root runs "
                            "--top 28 --out runs/analysis/compact400_floor_2026-11-19"),
                "date": "2026-11-19",
                "note": ("frequency part from 257 whole-fleet screen->verify pairs "
                         "(sd_diff_top). The generic v10 floor is NEVER assigned to this "
                         "brief."),
            },
            caveat=("Whole-fleet score-consistency floor of this target set, not a "
                    "repeatability floor measured on 400 mm horns. Re-measure once the "
                    "compact400 lanes have their own screen->verify pairs; until then treat "
                    "gains below about 0.13 J as ties."),
        ),
    ]


ENTRIES: list[dict] = _build_entries()
_ENTRIES_BY_ID = {e["id"]: e for e in ENTRIES}


def entries() -> list[dict]:
    """Public copy of the registry entries (stable order)."""
    return json.loads(json.dumps(ENTRIES, default=str))


def entry(entry_id: str) -> dict | None:
    return _ENTRIES_BY_ID.get(entry_id)


# ------------------------------------------------------------------ matching

def _cmp_value(name, run_value, entry_value, mismatched, missing, unverified):
    if entry_value is None:
        unverified.append(name)
    elif run_value is None:
        missing.append(name)
    elif run_value != entry_value:
        mismatched.append(name)


def _compare(run_identity: dict, ent: dict) -> dict:
    mismatched: list[str] = []
    missing: list[str] = []
    unverified: list[str] = []
    path_name_fallback = False

    r_ver = run_identity.get("objective_version")
    e_ver = ent["identity"].get("objective_version")
    _cmp_value("objective_version", r_ver, e_ver, mismatched, missing, unverified)

    r_brief = run_identity.get("brief") or {}
    e_brief = ent["identity"].get("brief") or {}
    r_sha, e_sha = r_brief.get("sha256"), e_brief.get("sha256")
    if e_sha is None:
        unverified.append("brief.sha256")
    elif r_sha is None:
        rp, ep = r_brief.get("path"), e_brief.get("path")
        name_ok = (r_brief.get("name") is not None
                   and r_brief.get("name") == e_brief.get("name"))
        path_ok = bool(rp) and bool(ep) and _same_path(rp, ep)
        if name_ok and path_ok:
            path_name_fallback = True
        else:
            missing.append("brief.sha256")
            if rp is None:
                missing.append("brief.path")
            elif ep is not None and not path_ok:
                mismatched.append("brief.path")
            if r_brief.get("name") is None:
                missing.append("brief.name")
    elif r_sha != e_sha:
        mismatched.append("brief.sha256")

    r_score = (run_identity.get("score_identity") or {}).get("hash")
    e_score = (ent["identity"].get("score_identity") or {}).get("hash")
    _cmp_value("score_identity.hash", r_score, e_score, mismatched, missing, unverified)

    r_back = (run_identity.get("solver") or {}).get("backend")
    e_back = (ent["identity"].get("solver") or {}).get("backend")
    _cmp_value("solver.backend", r_back, e_back, mismatched, missing, unverified)

    for key in ("quadrants", "epw", "rear_res_factor"):
        rv = (run_identity.get("fidelity") or {}).get(key)
        ev = (ent["identity"].get("fidelity") or {}).get(key)
        _cmp_value(f"fidelity.{key}", rv, ev, mismatched, missing, unverified)

    e_grid = ent["identity"].get("grid") or {}
    r_grid = run_identity.get("grid") or {}
    e_grid_hash = e_grid.get("hash")
    if e_grid_hash is None:
        unverified.append("grid.hash")
    elif r_grid.get("hash") is None:
        missing.append("grid.hash")
    elif r_grid.get("hash") != e_grid_hash:
        mismatched.append("grid.hash")
    modes = e_grid.get("mode")
    if isinstance(modes, list) and modes:
        r_mode = r_grid.get("mode")
        if r_mode is None:
            missing.append("grid.mode")
        elif r_mode not in modes:
            mismatched.append("grid.mode")
    else:
        unverified.append("grid.mode")

    ok = not mismatched and not missing
    if not ok:
        quality = None
    elif path_name_fallback:
        quality = "path_name_unresolved"
    elif unverified:
        quality = "exact_core"
    else:
        quality = "exact"
    return {"ok": ok, "match_quality": quality, "mismatched_fields": mismatched,
            "missing_fields": missing, "unverified_fields": unverified}


def _identity_missing_fields(identity: dict) -> list[str]:
    brief = identity.get("brief") or {}
    score = identity.get("score_identity") or {}
    missing = []
    if identity.get("objective_version") is None:
        missing.append("objective_version")
    if brief.get("sha256") is None:
        missing.append("brief.sha256")
    if not brief.get("name"):
        missing.append("brief.name")
    if score.get("hash") is None:
        missing.append("score_identity.hash")
    return missing


def resolve(identity: dict) -> dict:
    """Resolve an identity to a published floor, or refuse with the missing/mismatched fields."""
    scored = []
    for ent in ENTRIES:
        cmp = _compare(identity, ent)
        rank = {"exact": 3, "exact_core": 2, "path_name_unresolved": 1}.get(
            cmp["match_quality"], 0) if cmp["ok"] else 0
        scored.append((rank, ent, cmp))
    scored.sort(key=lambda row: (-row[0], row[1]["id"]))
    for rank, ent, cmp in scored:
        if cmp["ok"]:
            return {
                "status": "matched",
                "matched_entry": ent["id"],
                "match_quality": cmp["match_quality"],
                "floor_J": ent["floor_J"],
                "source": ent["source"],
                "uncertainty": ent["uncertainty"],
                "caveat": ent["caveat"],
                "test_method": ent["test_method"],
                "sample_size": ent["sample_size"],
                "missing_fields": [],
                "mismatched_fields": [],
                "unverified_fields": cmp["unverified_fields"],
                "why": (f"identity matches floor {ent['id']} "
                        f"({cmp['match_quality']}); floor {ent['floor_J']:.4f} J"),
            }
    # No applicable floor: report the identity fields that are unknown plus the closest
    # candidate's mismatches (fewest mismatched+missing fields, not the alphabetically first).
    # Never substitute another brief's threshold.
    missing = _identity_missing_fields(identity)
    closest = (min(scored,
                   key=lambda row: (len(row[2]["mismatched_fields"])
                                    + len(row[2]["missing_fields"]), row[1]["id"]))
               if scored else None)
    mismatched = list(closest[2]["mismatched_fields"]) if closest else []
    missing = sorted(set(missing) | set(closest[2]["missing_fields"] if closest else []))
    if closest is not None and closest[1]["id"]:
        why = (f"no applicable published floor: run identity does not match "
               f"'{closest[1]['id']}' (mismatched: "
               f"{', '.join(mismatched) or 'none'}; missing: "
               f"{', '.join(missing) or 'none'})")
    else:
        why = "no applicable published floor: registry has no entries"
    return {
        "status": "no_applicable_floor",
        "matched_entry": None,
        "match_quality": None,
        "floor_J": None,
        "source": None,
        "uncertainty": None,
        "caveat": None,
        "test_method": None,
        "sample_size": None,
        "missing_fields": missing,
        "mismatched_fields": mismatched,
        "unverified_fields": [],
        "why": why,
    }


def floor_for_run(run: dict) -> dict:
    """Convenience: identity -> resolution for one loaded run."""
    return resolve(identity_from_run(run))


def identity_summary(identity: dict) -> dict:
    """Compact JSON-safe identity for reports (full identity remains available)."""
    return {
        "objective_version": identity.get("objective_version"),
        "brief": identity.get("brief"),
        "score_identity_hash": (identity.get("score_identity") or {}).get("hash"),
        "score_code": (identity.get("score_identity") or {}).get("score_code"),
        "backend": (identity.get("solver") or {}).get("backend"),
        "fidelity": identity.get("fidelity"),
        "grid": identity.get("grid"),
        "hash": identity.get("hash"),
    }


__all__ = [
    "BORDERLINE_MULTIPLIER",
    "ENTRIES",
    "REGISTRY_VERSION",
    "TOOL",
    "entries",
    "entry",
    "floor_for_run",
    "identity_from_run",
    "identity_summary",
    "resolve",
]
