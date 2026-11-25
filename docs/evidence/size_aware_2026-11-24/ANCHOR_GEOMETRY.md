# Exact-anchor existing-law geometry controls

Reproduce from the repository root with `.venv\Scripts\python.exe docs/evidence/size_aware_2026-11-24/anchor_geometry.py`. The script reads the original saved `design.json` and `run.json`, checks the recorded parent implementation digest against the current implementation, uses their effective brief and knobs, and writes `anchor_geometry.json` and four fixed-seed YAML configurations. The original local runs are required. It calls CPU geometry only.

Both neutral adapters reproduce their exact saved parent **inner and outer point arrays bit-for-bit**. The rolled front-load control uses the existing CD law at H +10°, V +6°, window 0.30/0.60/0.88; maximum point displacement is 7.650 mm. Its inner lip and final 10% of sampled stations are unchanged. The Lamé Phase A control holds both entrance slopes at the actual parent's dense-table chord values, adds 2 mm H mid-gain with a 0.65 forward-branch join, and changes the inner grid by at most 1.930 mm. Its final lip differs by 0.000026 mm and final 10% by at most 0.0102 mm, caused by the altered arc-length resampling; the underlying parent rollback is not deformed. Full tangent samples, extents, driver, knob values, and implementation digests are in the JSON and YAMLs. Station angles are finite-difference directions along the sampled meridians; the returning section can exceed 90° or wrap negative, and these angles are not predicted acoustic beamwidths.

CPU shape preflight, 2026-11-24, exact command:

```powershell
.venv\Scripts\python.exe tools/shape_check.py docs/evidence/size_aware_2026-11-24/anchor_rolled_neutral.yaml docs/evidence/size_aware_2026-11-24/anchor_rolled_variant.yaml docs/evidence/size_aware_2026-11-24/anchor_lame_neutral.yaml docs/evidence/size_aware_2026-11-24/anchor_lame_variant.yaml
```

```text
| config | ok | dofs / cap | mouth W x H mm | depth mm | envelope | driver coupling |
| anchor_lame_neutral | yes | 3536 / 24000 | 490 x 281 | 210 | fits (production) | round, matches the exit |
| anchor_lame_variant | yes | 3534 / 24000 | 490 x 281 | 210 | fits (production) | round, matches the exit |
| anchor_rolled_neutral | yes | 3495 / 6000 | 581 x 366 | 217 | fits (production) | round, matches the exit |
| anchor_rolled_variant | yes | 3543 / 6000 | 581 x 366 | 217 | fits (production) | round, matches the exit |
```

These are geometry-valid hypotheses, not predicted improvements. Any future acoustic comparison must re-solve each neutral and variant with identical effective brief, mesh, source and fidelity, and compare full cuts, diagonal behavior, loading and score components. No BEM was run for these controls. Use separate caches, one GPU solve at a time, and normal lock and worker hygiene.
