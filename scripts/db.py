"""Helpers for reading and writing the NuIntBib YAML database (data/papers/*.yml)."""
from __future__ import annotations

import glob
import os
from typing import Dict, List

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAPERS_DIR = os.path.join(ROOT, "data", "papers")


def load_db() -> List[dict]:
    records: List[dict] = []
    for path in sorted(glob.glob(os.path.join(PAPERS_DIR, "*.yml"))):
        with open(path, encoding="utf-8") as fh:
            for rec in yaml.safe_load(fh) or []:
                records.append(rec)
    return records


def known_bibtags(records: List[dict] | None = None) -> set:
    records = records if records is not None else load_db()
    return {r["bibtag"] for r in records}


def known_arxivs(records: List[dict] | None = None) -> set:
    records = records if records is not None else load_db()
    return {r["arxiv"] for r in records if r.get("arxiv")}


def latest_published_date(records: List[dict] | None = None) -> str | None:
    records = records if records is not None else load_db()
    dates = sorted(r["published_date"] for r in records if r.get("published_date"))
    return dates[-1] if dates else None


def write_experiment(experiment: str, records: List[dict]) -> str:
    """Write (overwrite) one experiment file, newest first."""
    records = sorted(records, key=lambda r: (-(r.get("year") or 0), r["bibtag"]))
    path = os.path.join(PAPERS_DIR, f"{experiment}.yml")
    os.makedirs(PAPERS_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(records, fh, allow_unicode=True, sort_keys=False, width=100)
    return path


def append_records(new_records: List[dict]) -> Dict[str, int]:
    """Merge new records into their experiment files (skipping existing bibtags)."""
    existing = load_db()
    have = known_bibtags(existing)
    by_exp: Dict[str, List[dict]] = {}
    for r in existing:
        by_exp.setdefault(r["collaboration"], []).append(r)

    added: Dict[str, int] = {}
    for rec in new_records:
        if rec["bibtag"] in have:
            continue
        exp = rec["collaboration"]
        by_exp.setdefault(exp, []).append(rec)
        have.add(rec["bibtag"])
        added[exp] = added.get(exp, 0) + 1

    for exp in added:
        write_experiment(exp, by_exp[exp])
    return added
