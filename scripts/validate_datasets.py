#!/usr/bin/env python
"""Validate the built data-release JSONs. Exits non-zero on any error so the build
fails loudly instead of shipping a broken release (wrong source link, covariance
that doesn't match the errors, placeholder URLs, empty distributions, ...).

Run:  python scripts/validate_datasets.py   (build_datasets.py runs it automatically)
"""
import glob
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, 'data', 'datasets', 'nuisance')

# source label keyword -> domain substring its link MUST contain
SOURCE_DOMAINS = {
    'nuisance': 'github.com/nuisancemc',
    'zenodo': 'zenodo.org',
    't2k.org': 't2k-experiment.org',
    'arxiv': 'arxiv.org',
    'hepdata': 'hepdata.net',
}
PLACEHOLDERS = ('…', '...', 'TODO', 'FIXME', 'XXX', 'example.com')


def _host(url):
    """Coarse host key: scheme://domain/first-path-segment (e.g. github.com/NUISANCEMC,
    zenodo.org/records) — so different files under one release share a host."""
    parts = url.split('/')
    return '/'.join(parts[:4]).lower()


def _flatbins(d):
    bins = d.get('bins') or []
    if not bins and d.get('slices'):
        bins = [b for s in d['slices'] for b in s['bins']]
    return bins


def _expected_domain(source):
    s = source.lower()
    for kw, dom in SOURCE_DOMAINS.items():
        if kw in s:
            return dom
    # bare "T2K" (not "t2k.org") means the collaboration's public results site
    if 't2k' in s:
        return 't2k-experiment.org'
    return None


def validate(path):
    d = json.load(open(path))
    slug = os.path.basename(path)[:-5]
    errs = []

    # --- release-level source + link -------------------------------------------
    source = d.get('source', '')
    url = d.get('source_url', '')
    if not source:
        errs.append('missing release source')
    if not url:
        errs.append('missing release source_url')
    elif not url.startswith('http'):
        errs.append(f'source_url is not an http(s) URL: {url!r}')
    else:
        dom = _expected_domain(source)
        if dom and dom not in url.lower():
            errs.append(f'source "{source}" links to {url!r} (expected a {dom} URL)')

    dists = d.get('distributions', [])
    if not dists:
        errs.append('no distributions')

    # every distribution: non-empty, well-formed source link, no placeholders
    hosts = set()
    for x in dists:
        key = x.get('key', '?')
        if not _flatbins(x):
            errs.append(f'distribution {key!r} has no bins')
        if x.get('nbins', 0) <= 0:
            errs.append(f'distribution {key!r} has nbins={x.get("nbins")}')
        su = x.get('source_url', '')
        if su:
            hosts.add(_host(su))
        for field in ('source_url', 'nuisance_file', 'provenance'):
            v = str(x.get(field, ''))
            for ph in PLACEHOLDERS:
                if ph in v:
                    errs.append(f'distribution {key!r} {field} contains placeholder {ph!r}: {v!r}')
    # all distributions in a release must live on one host (different files are fine)
    if len(hosts) > 1:
        errs.append(f'distributions span multiple hosts: {sorted(hosts)}')
    if hosts and url and _host(url) not in hosts:
        errs.append(f'release link host {_host(url)!r} differs from distributions {sorted(hosts)}')

    # --- covariance ------------------------------------------------------------
    cov = d.get('covariance')
    if cov:
        M = cov.get('matrix', [])
        n = len(M)
        order = cov.get('order', [])
        flat = [b for x in dists for b in _flatbins(x)]
        if any(len(row) != n for row in M):
            errs.append('covariance matrix is not square')
        elif n != len(flat):
            errs.append(f'covariance is {n}x{n} but there are {len(flat)} bins')
        else:
            if len(order) != n:
                errs.append(f'covariance order has {len(order)} labels for {n} rows')
            # symmetric + finite
            asym = any(abs(M[i][j] - M[j][i]) > 1e-9 * (abs(M[i][j]) + abs(M[j][i]) + 1e-30)
                       for i in range(n) for j in range(i + 1, n))
            if asym:
                errs.append('covariance is not symmetric')
            if any(not math.isfinite(v) for row in M for v in row):
                errs.append('covariance has non-finite entries')
            # sqrt(diag) must reproduce the reported per-bin errors
            ratios = []
            for i, b in enumerate(flat):
                e = b.get('err', 0)
                if e > 0 and M[i][i] > 0:
                    ratios.append(math.sqrt(M[i][i]) / e)
            if ratios:
                ratios.sort()
                med = ratios[len(ratios) // 2]
                if not 0.9 < med < 1.1:
                    errs.append(f'covariance sqrt(diag)/err median = {med:.3f} (expected ~1)')

    # --- flux ------------------------------------------------------------------
    flux = d.get('flux')
    if flux:
        cols = flux.get('columns', [])
        rows = flux.get('rows', [])
        if len(cols) < 3:
            errs.append(f'flux has too few columns: {cols}')
        if not rows:
            errs.append('flux has no rows')
        elif any(len(r) != len(cols) for r in rows):
            errs.append('flux rows are ragged (row width != #columns)')
        else:
            edges = [r[0] for r in rows] + [rows[-1][1]]
            if any(edges[i + 1] < edges[i] for i in range(len(edges) - 1)):
                errs.append('flux energy edges are not monotonic')

    return slug, errs


def main():
    files = sorted(glob.glob(os.path.join(OUT_DIR, '*.json')))
    total_err = 0
    for f in files:
        slug, errs = validate(f)
        if errs:
            total_err += len(errs)
            print(f'✗ {slug}')
            for e in errs:
                print(f'    - {e}')
        else:
            print(f'✓ {slug}')
    print()
    if total_err:
        print(f'VALIDATION FAILED: {total_err} problem(s) across {len(files)} releases')
        sys.exit(1)
    print(f'All {len(files)} releases valid.')


if __name__ == '__main__':
    main()
