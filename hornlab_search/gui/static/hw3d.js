// hw3d.js — hornlab-search GUI   AGPL-3.0-or-later
//
// 3-D geometry tab for a horn + woofer case (handoff §5.6 "Geometry 3D", §6 P3).
// Two meshes from GET /api/hw/mesh/<exp>/<case>?part=box|horn, one scene:
//   box  = the staged/parent exterior, semi-transparent (opacity 0.15 / 0.45 / 0.85)
//   horn = the manifest mesh with its scale + translation already applied, solid
// The clearance record from /api/hw/case is drawn as a coloured measurement line; a violation
// also gets a red intersection plane/outline so the overlap is visible.
//
// UNITS: every mesh coordinate, bbox, camera distance, grid and scale bar is in MILLIMETRES.
// The API returns mm and we do not rescale: three.js is unitless, so the whole scene stays in one
// unit (mm) and the 100 mm bar is literally 100 scene units long.
//
// The viewer is lazy: hw.js calls mountHw3D only on ?tab=geometry3d. The [data-v3d] host carries
// _dispose3d, which app.js's route() sweep calls before replacing the view. mountHw3D returns the
// same dispose function for callers that need it explicitly.

import { css } from "./charts.js";
import { loadThree } from "./view3d.js";

const encKey = key => String(key).split("/").map(encodeURIComponent).join("/");
const esc = s => (s == null ? "" : String(s))
  .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
  .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
const num = (v, d = 1) => (v == null || !isFinite(v)) ? "?" : Number(v).toFixed(d);
const count = n => (n == null || !isFinite(n)) ? "?" : Number(n).toLocaleString("en-US");

async function api(path) {
  const r = await fetch(path);
  if (!r.ok) {
    let msg = String(r.status);
    try { const j = await r.json(); if (j && j.error) msg += " " + j.error; } catch { /* not JSON */ }
    throw new Error(msg);
  }
  return r.json();
}

const abortError = () => { const e = new Error("route changed"); e.aborted = true; return e; };

/** A CSS token as a THREE.Color, with a fallback for the first paint before theme tokens resolve. */
function tokenColor(THREE, name, fallback) {
  const v = css(name);
  try { return new THREE.Color(v || fallback); } catch { return new THREE.Color(fallback); }
}

function unionBboxes(a, b) {
  const lo = [0, 1, 2].map(i => Math.min(a[0][i], b[0][i]));
  const hi = [0, 1, 2].map(i => Math.max(a[1][i], b[1][i]));
  return { lo, hi, size: [hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]] };
}

/** Midpoint of the overlap on one axis, or the midpoint of the two nearest faces if separated. */
function overlapMid(a0, a1, b0, b1) {
  const lo = Math.max(a0, b0), hi = Math.min(a1, b1);
  if (lo <= hi) return (lo + hi) / 2;
  return a1 < b0 ? (a1 + b0) / 2 : (b1 + a0) / 2;
}

/**
 * The closest bbox faces along the separating axis, or the overlap slab when there is none.
 * All values are mm; the result is used only for the measurement overlay.
 */
function clearanceGeometry(boxB, hornB) {
  const b0 = boxB[0], b1 = boxB[1], h0 = hornB[0], h1 = hornB[1];
  const gaps = [0, 1, 2].map(i => Math.max(b0[i] - h1[i], h0[i] - b1[i]));
  const gap = Math.max(...gaps);
  const axis = gaps.indexOf(gap);
  const interLo = [0, 1, 2].map(i => Math.max(b0[i], h0[i]));
  const interHi = [0, 1, 2].map(i => Math.min(b1[i], h1[i]));
  const overlap = [0, 1, 2].map(i => interHi[i] - interLo[i]);
  const hasOverlap = overlap.every(v => v > 0);
  const pBox = [0, 0, 0], pHorn = [0, 0, 0];
  if (gap > 0) {
    // Separate along the largest positive gap; the other axes sit at the overlap midpoint.
    if (b1[axis] < h0[axis]) { pBox[axis] = b1[axis]; pHorn[axis] = h0[axis]; }
    else { pBox[axis] = b0[axis]; pHorn[axis] = h1[axis]; }
    for (const i of [0, 1, 2]) {
      if (i === axis) continue;
      const m = overlapMid(b0[i], b1[i], h0[i], h1[i]);
      pBox[i] = pHorn[i] = m;
    }
  } else {
    // No separating axis: use the assembly (z) axis through the intersection centre.
    pBox[0] = pHorn[0] = overlapMid(b0[0], b1[0], h0[0], h1[0]);
    pBox[1] = pHorn[1] = overlapMid(b0[1], b1[1], h0[1], h1[1]);
    pBox[2] = interLo[2]; pHorn[2] = interHi[2];
  }
  return { gap, axis, pBox, pHorn, interLo, interHi, overlap, hasOverlap };
}

/** Build the static 3-D viewer. Throws (so mountHw3D can fall back) on any load/build failure. */
async function build3d(host, key, opts, isDisposed) {
  host.innerHTML = `<p class="muted" role="status">Loading 3-D geometry…</p>`;
  const THREE = await loadThree();
  if (!THREE) throw new Error("three.js could not be loaded (CDN or import map unavailable)");
  let OrbitControls;
  try {
    ({ OrbitControls } = await import("three/addons/controls/OrbitControls.js"));
  } catch (e) {
    throw new Error(`OrbitControls could not be loaded (${e.message || e})`);
  }
  if (!host.isConnected || isDisposed()) throw abortError();

  const caseP = opts.caseData
    ? Promise.resolve(opts.caseData)
    : api(`/api/hw/case/${encKey(key)}`).catch(e => ({ error: e.message }));
  const [boxRes, hornRes] = await Promise.allSettled([
    api(`/api/hw/mesh/${encKey(key)}?part=box`),
    api(`/api/hw/mesh/${encKey(key)}?part=horn`),
  ]);
  const caseData = await caseP;
  if (boxRes.status !== "fulfilled" || hornRes.status !== "fulfilled") {
    const why = [];
    if (boxRes.status !== "fulfilled") why.push(`box mesh: ${boxRes.reason?.message || boxRes.reason}`);
    if (hornRes.status !== "fulfilled") why.push(`horn mesh: ${hornRes.reason?.message || hornRes.reason}`);
    return fallback(host, key, { ...opts, caseData }, why.join("; "));
  }
  if (!host.isConnected || isDisposed()) throw abortError();

  const box = boxRes.value, horn = hornRes.value;
  if (!box.verts?.length || !box.tris?.length) return fallback(host, key, { ...opts, caseData }, "the box mesh has no triangles");
  if (!horn.verts?.length || !horn.tris?.length) return fallback(host, key, { ...opts, caseData }, "the horn mesh has no triangles");

  const u = unionBboxes(box.bbox, horn.bbox);
  const maxDim = Math.max(...u.size);
  if (!isFinite(maxDim) || maxDim <= 0) return fallback(host, key, { ...opts, caseData }, "the mesh bounding box is empty");

  const stage = document.createElement("div");
  stage.className = "hw3d-stage";
  stage.setAttribute("role", "img");
  stage.setAttribute("aria-label",
    "3-D view of the staged box and horn in millimetres. Drag to orbit, scroll to zoom. " +
    "The clearance measurement is drawn as a coloured line.");
  const decimated = [box.decimated && "box", horn.decimated && "horn"].filter(Boolean);
  host.innerHTML = `
    <div class="hw3d-controls" role="group" aria-label="3-D view controls">
      <span class="hw3d-control-label">Box opacity</span>
      ${[0.15, 0.45, 0.85].map(o =>
        `<button type="button" class="btn btn-sm" data-hw3d-opacity="${o}" aria-pressed="${o === 0.45}"
          aria-label="Box opacity ${Math.round(o * 100)} percent">${Math.round(o * 100)}%</button>`).join("")}
      <button type="button" class="btn btn-sm" data-hw3d-horn aria-pressed="true"
        title="Show or hide the horn mesh">Horn</button>
      <button type="button" class="btn btn-sm" data-hw3d-reset
        title="Restore the starting camera">Reset view</button>
      <button type="button" class="btn btn-sm" disabled
        title="data_hw does not return probe positions, so no probe markers are drawn">probe positions not recorded</button>
    </div>
    <div class="hw3d-stage-host"></div>
    <p class="hw3d-note">box ${esc(count(box.triangle_count))} triangles · horn ${esc(count(horn.triangle_count))} triangles
      ${decimated.length ? `· decimated for display (${esc(decimated.join(", "))}, 60 k cap)` : ""}
      · frame: Boundary Lab project · units: mm</p>`;
  const stageHost = host.querySelector(".hw3d-stage-host");
  stageHost.appendChild(stage);

  const scene = new THREE.Scene();
  scene.background = tokenColor(THREE, "--viz-canvas", "#e9edf0");
  if (!css("--viz-canvas")) scene.background = tokenColor(THREE, "--surface", "#ffffff");

  const geo = payload => {
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.Float32BufferAttribute(new Float32Array(payload.verts), 3));
    g.setIndex(new THREE.Uint32BufferAttribute(new Uint32Array(payload.tris), 1));
    g.computeVertexNormals();
    g.computeBoundingBox();
    return g;
  };
  const boxGeo = geo(box), hornGeo = geo(horn);
  const boxMat = new THREE.MeshStandardMaterial({
    color: tokenColor(THREE, "--muted", "#8fa3ad"), roughness: 0.65, metalness: 0.02,
    transparent: true, opacity: 0.45, depthWrite: false, side: THREE.DoubleSide,
  });
  const hornMat = new THREE.MeshStandardMaterial({
    color: tokenColor(THREE, "--accent", "#0d6e7a"), roughness: 0.45, metalness: 0.04,
    side: THREE.DoubleSide,
  });
  const boxMesh = new THREE.Mesh(boxGeo, boxMat);
  const hornMesh = new THREE.Mesh(hornGeo, hornMat);
  boxMesh.renderOrder = 1;
  scene.add(boxMesh, hornMesh);

  // Lights: a hemisphere for the shadow side plus key/fill/rim, all scaled to the union.
  const center = new THREE.Vector3((u.lo[0] + u.hi[0]) / 2, (u.lo[1] + u.hi[1]) / 2, (u.lo[2] + u.hi[2]) / 2);
  const hemi = new THREE.HemisphereLight(0xffffff, 0x334048, 1.15);
  const keyLight = new THREE.DirectionalLight(0xffffff, 1.7);
  keyLight.position.copy(center).add(new THREE.Vector3(1.4, 2.2, 1.8).multiplyScalar(maxDim));
  const fill = new THREE.DirectionalLight(0xffffff, 0.55);
  fill.position.copy(center).add(new THREE.Vector3(-1.8, 0.5, 1.0).multiplyScalar(maxDim));
  const rim = new THREE.DirectionalLight(0xffffff, 0.65);
  rim.position.copy(center).add(new THREE.Vector3(-1.2, -1.0, -2.0).multiplyScalar(maxDim));
  scene.add(hemi, keyLight, fill, rim);

  // Grid: a truthful 100 mm pitch wherever the model fits, on the union's floor.
  const gridSpan = Math.max(200, Math.ceil(maxDim / 100) * 100);
  const grid = new THREE.GridHelper(gridSpan, Math.round(gridSpan / 100),
    tokenColor(THREE, "--muted", "#8fa3ad"), tokenColor(THREE, "--rule", "#c8d0d4"));
  grid.position.set(center.x, u.lo[1] - maxDim * 0.005, center.z);
  grid.material.transparent = true; grid.material.opacity = 0.38; grid.material.depthWrite = false;
  scene.add(grid);
  const axes = new THREE.AxesHelper(maxDim * 0.38);
  axes.position.set(u.lo[0], u.lo[1], u.lo[2]);
  axes.material.depthTest = false;
  axes.renderOrder = 2;
  scene.add(axes);

  // 100 mm scale bar at the front edge (mm are scene units). The label follows it on screen.
  const barLen = 100;
  const barX = center.x - barLen / 2;
  const barY = u.lo[1];
  const barZ = u.hi[2] + maxDim * 0.08;
  const barTick = Math.max(4, maxDim * 0.012);
  const barPts = [
    barX, barY, barZ, barX + barLen, barY, barZ,
    barX, barY - barTick, barZ, barX, barY + barTick, barZ,
    barX + barLen, barY - barTick, barZ, barX + barLen, barY + barTick, barZ,
  ];
  const barGeo = new THREE.BufferGeometry();
  barGeo.setAttribute("position", new THREE.Float32BufferAttribute(barPts, 3));
  const barMat = new THREE.LineBasicMaterial({
    color: tokenColor(THREE, "--accent", "#0d6e7a"), depthTest: false, transparent: true,
  });
  const bar = new THREE.LineSegments(barGeo, barMat);
  bar.renderOrder = 6;
  scene.add(bar);
  const barMid = new THREE.Vector3(barX + barLen / 2, barY + barTick, barZ);

  // Clearance measurement from the case record, drawn between the closest bbox faces.
  const row = caseData && caseData.row ? caseData.row : {};
  const rec = row.clearance || null;
  const status = rec && rec.status ? String(rec.status) : "NOT_CHECKED";
  const cg = clearanceGeometry(box.bbox, horn.bbox);
  const recordGapMm = rec && rec.aabb_gap_m != null ? rec.aabb_gap_m * 1000 : null;
  const overlapMm = cg.hasOverlap ? cg.overlap[cg.axis] : Math.abs(recordGapMm || cg.gap);
  const isPass = status === "PASS";
  const isViolation = /VIOLATION/i.test(status);
  const isUnproven = /UNPROVEN/i.test(status);
  const color = isPass ? tokenColor(THREE, "--good", "#2f7d3b")
    : isViolation ? tokenColor(THREE, "--bad", "#b23a3a")
    : tokenColor(THREE, "--warn", "#8a5414");
  const colorClass = isPass ? "pass" : isViolation ? "violation" : "warn";
  const labelText = isPass
    ? `gap ${num(recordGapMm == null ? cg.gap : recordGapMm, 1)} mm (bbox lower bound)`
    : isViolation
      ? `${status} · overlap ${num(overlapMm, 1)} mm (bbox)`
      : isUnproven
        ? `${status} · bbox gap ${num(cg.gap, 1)} mm`
        : "clearance not checked";
  const lineGeo = new THREE.BufferGeometry();
  lineGeo.setAttribute("position", new THREE.Float32BufferAttribute([
    cg.pBox[0], cg.pBox[1], cg.pBox[2], cg.pHorn[0], cg.pHorn[1], cg.pHorn[2],
  ], 3));
  const lineMat = new THREE.LineBasicMaterial({ color, depthTest: false, transparent: true, opacity: 0.95 });
  const line = new THREE.Line(lineGeo, lineMat);
  line.renderOrder = 7;
  scene.add(line);
  // End ticks, so a 3 mm violation line is still visible.
  const tickLen = Math.max(6, maxDim * 0.018);
  const tickPts = [];
  for (const p of [cg.pBox, cg.pHorn]) {
    tickPts.push(p[0], p[1] - tickLen, p[2], p[0], p[1] + tickLen, p[2]);
  }
  const tickGeo = new THREE.BufferGeometry();
  tickGeo.setAttribute("position", new THREE.Float32BufferAttribute(tickPts, 3));
  const tickMat = new THREE.LineBasicMaterial({ color, depthTest: false, transparent: true, opacity: 0.95 });
  const ticks = new THREE.LineSegments(tickGeo, tickMat);
  ticks.renderOrder = 7;
  scene.add(ticks);
  // A violation gets a red plane over the intersection area plus a red 3-D intersection outline.
  let overlapPlane = null, overlapEdge = null;
  if (isViolation || (cg.hasOverlap && !isPass)) {
    const w = Math.max(1, cg.interHi[0] - cg.interLo[0]);
    const h = Math.max(1, cg.interHi[1] - cg.interLo[1]);
    const pg = new THREE.PlaneGeometry(w, h);
    const pm = new THREE.MeshBasicMaterial({
      color, transparent: true, opacity: 0.38, side: THREE.DoubleSide,
      depthWrite: false, depthTest: false,
    });
    overlapPlane = new THREE.Mesh(pg, pm);
    overlapPlane.position.set((cg.interLo[0] + cg.interHi[0]) / 2, (cg.interLo[1] + cg.interHi[1]) / 2,
      (cg.interLo[2] + cg.interHi[2]) / 2);
    overlapPlane.renderOrder = 5;
    scene.add(overlapPlane);
    if (cg.hasOverlap) {
      const bx = new THREE.Box3(new THREE.Vector3(...cg.interLo), new THREE.Vector3(...cg.interHi));
      overlapEdge = new THREE.Box3Helper(bx, color);
      overlapEdge.material.depthTest = false;
      overlapEdge.material.transparent = true;
      overlapEdge.material.opacity = 0.9;
      overlapEdge.renderOrder = 6;
      scene.add(overlapEdge);
    }
  }
  const clearMid = new THREE.Vector3(
    (cg.pBox[0] + cg.pHorn[0]) / 2, (cg.pBox[1] + cg.pHorn[1]) / 2, (cg.pBox[2] + cg.pHorn[2]) / 2);

  // Renderer + camera framed to both bboxes. All distances are mm.
  const w = stage.clientWidth || 640, h = stage.clientHeight || 420;
  const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "low-power" });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setSize(w, h);
  renderer.domElement.tabIndex = 0;
  renderer.domElement.setAttribute("role", "img");
  renderer.domElement.setAttribute("aria-label",
    "Interactive 3-D view of the box and horn in millimetres. Use the buttons above for box opacity, horn visibility and reset.");
  stage.appendChild(renderer.domElement);

  const camera = new THREE.PerspectiveCamera(45, w / h, Math.max(0.1, maxDim / 1000), maxDim * 100);
  const home = new THREE.Vector3(center.x + maxDim * 1.15, center.y + maxDim * 0.75, center.z + maxDim * 1.5);
  camera.position.copy(home);
  camera.lookAt(center);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.target.copy(center);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.update();

  host._hw3dInfo = () => ({
    triangles: renderer.info.render.triangles,
    geometries: renderer.info.memory.geometries,
    textures: renderer.info.memory.textures,
    calls: renderer.info.render.calls,
  });

  // Overlays: a static unit/axes hint and two labels that are projected from world space each frame.
  const hud = document.createElement("div");
  hud.className = "hw3d-hud";
  hud.innerHTML = `<span>grid 100 mm</span><span>100 mm bar</span><span>axes: x / y / z</span><span>units: mm</span>`;
  stage.appendChild(hud);
  const clearLabel = document.createElement("div");
  clearLabel.className = `hw3d-clearance-label ${colorClass}`;
  clearLabel.textContent = labelText;
  stage.appendChild(clearLabel);
  const scaleLabel = document.createElement("div");
  scaleLabel.className = "hw3d-scale-label";
  scaleLabel.textContent = "100 mm";
  stage.appendChild(scaleLabel);

  const project = (v, el) => {
    const cw = stage.clientWidth || w, ch = stage.clientHeight || h;
    const p = v.clone().project(camera);
    const x = (p.x * 0.5 + 0.5) * cw;
    const y = (-p.y * 0.5 + 0.5) * ch;
    const visible = p.z > -1 && p.z < 1 && x > 8 && x < cw - 8 && y > 8 && y < ch - 8;
    el.style.display = visible ? "block" : "none";
    if (visible) el.style.transform = `translate(-50%,-50%) translate(${x}px,${y}px)`;
  };
  const updateLabels = () => {
    project(clearMid, clearLabel);
    project(barMid, scaleLabel);
  };

  const ro = new ResizeObserver(entries => {
    for (const e of entries) {
      const nw = Math.max(1, Math.round(e.contentRect.width));
      const nh = Math.max(1, Math.round(e.contentRect.height));
      renderer.setSize(nw, nh);
      camera.aspect = nw / nh;
      camera.updateProjectionMatrix();
      updateLabels();
    }
  });
  ro.observe(stage);

  // Toggles: box opacity (three pressed states), horn visible, reset view.
  host.querySelectorAll("button[data-hw3d-opacity]").forEach(btn => btn.addEventListener("click", () => {
    const o = Number(btn.dataset.hw3dOpacity);
    boxMat.opacity = isFinite(o) ? o : 0.45;
    boxMat.transparent = true;
    boxMat.needsUpdate = true;
    host.querySelectorAll("button[data-hw3d-opacity]").forEach(b =>
      b.setAttribute("aria-pressed", String(b === btn)));
  }));
  host.querySelector("button[data-hw3d-horn]").addEventListener("click", e => {
    hornMesh.visible = !hornMesh.visible;
    e.currentTarget.setAttribute("aria-pressed", String(hornMesh.visible));
  });
  host.querySelector("button[data-hw3d-reset]").addEventListener("click", () => {
    camera.position.copy(home);
    controls.target.copy(center);
    controls.update();
    updateLabels();
  });

  let raf = 0;
  const tick = () => {
    raf = requestAnimationFrame(tick);
    controls.update();
    updateLabels();
    renderer.render(scene, camera);
  };
  tick();
  const resizeNow = () => {
    const nw = Math.max(1, Math.round(stage.clientWidth || w));
    const nh = Math.max(1, Math.round(stage.clientHeight || h));
    renderer.setSize(nw, nh);
    camera.aspect = nw / nh;
    camera.updateProjectionMatrix();
  };
  resizeNow();
  updateLabels();

  let disposed = false;
  const dispose = () => {
    if (disposed) return;
    disposed = true;
    cancelAnimationFrame(raf);
    ro.disconnect();
    controls.dispose();
    scene.traverse(obj => {
      if (!obj) return;
      if (obj.geometry) obj.geometry.dispose();
      const mats = Array.isArray(obj.material) ? obj.material : (obj.material ? [obj.material] : []);
      for (const m of mats) {
        for (const k of Object.keys(m)) {
          const v = m[k];
          if (v && v.isTexture) v.dispose();
        }
        m.dispose();
      }
    });
    renderer.dispose();
    if (renderer.forceContextLoss) renderer.forceContextLoss();
    if (renderer.domElement && renderer.domElement.parentNode) {
      renderer.domElement.parentNode.removeChild(renderer.domElement);
    }
    host.innerHTML = "";
    host._hw3dInfo = () => ({ triangles: 0, geometries: 0, textures: 0, calls: 0 });
    host._dispose3d = () => {};
  };
  return dispose;
}

/** 2-D fallback: warn why 3-D is unavailable and render the existing elevations, never a blank panel. */
async function fallback(host, key, opts, reason) {
  host.innerHTML = "";
  host._hw3dInfo = () => ({ triangles: 0, geometries: 0, textures: 0, calls: 0 });
  host._dispose3d = () => {};
  const warn = document.createElement("div");
  warn.className = "alert warn";
  warn.setAttribute("role", "alert");
  warn.innerHTML = `<b>3-D is unavailable.</b> ${esc(reason || "the 3-D libraries or meshes could not be loaded")}. Showing the 2-D elevations instead.`;
  host.appendChild(warn);
  const stage = document.createElement("div");
  stage.className = "hw3d-fallback";
  host.appendChild(stage);
  try {
    const d = opts.caseData || await api(`/api/hw/case/${encKey(key)}`);
    const draw = typeof opts.drawGeometry === "function"
      ? opts.drawGeometry
      : (await import("./hw.js")).drawGeometry;
    if (d && d.geometry) draw(stage, d.geometry, d.row);
    else stage.insertAdjacentHTML("beforeend",
      `<p class="muted">No staged meshes are on disk for this case, so there are no elevations to draw.</p>`);
  } catch (e) {
    stage.insertAdjacentHTML("beforeend",
      `<p class="muted">The 2-D elevations are unavailable too: ${esc(e.message || e)}</p>`);
  }
  return () => {};
}

/**
 * Mount the 3-D viewer lazily. Returns a dispose function; the same function is installed on
 * host._dispose3d for app.js's [data-v3d] route sweep. The host must be connected to the document.
 */
export async function mountHw3D(host, key, opts = {}) {
  let disposed = false;
  host._dispose3d = () => { disposed = true; };
  host._hw3dInfo = () => ({ triangles: 0, geometries: 0, textures: 0, calls: 0 });
  try {
    const dispose = await build3d(host, key, opts, () => disposed);
    host._dispose3d = dispose;
    if (disposed) { dispose(); return () => {}; }
    return dispose;
  } catch (e) {
    if (e && e.aborted) return () => {};
    const dispose = await fallback(host, key, opts, e.message || String(e));
    host._dispose3d = dispose;
    if (disposed) dispose();
    return dispose;
  }
}
