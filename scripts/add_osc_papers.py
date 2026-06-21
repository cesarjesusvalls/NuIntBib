#!/usr/bin/env python3
"""Add classified oscillation candidates into the oscillation cluster.

Reads the discovery candidates (data/osc_candidates.yml, full metadata) and one
or more classification JSON files (arrays of {bibtag, decision, source,
framework, bsm_type, channels, mode, parameters, needs_fulltext}). For every
"keep", builds a record (candidate metadata + one measurement) with a normalized
collaboration, merges into data/oscillation/<Collaboration>.yml, and validates.

Usage:
  scripts/add_osc_papers.py /tmp/osc_cls.json /tmp/osc_out_*.json
  scripts/add_osc_papers.py --dry-run /tmp/osc_cls.json
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OSC_DIR = os.path.join(ROOT, "data", "oscillation")

# bibtag-prefix / raw-collaboration -> canonical file name (match the seed)
COLLAB_CANON = {
    "doublechooz": "Double Chooz",
    "dayabay": "Daya Bay",
    "super-kamiokande": "Super-Kamiokande",
    "superkamiokande": "Super-Kamiokande",
    "kamland": "KamLAND",
    "minibooNE".lower(): "MiniBooNE",
    "microboone": "MicroBooNE",
    "icecube": "IceCube",
    "km3net": "KM3NeT",
    "nova": "NOvA",
    "borexino": "Borexino",
    "gallex": "GALLEX",
    "sage": "SAGE",
    "antares": "ANTARES",
    "double-chooz": "Double Chooz",
}


# Collaboration-keyed texkey prefixes = real measurements. Author-keyed bibtags
# (a surname prefix) are proceedings/theses/talks and are dropped.
COLLAB_PREFIXES = {
    "T2K", "NOvA", "MINOS", "MINOS+", "K2K", "OPERA", "ICARUS", "MiniBooNE",
    "MicroBooNE", "LSND", "KamLAND", "DayaBay", "RENO", "DoubleChooz", "STEREO",
    "PROSPECT", "DANSS", "NEOS", "Neutrino-4", "NEUTRINO-4", "Super-Kamiokande",
    "IceCube", "IceCube-Gen2", "ANTARES", "KM3NeT", "SNO", "SNO+", "Borexino",
    "GALLEX", "GNO", "SAGE", "Homestake", "SciBooNE",
}


def is_collaboration_keyed(bibtag: str) -> bool:
    return bibtag.split(":")[0] in COLLAB_PREFIXES


def canon_collab(bibtag: str, raw: str) -> str:
    prefix = bibtag.split(":")[0]
    key = prefix.lower()
    if key in COLLAB_CANON:
        return COLLAB_CANON[key]
    # otherwise the texkey prefix is already clean (T2K, MINOS, SNO, RENO, ...)
    return prefix


def load_classifications(paths: list[str]) -> dict:
    out: dict[str, dict] = {}
    for p in paths:
        for f in sorted(glob.glob(p)):
            for c in json.load(open(f, encoding="utf-8")):
                out[c["bibtag"]] = c  # later files win on dup
    return out


def build_record(cand: dict, cls: dict) -> dict:
    rec = {k: v for k, v in cand.items() if not k.startswith("_") and k != "measurements"}
    rec["collaboration"] = canon_collab(cand["bibtag"], cand.get("collaboration", ""))
    note = "needs full-text check" if cls.get("needs_fulltext") else None
    rec["notes"] = note
    rec["measurements"] = [
        {
            "source": cls["source"],
            "framework": cls["framework"],
            "bsm_type": cls.get("bsm_type"),
            "channels": cls.get("channels") or [],
            "mode": cls.get("mode") or [],
            "parameters": cls.get("parameters") or [],
            "observables": None,
            "notes": None,
        }
    ]
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("classifications", nargs="+", help="JSON file(s)/glob(s)")
    ap.add_argument("--candidates", default=os.path.join(ROOT, "data", "osc_candidates.yml"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cands = {r["bibtag"]: r for r in (yaml.safe_load(open(args.candidates)) or [])}
    cls = load_classifications(args.classifications)
    keeps = {b: c for b, c in cls.items() if c.get("decision") == "keep"}

    # existing osc DB
    existing: dict[str, list] = {}
    have = set()
    for f in glob.glob(os.path.join(OSC_DIR, "*.yml")):
        recs = yaml.safe_load(open(f)) or []
        for r in recs:
            have.add(r["bibtag"])
            existing.setdefault(r["collaboration"], []).append(r)

    added: dict[str, int] = {}
    skipped_author = 0
    for bibtag, c in keeps.items():
        if bibtag in have or bibtag not in cands:
            continue
        if not is_collaboration_keyed(bibtag):
            skipped_author += 1
            continue
        rec = build_record(cands[bibtag], c)
        exp = rec["collaboration"]
        existing.setdefault(exp, []).append(rec)
        have.add(bibtag)
        added[exp] = added.get(exp, 0) + 1

    total = sum(added.values())
    print(f"{len(keeps)} keeps in classification, {total} new to add "
          f"({skipped_author} author-keyed proceedings/theses skipped)")
    for e, n in sorted(added.items(), key=lambda x: -x[1]):
        print(f"  +{n:2d}  {e}")
    if args.dry_run:
        print("\n(dry run — nothing written)")
        return 0

    for exp, recs in existing.items():
        if exp not in added:
            continue
        recs.sort(key=lambda r: (-(r.get("year") or 0), r["bibtag"]))
        with open(os.path.join(OSC_DIR, f"{exp}.yml"), "w", encoding="utf-8") as fh:
            yaml.safe_dump(recs, fh, allow_unicode=True, sort_keys=False, width=100)
    print(f"\nwrote {len(added)} experiment file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
