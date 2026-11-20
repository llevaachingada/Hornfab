// DOM-stub lifecycle harness for the horn + woofer (hw*) GUI modules. No jsdom/playwright is
// installed; this exercises the real module graph from disk (hw.js, hw_screen.js, hw_new.js,
// hw_compare.js, hw_dsp.js, hw3d.js + charts/glossary) against a hand-written DOM stub.
//
// The harness proves three things the router depends on:
//   1. every view mounts on a fresh container with a contract-shaped /api/hw payload and paints,
//   2. the 3D tab installs _dispose3d on its [data-v3d] host and the router sweep calls it once,
//   3. mount -> dispose does not leak listeners, observers or timers (10 cycles), and
//   4. the DSP page is fed per-channel arrays only — no summed/combined field is ever touched.
//
// The stub lives here on purpose: production modules are never modified for this test.

import assert from "node:assert/strict";
import { pathToFileURL, fileURLToPath } from "node:url";

// ── deterministic clock / timer tracking ─────────────────────────────────────────────────────
const realSetTimeout = globalThis.setTimeout.bind(globalThis);
const realClearTimeout = globalThis.clearTimeout.bind(globalThis);
const pendingTimers = new Set();
let timerSeq = 0;
globalThis.setTimeout = (fn, ms, ...args) => {
  const id = ++timerSeq;
  const handle = realSetTimeout(() => {
    pendingTimers.delete(id);
    try { fn(...args); } catch (e) { console.error("stub timer callback failed:", e); }
  }, ms);
  pendingTimers.set(id, handle);
  return id;
};
globalThis.clearTimeout = id => {
  const handle = pendingTimers.get(id);
  if (handle != null) realClearTimeout(handle);
  pendingTimers.delete(id);
};

// requestAnimationFrame is counted but never scheduled: the stub reports a non-zero width, so
// charts.js does not need the resize retry, and a non-zero count at the end means a real loop.
let rafPending = 0;
globalThis.requestAnimationFrame = () => { rafPending += 1; return rafPending; };
globalThis.cancelAnimationFrame = () => { rafPending = 0; };

// ── global stubs shared by the modules ──────────────────────────────────────────────────────
const listenerRecords = new Set();          // { el, type, fn }
const observerRecords = new Set();          // { targets:Set<element> }

const escapeText = s => String(s)
  .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const escapeAttr = s => String(s)
  .replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");
const decodeEntities = s => String(s)
  .replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"')
  .replace(/&#39;/g, "'").replace(/&amp;/g, "&");

const VOID_TAGS = new Set([
  "area", "base", "br", "col", "embed", "hr", "img", "input",
  "link", "meta", "param", "source", "track", "wbr",
]);

// ── a very small CSS selector matcher (the subset the hw modules use) ──────────────────────
function splitTopLevel(selector, separator) {
  const out = [];
  let cur = "";
  let depth = 0;
  let quote = null;
  for (const ch of String(selector)) {
    if (quote) {
      cur += ch;
      if (ch === quote) quote = null;
      continue;
    }
    if (ch === '"' || ch === "'") { quote = ch; cur += ch; continue; }
    if (ch === "[" || ch === "(") depth += 1;
    else if (ch === "]" || ch === ")") depth -= 1;
    if (ch === separator && depth === 0) {
      if (cur.trim()) out.push(cur.trim());
      cur = "";
      continue;
    }
    cur += ch;
  }
  if (cur.trim()) out.push(cur.trim());
  return out;
}

function parseAttrExpression(expr) {
  const eq = expr.indexOf("=");
  if (eq < 0) return { name: expr.trim().toLowerCase(), value: null };
  const name = expr.slice(0, eq).trim().toLowerCase();
  let value = expr.slice(eq + 1).trim();
  if ((value.startsWith('"') && value.endsWith('"'))
    || (value.startsWith("'") && value.endsWith("'"))) {
    value = value.slice(1, -1);
  }
  return { name, value: decodeEntities(value) };
}

function compileSimple(part) {
  const compiled = { tag: null, id: null, classes: [], attrs: [], pseudos: [] };
  let i = 0;
  const tagMatch = /^([a-zA-Z][\w:-]*|\*)/.exec(part);
  if (tagMatch) {
    if (tagMatch[1] !== "*") compiled.tag = tagMatch[1].toLowerCase();
    i = tagMatch[0].length;
  }
  while (i < part.length) {
    const ch = part[i];
    if (ch === "#") {
      const m = /^[A-Za-z0-9_-]+/.exec(part.slice(i + 1));
      if (!m) break;
      compiled.id = m[0];
      i += 1 + m[0].length;
    } else if (ch === ".") {
      const m = /^[A-Za-z0-9_-]+/.exec(part.slice(i + 1));
      if (!m) break;
      compiled.classes.push(m[0]);
      i += 1 + m[0].length;
    } else if (ch === "[") {
      let j = i + 1;
      let quote = null;
      for (; j < part.length; j++) {
        const c = part[j];
        if (quote) { if (c === quote) quote = null; }
        else if (c === '"' || c === "'") quote = c;
        else if (c === "]") break;
      }
      compiled.attrs.push(parseAttrExpression(part.slice(i + 1, j)));
      i = j + 1;
    } else if (ch === ":") {
      const m = /^:([A-Za-z-]+)/.exec(part.slice(i));
      if (!m) { i += 1; continue; }
      let name = m[1];
      i += m[0].length;
      let arg = null;
      if (part[i] === "(") {
        let depth = 1;
        let j = i + 1;
        for (; j < part.length; j++) {
          if (part[j] === "(") depth += 1;
          else if (part[j] === ")") { depth -= 1; if (depth === 0) break; }
        }
        arg = part.slice(i + 1, j);
        i = j + 1;
      }
      compiled.pseudos.push({ name, arg });
    } else {
      i += 1;
    }
  }
  return compiled;
}

const selectorCache = new Map();
function compileSelector(selector) {
  if (selectorCache.has(selector)) return selectorCache.get(selector);
  const groups = splitTopLevel(selector, ",").map(group =>
    splitTopLevel(group, " ").filter(Boolean).map(compileSimple));
  selectorCache.set(selector, groups);
  return groups;
}

function matchesSimple(el, simple) {
  if (!el || el.nodeType !== 1) return false;
  if (simple.tag && el.tagName.toLowerCase() !== simple.tag) return false;
  if (simple.id && el.getAttribute("id") !== simple.id) return false;
  for (const cls of simple.classes) if (!el.classList.contains(cls)) return false;
  for (const attr of simple.attrs) {
    if (!el.hasAttribute(attr.name)) return false;
    if (attr.value != null && String(el.getAttribute(attr.name)) !== attr.value) return false;
  }
  for (const pseudo of simple.pseudos) {
    if (pseudo.name === "checked") {
      if (!el.checked) return false;
    } else if (pseudo.name === "not") {
      if (matchesSelector(el, pseudo.arg)) return false;
    } else if (pseudo.name === "first-child") {
      if (!el.parentNode || el.parentNode.children[0] !== el) return false;
    } else if (pseudo.name === "last-child") {
      if (!el.parentNode || el.parentNode.children[el.parentNode.children.length - 1] !== el) return false;
    } else {
      return false;
    }
  }
  return true;
}

function matchesComplex(el, simples) {
  if (!matchesSimple(el, simples[simples.length - 1])) return false;
  let index = simples.length - 2;
  let node = el.parentElement;
  while (index >= 0 && node) {
    if (matchesSimple(node, simples[index])) index -= 1;
    node = node.parentElement;
  }
  return index < 0;
}

function matchesSelector(el, selector) {
  return compileSelector(selector).some(group => matchesComplex(el, group));
}

function descendantElements(root) {
  const out = [];
  const visit = el => {
    for (const child of el.children) {
      if (child.nodeType !== 1) continue;
      out.push(child);
      visit(child);
    }
  };
  visit(root);
  return out;
}

// ── DOM stub ────────────────────────────────────────────────────────────────────────────────
const rect = () => ({
  width: 760, height: 420, top: 0, left: 0, right: 760, bottom: 420, x: 0, y: 0,
  toJSON() { return { width: 760, height: 420, top: 0, left: 0 }; },
});

class StubElement {
  constructor(tag, doc = null) {
    this.ownerDocument = doc;
    this.tagName = String(tag).toUpperCase();
    this.nodeType = 1;
    this.parentNode = null;
    this.children = [];
    this._attrs = new Map();
    this._classes = new Set();
    this._listeners = new Map();
    this._raw = "";
    this._textOverride = null;
    this._textParts = [];
    this._checked = false;
    this._selected = false;
    this.value = "";
    this.scrollWidth = 1200;
    this.clientWidth = 760;
    this.clientHeight = 420;
    this.scrollLeft = 0;
    this.width = 300;
    this.height = 150;
    this.style = {
      cssText: "",
      setProperty() {},
      removeProperty() {},
    };
  }

  // ── attributes / properties ──
  setAttribute(name, value) {
    const n = String(name).toLowerCase();
    const v = value == null ? "" : String(value);
    this._attrs.set(n, v);
    if (n === "class") this._classes = new Set(v.split(/\s+/).filter(Boolean));
    else if (n === "checked") this._checked = true;
    else if (n === "selected") this._selected = true;
  }
  getAttribute(name) {
    const n = String(name).toLowerCase();
    return this._attrs.has(n) ? this._attrs.get(n) : null;
  }
  hasAttribute(name) { return this._attrs.has(String(name).toLowerCase()); }
  removeAttribute(name) {
    const n = String(name).toLowerCase();
    this._attrs.delete(n);
    if (n === "class") this._classes.clear();
    else if (n === "checked") this._checked = false;
    else if (n === "selected") this._selected = false;
  }
  get id() { return this.getAttribute("id") || ""; }
  set id(v) { this.setAttribute("id", v); }
  get className() { return [...this._classes].join(" "); }
  set className(v) { this.setAttribute("class", v); }
  get classList() {
    const self = this;
    return {
      add(...items) {
        const next = new Set(self._classes);
        for (const item of items) next.add(String(item));
        self.setAttribute("class", [...next].join(" "));
      },
      remove(...items) {
        const next = new Set(self._classes);
        for (const item of items) next.delete(String(item));
        self.setAttribute("class", [...next].join(" "));
      },
      toggle(item, force) {
        const name = String(item);
        const on = force == null ? !self._classes.has(name) : !!force;
        if (on) self._classes.add(name); else self._classes.delete(name);
        self.setAttribute("class", [...self._classes].join(" "));
        return on;
      },
      contains(item) { return self._classes.has(String(item)); },
      get length() { return self._classes.size; },
    };
  }
  get dataset() {
    const self = this;
    const attrName = key => "data-" + String(key).replace(/[A-Z]/g, m => "-" + m.toLowerCase());
    return {
      get(key) {
        const v = self.getAttribute(attrName(key));
        return v == null ? undefined : v;
      },
      set(key, value) { self.setAttribute(attrName(key), String(value)); return true; },
      has(key) { return self.hasAttribute(attrName(key)); },
      delete(key) { self.removeAttribute(attrName(key)); },
    };
  }
  get hidden() { return this.hasAttribute("hidden"); }
  set hidden(v) { if (v) this.setAttribute("hidden", ""); else this.removeAttribute("hidden"); }
  get open() { return this.hasAttribute("open"); }
  set open(v) { if (v) this.setAttribute("open", ""); else this.removeAttribute("open"); }
  get checked() { return this._checked; }
  set checked(v) { this._checked = !!v; }
  get selected() { return this._selected; }
  set selected(v) { this._selected = !!v; }
  get disabled() { return this.hasAttribute("disabled"); }
  set disabled(v) { if (v) this.setAttribute("disabled", ""); else this.removeAttribute("disabled"); }
  get title() { return this.getAttribute("title") || ""; }
  set title(v) { this.setAttribute("title", v); }
  get href() { return this.getAttribute("href") || ""; }
  set href(v) { this.setAttribute("href", v); }
  get name() { return this.getAttribute("name") || ""; }
  set name(v) { this.setAttribute("name", v); }
  get type() { return this.getAttribute("type") || ""; }
  set type(v) { this.setAttribute("type", v); }
  get parentElement() {
    return this.parentNode && this.parentNode.nodeType === 1 ? this.parentNode : null;
  }
  get isConnected() {
    let node = this;
    while (node) {
      if (node === globalThis.document?.documentElement) return true;
      node = node.parentNode;
    }
    return false;
  }

  // ── tree / HTML ──
  get innerHTML() { return this._raw; }
  set innerHTML(value) {
    this._raw = value == null ? "" : String(value);
    this._textOverride = null;
    this._textParts = [];
    for (const child of this.children) child.parentNode = null;
    this.children = [];
    parseInto(this, this._raw);
  }
  get outerHTML() {
    const attrs = [...this._attrs].map(([k, v]) =>
      v === "" ? ` ${k}` : ` ${k}="${escapeAttr(v)}"`).join("");
    const name = this.tagName.toLowerCase();
    if (VOID_TAGS.has(name)) return `<${name}${attrs}>`;
    return `<${name}${attrs}>${this._raw}</${name}>`;
  }
  get textContent() {
    if (this._textOverride != null) return this._textOverride;
    return this._textParts.join("") + this.children.map(c => c.textContent).join("");
  }
  set textContent(value) {
    this._textOverride = value == null ? "" : String(value);
    this._raw = escapeText(this._textOverride);
    this._textParts = [];
    for (const child of this.children) child.parentNode = null;
    this.children = [];
  }
  appendChild(node) {
    if (node == null) return node;
    if (typeof node === "string") {
      this._raw += escapeText(node);
      this._textParts.push(node);
      return node;
    }
    node.parentNode = this;
    this.children.push(node);
    this._raw += node.outerHTML;
    return node;
  }
  append(...nodes) {
    for (const node of nodes) this.appendChild(node);
  }
  insertBefore(node, ref) {
    if (!ref) return this.appendChild(node);
    node.parentNode = this;
    const index = this.children.indexOf(ref);
    if (index < 0) this.children.push(node); else this.children.splice(index, 0, node);
    this._raw += node.outerHTML;
    return node;
  }
  insertAdjacentHTML(position, html) {
    const value = String(html);
    if (position === "afterbegin") {
      this._raw = value + this._raw;
      parseInto(this, value);
    } else {
      this._raw += value;
      parseInto(this, value);
    }
  }
  remove() {
    if (!this.parentNode) return;
    const index = this.parentNode.children.indexOf(this);
    if (index >= 0) this.parentNode.children.splice(index, 1);
    this.parentNode = null;
  }
  replaceWith(node) {
    if (!this.parentNode) return;
    const index = this.parentNode.children.indexOf(this);
    if (index < 0) return;
    this.parentNode.children[index] = node;
    node.parentNode = this.parentNode;
    this.parentNode = null;
  }
  contains(node) {
    let cur = node;
    while (cur) {
      if (cur === this) return true;
      cur = cur.parentNode;
    }
    return false;
  }

  // ── selectors ──
  matches(selector) { return matchesSelector(this, selector); }
  closest(selector) {
    let node = this;
    while (node && node.nodeType === 1) {
      if (matchesSelector(node, selector)) return node;
      node = node.parentNode;
    }
    return null;
  }
  querySelectorAll(selector) {
    const groups = compileSelector(selector);
    return descendantElements(this).filter(el =>
      groups.some(group => matchesComplex(el, group)));
  }
  querySelector(selector) {
    return this.querySelectorAll(selector)[0] || null;
  }

  // ── events ──
  addEventListener(type, fn) {
    if (typeof fn !== "function") return;
    if (!this._listeners.has(type)) this._listeners.set(type, new Set());
    this._listeners.get(type).add(fn);
    listenerRecords.add({ el: this, type, fn });
  }
  removeEventListener(type, fn) {
    const set = this._listeners.get(type);
    if (set) set.delete(fn);
    for (const record of listenerRecords) {
      if (record.el === this && record.type === type && record.fn === fn) listenerRecords.delete(record);
    }
  }
  dispatchEvent(event) {
    const ev = event || {};
    if (!ev.target) ev.target = this;
    const set = this._listeners.get(ev.type);
    if (set) for (const fn of [...set]) fn(ev);
    return true;
  }
  click() {
    return this.dispatchEvent({
      type: "click", target: this, button: 0,
      preventDefault() {}, stopPropagation() {},
    });
  }
  focus() { globalThis.document.activeElement = this; }
  select() {}
  blur() { if (globalThis.document.activeElement === this) globalThis.document.activeElement = null; }

  // ── geometry / canvas hooks ──
  getBoundingClientRect() { return rect(); }
  getClientRects() { return [rect()]; }
  getContext() {
    return {
      fillRect() {}, clearRect() {}, save() {}, restore() {}, beginPath() {},
      moveTo() {}, lineTo() {}, stroke() {}, fill() {}, closePath() {}, arc() {},
      createImageData: (w, h) => ({ data: new Uint8ClampedArray(Math.max(1, w * h * 4)) }),
      putImageData() {}, drawImage() {}, setTransform() {},
    };
  }
}

class StubText {
  constructor(text) { this.nodeType = 3; this.textContent = String(text); this.parentNode = null; }
}
class StubFragment {
  constructor(doc) { this.ownerDocument = doc; this.nodeType = 11; this.children = []; this.parentNode = null; }
  appendChild(node) { node.parentNode = this; this.children.push(node); return node; }
}

function parseAttrs(source, el) {
  const re = /([^\s=/>]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]*)))?/g;
  let match;
  while ((match = re.exec(source))) {
    const name = match[1];
    if (!name || name === "/") continue;
    const value = match[2] != null ? match[2]
      : match[3] != null ? match[3]
      : match[4] != null ? match[4] : "";
    el.setAttribute(name, decodeEntities(value));
  }
}

function parseInto(parent, html) {
  const doc = parent.ownerDocument || globalThis.document;
  let i = 0;
  while (i < html.length) {
    const lt = html.indexOf("<", i);
    if (lt === -1) break;
    if (html.startsWith("<!--", lt)) {
      const end = html.indexOf("-->", lt + 4);
      i = end === -1 ? html.length : end + 3;
      continue;
    }
    if (html.startsWith("</", lt)) {
      const end = html.indexOf(">", lt + 2);
      i = end === -1 ? html.length : end + 1;
      continue;
    }
    let j = lt + 1;
    let quote = null;
    let tagEnd = -1;
    for (; j < html.length; j++) {
      const ch = html[j];
      if (quote) { if (ch === quote) quote = null; }
      else if (ch === '"' || ch === "'") quote = ch;
      else if (ch === ">") { tagEnd = j; break; }
    }
    if (tagEnd === -1) break;
    const raw = html.slice(lt + 1, tagEnd);
    const selfClosing = /\/\s*$/.test(raw);
    const content = selfClosing ? raw.replace(/\/\s*$/, "") : raw;
    const nameMatch = /^([a-zA-Z][\w:.-]*)/.exec(content);
    if (!nameMatch) { i = tagEnd + 1; continue; }
    const name = nameMatch[1];
    const child = doc.createElement(name);
    parseAttrs(content.slice(nameMatch[0].length), child);
    child.parentNode = parent;
    parent.children.push(child);
    if (!selfClosing && !VOID_TAGS.has(name.toLowerCase())) {
      // Nested content is parsed flat by this scanner only to build a tree; the raw string on
      // ancestor elements is what the test asserts against, so no per-child raw is required.
      const close = findMatchingClose(html, tagEnd + 1, name);
      if (close > tagEnd + 1) parseInto(child, html.slice(tagEnd + 1, close));
      i = close > tagEnd + 1 ? close : tagEnd + 1;
      // Skip the closing tag when present.
      if (html.startsWith("</", i)) {
        const end = html.indexOf(">", i + 2);
        i = end === -1 ? html.length : end + 1;
      }
    } else {
      i = tagEnd + 1;
    }
  }
}

function findMatchingClose(html, from, name) {
  const lower = name.toLowerCase();
  let depth = 1;
  let i = from;
  while (i < html.length) {
    const lt = html.indexOf("<", i);
    if (lt === -1) return html.length;
    if (html.startsWith("<!--", lt)) {
      const end = html.indexOf("-->", lt + 4);
      i = end === -1 ? html.length : end + 3;
      continue;
    }
    if (html.startsWith("</", lt)) {
      const end = html.indexOf(">", lt + 2);
      const closeName = html.slice(lt + 2, end).trim().toLowerCase();
      if (closeName === lower) {
        depth -= 1;
        if (depth === 0) return lt;
      }
      i = end === -1 ? html.length : end + 1;
      continue;
    }
    let j = lt + 1;
    let quote = null;
    let tagEnd = -1;
    for (; j < html.length; j++) {
      const ch = html[j];
      if (quote) { if (ch === quote) quote = null; }
      else if (ch === '"' || ch === "'") quote = ch;
      else if (ch === ">") { tagEnd = j; break; }
    }
    if (tagEnd === -1) return html.length;
    const raw = html.slice(lt + 1, tagEnd);
    const nameMatch = /^([a-zA-Z][\w:.-]*)/.exec(raw);
    if (nameMatch && nameMatch[1].toLowerCase() === lower && !/\/\s*$/.test(raw)) depth += 1;
    i = tagEnd + 1;
  }
  return html.length;
}

// ── document / window ───────────────────────────────────────────────────────────────────────
const documentElement = new StubElement("html");
const head = new StubElement("head");
const body = new StubElement("body");
documentElement.appendChild(head);
documentElement.appendChild(body);

const documentStub = {
  documentElement, head, body, activeElement: null,
  createElement(tag) {
    const el = new StubElement(tag, documentStub);
    return el;
  },
  createElementNS(ns, tag) {
    const el = new StubElement(tag, documentStub);
    el.namespaceURI = ns;
    return el;
  },
  createTextNode(text) { return new StubText(text); },
  createDocumentFragment() { return new StubFragment(documentStub); },
  getElementById(id) {
    return descendantElements(documentElement).find(el => el.getAttribute("id") === String(id)) || null;
  },
  querySelector(selector) { return documentElement.querySelector(selector); },
  querySelectorAll(selector) { return documentElement.querySelectorAll(selector); },
  addEventListener(type, fn) { listenerRecords.add({ el: documentStub, type, fn }); },
  removeEventListener(type, fn) {
    for (const record of listenerRecords) {
      if (record.el === documentStub && record.type === type && record.fn === fn) listenerRecords.delete(record);
    }
  },
};

const cssTokens = {
  "--ink": "#111111", "--muted": "#666666", "--accent": "#0d6e7a", "--best": "#2f7d3b",
  "--rule": "#c8d0d4", "--bad": "#b23a3a", "--good": "#2f7d3b", "--warn": "#8a5414",
  "--surface": "#ffffff", "--bg": "#f7f7f7", "--viz-canvas": "#e9edf0", "--label": "#444444",
};
const getComputedStyleStub = () => ({
  getPropertyValue(name) { return cssTokens[name] || ""; },
});

const windowStub = {
  devicePixelRatio: 1,
  isConnected: true,
  getComputedStyle: getComputedStyleStub,
  matchMedia: () => ({
    matches: false,
    addEventListener() {}, removeEventListener() {},
    addListener() {}, removeListener() {},
  }),
  addEventListener(type, fn) { listenerRecords.add({ el: windowStub, type, fn }); },
  removeEventListener(type, fn) {
    for (const record of listenerRecords) {
      if (record.el === windowStub && record.type === type && record.fn === fn) listenerRecords.delete(record);
    }
  },
  scrollTo() {},
  requestAnimationFrame: globalThis.requestAnimationFrame,
  cancelAnimationFrame: globalThis.cancelAnimationFrame,
};

globalThis.document = documentStub;
globalThis.window = windowStub;
globalThis.getComputedStyle = getComputedStyleStub;
globalThis.localStorage = {
  getItem() { return null; },
  setItem() {},
  removeItem() {},
};
globalThis.location = { hash: "" };
const pushed = [];
globalThis.history = {
  pushState(state, title, url) { pushed.push(url); globalThis.location.hash = url; },
  replaceState(state, title, url) { globalThis.location.hash = url; },
};
globalThis.ResizeObserver = class StubResizeObserver {
  constructor(callback) {
    this.callback = callback;
    this._record = { targets: new Set() };
    observerRecords.add(this._record);
  }
  observe(target) { this._record.targets.add(target); }
  unobserve(target) { this._record.targets.delete(target); }
  disconnect() { this._record.targets.clear(); observerRecords.delete(this._record); }
};

// ── leak accounting (only attached nodes count) ────────────────────────────────────────────
function liveListenerCount() {
  let count = 0;
  for (const record of listenerRecords) {
    const el = record.el;
    if (el === documentStub || el === windowStub || (el && el.isConnected)) count += 1;
  }
  return count;
}
function liveObserverCount() {
  let count = 0;
  for (const record of observerRecords) {
    for (const target of record.targets) {
      if (target && target.isConnected) { count += 1; break; }
    }
  }
  return count;
}

// ── deterministic fetch: contract-shaped, tiny, never a real store ─────────────────────────
const fetchLog = [];
const KEY_A = "bl_demo/20260101T000000Z-demo-case-0001-abcd1234";
const KEY_B = "bl_demo/20260101T000000Z-demo-case-0002-abcd5678";
const STUDY_ID = "0123456789abcdef";

const caseRow = (key, ref, state = "solved") => ({
  key, case: key.split("/")[1], experiment: key.split("/")[0], family: "bl_case",
  ref, gate: "g4wide", state, declared: true,
  box: {
    width_mm: 371.2, height_mm: 371.2, depth_mm: 1078.8, wall_mm: 18,
    driver_diameter_mm: 300, driver_y_mm: 180, port_area_cm2: 180,
    port_length_mm: 210, port_y_mm: 80, port_nfr: 8,
    mesh_size_mm: 18, detail_size_mm: 6,
  },
  horn: { translation_mm: [0, 0, 12.5], mesh: "horn.msh", mesh_role: "main", source_group: "horn" },
  clearance: { status: "PASS", aabb_gap_m: 0.0125, source: "manifest" },
  solve: { fmin_hz: 200, fmax_hz: 2000, done: 25, total: 25 },
  tokens: [], note: null, fidelity: "SCREEN_MAGNITUDE", status: "proposed",
  motor: "real", transducer_shape: "real", integrity: "ok", kind: "bl_case",
  validate_valid: true, pair_with: null, parent: null,
});

const CASE_A = caseRow(KEY_A, "ref_case");
const CASE_B = caseRow(KEY_B, "demo_case");

const overviewPayload = () => ({
  store: "runs/system",
  kpis: { screens: 1, shortlisted: 3, checked_in_bl: 1, solved: 1, blocked_decisions: 1 },
  readiness: {
    updated: "2026-01-01T00:00:00Z", risks_total: 2,
    risks_by_level: { HIGH: 1, LOW: 1 },
    open_decisions: [{ id: 3, blocks: "decision 3", question: "Calibration policy?", recommendation: "Answer it." }],
  },
  next_step: { id: "read", label: "Next: Read", why: "One case is solved.", href: "#/hw/cases" },
  recent_screens: [{
    study_id: STUDY_ID, mtime_utc: "2026-01-01T00:00:00Z",
    horn: { brief_id: "demo-horn", design_hash: "abcdef1234567890" },
    driver_count: 1, counts: { shortlist_rows: 3, bl_panel_fit_rejected: 0 },
    counts_missing: [], claim: "Screen estimate", replay_count: 1, byte_identical: true,
  }],
  recent_cases: [CASE_A],
  screen_errors: [], declared_missing: [], registry_error: null,
});

const casesPayload = () => ({
  store: "runs/system",
  counts: { solved: 1, staged: 0, stage_failed: 0, solve_failed: 0, recorded: 0, empty: 0 },
  cases: [CASE_A, CASE_B],
  declared_missing: [],
  fidelity_note: "",
  registry_error: null,
});

const casePayload = () => ({
  row: CASE_A,
  run: null,
  geometry: {
    box_bbox_mm: [[-185.6, -185.6, 0], [185.6, 185.6, 1078.8]],
    horn_bbox_mm: [[-150, -150, 600], [150, 150, 900]],
    horn_front: [[-100, -100], [100, -100], [100, 100], [-100, 100]],
    horn_side: [[0, 0], [100, 0], [100, 200], [0, 200]],
    horn_missing: null,
  },
  placeholders: [],
  highlights: {},
});

const readinessPayload = () => ({
  registry: "docs/research/system_woofer_2026-11-18/cases.d/readiness.yaml",
  updated: "2026-01-01T00:00:00Z",
  risks: [
    { id: "R1", level: "HIGH", status: "open", title: "No channel calibration policy", wp: "WP9", blocked_by: "decision 3", evidence: "none yet" },
    { id: "R2", level: "LOW", status: "closed", title: "Registry schema", wp: "WP7", blocked_by: "-", evidence: "readiness.yaml" },
  ],
  decisions: [
    { id: 3, question: "Calibration policy?", recommendation: "Define one.", status: "open" },
    { id: 6, question: "Owner approval to solve?", recommendation: "Record approval.", status: "open" },
  ],
  counts: { solved: 1, staged: 0, stage_failed: 0, solve_failed: 0, recorded: 0, empty: 0 },
});

const screensPayload = () => ({
  store: "runs/system",
  studies: [{
    study_id: STUDY_ID,
    mtime_utc: "2026-01-01T00:00:00Z",
    dir: "runs/system/screen",
    schema: "system_screen_v1",
    horn: { brief_id: "demo-horn", design_hash: "abcdef1234567890", quality: "MAGNITUDE_ONLY" },
    drivers: [{ driver_id: "woofer_a", driver_name: "Woofer A" }],
    driver_count: 1,
    replay_count: 1,
    byte_identical: true,
    counts: { shortlist_rows: 3, bl_panel_fit_rejected: 0 },
    counts_missing: [],
    claim: "Screen estimate; no winner.",
  }],
  errors: [],
});

const screenDetailPayload = () => ({
  study_id: STUDY_ID,
  dir: "runs/system/screen",
  schema: "system_screen_v1",
  asset: { brief_id: "demo-horn", design_hash: "abcdef1234567890" },
  counts: {
    drivers_loaded: 1, boxes_considered: 10, candidates_kept: 5,
    pareto_front_rows: 2, shortlist_rows: 0, bl_panel_fit_rejected: 0,
  },
  counts_missing: [],
  numeric_axes: ["match_error_h_db2", "match_error_v_db2"],
  axis_directions: { match_error_h_db2: "lower", match_error_v_db2: "lower" },
  metric_spec: {
    bl_panel_fit: {
      applied: true, driver_moving_diameter_m: 0.2,
      clearance_m: 0.01, port_roundover_m: 0.01,
    },
  },
  catalog: [{ driver_id: "woofer_a" }],
  kept_rows: [],
  shortlist: [],
  claim: "Screen estimate; no winner.",
});

const assetsPayload = () => ({
  assets: [{
    asset_id: "asset_a", name: "Horn A", brief_id: "demo-horn",
    design_hash: "abcdef1234567890", quality: "MAGNITUDE_ONLY",
    full_domain_mesh: true,
  }],
});

const driversPayload = () => ({
  drivers: [{
    driver_id: "woofer_a", name: "Woofer A", size_in: 12,
    fs_hz: 35, vas_l: 100, qts: 0.38, sd_cm2: 530, xmax_mm: 8,
    ts_verified: true, ts_verified_note: "vendor URL recorded",
    geometry: { complete: true, missing_fields: [], note: "" },
    provenance: { field_sources: { fs_hz: "vendor", vas_l: "vendor" }, ts_file: "woofer_a.yaml" },
  }],
});

const specDefaultsPayload = () => ({
  source: "examples/systems/system_default.yaml",
  spec: {
    experiment_id: "demo_system",
    fidelity: "SCREEN_MAGNITUDE",
    cabinet: {
      external_width_mm_range: [300, 450],
      external_height_mm_range: [300, 450],
      external_depth_mm_range: [800, 1200],
      net_volume_l_range: [40, 90],
      tuning_hz_range: [30, 45],
      port_throat_area_cm2_range: [100, 250],
      port_nfr_range: [5, 10],
      wall_mm: 18,
      port_type: "round_flared",
    },
    target: {
      beamwidth_h_deg: [60, 90], beamwidth_v_deg: [40, 60],
      listening_angle_h_deg: [0, 30], listening_angle_v_deg: [0, 20],
      low_freq_f3_hz_max: 45,
    },
    assembly: {
      woofer_center_y_mm_range: [100, 260],
      woofer_center_x_mm_range: [-50, 50],
      horn_mounting_offset_z_mm_range: [0, 30],
      horn_layout: "separate_above",
    },
    dsp: {
      crossover_types: ["LR4", "LR2"],
      xo_hz_range: [800, 2000],
      peq_max_bands: 2,
    },
    horn: { asset_id: "asset_a" },
    woofer: { driver_id: "woofer_a" },
  },
});

const specsPayload = () => ({
  specs: [{
    name: "demo_spec", path: "examples/systems/user/demo_spec.yaml",
    ok: true, experiment_id: "demo_system",
  }],
  notes: [],
});

const comparePayload = () => ({
  ok: true,
  a: KEY_A,
  b: KEY_B,
  caption: "Per probe and per excitation; never summed.",
  band_note: "Bands are the API's own.",
  what_differs: {
    a: { motor: { role: "real", mapping_present: true, driver_id: "woofer_a" }, box: { width_mm: 371.2 } },
    b: { motor: { role: "demo", mapping_present: true, driver_id: "woofer_a" }, box: { width_mm: 371.2 } },
    differs: ["motor.role"],
  },
  probes: [{
    probe_id: "on_axis", domain: "probe:on_axis", kind: "point_probe",
    distance_m: 1, n_points: 1,
    excitations: [{
      id: "woofer", b_id: "woofer-b", per_input: "V_rms",
      ratio_db: [0.1, -0.2, 0.3],
      delta_phase_deg: [1, -2, 3],
      max_abs_ratio_db: 0.3, max_abs_ratio_at_hz: 400,
      max_abs_delta_phase_deg: 3, max_relative_delta_percent: 0.4,
      max_relative_delta_at_hz: 400,
      bands: [{ band: "full", n_freqs: 3, max_abs_ratio_db: 0.3, max_abs_ratio_at_hz: 400, max_abs_delta_phase_deg: 3, max_relative_delta_percent: 0.4, max_relative_delta_at_hz: 400 }],
    }],
  }],
});

const matrixPayload = () => {
  const keys = [KEY_A, KEY_B, KEY_B, KEY_A];
  return {
    cells: keys.map((key, i) => ({
      key, state: "solved", ref: i % 2 ? "demo" : "real", motor: i % 2 ? "demo" : "real",
      box: { width_mm: 371.2, height_mm: 371.2, depth_mm: 1078.8 },
      horn_offset_mm: [0, 0, 12.5],
    })),
    edges: [
      { from: KEY_A, to: KEY_B, ok: true, mismatches: [] },
      { from: KEY_B, to: KEY_B, ok: true, mismatches: [] },
      { from: KEY_B, to: KEY_A, ok: true, mismatches: [] },
      { from: KEY_A, to: KEY_A, ok: true, mismatches: [] },
    ],
  };
};

const combinedTouched = [];
let dspServed = null;
const dspPayload = () => {
  const payload = {
    ok: true,
    probe_id: "on_axis",
    distance_m: 1,
    point_index: 0,
    frequencies_hz: [100, 200, 400],
    channels: [
      {
        channel: "woofer", per_input: "V_rms", reference: "2.83 V",
        spl_db: [80, 82, 84], phase_deg: [0, -10, -20], phase_unwrapped_deg: [0, -10, -20],
      },
      {
        channel: "horn", per_input: "normal_velocity_mps", reference: "1 m/s",
        spl_db: [90, 91, 92], phase_deg: [5, 0, -5], phase_unwrapped_deg: [5, 0, -5],
      },
    ],
    dsp: {
      source: "examples/systems/system_default.yaml",
      point: {
        crossover_type: "LR4", xo_hz: 1200,
        gain_db_woofer: 0, gain_db_horn: 0, relative_delay_ms: 0,
        polarity_woofer: 1, peq_bands_woofer: [],
      },
      ranges: {
        xo_hz_range: [800, 2000], gain_db_range: [-6, 6],
        relative_delay_ms_range: [-5, 5], peq_max_bands: 2,
        crossover_types: ["LR4", "LR2"],
      },
    },
    verdicts: [{ check: "channels_present", ok: true, detail: "two channels, separate arrays" }],
    locked: { decision: 3, risk: "R1", reason: "Calibration policy is open.", panel: "System sum" },
    captions: ["Per-channel only; nothing is summed."],
  };
  // Any code that reaches for a summed/combined field is a contract violation, not a warning.
  for (const key of ["system_sum_db", "summed_spl_db", "combined_db", "system_response_db"]) {
    Object.defineProperty(payload, key, {
      enumerable: false,
      get() { combinedTouched.push(key); return []; },
    });
  }
  return payload;
};

async function fakeFetch(input, init = {}) {
  const raw = typeof input === "string" ? input : (input && input.url) || String(input);
  const method = String(init.method || (input && input.method) || "GET").toUpperCase();
  const url = new URL(raw, "http://localhost");
  const path = url.pathname;
  fetchLog.push({ path, search: url.search, method });

  const json = (payload, status = 200) => ({
    ok: status >= 200 && status < 300,
    status,
    headers: { get() { return null; } },
    json: async () => payload,
    text: async () => JSON.stringify(payload),
  });

  if (method === "POST" && path === "/api/hw/dsp-preview") {
    dspServed = dspPayload();
    return json(dspServed);
  }
  if (path === "/api/hw/overview") return json(overviewPayload());
  if (path === "/api/hw/cases") return json(casesPayload());
  if (path === "/api/hw/readiness") return json(readinessPayload());
  if (path === "/api/hw/screens") return json(screensPayload());
  if (path.startsWith("/api/hw/screen/")) return json(screenDetailPayload());
  if (path.startsWith("/api/hw/case/")) return json(casePayload());
  if (path === "/api/hw/assets") return json(assetsPayload());
  if (path === "/api/hw/drivers") return json(driversPayload());
  if (path === "/api/hw/spec-defaults") return json(specDefaultsPayload());
  if (path === "/api/hw/specs") return json(specsPayload());
  if (path === "/api/jobs") return json([]);
  if (path.startsWith("/api/job/")) return json({ id: "job", status: "done", log_tail: [] });
  if (path === "/api/hw/compare-matrix") return json(matrixPayload());
  if (path === "/api/hw/compare") return json(comparePayload());
  if (path.startsWith("/api/hw/basis/")) return json({ frequencies_hz: [100, 200, 400] });
  if (path.startsWith("/api/hw/mesh/")) return json({ error: "no mesh in the lifecycle test" }, 404);
  if (path === "/api/preview") return json({ command: "hw-screen --spec demo" });
  return json({ error: "unexpected fetch path " + path }, 404);
}

globalThis.fetch = fakeFetch;

// ── the real module graph ──────────────────────────────────────────────────────────────────
const moduleUrl = relative => pathToFileURL(
  fileURLToPath(new URL(relative, import.meta.url)),
).href;

const hw = await import(moduleUrl("../hornlab_search/gui/static/hw.js"));
const hwScreen = await import(moduleUrl("../hornlab_search/gui/static/hw_screen.js"));
const hwNew = await import(moduleUrl("../hornlab_search/gui/static/hw_new.js"));
const hwCompare = await import(moduleUrl("../hornlab_search/gui/static/hw_compare.js"));
const hwDsp = await import(moduleUrl("../hornlab_search/gui/static/hw_dsp.js"));
const hw3d = await import(moduleUrl("../hornlab_search/gui/static/hw3d.js"));

const EXPORTS = {
  "hw.js": [hw, ["viewHwOverview", "viewHwCases", "viewHwCase", "viewHwReadiness"]],
  "hw_screen.js": [hwScreen, ["viewHwScreens", "viewHwScreen"]],
  "hw_new.js": [hwNew, ["viewHwNew", "viewHwLaunch"]],
  "hw_compare.js": [hwCompare, ["viewHwCompare"]],
  "hw_dsp.js": [hwDsp, ["viewHwDsp"]],
  "hw3d.js": [hw3d, ["mountHw3D"]],
};
for (const [file, [mod, names]] of Object.entries(EXPORTS)) {
  for (const name of names) {
    assert.equal(typeof mod[name], "function", `${file} must export ${name}()`);
  }
}

const tick = async (n = 8) => {
  for (let i = 0; i < n; i++) await new Promise(resolve => setImmediate(resolve));
};

function makeRoot() {
  const root = documentStub.createElement("div");
  root.setAttribute("id", "view-root");
  documentStub.body.appendChild(root);
  return root;
}

function disposeRoot(root) {
  // The app router sweeps attached [data-v3d] hosts before replacing the view; do the same so a
  // leak in the 3D page would show up in the listener/timer counts below.
  documentStub.querySelectorAll("[data-v3d]").forEach(host => {
    if (typeof host._dispose3d === "function") host._dispose3d();
  });
  root.remove();
}

async function mountView(hash, fn) {
  globalThis.location.hash = hash;
  const root = makeRoot();
  let error = null;
  try {
    await fn(root);
    await tick(16);
  } catch (e) {
    error = e;
  }
  return { root, error };
}

function assertPainted(root, label) {
  assert.ok(typeof root.innerHTML === "string" && root.innerHTML.length > 0,
    `${label} painted a non-empty innerHTML`);
}

const caseHash = key => "#/hw/case/" + String(key).split("/").map(encodeURIComponent).join("/");

// ── 1. every view mounts, does not throw, and paints ───────────────────────────────────────
{
  const mounts = [
    ["hw overview", "#/hw", root => hw.viewHwOverview(root), "Design a two-way"],
    ["hw cases", "#/hw/cases", root => hw.viewHwCases(root), "Boundary Lab cases"],
    ["hw case", caseHash(KEY_A), root => hw.viewHwCase(root, KEY_A), "Story step 7"],
    ["hw readiness", "#/hw/readiness", root => hw.viewHwReadiness(root), "Readiness"],
    ["hw screens", "#/hw/screens", root => hwScreen.viewHwScreens(root), "Screens"],
    ["hw screen", "#/hw/screen/" + STUDY_ID, root => hwScreen.viewHwScreen(root, STUDY_ID), "Shortlist for"],
    ["hw new", "#/hw/new", root => hwNew.viewHwNew(root), "New system"],
    ["hw launch", "#/hw/launch", root => hwNew.viewHwLaunch(root), "Quick launch"],
    ["hw compare", "#/hw/compare", root => hwCompare.viewHwCompare(root, "a=" + encodeURIComponent(KEY_A) + "&b=" + encodeURIComponent(KEY_B)), "Compare"],
    ["hw compare matrix", "#/hw/compare?matrix=motor,box", root => hwCompare.viewHwCompare(root, "matrix=motor,box"), "2×2 matrix"],
    ["hw dsp", "#/hw/case/" + KEY_A + "/crossover", root => hwDsp.viewHwDsp(root, KEY_A.split("/")[0], KEY_A.split("/")[1]), "Crossover preview"],
  ];

  for (const [label, hash, fn, marker] of mounts) {
    const { root, error } = await mountView(hash, fn);
    assert.equal(error, null, `${label} must not throw${error ? ": " + error.stack : ""}`);
    assertPainted(root, label);
    assert.ok(root.innerHTML.includes(marker),
      `${label} paints its real content (missing ${JSON.stringify(marker)})`);
    disposeRoot(root);
    await tick(2);
    assert.equal(pendingTimers.size, 0, `${label} leaves no pending timer`);
    assert.equal(rafPending, 0, `${label} leaves no pending animation frame`);
  }
  // Prove every contract endpoint the task names was actually exercised, not just stubbed.
  const paths = fetchLog.map(entry => entry.path);
  const endpoints = [
    ["overview", p => p === "/api/hw/overview"],
    ["cases", p => p === "/api/hw/cases"],
    ["case", p => p.startsWith("/api/hw/case/")],
    ["readiness", p => p === "/api/hw/readiness"],
    ["screens", p => p === "/api/hw/screens"],
    ["screen", p => p.startsWith("/api/hw/screen/")],
    ["assets", p => p === "/api/hw/assets"],
    ["drivers", p => p === "/api/hw/drivers"],
    ["spec-defaults", p => p === "/api/hw/spec-defaults"],
    ["specs", p => p === "/api/hw/specs"],
    ["compare", p => p === "/api/hw/compare"],
    ["compare-matrix", p => p === "/api/hw/compare-matrix"],
    ["dsp-preview", p => p === "/api/hw/dsp-preview"],
  ];
  for (const [name, predicate] of endpoints) {
    assert.ok(paths.some(predicate), `the harness exercised /api/hw/${name}`);
  }
  assert.equal(liveListenerCount(), 0, "no listeners survive view disposal");
  assert.equal(liveObserverCount(), 0, "no observers survive view disposal");
}

// ── 2. the 3D tab installs _dispose3d and the router sweep calls it once ───────────────────
{
  // Node has no package "three" (the GUI loads it from an import map in the browser). The real
  // mountHw3D catches that and takes its documented 2-D fallback; the warning is expected noise.
  const realWarn = console.warn;
  console.warn = (...args) => {
    if (args.map(String).join(" ").includes("three.js failed to load")) return;
    realWarn(...args);
  };
  const { root, error } = await mountView(caseHash(KEY_A) + "?tab=geometry3d",
    r => hw.viewHwCase(r, KEY_A));
  console.warn = realWarn;
  assert.equal(error, null, `geometry3d mount must not throw${error ? ": " + error.stack : ""}`);
  assert.ok(root.innerHTML.includes("Geometry 3D"), "the geometry3d tab paints its panel");
  const hosts = root.querySelectorAll("[data-v3d]");
  assert.equal(hosts.length, 1, "the geometry3d tab has exactly one [data-v3d] host");
  const host = hosts[0];
  assert.equal(typeof host._dispose3d, "function", "mountHw3D installs _dispose3d on the host");
  assert.equal(typeof host._hw3dInfo, "function", "mountHw3D installs the resource probe");
  // Node has no WebGL, so the real mountHw3D takes its 2-D fallback path. Instrument the
  // installed hook and run the router's own sweep semantics (one call per attached host).
  let sweepCalls = 0;
  const installed = host._dispose3d;
  host._dispose3d = () => { sweepCalls += 1; installed(); };
  documentStub.querySelectorAll("[data-v3d]").forEach(el => {
    if (typeof el._dispose3d === "function") el._dispose3d();
  });
  assert.equal(sweepCalls, 1, "the router sweep disposes the 3D host exactly once");
  const info = host._hw3dInfo();
  assert.equal(info.triangles, 0, "no render loop survives the fallback dispose");
  assert.equal(info.geometries, 0);
  assert.equal(info.textures, 0);
  assert.equal(rafPending, 0, "the 3D mount leaves no animation frame pending");
  assert.equal(pendingTimers.size, 0, "the 3D mount leaves no timer pending");
  disposeRoot(root);
  await tick(2);
  assert.equal(liveListenerCount(), 0, "3D disposal leaves no attached listeners");
  assert.equal(liveObserverCount(), 0, "3D disposal leaves no attached observers");
}

// ── 3. repeat mount -> dispose 10 times; listeners/observers/timers must not grow ──────────
{
  const baseListeners = liveListenerCount();
  const baseObservers = liveObserverCount();
  const cycles = [
    ["overview", "#/hw", root => hw.viewHwOverview(root)],
    ["cases", "#/hw/cases", root => hw.viewHwCases(root)],
    ["case", caseHash(KEY_A), root => hw.viewHwCase(root, KEY_A)],
    ["readiness", "#/hw/readiness", root => hw.viewHwReadiness(root)],
    ["screens", "#/hw/screens", root => hwScreen.viewHwScreens(root)],
    ["screen", "#/hw/screen/" + STUDY_ID, root => hwScreen.viewHwScreen(root, STUDY_ID)],
    ["new", "#/hw/new", root => hwNew.viewHwNew(root)],
    ["launch", "#/hw/launch", root => hwNew.viewHwLaunch(root)],
    ["compare", "#/hw/compare", root => hwCompare.viewHwCompare(root, "a=" + encodeURIComponent(KEY_A) + "&b=" + encodeURIComponent(KEY_B))],
    ["dsp", "#/hw/case/" + KEY_A + "/crossover", root => hwDsp.viewHwDsp(root, KEY_A.split("/")[0], KEY_A.split("/")[1])],
  ];

  for (let i = 0; i < 10; i++) {
    const [label, hash, fn] = cycles[i % cycles.length];
    globalThis.location.hash = hash;
    const root = makeRoot();
    await fn(root);
    await tick(16);
    disposeRoot(root);
    await tick(3);
    assert.equal(pendingTimers.size, 0, `cycle ${i + 1} (${label}) leaves no timer`);
    assert.equal(rafPending, 0, `cycle ${i + 1} (${label}) leaves no animation frame`);
    assert.equal(liveListenerCount(), baseListeners,
      `cycle ${i + 1} (${label}) adds no attached listener`);
    assert.equal(liveObserverCount(), baseObservers,
      `cycle ${i + 1} (${label}) adds no attached observer`);
  }
}

// ── 4. the DSP page is fed per-channel arrays; no summed/combined path is touched ──────────
{
  const { root, error } = await mountView("#/hw/case/" + KEY_A + "/crossover",
    r => hwDsp.viewHwDsp(r, KEY_A.split("/")[0], KEY_A.split("/")[1]));
  assert.equal(error, null, `dsp mount must not throw${error ? ": " + error.stack : ""}`);
  assert.equal(combinedTouched.length, 0,
    "no summed/combined field is read: " + combinedTouched.join(", "));
  assert.ok(dspServed, "the dsp-preview endpoint was served");
  assert.equal(dspServed.channels.length, 2, "the DSP payload carries two separate channels");
  assert.ok(dspServed.channels.every(c =>
    Array.isArray(c.spl_db) && Array.isArray(c.phase_deg) && Array.isArray(c.phase_unwrapped_deg)),
    "each channel carries its own per-channel arrays");
  assert.notEqual(dspServed.channels[0].spl_db, dspServed.channels[1].spl_db,
    "the two channels are not aliases of one combined array");
  assert.ok(!("spl_db" in dspServed), "the payload has no root-level SPL array");
  const chartHosts = root.querySelectorAll("[data-dsp-chart]");
  assert.equal(chartHosts.length, 4, "two channels each get their own SPL and phase chart");
  const html = root.innerHTML;
  assert.ok(html.includes("Woofer") && html.includes("Horn"),
    "both channel names paint; neither is replaced by a system sum");
  assert.ok(/not summed|never summed|nothing is summed/i.test(html),
    "the page states the channels are not summed");
  assert.ok(!/data-dsp-chart="[^"]*system/i.test(html),
    "no chart host is a summed/combined system chart");
  disposeRoot(root);
  await tick(2);
  assert.equal(pendingTimers.size, 0, "dsp mount leaves no timer");
  assert.equal(rafPending, 0, "dsp mount leaves no animation frame");
}

console.log("hw GUI lifecycle ok");
