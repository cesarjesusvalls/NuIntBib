import type { Metadata } from 'next';
import { PageHero } from '@/components/UI';
import { ClusteredTable } from '@/components/ClusteredTable';
import type { TBPaper, RowFacet } from '@/components/TableBuilder';
import { getAllPapers, getFacets } from '@/lib/papers';
import { getAllOscPapers, getOscFacets, channelLabel, paperExperiments } from '@/lib/oscillation';
import { stripTex, texToHtml } from '@/lib/tex';

export const metadata: Metadata = {
  title: 'Table builder',
  description:
    'Assemble a custom table of neutrino interaction or oscillation papers — pick columns and filters, preview it, and export a ready-to-paste LaTeX (booktabs) table.',
};

export default function TablePage() {
  const papers = getAllPapers();
  const intFacets = getFacets(papers) as RowFacet[];
  const intData: TBPaper[] = papers.map((p) => ({
    citekey: p.bibtag,
    title: stripTex(p.title),
    titleHtml: texToHtml(p.title),
    experiment: p.collaboration,
    experiments: [p.collaboration],
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

  const oscPapers = getAllOscPapers();
  const oscFacets = getOscFacets(oscPapers) as RowFacet[];
  const oscData: TBPaper[] = oscPapers.map((p) => {
    const exps = paperExperiments(p);
    return {
      citekey: p.bibtag,
      title: stripTex(p.title),
      titleHtml: texToHtml(p.title),
      experiment: exps.join(' + '),
      experiments: exps,
      year: p.year,
      journal: p.journal ?? null,
      arxiv: p.arxiv ?? null,
      doi: p.doi ?? null,
      citations: p.citation_count ?? null,
      measurements: p.measurements.map((m) => ({
        source: m.source,
        framework: m.framework,
        bsm_type: m.bsm_type ?? null,
        channel: (m.channels ?? []).map(channelLabel),
        mode: m.mode ?? [],
        parameters: m.parameters ?? [],
      })),
    };
  });

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
          <ClusteredTable
            interactions={{ data: intData, facets: intFacets, count: intData.length }}
            oscillations={{ data: oscData, facets: oscFacets, count: oscData.length }}
          />
        </div>
      </section>
    </>
  );
}
