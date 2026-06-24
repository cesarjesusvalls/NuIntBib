#!/usr/bin/env python3
"""Audit conference proceedings / theses in the database.

Policy (see UPDATE.md): we keep journal articles for measurements. A proceeding
is kept ONLY when no journal article reports the same result; if a matching
article exists (the common "proceeding-while-the-analysis-is-ongoing, article
later" pattern), we keep the article and drop the proceeding.

This tool finds proceeding/thesis records, searches INSPIRE for a matching
article, and labels each SUPERSEDED (article exists) or STANDALONE (keep).

Usage:
  scripts/audit_proceedings.py            # report
  scripts/audit_proceedings.py --remove   # drop only SUPERSEDED proceedings, validate
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db  # noqa: E402
import inspire  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PROCEEDING_TYPES = {"conference paper", "proceedings", "thesis", "report",
                    "activity report", "lectures", "note"}
PROCEEDING_VENUES = ("PoS", "J.Phys.Conf.Ser", "AIP Conf.Proc", "EPJ Web Conf", "Conf.Proc")
STOP = {"measurement", "measurements", "cross", "section", "sections", "neutrino",
        "neutrinos", "antineutrino", "study", "using", "induced", "interactions",
        "interaction", "scattering", "results", "recent", "production", "experiment"}


def is_proceeding(meta: dict) -> bool:
    dtypes = [d.lower() for d in (meta.get("document_type") or [])]
    if dtypes and "article" not in dtypes and any(t in dtypes for t in PROCEEDING_TYPES):
        return True
    n = inspire.normalize(meta)
    return (n.get("journal") or "").startswith(PROCEEDING_VENUES)


def terms(title: str) -> set:
    t = re.sub(r"[^a-z0-9 ]", " ", (title or "").lower())
    return {w for w in t.split() if len(w) > 3 and w not in STOP}


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if (a | b) else 0.0


def find_matching_article(meta: dict):
    """Search INSPIRE for a journal article reporting the same result. Returns
    (normalized_article, similarity) or None."""
    n = inspire.normalize(meta)
    tt = terms(n.get("title") or "")
    if not tt:
        return None
    qparts = ["document_type article"]
    if n.get("collaboration"):
        qparts.append(f'collaboration {n["collaboration"]}')
    qparts.append("(" + " or ".join(f"title {w}" for w in list(tt)[:6]) + ")")
    hits = inspire.search(" and ".join(qparts), size=25)
    best = None
    for h in hits:
        hn = inspire.normalize(h)
        if hn.get("inspire_recid") == n.get("inspire_recid"):
            continue
        if "article" not in [d.lower() for d in (h.get("document_type") or [])]:
            continue
        sim = jaccard(tt, terms(hn.get("title") or ""))
        if sim >= 0.6 and (best is None or sim > best[1]):
            best = (hn, sim)
    return best


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--remove", action="store_true", help="drop SUPERSEDED proceedings")
    args = ap.parse_args()

    records = db.load_db()
    superseded, standalone = [], []
    for rec in records:
        meta = inspire.fetch_record(arxiv=rec.get("arxiv"), texkey=rec["bibtag"])
        if not meta or not is_proceeding(meta):
            continue
        match = find_matching_article(meta)
        if match:
            art, sim = match
            superseded.append((rec, art))
            print(f"  SUPERSEDED  {rec['bibtag']:26} -> article {art.get('bibtag')} "
                  f"(recid {art.get('inspire_recid')}, sim {sim:.2f})")
            print(f"              {(rec.get('title') or '')[:78]}")
        else:
            standalone.append(rec)
            print(f"  STANDALONE  {rec['bibtag']:26} {rec.get('year')}  (no matching article, keep)")

    print(f"\n{len(superseded)} superseded, {len(standalone)} standalone "
          f"proceeding(s) among {len(records)} records")
    if not superseded or not args.remove:
        if superseded and not args.remove:
            print("Re-run with --remove to drop the superseded ones.")
        return 0

    drop = {r["bibtag"] for r, _ in superseded}
    by_exp: dict[str, list] = {}
    for r in records:
        if r["bibtag"] not in drop:
            by_exp.setdefault(r["collaboration"], []).append(r)
    for exp in {r["collaboration"] for r, _ in superseded}:
        db.write_experiment(exp, by_exp.get(exp, []))
        if not by_exp.get(exp):
            p = os.path.join(db.PAPERS_DIR, f"{exp}.yml")
            os.path.exists(p) and os.remove(p)
    print(f"Removed {len(drop)} superseded proceeding(s). Validating…")
    return subprocess.run([sys.executable, os.path.join(HERE, "validate.py")]).returncode


if __name__ == "__main__":
    raise SystemExit(main())
