#!/usr/bin/env python3
"""Merge classified candidate papers into the NuIntBib database.

Reads a candidates file (default data/candidates.yml) whose records each have a
non-empty `measurements` list, appends new ones to data/papers/<exp>.yml, and
re-runs schema validation. Candidates with no measurements are skipped (they
still need classification — see UPDATE.md).

A measurement may be given either as a structured object or as a legacy 6-tuple
[topology, target, current, flavor, observables, energy]; tuples are normalized.

Usage:
  scripts/add_papers.py --from data/candidates.yml
  scripts/add_papers.py --from data/candidates.yml --dry-run
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import classify  # noqa: E402
import db  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def normalize_measurements(rec: dict) -> list:
    out = []
    for m in rec.get("measurements") or []:
        out.append(classify.build_measurement(m) if isinstance(m, list) else m)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="src", default=os.path.join(db.ROOT, "data", "candidates.yml"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(args.src):
        print(f"No candidates file at {args.src}")
        return 1
    with open(args.src, encoding="utf-8") as fh:
        candidates = yaml.safe_load(fh) or []

    known = db.known_bibtags()
    ready, skipped_class, skipped_dup = [], [], []
    for rec in candidates:
        for k in [k for k in rec if k.startswith("_")]:
            rec.pop(k)
        if rec["bibtag"] in known:
            skipped_dup.append(rec["bibtag"])
            continue
        rec["measurements"] = normalize_measurements(rec)
        if not rec["measurements"]:
            skipped_class.append(rec["bibtag"])
            continue
        ready.append(rec)

    print(f"{len(ready)} ready to add, {len(skipped_class)} unclassified, {len(skipped_dup)} already present")
    if skipped_class:
        print(f"  needs classification: {skipped_class}")
    if not ready:
        return 0
    for rec in ready:
        ms = ", ".join(f"{m['current']}/{m['topology']}" for m in rec["measurements"])
        print(f"  + {rec['bibtag']:22} {rec.get('year')}  [{ms}]")

    if args.dry_run:
        print("\n(dry run — nothing written)")
        return 0

    added = db.append_records(ready)
    print(f"\nAdded: " + ", ".join(f"{k}+{v}" for k, v in added.items()))

    print("Validating…")
    r = subprocess.run([sys.executable, os.path.join(HERE, "validate.py")])
    return r.returncode


if __name__ == "__main__":
    raise SystemExit(main())
