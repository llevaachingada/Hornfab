"""Read the ACIS body of a DXF 3DSOLID (text SAT, e.g. a DWG converted to DXF R2000 by the ODA File
Converter) and dump its topology: vertices, edges (with curve type) and faces (surface type + vertex
loops) to JSON, for studying a reference CAD model. Not used by the solver path.

    .venv\\Scripts\\python.exe tools/cad/sat_dump.py reference/funktion-one/dxf2000/X.dxf out.json
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path


def _floats(ent, n=None):
    out = []
    for t in ent.data:
        try:
            out.append(float(str(t)))
        except ValueError:
            continue
    return out if n is None else out[:n]


def _ref(ent, name):
    for t in ent.data:
        if getattr(t, "name", None) == name:
            return t
    return None


def dump(dxf_path: str) -> dict:
    import ezdxf
    from ezdxf.acis import sat
    doc = ezdxf.readfile(dxf_path)
    solids = [e for e in doc.modelspace() if e.dxftype() == "3DSOLID"]
    b = sat.parse_sat(solids[0].sat)
    ents = b.entities
    vid = {}
    verts = []
    for e in ents:
        if e.name == "vertex":
            p = _ref(e, "point")
            vid[id(e)] = len(verts)
            verts.append(_floats(p, 3))
    edges = []
    eid = {}
    for e in ents:
        if e.name != "edge":
            continue
        vs = [t for t in e.data if getattr(t, "name", None) == "vertex"]
        curve = next((t for t in e.data if str(getattr(t, "name", "")).endswith("curve")), None)
        rec = {"v": [vid[id(v)] for v in vs[:2]], "curve": getattr(curve, "name", "?")}
        if curve is not None and curve.name == "ellipse-curve":
            f = _floats(curve)
            rec["ellipse"] = {"center": f[0:3], "normal": f[3:6], "major": f[6:9], "ratio": f[9] if len(f) > 9 else 1.0}
        eid[id(e)] = len(edges)
        edges.append(rec)
    faces = []
    for e in ents:
        if e.name != "face":
            continue
        surf = next((t for t in e.data if str(getattr(t, "name", "")).endswith("surface")), None)
        loops = []
        lp = _ref(e, "loop")
        seen_loops = 0
        while lp is not None and seen_loops < 20:
            seen_loops += 1
            ce0 = _ref(lp, "coedge")
            ce, ring, guard = ce0, [], 0
            while ce is not None and guard < 200:
                guard += 1
                ed = _ref(ce, "edge")
                sense = "reversed" in [str(t) for t in ce.data]
                if ed is not None and id(ed) in eid:
                    ring.append([eid[id(ed)], sense])
                nxt = [t for t in ce.data if getattr(t, "name", None) == "coedge"]
                ce = nxt[0] if nxt else None
                if ce is ce0:
                    break
            loops.append(ring)
            nxt = [t for t in lp.data if getattr(t, "name", None) == "loop"]
            lp = nxt[0] if nxt else None
        rec = {"surface": getattr(surf, "name", "?"), "loops": loops}
        if surf is not None and surf.name == "plane-surface":
            f = _floats(surf)
            rec["plane"] = {"point": f[0:3], "normal": f[3:6]}
        if surf is not None and surf.name == "cone-surface":
            rec["cone"] = _floats(surf)[:12]
        faces.append(rec)
    return {"vertices": verts, "edges": edges, "faces": faces}


def main(argv=None) -> int:
    argv = argv or sys.argv[1:]
    d = dump(argv[0])
    Path(argv[1]).write_text(json.dumps(d, indent=0), encoding="utf-8")
    import numpy as np
    v = np.array(d["vertices"])
    print(f"{len(v)} vertices, {len(d['edges'])} edges, {len(d['faces'])} faces; bbox min {v.min(0).round(1)} max {v.max(0).round(1)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
