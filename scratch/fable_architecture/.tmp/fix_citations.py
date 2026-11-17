import sys
edits = {
 'scratch/fable_architecture/FAILURE_AND_BOUNDARY_AUDIT.md': [
   ("(`generated.py:198-205`; `evaluate.py:1544-1548`)","(`generated.py:214-221`; `evaluate.py:1544-1548`)"),
   ("plughorn/meh layout `reasons` (`generated.py:118-121`)","plughorn/meh layout `reasons` (`generated.py:133-135`)"),
   ("(`generated.py:193-205`) after `materialize`","(`generated.py:205-221`) after `materialize`"),
   ("`None` (`registry.py:423-424`; `generated.py:195-197`)","`None` (`registry.py:423-424`; `generated.py:209-213`)"),
   ("`invalid_envelope` (`generated.py:198-205`), so a wrong","`invalid_envelope` (`generated.py:214-221`), so a wrong"),
 ],
 'scratch/fable_architecture/SIZE_FEASIBILITY_EVIDENCE.md': [
   ("(`design/generated.py:84-89`)","(`design/generated.py:99-104`)"),
   ("(`generated.py:198-205`, `:35-37`)","(`generated.py:214-221`, `:35-37`)"),
   ("(`generated.py:122-126`): `mouth_w/mouth_h/env_d_mm > env+0.5` \u2192 `ValueError`; layout `reasons` \u2192 `invalid_geometry` (`:118-121`)",
    "(`generated.py:136-141`): `mouth_w/mouth_h/env_d_mm > env+0.5` \u2192 `ValueError`; layout `reasons` \u2192 `invalid_geometry` (`:133-135`)"),
   ("(`generated.py:198-205`), so an over-estimate","(`generated.py:214-221`), so an over-estimate"),
   ("(`generated.py:84-89`, `:122-126`)","(`generated.py:99-104`, `:136-141`)"),
 ],
}
for path, reps in edits.items():
    s = open(path, encoding='utf-8').read()
    for a,b in reps:
        if a not in s:
            print('MISS', path, repr(a[:70]))
        s = s.replace(a,b)
    open(path,'w',encoding='utf-8').write(s)
    print('rewrote', path)
