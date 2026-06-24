#!/usr/bin/env python3
"""Discover neutrino cross-section papers not yet in the NuIntBib database.

Queries INSPIRE-HEP per collaboration for recent "cross section" papers, drops
anything already tracked, and writes candidate stubs to data/candidates.yml with
an empty `measurements` list for the maintainer/agent to classify.

Usage:
  scripts/find_new_papers.py                 # since (latest tracked date - 180d)
  scripts/find_new_papers.py --since 2024-01-01
  scripts/find_new_papers.py --collaborations T2K MINERvA
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db  # noqa: E402
import inspire  # noqa: E402

# Collaborations we track plus active/upcoming ones worth watching.
COLLABORATIONS = [
    "T2K", "MINERvA", "MicroBooNE", "MiniBooNE", "NOvA", "ArgoNeuT", "NOMAD",
    "K2K", "MINOS", "SciBooNE", "NINJA", "Super-Kamiokande", "FASER",
    # forward-looking / newer (note: use "SND@LHC", NOT "SND" which is the
    # Novosibirsk e+e- experiment and pollutes the results)
    "SBND", "ICARUS", "ANNIE", "DUNE", "SND@LHC", "WAGASCI",
    # high-energy DIS-era experiments
    "NuTeV", "CCFR", "CDHSW", "CDHS", "CHARM", "CHARM-II", "CHORUS", "IHEP-JINR",
]

# Topic terms that flag an experimental cross-section measurement.
TOPIC = '("cross section" or "cross-section")'


def default_since(records) -> str:
    latest = db.latest_published_date(records)
    if not latest:
        return "2000-01-01"
    d = dt.date.fromisoformat(latest) - dt.timedelta(days=180)
    return d.isoformat()


def is_proceeding(meta: dict) -> bool:
    """True for conference papers / theses (we track only journal articles)."""
    dtypes = [d.lower() for d in (meta.get("document_type") or [])]
    if dtypes and "article" not in dtypes:
        return True
    journal = ""
    for p in meta.get("publication_info") or []:
        if p.get("journal_title"):
            journal = p["journal_title"]
            break
    return journal.startswith(("PoS", "J.Phys.Conf.Ser", "AIP Conf.Proc", "EPJ Web Conf", "Conf.Proc"))


def candidate_from_meta(meta: dict) -> dict:
    n = inspire.normalize(meta)
    bibtag = n.get("bibtag")
    if not bibtag:
        return {}
    arxiv = n.get("arxiv")
    prefix = bibtag.split(":")[0]
    dtype = n.get("document_type") or []
    if is_proceeding(meta):
        triage = (
            "PROCEEDING/thesis, include ONLY if no journal article covers the same "
            "result (see UPDATE.md). Check for a matching article first."
        )
    elif prefix in COLLABORATIONS:
        triage = "collaboration-keyed article (likely a real measurement)"
    else:
        triage = "author-keyed article (verify it is a measurement, not theory)"
    return {
        "_triage": triage,
        "_document_type": dtype,
        "bibtag": bibtag,
        "title": n.get("title") or bibtag,
        "collaboration": n.get("collaboration") or bibtag.split(":")[0],
        "arxiv": arxiv,
        "doi": n.get("doi"),
        "journal": n.get("journal"),
        "volume": n.get("volume"),
        "pages": n.get("pages"),
        "year": n.get("year"),
        "published_date": n.get("published_date"),
        "inspire_recid": n.get("inspire_recid"),
        "citation_count": n.get("citation_count"),
        "abstract": n.get("abstract"),
        "added": dt.date.today().isoformat(),
        "notes": None,
        "links": {
            "arxiv": f"https://arxiv.org/abs/{arxiv}" if arxiv else None,
            "doi": f"https://doi.org/{n['doi']}" if n.get("doi") else None,
            "inspire": f"https://inspirehep.net/literature?q=texkeys.raw:{bibtag}",
        },
        # to be filled by the classification step (see UPDATE.md)
        "measurements": [],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", help="ISO date lower bound (default: latest tracked - 180d)")
    ap.add_argument("--collaborations", nargs="*", help="subset of collaborations to query")
    ap.add_argument("--size", type=int, default=80, help="max hits per collaboration")
    ap.add_argument("--out", default=os.path.join(db.ROOT, "data", "candidates.yml"))
    args = ap.parse_args()

    records = db.load_db()
    known_tags = db.known_bibtags(records)
    known_arxiv = db.known_arxivs(records)
    since = args.since or default_since(records)
    collabs = args.collaborations or COLLABORATIONS

    print(f"Known papers: {len(known_tags)}  |  searching since {since}")
    candidates: dict[str, dict] = {}
    for c in collabs:
        query = f"collaboration {c} and {TOPIC} and de >= {since}"
        hits = inspire.search(query, size=args.size)
        fresh = 0
        for meta in hits:
            cand = candidate_from_meta(meta)
            tag = cand.get("bibtag")
            if not tag or tag in known_tags or tag in candidates:
                continue
            if cand.get("arxiv") and cand["arxiv"] in known_arxiv:
                continue
            candidates[tag] = cand
            fresh += 1
        print(f"  {c:16} {len(hits):3d} hits  ->  {fresh} new")

    out_list = sorted(candidates.values(), key=lambda r: (r.get("published_date") or "", r["bibtag"]))
    with open(args.out, "w", encoding="utf-8") as fh:
        yaml.safe_dump(out_list, fh, allow_unicode=True, sort_keys=False, width=100)

    print(f"\n{len(out_list)} candidate(s) -> {os.path.relpath(args.out, db.ROOT)}")
    if out_list:
        print("\nNext: classify each candidate's `measurements` (see UPDATE.md), then run")
        print("  scripts/add_papers.py --from data/candidates.yml")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
