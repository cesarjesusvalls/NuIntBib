"""Tiny INSPIRE-HEP literature client with on-disk caching.

Used both for enriching the migrated database and for the update workflow.
Responses are cached under .cache/inspire/ (gitignored) so re-runs are cheap and
polite to the public API. No authentication required.

API docs: https://github.com/inspirehep/rest-api-doc
"""
from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from typing import Dict, List, Optional

API = "https://inspirehep.net/api"
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".cache", "inspire")
USER_AGENT = "NuIntBib/0.1 (https://github.com/cesarjesusvalls/NuIntBib; neutrino cross-section bibliography)"
FIELDS = ",".join([
    "control_number", "titles", "abstracts", "publication_info",
    "arxiv_eprints", "dois", "preprint_date", "earliest_date",
    "citation_count", "collaborations", "authors", "texkeys",
    "document_type", "number_of_pages",
])

_last_call = [0.0]
MIN_INTERVAL = 1.0  # seconds between live API calls


def _cache_path(tag: str) -> str:
    safe = urllib.parse.quote(tag, safe="")
    return os.path.join(CACHE_DIR, safe + ".json")


def _throttle():
    dt = time.time() - _last_call[0]
    if dt < MIN_INTERVAL:
        time.sleep(MIN_INTERVAL - dt)
    _last_call[0] = time.time()


def _get(url: str) -> Optional[dict]:
    _throttle()
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except Exception as e:  # noqa: BLE001
        print(f"  ! INSPIRE request failed: {e}")
        return None


def fetch_record(*, arxiv: Optional[str] = None, texkey: Optional[str] = None,
                 use_cache: bool = True) -> Optional[dict]:
    """Return the raw INSPIRE `metadata` object for a paper, or None.

    Looks up by arXiv id when available (most reliable), else by texkey.
    """
    tag = (arxiv and f"arxiv:{arxiv}") or (texkey and f"texkey:{texkey}")
    if not tag:
        return None
    cp = _cache_path(tag)
    if use_cache and os.path.exists(cp):
        with open(cp, encoding="utf-8") as fh:
            return json.load(fh)

    meta = None
    if arxiv:
        clean = arxiv.split("v")[0]
        data = _get(f"{API}/arxiv/{clean}")
        if data:
            meta = data.get("metadata", data)
    if meta is None and texkey:
        q = urllib.parse.quote(f'texkeys.raw:"{texkey}"')
        data = _get(f"{API}/literature?q={q}&fields={FIELDS}&size=1")
        hits = (data or {}).get("hits", {}).get("hits", [])
        if hits:
            meta = hits[0].get("metadata")

    if meta is not None:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(cp, "w", encoding="utf-8") as fh:
            json.dump(meta, fh, ensure_ascii=False)
    return meta


def search(query: str, *, size: int = 100, sort: str = "mostrecent",
           use_cache: bool = True) -> List[dict]:
    """Run an INSPIRE literature search and return the list of `metadata` objects."""
    import hashlib

    key = "search:" + hashlib.sha1(f"{query}|{size}|{sort}".encode()).hexdigest()[:16]
    cp = _cache_path(key)
    if use_cache and os.path.exists(cp):
        with open(cp, encoding="utf-8") as fh:
            return json.load(fh)

    q = urllib.parse.quote(query)
    url = f"{API}/literature?q={q}&fields={FIELDS}&size={size}&sort={sort}"
    data = _get(url)
    hits = [h.get("metadata", {}) for h in (data or {}).get("hits", {}).get("hits", [])]
    if data is not None:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(cp, "w", encoding="utf-8") as fh:
            json.dump(hits, fh, ensure_ascii=False)
    return hits


def normalize(meta: dict) -> Dict:
    """Extract the bibliographic fields NuIntBib cares about from INSPIRE metadata."""
    out: Dict = {
        "inspire_recid": meta.get("control_number"),
        "title": None, "abstract": None, "arxiv": None, "doi": None,
        "journal": None, "volume": None, "pages": None, "year": None,
        "published_date": None, "citation_count": meta.get("citation_count"),
        "collaboration": None, "bibtag": None,
        "document_type": meta.get("document_type") or [],
    }
    titles = meta.get("titles") or []
    if titles:
        out["title"] = titles[0].get("title")
    abstracts = meta.get("abstracts") or []
    if abstracts:
        # prefer the arXiv abstract, else the longest
        arx = [a for a in abstracts if (a.get("source") or "").lower() == "arxiv"]
        chosen = arx[0] if arx else max(abstracts, key=lambda a: len(a.get("value") or ""))
        out["abstract"] = chosen.get("value")
    eprints = meta.get("arxiv_eprints") or []
    if eprints:
        out["arxiv"] = eprints[0].get("value")
    dois = meta.get("dois") or []
    if dois:
        out["doi"] = dois[0].get("value")
    pubs = meta.get("publication_info") or []
    pub = next((p for p in pubs if p.get("journal_title")), None)
    if pub:
        out["journal"] = pub.get("journal_title")
        out["volume"] = str(pub["journal_volume"]) if pub.get("journal_volume") else None
        page = pub.get("page_start") or pub.get("artid")
        out["pages"] = str(page) if page else None
        if pub.get("year"):
            out["year"] = int(pub["year"])
    date = meta.get("earliest_date") or meta.get("preprint_date")
    if date:
        out["published_date"] = date[:10] if len(date) >= 10 else date
        if not out["year"]:
            try:
                out["year"] = int(date[:4])
            except ValueError:
                pass
    collabs = meta.get("collaborations") or []
    if collabs:
        out["collaboration"] = collabs[0].get("value")
    texkeys = meta.get("texkeys") or []
    if texkeys:
        out["bibtag"] = texkeys[0]
    return out


if __name__ == "__main__":
    import sys
    meta = fetch_record(arxiv=sys.argv[1] if len(sys.argv) > 1 else "1302.4908")
    print(json.dumps(normalize(meta), indent=2, ensure_ascii=False) if meta else "not found")
