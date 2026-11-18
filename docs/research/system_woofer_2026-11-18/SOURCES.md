# SOURCES — stage 0 (machine + repo + vendor), 2026-11-18

Companion to `BASELINE.md` in this folder. Facts are tagged: [MACHINE] = executed/read on this
machine this pass; [REPO] = repo file inspected; [WEB] = fetched this pass; [DOC] = master handoff
2026-11-18 (§ numbers refer to it) — treated as claims, not evidence.

## Machine [MACHINE]

1. `git worktree list`, `git log/status` in `C:/Users/hunte/Hrns/hornlab-search` — HEAD `1e9f71b`
   (cloud/fable-next-2026-11-18), 71 commits past `1d6ebc8`, ancestor check exit 0, canonical
   `runs/` live (GPU pid 62432, job c_rrect_100w_rc3).
2. `tools/night_status.py --since-hours 48` (canonical) — GPU lock HELD, CPU lane free. [MACHINE]
3. `pip show boundary-lab` in `C:\Users\hunte\Github\boundary-lab\.venv`, `git rev-parse HEAD`
   there → 15f9a89245a9adfec8c2f0006c164953ce381e58, v0.5.0, GPL-3.0. [MACHINE]
4. Directory scans: `%LOCALAPPDATA%\Programs`, `%LOCALAPPDATA%` ("Boundary Lab" logs dir only),
   `Hrns/*`, home top-level — no other BL install. [MACHINE]
5. Worktree venv: `python -m venv` + `pip install -e worktree` log (numpy 2.5.5, scipy 1.18.1, ...);
   `import hornlab_search` resolves inside the worktree. [MACHINE]
6. Asset counts: 836 run dirs / 41,859 response.npz / 48,207 status.json (recursive scan);
   per-run layout `runs/<run>/designs/<hash>/response.npz`. [MACHINE, read-only]

## Repo files consulted [REPO] (canonical read-only; worktree for owned code)

- `hornlab_search/types.py` — frozen Response fields, `_hash`, MeH additive channel fields (§2 matches).
- `hornlab_search/solve/cache.py` — official loader; explicit `root` params; no env var. (§2 matches.)
- `hornlab_search/solve/beat.py` (55; 553-554), `solve/phasor.py:3-9`, `solve/bempp.py:120-122`,
  `solve/traces.py:216` — stored drive = unit normal ACCELERATION, time exp(−iωt). Decisive
  phase/normalization fact.
- `hornlab_search/compare/hornfab_side.py:42-48` — `accel_to_canonical` = `conj(p·(−1j·ω))`; module
  docstring pins conversion + `+20 log10(2πf)` magnitude shift; tested in
  `tests/test_solve_phasor.py`, `tests/test_compare_ab_model.py`.
- `hornlab_search/meh/dsp.py`, `meh/network.py`, `meh/drivers.py`, `tools/bassbox.py`,
  `tests/test_bassbox.py`, `dataset/identity_v2.py`, `cli.py:29,360` — reuse seams per §2.
- `docs/plan/01_CONTRACTS.md` — FROZEN; contains NO complex-basis/identity-v2 sections; npz key-set
  parity assert in `solve/cache.py` means new fields need a contract-gap note (none added — the
  system package is strictly additive).
- `docs/CONTINUITY.md` (first ~70 lines), `docs/ISSUES.md` (first ~70), `NOTES_FOR_SENIOR.md`
  (last ~50, and one dated append by parent on 2026-11-18), `TOOLCHAIN.md`, `docs/ACTIVE_STATE.md`. [MACHINE]

## Vendor datasheets [WEB] (fetched 2026-11-18 for lane B proposals)

- FaitalPRO 12PR300 8Ω — `https://faitalpro.com/en/products/LF_Loudspeakers/product_details/index.php?id=101050110`
  — all T/S + geometry values verified byte-for-byte vs lane B's proposal; extras captured
  (bolt circle 298.5 mm, flange 12.1 mm, Vad 1.9 dm³, Xdamage 14 mm).
- FaitalPRO 12PR320 8Ω — `.../index.php?id=101050135` — same verification outcome; extras
  (bolt circle 298.5 mm, flange 12.0 mm, Vad 1.9 dm³, Xdamage 17 mm).
- EighteenSound 10NMB420 — `https://www.eighteensound.it/en/products/lf-driver/10-0/8/10nmb420`
  fetched text only (no numeric table); `https://www.eighteensound.com/...` ERR_TLS_CERT_ALTNAME_INVALID.
  **Values UNVERIFIED; datasheet-PDF gate before acceptance.** 12NMB420 same status (not fetched).

## Master handoff [DOC] — load-bearing claims re-verified or deferred

- §2/§3 BL seams: parameters.py/worker.py/backend.py geometry + headless CLI — **deferred to lane C's
  on-install verification** (installed 15f9a89 ≠ doc's 2cea009; installed code wins).
- §4.1 source/time-superposition conventions — encoded in contracts.py; conversion seam verified [REPO].
- §5 bassbox audit claim `z_in = 1.0/i` — reproduced as a red test before fixing [MACHINE].
- §6.1 asset-quality classes — implemented; measured distribution in BASELINE [MACHINE].
- §12 SYS-01 — done; SYS-05/06 partial (synthetic, lane A); SYS-08/18 done (lane D syntheses).
- §17 evidence ledger (S01–S29, D01–D06) — not re-fetched this pass except the four driver pages;
  each borrowed constant or method in system code cites in-code provenance only from repo files.

## Not used / explicitly out of scope this stage

- Fable scratch corpus (LANE_REVIEW/X1/etc.): background only; no selector/predictor adopted [DOC §1].
- Any GPU/BEM/BL solve. Any edit to canonical checkout (except the sanctioned NOTES_FOR_SENIOR.md append).
