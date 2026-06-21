#!/usr/bin/env python3
"""Discover neutrino-oscillation measurement papers not yet in the oscillation cluster.

Independent of the interaction pipeline: queries INSPIRE-HEP per oscillation
collaboration, drops anything already in data/oscillation/, and writes candidate
stubs to data/osc_candidates.yml with an empty `measurements` list for the
maintainer/agent to classify (source, framework, channels, parameters).

Usage:
  scripts/find_osc_papers.py
  scripts/find_osc_papers.py --since 1985-01-01 --collaborations T2K NOvA
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import os
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import inspire  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OSC_DIR = os.path.join(ROOT, "data", "oscillation")

# Experiments whose published oscillation measurements we want to track.
COLLABORATIONS = [
    # accelerator
    "T2K", "NOvA", "MINOS", "MINOS+", "K2K", "OPERA", "ICARUS",
    "MiniBooNE", "MicroBooNE", "LSND",
    # reactor
    "KamLAND", "Daya Bay", "RENO", "Double Chooz",
    "STEREO", "PROSPECT", "DANSS", "NEOS", "Neutrino-4",
    # atmospheric / astrophysical
    "Super-Kamiokande", "IceCube", "ANTARES", "KM3NeT",
    # solar
    "SNO", "Borexino", "GALLEX", "GNO", "SAGE", "Homestake",
]

# Topic terms that flag an oscillation result. Kept simple (INSPIRE's parser is
# finicky); finer filtering happens in Python / at classification time.
TOPIC = '(oscillation or "mixing angle" or "mass ordering")'


def known_from_osc_db() -> tuple[set, set]:
    tags, arxivs = set(), set()
    for f in glob.glob(os.path.join(OSC_DIR, "*.yml")):
        for rec in yaml.safe_load(open(f, encoding="utf-8")) or []:
            tags.add(rec["bibtag"])
            if rec.get("arxiv"):
                arxivs.add(rec["arxiv"])
    return tags, arxivs


# Title signals that a paper is an oscillation-parameter measurement, and
# anti-signals that it belongs to another cluster or isn't a measurement.
OSC_TITLE_TERMS = (
    "oscillation", "mixing angle", "theta", "θ", "delta m", "mass-squared",
    "mass squared", "mass splitting", "appearance", "disappearance",
    "mass ordering", "mass hierarchy", "cp violation", "cp-violation",
    "leptonic cp", "matter-antimatter", "sterile", "survival probability",
    "neutrino mixing", "solar neutrino", "atmospheric neutrino",
)
NON_MEASUREMENT_TERMS = (
    "cross section", "cross-section", "sensitivity", "projected", "prospects for",
    "expected sensitivity", "calibration", "reconstruction", "simulation",
    "performance of", "detector response", "trigger", "future", "design",
    "supernova", "dark matter", "proton decay", "monte carlo",
    # proposals / non-results / other physics topics
    "proposal", "letter of intent", "technical design", "conceptual design",
    "majorana", "neutrinoless", "double beta", "double-beta", "0νββ",
    "magnetic moment", "geoneutrino", "geo-neutrino", "review",
)


# Collaboration-keyed texkey prefixes = real measurements; author-keyed bibtags
# (surname prefix) are proceedings/theses/talks and are dropped at discovery.
COLLAB_PREFIXES = {
    "T2K", "NOvA", "MINOS", "MINOS+", "K2K", "OPERA", "ICARUS", "MiniBooNE",
    "MicroBooNE", "LSND", "KamLAND", "DayaBay", "RENO", "DoubleChooz", "STEREO",
    "PROSPECT", "DANSS", "NEOS", "Neutrino-4", "NEUTRINO-4", "Super-Kamiokande",
    "IceCube", "IceCube-Gen2", "ANTARES", "KM3NeT", "SNO", "SNO+", "Borexino",
    "GALLEX", "GNO", "SAGE", "Homestake", "SciBooNE",
}


def looks_like_osc_measurement(title: str) -> bool:
    t = (title or "").lower()
    if any(x in t for x in NON_MEASUREMENT_TERMS):
        return False
    return any(x in t for x in OSC_TITLE_TERMS)


def is_proceeding(meta: dict) -> bool:
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
    triage = (
        "PROCEEDING/thesis — include ONLY if no journal article covers it"
        if is_proceeding(meta)
        else "article — verify it is an EXPERIMENTAL oscillation MEASUREMENT "
        "(not sensitivity/projection, not phenomenology/global-fit)"
    )
    return {
        "_triage": triage,
        "_document_type": n.get("document_type") or [],
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
        "measurements": [],  # filled at classification
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="1985-01-01", help="ISO date lower bound")
    ap.add_argument("--collaborations", nargs="*")
    ap.add_argument("--size", type=int, default=200, help="max hits per collaboration")
    ap.add_argument("--min-cites", type=int, default=0, help="drop hits below this citation count")
    ap.add_argument("--no-title-filter", action="store_true", help="skip the osc-measurement title gate")
    ap.add_argument("--out", default=os.path.join(ROOT, "data", "osc_candidates.yml"))
    args = ap.parse_args()

    known_tags, known_arxiv = known_from_osc_db()
    collabs = args.collaborations or COLLABORATIONS
    print(f"Known oscillation papers: {len(known_tags)}  |  searching since {args.since}")

    candidates: dict[str, dict] = {}
    for c in collabs:
        query = f'collaboration "{c}" and {TOPIC} and de >= {args.since}'
        try:
            hits = inspire.search(query, size=args.size)
        except Exception as e:  # noqa: BLE001
            print(f"  {c:18} ERROR {e}")
            continue
        fresh = 0
        for meta in hits:
            cand = candidate_from_meta(meta)
            tag = cand.get("bibtag")
            if not tag or tag in known_tags or tag in candidates:
                continue
            if cand.get("arxiv") and cand["arxiv"] in known_arxiv:
                continue
            if (cand.get("citation_count") or 0) < args.min_cites:
                continue
            if tag.split(":")[0] not in COLLAB_PREFIXES:
                continue  # author-keyed proceeding/thesis
            if not args.no_title_filter and not looks_like_osc_measurement(cand.get("title", "")):
                continue
            candidates[tag] = cand
            fresh += 1
        print(f"  {c:18} {len(hits):3d} hits  ->  {fresh} new")

    out_list = sorted(candidates.values(), key=lambda r: -(r.get("citation_count") or 0))
    with open(args.out, "w", encoding="utf-8") as fh:
        yaml.safe_dump(out_list, fh, allow_unicode=True, sort_keys=False, width=100)
    print(f"\n{len(out_list)} candidate(s) -> {os.path.relpath(args.out, ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
