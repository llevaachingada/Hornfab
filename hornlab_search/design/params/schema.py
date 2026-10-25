"""Frozen documentation records for the parameter single-source-of-truth layer.

This module holds ONLY the shape of the records and their validation. It imports nothing
from ``hornlab_search.design`` and nothing outside the standard library, so the package
stays import-light (see ``tests/test_param_catalog.py``).

Nothing here is a numeric authority. ``KnobDoc.default`` / ``hard_lo`` / ``hard_hi`` are
filled in by :mod:`hornlab_search.design.params.knobs_generators` from
``registry.DEFAULT_KNOBS`` and ``families.FAMILY_KEYS``; the catalog builder attaches the
per-typology search bounds from ``examples/``. Any number typed into this package is a bug.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

#: Flag vocabulary. Plain strings so the wire contract and the docs are readable.
FLAGS: frozenset[str] = frozenset({
    "overloaded",       # the same knob name means different things in different contexts
    "derived",          # computed by the code, not an independent degree of freedom
    "not_a_knob",       # a prefix / block key / alias, not a standalone knob
    "doc_mismatch",     # prose and shipped code disagree; recorded, not resolved here
    "pinned_by_brief",  # a brief fixes this value for some typologies
    "deferred",         # another domain lane owns the remaining context(s)
})

#: Units this layer is allowed to emit. The suffix rule in knobs_generators.py decides
#: which one applies; none of these is invented here.
UNITS: frozenset[str] = frozenset({"mm", "deg", "Hz", "dB", "%", "1/mm", "mm/deg"})

_PLACEHOLDERS = ("todo", "tbd", "???", "lorem")
_UNIT_RE = re.compile(r"^[A-Za-z0-9%°/^.*_-]+$")
SUMMARY_LIMIT = 120


@dataclass(frozen=True)
class KnobContext:
    """One meaning of a knob name in one context (``generator``, ``osse``, ``rows``, ...).

    Only the generator context is authored by this lane. Contexts owned by a later lane
    carry ``flags=frozenset({"deferred"})`` and say so, rather than inventing physics.
    """

    label: str
    summary: str
    detail: str
    formula: str | None = None
    physical: str = ""
    flags: frozenset[str] = frozenset()


@dataclass(frozen=True)
class KnobDoc:
    """Authored prose for one knob NAME.

    ``default`` / ``hard_lo`` / ``hard_hi`` are READ from an existing authority when the
    module that defines the docs imports; they are never typed. ``default`` is ``None``
    for names that live in a generator block (their value comes from the config YAML).
    """

    knob: str
    label: str
    unit: str | None
    summary: str
    detail: str
    formula: str | None
    physical: str
    contexts: dict[str, KnobContext] = field(default_factory=dict)
    flags: frozenset[str] = frozenset()
    code_ref: str = ""                       # dotted module.symbol, verified by the tool
    doc_ref: tuple[str, str] = ("", "")      # (repo-relative path, heading)
    default: object = None
    hard_lo: float | None = None
    hard_hi: float | None = None


@dataclass(frozen=True)
class TypologyDoc:
    """Identity of one catalog id resolved down to the code that builds it."""

    name: str
    group: str
    symmetry: str
    description: str
    family: str
    kind: str                                # "generator" | "rows" | "native"
    config_path: str                         # repo-relative, posix separators
    brief_file: str | None
    source_status: str
    knobs: list[str]
    overrides: dict[str, KnobContext] = field(default_factory=dict)


def _placeholders(text: str) -> list[str]:
    low = text.lower()
    return [token for token in _PLACEHOLDERS if token in low]


def validate_knob_doc(doc: KnobDoc) -> list[str]:
    """Return a list of problems (empty = valid). Never raises."""
    problems: list[str] = []
    if not doc.knob:
        problems.append("knob name is empty")
    if not doc.label.strip():
        problems.append(f"{doc.knob}: label is empty")
    if not doc.summary.strip():
        problems.append(f"{doc.knob}: summary is empty")
    elif len(doc.summary) > SUMMARY_LIMIT:
        problems.append(f"{doc.knob}: summary is {len(doc.summary)} chars "
                        f"(limit {SUMMARY_LIMIT})")
    if not doc.detail.strip():
        problems.append(f"{doc.knob}: detail is empty")
    if not doc.physical.strip():
        problems.append(f"{doc.knob}: physical effect is empty")
    for where, text in (("summary", doc.summary), ("detail", doc.detail),
                        ("physical", doc.physical), ("label", doc.label)):
        hits = _placeholders(text)
        if hits:
            problems.append(f"{doc.knob}: {where} carries placeholder text {hits}")
    if doc.unit is not None:
        if not _UNIT_RE.match(doc.unit):
            problems.append(f"{doc.knob}: invalid unit token {doc.unit!r}")
        if doc.unit not in UNITS:
            problems.append(f"{doc.knob}: unit {doc.unit!r} is not in the allowed set")
    if doc.flags - FLAGS:
        problems.append(f"{doc.knob}: unknown flag(s) {sorted(doc.flags - FLAGS)}")
    for cid, ctx in doc.contexts.items():
        if not cid.strip():
            problems.append(f"{doc.knob}: empty context id")
        if not ctx.label.strip():
            problems.append(f"{doc.knob}:{cid}: label is empty")
        if not ctx.summary.strip():
            problems.append(f"{doc.knob}:{cid}: summary is empty")
        elif len(ctx.summary) > SUMMARY_LIMIT:
            problems.append(f"{doc.knob}:{cid}: summary is {len(ctx.summary)} chars "
                            f"(limit {SUMMARY_LIMIT})")
        if not ctx.detail.strip():
            problems.append(f"{doc.knob}:{cid}: detail is empty")
        hits = _placeholders(ctx.summary + " " + ctx.detail + " " + ctx.label)
        if hits:
            problems.append(f"{doc.knob}:{cid}: placeholder text {hits}")
        if ctx.flags - FLAGS:
            problems.append(f"{doc.knob}:{cid}: unknown flag(s) {sorted(ctx.flags - FLAGS)}")
        if ctx.flags and "deferred" in ctx.flags and not ctx.summary.strip():
            problems.append(f"{doc.knob}:{cid}: deferred context needs a stated reason")
    return problems


def validate_typology_doc(doc: TypologyDoc) -> list[str]:
    """Return a list of problems (empty = valid). Never raises."""
    problems: list[str] = []
    if not doc.name.strip():
        problems.append("typology name is empty")
    if doc.kind not in ("generator", "rows", "native"):
        problems.append(f"{doc.name}: unknown kind {doc.kind!r}")
    if not doc.family.strip():
        problems.append(f"{doc.name}: family is empty")
    if not doc.config_path.strip():
        problems.append(f"{doc.name}: config_path is empty")
    if not doc.source_status.strip():
        problems.append(f"{doc.name}: source_status is empty")
    if doc.kind == "generator" and not doc.knobs:
        problems.append(f"{doc.name}: generator typology has no knob names")
    hits = _placeholders(doc.description)
    if hits:
        problems.append(f"{doc.name}: description placeholder text {hits}")
    return problems


def validate_knob_docs(docs: dict[str, KnobDoc]) -> list[str]:
    """Validate a whole mapping; also checks the dict key matches ``doc.knob``."""
    problems: list[str] = []
    for key, doc in docs.items():
        if key != doc.knob:
            problems.append(f"key {key!r} does not match doc.knob {doc.knob!r}")
        problems.extend(validate_knob_doc(doc))
    return problems
