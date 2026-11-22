"""Deterministic, read-only funnel ledger for the HORN + VENTED-WOOFER system study.

The screening study (``system_runs/**/woofer_seed.json``) ranks woofer boxes against a horn
balloon, but a screen row is not evidence that a BEM case exists, solved, or contains both
channels.  This module joins each shortlist row to the case directories under
``system_runs/system/<experiment>/<case>/`` by ``seed.candidate_id`` and reports where the
funnel loses rows.

The ledger is deliberately honest about what it cannot prove:

* a join is by candidate id only -- never by asset id or driver id.  Asset-only diagnostics are
  labelled ``ASSET_ONLY_NOT_CANDIDATE``;
* a case with no ``adapter_spec.json`` seed is counted as "no join key", not guessed;
* the false-negative audit reports ``FALSE_NEGATIVE_AUDIT_INSUFFICIENT_PAIRS`` whenever no
  shortlist candidate reaches a solved two-channel (woofer + horn) case, and includes the true
  pair count;
* DSP summation and GUI solves are owner-gated, so the ledger stops there with explicit tokens.

The scan mirrors the discovery/status rules of :mod:`tools.data.system_cases` (same
``woofer_seed.json`` convention, same solved/staged/refused/invalid precedence) but keeps the
standard library only and never imports that tool, the solver or the GUI.

Read-only over ``system_runs/``.  The only writes happen when :func:`write_ledger` is called.

API::

    ledger = build_ledger(Path("."))
    print(render_markdown(ledger))
    write_ledger(ledger, Path("scratch/funnel"))
"""
from __future__ import annotations

import json
import math
import os
import re
from pathlib import Path
from typing import Any, Iterable

SCHEMA = "hornlab.system.funnel_ledger.v1"

#: Explicit funnel stop / loss tokens.  Order is meaningful: gate order, then audit.
TOKENS = (
    "NO_BEM_CASE_FOR_CANDIDATE",
    "BEM_CASE_STAGED_NOT_SOLVED",
    "BEM_CHANNEL_MISSING",
    "BEM_BAND_OUT_OF_RANGE",
    "DSP_SUM_LOCKED_OWNER_DECISION_3",
    "GUI_SOLVE_DISABLED_OWNER_DECISION_6",
    "FALSE_NEGATIVE_AUDIT_INSUFFICIENT_PAIRS",
)

#: Asset-level diagnostics are never a candidate join.
ASSET_ONLY_LABEL = "ASSET_ONLY_NOT_CANDIDATE"

#: Experiment/case path parts that are not study records (mirrors ``system_cases``).
SKIP_PARTS = frozenset({"_fixtures", "__pycache__", ".git"})

#: A case directory is a UTC timestamp prefix (``20261118T225108Z-...``).
CASE_DIR_RE = re.compile(r"^\d{8}T\d{6}Z")

#: Error text that marks a BL generator/validator refusal (not an adapter crash).
REFUSAL_PHRASES = (
    "refus",
    "must fit inside",
    "must not overlap",
    "does not fit",
    "panel-fit",
    "panel fit",
    "exceeds the panel",
)

#: ``REFUSED`` or a refusal-shaped ``BL_*`` token (``BL_CAPABILITY_OK`` is excluded).
REFUSAL_TOKEN_RE = re.compile(
    r"\bREFUSED\b"
    r"|\bBL_[A-Z0-9_]*(?:REFUS|REJECT|BLOCK|UNAVAIL|INCOMPATIBLE)[A-Z0-9_]*\b"
)

OUTPUT_JSON = "funnel_ledger.json"
OUTPUT_MARKDOWN = "funnel_ledger.md"


# --------------------------------------------------------------------------- small helpers


def _text(value: object) -> str:
    return value if isinstance(value, str) else ""


def _num(value: object) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, str):
        try:
            value = float(value)
        except ValueError:
            return None
    if not isinstance(value, (int, float)):
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def _read_json(path: Path) -> tuple[Any, str | None]:
    """``(data, error)``; never raises."""
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except OSError as exc:
        return None, f"{type(exc).__name__}: {exc}"
    except ValueError as exc:
        return None, f"JSONDecodeError: {exc}"


def _rel(path: Path, root: Path) -> str:
    """Repo-relative POSIX path, or the bare name when the path escapes ``root``."""
    try:
        return Path(os.path.abspath(path)).relative_to(Path(os.path.abspath(root))).as_posix()
    except ValueError:
        pass
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except (ValueError, OSError):
        return path.name


def _reparse_payload(payload: object) -> dict:
    """``payload`` with JSON-encoded dict/list strings parsed once."""
    if not isinstance(payload, dict):
        return {}
    parsed: dict = {}
    for key, value in payload.items():
        if isinstance(value, str) and value[:1] in ("{", "["):
            try:
                parsed[key] = json.loads(value)
                continue
            except ValueError:
                pass
        parsed[key] = value
    return parsed


def _flatten_strings(value: Any, depth: int = 0) -> str:
    """All string values joined (keys are not scanned)."""
    if depth > 8:
        return ""
    if isinstance(value, str):
        return value + "\n"
    if isinstance(value, dict):
        return "".join(_flatten_strings(item, depth + 1) for item in value.values())
    if isinstance(value, (list, tuple)):
        return "".join(_flatten_strings(item, depth + 1) for item in value)
    return ""


def _refusal_reason(payload: dict) -> str | None:
    """A case-level refusal reason, else ``None`` (field ledgers excluded)."""
    result = payload.get("result")
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except ValueError:
            result = None
    if isinstance(result, dict) and result.get("ok") is False:
        error = _text(result.get("error")).strip()
        if error and any(phrase in error.lower() for phrase in REFUSAL_PHRASES):
            return error
    if payload.get("refused") is True:
        return "refused: true"
    match = REFUSAL_TOKEN_RE.search(_flatten_strings(payload))
    return match.group(0) if match else None


def _band(value: object) -> list[float] | None:
    """A ``[low_hz, high_hz]`` band from a list, tuple or ``"low high"`` text."""
    if isinstance(value, str):
        parts = value.replace(",", " ").split()
    elif isinstance(value, (list, tuple)):
        parts = list(value)
    else:
        return None
    values = [_num(item) for item in parts]
    if len(values) != 2 or any(item is None for item in values):
        return None
    low, high = (float(item) for item in values if item is not None)
    if low > high:
        low, high = high, low
    return [low, high]


def _frequencies(value: object) -> list[float]:
    if not isinstance(value, list):
        return []
    return [number for item in value if (number := _num(item)) is not None]


def _channels(excitation_ids: object) -> list[str]:
    """Woofer/horn channels named by excitation port ids."""
    if not isinstance(excitation_ids, list):
        return []
    found: set[str] = set()
    for item in excitation_ids:
        text = _text(item).lower()
        if not text:
            continue
        if "horn" in text:
            found.add("horn")
        if "woofer" in text or "vented" in text:
            found.add("woofer")
    return sorted(found)


# --------------------------------------------------------------------------- screen scan


def _screen_paths(base: Path) -> list[Path]:
    """The same discovery convention as ``tools/data/system_cases._screen_paths``."""
    if not base.is_dir():
        return []
    paths: list[Path] = []
    for path in base.rglob("woofer_seed.json"):
        try:
            parts = path.relative_to(base).parts
        except ValueError:
            parts = path.parts
        if any(part in SKIP_PARTS for part in parts):
            continue
        paths.append(path)
    screens_dir = base / "screens"
    if screens_dir.is_dir():
        known = {item.resolve() for item in paths}
        for path in screens_dir.glob("*/*.json"):
            if path.resolve() in known:
                continue
            data, _error = _read_json(path)
            if isinstance(data, dict) and _text(data.get("schema")).startswith(
                "hornlab.system.woofer_seed"
            ):
                paths.append(path)
    deduped = {path.resolve(): path for path in paths}
    return sorted(deduped.values(), key=lambda item: item.as_posix())


def _screen_row(row: dict, study_id: str | None, path_label: str) -> dict:
    band = _band(row.get("xo_band_hz"))
    return {
        "candidate_id": _text(row.get("candidate_id")) or None,
        "driver_id": _text(row.get("driver_id")) or None,
        "study_id": study_id,
        "source_path": path_label,
        "status": _text(row.get("status")) or None,
        "shortlist_reason": _text(row.get("shortlist_reason")) or None,
        "xo_hz": _num(row.get("xo_hz")),
        "xo_band_hz": band,
    }


def _scan_screens(base: Path, root: Path) -> tuple[list[dict], list[dict], list[dict]]:
    """``(studies, rows, diagnostics)`` for every screen file under ``base``."""
    studies: list[dict] = []
    rows: list[dict] = []
    diagnostics: list[dict] = []
    for path in _screen_paths(base):
        label = _rel(path, root)
        data, error = _read_json(path)
        if not isinstance(data, dict):
            diagnostics.append({"path": label, "reason": error or "screen file is not an object"})
            continue
        study_id = _text(data.get("study_id")) or None
        shortlist: list[Any] = (
            data["shortlist"] if isinstance(data.get("shortlist"), list) else []
        )
        kept: list[Any] = data["kept_rows"] if isinstance(data.get("kept_rows"), list) else []
        rejected: list[Any] = (
            data["rejected_ledger"] if isinstance(data.get("rejected_ledger"), list) else []
        )
        study_rows = [
            _screen_row(row, study_id, label)
            for row in shortlist
            if isinstance(row, dict)
        ]
        rows.extend(study_rows)
        studies.append(
            {
                "study_id": study_id,
                "path": label,
                "schema": _text(data.get("schema")) or None,
                "shortlist_rows": len(shortlist),
                "kept_rows": len(kept),
                "rejected_rows": len(rejected),
                "distinct_shortlist_candidate_ids": len(
                    {
                        row["candidate_id"]
                        for row in study_rows
                        if row["candidate_id"]
                    }
                ),
            }
        )
    studies.sort(key=lambda item: item["path"])
    rows.sort(
        key=lambda item: (
            item["source_path"],
            item["candidate_id"] or "",
            item["driver_id"] or "",
            item["xo_hz"] if item["xo_hz"] is not None else -1.0,
        )
    )
    diagnostics.sort(key=lambda item: item["path"])
    return studies, rows, diagnostics


# --------------------------------------------------------------------------- case scan


def _case_dirs(base: Path) -> tuple[list[tuple[str, Path]], list[dict]]:
    pairs: list[tuple[str, Path]] = []
    diagnostics: list[dict] = []
    if not base.is_dir():
        diagnostics.append({"case_key": None, "reason": "system_runs/system is missing"})
        return pairs, diagnostics
    for experiment_dir in sorted(base.iterdir(), key=lambda item: item.name):
        if not experiment_dir.is_dir() or experiment_dir.name in SKIP_PARTS:
            continue
        if experiment_dir.name.startswith("_"):
            continue
        try:
            entries = sorted(experiment_dir.iterdir(), key=lambda item: item.name)
        except OSError as exc:
            diagnostics.append(
                {"case_key": experiment_dir.name, "reason": f"unreadable experiment dir: {exc}"}
            )
            continue
        for case_dir in entries:
            if not case_dir.is_dir() or not CASE_DIR_RE.match(case_dir.name):
                continue
            pairs.append((experiment_dir.name, case_dir))
    return pairs, diagnostics


def _run_facts(case: Path, payload: dict) -> dict:
    """Run manifest facts with the payload's recorded ``run`` block as a fallback."""
    recorded_raw = payload.get("run")
    recorded = _reparse_payload({"run": recorded_raw}).get("run") if recorded_raw else None
    recorded = recorded if isinstance(recorded, dict) else {}

    detail = {
        "present": False,
        "status": recorded.get("status"),
        "excitation_port_ids": recorded.get("excitation_port_ids"),
        "frequencies_hz": recorded.get("frequencies_hz"),
    }
    path = case / "run" / "manifest.json"
    if not path.is_file():
        return detail
    data, _error = _read_json(path)
    if not isinstance(data, dict):
        return detail
    detail.update(
        {
            "present": True,
            "status": data.get("status"),
            "excitation_port_ids": data.get("excitation_port_ids"),
            "frequencies_hz": data.get("frequencies_hz"),
        }
    )
    return detail


def _case_row(experiment: str, case: Path, root: Path) -> dict:
    manifest, manifest_error = _read_json(case / "manifest.json")
    payload_ok = isinstance(manifest, dict) and isinstance(manifest.get("payload"), dict)
    payload = _reparse_payload(manifest.get("payload")) if payload_ok else {}
    run = _run_facts(case, payload)

    if not payload_ok:
        status = "invalid"
        refusal = None
        refusal_detail = manifest_error or "manifest payload missing"
    elif run.get("present") and _text(run.get("status")) == "complete":
        status = "solved"
        refusal = None
        refusal_detail = None
    else:
        refusal = _refusal_reason(payload)
        status = "refused" if refusal else "staged"
        refusal_detail = refusal

    seed: dict = {}
    adapter, _adapter_error = _read_json(case / "adapter_spec.json")
    if isinstance(adapter, dict) and isinstance(adapter.get("seed"), dict):
        seed = adapter["seed"]

    frequencies = _frequencies(run.get("frequencies_hz"))
    channels = _channels(run.get("excitation_port_ids"))
    candidate_id = _text(seed.get("candidate_id")) or None
    return {
        "experiment": experiment,
        "case": case.name,
        "case_key": f"{experiment}/{case.name}",
        "status": status,
        "solved": status == "solved",
        "refusal": refusal_detail,
        "seed_candidate_id": candidate_id,
        "seed_source_path": _text(seed.get("source_path")) or None,
        "seed_source_sha256": _text(seed.get("source_sha256")) or None,
        "has_join_key": candidate_id is not None,
        "woofer": "woofer" in channels,
        "horn": "horn" in channels,
        "channels": channels,
        "two_channel": {"woofer", "horn"}.issubset(set(channels)),
        "n_frequencies": len(frequencies) or None,
        "freq_min_hz": min(frequencies) if frequencies else None,
        "freq_max_hz": max(frequencies) if frequencies else None,
        "source_path": _rel(case, root),
    }


def _scan_cases(base: Path, root: Path) -> tuple[list[dict], list[dict]]:
    pairs, diagnostics = _case_dirs(base)
    rows: list[dict] = []
    for experiment, case in pairs:
        try:
            rows.append(_case_row(experiment, case, root))
        except Exception as exc:  # noqa: BLE001 - a malformed case must never stop the ledger
            diagnostics.append(
                {
                    "case_key": f"{experiment}/{case.name}",
                    "reason": f"unexpected {type(exc).__name__}: {exc}",
                }
            )
    rows.sort(key=lambda item: (item["experiment"], item["case"]))
    diagnostics.sort(key=lambda item: (item["case_key"] or "", item["reason"]))
    return rows, diagnostics


# --------------------------------------------------------------------------- join


def _covers(case: dict, band: list[float] | None) -> bool:
    if band is None:
        return False
    low = case.get("freq_min_hz")
    high = case.get("freq_max_hz")
    if low is None or high is None:
        return False
    return float(low) <= band[0] and float(high) >= band[1]


def _join(rows: list[dict], cases: list[dict]) -> dict:
    by_candidate: dict[str, list[dict]] = {}
    without_key = 0
    for case in cases:
        candidate = case.get("seed_candidate_id")
        if candidate:
            by_candidate.setdefault(candidate, []).append(case)
        else:
            without_key += 1
    for matches in by_candidate.values():
        matches.sort(key=lambda item: item["case_key"])

    row_reports: list[dict] = []
    counts = {
        "shortlist_rows": len(rows),
        "matched_rows": 0,
        "missing_case_rows": 0,
        "solved_rows": 0,
        "staged_rows": 0,
        "refused_rows": 0,
        "invalid_rows": 0,
        "missing_channel_rows": 0,
        "band_miss_rows": 0,
    }
    paired_pairs: set[tuple[str, str]] = set()
    paired_candidates: set[str] = set()

    for row in rows:
        candidate = row.get("candidate_id")
        matches = by_candidate.get(candidate or "", [])
        solved_cases = [case for case in matches if case["status"] == "solved"]
        two_channel_cases = [case for case in solved_cases if case["two_channel"]]

        if not matches:
            outcome = "missing_case"
            counts["missing_case_rows"] += 1
        elif solved_cases:
            outcome = "solved"
            counts["solved_rows"] += 1
        elif any(case["status"] == "refused" for case in matches):
            outcome = "refused"
            counts["refused_rows"] += 1
        elif any(case["status"] == "staged" for case in matches):
            outcome = "staged"
            counts["staged_rows"] += 1
        else:
            outcome = "invalid"
            counts["invalid_rows"] += 1
        if matches:
            counts["matched_rows"] += 1

        missing_channel = bool(solved_cases) and not two_channel_cases
        if missing_channel:
            counts["missing_channel_rows"] += 1
        band_miss = bool(two_channel_cases) and not any(
            _covers(case, row["xo_band_hz"]) for case in two_channel_cases
        )
        if band_miss:
            counts["band_miss_rows"] += 1
        if two_channel_cases:
            # The first solved two-channel case is the deterministic attribution target.
            pair = two_channel_cases[0]
            if candidate:
                paired_pairs.add((candidate, pair["case_key"]))
                paired_candidates.add(candidate)

        row_reports.append(
            {
                "candidate_id": candidate,
                "driver_id": row.get("driver_id"),
                "source_path": row.get("source_path"),
                "study_id": row.get("study_id"),
                "status": row.get("status"),
                "xo_hz": row.get("xo_hz"),
                "xo_band_hz": row.get("xo_band_hz"),
                "outcome": outcome,
                "case_keys": [case["case_key"] for case in matches],
                "solved_case_keys": [case["case_key"] for case in solved_cases],
                "missing_channel": missing_channel,
                "band_miss": band_miss,
            }
        )

    row_reports.sort(
        key=lambda item: (
            item["source_path"] or "",
            item["candidate_id"] or "",
            item["driver_id"] or "",
            item["xo_hz"] if item["xo_hz"] is not None else -1.0,
        )
    )
    counts["shortlist_rows_with_solved_two_channel_case"] = sum(
        1
        for report in row_reports
        if any(
            case["two_channel"]
            for case in by_candidate.get(report["candidate_id"] or "", [])
            if case["status"] == "solved"
        )
    )

    return {
        "counts": counts,
        "distinct_shortlist_candidate_ids": len(
            {row["candidate_id"] for row in rows if row.get("candidate_id")}
        ),
        "distinct_joined_cases": len({case["case_key"] for case in cases if case.get("has_join_key")}),
        "cases_without_join_key": without_key,
        "joined_cases_by_status": _status_counts(
            [case for case in cases if case.get("has_join_key")]
        ),
        "paired_candidate_case_pairs": len(paired_pairs),
        "candidate_ids_with_solved_two_channel_case": len(paired_candidates),
        "rows": row_reports,
    }


def _status_counts(cases: Iterable[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for case in cases:
        counts[case["status"]] = counts.get(case["status"], 0) + 1
    return {key: counts[key] for key in sorted(counts)}


# --------------------------------------------------------------------------- ledger


def _tokens(join: dict) -> list[str]:
    emitted: set[str] = set()
    if join["counts"]["missing_case_rows"]:
        emitted.add("NO_BEM_CASE_FOR_CANDIDATE")
    if join["counts"]["staged_rows"]:
        emitted.add("BEM_CASE_STAGED_NOT_SOLVED")
    if join["counts"]["missing_channel_rows"]:
        emitted.add("BEM_CHANNEL_MISSING")
    if join["counts"]["band_miss_rows"]:
        emitted.add("BEM_BAND_OUT_OF_RANGE")
    # DSP summation and GUI solves are owner-gated stops, not scan conditions.
    emitted.add("DSP_SUM_LOCKED_OWNER_DECISION_3")
    emitted.add("GUI_SOLVE_DISABLED_OWNER_DECISION_6")
    if not join["candidate_ids_with_solved_two_channel_case"]:
        emitted.add("FALSE_NEGATIVE_AUDIT_INSUFFICIENT_PAIRS")
    return [token for token in TOKENS if token in emitted]


def build_ledger(
    root: Path | str,
    *,
    screens_root: Path | str | None = None,
    system_root: Path | str | None = None,
) -> dict:
    """Build the read-only funnel ledger.

    ``screens_root`` defaults to ``<root>/system_runs`` (the tree containing every
    ``woofer_seed.json``); ``system_root`` defaults to ``<root>/system_runs/system``.
    """
    root = Path(root)
    base_screens = Path(screens_root) if screens_root is not None else root / "system_runs"
    base_system = Path(system_root) if system_root is not None else root / "system_runs" / "system"

    studies, rows, screen_diagnostics = _scan_screens(base_screens, root)
    cases, case_diagnostics = _scan_cases(base_system, root)
    join = _join(rows, cases)

    study_ids = sorted({study["study_id"] for study in studies if study["study_id"]})
    duplicate_study_ids = sorted(
        study_id
        for study_id in study_ids
        if sum(1 for study in studies if study["study_id"] == study_id) > 1
    )
    screens_census = {
        "files": len(studies),
        "unique_study_ids": len(study_ids),
        "duplicate_study_ids": duplicate_study_ids,
        "shortlist_rows": sum(study["shortlist_rows"] for study in studies),
        "kept_rows": sum(study["kept_rows"] for study in studies),
        "rejected_rows": sum(study["rejected_rows"] for study in studies),
        "distinct_shortlist_candidate_ids": len(
            {row["candidate_id"] for row in rows if row["candidate_id"]}
        ),
    }
    cases_census = {
        "case_dirs": len(cases),
        "by_status": _status_counts(cases),
        "solved": sum(1 for case in cases if case["status"] == "solved"),
        "with_join_key": sum(1 for case in cases if case["has_join_key"]),
        "without_join_key": sum(1 for case in cases if not case["has_join_key"]),
        "two_channel": sum(1 for case in cases if case["two_channel"]),
    }

    audit = {
        "distinct_shortlist_candidate_ids": join["distinct_shortlist_candidate_ids"],
        "candidate_ids_with_solved_two_channel_case": join[
            "candidate_ids_with_solved_two_channel_case"
        ],
        "solved_two_channel_pairs": join["paired_candidate_case_pairs"],
        "shortlist_rows_with_solved_two_channel_case": join["counts"][
            "shortlist_rows_with_solved_two_channel_case"
        ],
        "pair_count": join["paired_candidate_case_pairs"],
        "token": (
            "FALSE_NEGATIVE_AUDIT_INSUFFICIENT_PAIRS"
            if not join["candidate_ids_with_solved_two_channel_case"]
            else None
        ),
        "note": (
            "No shortlist candidate reaches a solved two-channel (woofer + horn) case; the "
            "false-negative audit has insufficient paired data on this store."
            if not join["candidate_ids_with_solved_two_channel_case"]
            else "At least one shortlist candidate reaches a solved two-channel case."
        ),
    }

    ledger = {
        "schema": SCHEMA,
        "read_only": True,
        "source": {
            "root": _rel(root, root),
            "screens_root": _rel(base_screens, root),
            "system_root": _rel(base_system, root),
        },
        "tokens": _tokens(join),
        "screen_census": screens_census,
        "case_census": cases_census,
        "join": join,
        "false_negative_audit": audit,
        "asset_only_diagnostic": {
            "label": ASSET_ONLY_LABEL,
            "note": "Asset/driver ids are never used as a join key; candidate_id is primary.",
        },
        "diagnostics": {
            "screens": screen_diagnostics,
            "cases": case_diagnostics,
        },
        "screens": studies,
        "cases": cases,
    }
    return ledger


# --------------------------------------------------------------------------- rendering / writing


def _fmt(value: object) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:g}"
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value)


def render_markdown(ledger: dict) -> str:
    """Render a deterministic Markdown view of a funnel ledger."""
    screens = ledger.get("screen_census") or {}
    cases = ledger.get("case_census") or {}
    join = ledger.get("join") or {}
    counts = join.get("counts") or {}
    audit = ledger.get("false_negative_audit") or {}
    source = ledger.get("source") or {}

    lines = [
        "# System funnel ledger",
        "",
        f"Schema: `{ledger.get('schema')}`  ",
        f"Read-only: {_fmt(ledger.get('read_only'))}  ",
        f"Root: `{source.get('root', '.')}`  ",
        f"Screens root: `{source.get('screens_root', '-')}`  ",
        f"System root: `{source.get('system_root', '-')}`",
        "",
        "## Tokens",
        "",
    ]
    tokens = ledger.get("tokens") or []
    if tokens:
        lines.extend(f"- `{token}`" for token in tokens)
    else:
        lines.append("- (none)")
    lines.extend(
        [
            "",
            "## Screen census",
            "",
            "| metric | value |",
            "| --- | --- |",
        ]
    )
    for key in (
        "files",
        "unique_study_ids",
        "shortlist_rows",
        "kept_rows",
        "rejected_rows",
        "distinct_shortlist_candidate_ids",
    ):
        lines.append(f"| {key} | {_fmt(screens.get(key))} |")
    lines.extend(
        [
            "",
            "## Case census",
            "",
            "| metric | value |",
            "| --- | --- |",
            f"| case_dirs | {_fmt(cases.get('case_dirs'))} |",
            f"| solved | {_fmt(cases.get('solved'))} |",
            f"| with_join_key | {_fmt(cases.get('with_join_key'))} |",
            f"| without_join_key | {_fmt(cases.get('without_join_key'))} |",
            f"| two_channel | {_fmt(cases.get('two_channel'))} |",
        ]
    )
    for status, value in sorted((cases.get("by_status") or {}).items()):
        lines.append(f"| status:{status} | {_fmt(value)} |")
    lines.extend(
        [
            "",
            "## Join (candidate_id primary)",
            "",
            "| metric | value |",
            "| --- | --- |",
        ]
    )
    for key in (
        "shortlist_rows",
        "matched_rows",
        "missing_case_rows",
        "solved_rows",
        "staged_rows",
        "refused_rows",
        "invalid_rows",
        "missing_channel_rows",
        "band_miss_rows",
        "distinct_shortlist_candidate_ids",
        "distinct_joined_cases",
        "cases_without_join_key",
        "paired_candidate_case_pairs",
        "candidate_ids_with_solved_two_channel_case",
    ):
        lines.append(f"| {key} | {_fmt(join.get(key))} |")
    lines.extend(
        [
            "",
            "## False-negative audit",
            "",
            f"- token: {('`' + audit['token'] + '`') if audit.get('token') else '(not emitted)'}",
            f"- pair_count: {_fmt(audit.get('pair_count'))}",
            f"- note: {_fmt(audit.get('note'))}",
            "",
            "## Shortlist rows",
            "",
            "| source | candidate | driver | xo_hz | band_hz | outcome | cases | missing_channel | band_miss |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in join.get("rows") or []:
        band = row.get("xo_band_hz")
        band_text = "-" if not band else f"{_fmt(band[0])}..{_fmt(band[1])}"
        lines.append(
            "| {source} | {candidate} | {driver} | {xo} | {band} | {outcome} | {cases} | "
            "{missing} | {miss} |".format(
                source=row.get("source_path"),
                candidate=_fmt(row.get("candidate_id")),
                driver=_fmt(row.get("driver_id")),
                xo=_fmt(row.get("xo_hz")),
                band=band_text,
                outcome=_fmt(row.get("outcome")),
                cases=", ".join(row.get("case_keys") or []) or "-",
                missing=_fmt(row.get("missing_channel")),
                miss=_fmt(row.get("band_miss")),
            )
        )
    lines.extend(
        [
            "",
            "## Case rows",
            "",
            "| case | status | channels | freq_hz | seed_candidate_id | source_sha256 |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for case in ledger.get("cases") or []:
        if case.get("freq_min_hz") is None:
            freq = "-"
        else:
            freq = f"{_fmt(case['freq_min_hz'])}..{_fmt(case['freq_max_hz'])}"
        sha = case.get("seed_source_sha256")
        lines.append(
            "| {case} | {status} | {channels} | {freq} | {candidate} | {sha} |".format(
                case=case.get("case_key"),
                status=case.get("status"),
                channels=",".join(case.get("channels") or []) or "-",
                freq=freq,
                candidate=_fmt(case.get("seed_candidate_id")),
                sha=(sha[:12] if isinstance(sha, str) else "-"),
            )
        )
    lines.append("")
    return "\n".join(lines)


def write_ledger(ledger: dict, out_dir: Path | str) -> dict[str, str]:
    """Write ``funnel_ledger.json`` + ``funnel_ledger.md`` under ``out_dir``.

    Nothing is written unless this function is called.  Returns the two written paths.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / OUTPUT_JSON
    md_path = out / OUTPUT_MARKDOWN
    json_path.write_text(
        json.dumps(ledger, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    md_path.write_text(render_markdown(ledger), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
