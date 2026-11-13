# S10 studies workspace — screenshot evidence (2026-11-13)

Headless visual QA of the Studies workspace, produced by the S10/B6 pass. The images show the
list, create, snapshot/data, analysis/explain, propose, package/dry-run/execute, decide and export
panels.

**Hazard — the lanes read "idle" because this QA app used a temporary `runs/` root.** That is a
property of the QA harness, not the live lane state. Do not cite these screenshots as evidence that
the GPU/CPU lanes were idle.

The studies and jobs in the screenshots were created under a temporary study root. No live study,
job, solve, queue or dataset was started or modified. These are UI render/flow evidence only; they
make no acoustic or performance claim.

The render, link, preview, decision and execute-fallback findings they produced are fixed in the
same commit (`tests/test_gui_studies_qa_fixes.py`). The remaining "No action available" cause — the
upstream panel action payload — is recorded in `docs/ISSUES.md`, not fixed here.
