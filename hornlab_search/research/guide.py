"""Audience layers for one snapshot: plain-language summary, glossary and the agent guide.

The same snapshot serves three readers:

* non-technical readers get ``plain_summary`` (sentences, no symbols) and the glossary;
* technical readers get the drilldowns, cells and sources in ``index.html``;
* planning agents get ``AGENT_GUIDE.md`` + ``summary.json`` + ``findings.ndjson`` / ``rows.ndjson``,
  with the invariants they must respect and every suggested next step labelled for GPU use and
  owner approval.

Nothing here reads a source; it only re-presents values already in the snapshot.
"""
from __future__ import annotations

GLOSSARY = {
    "J": "The optimizer's single score for a design (lower is better). Only comparable between designs "
         "scored the same way (same brief, objective version, fidelity and mesh).",
    "score identity": "The exact scoring setup (brief, objective version, screen/verify fidelity, mesh and "
                      "solver settings). Scores from different identities must never be compared.",
    "predeclared rule": "An acceptance rule written down before the simulations ran, so results cannot be "
                        "judged by rules chosen afterwards.",
    "min Re(z)": "How well the horn loads the driver at low frequencies (normalised throat resistance). "
                 "Lower means the driver is less well controlled.",
    "beamwidth (H/V)": "How wide the sound spreads horizontally (H) or vertically (V), in degrees, at the "
                       "-6 dB points.",
    "epw / mesh": "Elements per wavelength: how finely the horn surface is divided for the simulation. "
                  "epw 9 is a finer check of an epw 6 result.",
    "DOF": "Degrees of freedom: the size of the simulation problem. Fewer DOF means a faster solve.",
    "cohort": "A set of optimizer results sharing one score identity and one experiment configuration name.",
    "holdout": "A frozen test where the newest results are hidden from a model to check whether it would "
               "have predicted them. PASS_FOR_EXPLORATORY_PILOT allows a small held trial only; HOLD means no.",
    "replay": "Re-encoding stored results under the current configuration; a mismatch means old rows no "
              "longer fit the current search box.",
    "cutoff": "The moment the snapshot is frozen at; anything recorded later is excluded and counted.",
    "screen / verify": "A quick lower-fidelity simulation (screen) versus a slower careful one (verify).",
    "canary": "A small, deliberately limited trial run of a new method before wider use.",
    "residual": "The difference between the stored score and the sum of its parts; zero means the "
                "breakdown is complete.",
}

AGENT_INVARIANTS = [
    "Never compare or rank J across different cohort ids or score identities (brief_hash, objective_version, "
    "mode, backend, fidelity_policy, mesh epw).",
    "A predeclared verdict (pass/fail) outranks J; select by rules first, then by J inside the passing set.",
    "Every value is a cell. {v, src}: src is '<repo path>#<pointer>' where pointer is a JSON pointer "
    "(/a/b/0) for JSON; 'line:N/<field>' for ndjson (1-based line N, then the JSON field); 'line:N/col:<header>' "
    "for a markdown table cell; 'line:N/text:<phrase>' for a phrase on a markdown line; 'row:N/<column>' "
    "for CSV (1-based data row, header not counted). {v, calc, calc_version, inputs} is a deterministic "
    "calculation over the listed inputs.",
    "Committed sources are read at manifest.source_commit via `git show <sha>:<path>`; runs/ sources are "
    "pinned by sha256 in manifest.sources.",
    "missing / unknown / unsupported / run_dir_missing are distinct states; never treat them as zero or pass.",
    "Findings are suggestions. next_steps with needs_gpu or needs_owner_approval must not be executed "
    "without the owner's explicit approval; GPU work also needs `hornlab-search gpu-clean` first (AGENTS.md).",
    "Values are simulated BEM results, not physical measurements.",
    "Respect the cutoff: evidence after manifest.cutoff_utc is out of scope for this snapshot; build a new "
    "snapshot instead of mixing.",
]


def plain_summary(snap: dict) -> list[str]:
    """Sentences for a non-technical reader, built only from finding ``plain`` texts and counts."""
    inv = snap["inventory"]
    n_c = len(inv["cohorts"])
    n_adm = sum(1 for c in inv["cohorts"] if c["admission"].get("kind"))
    out = [f"This page freezes what the project's records showed at {snap['cutoff_utc']} and explains what "
           f"they mean. It looked at {n_c} groups of optimizer results ({n_adm} of them checked for use in "
           f"training) and {len(snap['dose']['rows'])} carefully simulated horn designs."]
    for f in snap["findings"]:
        if f["severity"] in ("decision", "data_quality"):
            out.append(f["plain"])
    out.append("All numbers come from computer simulations, not from measuring real hardware. Nothing on this "
               "page starts any work by itself.")
    return out


def next_steps(snap: dict) -> list[dict]:
    """Every suggested step, flattened, CPU/no-approval steps first."""
    steps = []
    for f in snap["findings"]:
        for s in f.get("next_steps", []):
            steps.append({**s, "finding_id": f["id"], "finding_kind": f["kind"]})
    return sorted(steps, key=lambda s: (s["needs_gpu"], s["needs_owner_approval"], s["finding_kind"], s["what"]))


def agent_markdown(snap: dict) -> str:
    m = snap["manifest"]
    lines = [
        f"# Agent guide — research snapshot {snap['snapshot_id']}",
        "",
        f"Cutoff `{snap['cutoff_utc']}` · source commit `{snap['source_commit']}` · generator `{snap['generator']}`.",
        f"{m['n_sources']} sources, {len(m['exclusions'])} exclusions, {len(snap['findings'])} findings.",
        "",
        "## Files",
        "",
        "- `snapshot.json` — the artifact (every other file is derived from it).",
        "- `summary.json` — headline counts, plain summary and next steps (small; read first).",
        "- `findings.ndjson` — one finding per line: observation / hypothesis / action / plain / next_steps / evidence / cells.",
        "- `rows.ndjson` — one evidence row per line, `section` in {dose, cohort, reconciliation, mesh, canary, canary_replicate}.",
        "- `manifest.json` — sources with sha256/origin, cutoff, exclusions.",
        "- `index.html` — the human view of the same bytes.",
        "",
        "## Invariants (must hold for any plan built on this snapshot)",
        "",
        *[f"{i}. {t}" for i, t in enumerate(AGENT_INVARIANTS, start=1)],
        "",
        "## Suggested next steps (none are dispatched)",
        "",
        "| Step | Needs GPU | Owner approval | From finding |",
        "|---|---|---|---|",
    ]
    for s in next_steps(snap):
        lines.append(f"| {s['what']} | {'yes' if s['needs_gpu'] else 'no'} | "
                     f"{'yes' if s['needs_owner_approval'] else 'no'} | `{s['finding_kind']}` `{s['finding_id']}` |")
    lines += ["", "## Findings", ""]
    for f in snap["findings"]:
        lines += [f"### {f['title']}", "", f"- severity: `{f['severity']}` · id `{f['id']}` · strength: {f['strength']}",
                  f"- scope: {f['scope']}", f"- observation: {f['observation']}", f"- hypothesis: {f['hypothesis']}",
                  f"- action: {f['action']}", f"- evidence: {', '.join(f'`{e}`' for e in f['evidence'][:12])}"
                  + (" …" if len(f["evidence"]) > 12 else ""), ""]
    me = snap["missing_evidence"]
    lines += ["## Known gaps", "", *[f"- {u}" for u in me["unmeasured"]],
              f"- {len(me['cells'])} missing/unknown cells (see `snapshot.json` → `missing_evidence.cells`).", ""]
    return "\n".join(lines)


def summary(snap: dict) -> dict:
    inv = snap["inventory"]
    status_counts: dict[str, int] = {}
    for c in inv["cohorts"]:
        status_counts[c["status"]] = status_counts.get(c["status"], 0) + 1
    return {"schema": "hornfab-research-summary-m1", "snapshot_id": snap["snapshot_id"],
            "cutoff_utc": snap["cutoff_utc"], "source_commit": snap["source_commit"],
            "generator": snap["generator"],
            "counts": {"sources": snap["manifest"]["n_sources"], "exclusions": len(snap["manifest"]["exclusions"]),
                       "findings": len(snap["findings"]), "dose_rows": len(snap["dose"]["rows"]),
                       "cohorts": len(inv["cohorts"]), "missing_cells": len(snap["missing_evidence"]["cells"])},
            "cohort_status": dict(sorted(status_counts.items())),
            "headlines": [{"id": f["id"], "kind": f["kind"], "severity": f["severity"], "title": f["title"],
                           "plain": f["plain"]} for f in snap["findings"]],
            "plain_summary": snap["plain_summary"], "next_steps": next_steps(snap)}
