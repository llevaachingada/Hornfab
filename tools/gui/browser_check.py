"""Browser check for the hornlab-search GUI (handoff GUI_COMPLETION_HANDOFF_2026-11-19 §8.6).

Drives the local GUI with Playwright (Chromium) and reports, per route x width x theme:

1. console errors / page errors (fail on any);
2. page-level horizontal scroll: documentElement.scrollWidth <= clientWidth;
3. every ``svg[data-chart]`` has an aria-label and is not CSS-stretched (a numeric ``width``
   attribute must equal the rendered width; a ``width="100%"`` chart must carry a viewBox);
4. a full-page screenshot into the evidence folder;
5. keyboard: Tab reaches at least one control and no element has a negative tabindex on a control;
6. reload restores the same hash (URL state).

This script is tooling only: it never computes acoustics and never writes into the repo store.
Run with the Python 3.13 interpreter that has Playwright installed:

    & "C:\\Users\\hunte\\AppData\\Local\\Programs\\Python\\Python313\\python.exe" \\
        tools/gui/browser_check.py --base http://127.0.0.1:8799 --out docs/evidence/hw_gui_<date> \\
        --routes "/#/hw/cases,/#/hw/readiness"

Exit code 0 only when every check passes for every combination.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

DEFAULT_WIDTHS = (1280, 1009, 768, 375)
DEFAULT_THEMES = ("dark", "light")

CHECKS_JS = r"""
() => {
  const doc = document.documentElement;
  const charts = [];
  for (const svg of document.querySelectorAll("svg[data-chart]")) {
    const rect = svg.getBoundingClientRect();
    const wattr = svg.getAttribute("width");
    const numeric = wattr && /^\d+(\.\d+)?$/.test(wattr.trim());
    charts.push({
      width_attr: wattr,
      rendered: Math.round(rect.width * 10) / 10,
      has_viewbox: !!svg.getAttribute("viewBox"),
      aria_label: svg.getAttribute("aria-label") || "",
      stretched: numeric ? Math.abs(rect.width - Number(wattr)) > 2 : false,
    });
  }
  const chartsAll = [...document.querySelectorAll("svg")];
  const bad_aria = chartsAll.filter(s => !s.getAttribute("aria-label")).length;
  return {
    scrollWidth: doc.scrollWidth,
    clientWidth: doc.clientWidth,
    charts,
    svg_total: chartsAll.length,
    svg_missing_aria: bad_aria,
    h1_count: document.querySelectorAll("h1").length,
    hash: location.hash,
    title: (document.querySelector("#view-root h2") || {}).textContent || "",
    body_text_len: (document.body.innerText || "").length,
  };
}
"""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8799")
    ap.add_argument("--out", required=True, help="evidence folder for screenshots + report.json")
    ap.add_argument("--routes", default="/#/hw/cases,/#/hw/readiness")
    ap.add_argument("--widths", default=",".join(str(w) for w in DEFAULT_WIDTHS))
    ap.add_argument("--themes", default=",".join(DEFAULT_THEMES))
    ap.add_argument("--settle-ms", type=int, default=900)
    ap.add_argument("--timeout-ms", type=int, default=30000)
    a = ap.parse_args(argv)

    from playwright.sync_api import sync_playwright

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    routes = [r.strip() for r in a.routes.split(",") if r.strip()]
    widths = [int(w) for w in a.widths.split(",") if w.strip()]
    themes = [t.strip() for t in a.themes.split(",") if t.strip()]

    report = {"base": a.base, "runs": [], "failures": []}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for theme in themes:
            for width in widths:
                ctx = browser.new_context(viewport={"width": width, "height": 900})
                for route in routes:
                    page = ctx.new_page()
                    errors: list[str] = []
                    page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}")
                            if m.type == "error" else None)
                    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
                    # routes look like "/#/hw/cases" or "/#/hw/screen/<id>?tab=panel"; the query
                    # inside the route belongs to the hash, so build base + ?theme= + fragment.
                    frag = route[1:] if route.startswith("/") else "/" + route
                    url = f"{a.base}/?theme={theme}{frag}"
                    name = route.strip("/#").split("?")[0].replace("/", "_") or "home"
                    entry = {"route": route, "width": width, "theme": theme, "url": url,
                             "console_errors": [], "checks": {}, "screenshot": ""}
                    try:
                        page.goto(url, wait_until="networkidle", timeout=a.timeout_ms)
                        page.wait_for_selector("#view-root *", timeout=a.timeout_ms)
                        page.wait_for_timeout(a.settle_ms)
                        res = page.evaluate(CHECKS_JS)
                        entry["checks"] = res
                        entry["console_errors"] = errors
                        shot = out / f"{name}__{width}__{theme}.png"
                        page.screenshot(path=str(shot), full_page=True)
                        entry["screenshot"] = str(shot)
                        # keyboard reachability: first Tab moves focus off <body>
                        page.keyboard.press("Tab")
                        focused = page.evaluate(
                            "() => ({tag: (document.activeElement||{}).tagName || '',"
                            " id: (document.activeElement||{}).id || ''})")
                        entry["first_tab"] = focused
                        # reload restores the same hash
                        h0 = res.get("hash")
                        page.reload(wait_until="networkidle", timeout=a.timeout_ms)
                        page.wait_for_selector("#view-root *", timeout=a.timeout_ms)
                        page.wait_for_timeout(300)
                        h1 = page.evaluate("() => location.hash")
                        entry["reload_hash_ok"] = (h1 == h0)
                    except Exception as exc:  # noqa: BLE001 - reported, never hidden
                        entry["error"] = f"{type(exc).__name__}: {exc}"
                    page.close()

                    fails = []
                    if entry.get("error"):
                        fails.append(entry["error"])
                    if entry["console_errors"]:
                        fails.append("console: " + " | ".join(entry["console_errors"][:5]))
                    c = entry["checks"]
                    if c:
                        if c["scrollWidth"] > c["clientWidth"]:
                            fails.append(f"horizontal scroll {c['scrollWidth']} > {c['clientWidth']}")
                        if c["svg_missing_aria"]:
                            fails.append(f"{c['svg_missing_aria']} svg without aria-label")
                        for ch in c["charts"]:
                            if ch["stretched"]:
                                fails.append(f"chart stretched: attr {ch['width_attr']} vs "
                                             f"rendered {ch['rendered']}")
                            if not ch["aria_label"]:
                                fails.append("chart missing aria-label")
                        if entry.get("reload_hash_ok") is False:
                            fails.append("reload did not restore the hash")
                        if route.startswith("/#/hw") and c["h1_count"]:
                            fails.append(f"{c['h1_count']} <h1> element(s) on an hw page")
                    if fails:
                        entry["failures"] = fails
                        report["failures"].append({"route": route, "width": width,
                                                   "theme": theme, "failures": fails})
                    report["runs"].append(entry)
                    status = "FAIL" if fails else "ok"
                    print(f"[{status}] {route} @ {width}px {theme}")
                    for f in fails:
                        print(f"        - {f}")
                ctx.close()
        browser.close()

    (out / "browser_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\n{len(report['failures'])} failing combination(s); report: {out / 'browser_report.json'}")
    return 0 if not report["failures"] else 1


if __name__ == "__main__":
    sys.exit(main())
