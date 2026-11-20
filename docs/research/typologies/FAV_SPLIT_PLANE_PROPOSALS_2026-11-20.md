# Geometry improvements and a new typology from the FAV-001 findings (proposal dossier, 2026-11-20)

Owner ask (17:55): *"ways you think you can actually improve the geometry or make an alternate new typology
based on what we found thus far, in the repo and otherwise."* Status: **P1 IMPLEMENTED 2026-11-20 ~18:10 (owner: "Yes, build P1"); P2-P3 proposals.**
Protocol: `hornlab-typology-research` (inventory → sources → checkable properties). Parent research reused, not
redone: `docs/knowledge/claims/KH-002_*`, `KH-003_*`, `THROAT_HV_CONTROL_AUDIT_2026-11-18.md`,
`docs/knowledge/contracts/crowe_v2a_and_crowe_x_osse.md`, and today's
`docs/research/favorites_2026-11-20/{CROWE_X_FAVORITE_RESEARCH,THROAT_LOADING_LEVERS}.md`.

## 0. What the evidence says (all measured today unless labeled)

1. **Directivity at 3–8 kHz is set by the throat's first few cm; loading at 700 Hz by the first ~80 mm.**
   Global OS `k` changes nothing below ~2.3 kHz and beams above ~3 kHz (k 4: 8 kHz H 69→52°).
   A practitioner report on ATH matches (k 1 vs k 10: very different throat impedance at ~800 Hz with
   similar beamwidths) [secondary (practitioner reports), diyAudio ATH4 thread].
2. **The planes are not symmetric in what they need.** FAV-001 is too narrow in H (69 vs 80°) and too wide
   in V (57 vs 50°) at HF. HF narrowing is harmful in H and *helpful* in V. Measured: V-only k
   (k_H 1, k_V 3) keeps 8 kHz H at 70°, leaves off-axis smoothness at 0.574 (FAV 0.543), takes V 57 → 51°,
   and cuts load 2.645 → 1.951 (J 4.996 → 4.657, same identity).
3. **A bigger exit is the cleanest loading lever** (2": load −74 %, HF H 69 → 63°). Stacking 2" with k_V 2
   overshoots (V 43°).
4. **The mouth termination drives off-axis smoothness.** `fav8__k1_cd_polish`'s best non-load
   (`392276e62470`) differs from FAV-001 mainly by lip wrap 81 → 105° and depth 260 → 274 mm. It beats
   FAV-001 on every CD-matrix term.
5. **The extremes fail.** Throat-extension and resonant-throat horns load by resonance (Re z up to 3.2 ρc).
   The bi-radial lane (slot-like throat) scored v11 J 7.71 (`docs/evidence/cd_v11_2026-11-20/COMPLETION.md`).
6. **Classic CD practice** [secondary, AES abstract + history]: Keele (EV, AES preprint 1038, 1975) joined an
   **exponential throat** (loading) to a **conical body** (constant directivity) and a **rapid mouth flare**.
   Bi-radial (US4308932) defines the H and V wall pairs separately [primary-summary, KH-003].

## 1. Source table

| Source | What it gives us | Status |
|---|---|---|
| Batík, OS-SE (2020) Eq. 5 and §5: parameters "may vary around the device" | per-azimuth k, s, a in the OS-SE parent | primary (carried in KH-002/003; PDF text not re-fetched) |
| ATH User Guide 2.1.2: "ex" items may depend on azimuth p; OS.k is ex-capable | precedent for per-plane k and s | primary (carried, KH-003) |
| `hornlab_mesher.profile_formulas` `eval_param(k, p)` | the mesher already evaluates k(p) | [verified, code] |
| Keele, "What's so sacred about exponential horns?", AES 1038 (1975) ([AES](https://aes2.org/publications/elibrary-page/?id=2394), [scan](https://audioroundtable.com/misc/Keele_Horn_Design_AES_1038.pdf)) | exponential throat + conical body + mouth flare = CD horn | secondary here (abstract/history read; scan not text-extractable, KH-003 §0) |
| Keele US4308932 (bi-radial) | separately defined H/V wall pairs, y = a + b x + c xⁿ | primary-summary (KH-003) |
| Geddes US7068805; diyAudio "Geddes on waveguides" | true OS sections are round; a larger throat lowers falloff in a true CD guide | primary (author, patent/forum) |
| diyAudio ATH4 thread ([p. 228](https://diyaudio.com/community/threads/acoustic-horn-design-the-easy-way-ath4.338806/page-228), [post](https://www.diyaudio.com/community/goto/post?id=6079880)) | Batík: k>1 trades CD for loading/smoothness; users: k changes ~800 Hz impedance, not beamwidth | primary (author, forum) + secondary (practitioner reports) |
| Today's solves (`runs/20261120T2021*`, `…2220*`, `…2251*`…, `fav8_2026-11-20` summary) | every number in §0 | [measured] |

## 2. Proposals, ranked

### P1. Split-plane OS-SE (improve FAV-001 inside its own family): **recommended first**

Construction: FAV-001's OS-SE rows, with the **throat law and the mouth flare set per plane**:
- k(φ) = k_H cos²φ + k_V sin²φ with **k_H ≡ 1** (H keeps the exact OS throat, so the HF H pattern is
  untouched), k_V ∈ [1, 4]. Today this is reachable only through `g_throat_hv_ratio`, whose
  ρ^(−cos 2φ/2) law ties k_H to k_V. An explicit `g_k_v` with the same cos²/sin² law as a(φ) states the
  intent directly and keeps k_H exactly 1 at every ρ.
- s(φ) = s_H cos²φ + s_V sin²φ: **new knob `g_s_v`**, so the V mouth size can be restored after k_V shrinks
  it (k_V 3 took the V mouth 450 → 407 mm), without raising a_v and widening V again.

Why it should work: §0.1–0.2. Loading comes from the V plane's slow throat. V's HF narrowing serves the 50°
target. H, the plane that carries the 80° requirement, stays pure OS. It stays inside the OS-SE parent
(Batík §5 per-azimuth parameters), so it needs no new published name.

Code: additive knobs on `rows.type: osse_rollback` in `hornlab_search/design/generators/grid.py` (defaults
absent → byte-identical rows and design hashes), listed in the knob defaults per the shape-check rule.
Tests: the grid/rows/param-catalog suites.

Checkable properties (before any solve):
- `g_k_v` / `g_s_v` absent → rows byte-identical to today.
- k_V = k_H and s_V = s → identical to the single-k/single-s law.
- The φ = 0 row is identical to the parent at any k_V/s_V (H untouched).
- The V row matches `profile_points` with (k_V, s_V) within 0.2 mm.
- Throat C0/C1 at the round coupling (all rows start at r0 with slope tan a0).

### P2. New typology: "Keele-in-V" OS hybrid (exponential V throat → OS V body; H pure OS)

Construction: in the V plane only, the first `L_e` mm follow an **exponential (or Salmon hypex) area-matched
law** with a flare cutoff `f_e`. It blends C1 into the OS-SE V wall, which approaches the a_v asymptote
(Keele's conical body). H rows stay OS from the exit. Intermediate azimuths use the cos²/sin² blend.
Knobs: `f_e` (Hz, the loading corner stated directly), `L_e` (mm), `T` (hypex shape, optional).

Why beyond P1: k_V is a hyperbola whose slow start is set by geometry. An exponential section states the
loading corner in **Hz** and can load harder per mm, which is the point of Keele's throat. Risk:
a long exponential V neck becomes a slot, the bi-radial direction that scored poorly (§0.5). Bound `L_e` to
≲ 60 mm and `f_e` ≥ ~400 Hz.

Status: our construction (LABELED HYPOTHESIS-SHAPE EXPERIMENT), **no published name**. Keele is cited as the
principle (exponential throat + conical body), not as the geometry.
Gate: build only if P1 leaves a large loading gap. Needs a numeric reference case: an exponential section from
r0 = 18 mm with f_e = 500 Hz, so m = 4π f_e / c = 18.3 m⁻¹ and area ×2.5 over 50 mm, blended at L_e into an
OS wall with a = 27°, checked ≤ 0.2 mm against the formula.

### P3. Mouth-termination upgrade (FAV-001 family, no new law)
Measured: longer lip wrap improves off-axis smoothness. Next steps are a continuous rollback (R-OSSE-style
foldback) or an azimuth-varying wrap (wrap larger in H, where off-axis smoothness is scored at ±30/40°). That
needs an R-OSSE equation re-check (KH-003 §0: R-OSSE PDF text not retrieved). `fav8__lip_study` covers the
existing knobs tonight.

### P4. Driver-size system choice (not geometry)
2" exit + split-plane P1 with **mild** k_V (≈1.2–1.6). The 2" + k_V 2 single overshot. It is queued as a
lane tonight (no code).

### Rejected
- Area-programmed throat with V derived from a prescribed A(z): its limit is the bi-radial slot (§0.5).
- Designed resonant throats: they score well only because v11's load term is one-sided.
- Global k > 1 or throat extensions: HF beaming (§0.1).

## 3. Queued tonight without code (combination lanes)
Seeded at `392276e62470` (the k = 1 polish winner), both using the existing `g_throat_hv_ratio`
(k = √ρ, so k_H = 1 and k_V = ρ):
- `favM__polish_kv` (1.4" home 700): ρ ∈ [1, 4].
- `favM__polish_2in_kv` (2" home 700): ρ ∈ [1, 2].

## 4. Decision for the owner
Build P1 (two knobs, tests, then a split-plane search on FAV-001 and on `392276e62470`)? P2 waits for P1's
result.

## 5. P1 implementation record (2026-11-20 ~18:10)

- Code: `hornlab_search/design/generators/grid.py`. `ROWS_OSSE_ROLL_SPLIT_KNOBS = ("k_v", "s_v")` sits outside the
  defaults dict (absent → byte-identical knob dict, meta and hashes). In the march, k(φ) = k c² + k_v s² and
  s(φ) = s c² + s_v s² use the a(φ) weights. `k_v` with `throat_hv_ratio` ≠ 1 is refused (two k laws). meta gains
  `split_plane` + `split_plane_law` only when present.
- Tests: `tests/test_design_generators_grid_osse_split.py` (the §2 P1 properties: absent → no meta change; equal
  values → parent within 1e-9 mm; H row unchanged; V row = parent law at (k_v, s_v) within 1e-9 mm; every row
  starts at r0; illegal values and the two-law combination refused). Grid + mesh + param-catalog suites:
  **198 tests, 0 failures, 0 errors** (junit, CPU only, during the live night).
- Lanes: `examples/typologies/favP1_2026-11-20/` (writer `docs/research/favorites_2026-11-20/cpu/write_favP1.py`).
  `s_v` is solved so the V mouth returns to the seed's height: FAV-001 + k_v 3 → s_v 0.5512 (450 mm); polish
  winner + k_v 2.5 → 0.44 (447 mm); 2" + k_v 1.4 → 0.4115 (461 mm). shape_check 4/4 fit; preflight no HARD (valid 30–40 %).
- Queue: next in the live `fav8_2026-11-20` after `favL__2in_home`. The coupled-law lanes `favL__kv_home`,
  `favM__polish_kv` and `favM__polish_2in_kv` were removed before starting (superseded: P1 keeps k_H exactly 1).
