# FAV-001 matched acoustic pilot — 2026-11-25

**Status:** CPU verification running. This readout currently covers the two controls and the first two slot results.

## What was held fixed

The pilot uses FAV-001 `4140768780f0`, the [700 Hz HF1440 v11 CD brief](../../../examples/briefs/cd_v11_2026-11-20/room_landscape_80x50_700_hf1440_v11cd.yaml), and the [19-case bank](../../../examples/typologies/throat_sculpt_2026-11-25/pilot_fav001.yaml). The baseline passes an 18 mm radius, 2° driver exit into the same horn body and mouth. The i7-14650HX CPU lane is running BEAT CPU with the `verify` grid (`debe4c1083c2`, 29 frequencies over 300–8,000 Hz, 6 elements per wavelength at mesh fmax, quarter domain, 1,024-point balloon, 10 m observation). The v11 scored band is 350–8,000 Hz and the nominal 80° H / 50° V targets are inside the 60–90° H / 40–60° V corridors.

`B0_parent` uses the original 40-station design and reproduces its saved GPU result to 0.000026 J. `B0s_station` uses 64 stations and a negligible `ts_c2 = 1e-9` to exercise the sculpt stationing. Its +0.010512 J shift gives one measured estimate of numerical sensitivity. Treat changes below about 0.02 J as unresolved. The two controls bracket the main stationing change, but the core/body split still varies by treatment. In the geometry bank `B0s_station` has a 42 mm core and 18 dense stations, while some long-delay cases have 70–75 mm cores and 32–34 dense stations. The discrepancy matters when a small apparent gain comes from a long operator. Finalists need finer meshes and, for materially different core extents, a neutral geometry control with a matching core extent.

## How to read each case

- Compare ΔJ with both `B0_parent` and `B0s_station`. Lower is better. Inspect the measured grid within 4–8 kHz as well as the reported 4, 6.3 and 8 kHz values. The non-grid values interpolate in log frequency. The beamwidth is the total angle between the −6 dB crossings.
- `diag` is the diagonal beamwidth error relative to a 65° round reference on this brief. `distd` is the standard deviation of balloon DI over the scored profile band. Both have zero weight in J and must be inspected directly. The objective also has a separately weighted CD DI term.
- Compare the weighted `load` term, normalized throat-resistance curve, mean over band, and sampled minimum over the loaded window (700–5,600 Hz). A higher mean resistance can coexist with a weaker minimum near crossover. The modeled throat resistance and polar response use the brief's ideal piston source.

## Results so far

From the generated report as of 20:44 EST, eliding the header and controls:

```text
| S_h10 | 6.0502 | +1.0564 | +1.0459 | 67/77/79 | 59/48/59 | 11.40 | 0.856 | 2.824 | 0.007 | 0.244 | 0.472 | 0.059 | 0.990 |
| S_h20 | 7.3585 | +2.3646 | +2.3541 | 73/81/86 | 57/48/71 | 9.89 | 0.885 | 2.841 | 0.013 | 0.615 | 0.608 | 0.000 | 1.514 |
```

`S_h10` improves the upper end of the H cut (79° at 8 kHz versus about 69° for both controls), but H falls to 67° at 4 kHz. It worsens J by more than 1.04 against both controls. The largest weighted loss against the station control is off-axis smoothness (+0.564), followed by on-axis flatness (+0.215). Raw diagonal error rises from 0.219 to 0.244 while raw DI spread falls from 0.492 to 0.472 dB. Mean normalized resistance rises from 0.810 to 0.856, but its minimum in the loaded window drops from 0.300 to 0.291 and the load contribution rises from 2.728 to 2.824. One slot case demonstrates a change in H coverage, with a tradeoff in pattern and frequency-response consistency.

`S_h20` reduces H mean absolute error against the preferred 80° from 10.87° to 2.89° over the sampled 4–8 kHz band, but V exceeds the corridor on two samples and reaches 70.6° at 8 kHz. The extra horizontal width comes with +2.35 J versus the station control. Off-axis smoothness contributes +1.088, followed by +0.299 for on-axis flatness. Raw diagonal error rises to 0.615, DI spread to 0.608 dB, and the load contribution to 2.841. Its normalized loaded-window resistance minimum is 0.291 despite mean band resistance rising to 0.885.

## Meshing sensitivity

`S_v20` failed the symmetry-plane guard in the pilot geometry bank. A geometry-only repeat on the same design with the production mesher gave the following lines, eliding the mesher's separate shell-clearance notice and blank lines:

```text
S_v20 epw=6: GeometryInvalidError: mesh build failed: 8 non-sliver triangle(s) lie entirely in the y=0 symmetry plane; the geometry is defective
S_v20 epw=7.5: GeometryInvalidError: mesh build failed: 11 non-sliver triangle(s) lie entirely in the y=0 symmetry plane; the geometry is defective
S_v20 epw=9: GeometryInvalidError: mesh build failed: 20 non-sliver triangle(s) lie entirely in the y=0 symmetry plane; the geometry is defective
```

The refusal persists at finer density. This case cannot serve as the acoustic rotated-slot control. See the [geometry atlas](GEOMETRY_ATLAS.md) and the local reproduction log `runs/throat_sculpt_2026-11-25/s_v20_mesh_check.log`.
