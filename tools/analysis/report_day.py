"""A.8 report_day.py — run every Group A analysis from one YAML spec into one REPORT.md.

Usage:  PY tools\\analysis\\report_day.py --spec <yaml> --out <dir>

Spec keys (see ``tools/analysis/schema.md`` § report_day, and the shipped
``tools/analysis/specs/day_2026-11-12.yaml``): ``convergence``, ``seed_groups``,
``sensitivity``, ``links``, ``walls``, ``ab_compare``, ``lane_parity``,
``term_balance``, ``fidelity``; each entry is a list of ``{id: <key>, ...}`` sections.
``runs_root`` (optional) is prepended to every relative run path. Each section runs its
tool in its own subfolder of ``--out``; REPORT.md links all outputs and embeds the key
numbers. A failing section is recorded in REPORT.md (status: error) and never aborts the
others.
"""
from __future__ import annotations

import argparse
import importlib.util
import traceback
from pathlib import Path

from _common import add_out_arg, read_yaml, write_report

TOOL = "report_day"
_SPEC = Path(__file__).resolve().parent / "specs"
_TOOLS: dict = {}


def _load_tool(name: str):
    """Import a sibling analysis tool by file path (tools/ is not an importable package)."""
    if name in _TOOLS:
        return _TOOLS[name]
    path = Path(__file__).resolve().parent / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"analysis_{name}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    import sys

    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    _TOOLS[name] = module
    return module


def _resolve(runs_root: str | None, path: str) -> str:
    p = Path(path)
    if runs_root and not p.is_absolute():
        return str(Path(runs_root) / p)
    return str(p)


def run_sections(spec: dict, out_dir: Path) -> list[dict]:
    sections: list[dict] = []
    runs_root = spec.get("runs_root")

    for entry in spec.get("convergence") or []:
        mod = _load_tool("convergence")
        sections.append(_run_section(out_dir, entry, "convergence_" + str(entry["id"])
                                     if entry.get("id") else "convergence",
                                     lambda e, _m=mod: _m.analyse_run(Path(_resolve(runs_root, e["run"]))),
                                     md=lambda p, _m=mod: _m._md({"runs": [p]}),
                                     charts=lambda p, _m=mod: (
                                         {"convergence_1.png": _m._chart(p)}
                                         if p.get("curve") else None),
                                     tool="convergence"))
    for entry in spec.get("seed_groups") or []:
        mod = _load_tool("seed_variance")
        # one seed-group per spec id
        groups = {str(entry["id"]): [Path(_resolve(runs_root, p)) for p in entry["seeds"]]}
        sections.append(_run_section(out_dir, entry,
                                     "seed_variance_" + str(entry["id"]),
                                     lambda e, _m=mod, _g=groups: _m.analyse_groups(_g),
                                     tool="seed_variance"))
    for entry in spec.get("sensitivity") or []:
        mod = _load_tool("sensitivity")
        sections.append(_run_section(out_dir, entry, "sensitivity_" + str(entry["id"]),
                                     lambda e, _m=mod: _m.analyse_run(Path(_resolve(runs_root, e["run"]))),
                                     md=lambda p, _m=mod: _m._md(p),
                                     tool="sensitivity"))
    for entry in spec.get("links") or []:
        mod = _load_tool("links")
        sections.append(_run_section(out_dir, entry, "links_" + str(entry["id"]),
                                     lambda e, _m=mod: _m.analyse_run(Path(_resolve(runs_root, e["run"]))),
                                     md=lambda p, _m=mod: _m._md(p),
                                     charts=lambda p, _m=mod: _m.charts(p),
                                     tool="links"))
    for entry in spec.get("walls") or []:
        mod = _load_tool("walls")
        sections.append(_run_section(out_dir, entry, "walls_" + str(entry["id"]),
                                     lambda e, _m=mod: _m.analyse_run(Path(_resolve(runs_root, e["run"]))),
                                     md=lambda p, _m=mod: _m._md(p),
                                     charts=lambda p, _m=mod: _m.charts(p),
                                     tool="walls"))
    for entry in spec.get("ab_compare") or []:
        mod = _load_tool("ab_compare")
        sections.append(_run_section(
            out_dir, entry, "ab_compare_" + str(entry["id"]),
            lambda e, _m=mod: _m.analyse([Path(_resolve(runs_root, p)) for p in e["a"]],
                                         [Path(_resolve(runs_root, p)) for p in e["b"]],
                                         e.get("label_a"), e.get("label_b")),
            md=lambda p, _m=mod: _m._md(p),
            charts=lambda p, _m=mod: _m.charts(p),
            tool="ab_compare"))
    for entry in spec.get("lane_parity") or []:
        mod = _load_tool("lane_parity")
        sections.append(_run_section(
            out_dir, entry, "lane_parity_" + str(entry["id"]),
            lambda e, _m=mod: _m.analyse(Path(_resolve(runs_root, e["gpu"])),
                                         Path(_resolve(runs_root, e["cpu"]))),
            md=lambda p, _m=mod: _m._md(p),
            charts=lambda p, _m=mod: _m.charts(p),
            tool="lane_parity"))
    for entry in spec.get("term_balance") or []:
        mod = _load_tool("term_balance")
        sections.append(_run_section(
            out_dir, entry, "term_balance_" + str(entry["id"]),
            lambda e, _m=mod: _m.analyse_run(Path(_resolve(runs_root, e["run"]))),
            md=lambda p, _m=mod: _m._md(p),
            charts=lambda p, _m=mod: _m.charts(p),
            tool="term_balance"))
    for entry in spec.get("fidelity") or []:
        mod = _load_tool("fidelity")
        sections.append(_run_section(
            out_dir, entry, "fidelity_" + str(entry["id"]),
            lambda e, _m=mod: _m.analyse_run(Path(_resolve(runs_root, e["run"]))),
            md=lambda p, _m=mod: _m._md(p),
            charts=lambda p, _m=mod: _m.charts(p),
            tool="fidelity"))
    return sections


def _run_section(out_dir: Path, entry: dict, name: str,
                 compute, md=None, charts=None, tool=None) -> dict:
    """Run one spec section; catch everything and record status (never abort the report).

    ``fail()`` helpers raise SystemExit (not Exception) - caught too, since e.g.
    seed_variance refuses mixed-provenance groups that way. ``tool`` is the section's
    real tool name (e.g. "seed_variance") - splitting ``name`` on "_" is wrong for
    multi-word tools."""
    tool = tool or (name.split("_", 1)[0] if "_" in name else name)
    sec: dict = {"id": str(entry.get("id", name)), "tool": tool, "status": "",
                 "detail": "", "error": None}
    sub = Path(out_dir) / name
    try:
        payload = compute(entry)
        from _common import write_report

        table = md(payload) if md else _default_md(payload)
        written = write_report(sub, tool, payload, table,
                               (charts(payload) if charts else None) or None)  # type: ignore[arg-type]
        sec.update(status="ok", detail=str(sub),
                   outputs={Path(v).name: v for v in written.values()})
    except (Exception, SystemExit) as exc:  # noqa: BLE001 - a bad run dir must not kill the whole report
        sec.update(status="error", error=f"{type(exc).__name__}: {exc}",
                   detail="\n".join(traceback.format_exc().splitlines()[-3:]))
    return sec


def _default_md(payload) -> str:
    import json as _json
    return "# Report section\n\n```json\n" + \
        _json.dumps(payload, indent=1, default=str)[:4000] + "\n```\n"


def make_report_md(sections: list[dict], spec_path: str) -> str:
    lines = ["# Day analysis report", "",
             f"Spec: `{spec_path}`. Each section's JSON/MD lives in its subfolder of `--out`.",
             ""]
    for s in sections:
        tool = s.get("tool", "")
        line = f"- **{s['id']}** ({tool}): {s['status']}"
        if s.get("error"):
            line += f" — `{s['error']}`"
        lines.append(line)
    lines.append("")
    for s in sections:
        lines += [f"## {s['id']} ({s['tool']})", "", f"Status: **{s['status']}**"]
        if s.get("outputs"):
            for name, path in s["outputs"].items():
                if name.endswith(".json"):
                    lines.append(f"- JSON: {path}")
                elif name.endswith(".md"):
                    rel = Path(path)
                    try:
                        body = rel.read_text(encoding="utf-8")
                    except OSError:
                        body = ""
                    lines.append("")
                    lines.append(body)
        if s.get("error"):
            lines.append(f"Error: `{s['error']}`")
        lines += ["", "----", ""]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=( __doc__ or "").splitlines()[0])
    ap.add_argument("--spec", required=True, help="spec YAML (see tools/analysis/specs/)")
    add_out_arg(ap)
    args = ap.parse_args(argv)
    spec = read_yaml(Path(args.spec))
    if not isinstance(spec, dict):
        print(f"ERROR: {args.spec} is not a YAML mapping", file=__import__("sys").stderr)
        return 2
    sections = run_sections(spec, Path(args.out))
    payload = {"spec": str(Path(args.spec).resolve()),
               "n_sections": len(sections),
               "n_ok": sum(1 for s in sections if s["status"] == "ok"),
               "n_error": sum(1 for s in sections if s["status"] == "error"),
               "sections": sections}
    md = make_report_md(sections, args.spec)
    written = write_report(Path(args.out), TOOL, payload, md)
    # schema names the human report REPORT.md; report_day.md stays for the family naming
    report_md = Path(args.out) / "REPORT.md"
    try:
        report_md.write_text(md, encoding="utf-8")
        written["REPORT.md"] = str(report_md)
    except OSError as exc:
        print(f"warning: REPORT.md write failed ({exc})", file=__import__("sys").stderr)
    print(f"report_day OK: {payload['n_ok']} ok / {payload['n_error']} errored section(s)"
          f" -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
