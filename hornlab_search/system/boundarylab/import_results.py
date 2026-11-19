"""BL result import contract (Stage 4 pre-work): detection + manifest reading + refusals.

BL's documented result artifacts: ``.blabsp`` speaker packages (ZIP64, per-excitation basis,
``exp(+i omega t)``, schema-versioned manifest) and exported text/balloon data. No real
solved artifact exists yet (Stage 4 solves are behind the owner/senior gate), so this module
implements exactly what can be verified TODAY: artifact-kind detection from signatures,
manifest-level reading of a ``.blabsp`` (documented manifest semantics only), and a hard
refusal to synthesize bases from anything not fully validated. The deep payload parser lands
when a real package exists to pin the byte format.
"""
from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from hornlab_search.system import contracts as C

__all__ = ["ResultArtifact", "detect_result_artifact", "read_blabsp_manifest",
           "read_headless_result"]


@dataclass(frozen=True)
class ResultArtifact:
    kind: str                      # "blabsp" | "blab_project" | "bl_headless_result" | "unknown"
    path: str
    manifest: Mapping[str, Any] | None
    notes: tuple[str, ...]


def detect_result_artifact(path: str | Path) -> ResultArtifact:
    p = Path(path)
    if p.is_dir():
        from hornlab_search.system.boundarylab.bl_results import is_bl_headless_result_dir
        if is_bl_headless_result_dir(p):
            return ResultArtifact(kind="bl_headless_result", path=str(p), manifest=None,
                                  notes=("BL headless result directory; read per-excitation "
                                         "complex bases with bl_results.read_bl_headless_result",))
    if not p.exists():
        raise FileNotFoundError(f"result artifact not found: {p}")
    if p.suffix == ".blabsp" and zipfile.is_zipfile(p):
        manifest = _zip_member_json(p, ["manifest.json", "manifest/metadata.json"])
        notes = ()
        if manifest is None:
            notes = ("blabsp zip detected but no manifest.json at a documented location; "
                     "payload parsing waits for a real artifact to pin the layout",)
        return ResultArtifact(kind="blabsp", path=str(p), manifest=manifest, notes=notes)
    if p.suffix == ".json":
        try:
            loaded = json.loads(p.read_text(encoding="utf-8"))
        except ValueError as exc:
            raise C.DataQualityError(f"unreadable json project {p}: {exc}") from None
        if isinstance(loaded, dict) and "generator_documents" in loaded:
            return ResultArtifact(kind="blab_project", path=str(p), manifest=loaded,
                                  notes=("project file (geometry/config), not solved results",))
    return ResultArtifact(kind="unknown", path=str(p), manifest=None,
                          notes=("unknown artifact kind; supported: .blabsp package, "
                                 ".blab.json project, or a BL headless result directory",))


def read_headless_result(path: str | Path):
    """Delegating read of a BL headless result directory (no payload parsing duplicated).

    The typed reader, schema pins and refusal tokens live in
    :mod:`hornlab_search.system.boundarylab.bl_results`; this is the import-boundary alias.
    """
    from hornlab_search.system.boundarylab.bl_results import read_bl_headless_result
    return read_bl_headless_result(path)


def read_blabsp_manifest(path: str | Path) -> dict[str, Any]:
    """Manifest-only read of a speaker package (documented semantics, no payload parsing)."""
    artifact = detect_result_artifact(path)
    if artifact.kind != "blabsp" or artifact.manifest is None:
        raise C.DataQualityError(
            f"{artifact.path} is not a readable .blabsp package; bases are never synthesized "
            "from partial provenance")
    out = dict(artifact.manifest)
    # documented fields are semantic (medium properties, frequency/excitation order, provenance,
    # payload semantics, checksums); record which sections are present rather than inventing keys
    out["_present_sections"] = sorted(out.keys())
    return out


def _zip_member_json(path: Path, names: list[str]) -> dict[str, Any] | None:
    with zipfile.ZipFile(path) as zf:
        members = set(zf.namelist())
        for name in names:
            for member in members:
                if member == name or member.endswith("/" + name):
                    return json.loads(zf.read(member).decode("utf-8"))
    return None
