// verify.js — hornlab-search GUI   AGPL-3.0-or-later
//
// Verify view: table, KPIs, scatter, per-design panel, compare-two.
// Entered from #/run/<id>/verify and #/run/<id>/verify/compare.
//
// WP0: stub only — renders a placeholder via the existing skel/errBanner patterns.
// WP1 (backend), WP3 (table/KPIs/scatter), WP6 (panel/compare) fill the full view.

// ── XSS helper (local copy, same as app.js) ────────────────────────────────
const esc = s => (s == null ? "–" : String(s))
  .replace(/&/g, "&amp;")
  .replace(/</g, "&lt;")
  .replace(/>/g, "&gt;")
  .replace(/"/g, "&quot;")
  .replace(/'/g, "&#39;");

function errBanner(msg) {
  return `<div class="alert error" role="alert"><b>Error:</b> ${esc(msg)}</div>`;
}

function skel(root, msg = "") {
  root.innerHTML = `<div class="stack skeleton" style="gap:18px;opacity:0.6">
    <div class="skeleton-block" style="height:2.2rem;width:min(260px,60%)"></div>
    <div class="skeleton-block" style="height:1rem;width:min(400px,80%)"></div>
    <div class="skeleton-block" style="height:180px"></div>
    ${msg ? `<p class="muted" style="opacity:0.5;font-size:0.82rem">${esc(msg)}</p>` : ""}
  </div>`;
}

// ── Main entry point (called from app.js ROUTES) ───────────────────────────

/**
 * Render the verify view for a run.
 *
 * @param {HTMLElement} root   - The view-root element (replaced on every navigation).
 * @param {string}      runId  - Run id string.
 * @param {string}      mode   - "table" or "compare".
 * @param {string}      query  - Query string (without leading "?").
 */
export async function viewVerify(root, runId, mode, query) {
  skel(root, "Loading verify view…");
  root.innerHTML = `<div class="stack" style="max-width:860px">
    <p class="muted" style="font-size:0.85rem">← <a href="#/run/${esc(runId)}">${esc(runId)}</a></p>
    <h2>Verify view coming soon</h2>
    <p>The verify view for run <code>${esc(runId)}</code> (mode: ${esc(mode)}) is under construction.</p>
    <p class="hint">Use the command line to inspect verify results:
      <code>hornlab-search verify --run "runs/${esc(runId)}" --top 5</code>
    </p>
  </div>`;
}
