# Section-based H/V pucker pilot

Owner-authorized extension of the corrected section reference. Three48-attempt searches,
ordered control, moderate H/V, strong H/V, then top1 verification of all three. Seed1234,
population8, sigma .15, same objective7 and room_landscape_80x50_700_hf1440_v7 brief.

[Source night](home_section_pucker_2026-11-15.yaml), [full measured bounds evidence](section_pucker_validation_2026-11-15.json),
[construction and complete parameter ranges](../research/typologies/SECTION_PUCKER_RESEARCH_2026-11-15.md),
[render gallery](../renders/2026-11-15-rolled-rect/puckers/index.html).

Common bounds depth192..204, H-depth-scale.98..1.02, crown18..22; seed198/1/20. Moderate H0..6,
V0..8 at seeds3/4 mm; strong H4..10,V6..12 at seeds7/9 mm. Pucker onset/peak/end .30/.80/.96
and join rounding are fixed to avoid a poorly constrained placement/strength search. All
searched seed values are interior, no clipping or midpoint fill. Starting physical steps are
1.8mm/.006/.6mm and moderate H/V.9/1.2mm, strong.9/.9mm. No warm-start mean is imported: this
is a fresh visual seed study, not a restart of the earlier optimized winner. The new five-dimensional
relief basin is unknown; the common control history supports .15 as a reasonable initial scale.

Validation: seeds3306/3152/3134 DOFs, all circular36mm, envelope fits. All72 extrema passed;
maximum4055/6000 DOFs. Random meshing63/64,62/64,62/64; five invalid_geometry refusals charged
flat to attempted budgets. Expected valid counts47.25/46.5/46.5 from the uniform sample, not a
guarantee. Prediction: first improvement n1..8, best-at>0; compare with the final readout.
145 related CPU tests pass,19 new. Mesh epw6,65rows/128stations, caps6000/24000 unchanged.
Verification densifies frequency sampling; spatial convergence requires an independent check.

Detached queue controller10256, launched13:01:07 local via WMI, with no other GPU night live.
Prelaunch NVIDIA baseline1290MiB (desktop/GUI), no BEAT or Julia host observed. Runner performs
its standard sequential cleanup/locking. Log `runs/nights/queue_home_section_pucker.log`.
All core and prior geometry source/configuration bytes remain frozen. Keep the new source and
configs frozen while the queued jobs and their verification run. No unrelated GUI worker was stopped.
