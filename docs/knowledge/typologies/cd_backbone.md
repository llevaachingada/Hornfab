# CD wall-angle backbone (returned-lip hybrids)

- Status: navigation summary. **LABELED HYPOTHESIS**, no published name. A CD-style wall-angle
  backbone is blended into each azimuth row of an existing returned-lip parent, keeping the throat
  station, the roll-on station, the return and the rim bit-identical
  (`_cd_backbone_v1.py:1-21`). Three adapters exist. Rolled parents transfer; Klangfilm–Lamé and
  the generic non-CD rows parents did not pass the predeclared gates.
- Design principles: for each row the pre-roll arc is blended from the parent row toward a solved
  constant-θc backbone schedule; `theta_bb(u)` has a C2 throat transition, a conical body and a C2
  roll-in landing on the parent's own forward station. The blend weight is
  `lam(psi) = bb_h cos^2 psi + bb_v sin^2 psi`. `lam = 0` returns the parent unchanged.
- Appropriate objectives: CD corridor (H/V −6 dB width), 2–4 kHz waistband check, diagonal, DI
  slope/std, on-axis and listening-window smoothness, throat Re(z), and v11 J as a summary only.
  Never rank across briefs, grids or identities.
- Limitations: V is bounded by the roll-on budget (a longer return consumes angle); a conical body
  under a fixed return can waistband at 2–4 kHz; low-band V stays mouth-limited; real driver
  wavefronts and higher-order modes are not modelled.
- Common incorrect assumptions: a backbone dose is not a monotonically better design (J has no
  minimum on the dose axis); a `rows_bb_v1` result is not the parent typology and must never be
  ranked or named as it; the neutral control must build the saved mesh byte-for-byte.
- Key sources and detailed research: [returned-lip CD backbone dossier](../../research/typologies/RETURNED_LIP_CD_BACKBONE_RESEARCH_2026-11-25.md),
  [web report](../../research/typologies/RETURNED_LIP_CD_BACKBONE_WEB_REPORT_2026-11-25.md),
  [evidence](../../evidence/cd_backbone_2026-11-25/README.md). Joint laws:
  [FAMILY_LAWS.md](../FAMILY_LAWS.md).

## Kinds / generators

| Kind / `rows.type` | Adapter | Parent |
|---|---|---|
| `rolled_family_rect_bb_v1` | `cd_backbone_family.py` | `rolled_cd_family.KIND` (`rolled_family_rect_cd_v1`) |
| `klangfilm_lame_hv_bb_v1` | `cd_backbone_family.py` | `klangfilm_lame_hv_family.KIND` (`klangfilm_lame_hv_cd`) |
| `rows_bb_v1` | `cd_backbone_rows_family.py` | generic rows: `lecleach`, `lecleach_ar`, `iwata_ar`, `salmon_elliptical`, `lecleach_mod`, `toroidal_rollback` |

Kernel: `_cd_backbone_v1.py`. Quarter span only.

## Knobs with legal ranges

Backbone knobs (`_cd_backbone_v1.py:31-34`):

| Knob | Range |
|---|---|
| `bb_h` | [0, 1] |
| `bb_v` | [0, 1] |
| `bb_throat_frac` | [0.05, 0.30] |
| `bb_rollin_frac` | [0.15, 0.45] |
| `bb_throat_frac + bb_rollin_frac` | ≤ 0.80 (`MAX_BODY_SUM`, leaves a body) |

Config keys are `g_`-prefixed (`g_bb_h`, …). The parent knobs are carried unchanged under the same
knob mapping (`cd_backbone_family.py:62-74`; `cd_backbone_rows_family.py` carries the parent rows
recipe under `rows.parent_rows`).

## Joint validity laws (file:line)

- **Quarter symmetry only** — `cd_backbone_family.py:103-104`; `cd_backbone_rows_family.py:68-69`.
- **Saved-recipe schema + digest** — `cd_backbone_family.py:105-106`;
  `cd_backbone_rows_family.py:83-84`.
- **Knobs required; all backbone keys present and valid** — `cd_backbone_family.py:62-74`,
  `:107-108`; `cd_backbone_rows_family.py:85-86`.
- **Backbone law at every searched endpoint** — `cd_backbone_family.py:197-209`;
  `cd_backbone_rows_family.py:180-192`.
- **Shape dormancy**: a searched `g_bb_throat_frac`/`g_bb_rollin_frac` needs a strength box away
  from zero (`g_bb_h` or `g_bb_v` `lo > 0`) — `cd_backbone_family.py:210-213`;
  `cd_backbone_rows_family.py:193-196`.
- **Kernel geometry**: pre-roll z and radius monotone, no constriction before the roll, no axis
  crossing, the forward/roll-on station is not moved, finite output —
  `_cd_backbone_v1.py:130-149`.
- **Independent size policy** (`enforce` / `report_only`) and the envelope check —
  `cd_backbone_family.py:156-163`; `cd_backbone_rows_family.py:102-110`, `:148`.
- **`rows_bb_v1` neutral rule**: `bb_h == bb_v == 0` returns the parent's own `(inner_points,
  meta)` and **no** `outer_points`, so the shell is offset exactly as for the bare rows recipe and
  the verify mesh is byte-identical — `cd_backbone_rows_family.py:14-17`, `:152-153`.
- **`rows_bb_v1` parent identity is carried verbatim** under `rows.parent_rows`; parent type must be
  one of the allowed kinds — `cd_backbone_rows_family.py:8-12`, `:64-75`.
- **Parent contract mirrored**: `cd_backbone_family` runs the parent's
  `validate_search_config` on the parent-only bound subset — `:196`.

## Inert knobs per mode

- All backbone knobs are inert at `bb_h == bb_v == 0`; the kernel returns the parent object
  (`_cd_backbone_v1.py:59-60`; `cd_backbone_family.py:132-133`).
- `g_bb_throat_frac` / `g_bb_rollin_frac` are dormant when both strengths can be zero
  (`cd_backbone_family.py:210-213`).
- Parent-mode knobs are inherited from the parent; for `rows_bb_v1` only the backbone bound and
  dormancy rules are added (`cd_backbone_rows_family.py:173-196`).
- The Klangfilm parent's own class/blend rules still apply when `klangfilm_lame_hv_bb_v1` is used
  (see [klangfilm_lame.md](klangfilm_lame.md)).

## Implementation-digest files

- `cd_backbone_family`: this module + `_cd_backbone_v1.py` + `"{kind};parent={parent_digest}"`
  (`cd_backbone_family.py:50-59`).
- `cd_backbone_rows_family`: this module + `_cd_backbone_v1.py` + `cd_backbone_family.py` +
  `grid.py` + `profiles.py` + `throat_hv.py` + `"rows_bb_v1;parent=grid.rows_grid_points"`
  (`cd_backbone_rows_family.py:47-61`).
- `_rim_beak_v1.py` is a separate module over these kinds; adding it does not change these digests.

## Best-known designs (from I3 evidence)

- `docs/evidence/cd_backbone_2026-11-25/` [current] — rolled anchor `fa5b207bca6d`: control
  J 8.121 → `bb_h` 0.5 J **5.407** (H 65.7° at 8 kHz); keeper `bb_h` 0.65/throat 0.25 J 4.679.
  Second rolled body `20874108fe25`: J 7.683 → **4.562**. Klangfilm–Lamé control J 9.0845; **no**
  Lamé candidate passes (waistband + loading).
- `docs/evidence/cd_variants_2026-11-25/` [negative-result] — Le Cleac'h / Iwata `rows_bb_v1`
  hybrids: no variant passes all six rules (14 solves); 8 kHz H tops 59.9°; hypothesis rejected.
- `docs/evidence/cd_bo_cohort_2026-11-25/` [current; no results yet] — four predeclared 100-valid
  CMA cohorts under v11 open115; builds and space preflight present.
- `docs/evidence/cd_v11_2026-11-20/` and `cd_v11_completion_2026-11-20/` [current] — eight
  objective-v11 CD lanes; 8/8 reached 50 valid evals after completion.
- Mechanism (from `docs/evidence/directivity_attribution_2026-11-24/`): 6–8 kHz H follows the wall
  angle at ~20–40 % of the pre-roll arc.

## Open questions

- The conditional CMA over (`bb_h`, `bb_v`, throat, roll-in) was **not run**; the dose bracket puts
  the passing interval at rolled `bb_h` 0.45–0.50 with the upper edge set by throat loading.
- The V lever needs the V roll-on station moved outward or a tighter roll-in — an owner/look
  decision.
- The Lamé needs a different mouth/rollback or depth, not more backbone knobs.
- Low-band V (≤ 4 kHz) stays mouth-limited; spatial convergence beyond one epw step and the independent
  bempp cross-check remain open.
