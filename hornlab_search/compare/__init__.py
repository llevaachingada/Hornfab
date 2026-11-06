"""A/B check of a Hornfab solve against Boundary Lab (BL, JWSound/boundary-lab, BEAT Engine).

Package map (docs/ab/BOUNDARY_LAB_AB.md is the owner-facing guide):

* ``model``         normalized in-memory structure ``AbData`` (the same arrays as ``types.Response``,
                    in ONE convention: 1 m/s velocity drive, exp(+i w t), Pa) + durable npz round trip
* ``mshio``         read / write gmsh ASCII 2.2, mirror a quarter or half mesh to a FULL mesh
* ``export_for_bl`` write the "BL handoff" folder (mesh in metres, .blab.json, request overlay, steps for the friend)
* ``hornfab_side``  Hornfab arrays -> ``AbData``; the high-resolution reference solve command
* ``bl_import``     Boundary Lab exports (GUI text files, balloon folder, headless run dir) and generic CSV -> ``AbData``
* ``analysis``      frequency alignment, curves, beamwidth, DI, balloon difference, per-band stats, verdicts
* ``conventions``   "what probably went wrong" detector (6 dB, 20 log f slope, time convention, mirrored angles ...)
* ``charts`` / ``report``  self-contained HTML + summary.json + verdict.txt
* ``fake``          synthetic data for both sides (``demo --fake``)
* ``cli``           ``hornlab-search ab-bl export|solve|import|compare|demo``

Nothing here changes a solver, a hash, a cache key or any default. Boundary Lab is never imported
(it pins its own engine and lives in its own environment); its files are read as data.
"""
