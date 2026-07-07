import fs from 'node:fs';
import path from 'node:path';
import { texToHtml } from './tex';

// Data releases (parsed distributions) live alongside the paper database, in
// data/datasets/<source>/<slug>.json. Built by scripts/build_datasets.py.
const DATASETS_DIR = path.join(process.cwd(), '..', 'data', 'datasets');

export type DataBin = {
  i: number;
  lo: number;
  hi: number;
  hi_true?: number;   // true upper edge when a bin is display-clipped (overflow)
  center: number;
  val: number;
  err: number;
  err_up?: number;    // asymmetric errors (default to err)
  err_down?: number;
  cat_tex?: string;   // categorical x-axis label (xcat items), LaTeX
  cat?: string;       // plain-text category (for CSV)
  catHtml?: string;   // rendered at build time
};

export type Slice = {
  label_tex: string;
  label: string;
  labelHtml: string;   // added at build time
  lo: number;
  hi: number;
  nbins: number;
  bins: DataBin[];
  scale_note: string | null;
};

export type Distribution = {
  key: string;
  name: string;
  slug: string;
  xlabel: string;
  xunit: string;
  ylabel: string;
  ylabel_plot: string;
  yunit: string;
  // LaTeX source for the card title/subtitle
  name_tex: string;
  xlabel_tex?: string;
  ylabel_tex: string;
  yunit_tex: string;
  // KaTeX-rendered HTML (added at build time by getDataRelease)
  nameHtml: string;
  xlabelHtml: string;
  xunitHtml: string;
  ylabelHtml: string;
  yunitHtml: string;
  nbins: number;
  bins: DataBin[];
  // 2-D (double-differential) measurements: one data item, many slices
  is2d?: boolean;
  slicevar_tex?: string;
  slices?: Slice[];
  // single flux-averaged value(s): x is a category label (xlabel), no numeric axis
  xcat?: boolean;
  source: string;
  source_url: string;
  provenance: string;
  nuisance_file: string;
};

export type Covariance = {
  order: string[];      // human label for each matrix row/column
  matrix: number[][];
  note?: string;
};

export type Flux = {
  note?: string;
  columns: string[];
  rows: number[][];
};

export type DataRelease = {
  bibtag: string;
  slug: string;
  source: string;
  source_url?: string;
  arxiv?: string;
  cite?: string;
  note?: string;
  covariance?: Covariance;
  flux?: Flux;
  distributions: Distribution[];
};

/** Return the data release for a paper slug, or null if none is registered. */
export function getDataRelease(slug: string): DataRelease | null {
  for (const source of ['nuisance']) {
    const file = path.join(DATASETS_DIR, source, `${slug}.json`);
    if (fs.existsSync(file)) {
      const release = JSON.parse(fs.readFileSync(file, 'utf8')) as DataRelease;
      // render LaTeX labels to HTML once, at build time (KaTeX, server-side)
      for (const d of release.distributions) {
        d.nameHtml = texToHtml(d.name_tex);
        // KaTeX x-label when we have the LaTeX; else fall back to the plain unicode
        // label (e.g. legacy releases with no xlabel_tex) so the axis is never blank.
        d.xlabelHtml = d.xlabel_tex
          ? texToHtml(d.xlabel_tex)
          : `<span>${(d.xlabel ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')}</span>`;
        d.ylabelHtml = texToHtml(d.ylabel_tex);
        // Units as upright math (\mathrm) so "cm^2/(GeV/c)" renders as cm²/(GeV/c),
        // not literal carets. texToHtml swallows any KaTeX error to the escaped source.
        const unitHtml = (u?: string) => (u ? texToHtml(`$\\mathrm{${u}}$`) : '');
        d.xunitHtml = unitHtml(d.xunit);
        d.yunitHtml = unitHtml(d.yunit);
        if (d.slices) for (const s of d.slices) s.labelHtml = texToHtml(s.label_tex);
        if (d.xcat) for (const b of d.bins) b.catHtml = texToHtml(b.cat_tex ?? '');
      }
      return release;
    }
  }
  return null;
}

/** Slugs that have a data release — used to badge them elsewhere later. */
export function getDataReleaseSlugs(): Set<string> {
  const out = new Set<string>();
  for (const source of ['nuisance']) {
    const dir = path.join(DATASETS_DIR, source);
    if (!fs.existsSync(dir)) continue;
    for (const f of fs.readdirSync(dir)) {
      if (f.endsWith('.json')) out.add(f.replace(/\.json$/, ''));
    }
  }
  return out;
}
