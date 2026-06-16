#!/usr/bin/env python3
"""Build the structured NuIntBib database from the legacy sources.

Merges, per paper:
  * bibliographic fields from the *.bib files,
  * the hand classification from data/legacy_classification.json
    (frozen copy of PaperFeatures.ipynb's `paper_features`),
  * live enrichment from INSPIRE-HEP (recid, date, abstract, citations).

Writes one YAML file per experiment under data/papers/.

Usage:
  scripts/migrate.py                 # enrich via INSPIRE (cached)
  scripts/migrate.py --no-enrich     # bib + classification only (offline)
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bibparse  # noqa: E402
import classify  # noqa: E402
import inspire  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADDED_DATE = "2024-12-09"  # date the legacy NuIntBib collection was last curated


def clean_title(t: str) -> str:
    return (t or "").replace("{", "").replace("}", "").strip()


def experiment_of(bibtag: str, bib_entry, inspire_collab) -> str:
    if inspire_collab:
        return inspire_collab
    if bib_entry and bib_entry.get("collaboration"):
        return bib_entry["collaboration"]
    return bibtag.split(":")[0]


def build_record(bibtag, tup, bib_entry, meta, enrich) -> dict:
    norm = inspire.normalize(meta) if (enrich and meta) else {}
    bib = bib_entry or {}

    title = norm.get("title") or clean_title(bib.get("title")) or bibtag
    arxiv = norm.get("arxiv") or bib.get("eprint")
    doi = norm.get("doi") or bib.get("doi")
    journal = norm.get("journal") or bib.get("journal")
    volume = norm.get("volume") or bib.get("volume")
    pages = norm.get("pages") or bib.get("pages")
    year = norm.get("year") or (int(bib["year"]) if bib.get("year", "").isdigit() else None)
    collab = experiment_of(bibtag, bib, norm.get("collaboration"))

    links = {
        "arxiv": f"https://arxiv.org/abs/{arxiv}" if arxiv else None,
        "doi": f"https://doi.org/{doi}" if doi else None,
        "inspire": f"https://inspirehep.net/literature?q=texkeys.raw:{bibtag}",
    }

    record = {
        "bibtag": bibtag,
        "title": title,
        "collaboration": collab,
        "arxiv": arxiv,
        "doi": doi,
        "journal": journal,
        "volume": volume,
        "pages": pages,
        "year": year,
        "published_date": norm.get("published_date"),
        "inspire_recid": norm.get("inspire_recid"),
        "citation_count": norm.get("citation_count"),
        "abstract": norm.get("abstract"),
        "added": ADDED_DATE,
        "notes": None,
        "links": links,
        "measurements": [classify.build_measurement(tup)],
    }
    return record


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-enrich", action="store_true", help="skip INSPIRE enrichment")
    args = ap.parse_args()
    enrich = not args.no_enrich

    bib = bibparse.load_bib_dir(ROOT)
    with open(os.path.join(ROOT, "data", "legacy_classification.json"), encoding="utf-8") as fh:
        legacy = json.load(fh)

    bibtags = sorted(set(bib) | set(legacy))
    print(f"{len(bibtags)} papers ({len(bib)} bib / {len(legacy)} classified); enrich={enrich}")

    by_experiment: dict[str, list] = {}
    missing_class, missing_bib = [], []
    for i, tag in enumerate(bibtags, 1):
        tup = legacy.get(tag)
        if tup is None:
            missing_class.append(tag)
            continue  # cannot build measurements without classification
        entry = bib.get(tag)
        if entry is None:
            missing_bib.append(tag)
        meta = None
        if enrich:
            arxiv = (entry or {}).get("eprint")
            print(f"  [{i}/{len(bibtags)}] {tag}")
            meta = inspire.fetch_record(arxiv=arxiv, texkey=tag)
        rec = build_record(tag, tup, entry, meta, enrich)
        by_experiment.setdefault(rec["collaboration"], []).append(rec)

    os.makedirs(os.path.join(ROOT, "data", "papers"), exist_ok=True)
    total = 0
    for exp, recs in sorted(by_experiment.items()):
        recs.sort(key=lambda r: (-(r["year"] or 0), r["bibtag"]))
        path = os.path.join(ROOT, "data", "papers", f"{exp}.yml")
        with open(path, "w", encoding="utf-8") as fh:
            yaml.safe_dump(recs, fh, allow_unicode=True, sort_keys=False, width=100)
        total += len(recs)
        print(f"  wrote {len(recs):2d} -> data/papers/{exp}.yml")

    print(f"\n{total} records across {len(by_experiment)} experiments")
    if missing_class:
        print(f"WARNING: {len(missing_class)} bib entries without classification: {missing_class}")
    if missing_bib:
        print(f"NOTE: {len(missing_bib)} classified entries without a bib entry: {missing_bib}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
