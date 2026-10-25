# GUI contrast & form-visibility plan (proposed, 2026-10-24)

Proposed — awaiting owner approval (Oracle-reviewed 2026-10-24: all MUST/SHOULD/NICE items applied) · origin: contrast/visibility audit of rendered dark-theme screenshots.

## Goal

Make the GUI text clearly readable in both themes (all text ≥ 4.5:1, structural hairlines ~2–3:1, micro-label tier legible) and make the horn **form** readable in the 2D vector cross-section and the 3D view (better shading, light-grey horn material), without changing layout, navigation, or information architecture. Refines `docs/GUI_PLAN.md`'s finished GUI on color / line / type only.

## Constraints (binding)

- No build step, no npm, zero new runtime deps; edits confined to `hornlab_search/gui/static/**` (+1 line set in `tests/test_gui.py`).
- Three.js stays r160 pinned via the CDN import map (`static/index.html:13-20`); the 2D SVG fallback on import failure stays functional (`static/view3d.js:61-122`, entered at `view3d.js:132-133`; Phase 5 adds the seed outline — the CDN-blocked capture is the gate).
- Both themes must work: light + dark via `data-theme` + `localStorage "hl-theme"` + `prefers-color-scheme` fallback (`static/app.css:25-34`).
- Commits: `feat(gui): …` / `fix(gui): …`, one phase per commit, `docs/CONTINUITY.md` + `docs/ISSUES.md` updated in the same commit, `task/<NN>-<slug>` branches.
- This doc itself lands as `docs(gui): propose GUI contrast & form-visibility plan` committed directly to main (owner instruction; no GitHub issue), with docs/INDEX.md, docs/CODE_MAP.md (gui row), docs/CONTINUITY.md, docs/ISSUES.md updated in the same commit per the push rule.
- Packaging: `pyproject.toml:33-34` ships static with a **flat** glob `static/*` — this plan adds no subdirectories; if any later change adds one, the glob must become `static/**` in the same commit.
- Never touch: `hornlab_search/gui/server.py` security surface (Host-header check, 127.0.0.1 bind), `hornlab_search/gui/jobs.py` launch allow-list, `hornlab_search/gui/data.py` readers, any physics/mesher/solver code, `docs/plan/**` (frozen), and AGENTS.md hard rules 1–8 apply throughout.

## Baseline (measured 2026-10-24, file-verified)

| Check | Light | Dark | Verdict |
|---|---|---|---|
| Body `--ink` on surface | 16.5:1 | 14.0:1 | ok |
| `--muted` on surface | 5.7:1 | 6.6:1 | ok (prose only) |
| `--rule` hairline on surface | 1.36:1 | 1.38:1 | invisible (tables, cards, KPI gaps) |
| `--band` alpha | 0.08 | 0.09 | target band ≈ plot bg |
| `button.primary` text on `--accent` (`app.css:160`) | 5.95:1 | **2.07:1 (WCAG fail)** | fix |
| Micro-label tier (`svg text` 10px `--muted` `app.css:193`; `th` `app.css:139`; `.kpi span` `app.css:173`; `.legend` `app.css:187`) | ~5.7:1 @ 10–11px | ~6.6:1 @ 10–11px | structure dimmer than prose |
| Wall cross-section (`charts.js:229-275`, call `app.js:1089-1092`) | — | — | no `fill-rule` (nonzero) + fill 0.35 paints over the dashed start profile passed earlier in the array; H+V outlines + wall band merge into one ribbon |
| 3D (`view3d.js:156-172`) | — | — | Phong `--accent`, opacity 0.85, ambient 0.5 + 2 dirs; unlit flank merges into `--surface` canvas; `seedCol` computed at `view3d.js:111`, never used |
| Isobar contours (`charts.js:354-355`) | — | — | single white stroke, opacity 0.55/0.95 — white on `#FFDF00` is 1.3:1 |
| Hardcoded rgba orphans | `.alert.warn` `app.css:246`, `.gpu-busy-note` `app.css:377-378` = `rgba(168,102,27,.10)` in both themes | | |

Surfaces used in all ratio math: light surface `#ffffff`, light bg `#f4f6f7`, dark surface `#151d23`, dark bg `#0e1418`.

---

## Phase 1 — Token & annotation-type overhaul (app.css only)

**Changes** — `:root` block (`app.css:5-24`) and **both** dark blocks (`25-29`, `30-34`) kept in sync:

| Token | Light | Dark | Ratio (surface) | Note |
|---|---|---|---|---|
| `--label` (new) | `#46535e` | `#b3bfc6` | **7.9 / 9.1** | structural tier: ticks, legends, th, IDs |
| `--rule` | `#d7dee3` → `#a9b4bb` | `#2a363e` → `#40505b` | **2.1 / 2.0** (bg: 1.95 / 2.2) | quiet but visible hairlines |
| `--on-accent` (new) | `#ffffff` | `#0e1418` | 5.95 / **9.0** | fixes the 2.07 dark button |
| `--accent-strong` (new) | `#0a5c66` | `#7fd6de` | hover text 7.70 / 11.1 | replaces hover `opacity:.88` |
| `--band` | `rgba(13,110,122,0.08)` → **`0.32`** | `rgba(92,195,207,0.09)` → **`0.30`** | composite ≈ `#b2d1d4` / `#2a4f57` — 1.6 / 1.9 vs plot bg | band reads as a band |
| `--warn-soft` (new) | `rgba(138,84,20,0.12)` | `rgba(224,160,80,0.14)` | — | replaces `rgba(168,102,27,.10)` orphans |
| `--bad-soft` (new) | `rgba(178,58,58,0.10)` | `rgba(236,123,123,0.13)` | — | for `.alert.error`, danger hover |

Accent / seed / good / warn / bad hues unchanged (identity preserved). Type tier: `svg text` (`app.css:193`) → `fill:var(--label); font-size:11px` — lifts every chart tick/legend at once; `svg .axis` (`195`) → `--label`; `--label` on `th` (139), `.kpi span` (173), `.legend` (187), `.status-card .label` (259), `.camp-prof h4` (210), `.map .lbl` (202), `.run-tab small` (308), `.bbr-meta` (300), `.tl-time` (287), `.camp-dims` (446), `.nav-brand small` (57); `--muted` stays for `.lede`, `.cap`, `.hint`, `.g-long`. `button.primary` (160) `color:var(--on-accent)`; hover (161) → `background:var(--accent-strong)`. Size floor 0.66rem (`.kpi span` 0.66→0.68).

**Acceptance criteria**
- Re-measured ratios meet the WCAG acceptance table below (esp. labels ≥ 7.3/8.3; rule 2.0–2.2 both themes; button 5.95/9.0).
- Screenshots both themes: table separators visible yet quiet; KPI strip, table head, chart ticks legible at arm's length.
- No layout/IA change: same nav, same page order, same fonts (Bricolage/Spline stack untouched, `index.html:7-9`).
- `pytest tests/test_gui.py -q` green.

**Implementation notes** — files: `static/app.css` only (token lines 5-34 + the named selectors). Do not touch: any JS, `index.html`, server/data/jobs.
**Rollback** — single-commit revert of app.css; if a token reads wrong (e.g. hairline too heavy), tune the hex in a follow-up rather than reverting wholesale.

**Effort ~0.5d · risk very low.**

## Phase 2 — Theme boot correctness + `?theme=` capture override

**Changes**
1. First-click no-op (`index.html:71-77`): when no `data-theme` is set (OS dark, no stored pref), `cur` is null → `next="dark"` → no visible change. Resolve `eff = cur || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")` and toggle from `eff`.
2. No change needed — the toggle (index.html:74-75) already writes both the attribute and localStorage unconditionally; a preference is pinned from the first click today. R6 records this pre-existing trade-off; this plan does not introduce it.
3. Wrap both `localStorage` reads/writes (`index.html:63,75`) in try/catch (private-mode / disabled storage must not blank the toggle).
4. `?theme=light|dark` URL override (boot script, before stored-pref read): parse `location.search`, set attribute + localStorage. Works with hash routes (`/?theme=light#/run/x`). JS-only, no server change.
5. Stale-SVG-after-toggle (`app.js:1994-1997`): both observers (MutationObserver on `data-theme`, `matchMedia` change) call `route()` **unconditionally** instead of the `#/run|#/campaign|#/compare` prefix check, so typologies/campaign/profile SVGs recolor immediately. To avoid state loss on re-render: before calling, snapshot `window.scrollY` and the values of `.filter-bar input, .form-grid input, .form-grid select, textarea`; restore after. Restore must happen after the async view render settles: make `route()` return the matched view's promise (`return fn(m)` at app.js:81), `await` it in both observers, then restore `scrollY` and the snapshotted input values (one `requestAnimationFrame` retry if the view renders in stages). Restoring immediately after route() returns hits an empty #view-root. Skip the matchMedia handler when documentElement carries an explicit data-theme (pinned) — re-render there is pure waste.

**Acceptance criteria**
- With no stored preference and OS dark: first click visibly switches to light; every further click toggles.
- `?theme=light` capture renders a light page (pixel-sample a surface area ≈ `#ffffff`) — this is the unlock for all light-theme verification.
- After a toggle on typologies/campaign detail, thumbnails/profiles recolor without navigation; scroll returns to the same position; filter inputs survive.
- `pytest tests/test_gui.py -q` green (index.html inline script has no node --check gate — verified by the captures).
- Click-path checks are manual (local browser, OS theme dark): first-click switch, per-view recolor, scroll/filter restore — the capture recipe cannot click; only the ?theme= capture is scripted.

**Implementation notes** — files: `static/index.html:60-79`, `static/app.js:1989-1997`. Do not touch: server routing, import map, fonts links.
**Rollback** — revert the commit.

**Effort ~0.25d · risk low.**

## Phase 3 — Chart-graphics contrast pass (charts.js + 4 call-site tweaks)

**Changes**
1. Isobar contours (`charts.js:338-356`): two-pass halo per level — underlay `#10181d`, `stroke-opacity:0.55`, width **3.4** (−6 dB) / **2.6**; overlay `#ffffff` opacity **0.98** / **0.8**, width **1.8** / **1.1**. Rationale, measured: white on `#FFDF00` = 1.3:1; the 0.55-opaque halo over #FFDF00 composites ≈ 3.7:1 and the white core on it ≈ 5:1, which carries legibility. Matches polarMap's existing white-over-dark style (`charts.js:210-216`).
2. Keep a theme-independent mid grey for the isobar gridlines (the raster is the same in both themes — light `#46535e` over the navy `#00008F` raster bottoms out ≈1.15:1, worse than today's #808080@0.6 ≈ 1.9:1): #808080 at stroke-opacity:0.7 (0° line 0.9), width 0.8→1.0 — or use --label only where it passes over light bands. Tick text upgrades automatically via Phase 1's `svg text` rule.
3. `chart()` (`charts.js:40-83`): default dot `r 1.6→2.0`, `opacity 0.45→0.8` (line 76); `hlines` width 1.2→**1.5** (line 69); app.js call sites passing `css("--muted")` for target/reference lines (e.g. `app.js:1029`) → `css("--label")`; both seed strokes → **1.7** (`app.js:1017-1018` table series at 1.4; `1080` solid 1.4, `1081` dashed 1.2). `--band` rectangle (line 54) thickens via the Phase 1 token.
4. "Also show the starting design" checkbox (`app.js:952`, inside an `.evo-opt` label): label text → `color:var(--ink)` (it's an interactive control, not an annotation); keep native accent.

**Acceptance criteria**
- Screenshot check: −3/−6/−10 dB contours legible over `#FFDF00` band and `#FF0000`-adjacent bands in both themes; −6 dB visibly heavier.
- Convergence eval dots and dashed target hlines visible at 100% zoom without guessing.
- `pytest tests/test_gui.py -q` + node --check green (`charts.js` is in the `test_gui.py:319` set).

**Implementation notes** — files: `static/charts.js` (contour block 337-356, grid block 358-368, `chart()` defaults), `static/app.js` (named call sites only). Do not touch: marching-squares core (`charts.js:301-303,337-353` geometry), `cmap`/`ISOBAR_COLORS` ramp (identity), `polarMap` (already correct), hover crosshair (`382-404`).
**Rollback** — revert commit; contour styling is additive (halo pass + overlay), trivially removable.

**Effort ~0.5d · risk low.**

## Phase 4 — `wallSection` redesign + compact thumbnails

**Spec (full size, H=320, call `app.js:1089-1092`)**
- Margins: `m` l 40→**46**, b 30→**34**; true-aspect pad `1.04→1.02` (`charts.js:240`). **Do not distort aspect** — leftover width on deep horns stays, but the plane labels get it: "(← V) r mm" / "r mm (H →)" / "z mm" (`charts.js:255-257`) → "← vertical plane" / "horizontal plane →" / "depth z (mm)", moved to mid-height beside the drawing.
- **Z-order (the core fix):** three passes — (1) grid/axis, (2) **all fills**, (3) **all strokes**, dashed start last. The start profile is currently passed *before* best so the 0.35 fill paints over it (`app.js:1090-1091`); pass ordering no longer matters after re-work, but call order stays (seed, best) for clarity.
- **Fill** ("best (filled)" made true, `charts.js:265-269`): add `fill-rule:"evenodd"`, `fill-opacity:0.30` in both themes. The outline (`hornlab_search/gui/data.py:266-280`, kind `"section"`: throat cap → acoustic wall → mouth lip → outer shell → rear in one closed loop) then fills the **wall band**, bore stays background. Expected pixel composites: dark ≈ `rgb(42,79,87)` over `#151d23`; light ≈ `rgb(182,212,215)` over `#ffffff`. Verify by sampling; if the filled interior includes the bore (band pixel ≡ bore pixel — i.e. `max(chains, key=len)` at data.py:278 picked an outer silhouette without the acoustic-wall segment), fall back to `fill-opacity:0.22` full fill and record the data shape in ISSUES.md.
- **Strokes:** best H solid **2.25px**, best V dashed **2.0px (6-4)** — preserves the global "H solid / V dashed" convention (`app.js:1015`); start dashed **2.0px (6-4)** `--seed`. One hue per design; outer-vs-inner legibility comes from the even-odd wall band vs empty bore, not competing stroke colors.
- **Throat landmark:** filled circle r **2.5** (full) at the outline's min-z point with |r| > 0 (the throat aperture; the outline's cap spans r=0 along the axis — min-|r| would land there); if no such point, at min z — in the design color (compact: r **1.5**); `.fig .cap` line: "True aspect. Band = horn wall, interior = sound bore; dashed amber = starting design; dot = throat."
- **Centerline** (`charts.js:259`): width 1, `--label`, 3-3 dash, opacity `0.6`.
- Grid/ticks inherit Phase 1 (`--rule` ~2:1 lines, `--label` 11px text).

**Compact mode (campaign `app.js:693-694` H=130; typologies `app.js:2053` H=120 @150px):** min stroke **1.6px**; **no dashed strokes below 260px width** — both planes solid at thumbnail scale (4-3 dash at 150px reads as texture); even-odd fill 0.32; skip centerline below 200px width; shared `extent` (`app.js:678-681`) unchanged so sizes stay comparable.

**Acceptance criteria**
- Bore-interior pixel ≈ theme surface in both themes (sampled ±10/channel vs the composites above); wall band clearly distinct from bore.
- In a zoomed capture of the run-detail cross-section (both themes), the dashed start outline remains distinguishable from the best fill along the entire band perimeter — no stretch where it disappears.
- Every campaign thumbnail and typology card: wall band + throat dot legible at 150px; no dash mush.
- Legend "best (filled)" (`app.js:961-962`) is now literally accurate; `pytest` + node --check green.

**Implementation notes** — files: `static/charts.js:229-275` (self-contained helper), `static/app.js:677-695,952-966,1088-1092,2053` (call args + cap text only). Do not touch: `data.py` `_profile_from_mesh` / `mouth_outline` (readers, frozen-by-ownership), `cmap`/`FAMILY_COLORS`.
**Rollback** — revert commit; the old one-pass renderer returns untouched. If only the fill misbehaves, dropping the `fill-rule` attribute alone restores old appearance while keeping margins/labels/strokes.

**Effort ~1d · risk medium.**

## Phase 5 — 3D form, material, lighting, optional shadows

**Material** (replace `view3d.js:156-159`): `MeshStandardMaterial` — not `MeshPhysicalMaterial` (clearcoat/sheen/transmission uniforms are pure cost here, and Standard still reads form well without an env map): `color:0xdfe4e8` (light-neutral grey honoring the owner's white/light-gray preference), **roughness 0.55, metalness 0.05, side:DoubleSide, transparent:false**. Drop `opacity:0.85` (per-frame sorting cost + ghosting). DoubleSide stays: the open mouth must show the interior (view3d.js:46-50 already keeps mirrored windings consistent — DoubleSide is for interior visibility, not winding repair). Cost estimate: Standard ≈ Phong + a few G-buffer slots on a ≤60k-tri mesh — negligible on GPU.
- **Delete the black wireframe overlay** (`view3d.js:164-165`, incl. `wmat.dispose()` in cleanup at `221`); silhouette separation moves to the rim light.

**Lighting rig** (replace `168-172`; r160 default light intensity model; all positions `center + dir × maxDim`):

| Light | Type / color | Intensity | Direction | Job |
|---|---|---|---|---|
| Hemisphere | `HemisphereLight(0xffffff, 0x8fa3ad)` | **0.45** | — | shadow side never dies |
| Key | `DirectionalLight(0xffffff)` | **1.15** | (1.6, 2.2, 1.8) | main form modeling |
| Fill | `DirectionalLight(0xffffff)` | **0.35** | (−1.8, 0.6, 1.2) | lifts the dark flank |
| Rim | `DirectionalLight(0xffffff)` | **0.85** | (−1.2, −1.0, −2.2) | traces the far silhouette |

**Canvas bg per theme** (`view3d.js:139-141`): read new token `--viz-canvas` (app.css, added in this phase's commit): light **`#e9edf0`**, dark **`#1d272e`**, fallback `--surface`. Rationale: a ~0.77-luminance grey body against pure white reaches only ~1.2:1; shading + the darker canvas keep silhouette ≥ ~3:1 on the darkest flank. Verify in light captures (only possible after Phase 2).

**Shadow mapping — optional, toggle-checked** (`v3d-shadows` checkbox in the fig header, default on, persisted): `renderer.shadowMap.enabled = true; type = PCFSoftShadowMap`; key casts, `shadow.mapSize(1024,1024)`, ortho frustum ±0.8×maxDim, near 0.1, far 4×maxDim; mesh `castShadow = receiveShadow = true`; `key.shadow.normalBias = 0.01 × maxDim` (geometry is in metres after the ×0.001 scale; without a normalBias the thin double-sided wall acnes under PCFSoft at default bias 0), `key.shadow.bias = 0`; ground `PlaneGeometry(2.6×maxDim)² + ShadowMaterial({opacity:0.22})` at `y = box.min.y − 0.02×maxDim`, `rotation.x = −π/2`. Cost: one extra 60k-tri depth pass — trivial on GPU, perceptible under SwiftShader → the toggle is the guard.
**Orientation cue — optional:** three `ArrowHelper`s (x `0xc97b7b`, y `0xc9b46b`, z `0x6fb3c9`, length 0.22×maxDim, head 0.06×maxDim) at the bbox corner + `.cap` "width x · height y · horn axis z (throat → mouth)" — confirm throat/mouth direction in captures before freezing the caption.
**Orphaned `seedCol`** (`view3d.js:110-111`): used at last — extend `init3d(container, meshData, profile, seedProfile?)`; `init3d` is called at `app.js:1244-1246` (`await init3d(wrap, meshD, profile)` in `viewRun3D`) — pass `S.profile` there; the 2D **fallback** draws seed dashed `--seed` under best solid `--best` at 2.5/2px (no fill in fallback, so z-order trivial). Backward-compatible signature; fallback path untouched otherwise.

**Acceptance criteria**
- Dark capture: full silhouette visible; darkest flank vs canvas ≥ 2.8:1 (pixel-sampled along the outline); lit/shadow sides clearly distinct.
- Light capture (after Phase 2): silhouette edge legible against `#e9edf0`; if the body renders > 0.86 relative luminance anywhere, first lever = darken hemisphere ground color, second = canvas toward `#e3e8eb`.
- Shadows toggle on/off visibly; capture completes within the screenshot budget with shadows on.
- Force the CDN-failure path (block `cdn.jsdelivr.net`): the SVG fallback renders seed + best; hard-constraint test passes.
- `pytest` + node --check green (`view3d.js` is in the `test_gui.py:319` set).

**Implementation notes** — files: `static/view3d.js` (init3d body, fallback draw block), `static/app.css` (+2 `--viz-canvas` lines), static/app.js (init3d call arg at 1246; v3d-shadows checkbox + persisted toggle in the viewRun3D fig header, wrapped in the same localStorage try/catch as Phase 2). Do not touch: `loadThree` (8-20), `mirrorMesh` (29-55), mm→m scale (`150`), camera-fit logic (174-186), ResizeObserver/RAF/cleanup (198-222), the import map.
**Rollback** — revert commit; if shadows alone regress software-GL machines, ship the phase without them (they live behind the toggle already).

**Effort ~1d · risk medium-low.**

## Phase 6 — Semantics, state flags, test coverage

**Changes**
1. Budget over-limit (`app.js:1007`; same pattern duplicated at `197-208` and `430-438`): compute `over = sum.budget && sum.n > sum.budget`; render the value `class="… bad/warn"` and append literal text "over budget" (redundant to color); add `.progress-bar.bad { background:var(--bad); }` beside `app.css:273`.
2. Color-only status redundancy: campaign rank is currently a 3px left border only (`app.css:144-145`, set `app.js:597-598`) — add a trailing text badge in the same cell ("leader"/"within noise"). Timeline dots (`app.css:281-284`) get shape redundancy: `.tl-dot.skip` → transparent bg + 2px `--muted` outline, `.tl-dot.failed` → square (`border-radius:2px`). Percent-better pills already carry words — no change.
3. rgba consistency: `.alert.warn` (`246`), `.gpu-busy-note` (`377-378`), `.alert.error` (245), `button.danger:hover` (163) → `--warn-soft` / `--bad-soft`.
4. Test widening: add `"evolution.js"` to the `tests/test_gui.py:319` parametrize list (widening coverage; stated in the commit message so the gate change is auditable).

**Acceptance criteria**
- Fixture run with `n > budget`: KPI shows amber/warn style + "over budget" text; progress bar red; job strips consistent.
- Campaign leaderboard distinguishes leader/within-noise without color (grayscale-screenshot check).
- Toggle dots distinguishable in grayscale; run/cancelled/failed differ by shape + color.
- `pytest tests/test_gui.py -q` green with **five** files in the syntax gate.

**Implementation notes** — files: `static/app.js` (named lines), `static/app.css` (progress bar, dots), `tests/test_gui.py:319`. Do not touch: `jobs.py` job registry/allow-list, `server.py`.
**Rollback** — revert commit; the widened test list is the only part to keep if cherry-picking.

**Effort ~0.5d · risk low.**

---

## Risk register

| # | Risk | L×I | Mitigation | Detection |
|---|---|---|---|---|
| R1 | Chain picked by `max(chains, key=len)` is an outer silhouette without the acoustic-wall segment → filled region includes the bore | M×M | Decision rule in Phase 4: verified by pixel sampling; fallback full fill 0.22 + ISSUES.md record | Phase 4 capture (bore pixel ≠ band pixel) |
| R2 | 60k-tri mesh + shadow depth pass stalls under SwiftShader / weak iGPU | M×M | Shadows behind `v3d-shadows` toggle (persisted); Standard≈Phong cost otherwise | Capture with shadows on completes within budget; manual check on target machine |
| R3 | Light-theme 3D palette unverified until Phase 2 lands (no light captures existed) | H×M | Phase 2 ordered before Phase 5; `--viz-canvas` light `#e9edf0` not white; lever list (hemi ground, canvas shade); with hemi 0.45 / fill 0.35 / rim 0.85 a key-facing-away vertical flank computes to roughly ~0.45 luminance vs canvas #e9edf0 ≈ 1.8:1 — below the 2.8:1 gate; the lever list will likely be exercised on the first light capture | Phase 5 light capture + 2.8:1 flank check |
| R4 | CDN-failure 2D fallback breaks after view3d surgery | L×H | Fallback code path edited minimally (colors/arg only); explicit capture test with CDN blocked | Phase 5 verification step |
| R5 | Google Fonts offline → Segoe fallback shifts type metrics, screenshots misleading | L×L | Accept: fonts already fall back today; capture with network on; note in verification recipe | Screenshot metadata + glyph widths |
| R6 | First theme click pins a preference (pre-existing: index.html:74-75 writes attribute + localStorage unconditionally on every click) → OS-following users lose auto-switch after that click | H×L | pre-existing since the GUI shipped; documented in ISSUES.md; not introduced by this plan. | Phase 2 acceptance text |
| R7 | Unconditional `route()` on theme change wipes filters/scroll | M×M | Snapshot + restore scroll and filter/form values in the same change | Phase 2 acceptance step |
| R8 | `pyproject.toml` flat `static/*` glob misses future subdirectories | L×M | Plan adds no subdirs; rule stated in Constraints so any future subdir flips glob to `static/**` in the same commit | Packaging smoke check |
| R9 | Hairline/kpis changes make separators too prominent | M×L | Single-hex tokens; tune `--rule` in follow-up (values isolated by design) | Phase 1 screenshots |
| R10 | r160 light-intensity model differs from assumptions (legacy-lights default) | M×L | Rig verified visually per capture, not by spec; numbers are levers, not laws | Phase 5 captures both themes |

## Edge cases

- **Missing mesh / 0 triangles / no profile:** `wallSection` already no-ops on empty (`charts.js:238`); Phase 5 adds a guard in `init3d`: empty `verts`/`tris` or `maxDim=0` → show the existing fallback message instead of a degenerate camera (`maxDim || 1` for the rig).
- **`quadrants` ≠ 1 (full mesh):** `mirrorMesh` passes through (`view3d.js:30`) — material/lighting/shadow/orientation all derive from the bbox, so they hold.
- **Very small viewport:** ≤700px nav becomes a top bar (unchanged); `measuredWidth` keeps charts 1:1; compact rules (Phase 4) cover the 120–150px thumbnails; 3D wrap stays `min-height:400px` with ResizeObserver.
- **Runs without a seed/start profile:** `app.js:1090` already guards `S.profile ?`; `wallSection` renders single-design; the 3D fallback's seedProfile arg is optional and skipped.
- **Isolated servers (`--runs-dir` / other root):** plan reads zero new parameters from the server; all colors are CSS tokens at render time — behavior identical on any root.
- **OS light vs dark defaults:** `?theme=` sets the attribute and writes localStorage exactly like a click (it persists on that machine — intended for the capture box; a real user is only affected if they follow a themed link).
- **localStorage missing/disabled:** try/catch in the boot script (Phase 2); GUI degrades to attribute-based theme for the session.

## Implementation order

| # | Phase | Effort | Risk | Why this order |
|---|---|---|---|---|
| 1 | Tokens + type tier | 0.5d | very low | foundation: every later phase inherits the new token set |
| 2 | Theme boot + `?theme=` | 0.25d | low | **first-class need**: makes all light-theme verification deterministic before the visual phases |
| 6 | Semantics + flags + tests | 0.5d | low | cheap, independent; lands the evolution.js gate widening early |
| 3 | Chart contrast pass | 0.5d | low | mechanical; sets the stage for the wallSection judgment |
| 4 | wallSection redesign | 1d | medium | hardest 2D logic; needs 1–3 landed to judge fairly |
| 5 | 3D material/lighting | 1d | medium-low | biggest visible payoff; independent of 4 |

Total ≈ 3.75 agent-days. Phases 3 and 4 could merge if velocity allows; 2→5 ordering is fixed by R3.

## Verification recipe (every phase)

- Server: `.venv\Scripts\python.exe -m hornlab_search.gui` → `http://127.0.0.1:8765`.
- Capture (both themes once Phase 2 is in): `msedge --headless=new --use-angle=swiftshader --enable-unsafe-swiftshader --window-size=1360,2400 --virtual-time-budget=8000 --screenshot=<out.png> "http://127.0.0.1:8765/?theme=light#/run/<id>"`. Shots: home, runs, run detail (full-height incl. cross-section), run 3D, campaign detail, typologies.
- Gates: `pytest tests/test_gui.py -q` (offline; never weakened), node --check via the syntax parametrization (five files from Phase 6 on). Phase 5 adds the CDN-blocked fallback capture.
- Pixel sampling: .venv\Scripts\python.exe with matplotlib.image.imread (or PowerShell System.Drawing GetPixel) on the saved PNG.
- CDN-blocked fallback capture (Phase 5): same command plus `--host-resolver-rules="MAP cdn.jsdelivr.net 127.0.0.1"`.
- Fonts note: captures assume network access to Google Fonts (R5); font-fallback drift is acceptable for judgment calls, not for pixel-precision acceptance.

## WCAG acceptance table (per phase 1, re-checked at 6)

| Pair (light / dark) | Old | New target |
|---|---|---|
| Body `--ink` on surface | 16.5 / 14.0 | unchanged |
| `--muted` on surface (prose tier) | 5.7 / 6.6 | ≥ 4.5 (met) |
| `--label` on surface | n/a (was muted 5.7 / 6.6) | **≥ 7.3 / ≥ 8.3** |
| `--rule` on surface | 1.36 / 1.38 | **2.0–2.2** |
| `--rule` on bg | — | ≥ 1.9 |
| Button text on `--accent` | 5.95 / **2.07 ✗** | **≥ 4.5 / ≥ 8.9** |
| Button text on `--accent-strong` (hover) | n/a | ≥ 7.70 / ≥ 11.1 |
| `--warn` text on surface | ≈ 6.2 / ≈ 7.5 | unchanged, ≥ 4.5 both |
| Chart strokes on plot bg (1.4.11) | some < 3 | ≥ 3.0 both (seed 4.2 light) |
| `--band` vs plot bg | ≈ invisible | **1.6 / 1.9 (light / dark)** |
| Isobar overlay on `#FFDF00` | 1.3:1 | ≥ 4.5 (white core on the 0.55-opaque halo composite ≈ 5:1) |
| 3D flank vs canvas (pixel) | merges | **≥ 2.8:1** |

## Out of scope

Layout, navigation, IA, fonts, server/data/jobs code, physics, auth, `docs/plan/**`; radical restyling; adding JS chart libraries or npm; any change to the Three.js pin or the SVG fallback contract.

## Status (2026-10-24)

Proposed — awaiting owner approval (Oracle-reviewed 2026-10-24: all MUST/SHOULD/NICE items applied). Not started: no token, chart, view3d, or test changes from this plan exist yet.