import fs from 'node:fs';
import path from 'node:path';
import { parse as parseYaml } from 'yaml';
import type { Timeline } from './papers';

// Oscillation cluster — parallel to lib/papers.ts but reads data/oscillation/*.yml.
const REPO_ROOT = path.join(process.cwd(), '..');
const OSC_DIR = path.join(REPO_ROOT, 'data', 'oscillation');

export type OscChannel = { from: string; to: string; nubar?: boolean };

export type OscMeasurement = {
  source: 'solar' | 'atmospheric' | 'reactor' | 'accelerator';
  framework: 'PMNS' | 'Exotic';
  bsm_type?: string | null;
  channels: OscChannel[];
  mode?: string[];
  parameters?: string[];
  observables?: string | null;
  notes?: string | null;
};

export type OscPaper = {
  bibtag: string;
  title: string;
  collaboration: string;
  collaborations?: string[];
  arxiv?: string | null;
  doi?: string | null;
  journal?: string | null;
  volume?: string | null;
  pages?: string | null;
  year: number | null;
  published_date?: string | null;
  inspire_recid?: number | null;
  citation_count?: number | null;
  abstract?: string | null;
  added?: string | null;
  notes?: string | null;
  links?: Record<string, string | null>;
  measurements: OscMeasurement[];
  // derived
  slug: string;
  bibtex: string;
};

export function bibtagToSlug(bibtag: string): string {
  return bibtag.replace(/:/g, '-').toLowerCase();
}

const FLAVOR_SYMBOL: Record<string, string> = { nue: 'νe', numu: 'νμ', nutau: 'ντ', nus: 'νs' };

/** Human transition label, e.g. {from:numu,to:nue,nubar:true} -> "ν̄μ→ν̄e". */
export function channelLabel(c: OscChannel): string {
  const bar = c.nubar ? '̄' : '';
  const f = (k: string) => {
    const s = FLAVOR_SYMBOL[k] ?? k;
    return c.nubar ? `ν${bar}${s.slice(1)}` : s;
  };
  return `${f(c.from)}→${f(c.to)}`;
}

// ASCII aliases so the free-text search still matches typed forms like "theta13" / "dm2_32" / "dcp".
const PARAM_ALIAS: Record<string, string> = {
  'θ₁₂': 'theta12',
  'θ₁₃': 'theta13',
  'θ₂₃': 'theta23',
  'θ₁₄': 'theta14',
  'θ₂₄': 'theta24',
  'θ₃₄': 'theta34',
  'Δm²₂₁': 'dm2_21 dm221',
  'Δm²₃₁': 'dm2_31 dm231',
  'Δm²₃₂': 'dm2_32 dm232',
  'Δm²₄₁': 'dm2_41 dm241',
  δCP: 'dcp delta-cp',
};
export function paramSearchAliases(params: string[]): string[] {
  return params.map((p) => PARAM_ALIAS[p]).filter(Boolean);
}

function synthBibtex(p: OscPaper): string {
  const f = (k: string, v: unknown) => (v ? `  ${k} = "${v}",\n` : '');
  return (
    `@article{${p.bibtag},\n` +
    f('collaboration', p.collaboration) +
    f('title', `{${p.title}}`) +
    f('eprint', p.arxiv) +
    f('doi', p.doi) +
    f('journal', p.journal) +
    f('volume', p.volume) +
    f('pages', p.pages) +
    f('year', p.year) +
    `}`
  );
}

let _cache: OscPaper[] | null = null;

export function getAllOscPapers(): OscPaper[] {
  if (_cache) return _cache;
  const papers: OscPaper[] = [];
  if (!fs.existsSync(OSC_DIR)) return papers;
  for (const file of fs.readdirSync(OSC_DIR)) {
    if (!file.endsWith('.yml') && !file.endsWith('.yaml')) continue;
    const records = parseYaml(fs.readFileSync(path.join(OSC_DIR, file), 'utf8')) as OscPaper[];
    for (const rec of records ?? []) {
      rec.slug = bibtagToSlug(rec.bibtag);
      rec.bibtex = synthBibtex(rec);
      papers.push(rec);
    }
  }
  papers.sort((a, b) => (b.year ?? 0) - (a.year ?? 0) || a.bibtag.localeCompare(b.bibtag));
  _cache = papers;
  return papers;
}

// ---- facets --------------------------------------------------------------

export type Facet = { key: string; label: string; allLabel: string; values: string[] };

function uniqueSorted(values: string[]): string[] {
  return Array.from(new Set(values)).sort((a, b) => a.localeCompare(b));
}
function countBy(values: string[]): [string, number][] {
  const m = new Map<string, number>();
  for (const v of values) m.set(v, (m.get(v) ?? 0) + 1);
  return Array.from(m.entries()).sort((a, b) => b[1] - a[1]);
}

/** Flatten facet membership for an oscillation paper. */
/** All experiments for a paper (the joint-analysis list, or the single primary). */
export function paperExperiments(p: OscPaper): string[] {
  return p.collaborations && p.collaborations.length ? p.collaborations : [p.collaboration];
}

export function oscFacetValues(p: OscPaper): Record<string, string[]> {
  return {
    experiment: paperExperiments(p),
    source: uniqueSorted(p.measurements.map((m) => m.source)),
    framework: uniqueSorted(p.measurements.map((m) => m.framework)),
    mode: uniqueSorted(p.measurements.flatMap((m) => m.mode ?? [])),
    channel: uniqueSorted(p.measurements.flatMap((m) => (m.channels ?? []).map(channelLabel))),
    parameter: uniqueSorted(p.measurements.flatMap((m) => m.parameters ?? [])),
  };
}

// ---- timeline (papers/citations per year, broken down by dimension) --------

const TL_DIMS: { key: string; label: string; values: (p: OscPaper) => string[] }[] = [
  { key: 'experiment', label: 'Experiment', values: (p) => paperExperiments(p) },
  { key: 'source', label: 'Source', values: (p) => uniqueSorted(p.measurements.map((m) => m.source)) },
  { key: 'framework', label: 'Framework', values: (p) => uniqueSorted(p.measurements.map((m) => m.framework)) },
  { key: 'mode', label: 'Mode', values: (p) => uniqueSorted(p.measurements.flatMap((m) => m.mode ?? [])) },
  {
    key: 'channel',
    label: 'Channel',
    values: (p) => uniqueSorted(p.measurements.flatMap((m) => (m.channels ?? []).map(channelLabel))),
  },
  {
    key: 'parameter',
    label: 'Parameter',
    values: (p) => uniqueSorted(p.measurements.flatMap((m) => m.parameters ?? [])),
  },
];

/** Per-year paper counts and citation sums for the oscillation cluster, by dimension. */
export function getOscTimeline(papers: OscPaper[]): Timeline {
  const ys = papers.map((p) => p.year).filter((y): y is number => Boolean(y));
  if (!ys.length) return { years: [], total: { papers: [], citations: [] }, dims: [] };
  const min = Math.min(...ys);
  const max = Math.max(...ys);
  const years = Array.from({ length: max - min + 1 }, (_, i) => min + i);
  const idx = new Map(years.map((y, i) => [y, i]));
  const zeros = () => years.map(() => 0);
  const total = { papers: zeros(), citations: zeros() };
  const dims = TL_DIMS.map((s) => ({
    key: s.key,
    label: s.label,
    values: [] as string[],
    series: {} as Record<string, { papers: number[]; citations: number[] }>,
  }));
  for (const p of papers) {
    if (p.year == null) continue;
    const i = idx.get(p.year);
    if (i == null) continue;
    const c = p.citation_count ?? 0;
    total.papers[i] += 1;
    total.citations[i] += c;
    TL_DIMS.forEach((s, di) => {
      for (const v of s.values(p)) {
        const ser = (dims[di].series[v] ??= { papers: zeros(), citations: zeros() });
        ser.papers[i] += 1;
        ser.citations[i] += c;
      }
    });
  }
  const sum = (a: number[]) => a.reduce((x, y) => x + y, 0);
  for (const d of dims) {
    d.values = Object.keys(d.series).sort((a, b) => sum(d.series[b].papers) - sum(d.series[a].papers));
  }
  return { years, total, dims };
}

export function getOscFacets(papers: OscPaper[]): Facet[] {
  const experiments = uniqueSorted(papers.flatMap(paperExperiments));
  const sources = countBy(papers.flatMap((p) => p.measurements.map((m) => m.source))).map(([v]) => v);
  const frameworks = ['PMNS', 'Exotic'];
  const modes = countBy(papers.flatMap((p) => p.measurements.flatMap((m) => m.mode ?? []))).map(
    ([v]) => v,
  );
  const channels = countBy(
    papers.flatMap((p) => p.measurements.flatMap((m) => (m.channels ?? []).map(channelLabel))),
  ).map(([v]) => v);
  const parameters = countBy(
    papers.flatMap((p) => p.measurements.flatMap((m) => m.parameters ?? [])),
  ).map(([v]) => v);
  return [
    { key: 'experiment', label: 'Experiment', allLabel: 'All experiments', values: experiments },
    { key: 'source', label: 'Source', allLabel: 'All sources', values: sources },
    { key: 'framework', label: 'Framework', allLabel: 'PMNS + Exotic', values: frameworks },
    { key: 'mode', label: 'Mode', allLabel: 'All modes', values: modes },
    { key: 'channel', label: 'Channel', allLabel: 'All channels', values: channels },
    { key: 'parameter', label: 'Parameter', allLabel: 'All parameters', values: parameters },
  ];
}
