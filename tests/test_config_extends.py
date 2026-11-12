"""``extends:`` and profiles (swarm lane F, finished 2026-11-12).

A config/brief written with ``extends:`` must resolve BEFORE ``config_sha``/the solve hash and load
to the SAME ``Config`` as its flat copy. Goldens in ``tests/test_config*.py`` are unchanged (this
file only adds new coverage). Offline: YAML only, no solver, no GPU.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from conftest import EXAMPLES, REPO
from hornlab_search.config import ConfigError, load_brief, load_config, solve_spec
from hornlab_search.search.rundir import config_sha

#: Three REAL campaign cells (the plan's "3 real cells"), each with a brief_file.
CELLS = (
    "examples/typologies/campaign_2026-10-26/b1t__rosse_morph.yaml",
    "examples/typologies/campaign_2026-10-26/b1t__lecleach_iwata_ar.yaml",
    "examples/typologies/campaign_2026-10-26/b1w__osse_baseline.yaml",
)


def _raw(rel: str) -> dict:
    return yaml.safe_load((REPO / rel).read_text(encoding="utf-8"))


def _absolutize_brief(raw: dict, rel: str) -> dict:
    """Make a cell's ``brief_file`` absolute against the CELL's directory: briefs are written
    relative to the config that names them (``../../briefs/...``), so resolving from the repo
    root would point outside the checkout."""
    brief = raw.get("brief_file")
    if brief and not Path(brief).is_absolute():
        raw["brief_file"] = str(((REPO / rel).parent / brief).resolve())
    return raw


def _split_cell(tmp_path: Path, rel: str) -> tuple[Path, Path]:
    """Write a FLAT copy and an ``extends:`` copy of one real cell; return (flat, child)."""
    raw = _absolutize_brief(_raw(rel), rel)
    flat = dict(raw)
    profile = {"solve": raw["solve"], "mesh": raw["mesh"]}
    child = {k: v for k, v in raw.items() if k not in ("solve", "mesh")}
    child["extends"] = "profile.yaml"

    prof_path = tmp_path / "profile.yaml"
    prof_path.write_text(yaml.safe_dump(profile, sort_keys=False), encoding="utf-8")
    flat_path = tmp_path / "flat.yaml"
    flat_path.write_text(yaml.safe_dump(flat, sort_keys=False), encoding="utf-8")
    child_path = tmp_path / "child.yaml"
    child_path.write_text(yaml.safe_dump(child, sort_keys=False), encoding="utf-8")
    return flat_path, child_path


@pytest.mark.parametrize("rel", CELLS, ids=[Path(c).stem for c in CELLS])
def test_a_real_cell_with_extends_loads_the_same_config_and_sha(tmp_path, rel):
    flat_path, child_path = _split_cell(tmp_path, rel)
    flat = load_config(flat_path)
    child = load_config(child_path)

    assert child.raw == flat.raw
    assert config_sha(child.raw) == config_sha(flat.raw)
    assert child == flat
    for mode in ("screen", "verify", "final"):
        assert solve_spec(mode, child).hash() == solve_spec(mode, flat).hash(), mode


def test_extends_list_merges_in_order_and_child_wins(tmp_path):
    (tmp_path / "a.yaml").write_text("x: 1\nnested: {a: 1, b: 1}\n", encoding="utf-8")
    (tmp_path / "b.yaml").write_text("x: 2\nnested: {b: 2}\n", encoding="utf-8")
    path = tmp_path / "c.yaml"
    path.write_text("extends: [a.yaml, b.yaml]\nx: 3\n", encoding="utf-8")
    from hornlab_search.config import _load_yaml_extends
    merged = _load_yaml_extends(path)
    assert "extends" not in merged
    assert merged == {"x": 3, "nested": {"a": 1, "b": 2}}


def test_recursive_extends_is_resolved(tmp_path):
    (tmp_path / "base.yaml").write_text("solve: {backend: beat_cpu}\n", encoding="utf-8")
    (tmp_path / "mid.yaml").write_text("extends: base.yaml\nmesh: {epw: 6.0}\n", encoding="utf-8")
    path = tmp_path / "leaf.yaml"
    path.write_text("extends: mid.yaml\nname: leaf\n", encoding="utf-8")
    from hornlab_search.config import _load_yaml_extends
    merged = _load_yaml_extends(path)
    assert merged == {"solve": {"backend": "beat_cpu"}, "mesh": {"epw": 6.0}, "name": "leaf"}


def test_a_cycle_is_refused_and_the_chain_named(tmp_path):
    (tmp_path / "a.yaml").write_text("extends: b.yaml\nname: a\n", encoding="utf-8")
    (tmp_path / "b.yaml").write_text("extends: a.yaml\nname: b\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="cycle") as exc:
        load_config(tmp_path / "a.yaml")
    assert "a.yaml" in str(exc.value) and "b.yaml" in str(exc.value)


def test_a_missing_base_names_the_chain(tmp_path):
    (tmp_path / "child.yaml").write_text("extends: nope.yaml\nname: x\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="file not found") as exc:
        load_config(tmp_path / "child.yaml")
    message = str(exc.value)
    assert "nope.yaml" in message and "child.yaml" in message and "chain" in message


def test_extends_works_in_a_brief_too(tmp_path):
    """The plan says configs AND briefs: a brief extending a target profile loads identically."""
    real = yaml.safe_load((EXAMPLES / "briefs" / "ath_core_2in.yaml").read_text(encoding="utf-8"))
    flat = dict(real)
    profile = {"target": real["target"], "weights": real["weights"]}
    child = {k: v for k, v in real.items() if k not in ("target", "weights")}
    child["extends"] = "brief_profile.yaml"
    (tmp_path / "brief_profile.yaml").write_text(yaml.safe_dump(profile), encoding="utf-8")
    (tmp_path / "flat_brief.yaml").write_text(yaml.safe_dump(flat), encoding="utf-8")
    (tmp_path / "child_brief.yaml").write_text(yaml.safe_dump(child), encoding="utf-8")

    a = load_brief(tmp_path / "flat_brief.yaml")
    b = load_brief(tmp_path / "child_brief.yaml")
    # ``path`` is the only field that legitimately differs (it names the file that was loaded).
    assert {k: v for k, v in a.items() if k != "path"} == \
        {k: v for k, v in b.items() if k != "path"}


def test_the_v5_profile_is_gone_and_v7_holds_version_seven():
    profiles = REPO / "examples" / "profiles"
    assert not (profiles / "objective_v5.yaml").exists()
    data = yaml.safe_load((profiles / "objective_v7.yaml").read_text(encoding="utf-8"))
    assert data["objective"]["version"] == 7
    assert (profiles / "fused_cuda.yaml").is_file()
    assert (profiles / "objective_v4.yaml").is_file()


def test_fused_cuda_profile_has_mesh_dof_caps_not_solve():
    """fused_cuda.yaml must put dof_cap_verify/final under mesh:, not solve:, so that a config
    extending it passes ``_build(SolveSettings, ...)``'s unknown-key check."""
    data = yaml.safe_load((REPO / "examples" / "profiles" / "fused_cuda.yaml")
                          .read_text(encoding="utf-8"))
    assert "dof_cap_verify" not in data.get("solve", {}), (
        "fused_cuda.yaml must put dof_cap_verify under mesh:, not solve:")
    assert "dof_cap_final" not in data.get("solve", {}), (
        "fused_cuda.yaml must put dof_cap_final under mesh:, not solve:")
    mesh = data.get("mesh", {})
    assert mesh.get("dof_cap_verify") == 12000
    assert mesh.get("dof_cap_final") == 12000
    assert data.get("solve", {}).get("cuda_fused") is True


def test_fused_cuda_profile_merges_into_a_real_cell(tmp_path):
    """A config that extends fused_cuda.yaml should load successfully (the dof_cap keys must be
    in the mesh block so ``_build`` doesn't reject them)."""
    # Use the first real cell as the base (it's a cuda config); strip cuda_fused to avoid a
    # ConfigError for a non-cuda backend if the cell's backend is beat_cpu.
    rel = CELLS[0]
    raw = _absolutize_brief(_raw(rel), rel)
    # Ensure the base config uses beat_cuda so cuda_fused is accepted
    raw.setdefault("solve", {})
    raw["solve"]["backend"] = "beat_cuda"
    raw["solve"].pop("cuda_fused", None)  # will come from profile
    base_path = tmp_path / "base.yaml"
    base_path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    child = {"extends": ["base.yaml",
                         str((REPO / "examples" / "profiles" / "fused_cuda.yaml").resolve())]}
    child_path = tmp_path / "child.yaml"
    child_path.write_text(yaml.safe_dump(child, sort_keys=False), encoding="utf-8")
    cfg = load_config(child_path)
    assert cfg.solve.cuda_fused is True
    assert cfg.mesh.dof_cap_verify == 12000
    assert cfg.mesh.dof_cap_final == 12000
