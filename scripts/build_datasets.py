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
        'xlabel': plotify(xlab), 'xunit': xunit, 'xlabel_tex': f'${xlab}$',
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
        'xlabel_tex': f'${xl}$',
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


def build_2d_t2korg(spec):
    """t2k.org data release (only place this measurement lives): a global-binned
    TH1D result over a cos-p grid, with the total covariance = sum of per-source
    TMatrixT 'cvm_*' matrices.  Global bin 0 is out-of-range (dropped); some bins
    have no sensitivity (drop_bins) and are removed so the covariance is usable."""
    f = uproot.open(os.path.join(ROOT_DIR, spec['root']))
    vals = f[spec['result']].values()
    M = None
    for s in spec['cov_sources']:
        m = f[s]
        N = m.member('fNrows')
        el = np.asarray(m.member('fElements')).reshape(N, N)
        M = el.copy() if M is None else M + el
    Mreal = M[1:1 + len(vals), 1:1 + len(vals)]        # drop the out-of-range bin 0
    cos, ped = spec['cos_edges'], spec['p_edges']
    npb = len(ped) - 1
    drop = set(spec.get('drop_bins', []))              # 1-based global bins w/ no sensitivity
    grouped, order, keep = {}, [], []
    for g in range(1, len(vals) + 1):
        if g in drop:
            continue
        s, pb = (g - 1) // npb, (g - 1) % npb
        grouped.setdefault((cos[s], cos[s + 1]), []).append(
            (ped[pb], ped[pb + 1], float(vals[g - 1]),
             float(math.sqrt(max(Mreal[g - 1, g - 1], 0.0)))))
        order.append(f"cos[{cos[s]:g},{cos[s + 1]:g}] p[{ped[pb]:g},{ped[pb + 1]:g}]")
        keep.append(g - 1)
    out = _assemble_2d(grouped, spec)
    if out:
        out[0]['_release_cov'] = _cov_obj(Mreal[np.ix_(keep, keep)], order, spec.get(
            'cov_note', 'total covariance = sum of the per-source cvm_* matrices '
            '(no-sensitivity bins removed), row/col order below'))
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
                'xlabel_tex': f"${res['xlabel']}$",
                'ylabel': plotify(yl), 'ylabel_plot': plotify(yl), 'ylabel_tex': f'${yl}$',
                'yunit': res.get('yunit', ''),
                'yunit_tex': f"${tl(res.get('yunit', ''))}$" if res.get('yunit') else '',
                'nbins': len(bins), 'bins': bins, 'is2d': False, 'nuisance_file': '',
                'scale_note': 'last bin is an integration overflow (shown truncated)' if clipped else None,
                'source': spec['source'], 'source_url': spec['source_url'],
                'provenance': spec['provenance'],
            })
    return out


def _flux_open(path):
    """Return an openable local path for a flux source: the vendored file if it
    exists, otherwise fetch it from NUISANCE (cached)."""
    local = os.path.join(ROOT_DIR, path)
    return local if os.path.exists(local) else fetch(path)


def _flux_from_csv(spec):
    """Flux table from a text file: ecol=(i_lo,i_hi) energy-edge column indices,
    fcol=[(col_idx, label), ...] flux columns.  sep=None -> whitespace-split."""
    path = _flux_open(spec['csv'])
    sep = spec.get('sep')
    lines = [(l.split(sep) if sep else l.split()) for l in open(path)
             if l.strip() and not l.lstrip().startswith('#')]
    data = lines[1:] if spec.get('header', True) else lines
    elo, ehi = spec['ecol']
    rows = []
    for p in data:
        try:
            row = [round(float(p[elo]), 4), round(float(p[ehi]), 4)]
            row += [float(f'{float(p[ci]):.6g}') for ci, _ in spec['fcol']]
            rows.append(row)
        except (ValueError, IndexError):
            continue
    return {'note': spec['note'],
            'columns': ['E_low_GeV', 'E_high_GeV'] + [lbl for _, lbl in spec['fcol']],
            'rows': rows}


def extract_flux(spec):
    """Read a flux prediction into a table (E_low, E_high + one column per flux) for
    the release download bundle.  Flux is download-only, not displayed.  Source is a
    text file ('csv'), a ROOT file ('root'+'hists'), or several ROOT files ('blocks'
    = [{root, hists}, ...], merged column-wise assuming a common binning)."""
    if 'csv' in spec:
        return _flux_from_csv(spec)
    blocks = spec.get('blocks') or [{'root': spec['root'], 'hists': spec['hists']}]
    cols, vals, edges = [], {}, None
    for blk in blocks:
        f = uproot.open(_flux_open(blk['root']))
        for name, label in blk['hists']:
            h = f[name]
            vals[label] = h.values()
            cols.append(label)
            if edges is None:
                edges = h.axis().edges()
    rows = []
    for i in range(len(edges) - 1):
        row = [round(float(edges[i]), 4), round(float(edges[i + 1]), 4)]
        row += [float(f'{vals[c][i]:.6g}') for c in cols]
        rows.append(row)
    return {'note': spec['note'], 'columns': ['E_low_GeV', 'E_high_GeV'] + cols, 'rows': rows}


# Shared NUISANCE T2K ND280 flux (2016 tuning) — FHC (nu-mode) and RHC (nubar-mode).
_FLUX_NUM = [('enu_nd280_numu', 'numu'), ('enu_nd280_numub', 'numubar'),
             ('enu_nd280_nue', 'nue'), ('enu_nd280_nueb', 'nueb')]
_FLUX_FHC = {'root': 'data/datasets/sources/_t2kflux/t2kflux_2016_plus250kA.root',
             'hists': _FLUX_NUM,
             'note': 'T2K ND280 FHC (nu-mode) flux prediction, all flavours — provided by '
                     'NUISANCE (t2kflux_2016_plus250kA.root, 2016 tuning)'}
_FLUX_RHC = {'root': 'data/datasets/sources/_t2kflux/t2kflux_2016_minus250kA.root',
             'hists': _FLUX_NUM,
             'note': 'T2K ND280 RHC (nubar-mode) flux prediction, all flavours — provided by '
                     'NUISANCE (t2kflux_2016_minus250kA.root, 2016 tuning)'}
_FLUX_BOTH = {'blocks': [
    {'root': _FLUX_FHC['root'], 'hists': [(n, l + '_fhc') for n, l in _FLUX_NUM]},
    {'root': _FLUX_RHC['root'], 'hists': [(n, l + '_rhc') for n, l in _FLUX_NUM]}],
    'note': 'T2K ND280 flux prediction for both beam modes (FHC nu-mode + RHC nubar-mode), '
            'all flavours — provided by NUISANCE (t2kflux_2016_plus/minus250kA.root, 2016 tuning)'}
# Super-K (far-detector) unoscillated flux — for T2K SK cross-section measurements.
_FLUX_SK_NUM = [('enu_sk_numu', 'numu'), ('enu_sk_numub', 'numubar'),
                ('enu_sk_nue', 'nue'), ('enu_sk_nueb', 'nueb')]
_FLUX_SK_BOTH = {'blocks': [
    {'root': _FLUX_FHC['root'], 'hists': [(n, l + '_fhc') for n, l in _FLUX_SK_NUM]},
    {'root': _FLUX_RHC['root'], 'hists': [(n, l + '_rhc') for n, l in _FLUX_SK_NUM]}],
    'note': 'T2K Super-K (far detector) unoscillated flux for both beam modes (FHC+RHC), all '
            'flavours — provided by NUISANCE (t2kflux_2016_plus/minus250kA.root, enu_sk_*)'}


def _cat_plain(tex):
    """A readable ASCII form of a category label for CSV downloads."""
    s = tex.strip('$')
    for a, b in ((r'\bar\nu_\mu', 'antinumu'), (r'\nu_\mu', 'numu'),
                 (r'\mathrm{H_2O}', 'H2O'), (r'\mathrm{CH}', 'CH')):
        s = s.replace(a, b)
    s = s.replace(r'\!', '').replace(r'\,', ' ').replace('\\ ', ' ')
    s = re.sub(r'\\mathrm\{([^}]*)\}', r'\1', s)
    s = re.sub(r'[\\{}]', '', s)
    return re.sub(r'\s+', ' ', s).strip()


def build_values(spec):
    """A release of standalone measured VALUES with no differential binning: each
    item is a set of points on a CATEGORICAL x-axis (e.g. 'Averaged T2K flux', or
    targets H2O/CH, or beams).  A point carries a category label (cat, LaTeX) and a
    value with a symmetric ('err') or asymmetric (stat + syst_up/syst_down, added in
    quadrature) uncertainty.  Consumed by the front-end via the xcat flag plus each
    bin's cat_tex / err_up / err_down."""
    yl = spec['ylabel']
    out = []
    for it in spec['items']:
        bins = []
        for i, pt in enumerate(it['points']):
            if 'err' in pt:
                eu = ed = float(pt['err'])
            else:
                st = float(pt.get('stat', 0.0))
                eu = math.hypot(st, float(pt.get('syst_up', 0.0)))
                ed = math.hypot(st, float(pt.get('syst_down', 0.0)))
            bins.append({'i': i, 'lo': float(i), 'hi': float(i + 1), 'center': i + 0.5,
                         'val': float(pt['val']), 'err': max(eu, ed),
                         'err_up': eu, 'err_down': ed,
                         'cat_tex': pt['cat'], 'cat': _cat_plain(pt['cat'])})
        nu = it.get('name')
        suf_tex = rf'\ ({nu})' if nu else ''
        key = spec.get('key', 'val') + (f"_{it['slug']}" if it.get('slug') else '')
        out.append({
            'key': key, 'slug': key,
            'name': plotify(yl) + (f" ({it['slug']})" if it.get('slug') else ''),
            'name_tex': f'${yl}{suf_tex}$',
            'xlabel': '', 'xunit': '', 'xcat': True,
            'ylabel': plotify(yl), 'ylabel_plot': plotify(yl), 'ylabel_tex': f'${yl}$',
            'yunit': spec.get('yunit', ''),
            'yunit_tex': f"${tl(spec.get('yunit', ''))}$" if spec.get('yunit') else '',
            'nbins': len(bins), 'is2d': False, 'bins': bins,
            'nuisance_file': '', 'scale_note': it.get('note'),
            'source': spec['source'], 'source_url': spec['source_url'],
            'provenance': spec['provenance'] + (f" · {it['note']}" if it.get('note') else ''),
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
        'xlabel': plotify(xl), 'xunit': spec.get('xunit', ''), 'xlabel_tex': f'${xl}$',
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


def _read_matrix_txt(path, fmt=None):
    """Read a covariance matrix from text: fmt='pipe' -> '<idx> | v | v | ...'
    (skip header/separator); else whitespace-separated rows."""
    rows = []
    for ln in open(_flux_open(path)):
        if not ln.strip():
            continue
        if fmt == 'pipe':
            parts = ln.split('|')
            if not parts[0].strip().isdigit():
                continue
            cells = [c for c in parts[1:] if c.strip()]   # drop trailing empty from final '|'
        else:
            cells = ln.split()
        try:
            vals = [float(x) for x in cells]
        except ValueError:
            continue
        if vals:
            rows.append(vals)
    return np.asarray(rows)


def _notes_from_provenance(prov):
    """Derive the display 'Notes' from the full provenance: keep the technical caveats
    (how the error is defined, nothing digitized, rescalings, typos, ...) and drop the
    source / file path / citation, which are already shown by the subtitle, the source
    link, and the paper's own arXiv/DOI. Rendered as capitalised sentences."""
    keep = []
    for p in (part.strip() for part in prov.split(' · ')):
        low = p.lower()
        if not p or p in ('NUISANCE', 'NUISANCE neutrino_data'):
            continue                                   # source label
        if low.startswith('data/') or low.startswith('neutrino_data/'):
            continue                                   # in-repo file path
        if 'arxiv' in low or 'zenodo' in low or 't2k.org data release' in low:
            continue                                   # citation / description
        keep.append(p[0].upper() + p[1:])
    return '. '.join(keep) + ('.' if keep else '')


def build_sigma_enu(spec):
    """1-D sigma(E_nu) release from explicit rows 'lo hi value nominal' plus a
    fractional covariance defined RELATIVE TO THE PRE-FIT NOMINAL. The absolute
    covariance is cov_ij = frac_ij * nom_i * nom_j and the per-bin error is
    sqrt(frac_ii)*nom_i (nom = the pre-fit model, e.g. digitized NEUT-binned)."""
    rows = []
    for ln in open(_flux_open(spec['data'])):
        p = ln.replace(',', ' ').split()
        try:
            rows.append(tuple(float(x) for x in p[:4]))
        except (ValueError, IndexError):
            continue
    frac = _read_matrix_txt(spec['cov'])
    nom = np.array([r[3] for r in rows])
    errs = np.sqrt(np.clip(np.diag(frac), 0, None)) * nom
    bins, order = [], []
    for i, (lo, hi, val, _n) in enumerate(rows):
        bins.append({'i': i, 'lo': lo, 'hi': hi, 'center': 0.5 * (lo + hi),
                     'val': val, 'err': float(errs[i])})
        order.append(f"E[{lo:g},{hi:g}]")
    med = float(np.median([b['hi'] - b['lo'] for b in bins]))     # clip overflow last bin
    clipped = False
    for b in bins:
        if b['hi'] - b['lo'] > 4 * med:
            b['hi_true'] = b['hi']; b['hi'] = round(b['lo'] + med, 4)
            b['center'] = 0.5 * (b['lo'] + b['hi']); clipped = True
    xl, yl, yu = spec['xlabel'], spec['ylabel'], spec.get('yunit', '')
    dist = {
        'key': spec['key'], 'slug': spec['key'],
        'name': plotify(yl), 'name_tex': f'${yl}$',
        'xlabel': plotify(xl), 'xunit': spec.get('xunit', ''), 'xlabel_tex': f'${xl}$',
        'ylabel': plotify(yl), 'ylabel_plot': plotify(yl), 'ylabel_tex': f'${yl}$',
        'yunit': yu, 'yunit_tex': f'${tl(yu)}$' if yu else '',
        'nbins': len(bins), 'is2d': False, 'bins': bins, 'nuisance_file': '',
        'scale_note': 'last bin is an integration overflow (shown truncated)' if clipped else None,
        'source': spec['source'], 'source_url': spec['source_url'], 'provenance': spec['provenance'],
    }
    dist['_release_cov'] = _cov_obj(frac * np.outer(nom, nom), order, spec.get(
        'cov_note', 'covariance = fractional covariance x nominal_i*nominal_j; row/col order below'))
    if spec.get('digitization'):
        dist['digitization'] = spec['digitization']
    return [dist]


def build_minerva_root(spec):
    """Data release from a ROOT file of matched value TH1D + covariance TH2D per item
    (an observable, or an observable x target). The covariance may be NxN (MicroBooNE)
    or (N+2)x(N+2) with under/overflow (MINERvA, data at idx 1..N) — auto-detected.
    Per-bin error = sqrt(diag(total covariance)); covariances block-diagonal across items.
    Each item may override xlabel/xunit/ylabel/yunit (defaults from spec)."""
    _files = {}

    def _open(path):
        if path not in _files:
            _files[path] = uproot.open(_flux_open(path))
        return _files[path]

    def _cov(rr, key):                                                 # TH2D or TMatrixT/Sym
        o = rr[key]
        if 'TH2' in o.classname:
            return np.asarray(o.values())
        N = o.member('fNrows')
        return np.array(o.member('fElements')).reshape(N, N)
    droot = spec.get('root')                                           # default; items may override
    # 'cov' at spec level = one SHARED covariance over all items concatenated (keeps
    # cross-observable correlations); else each item carries its own 'cov' (block-diagonal).
    shared = _cov(_open(droot), spec['cov']) if spec.get('cov') else None
    dists, blocks, order = [], [], []
    soff = 0
    for it in spec['items']:
        r = _open(it.get('root', droot))
        h = r[it['hist']]; edges = h.axis().edges(); vv = h.values(); n = len(vv)
        if shared is not None:
            M = shared[soff:soff + n, soff:soff + n]; soff += n         # this item's diagonal block
        else:
            cov = _cov(r, it['cov']); K = cov.shape[0]
            M = cov if K == n else cov[1:n + 1, 1:n + 1]                # NxN or drop under/overflow
        err = np.sqrt(np.clip(np.diag(M), 0, None))                    # total per-bin error
        bins = [{'i': i, 'lo': float(edges[i]), 'hi': float(edges[i + 1]),
                 'center': 0.5 * (edges[i] + edges[i + 1]), 'val': float(vv[i]), 'err': float(err[i])}
                for i in range(n)]
        med = float(np.median([b['hi'] - b['lo'] for b in bins]))       # clip overflow last bin
        clipped = False
        for b in bins:
            if b['hi'] - b['lo'] > 4 * med:
                b['hi_true'] = b['hi']; b['hi'] = round(b['lo'] + med, 4)
                b['center'] = 0.5 * (b['lo'] + b['hi']); clipped = True
        lab = it.get('label', it['slug'])
        xl = it.get('xlabel', spec['xlabel']); yl = it.get('ylabel', spec['ylabel'])
        yu = it.get('yunit', spec.get('yunit', '')); xu = it.get('xunit', spec.get('xunit', ''))
        key = spec.get('key', 'xsec') + '_' + it['slug']
        dists.append({
            'key': key, 'slug': key,
            'name': plotify(yl) + (f' ({lab})' if lab else ''),
            'name_tex': f'${yl}' + (f'\\ ({lab})$' if lab else '$'),
            'xlabel': plotify(xl), 'xunit': xu, 'xlabel_tex': f'${xl}$',
            'ylabel': plotify(yl), 'ylabel_plot': plotify(yl), 'ylabel_tex': f'${yl}$',
            'yunit': yu, 'yunit_tex': f'${tl(yu)}$' if yu else '',
            'nbins': n, 'is2d': False, 'bins': bins,
            'nuisance_file': it.get('root', spec.get('root', '')),
            'scale_note': 'last bin is an integration overflow (shown truncated)' if clipped else None,
            'source': spec['source'], 'source_url': spec['source_url'], 'provenance': spec['provenance'],
        })
        if shared is None:
            blocks.append(M)
        for i in range(n):
            order.append(f"{it['slug']} [{edges[i]:g},{edges[i + 1]:g}]")
    if shared is not None:
        cov_out = shared                                               # full cross-observable matrix
        note = 'total (stat+syst) covariance over all observables (concatenated); row/col order below'
    else:
        total = sum(b.shape[0] for b in blocks)
        cov_out = np.zeros((total, total)); off = 0
        for b in blocks:
            k = b.shape[0]; cov_out[off:off + k, off:off + k] = b; off += k
        note = 'block-diagonal total (stat+syst) covariance per item; row/col order below'
    if dists:
        dists[0]['_release_cov'] = _cov_obj(cov_out, order, spec.get('cov_note', note))
    return dists


def build_minerva_csv(spec):
    """MINERvA anc CSV release: a values file with a 'Bin Low Edge...' row and a
    'Cross Section' row, plus a covariance CSV (first NxN numeric block). Per-bin
    error = sqrt(diag(covariance)); the last bin's high edge is spec['last_edge']."""
    named = {}
    for ln in open(_flux_open(spec['data'])):
        p = [x.strip() for x in ln.rstrip().split(',')]
        if p:
            named[p[0]] = p[1:]
    edrow = next(v for k, v in named.items() if k.lower().startswith('bin low edge'))
    lo = [float(x) for x in edrow if x]
    vals = [float(x) for x in named['Cross Section'] if x]
    n = len(vals)
    edges = lo + [spec['last_edge']]
    covrows = []
    for ln in open(_flux_open(spec['cov'])):
        p = [x.strip() for x in ln.rstrip().split(',')]
        if p and p[0].lstrip('-').isdigit():
            covrows.append([float(x) for x in p[1:1 + n]])
        if len(covrows) == n:
            break
    M = np.array(covrows)
    err = np.sqrt(np.clip(np.diag(M), 0, None))
    bins = [{'i': i, 'lo': edges[i], 'hi': edges[i + 1], 'center': 0.5 * (edges[i] + edges[i + 1]),
             'val': vals[i], 'err': float(err[i])} for i in range(n)]
    med = float(np.median([b['hi'] - b['lo'] for b in bins]))
    clipped = False
    for b in bins:
        if b['hi'] - b['lo'] > 4 * med:
            b['hi_true'] = b['hi']; b['hi'] = round(b['lo'] + med, 4)
            b['center'] = 0.5 * (b['lo'] + b['hi']); clipped = True
    xl, yl, yu = spec['xlabel'], spec['ylabel'], spec.get('yunit', '')
    dist = {
        'key': spec.get('key', 'dsigma'), 'slug': spec.get('key', 'dsigma'),
        'name': plotify(yl), 'name_tex': f'${yl}$',
        'xlabel': plotify(xl), 'xunit': spec.get('xunit', ''), 'xlabel_tex': f'${xl}$',
        'ylabel': plotify(yl), 'ylabel_plot': plotify(yl), 'ylabel_tex': f'${yl}$',
        'yunit': yu, 'yunit_tex': f'${tl(yu)}$' if yu else '',
        'nbins': n, 'is2d': False, 'bins': bins, 'nuisance_file': '',
        'scale_note': 'last bin is an integration overflow (shown truncated)' if clipped else None,
        'source': spec['source'], 'source_url': spec['source_url'], 'provenance': spec['provenance'],
    }
    dist['_release_cov'] = _cov_obj(M, [f"[{edges[i]:g},{edges[i + 1]:g}]" for i in range(n)],
                                    spec.get('cov_note', 'total covariance; row/col order below'))
    return [dist]


def _release_source_url(dists):
    """The URL for the whole release: the shared record when all distributions point
    at one file (Zenodo/arXiv), else the common parent directory (NUISANCE multi-file)."""
    urls = [x['source_url'] for x in dists if x.get('source_url')]
    if not urls:
        return ''
    if len(set(urls)) == 1:
        return urls[0]
    common = []
    for parts in zip(*(u.split('/') for u in urls)):
        if len(set(parts)) == 1:
            common.append(parts[0])
        else:
            break
    return '/'.join(common).replace('/blob/', '/tree/')   # github: a dir uses /tree/


def build_release_cov(spec, dists):
    """Attach a release-level covariance whose bin order matches the flattened
    distribution values (dist -> slices -> bins).  Source is a ROOT TMatrixTSym/TH2
    ('root'+'key') or a text matrix ('txt').  'fractional' -> multiply by value_i*value_j;
    'scale' -> constant factor.  sqrt(diag) is checked against the per-bin errors."""
    flat = []
    for d in dists:
        bins = d['bins'] if not d.get('is2d') else [b for s in d['slices'] for b in s['bins']]
        for b in bins:
            flat.append((d, b))
    if 'root' in spec:
        o = uproot.open(_flux_open(spec['root']))[spec['key']]
        M = _sym_from_packed(o) if 'TMatrix' in o.classname else np.asarray(o.values())
    else:
        M = _read_matrix_txt(spec['txt'], spec.get('txt_format'))
    M = M * spec.get('scale', 1.0)
    if spec.get('fractional'):
        v = np.array([b['val'] for _, b in flat])
        M = M * np.outer(v, v)
    if M.shape[0] != len(flat):
        raise ValueError(f"cov {M.shape} vs {len(flat)} flattened bins")
    err = np.array([b['err'] for _, b in flat])
    good = err > 0
    ratio = np.median(np.sqrt(np.clip(np.diag(M), 0, None))[good] / err[good]) if good.any() else 0
    if not 0.9 < ratio < 1.1:
        print(f"    !! cov sqrt(diag)/err median = {ratio:.3f} (expected ~1)")
    order = [(b['cat'] if b.get('cat') else f"{d['key']} [{b['lo']:g},{b.get('hi_true', b['hi']):g}]")
             for d, b in flat]
    return _cov_obj(M, order, spec['note'])


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


# forward-bin indices (cos>0) into the 25-bin true binning of T2K:2013nor, in the
# order cos-slice (th1..th4) x p_mu-ascending — matches the assembled distribution.
_2013NOR_FWD = [1, 6, 11, 16, 21, 2, 7, 12, 17, 22, 3, 8, 13, 18, 23, 4, 9, 14, 19, 24]


def build_2013nor(spec):
    """T2K 2013 numu CC-inclusive on carbon (ND280): four cos-theta slices
    (dxs_th1..4, 5 p_mu bins each) carrying values + errors, plus the released
    25x25 fractional covariance (stat+syst) restricted to the 20 forward bins and
    converted to absolute via value_i*value_j."""
    f = uproot.open(_flux_open(spec['root']))
    cos = [(0.0, 0.84), (0.84, 0.90), (0.90, 0.94), (0.94, 1.0)]
    ths = ['dxs_th1', 'dxs_th2', 'dxs_th3', 'dxs_th4']
    grouped, vflat, order = {}, [], []
    for (clo, chi), thk in zip(cos, ths):
        h = f[thk]; edges = h.axis().edges() / 1000.0        # MeV -> GeV/c
        vv, ee = h.values(), h.errors()
        grouped[(clo, chi)] = [(float(edges[i]), float(edges[i + 1]), float(vv[i]), float(ee[i]))
                               for i in range(len(vv))]
        for i in range(len(vv)):
            vflat.append(float(vv[i]))
            order.append(f"cos[{clo:g},{chi:g}] p[{edges[i]:g},{edges[i + 1]:g}]")
    out = _assemble_2d(grouped, {**spec, 'nuisance_file': spec['root']})

    def _m(key):
        o = f[key]; N = o.member('fNrows'); return np.array(o.member('fElements')).reshape(N, N)
    frac = _m('xs_stat_cov') + _m('xs_syst_cov')             # released fractional total
    v = np.array(vflat)
    cov = frac[np.ix_(_2013NOR_FWD, _2013NOR_FWD)] * np.outer(v, v)
    if out:
        out[0]['_release_cov'] = _cov_obj(cov, order,
            'total (stat+syst) covariance in (cm^2/nucleon/MeV)^2, from the released '
            'fractional covariance (forward bins) times value_i*value_j; row/col order below')
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
        'xlabel': plotify(xl), 'xunit': spec.get('xunit', ''), 'xlabel_tex': f'${xl}$',
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

def _mbar(var, xl, xu, ang=False, denom=None):
    """A MicroBooNE per-40Ar differential item for build_minerva_root: values in
    TotalUnc_<var> (bin content = xsec), covariance Cov_<var>. denom = the y-unit
    denominator ('(GeV/c)', 'GeV', '\\mathrm{deg}', or '' for dimensionless x)."""
    if denom is None:
        denom = r'\mathrm{deg}' if ang else '(GeV/c)'
    yu = r'10^{-38}cm^2/{}^{40}\mathrm{Ar}' + ('/' + denom if denom else '')
    return {'slug': var, 'label': '', 'hist': 'TotalUnc_' + var, 'cov': 'Cov_' + var,
            'xlabel': xl, 'xunit': xu, 'ylabel': r'\mathrm{d}\sigma/\mathrm{d}' + xl, 'yunit': yu}


REGISTRY = [
    {'bibtag': 'MINERvA:2020zzv', 'slug': 'minerva-2020zzv', 'source': 'arXiv',
     'note': 'numu CC inclusive differential cross sections d(sigma)/dpT and d(sigma)/dp_parallel '
             'on hydrocarbon (per nucleon), NuMI LE <Enu>~3.5 GeV. Muon-angle < 20 deg phase space. '
             'Values + total covariance from the arXiv ancillary release; each 1D projection '
             'carries its own covariance (the 2D d2sigma/dpTdp_par is in the release too).',
     'sources': [{'minerva_root': {
         'key': 'dsigma',
         'xlabel': r'p_{T\mu}', 'xunit': 'GeV/c',
         'ylabel': r'\mathrm{d}\sigma/\mathrm{d}p_{T\mu}', 'yunit': r'cm^2/(GeV/c)/nucleon',
         'items': [
             {'slug': 'ptmu', 'label': '',
              'root': 'data/datasets/sources/minerva-2020zzv/cov_fullUncertainty_ptmu_CCInclusive.root',
              'hist': 'ptmu_cross_section', 'cov': 'TotalCovariance',
              'xlabel': r'p_{T\mu}', 'xunit': 'GeV/c',
              'ylabel': r'\mathrm{d}\sigma/\mathrm{d}p_{T\mu}', 'yunit': r'cm^2/(GeV/c)/nucleon'},
             {'slug': 'pzmu', 'label': '',
              'root': 'data/datasets/sources/minerva-2020zzv/cov_fullUncertainty_pzmu_CCInclusive.root',
              'hist': 'pzmu_cross_section', 'cov': 'TotalCovariance',
              'xlabel': r'p_{\parallel\mu}', 'xunit': 'GeV/c',
              'ylabel': r'\mathrm{d}\sigma/\mathrm{d}p_{\parallel\mu}', 'yunit': r'cm^2/(GeV/c)/nucleon'}],
         'source': 'arXiv', 'source_url': 'https://arxiv.org/abs/2002.12496',
         'provenance': 'MINERvA numu CC inclusive dsigma/dpT and dsigma/dp_parallel on hydrocarbon '
                       '(NuMI LE <Enu>~3.5 GeV, arXiv:2002.12496) · per nucleon · muon angle < 20 deg '
                       '· total covariance per projection (block-diagonal) · from the arXiv ancillary '
                       'release · nothing digitized'}}]},
    {'bibtag': 'MINERvA:2018hqn', 'slug': 'minerva-2018hqn', 'source': 'arXiv',
     'note': 'numu CC quasielastic-like differential cross sections on hydrocarbon (per nucleon), '
             'NuMI LE. Values + total covariance from the arXiv ancillary release (QE-like signal '
             'definition); each observable carries its own covariance.',
     'sources': [{'minerva_root': {
         'key': 'dsigma',
         'xlabel': r'Q^2_{QE}', 'xunit': r'(GeV/c)^2',
         'ylabel': r'\mathrm{d}\sigma/\mathrm{d}Q^2_{QE}', 'yunit': r'cm^2/(GeV/c)^2/nucleon',
         'items': [
             {'slug': 'q2qe', 'label': '',
              'root': 'data/datasets/sources/minerva-2018hqn/cov_fullUncertainty_q2qe_qelike.root',
              'hist': 'q2qe_cross_section', 'cov': 'TotalCovariance',
              'xlabel': r'Q^2_{QE}', 'xunit': r'(GeV/c)^2',
              'ylabel': r'\mathrm{d}\sigma/\mathrm{d}Q^2_{QE}', 'yunit': r'cm^2/(GeV/c)^2/nucleon'},
             {'slug': 'ptmu', 'label': '',
              'root': 'data/datasets/sources/minerva-2018hqn/cov_fullUncertainty_ptmu_qelike.root',
              'hist': 'ptmu_cross_section', 'cov': 'TotalCovariance',
              'xlabel': r'p_{T\mu}', 'xunit': 'GeV/c',
              'ylabel': r'\mathrm{d}\sigma/\mathrm{d}p_{T\mu}', 'yunit': r'cm^2/(GeV/c)/nucleon'},
             {'slug': 'pzmu', 'label': '',
              'root': 'data/datasets/sources/minerva-2018hqn/cov_fullUncertainty_pzmu_qelike.root',
              'hist': 'pzmu_cross_section', 'cov': 'TotalCovariance',
              'xlabel': r'p_{z\mu}', 'xunit': 'GeV/c',
              'ylabel': r'\mathrm{d}\sigma/\mathrm{d}p_{z\mu}', 'yunit': r'cm^2/(GeV/c)/nucleon'},
             {'slug': 'enuqe', 'label': '',
              'root': 'data/datasets/sources/minerva-2018hqn/cov_fullUncertainty_enuqe_qelike.root',
              'hist': 'enuqe_cross_section', 'cov': 'TotalCovariance',
              'xlabel': r'E_\nu^{QE}', 'xunit': 'GeV',
              'ylabel': r'\sigma(E_\nu^{QE})', 'yunit': r'cm^2/nucleon'}],
         'source': 'arXiv', 'source_url': 'https://arxiv.org/abs/1811.02774',
         'provenance': 'MINERvA numu CC quasielastic-like cross sections on hydrocarbon (NuMI LE, '
                       'arXiv:1811.02774) · per nucleon · QE-like signal definition · total '
                       'covariance per observable (block-diagonal) · from the arXiv ancillary '
                       'release · nothing digitized'}}]},
    {'bibtag': 'MINERvA:2023ikp', 'slug': 'minerva-2023ikp', 'source': 'arXiv',
     'note': 'antinumu CC multi-neutron (>=2 neutrons, low available energy) dsigma/dpT on '
             'hydrocarbon (per nucleon), NuMI. Values + covariance from the arXiv ancillary CSV.',
     'sources': [{'minerva_csv': {
         'data': 'data/datasets/sources/minerva-2023ikp/crossSection.csv',
         'cov': 'data/datasets/sources/minerva-2023ikp/crossSectionCovariance.csv',
         'last_edge': 1.5, 'key': 'dsdpt',
         'xlabel': r'p_{T\mu}', 'xunit': 'GeV/c',
         'ylabel': r'\mathrm{d}\sigma/\mathrm{d}p_{T\mu}', 'yunit': r'10^{-39}cm^2/(GeV/c)/nucleon',
         'source': 'arXiv', 'source_url': 'https://arxiv.org/abs/2310.17014',
         'cov_note': 'total covariance in (10^-39 cm^2 c/GeV/nucleon)^2; row/col order below',
         'provenance': 'MINERvA antinumu CC multi-neutron dsigma/dpT_mu on hydrocarbon (NuMI, '
                       'arXiv:2310.17014) · per nucleon · total covariance · from the arXiv '
                       'ancillary CSV · nothing digitized'}}]},
    {'bibtag': 'MicroBooNE:2025pvb', 'slug': 'microboone-2025pvb', 'source': 'arXiv',
     'note': 'nu_e + nubar_e CC single-charged-pion differential cross sections on argon '
             '(per nucleon), NuMI off-axis (FHC+RHC combined). Values + full covariance from the '
             'arXiv ancillary release; apply the release smearing matrix A_C before model '
             'comparison.',
     'flux': {'blocks': [
         {'root': 'data/datasets/sources/microboone-2025pvb/nue_flux.root',
          'hists': [('nue_CV_AV_TPC_5MeV_bin', 'nue')]},
         {'root': 'data/datasets/sources/microboone-2025pvb/nuebar_flux.root',
          'hists': [('nuebar_CV_AV_TPC_5MeV_bin', 'nuebar')]}],
         'note': 'MicroBooNE NuMI nu_e and nubar_e flux (POT-weighted FHC+RHC), from the '
                 'release nue_flux.root / nuebar_flux.root'},
     'sources': [{'minerva_root': {
         'root': 'data/datasets/sources/microboone-2025pvb/release.root', 'cov': 'h_total_covmat',
         'xlabel': r'E_e', 'xunit': 'GeV', 'ylabel': r'\mathrm{d}\sigma/\mathrm{d}E_e',
         'yunit': r'10^{-39}cm^2/GeV/nucleon', 'key': 'dsigma',
         'items': [
             {'slug': 'Ee', 'label': '', 'hist': 'hSlice_E_{e}', 'xlabel': r'E_e', 'xunit': 'GeV',
              'ylabel': r'\mathrm{d}\sigma/\mathrm{d}E_e', 'yunit': r'10^{-39}cm^2/GeV/nucleon'},
             {'slug': 'cos_e', 'label': '', 'hist': 'hSlice_cos(#theta_{e})', 'xlabel': r'\cos\theta_e',
              'xunit': '', 'ylabel': r'\mathrm{d}\sigma/\mathrm{d}\cos\theta_e', 'yunit': r'10^{-39}cm^2/nucleon'},
             {'slug': 'cos_pi', 'label': '', 'hist': 'hSlice_cos(#theta_{#pi})', 'xlabel': r'\cos\theta_\pi',
              'xunit': '', 'ylabel': r'\mathrm{d}\sigma/\mathrm{d}\cos\theta_\pi', 'yunit': r'10^{-39}cm^2/nucleon'},
             {'slug': 'cos_epi', 'label': '', 'hist': 'hSlice_cos(#theta_{e#pi})',
              'xlabel': r'\cos\theta_{e\pi}', 'xunit': '',
              'ylabel': r'\mathrm{d}\sigma/\mathrm{d}\cos\theta_{e\pi}', 'yunit': r'10^{-39}cm^2/nucleon'}],
         'source': 'arXiv', 'source_url': 'https://arxiv.org/abs/2503.23384',
         'provenance': 'MicroBooNE nu_e+nubar_e CC1pi differential cross sections on argon (NuMI '
                       'off-axis FHC+RHC, arXiv:2503.23384) · per nucleon · full covariance over all '
                       'observables; apply the release smearing matrix A_C before comparison · from '
                       'the arXiv ancillary release · nothing digitized'}}]},
    {'bibtag': 'MicroBooNE:2023cmw', 'slug': 'microboone-2023cmw', 'source': 'arXiv',
     'note': 'numu CC1p0pi multidifferential cross sections on argon (per Ar), BNB. Values + '
             'covariance from the arXiv ancillary release; apply the release smearing matrix Ac '
             'before model comparison; BNB flux is the standard MicroBooNE product (not in this '
             'release).',
     'sources': [{'minerva_root': {
         'root': 'data/datasets/sources/microboone-2023cmw/release.root',
         'xlabel': r'\delta p_T', 'xunit': 'GeV/c', 'ylabel': r'\mathrm{d}\sigma/\mathrm{d}\delta p_T',
         'yunit': r'10^{-38}cm^2/{}^{40}\mathrm{Ar}/(GeV/c)', 'key': 'dsigma',
         'items': [
             _mbar('MuonCosTheta', r'\cos\theta_\mu', '', denom=''),
             _mbar('DeltaPT', r'\delta p_T', 'GeV/c'),
             _mbar('DeltaAlphaT', r'\delta\alpha_T', 'deg', ang=True),
             _mbar('DeltaPhiT', r'\delta\phi_T', 'deg', ang=True),
             _mbar('DeltaPtx', r'\delta p_{Tx}', 'GeV/c'),
             _mbar('ECal', r'E_\mathrm{cal}', 'GeV', denom='GeV')],
         'source': 'arXiv', 'source_url': 'https://arxiv.org/abs/2301.03700',
         'provenance': 'MicroBooNE numu CC1p0pi multidifferential cross sections on argon (BNB, '
                       'arXiv:2301.03700, Phys.Rev.D 108 053002) · per 40Ar · total covariance per '
                       'observable (block-diagonal); apply the release smearing matrix Ac before '
                       'comparison · from the arXiv ancillary release · nothing digitized'}}]},
    {'bibtag': 'MicroBooNE:2023krv', 'slug': 'microboone-2023krv', 'source': 'arXiv',
     'note': 'numu CC1p0pi generalized (3D) kinematic-imbalance cross sections on argon '
             '(per Ar), BNB. Values + covariance from the arXiv ancillary release; apply the '
             'release smearing matrix Ac to a model before comparison; BNB flux is the standard '
             'MicroBooNE product (not in this release).',
     'sources': [{'minerva_root': {
         'root': 'data/datasets/sources/microboone-2023krv/release.root',
         'xlabel': r'\delta p_n', 'xunit': 'GeV/c', 'ylabel': r'\mathrm{d}\sigma/\mathrm{d}\delta p_n',
         'yunit': r'10^{-38}cm^2/{}^{40}\mathrm{Ar}/(GeV/c)', 'key': 'dsigma',
         'items': [
             _mbar('DeltaPn', r'\delta p_n', 'GeV/c'),
             _mbar('DeltaAlpha3Dq', r'\delta\alpha_{3D,q}', 'deg', ang=True),
             _mbar('DeltaPhi3D', r'\delta\phi_{3D}', 'deg', ang=True),
             _mbar('DeltaPnPar', r'\delta p_{n,\parallel}', 'GeV/c'),
             _mbar('DeltaPnPerp', r'\delta p_{n,\perp}', 'GeV/c'),
             _mbar('DeltaPnPerpx', r'\delta p_{n,\perp x}', 'GeV/c'),
             _mbar('DeltaPnPerpy', r'\delta p_{n,\perp y}', 'GeV/c')],
         'source': 'arXiv', 'source_url': 'https://arxiv.org/abs/2310.06082',
         'provenance': 'MicroBooNE numu CC1p0pi generalized kinematic-imbalance cross sections on '
                       'argon (BNB, arXiv:2310.06082) · per 40Ar · total covariance per observable '
                       '(block-diagonal); apply the release smearing matrix Ac before comparison · '
                       'from the arXiv ancillary release · nothing digitized'}}]},
    {'bibtag': 'MicroBooNE:2023tzj', 'slug': 'microboone-2023tzj', 'source': 'arXiv',
     'note': 'numu CC1p0pi single-transverse-kinematic-imbalance cross sections on argon '
             '(per Ar), BNB. Values + covariance from the arXiv ancillary release; a smearing '
             'matrix Ac (in the release) must be applied to a model before comparison, and the '
             'BNB flux is the standard MicroBooNE product (not in this release).',
     'sources': [{'minerva_root': {
         'root': 'data/datasets/sources/microboone-2023tzj/release.root',
         'xlabel': r'\delta p_T', 'xunit': 'GeV/c',
         'ylabel': r'\mathrm{d}\sigma/\mathrm{d}\delta p_T', 'yunit': r'10^{-38}cm^2/{}^{40}\mathrm{Ar}/(GeV/c)',
         'key': 'dsigma',
         'items': [
             {'slug': 'dpT', 'label': '', 'hist': 'TotalUnc_DeltaPT', 'cov': 'Cov_DeltaPT',
              'xlabel': r'\delta p_T', 'xunit': 'GeV/c',
              'ylabel': r'\mathrm{d}\sigma/\mathrm{d}\delta p_T', 'yunit': r'10^{-38}cm^2/{}^{40}\mathrm{Ar}/(GeV/c)'},
             {'slug': 'dalphaT', 'label': '', 'hist': 'TotalUnc_DeltaAlphaT', 'cov': 'Cov_DeltaAlphaT',
              'xlabel': r'\delta\alpha_T', 'xunit': 'deg',
              'ylabel': r'\mathrm{d}\sigma/\mathrm{d}\delta\alpha_T', 'yunit': r'10^{-38}cm^2/{}^{40}\mathrm{Ar}/\mathrm{deg}'},
             {'slug': 'dpTx', 'label': '', 'hist': 'TotalUnc_DeltaPtx', 'cov': 'Cov_DeltaPtx',
              'xlabel': r'\delta p_{Tx}', 'xunit': 'GeV/c',
              'ylabel': r'\mathrm{d}\sigma/\mathrm{d}\delta p_{Tx}', 'yunit': r'10^{-38}cm^2/{}^{40}\mathrm{Ar}/(GeV/c)'}],
         'source': 'arXiv', 'source_url': 'https://arxiv.org/abs/2301.03706',
         'provenance': 'MicroBooNE numu CC1p0pi transverse-kinematic-imbalance cross sections on '
                       'argon (BNB, arXiv:2301.03706) · per 40Ar · total covariance per observable '
                       '(block-diagonal); apply the release smearing matrix Ac to a model before '
                       'comparison · from the arXiv ancillary release · nothing digitized'}}]},
    {'bibtag': 'MicroBooNE:2025aiw', 'slug': 'microboone-2025aiw', 'source': 'arXiv',
     'note': 'nu_e CC differential cross sections on argon (per nucleon) with final-state '
             'protons; NuMI off-axis, FHC+RHC combined. Values + covariance from the arXiv '
             'ancillary release; the NuMI off-axis flux is not in the release.',
     'sources': [{'minerva_root': {
         'root': 'data/datasets/sources/microboone-2025aiw/release.root',
         'xlabel': r'E_e', 'xunit': 'GeV', 'ylabel': r'\mathrm{d}\sigma/\mathrm{d}E_e',
         'yunit': r'10^{-39}cm^2/GeV/nucleon', 'key': 'dsigma',
         'items': [
             {'slug': 'Ee', 'label': '', 'hist': 'hSlice_E_{e}', 'cov': 'hCov_E_{e}',
              'xlabel': r'E_e', 'xunit': 'GeV', 'ylabel': r'\mathrm{d}\sigma/\mathrm{d}E_e',
              'yunit': r'10^{-39}cm^2/GeV/nucleon'},
             {'slug': 'Evis', 'label': '', 'hist': 'hSlice_E_{vis}', 'cov': 'hCov_E_{vis}',
              'xlabel': r'E_\mathrm{vis}', 'xunit': 'GeV',
              'ylabel': r'\mathrm{d}\sigma/\mathrm{d}E_\mathrm{vis}',
              'yunit': r'10^{-39}cm^2/GeV/nucleon'},
             {'slug': 'costheta_ep', 'label': '', 'hist': 'hSlice_cos#theta_{ep}',
              'cov': 'hCov_cos#theta_{ep}', 'xlabel': r'\cos\theta_{ep}', 'xunit': '',
              'ylabel': r'\mathrm{d}\sigma/\mathrm{d}\cos\theta_{ep}', 'yunit': r'10^{-39}cm^2/nucleon'}],
         'source': 'arXiv', 'source_url': 'https://arxiv.org/abs/2511.17342',
         'provenance': 'MicroBooNE nu_e CC differential cross sections on argon with final-state '
                       'protons (NuMI off-axis FHC+RHC, arXiv:2511.17342) · per nucleon · total '
                       'covariance per observable (block-diagonal) · from the arXiv ancillary '
                       'release · nothing digitized'}}]},
    {'bibtag': 'MINERvA:2026apf', 'slug': 'minerva-2026apf', 'source': 'arXiv',
     'note': 'CC-inclusive antineutrino dsigma/dpT per nucleon on C, CH, Fe, Pb; from the '
             'arXiv ancillary ROOT release.',
     'flux': {'root': 'data/datasets/sources/minerva-2026apf/release.root',
              'hists': [('flux_ptmu_carbon', 'numubar_C'), ('flux_ptmu_hydrocarbon', 'numubar_CH'),
                        ('flux_ptmu_iron', 'numubar_Fe'), ('flux_ptmu_lead', 'numubar_Pb')],
              'note': 'NuMI medium-energy antineutrino flux per target, from the release'},
     'sources': [{'minerva_root': {
         'root': 'data/datasets/sources/minerva-2026apf/release.root',
         'xlabel': r'p_T^\mu', 'xunit': 'GeV/c',
         'ylabel': r'\mathrm{d}\sigma/\mathrm{d}p_T^\mu', 'yunit': r'cm^2/nucleon/(GeV/c)',
         'key': 'dsdpt',
         'items': [{'slug': 'C', 'label': r'\mathrm{C}', 'hist': 'xsec_ptmu_carbon',
                    'cov': 'xsec_ptmu_carbon_covariance'},
                   {'slug': 'CH', 'label': r'\mathrm{CH}', 'hist': 'xsec_ptmu_hydrocarbon',
                    'cov': 'xsec_ptmu_hydrocarbon_covariance'},
                   {'slug': 'Fe', 'label': r'\mathrm{Fe}', 'hist': 'xsec_ptmu_iron',
                    'cov': 'xsec_ptmu_iron_covariance'},
                   {'slug': 'Pb', 'label': r'\mathrm{Pb}', 'hist': 'xsec_ptmu_lead',
                    'cov': 'xsec_ptmu_lead_covariance'}],
         'source': 'arXiv', 'source_url': 'https://arxiv.org/abs/2604.07091',
         'provenance': 'MINERvA CC-inclusive antinumu dsigma/dpT_mu on C/CH/Fe/Pb (NuMI ME RHC, '
                       'arXiv:2604.07091) · per nucleon · total (stat+syst) covariance per target '
                       '(block-diagonal) · from the arXiv ancillary ROOT release · nothing digitized'}}]},
    {'bibtag': 'T2K:2013nor', 'slug': 't2k-2013nor', 'source': 'T2K',
     'note': 'Data release recovered from the Web Archive of the (defunct) t2k-experiment.org.',
     'flux': {'root': 'data/datasets/sources/t2k-2013nor/data_release.root',
              'hists': [('flux_numu', 'numu'), ('flux_numubar', 'numubar'),
                        ('flux_nue', 'nue'), ('flux_nueb', 'nueb')],
              'note': 'T2K ND280 flux for this measurement (all flavours), from the data '
                      'release data_release.root'},
     'sources': [{'2013nor': {
         'root': 'data/datasets/sources/t2k-2013nor/data_release.root',
         'xlabel': r'p_\mu', 'xunit': 'GeV/c',
         'ylabel': r'\mathrm{d}^2\sigma/\mathrm{d}p_\mu\mathrm{d}\cos\theta_\mu',
         'yunit': r'cm^2/nucleon/MeV', 'slicevar': r'\cos\theta_\mu',
         'source': 'T2K',
         'source_url': 'http://web.archive.org/web/20190929033629/http://t2k-experiment.org/'
                       'results/nd280data-numu-cc-inc-xs-on-c-2013/',
         'provenance': 'T2K numu CC-inclusive on carbon (ND280/FGD1, arXiv:1302.4908, '
                       'Phys.Rev.D 87 092003) · forward bins only (backward bin is model '
                       'extrapolation) · per-bin error = sqrt(diag(covariance)) · nothing digitized'}}]},
    {'bibtag': 'T2K:2019zqh', 'slug': 't2k-2019zqh', 'source': 'T2K',
     'note': 'Values + 2x2 covariance transcribed from the paper (Table III); the legacy '
             'release page ships no data files.',
     'flux': _FLUX_SK_BOTH,
     'covariance': {'txt': 'data/datasets/sources/t2k-2019zqh/covariance.csv',
                    'note': 'total (stat+syst) covariance of the nu and nubar NCQE-like cross '
                            'sections in (10^-38 cm^2/oxygen)^2, from Table III; row/col order below'},
     'sources': [{'values': {
         'key': 'sigma', 'ylabel': r'\sigma_\mathrm{NCQE}', 'yunit': r'10^{-38}cm^2/{}^{16}\mathrm{O}',
         'source': 'T2K',
         'source_url': 'http://web.archive.org/web/2020/http://t2k-experiment.org/results/'
                       '2019-NCQE-nuclear-gamma',
         'provenance': 'T2K NCQE-like on oxygen (Super-K, arXiv:1910.09439, Phys.Rev.D 100 '
                       '112009) · flux-averaged single values · 2x2 stat+syst covariance from '
                       'Table III · nothing digitized',
         'items': [{'points': [
             {'cat': r'\nu\ \mathrm{(FHC)}', 'val': 1.70, 'stat': 0.17, 'syst_up': 0.51, 'syst_down': 0.38},
             {'cat': r'\bar\nu\ \mathrm{(RHC)}', 'val': 0.98, 'stat': 0.16, 'syst_up': 0.26, 'syst_down': 0.19}]}]}}]},
    {'bibtag': 'T2K:2019dgm', 'slug': 't2k-2019dgm', 'source': 'T2K',
     'note': 'On-axis measurement (INGRID complex, restricted phase space theta_mu<45 deg, '
             'p_mu>0.4 GeV/c); values taken from the paper.',
     'flux': {'root': 'data/datasets/sources/t2k-2023qjb/analysis_flux.root',
              'hists': [('ingrid_flux_fine_nominal', 'numu_nominal'),
                        ('ingrid_flux_fine_postfit', 'numu_postfit')],
              'note': 'T2K on-axis INGRID numu flux (nominal + postfit) — the shared T2K '
                      'on-axis flux, from the on/off-axis data release (2023qjb '
                      'analysis_flux.root)'},
     'sources': [
         {'values': {
             'key': 'sigma', 'ylabel': r'\sigma_\mathrm{CC}', 'yunit': r'10^{-38}cm^2/nucleon',
             'items': [{'slug': 'xsec', 'points': [
                 {'cat': r'$\mathrm{H_2O}$', 'val': 0.840, 'stat': 0.010, 'syst_up': 0.10, 'syst_down': 0.08},
                 {'cat': r'$\mathrm{CH}$', 'val': 0.817, 'stat': 0.007, 'syst_up': 0.11, 'syst_down': 0.08},
                 {'cat': r'$\mathrm{Fe}$', 'val': 0.859, 'stat': 0.003, 'syst_up': 0.12, 'syst_down': 0.10}]}],
             'source': 'T2K',
             'source_url': 'http://web.archive.org/web/2020/http://t2k-experiment.org/results/'
                           'ingriddata-numu-cc-inc-xs-on-h2o-2018',
             'provenance': 'T2K numu CC-inclusive on H2O/CH/Fe (on-axis INGRID complex, '
                           'arXiv:1904.09611, PTEP 2019 093C02) · flux-integrated per-nucleon '
                           'cross sections, restricted PS theta_mu<45 deg, p_mu>0.4 GeV/c · '
                           'stat + asymmetric syst · nothing digitized'}},
         {'values': {
             'key': 'ratio', 'ylabel': r'\sigma\ \mathrm{ratio}', 'yunit': '',
             'items': [{'slug': 'ratio', 'points': [
                 {'cat': r'$\sigma_\mathrm{H_2O}/\sigma_\mathrm{CH}$', 'val': 1.028, 'stat': 0.016, 'syst_up': 0.053, 'syst_down': 0.053},
                 {'cat': r'$\sigma_\mathrm{Fe}/\sigma_\mathrm{H_2O}$', 'val': 1.023, 'stat': 0.012, 'syst_up': 0.058, 'syst_down': 0.058},
                 {'cat': r'$\sigma_\mathrm{Fe}/\sigma_\mathrm{CH}$', 'val': 1.049, 'stat': 0.010, 'syst_up': 0.043, 'syst_down': 0.043}]}],
             'source': 'T2K',
             'source_url': 'http://web.archive.org/web/2020/http://t2k-experiment.org/results/'
                           'ingriddata-numu-cc-inc-xs-on-h2o-2018',
             'provenance': 'T2K numu CC-inclusive cross-section ratios among H2O/CH/Fe (on-axis '
                           'INGRID complex, arXiv:1904.09611, PTEP 2019 093C02) · stat + syst '
                           '(quadrature) · nothing digitized'}}]},
    {'bibtag': 'T2K:2014hih', 'slug': 't2k-2014hih', 'source': 'arXiv',
     'note': 'sigma(E_nu) central values digitized from Fig 7 (analytical digitizer, overlay '
             'verified; the 5 points flux-integrate to 0.855 vs the paper flux-integrated '
             '0.83). The paper prints a fractional covariance (relative to the pre-fit NEUT '
             'nominal); it is made absolute with the digitized pre-fit NEUT-binned curve, so '
             'the covariance and correlations are exact. CCQE-like, model-dependent '
             '(Smith-Moniz) extraction.',
     'flux': _FLUX_FHC,
     'sources': [{'sigma_enu': {
         'data': 'data/datasets/sources/t2k-2014hih/sigma_enu.csv',
         'cov': 'data/datasets/sources/t2k-2014hih/frac_cov.csv',
         'key': 'sigma_enu', 'xlabel': r'E_\nu', 'xunit': 'GeV',
         'ylabel': r'\sigma_\mathrm{CCQE}(E_\nu)', 'yunit': r'10^{-38}cm^2/\mathrm{neutron}',
         'source': 'arXiv', 'source_url': 'https://arxiv.org/abs/1411.6264',
         'provenance': 'T2K numu CCQE(-like) on carbon (ND280/FGD1, arXiv:1411.6264, '
                       'Phys.Rev.D 92 112003) · sigma(E_nu) per target neutron · central '
                       'values DIGITIZED from Fig 7 (analytical digitizer) · covariance = '
                       'fractional covariance (Table) x pre-fit NEUT nominal_i*nominal_j',
         'cov_note': 'covariance in (10^-38 cm^2/neutron)^2, from the paper fractional '
                     'covariance (relative to the pre-fit NEUT nominal) times the digitized '
                     'nominal_i*nominal_j; row/col order below',
         'digitization': {
             'original': '/digitize/t2k-2014hih/original.png',
             'overlay': '/digitize/t2k-2014hih/overlay.png',
             'note': 'Fig 7 of the paper (left); our extracted points + errors overlaid in '
                     'cyan (right); the digitized data below. Values are the black cross '
                     'markers; error bars are sqrt(frac_ii) x the pre-fit NEUT nominal.'}}}]},
    {'bibtag': 'T2K:2016cbz', 'slug': 't2k-2016cbz',
     'flux': {'root': 'data/T2K/CC1pip/H2O/nd280data-numu-cc1pi-xs-on-h2o-2015.root',
              'hists': [('numu_flux', 'numu')],
              'note': "T2K ND280 numu flux prediction, from this measurement's own data "
                      "release (numu_flux) via NUISANCE"},
     'sources': [{'root': 'data/T2K/CC1pip/H2O/nd280data-numu-cc1pi-xs-on-h2o-2015.root'}]},
    {'bibtag': 'T2K:2018rnz', 'slug': 't2k-2018rnz', 'flux': _FLUX_FHC,
     'sources': [
         {'root': 'data/T2K/CC0pi/STV/dptResults.root', 'name': 'dpt'},
         {'root': 'data/T2K/CC0pi/STV/dphitResults.root', 'name': 'dphit'},
         {'root': 'data/T2K/CC0pi/STV/datResults.root', 'name': 'dat'}]},
    {'bibtag': 'T2K:2021naz', 'slug': 't2k-2021naz',
     'flux': {'root': 'data/T2K/CC1pipNp_STV/xsec_dpTT.root',
              'hists': [('flux_best_fit', 'numu_bestfit')],
              'note': "T2K ND280 numu flux prediction (best fit), from this measurement's own "
                      "data release (flux_best_fit) via NUISANCE"},
     'sources': [
         {'root': 'data/T2K/CC1pipNp_STV/xsec_dpTT.root', 'name': 'dpTT'},
         {'root': 'data/T2K/CC1pipNp_STV/xsec_daT.root', 'name': 'daT'},
         {'root': 'data/T2K/CC1pipNp_STV/xsec_pN.root', 'name': 'pN'}]},
    {'bibtag': 'T2K:2016soz', 'slug': 't2k-2016soz', 'flux': _FLUX_FHC,
     'sources': [{'txt': 'data/T2K/CCCOH/C12_Enu_1bin.txt',
                  'labels': {'key': 'Enu', 'xlabel': r'E_\nu', 'xunit': 'GeV',
                             'ylabel': r'\sigma_{\mathrm{coh}}', 'yunit': r'cm^2/{}^{12}C'}}]},
    {'bibtag': 'T2K:2020lrr', 'slug': 't2k-2020lrr', 'flux': _FLUX_BOTH,
     'covariance': {'txt': 'data/T2K/CCinc/nue_2019/fract_covar_both.txt', 'fractional': True,
                    'note': 'fractional covariance across all reported bins, from the NUISANCE '
                            'release fract_covar_both.txt (converted to absolute via '
                            'value_i*value_j); row/col order below'},
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
    {'bibtag': 'T2K:2016jor', 'slug': 't2k-2016jor', 'flux': _FLUX_FHC,
     'sources': [{'slices2d': {
         'text': 'data/T2K/CC0pi/cross-section_analysisI.txt',
         'cov': 'data/T2K/CC0pi/T2K_CC0PI_2DPmuCosmu_Data.root', 'cov_key': 'analysis1_totcov',
         'xlabel': r'p_\mu', 'xunit': 'GeV',
         'ylabel': r'\mathrm{d}^2\sigma/\mathrm{d}p_\mu\mathrm{d}\cos\theta_\mu',
         'yunit': r'10^{-38}\ cm^2/GeV/nucleon'}}]},
    {'bibtag': 'T2K:2018lnf', 'slug': 't2k-2018lnf',
     'flux': {'root': 'data/T2K/CCinc/nd280data-numu-cc-inc-xs-on-c-2018/histograms.root',
              'hists': [('hflux', 'numu')],
              'note': "T2K ND280 numu flux prediction, from this measurement's own data "
                      "release (hflux) via NUISANCE"},
     'covariance': {'txt': 'data/T2K/CCinc/nd280data-numu-cc-inc-xs-on-c-2018/'
                           'covariance_matrix_neut.txt', 'txt_format': 'pipe', 'scale': 1e78,
                    'note': 'covariance matrix from the NUISANCE release '
                            'covariance_matrix_neut.txt (in (10^-39)^2 units to match the '
                            'reported values); row/col order below'},
     'sources': [{'slices2d_txt': {
         'text': 'data/T2K/CCinc/nd280data-numu-cc-inc-xs-on-c-2018/data_unfold_with_neut.txt',
         'xlabel': r'p_\mu', 'xunit': 'GeV/c',
         'ylabel': r'\mathrm{d}^2\sigma/\mathrm{d}\cos\theta_\mu\mathrm{d}p_\mu',
         'yunit': r'10^{-39}\ cm^2/(GeV/c)/nucleon'}}]},
    {'bibtag': 'T2K:2020jav', 'slug': 't2k-2020jav', 'flux': _FLUX_FHC,
     'covariance': {'root': 'data/T2K/CC0pi/JointO-C/covmatrix_reg.root',
                    'key': 'covmatrixOCratio',
                    'note': 'covariance of the O/C cross-section ratio (regularised), from the '
                            'NUISANCE release covmatrix_reg.root; row/col order below'},
     'sources': [{'slices2d_binned': {
         'binning': 'data/T2K/CC0pi/JointO-C/Binning.txt',
         'data': 'data/T2K/CC0pi/JointO-C/cc0pi_xsec_O-C-ratio_reg.txt',
         'vcol': 5, 'ecol': 6,          # ratio value, ratio error
         'key': 'oc_ratio', 'slug': 'oc_ratio',
         'xlabel': r'p_\mu', 'xunit': 'GeV/c',
         'ylabel': r'\sigma(\mathrm{O})/\sigma(\mathrm{C})', 'yunit': ''}}]},
    {'bibtag': 'T2K:2023qjb', 'slug': 't2k-2023qjb',
     'flux': {'root': 'data/datasets/sources/t2k-2023qjb/analysis_flux.root',
              'hists': [('nd280_flux_fine_nominal', 'nd280_nominal'),
                        ('nd280_flux_fine_postfit', 'nd280_postfit'),
                        ('ingrid_flux_fine_nominal', 'ingrid_nominal'),
                        ('ingrid_flux_fine_postfit', 'ingrid_postfit')],
              'note': 'T2K ND280 (2.5deg off-axis) and INGRID (on-axis) flux predictions '
                      '(nominal + postfit) for this joint on/off-axis measurement, from the '
                      'neutrino_data release analysis_flux.root'},
     'sources': [{'joint2d': {
         'data': _ND + 'xsec_data_mc.csv', 'cov': _ND + 'cov_matrix.csv',
         'vcol': 1, 'pdiv': 1000.0,        # data column; p MeV/c -> GeV/c
         'detectors': [{'name': 'ND280', 'file': _ND + 'nd280_analysis_binning.csv'},
                       {'name': 'INGRID', 'file': _ND + 'ingrid_analysis_binning.csv'}],
         'xlabel': r'p_\mu', 'xunit': 'GeV/c',
         'ylabel': r'\mathrm{d}^2\sigma/\mathrm{d}p_\mu\mathrm{d}\cos\theta_\mu',
         'yunit': r'cm^2/GeV',
         'nuisance_file': 'neutrino_data/data/T2K/CrossSection/PRD.108.112009/'
                          'onoffaxis_data_release/',
         'source': 'NUISANCE',
         'source_url': 'https://github.com/NUISANCEMC/neutrino_data/tree/main/data/T2K/'
                       'CrossSection/PRD.108.112009/onoffaxis_data_release'}}]},
    {'bibtag': 'T2K:2020sbd', 'slug': 't2k-2020sbd', 'flux': _FLUX_BOTH,
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
    {'bibtag': 'T2K:2019ddy', 'slug': 't2k-2019ddy', 'flux': _FLUX_RHC,
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
     'flux': {'csv': 'data/datasets/sources/t2k-2025smz/flux.csv', 'ecol': (1, 2),
              'fcol': [(3, 'nue_best_fit'), (4, 'nue_nominal')],
              'note': 'T2K nu_e flux prediction (best-fit and nominal) for the nue CC1pi+ '
                      'measurement, from the Zenodo data release flux.csv'},
     'sources': [{'zenodo3d': {
         'dir': 'data/datasets/sources/t2k-2025smz',
         'xlabel': r'p_e', 'xunit': 'GeV/c',
         'ylabel': r'\mathrm{d}^3\sigma/\mathrm{d}p_e\,\mathrm{d}\cos\theta_e\,\mathrm{d}p_\pi',
         'yunit': r'cm^2/nucleon/(GeV/c)^2',
         'source': 'Zenodo',
         'source_url': 'https://zenodo.org/records/15316318',
         'provenance': 'T2K nu_e CC1pi+ triple-differential cross section on carbon '
                       '(Zenodo 10.5281/zenodo.15316318, arXiv:2505.00516) · '
                       'per-bin error = sqrt(diag(covariance)) · nothing digitized'}}]},
    {'bibtag': 'T2K:2025wde', 'slug': 't2k-2025wde', 'source': 'Zenodo',
     'flux': {'root': 'data/datasets/sources/t2k-2025wde/flux_release.root',
              'hists': [('enu_numu', 'numu'), ('enu_numub', 'numubar'),
                        ('enu_nue', 'nue'), ('enu_nueb', 'nueb')],
              'note': 'T2K postfit flux prediction for all flavours (numu, numubar, nue, '
                      'nueb) for the NC1pi+ measurement, from the Zenodo flux_release.root'},
     'sources': [{'bracket2d': {
         'dir': 'data/datasets/sources/t2k-2025wde',
         'result': 'result_with_bins.csv', 'cov': 'covariance_matrix.csv',
         'result_scale': 1e-40, 'cov_scale': 1e-82,
         'xlabel': r'p_\pi', 'xunit': 'GeV/c', 'slicevar': r'\cos\theta_\pi',
         'ylabel': r'\mathrm{d}^2\sigma/\mathrm{d}p_\pi\,\mathrm{d}\cos\theta_\pi',
         'yunit': r'cm^2/nucleon/(GeV/c)',
         'source': 'Zenodo', 'source_url': 'https://zenodo.org/records/15776045',
         'provenance': 'T2K NC1pi+ double-differential cross section '
                       '(Zenodo 10.5281/zenodo.15776045, arXiv:2503.06849 & 2503.06843) · '
                       'per-bin error = sqrt(diag(covariance)) · nothing digitized'}}]},
    # NC1pi+ was published as a joint PRL+PRD (2503.06849 = 2025wde, 2503.06843 =
    # 2025kdk); both papers front the same shared data release.
    {'bibtag': 'T2K:2025kdk', 'slug': 't2k-2025kdk', 'source': 'Zenodo',
     'note': 'Shared with the companion paper arXiv:2503.06849.',
     'flux': {'root': 'data/datasets/sources/t2k-2025wde/flux_release.root',
              'hists': [('enu_numu', 'numu'), ('enu_numub', 'numubar'),
                        ('enu_nue', 'nue'), ('enu_nueb', 'nueb')],
              'note': 'T2K postfit flux prediction for all flavours (numu, numubar, nue, '
                      'nueb) for the NC1pi+ measurement, from the shared Zenodo '
                      'flux_release.root (10.5281/zenodo.15776045)'},
     'sources': [{'bracket2d': {
         'dir': 'data/datasets/sources/t2k-2025wde',
         'result': 'result_with_bins.csv', 'cov': 'covariance_matrix.csv',
         'result_scale': 1e-40, 'cov_scale': 1e-82,
         'xlabel': r'p_\pi', 'xunit': 'GeV/c', 'slicevar': r'\cos\theta_\pi',
         'ylabel': r'\mathrm{d}^2\sigma/\mathrm{d}p_\pi\,\mathrm{d}\cos\theta_\pi',
         'yunit': r'cm^2/nucleon/(GeV/c)',
         'source': 'Zenodo', 'source_url': 'https://zenodo.org/records/15776045',
         'provenance': 'T2K NC1pi+ double-differential cross section '
                       '(Zenodo 10.5281/zenodo.15776045, arXiv:2503.06843 & 2503.06849) · '
                       'per-bin error = sqrt(diag(covariance)) · nothing digitized'}}]},
    {'bibtag': 'T2K:2025kda', 'slug': 't2k-2025kda', 'source': 'Zenodo',
     'note': 'The Zenodo release includes momentum and cosine covariance matrices; not '
             'included here because their diagonals do not reproduce the reported per-bin '
             'errors. Will try to contact the authors.',
     'flux': {'root': 'data/datasets/sources/t2k-2025kda/flux_release.root',
              'hists': [('nominal_flux_numu;1', 'numu'), ('nominal_flux_numu;2', 'numubar'),
                        ('nominal_flux_numu;3', 'nue'), ('nominal_flux_numu;4', 'nueb')],
              'note': 'T2K nominal flux prediction for all flavours (numu, numubar, nue, '
                      'nueb) at the WAGASCI-BabyMIND setup, from the Zenodo flux_release.root '
                      '(the 4 histograms are all named nominal_flux_numu in the release; '
                      'read here by write-order cycle = numu/numubar/nue/nueb)'},
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
         'source': 'Zenodo', 'source_url': 'https://zenodo.org/records/16949979',
         'provenance': 'T2K WAGASCI-BabyMIND numu CC0pi differential cross section on CH/H2O '
                       '(Zenodo 10.5281/zenodo.16949979, arXiv:2509.07814) · quoted per-bin '
                       'errors · nothing digitized'}}]},
    {'bibtag': 'T2K:2017qxv', 'slug': 't2k-2017qxv', 'source': 'T2K',
     'note': 'This release lives only on t2k.org; it was never migrated to Zenodo.',
     'flux': {'root': 'data/datasets/sources/t2k-2017qxv/release.root',
              'hists': [('NuMuFlux', 'numu')],
              'note': 'T2K numu flux prediction (P0D water-in POT, runs 2-4), from the '
                      'release NuMuFlux histogram; bin content = flux over the bin width'},
     'sources': [{'t2korg2d': {
         'root': 'data/datasets/sources/t2k-2017qxv/release.root',
         'result': 'xsnominal',
         'cov_sources': ['cvm_statistics_data', 'cvm_statistics_mc', 'cvm_fsi', 'cvm_xs',
                         'cvm_flux', 'cvm_mass', 'cvm_detector'],
         'cos_edges': [0.0, 0.6, 0.7, 0.8, 0.85, 0.9, 0.925, 0.975, 1.0],
         'p_edges': [0.0, 0.4, 0.5, 0.7, 0.9, 2.5, 5.0],
         'drop_bins': [6, 12, 18],
         'slicevar': r'\cos\theta_\mu', 'xlabel': r'p_\mu', 'xunit': 'GeV/c',
         'ylabel': r'\mathrm{d}^2\sigma/\mathrm{d}p_\mu\mathrm{d}\cos\theta_\mu',
         'yunit': r'10^{-38}cm^2/GeV/neutron',
         'source': 'T2K (t2k.org)',
         'source_url': 'https://t2k-experiment.org/results/2017-cc0pi-water-xsec/',
         'provenance': 'T2K nu_mu CC0pi on H2O double-differential cross section '
                       '(t2k.org data release, arXiv:1708.06771, Phys.Rev.D 97 012001) · '
                       'total covariance = sum of per-source cvm_* · nothing digitized'}}]},
    # Flux-averaged coherent CC 1pi cross sections: two single values (nu_mu + antinu_mu),
    # no differential binning, so x is a single category "Averaged T2K flux".
    {'bibtag': 'T2K:2023xlh', 'slug': 't2k-2023xlh', 'source': 'T2K', 'flux': _FLUX_BOTH,
     'note': 'Taken directly from the paper (no data release).',
     'sources': [{'values': {
         'key': 'sigma', 'ylabel': r'\sigma_\mathrm{CCcoh}', 'yunit': r'10^{-40}cm^2',
         'items': [
             {'name': r'\nu_\mu', 'slug': 'numu',
              'note': 'Q^2-model uncertainty +0.49 (one-sided) not included in the error bar',
              'points': [{'cat': 'Averaged T2K flux', 'val': 2.98, 'err': 0.48}]},
             {'name': r'\bar\nu_\mu', 'slug': 'antinumu',
              'note': 'Q^2-model uncertainty +0.74 (one-sided) not included in the error bar',
              'points': [{'cat': 'Averaged T2K flux', 'val': 3.05, 'err': 0.81}]}],
         'source': 'arXiv', 'source_url': 'https://arxiv.org/abs/2308.16606',
         'provenance': 'T2K CC coherent charged-pion cross section on 12C '
                       '(arXiv:2308.16606) · flux-averaged total cross section, '
                       'stat+syst error in quadrature · nothing digitized'}}]},
    # WAGASCI-INGRID first CC0pi0p measurement: integrated cross sections on H2O and
    # CH (no differential binning). One 4-point sigma figure + one 2-point ratio figure.
    {'bibtag': 'T2K:2020txr', 'slug': 't2k-2020txr', 'source': 'Zenodo',
     'note': 'The Zenodo release includes a 16x16 covariance over the analysis (fit) bins; '
             'not included here because its mapping to the reported integrated cross sections '
             'is not understood. Will try to contact the authors.',
     'flux': {'root': 'data/datasets/sources/t2k-2020txr/histograms.root',
              'hists': [('flux_numu_wagasci', 'numu_wagasci'),
                        ('flux_numubar_wagasci', 'numubar_wagasci'),
                        ('flux_numu_pm', 'numu_pm'),
                        ('flux_numubar_pm', 'numubar_pm')],
              'note': 'T2K flux prediction Phi(E_nu) [/cm^2/50MeV/10^21 POT] for numu and '
                      'numubar at the WAGASCI module and the Proton Module (runs 2-4, RHC), '
                      'from the data release histograms.root (verified against ROOT)'},
     'sources': [
         {'values': {
             'key': 'sigma', 'ylabel': r'\sigma', 'yunit': r'10^{-39}cm^2/nucleon',
             'items': [{'slug': 'xsec', 'points': [
                 {'cat': r'$\bar\nu_\mu\ \mathrm{H_2O}$', 'val': 1.082,
                  'stat': 0.068, 'syst_up': 0.145, 'syst_down': 0.128},
                 {'cat': r'$\bar\nu_\mu\ \mathrm{CH}$', 'val': 1.096,
                  'stat': 0.054, 'syst_up': 0.132, 'syst_down': 0.117},
                 {'cat': r'$\nu_\mu\!+\!\bar\nu_\mu\ \mathrm{H_2O}$', 'val': 1.155,
                  'stat': 0.064, 'syst_up': 0.148, 'syst_down': 0.129},
                 {'cat': r'$\nu_\mu\!+\!\bar\nu_\mu\ \mathrm{CH}$', 'val': 1.159,
                  'stat': 0.049, 'syst_up': 0.129, 'syst_down': 0.115}]}],
             'source': 'Zenodo', 'source_url': 'https://zenodo.org/records/7065210',
             'provenance': 'T2K WAGASCI-INGRID CC0pi0p integrated cross sections on H2O/CH '
                           '(Zenodo 10.5281/zenodo.7065210, arXiv:2004.13989) · stat+syst '
                           '(asymmetric) added in quadrature · NOTE: the release file lists '
                           'the antinu_mu-CH systematic lower error as -0.017, which is a '
                           'typo for -0.117 (the paper value, used here) · nothing digitized'}},
         {'values': {
             'key': 'ratio', 'ylabel': r'\sigma_\mathrm{H_2O}/\sigma_\mathrm{CH}', 'yunit': '',
             'items': [{'slug': 'ratio', 'points': [
                 {'cat': r'$\bar\nu_\mu$', 'val': 0.987,
                  'stat': 0.078, 'syst_up': 0.093, 'syst_down': 0.090},
                 {'cat': r'$\nu_\mu\!+\!\bar\nu_\mu$', 'val': 0.997,
                  'stat': 0.069, 'syst_up': 0.083, 'syst_down': 0.078}]}],
             'source': 'Zenodo', 'source_url': 'https://zenodo.org/records/7065210',
             'provenance': 'T2K WAGASCI-INGRID CC0pi0p H2O/CH cross-section ratio '
                           '(Zenodo 10.5281/zenodo.7065210, arXiv:2004.13989) · stat+syst '
                           '(asymmetric) added in quadrature · nothing digitized'}}]},
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
        elif '2013nor' in src:
            dists.extend(build_2013nor(src['2013nor']))
        elif 'sigma_enu' in src:
            dists.extend(build_sigma_enu(src['sigma_enu']))
        elif 'minerva_root' in src:
            dists.extend(build_minerva_root(src['minerva_root']))
        elif 'minerva_csv' in src:
            dists.extend(build_minerva_csv(src['minerva_csv']))
        elif 'zenodo3d' in src:
            dists.extend(build_3d_zenodo(src['zenodo3d']))
        elif 'values' in src:
            dists.extend(build_values(src['values']))
        elif 'bracket2d' in src:
            dists.extend(build_2d_bracket(src['bracket2d']))
        elif 't2korg2d' in src:
            dists.extend(build_2d_t2korg(src['t2korg2d']))
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
    if release_cov is None and entry.get('covariance'):   # release-level covariance spec
        release_cov = build_release_cov(entry['covariance'], dists)
    # Release-level source + link come from the distributions (builder-set), so the
    # "Release from X" label and its href always agree and point at the real host
    # (Zenodo / t2k.org / arXiv / NUISANCE) — never a reconstructed guess. When a
    # release spans several files (NUISANCE, one per observable), link the common
    # parent directory instead of an arbitrary single file.
    for d in dists:                                  # display notes (full provenance kept)
        d['notes'] = _notes_from_provenance(d.get('provenance', ''))
    src = dists[0]['source'] if dists else entry.get('source', 'NUISANCE')
    src_url = _release_source_url(dists)
    out = {'bibtag': entry['bibtag'], 'slug': entry['slug'],
           'source': src, 'source_url': src_url,
           'arxiv': arxiv, 'cite': cite,
           'note': entry.get('note', ''),
           'distributions': dists}
    if release_cov:
        out['covariance'] = release_cov
    if entry.get('flux'):                        # flux prediction (download-only)
        out['flux'] = extract_flux(entry['flux'])
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

    # Legacy one-off JSONs not built from REGISTRY above: inject their flux so the
    # completeness principle holds (values + covariance + flux).
    EXTRA_FLUX = {'t2k-2019yqu': _FLUX_FHC}   # CC1pi+ CH, FHC (nu-mode)
    for slug, fspec in EXTRA_FLUX.items():
        if only and only != slug:
            continue
        path = os.path.join(OUT_DIR, f'{slug}.json')
        if os.path.exists(path):
            d = json.load(open(path))
            d['flux'] = extract_flux(fspec)
            json.dump(d, open(path, 'w'), indent=1)
            print(f"{slug:<15} -> injected flux ({len(d['flux']['columns']) - 2} cols)")

    # 2019yqu (one-off): block-diagonal covariance from its per-observable CH ROOTs.
    if not only or only == 't2k-2019yqu':
        path = os.path.join(OUT_DIR, 't2k-2019yqu.json')
        if os.path.exists(path):
            d = json.load(open(path))
            covfiles = {'Q2': ('Q2.root', 'Q2Cov'),
                        'MomentumPion': ('MomentumPion.root', 'Momentum_pionCov'),
                        'Thetapion': ('Thetapion.root', 'Theta_pionCov'),
                        'Thetapimu': ('Thetapimu.root', 'Theta(pi,mu)(rads)Cov'),
                        'phi_adler': ('phi_adler.root', 'Phi_AdlerCov'),
                        'theta_adler': ('theta_adler.root', 'Theta_AdlerCov')}
            mats, order, errs = [], [], []
            for dist in d['distributions']:
                fn, ck = covfiles[dist['key']]
                M = np.asarray(uproot.open(fetch('data/T2K/CC1pip/CH/' + fn))[ck].values())
                mats.append(M)
                for b in dist['bins']:
                    order.append(f"{dist['key']} [{b['lo']:g},{b['hi']:g}]")
                    errs.append(b['err'])
            N = sum(m.shape[0] for m in mats)
            big = np.zeros((N, N)); off = 0
            for m in mats:
                n = m.shape[0]; big[off:off + n, off:off + n] = m; off += n
            errs = np.array(errs); dg = np.diag(big)
            g = (dg > 0) & (errs > 0)
            scale = float(np.median(errs[g] ** 2 / dg[g]))     # cov units -> value units
            big = big * scale
            r = np.median(np.sqrt(np.diag(big))[g] / errs[g])
            if not 0.9 < r < 1.1:
                print(f"    !! 2019yqu cov sqrt(diag)/err = {r:.3f}")
            d['covariance'] = _cov_obj(big, order,
                'block-diagonal per-observable covariance from the NUISANCE CH data release '
                '(Q2Cov etc.; no inter-observable correlations), scaled to the reported '
                'values; row/col order below')
            d['note'] = ''
            for dist in d['distributions']:
                dist['notes'] = _notes_from_provenance(dist.get('provenance', ''))
            d['source'] = d['distributions'][0].get('source', d.get('source', 'NUISANCE'))
            d['source_url'] = _release_source_url(d['distributions'])
            json.dump(d, open(path, 'w'), indent=1)
            print(f"t2k-2019yqu     -> injected covariance ({N}x{N}, scale 1e{np.log10(scale):.0f})")

    # Validate everything we just built; a broken release fails the build loudly.
    print()
    import validate_datasets
    validate_datasets.main()
