"""Hermetic tests for the read-only system funnel ledger.

No real store, no GPU, no solver.  Every fixture is a synthetic ``system_runs`` tree under
``tmp_path``; the ledger must classify cases from manifests exactly as the census does and only
write files when :func:`write_ledger` is called.
"""
from __future__ import annotations

import json
from pathlib import Path

from hornlab_search.system.funnel import (
    ASSET_ONLY_LABEL,
    OUTPUT_JSON,
    OUTPUT_MARKDOWN,
    SCHEMA,
    TOKENS,
    build_ledger,
    render_markdown,
    write_ledger,
)

PAIR_BAND = [700.0, 1300.0]


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _screen(root: Path, name: str, study_id: str, shortlist: list[dict]) -> Path:
    path = root / "system_runs" / name / "woofer_seed.json"
    _write_json(
        path,
        {
            "schema": "hornlab.system.woofer_seed.v1",
            "study_id": study_id,
            "shortlist": shortlist,
            "kept_rows": [{"row_id": "kept"}],
            "rejected_ledger": [{"row_id": "rejected"}],
        },
    )
    return path


def _row(candidate_id: str, *, band: list[float] | None = None, driver: str = "driver") -> dict:
    row = {
        "candidate_id": candidate_id,
        "driver_id": driver,
        "status": "PASS",
        "shortlist_reason": "axis_best:test",
        "xo_hz": 1000.0,
    }
    if band is not None:
        row["xo_band_hz"] = f"{band[0]:g} {band[1]:g}"
    return row


def _case(
    root: Path,
    experiment: str,
    name: str,
    *,
    payload: object | None = None,
    run: dict | None = None,
    seed: dict | None = None,
) -> Path:
    case = root / "system_runs" / "system" / experiment / name
    _write_json(
        case / "manifest.json",
        {"payload": payload if payload is not None else {"kind": "test"}},
    )
    if run is not None:
        _write_json(case / "run" / "manifest.json", run)
    if seed is not None:
        _write_json(path=case / "adapter_spec.json", data={"seed": seed})
    return case


def _solved_run(channels: list[str], frequencies: list[float]) -> dict:
    return {
        "status": "complete",
        "excitation_port_ids": channels,
        "frequencies_hz": frequencies,
    }


def _make_main_fixture(root: Path) -> None:
    _screen(
        root,
        "study-a",
        "study-a-id",
        [
            _row("cand-pair", band=PAIR_BAND, driver="driver-pair"),
            _row("cand-staged", band=PAIR_BAND),
            _row("cand-refused", band=PAIR_BAND),
            _row("cand-missing", band=PAIR_BAND),
            _row("cand-woofer", band=PAIR_BAND),
            _row("cand-bandmiss", band=PAIR_BAND),
        ],
    )
    _case(
        root,
        "exp",
        "20260101T000001Z-pair",
        run=_solved_run(["vented/voltage", "excitation:horn"], [700.0, 1000.0, 1300.0]),
        seed={
            "candidate_id": "cand-pair",
            "source_path": "C:/store/woofer_seed.json",
            "source_sha256": "a" * 64,
        },
    )
    _case(root, "exp", "20260101T000002Z-staged", seed={"candidate_id": "cand-staged"})
    _case(
        root,
        "exp",
        "20260101T000003Z-refused",
        payload={"result": {"ok": False, "error": "does not fit inside the panel"}},
        seed={"candidate_id": "cand-refused"},
    )
    _case(
        root,
        "exp",
        "20260101T000004Z-woofer-only",
        run=_solved_run(["vented/voltage"], [30.0, 60.0, 100.0]),
        seed={"candidate_id": "cand-woofer"},
    )
    _case(
        root,
        "exp",
        "20260101T000005Z-band-miss",
        run=_solved_run(["vented/voltage", "excitation:horn"], [30.0, 60.0, 100.0]),
        seed={"candidate_id": "cand-bandmiss"},
    )
    # Solved case with no adapter seed: no join key, never guessed by driver/asset id.
    _case(
        root,
        "exp",
        "20260101T000006Z-no-key",
        run=_solved_run(["vented/voltage", "excitation:horn"], [200.0, 2000.0]),
    )
    # Malformed manifest: invalid, also no join key.
    invalid = root / "system_runs" / "system" / "exp" / "20260101T000007Z-invalid"
    invalid.mkdir(parents=True)
    (invalid / "manifest.json").write_text("{not json", encoding="utf-8")


def test_tokens_are_declared_in_funnel_order() -> None:
    assert TOKENS == (
        "NO_BEM_CASE_FOR_CANDIDATE",
        "BEM_CASE_STAGED_NOT_SOLVED",
        "BEM_CHANNEL_MISSING",
        "BEM_BAND_OUT_OF_RANGE",
        "DSP_SUM_LOCKED_OWNER_DECISION_3",
        "GUI_SOLVE_DISABLED_OWNER_DECISION_6",
        "FALSE_NEGATIVE_AUDIT_INSUFFICIENT_PAIRS",
    )


def test_join_reports_gate_losses_and_emits_tokens(tmp_path: Path) -> None:
    _make_main_fixture(tmp_path)
    ledger = build_ledger(tmp_path)

    assert ledger["schema"] == SCHEMA
    assert ledger["read_only"] is True
    assert ledger["source"] == {
        "root": ".",
        "screens_root": "system_runs",
        "system_root": "system_runs/system",
    }
    assert ledger["asset_only_diagnostic"]["label"] == ASSET_ONLY_LABEL

    screens = ledger["screen_census"]
    assert screens["files"] == 1
    assert screens["unique_study_ids"] == 1
    assert screens["shortlist_rows"] == 6
    assert screens["kept_rows"] == 1
    assert screens["rejected_rows"] == 1
    assert screens["distinct_shortlist_candidate_ids"] == 6

    cases = ledger["case_census"]
    assert cases["case_dirs"] == 7
    assert cases["by_status"] == {"invalid": 1, "refused": 1, "solved": 4, "staged": 1}
    assert cases["solved"] == 4
    assert cases["with_join_key"] == 5
    assert cases["without_join_key"] == 2
    assert cases["two_channel"] == 3

    join = ledger["join"]
    counts = join["counts"]
    assert counts["shortlist_rows"] == 6
    assert counts["matched_rows"] == 5
    assert counts["missing_case_rows"] == 1
    assert counts["solved_rows"] == 3
    assert counts["staged_rows"] == 1
    assert counts["refused_rows"] == 1
    assert counts["invalid_rows"] == 0
    assert counts["missing_channel_rows"] == 1
    assert counts["band_miss_rows"] == 1
    assert join["distinct_shortlist_candidate_ids"] == 6
    assert join["distinct_joined_cases"] == 5
    assert join["cases_without_join_key"] == 2
    assert join["paired_candidate_case_pairs"] == 2
    assert join["candidate_ids_with_solved_two_channel_case"] == 2
    assert counts["shortlist_rows_with_solved_two_channel_case"] == 2

    outcomes = {row["candidate_id"]: row for row in join["rows"]}
    assert outcomes["cand-pair"]["outcome"] == "solved"
    assert outcomes["cand-pair"]["missing_channel"] is False
    assert outcomes["cand-pair"]["band_miss"] is False
    assert outcomes["cand-staged"]["outcome"] == "staged"
    assert outcomes["cand-refused"]["outcome"] == "refused"
    assert outcomes["cand-missing"]["outcome"] == "missing_case"
    assert outcomes["cand-missing"]["case_keys"] == []
    assert outcomes["cand-woofer"]["outcome"] == "solved"
    assert outcomes["cand-woofer"]["missing_channel"] is True
    assert outcomes["cand-woofer"]["band_miss"] is False
    assert outcomes["cand-bandmiss"]["missing_channel"] is False
    assert outcomes["cand-bandmiss"]["band_miss"] is True

    assert ledger["tokens"] == [
        "NO_BEM_CASE_FOR_CANDIDATE",
        "BEM_CASE_STAGED_NOT_SOLVED",
        "BEM_CHANNEL_MISSING",
        "BEM_BAND_OUT_OF_RANGE",
        "DSP_SUM_LOCKED_OWNER_DECISION_3",
        "GUI_SOLVE_DISABLED_OWNER_DECISION_6",
    ]
    assert ledger["false_negative_audit"]["token"] is None
    assert ledger["false_negative_audit"]["pair_count"] == 2


def test_audit_token_fires_when_no_solved_two_channel_pair(tmp_path: Path) -> None:
    _screen(tmp_path, "woofer-only-study", "study-w", [_row("cand-woofer", band=PAIR_BAND)])
    _case(
        tmp_path,
        "exp",
        "20260101T000001Z-woofer-only",
        run=_solved_run(["vented/voltage"], [30.0, 60.0, 100.0]),
        seed={"candidate_id": "cand-woofer"},
    )

    ledger = build_ledger(tmp_path)
    audit = ledger["false_negative_audit"]

    assert audit["candidate_ids_with_solved_two_channel_case"] == 0
    assert audit["solved_two_channel_pairs"] == 0
    assert audit["pair_count"] == 0
    assert audit["token"] == "FALSE_NEGATIVE_AUDIT_INSUFFICIENT_PAIRS"
    assert "insufficient paired data" in audit["note"]
    assert ledger["tokens"][-1] == "FALSE_NEGATIVE_AUDIT_INSUFFICIENT_PAIRS"
    assert "FALSE_NEGATIVE_AUDIT_INSUFFICIENT_PAIRS" in ledger["tokens"]
    assert ledger["join"]["counts"]["missing_channel_rows"] == 1
    assert "BEM_CHANNEL_MISSING" in ledger["tokens"]


def test_build_is_deterministic_and_read_only(tmp_path: Path) -> None:
    _make_main_fixture(tmp_path)
    before = sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*"))

    first = build_ledger(tmp_path)
    second = build_ledger(tmp_path)
    assert first == second
    assert render_markdown(first) == render_markdown(second)

    after = sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*"))
    assert after == before
    assert not any(path.endswith(OUTPUT_JSON) for path in after)
    assert not any(path.endswith(OUTPUT_MARKDOWN) for path in after)


def test_write_ledger_writes_only_when_called(tmp_path: Path) -> None:
    _make_main_fixture(tmp_path)
    ledger = build_ledger(tmp_path)
    out_dir = tmp_path / "evidence" / "funnel"
    assert not out_dir.exists()

    written = write_ledger(ledger, out_dir)

    json_path = out_dir / OUTPUT_JSON
    md_path = out_dir / OUTPUT_MARKDOWN
    assert json_path.is_file()
    assert md_path.is_file()
    assert written == {"json": str(json_path), "markdown": str(md_path)}
    assert json.loads(json_path.read_text(encoding="utf-8")) == ledger
    markdown = md_path.read_text(encoding="utf-8")
    assert markdown.startswith("# System funnel ledger")
    assert "FALSE_NEGATIVE_AUDIT" not in markdown  # this fixture has a solved pair
    assert "BEM_CHANNEL_MISSING" in markdown
