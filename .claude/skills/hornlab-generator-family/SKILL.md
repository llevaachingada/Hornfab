---
name: hornlab-generator-family
description: Add or change a horn generator/typology implementation in hornlab-search without silently orphaning saved recipes. Use when the behaviour change is not a knob default (new shape law, new family, new adapter), when wiring a new generator module into the dispatch lists, or when a recipe is refused for schema/implementation mismatch. New typology/objective research is hornlab-typology-research; a knob-only variant is hornlab-shape-check.
---

# hornlab generator family

## The implementation digest (read this first)

A saved recipe records `rows.schema` and `rows.implementation_sha256`; loading it re-hashes the family's
declared source files and refuses on mismatch (`hornlab_search/design/generators/cd_backbone_rows_family.py:78-86`).
The digest is a sha256 over those source files **and** the kind string, with CRLF normalised to LF
(`:47-61`):

```python
def implementation_digest():
    for path in _sources():                 # Path(__file__), kernel, base, grid, profiles, throat_hv
        data = path.read_bytes().replace(b"\r\n", b"\n")
        digest.update(len(data).to_bytes(8, "big")); digest.update(data)
    digest.update(f"{KIND};parent=grid.rows_grid_points".encode())
```

**Editing any file in `_sources()` orphans every saved recipe of that family.** So:

- **New behaviour goes in a new module** (`<new>_family.py` + its `<new>_v1.py` kernel), with its own
  `is_family_spec` / `design_params` / `resolve_grid` / `KIND` / `SCHEMA` / `implementation_digest()`.
  Do not edit an existing family module or kernel to add a variant. Examples: `cd_backbone_rows_family.py`,
  `rim_beak_family.py` (each hashes only its own module + kernel, `rim_beak_family.py:41-44`).
- **Knob defaults stay additive**; changing geometry for every existing hash is a different task.
- Widen a family's `_sources()` only deliberately — it is a recipe-breaking change; say so in the commit.

## Register the module in the dispatch lists (byte-wise)

The module is inert until it is imported and tried in each dispatch loop. Add the module to **both** the
`from .generators import (...)` import and the `for family in (...)` tuple at every site:

- `hornlab_search/design/generators/grid.py` — four blocks: `:3037-3039`, `:3126-3128`, `:3174-3176`,
  `:3230-3232` (rows resolution, catalog, etc.; the lists are not identical, check each).
- `hornlab_search/mesh/build.py` — `:590-593`.
- `hornlab_search/design/generated.py` — `:270-276` (validate_search_config) and `:381-383`.

**Preserve each file's line endings; edit byte-wise (`read_bytes`/`replace`), never `sed -i`.** Measured
2026-11-25: `grid.py` and `generated.py` are CRLF; `mesh/build.py` and the new family module are LF. The
digest normalises CRLF→LF, so a half-converted file is not a cosmetic problem.

**Caveat:** `grid.py` is itself in `rows_bb_v1`'s `_sources()` (`cd_backbone_rows_family.py:47-51`), so a
dispatch edit there changes that family's digest and orphans its saved recipes — record the bump.

## Tests: parity, then digest guard

- **Parity**: with neutral knobs the new family must reproduce its parent **bit-for-bit** (geometry and a
  byte-identical verify mesh). Copy the pattern in `tests/test_cd_backbone_geometry.py:31` and `:150`
  (`test_neutral_is_bit_for_bit_parent`, `test_rows_neutral_verify_mesh_is_byte_identical`) or
  `tests/test_rim_beak_geometry.py:38` (`test_neutral_returns_parent_bit_for_bit`).
- **Digest-unchanged guard**: adding a new kind must not move an existing kind's digest. Pin the old value
  and assert it, as `tests/test_cd_backbone_geometry.py:125-126` does with
  `SAVED_ROLLED_DIGEST_PREFIX`; a digest pin with files/environment lives in
  `tests/test_klangfilm_hv_digest_pin.py:64`.
- **Recipe refusals**: tampering with `schema` or `implementation_sha256` must raise
  (`tests/test_cd_backbone_geometry.py:183-185`, `tests/test_rim_beak_geometry.py:83-85`).

## Run (CPU)

```powershell
.venv\Scripts\python.exe -m pytest tests\test_design_generators_grid.py tests\test_mesh_build_grid.py `
    tests\test_param_catalog.py tests\test_cd_backbone_geometry.py tests\test_rim_beak_geometry.py -q
```

Then prove it meshes with `hornlab-shape-check`, and read the family's laws in
`docs/knowledge/FAMILY_LAWS.md` before choosing bounds.
