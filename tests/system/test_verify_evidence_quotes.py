"""Tests for ``tools/system/verify_evidence_quotes.py`` (risk R12)."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

TOOL_PATH = Path(__file__).resolve().parents[2] / "tools" / "system" / "verify_evidence_quotes.py"


def _load_tool():
    spec = importlib.util.spec_from_file_location("verify_evidence_quotes_tool", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def tool():
    return _load_tool()


def _write_doc(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


def _run(tool, capsys, doc: Path, root: Path, *extra: str):
    code = tool.main(["--doc", str(doc), "--root", str(root), *extra])
    out = capsys.readouterr().out
    return code, out


def test_exact_block_pass(tool, tmp_path, capsys):
    root = tmp_path
    (root / "source.log").write_text("alpha\nbeta\ngamma\n", encoding="utf-8")
    doc = _write_doc(root / "doc.md", (
        "# evidence\n\n"
        "<!-- evidence-quote: source=source.log mode=exact decode=utf-8 -->\n"
        "```\n"
        "beta\ngamma\n"
        "```\n"
    ))

    code, out = _run(tool, capsys, doc, root)

    assert code == 0
    assert "[PASS] block 1" in out
    assert "annotated=1 passed=1 failed=0 skipped=0" in out


def test_exact_block_fail(tool, tmp_path, capsys):
    root = tmp_path
    (root / "source.log").write_text("alpha\nbeta\ngamma\n", encoding="utf-8")
    doc = _write_doc(root / "doc.md", (
        "<!-- evidence-quote: source=source.log mode=exact decode=utf-8 -->\n"
        "```\n"
        "beta\ndelta\n"
        "```\n"
    ))

    code, out = _run(tool, capsys, doc, root)

    assert code == 1
    assert "[FAIL] block 1" in out
    assert "annotated=1 passed=0 failed=1 skipped=0" in out


def test_lines_block_pass_with_elision_and_editorial_note(tool, tmp_path, capsys):
    root = tmp_path
    (root / "source.json").write_text(
        '{\n'
        '  "a": 1,\n'
        '  "b": 2,\n'
        '  "meshes": [\n'
        '    {\n'
        '      "purpose": "bem_surface",\n'
        '      "sha256": "deadbeef",\n'
        '      "size_bytes": 381105\n'
        '    }\n'
        '  ],\n'
        '  "tail": true\n'
        '}\n',
        encoding="utf-8",
    )
    doc = _write_doc(root / "doc.md", (
        "<!-- evidence-quote: source=source.json mode=lines decode=auto -->\n"
        "```json\n"
        '  "a": 1,\n'
        "  ...\n"
        '  "purpose": "bem_surface", "sha256": "deadbeef"  (mesh:horn, 381105 B)\n'
        "  ...\n"
        '  "tail": true\n'
        "```\n"
    ))

    code, out = _run(tool, capsys, doc, root)

    assert code == 0
    assert "[PASS] block 1" in out
    assert "present in order" in out


def test_lines_block_fail_when_line_absent(tool, tmp_path, capsys):
    root = tmp_path
    (root / "source.log").write_text("first\nsecond\nthird\n", encoding="utf-8")
    doc = _write_doc(root / "doc.md", (
        "<!-- evidence-quote: source=source.log mode=lines decode=utf-8 -->\n"
        "```\n"
        "first\n"
        "not-in-source\n"
        "third\n"
        "```\n"
    ))

    code, out = _run(tool, capsys, doc, root)

    assert code == 1
    assert "[FAIL] block 1" in out
    assert "not found in source" in out


@pytest.mark.parametrize("decode", ["auto", "utf-16"])
def test_utf16_source_decoded(tool, tmp_path, capsys, decode):
    root = tmp_path
    text = "ligne un\nligne deux\n"
    (root / "tee.log").write_bytes(b"\xff\xfe" + text.encode("utf-16-le"))
    doc = _write_doc(root / "doc.md", (
        f"<!-- evidence-quote: source=tee.log mode=exact decode={decode} -->\n"
        "```\n"
        "ligne un\nligne deux\n"
        "```\n"
    ))

    code, out = _run(tool, capsys, doc, root)

    assert code == 0
    assert "[PASS] block 1" in out


def test_parent_escape_source_refused(tool, tmp_path, capsys):
    root = tmp_path / "root"
    root.mkdir()
    (tmp_path / "outside.log").write_text("secret\n", encoding="utf-8")
    doc = _write_doc(root / "doc.md", (
        "<!-- evidence-quote: source=../outside.log mode=exact decode=utf-8 -->\n"
        "```\n"
        "secret\n"
        "```\n"
    ))

    code, out = _run(tool, capsys, doc, root)

    assert code == 2
    assert "[FAIL] block 1" in out
    assert "outside repo root" in out


def test_block_without_annotation_is_skipped(tool, tmp_path, capsys):
    root = tmp_path
    doc = _write_doc(root / "doc.md", (
        "# plain document\n\n"
        "```\n"
        "this block has no annotation\n"
        "```\n"
    ))

    code, out = _run(tool, capsys, doc, root)

    assert code == 0
    assert "annotated=0 passed=0 failed=0 skipped=1" in out
