import type { Metadata } from 'next';
import { PageHero } from '@/components/UI';
import { ClusteredPapers } from '@/components/ClusteredPapers';
import type { PaperRow, RowFacet } from '@/components/PapersTable';
import { getAllPapers, getFacets, paperFacetValues } from '@/lib/papers';
import { getAllOscPapers, getOscFacets, oscFacetValues, paramSearchAliases } from '@/lib/oscillation';
import { stripTex, texToHtml } from '@/lib/tex';

export const metadata: Metadata = {
  title: 'Papers',
  description:
    'Browse and filter neutrino interaction and oscillation measurements by experiment, channel, and more.',
};

export default function PapersPage() {
  // --- interactions cluster ---
  const papers = getAllPapers();
  const intFacets = getFacets(papers) as RowFacet[];
  const intRows: PaperRow[] = papers.map((p) => {
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

  // --- oscillations cluster ---
  const oscPapers = getAllOscPapers();
  const oscFacets = getOscFacets(oscPapers) as RowFacet[];
  const oscRows: PaperRow[] = oscPapers.map((p) => {
    const fv = oscFacetValues(p);
    const bsm = Array.from(
      new Set(p.measurements.map((m) => m.bsm_type).filter((x): x is string => Boolean(x))),
    );
    return {
      slug: p.slug,
      bibtag: p.bibtag,
      title: stripTex(p.title),
      titleHtml: texToHtml(p.title),
      collaboration: fv.experiment.join(' + '),
      year: p.year,
      citation_count: p.citation_count ?? null,
      arxiv: p.arxiv ?? null,
      doi: p.doi ?? null,
      inspire: p.links?.inspire ?? null,
      bibtex: p.bibtex,
      experiment: fv.experiment,
      source: fv.source,
      framework: fv.framework,
      mode: fv.mode,
      channel: fv.channel,
      parameter: fv.parameter,
      bsm,
      searchText: [
        stripTex(p.title),
        p.bibtag,
        ...fv.experiment,
        p.year,
        ...fv.source,
        ...fv.channel,
        ...fv.parameter,
        ...paramSearchAliases(fv.parameter),
        ...fv.framework,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase(),
    };
  });

  return (
    <>
      <PageHero
        eyebrow={`${intRows.length + oscRows.length} measurements`}
        title="Neutrino measurements"
        body="Up-to-date, labeled neutrino interaction and oscillation measurements."
        className="page-hero-flush"
      />
      <section className="section section-papers">
        <div className="container">
          <ClusteredPapers
            interactions={{ rows: intRows, facets: intFacets, count: intRows.length }}
            oscillations={{ rows: oscRows, facets: oscFacets, count: oscRows.length }}
          />
        </div>
      </section>
    </>
  );
}
