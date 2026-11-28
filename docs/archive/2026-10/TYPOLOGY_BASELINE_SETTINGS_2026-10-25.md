# Per-typology baseline settings (Phase D) — 2026-10-25

Owner ask (original handoff §Phase D): land the per-typology DEFAULT-SETTINGS table — knobs,
sensible bounds, default config values, the recommended screen/verify/final treatment — grounded in
each typology's dossier + the measured M3/M5 calibration numbers. Governing rule (handoff §4b):
the shipped `examples/typologies/*.yaml` defaults are verified sensible per their dossiers below;
**where a better default requires changing an EXISTING default → PROPOSAL ONLY** (owner gates all
default flips; nothing in this doc changes any default).

Complements (committed): `12_RESEARCH_BASIS.md` §13.6 (the Phase-D direction, owner-gated), the
R9 audit of the same date (`R9_AUDIT_2026-10-25.md`), and the GPU smoke matrix for the new
configurations (`docs/evidence/TYPOLOGY_SMOKE_MATRIX_2026-10-25.md` — LANDED: 3/5 seeds solve
green (biradial 2086 dofs / qtw 1616 / lecleach_asym 2815 full ring), 2/5 shipped demo seeds honestly
FAIL the screen caps (salmon_x_signed 14,414 tris + envelope overshoot 0.2201; salmon_ripple12 5,358
dofs > 5,000) — reseed proposals in the evidence doc + R9/baseline proposals below; nothing altered).

## Tier recipe (measured, frozen)

| Tier | Grid (frozen `config.py`) | DOF cap (quarter) | Balloon | Cost guidance (TOOLCHAIN) |
|---|---|---|---|---|
| screen | `FREQ_GRIDS["screen"]` = 12 log pts, 500–10 kHz (clamped to the brief's band top) | 5,000 | 512 (16×32) | ≈ 5.0 s/eval @ ~2.4k dofs |
| verify | 25 log pts, 300–16 kHz | 7,000 | 1024 (23×45) | ≈ 7.5 s/eval near cap |
| final | 36 log pts, 250–20 kHz | 8,900 | 2592 (36×72) | minutes per design |

Budgets via `campaign.budget_for_tier`: screen `max(40, 10×searchable knobs)`, 1 seed; compare
`max(150, 25×knobs)`, 2 seeds; GUI shows these as captions only. Caps NEVER raised offline
(TOOLCHAIN). 8 kHz band stays honest: above f11 = 7,914 Hz (1″ throat), compare GEOMETRIES, not
drivers — the f11 caveat renders wherever band_hi > f11 (G1).

## The five new (S1a) typologies — settings as shipped (verified sensible per dossier)

| Config | Knobs (bounds) | Seed rationale (dossier) | Recommended treatment |
|---|---|---|---|
| `biradial_keele` (US4308932A) | L [170,220], h_a [30,45], v_a [18,34], h_rm [140,197], v_rm [95,146], h_n [2,8], v_n [2,8] (claim-14 range) | K-law-consistent V case from the dossier (c 2.2847e-10, end-wall 39.35°); envelope-true at 396×296 inside 400×300 (test-pinned) | screen → verify winner; n range keeps both power-series lobes honest; do not widen bounds without the dossier's measured V case as anchor |
| `qtw_waveguide` (Hughes/Peavey rule) | L [150,215], h_a [34,46], v_a [22,33], h_R_arc [25,80], v_R_arc [25,80] | arc rule sets a_deg = coverage/2 per plane; rm DERIVED (never set) | screen → verify; the arc rule ties a_deg to the brief, so widening a beyond coverage/2 would break the published rule — keep bounds |
| `lecleach_asym_odd` (our reconstruction) | g_fc [600,1200], g_T [0.3,1.0], g_stop [120,240], g_eps_m [−0.3,0.3], g_eps_start [0,0.5]; span full, n_phi 25 | eps forces the full ring; W·fc ≈ 1.88e5 seeds the fc's when brief-derived | screen with the graded penalty ON; full ring bills ~4× the quarter — treat as verify-tier-sized when picking budgets |
| `salmon_x_signed` (sign demo) | fc_h/fc_v [600,1200], g_T [0.3,1.0], g_stop [120,240], g_x_amp [−0.4,0.4], x_fc [0,0.3]; n_phi 15 quarter | x_amp −0.25 seed = corner-in; +0.25 = the literal X; magnitudecap unchanged | screen; P-M4-2 note: the mod stop window (120,240) is defined but never enforced — do not rely on the stop knob to gate shapes |
| `salmon_ripple12` (our pleats experiment) | fc_h/fc_v [600,1200], g_T [0.3,1.0], g_stop [120,240], g_ripple_lobes [6,24], g_ripple_amp_mm [0.5,6], g_ripple_start [0.7,0.95]; span half, quadrants '14' | ≥4 samples-per-lobe guard: 25 rows/half-span with 12 lobes = exactly 4.0 | screen with lobes/amp wide enough to hunt; ≥ 4 samples/lobe must hold at any lobe count selected (validator enforces) |

Cross-cutting for all five: keep `infeasible_penalty: graded` ON (S1a enables it on the organic
configs; flat is the schema default), screen first then verify only the winner, and record the
smoke evidence before any search (one GPU job at a time).

## The Phase-D template brief: `examples/briefs/axi_2in_large.yaml`

2″ exit (25.4 mm radius, 4°), envelope 640×460×340 (wider than tall, HV), coverage 90×40,
band 500–8 kHz, **target.f0_hz 1000** + **objective v3**, load 0.5. This is the template
new-typology briefs ride into derived campaigns (the K-law preflight + seed derivation activate
only for f0-carrying briefs). For 1-inch briefs, f0 is optional: `absent = band_lo = byte-for-byte`.

## Objective-v3 usage guidance (default status = owner decision below)

- v3 is **opt-in** (`objective.version: 3` in the config's objective block; v1/v2 untouched —
  verified in scalar_v2 + the validator; the C3/C4 GUI surfaces render it: select option, run KPI,
  badge, mixed-key compare warns).
- Use v3 + f0 when the brief's low band is physically uncontrollable inside the envelope (the 75×35
  diagnosis: 61–87% of cov loss was unattainable-band). Do not retro-score old runs with v3.
- Feasibility preflight lands in run-dir config.yaml (`feasibility` block; GUI seed-derivation
  card) — read it before interpreting a run's J.

## Cross-cutting measured findings (numbers with pointers; proposals as PROPOSAL ONLY)

1. **`rear_res_factor`** (default 1.0; rides solve-spec extra): AXI screen-measured — 1.5 → 1,135
   dofs (−18.8%), 2.0 → 1,060 dofs (−24.1%), all inside the CP-7f bars, J deltas −0.00246/−0.00697.
   **PROPOSAL (existing)**: adopt 1.5 as the AXI screen default (owner-gated; 3.0 unmeasured).
   Pointer: CONTINUITY 2026 measurement block.
2. **Balloon density** (512/1024/2592 ladder): ΔDI 512→1035 up to ≈0.09 dB; 1035→2592 ≤ 0.0407 dB;
   screen→1024 was proposed and is owner-gated (W7 wants 1,000–6,600 + ~41 verify freqs, gated on
   the ΔDI ladder + 8 GB GPU cost). No flip made.
3. **`band_split`**: gate FAILED (CP-7f: in-band up to 1.2476°/0.1529 dB; band-0 worst) — stay
   opt-in; NOT proposed as any default.
4. **`source_motion`**: axial deltas ≤ 0.0070° AXI / ≤ 0.0036° HV above 5 kHz; default `normal`
   stays. RO measurements reach 0.43°/0.16°/0.04 dB at 12 kHz (recorded, not adopted anywhere).
5. **Weights**: `DEFAULT_WEIGHTS {cov 1, rip 1, di 0.3, dislope 0.5, flat 0.5, load 0}` shipped
   briefs override (`load: 0.5` on axi/organic/enclosure, 0.0 on the hifi brief). Keep; weight
   tuning before the cov/v3 era was contraindicated by §13.5-D.
6. **Mounting (WP12)**: enclosure costs 2.99× dofs (osse_axi) / 2.07× (sculpt) and improves J under
   its own landscape — treat enclosure runs as verify-tier-sized, and NEVER rank across mountings
   (compare warns; G6 landed. `full+enclosure` is refused this pass — C2).
7. **Search tier reality (M5)**: 3000-dof screen spec, 60/60 non-cached evals, VRAM baseline
   430 MiB → peak 2305 MiB — the measured envelope for planning a smoke matrix.

## Existing-config defaults audit (the other 26 entries)

Shipped defaults remain as landed; per §13.6 the per-typology baseline tables derive from the
(K-law + v3) rule **once the owner approves the settings pass** — this doc is that pass's
foundation, with the shipped configs verified sensible where a dossier anchors them (the classical
laws carry their published formulas unchanged; the Magnus mesher-native entries carry the mesher
defaults; the organic/labeled families carry their dossier-derived seeds). Any better default
beyond the numbered PROPOSALS above = a new owner-gated proposal; none is applied here.

## Objective v3 decision capsule (§4e of the handoff — for the owner; NOTHING FLIPPED)

- **What it is** (the "full-repair pass", owner-approved in the S1a gate): `objective.version: 3`
  joins WP4's `freq_weights` into cov, and both cov and dislope score only frequencies
  f ≥ `target.f0_hz` (the below-f0 mask); v1/v2 byte-identical behavior untouched; same key set;
  band-based n_nan; never-raise.
- **Landed state**: opt-in — the validator accepts 3 in the config objective block; nothing in the
  tree sets 3 as any default (shipped configs/defaults remain as they were; the one v3 usage shipped
  is the Phase-D template brief `axi_2in_large.yaml` carrying `objective: {version: 3}` + f0 1000).
- **Why it matters**: the measured 61–87% unattainable-band cov loss (13.5) no longer dominates the
  gradient on f0-carrying briefs; plus the K-law feasibility preflight discloses required-vs-envelope
  mouths + per-mode below-f0 counts before any spend.
- **Test coverage**: objective v3 dispatch + validator acceptance + below-f0 masking (S1a's
  objective/config tests), the derivation tests (test_brief_derivation 9/9), the GUI surfaces
  (select option, f0 KPI, seed-derivation card, generic J-vN badge, compare mixed-key warn — 4b42862).
- **Decision for the owner**: keep v3 opt-in (current; recommendation — non-retroactive, matches
  the record-group discipline), or promote v3+brief-f0 to a default for NEW briefs (a contract-level
  default flip = owner-gated; would land as a dated amendment in NEXT_DEV_PRIORITIES + the
  baseline-settings doc). No default changes until the owner says so.

— Phase-D foundation doc; written 2026-10-25; smoke-matrix linkage updates as GPU jobs land.

## Addendum (2026-10-25, later — the S1a driver pass; Oracle-decided, owner-directed)

The two smoke-matrix PROPOSAL items (salmon_x_signed / salmon_ripple12 reseeds) are now
owner-gated IN and landed: `salmon_x_signed` reseeded (stop 170→150, x_amp −0.25→−0.15 — the
cardinal rows crossed the 180° cap-area asymptote at the shipped seed), `salmon_ripple12`
(stop 170→150; seed dofs 5,358→2,852/2,567), `lecleach_asym_odd` eps 0.25→0.20 (full-ring
self-approach window at r0 ≥ 17.2) and onto its own family brief, `biradial_keele` seed
L 210→195 + rm bounds widened for the 2-inch class. The brief family landed as shipped
variants (`{hifi,organic_rollback,lecleach_rollback}_{1in,14in,2in}` — see
`docs/BRIEF_AND_SCORING_GUIDE_2026-10-25.md` for the physics and the selection table; the
scoring defaults there are the owner's answer to "is the scoring right" — no weights were
changed). The per-config tables above remain the parameter record; where this addendum
differs, the driver-pass values govern.