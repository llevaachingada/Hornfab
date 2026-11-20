# FAV-001 8-hour variation night `fav8_2026-11-20`

Owner request (2026-11-20 17:07): "queue up like 8 hours of solves related to variations on this new FAV horn".
Builds on `CROWE_X_FAVORITE_RESEARCH.md` (and its addenda): k ≈ 2 trades directivity for loading ~1:1; no
k-free design matched FAV-001's directivity; compact 500/900 is viable (`746d33134776`, verify 2.809).

Night: `docs/queue/fav8_2026-11-20.yaml` (live copy `runs/nights/`), launched 17:14 detached
(queue.ps1 pid 61992). 12 CMA lanes × 80 valid, `max_attempts` 450, then `verify_night_jobs.py --top 3` for every
lane. Configs: `examples/typologies/fav8_2026-11-20/` (writer `cpu/write_fav8.py`). shape_check 12/12 fit after
re-fitting `g_s` for the three wider/deeper seeds. Preflight: no HARD; uniform valid fraction 15–29 %, all envelope refusals.

**Rank only within one identity.**

| identity | brief | lanes |
|---|---|---|
| home 700 Hz v11 (= FAV-001's) | `cd_v11_2026-11-20/room_landscape_80x50_700_hf1440_v11cd.yaml` | k1_cd_polish, k_low, k_low_s2 (CMA seed 2026), sf_shape, wide_h, lip_study, deep |
| **NEW** home XO900 v11 | `home_xo900_2026-11-20/room_landscape_80x50_900_hf1440_v11cd.yaml` (envelope unchanged; only F_X 900, H anchor, CD band) | x900_k1, x900_klow_sf |
| compact500 XO900 v11 | `compact500_xo900_2026-11-20/…` | c500_polish, c500_wide_h, c500_sf (seeded at `746d33134776`) |

Questions each lane answers:
- **k1_cd_polish / x900_k1**: how good FAV-001's directivity can get with k held at 1 (wider box for depth, flare, lip and angles), under each crossover floor.
- **k_low (+ _s2 twin)**: is k in [1, 1.6] a better trade than k ≈ 2? The twin measures seed variance.
- **wide_h / c500_wide_h**: push toward a true 80 × 50 (FAV-001 is ~69 × 58; the compact horn narrows to ~58° H).
- **sf_shape / x900_klow_sf / c500_sf**: unlock the superformula mouth-morph shape (n1, n2, onset; m stays 4), never searched before.
- **lip_study**: mouth termination (wrap 30–200°, r_lip to 45 mm, OSSE q 0.95–0.999).
- **deep**: use the unused depth (L 260–420; the brief allows 480).

Read results with `tools/night_status.py`, per brief. For the owner, show CD-matrix terms and "non-load"
next to J (memory: the owner judges by directivity plots).
