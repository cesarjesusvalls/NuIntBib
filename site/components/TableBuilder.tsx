'use client';

import { useMemo, useState } from 'react';
import { Icon } from '@/components/Icon';
import { downloadText, fileSlug } from '@/lib/download';

type Measurement = {
  current: string;
  flavor: string[];
  target: string[];
  topology: string;
  measurement_type: string | null;
  observables: string | null;
  energy_notes: string | null;
};

export type TBPaper = {
  citekey: string;
  title: string;
  titleHtml: string;
  experiment: string;
  year: number | null;
  journal: string | null;
  arxiv: string | null;
  doi: string | null;
  citations: number | null;
  measurements: Measurement[];
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
  current?: string;
  flavor?: string[];
  target?: string[];
  topology?: string;
  measurement_type?: string | null;
  observables?: string | null;
  energy_notes?: string | null;
  facets: Record<string, string[]>;
};

const FLAVOR_LABEL: Record<string, string> = {
  numu: 'νμ',
  numubar: 'ν̄μ',
  nue: 'νe',
  nuebar: 'ν̄e',
};
const FLAVOR_TEX: Record<string, string> = {
  numu: '$\\nu_\\mu$',
  numubar: '$\\bar\\nu_\\mu$',
  nue: '$\\nu_e$',
  nuebar: '$\\bar\\nu_e$',
};
const flavorLabel = (f: string) => FLAVOR_LABEL[f] ?? f;
const flavorTex = (f: string) => FLAVOR_TEX[f] ?? texEscape(f);

// physics Unicode -> LaTeX math, applied after escaping the surrounding text
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

type Col = {
  id: string;
  label: string;
  scope: Mode | 'both';
  align: 'l' | 'r';
  text: (r: Row) => string;
  html?: (r: Row) => string;
  tex: (r: Row) => string;
};

const COLUMNS: Col[] = [
  { id: 'experiment', label: 'Experiment', scope: 'both', align: 'l', text: (r) => r.experiment, tex: (r) => texEscape(r.experiment) },
  { id: 'year', label: 'Year', scope: 'both', align: 'r', text: (r) => (r.year != null ? String(r.year) : ''), tex: (r) => (r.year != null ? String(r.year) : '') },
  { id: 'title', label: 'Title', scope: 'paper', align: 'l', text: (r) => r.title, html: (r) => r.titleHtml, tex: (r) => uni2tex(r.title) },
  { id: 'citekey', label: 'Key', scope: 'both', align: 'l', text: (r) => r.citekey, tex: (r) => `\\texttt{${texEscape(r.citekey)}}` },
  { id: 'cite', label: 'Citation', scope: 'both', align: 'l', text: (r) => `[${r.citekey}]`, tex: (r) => `\\cite{${r.citekey}}` },
  { id: 'journal', label: 'Journal', scope: 'paper', align: 'l', text: (r) => r.journal ?? '', tex: (r) => texEscape(r.journal ?? '') },
  { id: 'arxiv', label: 'arXiv', scope: 'paper', align: 'l', text: (r) => r.arxiv ?? '', tex: (r) => (r.arxiv ? `\\texttt{${texEscape(r.arxiv)}}` : '') },
  { id: 'doi', label: 'DOI', scope: 'paper', align: 'l', text: (r) => r.doi ?? '', tex: (r) => (r.doi ? `\\texttt{${texEscape(r.doi)}}` : '') },
  { id: 'citations', label: 'Cites', scope: 'paper', align: 'r', text: (r) => (r.citations != null ? String(r.citations) : ''), tex: (r) => (r.citations != null ? String(r.citations) : '') },
  { id: 'current', label: 'Current', scope: 'meas', align: 'l', text: (r) => r.current ?? '', tex: (r) => texEscape(r.current ?? '') },
  { id: 'flavor', label: 'Flavour', scope: 'meas', align: 'l', text: (r) => (r.flavor ?? []).map(flavorLabel).join(', '), tex: (r) => (r.flavor ?? []).map(flavorTex).join(', ') },
  { id: 'target', label: 'Target', scope: 'meas', align: 'l', text: (r) => (r.target ?? []).join(', '), tex: (r) => uni2tex((r.target ?? []).join(', ')) },
  { id: 'topology', label: 'Topology', scope: 'meas', align: 'l', text: (r) => r.topology ?? '', tex: (r) => uni2tex(r.topology ?? '') },
  { id: 'measurement_type', label: 'Type', scope: 'meas', align: 'l', text: (r) => r.measurement_type ?? '', tex: (r) => texEscape(r.measurement_type ?? '') },
  { id: 'observables', label: 'Observable', scope: 'meas', align: 'l', text: (r) => r.observables ?? '', tex: (r) => uni2tex(r.observables ?? '') },
  { id: 'energy', label: 'Energy', scope: 'meas', align: 'l', text: (r) => r.energy_notes ?? '', tex: (r) => uni2tex(r.energy_notes ?? '') },
];

const DEFAULT_COLS: Record<Mode, string[]> = {
  paper: ['experiment', 'year', 'title', 'cite'],
  meas: ['experiment', 'topology', 'target', 'flavor', 'year'],
};

const uniq = (a: string[]) => Array.from(new Set(a));

function paperFacets(p: TBPaper): Record<string, string[]> {
  return {
    experiment: [p.experiment],
    current: uniq(p.measurements.map((m) => m.current)),
    flavor: uniq(p.measurements.flatMap((m) => m.flavor)),
    target: uniq(p.measurements.flatMap((m) => m.target)),
    topology: uniq(p.measurements.map((m) => m.topology)),
    measurement_type: uniq(p.measurements.map((m) => m.measurement_type).filter((x): x is string => Boolean(x))),
  };
}

export function TableBuilder({ data, facets }: { data: TBPaper[]; facets: RowFacet[] }) {
  const [mode, setMode] = useState<Mode>('meas');
  const [active, setActive] = useState<Record<string, string>>({});
  const [cols, setCols] = useState<Record<Mode, string[]>>(DEFAULT_COLS);
  const [copied, setCopied] = useState(false);

  const availableCols = useMemo(
    () => COLUMNS.filter((c) => c.scope === 'both' || c.scope === mode),
    [mode],
  );
  const selectedCols = useMemo(
    () => availableCols.filter((c) => cols[mode].includes(c.id)),
    [availableCols, cols, mode],
  );

  const rows = useMemo<Row[]>(() => {
    const base = (p: TBPaper): Omit<Row, 'facets'> => ({
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
      return data.map((p) => ({ ...base(p), facets: paperFacets(p) }));
    }
    return data.flatMap((p) =>
      p.measurements.map((m) => ({
        ...base(p),
        current: m.current,
        flavor: m.flavor,
        target: m.target,
        topology: m.topology,
        measurement_type: m.measurement_type,
        observables: m.observables,
        energy_notes: m.energy_notes,
        facets: {
          experiment: [p.experiment],
          current: [m.current],
          flavor: m.flavor,
          target: m.target,
          topology: [m.topology],
          measurement_type: m.measurement_type ? [m.measurement_type] : [],
        },
      })),
    );
  }, [data, mode]);

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

  const latex = useMemo(() => buildLatex(selectedCols, visible), [selectedCols, visible]);

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
    const slug = fileSlug(facets.map((f) => active[f.key]));
    downloadText(`nubib-${slug}.tex`, latex, 'text/x-tex');
  }

  const noCols = selectedCols.length === 0;

  return (
    <div className="tb">
      <div className="tb-controls panel">
        <div className="tb-row">
          <span className="tb-label">Rows</span>
          <div className="seg" role="group" aria-label="Row mode">
            <button className={mode === 'meas' ? 'is-on' : ''} onClick={() => setMode('meas')} type="button">
              One per measurement
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
          {visible.length} {mode === 'paper' ? (visible.length === 1 ? 'paper' : 'papers') : visible.length === 1 ? 'measurement' : 'measurements'}
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
                      {c.html ? (
                        <span dangerouslySetInnerHTML={{ __html: c.html(r) }} />
                      ) : (
                        c.text(r)
                      )}
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

function buildLatex(cols: Col[], rows: Row[]): string {
  if (!cols.length || !rows.length) return '';
  const spec = cols.map((c) => c.align).join('');
  const header = cols.map((c) => `\\textbf{${texEscape(c.label)}}`).join(' & ') + ' \\\\';
  const body = rows.map((r) => '    ' + cols.map((c) => c.tex(r)).join(' & ') + ' \\\\').join('\n');
  return [
    '% Requires \\usepackage{booktabs}',
    '\\begin{table}[ht]',
    '  \\centering',
    '  \\caption{Neutrino interaction measurements (nubib.org).}',
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
