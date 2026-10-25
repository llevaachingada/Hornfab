// view3d.js — hornlab-search GUI   AGPL-3.0-or-later
// Three.js r160 mesh viewer for quarter/half-model horn meshes.
// Mirrors quarter models across x=0 and y=0, half models ('14' x-half / '12' y-half) across their
// one symmetry plane, to reconstruct the full horn.
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
 * Returns { verts: Float32Array, tris: Uint32Array }; verts on the symmetry planes are duplicated
 * (accepted seam — every mirrored quadrant keeps the original's triangulation).
 */
export function mirrorMesh(verts, tris, quadrants) {
  const q = String(quadrants ?? "");
  const copies = q === "1" ? [[1, 1], [-1, 1], [1, -1], [-1, -1]]
               : q === "14" ? [[1, 1], [-1, 1]]
               : q === "12" ? [[1, 1], [1, -1]]
               : [[1, 1]];
  if (copies.length === 1) return { verts: new Float32Array(verts), tris: new Uint32Array(tris) };

  const nOrig = verts.length / 3;
  const allVerts = [];
  const allTris = [];
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
  }
  return { verts: new Float32Array(allVerts), tris: new Uint32Array(allTris) };
}

// ── Persisted 3D render settings ─────────────────────────────────────────────
// One key for every 3D surface (dedicated page, run-detail inline viewer, evolution time-lapse):
// {surface: "satin"|"matte"|"metallic"|"studio", ridges: "on"|"off"|"thin", light: 0.5..2.0}.
// Defaults are exactly the pre-settings look (owner captures/tests pin it): satin material,
// near-white ridgelines at 0.28, key/fill/rim at 1.15/0.35/0.85.
const RENDER_PREF_KEY = "hl-v3d-render";
const RENDER_SURFACES = ["satin", "matte", "metallic", "studio"];
const RENDER_RIDGES = ["on", "off", "thin"];

// Existing colour constants, kept in one place so no preset invents a new hex.
const HORN_BASE_COLOR = 0xdfe4e8;   // light-neutral horn body
const WIRE_COLOR = 0xf4f7f9;        // near-white ridgelines
const HEMI_GROUND_COLOR = 0x8fa3ad; // hemisphere shadow-side tint
const LIGHT_COLOR = 0xffffff;

// Per-surface material + rig mix. `wireOpacity` is the "on" opacity (matte is deliberately
// "off-ish": calmer lines); "thin" overrides it to 0.12, "off" removes the LineSegments.
const RENDER_PRESETS = {
  satin:    { colorScale: 1.0,  roughness: 0.55, metalness: 0.05, wireOpacity: 0.28,
              light: { hemi: 0.45, key: 1.15, fill: 0.35, rim: 0.85 } },   // today's exact look
  matte:    { colorScale: 0.88, roughness: 0.85, metalness: 0.02, wireOpacity: 0.18,
              light: { hemi: 0.45, key: 1.15, fill: 0.35, rim: 0.85 } },
  metallic: { colorScale: 1.0,  roughness: 0.32, metalness: 0.35, wireOpacity: 0.28,
              light: { hemi: 0.45, key: 1.15, fill: 0.35, rim: 0.85 } },
  studio:   { colorScale: 1.0,  roughness: 0.45, metalness: 0.05, wireOpacity: 0.28,
              light: { hemi: 0.55, key: 1.55, fill: 0.70, rim: 1.15 } },
};

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

/** Apply a preset in place — material, ridgeline opacity/visibility and the four-light rig.
 *  No scene rebuild: the same objects are mutated so orbit camera/state stay live. */
function applyRenderLook(ctx, prefs) {
  const p = normalizeRenderPrefs(prefs);
  const preset = RENDER_PRESETS[p.surface] || RENDER_PRESETS.satin;
  const { mat, wire, wireMat, scene, lights } = ctx;
  mat.color.setHex(HORN_BASE_COLOR).multiplyScalar(preset.colorScale);
  mat.roughness = preset.roughness;
  mat.metalness = preset.metalness;
  wireMat.opacity = p.ridges === "thin" ? 0.12 : preset.wireOpacity;
  if (p.ridges === "off") scene.remove(wire);
  else scene.add(wire);
  lights.key.intensity = preset.light.key * p.light;
  lights.fill.intensity = preset.light.fill * p.light;
  lights.rim.intensity = preset.light.rim * p.light;
  lights.hemi.intensity = preset.light.hemi;   // ambient-relative, not part of the multiplier
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
  const prefs = loadRenderPrefs();
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
    `<label style="${lblStyle}">light` +
      `<input type="range" data-v3d-pref="light" min="0.5" max="2" step="0.1" ` +
        `value="${esc(prefs.light)}" aria-label="light intensity multiplier" ` +
        `style="width:72px;accent-color:var(--accent,#0d6e7a)">` +
      `<span data-v3d-light-val>${esc(prefs.light)}×</span></label>`;
  container.appendChild(chip);

  const surfaceSel = chip.querySelector('[data-v3d-pref="surface"]');
  const ridgeSel = chip.querySelector('[data-v3d-pref="ridges"]');
  const lightRange = chip.querySelector('[data-v3d-pref="light"]');
  const lightVal = chip.querySelector("[data-v3d-light-val]");
  const commit = () => {
    const next = saveRenderPrefs({
      surface: surfaceSel.value,
      ridges: ridgeSel.value,
      light: Number(lightRange.value),
    });
    lightVal.textContent = `${next.light}×`;
    onChange(next);
  };
  surfaceSel.addEventListener("change", commit);
  ridgeSel.addEventListener("change", commit);
  lightRange.addEventListener("input", commit);
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
export async function init3d(container, meshData, profile, seedProfile, shadows = true) {
  container.innerHTML = "";

  const ok = await loadThree();
  if (!ok) { render2DFallback(container, profile, seedProfile); return; }

  const { verts: rawVerts, tris: rawTris, quadrants } = meshData || {};
  if (!rawVerts || !rawVerts.length || !rawTris || !rawTris.length) {
    render2DFallback(container, profile, seedProfile); return;
  }
  const { verts, tris } = mirrorMesh(rawVerts, rawTris, quadrants);

  const cs = getComputedStyle(document.documentElement);
  const renderPrefs = loadRenderPrefs();
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(
    cs.getPropertyValue("--viz-canvas").trim() || cs.getPropertyValue("--surface").trim() || "#ffffff"
  );

  // Geometry
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.BufferAttribute(verts, 3));
  geo.setIndex(new THREE.BufferAttribute(tris, 1));
  geo.computeVertexNormals();

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
  // polygonOffset nudges the surface a hair back so the near-white wireframe ridgelines at
  // identical coordinates win the depth test; without it the LESS depth test drops fragments
  // wherever the line depth equals the surface depth (patchy, driver-dependent visibility).
  const mat = new THREE.MeshStandardMaterial({
    color: HORN_BASE_COLOR, roughness: 0.55, metalness: 0.05,
    side: THREE.DoubleSide,   // interior visibility of the open mouth (mirror windings are already consistent)
    transparent: false,
    polygonOffset: true, polygonOffsetFactor: 1, polygonOffsetUnits: 1,
  });
  const mesh = new THREE.Mesh(geo, mat);
  mesh.castShadow = mesh.receiveShadow = shadows;
  scene.add(mesh);

  // Near-white wireframe ridgelines over the horn — default on (owner override, not shadow-gated);
  // the ridges setting can thin (0.12) or remove them below.
  const wireGeo = new THREE.WireframeGeometry(geo);
  const wireMat = new THREE.LineBasicMaterial({ color: WIRE_COLOR, transparent: true, opacity: 0.28 });
  const wire = new THREE.LineSegments(wireGeo, wireMat);
  scene.add(wire);

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
  applyRenderLook({ mat, wire, wireMat, scene, lights }, renderPrefs);

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
  camera.position.set(center.x + maxDim * 1.2, center.y + maxDim * 0.8, center.z + maxDim * 1.5);
  camera.lookAt(center);

  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(window.devicePixelRatio);
  renderer.setSize(w, h);
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
  applyRenderControls(container, p => applyRenderLook({ mat, wire, wireMat, scene, lights }, p));

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.target.copy(center);
  controls.update();

  // Resize observer
  const ro = new ResizeObserver(entries => {
    for (const e of entries) {
      const { width, height } = e.contentRect;
      renderer.setSize(width, height);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
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

  // Cleanup when container is removed
  container._dispose3d = () => {
    cancelAnimationFrame(raf);
    ro.disconnect();
    renderer.dispose();
    geo.dispose(); mat.dispose();
    wireGeo.dispose(); wireMat.dispose();
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
 * BufferGeometry and wireframe ridgelines are built lazily on first show; decimated frames get an
 * on-screen "mesh decimated to N tris" disclosure. On CDN failure the 2D wall-profile fallback
 * renders and the promise resolves to null (callers stay honestly on 2D).
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
  const center = new THREE.Vector3((u.x0 + u.x1) / 2, (u.y0 + u.y1) / 2, (u.z0 + u.z1) / 2);
  const maxDim = Math.max(u.x1 - u.x0, u.y1 - u.y0, u.z1 - u.z0);
  if (!isFinite(maxDim) || maxDim <= 0) { render2DFallback(container, opts.profile || null, opts.seedProfile || null); return null; }
  const shadows = opts.shadows !== false;

  const cs = getComputedStyle(document.documentElement);
  const renderPrefs = loadRenderPrefs();
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(
    cs.getPropertyValue("--viz-canvas").trim() || cs.getPropertyValue("--surface").trim() || "#ffffff");

  const mat = new THREE.MeshStandardMaterial({
    color: HORN_BASE_COLOR, roughness: 0.55, metalness: 0.05,
    side: THREE.DoubleSide, transparent: false,
    polygonOffset: true, polygonOffsetFactor: 1, polygonOffsetUnits: 1,
  });
  const wireMat = new THREE.LineBasicMaterial({ color: WIRE_COLOR, transparent: true, opacity: 0.28 });
  const mesh = new THREE.Mesh(new THREE.BufferGeometry(), mat);          // geometry swapped per frame
  const wire = new THREE.LineSegments(new THREE.BufferGeometry(), wireMat);
  mesh.castShadow = mesh.receiveShadow = shadows;
  scene.add(mesh, wire);

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
  applyRenderLook({ mat, wire, wireMat, scene, lights }, renderPrefs);

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
  applyRenderControls(container, p => applyRenderLook({ mat, wire, wireMat, scene, lights }, p));

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.target.copy(center);
  controls.update();

  const ro = new ResizeObserver(entries => {
    for (const e of entries) {
      const { width, height } = e.contentRect;
      renderer.setSize(width, height);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
    }
  });
  ro.observe(container);

  // Lazy per-frame geometry: BufferGeometry + normals + wireframe are built on FIRST show and
  // cached for the rest of the playback (the mirrored arrays themselves come from prepareFrames).
  const cache = new Map();
  function buildGeo(i) {
    if (cache.has(i)) return cache.get(i);
    const p = prepared[i];
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(Float32Array.from(p.verts), 3));
    geo.setIndex(new THREE.BufferAttribute(Uint32Array.from(p.tris), 1));
    geo.computeVertexNormals();
    geo.scale(0.001, 0.001, 0.001);                    // verts are mm; the stage is metres
    const wireGeo = new THREE.WireframeGeometry(geo);
    const built = { geo, wireGeo };
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
    for (const { geo, wireGeo } of cache.values()) { geo.dispose(); wireGeo.dispose(); }
    cache.clear();
    renderer.dispose(); mat.dispose(); wireMat.dispose();
    hemi.dispose(); key.dispose(); fillL.dispose(); rim.dispose();
    if (groundGeo) groundGeo.dispose();
    if (groundMat) groundMat.dispose();
  }
  container._dispose3d = dispose;                       // route()'s [data-v3d] sweep kills playback
  return { show, frames: prepared, dispose };
}
