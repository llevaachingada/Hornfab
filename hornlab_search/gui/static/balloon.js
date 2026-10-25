// balloon.js — hornlab-search GUI   AGPL-3.0-or-later
//
// W6 "Balloon" view: a continuously-shaded 3D directivity balloon over a design's stored
// balloon grid (response.npz), with white isobar rings ON the surface, labeled
// On axis / Horizontal / Vertical rays with a faint protractor wireframe, a radar
// (great-circle) slicer, and a freq × polar-angle filled-isobar slice.
//
// Balloon display design follows Boundary Lab's (JWSound/boundary-lab, GPL-3.0) Balloon
// Plot — used here as the DESIGN REFERENCE only. This is our own implementation in the
// GUI's own stack (vanilla JS + three.js r160 via the pinned import map, no BL code, no new
// dependencies); hornlab-search is AGPL-3.0-or-later.
//
// The balloon encodes level in BOTH shape and colour (BL's mapping):
//   radius = max(spl − min_db, 0) with min_db = −30 dB; colour = a turbo-family ramp
//   interpolated from the house isobar palette (charts.js ISOBAR_COLORS) so the sphere and
//   the slice panel read as one instrument. Grid conventions are the stored ones
//   (data.py::balloon): theta rows 0..180 inclusive from +Z, phi columns 0..360 counterclock-
//   wise from +X toward +Y, flat index i*nP + j (theta-major), NO stored wrap column (the
//   viewer closes the seam), pole rows all share one direction (welded to one vertex each).
// Isobars: marching squares over the (theta, phi) grid at −6/−12/−18/−24 dB, mapped back onto
//   the surface at a small radial offset (a ring sits at one level, so its radius is constant).
// Radar slice: a great circle at a chosen azimuth through the CURRENT-frequency balloon,
//   drawn r = max(spl − min_db, 0) with dB rings, pink accent.
// Slice panel: charts.js::isobarMap at the chosen azimuth — house palette, log-frequency x,
//   0..180 theta up the y-axis, 0..−30 dB colour bar.
//
// Pure helpers (balloonTopology, balloonColor, splBilinear) are exported for the same
// node-testable precedent as view3d.js::mirrorMesh.

import { css, fmt, isobarMap, ISOBAR_COLORS } from "./charts.js";
import { loadThree } from "./view3d.js";

const esc = s => String(s ?? "").replace(/[&<>"']/g, c => (
  { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmtHz = v => v == null || !isFinite(v) ? "–"
  : v >= 1000 ? (v / 1000).toFixed(1) + " kHz" : Math.round(v) + " Hz";
const fmtDeg = v => (v == null || !isFinite(v)) ? "–" :
  (v < 0 ? "−" : "+") + Math.abs(v).toFixed(0) + "°";

async function api(path) {
  const r = await fetch(path);
  if (!r.ok) throw new Error(r.status + " " + (await r.text().catch(() => "")));
  return r.json();
}

// ── Pure helpers ───────────────────────────────────────────────────

/**
 * Pure topology of the balloon mesh (node-testable, like view3d.js::mirrorMesh).
 * Welded pole vertices (row 0 and row nT−1 collapse to one vertex each), ring rows for every
 * interior theta row, phi wrap closed with modular column indices (the grid stores NO wrap
 * column). Triangle winding is outward for the (θ, φ) parametrisation: d/dθ × d/dφ points
 * radially out, so fan/quad strips ordered (θ,φ),(θ+dθ,φ),(θ+dθ,φ+dφ) face out.
 * Returns { nV, dirs: Float32Array(nV*3), indices: Uint32Array, vRow: Int16Array,
 * vCol: Int16Array } — dirs are unit direction vectors; vRow/vCol give each vertex's grid
 * cell (0,0) for the north pole, (nT−1,0) for the south pole). Null for a degenerate grid.
 */
export function balloonTopology(nT, nP) {
  if (!(Number.isInteger(nT) && Number.isInteger(nP) && nT >= 3 && nP >= 3)) return null;
  const nV = 2 + (nT - 2) * nP;
  const dirs = new Float32Array(nV * 3);
  const vRow = new Int16Array(nV), vCol = new Int16Array(nV);
  const into = (o, theta, phi) => {
    const st = Math.sin(theta), c = Math.cos(theta);
    dirs[o] = st * Math.cos(phi); dirs[o + 1] = st * Math.sin(phi); dirs[o + 2] = c;
  };
  into(0, 0, 0);                                  // north pole (+Z — the horn's on-axis)
  into((nV - 1) * 3, Math.PI, 0);                 // south pole (−Z)
  for (let i = 1; i <= nT - 2; i++) {
    const theta = Math.PI * i / (nT - 1);
    for (let j = 0; j < nP; j++) {
      const vid = 1 + (i - 1) * nP + j;
      vRow[vid] = i; vCol[vid] = j;
      into(vid * 3, theta, 2 * Math.PI * j / nP);
    }
  }
  vRow[0] = 0; vCol[0] = 0;
  vRow[nV - 1] = nT - 1; vCol[nV - 1] = 0;
  const vid = (i, j) => (i === 0 ? 0 : i === nT - 1 ? nV - 1
    : 1 + (i - 1) * nP + ((j % nP) + nP) % nP);
  const indices = [];
  for (let j = 0; j < nP; j++)                                    // north fan
    indices.push(0, vid(1, j), vid(1, (j + 1) % nP));
  for (let i = 1; i <= nT - 3; i++)                               // interior quads
    for (let j = 0; j < nP; j++) {
      const a = vid(i, j), b = vid(i + 1, j), c = vid(i + 1, j + 1), d = vid(i, j + 1);
      indices.push(a, b, c, a, c, d);
    }
  for (let j = 0; j < nP; j++)                                    // south fan
    indices.push(vid(nT - 2, j), nV - 1, vid(nT - 2, (j + 1) % nP));
  return { nV, dirs, indices: new Uint32Array(indices), vRow, vCol, nT, nP };
}

let _rampStops = null;

/**
 * Turbo-family ramp for the balloon: linear interpolation across the house isobar palette
 * (charts.js ISOBAR_COLORS — the 3 dB directivity bands), stops placed at the band centres
 * (i+0.5)/n, so the sphere's colour at any level matches the slice panel's band colour at
 * the same level — one instrument, two views. t in [0, 1] over [min_db, 0]. → [r,g,b] 0..255.
 * The hot end is lifted above the paper palette (#8F0000 is for contour overlays on 2D where
 * white rings need a dark ground; on a lit 3D object the LOUDEST region must read hot, not
 * near-black) — the only deliberate divergence, confined to the sphere.
 */
export function balloonColor(t) {
  if (!_rampStops) _rampStops = ISOBAR_COLORS.map(h => {
    const n = parseInt(h.slice(1), 16); return [n >> 16, (n >> 8) & 255, n & 255];
  }).map((c, i) => (i === ISOBAR_COLORS.length - 1 ? [226, 68, 52] : c));   // #8F0000 -> hot red
  const n = _rampStops.length;
  t = Math.min(1, Math.max(0, +t));
  const f = t * n - 0.5;
  if (f <= 0) return _rampStops[0];
  if (f >= n - 1) return _rampStops[n - 1];
  const i = Math.floor(f), u = f - i, a = _rampStops[i], b = _rampStops[i + 1];
  return [a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u, a[2] + (b[2] - a[2]) * u];
}

/**
 * Bilinear sample of one frequency's flat spl row (theta-major, i*nP + j) at a
 * (thetaDeg 0..180, phiDeg 0..360) direction. Columns are exclusive (wrap-aware lerp between
 * the bracketing phi columns); null/NaN samples read as the floor. Returns dB.
 */
export function splBilinear(row, nT, nP, thetaDeg, phiDeg, floor = -30) {
  if (!row || row.length !== nT * nP) return floor;
  const ph = ((phiDeg % 360) + 360) % 360;
  const jf = ph / 360 * nP, j0i = Math.floor(jf);
  const j0 = j0i % nP, j1 = (j0 + 1) % nP, wj = jf - j0i;
  const it = Math.min(1, Math.max(0, thetaDeg / 180)) * (nT - 1);
  const i0 = Math.min(nT - 1, Math.floor(it)), i1 = Math.min(nT - 1, i0 + 1), wi = it - Math.floor(it);
  const g = (i, j) => { const v = row[i * nP + j]; return (v == null || !isFinite(v)) ? floor : v; };
  const top = g(i0, j0) * (1 - wj) + g(i0, j1) * wj;
  const bot = g(i1, j0) * (1 - wj) + g(i1, j1) * wj;
  return top * (1 - wi) + bot * wi;
}

// ── 3D balloon (three.js) ──────────────────────────────────────────

// Marching squares: crossed edges per corner-bit pattern (A,B,C,D bits 1,2,4,8; edges
// L = A–B (down), T = A–D (right), R = D–C (down), B = B–C (right)). Saddle patterns 5/10
// resolve by the cell mean. Same idea as charts.js's raster table, derived independently for
// the θ–φ grid.
const MS_EDGES = {
  1: ["L", "T"], 2: ["L", "B"], 3: ["T", "B"], 4: ["R", "B"], 6: ["L", "R"], 7: ["T", "R"],
  8: ["T", "R"], 9: ["L", "R"], 11: ["R", "B"], 12: ["L", "B"], 13: ["L", "B"], 14: ["T", "L"],
};

// Ring radius offset from the surface (a hair outward, like the view3d wire's polygonOffset
// trick but simpler: constant-level rings sit at one radius, so offset the whole ring).
const RING_OFFSET = 1.018;

/**
 * The 3D balloon viewer. Returns { setFreq, dispose } — setFreq(i) re-deforms and recolors
 * the SAME geometry (no rebuild), rebuilds the isobar rings, and drives the hover readout.
 * opts: { hover: (caption:string) => void }.
 */
export async function initBalloon3d(container, payload, opts = {}) {
  container.innerHTML = "";
  const THREE = await loadThree();
  if (!THREE) {
    container.innerHTML =
      `<div class="view3d-fallback">3D is unavailable (three.js did not load) — the slice and radar panels below still carry the data.</div>`;
    return null;
  }
  if (!container.isConnected) return null;               // navigated away mid-load: build nothing
  const [nT, nP] = payload.balloon_grid, floor = payload.min_db ?? -30, span = 0 - floor;
  const topo = balloonTopology(nT, nP);
  if (!topo) {
    container.innerHTML = `<div class="view3d-fallback">This balloon grid is too coarse to render (${nT}×${nP}).</div>`;
    return null;
  }
  const hover = (typeof opts.hover === "function") ? opts.hover : (() => {});
  const cs = getComputedStyle(document.documentElement);

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(css("--viz-canvas") || css("--surface") || "#e9edf0");

  const geo = new THREE.BufferGeometry();
  const posAttr = new THREE.BufferAttribute(new Float32Array(topo.nV * 3), 3);
  const colAttr = new THREE.BufferAttribute(new Float32Array(topo.nV * 3), 3);
  geo.setAttribute("position", posAttr);
  geo.setAttribute("color", colAttr);
  geo.setIndex(new THREE.BufferAttribute(topo.indices, 1));

  // Form shading from light, colour from data; double-sided so deep null dimples never vanish.
  const mat = new THREE.MeshStandardMaterial({
    vertexColors: true, roughness: 0.5, metalness: 0.0, side: THREE.DoubleSide,
  });
  const mesh = new THREE.Mesh(geo, mat);
  mesh.frustumCulled = false;
  scene.add(mesh);

  // Lighting: a lifted hemisphere keeps colours readable (form, not drama), one key gives the
  // sphere its roundness, a rim keeps the dark flank off the canvas in dark theme.
  const hemi = new THREE.HemisphereLight(0xffffff, 0x77848c, 0.85);
  scene.add(hemi);
  const key = new THREE.DirectionalLight(0xffffff, 0.5);
  key.position.set(1.4, 1.5, 1.8);
  const rim = new THREE.DirectionalLight(0xffffff, 0.4);
  rim.position.set(-1.6, -0.9, -2.0);
  scene.add(key, rim);

  // Isobar rings: one LineSegments, geometry rewritten per frequency (preallocated, capped).
  const RING_LEVELS = [-6, -12, -18, -24];
  const ringMat = new THREE.LineBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.85 });
  const ringGeo = new THREE.BufferGeometry();
  const ringAttr = new THREE.BufferAttribute(
    new Float32Array((topo.nT - 1) * topo.nP * 4 * RING_LEVELS.length * 3), 3);
  ringGeo.setAttribute("position", ringAttr);
  const rings = new THREE.LineSegments(ringGeo, ringMat);
  rings.frustumCulled = false;
  scene.add(rings);

  // Protractor: faint measurement-domain rings in the horizontal (y=0) and vertical (x=0)
  // planes at full-level radius, 15° ticks — BL's protractor idea, heavily simplified.
  const proCol = css("--label") || "#46535e";
  function protractor(axis /* 0 = H plane (x–z), 1 = V plane (y–z) */) {
    const pts = [], ticks = [];
    for (let k = 0; k < 96; k++) {
      const a0 = k / 96 * Math.PI * 2, a1 = (k + 1) / 96 * Math.PI * 2;
      if (axis === 0) { pts.push(Math.cos(a0) * 1.14, 0, Math.sin(a0) * 1.14, Math.cos(a1) * 1.14, 0, Math.sin(a1) * 1.14); }
      else { pts.push(0, Math.cos(a0) * 1.14, Math.sin(a0) * 1.14, 0, Math.cos(a1) * 1.14, Math.sin(a1) * 1.14); }
    }
    for (let a = 0; a < 360; a += 15) {          // tick marks poking outward, readable as angles
      const ar = a * Math.PI / 180;
      if (axis === 0) ticks.push(Math.cos(ar) * 1.14, 0, Math.sin(ar) * 1.14, Math.cos(ar) * 1.19, 0, Math.sin(ar) * 1.19);
      else ticks.push(0, Math.cos(ar) * 1.14, Math.sin(ar) * 1.14, 0, Math.cos(ar) * 1.19, Math.sin(ar) * 1.19);
    }
    const g1 = new THREE.BufferGeometry();
    g1.setAttribute("position", new THREE.Float32BufferAttribute(pts, 3));
    scene.add(new THREE.LineLoop(g1, new THREE.LineBasicMaterial({
      color: new THREE.Color(proCol), transparent: true, opacity: 0.3, depthWrite: false })));
    const g2 = new THREE.BufferGeometry();
    g2.setAttribute("position", new THREE.Float32BufferAttribute(ticks, 3));
    const t2 = new THREE.LineSegments(g2, new THREE.LineBasicMaterial({
      color: new THREE.Color(proCol), transparent: true, opacity: 0.35, depthWrite: false }));
    t2.frustumCulled = false;
    scene.add(t2);
    return [g1, g2];
  }

  function axisRay(dir, label, colorCss) {
    // Outer segment only (1.02R → 1.30R): inside the balloon a ray is just clutter.
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.Float32BufferAttribute([
      dir[0] * 1.02, dir[1] * 1.02, dir[2] * 1.02,
      dir[0] * 1.30, dir[1] * 1.30, dir[2] * 1.30], 3));
    scene.add(new THREE.Line(g, new THREE.LineBasicMaterial({ color: new THREE.Color(colorCss) })));
    // Label sprite (canvas texture): the quad is sized to the GLYPHS so every label reads the
    // same text height in world units, whatever the string length.
    const cv = document.createElement("canvas");
    const c2 = cv.getContext("2d");
    c2.font = "500 32px 'Spline Sans','Segoe UI',system-ui,sans-serif";
    const tw = Math.ceil(c2.measureText(label).width);
    cv.width = tw + 28; cv.height = 46;
    c2.font = "500 32px 'Spline Sans','Segoe UI',system-ui,sans-serif";
    c2.textAlign = "center"; c2.textBaseline = "middle";
    c2.fillStyle = colorCss; c2.fillText(label, cv.width / 2, 25);
    const tex = new THREE.CanvasTexture(cv);
    const h = 0.08, sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true, depthWrite: false }));
    sp.scale.set(h * cv.width / cv.height, h, 1);
    sp.position.set(dir[0] * 1.44, dir[1] * 1.44, dir[2] * 1.44);
    scene.add(sp);
    return [g, sp.material];
  }

  const disposables = [mat, ringMat, ringGeo];
  const proH = protractor(0), proV = protractor(1);
  disposables.push(...proH, ...proV);
  // labeled rays, BL-style (on-axis is --label-toned; H amber; V the pink radar accent)
  disposables.push(...[
    axisRay([0, 0, 1], "On axis", css("--label")),
    axisRay([1, 0, 0], "Horizontal", css("--seed")),
    axisRay([0, 1, 0], "Vertical", css("--balloon-cut")),
  ].flat());

  // Sizing
  const w0 = container.clientWidth || 600, h0 = container.clientHeight || 450;
  const camera = new THREE.PerspectiveCamera(45, w0 / h0, 0.01, 50);
  camera.position.set(1.5, 1.05, 2.1);
  camera.lookAt(0, 0, 0);
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(window.devicePixelRatio);
  renderer.setSize(w0, h0);
  container.appendChild(renderer.domElement);
  const { OrbitControls: OC } = await import("three/addons/controls/OrbitControls.js");
  if (!container.isConnected) return null;               // navigated away mid-load: build nothing
  const controls = new OC(camera, renderer.domElement);
  controls.update();

  const ro = new ResizeObserver(entries => {
    for (const e of entries) {
      if (!(e.contentRect.width > 0 && e.contentRect.height > 0)) continue;
      renderer.setSize(e.contentRect.width, e.contentRect.height);
      camera.aspect = e.contentRect.width / e.contentRect.height;
      camera.updateProjectionMatrix();
    }
  });
  ro.observe(container);

  // ── per-frequency update: positions + colours in place, then rings ──────────────
  let curFi = -1;
  function applyFreq(freqIdx) {
    if (freqIdx === curFi || !payload.spl[freqIdx]) return;
    curFi = freqIdx;
    const row = payload.spl[freqIdx];
    const pos = posAttr.array, col = colAttr.array;
    // floor-pin: an exact −30 dB vertex would collapse to r=0 and drop triangles out of the
    // closed shell; it is drawn at 2 % of full radius instead (a dimple, never a hole).
    for (let v = 0; v < topo.nV; v++) {
      const o = v * 3;
      const lvlRaw = row[topo.vRow[v] * nP + topo.vCol[v]];
      const lvl = (lvlRaw == null || !isFinite(lvlRaw)) ? floor : Math.min(0, lvlRaw);
      const r = Math.max((lvl - floor) / span, 0.02);
      pos[o] = topo.dirs[o] * r; pos[o + 1] = topo.dirs[o + 1] * r; pos[o + 2] = topo.dirs[o + 2] * r;
      const colv = balloonColor((lvl - floor) / span);
      col[o] = colv[0] / 255; col[o + 1] = colv[1] / 255; col[o + 2] = colv[2] / 255;
    }
    posAttr.needsUpdate = true;
    colAttr.needsUpdate = true;
    geo.computeVertexNormals();
    // rings: marching squares over the (θ, φ) grid; every crossing maps to 3D at level radius
    let k = 0;
    const cap = ringAttr.array.length;
    const push = (it, jf, L) => {
      if (k + 3 > cap) return;
      const theta = Math.PI * it / (nT - 1), phi = 2 * Math.PI * jf / nP;
      const st = Math.sin(theta), c = Math.cos(theta);
      const r = Math.max(L - floor, 0) / span * RING_OFFSET;
      ringAttr.array[k++] = st * Math.cos(phi) * r;
      ringAttr.array[k++] = st * Math.sin(phi) * r;
      ringAttr.array[k++] = c * r;
    };
    const val = (i, j) => { const v = row[i * nP + (j % nP)]; return (v == null || !isFinite(v)) ? floor : v; };
    for (const L of RING_LEVELS) {
      for (let i = 0; i < nT - 1; i++) {
        for (let j = 0; j < nP; j++) {
          const A = val(i, j), B = val(i + 1, j), C = val(i + 1, j + 1), D = val(i, j + 1);
          const code = (A > L ? 1 : 0) | (B > L ? 2 : 0) | (C > L ? 4 : 0) | (D > L ? 8 : 0);
          const seg = code === 5 || code === 10
            ? (((A + B + C + D) / 4) > L ? ["T", "R", "L", "B"] : ["L", "T", "R", "B"])
            : MS_EDGES[code];
          if (!seg || !seg.length) continue;
          const pt = e => {
            const u = e === "L" ? [i + (L - A) / (B - A), j] : e === "R" ? [i + (L - D) / (C - D), j + 1]
              : e === "T" ? [i, j + (L - A) / (D - A)] : [i + 1, j + (L - B) / (C - B)];
            push(Math.min(nT - 1, Math.max(0, u[0])), u[1], L);
          };
          pt(seg[0]); pt(seg[1]);
          if (seg.length === 4) { pt(seg[2]); pt(seg[3]); }
        }
      }
    }
    ringAttr.needsUpdate = true;
    ringGeo.setDrawRange(0, k / 3);
  }

  // ── hover readout: ray → nearest direction → bilinear level ─────────────────────
  const pv = new THREE.Vector3(), phv = new THREE.Vector3();
  function onMove(ev) {
    const row = payload.spl[curFi];
    if (!row) { hover(""); return; }
    const r = renderer.domElement.getBoundingClientRect();
    if (!(r.width > 0 && r.height > 0)) return;
    const nx = ((ev.clientX - r.left) / r.width) * 2 - 1;
    const ny = -((ev.clientY - r.top) / r.height) * 2 + 1;
    if (nx < -1.15 || nx > 1.15 || ny < -1.15 || ny > 1.15) { hover(""); return; }
    phv.set(nx, ny, 0.5).unproject(camera).sub(camera.position).normalize();  // world = balloon coords
    pv.copy(camera.position);
    const t0 = -pv.dot(phv);                             // closest approach of the ray to the origin
    pv.addScaledVector(phv, t0);
    if (pv.length() > 1.05) { hover(""); return; }       // pointer outside the balloon's reach
    const u = pv.normalize();
    const theta = Math.acos(Math.min(1, Math.max(-1, u.z))) * 180 / Math.PI;
    const phi = (Math.atan2(u.y, u.x) * 180 / Math.PI + 360) % 360;
    const db = splBilinear(row, nT, nP, theta, phi, floor);
    hover(`Horizontal ${fmtDeg(Math.atan2(u.x, u.z) * 180 / Math.PI)} · ` +
          `Vertical ${fmtDeg(Math.atan2(u.y, u.z) * 180 / Math.PI)} · ` +
          `${db.toFixed(1)} dB at ${fmtHz(payload.freqs_hz[curFi])}`);
  }
  function onLeave() { hover(""); }
  renderer.domElement.addEventListener("pointermove", onMove);
  renderer.domElement.addEventListener("pointerleave", onLeave);

  let raf;
  (function animate() {
    raf = requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
  })();

  let rafPending = -1;
  const setFreq = freqIdx => {                         // keeps the LATEST index if moves come faster
    rafPending = freqIdx;                              //   than frames — one rebuild per frame, ever
    requestAnimationFrame(() => { if (rafPending >= 0) { const f = rafPending; rafPending = -1; applyFreq(f); } });
  };
  applyFreq(0);

  function dispose() {
    cancelAnimationFrame(raf);
    ro.disconnect();
    renderer.domElement.removeEventListener("pointermove", onMove);
    renderer.domElement.removeEventListener("pointerleave", onLeave);
    controls.dispose();
    renderer.dispose();
    geo.dispose();
    for (const d of disposables) { if (d.map) d.map.dispose?.(); d.dispose?.(); }
    while (scene.children.length) scene.remove(scene.children[0]);
  }
  container._dispose3d = dispose;                        // route()'s [data-v3d] sweep kills the loop
  return { setFreq, dispose };
}

// ── Radar slicer (2D canvas, great-circle cut) ─────────────────────

/**
 * Redraw the radar panel: the great circle at `azDeg` through the balloon at frequency index
 * `fi`. r = max(spl − min_db, 0) with dB rings (0/−6/…/−30), 30° spokes, pink accent line.
 * Paint order: data fill UNDER, ring grid + labels OVER (labels never lost under the fill),
 * the cut's stroke last (topmost).
 */
export function drawRadar(canvas, payload, fi, azDeg) {
  if (!payload || !payload.spl || !payload.spl.length) return;
  const [nT, nP] = payload.balloon_grid, floor = payload.min_db ?? -30;
  const row = payload.spl[Math.max(0, Math.min(payload.spl.length - 1, fi | 0))] || [];
  const dpr = Math.min(2, window.devicePixelRatio || 1);
  const S = Math.max(120, Math.round(canvas.clientWidth || 300));
  if (canvas.width !== S * dpr) { canvas.width = S * dpr; canvas.height = S * dpr; }
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, S, S);
  const cx = S / 2, cy = S / 2, R = S / 2 - 26;
  const ringCol = css("--rule") || "#a9b4bb";
  const tickCol = css("--label") || "#46535e";
  ctx.font = "10px 'Spline Sans Mono','Cascadia Mono',Consolas,monospace";
  const cutCol = css("--balloon-cut") || "#c2417d";
  // (1) the cut's fill first — everything drawn after sits over it
  ctx.beginPath();
  for (let k = 0; k <= 240; k++) {
    const s = k / 240 * 360;
    const up = s <= 180;
    const db = splBilinear(row, nT, nP, up ? s : 360 - s, azDeg + (up ? 0 : 180), floor);
    const rr = R * Math.max(db - floor, 0) / (0 - floor);
    const a = s * Math.PI / 180;
    const x = cx + Math.sin(a) * rr, y = cy - Math.cos(a) * rr;
    if (k === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  }
  ctx.closePath();
  ctx.globalAlpha = 0.16; ctx.fillStyle = cutCol; ctx.fill();
  ctx.globalAlpha = 1;
  // (2) rings + spokes + labels — dB labels run down the LEFT horizontal arm, clear of the
  // 0°/90°/180° theta labels that live at the top / right / bottom of the frame
  for (let L = 0; L >= floor; L -= 6) {
    const r = R * (L - floor) / (0 - floor);
    ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.strokeStyle = ringCol; ctx.lineWidth = L === 0 ? 1.4 : 0.8; ctx.globalAlpha = L === 0 ? 0.9 : 0.55;
    ctx.stroke(); ctx.globalAlpha = 1;
    ctx.fillStyle = tickCol; ctx.textAlign = "right";
    ctx.fillText(String(L === 0 ? "0" : L), cx - r - 5, cy - 3);
  }
  ctx.strokeStyle = ringCol; ctx.lineWidth = 0.7; ctx.globalAlpha = 0.4;
  for (let s = 0; s < 360; s += 30) {
    const a = s * Math.PI / 180;
    ctx.beginPath(); ctx.moveTo(cx, cy);
    ctx.lineTo(cx + Math.sin(a) * R, cy - Math.cos(a) * R); ctx.stroke();
  }
  ctx.globalAlpha = 1;
  ctx.fillStyle = tickCol; ctx.textAlign = "center";
  for (const [s, lbl] of [[0, "0°"], [90, "90°"], [180, "180°"]]) {
    const a = s * Math.PI / 180;
    ctx.fillText(lbl, cx + Math.sin(a) * (R + 11), cy - Math.cos(a) * (R + 11));
  }
  // (3) the cut's stroke on top
  ctx.beginPath();
  for (let k = 0; k <= 240; k++) {
    const s = k / 240 * 360;
    const up = s <= 180;
    const db = splBilinear(row, nT, nP, up ? s : 360 - s, azDeg + (up ? 0 : 180), floor);
    const rr = R * Math.max(db - floor, 0) / (0 - floor);
    const a = s * Math.PI / 180;
    const x = cx + Math.sin(a) * rr, y = cy - Math.cos(a) * rr;
    if (k === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  }
  ctx.closePath();
  ctx.strokeStyle = cutCol; ctx.lineWidth = 1.9; ctx.lineJoin = "round";
  ctx.stroke();
}

// ── View ───────────────────────────────────────────────────────────

export async function viewBalloon(root, runId) {
  root.innerHTML = `<p class="muted">Loading balloon…</p>`;
  let pick;
  try { pick = await api("/api/balloon/" + encodeURIComponent(runId)); }
  catch (e) {
    if (root.isConnected) root.innerHTML = `<div class="alert error"><b>Error:</b> ${esc(e.message)}</div>`;
    return;
  }
  if (!root.isConnected) return;
  const designs = (pick.designs || []).filter(x => x.has_balloon);
  if (!designs.length) {
    root.innerHTML = `<div class="stack" style="gap:14px">
      <div><div class="eyebrow">Balloon</div><h2>${esc(pick.name || runId)}</h2></div>
      <p class="muted">No design in this run stores a balloon (an older
        <code>response.npz</code> without <code>spl_balloon_db</code>). Verify-tier solves always do;
        a fresh screen/verify run of this config would add one.</p>
      <p><a href="#/run/${esc(runId)}">← back to the run</a></p></div>`;
    return;
  }
  const hash0 = designs[0].hash;
  root.innerHTML = `<div class="stack" style="gap:16px">
    <div>
      <div class="eyebrow">Balloon · directivity sphere</div>
      <h2>${esc(pick.name || runId)}</h2>
      <p class="muted" style="margin:2px 0 0"><span id="balloon-caption">…</span>
        <a href="#/run/${esc(runId)}">← back to the run</a></p>
      <div class="pill-row" style="margin:8px 0 0">
        <label for="balloon-design" class="fam-meta">Design</label>
        <select id="balloon-design" aria-label="Design" class="sort-sel">
          ${designs.map(x => `<option value="${esc(x.hash)}">${esc(x.hash)} · J ${esc(
            x.objective == null ? "–" : fmt(x.objective, 2))}${x.hash === hash0 ? " · best" : ""}</option>`).join("")}
        </select>
      </div>
    </div>
    <div class="card balloon-controls" role="group" aria-label="Balloon frequency and slice controls">
      <label for="balloon-freq">Frequency</label>
      <input id="balloon-freq" type="range" min="0" max="0" value="0" step="1" aria-label="Frequency index">
      <span class="balloon-slider-val" id="balloon-freq-val">–</span>
      <label for="balloon-az">Cut azimuth</label>
      <input id="balloon-az" type="range" min="-180" max="180" value="0" step="1" aria-label="Slice azimuth degrees">
      <span class="balloon-slider-val" id="balloon-az-val">0°</span>
    </div>
    <div class="fig" style="padding-bottom:14px">
      <h3>3D balloon — shape and colour both encode level</h3>
      <div class="cap">Radius = SPL above −30 dB (on-axis = full radius), colour = the directivity
        palette, white rings = −6 / −12 / −18 / −24 dB isobars. Not equal-area-sampled: shading is
        interpolated on the sphere, per the grid's sin(θ) layout note. Drag to orbit · scroll to
        zoom · right-drag to pan.</div>
      <div id="balloon-wrap" data-v3d><div class="view3d-fallback">Loading 3D…</div></div>
      <div id="balloon-hover" class="mono" aria-live="polite"></div>
    </div>
    <div class="grid2">
      <div class="fig">
        <h3>Radar — great-circle cut at the current frequency</h3>
        <div class="cap">r = SPL above −30 dB; rings at 0 / −6 / … / −30 dB. 0° up (+Z) → 180° down
          (−Z) on the right half; the left half mirrors the antipode (azimuth + 180°).</div>
        <canvas id="balloon-radar" class="balloon-radar" aria-label="Radar slice polar plot"></canvas>
      </div>
      <div class="fig">
        <h3>Slice — level vs frequency × polar angle</h3>
        <div class="cap">The balloon along the chosen azimuth, as a filled isobar map over the full
          solved band (log frequency). Same palette and −30..0 dB bar as the directivity views.</div>
        <svg id="balloon-slice" role="img" aria-label="Isobar slice at the chosen azimuth"></svg>
      </div>
    </div>
  </div>`;

  // ── state + wiring ──────────────────────────────────────────────────
  let payload = null, fi = 0, az = 0, view3d = null;
  const caption = document.getElementById("balloon-caption");
  const freqIn = document.getElementById("balloon-freq");
  const freqVal = document.getElementById("balloon-freq-val");
  const azIn = document.getElementById("balloon-az");
  const azVal = document.getElementById("balloon-az-val");
  const hoverEl = document.getElementById("balloon-hover");
  const radarCv = document.getElementById("balloon-radar");
  const sliceSvg = document.getElementById("balloon-slice");
  const wrap = document.getElementById("balloon-wrap");

  function captionFor() {
    if (!payload) return "";
    const [nT, nP] = payload.balloon_grid;
    return `<a href="#/run/${esc(runId)}"><code>${esc(payload.design)}</code></a> · ${esc(payload.label || "–")} · ` +
      `${payload.n_dof != null ? payload.n_dof.toLocaleString() + " dofs · " : ""}` +
      `${payload.freqs_hz.length} freqs · θ ${nT} × φ ${nP} grid` +
      `${payload.distance_m != null ? ` · SPL @ ${payload.distance_m} m` : ""} · normalised to on-axis, −30…0 dB window`;
  }

  async function loadDesign(hash) {
    wrap.innerHTML = `<div class="view3d-fallback">Loading balloon…</div>`;
    let P;
    try { P = await api(`/api/balloon/${encodeURIComponent(runId)}/${encodeURIComponent(hash)}`); }
    catch (e) {
      if (wrap.isConnected) wrap.innerHTML = `<div class="view3d-fallback">Could not load balloon: ${esc(e.message)}</div>`;
      return;
    }
    if (!wrap.isConnected) return;
    payload = P;
    caption.innerHTML = captionFor();
    // First look = the top of the band (the most directive, most shaped balloon): 300 Hz is
    // honestly near-omni on every horn and would read as a plain red ball.
    fi = payload.spl.length - 1;
    freqIn.max = String(fi);
    freqIn.value = String(fi);
    freqVal.textContent = `${fmtHz(payload.freqs_hz[fi])} · ${fi + 1}/${payload.freqs_hz.length}`;
    hoverEl.textContent = "";
    if (view3d) { view3d.dispose(); view3d = null; }
    view3d = await initBalloon3d(wrap, payload, { hover: t => { hoverEl.textContent = t; } });
    if (view3d && !wrap.isConnected) { view3d.dispose(); view3d = null; return; }  // gone mid-await
    view3d?.setFreq(fi);
    redraw2d();
  }

  let pending = null;
  function redraw2d() {
    if (pending) cancelAnimationFrame(pending);
    pending = requestAnimationFrame(() => {
      pending = null;
      if (!wrap.isConnected || !payload) return;
      drawRadar(radarCv, payload, fi, az);
      drawSlice();
    });
  }

  function drawSlice() {
    const [nT, nP] = payload.balloon_grid, floor = payload.min_db ?? -30;
    const thetas = [];
    for (let i = 0; i < nT; i++) thetas.push(180 * i / (nT - 1));
    const rows = payload.freqs_hz.map((f, i) => {
      const row = payload.spl[i];
      return thetas.map(th => splBilinear(row, nT, nP, th, az, floor));
    });
    isobarMap(sliceSvg, rows, thetas, payload.freqs_hz.map(Number),
      { H: 300, title: `great-circle azimuth ${az}°`, angleTicks: [0, 30, 60, 90, 120, 150, 180] });
  }

  freqIn.addEventListener("input", () => {
    fi = Math.max(0, Math.min(payload.spl.length - 1, +freqIn.value | 0));
    freqVal.textContent = `${fmtHz(payload.freqs_hz[fi])} · ${fi + 1}/${payload.freqs_hz.length}`;
    view3d?.setFreq(fi);
    redraw2d();
  });
  azIn.addEventListener("input", () => {
    az = (+azIn.value | 0);
    azVal.textContent = `${az}°`;
    redraw2d();
  });
  document.getElementById("balloon-design").onchange = e => loadDesign(e.target.value);

  await loadDesign(hash0);
}