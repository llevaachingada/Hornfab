# Issue bodies

Each file is a GitHub issue body with a YAML front matter block (`title`, `labels`, `blocked_by`). `blocked_by` uses issue keys (the numeric prefix of the file name), not GitHub issue numbers.

| File | Title | Labels | blocked_by |
|---|---|---|---|
| `04-design-mesh.md` | [04] Design space and mesh | wave-1 | none |
| `05-solve.md` | [05] Solve backends and warm worker | wave-1 | none |
| `06-metrics.md` | [06] Metrics and targets | wave-1 | none |
| `07-dataset.md` | [07] Dataset record and store | wave-1 | none |
| `08-pipeline.md` | [08] Objective, search, report, CLI | wave-2, blocked | 04, 05, 06, 07 |
| `09-checkpoints.md` | [09] Physics checkpoints CP-7a to CP-7f | senior-review, blocked | 08 |
| `q-impedance-bc.md` | [Q] Collin: is a Robin/admittance BC planned for BEAT? | question | none |
| `q-surface-traces.md` | [Q] Collin: surface_traces ordering and bempp field recovery | question | none |
| `q-point-grid.md` | [Q] Collin: can build_point_grid be public API? | question | none |
| `q-excitation.md` | [Q] Collin: confirm BEAT driver excitation on tag 2 | question | none |
| `q-package-name.md` | [Q] Collin: OK with the hornlab-search name? | question | none |

## How the orchestrator creates them

For each file, the orchestrator reads the front matter for `title` and `labels`, strips the front matter to produce the body, and runs `gh issue create --title "<title>" --label "<label>" --body-file <body-file>` (one `--label` per label). Creation order is 04, 05, 06, 07, 08, 09, then the questions, so that the real GitHub issue numbers for 04 to 08 are known when `blocked_by` is resolved. After creation the orchestrator replaces each `blocked_by` key with the real `#number`, edits the "Blocked by" section of the dependent issue (`gh issue edit --body-file`), and mirrors the new issues into `docs/ISSUES.md` in the same commit as the `docs/CONTINUITY.md` update. Issues labelled `blocked` have that label removed once every issue in their `blocked_by` list is closed with its checkpoint passed.
