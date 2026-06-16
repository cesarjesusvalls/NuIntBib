import type { Metadata } from 'next';
import { PageHero } from '@/components/UI';
import { PapersTable, type PaperRow, type RowFacet } from '@/components/PapersTable';
import { getAllPapers, getFacets, paperFacetValues } from '@/lib/papers';
import { stripTex, texToHtml } from '@/lib/tex';

export const metadata: Metadata = {
  title: 'Papers',
  description:
    'Browse and filter every tracked neutrino interaction measurement by experiment, current, flavor, target, and interaction topology.',
};

export default function PapersPage() {
  const papers = getAllPapers();
  const facets = getFacets(papers) as RowFacet[];

  const rows: PaperRow[] = papers.map((p) => {
    const fv = paperFacetValues(p);
    return {
      slug: p.slug,
      bibtag: p.bibtag,
      title: stripTex(p.title),
      titleHtml: texToHtml(p.title),
      collaboration: p.collaboration,
      year: p.year,
      citation_count: p.citation_count ?? null,
      arxiv: p.arxiv ?? null,
      doi: p.doi ?? null,
      inspire: p.links?.inspire ?? null,
      bibtex: p.bibtex,
      experiment: fv.experiment,
      current: fv.current,
      flavor: fv.flavor,
      target: fv.target,
      topology: fv.topology,
      measurement_type: fv.measurement_type,
      searchText: [
        stripTex(p.title),
        p.bibtag,
        p.collaboration,
        p.year,
        ...fv.topology,
        ...fv.target,
        ...fv.flavor,
        ...fv.current,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase(),
    };
  });

  return (
    <>
      <PageHero
        eyebrow={`${papers.length} measurements`}
        title="Neutrino interaction measurements"
        body="Every record is enriched from INSPIRE-HEP. Filter by experiment, current, flavor, target, and topology; open arXiv, the journal, or INSPIRE, or copy a BibTeX citation in one click."
      />
      <section className="section">
        <div className="container">
          <PapersTable rows={rows} facets={facets} />
        </div>
      </section>
    </>
  );
}
