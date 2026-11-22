/** Film HornLab's real Evolution player with recording-tab-only presentation changes. */

const fs = require('node:fs/promises');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { chromium } = require(process.env.HORNLAB_PLAYWRIGHT || 'playwright');

const root = __dirname;
const outputRoot = path.join(root, 'revision-2');
const origin = 'http://127.0.0.1:8765';
const viewport = { width: 1080, height: 1920 };
const runs = [
  ['01-rolled-spiral', '20261116T001222Z-screen-b25d61'],
  ['02-rolled-vbeak', '20261119T172313Z-screen-081506'],
  ['03-ath-petal', '20261119T155454Z-screen-d1a61d'],
  ['04-curved-lame', '20261117T082535Z-screen-dd6a6c'],
  ['05-sculpted-r3', '20261121T135752Z-screen-8c15a8'],
  ['06-biradial-19-steps', '20261116T090751Z-screen-37b115'],
  ['07-lame-beak-17-steps', '20261117T071329Z-screen-e4f90d'],
  ['08-split-14-steps', '20261120T233156Z-screen-9e1688'],
];

const framing = [
  'html.capture-evolution { --capture-width:938px; }',
  '.capture-evolution body { overflow:hidden; }',
  '.capture-evolution #app-nav { display:none !important; }',
  '.capture-evolution #app-main { padding:42px 0 0 !important; width:100%; max-width:none !important; }',
  '.capture-evolution .evo { width:var(--capture-width); margin:0 auto; gap:11px !important; }',
  '.capture-evolution .evo > div:first-child { display:none; }',
  '.capture-evolution .evo .fig { padding:10px 20px 12px; border-radius:8px; }',
  '.capture-evolution .evo h3 { font:500 20px var(--f-mono); margin:3px 0 10px; }',
  '.capture-evolution .evo .cap, .capture-evolution #evo-3d-wrap h3 { display:none; }',
  '.capture-evolution .evo-opt, .capture-evolution #evo-3d-note { display:none!important; }',
  '.capture-evolution .evo-controls { flex-wrap:nowrap; padding:10px 16px; }',
  '.capture-evolution .evo-controls button { font-size:16px; }',
  '.capture-evolution #evo-pos { font-size:17px; text-align:right; }',
  '.capture-evolution .evo-status { font:17px var(--f-mono); padding:10px 17px; }',
  '.capture-evolution #evo-3d-wrap > div { padding:0; border:0; background:none; }',
  '.capture-evolution #evo-3d { height:960px !important; }',
  '.capture-evolution #evo-3d canvas + div { font-size:14px !important; }',
  '.capture-evolution #evo-3d > div:has(select[data-v3d-pref]) { display:none !important; }',
  '.capture-evolution .evo > div:nth-last-child(2) { display:none; }',
  '.capture-evolution .evo > div:last-child { display:grid; grid-template-columns:1fr; gap:10px; }',
  '.capture-evolution #evo-score { height:237px; }',
  '.capture-evolution .evo-knob { font-size:17px; grid-template-columns:210px 1fr 74px; }',
  '.capture-evolution .evo-knobs { gap:5px; }',
  '.capture-evolution .evo-knobs.capture-many { grid-template-columns:repeat(2,minmax(0,1fr)); column-gap:24px; }',
  '.capture-evolution .capture-many .evo-knob { font-size:15px; grid-template-columns:156px 1fr 58px; }',
  '.capture-evolution .capture-no-mesh { position:absolute; inset:0; display:grid; place-content:center; font:17px var(--f-mono); color:var(--muted); pointer-events:none; }',
  '.capture-evolution .capture-no-mesh[hidden] { display:none; }',
].join('\n');

function replace(source, before, after) {
  if (!source.includes(before)) throw new Error('Capture adaptation could not find: ' + before);
  return source.replace(before, after);
}

function evolution(source) {
  source = replace(source,
    'if (mode !== "best") { mode = "best"; document.getElementById("evo-mode").value = "best"; buildSeq(); }',
    '/* Capture can play every row; unsolved rows have no 3D mesh. */',
  );
  source = replace(source, 'if (j3 != null) player3d.show(j3);', [
    'if (j3 != null) player3d.show(j3);',
    'player3d.setPlaybackAppearance(Boolean(f.improved), j3 != null, f.n);',
  ].join('\n'));
  source = replace(source, 'const F = E.frames || [];', 'const F = (E.frames || []).filter(f => window.__captureSolved.includes(f.n));');
  source = source.replace('evaluation ${f.n + 1} / ${F.length}', 'evaluation ${f.n + 1}');
  return source;
}

function renderer(source) {
  const marker = 'export async function init3dFrames';
  const at = source.indexOf(marker);
  if (at < 0) throw new Error('No Evolution renderer in live app');
  let segment = source.slice(at);
  segment = replace(segment,
    'camera.position.set(center.x + maxDim * 1.2, center.y + maxDim * 0.8, center.z + maxDim * 1.5);',
    'camera.position.set(center.x + maxDim * 1.22, center.y + maxDim * .54, center.z + maxDim * 1.50); camera.zoom=1.43; camera.updateProjectionMatrix();',
  );
  segment = replace(segment, 'controls.target.copy(center);', [
    'controls.target.copy(center);',
    'controls.autoRotate = true;',
    'controls.autoRotateSpeed = 3.6;',
  ].join('\n'));
  segment = replace(segment, 'let cur = -1, raf;', [
    'let cur = -1, raf;',
    'const restingColor = mat.color.clone();',
    'const recordColor = new THREE.Color("#b9ff58");',
    'const missing = document.createElement("div");',
    'missing.className = "capture-no-mesh"; missing.hidden = true;',
    'missing.textContent = "No solved mesh"; container.appendChild(missing);',
    'let lastEvaluation, flashUntil = 0;',
    'function setPlaybackAppearance(improved, hasMesh, evaluation) {',
    '  if (lastEvaluation !== evaluation) {',
    '    flashUntil = improved && hasMesh ? performance.now() + 410 : 0;',
    '    lastEvaluation = evaluation;',
    '  }',
    '  mesh.visible = hasMesh;',
    '  missing.hidden = hasMesh;',
    '}',
  ].join('\n'));
  segment = replace(segment,
    'controls.update();\n    renderer.render(scene, camera);',
    [
      'controls.update();',
      'wire.visible = mesh.visible && renderPrefs.ridges !== "off";',
      'const pulse = Math.max(0, Math.min(1, (flashUntil - performance.now()) / 290));',
      'mat.color.copy(restingColor).lerp(recordColor, pulse);',
      'mat.emissive.copy(recordColor).multiplyScalar(.08 * pulse);',
      'renderer.render(scene, camera);',
    ].join('\n'),
  );
  segment = replace(segment, 'return { show, frames: prepared, dispose };',
    'return { show, frames: prepared, dispose, setPlaybackAppearance };');
  return source.slice(0, at) + segment;
}

async function capture(browser, sources, slug, run, mode) {
  const payloadPath = path.join(root, '.capture-data', run + '.json');
  const payload = JSON.parse(await fs.readFile(payloadPath, 'utf8'));
  const frameCount = mode === 'all' ? payload.frames.length : payload.frames.filter(f => f.improved).length;
  const context = await browser.newContext({ viewport, colorScheme:'dark', reducedMotion:'no-preference' });
  const page = await context.newPage();
  await page.addInitScript(solved => {
    window.__captureSolved = solved;
    localStorage.setItem('hl-v3d-look', JSON.stringify({mesh:'gray', contours:'on', angle:0}));
  }, payload.frames.map(f => f.n));
  const faults = [];
  page.on('pageerror', error => { faults.push(error.message); });
  const label = slug + '-' + (mode === 'all' ? 'all-evaluations' : 'improvements');
  const raw = path.join(root, '.capture-data', label + '.webm');
  const deliverable = path.join(outputRoot, 'reels', label + '.mp4');
  try {
    await page.route(/\/(?:evolution|view3d)\.js(?:\?.*)?$/, async route => {
      const asset = path.posix.basename(new URL(route.request().url()).pathname);
      await route.fulfill({ body:sources[asset], contentType:'text/javascript; charset=utf-8' });
    });
    await page.route('**/api/evolution/' + run + '/frames3d', async route => {
      const frames = mode === 'all' ? payload.frames : payload.frames.filter(frame => frame.improved);
      await route.fulfill({ json: { ...payload, frames } });
    });
    const url = origin + '/#/run/' + run + '/evolution?mode=' + mode;
    await page.goto(url, { waitUntil:'domcontentloaded' });
    const status = page.locator('#evo-status');
    const play = page.locator('#evo-play');
    await status.waitFor({ state:'visible', timeout:45000 });
    await page.locator('#evo-loop').uncheck();
    await page.locator('#evo-speed').evaluate((el, speed) => {
      el.add(new Option('capture', String(speed))); el.value=String(speed);
    }, mode === 'all' ? 240 : 1200);
    await page.addStyleTag({ content: framing });
    await page.evaluate(() => {
      document.documentElement.classList.add('capture-evolution');
      const knobs = document.querySelector('#evo-knobs');
      if (knobs.children.length > 11) knobs.classList.add('capture-many');
    });
    await page.locator('#evo-3d-toggle').evaluate(el => el.click());
    await page.locator('#evo-3d canvas').waitFor({ state:'visible', timeout:45000 });
    await page.waitForFunction(() => !document.querySelector('#evo-3d-note').textContent.startsWith('Building'));
    const check = await page.evaluate(() => ({
      params: document.querySelectorAll('.evo-knob').length,
      bounds: document.querySelector('.evo').getBoundingClientRect().toJSON(),
      mode: document.querySelector('#evo-mode').value,
      first: document.querySelector('#evo-pos').textContent,
    }));
    if (check.mode !== mode || check.first !== '1 / ' + frameCount || check.params === 0 || check.bounds.bottom > viewport.height) {
      throw new Error('Unexpected playback state: ' + JSON.stringify(check));
    }
    await page.mouse.move(12, 14);
    await page.evaluate(() => {
      window.__recordedEvaluations=[];
      new MutationObserver(() => {
        const status=document.querySelector('#evo-status').textContent;
        window.__recordedEvaluations.push(status);
      }).observe(document.querySelector('#evo-status'),{childList:true,subtree:true});
    });
    await page.screencast.start({ path:raw, size:viewport, fps:30, quality:90 });
    await page.waitForTimeout(550);
    await play.click();
    await page.mouse.move(12, 14);
    await page.waitForFunction(count => {
      const pos = document.querySelector('#evo-pos');
      const button = document.querySelector('#evo-play');
      return pos.textContent === count + ' / ' + count && button.textContent.includes('Play');
    }, frameCount, { timeout:240000 });
    await page.waitForTimeout(720);
    await page.screencast.stop();
    if (faults.length) throw new Error(faults.join('; '));
    const recorded = await page.evaluate(() => window.__recordedEvaluations);
    if (recorded.some(s => s.includes('No solved mesh') || s.includes('no mesh saved'))) throw new Error('Unsolved frame recorded');
    const statusText = (await status.innerText()).replace(/\s+/g, ' ');
    const temp = deliverable.slice(0, -4) + '.tmp.mp4';
    execFileSync('ffmpeg', [
      '-hide_banner', '-loglevel', 'error', '-y', '-i', raw, '-an', '-c:v', 'libx264',
      '-preset', 'fast', '-crf', '17', '-pix_fmt', 'yuv420p', '-r', '30', '-threads', '2',
      '-movflags', '+faststart', temp,
    ], { stdio:'inherit' });
    await fs.rename(temp, deliverable);
    console.log(label + ': ' + frameCount + ' playback frames; ' + statusText);
    return {
      file:path.basename(deliverable), url, run, mode,
      skippedUnsolved:true, mesh:'gray', depthLines:true, rotationSpeed:3.6, playbackFrames:frameCount, parameterBars:check.params,
      solvedMeshes:payload.frames.length,
      withoutSolvedMesh:payload.total_evaluations-payload.frames.length,
      recordEvaluations:payload.frames.filter(f => f.improved).map(f => f.n),
    };
  } catch (error) {
    error.message += ' ' + label + ' | ' + faults.join('; ');
    throw error;
  } finally {
    await context.close();
  }
}

async function main() {
  const command = process.argv.slice(2);
  const picks = (command[0] || '1,2,3,4,5').split(',').map(n => runs[Number(n)-1]);
  const modes = command[1] ? [command[1]] : ['best', 'all'];
  if (picks.some(pick => !pick) || modes.some(m => !['best','all'].includes(m))) {
    throw new Error('Use capture_evolution.cjs [1,2,3,4,5] [best|all]');
  }
  await fs.mkdir(path.join(outputRoot, 'reels'), {recursive:true});
  const manifestFile = path.join(outputRoot, 'capture-sources.json');
  const manifest = JSON.parse(await fs.readFile(manifestFile,'utf8').catch(() => '{}'));
  const sources = {};
  for (const [file, adapt] of [['evolution.js', evolution], ['view3d.js', renderer]]) {
    const response = await fetch(origin + '/' + file);
    if (!response.ok) throw new Error('HornLab asset ' + file + ' returned ' + response.status);
    sources[file] = adapt((await response.text()).replace(/\r\n/g, '\n'));
  }
  const browser = await chromium.launch({ channel:'chrome', headless:true, args:['--enable-unsafe-swiftshader'] });
  try {
    for (const [slug, run] of picks) {
      for (const mode of modes) {
        const result = await capture(browser, sources, slug, run, mode);
        manifest[result.file] = result;
        await fs.writeFile(manifestFile, JSON.stringify(manifest, null, 2) + '\n', 'utf8');
      }
    }
  } finally {
    await browser.close();
  }
}

main().catch(error => { console.error(error); process.exitCode = 1; });
