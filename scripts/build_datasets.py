#!/usr/bin/env python3
"""Build NuBib 'data release' JSON from NUISANCE for the papers in REGISTRY.

Most NUISANCE data lives in ROOT files (official experiment releases: a TH1D
cross section + a TH2D covariance, with ROOT-LaTeX axis titles), some in text.
This ingests both, derives per-bin errors from sqrt(diag(covariance)), sanity-
checks the error scale, and writes data/datasets/nuisance/<slug>.json — the shape
the site's getDataRelease() reads.  Nothing is digitized: values come straight
from the release.

    python scripts/build_datasets.py            # all papers in REGISTRY
    python scripts/build_datasets.py t2k-2016cbz
"""
import json, os, re, sys, glob, urllib.request, math
import numpy as np
import uproot
import yaml

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT_DIR, 'data', 'datasets', 'nuisance')
CACHE = '/tmp/nuis_cache'
RAW = 'https://raw.githubusercontent.com/NUISANCEMC/nuisance/main/'
BLOB = 'https://github.com/NUISANCEMC/nuisance/blob/main/'
os.makedirs(CACHE, exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)

# paper metadata (arXiv + citation) comes from the NuBib database, keyed by bibtag
PAPERS = {}
for _f in glob.glob(os.path.join(ROOT_DIR, 'data', 'papers', '*.yml')):
    for _p in yaml.safe_load(open(_f)) or []:
        PAPERS[_p['bibtag']] = _p
def cite_of(bibtag):
    p = PAPERS.get(bibtag, {})
    cite = ' '.join(str(x) for x in [p.get('journal'), p.get('volume'), p.get('pages')] if x)
    return p.get('arxiv', ''), cite


def fetch(relpath):
    """Cache a file and return its local path. `relpath` is a NUISANCE-repo path,
    or a full https URL (e.g. a neutrino_data release file)."""
    url = relpath if relpath.startswith('http') else RAW + relpath
    local = os.path.join(CACHE, url.split('://', 1)[-1].replace('/', '__'))
    if not os.path.exists(local):
        urllib.request.urlretrieve(url, local)
    return local


# --- ROOT TLatex -> LaTeX ---------------------------------------------------
# each greek/command gets a TRAILING SPACE so a command glued to a following
# letter (ROOT's '#deltap_{T}') becomes '\delta p_{T}', not the bad '\deltap'.
_TL = {'#pi': r'\pi ', '#mu': r'\mu ', '#nu': r'\nu ', '#theta': r'\theta ',
       '#phi': r'\phi ', '#delta': r'\delta ', '#Delta': r'\Delta ',
       '#sigma': r'\sigma ', '#alpha': r'\alpha ', '#gamma': r'\gamma ',
       '#circ': r'^\circ ', '#bar{': r'\bar{', '#hat{': r'\hat{',
       '#times': r'\times ', '#pm': r'\pm ', '#frac': r'\frac'}
def tl(s):
    if not s:
        return ''
    for k, v in _TL.items():
        s = s.replace(k, v)
    s = s.replace('#', '\\')
    s = re.sub(r'\bcos\b', r'\\cos ', s)
    s = re.sub(r'\bsin\b', r'\\sin ', s)
    s = re.sub(r'\s+', ' ', s)                    # collapse whitespace
    s = re.sub(r'\s+([_^}),])', r'\1', s)         # drop space before delimiters
    return s.strip()


_UNIT = re.compile(r'GeV|MeV|rad|cm|Nucleon|neutron|nucleon|deg|/\s*c\b', re.I)
def _trailing_paren(s):
    """Content of the OUTERMOST balanced parentheses at the end of s (or None)."""
    s = s.rstrip()
    if not s.endswith(')'):
        return None, s
    depth = 0
    for i in range(len(s) - 1, -1, -1):
        depth += (s[i] == ')') - (s[i] == '(')
        if depth == 0:
            return s[i + 1:-1], s[:i]
    return None, s
def split_axis(title):
    """Split a ROOT axis title into (label_tex, unit). Trailing (balanced) parens
    are a unit ONLY if they contain unit tokens (else they're a qualifier like
    '(#Delta)')."""
    title = re.sub(r'\s+', ' ', title).strip()
    inner, head = _trailing_paren(title)
    if inner is not None and _UNIT.search(inner):      # unit in trailing parens
        return tl(head.strip()), tl(re.sub(r'\s+', ' ', inner).strip())
    if ' / ' in title:                                 # 'label / unit'
        h, tail = title.rsplit(' / ', 1)
        if _UNIT.search(tail):
            return tl(h.strip()), tl(tail.strip())
    return tl(title), ''


def plotify(tex):
    """LaTeX-ish -> compact unicode for the SVG axis labels."""
    return (tex.replace('\\mathrm', '').replace('{', '').replace('}', '')
            .replace('\\pi', 'π').replace('\\mu', 'μ').replace('\\nu', 'ν')
            .replace('\\theta', 'θ').replace('\\phi', 'φ').replace('\\delta', 'δ')
            .replace('\\sigma', 'σ').replace('\\cos', 'cos').replace('\\sin', 'sin')
            .replace('\\in', '∈').replace('\\times', '×').replace('\\,', ' ')
            .replace('\\', '')
            .replace('^2', '²').replace('^{2}', '²').replace('^3', '³').replace('^{3}', '³'))


# --- extract distributions from a ROOT file ---------------------------------
def _th1_bins(h):
    edges = h.axis().edges()
    vals = h.values()
    return edges, vals


def _distr_from(name, hres, hcov, relfile):
    edges, vals = _th1_bins(hres)
    cov = hcov.values()
    err = np.sqrt(np.clip(np.diag(cov), 0, None))
    scale_note = None
    # some NUISANCE result files store the covariance on a different power of ten
    # than the cross section. A relative error should sit near ~15%; if it's many
    # orders off, snap the covariance to the power of ten that lands it there.
    cov_scale = 1.0
    good = (np.abs(vals) > 0) & (err > 0)
    if good.any():
        ratio = np.median(err[good] / np.abs(vals[good]))
        if ratio > 0:
            m = round(math.log10(0.15 / ratio))
            if abs(m) >= 2:                 # gross unit mismatch, not a real error
                err = err * (10.0 ** m)
                cov_scale = 10.0 ** (2 * m)
                scale_note = f'covariance rescaled by 1e{m} to match cross-section units'
    xlab, xunit = split_axis(hres.member('fXaxis').member('fTitle'))
    ylab, yunit = split_axis(hres.member('fYaxis').member('fTitle'))
    bins = []
    for i in range(len(vals)):
        lo, hi = float(edges[i]), float(edges[i + 1])
        bins.append({'i': i, 'lo': lo, 'hi': hi, 'center': 0.5 * (lo + hi),
                     'val': float(vals[i]), 'err': float(err[i])})
    return {
        'key': name, 'slug': re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_'),
        'name': plotify(xlab), 'name_tex': f'${xlab}$',
        'xlabel': plotify(xlab), 'xunit': xunit,
        'ylabel': plotify(ylab), 'ylabel_plot': plotify(ylab),
        'ylabel_tex': f'${ylab}$' if ylab else '$\\mathrm{d}\\sigma$',
        'yunit': yunit, 'yunit_tex': f'${tl(yunit)}$' if yunit else '',
        'nbins': len(bins), 'bins': bins,
        'nuisance_file': relfile, 'scale_note': scale_note,
        '_cov': (np.asarray(cov) * cov_scale,
                 [f"{name} [{float(edges[i]):g},{float(edges[i + 1]):g}]"
                  for i in range(len(vals))]),
    }


def parse_edge_txt(relfile, labels):
    """Parse the simple NUISANCE 'x value error' text format, where x is the bin
    LOW edge and the final row (value 0) closes the last bin.  Labels are supplied
    (these files carry no axis titles)."""
    rows = []
    for line in open(fetch(relfile)):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        p = line.replace(',', ' ').split()
        try:
            rows.append((float(p[0]), float(p[1]), float(p[2])))
        except (ValueError, IndexError):
            continue
    if len(rows) < 2:
        return None
    bins = []
    for i in range(len(rows) - 1):
        lo, v, e = rows[i]
        hi = rows[i + 1][0]
        if v == 0:
            continue
        bins.append({'i': len(bins), 'lo': lo, 'hi': hi, 'center': 0.5 * (lo + hi),
                     'val': v, 'err': e})
    xl, yl = labels['xlabel'], labels['ylabel']
    xu, yu = labels.get('xunit', ''), labels.get('yunit', '')
    return {
        'key': labels['key'], 'slug': re.sub(r'[^a-z0-9]+', '_', labels['key'].lower()).strip('_'),
        'name': plotify(xl), 'name_tex': f'${xl}$', 'xlabel': plotify(xl), 'xunit': xu,
        'ylabel': plotify(yl), 'ylabel_plot': plotify(yl), 'ylabel_tex': f'${yl}$',
        'yunit': yu, 'yunit_tex': f'${tl(yu)}$' if yu else '',
        'nbins': len(bins), 'bins': bins, 'nuisance_file': relfile, 'scale_note': None,
    }


_ROW2D = re.compile(r'\s*(\d+)\s*\|\s*([-\d.]+)\s*-\s*([-\d.]+)\s*\|'
                    r'\s*([-\d.]+)\s*-\s*([-\d.]+)\s*\|\s*([-\d.eE]+)')
def build_2d_slices(spec):
    """A 2-D double-differential release, presented as sliced 1-D panels (one
    d(sigma)/dp per cos-theta slice).  Values from a flattened text table
    'bin | cos_lo-cos_hi | p_lo-p_hi | value'; per-bin errors from the diagonal
    of a covariance TH2D (same flattened order)."""
    rows = []
    for ln in open(fetch(spec['text'])):
        m = _ROW2D.match(ln)
        if m:
            rows.append(tuple(float(x) for x in m.groups()))
    Mfull = np.asarray(uproot.open(fetch(spec['cov']))[spec['cov_key']].values())
    err = np.sqrt(np.clip(np.diag(Mfull), 0, None))
    if len(err) != len(rows):
        raise ValueError(f"{spec['text']}: {len(rows)} rows vs {len(err)} cov bins")
    grouped, order = {}, []
    for (b, clo, chi, plo, phi, val), e in zip(rows, err):
        grouped.setdefault((clo, chi), []).append((plo, phi, val, e))
        order.append(f"cos[{clo:g},{chi:g}] p[{plo:g},{phi:g}]")
    out = _assemble_2d(grouped, spec)
    if out:
        out[0]['_release_cov'] = _cov_obj(Mfull, order, spec.get(
            'cov_note', 'covariance in the released cross-section units^2, row/col order below'))
    return out


_ROW2D_BR = re.compile(
    r'\s*\d+\s+\[\s*([-\d.]+)\s*,\s*([-\d.]+)\s*\]\s+\[\s*([-\d.]+)\s*,\s*([-\d.]+)\s*\]'
    r'\s+([-\d.eE]+)\s+([-\d.eE]+)')
def build_2d_text(spec):
    """2-D release from an inline-error bracketed text table:
    'bin  [cos_lo,cos_hi]  [p_lo,p_hi]  value  error'."""
    grouped = {}
    for ln in open(fetch(spec['text'])):
        m = _ROW2D_BR.match(ln)
        if m:
            clo, chi, plo, phi, val, err = (float(x) for x in m.groups())
            grouped.setdefault((clo, chi), []).append((plo, phi, val, err))
    return _assemble_2d(grouped, spec)


def build_2d_binned(spec):
    """2-D release where the (cos,p) binning is in a separate 'min_cos max_cos
    min_p max_p' file and the values+errors are columns of a data file (same row
    order) -- e.g. an O/C cross-section ratio with the ratio + error inline."""
    binning = []
    for ln in open(fetch(spec['binning'])):
        ln = ln.strip()
        if not ln or ln.startswith(('//', '#')):
            continue
        p = ln.split()
        if len(p) >= 4:
            try:
                binning.append(tuple(float(x) for x in p[:4]))
            except ValueError:
                pass
    vc, ec = spec['vcol'], spec['ecol']
    vals = []
    for ln in open(fetch(spec['data'])):
        p = ln.split()
        try:
            vals.append((float(p[vc]), float(p[ec])))
        except (ValueError, IndexError):
            vals.append(None)
    grouped = {}
    for (clo, chi, plo, phi), ve in zip(binning, vals):
        if ve is None:
            continue
        grouped.setdefault((clo, chi), []).append((plo, phi, ve[0], ve[1]))
    return _assemble_2d(grouped, spec)


def build_2d_joint(spec):
    """A joint multi-detector 2-D release: one flattened bin array over >=1
    detectors, each with its own cos-p binning.  Values from a CSV (bin,data,..),
    errors from the diagonal of a covariance CSV, binning + detector split from
    per-detector binning CSVs (global 1-based bin index).  One 2-D item per
    detector."""
    vals = {}
    for ln in open(fetch(spec['data'])):
        p = [x.strip() for x in ln.split(',')]
        try:
            vals[int(p[0])] = float(p[spec.get('vcol', 1)])
        except (ValueError, IndexError):
            pass
    Mfull = np.array([[float(x) for x in l.split(',')]
                      for l in open(fetch(spec['cov'])) if l.strip()])
    diag = {i + 1: math.sqrt(max(Mfull[i, i], 0.0)) for i in range(len(Mfull))}
    pdiv = spec.get('pdiv', 1.0)
    out, order = [], {}
    for det in spec['detectors']:
        grouped = {}
        for ln in open(fetch(det['file'])):
            p = [x.strip() for x in ln.split(',')]
            try:
                b = int(p[0]); alo, ahi, plo, phi = (float(p[i]) for i in (1, 2, 3, 4))
            except (ValueError, IndexError):
                continue
            if b in vals and b in diag:
                grouped.setdefault((alo, ahi), []).append(
                    (plo / pdiv, phi / pdiv, vals[b], diag[b]))
                order[b] = (f"{det['name']} cos[{alo:g},{ahi:g}] "
                            f"p[{plo / pdiv:g},{phi / pdiv:g}]")
        out += _assemble_2d(grouped, {**spec, 'det_tex': rf"\mathrm{{{det['name']}}}",
                                      'det_slug': det['name'].lower()})
    if out:
        order_list = [order[k] for k in sorted(order)]
        out[0]['_release_cov'] = _cov_obj(Mfull, order_list, spec.get(
            'cov_note', 'covariance in (cm^2/GeV)^2, row/col order below'))
    return out


def build_2d_bracket(spec):
    """2-D release from a bracketed-text result ('cos theta [a,b], momentum [c,d]
    GeV/c  <result> <error>') plus a covariance matrix stored WITHOUT the per-bin
    normalization.  The result is a density d2sigma/dp dcos; the covariance is
    bin-integrated, so we divide it by the bin areas (Dcos*Dp) so sqrt(diag) equals
    the quoted per-bin error.  Everything stored in absolute units via *_scale."""
    base = os.path.join(ROOT_DIR, spec['dir'])
    rx = re.compile(r'cos\s*theta\s*\[([-\d.]+),\s*([-\d.]+)\].*?momentum\s*\[([-\d.]+),'
                    r'\s*([-\d.]+)\].*?([-\d.eE+]+)\s+([-\d.eE+]+)\s*$', re.I)
    rs = spec.get('result_scale', 1.0)
    bins = []                                          # (clo,chi,plo,phi,val,err,area) file order
    for ln in open(os.path.join(base, spec['result'])):
        if ln.startswith('#') or not ln.strip():
            continue
        m = rx.search(ln.strip())
        if not m:
            continue
        clo, chi, plo, phi, val, err = (float(x) for x in m.groups())
        bins.append((clo, chi, plo, phi, val * rs, err * rs, (chi - clo) * (phi - plo)))
    raw = []
    for ln in open(os.path.join(base, spec['cov'])):
        try:
            row = [float(x) for x in ln.split()]
        except ValueError:
            continue
        if row:
            raw.append(row)
    areas = np.array([b[6] for b in bins])
    Mnorm = np.array(raw) * spec.get('cov_scale', 1.0) / np.outer(areas, areas)
    order = [f"cos[{b[0]:g},{b[1]:g}] p[{b[2]:g},{b[3]:g}]" for b in bins]
    grouped = {}
    for (clo, chi, plo, phi, val, err, _a) in bins:
        grouped.setdefault((clo, chi), []).append((plo, phi, val, err))
    out = _assemble_2d(grouped, spec)
    if out:
        out[0]['_release_cov'] = _cov_obj(Mnorm, order, spec.get(
            'cov_note', 'covariance normalized to the reported density '
            '(sqrt(diag) = per-bin error), row/col order below'))
    return out


def build_1d_csv_targets(spec):
    """Several 1-D differential results in one CSV (target,bin_low,bin_high,<value>,
    error), split into one distribution per (observable, target).  Quoted errors are
    used directly; an overflow last bin (e.g. p in [1.5, 30]) is shown truncated."""
    base = os.path.join(ROOT_DIR, spec['dir'])
    out = []
    for res in spec['results']:
        lines = [ln.rstrip('\n') for ln in open(os.path.join(base, res['file'])) if ln.strip()]
        hdr = [h.strip() for h in lines[0].split(',')]
        rows = [dict(zip(hdr, [c.strip() for c in ln.split(',')])) for ln in lines[1:]]
        sc = res.get('scale', 1.0)
        targets, by = [], {}
        for r in rows:
            t = r['target']
            if t not in by:
                by[t] = []
                targets.append(t)
            by[t].append(r)
        for t in targets:
            bins = []
            for i, r in enumerate(by[t]):
                lo, hi = float(r['bin_low']), float(r['bin_high'])
                bins.append({'i': i, 'lo': lo, 'hi': hi, 'center': 0.5 * (lo + hi),
                             'val': float(r[res['vcol']]) * sc, 'err': float(r['error']) * sc})
            med = float(np.median([b['hi'] - b['lo'] for b in bins]))
            clipped = False
            for b in bins:
                if b['hi'] - b['lo'] > 4 * med:
                    b['hi_true'] = b['hi']
                    b['hi'] = round(b['lo'] + med, 4)
                    b['center'] = 0.5 * (b['lo'] + b['hi'])
                    clipped = True
            yl, key = res['ylabel'], f"{res['key']}_{t.lower()}"
            out.append({
                'key': key, 'slug': key, 'name': plotify(yl) + f' ({t})',
                'name_tex': rf'${yl}\ (\mathrm{{{t}}})$',
                'xlabel': plotify(res['xlabel']), 'xunit': res.get('xunit', ''),
                'ylabel': plotify(yl), 'ylabel_plot': plotify(yl), 'ylabel_tex': f'${yl}$',
                'yunit': res.get('yunit', ''),
                'yunit_tex': f"${tl(res.get('yunit', ''))}$" if res.get('yunit') else '',
                'nbins': len(bins), 'bins': bins, 'is2d': False, 'nuisance_file': '',
                'scale_note': 'last bin is an integration overflow (shown truncated)' if clipped else None,
                'source': spec['source'], 'source_url': spec['source_url'],
                'provenance': spec['provenance'],
            })
    return out


def build_3d_zenodo(spec):
    """T2K nu_e CC1pi+ (2025smz): a flux-integrated TRIPLE-differential
    (p_e x cos_e x p_pi) cross section vendored from Zenodo.  xsec.csv gives each
    bin's 3-D edges + value; covariance.csv is (bin1 bin2 cov).  Presented as one
    item: p_e panels sliced by (cos_e, p_pi).  Files are local (Zenodo rate-limits
    scripted fetches), so paths are read directly, not via fetch()."""
    base = spec['dir']
    rows = []
    for ln in open(os.path.join(ROOT_DIR, base, 'xsec.csv')):
        p = ln.split()
        if len(p) < 8 or not p[0].isdigit():
            continue
        rows.append((int(p[0]), *(float(x) for x in p[1:8])))
    N = len(rows)
    M = np.zeros((N, N))
    for ln in open(os.path.join(ROOT_DIR, base, 'covariance.csv')):
        p = ln.split()
        if len(p) < 3 or not p[0].isdigit():
            continue
        M[int(p[0]) - 1, int(p[1]) - 1] = float(p[2])
    err = np.sqrt(np.clip(np.diag(M), 0, None))
    OV = spec.get('overflow_hi', 10.0)                 # p_e cap bin (e.g. [1.7, 30])
    grouped, order = {}, []
    for (b, pe1, pe2, ce1, ce2, pp1, pp2, val) in rows:
        grouped.setdefault((ce1, ce2, pp1, pp2), []).append((pe1, pe2, val, float(err[b - 1])))
        order.append(f"cos_e[{ce1:g},{ce2:g}] p_pi[{pp1:g},{pp2:g}] p_e[{pe1:g},{pe2:g}]")
    yl, xl = spec['ylabel'], spec['xlabel']
    slices, total = [], 0
    for (ce1, ce2, pp1, pp2), pts in grouped.items():
        bins = [{'i': i, 'lo': plo, 'hi': phi, 'center': 0.5 * (plo + phi), 'val': v, 'err': e}
                for i, (plo, phi, v, e) in enumerate(sorted(pts))]
        normal = [b['hi'] - b['lo'] for b in bins if b['hi'] < OV]
        med = float(np.median(normal)) if normal else float(np.median([b['hi'] - b['lo'] for b in bins]))
        clipped = False
        for b in bins:
            if b['hi'] >= OV:                          # overflow p_e bin: truncate for display
                b['hi_true'] = b['hi']
                b['hi'] = round(b['lo'] + med, 4)
                b['center'] = 0.5 * (b['lo'] + b['hi'])
                clipped = True
        total += len(bins)
        lab = rf'\cos\theta_e\in[{ce1:g},{ce2:g}],\ p_\pi\in[{pp1:g},{pp2:g}]'
        slices.append({'label_tex': f'${lab}$', 'label': plotify(lab),
                       'lo': pp1, 'hi': pp2, 'nbins': len(bins), 'bins': bins,
                       'scale_note': 'last p_e bin is an integration overflow (shown truncated)'
                       if clipped else None})
    dist = {
        'key': 'd3xsec', 'slug': 'd3xsec',
        'name': plotify(yl), 'name_tex': f'${yl}$',
        'xlabel': plotify(xl), 'xunit': spec.get('xunit', ''),
        'ylabel': plotify(yl), 'ylabel_plot': plotify(yl), 'ylabel_tex': f'${yl}$',
        'yunit': spec.get('yunit', ''),
        'yunit_tex': f"${tl(spec.get('yunit', ''))}$" if spec.get('yunit') else '',
        'nbins': total, 'is2d': True, 'slicevar_tex': r'$\cos\theta_e \times p_\pi$',
        'slices': slices, 'bins': [], 'nuisance_file': '', 'scale_note': None,
        'source': spec['source'], 'source_url': spec['source_url'], 'provenance': spec['provenance'],
    }
    dist['_release_cov'] = _cov_obj(M, order, spec.get(
        'cov_note', 'covariance in (cm^2/nucleon/(GeV/c)^2)^2, row/col order below'))
    return [dist]


def _sym_from_packed(m):
    """Unpack a ROOT TMatrixTSym (upper-triangle fElements) into a full matrix."""
    N = m.member('fNrows'); el = np.asarray(m.member('fElements'))
    M = np.zeros((N, N)); idx = 0
    for i in range(N):
        for j in range(i, N):
            M[i, j] = M[j, i] = el[idx]; idx += 1
    return M


def _cov_obj(M, order, note):
    """Package a full covariance matrix for the release JSON (5 sig figs)."""
    return {'order': order, 'note': note,
            'matrix': [[float(f'{v:.5g}') for v in row] for row in np.asarray(M)]}


def build_2d_rootslices(spec):
    """Reconstruct a 2-D release from a NUISANCE ROOT file whose DataSlice hists
    are empty binning templates: values from a flattened LinearResult TH1D, p-edges
    per cos-slice from the DataSlice hists, cos edges supplied, errors from the
    diagonal of summed TMatrixTSym covariances (block-offset per beam)."""
    f = uproot.open(fetch(spec['root']))
    Mfull = None
    for ck in spec['cov_keys']:
        M = _sym_from_packed(f[ck])
        Mfull = M if Mfull is None else Mfull + M
    err_all = np.sqrt(np.clip(np.diag(Mfull), 0, None))
    cos = spec['cos_edges']
    out, order = [], []
    for beam in spec['beams']:
        vals = f[beam['result']].values()
        off, b, grouped = beam['offset'], 0, {}
        for s in range(len(cos) - 1):
            edges = f[f"{beam['slice_prefix']}{s}"].axis().edges()
            for pi in range(len(edges) - 1):
                grouped.setdefault((cos[s], cos[s + 1]), []).append(
                    (float(edges[pi]), float(edges[pi + 1]),
                     float(vals[b]), float(err_all[off + b])))
                order.append(f"{beam['slug']} cos[{cos[s]:g},{cos[s + 1]:g}] "
                             f"p[{edges[pi]:g},{edges[pi + 1]:g}]")
                b += 1
        out += _assemble_2d(grouped, {**spec, 'det_tex': beam['tex'],
                                      'det_slug': beam['slug'], 'nuisance_file': spec['root']})
    if out:
        out[0]['_release_cov'] = _cov_obj(
            Mfull, order, 'total (stat+syst) covariance in (cm^2/GeV)^2, row/col order below')
    return out


def build_2d_root_explicit(spec):
    """2-D release from a flattened result TH1 + covariance TH2 with an EXPLICIT
    slice binning (slice_edges + per-slice x-edges) taken from the sample class.
    cov_fractional=True: the stored covariance is relative, so the absolute per-bin
    error is value * sqrt(diag).  Slice var and x axis are whatever the spec says
    (this release slices by p_mu and plots vs cos_theta)."""
    f = uproot.open(fetch(spec['root']))
    vals = f[spec['result']].values()
    Mraw = np.asarray(f[spec['cov']].values())
    # if the release covariance is fractional (relative), the absolute covariance
    # is cov_ij * value_i * value_j (so error_i = value_i * sqrt(cov_ii)).
    if spec.get('cov_fractional'):
        v = np.asarray(vals[:len(Mraw)], dtype=float)
        Mabs = Mraw * np.outer(v, v)
    else:
        Mabs = Mraw
    sedges, xbins, sdiv = spec['slice_edges'], spec['xbins'], spec.get('sdiv', 1.0)
    grouped, order, b = {}, [], 0
    for i in range(len(sedges) - 1):
        slo, shi = sedges[i] / sdiv, sedges[i + 1] / sdiv
        edges = xbins[i]
        for j in range(len(edges) - 1):
            grouped.setdefault((slo, shi), []).append(
                (edges[j], edges[j + 1], float(vals[b]), math.sqrt(max(Mabs[b, b], 0.0))))
            order.append(f"p[{slo:g},{shi:g}] cos[{edges[j]:g},{edges[j + 1]:g}]")
            b += 1
    out = _assemble_2d(grouped, spec)
    if out:
        out[0]['_release_cov'] = _cov_obj(Mabs, order, spec.get(
            'cov_note', 'covariance in (cm^2/GeV)^2, row/col order below'))
    return out


def _assemble_2d(grouped, spec):
    """Turn {(cos_lo,cos_hi): [(p_lo,p_hi,val,err),...]} into a single 2-D
    distribution presented as sliced 1-D panels (overflow last bins truncated)."""
    xl, yl = spec['xlabel'], spec['ylabel']       # yl = the 2-D observable itself
    slices, total = [], 0
    for (clo, chi), pts in grouped.items():
        bins = [{'i': i, 'lo': plo, 'hi': phi, 'center': 0.5 * (plo + phi), 'val': v, 'err': e}
                for i, (plo, phi, v, e) in enumerate(sorted(pts))]
        # clip an integration-overflow last bin (e.g. p in [x, 30]) to a median
        # width so it doesn't dominate the axis; keep the true edge for the table.
        med = float(np.median([b['hi'] - b['lo'] for b in bins]))
        clipped = False
        for b in bins:
            if b['hi'] - b['lo'] > 4 * med:
                b['hi_true'] = b['hi']
                b['hi'] = round(b['lo'] + med, 4)
                b['center'] = 0.5 * (b['lo'] + b['hi'])
                clipped = True
        total += len(bins)
        sl = spec.get('slicevar', r'\cos\theta_\mu')
        slices.append({
            'label_tex': f'${clo:g} < {sl} < {chi:g}$',
            'label': plotify(f'{clo:g} < {sl} < {chi:g}'),
            'lo': clo, 'hi': chi, 'nbins': len(bins), 'bins': bins,
            'scale_note': 'last bin is an integration overflow (shown truncated)' if clipped else None,
        })
    # optional group label (a detector like ND280, or a beam like \nu_\mu):
    # det_tex is the LaTeX to show, det_slug the ascii key/name suffix.
    det_tex, det_slug = spec.get('det_tex'), spec.get('det_slug')
    suf_tex = rf'\ ({det_tex})' if det_tex else ''
    suf = f' ({det_slug})' if det_slug else ''
    dkey = (f"_{det_slug}" if det_slug else '')
    dist = {
        'key': spec.get('key', 'd2xsec') + dkey, 'slug': spec.get('slug', 'd2xsec') + dkey,
        'name': plotify(yl) + suf, 'name_tex': f'${yl}{suf_tex}$',
        'xlabel': plotify(xl), 'xunit': spec.get('xunit', ''),
        'ylabel': plotify(yl), 'ylabel_plot': plotify(yl), 'ylabel_tex': f'${yl}$',
        'yunit': spec.get('yunit', ''), 'yunit_tex': f"${tl(spec.get('yunit',''))}$" if spec.get('yunit') else '',
        'nbins': total, 'is2d': True, 'slicevar_tex': f"${spec.get('slicevar', r'cos theta_mu')}$",
        'slices': slices, 'bins': [],
        'nuisance_file': spec.get('nuisance_file') or spec.get('text') or spec.get('data') or '',
        'scale_note': None,
    }
    for k in ('source', 'source_url', 'provenance'):   # let a builder pre-set these
        if spec.get(k):
            dist[k] = spec[k]
    return [dist]


def extract_root(relfile, want=None,
                 result_keys=('hResultTot', 'Result', 'xsec_best_fit'),
                 cov_keys=('TotalCovariance', 'Covariance_Matrix', 'xsec_cov')):
    """Yield distributions from a ROOT file: pair each result TH1D with its
    sibling covariance TH2D (nested-dir or flat layouts).  Skips 2-D results."""
    f = uproot.open(fetch(relfile))
    keys = [k.split(';')[0] for k in f.keys()]
    out = []
    # nested: <dir>/hResultTot + <dir>/TotalCovariance
    dirs = sorted(set(k.split('/')[0] for k in keys if '/' in k))
    for d in dirs:
        if want and d not in want:
            continue
        res = next((f[f'{d}/{r}'] for r in result_keys if f'{d}/{r}' in keys), None)
        cov = next((f[f'{d}/{c}'] for c in cov_keys if f'{d}/{c}' in keys), None)
        if res is None or cov is None:
            continue
        if 'TH1' not in res.classname:
            continue
        out.append(_distr_from(d, res, cov, relfile))
    # flat: Result + Covariance_Matrix at top level
    if not dirs:
        res = next((f[r] for r in result_keys if r in keys), None)
        cov = next((f[c] for c in cov_keys if c in keys), None)
        if res is not None and cov is not None and 'TH1' in res.classname:
            out.append(_distr_from(want or 'result', res, cov, relfile))
    return out


# --- registry: paper -> how to build its release ----------------------------
# Each entry: bibtag, slug, list of sources. arXiv + citation come from the DB.
# A source is {'root': path[, 'name']} or {'txt': path, 'labels': {...}}.
NUE = 'data/T2K/CCinc/nue_2019/'
# neutrino_data repo (HEPData-homogenised) release dir for T2K:2023qjb
_ND = ('https://raw.githubusercontent.com/NUISANCEMC/neutrino_data/main/data/T2K/'
       'CrossSection/PRD.108.112009/onoffaxis_data_release/')
def _nue(f, name, x, xu, y, yu):
    return {'txt': NUE + f, 'labels': {'key': name, 'xlabel': x, 'xunit': xu,
                                       'ylabel': y, 'yunit': yu}}

REGISTRY = [
    {'bibtag': 'T2K:2016cbz', 'slug': 't2k-2016cbz',
     'sources': [{'root': 'data/T2K/CC1pip/H2O/nd280data-numu-cc1pi-xs-on-h2o-2015.root'}]},
    {'bibtag': 'T2K:2018rnz', 'slug': 't2k-2018rnz',
     'sources': [
         {'root': 'data/T2K/CC0pi/STV/dptResults.root', 'name': 'dpt'},
         {'root': 'data/T2K/CC0pi/STV/dphitResults.root', 'name': 'dphit'},
         {'root': 'data/T2K/CC0pi/STV/datResults.root', 'name': 'dat'}]},
    {'bibtag': 'T2K:2021naz', 'slug': 't2k-2021naz',
     'sources': [
         {'root': 'data/T2K/CC1pipNp_STV/xsec_dpTT.root', 'name': 'dpTT'},
         {'root': 'data/T2K/CC1pipNp_STV/xsec_daT.root', 'name': 'daT'},
         {'root': 'data/T2K/CC1pipNp_STV/xsec_pN.root', 'name': 'pN'}]},
    {'bibtag': 'T2K:2016soz', 'slug': 't2k-2016soz',
     'sources': [{'txt': 'data/T2K/CCCOH/C12_Enu_1bin.txt',
                  'labels': {'key': 'Enu', 'xlabel': r'E_\nu', 'xunit': 'GeV',
                             'ylabel': r'\sigma_{\mathrm{coh}}', 'yunit': r'cm^2/{}^{12}C'}}]},
    {'bibtag': 'T2K:2020lrr', 'slug': 't2k-2020lrr',
     'sources': [
         _nue('FHC_nue_pe.txt', 'nue_FHC_pe', r'p_e\ (\nu_e,\ \mathrm{FHC})', 'GeV',
              r'\mathrm{d}\sigma/\mathrm{d}p_e', r'cm^2/GeV/nucleon'),
         _nue('FHC_nue_thetae.txt', 'nue_FHC_costhetae', r'\cos\theta_e\ (\nu_e,\ \mathrm{FHC})', '',
              r'\mathrm{d}\sigma/\mathrm{d}\cos\theta_e', r'cm^2/nucleon'),
         _nue('RHC_nue_pe.txt', 'nue_RHC_pe', r'p_e\ (\nu_e,\ \mathrm{RHC})', 'GeV',
              r'\mathrm{d}\sigma/\mathrm{d}p_e', r'cm^2/GeV/nucleon'),
         _nue('RHC_nue_thetae.txt', 'nue_RHC_costhetae', r'\cos\theta_e\ (\nu_e,\ \mathrm{RHC})', '',
              r'\mathrm{d}\sigma/\mathrm{d}\cos\theta_e', r'cm^2/nucleon'),
         _nue('RHC_nuebar_pe.txt', 'nuebar_RHC_pe', r'p_e\ (\bar\nu_e,\ \mathrm{RHC})', 'GeV',
              r'\mathrm{d}\sigma/\mathrm{d}p_e', r'cm^2/GeV/nucleon'),
         _nue('RHC_nuebar_thetae.txt', 'nuebar_RHC_costhetae', r'\cos\theta_e\ (\bar\nu_e,\ \mathrm{RHC})', '',
              r'\mathrm{d}\sigma/\mathrm{d}\cos\theta_e', r'cm^2/nucleon')]},
    {'bibtag': 'T2K:2016jor', 'slug': 't2k-2016jor',
     'sources': [{'slices2d': {
         'text': 'data/T2K/CC0pi/cross-section_analysisI.txt',
         'cov': 'data/T2K/CC0pi/T2K_CC0PI_2DPmuCosmu_Data.root', 'cov_key': 'analysis1_totcov',
         'xlabel': r'p_\mu', 'xunit': 'GeV',
         'ylabel': r'\mathrm{d}^2\sigma/\mathrm{d}p_\mu\mathrm{d}\cos\theta_\mu',
         'yunit': r'10^{-38}\ cm^2/GeV/nucleon'}}]},
    {'bibtag': 'T2K:2018lnf', 'slug': 't2k-2018lnf',
     'sources': [{'slices2d_txt': {
         'text': 'data/T2K/CCinc/nd280data-numu-cc-inc-xs-on-c-2018/data_unfold_with_neut.txt',
         'xlabel': r'p_\mu', 'xunit': 'GeV/c',
         'ylabel': r'\mathrm{d}^2\sigma/\mathrm{d}\cos\theta_\mu\mathrm{d}p_\mu',
         'yunit': r'10^{-39}\ cm^2/(GeV/c)/nucleon'}}]},
    {'bibtag': 'T2K:2020jav', 'slug': 't2k-2020jav',
     'sources': [{'slices2d_binned': {
         'binning': 'data/T2K/CC0pi/JointO-C/Binning.txt',
         'data': 'data/T2K/CC0pi/JointO-C/cc0pi_xsec_O-C-ratio_reg.txt',
         'vcol': 5, 'ecol': 6,          # ratio value, ratio error
         'key': 'oc_ratio', 'slug': 'oc_ratio',
         'xlabel': r'p_\mu', 'xunit': 'GeV/c',
         'ylabel': r'\sigma(\mathrm{O})/\sigma(\mathrm{C})', 'yunit': ''}}]},
    {'bibtag': 'T2K:2023qjb', 'slug': 't2k-2023qjb',
     'sources': [{'joint2d': {
         'data': _ND + 'xsec_data_mc.csv', 'cov': _ND + 'cov_matrix.csv',
         'vcol': 1, 'pdiv': 1000.0,        # data column; p MeV/c -> GeV/c
         'detectors': [{'name': 'ND280', 'file': _ND + 'nd280_analysis_binning.csv'},
                       {'name': 'INGRID', 'file': _ND + 'ingrid_analysis_binning.csv'}],
         'xlabel': r'p_\mu', 'xunit': 'GeV/c',
         'ylabel': r'\mathrm{d}^2\sigma/\mathrm{d}p_\mu\mathrm{d}\cos\theta_\mu',
         'yunit': r'cm^2/GeV',
         'nuisance_file': 'neutrino_data/…/PRD.108.112009/onoffaxis_data_release/',
         'source': 'NUISANCE neutrino_data',
         'source_url': 'https://github.com/NUISANCEMC/neutrino_data/tree/main/data/T2K/'
                       'CrossSection/PRD.108.112009/onoffaxis_data_release'}}]},
    {'bibtag': 'T2K:2020sbd', 'slug': 't2k-2020sbd',
     'sources': [{'rootslices': {
         'root': 'data/T2K/CC0pi/JointNuMu-AntiNuMu/JointNuMuAntiNuMuCC0piXsecDataRelease.root',
         'cov_keys': ['JointNuMuAntiNuMuCC0piXsecCovMatrixStat',
                      'JointNuMuAntiNuMuCC0piXsecCovMatrixSyst'],
         'cos_edges': [-1, 0.2, 0.6, 0.7, 0.8, 0.85, 0.9, 0.94, 0.98, 1],
         'beams': [
             {'tex': r'\nu_\mu', 'slug': 'numu', 'offset': 0,
              'result': 'hNuMuCC0piXsecLinearResult',
              'slice_prefix': 'hXsecNuMuCC0piDataSlice_'},
             {'tex': r'\bar\nu_\mu', 'slug': 'antinumu', 'offset': 58,
              'result': 'hAntiNuMuCC0piXsecLinearResult',
              'slice_prefix': 'hXsecAntiNuMuCC0piDataSlice_'}],
         'xlabel': r'p_\mu', 'xunit': 'GeV/c',
         'ylabel': r'\mathrm{d}^2\sigma/\mathrm{d}p_\mu\mathrm{d}\cos\theta_\mu',
         'yunit': r'cm^2/GeV'}}]},
    {'bibtag': 'T2K:2019ddy', 'slug': 't2k-2019ddy',
     'sources': [{'root_explicit': {
         'root': 'data/T2K/CC0pi/AntiNuMuH2O/AntiNuMuOnH2O_unreg.root',
         'result': 'xsecDataRelease', 'cov': 'covDataRelease', 'cov_fractional': True,
         'slice_edges': [400, 530, 670, 800, 1000, 1380, 2010, 3410], 'sdiv': 1000.0,
         'xbins': [[0.84, 0.94, 1.0], [0.85, 0.92, 0.96, 1.0], [0.88, 0.93, 0.97, 1.0],
                   [0.90, 0.94, 0.97, 1.0], [0.91, 0.95, 0.97, 1.0],
                   [0.92, 0.96, 0.98, 1.0], [0.95, 0.98, 1.0]],
         'slicevar': r'p_\mu', 'xlabel': r'\cos\theta_\mu', 'xunit': '',
         'ylabel': r'\mathrm{d}^2\sigma/\mathrm{d}p_\mu\mathrm{d}\cos\theta_\mu',
         'yunit': r'cm^2/GeV'}}]},
    {'bibtag': 'T2K:2025smz', 'slug': 't2k-2025smz', 'source': 'Zenodo',
     'note': 'Flux-integrated triple-differential cross section, taken directly from '
             'the T2K Zenodo data release (values + full covariance; nothing digitized).',
     'sources': [{'zenodo3d': {
         'dir': 'data/datasets/sources/t2k-2025smz',
         'xlabel': r'p_e', 'xunit': 'GeV/c',
         'ylabel': r'\mathrm{d}^3\sigma/\mathrm{d}p_e\,\mathrm{d}\cos\theta_e\,\mathrm{d}p_\pi',
         'yunit': r'cm^2/nucleon/(GeV/c)^2',
         'source': 'Zenodo (T2K)',
         'source_url': 'https://zenodo.org/records/15316318',
         'provenance': 'T2K nu_e CC1pi+ triple-differential cross section on carbon '
                       '(Zenodo 10.5281/zenodo.15316318, arXiv:2505.00516) · '
                       'per-bin error = sqrt(diag(covariance)) · nothing digitized'}}]},
    {'bibtag': 'T2K:2025wde', 'slug': 't2k-2025wde', 'source': 'Zenodo',
     'note': 'Double-differential NC1pi+ cross section, taken directly from the T2K '
             'Zenodo data release (values + covariance; nothing digitized).',
     'sources': [{'bracket2d': {
         'dir': 'data/datasets/sources/t2k-2025wde',
         'result': 'result_with_bins.csv', 'cov': 'covariance_matrix.csv',
         'result_scale': 1e-40, 'cov_scale': 1e-82,
         'xlabel': r'p_\pi', 'xunit': 'GeV/c', 'slicevar': r'\cos\theta_\pi',
         'ylabel': r'\mathrm{d}^2\sigma/\mathrm{d}p_\pi\,\mathrm{d}\cos\theta_\pi',
         'yunit': r'cm^2/nucleon/(GeV/c)',
         'source': 'Zenodo (T2K)', 'source_url': 'https://zenodo.org/records/15776045',
         'provenance': 'T2K NC1pi+ double-differential cross section '
                       '(Zenodo 10.5281/zenodo.15776045, arXiv:2503.06849 & 2503.06843) · '
                       'per-bin error = sqrt(diag(covariance)) · nothing digitized'}}]},
    {'bibtag': 'T2K:2025kda', 'slug': 't2k-2025kda', 'source': 'Zenodo',
     'note': 'WAGASCI-BabyMIND numu CC0pi differential cross sections on CH and H2O, '
             'taken directly from the T2K Zenodo data release (values + quoted errors; '
             'the release also provides covariance matrices).',
     'sources': [{'csv1d_targets': {
         'dir': 'data/datasets/sources/t2k-2025kda',
         'results': [
             {'file': 'result_1d_diff_momentum.csv', 'key': 'dsdp', 'vcol': 'dsigma/dp',
              'xlabel': r'p_\mu', 'xunit': 'GeV/c', 'ylabel': r'\mathrm{d}\sigma/\mathrm{d}p_\mu',
              'yunit': r'cm^2/nucleon/(GeV/c)', 'scale': 1e-39},
             {'file': 'result_1d_diff_cosine.csv', 'key': 'dsdcos', 'vcol': 'dsigma/dcos',
              'xlabel': r'\cos\theta_\mu', 'xunit': '',
              'ylabel': r'\mathrm{d}\sigma/\mathrm{d}\cos\theta_\mu', 'yunit': r'cm^2/nucleon',
              'scale': 1e-39}],
         'source': 'Zenodo (T2K)', 'source_url': 'https://zenodo.org/records/16949979',
         'provenance': 'T2K WAGASCI-BabyMIND numu CC0pi differential cross section on CH/H2O '
                       '(Zenodo 10.5281/zenodo.16949979, arXiv:2509.07814) · quoted per-bin '
                       'errors · nothing digitized'}}]},
]


def build(entry):
    arxiv, cite = cite_of(entry['bibtag'])
    dists = []
    for src in entry['sources']:
        if 'root' in src:
            got = extract_root(src['root'], want=src.get('want'))
            if src.get('name') and len(got) == 1:
                got[0]['key'] = src['name']
                got[0]['slug'] = re.sub(r'[^a-z0-9]+', '_', src['name'].lower()).strip('_')
            dists.extend(got)
        elif 'txt' in src:
            d = parse_edge_txt(src['txt'], src['labels'])
            if d and d['nbins']:
                dists.append(d)
        elif 'slices2d' in src:
            dists.extend(build_2d_slices(src['slices2d']))
        elif 'slices2d_txt' in src:
            dists.extend(build_2d_text(src['slices2d_txt']))
        elif 'slices2d_binned' in src:
            dists.extend(build_2d_binned(src['slices2d_binned']))
        elif 'joint2d' in src:
            dists.extend(build_2d_joint(src['joint2d']))
        elif 'rootslices' in src:
            dists.extend(build_2d_rootslices(src['rootslices']))
        elif 'root_explicit' in src:
            dists.extend(build_2d_root_explicit(src['root_explicit']))
        elif 'zenodo3d' in src:
            dists.extend(build_3d_zenodo(src['zenodo3d']))
        elif 'bracket2d' in src:
            dists.extend(build_2d_bracket(src['bracket2d']))
        elif 'csv1d_targets' in src:
            dists.extend(build_1d_csv_targets(src['csv1d_targets']))
    for d in dists:
        d.setdefault('source', 'NUISANCE')
        d.setdefault('source_url', BLOB + d['nuisance_file'])
        d.setdefault('provenance', f"{d['source']} · {d['nuisance_file']} · from "
                     f"arXiv:{arxiv} ({cite}) · per-bin error = sqrt(diag(covariance))"
                     + (f" · {d['scale_note']}" if d.get('scale_note') else ''))
    release_cov = None
    for d in dists:
        if '_release_cov' in d:
            release_cov = d.pop('_release_cov')
    # per-observable ROOT releases: assemble a block-diagonal matrix from each
    # distribution's own covariance (NUISANCE gives no inter-observable terms).
    blocks = [d.pop('_cov') for d in dists if '_cov' in d]
    if release_cov is None and blocks:
        mats = [np.asarray(b[0]) for b in blocks]
        labels = [lab for b in blocks for lab in b[1]]
        total = sum(m.shape[0] for m in mats)
        M = np.zeros((total, total))
        off = 0
        for m in mats:
            n = m.shape[0]
            M[off:off + n, off:off + n] = m
            off += n
        release_cov = _cov_obj(M, labels, 'block-diagonal per-observable covariance '
                               '(NUISANCE provides no inter-observable correlations)')
    out = {'bibtag': entry['bibtag'], 'slug': entry['slug'],
           'source': entry.get('source', 'NUISANCE'),
           'arxiv': arxiv, 'cite': cite,
           'note': entry.get('note', 'Cross sections taken directly from the NUISANCE data release.'),
           'distributions': dists}
    if release_cov:
        out['covariance'] = release_cov
    path = os.path.join(OUT_DIR, f"{entry['slug']}.json")
    json.dump(out, open(path, 'w'), indent=1)
    return path, dists


if __name__ == '__main__':
    only = sys.argv[1] if len(sys.argv) > 1 else None
    for e in REGISTRY:
        if only and e['slug'] != only:
            continue
        path, dists = build(e)
        print(f"{e['bibtag']:<15} -> {os.path.relpath(path, ROOT_DIR)}  "
              f"({len(dists)} distributions, {sum(d['nbins'] for d in dists)} pts)")
        for d in dists:
            allbins = d['bins'] or [b for s in d.get('slices', []) for b in s['bins']]
            ratios = [b['err'] / abs(b['val']) for b in allbins if b['val']]
            rr = f"{np.median(ratios):.2f}" if ratios else "-"
            kind = f"{len(d['slices'])} slices" if d.get('is2d') else f"{d['nbins']} bins"
            print(f"    {d['key']:<26} {kind:<12} x[{d['xunit']}]  "
                  f"y[{d['yunit'][:30]}]  err/val~{rr}")
