// view3d.js — hornlab-search GUI   AGPL-3.0-or-later
// Three.js r160 mesh viewer for quarter-model horn meshes.
// Mirrors quarter model across x=0 and y=0 to reconstruct full horn.
// Falls back to a 2D wall-profile SVG if the CDN import fails.

let THREE, OrbitControls;

async function loadThree() {
  if (THREE) return true;
  try {
    const mod = await import("three");
    THREE = mod;
    const { OrbitControls: OC } = await import("three/addons/controls/OrbitControls.js");
    OrbitControls = OC;
    return true;
  } catch (e) {
    console.warn("view3d: three.js failed to load:", e);
    return false;
  }
}

/**
 * Mirror a quarter mesh to a full mesh.
 * quadrants: 1 means mirror across x=0 and y=0 (H/V symmetry).
 * verts: flat [x,y,z, x,y,z, ...] in mm
 * tris: flat [i,j,k, ...] indices
 * Returns { verts: Float32Array, tris: Uint32Array }
 */
function mirrorMesh(verts, tris, quadrants) {
  if (String(quadrants) !== "1") return { verts: new Float32Array(verts), tris: new Uint32Array(tris) };

  const nOrig = verts.length / 3;
  // Four copies: original (x,y,z), flip x (-x,y,z), flip y (x,-y,z), flip both (-x,-y,z)
  // We mark each vert to avoid duplicating verts on the x=0 or y=0 plane.
  // For simplicity, just create all four copies and deduplicate via epsilon later.
  // Simpler: just add all four quadrants and accept small duplication on seam.
  const copies = [[1, 1], [-1, 1], [1, -1], [-1, -1]];
  const allVerts = [];
  const allTris = [];
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

/**
 * Render a 2D wall profile as a fallback SVG.
 * profile: {h:[[z,r],...], v:[[z,r],...]} from run detail.
 */
function render2DFallback(container, profile) {
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

  const h = profile.h || [], v = profile.v || [];
  const all = [...h, ...v];
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

  const drawPts = (pts, sgn, color, dash) => {
    const pp = pts.map(p => [X(sgn * Math.abs(p[1])), Y(p[0])]).filter(p => isFinite(p[0]) && isFinite(p[1]));
    if (pp.length < 2) return;
    const path = document.createElementNS(NS, "path");
    path.setAttribute("d", pp.map((p,i) => (i?"L":"M")+p[0].toFixed(1)+","+p[1].toFixed(1)).join(""));
    path.setAttribute("fill","none"); path.setAttribute("stroke",color);
    path.setAttribute("stroke-width","2");
    if (dash) path.setAttribute("stroke-dasharray","5 3");
    svg.appendChild(path);
  };

  const cs = getComputedStyle(document.documentElement);
  const seedCol = cs.getPropertyValue("--seed").trim() || "#a3713a";
  const bestCol = cs.getPropertyValue("--best").trim() || "#0d6e7a";
  drawPts(h, 1, bestCol, false);
  drawPts(v, -1, bestCol, true);

  container.appendChild(svg);
  const lbl = document.createElement("div");
  lbl.style.cssText = "position:absolute;bottom:8px;right:12px;font-family:var(--f-mono);font-size:0.7rem;color:var(--muted);";
  lbl.textContent = "2D fallback — three.js unavailable";
  container.style.position = "relative";
  container.appendChild(lbl);
}

/**
 * Init the 3D view in `container`.
 * meshData: { quadrants, verts: [x,y,z,...], tris: [i,j,k,...] }
 * profile (optional): best design profile for 2D fallback.
 */
export async function init3d(container, meshData, profile) {
  container.innerHTML = "";

  const ok = await loadThree();
  if (!ok) { render2DFallback(container, profile); return; }

  const { verts: rawVerts, tris: rawTris, quadrants } = meshData;
  const { verts, tris } = mirrorMesh(rawVerts, rawTris, quadrants);

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(
    getComputedStyle(document.documentElement).getPropertyValue("--surface").trim() || "#ffffff"
  );

  // Geometry
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.BufferAttribute(verts, 3));
  geo.setIndex(new THREE.BufferAttribute(tris, 1));
  geo.computeVertexNormals();

  // Scale: verts are in mm — scale to metres for display
  geo.scale(0.001, 0.001, 0.001);

  const cs = getComputedStyle(document.documentElement);
  const accentHex = cs.getPropertyValue("--accent").trim() || "#0d6e7a";

  // Solid mesh
  const mat = new THREE.MeshPhongMaterial({
    color: new THREE.Color(accentHex), side: THREE.DoubleSide,
    transparent: true, opacity: 0.85, shininess: 40,
  });
  const mesh = new THREE.Mesh(geo, mat);
  scene.add(mesh);

  // Wireframe overlay
  const wmat = new THREE.MeshBasicMaterial({ color: 0x000000, wireframe: true, opacity: 0.08, transparent: true });
  scene.add(new THREE.Mesh(geo, wmat));

  // Lights
  scene.add(new THREE.AmbientLight(0xffffff, 0.5));
  const d1 = new THREE.DirectionalLight(0xffffff, 0.8);
  d1.position.set(1, 2, 2); scene.add(d1);
  const d2 = new THREE.DirectionalLight(0xffffff, 0.3);
  d2.position.set(-1, -1, -1); scene.add(d2);

  // Camera — fit to bounding box
  geo.computeBoundingBox();
  const box = geo.boundingBox;
  const center = new THREE.Vector3();
  box.getCenter(center);
  const size = new THREE.Vector3();
  box.getSize(size);
  const maxDim = Math.max(size.x, size.y, size.z);

  const w = container.clientWidth || 600, h = container.clientHeight || 400;
  const camera = new THREE.PerspectiveCamera(45, w / h, 0.001, 100);
  camera.position.set(center.x + maxDim * 1.2, center.y + maxDim * 0.8, center.z + maxDim * 1.5);
  camera.lookAt(center);

  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(window.devicePixelRatio);
  renderer.setSize(w, h);
  container.appendChild(renderer.domElement);

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
    geo.dispose(); mat.dispose(); wmat.dispose();
  };
}
