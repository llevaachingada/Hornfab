"""Overview (phase 1): the live project briefing behind ``GET /api/overview``.

Read-only over ``runs/``. It rolls run folders up into the units a person reasons in:

* **score identity** - one rankable (brief, objective version) pair, from
  ``examples/score_identities.yaml`` (floor, status). J is never ranked across identities.
* **typology** - the knowledge-hub family card a run belongs to (``docs/knowledge/typologies``),
  resolved from the config name, plus a construction label (fold, morph, klangfilm, ...).
  The run's own ``family`` field is only ``OSSE``/``FREEFORM`` and cannot be grouped on.
* **line of work** - identity x construction: every run of one construction under one score,
  so resumes, continuations, scout repeats and warm starts fold into one row.

Leaders are lines ranked by their best valid J inside one identity; probe runs (fewer than
``min_valid_for_leader`` valid evaluations) never lead. With a published floor, every line
within ``floor_j`` of the leader is marked a tie.
"""
from __future__ import annotations

import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml

from . import data as D

IDENTITIES_REL = Path("examples/score_identities.yaml")
KNOWLEDGE_CARD_REL = "docs/knowledge/typologies/{card}.md"

#: Family cards of the knowledge hub (docs/knowledge/README.md), in display order.
FAMILY_CARDS = {
    "osse_ath": "OSSE / R-OSSE / ATH",
    "lecleach_iwata": "JMLC / Le Cleac'h / Iwata",
    "biradial": "Keele / biradial",
    "salmon": "Salmon / X-shape",
    "classical": "Conical / exponential / tractrix",
    "multicell": "Multicell",
    "meh": "MEH / multiple-entry",
    "experimental_morphs": "Derived morphs / rolled / experimental",
    "unclassified": "Unclassified",
}

#: (pattern, card, construction) - first match on the lower-cased config name wins. Order matters:
#: specific constructions before the broad OSSE tokens they often contain (e.g. "crowe_x_osse").
_TYPOLOGY_RULES: tuple[tuple[str, str, str], ...] = (
    (r"(^|_)meh(_|$)|sawmod_meh|solana_meh", "meh", "meh"),
    (r"klangfilm", "experimental_morphs", "klangfilm"),
    (r"crowe", "experimental_morphs", "crowe"),
    (r"rolled|spiral", "experimental_morphs", "rolled"),
    (r"section_axial|(^|_)rf__|(^|_)rf_rect", "experimental_morphs", "section_axial"),
    (r"(^|_)rr__", "experimental_morphs", "rolled_rect"),
    (r"petal_os|quatrefoil|ruffle|chanterelle|trumpet|hybrid__|(^|_)sf_", "experimental_morphs", "hybrid"),
    (r"lecleach|iwata|jmlc", "lecleach_iwata", "lecleach"),
    (r"biradial|keele|es_style", "biradial", "biradial"),
    (r"salmon|flute|ripple", "salmon", "salmon"),
    (r"multicell", "multicell", "multicell"),
    (r"tractrix", "classical", "tractrix"),
    (r"conical", "classical", "conical"),
    (r"exponential|(^|_)expo(_|$)", "classical", "exponential"),
    (r"rosse", "osse_ath", "r-osse"),
    (r"tritonia", "osse_ath", "tritonia"),
    (r"twinray", "osse_ath", "twinray"),
    (r"fold", "osse_ath", "fold"),
    (r"morph", "osse_ath", "morph"),
    (r"ext_throat", "osse_ath", "ext_throat"),
    (r"petal", "osse_ath", "petal"),
    (r"hypex", "osse_ath", "osse_hypex"),
    (r"core_?law|ath_core|atlas", "osse_ath", "ath_core"),
    (r"crease|gcurve|ridge", "osse_ath", "osse_detail"),
    (r"osse|(^|_)ath(_|$)", "osse_ath", "osse"),
    # No knowledge-hub card claims these: keep them Unclassified but name the construction, so
    # they never pose as a family (grounding rule: no cross-family assumptions by guess).
    (r"(^|_)fid_", "unclassified", "fidelity_probe"),
    (r"(^|_)abl_", "unclassified", "ablation"),
    (r"plughorn", "unclassified", "cone_plughorn"),
    (r"(^|_)icw", "unclassified", "icw"),
    (r"qtw", "unclassified", "qtw_waveguide"),
    (r"grid_ellipse|ellipse", "unclassified", "ellipse"),
    (r"(^|_)sp__", "unclassified", "sp"),
    (r"sculpt|freeform", "unclassified", "freeform"),
)
_TYPOLOGY_RE = tuple((re.compile(p), card, cons) for p, card, cons in _TYPOLOGY_RULES)


def typology_of(name: str | None, family: str | None = None) -> dict:
    """``{card, card_label, construction, card_doc}`` for a config name (``family`` is the
    fallback: a bare ``OSSE``/``R-OSSE`` run with an uninformative name is still OSSE)."""
    n = str(name or "").lower()
    for rx, card, cons in _TYPOLOGY_RE:
        if rx.search(n):
            break
    else:
        fam = str(family or "").upper()
        card, cons = (("osse_ath", "r-osse") if fam == "R-OSSE" else
                      ("osse_ath", "osse") if fam == "OSSE" else ("unclassified", "unclassified"))
    return {"card": card, "card_label": FAMILY_CARDS[card], "construction": cons,
            "card_doc": KNOWLEDGE_CARD_REL.format(card=card) if card != "unclassified" else None}


# ---------------------------------------------------------------------------- identities

def load_identities(root: Path) -> dict:
    """The registry, validated. A missing or malformed file is reported, never guessed around:
    every run then resolves to an unregistered identity."""
    path = Path(root) / IDENTITIES_REL
    out = {"path": IDENTITIES_REL.as_posix(), "error": None, "defaults": {}, "identities": []}
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        out["error"] = f"{type(exc).__name__}: {exc}"
        return out
    if raw.get("schema") != "score_identities_v1":
        out["error"] = f"{out['path']}: schema must be score_identities_v1"
        return out
    out["updated"] = str(raw.get("updated") or "")
    out["defaults"] = dict(raw.get("defaults") or {})
    seen = set()
    for e in raw.get("identities") or []:
        if not isinstance(e, dict) or not e.get("id") or not e.get("brief"):
            continue
        key = (str(e["brief"]), int(e.get("objective_version") or 0))
        if key in seen:
            out["error"] = f"duplicate identity for brief {key[0]!r} v{key[1]}"
            continue
        seen.add(key)
        out["identities"].append(e)
    return out


def _identity_for(reg: dict, brief: str | None, version: int | None) -> dict:
    for e in reg["identities"]:
        if str(e["brief"]) == str(brief) and int(e.get("objective_version") or 0) == int(version or 0):
            return e
    legacy_below = int(reg["defaults"].get("legacy_below_version", 7))
    v = int(version or 1)
    return {"id": f"{brief or 'no_brief'}__v{v}", "label": f"{brief or '(no brief)'} · v{v}",
            "brief": brief, "objective_version": v, "floor_j": None,
            "status": "legacy" if v < legacy_below else "unregistered", "source": None}


# ---------------------------------------------------------------------------- runs

def _parse_utc(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        t = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def _refused(summary: dict) -> int:
    return int(sum(int(v or 0) for v in (summary.get("failures") or {}).values()))


def run_records(runs: Path, since: datetime) -> list[dict]:
    """Run summaries whose newest row is at or after ``since``; the ndjson mtime is a cheap
    pre-filter so a large history is never fully re-read."""
    cutoff = since.timestamp() - 3600          # mtime slack for clock / write lag
    out = []
    for d in D._run_dirs(runs):
        try:
            if (d / "search.ndjson").stat().st_mtime < cutoff:
                continue
        except OSError:
            continue
        try:
            s = D.run_summary(d)
        except Exception:                      # noqa: BLE001 - one unreadable run never hides the rest
            continue
        last = _parse_utc(s.get("last"))
        if last is None or last < since:
            continue
        out.append(s)
    return out


# ---------------------------------------------------------------------------- overview

def overview(root: Path, runs: Path, days: float = 14.0, show_legacy: bool = False) -> dict:
    """Briefing KPIs + per-identity leaders (lines of work) for runs active in the last ``days``."""
    t0 = time.time()
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=float(days))
    reg = load_identities(root)
    min_valid = int(reg["defaults"].get("min_valid_for_leader", 10))
    recs = run_records(runs, since)

    day_ago = now - timedelta(days=1)
    kpi = {"runs": len(recs), "evals": 0, "valid": 0, "refused": 0,
           "runs_24h": 0, "evals_24h": 0, "active_runs": 0}
    idents: dict[str, dict] = {}
    for s in recs:
        n, ok, ref = int(s.get("n") or 0), int(s.get("n_ok") or 0), _refused(s)
        kpi["evals"] += n
        kpi["valid"] += ok
        kpi["refused"] += ref
        last = _parse_utc(s.get("last"))
        if last and last >= day_ago:
            kpi["runs_24h"] += 1
            kpi["evals_24h"] += int(s.get("session_n") or n) if s.get("resumed") else n
        if s.get("active"):
            kpi["active_runs"] += 1
        ident = _identity_for(reg, s.get("brief"), s.get("objective_version"))
        typ = typology_of(s.get("name"), s.get("family"))
        g = idents.setdefault(ident["id"], {"identity": ident, "lines": {}, "runs": 0, "evals": 0,
                                            "probes": 0, "last": None})
        g["runs"] += 1
        g["evals"] += n
        if g["last"] is None or (s.get("last") or "") > g["last"]:
            g["last"] = s.get("last")
        probe = ok < min_valid
        g["probes"] += int(probe)
        key = f"{typ['card']}|{typ['construction']}"
        line = g["lines"].setdefault(key, {
            "key": key, **typ, "runs": [], "best_j": None, "best_run_id": None,
            "best_run_name": None, "best_dims": None, "evals": 0, "valid": 0, "refused": 0,
            "last": None, "verified": False, "active": False, "probe_only": True})
        line["evals"] += n
        line["valid"] += ok
        line["refused"] += ref
        line["active"] = line["active"] or bool(s.get("active"))
        line["verified"] = line["verified"] or bool(s.get("has_verify") or s.get("has_inline_verify"))
        if line["last"] is None or (s.get("last") or "") > line["last"]:
            line["last"] = s.get("last")
        bj = s.get("best_j")
        line["runs"].append({"id": s.get("id"), "name": s.get("name"), "best_j": bj, "n": n,
                             "n_ok": ok, "refused": ref, "last": s.get("last"),
                             "mode": s.get("mode"), "probe": probe, "active": bool(s.get("active"))})
        if bj is None or probe or s.get("mode") == "verify":
            continue
        line["probe_only"] = False
        if line["best_j"] is None or bj < line["best_j"]:
            line.update(best_j=bj, best_run_id=s.get("id"), best_run_name=s.get("name"),
                        best_dims=s.get("dims"))

    identities = []
    for g in idents.values():
        ident = g["identity"]
        if ident["status"] == "legacy" and not show_legacy:
            continue
        lines = list(g["lines"].values())
        for ln in lines:
            ln["runs"].sort(key=lambda r: r.get("last") or "", reverse=True)
            ln["refused_pct"] = round(100.0 * ln["refused"] / ln["evals"], 1) if ln["evals"] else None
        ranked = sorted((ln for ln in lines if ln["best_j"] is not None), key=lambda ln: ln["best_j"])
        unranked = [ln for ln in lines if ln["best_j"] is None]
        lead = ranked[0]["best_j"] if ranked else None
        floor = ident.get("floor_j")
        for i, ln in enumerate(ranked, 1):
            ln["rank"] = i
            ln["gap"] = (ln["best_j"] - lead) if lead is not None else None
            ln["tie"] = bool(floor is not None and ln["gap"] is not None and ln["gap"] <= float(floor))
        n_tied = sum(1 for ln in ranked if ln["tie"])
        identities.append(D.clean({
            "id": ident["id"], "label": ident.get("label") or ident["id"],
            "brief": ident.get("brief"), "objective_version": ident.get("objective_version"),
            "status": ident["status"], "floor_j": floor, "bar_j": ident.get("bar_j"),
            "source": ident.get("source"), "runs": g["runs"], "evals": g["evals"],
            "probes": g["probes"], "last": g["last"], "leader_j": lead,
            "n_tied": n_tied if floor is not None else None,
            "lines": ranked + unranked}))
    status_order = {"current": 0, "unregistered": 1, "diagnostic": 2, "legacy": 3}
    identities.sort(key=lambda x: (status_order.get(x["status"], 9), -(x.get("evals") or 0)))

    # typology rollup: family card x identity, best rank per cell
    cards: dict[str, dict] = {}
    for ident in identities:
        for ln in ident["lines"]:
            c = cards.setdefault(ln["card"], {"card": ln["card"], "label": ln["card_label"],
                                              "doc": ln.get("card_doc"), "evals": 0,
                                              "constructions": set(), "cells": {}})
            c["evals"] += ln["evals"]
            c["constructions"].add(ln["construction"])
            cell = c["cells"].get(ident["id"])
            if ln.get("rank") and (cell is None or ln["rank"] < cell["rank"]):
                c["cells"][ident["id"]] = {"rank": ln["rank"], "of": sum(1 for x in ident["lines"] if x.get("rank")),
                                           "best_j": ln["best_j"], "tie": ln.get("tie"),
                                           "construction": ln["construction"]}
    typology = [dict(c, constructions=sorted(c["constructions"]))
                for c in sorted(cards.values(), key=lambda c: list(FAMILY_CARDS).index(c["card"]))]

    lanes = None
    try:
        lanes = D.lane_status(runs)
    except Exception as exc:                   # noqa: BLE001 - lane errors are shown, not fatal
        lanes = {"error": f"{type(exc).__name__}: {exc}"}
    readiness = None
    try:
        from . import data_hw as HW
        r = HW.load_registry(root)
        risks = r.get("risks") or []
        readiness = {"registry": HW.REGISTRY_REL.as_posix(), "error": r.get("error"),
                     "open_decisions": sum(1 for d in r.get("decisions") or [] if d.get("status") != "closed"),
                     "risks_open": sum(1 for x in risks if x.get("status") != "closed"),
                     "risks_critical": sum(1 for x in risks if str(x.get("level") or "").upper() == "CRITICAL"
                                           and x.get("status") != "closed")}
    except Exception as exc:                   # noqa: BLE001
        readiness = {"error": f"{type(exc).__name__}: {exc}"}

    kpi["refused_pct"] = round(100.0 * kpi["refused"] / kpi["evals"], 1) if kpi["evals"] else None
    return D.clean({
        "generated_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "days": float(days),
        "since_utc": since.strftime("%Y-%m-%dT%H:%M:%SZ"), "show_legacy": bool(show_legacy),
        "registry": {"path": reg["path"], "error": reg["error"], "updated": reg.get("updated"),
                     "min_valid_for_leader": min_valid},
        "kpis": kpi, "identities": identities, "typology": typology,
        "lanes": lanes, "readiness": readiness, "elapsed_s": round(time.time() - t0, 2)})
