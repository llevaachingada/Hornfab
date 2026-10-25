"""Drift gate for the parameter single-source-of-truth layer.

Offline. FAILS (never warns) when the docs stop agreeing with the authorities. Every
expected value is READ from the authority, never typed twice.
"""
from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from hornlab_search.design import families
from hornlab_search.design.generators import grid, registry
from hornlab_search.design.params import (
    all_typologies,
    bounds_for,
    catalog_version,
    describe,
    domains_covered,
    knobs_for,
)
from hornlab_search.design.params.catalog import (
    DOMAINS,
    _rows_default,
    build_catalog,
    catalog_json_bytes,
)
from hornlab_search.design.params.knobs_generators import GENERATOR_KNOBS
from hornlab_search.design.params.knobs_rows import (
    ROWS_KNOBS,
    ROWS_TYPOLOGY_NOTES,
    split_rows_knob,
)
from hornlab_search.design.params.schema import (
    FLAGS,
    SUMMARY_LIMIT,
    validate_knob_doc,
    validate_knob_docs,
)

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "hornlab_search" / "gui" / "static" / "param-catalog.v1.json"
OVERLOADED = ("n", "q", "a_deg", "T", "stop_deg", "max_wall_deg", "exponent")


# ------------------------------------------------------------------ import light


def test_import_is_light_without_numpy():
    """Importing the package must not pull numpy (or the mesher/search layers)."""
    code = (
        "import sys\n"
        "sys.modules['numpy'] = None\n"
        "import hornlab_search.design.params as p\n"
        "bad = [m for m, v in sys.modules.items() if m.split('.')[0] == 'numpy' and v is not None]\n"
        "assert not bad, bad\n"
        "assert p.schema.__name__.endswith('.schema')\n"
        "print('import-light OK')\n"
    )
    proc = subprocess.run([sys.executable, "-c", code], cwd=str(ROOT),
                          capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "import-light OK" in proc.stdout


# ------------------------------------------------------------------ domain coverage


def test_every_default_knob_has_a_doc_when_the_domain_is_covered():
    domains = set(domains_covered())
    assert set(DOMAINS) <= {"generators", "rows", "native"}
    if "generators" not in domains:
        pytest.fail("the generators domain must be covered by this lane")
    missing = sorted(set(registry.DEFAULT_KNOBS) - set(GENERATOR_KNOBS))
    assert not missing, f"DEFAULT_KNOBS with no GENERATOR_KNOBS entry: {missing}"


def test_generator_docs_cover_the_visible_block_keys():
    required = {
        "n_anchors", "max_wall_deg", "mouth", "wall_thickness_mm",
        "perturb.u_max", "perturb.mode", "zs_frac", "w",
    }
    assert required <= set(GENERATOR_KNOBS)


# ------------------------------------------------------------------ defaults / hard limits


def test_documented_defaults_equal_default_knobs():
    for name, value in registry.DEFAULT_KNOBS.items():
        doc = GENERATOR_KNOBS[name]
        assert doc.default == value, (
            f"{name}: GENERATOR_KNOBS default {doc.default!r} != DEFAULT_KNOBS {value!r}")


def test_names_outside_default_knobs_carry_no_authored_default():
    for name, doc in GENERATOR_KNOBS.items():
        if name not in registry.DEFAULT_KNOBS:
            assert doc.default is None, (
                f"{name}: block/config values live in examples/, so this doc must not "
                f"author a default (got {doc.default!r})")


def _family_spec(name: str):
    found = [(fam, families.FAMILY_KEYS[fam][name])
             for fam in sorted(families.FAMILY_KEYS)
             if name in families.FAMILY_KEYS[fam]]
    if not found:
        return None
    los = [spec.lo for _, spec in found if spec.lo is not None]
    his = [spec.hi for _, spec in found if spec.hi is not None]
    return (max(los) if los else None, min(his) if his else None)


def test_documented_hard_limits_equal_family_keyspec():
    for name, doc in GENERATOR_KNOBS.items():
        spec = _family_spec(name)
        if spec is None:
            assert doc.hard_lo is None and doc.hard_hi is None, (
                f"{name}: not a family key, so hard limits must be None")
        else:
            lo, hi = spec
            assert (doc.hard_lo, doc.hard_hi) == (lo, hi), (
                f"{name}: hard limits {doc.hard_lo, doc.hard_hi} != KeySpec {lo, hi}")


# ------------------------------------------------------------------ catalog consistency


def test_every_resolved_typology_matches_domain_coverage():
    catalog = build_catalog(ROOT)
    domains = set(catalog["domains_covered"])
    kind_domain = {"generator": "generators", "rows": "rows", "native": "native"}
    for name, typ in catalog["typologies"].items():
        expected = kind_domain[typ["kind"]] in domains
        assert typ["documented"] is expected, (
            f"{name}: documented={typ['documented']} but {typ['kind']} -> "
            f"{kind_domain[typ['kind']]} in {sorted(domains)}")
        if not expected:
            assert typ["knobs"] == [], f"{name}: undocumented typology fabricated knobs"


def test_catalog_resolves_catalog_and_uncatalogued_configs():
    catalog = build_catalog(ROOT)
    ids = set(catalog["typologies"])
    assert len(ids) >= 36
    assert {"conical", "salmon_elliptical", "osse_baseline"} <= ids
    # Every file under examples/typologies is represented once.
    files = {f"examples/typologies/{p.name}"
             for p in (ROOT / "examples" / "typologies").glob("*.yaml")}
    resolved = {t["config_path"] for t in catalog["typologies"].values()}
    assert files <= resolved


# ------------------------------------------------------------------ prose validation


def test_metadata_validates():
    problems = validate_knob_docs(GENERATOR_KNOBS)
    problems += validate_knob_docs(ROWS_KNOBS)
    assert not problems, "\n".join(problems)


def test_summaries_are_short_and_placeholder_free():
    for table in (GENERATOR_KNOBS, ROWS_KNOBS):
        for name, doc in table.items():
            assert len(doc.summary) <= SUMMARY_LIMIT, f"{name}: summary too long"
            assert validate_knob_doc(doc) == [], f"{name}: invalid"
            assert doc.flags <= FLAGS


# ------------------------------------------------------------------ anchors resolve


def test_code_refs_resolve():
    refs = {doc.code_ref for table in (GENERATOR_KNOBS, ROWS_KNOBS)
            for doc in table.values() if doc.code_ref}
    catalog = build_catalog(ROOT)
    for typ in catalog["typologies"].values():
        refs.update(k["code_ref"] for k in typ["knobs"] if k.get("code_ref"))
    for ref in sorted(refs):
        module_name, _, symbol = ref.rpartition(".")
        module = importlib.import_module(module_name)
        assert hasattr(module, symbol), f"code_ref does not resolve: {ref}"


def test_doc_refs_exist_and_headings_are_present():
    refs: set[tuple[str, str]] = set()
    for table in (GENERATOR_KNOBS, ROWS_KNOBS):
        for doc in table.values():
            if doc.doc_ref and doc.doc_ref[0]:
                refs.add(tuple(doc.doc_ref))
    catalog = build_catalog(ROOT)
    for typ in catalog["typologies"].values():
        for knob in typ["knobs"]:
            if knob.get("doc_ref"):
                refs.add(tuple(knob["doc_ref"]))
    for path, heading in sorted(refs):
        target = ROOT / path
        assert target.is_file(), f"doc_ref path missing: {path}"
        lines = target.read_text(encoding="utf-8").splitlines()
        assert any(line.strip().startswith(heading) for line in lines), (
            f"doc_ref heading missing in {path}: {heading!r}")


# ------------------------------------------------------------------ wire artifact


def test_committed_json_is_byte_identical_to_a_fresh_build():
    expected = catalog_json_bytes(build_catalog(ROOT))
    actual = JSON_PATH.read_bytes()
    assert actual == expected, (
        "committed param-catalog.v1.json is stale; run "
        ".venv\\Scripts\\python.exe tools/gen_param_catalog.py --write")


def test_catalog_version_and_domains_are_exposed():
    assert isinstance(catalog_version(), int)
    assert catalog_version() >= 1
    assert tuple(domains_covered()) == DOMAINS


# ------------------------------------------------------------------ overloads


def test_overloaded_names_carry_distinct_contexts_or_are_deferred():
    for name in OVERLOADED:
        doc = GENERATOR_KNOBS[name]
        assert "overloaded" in doc.flags, f"{name}: must be flagged overloaded"
        assert len(doc.contexts) >= 2 or "deferred" in doc.flags, (
            f"{name}: needs >=2 contexts or an explicit deferred flag")


def test_deferred_native_meaning_is_not_invented():
    q = GENERATOR_KNOBS["q"].contexts.get("rosse")
    assert q is not None and "deferred" in q.flags
    exponent = GENERATOR_KNOBS["exponent"].contexts.get("native")
    assert exponent is not None and "deferred" in exponent.flags
    # The generator meaning itself is authored.
    assert GENERATOR_KNOBS["q"].contexts["generator"].summary
    assert GENERATOR_KNOBS["exponent"].contexts["generator"].summary


# ------------------------------------------------------------------ rows domain


def _rows_typologies(catalog: dict) -> dict[str, dict]:
    return {name: typ for name, typ in catalog["typologies"].items()
            if typ["kind"] == "rows"}


def _live_rows_default(base: str):
    """Independent read of the live grid.py default (no catalog helper)."""
    key = ("a_throat" if base == "a{k}_throat"
           else "a_mouth" if base == "a{k}_mouth" else base)
    maps = ("GRID_DEFAULTS", "ROWS_KNOB_DEFAULTS", "ROWS_LECLEACH_KNOB_DEFAULTS",
            "ROWS_MOD_KNOB_DEFAULTS", "ROWS_AR_KNOB_DEFAULTS",
            "ROWS_IWATA_KNOB_DEFAULTS", "ROWS_TOROIDAL_KNOB_DEFAULTS")
    found = {}
    for map_name in maps:
        table = getattr(grid, map_name, {})
        if key in table:
            found[map_name] = table[key]
    if not found or len(set(found.values())) != 1:
        return None
    return next(iter(found.values()))


def test_rows_domain_is_claimed_and_all_rows_typologies_resolve_with_knobs():
    assert "rows" in domains_covered()
    catalog = build_catalog(ROOT)
    rows = _rows_typologies(catalog)
    assert rows, "no rows typologies resolved"
    for name, typ in rows.items():
        assert typ["documented"] is True, f"{name}: rows domain is claimed but not documented"
        assert typ["knobs"], f"{name}: documented rows typology has no knobs"


def test_every_rows_config_search_key_has_a_rows_doc():
    """The gate: every seed/bounds key in every rows config resolves to ROWS_KNOBS."""
    catalog = build_catalog(ROOT)
    for name, typ in _rows_typologies(catalog).items():
        data = yaml.safe_load((ROOT / typ["config_path"]).read_text(encoding="utf-8"))
        keys = set(data.get("seed_params") or {}) | set(data.get("bounds") or {})
        for key in sorted(keys):
            base, _prefix = split_rows_knob(key)
            doc = ROWS_KNOBS.get(base)
            assert doc is not None, (
                f"{name}: search key {key!r} resolves to {base!r}, which has no "
                "ROWS_KNOBS entry (document it, or flag it as a non-knob)")


def test_rows_docs_author_no_defaults_or_hard_numbers():
    """Prose only: catalog reads every value from grid.py, never from this module."""
    for name, doc in ROWS_KNOBS.items():
        assert doc.default is None, f"{name}: ROWS_KNOBS must not author a default"
        assert doc.hard_lo is None and doc.hard_hi is None, (
            f"{name}: ROWS_KNOBS must not author a hard limit")


def test_rows_default_helper_equals_the_live_grid_default_exactly():
    for base in ROWS_KNOBS:
        value, source = _rows_default(base)
        expected = _live_rows_default(base)
        assert value == expected, (
            f"{base}: catalog default {value!r} != live grid.py default {expected!r}")
        if expected is None:
            assert source is None, f"{base}: no single grid default, so no source"
        else:
            assert source is not None and source["file"].endswith("grid.py"), (
                f"{base}: a grid default must cite grid.py")


def test_rows_emitted_grid_defaults_match_the_live_map():
    catalog = build_catalog(ROOT)
    for name, typ in _rows_typologies(catalog).items():
        for knob in typ["knobs"]:
            src = knob.get("default_source")
            if not src or not src["file"].endswith("grid.py"):
                continue
            map_name, _, key = src["key"].partition(".")
            live = getattr(grid, map_name)
            assert knob["default"] == live[key], (
                f"{name}.{knob['knob']}: emitted default {knob['default']!r} != "
                f"{map_name}.{key} {live[key]!r}")


def test_rows_span_choices_come_from_grid():
    catalog = build_catalog(ROOT)
    for name, typ in _rows_typologies(catalog).items():
        span = next((k for k in typ["knobs"] if k["knob"] == "span"), None)
        if span is None:
            continue
        assert span["hard"]["choices"] == list(grid.ROWS_SPANS), (
            f"{name}: span choices must be grid.ROWS_SPANS")


def test_rows_hard_caps_are_read_from_named_grid_constants():
    catalog = build_catalog(ROOT)
    signed = catalog["typologies"]["salmon_x_signed"]
    xamp = next(k for k in signed["knobs"] if k["knob"] == "g_x_amp")
    assert (xamp["hard"]["lo"], xamp["hard"]["hi"]) == (
        -grid.ROWS_MAX_X_AMP, grid.ROWS_MAX_X_AMP)
    assert xamp["hard"]["source"]["key"] == "ROWS_MAX_X_AMP"


def test_rows_typology_notes_are_valid_prose():
    bad = ("todo", "tbd", "???", "lorem")
    for name, notes in ROWS_TYPOLOGY_NOTES.items():
        assert notes, f"{name}: empty override mapping"
        for base, ctx in notes.items():
            assert base in ROWS_KNOBS, f"{name}: override for unknown base {base!r}"
            assert len(ctx.summary) <= SUMMARY_LIMIT, f"{name}.{base}: summary too long"
            assert ctx.detail.strip(), f"{name}.{base}: empty detail"
            assert ctx.physical.strip(), f"{name}.{base}: empty physical effect"
            text = (ctx.label + " " + ctx.summary + " " + ctx.detail).lower()
            assert not any(tok in text for tok in bad), f"{name}.{base}: placeholder"


def test_rows_typology_notes_are_wired_and_typed():
    catalog = build_catalog(ROOT)
    rows = _rows_typologies(catalog)
    for name in ROWS_TYPOLOGY_NOTES:
        assert name in rows, f"note for a typology that is not a rows config: {name}"
    signed = {k["knob"]: k for k in rows["salmon_x_signed"]["knobs"]}["g_x_amp"]
    shaped = {k["knob"]: k for k in rows["salmon_x_shape"]["knobs"]}["g_x_amp"]
    assert signed["summary"] != shaped["summary"], "the signed-X override did not apply"
    assert "negative" in signed["summary"].lower()
    lecl = {k["knob"]: k for k in rows["lecleach_rollback"]["knobs"]}["g_stop_deg"]
    assert "fourcade" in lecl["summary"].lower(), "the verified-march override did not apply"


# ------------------------------------------------------------------ public API never raises


def test_unknown_lookups_degrade_to_placeholders():
    assert describe("no_such_typology", "no_such_knob")["documented"] is False
    assert describe("generator", "no_such_knob")["documented"] is False
    assert knobs_for("no_such_typology") == []
    assert bounds_for("no_such_typology", "x")["documented"] is False
    assert "conical" in all_typologies()


def test_bounds_source_points_at_the_yaml_that_owns_the_box():
    catalog = build_catalog(ROOT)
    gen = catalog["typologies"]["conical"]["knobs"]
    rm = next(k for k in gen if k["knob"] == "h_rm_mm")
    assert rm["bounds_source"] == {
        "file": "examples/typologies/conical.yaml", "key": "bounds.h_rm_mm"}
    rows = catalog["typologies"]["salmon_elliptical"]
    assert rows["documented"] is True and rows["knobs"]
    rb = bounds_for("salmon_elliptical", "g_stop_deg")
    assert rb["bounds_source"] == {
        "file": "examples/typologies/salmon_elliptical.yaml", "key": "bounds.g_stop_deg"}
    raw = yaml.safe_load(
        (ROOT / "examples/typologies/salmon_elliptical.yaml").read_text(encoding="utf-8"))
    assert rb["search"]["lo"] == raw["bounds"]["g_stop_deg"]["lo"]
    assert rb["search"]["hi"] == raw["bounds"]["g_stop_deg"]["hi"]
    assert rb["documented"] is True
