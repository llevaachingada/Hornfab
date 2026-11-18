"""Read-only discovery of an installed Boundary Lab (BL).

This module answers one question: *where is Boundary Lab, and which public pieces does this
machine actually expose?*  It never imports ``blab`` into the HornLab environment, never
installs anything, never starts a solve and never writes anywhere.  Every probe is a bounded
directory walk plus (when a plausible Python is found) a read-only ``python -m pip show``.

The discovered reality wins over the upstream snapshot claims in the parent brief.  Capabilities
that cannot be verified are reported as ``BL_CAPABILITY_MISSING`` reasons instead of guessed.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

__all__ = [
    "BL_CAPABILITY_OK",
    "BL_CAPABILITY_MISSING",
    "BLCapabilityError",
    "BLRoot",
    "BLProbeResult",
    "probe_boundarylab",
]

#: Token exported for a verified Boundary Lab install.
BL_CAPABILITY_OK = "BL_CAPABILITY_OK"
#: Token exported when a required BL capability cannot be verified on this machine.
BL_CAPABILITY_MISSING = "BL_CAPABILITY_MISSING"

#: Files a source checkout must contain for this adapter to use its public generator API.
REQUIRED_CHECKOUT_FILES: tuple[str, ...] = (
    "pyproject.toml",
    "src/blab/headless.py",
    "src/blab/project_cli.py",
    "src/blab/generators/__init__.py",
    "src/blab/generators/base.py",
    "geometry_providers/vented_enclosure/provider.json",
    "geometry_providers/vented_enclosure/enclosure/parameters.py",
    "geometry_providers/vented_enclosure/enclosure/worker.py",
    "geometry_providers/vented_enclosure/enclosure/backend.py",
)

_VENV_PYTHON_RELATIVE: tuple[str, ...] = (
    ".venv/Scripts/python.exe",
    "venv/Scripts/python.exe",
    "env/Scripts/python.exe",
    ".venv/bin/python",
    "venv/bin/python",
)
_VENV_CLI_RELATIVE: tuple[str, ...] = (
    ".venv/Scripts/blab.exe",
    "venv/Scripts/blab.exe",
    "env/Scripts/blab.exe",
    ".venv/bin/blab",
    "venv/bin/blab",
)
#: Bounded extension beyond the parent brief's roots: conventional developer checkouts.
_DEV_ROOT_NAMES: tuple[str, ...] = ("Github", "source", "repos", "code", "dev", "projects")
_ROOT_NAME_RE = re.compile(r"(boundary|blab|^bl)", re.IGNORECASE)


class BLCapabilityError(RuntimeError):
    """A required Boundary Lab capability is not verifiably present on this machine."""

    token = BL_CAPABILITY_MISSING

    def __init__(self, reasons: Iterable[str]):
        self.reasons: tuple[str, ...] = tuple(str(r) for r in reasons) or (
            f"{BL_CAPABILITY_MISSING}: no reason recorded",
        )
        super().__init__(f"{BL_CAPABILITY_MISSING}: " + " | ".join(self.reasons))


@dataclass(frozen=True)
class BLRoot:
    """One discovered Boundary Lab root and the public pieces verified on disk."""

    path: str
    kind: str  # "checkout" | "installed"
    version: str | None
    git_head: str | None
    python_executable: str | None
    cli_entry: str | None
    provider_dir: str | None
    hashes: tuple[tuple[str, str], ...] = ()
    missing: tuple[str, ...] = ()
    detail: Mapping[str, Any] = field(default_factory=dict)

    @property
    def verified(self) -> bool:
        return not self.missing

    @property
    def status(self) -> str:
        return BL_CAPABILITY_OK if self.verified else BL_CAPABILITY_MISSING

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "kind": self.kind,
            "version": self.version,
            "git_head": self.git_head,
            "python_executable": self.python_executable,
            "cli_entry": self.cli_entry,
            "provider_dir": self.provider_dir,
            "verified": self.verified,
            "status": self.status,
            "missing": list(self.missing),
            "hashes": {name: digest for name, digest in self.hashes},
        }


@dataclass(frozen=True)
class BLProbeResult:
    """The frozen result of one read-only probe."""

    found: bool
    roots: tuple[BLRoot, ...]
    capability_missing: tuple[str, ...]

    @property
    def status(self) -> str:
        return BL_CAPABILITY_OK if self.found and not self.capability_missing else BL_CAPABILITY_MISSING

    @property
    def verified_root(self) -> BLRoot | None:
        for root in self.roots:
            if root.verified:
                return root
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "found": self.found,
            "status": self.status,
            "roots": [root.to_dict() for root in self.roots],
            "capability_missing": list(self.capability_missing),
        }

    def to_json(self, indent: int | None = None) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)


# --------------------------------------------------------------------------- read-only helpers

def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_git_head(root: Path) -> str | None:
    """Resolve HEAD by reading git files only (no ``git`` subprocess)."""
    git_dir = root / ".git"
    if not git_dir.is_dir():
        return None
    try:
        head = (git_dir / "HEAD").read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not head.startswith("ref:"):
        return head or None
    ref = head[4:].strip()
    try:
        ref_file = git_dir / ref
        if ref_file.is_file():
            return ref_file.read_text(encoding="utf-8").strip() or None
    except OSError:
        pass
    packed = git_dir / "packed-refs"
    if packed.is_file():
        try:
            for line in packed.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("^"):
                    continue
                parts = line.split(None, 1)
                if len(parts) == 2 and parts[1] == ref:
                    return parts[0]
        except OSError:
            pass
    return None


def _read_version(pyproject: Path) -> str | None:
    try:
        text = pyproject.read_text(encoding="utf-8")
    except OSError:
        return None
    match = re.search(r'(?m)^version\s*=\s*"([^"]+)"', text)
    return match.group(1) if match else None


def _first_existing(root: Path, relatives: Sequence[str]) -> Path | None:
    for relative in relatives:
        candidate = root / relative
        if candidate.is_file():
            return candidate
    return None


def _candidate_text(root: Path) -> str:
    return f"Boundary Lab checkout at {root}"


def _checkout_missing_reason(root: Path, relative: str) -> str:
    return (
        f"missing {relative} under {_candidate_text(root)}; install or upgrade Boundary Lab "
        f"(git clone https://github.com/JWSound/boundary-lab and `pip install -e .` in its "
        f"environment) or point BOUNDARY_LAB_HOME at a complete checkout"
    )


def _verify_checkout(root: Path) -> BLRoot:
    root = root.resolve()
    missing: list[str] = []
    hashes: list[tuple[str, str]] = []
    for relative in REQUIRED_CHECKOUT_FILES:
        path = root / relative
        if not path.is_file():
            missing.append(_checkout_missing_reason(root, relative))
        else:
            hashes.append((relative, _sha256_file(path)))

    python_executable = _first_existing(root, _VENV_PYTHON_RELATIVE)
    if python_executable is None:
        missing.append(
            f"no Boundary Lab Python executable found at {root}/.venv/Scripts/python.exe "
            f"(or venv/env equivalents); create the project's own environment and install "
            f"Boundary Lab into it"
        )
    cli_entry = _first_existing(root, _VENV_CLI_RELATIVE)
    if cli_entry is None:
        missing.append(
            f"no `blab` console entry found under {root}/.venv/Scripts/blab.exe; the installed "
            f"copy must expose pyproject [project.scripts] blab = \"blab.cli:main\""
        )

    provider_dir = root / "geometry_providers" / "vented_enclosure"
    manifest = provider_dir / "provider.json"
    detail: dict[str, Any] = {}
    if manifest.is_file():
        try:
            detail["provider_manifest"] = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            missing.append(
                f"provider manifest {manifest} is not readable JSON ({exc}); repair the "
                f"Boundary Lab checkout"
            )
        else:
            manifest_data = detail["provider_manifest"]
            if not isinstance(manifest_data.get("id"), str):
                missing.append(f"provider manifest {manifest} has no string `id`; cannot target it")
            backend = manifest_data.get("backend")
            if not isinstance(backend, str) or ":" not in backend:
                missing.append(
                    f"provider manifest {manifest} does not declare a `module:factory` backend; "
                    f"the public generator API cannot be targeted"
                )
            detail["backend"] = backend if isinstance(backend, str) else None

    return BLRoot(
        path=str(root),
        kind="checkout",
        version=_read_version(root / "pyproject.toml"),
        git_head=_read_git_head(root),
        python_executable=None if python_executable is None else str(python_executable),
        cli_entry=None if cli_entry is None else str(cli_entry),
        provider_dir=str(provider_dir),
        hashes=tuple(hashes),
        missing=tuple(missing),
        detail=detail,
    )


def _classify_checkout(path: Path) -> bool:
    if not path.is_dir():
        return False
    pyproject = path / "pyproject.toml"
    if pyproject.is_file():
        try:
            text = pyproject.read_text(encoding="utf-8")
        except OSError:
            text = ""
        if re.search(r'(?m)^name\s*=\s*"boundary-lab"', text):
            return True
    return (path / "src" / "blab" / "headless.py").is_file() or (
        path / "geometry_providers" / "vented_enclosure" / "provider.json"
    ).is_file()


# --------------------------------------------------------------------------- Python / pip probing

def _run_capture(argv: Sequence[str], timeout_s: float = 30.0) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            list(argv),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_s,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return 127, "", f"{type(exc).__name__}: {exc}"
    return proc.returncode, proc.stdout or "", proc.stderr or ""


def _pip_show(python: Path, package: str = "boundary-lab") -> dict[str, str] | None:
    code, out, _err = _run_capture([str(python), "-m", "pip", "show", package], timeout_s=25.0)
    if code != 0:
        return None
    info: dict[str, str] = {}
    for line in out.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            info[key.strip()] = value.strip()
    return info or None


def _python_candidates_from_root(root: Path) -> list[Path]:
    found: list[Path] = []
    for relative in _VENV_PYTHON_RELATIVE:
        candidate = root / relative
        if candidate.is_file():
            found.append(candidate)
    for cfg in (root / "pyvenv.cfg", root / ".venv" / "pyvenv.cfg"):
        if not cfg.is_file():
            continue
        try:
            for line in cfg.read_text(encoding="utf-8").splitlines():
                if line.strip().lower().startswith("home") and "=" in line:
                    home = line.split("=", 1)[1].strip()
                    candidate = Path(home) / "python.exe"
                    if candidate.is_file():
                        found.append(candidate)
                    candidate = Path(home) / "python"
                    if candidate.is_file():
                        found.append(candidate)
        except OSError:
            continue
    return found


def _base_python_candidates() -> list[Path]:
    found: list[Path] = []
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        found.extend(Path(p) for p in glob.glob(str(Path(local_appdata) / "Programs" / "Python" / "*" / "python.exe")))
    return found


def _verify_installed(site_packages: Path, python: Path, info: Mapping[str, str]) -> BLRoot:
    site_packages = site_packages.resolve()
    missing: list[str] = []
    hashes: list[tuple[str, str]] = []
    for relative in ("blab/headless.py", "blab/generators/__init__.py", "blab/generators/base.py"):
        path = site_packages / relative
        if not path.is_file():
            missing.append(
                f"installed boundary-lab package at {site_packages} lacks {relative}; upgrade "
                f"Boundary Lab (pip install -U boundary-lab) or use a source checkout"
            )
        else:
            hashes.append((relative, _sha256_file(path)))
    provider_dir = site_packages / "geometry_providers" / "vented_enclosure"
    if not (provider_dir / "provider.json").is_file():
        missing.append(
            f"installed boundary-lab package at {site_packages} does not ship "
            f"geometry_providers/vented_enclosure/provider.json; wheels exclude the plugin, so "
            f"use a source checkout (`pip install -e <checkout>`) to generate vented enclosures"
        )
    cli_entry = _first_existing(python.parent, ("blab.exe", "blab"))
    if cli_entry is None:
        missing.append(
            f"no `blab` console entry beside {python}; reinstall Boundary Lab so pyproject "
            f"[project.scripts] blab = \"blab.cli:main\" is installed"
        )
    return BLRoot(
        path=str(site_packages),
        kind="installed",
        version=info.get("Version"),
        git_head=None,
        python_executable=str(python),
        cli_entry=None if cli_entry is None else str(cli_entry),
        provider_dir=str(provider_dir) if provider_dir.is_dir() else None,
        hashes=tuple(hashes),
        missing=tuple(missing),
        detail={"package_location": str(site_packages)},
    )


# --------------------------------------------------------------------------- search policy

def _default_candidate_roots() -> list[Path]:
    home = Path.home()
    candidates: list[Path] = []

    env = os.environ.get("BOUNDARY_LAB_HOME", "").strip()
    if env:
        candidates.append(Path(env))

    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        programs = Path(local_appdata) / "Programs"
        if programs.is_dir():
            candidates.extend(p for p in programs.iterdir() if p.is_dir())

    if home.is_dir():
        try:
            for child in home.iterdir():
                if child.is_dir() and _ROOT_NAME_RE.search(child.name):
                    candidates.append(child)
        except OSError:
            pass
        hrns = home / "Hrns"
        if hrns.is_dir():
            try:
                candidates.extend(child for child in hrns.iterdir() if child.is_dir())
            except OSError:
                pass
        for dev_name in _DEV_ROOT_NAMES:
            dev_root = home / dev_name
            if not dev_root.is_dir():
                continue
            try:
                candidates.extend(
                    child
                    for child in dev_root.iterdir()
                    if child.is_dir() and _ROOT_NAME_RE.search(child.name)
                )
            except OSError:
                pass

    for program_files in (Path("C:/Program Files"), Path("C:/Program Files (x86)")):
        if not program_files.is_dir():
            continue
        try:
            for vendor in program_files.iterdir():
                if not vendor.is_dir():
                    continue
                try:
                    candidates.extend(
                        child
                        for child in vendor.iterdir()
                        if child.is_dir() and re.search(r"boundar", child.name, re.IGNORECASE)
                    )
                except OSError:
                    continue
        except OSError:
            pass

    return candidates


def _dedupe(paths: Iterable[Path]) -> list[Path]:
    seen: set[str] = set()
    result: list[Path] = []
    for path in paths:
        try:
            key = str(path.resolve()).lower()
        except OSError:
            key = str(path).lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(path)
    return result


def probe_boundarylab(
    *,
    extra_roots: Sequence[str | os.PathLike[str]] = (),
    use_default_roots: bool = True,
) -> BLProbeResult:
    """Locate Boundary Lab without writing, installing or solving anything.

    ``use_default_roots=False`` restricts the search to ``extra_roots`` (used by tests and by
    CI smoke runs with a fake tree, so a developer machine's real install cannot mask the fake).
    """
    candidates: list[Path] = [Path(p) for p in extra_roots]
    if use_default_roots:
        candidates.extend(_default_candidate_roots())

    roots: list[BLRoot] = []
    seen_roots: set[str] = set()

    if use_default_roots:
        where_code, where_out, _ = _run_capture(["where.exe", "blab"], timeout_s=10.0)
        if where_code == 0:
            for line in where_out.splitlines():
                line = line.strip()
                if not line:
                    continue
                cli = Path(line)
                candidates.append(cli.parent.parent)

    candidates = _dedupe(candidates)

    for candidate in candidates:
        if not _classify_checkout(candidate):
            continue
        root = _verify_checkout(candidate)
        key = root.path.lower()
        if key not in seen_roots:
            seen_roots.add(key)
            roots.append(root)

    if use_default_roots:
        pythons: list[Path] = []
        for candidate in candidates:
            pythons.extend(_python_candidates_from_root(candidate))
        pythons.extend(_base_python_candidates())
        for python in _dedupe(pythons):
            info = _pip_show(python)
            if info is None:
                continue
            editable = info.get("Editable project location")
            if editable and _classify_checkout(Path(editable)):
                root = _verify_checkout(Path(editable))
            elif info.get("Location"):
                root = _verify_installed(Path(info["Location"]), python, info)
            else:
                continue
            key = root.path.lower()
            if key not in seen_roots:
                seen_roots.add(key)
                roots.append(root)

    roots.sort(key=lambda root: (len(root.missing), root.kind != "checkout", root.path.lower()))

    if not roots:
        searched = ", ".join(str(path) for path in candidates[:12]) or "(no candidate roots)"
        return BLProbeResult(
            found=False,
            roots=(),
            capability_missing=(
                f"no Boundary Lab checkout or installed 'boundary-lab' package found; searched "
                f"{searched}. Install from https://github.com/JWSound/boundary-lab (GPLv3), "
                f"`pip install -e` its checkout, or set BOUNDARY_LAB_HOME to that checkout",
            ),
        )

    best = roots[0]
    return BLProbeResult(found=True, roots=tuple(roots), capability_missing=best.missing)
