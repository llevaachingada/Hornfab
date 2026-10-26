"""Widen the 2026-10-26 campaign search boxes to physical ranges (owner ruling).

    .venv\\Scripts\\python.exe tools/widen_campaign_boxes.py --dry-run
    .venv\\Scripts\\python.exe tools/widen_campaign_boxes.py --write

The campaign lane narrowed boxes to keep the invalid rate under 40 %, leaving searched knobs
boxed at 1-10 % of their seed. The owner ruling: the box must not be the binding constraint;
the brief envelope + mesh validity are. This tool widens every SEARCHED knob (a ``bounds``
entry without ``search: false``) to the physical range, intersects with the ``KeySpec`` hard
limits in ``hornlab_search/design/families.py``, keeps the seed inside the box, and NEVER
narrows an existing edge. Pinned keys stay pinned; seeds are never changed.

Text-only, comment-preserving patch: PyYAML is used to READ and to VERIFY only. The write
changes just the ``lo:``/``hi:`` value tokens inside the ``bounds`` block, plus one
``search.infeasible_penalty: graded`` insertion when absent. Every other byte - the long
hand-written header comments, the inline maps, the ``seed_params:`` block - is untouched.
Precedent: the GUI's ``POST /api/save-bounds`` (``hornlab_search/gui/data.py``).
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hornlab_search.design.families import FAMILY_KEYS  # noqa: E402

CAMPAIGN_DIR = ROOT / "examples" / "typologies" / "campaign_2026-10-26"
SKIP_PREFIXES = ("crease__", "gcurve__", "control__")   # another agent's four configs
PORTRAIT_CELLS = {"b1t", "b2t", "b3bt"}                 # portrait-envelope cells
SEED_BLOCK = "seed_params"


# ------------------------------------------------------------------ physical ranges


def cell_prefix(name: str) -> str:
    return name.split("__", 1)[0]


def _as_dict(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def pinned_keys(doc: dict) -> set[str]:
    """Bounds keys carrying ``search: false`` (they must stay pinned, verbatim)."""
    bounds = _as_dict(doc.get("bounds"))
    return {k for k, v in bounds.items() if isinstance(v, dict) and v.get("search") is False}


def _rel(seed: float, lo_f: float, hi_f: float) -> tuple[float, float]:
    return (lo_f * seed, hi_f * seed)


def physical_range(
    key: str,
    seed: float,
    cell: str,
    family: str,
    envelope_depth: float | None,
) -> tuple[float, float, str] | None:
    """(lo, hi, rule) for one knob, or None when the knob is not in the brief's table.

    Every rule below is one bullet of the SUB-B brief's "Physical boxes" section.
    """
    portrait = cell in PORTRAIT_CELLS
    if key in ("a_deg", "h_a_deg", "v_a_deg"):
        return 10.0, 80.0, "wall half-angle 10..80"
    if key in ("n", "h_n", "v_n"):
        return 1.0, 10.0, "OSSE n 1..10"
    if key in ("s", "h_s", "v_s"):
        return 0.0, 1.5, "OSSE s 0..1.5"
    if key in ("k", "h_k", "v_k"):
        return 0.3, 5.0, "OSSE k 0.3..5"
    if key in ("q", "h_q", "v_q"):
        if family == "R-OSSE":
            return 0.5, 2.0, "R-OSSE q 0.5..2"
        return 0.90, 1.0, "OSSE q 0.90..1.0"
    if key in ("aspect_ratio", "g_ar_m"):
        if portrait:
            return 0.4, 1.2, "aspect 0.4..1.2 (portrait envelope)"
        return 0.4, 2.5, "aspect 0.4..2.5"
    if key in ("exponent", "mouth_exponent", "morph_exponent"):
        return 2.0, 10.0, "exponent 2..10"
    if key == "L_mm":
        if envelope_depth is None:
            return None
        lo = 0.4 * seed
        if lo > envelope_depth:
            return None
        return lo, envelope_depth, f"depth 0.4*seed..envelope {envelope_depth:g}"
    if key in ("R_mm", "h_rm_mm", "v_rm_mm", "morph_width_mm", "morph_height_mm"):
        return _rel(seed, 0.6, 1.15) + ("mouth size 0.6..1.15*seed",)
    if key in ("g_fc_h_hz", "g_fc_hz", "g_fc_v_hz"):
        return _rel(seed, 0.7, 2.0) + ("rows cutoff 0.7..2.0*seed",)
    if key in ("g_T", "h_T", "v_T"):
        return 0.3, 1.0, "rows T 0.3..1.0"
    if key == "g_stop_deg":
        return 90.0, 175.0, "rows stop 90..175"
    if key == "g_x_amp":
        return -0.4, 0.4, "rows x_amp -0.4..0.4"
    if key == "g_x_fc":
        return 0.0, 0.3, "rows x_fc 0..0.3"
    if key == "tmax":
        return 0.6, 1.0, "R-OSSE tmax 0.6..1.0"
    if key == "m":
        return 0.2, 1.5, "R-OSSE m 0.2..1.5"
    if key == "r":
        return 0.05, 1.0, "R-OSSE r 0.05..1.0"
    if key == "b":
        return 0.0, 0.6, "R-OSSE b 0..0.6"
    if key == "morph_rate":
        return 0.5, 8.0, "morph rate 0.5..8"
    if key == "morph_corner_mm":
        return 0.0, 80.0, "morph corner 0..80 mm"
    if key == "morph_fixed":
        return 0.0, 0.6, "morph fixed 0..0.6"
    return None


# knobs that keep their current box, with the reason printed in the report
NOT_IN_TABLE_REASON = "not in the brief's physical table"
NARROWING_EXCEPTIONS = {
    # the salmon diagonal x_amp blow-up: stop stays 90..150, not 90..175
    ("b1t__salmon_x_signed", "g_stop_deg"): 150.0,
    ("b3bt__salmon_x_signed", "g_stop_deg"): 150.0,
}
ATH_TWINRAY_ORIGINALS = {
    "L_mm": (160.0, 240.0),
    "h_a_deg": (22.0, 46.0),
    "v_a_deg": (16.0, 40.0),
    "h_s": (0.25, 0.95),
    "v_s": (0.25, 0.95),
    "h_n": (3.5, 9.0),
    "v_n": (3.5, 9.0),
    "h_q": (0.96, 1.0),
    "v_q": (0.96, 1.0),
    "mouth_exponent": (2.0, 12.0),
}


# ------------------------------------------------------------------ text patching


def _fmt(v: float) -> str:
    return repr(round(float(v), 6))


def _find_block(lines: list[str], block: str) -> int | None:
    pat = re.compile(rf"^{re.escape(block)}\s*:\s*(#.*)?(\r?\n)?$")
    return next((i for i, ln in enumerate(lines) if pat.match(ln)), None)


def patch_bounds_lines(text: str, updates: dict[str, tuple[float, float]]) -> tuple[str, set[str]]:
    """Comment-preserving, indentation-aware patch of ONLY the bounds ``lo:``/``hi:`` tokens.

    Supports block mappings and a flow mapping on the key line (``key: {lo: .., hi: ..}``).
    No YAML round trip: the rest of the file stays byte-identical.
    """
    lines = text.splitlines(keepends=True)
    start = _find_block(lines, "bounds")
    if start is None:
        return text, set()

    key_indent = None
    for line in lines[start + 1:]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not line[:1].isspace():
            break
        key_indent = len(line) - len(line.lstrip())
        break
    if key_indent is None:
        return text, set()

    patched: set[str] = set()
    key_line = re.compile(
        r"^(?P<indent>\s*)(?P<q>['\"]?)(?P<key>[^:'\"]+)(?P=q)\s*:(?P<rest>.*)$")
    leaf = re.compile(r"^(?P<lead>\s*)(?P<kind>lo|hi)\s*:\s*(?P<val>[^\s#]+)(?P<trail>.*)$")

    i = start + 1
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            indent = len(line) - len(line.lstrip())
            if indent <= 0 or indent < key_indent:
                break
        if not stripped or stripped.startswith("#") or (len(line) - len(line.lstrip())) != key_indent:
            i += 1
            continue
        m = key_line.match(line)
        if not m:
            i += 1
            continue
        key = m.group("key")
        if key not in updates:
            i += 1
            continue
        lo, hi = updates[key]
        rest = m.group("rest")
        if "{" in rest:
            new_rest = re.sub(r"(lo\s*:\s*)([^,}\s]+)",
                              lambda mm: mm.group(1) + _fmt(lo), rest, count=1)
            new_rest = re.sub(r"(hi\s*:\s*)([^,}\s]+)",
                              lambda mm: mm.group(1) + _fmt(hi), new_rest, count=1)
            if new_rest != rest:
                lines[i] = line[:m.start("rest")] + new_rest
                patched.add(key)
            i += 1
            continue
        found = set()
        j = i + 1
        while j < len(lines):
            nxt = lines[j]
            nxt_stripped = nxt.strip()
            nxt_indent = len(nxt) - len(nxt.lstrip())
            if nxt_stripped and not nxt_stripped.startswith("#") and nxt_indent <= key_indent:
                break
            lm = leaf.match(nxt)
            if lm and lm.group("kind") not in found:
                value = lo if lm.group("kind") == "lo" else hi
                lines[j] = nxt[:lm.start("val")] + _fmt(value) + nxt[lm.end("val"):]
                found.add(lm.group("kind"))
            j += 1
        if found == {"lo", "hi"}:
            patched.add(key)
        i = j
    return "".join(lines), patched


def insert_block_key(text: str, block: str, entry: str) -> str:
    """Insert ``entry`` as the last child of top-level ``block:`` (byte-preserving otherwise)."""
    nl = "\r\n" if "\r\n" in text else "\n"
    lines = text.splitlines(keepends=True)
    start = _find_block(lines, block)
    if start is None:
        raise ValueError(f"top-level block {block!r} not found")
    indent, last = 2, start
    for j in range(start + 1, len(lines)):
        st = lines[j].strip()
        if not st or st.startswith("#"):
            continue
        if not lines[j][:1].isspace():
            break
        if last == start:
            indent = len(lines[j]) - len(lines[j].lstrip())
        last = j
    if not lines[last].endswith(("\n", "\r\n")):
        lines[last] += nl
    lines.insert(last + 1, " " * indent + entry + nl)
    return "".join(lines)


def block_text(text: str, block: str) -> str:
    lines = text.splitlines(keepends=True)
    start, end = block_span(lines, block)
    if start is None:
        return ""
    return "".join(lines[start:end])


def block_span(lines: list[str], block: str) -> tuple[int | None, int]:
    """Line span [start, end) of a top-level ``block:`` mapping."""
    start = _find_block(lines, block)
    if start is None:
        return None, 0
    end = len(lines)
    for j in range(start + 1, len(lines)):
        st = lines[j].strip()
        if st and not st.startswith("#") and not lines[j][:1].isspace():
            end = j
            break
    return start, end


# ------------------------------------------------------------------ planning


@dataclass
class Kept:
    key: str
    box: tuple[float, float] | None
    reason: str


@dataclass
class Change:
    key: str
    old: tuple[float, float]
    new: tuple[float, float]
    rule: str


@dataclass
class Cell:
    path: Path
    name: str
    family: str
    changes: list[Change] = field(default_factory=list)
    kept: list[Kept] = field(default_factory=list)
    pinned: list[str] = field(default_factory=list)
    add_penalty: bool = False
    brief_note: str = ""
    old_text: str = ""
    new_text: str = ""

    @property
    def changed(self) -> bool:
        return bool(self.changes) or self.add_penalty


def envelope_depth(path: Path, raw: dict, cfg_dir: Path) -> tuple[float | None, str]:
    rel = raw.get("brief_file")
    if not isinstance(rel, str) or not rel:
        return None, "no brief_file; L_mm hi kept"
    brief = (cfg_dir / rel).resolve()
    try:
        doc = yaml.safe_load(brief.read_text(encoding="utf-8")) or {}
        depth = (doc.get("envelope") or {}).get("max_depth_mm")
        if depth is None:
            return None, f"brief {brief.name} has no envelope.max_depth_mm; L_mm hi kept"
        return float(depth), ""
    except (OSError, yaml.YAMLError) as exc:
        return None, f"brief {brief.name} unresolvable ({exc}); L_mm hi kept"


def plan_cell(path: Path) -> Cell:
    text = path.read_bytes().decode("utf-8")
    doc = yaml.safe_load(text) or {}
    name = str(doc.get("name") or path.stem)
    family = str(doc.get("family") or "")
    seeds = _as_dict(doc.get("seed_params"))
    bounds = _as_dict(doc.get("bounds"))
    specs = FAMILY_KEYS.get(family, {})
    depth, brief_note = envelope_depth(path, doc, path.parent)
    cell = Cell(path=path, name=name, family=family, brief_note=brief_note, old_text=text)

    updates: dict[str, tuple[float, float]] = {}
    for key in [k for k, v in bounds.items() if isinstance(v, dict)]:
        row = bounds[key]
        if "lo" not in row or "hi" not in row:
            cell.kept.append(Kept(key, None, "no lo/hi pair"))
            continue
        old = (float(row["lo"]), float(row["hi"]))
        if row.get("search") is False:
            cell.pinned.append(key)
            continue
        if key not in seeds:
            cell.kept.append(Kept(key, old, "no seed_params value"))
            continue
        seed = float(seeds[key])
        phys = physical_range(key, seed, cell_prefix(name), family, depth)
        if phys is None:
            cell.kept.append(Kept(key, old, NOT_IN_TABLE_REASON))
            continue
        lo, hi, rule = phys
        hi_cap = NARROWING_EXCEPTIONS.get((name, key))
        if hi_cap is not None:
            hi = min(hi, hi_cap)
            rule += f" (exception: hi {hi_cap:g})"
        spec = specs.get(key)
        if spec is not None:
            if spec.lo is not None and lo < float(spec.lo):
                lo = float(spec.lo)
                rule += f" (hard lo {spec.lo:g})"
            if spec.hi is not None and hi > float(spec.hi):
                hi = float(spec.hi)
                rule += f" (hard hi {spec.hi:g})"
        # keep the seed inside the box, then never narrow an existing edge
        lo, hi = min(lo, seed), max(hi, seed)
        if name == "native__ath_twinray_380" and key in ATH_TWINRAY_ORIGINALS:
            a_lo, a_hi = ATH_TWINRAY_ORIGINALS[key]
            lo, hi = min(lo, a_lo), max(hi, a_hi)
            rule += f" v ATH originals {a_lo:g}..{a_hi:g}"
        # canonicalise to the 6-decimal text form so a second --write is a no-op
        new = (round(min(lo, old[0]), 6), round(max(hi, old[1]), 6))
        if new[0] < round(lo, 6):
            rule += f"; lo kept at current {_fmt(old[0])} (never narrow)"
        if new[1] > round(hi, 6):
            rule += f"; hi kept at current {_fmt(old[1])} (never narrow)"
        if (_fmt(new[0]), _fmt(new[1])) == (_fmt(old[0]), _fmt(old[1])):
            cell.kept.append(Kept(key, old, "current box already covers the physical range"))
            continue
        updates[key] = new
        cell.changes.append(Change(key=key, old=old, new=new, rule=rule))

    new_text, patched = patch_bounds_lines(text, updates)
    missing = sorted(set(updates) - patched)
    if missing:
        raise SystemExit(f"{path.name}: could not patch bounds rows: {missing}")
    search = _as_dict(doc.get("search"))
    if "infeasible_penalty" not in search:
        cell.add_penalty = True
        new_text = insert_block_key(new_text, "search", "infeasible_penalty: graded")
    cell.new_text = new_text
    return cell


def list_cells() -> list[Cell]:
    paths = sorted(
        (p for p in CAMPAIGN_DIR.glob("*.yaml")
         if not p.name.startswith(SKIP_PREFIXES)),
        key=lambda p: p.name,
    )
    return [plan_cell(p) for p in paths]


# ------------------------------------------------------------------ reporting

def print_table(cells: list[Cell]) -> None:
    for cell in cells:
        print(f"=== {cell.name}  [{cell.family}]")
        if cell.brief_note:
            print(f"  ! {cell.brief_note}")
        for ch in cell.changes:
            before = f"{_fmt(ch.old[0])} .. {_fmt(ch.old[1])}"
            after = f"{_fmt(ch.new[0])} .. {_fmt(ch.new[1])}"
            print(f"  {ch.key:<18} {before:>24}  ->  {after:<24} {ch.rule}")
        for kept in cell.kept:
            box = "" if kept.box is None else (
                f"{_fmt(kept.box[0])} .. {_fmt(kept.box[1])}")
            print(f"  - {kept.key:<18} {box:>24}   kept: {kept.reason}")
        if cell.pinned:
            print(f"  pinned (search: false): {', '.join(cell.pinned)}")
        if cell.add_penalty:
            print("  search.infeasible_penalty: (absent) -> graded")
        if not cell.changes:
            print("  (no box changes)")
    changed = sum(1 for c in cells if c.changed)
    print(f"\ncells: {len(cells)}   files changed: {changed}   "
          f"knobs changed: {sum(len(c.changes) for c in cells)}")


# ------------------------------------------------------------------ verification

BOUNDS_LEAF = re.compile(r"^\s+(lo|hi)\s*:")


def verify_cell(cell: Cell) -> list[str]:
    """Post-write proof: parses, seed block byte-identical, pins intact, only lo/hi touched."""
    problems: list[str] = []
    before, after = cell.old_text, cell.new_text
    try:
        after_doc = yaml.safe_load(after) or {}
    except yaml.YAMLError as exc:  # pragma: no cover - would be a real failure
        return [f"{cell.name}: after-text no longer parses: {exc}"]
    before_doc = yaml.safe_load(before) or {}
    if cell.name not in (after_doc.get("name"), cell.path.stem):
        problems.append(f"{cell.name}: name field changed")

    if block_text(before, SEED_BLOCK) != block_text(after, SEED_BLOCK):
        problems.append(f"{cell.name}: seed_params block changed")

    if pinned_keys(before_doc) != pinned_keys(after_doc):
        problems.append(f"{cell.name}: search: false set changed "
                        f"{sorted(pinned_keys(before_doc))} -> {sorted(pinned_keys(after_doc))}")
    if before.count("search: false") != after.count("search: false"):
        problems.append(f"{cell.name}: raw 'search: false' count changed")

    before_lines = before.splitlines(keepends=True)
    after_lines = after.splitlines(keepends=True)
    b_start, b_end = block_span(before_lines, "bounds")
    a_start, a_end = block_span(after_lines, "bounds")
    if b_start is None or a_start is None:
        problems.append(f"{cell.name}: bounds block missing")
        return problems
    b_block = before_lines[b_start:b_end]
    a_block = after_lines[a_start:a_end]
    if len(b_block) != len(a_block):
        problems.append(f"{cell.name}: bounds block changed line count")
    for old_line, new_line in zip(b_block, a_block):
        if old_line != new_line and not (BOUNDS_LEAF.match(old_line)
                                         and BOUNDS_LEAF.match(new_line)):
            problems.append(f"{cell.name}: non-lo/hi line inside bounds changed: {old_line!r}")

    # every byte outside the bounds block must be identical, except the one insertion
    before_out = "".join(before_lines[:b_start] + before_lines[b_end:])
    after_out = "".join(after_lines[:a_start] + after_lines[a_end:])
    if cell.add_penalty:
        out_lines = after_out.splitlines(keepends=True)
        added = [i for i, ln in enumerate(out_lines)
                 if ln.strip() == "infeasible_penalty: graded"]
        if len(added) != 1:
            problems.append(f"{cell.name}: expected exactly one infeasible_penalty insertion")
        else:
            after_out = "".join(out_lines[:added[0]] + out_lines[added[0] + 1:])
    if before_out != after_out:
        problems.append(f"{cell.name}: content outside the bounds block changed")
    return problems


def write_cells(cells: list[Cell]) -> int:
    written = 0
    for cell in cells:
        if cell.old_text != cell.new_text:
            cell.path.write_bytes(cell.new_text.encode("utf-8"))
            written += 1
    n = len(cells)
    seed_ok = 0
    pin_files_ok = 0
    pins_before = 0
    pins_after = 0
    parsed = 0
    problems: list[str] = []
    for cell in cells:
        found = verify_cell(cell)
        problems += found
        after = yaml.safe_load(cell.path.read_bytes().decode("utf-8")) or {}
        parsed += 1
        if block_text(cell.old_text, SEED_BLOCK) == block_text(
                cell.path.read_bytes().decode("utf-8"), SEED_BLOCK):
            seed_ok += 1

        before_doc = yaml.safe_load(cell.old_text) or {}
        pins_before += len(pinned_keys(before_doc))
        pins_after += len(pinned_keys(after))
        if pinned_keys(before_doc) == pinned_keys(after):
            pin_files_ok += 1
        if not isinstance(after.get("search"), dict) or \
                after["search"].get("infeasible_penalty") != "graded":
            problems.append(f"{cell.name}: search.infeasible_penalty is not graded")
    print(f"\nwritten: {written}/{n} files")
    print(f"yaml parses: {parsed}/{n}")
    print(f"seeds unchanged: {seed_ok}/{n}")
    print(f"pinned search:false entries intact: {pins_after}/{pins_before} "
          f"({pin_files_ok}/{n} files)")
    if problems:
        for p in problems:
            print(f"FAIL {p}")
        return 1
    print("all checks passed")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="print the table, write nothing")
    mode.add_argument("--write", action="store_true", help="apply the widening")
    args = ap.parse_args(argv)
    cells = list_cells()
    if not cells:
        raise SystemExit(f"no configs under {CAMPAIGN_DIR}")
    print_table(cells)
    if args.write:
        return write_cells(cells)
    if args.dry_run or not args.write:
        changed = sum(1 for c in cells if c.changed)
        print("dry run: nothing written" + ("" if changed else " - no changes"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
