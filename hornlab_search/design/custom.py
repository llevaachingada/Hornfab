"""Geometry beyond what hornlab_mesher supports.

The mesher refuses per-azimuth throat stretch ("not supported yet") and has no
low-order azimuthal series over the flare parameters. That gap is the geometry
novelty opening for this project; see 12_RESEARCH_BASIS.md section 8.

A future family implemented here must produce a gmsh .msh in METRES with the
physical tags from hornlab_mesher.tags, so that solve/ needs no changes.
"""
from __future__ import annotations

from pathlib import Path

from ..types import Design, MeshSpec


def build_custom(design: Design, mesh: MeshSpec, res_mm: dict, out: Path):
    raise NotImplementedError("phase 2: see 11_PHASE2_SURROGATE.md forks")
