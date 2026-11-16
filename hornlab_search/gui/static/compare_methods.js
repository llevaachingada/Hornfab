// Compare-methods board: renders a declarative comparison spec from recorded rows only.
// No score math here; the backend view model names every number's source.
const esc = value => String(value ?? "—").replace(/[&<>"']/g, ch => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
}[ch]));
const fmt = (value, digits = 3) => {
  const number = Number(value);
  return value == null || !Number.isFinite(number) ? "—" :
    number.toLocaleString("en-US", {maximumFractionDigits: digits});
};
const label = value => String(value ?? "").replace(/_/g, " ");
const statusClass = status => status === "ready" ? "good" : status === "partial" ? "warn" : status === "missing" ? "" : "bad";

function verdictText(entry) {
  const verdict = entry?.verdict;
  if (verdict === "incomplete") return "Incomplete";
  if (verdict === "inconclusive") return "Inconclusive";
  if (verdict) return `${verdict} wins`;
  return "—";
}

function comparisonCard(entry) {
  if (!entry) return "";
  const bits = [];
  if (entry.gap != null) bits.push(`median gap ${fmt(entry.gap)} J`);
  if (entry.spread != null) bits.push(`larger seed spread ${fmt(entry.spread)} J`);
  return `<article class="bo-panel" data-comparison="${esc(entry.id)}">
    <div class="bo-head"><h3>${esc(entry.id || "comparison")}</h3><span class="pill ${statusClass(entry.status === "ready" ? "ready" : entry.status)}">${esc(verdictText(entry))}</span></div>
    <p class="muted">${esc(entry.rule || "declared rule")}${bits.length ? ` · ${bits.map(esc).join(" · ")}` : ""}</p>
    ${entry.reason ? `<p class="muted">${esc(entry.reason)}</p>` : ""}
  </article>`;
}

export function renderMethodBoard(board) {
  if (!board || typeof board !== "object") return '<p role="alert">The comparison board could not be loaded.</p>';
  const methods = board.methods || {};
  const methodRows = Object.entries(methods).map(([name, stats]) => `<tr><td>${esc(name)}</td><td class="r mono">${fmt(stats.n, 0)}</td><td class="r mono">${fmt(stats.n_verified, 0)}</td><td class="r mono">${fmt(stats.median_verify_j)}</td><td class="r mono">${fmt(stats.seed_spread)}</td><td class="r mono">${fmt(stats.median_screens_to_target, 1)}</td></tr>`).join("");
  const arms = Array.isArray(board.arms) ? board.arms : [];
  const armRows = arms.map(arm => `<tr><td>${esc(arm.id)}${arm.study_id ? ` <span class="muted mono">${esc(arm.study_id.slice(0, 8))}</span>` : ""}</td><td>${esc(arm.method)}</td><td>${esc(arm.policy || "—")}</td><td class="r mono">${fmt(arm.screens, 0)}</td><td class="r mono">${fmt(arm.verify, 0)}</td><td class="r mono">${fmt(arm.best_screen_j)}</td><td class="r mono">${fmt(arm.best_verify_j)}</td><td class="r mono">${arm.screens_to_target == null ? "—" : fmt(arm.screens_to_target, 0)}</td><td>${arm.complete ? '<span class="pill good">ok</span>' : '<span class="pill warn">incomplete</span>'}</td></tr>`).join("");
  const cards = (Array.isArray(board.comparisons) ? board.comparisons : []).map(comparisonCard).join("");
  const notes = (Array.isArray(board.notes) ? board.notes : []).map(note => `<li>${esc(note)}</li>`).join("");
  return `<section class="study-workspace" aria-label="Compare methods">
    <header><p class="eyebrow">Pre-declared comparison</p><h2>${esc(board.name || "Method comparison")}</h2>
      <p class="muted">${board.objective_version != null ? `Objective v${esc(board.objective_version)} · ` : ""}${board.target_j != null ? `target J ${fmt(board.target_j)} · ` : ""}recorded rows only</p></header>
    <div class="bo-comparison-grid">${cards || '<p class="muted">No declared comparison.</p>'}</div>
    <h2>Methods</h2>
    ${methodRows ? `<div class="tbl-scroll"><table><thead><tr><th>Method</th><th class="r">Arms</th><th class="r">Verified</th><th class="r">Median verify J</th><th class="r">Seed spread</th><th class="r">Median screens to target</th></tr></thead><tbody>${methodRows}</tbody></table></div><p class="bo-scroll-hint">Scroll horizontally for all columns →</p>` : '<p class="muted">No method statistics yet.</p>'}
    <h2>Arms</h2>
    ${armRows ? `<div class="tbl-scroll"><table><thead><tr><th>Arm</th><th>Method</th><th>Policy</th><th class="r">Screens</th><th class="r">Verify</th><th class="r">Best screen J</th><th class="r">Best verify J</th><th class="r">Screens to target</th><th>Status</th></tr></thead><tbody>${armRows}</tbody></table></div><p class="bo-scroll-hint">Scroll horizontally for all columns →</p>` : '<p class="muted">No arms match this spec yet.</p>'}
    ${notes ? `<ul class="bo-notes">${notes}</ul>` : ""}
    <p class="muted">Screen J is reported but does not decide; the pre-declared rule does. Missing arms make the verdict incomplete, never a guess.</p>
  </section>`;
}

export function renderComparisonList(comparisons, selected) {
  const items = Array.isArray(comparisons) ? comparisons : [];
  if (!items.length) return '<p class="muted">No comparison specs found under <code>tools/analysis/specs/bo_*.yaml</code>.</p>';
  return `<label for="comparison-select" class="fam-meta">Comparison</label>
    <select id="comparison-select" class="sort-sel">${items.map(item => `<option value="${esc(item.name)}"${item.name === selected ? " selected" : ""}>${esc(item.label || item.name)}</option>`).join("")}</select>`;
}

/** Mount the comparison board.  api: {list({signal}), board(name,{signal})}. */
export function mountCompareMethods(root, {api, onError = () => {}}) {
  if (!root || !api || typeof api.list !== "function" || typeof api.board !== "function") throw new Error("Invalid comparison mount");
  const controller = new AbortController();
  let disposed = false, notice = "", list = [], selected = null, board = null, loading = false;
  const draw = () => {
    if (disposed) return;
    root.innerHTML = `<section class="study-workspace" aria-label="Compare methods">
      <header><p><a href="#/bayes/studies">Bayes</a> / Compare methods</p><h1>Compare methods</h1>
      <p class="muted">Pre-declared rules over matched arms; every number comes from a recorded run.</p></header>
      ${notice ? `<p role="alert">${esc(notice)}</p>` : ""}
      ${list.length ? `<p>${renderComparisonList(list, selected)}</p>` : ""}
      ${loading ? '<p class="muted">Loading…</p>' : (board ? renderMethodBoard(board) : "")}
    </section>`;
    const select = root.querySelector("#comparison-select");
    if (select) select.onchange = () => load(select.value);
  };
  async function load(name) {
    if (disposed || !name || loading) return;
    loading = true; notice = ""; selected = name; board = null; draw();
    try {
      const next = await api.board(name, {signal: controller.signal});
      if (disposed) return;
      board = next;
    } catch (error) {
      if (disposed || error?.name === "AbortError") return;
      notice = "The comparison board could not be loaded."; onError(error);
    } finally {
      loading = false; draw();
    }
  }
  async function start() {
    try {
      const response = await api.list({signal: controller.signal});
      if (disposed) return;
      list = Array.isArray(response?.comparisons) ? response.comparisons : [];
      if (!list.length) { notice = "No comparison specs are available."; draw(); return; }
      await load(list[0].name);
    } catch (error) {
      if (disposed || error?.name === "AbortError") return;
      notice = "Comparison specs could not be loaded."; onError(error); draw();
    }
  }
  draw(); start();
  return () => { disposed = true; controller.abort(); };
}
