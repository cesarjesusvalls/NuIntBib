#!/usr/bin/env python3
"""Fetch complete BibTeX from INSPIRE for every paper that isn't already in one
of the hand-curated *.bib files (the 2024-2026 update-workflow additions).

The site's synthBibtex() only knows the YAML fields (collaboration/title/eprint/
journal/year), so those papers render an incomplete citation missing author,
archivePrefix/primaryClass, reportNumber, month.  INSPIRE has the full entry.
We write them to inspire_added.bib in the repo root, which lib/papers.ts already
indexes (keyed by texkey == bibtag), so the complete entry wins over synthBibtex.

    python scripts/fetch_bibtex.py
"""
import glob, os, re, sys, time, urllib.request
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'inspire_added.bib')

# texkeys already covered by the hand-curated .bib files
bibkeys = set()
for f in glob.glob(os.path.join(ROOT, '*.bib')):
    if os.path.basename(f) == 'inspire_added.bib':
        continue
    for m in re.finditer(r'@\w+\s*\{\s*([^,]+),', open(f).read()):
        bibkeys.add(m.group(1).strip())

papers = []
for sub in ('papers', 'oscillation'):            # interactions + oscillations
    for f in glob.glob(os.path.join(ROOT, 'data', sub, '*.yml')):
        papers += yaml.safe_load(open(f)) or []
# de-dupe by bibtag (a paper can appear in both clusters)
seen, uniq = set(), []
for p in papers:
    if p['bibtag'] not in seen:
        seen.add(p['bibtag'])
        uniq.append(p)
missing = [p for p in uniq if p['bibtag'] not in bibkeys and p.get('inspire_recid')]
print(f"{len(missing)} papers (interactions + oscillations) need BibTeX from INSPIRE")


def fetch_bibtex(recid):
    req = urllib.request.Request(
        f"https://inspirehep.net/api/literature/{recid}",
        headers={'Accept': 'application/x-bibtex', 'User-Agent': 'nubib/1.0'})
    return urllib.request.urlopen(req, timeout=30).read().decode('utf-8').strip()


entries, failed = [], []
for i, p in enumerate(missing):
    try:
        bt = fetch_bibtex(p['inspire_recid'])
        # ensure the texkey matches the bibtag so indexBibtex keys it correctly
        key = re.match(r'@\w+\s*\{\s*([^,]+),', bt)
        if key and key.group(1).strip() != p['bibtag']:
            bt = re.sub(r'(@\w+\s*\{\s*)[^,]+,', r'\g<1>' + p['bibtag'] + ',', bt, count=1)
        entries.append(bt)
    except Exception as e:
        failed.append((p['bibtag'], str(e)))
    if (i + 1) % 20 == 0:
        print(f"  ...{i + 1}/{len(missing)}")
    time.sleep(0.34)                     # be polite to INSPIRE

header = ("% Auto-fetched from INSPIRE-HEP for papers added via the update workflow\n"
          "% and not present in the hand-curated *.bib files. Regenerate with:\n"
          "%   python scripts/fetch_bibtex.py\n\n")
open(OUT, 'w').write(header + '\n\n'.join(entries) + '\n')
print(f"wrote {len(entries)} entries -> {os.path.relpath(OUT, ROOT)}")
if failed:
    print(f"FAILED ({len(failed)}):")
    for bt, e in failed:
        print(f"  {bt}: {e}")
