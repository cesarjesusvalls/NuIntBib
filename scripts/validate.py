#!/usr/bin/env python3
"""Validate every data/papers/*.yml record against schemas/paper.schema.json.

Also checks database-level invariants: unique bibtags and required enrichment.
Exit code is non-zero on any error, so it can gate CI and the update workflow.
"""
from __future__ import annotations

import glob
import os
import sys

import yaml
from jsonschema import Draft202012Validator

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_all():
    records = []
    for path in sorted(glob.glob(os.path.join(ROOT, "data", "papers", "*.yml"))):
        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or []
        for rec in data:
            records.append((os.path.basename(path), rec))
    return records


def main() -> int:
    with open(os.path.join(ROOT, "schemas", "paper.schema.json"), encoding="utf-8") as fh:
        schema = yaml.safe_load(fh)
    validator = Draft202012Validator(schema)

    records = load_all()
    errors = 0
    seen: dict[str, str] = {}
    for fname, rec in records:
        tag = rec.get("bibtag", "<no-bibtag>")
        for err in validator.iter_errors(rec):
            loc = "/".join(str(p) for p in err.path)
            print(f"  SCHEMA  {fname}:{tag} [{loc}] {err.message}")
            errors += 1
        if tag in seen:
            print(f"  DUP     {tag} in {fname} and {seen[tag]}")
            errors += 1
        seen[tag] = fname

    print(f"\n{len(records)} records validated, {errors} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
