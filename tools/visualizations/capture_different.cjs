/** Film HornLab's real Evolution player with recording-tab-only presentation changes. */

const fs = require('node:fs/promises');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { chromium } = require(process.env.HORNLAB_PLAYWRIGHT || 'playwright');

const root = __dirname;
const outputRoot = process.env.HORNLAB_CAPTURE_ROOT
  ? path.resolve(root, process.env.HORNLAB_CAPTURE_ROOT)
  : path.join(root, 'different-horns');
const recordHex = process.env.HORNLAB_CAPTURE_COLOR || '#b9ff58';
const origin = 'http://127.0.0.1:8765';
const viewport = { width: 1080, height: 1920 };
const runs = [
 ['01-lecleach', '20261118T200653Z-screen-31495a'],
 ['02-rosse-rect', '20261117T053153Z-screen-15f0e4'],
 ['03-rrect-morph', '20261119T181029Z-screen-c3b6c6'],
 ['04-fold', '20261120T043857Z-screen-ae2855'],
 ['05-tritonia', '20261116T044917Z-screen-12eb61'],
 ['06-crowe-sculpted', '20261121T143911Z-screen-2f8cd1'],
 ['07-curved-lame', '20261117T082535Z-screen-dd6a6c'],
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
  source = replace(source, 'const F = E.frames || [];', 'const F = E.frames || [];');
  source = source.replace('evaluation ${f.n + 1} / ${F.length}', 'evaluation ${f.n + 1}');
  source = replace(source, 'if (!seq.length) seq = [0];', 'seq = seq.filter(i => window.__captureSolved.includes(F[i].n)); if (!seq.length) seq = [0];');
  return source;
}

function renderer(source, recordColor) {
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
    'const recordColor = new THREE.Color("' + recordColor + '");',
    'const missing = document.createElement("div");',
    'missing.className = "capture-no-mesh"; missing.hidden = true;',
    'missing.textContent = "No solved mesh"; container.appendChild(missing);',
    'let lastEvaluation, flashUntil = 0, pendingFlash = false;',
    'function setPlaybackAppearance(improved, hasMesh, evaluation) {',
    '  if (lastEvaluation !== evaluation) {',
    // Anchor the flash to the first painted frame AFTER the swap: a heavy mesh build can block the
    // render loop for longer than the flash itself, which would otherwise eat the improvement.
    '    pendingFlash = Boolean(improved && hasMesh);',
    '    flashUntil = 0;',
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
      'const flash = window.__captureFlash || 410;',
      'if (pendingFlash) { pendingFlash = false; flashUntil = performance.now() + flash; }',
      // 'all' mode holds the lime for the whole step (a hard cut at the next evaluation): a single
      // 173 ms decay can fall entirely inside a main-thread geometry build and never be painted.
      'const pulse = flashUntil ? (window.__captureHold ? 1 : Math.max(0, Math.min(1, (flashUntil - performance.now()) / flash))) : 0;',
      'if (pulse > 0 && window.__flashLog && window.__flashLog.lastEval !== lastEvaluation) {',
      '  window.__flashLog.lastEval = lastEvaluation;',
      '  window.__flashLog.push([lastEvaluation, +pulse.toFixed(2)]);',
      '}',
      'mat.color.copy(restingColor).lerp(recordColor, pulse);',
      'mat.emissive.copy(recordColor).multiplyScalar(.08 * pulse);',
      'renderer.render(scene, camera);',
    ].join('\n'),
  );
  segment = replace(segment, 'return { show, frames: prepared, dispose };', [
    'container._captureFlashNow = () => { pendingFlash = true; if (window.__flashLog) window.__flashLog.lastEval = undefined; };',
    'return { show, frames: prepared, dispose, setPlaybackAppearance };',
  ].join('\n'));
  return source.slice(0, at) + segment;
}

async function capture(browser, sources, slug, run, mode) {
  const payloadPath = path.join(root, '.capture-data', run + '.json');
  const payload = JSON.parse(await fs.readFile(payloadPath, 'utf8'));
  const frameCount = mode === 'all' ? payload.frames.length : payload.frames.filter(f => f.improved).length;
  // The flash must end before the next evaluation appears: in 'all' mode the 240 ms step would
  // otherwise bleed the lime into the following (non-improving) candidate, so the flash is paced
  // to the step instead of a fixed 410 ms.
  const stepMs = mode === 'all' ? 240 : 1200;
  const flashMs = mode === 'all' ? Math.round(stepMs * 0.72) : 410;
  const context = await browser.newContext({ viewport, colorScheme:'dark', reducedMotion:'no-preference' });
  const page = await context.newPage();
  await page.addInitScript(cfg => {
    window.__captureSolved = cfg.solved;
    window.__captureFlash = cfg.flash;
    window.__captureHold = cfg.hold;
    window.__flashLog = [];
    localStorage.setItem('hl-v3d-render', JSON.stringify({surface:'metallic',ridges:'on',light:1}));
    localStorage.setItem('hl-v3d-look', JSON.stringify({mesh:'gray', contours:'on', angle:0}));
  }, { solved: payload.frames.map(f => f.n), flash: flashMs, hold: mode === 'all' });
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
    }, stepMs);
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
      canvas: (() => { const c = document.querySelector('#evo-3d canvas'); return c ? c.getBoundingClientRect().toJSON() : null; })(),
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
    // Re-arm the opening frame: the seed is an improvement, but its first flash happened while
    // the 3D player was still being built, before the screencast was live.
    await page.evaluate(() => {
      const holder = document.getElementById('evo-3d');
      if (holder && holder._captureFlashNow) holder._captureFlashNow();
    });
    await page.waitForTimeout(550);
    await play.click();
    await page.mouse.move(12, 14);
    await page.waitForFunction(count => {
      const pos = document.querySelector('#evo-pos');
      const button = document.querySelector('#evo-play');
      return pos.textContent === count + ' / ' + count && button.textContent.includes('Play');
    }, frameCount, { timeout:600000 });
    await page.waitForTimeout(720);
    await page.screencast.stop();
    if (faults.length) throw new Error(faults.join('; '));
    const recorded = await page.evaluate(() => window.__recordedEvaluations);
    if (recorded.some(s => s.includes('No solved mesh') || s.includes('no mesh saved'))) throw new Error('Unsolved frame recorded');
    // Only improvement frames may carry the lime flash: the renderer logs every evaluation whose
    // pulse went above zero, so a bleed onto the next candidate would show up here.
    const flashed = await page.evaluate(() => window.__flashLog.map(entry => entry[0]));
    const improvedNs = payload.frames.filter(f => f.improved).map(f => f.n);
    const strayFlashes = flashed.filter(n => !improvedNs.includes(n));
    const missingFlashes = improvedNs.filter(n => !flashed.includes(n));
    if (strayFlashes.length) throw new Error('Non-improvement frames flashed: ' + strayFlashes.join(','));
    if (mode === 'all' && missingFlashes.length) throw new Error('Improvement frames did not flash: ' + missingFlashes.join(','));
    const statusText = (await status.innerText()).replace(/\s+/g, ' ');
    const temp = deliverable.slice(0, -4) + '.tmp.mp4';
    execFileSync('ffmpeg', [
      '-hide_banner', '-loglevel', 'error', '-y', '-i', raw, '-an', '-c:v', 'libx264',
      '-preset', 'fast', '-crf', '17', '-pix_fmt', 'yuv420p', '-r', '30', '-threads', '2',
      '-movflags', '+faststart', temp,
    ], { stdio:'inherit' });
    await fs.rename(temp, deliverable);
    console.log(label + ': ' + frameCount + ' playback frames; ' + flashed.length + ' flashes; ' + statusText);
    return {
      file:path.basename(deliverable), url, run, mode,
      skippedUnsolved:true, mesh:'gray', depthLines:true, rotationSpeed:3.6, playbackFrames:frameCount, parameterBars:check.params,
      canvasBounds:check.canvas,
      stageBounds:check.bounds,
      flashColor:recordHex,
      solvedMeshes:payload.frames.length,
      improvementFrames:improvedNs.length,
      withoutSolvedMesh:payload.total_evaluations-payload.frames.length,
      flashMs:mode === 'all' ? stepMs : flashMs,
      flashHeldForStep:mode === 'all',
      recordEvaluations:improvedNs,
      flashedEvaluations:flashed,
      flashOnlyImprovements:strayFlashes.length === 0,
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
  for (const [file, adapt] of [['evolution.js', evolution], ['view3d.js', source => renderer(source, recordHex)]]) {
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
