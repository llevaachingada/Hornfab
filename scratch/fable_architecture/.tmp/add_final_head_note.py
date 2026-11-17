import io
note = (" The tree later advanced to `50f3d8c` @ 19:55:43 (test/docs only): "
        "`git diff --stat d187c06..50f3d8c` shows **none** of the traced files changed, so all "
        "citations remain valid at `50f3d8c`.")
targets = {
 'scratch/fable_architecture/FAILURE_AND_BOUNDARY_AUDIT.md':
   "The tree advanced **twice** during this read-only pass (concurrent lane).",
 'scratch/fable_architecture/SIZE_FEASIBILITY_EVIDENCE.md':
   "The tree advanced during the pass.",
 'scratch/fable_architecture/SEARCH_CONTROL_MAP.md':
   "The tree advanced during the pass.",
 'scratch/fable_architecture/WATCHDOG_REPLAY.md':
   "The tree advanced during the pass;",
}
for p, anchor in targets.items():
    s = open(p, encoding='utf-8').read()
    if anchor not in s:
        print("ANCHOR MISS", p); continue
    if anchor.endswith(';'):
        # keep the clause flowing: insert note before the semicolon clause
        s = s.replace(anchor, "The tree advanced during the pass;" + note, 1)
    else:
        s = s.replace(anchor, anchor + note, 1)
    open(p, 'w', encoding='utf-8').write(s)
    print("updated", p)
