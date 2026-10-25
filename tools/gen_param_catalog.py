"""Generate / check the parameter catalog artifacts.

    .venv\\Scripts\\python.exe tools/gen_param_catalog.py --write
    .venv\\Scripts\\python.exe tools/gen_param_catalog.py --check
    .venv\\Scripts\\python.exe tools/gen_param_catalog.py

``--write`` regenerates the three artifacts. ``--check`` rebuilds them in memory and
compares byte-for-byte with the committed files, exiting non-zero on any drift. No flag
prints the same check result. The generator FAILS LOUDLY if a symbol anchor or a doc
heading does not resolve; it never emits a stale reference.
"""
from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hornlab_search.design.params.catalog import (  # noqa: E402
    build_catalog,
    catalog_json_bytes,
    render_parameters_markdown,
    render_typologies_markdown,
)
from hornlab_search.design.params.knobs_generators import GENERATOR_KNOBS  # noqa: E402
from hornlab_search.design.params.schema import validate_knob_docs  # noqa: E402

ARTIFACTS = {
    "hornlab_search/gui/static/param-catalog.v1.json": "json",
    "docs/reference/PARAMETERS.md": "markdown-parameters",
    "docs/reference/TYPOLOGIES.md": "markdown-typologies",
}


def _artifact_bytes(catalog: dict) -> dict[str, bytes]:
    return {
        "hornlab_search/gui/static/param-catalog.v1.json": catalog_json_bytes(catalog),
        "docs/reference/PARAMETERS.md":
            render_parameters_markdown(catalog).encode("utf-8"),
        "docs/reference/TYPOLOGIES.md":
            render_typologies_markdown(catalog).encode("utf-8"),
    }


def _verify_symbol(ref: str) -> None:
    module_name, _, symbol = ref.rpartition(".")
    if not module_name or not symbol:
        raise SystemExit(f"FAIL: code_ref {ref!r} is not a dotted module.symbol")
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:  # noqa: BLE001 - report the import failure verbatim
        raise SystemExit(f"FAIL: code_ref {ref!r}: cannot import {module_name!r}: {exc}")
    if not hasattr(module, symbol):
        raise SystemExit(f"FAIL: code_ref {ref!r}: {module_name} has no symbol {symbol!r}")


def _verify_doc(ref: tuple[str, str] | list[str] | None) -> None:
    if not ref:
        return
    path, heading = ref
    target = ROOT / path
    if not target.is_file():
        raise SystemExit(f"FAIL: doc_ref path does not exist: {path}")
    lines = target.read_text(encoding="utf-8").splitlines()
    if not any(line.strip().startswith(heading) for line in lines):
        raise SystemExit(f"FAIL: doc_ref heading not found in {path}: {heading!r}")


def _verify_metadata(catalog: dict) -> None:
    problems = validate_knob_docs(GENERATOR_KNOBS)  # type: ignore[arg-type]
    if problems:
        raise SystemExit("FAIL: metadata validation:\n  " + "\n  ".join(problems))

    refs: set[str] = set()
    docs: set[tuple[str, str]] = set()
    for doc in GENERATOR_KNOBS.values():
        if doc.code_ref:
            refs.add(doc.code_ref)
        if doc.doc_ref and doc.doc_ref[0]:
            docs.add(tuple(doc.doc_ref))
    for typ in catalog["typologies"].values():
        for knob in typ["knobs"]:
            ref = knob.get("code_ref")
            if ref:
                refs.add(ref)
            doc_ref = knob.get("doc_ref")
            if doc_ref:
                docs.add(tuple(doc_ref))
    for ref in sorted(refs):
        _verify_symbol(ref)
    for ref in sorted(docs):
        _verify_doc(list(ref))


def _first_diff(expected: bytes, actual: bytes) -> str:
    if expected == actual:
        return ""
    exp = expected.decode("utf-8", errors="replace").splitlines()
    act = actual.decode("utf-8", errors="replace").splitlines()
    for i in range(max(len(exp), len(act))):
        left = exp[i] if i < len(exp) else "<missing>"
        right = act[i] if i < len(act) else "<missing>"
        if left != right:
            return f"line {i + 1}: committed={left[:120]!r} fresh={right[:120]!r}"
    return "bytes differ"


def _check(expected: dict[str, bytes]) -> list[str]:
    stale: list[str] = []
    for rel, fresh in expected.items():
        path = ROOT / rel
        if not path.is_file():
            stale.append(f"{rel}: MISSING on disk")
            continue
        actual = path.read_bytes()
        if actual != fresh:
            stale.append(f"{rel}: STALE ({_first_diff(fresh, actual)})")
    return stale


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--write", action="store_true", help="write the three artifacts")
    group.add_argument("--check", action="store_true",
                       help="rebuild and compare byte-for-byte (exit 1 when stale)")
    args = parser.parse_args(argv)

    catalog = build_catalog(ROOT)
    _verify_metadata(catalog)
    expected = _artifact_bytes(catalog)

    if args.write:
        for rel, payload in expected.items():
            path = ROOT / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
            print(f"wrote {rel} ({len(payload)} bytes)")
        return 0

    stale = _check(expected)
    if stale:
        print("param catalog STALE:")
        for line in stale:
            print(f"  {line}")
        print("run: .venv\\Scripts\\python.exe tools/gen_param_catalog.py --write")
        return 1
    print("param catalog OK: all three artifacts match a fresh build")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
