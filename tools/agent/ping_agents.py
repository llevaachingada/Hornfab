"""Agent ping — prove skill discovery, skill grants and skill loading actually work.

Static checks are free and always run. ``--live`` adds real model calls (they cost
tokens and need a working provider).

Usage (from the repository root)::

    .venv\\Scripts\\python.exe tools/agent/ping_agents.py
    .venv\\Scripts\\python.exe tools/agent/ping_agents.py --live
    .venv\\Scripts\\python.exe tools/agent/ping_agents.py --live --model ollama-cloud/deepseek-v4.1-flash:1017

Exit codes: 0 all checks passed, 1 at least one check failed.

This is a diagnostic, not a test-suite gate: the live half needs a funded model
provider and is not run in CI.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CONTAINER = REPO.parent

HORNLAB_SKILLS = [
    "hornlab-acoustic-grounding",
    "hornlab-evidence",
    "hornlab-gpu-job",
    "hornlab-night-queue",
    "hornlab-render",
    "hornlab-search-economy",
    "hornlab-shape-check",
    "hornlab-typology-research",
]

RBASSIST_SKILLS = [
    "rbassist-cloud-desktop-clickthrough",
    "rbassist-desktop-snapshot",
    "rbassist-native-qt-design-contract",
    "rbassist-pyside-design-system-refactor",
    "rbassist-pyside-gui-fixer",
    "rbassist-real-pyside-validation",
]

ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def opencode_cmd() -> list[str]:
    exe = shutil.which("opencode.exe")
    if exe:
        return [exe]
    npm = Path(os.environ.get("APPDATA", "")) / "npm" / "node_modules" / "opencode-ai" / "bin" / "opencode.exe"
    if npm.exists():
        return [str(npm)]
    shim = shutil.which("opencode")
    if shim:
        return [shim]
    raise SystemExit("opencode executable not found (set PATH or install opencode)")


def run(cmd: list[str], cwd: Path, timeout: int) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


def clean(text: str) -> str:
    return ANSI.sub("", text or "")


def parse_first_json(text: str):
    start = text.find("{")
    if start < 0:
        raise ValueError("no JSON object in output")
    return json.loads(text[start:])


def parse_skills(text: str) -> list[str]:
    start = text.find("[")
    if start < 0:
        return []
    return sorted(s["name"] for s in json.loads(text[start:]))


RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" - {detail}" if detail else ""))


def static_checks() -> None:
    bin_cmd = opencode_cmd()

    for label, cwd in (("canonical", REPO), ("container", CONTAINER)):
        proc = run(bin_cmd + ["debug", "skill"], cwd, timeout=180)
        text = clean(proc.stdout + proc.stderr)
        try:
            names = parse_skills(text)
        except Exception as exc:  # noqa: BLE001 - report, do not crash the ping
            check(f"{label}: skill list parses", False, str(exc))
            continue
        missing = [s for s in HORNLAB_SKILLS if s not in names]
        check(
            f"{label}: all 8 hornlab skills discoverable",
            not missing,
            f"{len(names)} skills" if not missing else f"missing {missing}",
        )

    proc = run(bin_cmd + ["debug", "config"], cwd=REPO, timeout=180)
    check("canonical: config parses", proc.returncode == 0, f"exit {proc.returncode}")

    for label, cwd in (("canonical", REPO), ("container", CONTAINER)):
        proc = run(bin_cmd + ["debug", "agent", "orchestrator"], cwd, timeout=180)
        text = clean(proc.stdout + proc.stderr)
        try:
            agent = parse_first_json(text)
        except Exception as exc:  # noqa: BLE001
            check(f"{label}: orchestrator config parses", False, str(exc))
            continue
        perms = agent.get("permission", [])
        allowed = [
            p["pattern"]
            for p in perms
            if p.get("permission") == "skill"
            and p.get("action") == "allow"
            and p.get("pattern") in RBASSIST_SKILLS
        ]
        check(
            f"{label}: no rbassist skill granted to orchestrator",
            not allowed,
            "none granted" if not allowed else f"granted {allowed}",
        )

    print()
    print("Static checks done. Live checks: --live (costs tokens).")


def run_prompt(bin_cmd: list[str], cwd: Path, prompt: str, model: str | None, timeout: int) -> str:
    cmd = list(bin_cmd)
    if model:
        cmd += ["-m", model]
    cmd += ["run", "--dir", str(cwd), prompt]
    proc = run(cmd, cwd, timeout=timeout)
    return clean(proc.stdout + proc.stderr)


def live_checks(model: str | None) -> None:
    bin_cmd = opencode_cmd()

    out = run_prompt(
        bin_cmd,
        REPO,
        "PING (read-only). Use the skill tool to load skill hornlab-gpu-job, then reply with exactly one line: "
        "PING-ORCHESTRATOR OK: <first 6 words of the body>. Do not call any other tool.",
        model,
        timeout=420,
    )
    check("live: orchestrator loads a hornlab skill", "PING-ORCHESTRATOR OK" in out, tail(out))

    out = run_prompt(
        bin_cmd,
        REPO,
        "PING (read-only). Delegate exactly once to @fixer with: 'Use the skill tool to load skill "
        "hornlab-gpu-job, then reply with one line: PING-FIXER OK: <first 6 words of the body>. Do not call any "
        "other tool.' Then report the child's reply verbatim. Do not perform the task yourself.",
        model,
        timeout=600,
    )
    check("live: delegated fixer loads a hornlab skill", "PING-FIXER OK" in out, tail(out))

    out = run_prompt(
        bin_cmd,
        REPO,
        "PING (read-only, no tools). From your own instructions and available-skill list: do you require "
        "rbassist-real-pyside-validation for rbassist/desktop changes, and do any rbassist-* skills appear? "
        "Reply exactly: PING-ISOLATION: (<yes/no>); rbassist skills: (<none|names>).",
        model,
        timeout=420,
    )
    normalized = re.sub(r"[()]", "", out.lower())
    check(
        "live: no rbassist directive or skill in HornLab",
        "ping-isolation: no" in normalized and "rbassist skills: none" in normalized,
        tail(out),
    )


def tail(text: str, limit: int = 220) -> str:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    joined = " | ".join(lines[-2:])[:limit]
    return joined.encode("ascii", "replace").decode()


def main(argv: list[str] | None = None) -> int:
    try:
        reconfigure = getattr(sys.stdout, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001 - older or embedded stdout
        pass

    parser = argparse.ArgumentParser(description="Ping OpenCode agents for skill discovery and loading.")
    parser.add_argument("--live", action="store_true", help="also run model-backed skill-load pings (costs tokens)")
    parser.add_argument("--model", default=None, help="override the run model, e.g. ollama-cloud/deepseek-v4.1-flash:1017")
    args = parser.parse_args(argv)

    static_checks()
    if args.live:
        print()
        live_checks(args.model)

    failed = [name for name, ok, _ in RESULTS if not ok]
    print()
    print(f"{len(RESULTS) - len(failed)}/{len(RESULTS)} checks passed")
    if failed:
        print("failed: " + ", ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
