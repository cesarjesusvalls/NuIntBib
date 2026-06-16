import type { Metadata } from 'next';
import { Container, PageHero } from '@/components/UI';
import { site } from '@/lib/site-data';

export const metadata: Metadata = {
  title: 'About',
  description: 'What NuIntBib is, where the data comes from, and how to contribute.',
};

export default function AboutPage() {
  return (
    <>
      <PageHero
        eyebrow="About"
        title="A living index of neutrino cross-section measurements"
        body="NuIntBib started as a hand-curated bibliography and is now a structured, validated database that anyone can browse, cite, and help grow."
      />
      <section className="section">
        <Container className="prose">
          <h2 className="type-h3">What it tracks</h2>
          <p>
            NuIntBib focuses on published <strong>experimental neutrino cross-section
            measurements</strong> — inclusive and exclusive channels (CCQE, CC0π, CC1π, NC1π0,
            coherent production, DIS, strange production, and more) across targets from hydrocarbon
            and carbon to argon, water, and iron. Each paper is classified by current, neutrino
            flavor, target material, interaction topology, and measurement type.
          </p>

          <h2 className="type-h3">Where the data comes from</h2>
          <p>
            Every record is enriched from{' '}
            <a href="https://inspirehep.net" target="_blank" rel="noreferrer">
              INSPIRE-HEP
            </a>{' '}
            — title, authors, journal reference, arXiv identifier, publication date, and live
            citation count. The physics classification is curated by the maintainer. The canonical
            data lives as version-controlled YAML in the{' '}
            <a href={site.githubUrl} target="_blank" rel="noreferrer">
              GitHub repository
            </a>
            , validated against a JSON schema, so the site is always a faithful render of the
            database.
          </p>

          <h2 className="type-h3" id="contribute">
            How to contribute
          </h2>
          <p>
            Spotted a missing paper, or a classification you would refine? Open an issue or a pull
            request against <code>data/papers/*.yml</code>. The maintainer runs a periodic update
            pass that queries INSPIRE-HEP for new neutrino cross-section measurements, classifies
            them, and adds them to the database after review — so the index stays current with the
            field.
          </p>

          <h2 className="type-h3">Citing</h2>
          <p>
            Use the <strong>Cite</strong> button on any row, or the BibTeX block on a paper&apos;s
            page, to copy a ready-to-use entry. Keys follow the INSPIRE texkey convention (e.g.{' '}
            <code>T2K:2013nor</code>).
          </p>

          <h2 className="type-h3">Maintainer</h2>
          <p>
            NuIntBib is developed and managed by{' '}
            <a href={`mailto:${site.contactEmail}`}>{site.maintainer}</a> ({site.maintainerAffiliation}).
            Corrections, additions, and suggestions are welcome by email or on{' '}
            <a href={site.githubUrl} target="_blank" rel="noreferrer">
              GitHub
            </a>
            .
          </p>
        </Container>
      </section>
    </>
  );
}
