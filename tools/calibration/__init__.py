"""Calibration harness (day plan 2026-11-12, Group C).

Two offline tools around the P0 calibration night (NEXT_DEV_PRIORITIES P0 item 2):

* ``plan_calibration.py`` -- generate the runnable night file (runner format of
  ``tools/run_campaign_night.py``) that re-verifies stored finalists under the mesh/distance/epw
  calibration variants, plus the ``extends:`` overlays and per-variant run directories it needs.
* ``compare_calibration.py`` -- after the night ran: pair the variants per design, report
  pass/fail per acceptance threshold, and rank-agreement (Spearman) across variants.

Both tools are offline: they write YAML/JSON/NDJSON copies, never launch a solve.
"""
