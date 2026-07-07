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

function plotSVG(bins: DataBin[], logy: boolean): string {
  // Axis labels are laid out as HTML around the SVG (see the grid in the render);
  // the SVG carries only ticks + data, so margins just cover the tick numbers.
  const W = 560, H = 360, mL = 58, mR = 14, mT = 14, mB = 38;
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
    s += `<text x="${mL - 8}" y="${(y + 4).toFixed(1)}" text-anchor="end" font-family="var(--dr-mono)" font-size="13" fill="var(--muted)">${fmt(t)}</text>`;
  }
  for (const t of xticks) {
    const x = X(t);
    s += `<line x1="${x.toFixed(1)}" y1="${mT + ih}" x2="${x.toFixed(1)}" y2="${mT + ih + 4}" stroke="var(--muted)"/>`;
    s += `<text x="${x.toFixed(1)}" y="${mT + ih + 18}" text-anchor="middle" font-family="var(--dr-mono)" font-size="13" fill="var(--muted)">${fmt(t)}</text>`;
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
  s += `</svg>`;
  return s;
}

function triggerDownload(uri: string, filename: string) {
  const a = document.createElement('a');
  a.href = uri;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
}

// --- CSV bodies bundled into the ZIP ---
function distCsv(d: Distribution): string {
  const head = d.is2d ? 'slice,x_low,x_high,x_center,value,error'
                      : 'x_low,x_high,x_center,value,error';
  const rows: string[] = [];
  const push = (slice: string, b: DataBin) =>
    rows.push([...(d.is2d ? [`"${slice}"`] : []),
      b.lo, b.hi_true ?? b.hi, b.center, b.val, b.err.toPrecision(6)].join(','));
  if (d.is2d && d.slices) for (const s of d.slices) for (const b of s.bins) push(s.label, b);
  else for (const b of d.bins) push('', b);
  return `# ${strip(d.name)}  [${d.yunit}]\n# ${d.provenance}\n${head}\n${rows.join('\n')}\n`;
}
function covCsv(release: Release): string {
  const c = release.covariance!;
  return [
    `# ${release.bibtag} — covariance matrix (${c.matrix.length}x${c.matrix.length})`,
    `# ${c.note ?? ''}`,
    ...c.order.map((o, i) => `# bin ${i}: ${o}`),
    ...c.matrix.map((row) => row.join(',')),
  ].join('\n') + '\n';
}
function readme(release: Release): string {
  const n = release.distributions.length;
  const cov = release.covariance;
  return [
    `${release.bibtag} — ${release.source} data release`,
    `${release.cite ?? ''}   arXiv:${release.arxiv ?? ''}`,
    '',
    release.note ?? '',
    '',
    'Contents:',
    `  ${n} distribution CSV file(s): x bins, value, error (2-D files have a "slice" column).`,
    cov ? `  covariance.csv: full ${cov.matrix.length}x${cov.matrix.length} matrix; bin order in its header.`
        : '  (no full covariance matrix in this release; per-bin errors are in the CSVs.)',
    '',
    'Nothing is digitized — values and covariance come directly from the release.',
  ].join('\n') + '\n';
}

// --- minimal store (uncompressed) ZIP builder, no dependency ---
function crc32(buf: Uint8Array): number {
  let c = ~0;
  for (let i = 0; i < buf.length; i++) {
    c ^= buf[i];
    for (let k = 0; k < 8; k++) c = (c >>> 1) ^ (0xedb88320 & -(c & 1));
  }
  return (~c) >>> 0;
}
function makeZip(files: Record<string, string>): Uint8Array {
  const enc = new TextEncoder();
  const u16 = (n: number) => [n & 255, (n >>> 8) & 255];
  const u32 = (n: number) => [n & 255, (n >>> 8) & 255, (n >>> 16) & 255, (n >>> 24) & 255];
  const chunks: Uint8Array[] = [];
  const central: Uint8Array[] = [];
  let offset = 0;
  for (const [name, content] of Object.entries(files)) {
    const data = enc.encode(content);
    const nb = enc.encode(name);
    const crc = crc32(data);
    const lfh = new Uint8Array([0x50, 0x4b, 0x03, 0x04, ...u16(20), ...u16(0), ...u16(0),
      ...u16(0), ...u16(0), ...u32(crc), ...u32(data.length), ...u32(data.length),
      ...u16(nb.length), ...u16(0)]);
    chunks.push(lfh, nb, data);
    central.push(new Uint8Array([0x50, 0x4b, 0x01, 0x02, ...u16(20), ...u16(20), ...u16(0),
      ...u16(0), ...u16(0), ...u16(0), ...u32(crc), ...u32(data.length), ...u32(data.length),
      ...u16(nb.length), ...u16(0), ...u16(0), ...u16(0), ...u16(0), ...u32(0), ...u32(offset)]), nb);
    offset += lfh.length + nb.length + data.length;
  }
  const cdSize = central.reduce((s, a) => s + a.length, 0);
  const n = Object.keys(files).length;
  const eocd = new Uint8Array([0x50, 0x4b, 0x05, 0x06, ...u16(0), ...u16(0), ...u16(n),
    ...u16(n), ...u32(cdSize), ...u32(offset), ...u16(0)]);
  const all = [...chunks, ...central, eocd];
  const out = new Uint8Array(all.reduce((s, a) => s + a.length, 0));
  let p = 0;
  for (const a of all) { out.set(a, p); p += a.length; }
  return out;
}
function downloadZip(release: Release) {
  const files: Record<string, string> = { 'README.txt': readme(release) };
  for (const d of release.distributions) files[`${d.slug || d.key}.csv`] = distCsv(d);
  if (release.covariance) files['covariance.csv'] = covCsv(release);
  const url = URL.createObjectURL(new Blob([makeZip(files) as BlobPart], { type: 'application/zip' }));
  triggerDownload(url, `${release.bibtag.replace(':', '_')}_${release.source}.zip`);
  setTimeout(() => URL.revokeObjectURL(url), 2000);
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
        <button className="dr-btn primary dr-downloadall" onClick={() => downloadZip(release)}>
          ↓ Download files (ZIP)
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
          const axunit = (h: string) => (h ? ` <span class="dr-axunit">[${h}]</span>` : '');
          const xlabHtml = d.xlabelHtml + axunit(d.xunitHtml);
          const ylabHtml = d.ylabelHtml + axunit(d.yunitHtml);
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
                      <div className="dr-plot">
                        <div className="dr-plot-ylab">
                          <span dangerouslySetInnerHTML={{ __html: ylabHtml }} />
                        </div>
                        <div
                          className="dr-plot-canvas"
                          dangerouslySetInnerHTML={{ __html: plotSVG(activeBins, logy) }}
                        />
                        <div
                          className="dr-plot-xlab"
                          dangerouslySetInnerHTML={{ __html: xlabHtml }}
                        />
                      </div>
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
