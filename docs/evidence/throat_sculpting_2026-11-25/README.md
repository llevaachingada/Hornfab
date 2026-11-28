# Sculpted-throat evidence — FAV-001, 2026-11-25

The pilot tests whether changing the throat alone helps FAV-001 reach the 80° preferred horizontal coverage from 4–8 kHz while keeping vertical coverage in the 40–60° corridor. It uses the room landscape HF1440 700 Hz v11 CD brief and an ideal piston source. The case bank includes flare delays, true constrictions, area-preserving constrictions, and variations of the diagonal shape.

| Evidence | Contents |
|---|---|
| [Reference and repository audit](../../research/typologies/sculpted_throat_2026-11-25/02_REFERENCE_AND_REPO_AUDIT.md) | CAD construction, recipe fit, seed replay, and digest dependencies |
| [Source verification](../../research/typologies/sculpted_throat_2026-11-25/01_SOURCE_VERIFICATION.md) | Primary-source checks and forum access limits |
| [Reference manifest](reference_manifest.json), [STL sections](bld_stl_sections.png), [analytic fit](bld_rosse_fit_stl.json) | Source hashes, derived sections, and reconstruction error |
| [Geometry atlas](GEOMETRY_ATLAS.md), [section plot](atlas_sections.png), [3D views](throat_3d.png), [bank data](bank_fav001.csv) | Analytic and emitted-mesh waists for all 19 cases, including one symmetry-plane refusal |
| [Matched acoustic pilot](MATCHED_ACOUSTIC_PILOT.md) | CPU verify controls, case-level tradeoffs, and mesh sensitivity |
| [Optimizer recommendation](../../research/typologies/sculpted_throat_2026-11-25/03_OPTIMIZER_RECOMMENDATION.md) | Provisional local bounds and refinement criteria |

## Reference CAD cross-check

[Measured] OpenCascade sectioning finished at 20:27 EST. The STEP tessellation used 0.02 mm linear and 0.05 rad angular deflection. Its section radii were compared to the STL at the same axial stations and azimuths, in the original CAD frame. The minimum was on the same vertical diameter and at the same axial station in both exports. Each export picked an opposite end of that diameter as the numerical minimum.

| Quantity | STEP | STL |
|---|---:|---:|
| Minimum wall radius | 4.7933 mm | 4.8006 mm |
| Axial station at minimum | 25.5 mm | 25.5 mm |
| Waist / source radius | 0.3774 | 0.3780 |
| Minimum section area / convex-hull area | 0.8761 | 0.8762 |
| Source aperture occluded axially | 21.014% | 20.998% |

Over the first 50 mm, 36,360 matched rays across 101 sections differ by 0.01579 mm RMS, with a 0.10468 mm maximum. Local sources are `runs/throat_sculpt_2026-11-25/reference/bld_{step,stl}/summary.json` and `angular_radii.npz`. The CAD archives are local under `reference/ath_st260_bld/`.

## Acoustic pilot status

The CPU verify pilot is in progress. The two control scores are 4.993855 (`B0_parent`) and 5.004367 (`B0s_station`). The +0.0105 change motivates a provisional ±0.02 J threshold. The local run is `runs/throat_sculpt_2026-11-25/pilot_fav001/`.
