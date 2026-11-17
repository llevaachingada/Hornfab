# X1 addendum — Klangfilm recipe provenance resolved

**Run:** 2026-11-16 23:40 ET, HEAD `207f97a`. Read-only; one import of a digest function, no mesh,
no solve. Extends `X1_ROUND_TRIP.md`, which reported 0/10 Klangfilm designs materialized.

## Finding

The stored Klangfilm designs **can be rebuilt with verified provenance.**

- Stored recipes (for example `runs/20261116T224336Z-screen-55f39d/designs/01e5144eed36/design.json`)
  carry `rows.schema: klangfilm-lame-v1` and
  `rows.implementation_sha256: ea5026813d6aef0da87d844cb5b74bac97eaa10f146a1aaf874190b4f7ddc4a5`.
- The current adapter `hornlab_search/design/generators/klangfilm_lame_family.py:62-68` accepts
  only schema `klangfilm-lame-canonical-v1` with its own digest, so it refuses them. That is the
  refusal X1 hit. It is an adapter-version check, not a geometry failure.
- Those runs were made through the **legacy bridge** `tools/geometry/klangfilm_lame_cli.py`, whose
  `implementation_digest()` (`:20-26`) hashes `tools/geometry/klangfilm_lame.py`,
  `tools/geometry/rolled_rect_cli.py` and itself.
- **Evaluating that function at HEAD `207f97a` returns exactly `ea5026813d6a…c4a5`.** The three
  legacy files are byte-for-byte what produced the stored designs.
- `hornlab_search/design/generators/_klangfilm_lame_v1.py` (the kernel X1's `.x1/legacy_k.py` used)
  differs from `tools/geometry/klangfilm_lame.py` in one line only: the import of the Lamé cap
  module (`tools.geometry.lame_cap` versus `._lame_cap_v1`). Those two cap modules are identical
  after line-ending normalization (0 differing lines).

## Consequence for X1

- The ten candidate Klangfilm grids in `.x1/legacy_k_results.txt` come from the same mathematics as
  the verified legacy kernel. They may be admitted to the X1 acceptance tests, with provenance
  stated as "legacy bridge, digest verified at 207f97a; kernel copy differs by one import line".
- Strictest route for a re-run: build the grids by importing `tools/geometry/klangfilm_lame.py`
  directly (the digest-covered file), not the generators copy.
- Still open for Klangfilm, as for the other routes: contract tests 1–5 (refinement, mesh agreement
  with inner and shell surfaces separated, envelope, exact metadata, determinism).

## A general point for the implementation plan

Two adapters for one family now disagree about which recipes are valid. Historical designs are
rebuildable only through a process-local bridge CLI. Any plan that re-scores or re-uses history
needs a rule for this: either adapters accept older schemas they can verify by digest, or the
legacy route is kept runnable and named in the record.
