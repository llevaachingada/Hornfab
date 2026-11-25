// view3d.js — hornlab-search GUI   AGPL-3.0-or-later
// Three.js r160 mesh viewer for quarter/half-model horn meshes.
// Mirrors quarter models across x=0 and y=0, half models ('14' x-half / '12' y-half) across their
// one symmetry plane, to reconstruct the full horn.
// Draws two line overlays over the shaded surface: the sparse dihedral ridgelines (default on) and,
// on request, every triangle edge of the tessellation itself (buildMeshEdgeGeometry, default off —
// the same toggle is persisted for every 3D surface and read back by hw3d.js and sandbox.js).
// Falls back to a 2D wall-profile SVG if the CDN import fails.

let THREE, OrbitControls;

/** Load three.js r160 + OrbitControls (module-scope). Resolves to the THREE namespace (falsy
 *  when the CDN import failed) so a viewer can also `const THREE = await loadThree()` and use
 *  it in its own scope. */
export async function loadThree() {
  if (THREE) return THREE;
  try {
    const mod = await import("three");
    THREE = mod;
    const { OrbitControls: OC } = await import("three/addons/controls/OrbitControls.js");
    OrbitControls = OC;
    return THREE;
  } catch (e) {
    console.warn("view3d: three.js failed to load:", e);
    return null;
  }
}

/**
 * Mirror a quarter/half mesh to a full mesh.
 * Quadrant semantics (same source of truth as gui/data.py::horn_dims — search-recorded rows carry the
 * quadrant string; the GRID route meshes half-models, "14" = the +x half, "12" = the +y half):
 *   '1'    quarter (x >= 0, y >= 0)  -> mirror across x=0 and y=0 (4 copies)
 *   '14'   +x half (x >= 0, full y)  -> mirror across x=0        (2 copies)
 *   '12'   +y half (full x, y >= 0)  -> mirror across y=0        (2 copies)
 *   anything else ('1234', …) is already a full mesh -> passthrough.
 * verts: flat [x,y,z, x,y,z, ...] in mm; tris: flat [i,j,k, ...] indices.
 * Returns { verts: Float32Array, tris: Uint32Array, triSrc: Int32Array }; verts on the symmetry
 * planes are duplicated (accepted seam — every mirrored quadrant keeps the original's
 * triangulation). `triSrc[t]` is the ORIGINAL triangle index of mirrored triangle `t`, so a
 * per-triangle attribute (a density value, a tag) survives the mirror faithfully.
 */
export function mirrorMesh(verts, tris, quadrants) {
  const q = String(quadrants ?? "");
  const copies = q === "1" ? [[1, 1], [-1, 1], [1, -1], [-1, -1]]
               : q === "14" ? [[1, 1], [-1, 1]]
               : q === "12" ? [[1, 1], [1, -1]]
               : [[1, 1]];
  const nT = Math.floor(tris.length / 3);
  if (copies.length === 1) {
    const triSrc = new Int32Array(nT);
    for (let t = 0; t < nT; t++) triSrc[t] = t;
    return { verts: new Float32Array(verts), tris: new Uint32Array(tris), triSrc };
  }

  const nOrig = verts.length / 3;
  const allVerts = [];
  const allTris = [];
  const triSrc = new Int32Array(nT * copies.length);
  let copyIndex = 0;
  // A single reflection flips triangle handedness; two reflections preserve it.
  // flips when exactly one of sx, sy is -1 (sx * sy < 0).
  for (const [sx, sy] of copies) {
    const offset = allVerts.length / 3;
    for (let i = 0; i < nOrig; i++) {
      allVerts.push(sx * verts[i * 3], sy * verts[i * 3 + 1], verts[i * 3 + 2]);
    }
    for (let i = 0; i < tris.length; i += 3) {
      if (sx * sy < 0) {
        // flip winding for reflected quadrants
        allTris.push(tris[i] + offset, tris[i + 2] + offset, tris[i + 1] + offset);
      } else {
        allTris.push(tris[i] + offset, tris[i + 1] + offset, tris[i + 2] + offset);
      }
    }
    for (let t = 0; t < nT; t++) triSrc[copyIndex * nT + t] = t;
    copyIndex++;
  }
  return { verts: new Float32Array(allVerts), tris: new Uint32Array(allTris), triSrc };
}

// ── Persisted 3D render settings ─────────────────────────────────────────────
// One key for every 3D surface (dedicated page, run-detail inline viewer, evolution time-lapse):
// {surface: "satin"|"matte"|"metallic"|"studio", ridges: "on"|"off"|"thin", light: 0.5..2.0}.
// Defaults are exactly the pre-settings look (owner captures/tests pin it): satin material,
// near-white ridgelines at 0.28, key/fill/rim at 1.15/0.35/0.85.
const RENDER_PREF_KEY = "hl-v3d-render";
const RENDER_SURFACES = ["satin", "matte", "metallic", "studio", "relief"];
const RENDER_RIDGES = ["on", "off", "thin"];

// Existing colour constants, kept in one place so no preset invents a new hex.
const HORN_BASE_COLOR = 0xdfe4e8;   // light-neutral horn body
const WIRE_COLOR = 0xf4f7f9;        // near-white ridgelines
const HEMI_GROUND_COLOR = 0x8fa3ad; // hemisphere shadow-side tint
const LIGHT_COLOR = 0xffffff;

// Mesh-net styles: one enum shared by every 3D horn surface via the look-extra key. "off" = solid
// only; every colour turns the net on. These are deliberate LITERAL colours, not theme tokens:
// the net must read the same in the light and dark themes (theme tokens made "black" render
// near-white on dark). Opacities keep the net behind the topography — a quiet background texture.
const MESH_NET_MODES = ["off", "white", "black", "gray"];
const MESH_NET_LINE_WIDTH = 1.0;    // CSS pixels (LineMaterial worldUnits:false)
const MESH_NET_FADE_MIN = 1.5;      // projected segment length (CSS px) at/below which the net fades out
const MESH_NET_FADE_MAX = 5.0;      // at/above which it draws at full colour
const MESH_NET_STYLES = {
  white: { hex: WIRE_COLOR,  opacity: 0.22 },                        // 0xf4f7f9
  black: { hex: 0x14181b,    opacity: 0.22 },
  gray:  { hex: 0x8a949a,    opacity: 0.28 },
};

// ── Mesh-density heat ramp ───────────────────────────────────────────────────
// Perceptually ordered cool -> warm stops (sRGB bytes). Cool = small max edge length (fine mesh),
// warm = large max edge length (coarse mesh). Literal colours on purpose, like the mesh net: the
// same scale reads in both themes. The CSS gradient is exported so the legend in app.js is the
// exact same ramp the triangles use (one source of truth, no eyeballed copy).
const HEAT_STOPS = [
  [0.00, [ 40,  60, 130]],   // deep blue
  [0.20, [ 42, 120, 178]],   // blue
  [0.40, [ 65, 176, 160]],   // teal
  [0.60, [170, 202,  90]],   // yellow-green
  [0.80, [236, 170,  52]],   // amber
  [1.00, [190,  46,  36]],   // warm red
];
export const HEAT_RAMP_CSS = "linear-gradient(90deg, " +
  HEAT_STOPS.map(([t, rgb]) => `rgb(${rgb.join(",")}) ${Math.round(t * 100)}%`).join(", ") + ")";

/** Heat colour for t in [0,1] as sRGB bytes, linearly interpolated between the stops. */
function heatRgb(t) {
  const x = Math.min(1, Math.max(0, t));
  for (let i = 1; i < HEAT_STOPS.length; i++) {
    const [t1, c1] = HEAT_STOPS[i];
    if (x <= t1) {
      const [t0, c0] = HEAT_STOPS[i - 1];
      const f = t1 === t0 ? 0 : (x - t0) / (t1 - t0);
      return [c0[0] + (c1[0] - c0[0]) * f,
              c0[1] + (c1[1] - c0[1]) * f,
              c0[2] + (c1[2] - c0[2]) * f];
    }
  }
  return HEAT_STOPS[HEAT_STOPS.length - 1][1];
}

// Per-surface material + rig mix. `wireOpacity` is the "on" opacity *before* RIDGE_OPACITY_GAIN
// (matte is deliberately "off-ish": calmer lines); "thin" starts at 0.12 and takes the same gain,
// "off" removes the LineSegments.
const RENDER_PRESETS = {
  satin:    { colorScale: 1.0,  roughness: 0.55, metalness: 0.05, wireOpacity: 0.28,
              light: { hemi: 0.45, key: 1.15, fill: 0.35, rim: 0.85 } },   // today's exact look
  matte:    { colorScale: 0.88, roughness: 0.85, metalness: 0.02, wireOpacity: 0.18,
              light: { hemi: 0.45, key: 1.15, fill: 0.35, rim: 0.85 } },
  metallic: { colorScale: 1.0,  roughness: 0.32, metalness: 0.35, wireOpacity: 0.28,
              light: { hemi: 0.45, key: 1.15, fill: 0.35, rim: 0.85 } },
  studio:   { colorScale: 1.0,  roughness: 0.45, metalness: 0.05, wireOpacity: 0.28,
              light: { hemi: 0.55, key: 1.55, fill: 0.70, rim: 1.15 } },
  // Gentle-form reader: little ambient, one strong raking key, matte so highlights never wash the
  // slow curvature out. Pair it with the "light angle" slider and the depth contours.
  relief:   { colorScale: 0.92, roughness: 0.9,  metalness: 0.0,  wireOpacity: 0.18,
              light: { hemi: 0.16, key: 1.9, fill: 0.12, rim: 0.45 } },
};

// ── Look extras (contours + light angle + mesh edges) ────────────────────────
// Kept in their OWN storage key so the three-field render prefs above stay byte-identical for
// every existing capture/test. contours: "off"|"on" (iso-depth lines, readable slope for gentle
// changes); angle: 0..345 deg, spins the key/fill/rim rig about the horn axis (raking light);
// mesh: "off"|"white"|"black"|"gray" (every triangle edge of the shaded mesh, in that colour,
// drawn over the surface — the tessellation the material would otherwise hide; legacy "on" reads
// as "gray"). The key is shared by every 3D horn surface (init3d, init3dFrames, sandbox.js), so
// the mesh toggle reads the same everywhere.
const LOOK_EXTRA_KEY = "hl-v3d-look";
const KEY_BASE = [1.6, 2.2, 1.8], FILL_BASE = [-1.8, 0.6, 1.2], RIM_BASE = [-1.2, -1.0, -2.2];

export function normalizeLookExtras(raw) {
  let o = raw;
  if (typeof o === "string") { try { o = JSON.parse(o); } catch (e) { o = null; } }
  if (!o || typeof o !== "object" || Array.isArray(o)) o = {};
  const contours = o.contours === "on" ? "on" : "off";
  const mesh = MESH_NET_MODES.indexOf(o.mesh) >= 0 ? o.mesh : (o.mesh === "on" ? "gray" : "off");
  let angle = typeof o.angle === "number" ? o.angle : Number(o.angle);
  if (!isFinite(angle)) angle = 0;
  angle = ((Math.round(angle / 15) * 15) % 360 + 360) % 360;
  return { contours, angle, mesh };
}
export function loadLookExtras() {
  try { return normalizeLookExtras(localStorage.getItem(LOOK_EXTRA_KEY)); }
  catch (e) { return normalizeLookExtras(null); }
}
export function saveLookExtras(x) {
  const p = normalizeLookExtras(x);
  try { localStorage.setItem(LOOK_EXTRA_KEY, JSON.stringify(p)); } catch (e) { /* private mode */ }
  return p;
}

/** 1/2/5 x 10^n contour spacing (metres) targeting ~28 intervals over the depth range — twice the
 *  old density (the 1/2/5 rounding lands the actual count between ~24 and ~40 lines). */
export function niceContourStep(rangeM) {
  const raw = Math.max(1e-6, rangeM) / 28;
  const pow = Math.pow(10, Math.floor(Math.log10(raw)));
  const f = raw / pow;
  return (f < 1.5 ? 1 : f < 3.5 ? 2 : f < 7.5 ? 5 : 10) * pow;
}

/** Iso-depth contour lines drawn in the fragment shader (object-space z, metres). Returns the
 *  uniform; value 0 = off. Lines fade where they would alias (grazing / far away). Soft neutral
 *  grey at low mix strength: readable on the lit wall and the shadow side without reading as ink. */
function installContours(mat) {
  const u = { value: 0 };
  mat.onBeforeCompile = shader => {
    shader.uniforms.uContour = u;
    shader.vertexShader = shader.vertexShader
      .replace("#include <common>", "#include <common>\nvarying float vContourZ;")
      .replace("#include <begin_vertex>", "#include <begin_vertex>\nvContourZ = position.z;");
    shader.fragmentShader = shader.fragmentShader
      .replace("#include <common>", "#include <common>\nvarying float vContourZ;\nuniform float uContour;")
      .replace("#include <dithering_fragment>",
        "#include <dithering_fragment>\n" +
        "if (uContour > 0.0) {\n" +
        "  float d = vContourZ / uContour; float w = fwidth(d);\n" +
        "  float g = abs(fract(d - 0.5) - 0.5) / max(w, 1e-5);\n" +
        "  float ln = (1.0 - smoothstep(0.5, 1.5, g)) * (1.0 - smoothstep(0.35, 0.6, w));\n" +
        "  gl_FragColor.rgb = mix(gl_FragColor.rgb, vec3(0.38, 0.41, 0.43), ln * 0.42);\n" +
        "}");
  };
  mat.customProgramCacheKey = () => "hl-contour-v3";
  return u;
}

/**
 * Welded, crease-aware smooth geometry (positions in the input unit). The mirrored quarter/half
 * mesh duplicates every vertex on the symmetry planes, and the mesher's own seams do the same, so
 * plain computeVertexNormals() shades a hard dark line down each plane and every triangle edge
 * reads as a facet. Here coincident vertices (0.01 mm) are merged, then each welded vertex gets one
 * area/angle-weighted normal per group of incident faces within `creaseDeg` of each other: smooth
 * where the wall is smooth, still sharp at a real rim or fold. Indexed output, winding preserved.
 */
export function buildSmoothGeometry(T, verts, tris, creaseDeg = 45) {
  const nV = Math.floor(verts.length / 3);
  const keyToUid = new Map();
  const wx = [], wy = [], wz = [];
  const weld = new Int32Array(nV);
  for (let i = 0; i < nV; i++) {
    const x = verts[i * 3], y = verts[i * 3 + 1], z = verts[i * 3 + 2];
    const key = `${Math.round(x * 100)},${Math.round(y * 100)},${Math.round(z * 100)}`;
    let uid = keyToUid.get(key);
    if (uid === undefined) { uid = wx.length; keyToUid.set(key, uid); wx.push(x); wy.push(y); wz.push(z); }
    weld[i] = uid;
  }
  const U = wx.length;
  const nT = Math.floor(tris.length / 3);
  const fc = new Int32Array(nT * 3);
  const fn = new Float32Array(nT * 3);
  let nF = 0;
  for (let t = 0; t < nT; t++) {
    const a = weld[tris[t * 3]], b = weld[tris[t * 3 + 1]], c = weld[tris[t * 3 + 2]];
    if (a === b || b === c || c === a) continue;
    const ux = wx[b] - wx[a], uy = wy[b] - wy[a], uz = wz[b] - wz[a];
    const vx = wx[c] - wx[a], vy = wy[c] - wy[a], vz = wz[c] - wz[a];
    let nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx;
    const len = Math.sqrt(nx * nx + ny * ny + nz * nz);
    if (!(len > 0)) continue;
    fc[nF * 3] = a; fc[nF * 3 + 1] = b; fc[nF * 3 + 2] = c;
    fn[nF * 3] = nx / len; fn[nF * 3 + 1] = ny / len; fn[nF * 3 + 2] = nz / len;
    nF++;
  }
  // vertex -> corner list (CSR); a corner id is faceIndex*3 + cornerSlot
  const start = new Int32Array(U + 1);
  for (let k = 0; k < nF * 3; k++) start[fc[k] + 1]++;
  for (let v = 0; v < U; v++) start[v + 1] += start[v];
  const fill = start.slice(0, U);
  const corners = new Int32Array(nF * 3);
  for (let k = 0; k < nF * 3; k++) corners[fill[fc[k]]++] = k;

  const cosC = Math.cos(creaseDeg * Math.PI / 180);
  const px = [], py = [], pz = [], qx = [], qy = [], qz = [];
  const idx = new Uint32Array(nF * 3);
  for (let v = 0; v < U; v++) {
    const g0 = px.length;                      // this vertex's groups live at [g0, px.length)
    const gSeed = [];                          // seed face normal per group
    for (let s = start[v]; s < start[v + 1]; s++) {
      const k = corners[s], f = (k / 3) | 0, j = k % 3;
      const fx = fn[f * 3], fy = fn[f * 3 + 1], fz = fn[f * 3 + 2];
      let g = -1;
      for (let q = 0; q < gSeed.length; q++) {
        const sd = gSeed[q];
        if (sd[0] * fx + sd[1] * fy + sd[2] * fz >= cosC) { g = q; break; }
      }
      if (g < 0) {
        g = gSeed.length; gSeed.push([fx, fy, fz]);
        px.push(wx[v]); py.push(wy[v]); pz.push(wz[v]); qx.push(0); qy.push(0); qz.push(0);
      }
      // corner angle weight
      const b = fc[f * 3 + (j + 1) % 3], c = fc[f * 3 + (j + 2) % 3];
      const e1x = wx[b] - wx[v], e1y = wy[b] - wy[v], e1z = wz[b] - wz[v];
      const e2x = wx[c] - wx[v], e2y = wy[c] - wy[v], e2z = wz[c] - wz[v];
      const l1 = Math.sqrt(e1x * e1x + e1y * e1y + e1z * e1z), l2 = Math.sqrt(e2x * e2x + e2y * e2y + e2z * e2z);
      const cs = (l1 > 0 && l2 > 0) ? (e1x * e2x + e1y * e2y + e1z * e2z) / (l1 * l2) : 0;
      const wgt = Math.acos(Math.max(-1, Math.min(1, cs)));
      qx[g0 + g] += fx * wgt; qy[g0 + g] += fy * wgt; qz[g0 + g] += fz * wgt;
      idx[k] = g0 + g;
    }
  }
  const nOut = px.length;
  const pos = new Float32Array(nOut * 3), nrm = new Float32Array(nOut * 3);
  for (let i = 0; i < nOut; i++) {
    pos[i * 3] = px[i]; pos[i * 3 + 1] = py[i]; pos[i * 3 + 2] = pz[i];
    const l = Math.sqrt(qx[i] * qx[i] + qy[i] * qy[i] + qz[i] * qz[i]) || 1;
    nrm[i * 3] = qx[i] / l; nrm[i * 3 + 1] = qy[i] / l; nrm[i * 3 + 2] = qz[i] / l;
  }
  const geo = new T.BufferGeometry();
  geo.setAttribute("position", new T.BufferAttribute(pos, 3));
  geo.setAttribute("normal", new T.BufferAttribute(nrm, 3));
  geo.setIndex(new T.BufferAttribute(idx, 1));
  return geo;
}

/**
 * Non-indexed triangle soup for the mesh-density heatmap: every triangle gets ONE flat colour
 * (per-triangle constant, as required) while normals are averaged across welded positions so the
 * horn still reads as a form instead of a faceted shell. `triEdge[t]` is triangle t's own max edge
 * length (mm, same order as `tris`); the colour ramp is clamped to [lo, hi] (the displayed p05..p95).
 * Positions are mm in, metres out — the same stage as buildSmoothGeometry + geo.scale(0.001).
 */
function buildDensityGeometry(T, verts, tris, triEdge, lo, hi) {
  const nT = Math.floor(tris.length / 3);
  const P = new Float32Array(nT * 9), N = new Float32Array(nT * 9), C = new Float32Array(nT * 9);
  const keyToUid = new Map();
  const wx = [], wy = [], wz = [], ax = [], ay = [], az = [];
  const wid = new Int32Array(nT * 3);

  for (let t = 0; t < nT; t++) {
    for (let c = 0; c < 3; c++) {
      const vi = tris[t * 3 + c];
      const x = verts[vi * 3], y = verts[vi * 3 + 1], z = verts[vi * 3 + 2];
      const key = `${Math.round(x * 100)},${Math.round(y * 100)},${Math.round(z * 100)}`;
      let u = keyToUid.get(key);
      if (u === undefined) {
        u = wx.length; keyToUid.set(key, u);
        wx.push(x); wy.push(y); wz.push(z);
        ax.push(0); ay.push(0); az.push(0);
      }
      wid[t * 3 + c] = u;
    }
    const a = wid[t * 3], b = wid[t * 3 + 1], c = wid[t * 3 + 2];
    if (a === b || b === c || c === a) continue;
    const ux = wx[b] - wx[a], uy = wy[b] - wy[a], uz = wz[b] - wz[a];
    const vx = wx[c] - wx[a], vy = wy[c] - wy[a], vz = wz[c] - wz[a];
    const nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx;
    const len = Math.sqrt(nx * nx + ny * ny + nz * nz);
    if (!(len > 0)) continue;
    ax[a] += nx / len; ay[a] += ny / len; az[a] += nz / len;
    ax[b] += nx / len; ay[b] += ny / len; az[b] += nz / len;
    ax[c] += nx / len; ay[c] += ny / len; az[c] += nz / len;
  }

  const span = Math.max(1e-9, hi - lo);
  const color = new T.Color();
  for (let t = 0; t < nT; t++) {
    const rgb = heatRgb((triEdge[t] - lo) / span);
    color.setRGB(rgb[0] / 255, rgb[1] / 255, rgb[2] / 255, T.SRGBColorSpace);
    for (let c = 0; c < 3; c++) {
      const u = wid[t * 3 + c];
      const o = (t * 3 + c) * 3;
      P[o] = wx[u] * 0.001; P[o + 1] = wy[u] * 0.001; P[o + 2] = wz[u] * 0.001;
      const l = Math.sqrt(ax[u] * ax[u] + ay[u] * ay[u] + az[u] * az[u]) || 1;
      N[o] = ax[u] / l; N[o + 1] = ay[u] / l; N[o + 2] = az[u] / l;
      C[o] = color.r; C[o + 1] = color.g; C[o + 2] = color.b;
    }
  }
  const geo = new T.BufferGeometry();
  geo.setAttribute("position", new T.BufferAttribute(P, 3));
  geo.setAttribute("normal", new T.BufferAttribute(N, 3));
  geo.setAttribute("color", new T.BufferAttribute(C, 3));
  return geo;
}

// ── Ridge overlay geometry ───────────────────────────────────────────────────
// A per-triangle WireframeGeometry paints a translucent veil over the shaded horn once the mesh
// reaches ~10k triangles: every triangle edge is drawn, and shared edges are emitted twice. The
// line set below keeps the mesh's own face normals as the only source of truth but emits only
// edges whose two faces meet at a real dihedral angle, then caps the total so the result stays a
// crease drawing instead of a screen. Measured on the live run at 1400x900: mean horizontal
// luminance gradient 4.46 with ridges on (13.9 with the old wireframe, 2.50 with no overlay).
//
// The cap is per geometry, not per triangle: on a 30k-triangle shell ~1.6k creases is ~3.5% of
// the 45k half-edges, dense enough to read the form and sparse enough to leave the shading visible.
// Whole angle tie-groups are kept or dropped together, so a crease never stops halfway.
const RIDGE_MIN_DEG = 40;               // dihedral below this is shading, not a ridge
const RIDGE_SEG_CAP = 1600;            // target line budget for one horn
const RIDGE_TIE_OVERFLOW = 1.5;         // include a tie-group up to 1.5x the budget, never half of it
const RIDGE_BOUNDARY_FRACTION = 0.35;   // above this, unmatched edges are soup artefacts, not a rim
const RIDGE_OPACITY_GAIN = 2.0;         // 0.28 -> ~0.56: sparse creases need more ink than a full net
const ridgeCache = new WeakMap();       // BufferGeometry -> ridge line geometry (built once per mesh)
const meshEdgeCache = new WeakMap();    // BufferGeometry -> full triangle-edge line geometry

/** Pure normalizer for the persisted render settings (node-testable, never throws).
 *  Accepts the parsed object, the raw localStorage string, or junk; returns a fresh,
 *  in-range object. Unknown enums and non-finite/out-of-range light fall back/clamp. */
export function normalizeRenderPrefs(raw) {
  let o = raw;
  if (typeof o === "string") {
    try { o = JSON.parse(o); } catch (e) { o = null; }
  }
  if (!o || typeof o !== "object" || Array.isArray(o)) o = {};
  const surface = RENDER_SURFACES.indexOf(o.surface) >= 0 ? o.surface : "satin";
  const ridges = RENDER_RIDGES.indexOf(o.ridges) >= 0 ? o.ridges : "on";
  let light = typeof o.light === "number" ? o.light : Number(o.light);
  if (!isFinite(light)) light = 1.0;
  light = Math.min(2.0, Math.max(0.5, light));
  return { surface, ridges, light };
}

/** Current settings from localStorage; missing, corrupt or disabled storage -> defaults. */
function loadRenderPrefs() {
  try { return normalizeRenderPrefs(localStorage.getItem(RENDER_PREF_KEY)); }
  catch (e) { return normalizeRenderPrefs(null); }
}

/** Persist the (normalized) settings; storage failure is non-fatal. */
function saveRenderPrefs(prefs) {
  const p = normalizeRenderPrefs(prefs);
  try { localStorage.setItem(RENDER_PREF_KEY, JSON.stringify(p)); } catch (e) { /* private mode */ }
  return p;
}

/**
 * Build the ridge line geometry for one mesh, cached on that geometry object.
 *
 * The rule is the same one EdgesGeometry uses — weld coincident vertices, compare the normals of
 * the two faces sharing an edge — but the output is driven by the mesh's own sorted dihedral
 * angles instead of a fixed angle, because the three 3D surfaces feed two different mesh shapes:
 *
 *  - a connected shell (the run-detail / sandbox mesh): unmatched edges are the real rim, kept;
 *  - a stride-decimated evolution frame: ~one welded vertex per triangle, so most edges are
 *    unmatched decimation holes. EdgesGeometry emits all of them at every threshold (measured:
 *    ~30k segments even at 65°), which is the same screen the owner reported. Here they are
 *    dropped when they dominate the edge set, leaving only the surviving dihedral creases.
 *
 * Shared edges are emitted once (no double-blend), duplicate lines are impossible, and the total
 * is capped by taking the sharpest whole tie-group that fits RIDGE_SEG_CAP.
 */
function buildRidgeGeometry(geo) {
  const cached = ridgeCache.get(geo);
  if (cached) return cached;

  const pos = geo.getAttribute("position");
  const index = geo.getIndex();
  if (!pos || !index) {
    const empty = new THREE.BufferGeometry();
    ridgeCache.set(geo, empty);
    return empty;
  }
  const P = pos.array, I = index.array;
  const nTri = Math.floor(I.length / 3);
  const Q = 1e5;                                   // 0.01 mm in metres — the payload's own rounding
  const keyToUid = new Map();
  const vx = [], vy = [], vz = [];
  const weld = new Int32Array(pos.count);
  for (let i = 0; i < pos.count; i++) {
    const x = P[i * 3], y = P[i * 3 + 1], z = P[i * 3 + 2];
    const key = `${Math.round(x * Q)},${Math.round(y * Q)},${Math.round(z * Q)}`;
    let uid = keyToUid.get(key);
    if (uid === undefined) {
      uid = vx.length;
      keyToUid.set(key, uid);
      vx.push(x); vy.push(y); vz.push(z);
    }
    weld[i] = uid;
  }
  const U = Math.max(1, vx.length);

  // Face normals; |dot| accepts either winding so a mixed-winding mesh cannot explode the set.
  const nx = new Float32Array(nTri), ny = new Float32Array(nTri), nz = new Float32Array(nTri);
  const edgeFace = new Map();                      // min*U+max -> first face index, or -1 once paired
  const edgeA = [], edgeB = [], angle = [];
  for (let t = 0; t < nTri; t++) {
    const a = weld[I[t * 3]], b = weld[I[t * 3 + 1]], c = weld[I[t * 3 + 2]];
    if (a === b || b === c || c === a) continue;   // degenerate after welding
    const ax = vx[a], ay = vy[a], az = vz[a];
    const ux = vx[b] - ax, uy = vy[b] - ay, uz = vz[b] - az;
    const wx = vx[c] - ax, wy = vy[c] - ay, wz = vz[c] - az;
    let fx = uy * wz - uz * wy, fy = uz * wx - ux * wz, fz = ux * wy - uy * wx;
    const len = Math.sqrt(fx * fx + fy * fy + fz * fz);
    if (!(len > 0)) continue;
    fx /= len; fy /= len; fz /= len;
    nx[t] = fx; ny[t] = fy; nz[t] = fz;
    const corners = [a, b, c];
    for (let j = 0; j < 3; j++) {
      const p = corners[j], q = corners[(j + 1) % 3];
      const key = p < q ? p * U + q : q * U + p;
      const hit = edgeFace.get(key);
      if (hit === undefined) {
        edgeFace.set(key, t);
      } else if (hit >= 0) {
        const dot = nx[hit] * fx + ny[hit] * fy + nz[hit] * fz;
        // Only REAL folds (rim, throat lip, wall break) become ridges. Tessellation noise on a
        // smooth wall sits well under RIDGE_MIN_DEG and used to scribble the surface white.
        const ang = Math.acos(Math.min(1, Math.abs(dot))) * 180 / Math.PI;
        if (ang >= RIDGE_MIN_DEG) { angle.push(ang); edgeA.push(p); edgeB.push(q); }
        edgeFace.set(key, -1);                    // a third face on a non-manifold edge is ignored
      }
    }
  }

  // Unmatched edges: a rim on a connected shell, decimation holes on a triangle soup.
  const boundary = [];
  for (const [key, face] of edgeFace) {
    if (face >= 0) boundary.push(Math.floor(key / U), key % U);
  }
  const totalEdges = edgeFace.size || 1;
  const keepBoundary = (boundary.length / 2) / totalEdges <= RIDGE_BOUNDARY_FRACTION;
  const boundarySegs = keepBoundary ? boundary.length / 2 : 0;
  const budget = Math.max(0, RIDGE_SEG_CAP - boundarySegs);

  // Sharpest first; expand the cut to the whole tie-group unless that would blow the budget.
  const order = new Array(angle.length);
  for (let i = 0; i < order.length; i++) order[i] = i;
  order.sort((i, j) => angle[j] - angle[i]);
  let keep = Math.min(budget, order.length);
  if (keep > 0 && keep < order.length) {
    const cut = angle[order[keep - 1]];
    let above = 0;
    while (above < order.length && angle[order[above]] > cut) above++;
    let ties = 0;
    while (above + ties < order.length && angle[order[above + ties]] === cut) ties++;
    keep = above + ties > budget * RIDGE_TIE_OVERFLOW ? above : above + ties;
  }

  const out = new Float32Array((keep + boundarySegs) * 6);
  let o = 0;
  const put = (a, b) => {
    out[o++] = vx[a]; out[o++] = vy[a]; out[o++] = vz[a];
    out[o++] = vx[b]; out[o++] = vy[b]; out[o++] = vz[b];
  };
  for (let i = 0; i < keep; i++) { const e = order[i]; put(edgeA[e], edgeB[e]); }
  if (keepBoundary) for (let i = 0; i < boundary.length; i += 2) put(boundary[i], boundary[i + 1]);

  const ridge = new THREE.BufferGeometry();
  ridge.setAttribute("position", new THREE.BufferAttribute(out, 3));
  // Honest per-geometry facts for debugging/inspection; no rendering depends on them.
  ridge.userData.ridgeSegments = keep + boundarySegs;
  ridge.userData.ridgeThresholdDeg = keep ? +angle[order[keep - 1]].toFixed(2) : null;
  ridge.userData.ridgeBoundaryKept = keepBoundary;
  ridgeCache.set(geo, ridge);
  return ridge;
}

/**
 * Build the FULL triangle-edge line geometry for one mesh, cached on that geometry object.
 *
 * The ridge overlay above deliberately keeps only dihedral creases, so on a smooth horn wall it is
 * nearly empty. This one is the tessellation itself: weld coincident positions exactly like the
 * ridge pass (same 0.01 mm rounding, so the mirrored seams collapse), then emit every unique
 * triangle edge once — no dihedral filter, no segment cap. Degenerate triangles are skipped, so
 * no zero-length line ever lands in the buffer.
 *
 * Draw it depth-tested with a small renderOrder (after the opaque surface): the edges are coincident
 * with the shaded triangles, and the surface material carries a polygonOffset so the coincident
 * lines win the depth test. That keeps the solid readable and paints the tessellation only over the
 * faces you can actually see (not as an x-ray through the far wall).
 * Shared by init3d, init3dFrames, hw3d.js and sandbox.js; `THREE` comes from loadThree().
 */
export function buildMeshEdgeGeometry(geo) {
  const cached = meshEdgeCache.get(geo);
  if (cached) return cached;

  const pos = geo.getAttribute("position");
  const index = geo.getIndex();
  if (!pos || !index) {
    const empty = new THREE.BufferGeometry();
    meshEdgeCache.set(geo, empty);
    return empty;
  }
  const P = pos.array, I = index.array;
  const nTri = Math.floor(I.length / 3);
  const Q = 1e5;                                   // 0.01 mm in metres — the payload's own rounding
  const keyToUid = new Map();
  const vx = [], vy = [], vz = [];
  const weld = new Int32Array(pos.count);
  for (let i = 0; i < pos.count; i++) {
    const x = P[i * 3], y = P[i * 3 + 1], z = P[i * 3 + 2];
    const key = `${Math.round(x * Q)},${Math.round(y * Q)},${Math.round(z * Q)}`;
    let uid = keyToUid.get(key);
    if (uid === undefined) {
      uid = vx.length;
      keyToUid.set(key, uid);
      vx.push(x); vy.push(y); vz.push(z);
    }
    weld[i] = uid;
  }
  const U = Math.max(1, vx.length);

  const seen = new Set();                          // min*U+max -> already emitted (double lines impossible)
  const edgeA = [], edgeB = [];
  for (let t = 0; t < nTri; t++) {
    const a = weld[I[t * 3]], b = weld[I[t * 3 + 1]], c = weld[I[t * 3 + 2]];
    if (a === b || b === c || c === a) continue;   // degenerate after welding
    const corners = [a, b, c];
    for (let j = 0; j < 3; j++) {
      const p = corners[j], q = corners[(j + 1) % 3];
      const key = p < q ? p * U + q : q * U + p;
      if (seen.has(key)) continue;
      seen.add(key);
      edgeA.push(p); edgeB.push(q);
    }
  }

  const out = new Float32Array(edgeA.length * 6);
  let o = 0;
  for (let e = 0; e < edgeA.length; e++) {
    const a = edgeA[e], b = edgeB[e];
    out[o++] = vx[a]; out[o++] = vy[a]; out[o++] = vz[a];
    out[o++] = vx[b]; out[o++] = vy[b]; out[o++] = vz[b];
  }
  const edges = new THREE.BufferGeometry();
  edges.setAttribute("position", new THREE.BufferAttribute(out, 3));
  // Honest per-geometry fact for debugging/inspection; no rendering depends on it.
  edges.userData.edgeSegments = edgeA.length;
  meshEdgeCache.set(geo, edges);
  return edges;
}

/** Drop one cached triangle-edge geometry (callers disposing its source geometry pair this with
 *  meshEdgeGeo.dispose(), exactly like ridgeCache.delete(geo) pairs with wireGeo.dispose()). */
export function releaseMeshEdgeGeometry(geo) {
  meshEdgeCache.delete(geo);
}

/** Resolve one mesh-net mode to { color: THREE.Color, opacity } — literal, theme-independent
 *  values (a theme token made "black" render near-white on the dark theme). Returns null for
 *  "off". Callers copy the colour and opacity onto the net material in place. */
export function meshNetLook(mode) {
  const s = MESH_NET_STYLES[mode];
  if (!s) return null;
  let color;
  try { color = new THREE.Color(s.hex); } catch (e) { color = new THREE.Color(0x8a949a); }
  return { color, opacity: s.opacity };
}

/**
 * Shared, anti-aliased mesh net over the shaded horn (one factory for every 3D surface).
 *
 * Preferred: three.js fat lines (LineSegmentsGeometry + LineSegments2 + LineMaterial), which draw
 * an anti-aliased ~1 px screen-space ribbon instead of a hard aliased GL line. The addons are
 * dynamic imports so a CDN/offline failure degrades silently to a plain LineSegments with the same
 * colour/opacity — never a blank panel and never a thrown error.
 *
 * Screen-space density fade (fat path only): the LineMaterial shaders are patched in
 * onBeforeCompile to compute each segment's projected length in CSS pixels and multiply the line's
 * alpha by smoothstep(1.5, 5.0, px). Where neighbouring edges compress (grazing walls, throat, far
 * side) or the segment projects shorter than ~1.5 px, the net quietly fades out; it also doubles as
 * a depth cue. The patch is applied only when every expected r160 shader substring is present, and
 * the plain LineBasicMaterial fallback has no per-segment data, so it stays unfaded.
 *
 * Returns { object, material, setPositions(Float32Array), setSize(w, h), dispose() }:
 *  - setPositions takes the flat xyz,xyz pairs of buildMeshEdgeGeometry's position array;
 *  - setSize must be called with the renderer's CSS-pixel size (LineMaterial.resolution is what
 *    turns linewidth into pixels AND feeds the fade) and again on every resize;
 *  - the caller sets material.color/opacity in place (meshNetLook) and adds/removes object.
 *
 * depthTest stays ON: with the horn surface pushed back by polygonOffset 2/2 the net is a
 * depth-tested decal on the visible solid (solid + mesh), never an x-ray through the far wall.
 */
export async function createMeshNet(opts = {}) {
  const T = THREE;                                   // set by loadThree() before any scene builds
  const color = opts.color != null ? opts.color : WIRE_COLOR;
  const opacity = opts.opacity != null ? opts.opacity : 0.22;
  const linewidth = opts.linewidth != null ? opts.linewidth : MESH_NET_LINE_WIDTH;

  let object = null, material = null, geometry = null, fat = false;
  try {
    const [gMod, oMod, mMod] = await Promise.all([
      import("three/addons/lines/LineSegmentsGeometry.js"),
      import("three/addons/lines/LineSegments2.js"),
      import("three/addons/lines/LineMaterial.js"),
    ]);
    geometry = new gMod.LineSegmentsGeometry();
    material = new mMod.LineMaterial({
      color, linewidth, worldUnits: false,
      transparent: true, opacity, depthTest: true, depthWrite: false,
    });
    // ── Screen-space density fade, patched into the pinned r160 LineMaterial shaders ──
    // Vertex: every segment already has clipStart/clipEnd right after the NDC lines; the
    // projected length in CSS pixels is |Δndc * resolution / 2|.
    // Fragment: alpha is the variable actually written into gl_FragColor.a, so attenuate it just
    // before diffuseColor/gl_FragColor are built. Only patch when ALL four substrings match —
    // never leave a fragment varying that the vertex stage does not declare.
    material.onBeforeCompile = shader => {
      const V_RES = "uniform vec2 resolution;";
      const V_NDC = "vec3 ndcEnd = clipEnd.xyz / clipEnd.w;";
      const F_DECL = "uniform float linewidth;";
      const F_DIFF = "vec4 diffuseColor = vec4( diffuse, alpha );";
      if (!(shader.vertexShader.includes(V_RES) && shader.vertexShader.includes(V_NDC) &&
            shader.fragmentShader.includes(F_DECL) && shader.fragmentShader.includes(F_DIFF))) {
        return;                                      // unknown shader: leave the net exactly as built
      }
      shader.uniforms.uNetFadeMin = { value: MESH_NET_FADE_MIN };
      shader.uniforms.uNetFadeMax = { value: MESH_NET_FADE_MAX };
      shader.vertexShader = shader.vertexShader
        .replace(V_RES, "uniform vec2 resolution;\nvarying float vNetSegPx;")
        .replace(V_NDC, "vec3 ndcEnd = clipEnd.xyz / clipEnd.w;\n" +
          "vNetSegPx = length((clipEnd.xy / clipEnd.w - clipStart.xy / clipStart.w) * resolution * 0.5);");
      shader.fragmentShader = shader.fragmentShader
        .replace(F_DECL, "uniform float linewidth;\nvarying float vNetSegPx;\n" +
          "uniform float uNetFadeMin;\nuniform float uNetFadeMax;")
        .replace(F_DIFF, "alpha *= smoothstep( uNetFadeMin, uNetFadeMax, vNetSegPx );\n" +
          "vec4 diffuseColor = vec4( diffuse, alpha );");
    };
    material.customProgramCacheKey = () => "hl-mesh-net-fade-v1";
    object = new oMod.LineSegments2(geometry, material);
    fat = true;
  } catch (e) {
    // No per-segment data here: the 1 px LineBasicMaterial net is left unfaded (and still correct).
    geometry = new T.BufferGeometry();
    material = new T.LineBasicMaterial({
      color, transparent: true, opacity, depthTest: true, depthWrite: false,
    });
    object = new T.LineSegments(geometry, material);
  }
  object.frustumCulled = false;                      // empty/instanced bounds are not worth trusting
  object.renderOrder = 3;                            // after the opaque surface

  return {
    object,
    material,
    fat,
    setPositions(arr) {
      const data = (arr && arr.length >= 6) ? arr : new Float32Array(0);
      if (fat) {
        // Free the previous frame's GPU buffers before replacing the instanced attributes.
        try { geometry.dispose(); } catch (e) { /* never rendered yet */ }
        geometry.setPositions(data);
      } else {
        geometry.setAttribute("position", new T.BufferAttribute(data, 3));
        geometry.computeBoundingSphere();
      }
    },
    setSize(w, h) {
      if (fat && material.resolution) {
        material.resolution.set(Math.max(1, w || 1), Math.max(1, h || 1));
      }
    },
    dispose() {
      try { geometry.dispose(); } catch (e) { /* already gone */ }
      try { material.dispose(); } catch (e) { /* already gone */ }
    },
  };
}

/** Apply a preset in place — material, ridgeline opacity/visibility and the four-light rig.
 *  No scene rebuild: the same objects are mutated so orbit camera/state stay live. */
function applyRenderLook(ctx, prefs) {
  const p = normalizeRenderPrefs(prefs);
  const preset = RENDER_PRESETS[p.surface] || RENDER_PRESETS.satin;
  const { mat, wire, wireMat, scene, lights } = ctx;  mat.color.setHex(HORN_BASE_COLOR).multiplyScalar(preset.colorScale);
  mat.roughness = preset.roughness;
  mat.metalness = preset.metalness;
  const ridgeOpacity = p.ridges === "thin" ? 0.12 : preset.wireOpacity;
  wireMat.opacity = ridgeOpacity * RIDGE_OPACITY_GAIN;
  if (p.ridges === "off") scene.remove(wire);
  else scene.add(wire);
  lights.key.intensity = preset.light.key * p.light;
  lights.fill.intensity = preset.light.fill * p.light;
  lights.rim.intensity = preset.light.rim * p.light;
  lights.hemi.intensity = preset.light.hemi;   // ambient-relative, not part of the multiplier

  // Look extras: light angle (rig spun about the horn's z axis) and iso-depth contours.
  const x = normalizeLookExtras(prefs);
  if (ctx.center && ctx.maxDim) {
    const a = x.angle * Math.PI / 180, c = Math.cos(a), s = Math.sin(a);
    const put = (L, b) => L.position.set(
      ctx.center.x + (b[0] * c - b[1] * s) * ctx.maxDim,
      ctx.center.y + (b[0] * s + b[1] * c) * ctx.maxDim,
      ctx.center.z + b[2] * ctx.maxDim);
    put(lights.key, KEY_BASE); put(lights.fill, FILL_BASE); put(lights.rim, RIM_BASE);
  }
  if (ctx.contourU) ctx.contourU.value = x.contours === "on" ? (ctx.contourStep || 0) : 0;

  // Triangle-edge net: colour/opacity and visibility are mutated in place, never rebuilt. Any
  // colour mode turns the net on; "off" leaves the solid on its own.
  if (ctx.meshNet) {
    const look = meshNetLook(x.mesh);
    if (!look) {
      scene.remove(ctx.meshNet.object);
    } else {
      ctx.meshNet.material.color.copy(look.color);
      ctx.meshNet.material.opacity = look.opacity;
      scene.add(ctx.meshNet.object);
    }
  }
}

/** Minimal HTML escaper for the control labels (same contract as app.js::esc). */
function esc(v) {
  return String(v).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

/**
 * Append the compact render-settings chip INSIDE `container` (absolute overlay). Both 3D surfaces
 * (init3d and init3dFrames) call this. Changes apply immediately through onChange(prefs) and are
 * persisted for every next init. The chip is pointer-events:auto deliberately — unlike the static
 * enclosure caption (pointer-events:none) — because its selects/slider must stay clickable while
 * OrbitControls listens on the canvas. app.js's shadows toggle wipes the container via
 * container.innerHTML = "" before re-calling init3d, so this chip is re-added on every re-init.
 */
function applyRenderControls(container, onChange) {
  const prefs = Object.assign(loadRenderPrefs(), loadLookExtras());
  if (getComputedStyle(container).position === "static") container.style.position = "relative";
  const chip = document.createElement("div");
  chip.style.cssText = "position:absolute;top:8px;right:8px;z-index:2;display:flex;" +
    "align-items:center;flex-wrap:wrap;gap:4px 10px;max-width:calc(100% - 16px);padding:3px 8px;" +
    "font-family:var(--f-mono);font-size:0.72rem;line-height:1.5;border-radius:4px;" +
    "color:var(--ink,#222);background:var(--surface,#fff);border:1px solid var(--rule,#ccc);" +
    "opacity:0.94;pointer-events:auto";
  const lblStyle = "display:inline-flex;align-items:center;gap:4px";
  const selStyle = "font:inherit;font-size:0.72rem;background:var(--surface,#fff);color:var(--ink,#222);" +
    "border:1px solid var(--rule,#ccc);border-radius:4px;padding:0 3px";
  const opt = (v, cur, label) =>
    `<option value="${esc(v)}"${v === cur ? " selected" : ""}>${esc(label)}</option>`;
  chip.innerHTML =
    `<label style="${lblStyle}">surface<select data-v3d-pref="surface" style="${selStyle}">` +
      RENDER_SURFACES.map(s => opt(s, prefs.surface, s === "satin" ? "satin (default)" : s)).join("") +
    `</select></label>` +
    `<label style="${lblStyle}">ridges<select data-v3d-pref="ridges" style="${selStyle}">` +
      RENDER_RIDGES.map(s => opt(s, prefs.ridges, s === "on" ? "on (default)" : s)).join("") +
    `</select></label>` +
    `<label style="${lblStyle}" title="draw every triangle edge over the surface in white, black or gray: see the tessellation the shading covers">mesh<select data-v3d-pref="mesh" style="${selStyle}">` +
      MESH_NET_MODES.map(m => opt(m, prefs.mesh, m === "off" ? "off (default)" : m)).join("") +
    `</select></label>` +
    `<label style="${lblStyle}" title="iso-depth lines: make slow curvature and slope readable">depth lines<select data-v3d-pref="contours" style="${selStyle}">` +
      opt("off", prefs.contours, "off") + opt("on", prefs.contours, "on") +
    `</select></label>` +
    `<label style="${lblStyle}">light` +
      `<input type="range" data-v3d-pref="light" min="0.5" max="2" step="0.1" ` +
        `value="${esc(prefs.light)}" aria-label="light intensity multiplier" ` +
        `style="width:72px;accent-color:var(--accent,#0d6e7a)">` +
      `<span data-v3d-light-val>${esc(prefs.light)}×</span></label>` +
    `<label style="${lblStyle}" title="spin the light around the horn axis: a low raking angle shows gentle changes">angle` +
      `<input type="range" data-v3d-pref="angle" min="0" max="345" step="15" ` +
        `value="${esc(prefs.angle)}" aria-label="light direction, degrees about the horn axis" ` +
        `style="width:72px;accent-color:var(--accent,#0d6e7a)">` +
      `<span data-v3d-angle-val>${esc(prefs.angle)}°</span></label>`;
  container.appendChild(chip);

  const surfaceSel = chip.querySelector('[data-v3d-pref="surface"]');
  const ridgeSel = chip.querySelector('[data-v3d-pref="ridges"]');
  const lightRange = chip.querySelector('[data-v3d-pref="light"]');
  const lightVal = chip.querySelector("[data-v3d-light-val]");
  const contourSel = chip.querySelector('[data-v3d-pref="contours"]');
  const meshSel = chip.querySelector('[data-v3d-pref="mesh"]');
  const angleRange = chip.querySelector('[data-v3d-pref="angle"]');
  const angleVal = chip.querySelector("[data-v3d-angle-val]");
  const commit = () => {
    const next = saveRenderPrefs({
      surface: surfaceSel.value,
      ridges: ridgeSel.value,
      light: Number(lightRange.value),
    });
    const extra = saveLookExtras({
      contours: contourSel.value,
      angle: Number(angleRange.value),
      mesh: meshSel.value,
    });
    lightVal.textContent = `${next.light}×`;
    angleVal.textContent = `${extra.angle}°`;
    onChange(Object.assign(next, extra));
  };
  surfaceSel.addEventListener("change", commit);
  ridgeSel.addEventListener("change", commit);
  contourSel.addEventListener("change", commit);
  meshSel.addEventListener("change", commit);
  lightRange.addEventListener("input", commit);
  angleRange.addEventListener("input", commit);
  return chip;
}

/**
 * Render a 2D wall profile as a fallback SVG.
 * profile: {h:[[z,r],...], v:[[z,r],...]} from run detail.
 */
function render2DFallback(container, profile, seedProfile) {
  container.innerHTML = "";
  const msg = document.createElement("div");
  msg.className = "view3d-fallback";
  if (!profile) {
    msg.textContent = "3D view unavailable (three.js not loaded) and no profile data.";
    container.appendChild(msg);
    return;
  }
  const NS = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(NS, "svg");
  svg.style.width = "100%"; svg.style.height = "100%";

  const h = (profile || {}).h || [], v = (profile || {}).v || [];
  const sh = (seedProfile || {}).h || [], sv = (seedProfile || {}).v || [];
  const all = [...h, ...v, ...sh, ...sv];
  if (!all.length) { msg.textContent = "No profile data."; container.appendChild(msg); return; }

  const rs = all.map(p => Math.abs(p[1])), zs = all.map(p => p[0]);
  const rmax = Math.max(...rs) * 1.1 || 200;
  const zmin = Math.min(...zs) - 5, zmax = Math.max(...zs) + 5;

  const W = 600, H = 400, m = {l:40,r:10,t:10,b:30};
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);

  const X = r => m.l + (r + rmax) / (2 * rmax) * (W - m.l - m.r);
  const Y = z => H - m.b - (z - zmin) / (zmax - zmin) * (H - m.t - m.b);

  // axes
  const mkLine = (x1,y1,x2,y2,stroke,dash) => {
    const l = document.createElementNS(NS,"line");
    l.setAttribute("x1",x1); l.setAttribute("y1",y1);
    l.setAttribute("x2",x2); l.setAttribute("y2",y2);
    l.setAttribute("stroke",stroke||"var(--rule)");
    if (dash) l.setAttribute("stroke-dasharray","4 3");
    svg.appendChild(l);
  };
  mkLine(X(0),m.t,X(0),H-m.b,"var(--rule)",false);

  const drawPts = (pts, sgn, color, dash, w) => {
    const pp = pts.map(p => [X(sgn * Math.abs(p[1])), Y(p[0])]).filter(p => isFinite(p[0]) && isFinite(p[1]));
    if (pp.length < 2) return;
    const path = document.createElementNS(NS, "path");
    path.setAttribute("d", pp.map((p,i) => (i?"L":"M")+p[0].toFixed(1)+","+p[1].toFixed(1)).join(""));
    path.setAttribute("fill","none"); path.setAttribute("stroke",color);
    path.setAttribute("stroke-width", String(w || 2));
    if (dash) path.setAttribute("stroke-dasharray","5 3");
    svg.appendChild(path);
  };

  const cs = getComputedStyle(document.documentElement);
  const seedCol = cs.getPropertyValue("--seed").trim() || "#a3713a";
  const bestCol = cs.getPropertyValue("--best").trim() || "#0d6e7a";
  // dashed start outline first (= under the best stroke), then the solid best outline
  if (sh.length || sv.length) { drawPts(sh, 1, seedCol, true, 2); drawPts(sv, -1, seedCol, true, 2); }
  drawPts(h, 1, bestCol, false, 2.5);
  drawPts(v, -1, bestCol, true, 2.5);

  container.appendChild(svg);
  const lbl = document.createElement("div");
  lbl.style.cssText = "position:absolute;bottom:8px;right:12px;font-family:var(--f-mono);font-size:0.7rem;color:var(--muted);";
  lbl.textContent = "2D fallback — three.js unavailable";
  container.style.position = "relative";
  container.appendChild(lbl);
}

/** Defensive label for one mounting value: finite numbers as-is, non-empty strings trimmed, anything
 *  else null (the caption then omits that token rather than printing "undefined"). */
function mountNum(v) {
  if (typeof v === "number" && isFinite(v)) return String(v);
  if (typeof v === "string" && v.trim() !== "") return v.trim();
  return null;
}

/** Caption body for `mesh_meta.mounting`: prefer the brief's `normalized` block (depth_mm, edge_mm,
 *  margins_mm {l,t,r,b}), else the mesher's own `mesher` block (depth_mm, edge_mm, space_*_mm).
 *  Returns null when neither block carries any of those values. */
function mountingDetail(mounting) {
  const norm = mounting && typeof mounting.normalized === "object" && mounting.normalized
    ? mounting.normalized : null;
  const mesher = mounting && typeof mounting.mesher === "object" && mounting.mesher
    ? mounting.mesher : null;
  for (const src of [norm, mesher]) {
    if (!src) continue;
    const parts = [];
    const depth = mountNum(src.depth_mm), edge = mountNum(src.edge_mm);
    if (depth != null) parts.push(`depth ${depth} mm`);
    if (edge != null) parts.push(`edge ${edge} mm`);
    const mg = src === norm
      ? (src.margins_mm && typeof src.margins_mm === "object" ? src.margins_mm : null)
      : { l: src.space_l_mm, t: src.space_t_mm, r: src.space_r_mm, b: src.space_b_mm };
    const mt = [];
    if (mg) for (const k of ["l", "t", "r", "b"]) {
      const val = mountNum(mg[k]);
      if (val != null) mt.push(`${k} ${val}`);
    }
    if (mt.length) parts.push(`margins ${mt.join(" ")} mm`);
    if (parts.length) return parts.join(" · ");
  }
  return null;
}

/**
 * Init the 3D view in `container`.
 * meshData: { quadrants, verts: [x,y,z,...], tris: [i,j,k,...], mounting? }
 * profile (optional): best design profile for 2D fallback.
 */
export async function init3d(container, meshData, profile, seedProfile, shadows = true, opts = {}) {
  container.innerHTML = "";

  const ok = await loadThree();
  if (!ok) { render2DFallback(container, profile, seedProfile); return; }

  const { verts: rawVerts, tris: rawTris, quadrants } = meshData || {};
  if (!rawVerts || !rawVerts.length || !rawTris || !rawTris.length) {
    render2DFallback(container, profile, seedProfile); return;
  }
  const { verts, tris, triSrc } = mirrorMesh(rawVerts, rawTris, quadrants);

  const cs = getComputedStyle(document.documentElement);
  const renderPrefs = Object.assign(loadRenderPrefs(), loadLookExtras());
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(
    cs.getPropertyValue("--viz-canvas").trim() || cs.getPropertyValue("--surface").trim() || "#ffffff"
  );

  // Geometry: welded across the mirror seams, crease-aware smooth normals (no dark seam lines,
  // no per-triangle facets on the gentle wall).
  const geo = buildSmoothGeometry(THREE, verts, tris);

  // Scale: verts are in mm — scale to metres for display
  geo.scale(0.001, 0.001, 0.001);

  // Bounding-box fit first — lights, shadow rig and camera all derive from it
  geo.computeBoundingBox();
  const box = geo.boundingBox;
  const center = new THREE.Vector3();
  box.getCenter(center);
  const size = new THREE.Vector3();
  box.getSize(size);
  const maxDim = Math.max(size.x, size.y, size.z);
  if (!isFinite(maxDim) || maxDim <= 0) { render2DFallback(container, profile, seedProfile); return; }

  // WP12 enclosure mounting: the dashed outline is deliberately "the solved mesh's own extent" —
  // sized exactly from the mirrored mesh's bounding box above, never invented enclosure geometry.
  // Absent `mounting` (every free run) renders nothing, so free-run 3D stays bit-identical.
  const mounting = (meshData || {}).mounting;
  const hasMounting = !!mounting && typeof mounting === "object" && Object.keys(mounting).length > 0;
  let mountEdges = null, mountLineMat = null;
  if (hasMounting) {
    const rule = cs.getPropertyValue("--rule").trim();
    const mountBox = new THREE.BoxGeometry(size.x, size.y, size.z);
    mountEdges = new THREE.EdgesGeometry(mountBox);
    mountBox.dispose();
    mountLineMat = new THREE.LineDashedMaterial({
      color: rule ? new THREE.Color(rule) : 0x8fa3ad,
      dashSize: 0.02 * maxDim, gapSize: 0.012 * maxDim,
      transparent: true, opacity: 0.9,
    });
    const mountOutline = new THREE.LineSegments(mountEdges, mountLineMat);
    mountOutline.position.copy(center);
    mountOutline.computeLineDistances();
    scene.add(mountOutline);
  }

  // Solid mesh — light neutral grey (form over decoration), opaque.
  // polygonOffset nudges the surface a hair back so the coincident ridge/mesh-edge lines win the
  // depth test while the surface still hides the far wall (no x-ray); the line materials do not
  // write depth (they are overlays).
  const mat = new THREE.MeshStandardMaterial({
    color: HORN_BASE_COLOR, roughness: 0.55, metalness: 0.05,
    side: THREE.DoubleSide,   // interior visibility of the open mouth (mirror windings are already consistent)
    transparent: false,
    polygonOffset: true, polygonOffsetFactor: 2, polygonOffsetUnits: 2,
  });
  const contourU = installContours(mat);
  const mesh = new THREE.Mesh(geo, mat);
  mesh.castShadow = mesh.receiveShadow = shadows;
  scene.add(mesh);

  // Ridge overlay: the mesh's own dihedral creases (mouth rim, throat, wall breaks), not one line
  // per triangle. Default on (owner override, not shadow-gated); "thin"/"off" apply below.
  const wireGeo = buildRidgeGeometry(geo);
  const wireMat = new THREE.LineBasicMaterial({
    color: WIRE_COLOR, transparent: true, opacity: 0.28,
    depthWrite: false,   // an overlay must not occlude the shaded surface or its own creases
  });
  const wire = new THREE.LineSegments(wireGeo, wireMat);
  scene.add(wire);

  // Triangle-edge net: the tessellation itself, every unique edge once, drawn as anti-aliased fat
  // lines (falling back to plain 1 px lines offline). Off by default; the chip's "mesh" select
  // sets the colour (white/black/gray) and adds/removes it in place. Depth-tested, with the
  // surface's polygonOffset 2/2 pushing the coincident triangles a hair back, so the lines land ON
  // the visible solid — solid + mesh, never an x-ray.
  const meshEdgeGeo = buildMeshEdgeGeometry(geo);
  const meshNet = await createMeshNet();
  meshNet.setPositions(meshEdgeGeo.getAttribute("position").array);

  // Lighting rig: hemisphere keeps the shadow side readable, key models the form,
  // fill lifts the dark flank, rim traces the far silhouette against the canvas
  const hemi = new THREE.HemisphereLight(LIGHT_COLOR, HEMI_GROUND_COLOR, 0.45);
  scene.add(hemi);
  const key = new THREE.DirectionalLight(LIGHT_COLOR, 1.15);
  key.position.copy(center).addScaledVector(new THREE.Vector3(1.6, 2.2, 1.8), maxDim);
  const fillL = new THREE.DirectionalLight(LIGHT_COLOR, 0.35);
  fillL.position.copy(center).addScaledVector(new THREE.Vector3(-1.8, 0.6, 1.2), maxDim);
  const rim = new THREE.DirectionalLight(LIGHT_COLOR, 0.85);
  rim.position.copy(center).addScaledVector(new THREE.Vector3(-1.2, -1.0, -2.2), maxDim);
  scene.add(key, fillL, rim);

  // Apply the persisted preset in place (satin + on + 1.0x reproduces the pre-settings look).
  const lights = { hemi, key, fill: fillL, rim };
  const lookCtx = { mat, wire, wireMat, meshNet, scene, lights, center, maxDim, contourU,
                    contourStep: niceContourStep(size.z) };
  applyRenderLook(lookCtx, renderPrefs);

  // Shadow rig (optional, toggled): the thin double-sided wall needs a normalBias
  let ground = null, groundGeo = null, groundMat = null;
  if (shadows) {
    key.castShadow = true;
    key.target.position.copy(center);
    scene.add(key.target);
    key.shadow.mapSize.set(1024, 1024);
    key.shadow.camera.left = -0.8 * maxDim; key.shadow.camera.right = 0.8 * maxDim;
    key.shadow.camera.top = 0.8 * maxDim;   key.shadow.camera.bottom = -0.8 * maxDim;
    key.shadow.camera.near = 0.1;           key.shadow.camera.far = 4 * maxDim;
    key.shadow.normalBias = 0.01 * maxDim;  key.shadow.bias = 0;
    groundGeo = new THREE.PlaneGeometry(2.6 * maxDim, 2.6 * maxDim);
    groundMat = new THREE.ShadowMaterial({ opacity: 0.22 });
    ground = new THREE.Mesh(groundGeo, groundMat);
    ground.position.set(center.x, box.min.y - 0.02 * maxDim, center.z);
    ground.rotation.x = -Math.PI / 2;
    ground.receiveShadow = true;
    scene.add(ground);
  }

  const w = container.clientWidth || 600, h = container.clientHeight || 400;
  const camera = new THREE.PerspectiveCamera(45, w / h, 0.001, 100);
  // Desktop framing is pinned to this exact position (2.094 * maxDim from the centre). Narrow
  // canvases shrink the horizontal FOV, so the fit below may move the camera further out along the
  // same ray; at >= 16:9 this copy is used unchanged.
  const basePos = new THREE.Vector3(center.x + maxDim * 1.2, center.y + maxDim * 0.8,
                                    center.z + maxDim * 1.5);
  const camDir = basePos.clone().sub(center).normalize();
  const baseDist = basePos.distanceTo(center);
  camera.position.copy(basePos);
  camera.lookAt(center);
  camera.updateProjectionMatrix();

  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(window.devicePixelRatio);
  renderer.setSize(w, h);
  meshNet.setSize(w, h);                 // LineMaterial.linewidth is in CSS pixels
  if (shadows) { renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap; }
  container.appendChild(renderer.domElement);

  // Enclosure caption, OVER the canvas (both host containers are fixed-height with
  // overflow:hidden — #inline-3d height:300px, #view3d-wrap aspect-ratio — so a block-level
  // caption appended after the canvas would be clipped): a themed overlay chip in the canvas
  // corner, pointer-events:none so orbit controls stay live. It joins the container's child
  // list (route()'s disposal sweep removes the whole container) and carries no data-v3d marker.
  if (hasMounting) {
    const cap = document.createElement("div");
    cap.style.cssText = "position:absolute;left:8px;bottom:6px;max-width:calc(100% - 16px);" +
      "padding:2px 8px;font-size:0.8rem;border-radius:4px;pointer-events:none;" +
      "color:var(--ink,#222);background:var(--surface,#fff);border:1px solid var(--rule,#ccc);opacity:0.92";
    const detail = mountingDetail(mounting);
    cap.textContent = "enclosure outline = the solved mesh's extent — " +
      (detail || "enclosure-mounted (mesh_meta.mounting)");
    container.appendChild(cap);
  }

  // Render-settings chip (surface / ridges / light) — additive overlay, clickable.
  applyRenderControls(container, p => applyRenderLook(lookCtx, p));

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.target.copy(center);
  controls.update();

  // ── Narrow-canvas framing ────────────────────────────────────────────────────────────────────
  // The camera is framed for the 16:9 stage. On a tall/narrow canvas the fixed 45° vertical FOV
  // shrinks the horizontal FOV and the horn can leave the frame, so project the model's own bounds
  // at the current aspect and move the camera out along the SAME ray until they sit inside a small
  // margin. At >= 16:9 the exact desktop position is reused (no refit, no framing change).
  const REF_ASPECT = 16 / 9;
  const FIT_NDC = 0.80;            // keep 10 % of the full canvas clear on the tight side
  const fitCorners = [];
  for (const x of [box.min.x, box.max.x])
    for (const y of [box.min.y, box.max.y])
      for (const z of [box.min.z, box.max.z])
        fitCorners.push(new THREE.Vector3(x, y, z));
  const fitProbe = new THREE.Vector3();
  const posAttr = geo.getAttribute("position");

  const maxNdcAt = dist => {
    camera.position.copy(center).addScaledVector(camDir, dist);
    camera.lookAt(center);
    camera.updateMatrixWorld();
    camera.updateProjectionMatrix();
    let m = 0;
    for (const c of fitCorners) {
      fitProbe.copy(c).project(camera);
      m = Math.max(m, Math.abs(fitProbe.x), Math.abs(fitProbe.y));
    }
    return m;
  };

  let cameraTouched = false;       // a resize never overrides a view the user has moved
  controls.addEventListener("start", () => { cameraTouched = true; });

  const fitCamera = () => {
    const aspect = camera.aspect;
    if (!(aspect > 0) || !(baseDist > 0)) return;   // hidden/zero-size container: keep the pose
    let dist = baseDist;
    let bboxMax = null;
    if (aspect < REF_ASPECT - 0.01) {
      bboxMax = maxNdcAt(dist);
      for (let i = 0; i < 4 && bboxMax > FIT_NDC; i++) {
        dist *= bboxMax / FIT_NDC;
        bboxMax = maxNdcAt(dist);
      }
    }
    // >= 16:9 keeps the byte-identical desktop position; narrow canvases use the fitted distance.
    if (dist === baseDist) camera.position.copy(basePos);
    else camera.position.copy(center).addScaledVector(camDir, dist);
    camera.lookAt(center);
    camera.updateMatrixWorld();
    camera.updateProjectionMatrix();

    let vx0 = Infinity, vx1 = -Infinity, vy0 = Infinity, vy1 = -Infinity;
    for (let i = 0; i < posAttr.count; i++) {
      fitProbe.set(posAttr.getX(i), posAttr.getY(i), posAttr.getZ(i)).project(camera);
      vx0 = Math.min(vx0, fitProbe.x); vx1 = Math.max(vx1, fitProbe.x);
      vy0 = Math.min(vy0, fitProbe.y); vy1 = Math.max(vy1, fitProbe.y);
    }
    container._view3dFit = {
      aspect, ref_aspect: REF_ASPECT, fit_ndc: FIT_NDC,
      base_dist_m: baseDist, dist_m: dist, refit: dist !== baseDist,
      bbox_max_ndc: bboxMax,
      vertex_ndc: { x: [vx0, vx1], y: [vy0, vy1] },
      vertex_max_ndc: Math.max(Math.abs(vx0), Math.abs(vx1), Math.abs(vy0), Math.abs(vy1)),
    };
  };
  fitCamera();

  // Resize observer
  const ro = new ResizeObserver(entries => {
    for (const e of entries) {
      const { width, height } = e.contentRect;
      if (!(width > 0 && height > 0)) continue;   // transient zero-size (hidden/teardown)
      renderer.setSize(width, height);
      meshNet.setSize(width, height);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      if (!cameraTouched) fitCamera();
    }
  });
  ro.observe(container);

  let raf;
  function animate() {
    raf = requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
  }
  animate();

  // ── Mesh-density overlay (lazy: the caller fetches the density payload only on demand) ───────
  // Colours the DISPLAYED triangles by their own max edge length. The payload's edge_mm is in the
  // stored (pre-mirror) triangle order; triSrc carries each mirrored triangle back to it.
  let densityMesh = null, densityGeo = null, densityMat = null;
  function clearDensity() {
    if (densityMesh) scene.remove(densityMesh);
    if (densityGeo) densityGeo.dispose();
    if (densityMat) densityMat.dispose();
    densityMesh = null; densityGeo = null; densityMat = null;
    mesh.visible = true;
  }
  container._setMeshDensity = (density) => {
    clearDensity();
    if (!density) return { ok: false, reason: "off" };
    const edges = density.edge_mm;
    const nRaw = Math.floor(rawTris.length / 3);
    if (!Array.isArray(edges) || edges.length !== nRaw) {
      return { ok: false,
               reason: `density describes ${Array.isArray(edges) ? edges.length : 0} triangles, the displayed mesh has ${nRaw}` };
    }
    // One length per mirrored triangle, from that triangle's own stored index.
    const perMirrored = new Float32Array(tris.length / 3);
    for (let t = 0; t < perMirrored.length; t++) perMirrored[t] = edges[triSrc ? triSrc[t] : t];
    // Colour domain from the DISPLAYED lengths: p05..p95 keeps one hot triangle from flattening
    // the whole ramp; values outside the domain clamp to the end colours.
    const sorted = Float32Array.from(edges).sort();
    const min = sorted[0], max = sorted[sorted.length - 1];
    let lo = sorted[Math.floor(0.05 * (sorted.length - 1))];
    let hi = sorted[Math.floor(0.95 * (sorted.length - 1))];
    if (!(hi > lo)) { lo = min; hi = max; }
    if (!(hi > lo)) { lo = min - 0.5; hi = max + 0.5; }
    densityGeo = buildDensityGeometry(THREE, verts, tris, perMirrored, lo, hi);
    densityMat = new THREE.MeshStandardMaterial({
      vertexColors: true, roughness: 0.62, metalness: 0.03,
      side: THREE.DoubleSide, transparent: false,
      polygonOffset: true, polygonOffsetFactor: 2, polygonOffsetUnits: 2,
    });
    densityMesh = new THREE.Mesh(densityGeo, densityMat);
    densityMesh.castShadow = densityMesh.receiveShadow = shadows;
    scene.add(densityMesh);
    mesh.visible = false;      // the coloured soup is the surface; ridges + net stay on top
    return { ok: true, min, max, lo, hi, n: edges.length };
  };
  if (opts && opts.density) container._setMeshDensity(opts.density);

  // Cleanup when container is removed
  container._dispose3d = () => {
    cancelAnimationFrame(raf);
    ro.disconnect();
    renderer.dispose();
    if (densityMesh) scene.remove(densityMesh);
    if (densityGeo) densityGeo.dispose();
    if (densityMat) densityMat.dispose();
    container._setMeshDensity = null;
    geo.dispose(); mat.dispose();
    ridgeCache.delete(geo);
    wireGeo.dispose(); wireMat.dispose();
    releaseMeshEdgeGeometry(geo);
    meshEdgeGeo.dispose();
    meshNet.dispose();
    if (mountEdges) mountEdges.dispose();
    if (mountLineMat) mountLineMat.dispose();
    hemi.dispose(); key.dispose(); fillL.dispose(); rim.dispose();
    if (groundGeo) groundGeo.dispose();
    if (groundMat) groundMat.dispose();
  };
}

/**
 * Pure per-frame preparation for the 3D time-lapse (no THREE, node-testable): mirrors each frame's
 * mesh to the full horn with mirrorMesh, records every frame's mm bounding box (the player unions
 * them for ONE fixed camera), and carries the honest per-frame facts (evaluation number, objective,
 * hash, decimation disclosure, full-mesh tri count). Frames without mesh data are skipped.
 * frames: [{n, objective, mesh_hash, quadrants, verts, tris, decimated, n_tris_full}, ...].
 * Returns [{n, objective, mesh_hash, decimated, n_tris_full, verts, tris, bounds}, ...].
 */
export function prepareFrames(frames) {
  const out = [];
  for (const f of (Array.isArray(frames) ? frames : [])) {
    // Shape gate: a renderable frame holds whole vertices (x,y,z triples, at least one triangle's
    // worth) and whole index triples — anything less is unusable junk, skipped honestly.
    if (!f || !Array.isArray(f.verts) || f.verts.length < 9 || f.verts.length % 3 !== 0 ||
        !Array.isArray(f.tris) || f.tris.length < 3 || f.tris.length % 3 !== 0) continue;
    const { verts, tris } = mirrorMesh(f.verts, f.tris, f.quadrants);
    const bounds = { x0: Infinity, y0: Infinity, z0: Infinity, x1: -Infinity, y1: -Infinity, z1: -Infinity };
    for (let i = 0; i < verts.length; i += 3) {
      bounds.x0 = Math.min(bounds.x0, verts[i]);     bounds.x1 = Math.max(bounds.x1, verts[i]);
      bounds.y0 = Math.min(bounds.y0, verts[i + 1]); bounds.y1 = Math.max(bounds.y1, verts[i + 1]);
      bounds.z0 = Math.min(bounds.z0, verts[i + 2]); bounds.z1 = Math.max(bounds.z1, verts[i + 2]);
    }
    out.push({ n: f.n, objective: f.objective == null ? null : f.objective, mesh_hash: f.mesh_hash == null ? null : f.mesh_hash,
               decimated: f.decimated === true, n_tris_full: f.n_tris_full == null ? null : f.n_tris_full,
               verts, tris, bounds });
  }
  return out;
}

/** Union of per-frame mm bounds — the one camera fits the WHOLE time-lapse, so no frame jump ever
 *  moves it. (internal; bounds objects from prepareFrames) */
function unionBounds(list) {
  const u = { x0: Infinity, y0: Infinity, z0: Infinity, x1: -Infinity, y1: -Infinity, z1: -Infinity };
  for (const b of list) {
    if (!b) continue;
    u.x0 = Math.min(u.x0, b.x0); u.x1 = Math.max(u.x1, b.x1);
    u.y0 = Math.min(u.y0, b.y0); u.y1 = Math.max(u.y1, b.y1);
    u.z0 = Math.min(u.z0, b.z0); u.z1 = Math.max(u.z1, b.z1);
  }
  return u;
}

/**
 * 3D time-lapse player (evolution's 3D mode): ONE scene, fixed camera and lights sized from the
 * UNION of every frame's mirrored bounds, geometry hot-swapped per frame index. Each frame's
 * BufferGeometry, ridge lines and (opt-in) full triangle-edge lines are built lazily on first show;
 * decimated frames get an on-screen "mesh decimated to N tris" disclosure. On CDN failure the 2D
 * wall-profile fallback renders and the promise resolves to null (callers stay honestly on 2D).
 * opts: { shadows = true, profile, seedProfile, emptyMessage }.
 * Returns { show(i), frames (prepared), dispose } — or null when 3D is unavailable.
 */
export async function init3dFrames(container, frames, opts = {}) {
  const prepared = prepareFrames(frames);
  container.innerHTML = "";
  if (!prepared.length) {
    const msg = document.createElement("div");
    msg.className = "view3d-fallback";
    msg.textContent = opts.emptyMessage || "No meshed improvement frames in this run — nothing to play in 3D.";
    container.appendChild(msg);
    return null;
  }
  const ok = await loadThree();
  if (!ok) { render2DFallback(container, opts.profile || null, opts.seedProfile || null); return null; }

  // One rig for the whole time-lapse: the camera, lights and shadow ground derive from the union
  // of all frames' bounds, so swapping geometry never moves the camera.
  const u = unionBounds(prepared.map(p => p.bounds));
  // Frame vertices are MILLIMETRES and buildGeo scales the geometry by 0.001 onto the metre stage,
  // so the rig must live in the SAME unit system: compute the centre/extent in metres here too.
  // (Before this, the camera sat ~600 "units" from a horn that was 0.4 units wide with far=100 —
  // everything was clipped, which is why the evolution 3D panel rendered blank. The single-mesh
  // init3d receives metre payloads, so it needs no conversion.)
  const CENTRE_SCALE = 0.001;
  const center = new THREE.Vector3((u.x0 + u.x1) / 2 * CENTRE_SCALE,
                                   (u.y0 + u.y1) / 2 * CENTRE_SCALE,
                                   (u.z0 + u.z1) / 2 * CENTRE_SCALE);
  const maxDim = Math.max(u.x1 - u.x0, u.y1 - u.y0, u.z1 - u.z0) * CENTRE_SCALE;
  if (!isFinite(maxDim) || maxDim <= 0) { render2DFallback(container, opts.profile || null, opts.seedProfile || null); return null; }
  const shadows = opts.shadows !== false;

  const cs = getComputedStyle(document.documentElement);
  const renderPrefs = Object.assign(loadRenderPrefs(), loadLookExtras());
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(
    cs.getPropertyValue("--viz-canvas").trim() || cs.getPropertyValue("--surface").trim() || "#ffffff");

  const mat = new THREE.MeshStandardMaterial({
    color: HORN_BASE_COLOR, roughness: 0.55, metalness: 0.05,
    side: THREE.DoubleSide, transparent: false,
    polygonOffset: true, polygonOffsetFactor: 2, polygonOffsetUnits: 2,
  });
  const contourU = installContours(mat);
  const wireMat = new THREE.LineBasicMaterial({
    color: WIRE_COLOR, transparent: true, opacity: 0.28,
    depthWrite: false,   // overlay only; never occlude the shaded surface or its own creases
  });
  const mesh = new THREE.Mesh(new THREE.BufferGeometry(), mat);          // geometry swapped per frame
  const wire = new THREE.LineSegments(new THREE.BufferGeometry(), wireMat);
  mesh.castShadow = mesh.receiveShadow = shadows;

  // Triangle-edge net, same anti-aliased factory as init3d; positions swapped per frame by show().
  const meshNet = await createMeshNet();
  scene.add(mesh, wire, meshNet.object);

  const hemi = new THREE.HemisphereLight(LIGHT_COLOR, HEMI_GROUND_COLOR, 0.45);
  scene.add(hemi);
  const key = new THREE.DirectionalLight(LIGHT_COLOR, 1.15);
  key.position.copy(center).addScaledVector(new THREE.Vector3(1.6, 2.2, 1.8), maxDim);
  const fillL = new THREE.DirectionalLight(LIGHT_COLOR, 0.35);
  fillL.position.copy(center).addScaledVector(new THREE.Vector3(-1.8, 0.6, 1.2), maxDim);
  const rim = new THREE.DirectionalLight(LIGHT_COLOR, 0.85);
  rim.position.copy(center).addScaledVector(new THREE.Vector3(-1.2, -1.0, -2.2), maxDim);
  scene.add(key, fillL, rim);

  // Same persisted preset as the single-mesh viewer (satin default keeps the pre-settings look).
  const lights = { hemi, key, fill: fillL, rim };
  const lookCtx = { mat, wire, wireMat, meshNet, scene, lights, center, maxDim, contourU,
                    contourStep: niceContourStep((u.z1 - u.z0) * CENTRE_SCALE) };
  applyRenderLook(lookCtx, renderPrefs);

  let groundGeo = null, groundMat = null;
  if (shadows) {
    key.castShadow = true;
    key.target.position.copy(center);
    scene.add(key.target);
    key.shadow.mapSize.set(1024, 1024);
    key.shadow.camera.left = -0.8 * maxDim; key.shadow.camera.right = 0.8 * maxDim;
    key.shadow.camera.top = 0.8 * maxDim;   key.shadow.camera.bottom = -0.8 * maxDim;
    key.shadow.camera.near = 0.1;           key.shadow.camera.far = 4 * maxDim;
    key.shadow.normalBias = 0.01 * maxDim;  key.shadow.bias = 0;
    groundGeo = new THREE.PlaneGeometry(2.6 * maxDim, 2.6 * maxDim);
    groundMat = new THREE.ShadowMaterial({ opacity: 0.22 });
    const ground = new THREE.Mesh(groundGeo, groundMat);
    ground.position.set(center.x, u.y0 * 0.001 - 0.02 * maxDim, center.z);
    ground.rotation.x = -Math.PI / 2;
    ground.receiveShadow = true;
    scene.add(ground);
  }

  const w = container.clientWidth || 600, h = container.clientHeight || 400;
  const camera = new THREE.PerspectiveCamera(45, w / h, 0.001, 100);
  camera.position.set(center.x + maxDim * 1.2, center.y + maxDim * 0.8, center.z + maxDim * 1.5);
  camera.lookAt(center);

  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(window.devicePixelRatio);
  renderer.setSize(w, h);
  meshNet.setSize(w, h);                 // LineMaterial.linewidth is in CSS pixels
  if (shadows) { renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap; }
  container.appendChild(renderer.domElement);

  // Per-frame decimation disclosure ("mesh decimated to N tris") — subtle, honest, on-screen.
  const frameNote = document.createElement("div");
  frameNote.style.cssText = "position:absolute;bottom:8px;left:12px;font-family:var(--f-mono);" +
    "font-size:0.7rem;color:var(--muted);pointer-events:none;";
  frameNote.textContent = "";
  container.style.position = "relative";
  container.appendChild(frameNote);

  // Render-settings chip shared with init3d; mutates the one material/rig in place.
  applyRenderControls(container, p => applyRenderLook(lookCtx, p));

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.target.copy(center);
  controls.update();

  const ro = new ResizeObserver(entries => {
    for (const e of entries) {
      const { width, height } = e.contentRect;
      renderer.setSize(width, height);
      meshNet.setSize(width, height);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
    }
  });
  ro.observe(container);

  // Lazy per-frame geometry: BufferGeometry + normals + ridge/edge lines are built on FIRST show
  // and cached for the rest of the playback (the mirrored arrays themselves come from
  // prepareFrames). The ridge set is built from the frame's own dihedral angles
  // (buildRidgeGeometry), so the stride-decimated frame meshes get creases rather than a
  // full-screen edge net; the triangle-edge set is the full tessellation, opt-in.
  const cache = new Map();
  function buildGeo(i) {
    if (cache.has(i)) return cache.get(i);
    const p = prepared[i];
    const geo = buildSmoothGeometry(THREE, p.verts, p.tris);
    geo.scale(0.001, 0.001, 0.001);                    // verts are mm; the stage is metres
    const wireGeo = buildRidgeGeometry(geo);
    const meshEdgeGeo = buildMeshEdgeGeometry(geo);
    const built = { geo, wireGeo, meshEdgeGeo };
    cache.set(i, built);
    return built;
  }

  let cur = -1, raf;
  function show(i) {
    const j = Math.max(0, Math.min(prepared.length - 1, Number(i) || 0));
    if (j === cur) return;
    cur = j;
    const built = buildGeo(j);
    mesh.geometry = built.geo;
    wire.geometry = built.wireGeo;
    meshNet.setPositions(built.meshEdgeGeo.getAttribute("position").array);
    frameNote.textContent = prepared[j].decimated
      ? `mesh decimated to ${prepared[j].tris.length / 3} tris` : "";
  }
  show(0);

  function animate() {
    raf = requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
  }
  animate();

  function dispose() {
    cancelAnimationFrame(raf);
    ro.disconnect();
    for (const { geo, wireGeo, meshEdgeGeo } of cache.values()) {
      ridgeCache.delete(geo); releaseMeshEdgeGeometry(geo);
      geo.dispose(); wireGeo.dispose(); meshEdgeGeo.dispose();
    }
    cache.clear();
    renderer.dispose(); mat.dispose(); wireMat.dispose(); meshNet.dispose();
    hemi.dispose(); key.dispose(); fillL.dispose(); rim.dispose();
    if (groundGeo) groundGeo.dispose();
    if (groundMat) groundMat.dispose();
  }
  container._dispose3d = dispose;                       // route()'s [data-v3d] sweep kills playback
  return { show, frames: prepared, dispose };
}
