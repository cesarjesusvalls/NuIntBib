import fs from 'node:fs';
import path from 'node:path';
import { parse as parseYaml } from 'yaml';

// The canonical database lives one level up from the site/ app, in data/papers/*.yml.
const REPO_ROOT = path.join(process.cwd(), '..');
const PAPERS_DIR = path.join(REPO_ROOT, 'data', 'papers');

export type Measurement = {
  current: 'CC' | 'NC';
  flavor: string[];
  flavor_note?: string | null;
  target: string[];
  topology: string;
  pion_bucket?: string | null;
  measurement_type?: string | null;
  observables?: string | null;
  energy_notes?: string | null;
};

export type Paper = {
  bibtag: string;
  title: string;
  collaboration: string;
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
  measurements: Measurement[];
  // derived
  slug: string;
  bibtex: string;
};

export function bibtagToSlug(bibtag: string): string {
  return bibtag.replace(/:/g, '-').toLowerCase();
}

/** Split raw .bib text into { texkey: rawEntry } via brace matching. */
function indexBibtex(): Record<string, string> {
  const out: Record<string, string> = {};
  for (const file of fs.readdirSync(REPO_ROOT)) {
    if (!file.endsWith('.bib')) continue;
    const text = fs.readFileSync(path.join(REPO_ROOT, file), 'utf8');
    const re = /@(\w+)\s*\{/gi;
    let m: RegExpExecArray | null;
    while ((m = re.exec(text))) {
      const start = m.index;
      let i = m.index + m[0].length;
      const keyEnd = text.indexOf(',', i);
      const key = text.slice(i, keyEnd).trim();
      // brace-match from the entry's opening brace
      let depth = 1;
      let j = m.index + m[0].length;
      while (j < text.length && depth > 0) {
        if (text[j] === '{') depth++;
        else if (text[j] === '}') depth--;
        j++;
      }
      out[key] = text.slice(start, j).trim();
      re.lastIndex = j;
    }
  }
  return out;
}

let _cache: Paper[] | null = null;

export function getAllPapers(): Paper[] {
  if (_cache) return _cache;
  const bib = indexBibtex();
  const papers: Paper[] = [];
  for (const file of fs.readdirSync(PAPERS_DIR)) {
    if (!file.endsWith('.yml') && !file.endsWith('.yaml')) continue;
    const records = parseYaml(fs.readFileSync(path.join(PAPERS_DIR, file), 'utf8')) as Paper[];
    for (const rec of records ?? []) {
      rec.slug = bibtagToSlug(rec.bibtag);
      rec.bibtex = bib[rec.bibtag] ?? synthBibtex(rec);
      papers.push(rec);
    }
  }
  papers.sort((a, b) => (b.year ?? 0) - (a.year ?? 0) || a.bibtag.localeCompare(b.bibtag));
  _cache = papers;
  return papers;
}

function synthBibtex(p: Paper): string {
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

export function getPaperBySlug(slug: string): Paper | undefined {
  return getAllPapers().find((p) => p.slug === slug);
}

// ---- facets & stats --------------------------------------------------------

export type Facet = { key: string; label: string; allLabel: string; values: string[] };

function uniqueSorted(values: string[]): string[] {
  return Array.from(new Set(values)).sort((a, b) => a.localeCompare(b));
}

function countBy(values: string[]): [string, number][] {
  const m = new Map<string, number>();
  for (const v of values) m.set(v, (m.get(v) ?? 0) + 1);
  return Array.from(m.entries()).sort((a, b) => b[1] - a[1]);
}

export function getFacets(papers: Paper[]): Facet[] {
  const experiments = uniqueSorted(papers.map((p) => p.collaboration));
  const currents = ['CC', 'NC'];
  const flavors = uniqueSorted(papers.flatMap((p) => p.measurements.flatMap((m) => m.flavor)));
  const targets = countBy(papers.flatMap((p) => p.measurements.flatMap((m) => m.target))).map(
    ([v]) => v,
  );
  const topologies = countBy(papers.flatMap((p) => p.measurements.map((m) => m.topology))).map(
    ([v]) => v,
  );
  const types = uniqueSorted(
    papers.flatMap((p) =>
      p.measurements.map((m) => m.measurement_type).filter((x): x is string => Boolean(x)),
    ),
  );
  return [
    { key: 'experiment', label: 'Experiment', allLabel: 'All experiments', values: experiments },
    { key: 'current', label: 'Current', allLabel: 'CC + NC', values: currents },
    { key: 'flavor', label: 'Flavor', allLabel: 'All flavors', values: flavors },
    { key: 'target', label: 'Target', allLabel: 'All targets', values: targets },
    { key: 'topology', label: 'Topology', allLabel: 'All topologies', values: topologies },
    { key: 'measurement_type', label: 'Measurement', allLabel: 'All types', values: types },
  ];
}

export type DbStats = {
  papers: number;
  measurements: number;
  experiments: [string, number][];
  byCurrent: [string, number][];
  byFlavor: [string, number][];
  byTarget: [string, number][];
  byTopology: [string, number][];
  byYear: [string, number][];
  yearRange: [number, number];
  totalCitations: number;
  lastUpdated: string | null;
};

export function getStats(papers: Paper[]): DbStats {
  const years = papers.map((p) => p.year).filter((y): y is number => Boolean(y));
  const dates = papers.map((p) => p.published_date).filter(Boolean) as string[];
  return {
    papers: papers.length,
    measurements: papers.reduce((n, p) => n + p.measurements.length, 0),
    experiments: countBy(papers.map((p) => p.collaboration)),
    byCurrent: countBy(papers.flatMap((p) => p.measurements.map((m) => m.current))),
    byFlavor: countBy(papers.flatMap((p) => p.measurements.flatMap((m) => m.flavor))),
    byTarget: countBy(papers.flatMap((p) => p.measurements.flatMap((m) => m.target))),
    byTopology: countBy(papers.flatMap((p) => p.measurements.map((m) => m.topology))),
    byYear: countBy(years.map(String)).sort((a, b) => a[0].localeCompare(b[0])),
    yearRange: [Math.min(...years), Math.max(...years)],
    totalCitations: papers.reduce((n, p) => n + (p.citation_count ?? 0), 0),
    lastUpdated: dates.sort().at(-1) ?? null,
  };
}

export type Timeline = {
  years: number[];
  total: { papers: number[]; citations: number[] };
  byExp: Record<string, { papers: number[]; citations: number[] }>;
  experiments: string[]; // sorted by total papers, desc
};

/** Per-year (and per-experiment) paper counts and citation sums, for the time chart. */
export function getTimeline(papers: Paper[]): Timeline {
  const ys = papers.map((p) => p.year).filter((y): y is number => Boolean(y));
  const min = Math.min(...ys);
  const max = Math.max(...ys);
  const years = Array.from({ length: max - min + 1 }, (_, i) => min + i);
  const idx = new Map(years.map((y, i) => [y, i]));
  const zeros = () => years.map(() => 0);
  const total = { papers: zeros(), citations: zeros() };
  const byExp: Record<string, { papers: number[]; citations: number[] }> = {};
  for (const p of papers) {
    if (p.year == null) continue;
    const i = idx.get(p.year);
    if (i == null) continue;
    const c = p.citation_count ?? 0;
    total.papers[i] += 1;
    total.citations[i] += c;
    (byExp[p.collaboration] ??= { papers: zeros(), citations: zeros() });
    byExp[p.collaboration].papers[i] += 1;
    byExp[p.collaboration].citations[i] += c;
  }
  const sum = (a: number[]) => a.reduce((x, y) => x + y, 0);
  const experiments = Object.keys(byExp).sort(
    (a, b) => sum(byExp[b].papers) - sum(byExp[a].papers),
  );
  return { years, total, byExp, experiments };
}

/** Flatten facet membership for a paper (used by the client filter). */
export function paperFacetValues(p: Paper): Record<string, string[]> {
  return {
    experiment: [p.collaboration],
    current: uniqueSorted(p.measurements.map((m) => m.current)),
    flavor: uniqueSorted(p.measurements.flatMap((m) => m.flavor)),
    target: uniqueSorted(p.measurements.flatMap((m) => m.target)),
    topology: uniqueSorted(p.measurements.map((m) => m.topology)),
    measurement_type: uniqueSorted(
      p.measurements.map((m) => m.measurement_type).filter((x): x is string => Boolean(x)),
    ),
  };
}
