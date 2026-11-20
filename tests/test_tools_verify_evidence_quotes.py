"""Offline tests for ``tools/evidence/verify_evidence_quotes.py``.

The tool is loaded by path, matching the ``tests/test_tools_*.py`` convention.  Everything is
synthetic and lives in ``tmp_path``; no real evidence, log or network access.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from conftest import REPO

TOOL = REPO / "tools" / "evidence" / "verify_evidence_quotes.py"


def _load_tool():
    spec = importlib.util.spec_from_file_location("verify_evidence_quotes", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


verify_tool = _load_tool()

MARKDOWN = """# Evidence

[measured] Captured stdout:

```
alpha line
beta line
```

Some ordinary prose that is not tagged:

```
ignored line
```

Final run, verbatim:

```
gamma line
```
"""


def _utf16_log(path: Path, lines: list[str]) -> Path:
    path.write_text("\n".join(lines) + "\n", encoding="utf-16")
    return path


def test_marker_and_verbatim_fences_are_quotes_but_plain_fences_are_not() -> None:
    quotes = verify_tool.quote_lines(MARKDOWN)
    assert [q.text for q in quotes] == ["alpha line", "beta line", "gamma line"]
    assert [q.line_no for q in quotes] == [6, 7, 19]


def test_utf16_log_is_detected_by_bom(tmp_path: Path) -> None:
    log = _utf16_log(tmp_path / "run.log", ["alpha line", "beta line", "gamma line"])
    raw = log.read_bytes()
    assert raw[:2] in (b"\xff\xfe", b"\xfe\xff")
    assert verify_tool.decode_log(raw).splitlines() == ["alpha line", "beta line", "gamma line"]


def test_all_quotes_found_exits_zero(tmp_path: Path, capsys) -> None:
    evidence = tmp_path / "EVIDENCE.md"
    evidence.write_text(MARKDOWN, encoding="utf-8")
    log = _utf16_log(tmp_path / "run.log", ["noise", "alpha line", "beta line", "gamma line"])

    assert verify_tool.main([str(evidence), str(log)]) == 0
    captured = capsys.readouterr()
    assert "OK: 3 quoted line(s) found verbatim" in captured.out
    assert captured.err == ""


def test_a_missing_quote_exits_one_and_names_the_line(tmp_path: Path, capsys) -> None:
    evidence = tmp_path / "EVIDENCE.md"
    evidence.write_text(MARKDOWN, encoding="utf-8")
    log = _utf16_log(tmp_path / "run.log", ["alpha line", "gamma line"])

    assert verify_tool.main([str(evidence), str(log)]) == 1
    captured = capsys.readouterr()
    assert "MISS " in captured.out
    assert "beta line" in captured.out
    assert "1 of 3 quoted line(s) not found verbatim" in captured.err


def test_quotes_may_be_found_in_any_of_several_logs(tmp_path: Path) -> None:
    evidence = tmp_path / "EVIDENCE.md"
    evidence.write_text(MARKDOWN, encoding="utf-8")
    first = _utf16_log(tmp_path / "a.log", ["alpha line"])
    second = tmp_path / "b.log"
    second.write_text("beta line\ngamma line\n", encoding="utf-8")

    total, misses = verify_tool.verify(evidence, [first, second])
    assert total == 3
    assert misses == []
