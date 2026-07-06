'use client';

import { useState } from 'react';
import type { DataRelease as Release, Distribution, DataBin } from '@/lib/datasets';

/* minimal TeX -> unicode for short observable labels */
function tex(s: string): string {
  if (!s) return '';
  const map: Record<string, string> = {
    '\\pi': 'π', '\\mu': 'μ', '\\nu': 'ν', '\\theta': 'θ', '\\phi': 'φ',
    '\\sigma': 'σ', '\\pm': '±', '\\times': '×', '\\,': ' ',
  };
  let out = s.replace(/\$(.*?)\$/g, (_, m) => m);
  for (const k in map) out = out.split(k).join(map[k]);
  return out
    .replace(/\^\{([^}]*)\}/g, (_, x) => ' ' + toSup(x))
    .replace(/\^(\S)/g, (_, x) => toSup(x))
    .replace(/_\{([^}]*)\}/g, (_, x) => toSub(x))
    .replace(/_(\S)/g, (_, x) => toSub(x));
}
const SUP: Record<string, string> = { '0': '⁰', '1': '¹', '2': '²', '3': '³', '+': '⁺', '-': '⁻' };
const SUB: Record<string, string> = {
  '0': '₀', '1': '₁', '2': '₂', 'i': 'ᵢ', 'π': 'π', 'μ': 'μ', 'e': 'ₑ',
};
const toSup = (x: string) => [...x].map((c) => SUP[c] ?? c).join('');
const toSub = (x: string) => [...x].map((c) => SUB[c] ?? c).join('');
function strip(s: string): string {
  return String(s)
    .replace(/[${}\\]/g, '')
    .replace(/\^2/g, '²')
    .replace(/pi/g, 'π')
    .replace(/theta/g, 'θ')
    .replace(/phi/g, 'φ')
    .replace(/mu/g, 'μ');
}
const fmt = (v: number): string => {
  const a = Math.abs(v);
  if (a === 0) return '0';
  if (a < 0.001 || a >= 1000) return v.toExponential(0);
  return String(+v.toPrecision(3));
};

function sparkline(bins: DataBin[]): string {
  const w = 84, h = 28, pad = 3;
  const xs = bins.map((b) => b.center);
  const xmin = Math.min(...xs), xmax = Math.max(...xs);
  const ymax = Math.max(...bins.map((b) => b.val)) || 1;
  const px = (v: number) => pad + ((v - xmin) / (xmax - xmin || 1)) * (w - 2 * pad);
  const py = (v: number) => h - pad - (v / ymax) * (h - 2 * pad);
  const pts = bins.map((b) => `${px(b.center).toFixed(1)},${py(b.val).toFixed(1)}`).join(' ');
  return `<svg class="dr-spark" viewBox="0 0 ${w} ${h}" aria-hidden="true"><polyline points="${pts}" fill="none" stroke="var(--dr-accent)" stroke-width="1.5" stroke-linejoin="round"/></svg>`;
}

function plotSVG(bins: DataBin[], xlab: string, ylab: string, logy: boolean): string {
  const W = 560, H = 360, mL = 66, mR = 14, mT = 14, mB = 52;
  const xmin = Math.min(...bins.map((b) => b.lo));
  const xmax = Math.max(...bins.map((b) => b.hi));
  const vmax = Math.max(...bins.map((b) => b.val + b.err));
  const vmin = Math.min(...bins.map((b) => Math.max(b.val - b.err, 0)));
  const iw = W - mL - mR, ih = H - mT - mB;
  const X = (v: number) => mL + ((v - xmin) / (xmax - xmin || 1)) * iw;
  let Y: (v: number) => number;
  let yticks: number[] = [];
  if (logy) {
    const lo = Math.max(vmin, vmax / 1e4) || 1e-4, hi = vmax * 1.3;
    const l = Math.log10(lo), u = Math.log10(hi);
    Y = (v) => { v = Math.max(v, lo); return mT + ih - ((Math.log10(v) - l) / (u - l || 1)) * ih; };
    for (let e = Math.floor(l); e <= Math.ceil(u); e++) yticks.push(Math.pow(10, e));
    yticks = yticks.filter((t) => t >= lo * 0.999 && t <= hi);
  } else {
    const hi = vmax * 1.12;
    Y = (v) => mT + ih - (v / hi) * ih;
    for (let i = 0; i <= 5; i++) yticks.push((hi * i) / 5);
  }
  const xticks: number[] = [];
  for (let i = 0; i <= 5; i++) xticks.push(xmin + ((xmax - xmin) * i) / 5);
  let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="cross-section plot">`;
  s += `<rect x="${mL}" y="${mT}" width="${iw}" height="${ih}" fill="none" stroke="var(--line)"/>`;
  for (const t of yticks) {
    const y = Y(t);
    s += `<line x1="${mL}" y1="${y.toFixed(1)}" x2="${mL + iw}" y2="${y.toFixed(1)}" stroke="var(--line-soft)"/>`;
    s += `<text x="${mL - 8}" y="${(y + 3).toFixed(1)}" text-anchor="end" font-family="var(--dr-mono)" font-size="10" fill="var(--muted)">${fmt(t)}</text>`;
  }
  for (const t of xticks) {
    const x = X(t);
    s += `<line x1="${x.toFixed(1)}" y1="${mT + ih}" x2="${x.toFixed(1)}" y2="${mT + ih + 4}" stroke="var(--muted)"/>`;
    s += `<text x="${x.toFixed(1)}" y="${mT + ih + 16}" text-anchor="middle" font-family="var(--dr-mono)" font-size="10" fill="var(--muted)">${fmt(t)}</text>`;
  }
  for (const b of bins) {
    const x = X(b.center), yv = Y(b.val);
    const yhi = Y(b.val + b.err), ylo = Y(Math.max(b.val - b.err, logy ? 1e-9 : 0));
    s += `<line x1="${X(b.lo).toFixed(1)}" y1="${yv.toFixed(1)}" x2="${X(b.hi).toFixed(1)}" y2="${yv.toFixed(1)}" stroke="var(--dr-accent)" stroke-opacity=".4" stroke-width="1"/>`;
    s += `<line x1="${x.toFixed(1)}" y1="${yhi.toFixed(1)}" x2="${x.toFixed(1)}" y2="${ylo.toFixed(1)}" stroke="var(--dr-accent)" stroke-width="1.3"/>`;
    s += `<line x1="${(x - 3).toFixed(1)}" y1="${yhi.toFixed(1)}" x2="${(x + 3).toFixed(1)}" y2="${yhi.toFixed(1)}" stroke="var(--dr-accent)" stroke-width="1.3"/>`;
    s += `<line x1="${(x - 3).toFixed(1)}" y1="${ylo.toFixed(1)}" x2="${(x + 3).toFixed(1)}" y2="${ylo.toFixed(1)}" stroke="var(--dr-accent)" stroke-width="1.3"/>`;
    s += `<circle cx="${x.toFixed(1)}" cy="${yv.toFixed(1)}" r="2.6" fill="var(--dr-accent)"/>`;
  }
  s += `<text x="${mL + iw / 2}" y="${H - 6}" text-anchor="middle" font-family="var(--dr-mono)" font-size="11" fill="var(--ink)">${xlab}</text>`;
  s += `<text x="14" y="${mT + ih / 2}" text-anchor="middle" font-family="var(--dr-mono)" font-size="11" fill="var(--ink)" transform="rotate(-90 14 ${mT + ih / 2})">${ylab}</text>`;
  s += `</svg>`;
  return s;
}

function csv(d: Distribution): string {
  const head = 'bin,x_low,x_high,x_center,value,error';
  const rows = d.bins.map((b) => [b.i, b.lo, b.hi, b.center, b.val, b.err.toPrecision(6)].join(','));
  return head + '\n' + rows.join('\n') + '\n';
}
function triggerDownload(uri: string, filename: string) {
  const a = document.createElement('a');
  a.href = uri;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
}
function download(d: Distribution, bibtag: string) {
  const uri = 'data:text/csv;charset=utf-8,' +
    encodeURIComponent(`# ${bibtag} ${strip(d.name)}  (${d.yunit})\n# source: ${d.provenance}\n` + csv(d));
  triggerDownload(uri, `${bibtag.replace(':', '_')}_${d.slug}.csv`);
}
function downloadAll(release: Release) {
  const lines = [
    `# ${release.bibtag} — ${release.source} data release`,
    `# ${release.cite ?? ''} · arXiv:${release.arxiv ?? ''}`,
    `# ${release.distributions.length} distributions · taken directly from NUISANCE (values + covariance diagonal); nothing digitized`,
    `distribution,slice,x_label,x_low,x_high,x_center,value,error,y_unit`,
  ];
  for (const d of release.distributions) {
    const rows = d.is2d && d.slices
      ? d.slices.flatMap((s) => s.bins.map((b) => ({ slice: s.label, b })))
      : d.bins.map((b) => ({ slice: '', b }));
    for (const { slice, b } of rows) {
      lines.push([d.key, `"${slice}"`, strip(d.xlabel), b.lo, b.hi_true ?? b.hi,
        b.center, b.val, b.err.toPrecision(6), `"${d.yunit}"`].join(','));
    }
  }
  const uri = 'data:text/csv;charset=utf-8,' + encodeURIComponent(lines.join('\n') + '\n');
  triggerDownload(uri, `${release.bibtag.replace(':', '_')}_${release.source}_all.csv`);
}

function downloadSlices(d: Distribution, bibtag: string) {
  const lines = [`# ${bibtag} ${strip(d.name)}  (${d.yunit})`,
    `# source: ${d.provenance}`,
    `slice,x_low,x_high,x_center,value,error`];
  for (const s of d.slices ?? []) {
    for (const b of s.bins) {
      lines.push([`"${s.label}"`, b.lo, b.hi_true ?? b.hi, b.center, b.val, b.err.toPrecision(6)].join(','));
    }
  }
  const uri = 'data:text/csv;charset=utf-8,' + encodeURIComponent(lines.join('\n') + '\n');
  triggerDownload(uri, `${bibtag.replace(':', '_')}_${d.slug}.csv`);
}

// index of the slice with the most bins — the representative one for a sparkline
function fatSlice(d: Distribution): number {
  const sl = d.slices ?? [];
  let best = 0;
  for (let i = 1; i < sl.length; i++) if (sl[i].nbins > sl[best].nbins) best = i;
  return best;
}

const EXT =
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="12" height="12">
    <path d="M14 5h5v5M19 5l-8 8M18 13v6H5V6h6" />
  </svg>;

export function DataRelease({ release }: { release: Release }) {
  const [open, setOpen] = useState<Set<string>>(new Set());
  const [mode, setMode] = useState<Record<string, 'lin' | 'log'>>({});
  const [slice, setSlice] = useState<Record<string, number>>({});
  const [copied, setCopied] = useState<string | null>(null);

  const toggle = (k: string) =>
    setOpen((prev) => {
      const n = new Set(prev);
      n.has(k) ? n.delete(k) : n.add(k);
      return n;
    });

  // release-level source: the NUISANCE directory the distributions live in
  const dir = release.distributions[0]?.nuisance_file.split('/').slice(0, -1).join('/') ?? '';
  const releaseUrl = dir
    ? `https://github.com/NUISANCEMC/nuisance/tree/main/${dir}`
    : 'https://github.com/NUISANCEMC/nuisance';

  return (
    <section className="dr">
      <div className="dr-head">
        <h2 className="type-h3" style={{ margin: 0 }}>Data release</h2>
        <button className="dr-btn primary dr-downloadall" onClick={() => downloadAll(release)}>
          ↓ Download all (CSV)
        </button>
      </div>
      <p className="dr-sub">
        Release from{' '}
        <a className="dr-src-link" href={releaseUrl} target="_blank" rel="noopener noreferrer">
          {release.source}
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="11" height="11" aria-hidden="true">
            <path d="M14 5h5v5M19 5l-8 8M18 13v6H5V6h6" />
          </svg>
        </a>{' '}
        (values + covariance); nothing digitized.
      </p>

      <div className="dr-items">
        {release.distributions.map((d, i) => {
          const isOpen = open.has(d.key);
          const logy = mode[d.key] === 'log';
          const is2d = !!d.is2d && !!d.slices?.length;
          const si = is2d ? (slice[d.key] ?? fatSlice(d)) : 0;
          const activeBins = is2d ? d.slices![si].bins : d.bins;
          const activeNote = is2d ? d.slices![si].scale_note : null;
          const xlab = `${strip(d.xlabel)}${d.xunit ? ` [${d.xunit}]` : ''}`;
          const ylab = strip(d.ylabel_plot);
          return (
            <div className={`dr-item${isOpen ? ' open' : ''}`} key={d.key}>
              <button
                className="dr-item-head"
                aria-expanded={isOpen}
                onClick={() => toggle(d.key)}
              >
                <span className="dr-idx">{String(i + 1).padStart(2, '0')}</span>
                <span className="dr-item-title">
                  <span className="t" dangerouslySetInnerHTML={{ __html: d.nameHtml }} />
                  <span className="s">
                    {is2d ? `${d.slices!.length} slices · ${d.nbins} points` : `${d.nbins} bins`} ·{' '}
                    <span dangerouslySetInnerHTML={{ __html: d.ylabelHtml }} />{' '}
                    <span dangerouslySetInnerHTML={{ __html: d.yunitHtml }} />
                  </span>
                </span>
                <span
                  className="dr-spark-wrap"
                  aria-hidden="true"
                  dangerouslySetInnerHTML={{ __html: sparkline(is2d ? d.slices![fatSlice(d)].bins : d.bins) }}
                />
                <svg className="dr-chev" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M9 6l6 6-6 6" />
                </svg>
              </button>

              {isOpen && (
                <div className="dr-body">
                  {is2d && (
                    <div className="dr-slices">
                      <span className="dr-slices-lbl">{d.slicevar_tex ? `${strip(d.slicevar_tex)} slice:` : 'slice:'}</span>
                      {d.slices!.map((s, k) => (
                        <button
                          key={k}
                          className={`dr-slice-btn${k === si ? ' on' : ''}`}
                          onClick={() => setSlice((m) => ({ ...m, [d.key]: k }))}
                          dangerouslySetInnerHTML={{ __html: s.labelHtml }}
                        />
                      ))}
                    </div>
                  )}
                  <div className="dr-bodygrid">
                    <div>
                      <div className="dr-toolbar">
                        <button
                          className={`dr-toggle${!logy ? ' on' : ''}`}
                          onClick={() => setMode((m) => ({ ...m, [d.key]: 'lin' }))}
                        >
                          linear y
                        </button>
                        <button
                          className={`dr-toggle${logy ? ' on' : ''}`}
                          onClick={() => setMode((m) => ({ ...m, [d.key]: 'log' }))}
                        >
                          log y
                        </button>
                      </div>
                      <div
                        className="dr-plot"
                        dangerouslySetInnerHTML={{ __html: plotSVG(activeBins, xlab, ylab, logy) }}
                      />
                      {activeNote ? <p className="dr-note">{activeNote}</p> : null}
                    </div>

                    <div className="dr-dwrap">
                      <div className="dr-dtable-scroll">
                        <table className="dr-data">
                          <thead>
                            <tr>
                              <th>bin</th>
                              <th>x range</th>
                              <th>value</th>
                              <th>± err</th>
                            </tr>
                          </thead>
                          <tbody>
                            {activeBins.map((b) => (
                              <tr key={b.i}>
                                <td>{b.i}</td>
                                <td>{b.lo}, {b.hi_true ?? b.hi}</td>
                                <td>{b.val}</td>
                                <td>{+b.err.toPrecision(3)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                      <div className="dr-actions">
                        <button
                          className="dr-btn primary"
                          onClick={() => (is2d ? downloadSlices(d, release.bibtag) : download(d, release.bibtag))}
                        >
                          ↓ Download CSV{is2d ? ' (all slices)' : ''}
                        </button>
                        <a className="dr-btn" href={d.source_url} target="_blank" rel="noopener noreferrer">
                          View on NUISANCE {EXT}
                        </a>
                      </div>
                    </div>
                  </div>

                  <div className="dr-prov">
                    <div className="dr-prov-lbl">Provenance</div>
                    <div className="dr-prov-val">
                      <span>{d.provenance}</span>{' '}
                      <button
                        className="dr-copy"
                        onClick={() => {
                          navigator.clipboard?.writeText(d.provenance);
                          setCopied(d.key);
                          setTimeout(() => setCopied(null), 1200);
                        }}
                      >
                        {copied === d.key ? 'copied' : 'copy'}
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
