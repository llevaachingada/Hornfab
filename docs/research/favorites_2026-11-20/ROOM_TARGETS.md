# Coverage targets for the owner's room (2026-11-20)

Owner: room ~20 ft × 16 ft × 9 ft (6.1 × 4.9 × 2.74 m), **speakers on the 20 ft wall** (firing across the 16 ft
dimension), goal: **wide sweet spot**. Questioned whether the 80 × 50° briefs are right.

## Geometry [derived; assumptions labeled]
Assumed [inferred]: tweeter/horn axis 1.0 m high, seated ears 1.1 m, listening distance ~3.0 m (16 ft depth minus
speaker and seat clearance). Image-source reflection angles leaving the horn:
- floor: x = 3.0·1.0/(1.0+1.1) = 1.43 m → **~35° below axis**;
- ceiling: x = 3.0·1.74/(1.74+1.64) = 1.54 m → **~48° above axis**.
A 50° vertical pattern (±25° at −6 dB) already puts both bounces well down. 60° is more forgiving for
standing/tall seating at the cost of more floor/ceiling energy. Narrowing below 50° is not needed.

On the 20 ft wall the speakers can sit wide (~2.5–3 m apart) with long paths to the side walls, so lateral
reflections arrive later and from wider angles.

## Horizontal
For a wide sweet spot, the established practice is **~90° CD horns toed in so the axes cross in front of the
listening position**. Moving toward one speaker moves you off its axis and onto the far speaker's axis, so
level/time trade-off keeps the image centred. [secondary (practitioner reports): Geddes' toe-in/crossfire
recommendation, diyAudio "Geddes on waveguides".] Wide lateral coverage into the side walls is also associated
with preferred spaciousness (Toole/Olive preference work, cited in `docs/research/SIM_VS_REAL_HORN_2026-10-27.md` §4).
**So H 90° (corridor 75–105) is the better target here than 80°.** 80° stays as a control (FAV-001 is ~69° in practice).

## Lanes queued (live `fav8_2026-11-20`, after `favA9_verify_top3`)
Briefs `examples/briefs/room_2026-11-20/`: the v11 home brief with only the coverage corridors, `coverage_h/v_deg`,
F_X, CD band start and envelope changed. **Each brief is its own J identity.** Lanes: P1 split-plane
(`g_k_v`, `g_s_v`) seeded from FAV-001 with angles and depth re-fitted (`cpu/write_room.py`), CMA 80 valid each:

| lane | brief | envelope | F_X | H target | V target |
|---|---|---|---|---|---|
| `room__w90x50_home` | room_w90x50_700 | 600×480×480 | 700 | 90 (75–105) | 50 (40–60) |
| `room__w90x60_home` | room_w90x60_700 | 600×480×480 | 700 | 90 | 60 (48–72) |
| `room__c400_w90x50` | compact400_xo1000_w90x50 | 400³ | 1000 | 90 | 50 |
| `room__c400_w90x60` | compact400_xo1000_w90x60 | 400³ | 1000 | 90 | 60 |
| `room__c400_80x50` | compact400_xo1000_80x50 | 400³ | 1000 | 80 | 50 |

+ `room_verify_top3`. shape_check 5/5 fit (compact seeds 388 × 269–330 mm, depth 148–179 mm). Preflight no HARD:
valid 25 % on 12 uniform samples after tightening the boxes (CMA stays near the seed; `max_attempts` 450).
