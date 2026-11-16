# Preserved rolled-family execution evidence

Copied from existing local artifacts on 2026-11-15 for the owner's documentation-only handoff.
No geometry generation, meshing, optimization or acoustic solve was run to create this bundle.
Read [the correction and readiness ledger](../ROLLED_FAMILY_EVIDENCE_HANDOFF_2026-11-15.md).

- `manifest.json`: original paths, byte hashes, historical execution summaries, current observed
  source/config/packet hashes, and packet image existence checks.
- `audit-rect_*.json`: four historical rectangle-arm audits at their recorded implementation hash.
- `audit-section_control.json`: **pre-correction failure evidence**, not acceptance. Retained so
  the inverse-tail NaN failure is not lost.
- `final-section_*.json`: corrected section-arm audits at their later implementation hash.
- `bo_synthetic_smoke.py` and `.json`: real CPU BoTorch path with **synthetic labels only**.
  No BEM calls; does not meet the production gate of >=100 usable matched acoustic solves.
- `working_tree_status_at_capture.txt`: shared working-tree snapshot, including pre-existing
  concurrent changes. It is not a list of files changed by this documentation task.

Preservation checks: all 11 copied artifacts match their manifest SHA-256; all 34 observed
source/config paths existed; all 24 local image paths referenced by the HTML existed; local
Markdown links in the new handoff resolved. These are file-integrity checks, not physics tests.

The six current home-cell constructions are not automatically covered by the older native
family's sampled audits. The owner hold on new solves remains in force. Refresh state on pickup.
