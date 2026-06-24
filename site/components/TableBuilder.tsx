'use client';

import { useMemo, useState } from 'react';
import { Icon } from '@/components/Icon';
import { downloadText, fileSlug } from '@/lib/download';

export type Cluster = 'interactions' | 'oscillations';
type TBMeas = Record<string, unknown>;

export type TBPaper = {
  citekey: string;
  title: string;
  titleHtml: string;
  experiment: string; // display (joined for joint analyses)
  experiments: string[]; // facet membership
  year: number | null;
  journal: string | null;
  arxiv: string | null;
  doi: string | null;
  citations: number | null;
  measurements: TBMeas[];
};

export type RowFacet = { key: string; label: string; allLabel: string; values: string[] };

type Mode = 'paper' | 'meas';
const ALL = 'All';

type Row = {
  citekey: string;
  title: string;
  titleHtml: string;
  experiment: string;
  year: number | null;
  journal: string | null;
  arxiv: string | null;
  doi: string | null;
  citations: number | null;
  facets: Record<string, string[]>;
  [key: string]: unknown;
};

const FLAVOR_LABEL: Record<string, string> = { numu: 'νμ', numubar: 'ν̄μ', nue: 'νe', nuebar: 'ν̄e' };
const FLAVOR_TEX: Record<string, string> = {
  numu: '$\\nu_\\mu$',
  numubar: '$\\bar\\nu_\\mu$',
  nue: '$\\nu_e$',
  nuebar: '$\\bar\\nu_e$',
};
const flavorLabel = (f: string) => FLAVOR_LABEL[f] ?? f;
const flavorTex = (f: string) => FLAVOR_TEX[f] ?? texEscape(f);

const UNI: [string, string][] = [
  ['π', '\\pi'],
  ['γ', '\\gamma'],
  ['ν', '\\nu'],
  ['μ', '\\mu'],
  ['Λ', '\\Lambda'],
  ['Δ', '\\Delta'],
  ['η', '\\eta'],
  ['ρ', '\\rho'],
  ['±', '\\pm'],
  ['→', '\\to'],
  ['×', '\\times'],
];

function texEscape(s: string): string {
  return s
    .replace(/\\/g, '\\textbackslash{}')
    .replace(/([&%$#_{}])/g, '\\$1')
    .replace(/~/g, '\\textasciitilde{}')
    .replace(/\^/g, '\\textasciicircum{}');
}
function uni2tex(s: string): string {
  let out = texEscape(s);
  for (const [u, t] of UNI) out = out.split(u).join(`$${t}$`);
  return out;
}

// oscillation parameter tokens -> LaTeX
const PARAM_TEX: Record<string, string> = {
  'θ₁₂': '\\theta_{12}',
  'θ₁₃': '\\theta_{13}',
  'θ₂₃': '\\theta_{23}',
  'θ₁₄': '\\theta_{14}',
  'θ₂₄': '\\theta_{24}',
  'θ₃₄': '\\theta_{34}',
  'Δm²₂₁': '\\Delta m^2_{21}',
  'Δm²₃₁': '\\Delta m^2_{31}',
  'Δm²₃₂': '\\Delta m^2_{32}',
  'Δm²₄₁': '\\Delta m^2_{41}',
  'δCP': '\\delta_{CP}',
};
function paramTex(p: string): string {
  if (p in PARAM_TEX) return `$${PARAM_TEX[p]}$`;
  return texEscape(p); // e.g. "mass ordering"
}
// oscillation channel label (νμ→νe) -> LaTeX
const CHAN_TEX: [string, string][] = [
  ['ν̄μ', '\\bar\\nu_\\mu'],
  ['ν̄e', '\\bar\\nu_e'],
  ['ν̄τ', '\\bar\\nu_\\tau'],
  ['ν̄s', '\\bar\\nu_s'],
  ['νμ', '\\nu_\\mu'],
  ['νe', '\\nu_e'],
  ['ντ', '\\nu_\\tau'],
  ['νs', '\\nu_s'],
  ['→', '\\to '],
];
function channelTex(label: string): string {
  let s = label;
  for (const [u, t] of CHAN_TEX) s = s.split(u).join(t);
  return `$${s}$`;
}

type Col = {
  id: string;
  label: string;
  scope: Mode | 'both';
  align: 'l' | 'r';
  text: (r: Row) => string;
  html?: (r: Row) => string;
  tex: (r: Row) => string;
};

const sa = (r: Row, k: string) => (r[k] as string[] | undefined) ?? [];
const ss = (r: Row, k: string) => (r[k] as string | null | undefined) ?? '';

const PAPER_COLS: Col[] = [
  { id: 'experiment', label: 'Experiment', scope: 'both', align: 'l', text: (r) => r.experiment, tex: (r) => texEscape(r.experiment) },
  { id: 'year', label: 'Year', scope: 'both', align: 'r', text: (r) => (r.year != null ? String(r.year) : ''), tex: (r) => (r.year != null ? String(r.year) : '') },
  { id: 'title', label: 'Title', scope: 'paper', align: 'l', text: (r) => r.title, html: (r) => r.titleHtml, tex: (r) => uni2tex(r.title) },
  { id: 'citekey', label: 'Key', scope: 'both', align: 'l', text: (r) => r.citekey, tex: (r) => `\\texttt{${texEscape(r.citekey)}}` },
  { id: 'cite', label: 'Citation', scope: 'both', align: 'l', text: (r) => `[${r.citekey}]`, tex: (r) => `\\cite{${r.citekey}}` },
  { id: 'journal', label: 'Journal', scope: 'paper', align: 'l', text: (r) => r.journal ?? '', tex: (r) => texEscape(r.journal ?? '') },
  { id: 'arxiv', label: 'arXiv', scope: 'paper', align: 'l', text: (r) => r.arxiv ?? '', tex: (r) => (r.arxiv ? `\\texttt{${texEscape(r.arxiv)}}` : '') },
  { id: 'doi', label: 'DOI', scope: 'paper', align: 'l', text: (r) => r.doi ?? '', tex: (r) => (r.doi ? `\\texttt{${texEscape(r.doi)}}` : '') },
  { id: 'citations', label: 'Cites', scope: 'paper', align: 'r', text: (r) => (r.citations != null ? String(r.citations) : ''), tex: (r) => (r.citations != null ? String(r.citations) : '') },
];

const INT_MEAS_COLS: Col[] = [
  { id: 'current', label: 'Current', scope: 'meas', align: 'l', text: (r) => ss(r, 'current'), tex: (r) => texEscape(ss(r, 'current')) },
  { id: 'flavor', label: 'Flavour', scope: 'meas', align: 'l', text: (r) => sa(r, 'flavor').map(flavorLabel).join(', '), tex: (r) => sa(r, 'flavor').map(flavorTex).join(', ') },
  { id: 'target', label: 'Target', scope: 'meas', align: 'l', text: (r) => sa(r, 'target').join(', '), tex: (r) => uni2tex(sa(r, 'target').join(', ')) },
  { id: 'topology', label: 'Topology', scope: 'meas', align: 'l', text: (r) => ss(r, 'topology'), tex: (r) => uni2tex(ss(r, 'topology')) },
  { id: 'measurement_type', label: 'Type', scope: 'meas', align: 'l', text: (r) => ss(r, 'measurement_type'), tex: (r) => texEscape(ss(r, 'measurement_type')) },
  { id: 'observables', label: 'Observable', scope: 'meas', align: 'l', text: (r) => ss(r, 'observables'), tex: (r) => uni2tex(ss(r, 'observables')) },
  { id: 'energy', label: 'Energy', scope: 'meas', align: 'l', text: (r) => ss(r, 'energy_notes'), tex: (r) => uni2tex(ss(r, 'energy_notes')) },
];

const OSC_MEAS_COLS: Col[] = [
  { id: 'source', label: 'Source', scope: 'meas', align: 'l', text: (r) => ss(r, 'source'), tex: (r) => texEscape(ss(r, 'source')) },
  { id: 'framework', label: 'Framework', scope: 'meas', align: 'l', text: (r) => ss(r, 'framework'), tex: (r) => texEscape(ss(r, 'framework')) },
  { id: 'bsm', label: 'BSM', scope: 'meas', align: 'l', text: (r) => ss(r, 'bsm_type'), tex: (r) => texEscape(ss(r, 'bsm_type')) },
  { id: 'channel', label: 'Channel', scope: 'meas', align: 'l', text: (r) => sa(r, 'channel').join(', '), tex: (r) => sa(r, 'channel').map(channelTex).join(', ') },
  { id: 'mode', label: 'Mode', scope: 'meas', align: 'l', text: (r) => sa(r, 'oscmode').join(', '), tex: (r) => texEscape(sa(r, 'oscmode').join(', ')) },
  { id: 'parameter', label: 'Parameters', scope: 'meas', align: 'l', text: (r) => sa(r, 'parameters').join(', '), tex: (r) => sa(r, 'parameters').map(paramTex).join(', ') },
];

const columnsFor = (c: Cluster) => [...PAPER_COLS, ...(c === 'interactions' ? INT_MEAS_COLS : OSC_MEAS_COLS)];

const DEFAULT_COLS: Record<Cluster, Record<Mode, string[]>> = {
  interactions: {
    paper: ['experiment', 'year', 'title', 'cite'],
    meas: ['experiment', 'topology', 'target', 'flavor', 'year'],
  },
  oscillations: {
    paper: ['experiment', 'year', 'title', 'cite'],
    meas: ['experiment', 'source', 'channel', 'parameter', 'year'],
  },
};

const uniq = (a: string[]) => Array.from(new Set(a));
const arr = (m: TBMeas, k: string) => (m[k] as string[] | undefined) ?? [];
const str = (m: TBMeas, k: string) => m[k] as string | null | undefined;

function measRowFields(cluster: Cluster, m: TBMeas): Record<string, unknown> {
  if (cluster === 'interactions') {
    return {
      current: m.current,
      flavor: m.flavor,
      target: m.target,
      topology: m.topology,
      measurement_type: m.measurement_type,
      observables: m.observables,
      energy_notes: m.energy_notes,
    };
  }
  return {
    source: m.source,
    framework: m.framework,
    bsm_type: m.bsm_type,
    channel: m.channel,
    oscmode: m.mode,
    parameters: m.parameters,
  };
}

function measFacets(cluster: Cluster, exps: string[], m: TBMeas): Record<string, string[]> {
  if (cluster === 'interactions') {
    return {
      experiment: exps,
      current: str(m, 'current') ? [str(m, 'current') as string] : [],
      flavor: arr(m, 'flavor'),
      target: arr(m, 'target'),
      topology: str(m, 'topology') ? [str(m, 'topology') as string] : [],
      measurement_type: str(m, 'measurement_type') ? [str(m, 'measurement_type') as string] : [],
    };
  }
  return {
    experiment: exps,
    source: str(m, 'source') ? [str(m, 'source') as string] : [],
    framework: str(m, 'framework') ? [str(m, 'framework') as string] : [],
    mode: arr(m, 'mode'),
    channel: arr(m, 'channel'),
    parameter: arr(m, 'parameters'),
  };
}

function paperFacets(cluster: Cluster, p: TBPaper): Record<string, string[]> {
  const ms = p.measurements;
  if (cluster === 'interactions') {
    return {
      experiment: p.experiments,
      current: uniq(ms.map((m) => str(m, 'current')).filter(Boolean) as string[]),
      flavor: uniq(ms.flatMap((m) => arr(m, 'flavor'))),
      target: uniq(ms.flatMap((m) => arr(m, 'target'))),
      topology: uniq(ms.map((m) => str(m, 'topology')).filter(Boolean) as string[]),
      measurement_type: uniq(ms.map((m) => str(m, 'measurement_type')).filter(Boolean) as string[]),
    };
  }
  return {
    experiment: p.experiments,
    source: uniq(ms.map((m) => str(m, 'source')).filter(Boolean) as string[]),
    framework: uniq(ms.map((m) => str(m, 'framework')).filter(Boolean) as string[]),
    mode: uniq(ms.flatMap((m) => arr(m, 'mode'))),
    channel: uniq(ms.flatMap((m) => arr(m, 'channel'))),
    parameter: uniq(ms.flatMap((m) => arr(m, 'parameters'))),
  };
}

export function TableBuilder({
  cluster,
  data,
  facets,
}: {
  cluster: Cluster;
  data: TBPaper[];
  facets: RowFacet[];
}) {
  const [mode, setMode] = useState<Mode>('meas');
  const [active, setActive] = useState<Record<string, string>>({});
  const [cols, setCols] = useState<Record<Mode, string[]>>(DEFAULT_COLS[cluster]);
  const [copied, setCopied] = useState(false);

  const allCols = useMemo(() => columnsFor(cluster), [cluster]);
  const availableCols = useMemo(
    () => allCols.filter((c) => c.scope === 'both' || c.scope === mode),
    [allCols, mode],
  );
  const selectedCols = useMemo(
    () => availableCols.filter((c) => cols[mode].includes(c.id)),
    [availableCols, cols, mode],
  );

  const rows = useMemo<Row[]>(() => {
    const base = (p: TBPaper) => ({
      citekey: p.citekey,
      title: p.title,
      titleHtml: p.titleHtml,
      experiment: p.experiment,
      year: p.year,
      journal: p.journal,
      arxiv: p.arxiv,
      doi: p.doi,
      citations: p.citations,
    });
    if (mode === 'paper') {
      return data.map((p) => ({ ...base(p), facets: paperFacets(cluster, p) }));
    }
    return data.flatMap((p) =>
      p.measurements.map((m) => ({
        ...base(p),
        ...measRowFields(cluster, m),
        facets: measFacets(cluster, p.experiments, m),
      })),
    );
  }, [data, mode, cluster]);

  const visible = useMemo(
    () =>
      rows.filter((r) =>
        facets.every((f) => {
          const v = active[f.key] ?? ALL;
          return v === ALL || (r.facets[f.key] ?? []).includes(v);
        }),
      ),
    [rows, facets, active],
  );

  const caption = `Neutrino ${cluster === 'interactions' ? 'interaction' : 'oscillation'} data (nubib.org).`;
  const latex = useMemo(() => buildLatex(selectedCols, visible, caption), [selectedCols, visible, caption]);

  function toggleCol(id: string) {
    setCols((c) => {
      const cur = c[mode];
      const next = cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id];
      return { ...c, [mode]: next };
    });
  }
  function copyLatex() {
    navigator.clipboard?.writeText(latex).then(
      () => {
        setCopied(true);
        window.setTimeout(() => setCopied(false), 1600);
      },
      () => {},
    );
  }
  function downloadTex() {
    const slug = fileSlug([cluster, ...facets.map((f) => active[f.key])]);
    downloadText(`nubib-${slug}.tex`, latex, 'text/x-tex');
  }

  const noCols = selectedCols.length === 0;
  const rowWord = mode === 'paper' ? 'paper' : 'result';

  return (
    <div className="tb">
      <div className="tb-controls panel">
        <div className="tb-row">
          <span className="tb-label">Rows</span>
          <div className="seg" role="group" aria-label="Row mode">
            <button className={mode === 'meas' ? 'is-on' : ''} onClick={() => setMode('meas')} type="button">
              One per result
            </button>
            <button className={mode === 'paper' ? 'is-on' : ''} onClick={() => setMode('paper')} type="button">
              One per paper
            </button>
          </div>
        </div>

        <div className="tb-row tb-filters">
          <span className="tb-label">Filter</span>
          {facets.map((f) => (
            <label key={f.key} className="tb-filter">
              {f.label}
              <select
                value={active[f.key] ?? ALL}
                onChange={(e) => {
                  const value = e.currentTarget.value;
                  setActive((c) => ({ ...c, [f.key]: value }));
                }}
              >
                <option value={ALL}>{f.allLabel}</option>
                {f.values.map((v) => (
                  <option key={v} value={v}>
                    {f.key === 'flavor' ? flavorLabel(v) : v}
                  </option>
                ))}
              </select>
            </label>
          ))}
          <button className="tb-clear" onClick={() => setActive({})} type="button">
            Clear
          </button>
        </div>

        <div className="tb-row tb-cols">
          <span className="tb-label">Columns</span>
          <div className="tb-col-chips">
            {availableCols.map((c) => (
              <button
                key={c.id}
                aria-pressed={cols[mode].includes(c.id)}
                className="challenge-chip"
                onClick={() => toggleCol(c.id)}
                type="button"
              >
                {c.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="tb-resultbar">
        <p>
          {visible.length} {visible.length === 1 ? rowWord : `${rowWord}s`}
          {' · '}
          {selectedCols.length} {selectedCols.length === 1 ? 'column' : 'columns'}
        </p>
        <div className="tb-exports">
          <button className="papers-bib-btn" onClick={copyLatex} type="button" disabled={noCols || !visible.length}>
            <Icon name={copied ? 'check' : 'copy'} size={14} />
            <span>{copied ? 'Copied' : 'Copy LaTeX'}</span>
          </button>
          <button className="papers-bib-btn" onClick={downloadTex} type="button" disabled={noCols || !visible.length}>
            <Icon name="download" size={14} />
            <span>.tex</span>
          </button>
        </div>
      </div>

      {noCols ? (
        <p className="papers-empty">Pick at least one column to build a table.</p>
      ) : !visible.length ? (
        <p className="papers-empty">No rows match these filters. Try clearing some.</p>
      ) : (
        <div className="tb-preview">
          <table>
            <thead>
              <tr>
                {selectedCols.map((c) => (
                  <th key={c.id} className={c.align === 'r' ? 'tb-num' : ''}>
                    {c.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {visible.map((r, i) => (
                <tr key={`${r.citekey}-${i}`}>
                  {selectedCols.map((c) => (
                    <td key={c.id} className={c.align === 'r' ? 'tb-num' : ''}>
                      {c.html ? <span dangerouslySetInnerHTML={{ __html: c.html(r) }} /> : c.text(r)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function buildLatex(cols: Col[], rows: Row[], caption: string): string {
  if (!cols.length || !rows.length) return '';
  const spec = cols.map((c) => c.align).join('');
  const header = cols.map((c) => `\\textbf{${texEscape(c.label)}}`).join(' & ') + ' \\\\';
  const body = rows.map((r) => '    ' + cols.map((c) => c.tex(r)).join(' & ') + ' \\\\').join('\n');
  return [
    '% Requires \\usepackage{booktabs}',
    '\\begin{table}[ht]',
    '  \\centering',
    `  \\caption{${caption}}`,
    '  \\label{tab:nubib}',
    `  \\begin{tabular}{${spec}}`,
    '    \\toprule',
    '    ' + header,
    '    \\midrule',
    body,
    '    \\bottomrule',
    '  \\end{tabular}',
    '\\end{table}',
  ].join('\n');
}
