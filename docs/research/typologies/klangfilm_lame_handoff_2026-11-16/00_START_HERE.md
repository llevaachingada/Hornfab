# START HERE: HornFab Lamé, rollback, and HF1440 throat coupling (v3)

**Prepared:** 2026-11-16. **Status:** senior research and local-agent implementation specification, not code merged into HornFab and not verified by a real HF1440 measurement or GPU BEM run.

## Mandatory reading order for local OpenCode / Claude agent

1. **`03_THROAT_COUPLING_SENIOR_ADDENDUM.md` FIRST.** This corrects the prior handoff's unsupported physical claim about an HF1440 2° exit angle. Official FaitalPRO data identifies a 35.8 mm **Combined Exit** with radial phase plug, but supplies **no numeric outlet-angle specification**. In the existing HornFab home brief, `exit_angle_deg: 2.0` is a simulation assumption, not a verified driver measurement. The Klangfilm baseline `10.617223°` is the *horn* wall half-angle at 560 Hz and 18 mm radius, not the manufacturer's angle. Do NOT force CAD to 2° and claim driver compatibility.
2. **`01_IMPLEMENTATION_HANDOFF.md`**. Full research dossier with 32-source Lamé/shape-optimization bibliography, geometry equations, typed GRID integration, parameter optimization, mesh and acoustic acceptance gates. The v3 correction and this addendum override any older text or scripts in the archive.
3. **`02_LAME_CAP_MATH_REFERENCE.py`**, standalone NumPy/SciPy numerical area reference. Run independently before porting curved-cap mathematics.
4. **`04_THROAT_ANGLE_ANALYTIC_CHECK.py`**, standard-library analytic test of original Klangfilm half-angle and an optional proposed **derived** C2 entrance correction. Run with `python 04_THROAT_ANGLE_ANALYTIC_CHECK.py`. Compare to `04_THROAT_ANALYTIC_RESULTS.txt`.
5. **`references/`**: original Excel calculator, cached coordinate samples, prior local-agent handoff, source screenshots, user reference comparisons and parameter sweep. These assets ground geometry decisions, not acoustic performance.

## Agent kickoff prompt (copy to your local agent)

> You are implementing the HornFab Lamé/rollback geometry research handoff in a NEW isolated worktree. Before editing, read `03_THROAT_COUPLING_SENIOR_ADDENDUM.md` and `01_IMPLEMENTATION_HANDOFF.md` in full, inspect AGENTS.md/TOOLCHAIN.md, current main and active worktrees, exact mesher and solver versions, and all reference math. Preserve the historical Ahlswede 2018 port, original Le Cléac'h march, old design/mesh hashes, datasets, and live GPU queues. First verify: the HF1440 manufacturer's 35.8 mm combined radial-phase-plug exit has **no published numerical exit angle**; the repo's 2° is a chosen source-cap assumption; the pure 560 Hz/18 mm Klangfilm wall is ~10.617° by independent differentiation. Implement the reusable, versioned, area-checked Lamé/rollback-aware GRID geometry and robust physical throat/tangent diagnostics WITHOUT an automatic forced 2° correction. Initial optimization gene set is nominal cutoff, aperture aspect, Lamé exponent, termination fraction and rim-sweep; source blend is OFF (zero) and not searched. Add optional throat adaptation ONLY in a separate source-controlled, geometry-verified, small acoustic A/B after CPU checks; do not claim the selected value is a physical HF1440 angle without driver measurements/CAD. Generate camera-matched comparison renders, check curved-wavefront area, 3-D mesh normals, shell clearance, source physical tag, param activity, convergence, provenance and deterministic hash/replay. Never launch a large GPU campaign, rewrite scoring v7, update old solved records, or change legacy default configs in this phase. Produce tests, benchmark evidence, and a distinct research/implementation PR or patch. Report failures and remaining uncertainties explicitly.

## Evidence and test status

- The original Klangfilm 2018 Excel/VBA port was previously checked against workbook cached coordinate samples, per the earlier local-agent handoff; this does not establish accuracy for the 2019 high-Lamé fully rolled example.
- New `04_THROAT_ANGLE_ANALYTIC_CHECK.py` ran successfully on the mathematical 2018 parent, including nominal `10.617223°` and 20 derived local-blend combinations. **No actual HF1440 exit slope has been measured, and no full 3-D BEM geometry/source ablation has been performed.**
- `02_LAME_CAP_MATH_REFERENCE.py` numerical self-test passes independently. This is an area-consistent generalized cap approximation, **not a claim of exact parity** with unpublished Ahlswede 2019 code.
- Original 2018 workbook's publication includes noncommercial-use language; check license/permission before distributing code or commercial products derived directly from it.

## Deliverable files

- `00_START_HERE.md` (this overview)
- `01_IMPLEMENTATION_HANDOFF.md` (primary full dossier, v3-corrected)
- `02_LAME_CAP_MATH_REFERENCE.py` (standalone math)
- `03_THROAT_COUPLING_SENIOR_ADDENDUM.md` (new primary+contrary evidence, angle/source protocol)
- `04_THROAT_ANGLE_ANALYTIC_CHECK.py` (standalone analytic test)
- `04_THROAT_ANALYTIC_RESULTS.txt` (recorded numerical output)
- `references/` (source and context files)
- `SHA256SUMS.txt` (manifest for source verification)

**Repository:** https://github.com/llevaachingada/Hornfab
