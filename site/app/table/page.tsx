import type { Metadata } from 'next';
import { PageHero } from '@/components/UI';
import { TableBuilder, type TBPaper, type RowFacet } from '@/components/TableBuilder';
import { getAllPapers, getFacets } from '@/lib/papers';
import { stripTex, texToHtml } from '@/lib/tex';

export const metadata: Metadata = {
  title: 'Table builder',
  description:
    'Assemble a custom table of neutrino interaction measurements — pick columns and filters, preview it, and export a ready-to-paste LaTeX (booktabs) table.',
};

export default function TablePage() {
  const papers = getAllPapers();
  const facets = getFacets(papers) as RowFacet[];

  const data: TBPaper[] = papers.map((p) => ({
    citekey: p.bibtag,
    title: stripTex(p.title),
    titleHtml: texToHtml(p.title),
    experiment: p.collaboration,
    year: p.year,
    journal: p.journal ?? null,
    arxiv: p.arxiv ?? null,
    doi: p.doi ?? null,
    citations: p.citation_count ?? null,
    measurements: p.measurements.map((m) => ({
      current: m.current,
      flavor: m.flavor ?? [],
      target: m.target ?? [],
      topology: m.topology,
      measurement_type: m.measurement_type ?? null,
      observables: m.observables ?? null,
      energy_notes: m.energy_notes ?? null,
    })),
  }));

  return (
    <>
      <PageHero
        eyebrow="Table builder"
        title="Build a table for your slides or paper"
        body="Pick the rows, columns, and filters; preview a clean table to screenshot, or export it as a ready-to-paste LaTeX (booktabs) table."
        className="page-hero-flush"
      />
      <section className="section section-papers">
        <div className="container">
          <TableBuilder data={data} facets={facets} />
        </div>
      </section>
    </>
  );
}
