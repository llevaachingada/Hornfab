# Exact proposed review domains

Every range below is a **CPU review domain**, intersected with the listed physical/construction constraints. No family receives an approved acoustic optimization domain from this audit. A source law or capability gap cannot be repaired by choosing a larger box. Original files and recipes stay unchanged. Numeric domains, seeds, transforms, activity and nominal initial physical steps are carried verbatim from the resolved inventory; fixed controls are explicit. This is a bounded proposal to test or reject current domains before any future short pilot.

For linear bounds the nominal starting step is sigma0*(hi-lo); fixed step0. Log bounds use the recorded asymmetric steps. These are current, unbounded initial standard deviations, not promises that they fit a useful acoustic basin. A later30-call pilot must set its step using measured local feasibility and incumbent spread, retaining all useful controls. No invented uniform small sigma is approved.

Per-key meanings and activity: [semantics](domains_semantics.md). Current evidence: [inventory JSON](domains_current.json). The generator/sampling/driver fixed rows below are physical identity inputs, not searched controls. Untraced dependency defaults remain a blocking inventory gap, rather than fabricated values.


## hl__ath_core_petal_hvlaw_v7

Source `examples/typologies/home_landscape_2026-11-15/hl__ath_core_petal_hvlaw_v7.yaml`, SHA256 `a56c824b0906ac7203a509db199331fc7ced16fe6dfddee5b2f3713bc801f4c6`. Starting unit sigma `0.2`; blocked for acoustics.

| Key | Physical meaning / unit | Seed | Proposed bounds | Transform / activity | Initial physical step |
|---|---|---|---|---|---|
| `L_mm` | axial profile length / mm | 250.0 | 160.0 .. 340.0 | linear unit interval / searched | 36.0 |
| `a0_deg` | throat wall angle / deg | 1.9863 | 1.0 .. 3.0 | linear unit interval / searched | 0.4 |
| `a_deg` | profile wall angle (interpretation depends on profile) / deg | 24.0 | 12.0 .. 36.0 | linear unit interval / searched | 4.800000000000001 |
| `aspect_ratio` | cross section aspect ratio / dimensionless / categorical | 1.0 | fixed 1.0 | fixed / fixed bound | 0 |
| `az_a_cos_amp` | azimuth wall angle cosine amplitude / deg | 14.0 | 0.0 .. 25.0 | linear unit interval / searched | 5.0 |
| `az_a_cos_pow` | azimuth angle cosine exponent / dimensionless / categorical | 2.0 | 1.0 .. 6.0 | linear unit interval / searched; inactive when az_a_cos_amp=0 | 1.0 |
| `az_a_sf_amp` | azimuth superformula wall-angle amplitude / deg | 3.0 | 0.0 .. 8.0 | linear unit interval / searched | 1.6 |
| `az_n_cos2_amp` | azimuth profile exponent cosine amplitude / dimensionless / categorical | 0.0 | fixed 0.0 | fixed / fixed bound | 0 |
| `az_s_cos2_amp` | azimuth termination cosine amplitude / dimensionless / categorical | 0.0 | -0.25 .. 0.5 | linear unit interval / searched | 0.15000000000000002 |
| `az_sf_a` | azimuth superformula scale a / dimensionless / categorical | 1.0 | fixed 1.0 | fixed / fixed bound; azimuth superformula affects wall only when az_a_sf_amp nonzero | 0 |
| `az_sf_b` | azimuth superformula scale b / dimensionless / categorical | 0.8569 | fixed 0.8569 | fixed / fixed bound; azimuth superformula affects wall only when az_a_sf_amp nonzero | 0 |
| `az_sf_m` | azimuth superformula symmetry order / dimensionless / categorical | 4.0 | fixed 4.0 | fixed / fixed bound; azimuth superformula affects wall only when az_a_sf_amp nonzero | 0 |
| `az_sf_n1` | azimuth superformula exponent 1 / dimensionless / categorical | 7.4958 | fixed 7.4958 | fixed / fixed bound; azimuth superformula affects wall only when az_a_sf_amp nonzero | 0 |
| `az_sf_n2` | azimuth superformula exponent 2 / dimensionless / categorical | 12.4449 | fixed 12.4449 | fixed / fixed bound; azimuth superformula affects wall only when az_a_sf_amp nonzero | 0 |
| `az_sf_n3` | azimuth superformula exponent 3 / dimensionless / categorical | 13.4442 | fixed 13.4442 | fixed / fixed bound; azimuth superformula affects wall only when az_a_sf_amp nonzero | 0 |
| `exponent` | cross section exponent / dimensionless / categorical | 2.0 | fixed 2.0 | fixed / fixed bound | 0 |
| `k` | OSSE base throat-to-wall shape factor / dimensionless / categorical | 1.2163 | 0.3 .. 3.0 | linear unit interval / searched | 0.54 |
| `morph_allow_shrinkage` | mouth morph shrinkage flag / dimensionless / categorical | 0 | fixed 0 | fixed / fixed bound; inactive if morph_target=0 | 0 |
| `morph_corner_mm` | mouth morph corner radius / mm | 15.0 | fixed 15.0 | fixed / fixed bound; inactive if morph_target=0; corner applies to rectangular target only | 0 |
| `morph_exponent` | mouth morph exponent / dimensionless / categorical | 4.5 | fixed 4.5 | fixed / fixed bound; inactive if morph_target=0; exponent applies to superellipse target 3 only | 0 |
| `morph_fixed` | mouth morph fixed factor / dimensionless / categorical | 0.0 | fixed 0.0 | fixed / fixed bound; inactive if morph_target=0 | 0 |
| `morph_height_mm` | mouth morph target height / mm | 400.0 | fixed 400.0 | fixed / fixed bound; inactive if morph_target=0 | 0 |
| `morph_rate` | mouth morph rate / dimensionless / categorical | 3.46 | fixed 3.46 | fixed / fixed bound; inactive if morph_target=0 | 0 |
| `morph_target` | mouth morph target selection / dimensionless / categorical | 0 | fixed 0 | fixed / fixed bound | 0 |
| `morph_width_mm` | mouth morph target width / mm | 540.0 | fixed 540.0 | fixed / fixed bound; inactive if morph_target=0 | 0 |
| `n` | OSSE superellipse termination exponent / dimensionless / categorical | 6.9046 | 2.0 .. 10.0 | linear unit interval / searched; termination term inactive when s=0 | 1.6 |
| `q` | OSSE normalized termination saturation / dimensionless / categorical | 0.9869 | 0.9 .. 1.0 | linear unit interval / searched; termination term inactive when s=0 | 0.019999999999999997 |
| `r0_mm` | throat radius / mm | 18.0 | fixed 18.0 | fixed / fixed bound; fresh supplied brief pins radius to driver, unless extension active; embedded replay retains saved config | 0 |
| `s` | OSSE termination amplitude / dimensionless / categorical | 0.7503 | 0.2 .. 1.2 | linear unit interval / searched | 0.2 |
| `s1` | throat stretch coefficient: x_stretched = x + s1*degrees(atan(s2*x)) / mm/deg | 1.1799 | fixed 1.1799 | fixed / fixed bound; requires both s1 and s2 nonzero | 0 |
| `s2` | throat stretch coefficient: x_stretched = x + s1*degrees(atan(s2*x)) / 1/mm | 0.0286 | fixed 0.0286 | fixed / fixed bound; requires both s1 and s2 nonzero | 0 |
| `brief.driver.exit_radius_mm` | driver coupling-plane radius / mm | 18.0 | fixed 18.0 | fixed / fixed construction input | 0 |
| `brief.driver.exit_angle_deg` | driver exit wall half-angle / deg | 2.0 | fixed 2.0 | fixed / fixed construction input | 0 |

Coupled constraints:

- All resolved physical values finite; every seed present and inside its own declared domain; fixed values equal both endpoints.
- Finished inner+outer+closure envelope W<=600 mm,H<=480 mm,D<=480 mm and W>H; nominal dimensions are not the test.
- Driver connection radius18 mm; physical tangent/source-cap policy must be resolved per family, including R-OSSE and extended-throat cases.
- Reject nonpositive radius, degeneracy, nonmanifold connectivity, unintended intersections/clearance failure and invalid source cap before acoustics; preserve refusal records.
- No silent clipping onto another candidate; canonical full-boundary duplicate identity and inherited config/source/recipe/brief/mesh/solve hashes required.
- No acoustic launch under this document; separate objective, geometry, replay and validation gates apply.
- Evaluate complete azimuth functions a(phi),n(phi),s(phi); require valid OSSE at every azimuth, round driver and quarter symmetry (superformula m multiple4 when required).
- Morph target0 makes target dimensions/rate/corner/exponent inactive; use per-law activity mapping, never count inactive dimensions as distinct physical observations.

## hl__biradial_es_style_v7

Source `examples/typologies/home_landscape_2026-11-15/hl__biradial_es_style_v7.yaml`, SHA256 `9a113bf349143c89b788b6f016e0a1a3a5531ff5112c1939b7b28d28a8131a03`. Starting unit sigma `0.2`; blocked for acoustics.

| Key | Physical meaning / unit | Seed | Proposed bounds | Transform / activity | Initial physical step |
|---|---|---|---|---|---|
| `L_mm` | axial profile length / mm | 255.0 | 220.0 .. 320.0 | linear unit interval / searched | 20.0 |
| `h_a_deg` | horizontal profile wall angle (interpretation depends on profile) / deg | 36.0 | 32.0 .. 37.0 | linear unit interval / searched | 1.0 |
| `h_n` | plane-specific power n in r=r0+tan(a)z+c*z^n, with c constrained by mouth radius and length / dimensionless / categorical | 5.0 | 3.0 .. 7.0 | linear unit interval / searched | 0.8 |
| `h_rm_mm` | horizontal mouth radius in plane / mm | 280.0 | 260.0 .. 292.0 | linear unit interval / searched | 6.4 |
| `h_throat_blend_mm` | horizontal throat blend length / mm | 25.0 | fixed 25.0 | fixed / fixed bound | 0 |
| `mouth_exponent` | mouth outline superellipse exponent / dimensionless / categorical | 3.0 | 2.2 .. 5.0 | linear unit interval / searched | 0.5599999999999999 |
| `v_a_deg` | vertical profile wall angle (interpretation depends on profile) / deg | 22.5 | 18.0 .. 24.0 | linear unit interval / searched | 1.2000000000000002 |
| `v_n` | plane-specific power n in r=r0+tan(a)z+c*z^n, with c constrained by mouth radius and length / dimensionless / categorical | 5.0 | 3.0 .. 7.0 | linear unit interval / searched | 0.8 |
| `v_rm_mm` | vertical mouth radius in plane / mm | 175.0 | 162.0 .. 230.0 | linear unit interval / searched | 13.600000000000001 |
| `v_throat_blend_mm` | vertical throat blend length / mm | 25.0 | fixed 25.0 | fixed / fixed bound | 0 |
| `generator.name` | generator construction route / dimensionless / categorical | typology | fixed typology | fixed / fixed construction input | 0 |
| `generator.profile_h.type` | profile or rows construction kind / dimensionless / categorical | biradial | fixed biradial | fixed / fixed construction input | 0 |
| `generator.profile_v.type` | profile or rows construction kind / dimensionless / categorical | biradial | fixed biradial | fixed / fixed construction input | 0 |
| `generator.n_anchors` | number of meridian anchor stations / dimensionless / categorical | 16 | fixed 16 | fixed / fixed construction input | 0 |
| `generator.max_wall_deg` | maximum meridian wall angle guard / deg | 80.0 | fixed 80.0 | fixed / fixed construction input | 0 |
| `generator.mouth` | mouth cross-section law / dimensionless / categorical | superellipse | fixed superellipse | fixed / fixed construction input | 0 |
| `generator.seed_policy` | config-load seed derivation policy / dimensionless / categorical | explicit | fixed explicit | fixed / fixed construction input | 0 |
| `generator.wall_thickness_mm` | resolver default wall thickness / mm | 3.0 | fixed 3.0 | fixed / fixed construction input | 0 |
| `morph_target` | native mouth morph target (0 off) / dimensionless / categorical | 0 | fixed 0 | fixed / fixed off; other morph controls inactive | 0 |
| `brief.driver.exit_radius_mm` | driver coupling-plane radius / mm | 18.0 | fixed 18.0 | fixed / fixed construction input | 0 |
| `brief.driver.exit_angle_deg` | driver exit wall half-angle / deg | 2.0 | fixed 2.0 | fixed / fixed construction input | 0 |

Coupled constraints:

- All resolved physical values finite; every seed present and inside its own declared domain; fixed values equal both endpoints.
- Finished inner+outer+closure envelope W<=600 mm,H<=480 mm,D<=480 mm and W>H; nominal dimensions are not the test.
- Driver connection radius18 mm; physical tangent/source-cap policy must be resolved per family, including R-OSSE and extended-throat cases.
- Reject nonpositive radius, degeneracy, nonmanifold connectivity, unintended intersections/clearance failure and invalid source cap before acoustics; preserve refusal records.
- No silent clipping onto another candidate; canonical full-boundary duplicate identity and inherited config/source/recipe/brief/mesh/solve hashes required.
- No acoustic launch under this document; separate objective, geometry, replay and validation gates apply.
- For j=H,V: rm_j >= 18+L*tan(a_j*pi/180); n_j>=1 and finite derived c=(rm_j-18-L*tan(a_j))/L**n_j. This is construction closure, not a beamwidth prediction.
- Resolve actual 25 mm throat blend in both planes; check its endpoint derivatives and full-body envelope. Preserve stock corrected config separately from failed old runs.

## hl__crowe_es_biradial_rr_v7

Source `examples/typologies/home_landscape_2026-11-15/hl__crowe_es_biradial_rr_v7.yaml`, SHA256 `77739a930e0ce61eede18658bd5cc8f376104dc6e40cc5ed3193819e049add5b`. Starting unit sigma `0.2`; blocked for acoustics.

| Key | Physical meaning / unit | Seed | Proposed bounds | Transform / activity | Initial physical step |
|---|---|---|---|---|---|
| `L_mm` | axial profile length / mm | 200.0 | 170.0 .. 260.0 | linear unit interval / searched | 18.0 |
| `h_T` | plane-specific hypex hyperbolic profile parameter T; T=1 gives exponential limit / dimensionless / categorical | 1.0 | 0.6 .. 1.0 | linear unit interval / searched | 0.08000000000000002 |
| `h_rm_mm` | horizontal mouth radius in plane / mm | 250.0 | 215.0 .. 290.0 | linear unit interval / searched | 15.0 |
| `mouth_corner_mm` | mouth corner radius / mm | 40.0 | 20.0 .. 80.0 | linear unit interval / searched | 12.0 |
| `v_T` | plane-specific hypex hyperbolic profile parameter T; T=1 gives exponential limit / dimensionless / categorical | 1.0 | 0.6 .. 1.0 | linear unit interval / searched | 0.08000000000000002 |
| `v_rm_mm` | vertical mouth radius in plane / mm | 125.0 | 105.0 .. 160.0 | linear unit interval / searched | 11.0 |
| `generator.name` | generator construction route / dimensionless / categorical | typology | fixed typology | fixed / fixed construction input | 0 |
| `generator.seed_policy` | config-load seed derivation policy / dimensionless / categorical | explicit | fixed explicit | fixed / fixed construction input | 0 |
| `generator.profile_h.type` | profile or rows construction kind / dimensionless / categorical | hypex | fixed hypex | fixed / fixed construction input | 0 |
| `generator.profile_v.type` | profile or rows construction kind / dimensionless / categorical | hypex | fixed hypex | fixed / fixed construction input | 0 |
| `generator.n_anchors` | number of meridian anchor stations / dimensionless / categorical | 20 | fixed 20 | fixed / fixed construction input | 0 |
| `generator.max_wall_deg` | maximum meridian wall angle guard / deg | 85.0 | fixed 85.0 | fixed / fixed construction input | 0 |
| `generator.mouth` | mouth cross-section law / dimensionless / categorical | rounded_rectangle | fixed rounded_rectangle | fixed / fixed construction input | 0 |
| `generator.wall_thickness_mm` | outer wall thickness / mm | 4.0 | fixed 4.0 | fixed / fixed construction input | 0 |
| `morph_target` | native mouth morph target (0 off) / dimensionless / categorical | 0 | fixed 0 | fixed / fixed off; other morph controls inactive | 0 |
| `h_throat_blend_mm` | h throat blend length; zero skips blend / mm | 0.0 | fixed 0.0 | fixed / fixed off | 0 |
| `v_throat_blend_mm` | v throat blend length; zero skips blend / mm | 0.0 | fixed 0.0 | fixed / fixed off | 0 |
| `brief.driver.exit_radius_mm` | driver coupling-plane radius / mm | 18.0 | fixed 18.0 | fixed / fixed construction input | 0 |
| `brief.driver.exit_angle_deg` | driver exit wall half-angle / deg | 2.0 | fixed 2.0 | fixed / fixed construction input | 0 |

Coupled constraints:

- All resolved physical values finite; every seed present and inside its own declared domain; fixed values equal both endpoints.
- Finished inner+outer+closure envelope W<=600 mm,H<=480 mm,D<=480 mm and W>H; nominal dimensions are not the test.
- Driver connection radius18 mm; physical tangent/source-cap policy must be resolved per family, including R-OSSE and extended-throat cases.
- Reject nonpositive radius, degeneracy, nonmanifold connectivity, unintended intersections/clearance failure and invalid source cap before acoustics; preserve refusal records.
- No silent clipping onto another candidate; canonical full-boundary duplicate identity and inherited config/source/recipe/brief/mesh/solve hashes required.
- No acoustic launch under this document; separate objective, geometry, replay and validation gates apply.
- This is Hypex, not the Crowe spiral or Keele bi-radial. Use actual hypex inversion/finite-curvature/max-wall-angle guards for both planes; rounded mouth corner <=min(half-width,half-height).
- No acoustic domain proposed under Crowe attribution; retain numeric box for neutral Hypex CPU reference only.

## hl__crowe_panel_home_v7

Source `examples/typologies/home_landscape_2026-11-15/hl__crowe_panel_home_v7.yaml`, SHA256 `3960c358d2c65e2c5f8a86e2cc1b5cf99a542743cdaaa2115e4a07c0c43de6fe`. Starting unit sigma `0.2`; blocked for acoustics.

| Key | Physical meaning / unit | Seed | Proposed bounds | Transform / activity | Initial physical step |
|---|---|---|---|---|---|
| `g_crown_mm` | section crown / mm | 26.0 | 10.0 .. 40.0 | linear unit interval / searched | 6.0 |
| `g_depth_mm` | nominal depth / mm | 270.0 | 170.0 .. 300.0 | linear unit interval / searched | 26.0 |
| `g_h_depth_scale` | horizontal section depth scale relative to reference vertical section / dimensionless / categorical | 1.0 | 0.9 .. 1.1 | linear unit interval / searched | 0.040000000000000015 |
| `g_height_mm` | nominal height / mm | 280.0 | 220.0 .. 420.0 | linear unit interval / searched | 40.0 |
| `g_junction_power` | section junction exponent / dimensionless / categorical | 32.0 | 16.0 .. 48.0 | linear unit interval / searched | 6.4 |
| `g_throat_blend_mm` | throat blend length / mm | 20.0 | fixed 20.0 | fixed / fixed bound | 0 |
| `g_width_mm` | nominal width / mm | 560.0 | 480.0 .. 590.0 | linear unit interval / searched | 22.0 |
| `generator.name` | generator construction route / dimensionless / categorical | grid | fixed grid | fixed / fixed construction input | 0 |
| `generator.rows.type` | profile or rows construction kind / dimensionless / categorical | crowe_panel | fixed crowe_panel | fixed / fixed construction input | 0 |
| `generator.seed_policy` | config-load seed derivation policy / dimensionless / categorical | explicit | fixed explicit | fixed / fixed construction input | 0 |
| `generator.span` | modeled azimuthal span and symmetry / dimensionless / categorical | quarter | fixed quarter | fixed / fixed construction input | 0 |
| `generator.n_phi` | number of azimuth samples / dimensionless / categorical | 49 | fixed 49 | fixed / fixed construction input | 0 |
| `generator.n_s` | number of curve stations / dimensionless / categorical | 96 | fixed 96 | fixed / fixed construction input | 0 |
| `generator.wall_thickness_mm` | outer wall thickness / mm | 3.0 | fixed 3.0 | fixed / fixed construction input | 0 |
| `brief.driver.exit_radius_mm` | driver coupling-plane radius / mm | 18.0 | fixed 18.0 | fixed / fixed construction input | 0 |
| `brief.driver.exit_angle_deg` | driver exit wall half-angle / deg | 2.0 | fixed 2.0 | fixed / fixed construction input | 0 |

Coupled constraints:

- All resolved physical values finite; every seed present and inside its own declared domain; fixed values equal both endpoints.
- Finished inner+outer+closure envelope W<=600 mm,H<=480 mm,D<=480 mm and W>H; nominal dimensions are not the test.
- Driver connection radius18 mm; physical tangent/source-cap policy must be resolved per family, including R-OSSE and extended-throat cases.
- Reject nonpositive radius, degeneracy, nonmanifold connectivity, unintended intersections/clearance failure and invalid source cap before acoustics; preserve refusal records.
- No silent clipping onto another candidate; canonical full-boundary duplicate identity and inherited config/source/recipe/brief/mesh/solve hashes required.
- No acoustic launch under this document; separate objective, geometry, replay and validation gates apply.
- 0.9<=h_depth_scale<=1.1; 0<=crown<0.2*height;16<=junction_power<=48;0<throat_blend<0.2*depth.
- Use actual _sweep tests: max(zH)<max(zV),positive pivot,single-peaked sweep radius,compatible return domains,real radicand and source blend after inverse exists. Do not substitute empirical depth<=0.57*width for these exact tests.
- Outer return/closure needs off-axis tangent,intersection and clearance audit; consistent winding alone is insufficient.

## hl__crowe_x_osse_cd_v7

Source `examples/typologies/home_landscape_2026-11-15/hl__crowe_x_osse_cd_v7.yaml`, SHA256 `31fb58d2cf5372531ce9071061e62e403b9beaed3a5dc14efe2f9ea2e4c92f73`. Starting unit sigma `0.2`; blocked for acoustics.

| Key | Physical meaning / unit | Seed | Proposed bounds | Transform / activity | Initial physical step |
|---|---|---|---|---|---|
| `g_L_mm` | axial profile length / mm | 240.0 | 200.0 .. 260.0 | linear unit interval / searched | 12.0 |
| `g_a_h_deg` | horizontal wall half-angle / deg | 38.0 | 33.0 .. 40.0 | linear unit interval / searched | 1.4000000000000001 |
| `g_a_v_deg` | vertical wall half-angle / deg | 24.0 | 20.0 .. 28.0 | linear unit interval / searched | 1.6 |
| `g_k` | OSSE base throat-to-wall shape factor / dimensionless / categorical | 1.0 | fixed 1.0 | fixed / fixed bound | 0 |
| `g_n` | OSSE superellipse termination exponent / dimensionless / categorical | 2.0 | 1.8 .. 3.2 | linear unit interval / searched; termination term inactive when s=0 | 0.28 |
| `g_q` | OSSE normalized termination saturation / dimensionless / categorical | 0.996 | fixed 0.996 | fixed / fixed bound; termination term inactive when s=0 | 0 |
| `g_r_lip_mm` | lip radius / mm | 25.0 | 8.0 .. 30.0 | linear unit interval / searched | 4.4 |
| `g_s` | OSSE termination amplitude / dimensionless / categorical | 0.35 | 0.2 .. 0.45 | linear unit interval / searched | 0.05 |
| `g_sf_ab` | superformula aspect factor / dimensionless / categorical | 0.8 | 0.7 .. 0.9 | linear unit interval / searched; superformula shape inactive when g_sf_amt=0 | 0.040000000000000015 |
| `g_sf_amt` | superformula shaping amount / dimensionless / categorical | 0.3 | 0.15 .. 0.38 | linear unit interval / searched | 0.046000000000000006 |
| `g_sf_m` | superformula symmetry order / dimensionless / categorical | 4 | fixed 4 | fixed / fixed bound; superformula shape inactive when g_sf_amt=0 | 0 |
| `g_sf_n1` | superformula exponent 1 / dimensionless / categorical | 1.8 | fixed 1.8 | fixed / fixed bound; superformula shape inactive when g_sf_amt=0 | 0 |
| `g_sf_n2` | superformula exponent 2 / dimensionless / categorical | 7.0 | fixed 7.0 | fixed / fixed bound; superformula shape inactive when g_sf_amt=0 | 0 |
| `g_sf_start` | superformula shaping start / dimensionless / categorical | 0.25 | fixed 0.25 | fixed / fixed bound; superformula shape inactive when g_sf_amt=0 | 0 |
| `g_wrap_deg` | lip curve parameter / deg | 130.0 | 80.0 .. 160.0 | linear unit interval / searched | 16.0 |
| `generator.name` | generator construction route / dimensionless / categorical | grid | fixed grid | fixed / fixed construction input | 0 |
| `generator.rows.type` | profile or rows construction kind / dimensionless / categorical | osse_rollback | fixed osse_rollback | fixed / fixed construction input | 0 |
| `generator.n_phi` | number of azimuth samples / dimensionless / categorical | 25 | fixed 25 | fixed / fixed construction input | 0 |
| `generator.n_s` | number of curve stations / dimensionless / categorical | 40 | fixed 40 | fixed / fixed construction input | 0 |
| `generator.wall_thickness_mm` | outer wall thickness / mm | 3.0 | fixed 3.0 | fixed / fixed construction input | 0 |
| `generator.seed_policy` | config-load seed derivation policy / dimensionless / categorical | explicit | fixed explicit | fixed / fixed construction input | 0 |
| `generator.span` | modeled azimuthal span and symmetry / dimensionless / categorical | quarter | fixed quarter | fixed / fixed construction input | 0 |
| `g_wrap_cos_amp` | lip wrap azimuth modulation amplitude; inactive without ripple lobes / dimensionless / categorical | 0.0 | fixed 0.0 | fixed / resolver default; lip wrap azimuth modulation amplitude; inactive without ripple lobes | 0 |
| `g_a_fold` | wall angle azimuth fold count / dimensionless / categorical | 2.0 | fixed 2.0 | fixed / resolver default; wall angle azimuth fold count | 0 |
| `g_a_union` | enable union angle construction / dimensionless / categorical | 0.0 | fixed 0.0 | fixed / resolver default; enable union angle construction | 0 |
| `g_union_blend_deg` | union angle smoothing; inactive when union is off / deg | 0.0 | fixed 0.0 | fixed / resolver default; union angle smoothing; inactive when union is off | 0 |
| `g_ripple_lobes` | even mouth ripple lobe count; 0 disables ripple / dimensionless / categorical | 0.0 | fixed 0.0 | fixed / resolver default; even mouth ripple lobe count; 0 disables ripple | 0 |
| `g_ripple_amp_mm` | mouth ripple radial amplitude; inactive at zero lobes / mm | 0.0 | fixed 0.0 | fixed / resolver default; mouth ripple radial amplitude; inactive at zero lobes | 0 |
| `g_ripple_start` | mouth ripple window start; inactive at zero lobes / dimensionless / categorical | 0.0 | fixed 0.0 | fixed / resolver default; mouth ripple window start; inactive at zero lobes | 0 |
| `brief.driver.exit_radius_mm` | driver coupling-plane radius / mm | 18.0 | fixed 18.0 | fixed / fixed construction input | 0 |
| `brief.driver.exit_angle_deg` | driver exit wall half-angle / deg | 2.0 | fixed 2.0 | fixed / fixed construction input | 0 |

Coupled constraints:

- All resolved physical values finite; every seed present and inside its own declared domain; fixed values equal both endpoints.
- Finished inner+outer+closure envelope W<=600 mm,H<=480 mm,D<=480 mm and W>H; nominal dimensions are not the test.
- Driver connection radius18 mm; physical tangent/source-cap policy must be resolved per family, including R-OSSE and extended-throat cases.
- Reject nonpositive radius, degeneracy, nonmanifold connectivity, unintended intersections/clearance failure and invalid source cap before acoustics; preserve refusal records.
- No silent clipping onto another candidate; canonical full-boundary duplicate identity and inherited config/source/recipe/brief/mesh/solve hashes required.
- No acoustic launch under this document; separate objective, geometry, replay and validation gates apply.
- Evaluate actual OSSE+superformula+lip+outer shell extents; existing corners exceed600 mm. Reject combinations before meshing; do not shrink aH/aV merely to fit.
- Positive k,n,L; s>=0;0<q<=1; mirror-safe fixed sf_m=4; all polar angles in supported range; check lip/corner clearance and actual tangent return.
- Fixed k=1,q=.996 and superformula shape are reference restrictions. Do not claim independent loading/pucker optimization until those controls are audited; do not blindly widen them.

## hl__es_style_rollback_v7

Source `examples/typologies/home_landscape_2026-11-15/hl__es_style_rollback_v7.yaml`, SHA256 `018bd20e4ad17e26cf5c2e2af60a39184bf11d55e6f461165061ec6f5392c0e7`. Starting unit sigma `0.2`; blocked for acoustics.

| Key | Physical meaning / unit | Seed | Proposed bounds | Transform / activity | Initial physical step |
|---|---|---|---|---|---|
| `g_T` | Le Cléach march hyperbolic profile parameter T in the Iwata aspect-stretch reconstruction / dimensionless / categorical | 0.6 | 0.5 .. 0.9 | linear unit interval / searched | 0.08000000000000002 |
| `g_ar_m` | mouth aspect ratio / dimensionless / categorical | 2.0 | 1.6 .. 2.4 | linear unit interval / searched | 0.15999999999999998 |
| `g_ar_p` | aspect ratio progression exponent / dimensionless / categorical | 1.0 | 0.5 .. 2.0 | linear unit interval / searched | 0.30000000000000004 |
| `g_fc_hz` | profile cutoff parameter / Hz | 520.0 | 450.0 .. 700.0 | linear unit interval / searched | 50.0 |
| `g_stop_deg` | curve stop parameter / deg | 230.0 | 170.0 .. 240.0 | linear unit interval / searched | 14.0 |
| `generator.name` | generator construction route / dimensionless / categorical | grid | fixed grid | fixed / fixed construction input | 0 |
| `generator.rows.type` | profile or rows construction kind / dimensionless / categorical | iwata_ar | fixed iwata_ar | fixed / fixed construction input | 0 |
| `generator.n_phi` | number of azimuth samples / dimensionless / categorical | 15 | fixed 15 | fixed / fixed construction input | 0 |
| `generator.n_s` | number of curve stations / dimensionless / categorical | 32 | fixed 32 | fixed / fixed construction input | 0 |
| `generator.seed_policy` | config-load seed derivation policy / dimensionless / categorical | explicit | fixed explicit | fixed / fixed construction input | 0 |
| `generator.wall_thickness_mm` | outer wall thickness / mm | 3.0 | fixed 3.0 | fixed / fixed construction input | 0 |
| `generator.span` | stock rows default span for this kind / dimensionless / categorical | quarter | fixed quarter | fixed / fixed construction input | 0 |
| `brief.driver.exit_radius_mm` | driver coupling-plane radius / mm | 18.0 | fixed 18.0 | fixed / fixed construction input | 0 |
| `brief.driver.exit_angle_deg` | driver exit wall half-angle / deg | 2.0 | fixed 2.0 | fixed / fixed construction input | 0 |

Coupled constraints:

- All resolved physical values finite; every seed present and inside its own declared domain; fixed values equal both endpoints.
- Finished inner+outer+closure envelope W<=600 mm,H<=480 mm,D<=480 mm and W>H; nominal dimensions are not the test.
- Driver connection radius18 mm; physical tangent/source-cap policy must be resolved per family, including R-OSSE and extended-throat cases.
- Reject nonpositive radius, degeneracy, nonmanifold connectivity, unintended intersections/clearance failure and invalid source cap before acoustics; preserve refusal records.
- No silent clipping onto another candidate; canonical full-boundary duplicate identity and inherited config/source/recipe/brief/mesh/solve hashes required.
- No acoustic launch under this document; separate objective, geometry, replay and validation gates apply.
- LeCleach march validity and circular throat before aspect stretch; terminal curve coordinate is not a Crowe wrap angle. Check aspect progression+return+outer-body envelope jointly.

## hl__ext_throat_hvlaw_v7

Source `examples/typologies/home_landscape_2026-11-15/hl__ext_throat_hvlaw_v7.yaml`, SHA256 `ce3baa6fafbddd55781d82ac7ed58cb59846f924b61c70c8af1bbf4c79b7c876`. Starting unit sigma `0.2`; blocked for acoustics.

| Key | Physical meaning / unit | Seed | Proposed bounds | Transform / activity | Initial physical step |
|---|---|---|---|---|---|
| `L_mm` | axial profile length / mm | 250.0 | 180.0 .. 330.0 | linear unit interval / searched | 30.0 |
| `a0_deg` | throat wall angle / deg | 4.5 | fixed 4.5 | fixed / fixed bound; evaluated value derived from driver exit and extension, not independent: r0=exit_radius+length*tan(angle), a0=angle | 0 |
| `a_deg` | profile wall angle (interpretation depends on profile) / deg | 24.0 | 15.0 .. 40.0 | linear unit interval / searched | 5.0 |
| `aspect_ratio` | cross section aspect ratio / dimensionless / categorical | 1.0 | fixed 1.0 | fixed / fixed bound | 0 |
| `az_a_cos_amp` | azimuth wall angle cosine amplitude / deg | 14.0 | 0.0 .. 25.0 | linear unit interval / searched | 5.0 |
| `az_a_cos_pow` | azimuth angle cosine exponent / dimensionless / categorical | 2.0 | 1.0 .. 6.0 | linear unit interval / searched; inactive when az_a_cos_amp=0 | 1.0 |
| `az_a_sf_amp` | azimuth superformula wall-angle amplitude / deg | 0.0 | fixed 0.0 | fixed / fixed bound | 0 |
| `az_n_cos2_amp` | azimuth profile exponent cosine amplitude / dimensionless / categorical | 0.0 | fixed 0.0 | fixed / fixed bound | 0 |
| `az_s_cos2_amp` | azimuth termination cosine amplitude / dimensionless / categorical | 0.0 | -0.25 .. 0.5 | linear unit interval / searched | 0.15000000000000002 |
| `az_sf_a` | azimuth superformula scale a / dimensionless / categorical | 1.0 | fixed 1.0 | fixed / fixed bound; azimuth superformula affects wall only when az_a_sf_amp nonzero | 0 |
| `az_sf_b` | azimuth superformula scale b / dimensionless / categorical | 0.8569 | fixed 0.8569 | fixed / fixed bound; azimuth superformula affects wall only when az_a_sf_amp nonzero | 0 |
| `az_sf_m` | azimuth superformula symmetry order / dimensionless / categorical | 4.0 | fixed 4.0 | fixed / fixed bound; azimuth superformula affects wall only when az_a_sf_amp nonzero | 0 |
| `az_sf_n1` | azimuth superformula exponent 1 / dimensionless / categorical | 7.4958 | fixed 7.4958 | fixed / fixed bound; azimuth superformula affects wall only when az_a_sf_amp nonzero | 0 |
| `az_sf_n2` | azimuth superformula exponent 2 / dimensionless / categorical | 12.4449 | fixed 12.4449 | fixed / fixed bound; azimuth superformula affects wall only when az_a_sf_amp nonzero | 0 |
| `az_sf_n3` | azimuth superformula exponent 3 / dimensionless / categorical | 13.4442 | fixed 13.4442 | fixed / fixed bound; azimuth superformula affects wall only when az_a_sf_amp nonzero | 0 |
| `exponent` | cross section exponent / dimensionless / categorical | 2.0 | fixed 2.0 | fixed / fixed bound | 0 |
| `k` | OSSE base throat-to-wall shape factor / dimensionless / categorical | 1.0 | fixed 1.0 | fixed / fixed bound | 0 |
| `morph_allow_shrinkage` | mouth morph shrinkage flag / dimensionless / categorical | 0 | fixed 0 | fixed / fixed bound; inactive if morph_target=0 | 0 |
| `morph_corner_mm` | mouth morph corner radius / mm | 35.0 | fixed 35.0 | fixed / fixed bound; inactive if morph_target=0; corner applies to rectangular target only | 0 |
| `morph_exponent` | mouth morph exponent / dimensionless / categorical | 4.0 | fixed 4.0 | fixed / fixed bound; inactive if morph_target=0; exponent applies to superellipse target 3 only | 0 |
| `morph_fixed` | mouth morph fixed factor / dimensionless / categorical | 0.0 | fixed 0.0 | fixed / fixed bound; inactive if morph_target=0 | 0 |
| `morph_height_mm` | mouth morph target height / mm | 660.0 | fixed 660.0 | fixed / fixed bound; inactive if morph_target=0 | 0 |
| `morph_rate` | mouth morph rate / dimensionless / categorical | 4.1236 | fixed 4.1236 | fixed / fixed bound; inactive if morph_target=0 | 0 |
| `morph_target` | mouth morph target selection / dimensionless / categorical | 0 | fixed 0 | fixed / fixed bound | 0 |
| `morph_width_mm` | mouth morph target width / mm | 500.0 | fixed 500.0 | fixed / fixed bound; inactive if morph_target=0 | 0 |
| `n` | OSSE superellipse termination exponent / dimensionless / categorical | 6.0 | fixed 6.0 | fixed / fixed bound; termination term inactive when s=0 | 0 |
| `q` | OSSE normalized termination saturation / dimensionless / categorical | 0.996 | fixed 0.996 | fixed / fixed bound; termination term inactive when s=0 | 0 |
| `r0_mm` | throat radius / mm | 27.0507 | fixed 27.0507 | fixed / fixed bound; evaluated value derived from driver exit and extension, not independent: r0=exit_radius+length*tan(angle), a0=angle | 0 |
| `s` | OSSE termination amplitude / dimensionless / categorical | 0.55 | 0.3 .. 0.9 | linear unit interval / searched | 0.12000000000000002 |
| `slot_length_mm` | throat slot length / mm | 0.0 | fixed 0.0 | fixed / fixed bound | 0 |
| `throat_ext_angle_deg` | throat extension wall angle / deg | 4.5 | 1.5 .. 6.0 | linear unit interval / searched | 0.9 |
| `throat_ext_length_mm` | throat extension length / mm | 115.0 | 60.0 .. 220.0 | linear unit interval / searched | 32.0 |
| `wall_thickness_mm` | wall thickness / mm | 5.0 | fixed 5.0 | fixed / fixed bound | 0 |
| `brief.driver.exit_radius_mm` | driver coupling-plane radius / mm | 18.0 | fixed 18.0 | fixed / fixed construction input | 0 |
| `brief.driver.exit_angle_deg` | driver exit wall half-angle / deg | 2.0 | fixed 2.0 | fixed / fixed construction input | 0 |

Coupled constraints:

- All resolved physical values finite; every seed present and inside its own declared domain; fixed values equal both endpoints.
- Finished inner+outer+closure envelope W<=600 mm,H<=480 mm,D<=480 mm and W>H; nominal dimensions are not the test.
- Driver connection radius18 mm; physical tangent/source-cap policy must be resolved per family, including R-OSSE and extended-throat cases.
- Reject nonpositive radius, degeneracy, nonmanifold connectivity, unintended intersections/clearance failure and invalid source cap before acoustics; preserve refusal records.
- No silent clipping onto another candidate; canonical full-boundary duplicate identity and inherited config/source/recipe/brief/mesh/solve hashes required.
- No acoustic launch under this document; separate objective, geometry, replay and validation gates apply.
- Evaluate complete azimuth functions a(phi),n(phi),s(phi); require valid OSSE at every azimuth, round driver and quarter symmetry (superformula m multiple4 when required).
- Morph target0 makes target dimensions/rate/corner/exponent inactive; use per-law activity mapping, never count inactive dimensions as distinct physical observations.
- Derive main r0=18+extension_length*tan(extension_angle*pi/180),main a0=extension_angle. The source connection and extension entrance policy need explicit checking; these are not two additional independent knobs.

## hl__lecleach_iwata_ar_landscape_v7

Source `examples/typologies/home_landscape_2026-11-15/hl__lecleach_iwata_ar_landscape_v7.yaml`, SHA256 `6dc449200a0eb4087d66b1036d1979e41654c4d21a70857e7a21f3fb07ea5321`. Starting unit sigma `0.2`; blocked for acoustics.

| Key | Physical meaning / unit | Seed | Proposed bounds | Transform / activity | Initial physical step |
|---|---|---|---|---|---|
| `g_T` | Le Cléach march hyperbolic profile parameter T in the Iwata aspect-stretch reconstruction / dimensionless / categorical | 0.5 | fixed 0.5 | fixed / fixed bound | 0 |
| `g_ar_m` | mouth aspect ratio / dimensionless / categorical | 1.5 | 1.2 .. 2.4 | linear unit interval / searched | 0.24 |
| `g_ar_p` | aspect ratio progression exponent / dimensionless / categorical | 1.0 | 0.5 .. 2.0 | linear unit interval / searched | 0.30000000000000004 |
| `g_fc_hz` | profile cutoff parameter / Hz | 550.0 | 450.0 .. 900.0 | linear unit interval / searched | 90.0 |
| `g_stop_deg` | curve stop parameter / deg | 180.0 | 110.0 .. 200.0 | linear unit interval / searched | 18.0 |
| `generator.name` | generator construction route / dimensionless / categorical | grid | fixed grid | fixed / fixed construction input | 0 |
| `generator.rows.type` | profile or rows construction kind / dimensionless / categorical | iwata_ar | fixed iwata_ar | fixed / fixed construction input | 0 |
| `generator.n_phi` | number of azimuth samples / dimensionless / categorical | 15 | fixed 15 | fixed / fixed construction input | 0 |
| `generator.n_s` | number of curve stations / dimensionless / categorical | 32 | fixed 32 | fixed / fixed construction input | 0 |
| `generator.seed_policy` | config-load seed derivation policy / dimensionless / categorical | explicit | fixed explicit | fixed / fixed construction input | 0 |
| `generator.wall_thickness_mm` | outer wall thickness / mm | 3.0 | fixed 3.0 | fixed / fixed construction input | 0 |
| `generator.span` | stock rows default span for this kind / dimensionless / categorical | quarter | fixed quarter | fixed / fixed construction input | 0 |
| `brief.driver.exit_radius_mm` | driver coupling-plane radius / mm | 18.0 | fixed 18.0 | fixed / fixed construction input | 0 |
| `brief.driver.exit_angle_deg` | driver exit wall half-angle / deg | 2.0 | fixed 2.0 | fixed / fixed construction input | 0 |

Coupled constraints:

- All resolved physical values finite; every seed present and inside its own declared domain; fixed values equal both endpoints.
- Finished inner+outer+closure envelope W<=600 mm,H<=480 mm,D<=480 mm and W>H; nominal dimensions are not the test.
- Driver connection radius18 mm; physical tangent/source-cap policy must be resolved per family, including R-OSSE and extended-throat cases.
- Reject nonpositive radius, degeneracy, nonmanifold connectivity, unintended intersections/clearance failure and invalid source cap before acoustics; preserve refusal records.
- No silent clipping onto another candidate; canonical full-boundary duplicate identity and inherited config/source/recipe/brief/mesh/solve hashes required.
- No acoustic launch under this document; separate objective, geometry, replay and validation gates apply.
- LeCleach march validity and circular throat before aspect stretch; terminal curve coordinate is not a Crowe wrap angle. Check aspect progression+return+outer-body envelope jointly.

## hl__osse_rrect_morph_v7

Source `examples/typologies/home_landscape_2026-11-15/hl__osse_rrect_morph_v7.yaml`, SHA256 `b98fcbced85b8e23eb231216a1990c2343f05c9484fbdea2c01b7ff884de7908`. Starting unit sigma `0.2`; blocked for acoustics.

| Key | Physical meaning / unit | Seed | Proposed bounds | Transform / activity | Initial physical step |
|---|---|---|---|---|---|
| `L_mm` | axial profile length / mm | 250.0 | 160.0 .. 340.0 | linear unit interval / searched | 36.0 |
| `a0_deg` | throat wall angle / deg | 1.9863 | 1.0 .. 3.0 | linear unit interval / searched | 0.4 |
| `a_deg` | profile wall angle (interpretation depends on profile) / deg | 30.0 | 20.0 .. 40.0 | linear unit interval / searched | 4.0 |
| `aspect_ratio` | cross section aspect ratio / dimensionless / categorical | 1.0 | fixed 1.0 | fixed / fixed bound | 0 |
| `az_a_cos_amp` | azimuth wall angle cosine amplitude / deg | 8.0 | 0.0 .. 15.0 | linear unit interval / searched | 3.0 |
| `az_a_cos_pow` | azimuth angle cosine exponent / dimensionless / categorical | 2.0 | 1.0 .. 6.0 | linear unit interval / searched; inactive when az_a_cos_amp=0 | 1.0 |
| `az_a_sf_amp` | azimuth superformula wall-angle amplitude / deg | 0.0 | fixed 0.0 | fixed / fixed bound | 0 |
| `az_n_cos2_amp` | azimuth profile exponent cosine amplitude / dimensionless / categorical | 0.0 | fixed 0.0 | fixed / fixed bound | 0 |
| `az_s_cos2_amp` | azimuth termination cosine amplitude / dimensionless / categorical | 0.0 | -0.25 .. 0.5 | linear unit interval / searched | 0.15000000000000002 |
| `az_sf_a` | azimuth superformula scale a / dimensionless / categorical | 1.0 | fixed 1.0 | fixed / fixed bound; azimuth superformula affects wall only when az_a_sf_amp nonzero | 0 |
| `az_sf_b` | azimuth superformula scale b / dimensionless / categorical | 0.8569 | fixed 0.8569 | fixed / fixed bound; azimuth superformula affects wall only when az_a_sf_amp nonzero | 0 |
| `az_sf_m` | azimuth superformula symmetry order / dimensionless / categorical | 4.0 | fixed 4.0 | fixed / fixed bound; azimuth superformula affects wall only when az_a_sf_amp nonzero | 0 |
| `az_sf_n1` | azimuth superformula exponent 1 / dimensionless / categorical | 7.4958 | fixed 7.4958 | fixed / fixed bound; azimuth superformula affects wall only when az_a_sf_amp nonzero | 0 |
| `az_sf_n2` | azimuth superformula exponent 2 / dimensionless / categorical | 12.4449 | fixed 12.4449 | fixed / fixed bound; azimuth superformula affects wall only when az_a_sf_amp nonzero | 0 |
| `az_sf_n3` | azimuth superformula exponent 3 / dimensionless / categorical | 13.4442 | fixed 13.4442 | fixed / fixed bound; azimuth superformula affects wall only when az_a_sf_amp nonzero | 0 |
| `exponent` | cross section exponent / dimensionless / categorical | 2.0 | fixed 2.0 | fixed / fixed bound | 0 |
| `k` | OSSE base throat-to-wall shape factor / dimensionless / categorical | 1.2163 | 0.3 .. 3.0 | linear unit interval / searched | 0.54 |
| `morph_allow_shrinkage` | mouth morph shrinkage flag / dimensionless / categorical | 1 | fixed 1 | fixed / fixed bound; inactive if morph_target=0 | 0 |
| `morph_corner_mm` | mouth morph corner radius / mm | 60.0 | 30.0 .. 100.0 | linear unit interval / searched; inactive if morph_target=0; corner applies to rectangular target only | 14.0 |
| `morph_exponent` | mouth morph exponent / dimensionless / categorical | 4.0 | fixed 4.0 | fixed / fixed bound; inactive if morph_target=0; exponent applies to superellipse target 3 only | 0 |
| `morph_fixed` | mouth morph fixed factor / dimensionless / categorical | 0.0 | fixed 0.0 | fixed / fixed bound; inactive if morph_target=0 | 0 |
| `morph_height_mm` | mouth morph target height / mm | 380.0 | 320.0 .. 460.0 | linear unit interval / searched; inactive if morph_target=0 | 28.0 |
| `morph_rate` | mouth morph rate / dimensionless / categorical | 3.0 | 1.0 .. 6.0 | linear unit interval / searched; inactive if morph_target=0 | 1.0 |
| `morph_target` | mouth morph target selection / dimensionless / categorical | 1 | fixed 1 | fixed / fixed bound | 0 |
| `morph_width_mm` | mouth morph target width / mm | 540.0 | 480.0 .. 600.0 | linear unit interval / searched; inactive if morph_target=0 | 24.0 |
| `n` | OSSE superellipse termination exponent / dimensionless / categorical | 6.9046 | 2.0 .. 10.0 | linear unit interval / searched; termination term inactive when s=0 | 1.6 |
| `q` | OSSE normalized termination saturation / dimensionless / categorical | 0.9869 | 0.9 .. 1.0 | linear unit interval / searched; termination term inactive when s=0 | 0.019999999999999997 |
| `r0_mm` | throat radius / mm | 18.0 | fixed 18.0 | fixed / fixed bound; fresh supplied brief pins radius to driver, unless extension active; embedded replay retains saved config | 0 |
| `s` | OSSE termination amplitude / dimensionless / categorical | 0.7503 | 0.2 .. 1.2 | linear unit interval / searched | 0.2 |
| `s1` | throat stretch coefficient: x_stretched = x + s1*degrees(atan(s2*x)) / mm/deg | 1.1799 | fixed 1.1799 | fixed / fixed bound; requires both s1 and s2 nonzero | 0 |
| `s2` | throat stretch coefficient: x_stretched = x + s1*degrees(atan(s2*x)) / 1/mm | 0.0286 | fixed 0.0286 | fixed / fixed bound; requires both s1 and s2 nonzero | 0 |
| `brief.driver.exit_radius_mm` | driver coupling-plane radius / mm | 18.0 | fixed 18.0 | fixed / fixed construction input | 0 |
| `brief.driver.exit_angle_deg` | driver exit wall half-angle / deg | 2.0 | fixed 2.0 | fixed / fixed construction input | 0 |

Coupled constraints:

- All resolved physical values finite; every seed present and inside its own declared domain; fixed values equal both endpoints.
- Finished inner+outer+closure envelope W<=600 mm,H<=480 mm,D<=480 mm and W>H; nominal dimensions are not the test.
- Driver connection radius18 mm; physical tangent/source-cap policy must be resolved per family, including R-OSSE and extended-throat cases.
- Reject nonpositive radius, degeneracy, nonmanifold connectivity, unintended intersections/clearance failure and invalid source cap before acoustics; preserve refusal records.
- No silent clipping onto another candidate; canonical full-boundary duplicate identity and inherited config/source/recipe/brief/mesh/solve hashes required.
- No acoustic launch under this document; separate objective, geometry, replay and validation gates apply.
- Evaluate complete azimuth functions a(phi),n(phi),s(phi); require valid OSSE at every azimuth, round driver and quarter symmetry (superformula m multiple4 when required).
- Morph target0 makes target dimensions/rate/corner/exponent inactive; use per-law activity mapping, never count inactive dimensions as distinct physical observations.

## hl__rolled_es_spiral_v7

Source `examples/typologies/home_landscape_2026-11-15/hl__rolled_es_spiral_v7.yaml`, SHA256 `b20383bb881bdfc948f2810c35efee8ac773b79ab4cd25b94bf254f0c64a11a8`. Starting unit sigma `0.2`; blocked for acoustics.

| Key | Physical meaning / unit | Seed | Proposed bounds | Transform / activity | Initial physical step |
|---|---|---|---|---|---|
| `g_decay` | curve decay / dimensionless / categorical | 0.7 | 0.4 .. 1.0 | linear unit interval / searched | 0.12 |
| `g_depth_h_ratio` | horizontal/vertical depth ratio / dimensionless / categorical | 0.68 | 0.55 .. 1.0 | linear unit interval / searched | 0.09 |
| `g_depth_mm` | nominal depth / mm | 238.0 | 200.0 .. 380.0 | linear unit interval / searched | 36.0 |
| `g_height_mm` | nominal height / mm | 299.0 | 260.0 .. 420.0 | linear unit interval / searched | 32.0 |
| `g_pucker_h_mm` | horizontal pucker amplitude / mm | 6.0 | 0.0 .. 18.0 | linear unit interval / searched | 3.6 |
| `g_pucker_start_deg` | pucker start turn / deg | 55.0 | fixed 55.0 | fixed / fixed bound | 0 |
| `g_pucker_v_mm` | vertical pucker amplitude / mm | 8.0 | 0.0 .. 24.0 | linear unit interval / searched | 4.800000000000001 |
| `g_rect_exponent` | rectangular outline exponent / dimensionless / categorical | 12.0 | 4.0 .. 14.0 | linear unit interval / searched | 2.0 |
| `g_rect_turn_deg` | rectangle onset turn / deg | 65.0 | 45.0 .. 85.0 | linear unit interval / searched | 8.0 |
| `g_terminal_deg` | terminal curve turn / deg | 270.0 | 200.0 .. 275.0 | linear unit interval / searched | 15.0 |
| `g_throat_turn_deg` | throat transition turn / deg | 25.0 | fixed 25.0 | fixed / fixed bound | 0 |
| `g_width_mm` | nominal width / mm | 542.0 | 480.0 .. 590.0 | linear unit interval / searched | 22.0 |
| `generator.name` | generator construction route / dimensionless / categorical | grid | fixed grid | fixed / fixed construction input | 0 |
| `generator.rows.type` | profile or rows construction kind / dimensionless / categorical | rolled_rect_pucker | fixed rolled_rect_pucker | fixed / fixed construction input | 0 |
| `generator.seed_policy` | config-load seed derivation policy / dimensionless / categorical | explicit | fixed explicit | fixed / fixed construction input | 0 |
| `generator.span` | modeled azimuthal span and symmetry / dimensionless / categorical | quarter | fixed quarter | fixed / fixed construction input | 0 |
| `generator.n_phi` | number of azimuth samples / dimensionless / categorical | 49 | fixed 49 | fixed / fixed construction input | 0 |
| `generator.n_s` | number of curve stations / dimensionless / categorical | 96 | fixed 96 | fixed / fixed construction input | 0 |
| `generator.wall_thickness_mm` | outer wall thickness / mm | 3.0 | fixed 3.0 | fixed / fixed construction input | 0 |
| `brief.driver.exit_radius_mm` | driver coupling-plane radius / mm | 18.0 | fixed 18.0 | fixed / fixed construction input | 0 |
| `brief.driver.exit_angle_deg` | driver exit wall half-angle / deg | 2.0 | fixed 2.0 | fixed / fixed construction input | 0 |

Coupled constraints:

- All resolved physical values finite; every seed present and inside its own declared domain; fixed values equal both endpoints.
- Finished inner+outer+closure envelope W<=600 mm,H<=480 mm,D<=480 mm and W>H; nominal dimensions are not the test.
- Driver connection radius18 mm; physical tangent/source-cap policy must be resolved per family, including R-OSSE and extended-throat cases.
- Reject nonpositive radius, degeneracy, nonmanifold connectivity, unintended intersections/clearance failure and invalid source cap before acoustics; preserve refusal records.
- No silent clipping onto another candidate; canonical full-boundary duplicate identity and inherited config/source/recipe/brief/mesh/solve hashes required.
- No acoustic launch under this document; separate objective, geometry, replay and validation gates apply.
- width>height>36;0<throat_turn<rect_turn<90 degrees;180<terminal<=280 degrees;0.5<=depth_h_ratio<=1.2;2<=rect_exponent<=16;decay>0.
- Original axial law only: throat_turn<pucker_start<180 degrees and max(abs(H),abs(V))<=0.15*depth. No replacement with ATH radial morph.
- Shared normalized spiral law lacks separate H/V flare-rate/angle controls; box retained for CPU hypothesis study, not broad coverage optimization.

## hl__rosse_rect_cd_v7

Source `examples/typologies/home_landscape_2026-11-15/hl__rosse_rect_cd_v7.yaml`, SHA256 `ab9129c35fc53ac7414792952839db0b408f5574c51b39abe02d46305c24e938`. Starting unit sigma `0.2`; blocked for acoustics.

| Key | Physical meaning / unit | Seed | Proposed bounds | Transform / activity | Initial physical step |
|---|---|---|---|---|---|
| `g_a_diag_deg` | diagonal angular shaping / deg | 0.0 | fixed 0.0 | fixed / fixed bound | 0 |
| `g_a_h_deg` | horizontal wall half-angle / deg | 40.0 | 32.0 .. 46.0 | linear unit interval / searched | 2.8000000000000003 |
| `g_a_v_deg` | vertical wall half-angle / deg | 25.0 | 18.0 .. 30.0 | linear unit interval / searched | 2.4000000000000004 |
| `g_b` | R-OSSE secondary quadratic axial-map weight / dimensionless / categorical | 0.2 | 0.0 .. 0.4 | linear unit interval / searched; secondary axial term vanishes at zero | 0.08000000000000002 |
| `g_height_mm` | nominal height / mm | 360.0 | 280.0 .. 420.0 | linear unit interval / searched | 28.0 |
| `g_k` | R-OSSE throat radius-curve shape factor / dimensionless / categorical | 1.0 | 0.8 .. 3.0 | linear unit interval / searched | 0.44000000000000006 |
| `g_m` | R-OSSE dimensionless axial-map shoulder / dimensionless / categorical | 0.85 | fixed 0.85 | fixed / fixed bound | 0 |
| `g_q` | R-OSSE throat-to-mouth radius blend exponent / dimensionless / categorical | 3.0 | fixed 3.0 | fixed / fixed bound | 0 |
| `g_r` | R-OSSE dimensionless axial-map rounding parameter, not physical radius / dimensionless / categorical | 0.4 | 0.25 .. 0.6 | linear unit interval / searched | 0.06999999999999999 |
| `g_rect_exponent` | rectangular outline exponent / dimensionless / categorical | 4.0 | 2.5 .. 8.0 | linear unit interval / searched | 1.1 |
| `g_tmax` | R-OSSE terminal parametric coordinate / dimensionless / categorical | 1.0 | 0.85 .. 1.0 | linear unit interval / searched | 0.030000000000000006 |
| `g_width_mm` | nominal width / mm | 560.0 | 480.0 .. 590.0 | linear unit interval / searched | 22.0 |
| `generator.name` | generator construction route / dimensionless / categorical | grid | fixed grid | fixed / fixed construction input | 0 |
| `generator.rows.type` | profile or rows construction kind / dimensionless / categorical | rosse_rect | fixed rosse_rect | fixed / fixed construction input | 0 |
| `generator.n_phi` | number of azimuth samples / dimensionless / categorical | 25 | fixed 25 | fixed / fixed construction input | 0 |
| `generator.n_s` | number of curve stations / dimensionless / categorical | 48 | fixed 48 | fixed / fixed construction input | 0 |
| `generator.wall_thickness_mm` | outer wall thickness / mm | 3.0 | fixed 3.0 | fixed / fixed construction input | 0 |
| `generator.seed_policy` | config-load seed derivation policy / dimensionless / categorical | explicit | fixed explicit | fixed / fixed construction input | 0 |
| `generator.span` | modeled azimuthal span and symmetry / dimensionless / categorical | quarter | fixed quarter | fixed / fixed construction input | 0 |
| `brief.driver.exit_radius_mm` | driver coupling-plane radius / mm | 18.0 | fixed 18.0 | fixed / fixed construction input | 0 |
| `brief.driver.exit_angle_deg` | driver exit wall half-angle / deg | 2.0 | fixed 2.0 | fixed / fixed construction input | 0 |

Coupled constraints:

- All resolved physical values finite; every seed present and inside its own declared domain; fixed values equal both endpoints.
- Finished inner+outer+closure envelope W<=600 mm,H<=480 mm,D<=480 mm and W>H; nominal dimensions are not the test.
- Driver connection radius18 mm; physical tangent/source-cap policy must be resolved per family, including R-OSSE and extended-throat cases.
- Reject nonpositive radius, degeneracy, nonmanifold connectivity, unintended intersections/clearance failure and invalid source cap before acoustics; preserve refusal records.
- No silent clipping onto another candidate; canonical full-boundary duplicate identity and inherited config/source/recipe/brief/mesh/solve hashes required.
- No acoustic launch under this document; separate objective, geometry, replay and validation gates apply.
- R(phi)=(|cos(phi)/(W/2)|**p+|sin(phi)/(H/2)|**p)**(-1/p), a(phi)=aV+(aH-aV)*cos(phi)**2+aDiag*sin(2*phi)**2.
- Use actual R-OSSE domain at EVERY azimuth; fixed r0=18 mm; r and m are dimensionless; depth and terminal radius follow parametric law+tmax, not W/H labels alone.
- Resolve physical tangent: for unstretched q>1,k>0, initial dr/dz=tan(a0)*sqrt(r*r+m*m)/m. Raw a0=driver2deg does not guarantee2deg spatial tangent.
- Current m=.85,q=3,aDiag=0 are a reference slice, not evidence they should remain fixed in final optimization. Their future domains need source/domain/control experiments.

## rf__rect_axial_v7

Source `examples/typologies/rolled_family_2026-11-15/rf__rect_axial_v7.yaml`, SHA256 `36836a07b4e311e0014eb8b42784d7d9fbd2917a3b9c33eaae17f8bf31eecd40`. Starting unit sigma `0.15`; blocked for acoustics.

| Key | Physical meaning / unit | Seed | Proposed bounds | Transform / activity | Initial physical step |
|---|---|---|---|---|---|
| `g_axial_h_mm` | horizontal signed axial relief amplitude / mm | 3.0 | -5.0 .. 5.0 | linear unit interval / searched; mode axial; neutral zero if inactive | 1.5 |
| `g_axial_v_mm` | vertical signed axial relief amplitude / mm | 4.0 | -5.0 .. 5.0 | linear unit interval / searched; mode axial; neutral zero if inactive | 1.5 |
| `g_decay` | curve decay / dimensionless / categorical | 0.7 | 0.65 .. 0.75 | linear unit interval / searched | 0.014999999999999996 |
| `g_depth_h_ratio` | horizontal/vertical depth ratio / dimensionless / categorical | 0.68 | fixed 0.68 | fixed / fixed bound | 0 |
| `g_depth_mm` | nominal depth / mm | 238.0 | 230.0 .. 246.0 | linear unit interval / searched | 2.4 |
| `g_height_mm` | nominal height / mm | 299.0 | fixed 299.0 | fixed / fixed bound | 0 |
| `g_inward_h_mm` | horizontal radial inward relief amplitude / mm | 0.0 | fixed 0.0 | fixed / fixed bound; mode axial; neutral zero if inactive | 0 |
| `g_inward_v_mm` | vertical radial inward relief amplitude / mm | 0.0 | fixed 0.0 | fixed / fixed bound; mode axial; neutral zero if inactive | 0 |
| `g_rect_exponent` | rectangular outline exponent / dimensionless / categorical | 12.0 | 10.0 .. 14.0 | linear unit interval / searched | 0.6 |
| `g_rect_turn_deg` | rectangle onset turn / deg | 65.0 | fixed 65.0 | fixed / fixed bound | 0 |
| `g_relief_end_s` | relief window end in normalized station / dimensionless / categorical | 0.96 | fixed 0.96 | fixed / fixed bound | 0 |
| `g_relief_peak_s` | relief window peak in normalized station / dimensionless / categorical | 0.8 | fixed 0.8 | fixed / fixed bound | 0 |
| `g_relief_start_s` | relief window start in normalized station / dimensionless / categorical | 0.5 | fixed 0.5 | fixed / fixed bound | 0 |
| `g_terminal_deg` | terminal curve turn / deg | 270.0 | fixed 270.0 | fixed / fixed bound | 0 |
| `g_throat_turn_deg` | throat transition turn / deg | 25.0 | fixed 25.0 | fixed / fixed bound | 0 |
| `g_width_mm` | nominal width / mm | 542.0 | fixed 542.0 | fixed / fixed bound | 0 |
| `generator.name` | generator construction route / dimensionless / categorical | grid | fixed grid | fixed / fixed construction input | 0 |
| `generator.rows.type` | profile or rows construction kind / dimensionless / categorical | rolled_family_rect_v1 | fixed rolled_family_rect_v1 | fixed / fixed construction input | 0 |
| `generator.rows.mode` | native rolled-family relief mode / dimensionless / categorical | axial | fixed axial | fixed / fixed construction input | 0 |
| `generator.seed_policy` | config-load seed derivation policy / dimensionless / categorical | explicit | fixed explicit | fixed / fixed construction input | 0 |
| `generator.span` | modeled azimuthal span and symmetry / dimensionless / categorical | quarter | fixed quarter | fixed / fixed construction input | 0 |
| `generator.n_phi` | number of azimuth samples / dimensionless / categorical | 65 | fixed 65 | fixed / fixed construction input | 0 |
| `generator.n_s` | number of curve stations / dimensionless / categorical | 128 | fixed 128 | fixed / fixed construction input | 0 |
| `generator.wall_thickness_mm` | outer wall thickness / mm | 3.0 | fixed 3.0 | fixed / fixed construction input | 0 |
| `brief.driver.exit_radius_mm` | driver coupling-plane radius / mm | 18.0 | fixed 18.0 | fixed / fixed construction input | 0 |
| `brief.driver.exit_angle_deg` | driver exit wall half-angle / deg | 2.0 | fixed 2.0 | fixed / fixed construction input | 0 |

Coupled constraints:

- All resolved physical values finite; every seed present and inside its own declared domain; fixed values equal both endpoints.
- Finished inner+outer+closure envelope W<=600 mm,H<=480 mm,D<=480 mm and W>H; nominal dimensions are not the test.
- Driver connection radius18 mm; physical tangent/source-cap policy must be resolved per family, including R-OSSE and extended-throat cases.
- Reject nonpositive radius, degeneracy, nonmanifold connectivity, unintended intersections/clearance failure and invalid source cap before acoustics; preserve refusal records.
- No silent clipping onto another candidate; canonical full-boundary duplicate identity and inherited config/source/recipe/brief/mesh/solve hashes required.
- No acoustic launch under this document; separate objective, geometry, replay and validation gates apply.
- width>height>36;0<throat_turn<rect_turn<90 degrees;180<terminal<=280 degrees;0.5<=depth_h_ratio<=1.2;2<=rect_exponent<=16;decay>0.
- Original axial law only: throat_turn<pucker_start<180 degrees and max(abs(H),abs(V))<=0.15*depth. No replacement with ATH radial morph.
- Shared normalized spiral law lacks separate H/V flare-rate/angle controls; box retained for CPU hypothesis study, not broad coverage optimization.
- Inactive axial/radial controls exactly0; start_hi<peak_lo<end_lo and window starts after source neighbourhood; end before final2 grid stations.
- With active amplitude domains including0, keep window placement fixed for this matched amplitude experiment. This is an identifiability rule, not proof placement never matters.
- Positive rho-relief, no pre-roll radial constriction, nondegenerate inner+outer sheets and native self-approach guard. Reference arc station is not axial-depth fraction.

## rf__rect_control_v7

Source `examples/typologies/rolled_family_2026-11-15/rf__rect_control_v7.yaml`, SHA256 `f814f6884067f558d2205a2f953844c939c4012a0997d62d15ea2c6aff5e55cf`. Starting unit sigma `0.15`; blocked for acoustics.

| Key | Physical meaning / unit | Seed | Proposed bounds | Transform / activity | Initial physical step |
|---|---|---|---|---|---|
| `g_axial_h_mm` | horizontal signed axial relief amplitude / mm | 0.0 | fixed 0.0 | fixed / fixed bound; mode smooth; neutral zero if inactive | 0 |
| `g_axial_v_mm` | vertical signed axial relief amplitude / mm | 0.0 | fixed 0.0 | fixed / fixed bound; mode smooth; neutral zero if inactive | 0 |
| `g_decay` | curve decay / dimensionless / categorical | 0.7 | 0.65 .. 0.75 | linear unit interval / searched | 0.014999999999999996 |
| `g_depth_h_ratio` | horizontal/vertical depth ratio / dimensionless / categorical | 0.68 | fixed 0.68 | fixed / fixed bound | 0 |
| `g_depth_mm` | nominal depth / mm | 238.0 | 230.0 .. 246.0 | linear unit interval / searched | 2.4 |
| `g_height_mm` | nominal height / mm | 299.0 | fixed 299.0 | fixed / fixed bound | 0 |
| `g_inward_h_mm` | horizontal radial inward relief amplitude / mm | 0.0 | fixed 0.0 | fixed / fixed bound; mode smooth; neutral zero if inactive | 0 |
| `g_inward_v_mm` | vertical radial inward relief amplitude / mm | 0.0 | fixed 0.0 | fixed / fixed bound; mode smooth; neutral zero if inactive | 0 |
| `g_rect_exponent` | rectangular outline exponent / dimensionless / categorical | 12.0 | 10.0 .. 14.0 | linear unit interval / searched | 0.6 |
| `g_rect_turn_deg` | rectangle onset turn / deg | 65.0 | fixed 65.0 | fixed / fixed bound | 0 |
| `g_relief_end_s` | relief window end in normalized station / dimensionless / categorical | 0.96 | fixed 0.96 | fixed / fixed bound | 0 |
| `g_relief_peak_s` | relief window peak in normalized station / dimensionless / categorical | 0.8 | fixed 0.8 | fixed / fixed bound | 0 |
| `g_relief_start_s` | relief window start in normalized station / dimensionless / categorical | 0.5 | fixed 0.5 | fixed / fixed bound | 0 |
| `g_terminal_deg` | terminal curve turn / deg | 270.0 | fixed 270.0 | fixed / fixed bound | 0 |
| `g_throat_turn_deg` | throat transition turn / deg | 25.0 | fixed 25.0 | fixed / fixed bound | 0 |
| `g_width_mm` | nominal width / mm | 542.0 | fixed 542.0 | fixed / fixed bound | 0 |
| `generator.name` | generator construction route / dimensionless / categorical | grid | fixed grid | fixed / fixed construction input | 0 |
| `generator.rows.type` | profile or rows construction kind / dimensionless / categorical | rolled_family_rect_v1 | fixed rolled_family_rect_v1 | fixed / fixed construction input | 0 |
| `generator.rows.mode` | native rolled-family relief mode / dimensionless / categorical | smooth | fixed smooth | fixed / fixed construction input | 0 |
| `generator.seed_policy` | config-load seed derivation policy / dimensionless / categorical | explicit | fixed explicit | fixed / fixed construction input | 0 |
| `generator.span` | modeled azimuthal span and symmetry / dimensionless / categorical | quarter | fixed quarter | fixed / fixed construction input | 0 |
| `generator.n_phi` | number of azimuth samples / dimensionless / categorical | 65 | fixed 65 | fixed / fixed construction input | 0 |
| `generator.n_s` | number of curve stations / dimensionless / categorical | 128 | fixed 128 | fixed / fixed construction input | 0 |
| `generator.wall_thickness_mm` | outer wall thickness / mm | 3.0 | fixed 3.0 | fixed / fixed construction input | 0 |
| `brief.driver.exit_radius_mm` | driver coupling-plane radius / mm | 18.0 | fixed 18.0 | fixed / fixed construction input | 0 |
| `brief.driver.exit_angle_deg` | driver exit wall half-angle / deg | 2.0 | fixed 2.0 | fixed / fixed construction input | 0 |

Coupled constraints:

- All resolved physical values finite; every seed present and inside its own declared domain; fixed values equal both endpoints.
- Finished inner+outer+closure envelope W<=600 mm,H<=480 mm,D<=480 mm and W>H; nominal dimensions are not the test.
- Driver connection radius18 mm; physical tangent/source-cap policy must be resolved per family, including R-OSSE and extended-throat cases.
- Reject nonpositive radius, degeneracy, nonmanifold connectivity, unintended intersections/clearance failure and invalid source cap before acoustics; preserve refusal records.
- No silent clipping onto another candidate; canonical full-boundary duplicate identity and inherited config/source/recipe/brief/mesh/solve hashes required.
- No acoustic launch under this document; separate objective, geometry, replay and validation gates apply.
- width>height>36;0<throat_turn<rect_turn<90 degrees;180<terminal<=280 degrees;0.5<=depth_h_ratio<=1.2;2<=rect_exponent<=16;decay>0.
- Original axial law only: throat_turn<pucker_start<180 degrees and max(abs(H),abs(V))<=0.15*depth. No replacement with ATH radial morph.
- Shared normalized spiral law lacks separate H/V flare-rate/angle controls; box retained for CPU hypothesis study, not broad coverage optimization.
- Inactive axial/radial controls exactly0; start_hi<peak_lo<end_lo and window starts after source neighbourhood; end before final2 grid stations.
- With active amplitude domains including0, keep window placement fixed for this matched amplitude experiment. This is an identifiability rule, not proof placement never matters.
- Positive rho-relief, no pre-roll radial constriction, nondegenerate inner+outer sheets and native self-approach guard. Reference arc station is not axial-depth fraction.

## rf__rect_radial_strong_v7

Source `examples/typologies/rolled_family_2026-11-15/rf__rect_radial_strong_v7.yaml`, SHA256 `0fb31ef73693dd0673fd12782c3807f30aa6c0276ac6448aa3a6efe89d4f52f2`. Starting unit sigma `0.15`; blocked for acoustics.

| Key | Physical meaning / unit | Seed | Proposed bounds | Transform / activity | Initial physical step |
|---|---|---|---|---|---|
| `g_axial_h_mm` | horizontal signed axial relief amplitude / mm | 0.0 | fixed 0.0 | fixed / fixed bound; mode radial; neutral zero if inactive | 0 |
| `g_axial_v_mm` | vertical signed axial relief amplitude / mm | 0.0 | fixed 0.0 | fixed / fixed bound; mode radial; neutral zero if inactive | 0 |
| `g_decay` | curve decay / dimensionless / categorical | 0.7 | 0.65 .. 0.75 | linear unit interval / searched | 0.014999999999999996 |
| `g_depth_h_ratio` | horizontal/vertical depth ratio / dimensionless / categorical | 0.68 | fixed 0.68 | fixed / fixed bound | 0 |
| `g_depth_mm` | nominal depth / mm | 238.0 | 230.0 .. 246.0 | linear unit interval / searched | 2.4 |
| `g_height_mm` | nominal height / mm | 299.0 | fixed 299.0 | fixed / fixed bound | 0 |
| `g_inward_h_mm` | horizontal radial inward relief amplitude / mm | 6.0 | 4.0 .. 8.0 | linear unit interval / searched; mode radial; neutral zero if inactive | 0.6 |
| `g_inward_v_mm` | vertical radial inward relief amplitude / mm | 8.0 | 6.0 .. 10.0 | linear unit interval / searched; mode radial; neutral zero if inactive | 0.6 |
| `g_rect_exponent` | rectangular outline exponent / dimensionless / categorical | 12.0 | 10.0 .. 14.0 | linear unit interval / searched | 0.6 |
| `g_rect_turn_deg` | rectangle onset turn / deg | 65.0 | fixed 65.0 | fixed / fixed bound | 0 |
| `g_relief_end_s` | relief window end in normalized station / dimensionless / categorical | 0.96 | fixed 0.96 | fixed / fixed bound | 0 |
| `g_relief_peak_s` | relief window peak in normalized station / dimensionless / categorical | 0.8 | fixed 0.8 | fixed / fixed bound | 0 |
| `g_relief_start_s` | relief window start in normalized station / dimensionless / categorical | 0.5 | fixed 0.5 | fixed / fixed bound | 0 |
| `g_terminal_deg` | terminal curve turn / deg | 270.0 | fixed 270.0 | fixed / fixed bound | 0 |
| `g_throat_turn_deg` | throat transition turn / deg | 25.0 | fixed 25.0 | fixed / fixed bound | 0 |
| `g_width_mm` | nominal width / mm | 542.0 | fixed 542.0 | fixed / fixed bound | 0 |
| `generator.name` | generator construction route / dimensionless / categorical | grid | fixed grid | fixed / fixed construction input | 0 |
| `generator.rows.type` | profile or rows construction kind / dimensionless / categorical | rolled_family_rect_v1 | fixed rolled_family_rect_v1 | fixed / fixed construction input | 0 |
| `generator.rows.mode` | native rolled-family relief mode / dimensionless / categorical | radial | fixed radial | fixed / fixed construction input | 0 |
| `generator.seed_policy` | config-load seed derivation policy / dimensionless / categorical | explicit | fixed explicit | fixed / fixed construction input | 0 |
| `generator.span` | modeled azimuthal span and symmetry / dimensionless / categorical | quarter | fixed quarter | fixed / fixed construction input | 0 |
| `generator.n_phi` | number of azimuth samples / dimensionless / categorical | 65 | fixed 65 | fixed / fixed construction input | 0 |
| `generator.n_s` | number of curve stations / dimensionless / categorical | 128 | fixed 128 | fixed / fixed construction input | 0 |
| `generator.wall_thickness_mm` | outer wall thickness / mm | 3.0 | fixed 3.0 | fixed / fixed construction input | 0 |
| `brief.driver.exit_radius_mm` | driver coupling-plane radius / mm | 18.0 | fixed 18.0 | fixed / fixed construction input | 0 |
| `brief.driver.exit_angle_deg` | driver exit wall half-angle / deg | 2.0 | fixed 2.0 | fixed / fixed construction input | 0 |

Coupled constraints:

- All resolved physical values finite; every seed present and inside its own declared domain; fixed values equal both endpoints.
- Finished inner+outer+closure envelope W<=600 mm,H<=480 mm,D<=480 mm and W>H; nominal dimensions are not the test.
- Driver connection radius18 mm; physical tangent/source-cap policy must be resolved per family, including R-OSSE and extended-throat cases.
- Reject nonpositive radius, degeneracy, nonmanifold connectivity, unintended intersections/clearance failure and invalid source cap before acoustics; preserve refusal records.
- No silent clipping onto another candidate; canonical full-boundary duplicate identity and inherited config/source/recipe/brief/mesh/solve hashes required.
- No acoustic launch under this document; separate objective, geometry, replay and validation gates apply.
- width>height>36;0<throat_turn<rect_turn<90 degrees;180<terminal<=280 degrees;0.5<=depth_h_ratio<=1.2;2<=rect_exponent<=16;decay>0.
- Original axial law only: throat_turn<pucker_start<180 degrees and max(abs(H),abs(V))<=0.15*depth. No replacement with ATH radial morph.
- Shared normalized spiral law lacks separate H/V flare-rate/angle controls; box retained for CPU hypothesis study, not broad coverage optimization.
- Inactive axial/radial controls exactly0; start_hi<peak_lo<end_lo and window starts after source neighbourhood; end before final2 grid stations.
- With active amplitude domains including0, keep window placement fixed for this matched amplitude experiment. This is an identifiability rule, not proof placement never matters.
- Positive rho-relief, no pre-roll radial constriction, nondegenerate inner+outer sheets and native self-approach guard. Reference arc station is not axial-depth fraction.

## rf__rect_radial_v7

Source `examples/typologies/rolled_family_2026-11-15/rf__rect_radial_v7.yaml`, SHA256 `4a69670fa63e10bdaa298b701217e177474e551f1b565cd25f206eff784ec623`. Starting unit sigma `0.15`; blocked for acoustics.

| Key | Physical meaning / unit | Seed | Proposed bounds | Transform / activity | Initial physical step |
|---|---|---|---|---|---|
| `g_axial_h_mm` | horizontal signed axial relief amplitude / mm | 0.0 | fixed 0.0 | fixed / fixed bound; mode radial; neutral zero if inactive | 0 |
| `g_axial_v_mm` | vertical signed axial relief amplitude / mm | 0.0 | fixed 0.0 | fixed / fixed bound; mode radial; neutral zero if inactive | 0 |
| `g_decay` | curve decay / dimensionless / categorical | 0.7 | 0.65 .. 0.75 | linear unit interval / searched | 0.014999999999999996 |
| `g_depth_h_ratio` | horizontal/vertical depth ratio / dimensionless / categorical | 0.68 | fixed 0.68 | fixed / fixed bound | 0 |
| `g_depth_mm` | nominal depth / mm | 238.0 | 230.0 .. 246.0 | linear unit interval / searched | 2.4 |
| `g_height_mm` | nominal height / mm | 299.0 | fixed 299.0 | fixed / fixed bound | 0 |
| `g_inward_h_mm` | horizontal radial inward relief amplitude / mm | 3.0 | 0.0 .. 6.0 | linear unit interval / searched; mode radial; neutral zero if inactive | 0.8999999999999999 |
| `g_inward_v_mm` | vertical radial inward relief amplitude / mm | 4.0 | 0.0 .. 8.0 | linear unit interval / searched; mode radial; neutral zero if inactive | 1.2 |
| `g_rect_exponent` | rectangular outline exponent / dimensionless / categorical | 12.0 | 10.0 .. 14.0 | linear unit interval / searched | 0.6 |
| `g_rect_turn_deg` | rectangle onset turn / deg | 65.0 | fixed 65.0 | fixed / fixed bound | 0 |
| `g_relief_end_s` | relief window end in normalized station / dimensionless / categorical | 0.96 | fixed 0.96 | fixed / fixed bound | 0 |
| `g_relief_peak_s` | relief window peak in normalized station / dimensionless / categorical | 0.8 | fixed 0.8 | fixed / fixed bound | 0 |
| `g_relief_start_s` | relief window start in normalized station / dimensionless / categorical | 0.5 | fixed 0.5 | fixed / fixed bound | 0 |
| `g_terminal_deg` | terminal curve turn / deg | 270.0 | fixed 270.0 | fixed / fixed bound | 0 |
| `g_throat_turn_deg` | throat transition turn / deg | 25.0 | fixed 25.0 | fixed / fixed bound | 0 |
| `g_width_mm` | nominal width / mm | 542.0 | fixed 542.0 | fixed / fixed bound | 0 |
| `generator.name` | generator construction route / dimensionless / categorical | grid | fixed grid | fixed / fixed construction input | 0 |
| `generator.rows.type` | profile or rows construction kind / dimensionless / categorical | rolled_family_rect_v1 | fixed rolled_family_rect_v1 | fixed / fixed construction input | 0 |
| `generator.rows.mode` | native rolled-family relief mode / dimensionless / categorical | radial | fixed radial | fixed / fixed construction input | 0 |
| `generator.seed_policy` | config-load seed derivation policy / dimensionless / categorical | explicit | fixed explicit | fixed / fixed construction input | 0 |
| `generator.span` | modeled azimuthal span and symmetry / dimensionless / categorical | quarter | fixed quarter | fixed / fixed construction input | 0 |
| `generator.n_phi` | number of azimuth samples / dimensionless / categorical | 65 | fixed 65 | fixed / fixed construction input | 0 |
| `generator.n_s` | number of curve stations / dimensionless / categorical | 128 | fixed 128 | fixed / fixed construction input | 0 |
| `generator.wall_thickness_mm` | outer wall thickness / mm | 3.0 | fixed 3.0 | fixed / fixed construction input | 0 |
| `brief.driver.exit_radius_mm` | driver coupling-plane radius / mm | 18.0 | fixed 18.0 | fixed / fixed construction input | 0 |
| `brief.driver.exit_angle_deg` | driver exit wall half-angle / deg | 2.0 | fixed 2.0 | fixed / fixed construction input | 0 |

Coupled constraints:

- All resolved physical values finite; every seed present and inside its own declared domain; fixed values equal both endpoints.
- Finished inner+outer+closure envelope W<=600 mm,H<=480 mm,D<=480 mm and W>H; nominal dimensions are not the test.
- Driver connection radius18 mm; physical tangent/source-cap policy must be resolved per family, including R-OSSE and extended-throat cases.
- Reject nonpositive radius, degeneracy, nonmanifold connectivity, unintended intersections/clearance failure and invalid source cap before acoustics; preserve refusal records.
- No silent clipping onto another candidate; canonical full-boundary duplicate identity and inherited config/source/recipe/brief/mesh/solve hashes required.
- No acoustic launch under this document; separate objective, geometry, replay and validation gates apply.
- width>height>36;0<throat_turn<rect_turn<90 degrees;180<terminal<=280 degrees;0.5<=depth_h_ratio<=1.2;2<=rect_exponent<=16;decay>0.
- Original axial law only: throat_turn<pucker_start<180 degrees and max(abs(H),abs(V))<=0.15*depth. No replacement with ATH radial morph.
- Shared normalized spiral law lacks separate H/V flare-rate/angle controls; box retained for CPU hypothesis study, not broad coverage optimization.
- Inactive axial/radial controls exactly0; start_hi<peak_lo<end_lo and window starts after source neighbourhood; end before final2 grid stations.
- With active amplitude domains including0, keep window placement fixed for this matched amplitude experiment. This is an identifiability rule, not proof placement never matters.
- Positive rho-relief, no pre-roll radial constriction, nondegenerate inner+outer sheets and native self-approach guard. Reference arc station is not axial-depth fraction.

## rf__section_axial_v7

Source `examples/typologies/rolled_family_2026-11-15/rf__section_axial_v7.yaml`, SHA256 `37187af0671b038fa81e233b7cc00745fa6fa075d6e40809a3f2f28d8c5db0b4`. Starting unit sigma `0.15`; blocked for acoustics.

| Key | Physical meaning / unit | Seed | Proposed bounds | Transform / activity | Initial physical step |
|---|---|---|---|---|---|
| `g_axial_h_mm` | horizontal signed axial relief amplitude / mm | 3.0 | -5.0 .. 5.0 | linear unit interval / searched; mode axial; neutral zero if inactive | 1.5 |
| `g_axial_v_mm` | vertical signed axial relief amplitude / mm | 4.0 | -5.0 .. 5.0 | linear unit interval / searched; mode axial; neutral zero if inactive | 1.5 |
| `g_crown_mm` | section crown / mm | 20.0 | 18.0 .. 22.0 | linear unit interval / searched | 0.6 |
| `g_depth_mm` | nominal depth / mm | 198.0 | 194.0 .. 202.0 | linear unit interval / searched | 1.2 |
| `g_h_depth_scale` | horizontal section depth scale relative to reference vertical section / dimensionless / categorical | 1.0 | 0.99 .. 1.01 | linear unit interval / searched | 0.0030000000000000027 |
| `g_height_mm` | nominal height / mm | 203.0 | fixed 203.0 | fixed / fixed bound | 0 |
| `g_inward_h_mm` | horizontal radial inward relief amplitude / mm | 0.0 | fixed 0.0 | fixed / fixed bound; mode axial; neutral zero if inactive | 0 |
| `g_inward_v_mm` | vertical radial inward relief amplitude / mm | 0.0 | fixed 0.0 | fixed / fixed bound; mode axial; neutral zero if inactive | 0 |
| `g_junction_power` | section junction exponent / dimensionless / categorical | 32.0 | fixed 32.0 | fixed / fixed bound | 0 |
| `g_relief_end_s` | relief window end in normalized station / dimensionless / categorical | 0.96 | fixed 0.96 | fixed / fixed bound | 0 |
| `g_relief_peak_s` | relief window peak in normalized station / dimensionless / categorical | 0.8 | fixed 0.8 | fixed / fixed bound | 0 |
| `g_relief_start_s` | relief window start in normalized station / dimensionless / categorical | 0.3 | fixed 0.3 | fixed / fixed bound | 0 |
| `g_throat_blend_mm` | throat blend length / mm | 20.0 | fixed 20.0 | fixed / fixed bound | 0 |
| `g_width_mm` | nominal width / mm | 417.0 | fixed 417.0 | fixed / fixed bound | 0 |
| `generator.name` | generator construction route / dimensionless / categorical | grid | fixed grid | fixed / fixed construction input | 0 |
| `generator.rows.type` | profile or rows construction kind / dimensionless / categorical | rolled_family_section_v1 | fixed rolled_family_section_v1 | fixed / fixed construction input | 0 |
| `generator.rows.mode` | native rolled-family relief mode / dimensionless / categorical | axial | fixed axial | fixed / fixed construction input | 0 |
| `generator.seed_policy` | config-load seed derivation policy / dimensionless / categorical | explicit | fixed explicit | fixed / fixed construction input | 0 |
| `generator.span` | modeled azimuthal span and symmetry / dimensionless / categorical | quarter | fixed quarter | fixed / fixed construction input | 0 |
| `generator.n_phi` | number of azimuth samples / dimensionless / categorical | 65 | fixed 65 | fixed / fixed construction input | 0 |
| `generator.n_s` | number of curve stations / dimensionless / categorical | 128 | fixed 128 | fixed / fixed construction input | 0 |
| `generator.wall_thickness_mm` | outer wall thickness / mm | 3.0 | fixed 3.0 | fixed / fixed construction input | 0 |
| `brief.driver.exit_radius_mm` | driver coupling-plane radius / mm | 18.0 | fixed 18.0 | fixed / fixed construction input | 0 |
| `brief.driver.exit_angle_deg` | driver exit wall half-angle / deg | 2.0 | fixed 2.0 | fixed / fixed construction input | 0 |

Coupled constraints:

- All resolved physical values finite; every seed present and inside its own declared domain; fixed values equal both endpoints.
- Finished inner+outer+closure envelope W<=600 mm,H<=480 mm,D<=480 mm and W>H; nominal dimensions are not the test.
- Driver connection radius18 mm; physical tangent/source-cap policy must be resolved per family, including R-OSSE and extended-throat cases.
- Reject nonpositive radius, degeneracy, nonmanifold connectivity, unintended intersections/clearance failure and invalid source cap before acoustics; preserve refusal records.
- No silent clipping onto another candidate; canonical full-boundary duplicate identity and inherited config/source/recipe/brief/mesh/solve hashes required.
- No acoustic launch under this document; separate objective, geometry, replay and validation gates apply.
- 0.9<=h_depth_scale<=1.1; 0<=crown<0.2*height;16<=junction_power<=48;0<throat_blend<0.2*depth.
- Use actual _sweep tests: max(zH)<max(zV),positive pivot,single-peaked sweep radius,compatible return domains,real radicand and source blend after inverse exists. Do not substitute empirical depth<=0.57*width for these exact tests.
- Outer return/closure needs off-axis tangent,intersection and clearance audit; consistent winding alone is insufficient.
- Inactive axial/radial controls exactly0; start_hi<peak_lo<end_lo and window starts after source neighbourhood; end before final2 grid stations.
- With active amplitude domains including0, keep window placement fixed for this matched amplitude experiment. This is an identifiability rule, not proof placement never matters.
- Positive rho-relief, no pre-roll radial constriction, nondegenerate inner+outer sheets and native self-approach guard. Reference arc station is not axial-depth fraction.

## rf__section_control_v7

Source `examples/typologies/rolled_family_2026-11-15/rf__section_control_v7.yaml`, SHA256 `edf9f99279a50f7b940153b4c17aab6e4761de2626fa5d10d798a85d3d25bb41`. Starting unit sigma `0.15`; blocked for acoustics.

| Key | Physical meaning / unit | Seed | Proposed bounds | Transform / activity | Initial physical step |
|---|---|---|---|---|---|
| `g_axial_h_mm` | horizontal signed axial relief amplitude / mm | 0.0 | fixed 0.0 | fixed / fixed bound; mode smooth; neutral zero if inactive | 0 |
| `g_axial_v_mm` | vertical signed axial relief amplitude / mm | 0.0 | fixed 0.0 | fixed / fixed bound; mode smooth; neutral zero if inactive | 0 |
| `g_crown_mm` | section crown / mm | 20.0 | 18.0 .. 22.0 | linear unit interval / searched | 0.6 |
| `g_depth_mm` | nominal depth / mm | 198.0 | 194.0 .. 202.0 | linear unit interval / searched | 1.2 |
| `g_h_depth_scale` | horizontal section depth scale relative to reference vertical section / dimensionless / categorical | 1.0 | 0.99 .. 1.01 | linear unit interval / searched | 0.0030000000000000027 |
| `g_height_mm` | nominal height / mm | 203.0 | fixed 203.0 | fixed / fixed bound | 0 |
| `g_inward_h_mm` | horizontal radial inward relief amplitude / mm | 0.0 | fixed 0.0 | fixed / fixed bound; mode smooth; neutral zero if inactive | 0 |
| `g_inward_v_mm` | vertical radial inward relief amplitude / mm | 0.0 | fixed 0.0 | fixed / fixed bound; mode smooth; neutral zero if inactive | 0 |
| `g_junction_power` | section junction exponent / dimensionless / categorical | 32.0 | fixed 32.0 | fixed / fixed bound | 0 |
| `g_relief_end_s` | relief window end in normalized station / dimensionless / categorical | 0.96 | fixed 0.96 | fixed / fixed bound | 0 |
| `g_relief_peak_s` | relief window peak in normalized station / dimensionless / categorical | 0.8 | fixed 0.8 | fixed / fixed bound | 0 |
| `g_relief_start_s` | relief window start in normalized station / dimensionless / categorical | 0.3 | fixed 0.3 | fixed / fixed bound | 0 |
| `g_throat_blend_mm` | throat blend length / mm | 20.0 | fixed 20.0 | fixed / fixed bound | 0 |
| `g_width_mm` | nominal width / mm | 417.0 | fixed 417.0 | fixed / fixed bound | 0 |
| `generator.name` | generator construction route / dimensionless / categorical | grid | fixed grid | fixed / fixed construction input | 0 |
| `generator.rows.type` | profile or rows construction kind / dimensionless / categorical | rolled_family_section_v1 | fixed rolled_family_section_v1 | fixed / fixed construction input | 0 |
| `generator.rows.mode` | native rolled-family relief mode / dimensionless / categorical | smooth | fixed smooth | fixed / fixed construction input | 0 |
| `generator.seed_policy` | config-load seed derivation policy / dimensionless / categorical | explicit | fixed explicit | fixed / fixed construction input | 0 |
| `generator.span` | modeled azimuthal span and symmetry / dimensionless / categorical | quarter | fixed quarter | fixed / fixed construction input | 0 |
| `generator.n_phi` | number of azimuth samples / dimensionless / categorical | 65 | fixed 65 | fixed / fixed construction input | 0 |
| `generator.n_s` | number of curve stations / dimensionless / categorical | 128 | fixed 128 | fixed / fixed construction input | 0 |
| `generator.wall_thickness_mm` | outer wall thickness / mm | 3.0 | fixed 3.0 | fixed / fixed construction input | 0 |
| `brief.driver.exit_radius_mm` | driver coupling-plane radius / mm | 18.0 | fixed 18.0 | fixed / fixed construction input | 0 |
| `brief.driver.exit_angle_deg` | driver exit wall half-angle / deg | 2.0 | fixed 2.0 | fixed / fixed construction input | 0 |

Coupled constraints:

- All resolved physical values finite; every seed present and inside its own declared domain; fixed values equal both endpoints.
- Finished inner+outer+closure envelope W<=600 mm,H<=480 mm,D<=480 mm and W>H; nominal dimensions are not the test.
- Driver connection radius18 mm; physical tangent/source-cap policy must be resolved per family, including R-OSSE and extended-throat cases.
- Reject nonpositive radius, degeneracy, nonmanifold connectivity, unintended intersections/clearance failure and invalid source cap before acoustics; preserve refusal records.
- No silent clipping onto another candidate; canonical full-boundary duplicate identity and inherited config/source/recipe/brief/mesh/solve hashes required.
- No acoustic launch under this document; separate objective, geometry, replay and validation gates apply.
- 0.9<=h_depth_scale<=1.1; 0<=crown<0.2*height;16<=junction_power<=48;0<throat_blend<0.2*depth.
- Use actual _sweep tests: max(zH)<max(zV),positive pivot,single-peaked sweep radius,compatible return domains,real radicand and source blend after inverse exists. Do not substitute empirical depth<=0.57*width for these exact tests.
- Outer return/closure needs off-axis tangent,intersection and clearance audit; consistent winding alone is insufficient.
- Inactive axial/radial controls exactly0; start_hi<peak_lo<end_lo and window starts after source neighbourhood; end before final2 grid stations.
- With active amplitude domains including0, keep window placement fixed for this matched amplitude experiment. This is an identifiability rule, not proof placement never matters.
- Positive rho-relief, no pre-roll radial constriction, nondegenerate inner+outer sheets and native self-approach guard. Reference arc station is not axial-depth fraction.

## rf__section_radial_strong_v7

Source `examples/typologies/rolled_family_2026-11-15/rf__section_radial_strong_v7.yaml`, SHA256 `37d2fc21b97cc482cbcbd60728785ca7b465763d2ac1f65171dc86679f6513c9`. Starting unit sigma `0.15`; blocked for acoustics.

| Key | Physical meaning / unit | Seed | Proposed bounds | Transform / activity | Initial physical step |
|---|---|---|---|---|---|
| `g_axial_h_mm` | horizontal signed axial relief amplitude / mm | 0.0 | fixed 0.0 | fixed / fixed bound; mode radial; neutral zero if inactive | 0 |
| `g_axial_v_mm` | vertical signed axial relief amplitude / mm | 0.0 | fixed 0.0 | fixed / fixed bound; mode radial; neutral zero if inactive | 0 |
| `g_crown_mm` | section crown / mm | 20.0 | 18.0 .. 22.0 | linear unit interval / searched | 0.6 |
| `g_depth_mm` | nominal depth / mm | 198.0 | 194.0 .. 202.0 | linear unit interval / searched | 1.2 |
| `g_h_depth_scale` | horizontal section depth scale relative to reference vertical section / dimensionless / categorical | 1.0 | 0.99 .. 1.01 | linear unit interval / searched | 0.0030000000000000027 |
| `g_height_mm` | nominal height / mm | 203.0 | fixed 203.0 | fixed / fixed bound | 0 |
| `g_inward_h_mm` | horizontal radial inward relief amplitude / mm | 6.0 | 4.0 .. 8.0 | linear unit interval / searched; mode radial; neutral zero if inactive | 0.6 |
| `g_inward_v_mm` | vertical radial inward relief amplitude / mm | 8.0 | 6.0 .. 10.0 | linear unit interval / searched; mode radial; neutral zero if inactive | 0.6 |
| `g_junction_power` | section junction exponent / dimensionless / categorical | 32.0 | fixed 32.0 | fixed / fixed bound | 0 |
| `g_relief_end_s` | relief window end in normalized station / dimensionless / categorical | 0.96 | fixed 0.96 | fixed / fixed bound | 0 |
| `g_relief_peak_s` | relief window peak in normalized station / dimensionless / categorical | 0.8 | fixed 0.8 | fixed / fixed bound | 0 |
| `g_relief_start_s` | relief window start in normalized station / dimensionless / categorical | 0.3 | fixed 0.3 | fixed / fixed bound | 0 |
| `g_throat_blend_mm` | throat blend length / mm | 20.0 | fixed 20.0 | fixed / fixed bound | 0 |
| `g_width_mm` | nominal width / mm | 417.0 | fixed 417.0 | fixed / fixed bound | 0 |
| `generator.name` | generator construction route / dimensionless / categorical | grid | fixed grid | fixed / fixed construction input | 0 |
| `generator.rows.type` | profile or rows construction kind / dimensionless / categorical | rolled_family_section_v1 | fixed rolled_family_section_v1 | fixed / fixed construction input | 0 |
| `generator.rows.mode` | native rolled-family relief mode / dimensionless / categorical | radial | fixed radial | fixed / fixed construction input | 0 |
| `generator.seed_policy` | config-load seed derivation policy / dimensionless / categorical | explicit | fixed explicit | fixed / fixed construction input | 0 |
| `generator.span` | modeled azimuthal span and symmetry / dimensionless / categorical | quarter | fixed quarter | fixed / fixed construction input | 0 |
| `generator.n_phi` | number of azimuth samples / dimensionless / categorical | 65 | fixed 65 | fixed / fixed construction input | 0 |
| `generator.n_s` | number of curve stations / dimensionless / categorical | 128 | fixed 128 | fixed / fixed construction input | 0 |
| `generator.wall_thickness_mm` | outer wall thickness / mm | 3.0 | fixed 3.0 | fixed / fixed construction input | 0 |
| `brief.driver.exit_radius_mm` | driver coupling-plane radius / mm | 18.0 | fixed 18.0 | fixed / fixed construction input | 0 |
| `brief.driver.exit_angle_deg` | driver exit wall half-angle / deg | 2.0 | fixed 2.0 | fixed / fixed construction input | 0 |

Coupled constraints:

- All resolved physical values finite; every seed present and inside its own declared domain; fixed values equal both endpoints.
- Finished inner+outer+closure envelope W<=600 mm,H<=480 mm,D<=480 mm and W>H; nominal dimensions are not the test.
- Driver connection radius18 mm; physical tangent/source-cap policy must be resolved per family, including R-OSSE and extended-throat cases.
- Reject nonpositive radius, degeneracy, nonmanifold connectivity, unintended intersections/clearance failure and invalid source cap before acoustics; preserve refusal records.
- No silent clipping onto another candidate; canonical full-boundary duplicate identity and inherited config/source/recipe/brief/mesh/solve hashes required.
- No acoustic launch under this document; separate objective, geometry, replay and validation gates apply.
- 0.9<=h_depth_scale<=1.1; 0<=crown<0.2*height;16<=junction_power<=48;0<throat_blend<0.2*depth.
- Use actual _sweep tests: max(zH)<max(zV),positive pivot,single-peaked sweep radius,compatible return domains,real radicand and source blend after inverse exists. Do not substitute empirical depth<=0.57*width for these exact tests.
- Outer return/closure needs off-axis tangent,intersection and clearance audit; consistent winding alone is insufficient.
- Inactive axial/radial controls exactly0; start_hi<peak_lo<end_lo and window starts after source neighbourhood; end before final2 grid stations.
- With active amplitude domains including0, keep window placement fixed for this matched amplitude experiment. This is an identifiability rule, not proof placement never matters.
- Positive rho-relief, no pre-roll radial constriction, nondegenerate inner+outer sheets and native self-approach guard. Reference arc station is not axial-depth fraction.

## rf__section_radial_v7

Source `examples/typologies/rolled_family_2026-11-15/rf__section_radial_v7.yaml`, SHA256 `3c5108ae6cce802bb658b25fc07beec4fe8484cf02861e9f7ceb7500adaf33b6`. Starting unit sigma `0.15`; blocked for acoustics.

| Key | Physical meaning / unit | Seed | Proposed bounds | Transform / activity | Initial physical step |
|---|---|---|---|---|---|
| `g_axial_h_mm` | horizontal signed axial relief amplitude / mm | 0.0 | fixed 0.0 | fixed / fixed bound; mode radial; neutral zero if inactive | 0 |
| `g_axial_v_mm` | vertical signed axial relief amplitude / mm | 0.0 | fixed 0.0 | fixed / fixed bound; mode radial; neutral zero if inactive | 0 |
| `g_crown_mm` | section crown / mm | 20.0 | 18.0 .. 22.0 | linear unit interval / searched | 0.6 |
| `g_depth_mm` | nominal depth / mm | 198.0 | 194.0 .. 202.0 | linear unit interval / searched | 1.2 |
| `g_h_depth_scale` | horizontal section depth scale relative to reference vertical section / dimensionless / categorical | 1.0 | 0.99 .. 1.01 | linear unit interval / searched | 0.0030000000000000027 |
| `g_height_mm` | nominal height / mm | 203.0 | fixed 203.0 | fixed / fixed bound | 0 |
| `g_inward_h_mm` | horizontal radial inward relief amplitude / mm | 3.0 | 0.0 .. 6.0 | linear unit interval / searched; mode radial; neutral zero if inactive | 0.8999999999999999 |
| `g_inward_v_mm` | vertical radial inward relief amplitude / mm | 4.0 | 0.0 .. 8.0 | linear unit interval / searched; mode radial; neutral zero if inactive | 1.2 |
| `g_junction_power` | section junction exponent / dimensionless / categorical | 32.0 | fixed 32.0 | fixed / fixed bound | 0 |
| `g_relief_end_s` | relief window end in normalized station / dimensionless / categorical | 0.96 | fixed 0.96 | fixed / fixed bound | 0 |
| `g_relief_peak_s` | relief window peak in normalized station / dimensionless / categorical | 0.8 | fixed 0.8 | fixed / fixed bound | 0 |
| `g_relief_start_s` | relief window start in normalized station / dimensionless / categorical | 0.3 | fixed 0.3 | fixed / fixed bound | 0 |
| `g_throat_blend_mm` | throat blend length / mm | 20.0 | fixed 20.0 | fixed / fixed bound | 0 |
| `g_width_mm` | nominal width / mm | 417.0 | fixed 417.0 | fixed / fixed bound | 0 |
| `generator.name` | generator construction route / dimensionless / categorical | grid | fixed grid | fixed / fixed construction input | 0 |
| `generator.rows.type` | profile or rows construction kind / dimensionless / categorical | rolled_family_section_v1 | fixed rolled_family_section_v1 | fixed / fixed construction input | 0 |
| `generator.rows.mode` | native rolled-family relief mode / dimensionless / categorical | radial | fixed radial | fixed / fixed construction input | 0 |
| `generator.seed_policy` | config-load seed derivation policy / dimensionless / categorical | explicit | fixed explicit | fixed / fixed construction input | 0 |
| `generator.span` | modeled azimuthal span and symmetry / dimensionless / categorical | quarter | fixed quarter | fixed / fixed construction input | 0 |
| `generator.n_phi` | number of azimuth samples / dimensionless / categorical | 65 | fixed 65 | fixed / fixed construction input | 0 |
| `generator.n_s` | number of curve stations / dimensionless / categorical | 128 | fixed 128 | fixed / fixed construction input | 0 |
| `generator.wall_thickness_mm` | outer wall thickness / mm | 3.0 | fixed 3.0 | fixed / fixed construction input | 0 |
| `brief.driver.exit_radius_mm` | driver coupling-plane radius / mm | 18.0 | fixed 18.0 | fixed / fixed construction input | 0 |
| `brief.driver.exit_angle_deg` | driver exit wall half-angle / deg | 2.0 | fixed 2.0 | fixed / fixed construction input | 0 |

Coupled constraints:

- All resolved physical values finite; every seed present and inside its own declared domain; fixed values equal both endpoints.
- Finished inner+outer+closure envelope W<=600 mm,H<=480 mm,D<=480 mm and W>H; nominal dimensions are not the test.
- Driver connection radius18 mm; physical tangent/source-cap policy must be resolved per family, including R-OSSE and extended-throat cases.
- Reject nonpositive radius, degeneracy, nonmanifold connectivity, unintended intersections/clearance failure and invalid source cap before acoustics; preserve refusal records.
- No silent clipping onto another candidate; canonical full-boundary duplicate identity and inherited config/source/recipe/brief/mesh/solve hashes required.
- No acoustic launch under this document; separate objective, geometry, replay and validation gates apply.
- 0.9<=h_depth_scale<=1.1; 0<=crown<0.2*height;16<=junction_power<=48;0<throat_blend<0.2*depth.
- Use actual _sweep tests: max(zH)<max(zV),positive pivot,single-peaked sweep radius,compatible return domains,real radicand and source blend after inverse exists. Do not substitute empirical depth<=0.57*width for these exact tests.
- Outer return/closure needs off-axis tangent,intersection and clearance audit; consistent winding alone is insufficient.
- Inactive axial/radial controls exactly0; start_hi<peak_lo<end_lo and window starts after source neighbourhood; end before final2 grid stations.
- With active amplitude domains including0, keep window placement fixed for this matched amplitude experiment. This is an identifiability rule, not proof placement never matters.
- Positive rho-relief, no pre-roll radial constriction, nondegenerate inner+outer sheets and native self-approach guard. Reference arc station is not axial-depth fraction.

## rr__crowe_panel_es600_v7

Source `examples/typologies/rolled_rect_2026-11-15/rr__crowe_panel_es600_v7.yaml`, SHA256 `55a5a822bd8a4af950e71d3a9be47f095ccbbf3a39613216fbe41ddbc2b062e4`. Starting unit sigma `0.15`; blocked for acoustics.

| Key | Physical meaning / unit | Seed | Proposed bounds | Transform / activity | Initial physical step |
|---|---|---|---|---|---|
| `g_crown_mm` | section crown / mm | 20.0 | 16.0 .. 24.0 | linear unit interval / searched | 1.2 |
| `g_depth_mm` | nominal depth / mm | 198.0 | 190.0 .. 206.0 | linear unit interval / searched | 2.4 |
| `g_h_depth_scale` | horizontal section depth scale relative to reference vertical section / dimensionless / categorical | 1.0 | 0.97 .. 1.03 | linear unit interval / searched | 0.009000000000000008 |
| `g_height_mm` | nominal height / mm | 203.0 | fixed 203.0 | fixed / fixed bound | 0 |
| `g_junction_power` | section junction exponent / dimensionless / categorical | 32.0 | fixed 32.0 | fixed / fixed bound | 0 |
| `g_throat_blend_mm` | throat blend length / mm | 20.0 | fixed 20.0 | fixed / fixed bound | 0 |
| `g_width_mm` | nominal width / mm | 417.0 | fixed 417.0 | fixed / fixed bound | 0 |
| `generator.name` | generator construction route / dimensionless / categorical | grid | fixed grid | fixed / fixed construction input | 0 |
| `generator.rows.type` | profile or rows construction kind / dimensionless / categorical | crowe_panel | fixed crowe_panel | fixed / fixed construction input | 0 |
| `generator.seed_policy` | config-load seed derivation policy / dimensionless / categorical | explicit | fixed explicit | fixed / fixed construction input | 0 |
| `generator.span` | modeled azimuthal span and symmetry / dimensionless / categorical | quarter | fixed quarter | fixed / fixed construction input | 0 |
| `generator.n_phi` | number of azimuth samples / dimensionless / categorical | 49 | fixed 49 | fixed / fixed construction input | 0 |
| `generator.n_s` | number of curve stations / dimensionless / categorical | 96 | fixed 96 | fixed / fixed construction input | 0 |
| `generator.wall_thickness_mm` | outer wall thickness / mm | 3.0 | fixed 3.0 | fixed / fixed construction input | 0 |
| `brief.driver.exit_radius_mm` | driver coupling-plane radius / mm | 18.0 | fixed 18.0 | fixed / fixed construction input | 0 |
| `brief.driver.exit_angle_deg` | driver exit wall half-angle / deg | 2.0 | fixed 2.0 | fixed / fixed construction input | 0 |

Coupled constraints:

- All resolved physical values finite; every seed present and inside its own declared domain; fixed values equal both endpoints.
- Finished inner+outer+closure envelope W<=600 mm,H<=480 mm,D<=480 mm and W>H; nominal dimensions are not the test.
- Driver connection radius18 mm; physical tangent/source-cap policy must be resolved per family, including R-OSSE and extended-throat cases.
- Reject nonpositive radius, degeneracy, nonmanifold connectivity, unintended intersections/clearance failure and invalid source cap before acoustics; preserve refusal records.
- No silent clipping onto another candidate; canonical full-boundary duplicate identity and inherited config/source/recipe/brief/mesh/solve hashes required.
- No acoustic launch under this document; separate objective, geometry, replay and validation gates apply.
- 0.9<=h_depth_scale<=1.1; 0<=crown<0.2*height;16<=junction_power<=48;0<throat_blend<0.2*depth.
- Use actual _sweep tests: max(zH)<max(zV),positive pivot,single-peaked sweep radius,compatible return domains,real radicand and source blend after inverse exists. Do not substitute empirical depth<=0.57*width for these exact tests.
- Outer return/closure needs off-axis tangent,intersection and clearance audit; consistent winding alone is insufficient.

## rr__pucker_hv_moderate_v7

Source `examples/typologies/rolled_rect_2026-11-15/rr__pucker_hv_moderate_v7.yaml`, SHA256 `3d826b631a5d42b637e3ea6721dff154a649714d1b0fe5dfae48a6fdfc7498f5`. Starting unit sigma `0.15`; blocked for acoustics.

| Key | Physical meaning / unit | Seed | Proposed bounds | Transform / activity | Initial physical step |
|---|---|---|---|---|---|
| `g_decay` | curve decay / dimensionless / categorical | 0.7 | 0.55 .. 0.85 | linear unit interval / searched | 0.04499999999999999 |
| `g_depth_h_ratio` | horizontal/vertical depth ratio / dimensionless / categorical | 0.68 | fixed 0.68 | fixed / fixed bound | 0 |
| `g_depth_mm` | nominal depth / mm | 238.0 | 220.0 .. 265.0 | linear unit interval / searched | 6.75 |
| `g_height_mm` | nominal height / mm | 299.0 | fixed 299.0 | fixed / fixed bound | 0 |
| `g_pucker_h_mm` | horizontal pucker amplitude / mm | 12.0 | fixed 12.0 | fixed / fixed bound | 0 |
| `g_pucker_start_deg` | pucker start turn / deg | 55.0 | fixed 55.0 | fixed / fixed bound | 0 |
| `g_pucker_v_mm` | vertical pucker amplitude / mm | 16.0 | fixed 16.0 | fixed / fixed bound | 0 |
| `g_rect_exponent` | rectangular outline exponent / dimensionless / categorical | 12.0 | 8.0 .. 16.0 | linear unit interval / searched | 1.2 |
| `g_rect_turn_deg` | rectangle onset turn / deg | 65.0 | fixed 65.0 | fixed / fixed bound | 0 |
| `g_terminal_deg` | terminal curve turn / deg | 270.0 | fixed 270.0 | fixed / fixed bound | 0 |
| `g_throat_turn_deg` | throat transition turn / deg | 25.0 | fixed 25.0 | fixed / fixed bound | 0 |
| `g_width_mm` | nominal width / mm | 542.0 | fixed 542.0 | fixed / fixed bound | 0 |
| `generator.name` | generator construction route / dimensionless / categorical | grid | fixed grid | fixed / fixed construction input | 0 |
| `generator.rows.type` | profile or rows construction kind / dimensionless / categorical | rolled_rect_pucker | fixed rolled_rect_pucker | fixed / fixed construction input | 0 |
| `generator.seed_policy` | config-load seed derivation policy / dimensionless / categorical | explicit | fixed explicit | fixed / fixed construction input | 0 |
| `generator.span` | modeled azimuthal span and symmetry / dimensionless / categorical | quarter | fixed quarter | fixed / fixed construction input | 0 |
| `generator.n_phi` | number of azimuth samples / dimensionless / categorical | 49 | fixed 49 | fixed / fixed construction input | 0 |
| `generator.n_s` | number of curve stations / dimensionless / categorical | 96 | fixed 96 | fixed / fixed construction input | 0 |
| `generator.wall_thickness_mm` | outer wall thickness / mm | 3.0 | fixed 3.0 | fixed / fixed construction input | 0 |
| `brief.driver.exit_radius_mm` | driver coupling-plane radius / mm | 18.0 | fixed 18.0 | fixed / fixed construction input | 0 |
| `brief.driver.exit_angle_deg` | driver exit wall half-angle / deg | 2.0 | fixed 2.0 | fixed / fixed construction input | 0 |

Coupled constraints:

- All resolved physical values finite; every seed present and inside its own declared domain; fixed values equal both endpoints.
- Finished inner+outer+closure envelope W<=600 mm,H<=480 mm,D<=480 mm and W>H; nominal dimensions are not the test.
- Driver connection radius18 mm; physical tangent/source-cap policy must be resolved per family, including R-OSSE and extended-throat cases.
- Reject nonpositive radius, degeneracy, nonmanifold connectivity, unintended intersections/clearance failure and invalid source cap before acoustics; preserve refusal records.
- No silent clipping onto another candidate; canonical full-boundary duplicate identity and inherited config/source/recipe/brief/mesh/solve hashes required.
- No acoustic launch under this document; separate objective, geometry, replay and validation gates apply.
- width>height>36;0<throat_turn<rect_turn<90 degrees;180<terminal<=280 degrees;0.5<=depth_h_ratio<=1.2;2<=rect_exponent<=16;decay>0.
- Original axial law only: throat_turn<pucker_start<180 degrees and max(abs(H),abs(V))<=0.15*depth. No replacement with ATH radial morph.
- Shared normalized spiral law lacks separate H/V flare-rate/angle controls; box retained for CPU hypothesis study, not broad coverage optimization.

## rr__pucker_hv_strong_v7

Source `examples/typologies/rolled_rect_2026-11-15/rr__pucker_hv_strong_v7.yaml`, SHA256 `4ee548128f79c868faa527c2743af1754ac4fb74808d0eaf4f7beac05fe287ce`. Starting unit sigma `0.15`; blocked for acoustics.

| Key | Physical meaning / unit | Seed | Proposed bounds | Transform / activity | Initial physical step |
|---|---|---|---|---|---|
| `g_decay` | curve decay / dimensionless / categorical | 0.7 | 0.55 .. 0.85 | linear unit interval / searched | 0.04499999999999999 |
| `g_depth_h_ratio` | horizontal/vertical depth ratio / dimensionless / categorical | 0.68 | fixed 0.68 | fixed / fixed bound | 0 |
| `g_depth_mm` | nominal depth / mm | 238.0 | 220.0 .. 265.0 | linear unit interval / searched | 6.75 |
| `g_height_mm` | nominal height / mm | 299.0 | fixed 299.0 | fixed / fixed bound | 0 |
| `g_pucker_h_mm` | horizontal pucker amplitude / mm | 24.0 | fixed 24.0 | fixed / fixed bound | 0 |
| `g_pucker_start_deg` | pucker start turn / deg | 55.0 | fixed 55.0 | fixed / fixed bound | 0 |
| `g_pucker_v_mm` | vertical pucker amplitude / mm | 28.0 | fixed 28.0 | fixed / fixed bound | 0 |
| `g_rect_exponent` | rectangular outline exponent / dimensionless / categorical | 12.0 | 8.0 .. 16.0 | linear unit interval / searched | 1.2 |
| `g_rect_turn_deg` | rectangle onset turn / deg | 65.0 | fixed 65.0 | fixed / fixed bound | 0 |
| `g_terminal_deg` | terminal curve turn / deg | 270.0 | fixed 270.0 | fixed / fixed bound | 0 |
| `g_throat_turn_deg` | throat transition turn / deg | 25.0 | fixed 25.0 | fixed / fixed bound | 0 |
| `g_width_mm` | nominal width / mm | 542.0 | fixed 542.0 | fixed / fixed bound | 0 |
| `generator.name` | generator construction route / dimensionless / categorical | grid | fixed grid | fixed / fixed construction input | 0 |
| `generator.rows.type` | profile or rows construction kind / dimensionless / categorical | rolled_rect_pucker | fixed rolled_rect_pucker | fixed / fixed construction input | 0 |
| `generator.seed_policy` | config-load seed derivation policy / dimensionless / categorical | explicit | fixed explicit | fixed / fixed construction input | 0 |
| `generator.span` | modeled azimuthal span and symmetry / dimensionless / categorical | quarter | fixed quarter | fixed / fixed construction input | 0 |
| `generator.n_phi` | number of azimuth samples / dimensionless / categorical | 49 | fixed 49 | fixed / fixed construction input | 0 |
| `generator.n_s` | number of curve stations / dimensionless / categorical | 96 | fixed 96 | fixed / fixed construction input | 0 |
| `generator.wall_thickness_mm` | outer wall thickness / mm | 3.0 | fixed 3.0 | fixed / fixed construction input | 0 |
| `brief.driver.exit_radius_mm` | driver coupling-plane radius / mm | 18.0 | fixed 18.0 | fixed / fixed construction input | 0 |
| `brief.driver.exit_angle_deg` | driver exit wall half-angle / deg | 2.0 | fixed 2.0 | fixed / fixed construction input | 0 |

Coupled constraints:

- All resolved physical values finite; every seed present and inside its own declared domain; fixed values equal both endpoints.
- Finished inner+outer+closure envelope W<=600 mm,H<=480 mm,D<=480 mm and W>H; nominal dimensions are not the test.
- Driver connection radius18 mm; physical tangent/source-cap policy must be resolved per family, including R-OSSE and extended-throat cases.
- Reject nonpositive radius, degeneracy, nonmanifold connectivity, unintended intersections/clearance failure and invalid source cap before acoustics; preserve refusal records.
- No silent clipping onto another candidate; canonical full-boundary duplicate identity and inherited config/source/recipe/brief/mesh/solve hashes required.
- No acoustic launch under this document; separate objective, geometry, replay and validation gates apply.
- width>height>36;0<throat_turn<rect_turn<90 degrees;180<terminal<=280 degrees;0.5<=depth_h_ratio<=1.2;2<=rect_exponent<=16;decay>0.
- Original axial law only: throat_turn<pucker_start<180 degrees and max(abs(H),abs(V))<=0.15*depth. No replacement with ATH radial morph.
- Shared normalized spiral law lacks separate H/V flare-rate/angle controls; box retained for CPU hypothesis study, not broad coverage optimization.

## rr__reference_v7

Source `examples/typologies/rolled_rect_2026-11-15/rr__reference_v7.yaml`, SHA256 `12ec9ebd6d5af1ee8e0340432adbc251efb2dd5e458bb55a0471eaf4dbd8ea24`. Starting unit sigma `0.15`; blocked for acoustics.

| Key | Physical meaning / unit | Seed | Proposed bounds | Transform / activity | Initial physical step |
|---|---|---|---|---|---|
| `g_decay` | curve decay / dimensionless / categorical | 0.7 | 0.55 .. 0.85 | linear unit interval / searched | 0.04499999999999999 |
| `g_depth_h_ratio` | horizontal/vertical depth ratio / dimensionless / categorical | 0.68 | fixed 0.68 | fixed / fixed bound | 0 |
| `g_depth_mm` | nominal depth / mm | 238.0 | 220.0 .. 265.0 | linear unit interval / searched | 6.75 |
| `g_height_mm` | nominal height / mm | 299.0 | fixed 299.0 | fixed / fixed bound | 0 |
| `g_pucker_h_mm` | horizontal pucker amplitude / mm | 0.0 | fixed 0.0 | fixed / fixed bound | 0 |
| `g_pucker_start_deg` | pucker start turn / deg | 55.0 | fixed 55.0 | fixed / fixed bound | 0 |
| `g_pucker_v_mm` | vertical pucker amplitude / mm | 0.0 | fixed 0.0 | fixed / fixed bound | 0 |
| `g_rect_exponent` | rectangular outline exponent / dimensionless / categorical | 12.0 | 8.0 .. 16.0 | linear unit interval / searched | 1.2 |
| `g_rect_turn_deg` | rectangle onset turn / deg | 65.0 | fixed 65.0 | fixed / fixed bound | 0 |
| `g_terminal_deg` | terminal curve turn / deg | 270.0 | fixed 270.0 | fixed / fixed bound | 0 |
| `g_throat_turn_deg` | throat transition turn / deg | 25.0 | fixed 25.0 | fixed / fixed bound | 0 |
| `g_width_mm` | nominal width / mm | 542.0 | fixed 542.0 | fixed / fixed bound | 0 |
| `generator.name` | generator construction route / dimensionless / categorical | grid | fixed grid | fixed / fixed construction input | 0 |
| `generator.rows.type` | profile or rows construction kind / dimensionless / categorical | rolled_rect | fixed rolled_rect | fixed / fixed construction input | 0 |
| `generator.seed_policy` | config-load seed derivation policy / dimensionless / categorical | explicit | fixed explicit | fixed / fixed construction input | 0 |
| `generator.span` | modeled azimuthal span and symmetry / dimensionless / categorical | quarter | fixed quarter | fixed / fixed construction input | 0 |
| `generator.n_phi` | number of azimuth samples / dimensionless / categorical | 49 | fixed 49 | fixed / fixed construction input | 0 |
| `generator.n_s` | number of curve stations / dimensionless / categorical | 96 | fixed 96 | fixed / fixed construction input | 0 |
| `generator.wall_thickness_mm` | outer wall thickness / mm | 3.0 | fixed 3.0 | fixed / fixed construction input | 0 |
| `brief.driver.exit_radius_mm` | driver coupling-plane radius / mm | 18.0 | fixed 18.0 | fixed / fixed construction input | 0 |
| `brief.driver.exit_angle_deg` | driver exit wall half-angle / deg | 2.0 | fixed 2.0 | fixed / fixed construction input | 0 |

Coupled constraints:

- All resolved physical values finite; every seed present and inside its own declared domain; fixed values equal both endpoints.
- Finished inner+outer+closure envelope W<=600 mm,H<=480 mm,D<=480 mm and W>H; nominal dimensions are not the test.
- Driver connection radius18 mm; physical tangent/source-cap policy must be resolved per family, including R-OSSE and extended-throat cases.
- Reject nonpositive radius, degeneracy, nonmanifold connectivity, unintended intersections/clearance failure and invalid source cap before acoustics; preserve refusal records.
- No silent clipping onto another candidate; canonical full-boundary duplicate identity and inherited config/source/recipe/brief/mesh/solve hashes required.
- No acoustic launch under this document; separate objective, geometry, replay and validation gates apply.
- width>height>36;0<throat_turn<rect_turn<90 degrees;180<terminal<=280 degrees;0.5<=depth_h_ratio<=1.2;2<=rect_exponent<=16;decay>0.
- Original axial law only: throat_turn<pucker_start<180 degrees and max(abs(H),abs(V))<=0.15*depth. No replacement with ATH radial morph.
- Shared normalized spiral law lacks separate H/V flare-rate/angle controls; box retained for CPU hypothesis study, not broad coverage optimization.

## sp__control_v7

Source `examples/typologies/section_pucker_2026-11-15/sp__control_v7.yaml`, SHA256 `c3500e4e8684e17bdadf8bf2142f0668346fd5fbb53476e82cae67867e72dc37`. Starting unit sigma `0.15`; blocked for acoustics.

| Key | Physical meaning / unit | Seed | Proposed bounds | Transform / activity | Initial physical step |
|---|---|---|---|---|---|
| `g_crown_mm` | section crown / mm | 20.0 | 18.0 .. 22.0 | linear unit interval / searched | 0.6 |
| `g_depth_mm` | nominal depth / mm | 198.0 | 192.0 .. 204.0 | linear unit interval / searched | 1.7999999999999998 |
| `g_h_depth_scale` | horizontal section depth scale relative to reference vertical section / dimensionless / categorical | 1.0 | 0.98 .. 1.02 | linear unit interval / searched | 0.006000000000000005 |
| `g_height_mm` | nominal height / mm | 203.0 | fixed 203.0 | fixed / fixed bound | 0 |
| `g_junction_power` | section junction exponent / dimensionless / categorical | 32.0 | fixed 32.0 | fixed / fixed bound | 0 |
| `g_pucker_end_s` | axial pucker window end station / dimensionless / categorical | 0.96 | fixed 0.96 | fixed / fixed bound | 0 |
| `g_pucker_h_mm` | horizontal pucker amplitude / mm | 0.0 | fixed 0.0 | fixed / fixed bound | 0 |
| `g_pucker_peak_s` | axial pucker window peak station / dimensionless / categorical | 0.8 | fixed 0.8 | fixed / fixed bound | 0 |
| `g_pucker_start_s` | axial pucker window start station / dimensionless / categorical | 0.3 | fixed 0.3 | fixed / fixed bound | 0 |
| `g_pucker_v_mm` | vertical pucker amplitude / mm | 0.0 | fixed 0.0 | fixed / fixed bound | 0 |
| `g_throat_blend_mm` | throat blend length / mm | 20.0 | fixed 20.0 | fixed / fixed bound | 0 |
| `g_width_mm` | nominal width / mm | 417.0 | fixed 417.0 | fixed / fixed bound | 0 |
| `generator.name` | generator construction route / dimensionless / categorical | grid | fixed grid | fixed / fixed construction input | 0 |
| `generator.rows.type` | profile or rows construction kind / dimensionless / categorical | section_pucker | fixed section_pucker | fixed / fixed construction input | 0 |
| `generator.seed_policy` | config-load seed derivation policy / dimensionless / categorical | explicit | fixed explicit | fixed / fixed construction input | 0 |
| `generator.span` | modeled azimuthal span and symmetry / dimensionless / categorical | quarter | fixed quarter | fixed / fixed construction input | 0 |
| `generator.n_phi` | number of azimuth samples / dimensionless / categorical | 65 | fixed 65 | fixed / fixed construction input | 0 |
| `generator.n_s` | number of curve stations / dimensionless / categorical | 128 | fixed 128 | fixed / fixed construction input | 0 |
| `generator.wall_thickness_mm` | outer wall thickness / mm | 3.0 | fixed 3.0 | fixed / fixed construction input | 0 |
| `brief.driver.exit_radius_mm` | driver coupling-plane radius / mm | 18.0 | fixed 18.0 | fixed / fixed construction input | 0 |
| `brief.driver.exit_angle_deg` | driver exit wall half-angle / deg | 2.0 | fixed 2.0 | fixed / fixed construction input | 0 |

Coupled constraints:

- All resolved physical values finite; every seed present and inside its own declared domain; fixed values equal both endpoints.
- Finished inner+outer+closure envelope W<=600 mm,H<=480 mm,D<=480 mm and W>H; nominal dimensions are not the test.
- Driver connection radius18 mm; physical tangent/source-cap policy must be resolved per family, including R-OSSE and extended-throat cases.
- Reject nonpositive radius, degeneracy, nonmanifold connectivity, unintended intersections/clearance failure and invalid source cap before acoustics; preserve refusal records.
- No silent clipping onto another candidate; canonical full-boundary duplicate identity and inherited config/source/recipe/brief/mesh/solve hashes required.
- No acoustic launch under this document; separate objective, geometry, replay and validation gates apply.
- 0.9<=h_depth_scale<=1.1; 0<=crown<0.2*height;16<=junction_power<=48;0<throat_blend<0.2*depth.
- Use actual _sweep tests: max(zH)<max(zV),positive pivot,single-peaked sweep radius,compatible return domains,real radicand and source blend after inverse exists. Do not substitute empirical depth<=0.57*width for these exact tests.
- Outer return/closure needs off-axis tangent,intersection and clearance audit; consistent winding alone is insufficient.
- Window onset<peak<end and onset beyond actual throat blend; end before returned attachment; z-only signed relief, preserve x/y.

## sp__moderate_v7

Source `examples/typologies/section_pucker_2026-11-15/sp__moderate_v7.yaml`, SHA256 `3503a26bb65b079dd4fd22b751a3e1fb70b2e1252fd8a5f90d1c013a8c6a7bb3`. Starting unit sigma `0.15`; blocked for acoustics.

| Key | Physical meaning / unit | Seed | Proposed bounds | Transform / activity | Initial physical step |
|---|---|---|---|---|---|
| `g_crown_mm` | section crown / mm | 20.0 | 18.0 .. 22.0 | linear unit interval / searched | 0.6 |
| `g_depth_mm` | nominal depth / mm | 198.0 | 192.0 .. 204.0 | linear unit interval / searched | 1.7999999999999998 |
| `g_h_depth_scale` | horizontal section depth scale relative to reference vertical section / dimensionless / categorical | 1.0 | 0.98 .. 1.02 | linear unit interval / searched | 0.006000000000000005 |
| `g_height_mm` | nominal height / mm | 203.0 | fixed 203.0 | fixed / fixed bound | 0 |
| `g_junction_power` | section junction exponent / dimensionless / categorical | 32.0 | fixed 32.0 | fixed / fixed bound | 0 |
| `g_pucker_end_s` | axial pucker window end station / dimensionless / categorical | 0.96 | fixed 0.96 | fixed / fixed bound | 0 |
| `g_pucker_h_mm` | horizontal pucker amplitude / mm | 3.0 | 0.0 .. 6.0 | linear unit interval / searched | 0.8999999999999999 |
| `g_pucker_peak_s` | axial pucker window peak station / dimensionless / categorical | 0.8 | fixed 0.8 | fixed / fixed bound | 0 |
| `g_pucker_start_s` | axial pucker window start station / dimensionless / categorical | 0.3 | fixed 0.3 | fixed / fixed bound | 0 |
| `g_pucker_v_mm` | vertical pucker amplitude / mm | 4.0 | 0.0 .. 8.0 | linear unit interval / searched | 1.2 |
| `g_throat_blend_mm` | throat blend length / mm | 20.0 | fixed 20.0 | fixed / fixed bound | 0 |
| `g_width_mm` | nominal width / mm | 417.0 | fixed 417.0 | fixed / fixed bound | 0 |
| `generator.name` | generator construction route / dimensionless / categorical | grid | fixed grid | fixed / fixed construction input | 0 |
| `generator.rows.type` | profile or rows construction kind / dimensionless / categorical | section_pucker | fixed section_pucker | fixed / fixed construction input | 0 |
| `generator.seed_policy` | config-load seed derivation policy / dimensionless / categorical | explicit | fixed explicit | fixed / fixed construction input | 0 |
| `generator.span` | modeled azimuthal span and symmetry / dimensionless / categorical | quarter | fixed quarter | fixed / fixed construction input | 0 |
| `generator.n_phi` | number of azimuth samples / dimensionless / categorical | 65 | fixed 65 | fixed / fixed construction input | 0 |
| `generator.n_s` | number of curve stations / dimensionless / categorical | 128 | fixed 128 | fixed / fixed construction input | 0 |
| `generator.wall_thickness_mm` | outer wall thickness / mm | 3.0 | fixed 3.0 | fixed / fixed construction input | 0 |
| `brief.driver.exit_radius_mm` | driver coupling-plane radius / mm | 18.0 | fixed 18.0 | fixed / fixed construction input | 0 |
| `brief.driver.exit_angle_deg` | driver exit wall half-angle / deg | 2.0 | fixed 2.0 | fixed / fixed construction input | 0 |

Coupled constraints:

- All resolved physical values finite; every seed present and inside its own declared domain; fixed values equal both endpoints.
- Finished inner+outer+closure envelope W<=600 mm,H<=480 mm,D<=480 mm and W>H; nominal dimensions are not the test.
- Driver connection radius18 mm; physical tangent/source-cap policy must be resolved per family, including R-OSSE and extended-throat cases.
- Reject nonpositive radius, degeneracy, nonmanifold connectivity, unintended intersections/clearance failure and invalid source cap before acoustics; preserve refusal records.
- No silent clipping onto another candidate; canonical full-boundary duplicate identity and inherited config/source/recipe/brief/mesh/solve hashes required.
- No acoustic launch under this document; separate objective, geometry, replay and validation gates apply.
- 0.9<=h_depth_scale<=1.1; 0<=crown<0.2*height;16<=junction_power<=48;0<throat_blend<0.2*depth.
- Use actual _sweep tests: max(zH)<max(zV),positive pivot,single-peaked sweep radius,compatible return domains,real radicand and source blend after inverse exists. Do not substitute empirical depth<=0.57*width for these exact tests.
- Outer return/closure needs off-axis tangent,intersection and clearance audit; consistent winding alone is insufficient.
- Window onset<peak<end and onset beyond actual throat blend; end before returned attachment; z-only signed relief, preserve x/y.

## sp__strong_v7

Source `examples/typologies/section_pucker_2026-11-15/sp__strong_v7.yaml`, SHA256 `8c92804f7a2c0289e34a7f82fdc02e9aaf8849c0c40b5e3265decff467ff8590`. Starting unit sigma `0.15`; blocked for acoustics.

| Key | Physical meaning / unit | Seed | Proposed bounds | Transform / activity | Initial physical step |
|---|---|---|---|---|---|
| `g_crown_mm` | section crown / mm | 20.0 | 18.0 .. 22.0 | linear unit interval / searched | 0.6 |
| `g_depth_mm` | nominal depth / mm | 198.0 | 192.0 .. 204.0 | linear unit interval / searched | 1.7999999999999998 |
| `g_h_depth_scale` | horizontal section depth scale relative to reference vertical section / dimensionless / categorical | 1.0 | 0.98 .. 1.02 | linear unit interval / searched | 0.006000000000000005 |
| `g_height_mm` | nominal height / mm | 203.0 | fixed 203.0 | fixed / fixed bound | 0 |
| `g_junction_power` | section junction exponent / dimensionless / categorical | 32.0 | fixed 32.0 | fixed / fixed bound | 0 |
| `g_pucker_end_s` | axial pucker window end station / dimensionless / categorical | 0.96 | fixed 0.96 | fixed / fixed bound | 0 |
| `g_pucker_h_mm` | horizontal pucker amplitude / mm | 7.0 | 4.0 .. 10.0 | linear unit interval / searched | 0.8999999999999999 |
| `g_pucker_peak_s` | axial pucker window peak station / dimensionless / categorical | 0.8 | fixed 0.8 | fixed / fixed bound | 0 |
| `g_pucker_start_s` | axial pucker window start station / dimensionless / categorical | 0.3 | fixed 0.3 | fixed / fixed bound | 0 |
| `g_pucker_v_mm` | vertical pucker amplitude / mm | 9.0 | 6.0 .. 12.0 | linear unit interval / searched | 0.8999999999999999 |
| `g_throat_blend_mm` | throat blend length / mm | 20.0 | fixed 20.0 | fixed / fixed bound | 0 |
| `g_width_mm` | nominal width / mm | 417.0 | fixed 417.0 | fixed / fixed bound | 0 |
| `generator.name` | generator construction route / dimensionless / categorical | grid | fixed grid | fixed / fixed construction input | 0 |
| `generator.rows.type` | profile or rows construction kind / dimensionless / categorical | section_pucker | fixed section_pucker | fixed / fixed construction input | 0 |
| `generator.seed_policy` | config-load seed derivation policy / dimensionless / categorical | explicit | fixed explicit | fixed / fixed construction input | 0 |
| `generator.span` | modeled azimuthal span and symmetry / dimensionless / categorical | quarter | fixed quarter | fixed / fixed construction input | 0 |
| `generator.n_phi` | number of azimuth samples / dimensionless / categorical | 65 | fixed 65 | fixed / fixed construction input | 0 |
| `generator.n_s` | number of curve stations / dimensionless / categorical | 128 | fixed 128 | fixed / fixed construction input | 0 |
| `generator.wall_thickness_mm` | outer wall thickness / mm | 3.0 | fixed 3.0 | fixed / fixed construction input | 0 |
| `brief.driver.exit_radius_mm` | driver coupling-plane radius / mm | 18.0 | fixed 18.0 | fixed / fixed construction input | 0 |
| `brief.driver.exit_angle_deg` | driver exit wall half-angle / deg | 2.0 | fixed 2.0 | fixed / fixed construction input | 0 |

Coupled constraints:

- All resolved physical values finite; every seed present and inside its own declared domain; fixed values equal both endpoints.
- Finished inner+outer+closure envelope W<=600 mm,H<=480 mm,D<=480 mm and W>H; nominal dimensions are not the test.
- Driver connection radius18 mm; physical tangent/source-cap policy must be resolved per family, including R-OSSE and extended-throat cases.
- Reject nonpositive radius, degeneracy, nonmanifold connectivity, unintended intersections/clearance failure and invalid source cap before acoustics; preserve refusal records.
- No silent clipping onto another candidate; canonical full-boundary duplicate identity and inherited config/source/recipe/brief/mesh/solve hashes required.
- No acoustic launch under this document; separate objective, geometry, replay and validation gates apply.
- 0.9<=h_depth_scale<=1.1; 0<=crown<0.2*height;16<=junction_power<=48;0<throat_blend<0.2*depth.
- Use actual _sweep tests: max(zH)<max(zV),positive pivot,single-peaked sweep radius,compatible return domains,real radicand and source blend after inverse exists. Do not substitute empirical depth<=0.57*width for these exact tests.
- Outer return/closure needs off-axis tangent,intersection and clearance audit; consistent winding alone is insufficient.
- Window onset<peak<end and onset beyond actual throat blend; end before returned attachment; z-only signed relief, preserve x/y.
