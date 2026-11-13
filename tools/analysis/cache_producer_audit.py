"""S2 read-only cache producer compatibility audit.

Reports, from source and from a BOUNDED sample of the two solve-cache roots:

* every source-level reader/writer of the solve cache and of the mesh cache,
* the current key/validity semantics (design-mesh-solve; a hit checks ``ok``/readability,
  not the library versions that produced the entry),
* how much sampled legacy evidence lacks producer pins (``unknown``, not "miss"),
* a reversible opt-in producer-policy PROPOSAL only.

It never deletes, rewrites, migrates or opens an unbounded number of cache entries,
never imports the solver/mesher and never touches the network. The only writes are the
two requested artifact files (``cache_producer_audit.json`` / ``.md``), and an ``--out``
inside a cache root is refused.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

TOOL_VERSION = "1.0.0"
ARTIFACT_JSON = "cache_producer_audit.json"
ARTIFACT_MD = "cache_producer_audit.md"
DEFAULT_SAMPLE_LIMIT = 200

#: Top-level entry names are ``<design>-<mesh>-<solve>`` (solve/cache.py::key).
KEY_RE = re.compile(r"^(?P<design>[0-9a-f]+)-(?P<mesh>[0-9a-f]+)-(?P<solve>[0-9a-f]+)$")

#: Provenance fields a producer-aware entry would carry. Current status.json/meta have none.
PRODUCER_STATUS_KEYS = ("lib_shas", "producer", "producer_pins", "library_versions")
PRODUCER_META_KEYS = ("lib_shas", "producer", "producer_pins", "library_versions",
                      "mesher_sha", "solver_sha")

#: Consumer modules inspected statically (AST; nothing is imported or executed).
SOLVE_CACHE_CALLS = {"lookup", "lookup_status", "store", "key", "entry_dir",
                     "load_response", "save_response", "copy_entry"}
MESH_CACHE_CALLS = {"build_mesh", "mesh_cache_key", "prebuilt_key", "_copy_entry",
                    "_load_cached"}
CONSUMER_FILES = (
    "hornlab_search/solve/cache.py",
    "hornlab_search/mesh/build.py",
    "hornlab_search/search/evaluate.py",
    "hornlab_search/report/html.py",
    "hornlab_search/compare/hornfab_side.py",
    "hornlab_search/compare/fake.py",
    "hornlab_search/metrics/acoustic_v2.py",
    "hornlab_search/objective/replay.py",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)


def _sha256_file(path: Path) -> str | None:
    try:
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def _sample_evenly(names: list[str], limit: int) -> list[str]:
    """Deterministic, spread over the sorted keys (not just the lexicographic prefix)."""
    if limit <= 0 or not names:
        return []
    if len(names) <= limit:
        return list(names)
    step = len(names) / float(limit)
    return [names[min(int(i * step), len(names) - 1)] for i in range(limit)]


class _CallCollector(ast.NodeVisitor):
    def __init__(self):
        self.stack: list[str] = []
        self.calls: list[dict] = []

    def _visit_func(self, node):
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    visit_FunctionDef = _visit_func
    visit_AsyncFunctionDef = _visit_func

    def visit_Call(self, node):
        symbol = None
        source = None
        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name) and node.func.value.id == "solve_cache":
                symbol, source = node.func.attr, "solve_cache"
        elif isinstance(node.func, ast.Name):
            if node.func.id in MESH_CACHE_CALLS:
                symbol, source = node.func.id, "mesh_cache"
        if source is not None and (symbol in SOLVE_CACHE_CALLS or symbol in MESH_CACHE_CALLS):
            self.calls.append({
                "line": int(getattr(node, "lineno", 0)),
                "function": ".".join(self.stack) or "<module>",
                "symbol": symbol,
                "source": source,
                "kwargs": [kw.arg for kw in node.keywords if kw.arg],
            })
        self.generic_visit(node)


def _role(rel: str, func: str, symbol: str, line: int) -> str:
    """Human role for a discovered call site. Unknown sites still get an honest generic role."""
    if rel == "hornlab_search/search/evaluate.py":
        if func == "_seam_check":
            return ("band-split seam probe: read a one-frequency response then write it; "
                    "no producer-pin check")
        if func == "_compute_band_split":
            return ("band-split per-band solve: read hit or write response; key is "
                    "design+per-band-mesh+band-solve")
        if func == "_compute_meh":
            return ("MEH single-mesh solve: read hit or write the BEM response for CPU "
                    "re-scoring; no producer-pin check")
        if func == "_compute":
            return ("normal single-mesh solve: read hit or write response; no producer-pin "
                    "check")
        if func == "_persist":
            return "run artifact copy of the response (not a cache lookup)"
        if func == "_write_design_artifacts":
            return "run artifact copy of the response (not a cache lookup)"
    if rel == "hornlab_search/mesh/build.py":
        if symbol == "_copy_entry" and line and line > 450:
            return "mesh cache writer: copy the built mesh into the shared mesh cache"
        if symbol == "_copy_entry":
            return "mesh cache reader: copy a cached mesh into the run directory"
        if symbol == "_load_cached":
            return "mesh cache reader: load cached mesh metadata"
        if symbol in ("mesh_cache_key", "prebuilt_key"):
            return "mesh cache key builder (design+mesh+mounting/rear factor)"
        if symbol == "build_mesh":
            return "mesh cache read/write entry point (cache_dir optional)"
    if rel == "hornlab_search/solve/cache.py":
        return "solve-cache implementation: internal response/status read or write"
    if rel == "hornlab_search/report/html.py":
        return "report reader: load a run's response artifact"
    if rel == "hornlab_search/compare/hornfab_side.py":
        return "independent compare-side response reader/writer (not the search cache)"
    if rel == "hornlab_search/compare/fake.py":
        return "fake-response fixture writer (not a solve-cache entry)"
    if rel == "hornlab_search/metrics/acoustic_v2.py":
        return "legacy metric reader: load a stored response artifact"
    if rel == "hornlab_search/objective/replay.py":
        return "replay reader: load a stored response artifact for zero-solve scoring"
    generic = {
        "lookup": "solve-cache reader",
        "lookup_status": "solve-cache status reader",
        "store": "solve-cache writer",
        "key": "solve-cache key builder",
        "entry_dir": "solve-cache path builder",
        "load_response": "response reader",
        "save_response": "response writer",
        "copy_entry": "cache entry copy/hardlink",
        "build_mesh": "mesh cache read/write entry point",
        "mesh_cache_key": "mesh cache key builder",
        "prebuilt_key": "mesh prefetch key builder",
        "_copy_entry": "mesh cache copy",
        "_load_cached": "mesh cache reader",
    }
    return generic.get(symbol, "cache-related call")


def source_coverage(repo_root: Path) -> dict:
    """Static AST scan of the known cache consumers; returns one record per call site."""
    callers: list[dict] = []
    scanned: list[str] = []
    problems: list[str] = []
    for rel in CONSUMER_FILES:
        path = repo_root / rel
        if not path.is_file():
            problems.append(f"{rel}: missing (excluded from caller coverage)")
            continue
        scanned.append(rel)
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        except (OSError, SyntaxError) as exc:
            problems.append(f"{rel}: unreadable ({type(exc).__name__}: {exc})")
            continue
        collector = _CallCollector()
        collector.visit(tree)
        for call in collector.calls:
            callers.append({
                "file": rel,
                "line": call["line"],
                "function": call["function"],
                "specificity": call["source"],
                "symbol": call["symbol"],
                "role": _role(rel, call["function"], call["symbol"], call["line"]),
                "kwargs": call["kwargs"],
            })
    callers.sort(key=lambda c: (c["file"], c["line"], c["symbol"]))
    return {
        "files_scanned": scanned,
        "files_missing": problems,
        "n_call_sites": len(callers),
        "callers": callers,
        "method": "Python AST over the fixed consumer list; no module is imported or executed",
    }


def _read_entry(path: Path, *, want_hashes: bool) -> dict:
    """Read ONE entry within the sample cap. Never writes; any error is data, not a crash."""
    status_path = path / "status.json"
    response_path = path / "response.npz"
    out = {
        "key": path.name,
        "key_parts": None,
        "status_present": status_path.is_file(),
        "response_present": response_path.is_file(),
        "status_ok": None,
        "status_keys": [],
        "meta_keys": [],
        "npz_keys": [],
        "producer_evidence": "unknown",
        "producer_fields_found": [],
        "markers": {"band_split": False, "seam": False, "trace": False, "normal": False},
        "score_only_reusable": False,
        "read_error": None,
        "bytes": 0,
        "sha256_status": None,
        "sha256_response": None,
    }
    m = KEY_RE.match(path.name)
    if m:
        out["key_parts"] = m.groupdict()
    for p in (status_path, response_path):
        try:
            out["bytes"] += int(p.stat().st_size)
        except OSError:
            pass
    if want_hashes:
        if out["status_present"]:
            out["sha256_status"] = _sha256_file(status_path)
        if out["response_present"]:
            out["sha256_response"] = _sha256_file(response_path)

    status = None
    if out["status_present"]:
        try:
            status = json.loads(status_path.read_text(encoding="utf-8"))
            if not isinstance(status, dict):
                raise ValueError("status.json is not an object")
            out["status_keys"] = sorted(status)
            out["status_ok"] = status.get("ok") is True
        except (OSError, ValueError) as exc:
            out["read_error"] = f"status: {type(exc).__name__}: {exc}"
            status = None

    meta = None
    if out["response_present"]:
        try:
            import numpy as np            # local: the tool runs without importing hornlab_search
            with np.load(response_path, allow_pickle=False) as z:
                out["npz_keys"] = sorted(z.files)
                meta = json.loads(str(z["meta"])) if "meta" in z.files else {}
                if not isinstance(meta, dict):
                    meta = {}
                out["meta_keys"] = sorted(meta)
                out["markers"]["trace"] = any(k in z.files for k in ("p_h", "p_v", "p_balloon"))
        except Exception as exc:          # noqa: BLE001 - a corrupt entry is a finding
            out["read_error"] = (out["read_error"] + "; " if out["read_error"] else "") + \
                f"response: {type(exc).__name__}: {exc}"

    found = []
    if isinstance(status, dict):
        found += [k for k in PRODUCER_STATUS_KEYS if status.get(k)]
    if isinstance(meta, dict):
        found += [k for k in PRODUCER_META_KEYS if meta.get(k)]
    out["producer_fields_found"] = sorted(set(found))
    if out["producer_fields_found"]:
        out["producer_evidence"] = "present"

    if isinstance(meta, dict):
        out["markers"]["band_split"] = bool(
            "band_edges_hz" in meta or "band_split" in meta)
        out["markers"]["seam"] = "seam_check" in meta
        out["markers"]["normal"] = bool(
            "quadrants" in meta or "symmetry_plane" in meta or "mesh_policy" in meta)
    out["score_only_reusable"] = bool(out["status_ok"] and out["response_present"]
                                      and not out["read_error"])
    return out


def inventory_root(root: Path, *, sample_limit: int) -> dict:
    """Bounded inventory of one cache root. Listing only names; parsing capped."""
    rec = {
        "root": str(root),
        "exists": root.is_dir(),
        "entry_count": 0,
        "entry_count_scope": "full top-level directory listing (names only; no open/parse)",
        "sample_limit": int(sample_limit),
        "sampled_entry_count": 0,
        "sampling": "evenly spaced over lexicographically sorted top-level entry names",
        "sampled_bytes": 0,
        "sampled_status_ok": 0,
        "sampled_status_not_ok": 0,
        "sampled_status_missing": 0,
        "sampled_response_missing": 0,
        "sampled_read_errors": 0,
        "keys_parsed": 0,
        "keys_unparsed": 0,
        "unique_design_hashes": 0,
        "unique_mesh_hashes": 0,
        "unique_solve_hashes": 0,
        "producer_evidence_present": 0,
        "producer_evidence_unknown": 0,
        "status_keys_seen": [],
        "meta_keys_seen": [],
        "markers": {"band_split": 0, "seam": 0, "trace": 0, "normal": 0},
        "score_only_reusable": 0,
        "entries": [],
    }
    if not rec["exists"]:
        return rec
    try:
        names = sorted(p.name for p in root.iterdir() if p.is_dir())
    except OSError as exc:
        rec["read_error"] = f"{type(exc).__name__}: {exc}"
        return rec
    rec["entry_count"] = len(names)
    sample = _sample_evenly(names, sample_limit)
    rows = [_read_entry(root / name, want_hashes=True) for name in sample]
    rec["entries"] = rows
    rec["sampled_entry_count"] = len(rows)
    rec["sampled_bytes"] = sum(r["bytes"] for r in rows)
    rec["sampled_status_ok"] = sum(1 for r in rows if r["status_ok"] is True)
    rec["sampled_status_not_ok"] = sum(1 for r in rows if r["status_ok"] is False)
    rec["sampled_status_missing"] = sum(1 for r in rows if not r["status_present"])
    rec["sampled_response_missing"] = sum(1 for r in rows if not r["response_present"])
    rec["sampled_read_errors"] = sum(1 for r in rows if r["read_error"])
    rec["keys_parsed"] = sum(1 for r in rows if r["key_parts"])
    rec["keys_unparsed"] = len(rows) - rec["keys_parsed"]
    rec["unique_design_hashes"] = len({r["key_parts"]["design"] for r in rows if r["key_parts"]})
    rec["unique_mesh_hashes"] = len({r["key_parts"]["mesh"] for r in rows if r["key_parts"]})
    rec["unique_solve_hashes"] = len({r["key_parts"]["solve"] for r in rows if r["key_parts"]})
    rec["producer_evidence_present"] = sum(1 for r in rows if r["producer_evidence"] == "present")
    rec["producer_evidence_unknown"] = len(rows) - rec["producer_evidence_present"]
    rec["status_keys_seen"] = sorted({k for r in rows for k in r["status_keys"]})
    rec["meta_keys_seen"] = sorted({k for r in rows for k in r["meta_keys"]})
    for marker in rec["markers"]:
        rec["markers"][marker] = sum(1 for r in rows if r["markers"][marker])
    rec["score_only_reusable"] = sum(1 for r in rows if r["score_only_reusable"])
    return rec


def _proposal() -> dict:
    return {
        "status": "proposal_only_no_enforcement",
        "behavior_changed": False,
        "policy": {
            "name": "opt_in_producer_pin_v1",
            "default": "off (today's key/validity behavior is unchanged)",
            "check": ("on an opt-in lookup, compare the entry's recorded producer evidence "
                      "with the current library pins/solve-spec identity; a missing or "
                      "mismatching pin is a MISS, never an error and never a rewrite"),
            "legacy": ("legacy entries with unknown producer evidence stay UNKNOWN: the opt-in "
                       "guard may miss them, but the audit does not relabel them as known-good "
                       "or blanket-delete them"),
            "unknown_is_not_miss_today": True,
        },
        "rollout": [
            "ship the audit artifact only; no cache behavior change",
            "add a config/tool flag that is off by default and covers every solve-cache caller",
            "in an isolated temp root, prove producer evidence is written on new entries and "
            "that an unknown/mismatched legacy entry misses while an unchanged score-only hit "
            "still hits",
            "only after a separate approved slice, enable the flag for a bounded lane",
        ],
        "rollback": [
            "turn the opt-in flag off (default path is byte-compatible)",
            "delete only the temp-root fixtures, never production cache entries",
            "the audit artifact records the pre-change key/validity finding for comparison",
        ],
        "temp_only_compatibility_fixtures": [
            "new entry with producer pins -> hit",
            "entry with no producer pins -> unknown, opt-in miss",
            "entry with mismatched pins -> miss",
            "score-only re-scoring of an unchanged response -> hit",
            "band-split seam entry -> covered by the same policy",
            "trace/normal entry -> covered by the same policy",
        ],
        "caller_coverage_required_before_enforcement": [
            "search/evaluate.py:_compute (normal single-mesh read/write)",
            "search/evaluate.py:_compute_band_split (per-band read/write)",
            "search/evaluate.py:_seam_check (seam-only read/write)",
            "search/evaluate.py:_compute_meh (MEH read/write)",
            "mesh/build.py (mesh-cache read/write, separate key space)",
            "report/compare/replay readers (run artifacts, not the shared solve cache)",
        ],
        "explicit_unknowns": [
            "the real reuse fraction of legacy entries cannot be measured from a bounded sample",
            "whether every legacy producer used the same installed library pins is unknown",
            "band-split/seam/trace marker coverage is sampled, not an exhaustive census",
            "no measured solve-cost or ranking impact is claimed here",
        ],
    }


def build_report(cache_roots, *, sample_limit: int = DEFAULT_SAMPLE_LIMIT,
                 repo_root: Path | None = None, generated_utc: str | None = None) -> dict:
    """Build the deterministic audit payload. ``generated_utc`` can be frozen for tests."""
    repo = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[2]
    roots = [Path(r) for r in cache_roots]
    inv = [inventory_root(r, sample_limit=sample_limit) for r in roots]
    unknown = sum(r["producer_evidence_unknown"] for r in inv)
    sampled = sum(r["sampled_entry_count"] for r in inv)
    entries = sum(r["entry_count"] for r in inv)
    return {
        "tool": "cache_producer_audit",
        "tool_version": TOOL_VERSION,
        "generated_utc": generated_utc or _utc_now(),
        "behavior_changed": False,
        "no_cache_writes": True,
        "write_policy": ("only the two --out artifact files are written; no cache entry is "
                         "created, modified, deleted or migrated"),
        "inputs": {
            "repo_root": str(repo),
            "cache_roots": [{"requested": str(r), "resolved": str(r.resolve())} for r in roots],
            "sample_limit": int(sample_limit),
        },
        "key_finding": {
            "key_format": "{design_hash}-{mesh_hash}-{solve_hash}",
            "source": "hornlab_search/solve/cache.py::key",
            "lookup_validity": ("status.json with ok:true AND a loadable response.npz; nothing "
                                "else. Corrupt/absent/ok:false is a miss, never an error."),
            "producer_pins_checked": False,
            "library_pins_in_status": False,
            "library_pins_in_response_meta": False,
            "solving_library_version_identity": "not part of the key or the hit check",
            "v7_throat_gate_note": ("search/evaluate.py runs the v7 throat gate before the "
                                    "solve-cache lookup, so a stored response cannot bypass "
                                    "that one newer physical check; this is not a general "
                                    "producer-pin guard."),
        },
        "source_caller_coverage": source_coverage(repo),
        "inventory": {
            "roots": inv,
            "totals": {
                "entry_count": entries,
                "sampled_entry_count": sampled,
                "sample_limit": int(sample_limit),
                "sampled_bytes": sum(r["sampled_bytes"] for r in inv),
                "producer_evidence_present": sum(r["producer_evidence_present"] for r in inv),
                "producer_evidence_unknown": unknown,
                "score_only_reusable": sum(r["score_only_reusable"] for r in inv),
                "markers": {m: sum(r["markers"][m] for r in inv)
                            for m in ("band_split", "seam", "trace", "normal")},
            },
        },
        "risk_summary": {
            "current_finding": ("The key is design-mesh-solve. A successful lookup checks "
                                "ok/readability but not the library pins that produced the "
                                "response, so a legacy entry is reusable by identity alone."),
            "sampled_unknown_producer_evidence": unknown,
            "sampled_unknown_fraction": (round(unknown / sampled, 6) if sampled else None),
            "legacy_reuse_exposure": ("sampled unknown-producer entries are potentially "
                                      "reusable under today's lookup; this is a bounded "
                                      "sample, not a measured reuse count"),
            "explicit_unknowns": [
                "producer provenance of unsampled entries",
                "whether legacy entries were produced by the currently installed pins",
                "actual reuse frequency and acoustic impact (no solves were run)",
                "band-split/seam/trace coverage outside the sample",
            ],
        },
        "proposal": _proposal(),
        "completeness": {
            "bounded_sample_cap": int(sample_limit),
            "parse_scope": ("at most sample_limit entries per root are opened; every entry is "
                            "statted for size and hashed on the sample"),
            "entry_listing": "all top-level entry names are listed; nested files are not walked",
            "excluded": [
                "runs/, dataset/, dataset_cpu/ (not solve-cache roots)",
                "mesh cache roots (different key space; source coverage only)",
                "unsampled entries beyond --sample-limit",
            ],
        },
    }


def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(headers) + " |",
           "| " + " | ".join("---" for _ in headers) + " |"]
    out += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(out)


def to_markdown(payload: dict) -> str:
    inv = payload["inventory"]
    kf = payload["key_finding"]
    risk = payload["risk_summary"]
    lines = [
        "# S2 cache producer compatibility audit (read-only)",
        "",
        f"- generated_utc: `{payload['generated_utc']}`",
        f"- tool: `{payload['tool']} {payload['tool_version']}`",
        f"- behavior_changed: `{str(payload['behavior_changed']).lower()}`",
        f"- no_cache_writes: `{str(payload['no_cache_writes']).lower()}`",
        "",
        "## Key / validity finding",
        "",
        f"- key: `{kf['key_format']}` (`{kf['source']}`)",
        f"- lookup validity: {kf['lookup_validity']}",
        f"- producer library pins checked on lookup: **{str(kf['producer_pins_checked']).lower()}**",
        f"- v7 throat gate: {kf['v7_throat_gate_note']}",
        "",
        "## Cache inventory (bounded sample)",
        "",
    ]
    rows = []
    for r in inv["roots"]:
        rows.append([
            r["root"], str(r["exists"]), str(r["entry_count"]), str(r["sampled_entry_count"]),
            str(r["producer_evidence_present"]), str(r["producer_evidence_unknown"]),
            str(r["score_only_reusable"]),
        ])
    lines.append(_md_table(
        ["root", "exists", "entries (names)", "sampled", "producer present",
         "producer unknown", "score-only reusable"], rows))
    lines += [
        "",
        f"- sample cap: {inv['totals']['sample_limit']} per root; sampled bytes: "
        f"{inv['totals']['sampled_bytes']}",
        f"- markers in sample: {inv['totals']['markers']}",
        "",
        "## Source-level caller coverage",
        "",
    ]
    cov = payload["source_caller_coverage"]
    rows = [[c["file"], str(c["line"]), c["function"], c["role"]]
            for c in cov["callers"]]
    lines.append(_md_table(["file", "line", "function", "role"], rows))
    lines += [
        "",
        f"- method: {cov['method']}; call sites: {cov['n_call_sites']}",
        f"- missing consumer files: {cov['files_missing'] or 'none'}",
        "",
        "## Risk summary",
        "",
        f"- {risk['current_finding']}",
        f"- sampled unknown producer evidence: {risk['sampled_unknown_producer_evidence']} "
        f"(fraction {risk['sampled_unknown_fraction']})",
        f"- legacy reuse exposure: {risk['legacy_reuse_exposure']}",
        "- explicit unknowns:",
    ]
    lines += [f"  - {u}" for u in risk["explicit_unknowns"]]
    prop = payload["proposal"]
    lines += ["", "## Proposal (no enforcement)", "",
              f"- status: `{prop['status']}`; behavior_changed: "
              f"`{str(prop['behavior_changed']).lower()}`",
              f"- policy: {prop['policy']['name']} (default {prop['policy']['default']})"]
    lines += [f"- rollout: {x}" for x in prop["rollout"]]
    lines += [f"- rollback: {x}" for x in prop["rollback"]]
    lines += ["", "Temp-only compatibility fixtures:",
              *[f"- {x}" for x in prop["temp_only_compatibility_fixtures"]],
              "", "Callers an approved guard must cover:",
              *[f"- {x}" for x in prop["caller_coverage_required_before_enforcement"]]]
    lines += ["", "## Completeness / exclusions", ""]
    lines += [f"- {x}" for x in payload["completeness"]["excluded"]]
    lines += [f"- {x}" for x in prop["explicit_unknowns"]]
    return "\n".join(lines) + "\n"


def _inside(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Read-only S2 solve-cache producer compatibility audit.")
    p.add_argument("--cache-root", action="append", dest="cache_roots", default=None,
                   help="cache root to inventory (repeatable; default cache/solve and cache_cpu/solve)")
    p.add_argument("--out", default=str(Path(__file__).resolve().parents[2]
                                        / "docs/evidence/bo_study_2026-11-12/s2"),
                   help="output DIRECTORY for cache_producer_audit.{json,md}")
    p.add_argument("--sample-limit", type=int, default=DEFAULT_SAMPLE_LIMIT,
                   help=f"max entries opened per root (default {DEFAULT_SAMPLE_LIMIT})")
    args = p.parse_args(argv)
    if args.sample_limit < 1:
        p.error("--sample-limit must be >= 1")
    repo = Path(__file__).resolve().parents[2]
    roots = ([Path(x) for x in args.cache_roots] if args.cache_roots
             else [repo / "cache" / "solve", repo / "cache_cpu" / "solve"])
    out_dir = Path(args.out)
    for root in roots:
        if _inside(out_dir, root):
            print(f"refusing --out {out_dir}: it is inside cache root {root}", file=sys.stderr)
            return 2
    payload = build_report(roots, sample_limit=args.sample_limit, repo_root=repo)
    out_dir.mkdir(parents=True, exist_ok=True)
    js = out_dir / ARTIFACT_JSON
    md = out_dir / ARTIFACT_MD
    js.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
                  encoding="utf-8")
    md.write_text(to_markdown(payload), encoding="utf-8")
    print(f"cache producer audit: {payload['inventory']['totals']['entry_count']} entries, "
          f"{payload['inventory']['totals']['sampled_entry_count']} sampled, "
          f"{payload['inventory']['totals']['producer_evidence_unknown']} unknown producer "
          f"evidence -> {js} and {md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
