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
            .replace('\\sigma', 'σ').replace('\\cos', 'cos').replace('\\', '')
            .replace('^2', '²').replace('^{2}', '²'))


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
    good = (np.abs(vals) > 0) & (err > 0)
    if good.any():
        ratio = np.median(err[good] / np.abs(vals[good]))
        if ratio > 0:
            m = round(math.log10(0.15 / ratio))
            if abs(m) >= 2:                 # gross unit mismatch, not a real error
                err = err * (10.0 ** m)
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
    err = np.sqrt(np.clip(np.diag(uproot.open(fetch(spec['cov']))[spec['cov_key']].values()), 0, None))
    if len(err) != len(rows):
        raise ValueError(f"{spec['text']}: {len(rows)} rows vs {len(err)} cov bins")
    grouped = {}
    for (b, clo, chi, plo, phi, val), e in zip(rows, err):
        grouped.setdefault((clo, chi), []).append((plo, phi, val, e))
    return _assemble_2d(grouped, spec)


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
    diag = {}
    for i, l in enumerate(l for l in open(fetch(spec['cov'])) if l.strip()):
        try:
            diag[i + 1] = math.sqrt(max(float(l.split(',')[i]), 0.0))
        except (ValueError, IndexError):
            pass
    pdiv = spec.get('pdiv', 1.0)
    out = []
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
        out += _assemble_2d(grouped, {**spec, 'detector': det['name']})
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
    det = spec.get('detector')                    # optional group label (ND280/INGRID)
    suf_tex = rf'\ (\mathrm{{{det}}})' if det else ''
    suf = f' ({det})' if det else ''
    dkey = (f"_{det.lower()}" if det else '')
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
    for d in dists:
        d.setdefault('source', 'NUISANCE')
        d.setdefault('source_url', BLOB + d['nuisance_file'])
        d.setdefault('provenance', f"{d['source']} · {d['nuisance_file']} · from "
                     f"arXiv:{arxiv} ({cite}) · per-bin error = sqrt(diag(covariance))"
                     + (f" · {d['scale_note']}" if d.get('scale_note') else ''))
    out = {'bibtag': entry['bibtag'], 'slug': entry['slug'], 'source': 'NUISANCE',
           'arxiv': arxiv, 'cite': cite,
           'note': 'Cross sections taken directly from the NUISANCE data release.',
           'distributions': dists}
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
