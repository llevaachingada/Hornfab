"""Command-line entry point: ``doctor`` and ``version``.

Owned by task 03 until Wave 2 (task 08) adds run / search / verify / report /
selftest below.
"""
from __future__ import annotations

import importlib.util
import json
import re
import shutil
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, distribution
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
EXAMPLES = REPO / "examples"
TOOLCHAIN_MD = REPO / "TOOLCHAIN.md"

EXAMPLE_NAMES = ("osse_baseline", "throat_adapter", "icw_termination",
                 "freeform_hv", "search_smoke")

CORE_IMPORTS = ("numpy", "scipy", "cma", "yaml", "jinja2")
HORNLAB_IMPORTS = ("hornlab_mesher", "hornlab_beat_bem", "hornlab_plots")

# pyproject dependency git SHAs: package name -> 40-char commit.
_GIT_URL_RE = re.compile(r"hornlab-(?:waveguide-mesher|beat-bem|plots|bempp-bem)\s*@\s*git\+https://github\.com/m3gnus/([^/@]+)\.git@([0-9a-f]{40})")


def _have(module: str) -> bool:
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):
        return False


def _version() -> str:
    from hornlab_search import __version__
    return __version__


def _expected_shas() -> dict[str, str]:
    """{package name -> 40-char SHA} parsed from pyproject.toml dependencies."""
    text = (REPO / "pyproject.toml").read_text(encoding="utf-8")
    out: dict[str, str] = {}
    for line in text.splitlines():
        m = _GIT_URL_RE.search(line)
        if m:
            repo, sha = m.group(1), m.group(2)
            out[repo] = sha
    return out


def _installed_shas() -> dict[str, str]:
    """{package name -> installed commit SHA} from each dist's direct_url.json.

    Returns "" for a package whose commit cannot be determined (editable checkouts,
    non-git installs)."""
    out: dict[str, str] = {}
    for repo in ("hornlab-waveguide-mesher", "hornlab-beat-bem",
                 "hornlab-plots", "hornlab-bempp-bem"):
        name = repo.replace("hornlab-", "hornlab_")
        try:
            dist = distribution(name)
        except PackageNotFoundError:
            out[repo] = ""
            continue
        raw = dist.read_text("direct_url.json")
        sha = ""
        if raw:
            try:
                data = json.loads(raw)
                vcs = data.get("vcs_info") or {}
                sha = vcs.get("commit_id") or data.get("commit_id") or ""
            except (ValueError, TypeError):
                sha = ""
        out[repo] = sha
    return out


def _python_ok() -> tuple[bool, str]:
    v = sys.version_info
    if (3, 11) <= (v.major, v.minor) < (3, 14):
        return True, f"Python {v.major}.{v.minor}.{v.micro} in [3.11, 3.14)"
    return False, f"Python {v.major}.{v.minor}.{v.micro} outside [3.11, 3.14)"


def _backend_status():
    try:
        import hornlab_beat_bem as beat
        return beat.beat_backend_statuses()
    except Exception as exc:  # pragma: no cover - environment dependent
        return {"__error__": str(exc)}


def _configured_backend() -> tuple[str, str]:
    """(configured backend token, bare backend name) from osse_baseline.yaml."""
    from hornlab_search.config import load_config
    cfg = load_config(EXAMPLES / "osse_baseline.yaml")
    token = cfg.solve.backend            # e.g. "beat_cuda"
    bare = token.removeprefix("beat_") if token.startswith("beat_") else token
    return token, bare


class Doctor:
    """One check at a time; each returns (ok, reason)."""

    def __init__(self) -> None:
        self.results: list[tuple[str, bool, str]] = []

    def run(self, label: str, fn):
        ok = True
        reason = ""
        try:
            ok, reason = fn()
        except Exception as exc:  # noqa: BLE001 - a doctor must never crash
            ok, reason = False, f"unexpected error: {exc!r}"
        self.results.append((label, ok, reason))

    def check_python(self):
        self.run("python-version", _python_ok)

    def check_core_imports(self):
        missing = [m for m in CORE_IMPORTS if not _have(m)]
        if missing:
            self.run("core-imports", lambda: (False, f"missing: {', '.join(missing)}"))
        else:
            self.run("core-imports", lambda: (True, "numpy, scipy, cma, yaml, jinja2"))

    def check_hornlab_imports(self):
        missing = [m for m in HORNLAB_IMPORTS if not _have(m)]
        bempp = "yes" if _have("hornlab_bempp_bem") else "no (optional)"
        if missing:
            self.run("hornlab-imports", lambda: (False, f"missing: {', '.join(missing)}; bempp {bempp}"))
        else:
            self.run("hornlab-imports", lambda: (True, f"mesher, beat, plots; bempp {bempp}"))

    def check_shas(self):
        expected = _expected_shas()
        installed = _installed_shas()
        problems = []
        for repo, want in expected.items():
            got = installed.get(repo, "")
            if not got:
                problems.append(f"{repo}: installed SHA UNKNOWN (expected {want[:12]})")
            elif got != want:
                problems.append(f"{repo}: installed {got[:12]} != expected {want[:12]}")
        if problems:
            # Mismatch is a WARNING, not a failure (03 step 7).
            self.results.append(("pinned-shas", True, "WARNING: " + "; ".join(problems)))
        else:
            self.results.append(("pinned-shas", True, "all installed SHAs match pyproject.toml"))

    def check_toolchain(self):
        def fn():
            if not TOOLCHAIN_MD.exists():
                return False, "TOOLCHAIN.md missing"
            text = TOOLCHAIN_MD.read_text(encoding="utf-8")
            m = re.search(r"dof_per_triangle\s*[:=]\s*([0-9.]+)", text)
            if not m:
                return False, "TOOLCHAIN.md has no dof_per_triangle value"
            if float(m.group(1)) == 0.5:
                return False, "dof_per_triangle is still the 0.5 placeholder"
            return True, f"TOOLCHAIN.md present, dof_per_triangle={m.group(1)}"
        self.run("toolchain", fn)

    def check_gpu(self):
        def fn():
            nv = shutil.which("nvidia-smi")
            if not nv:
                return False, "nvidia-smi not on PATH"
            r = subprocess.run([nv], capture_output=True, timeout=30)
            if r.returncode == 0:
                return True, "nvidia-smi exits 0"
            return False, f"nvidia-smi exits {r.returncode}"
        self.run("gpu", fn)

    def check_backend(self):
        def fn():
            token, bare = _configured_backend()
            statuses = _backend_status()
            entry = statuses.get(bare)
            if not isinstance(entry, dict):
                return False, f"backend {bare!r} not in statuses: {list(statuses)}"
            if entry.get("available"):
                return True, f"{token} functional (state={entry.get('state')})"
            return False, f"{token} not functional: {entry.get('reason', entry)}"
        self.run("backend", fn)

    def check_configs(self):
        def fn():
            from hornlab_search.config import load_config
            bad = []
            for name in EXAMPLE_NAMES:
                try:
                    load_config(EXAMPLES / f"{name}.yaml")
                except Exception as exc:  # noqa: BLE001
                    bad.append(f"{name}: {exc}")
            if bad:
                return False, "; ".join(bad)
            return True, f"all {len(EXAMPLE_NAMES)} example configs load"
        self.run("configs", fn)

    def check_roundtrip(self):
        # Reserved: filled by task 04 (mesh round-trip). Always passes in Wave 0.
        self.results.append(("round-trip", True, "reserved for task 04"))


def _cmd_doctor() -> int:
    d = Doctor()
    d.check_python()
    d.check_core_imports()
    d.check_hornlab_imports()
    d.check_shas()
    d.check_toolchain()
    d.check_gpu()
    d.check_backend()
    d.check_configs()
    d.check_roundtrip()
    any_fail = False
    for label, ok, reason in d.results:
        mark = "PASS" if ok else "FAIL"
        if not ok:
            any_fail = True
        print(f"{mark:4}  {label:16}  {reason}")
    return 1 if any_fail else 0


def _cmd_version() -> int:
    print(_version())
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print("usage: hornlab-search <doctor|version>", file=sys.stderr)
        return 2
    cmd = args[0]
    if cmd == "doctor":
        return _cmd_doctor()
    if cmd == "version":
        return _cmd_version()
    print(f"unknown command {cmd!r}", file=sys.stderr)
    return 2


# --- Wave 2 adds run / search / verify / report / selftest below (task 08) ---


if __name__ == "__main__":
    raise SystemExit(main())
