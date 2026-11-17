# U3 record edits, CPU stage (WP 4.1) - first run

Senior pass, 2026-11-17, Linux container, HEAD after `49e28a9`. CPU only: record build, edits,
validity, real gmsh point-grid meshes. **No solve.** Code: `hornlab_search/geometry/edits.py`;
tests: `tests/test_geometry_edits.py` (8 offline + 1 mesher test, all pass).

Host used here: the **seed** of `hl__biradial_es_style_v7` (not the best stored design: `runs/` is
not in this container). Record route `native`, wall 3.0 mm, mouth 560 W x 350 H, depth 255 mm.

| Variant | Valid (U2) | Max station RMS change outside last 5 % (mm) | Mouth W x H (mm) | Point-grid mesh |
|---|---|---:|---|---|
| control | yes | 0.0 | 560.0 x 350.0 | ok |
| vertical timing → 460 | yes | 28.4 | 560.3 x 460.0 | ok |
| vertical timing → 480 | yes | 34.1 | 560.5 x 480.0 | ok |
| termination split, sides | yes | 3.1 | 590.0 x 352.1 | ok |
| termination split, top/bottom | yes | 3.1 | 560.0 x 380.0 | ok |
| section steering, early (p→3) | yes | 1.5 | 560.0 x 350.0 | ok |
| section steering, late (p→3) | yes | 1.3 | 560.0 x 350.0 | ok |
| diagonal pull 10 mm | yes | 5.4 | 560.0 x 350.0 | ok |

Reading against the U3 CPU lines:
- **Failure line not met:** vertical timing reaches 460 and 480 mm without breaking a validity check,
  so "unused height" is geometrically real on this host.
- **Success line partly met:** 3 of 7 variants reach ≥ 5 mm RMS outside the last 5 % of wall. The
  termination split is confined to the lip by design (its change is mostly inside the last 5-15 %),
  and this seed's sections are already close to p = 3, so steering moves little. Both are honest
  outcomes for this host, not tuning targets; the line is not moved.
- Next: repeat on the best stored biradial and ext-throat designs on the Windows checkout
  (`runs/` needed), then WP 4.2 (2-solve record-route equivalence) before any variant is solved.

**Envelope convention, made concrete (added with the evidence driver):** the "vertical timing →
480" variant puts the *inner* mouth at exactly 480 mm. Under the acoustic-box convention it fits;
under the build-box convention (+2 × 3 mm wall) it is 6 mm over the 480 mm brief and fails the
U2 envelope check. The owner's envelope decision (senior review §4.2) decides whether this
variant is admissible. The 460 mm variant passes both.
