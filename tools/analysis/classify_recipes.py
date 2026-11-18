"""WP 0.9 / D9 legacy-recipe classification (R12b): which stored design recipes still rebuild?

CPU-only scan over ``runs/``: every ``designs/<hash>/design.json`` generator block is classified
against the LIVE code, nothing in ``runs/`` is modified:

* ``rebuildable``        -- geometry is derived from recipe params (formula families, point grids
                            without a kernel digest), or a ``canonical_record_v2`` body whose
                            inline points re-hash to the recorded ``implementation_sha256``
                            (the gate that ``resolve_grid`` enforces at rebuild), or a
                            kernel-digest recipe whose recorded digest equals the LIVE module
                            digest.
* ``bridge``             -- a kernel-digest recipe (``klangfilm_lame_hv_cd`` /
                            ``klangfilm_lame_hv_core``) whose recorded ``implementation_sha256``
                            no longer equals the live module digest: the recipe is still the
                            record of record, but rebuild-refusal is decided by the kernel gate,
                            not by this digest (R12b: kernel digests are INFORMATIONAL).
* ``record_refused``     -- a ``canonical_record_v2`` body whose inline points do NOT re-hash to
                            the recorded digest: the rebuild gate refuses it today.
* ``unverified``         -- no readable generator block / no digest and no param route.

Ownership note: ``tools/analysis/**`` is Fable-senior-owned (CLAUDE.md R21 row); this tool is the
R12b execution exception assigned to the local orchestrator in LOCAL_AGENT_PROMPT_2026-11-18.md
STEP 4f.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np

REBUILDABLE = "rebuildable"
BRIDGE = "bridge"
RECORD_REFUSED = "record_refused"
UNVERIFIED = "unverified"

#: versioned-generator kinds that pin a kernel implementation digest (informational, R12b).
_KERNEL_KINDS = {
    "klangfilm_lame_hv_cd": "klangfilm_lame_hv_family",
    "klangfilm_lame_hv_core": "klangfilm_lame_hv_core_family",
}


def _points_digest(inner: np.ndarray, sampler_version: str = "record-v2.0") -> str:
    h = hashlib.sha256()
    h.update(f"{sampler_version}|{inner.shape}".encode())
    h.update(np.ascontiguousarray(inner, dtype="<f8").tobytes())
    return h.hexdigest()


def _live_kernel_digest(module_name: str) -> str | None:
    try:
        import importlib
        mod = importlib.import_module(f"hornlab_search.design.generators.{module_name}")
        return mod.implementation_digest()
    except Exception:  # noqa: BLE001 - missing module => cannot verify
        return None


def _rows_blocks(payload: dict) -> list[dict]:
    """The recipe's ``rows`` blocks: saved designs carry the family recipe at
    ``params.grid.rows`` (real design.json shape), inline record bodies may also appear under
    ``generator.spec.rows``. Both are checked; older records keep ``generator.spec``."""
    out: list[dict] = []
    gen = payload.get("generator")
    if not isinstance(gen, dict):
        return out
    for holder in (payload.get("params") if isinstance(payload.get("params"), dict) else {},
                   gen.get("spec") if isinstance(gen.get("spec"), dict) else {}):
        grid = holder.get("grid")
        if isinstance(grid, dict) and isinstance(grid.get("rows"), dict):
            out.append(grid["rows"])
    return out


def classify_design(payload: dict) -> tuple[str, str]:
    """(class, detail) for one design.json payload. Pure; no filesystem access."""
    gen = payload.get("generator")
    if not isinstance(gen, dict):
        # Legacy design.json schema (pre-generator era): {design_hash, family, params}. The
        # design hash and the geometry derive from family + params by construction, so the
        # record rebuilds without any digest - classified rebuildable, schema flagged.
        if payload.get("family") and isinstance(payload.get("params"), dict):
            return REBUILDABLE, "legacy schema (family+params, no generator block): rebuilds from params"
        return UNVERIFIED, "no generator block and no (family, params) route"
    blocks = _rows_blocks(payload)
    kind = str(next((b.get("type") for b in blocks if b.get("type")),
                    payload.get("family") or ""))
    if kind == "canonical_record_v2":
        rows = next((b for b in blocks if b.get("type") == kind), {})
        pts = rows.get("points")
        want = rows.get("implementation_sha256")
        if not isinstance(pts, list) or not want:
            return UNVERIFIED, "canonical_record_v2 without inline points/digest"
        try:
            inner = np.asarray(pts, dtype=float)
            got = _points_digest(inner, str(rows.get("sampler_version") or "record-v2.0"))
        except Exception as exc:  # noqa: BLE001
            return UNVERIFIED, f"points not hashable: {type(exc).__name__}"
        if got == want:
            return REBUILDABLE, "record digest matches (gate passes)"
        return RECORD_REFUSED, f"gate refuses: {str(got)[:12]} != recorded {str(want)[:12]}"
    if kind in _KERNEL_KINDS:
        rows = next((b for b in blocks if b.get("type") == kind and b.get("implementation_sha256")),
                    next((b for b in blocks if b.get("implementation_sha256")), {}))
        want = rows.get("implementation_sha256")
        live = _live_kernel_digest(_KERNEL_KINDS[kind])
        if not want:
            return UNVERIFIED, f"{kind}: no kernel digest recorded"
        if live is None:
            return UNVERIFIED, f"{kind}: live module unavailable"
        if want == live:
            return REBUILDABLE, f"{kind}: kernel information-digest matches live"
        return BRIDGE, f"{kind}: kernel digest moved since save (informational only, R12b)"
    if kind:
        return REBUILDABLE, f"{kind}: geometry derives from recipe params (no kernel digest)"
    return UNVERIFIED, "unrecognised generator block"


def iter_design_files(runs_root: Path):
    for ddir in sorted(runs_root.glob("**/designs")):
        for djson in sorted(ddir.glob("*/design.json")):
            yield djson


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--runs-root", default="runs")
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=None, help="cap files scanned (tests)")
    a = ap.parse_args(argv)
    root = Path(a.runs_root)
    out = Path(a.out)
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"refusing: output dir {out} exists and is not empty")
    counts: Counter[str] = Counter()
    details: Counter[str] = Counter()
    rows: list[dict] = []
    t0 = time.perf_counter()
    scanned = 0
    for djson in iter_design_files(root):
        if a.limit is not None and scanned >= a.limit:
            break
        scanned += 1
        try:
            payload = json.loads(djson.read_text(encoding="utf-8"))
            cls, detail = classify_design(payload)
        except Exception as exc:  # noqa: BLE001 - a malformed record must not stop the scan
            cls, detail = UNVERIFIED, f"unreadable: {type(exc).__name__}"
        counts[cls] += 1
        details[f"{cls}: {detail.split(' (')[0]}"] += 1
        rows.append({"path": str(djson), "class": cls, "detail": detail})
    out.mkdir(parents=True)
    summary = {"runs_root": str(root), "scanned": scanned, "seconds": round(time.perf_counter() - t0, 1),
               "classes": dict(counts), "details": dict(details.most_common(24)),
               "legend": {"rebuildable": REBUILDABLE, "bridge": BRIDGE,
                          "record_refused": RECORD_REFUSED, "unverified": UNVERIFIED}}
    (out / "classify_summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    with (out / "classify_rows.jsonl").open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(json.dumps(summary["classes"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
