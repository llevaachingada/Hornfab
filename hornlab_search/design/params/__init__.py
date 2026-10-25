"""Public API for the parameter single-source-of-truth layer.

IMPORT-LIGHT BY CONSTRUCTION: importing this package pulls only :mod:`.schema`, which is
standard-library only. It does not import numpy, the mesher, the solver, or the search
layer. The catalog is built lazily on the first lookup; that build reads the YAML configs
and the design authorities. ``tests/test_param_catalog.py`` proves the import with numpy
blocked from ``sys.modules``.

The API NEVER raises on an unknown typology or knob. An undocumented lookup returns a
shape-compatible placeholder with ``documented: False``; it never guesses physics.
"""
from __future__ import annotations

from pathlib import Path

from .schema import KnobContext, KnobDoc, TypologyDoc

__all__ = [
    "KnobContext",
    "KnobDoc",
    "TypologyDoc",
    "all_typologies",
    "bounds_for",
    "catalog_version",
    "describe",
    "domains_covered",
    "knobs_for",
]

_ROOT = Path(__file__).resolve().parents[3]
_CATALOG: dict | None = None


def _catalog() -> dict:
    global _CATALOG
    if _CATALOG is None:
        from .catalog import build_catalog

        _CATALOG = build_catalog(_ROOT)
    return _CATALOG


def _unknown(knob: str, context: str, *, typology: str | None = None) -> dict:
    return {
        "typology": typology,
        "knob": knob,
        "base_knob": knob,
        "context": context,
        "documented": False,
        "label": knob,
        "unit": None,
        "summary": "No documentation authored for this lookup yet.",
        "detail": ("This typology or knob name has no authored entry in the current "
                   "parameter layer. It is reported, not guessed."),
        "formula": None,
        "physical": "Not documented in this layer.",
        "code_ref": None,
        "doc_ref": None,
        "flags": ["deferred"],
        "default": None,
        "default_source": None,
        "search": None,
        "bounds_source": None,
        "hard": {"lo": None, "hi": None, "kind": None, "choices": None,
                 "section": None, "source": None,
                 "note": "no authored documentation for this lookup"},
        "contexts": [],
    }


def _merge_doc(doc: KnobDoc, context_id: str) -> dict:
    ctx: KnobContext | None = doc.contexts.get(context_id)
    flags = set(doc.flags)
    if ctx is not None:
        flags |= set(ctx.flags)
    return {
        "knob": doc.knob,
        "base_knob": doc.knob,
        "context": context_id,
        "documented": True,
        "label": ctx.label if ctx is not None else doc.label,
        "unit": doc.unit,
        "summary": ctx.summary if ctx is not None else doc.summary,
        "detail": ctx.detail if ctx is not None else doc.detail,
        "formula": (ctx.formula if ctx is not None and ctx.formula is not None
                    else doc.formula),
        "physical": (ctx.physical if ctx is not None and ctx.physical else doc.physical),
        "code_ref": doc.code_ref,
        "doc_ref": list(doc.doc_ref) if doc.doc_ref and doc.doc_ref[0] else None,
        "flags": sorted(flags),
        "default": doc.default,
        "default_source": None,
        "search": None,
        "bounds_source": None,
        "hard": {"lo": doc.hard_lo, "hi": doc.hard_hi, "kind": None,
                 "choices": None, "section": None, "source": None,
                 "note": ("mesher schema limit" if doc.hard_lo is not None
                          else "no hard schema clamp on this name")},
        "contexts": sorted(doc.contexts),
    }


def _doc_for(knob: str, context_id: str) -> dict:
    from .knobs_generators import GENERATOR_KNOBS, split_knob

    base, _prefix = split_knob(knob)
    doc = GENERATOR_KNOBS.get(base) or GENERATOR_KNOBS.get(knob)
    if doc is None:
        return _unknown(knob, context_id)
    if context_id not in doc.contexts and context_id not in ("generator",):
        # A requested native/rows context that nobody authored is NOT the generator meaning.
        if context_id in ("native", "rows") or context_id.startswith(("native:", "rows:")):
            return _unknown(knob, context_id)
    cid = context_id if context_id in doc.contexts else "generator"
    out = _merge_doc(doc, cid)
    out["knob"] = knob
    return out


def describe(context_or_typology: str, knob: str) -> dict:
    """Describe ``knob`` in a context id (``"generator"``, ``"rows"``, ...) or a typology.

    A typology lookup uses that typology's own knob entry (so prefixed names such as
    ``h_rm_mm`` keep their plane and their per-typology bounds). An unknown lookup returns
    ``documented: False`` instead of raising.
    """
    key = str(context_or_typology)
    catalog = _catalog()
    typ = catalog["typologies"].get(key)
    if typ is None:
        return _doc_for(str(knob), key)

    for entry in typ["knobs"]:
        if entry["knob"] == knob:
            out = dict(entry)
            out["typology"] = typ["name"]
            return out
    base = str(knob)
    from .knobs_generators import split_knob

    base, _prefix = split_knob(base)
    for entry in typ["knobs"]:
        if entry["base_knob"] == base:
            out = dict(entry)
            out["typology"] = typ["name"]
            out["requested_knob"] = knob
            return out
    if not typ["documented"]:
        return _unknown(str(knob), typ["kind"], typology=typ["name"])
    # Documented domain, but this knob is not used by this typology.
    out = _doc_for(base, "generator" if typ["kind"] == "generator" else typ["kind"])
    out["typology"] = typ["name"]
    out["requested_knob"] = knob
    out["in_typology"] = False
    return out


def knobs_for(typology: str) -> list[dict]:
    """Every authored knob entry for ``typology``; ``[]`` for an unknown/undocumented id."""
    typ = _catalog()["typologies"].get(str(typology))
    if typ is None:
        return []
    return [dict(entry) for entry in typ["knobs"]]


def bounds_for(typology: str, knob: str) -> dict:
    """The default + search bounds + hard limits for ``(typology, knob)``.

    ``bounds_source`` names the exact YAML file and key where the search box LIVES, so a
    GUI editor can save an edit back to the authority instead of a private copy.
    """
    typ = _catalog()["typologies"].get(str(typology))
    if typ is None:
        return _unknown(str(knob), "unknown", typology=str(typology))
    for entry in typ["knobs"]:
        if entry["knob"] == knob:
            return {
                "typology": typ["name"],
                "knob": entry["knob"],
                "documented": True,
                "default": entry.get("default"),
                "default_source": entry.get("default_source"),
                "search": entry.get("search"),
                "bounds_source": entry.get("bounds_source"),
                "hard": entry.get("hard"),
            }
    from .knobs_generators import split_knob

    base, _prefix = split_knob(str(knob))
    for entry in typ["knobs"]:
        if entry["base_knob"] == base:
            return {
                "typology": typ["name"],
                "knob": entry["knob"],
                "requested_knob": knob,
                "documented": True,
                "default": entry.get("default"),
                "default_source": entry.get("default_source"),
                "search": entry.get("search"),
                "bounds_source": entry.get("bounds_source"),
                "hard": entry.get("hard"),
            }
    # A domain not yet authored still has REAL bounds in its YAML. Return the location of
    # that box so a GUI editor can find it, without fabricating knob prose.
    index = (typ.get("bounds_index") or {}).get(str(knob))
    if isinstance(index, dict):
        return {
            "typology": typ["name"],
            "knob": str(knob),
            "documented": typ["documented"],
            "default": None,
            "default_source": None,
            "search": {
                "lo": index.get("lo"),
                "hi": index.get("hi"),
                "search": index.get("search"),
                "log": index.get("log"),
            },
            "bounds_source": {"file": index.get("file"), "key": index.get("key")},
            "hard": {"lo": None, "hi": None, "kind": None, "choices": None,
                     "section": None, "source": None,
                     "note": "knob prose is not authored for this domain yet"},
            "note": ("the search bound is real and lives in the cited YAML; the knob "
                     "description is not authored in the current domains"),
        }
    return _unknown(str(knob), typ["kind"], typology=typ["name"])


def all_typologies() -> list[str]:
    """Every resolved catalog id, sorted (catalog entries plus uncatalogued typology files)."""
    return sorted(_catalog()["typologies"])


def catalog_version() -> int:
    return int(_catalog()["catalog_version"])


def domains_covered() -> tuple[str, ...]:
    return tuple(_catalog()["domains_covered"])
