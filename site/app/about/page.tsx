import type { Metadata } from 'next';
import { Container, PageHero } from '@/components/UI';
import { site } from '@/lib/site-data';

export const metadata: Metadata = {
  title: 'About',
  description: 'What NuIntBib keeps track of, and how to contribute.',
};

export default function AboutPage() {
  return (
    <>
      <PageHero
        eyebrow="About"
        title="A living index of neutrino interaction measurements"
        body="A structured, validated database that anyone can browse, cite, and help grow."
        className="page-hero-flush"
      />
      <section className="section section-about">
        <Container className="prose">
          <h2 className="type-h3">What we keep track of</h2>
          <p>
            NuIntBib indexes published, peer-reviewed measurements of neutrino interactions.
            Qualifying measurements include both cross section results (inclusive or exclusive) and
            related interaction observables (e.g. production yields).
          </p>
          <p>
            Not included: theory/generator papers, pure flux measurements, detector- or method-only
            papers, and conference proceedings whose result also appears as a journal article.
          </p>

          <h2 className="type-h3" id="contribute">
            How to contribute
          </h2>
          <p>
            NuIntBib is developed and managed by {site.maintainer} ({site.maintainerAffiliation}).
            Corrections, additions, and suggestions are welcome by email (
            <a href={`mailto:${site.contactEmail}`}>{site.contactEmail}</a>) or on{' '}
            <a href={site.githubUrl} target="_blank" rel="noreferrer">
              GitHub
            </a>
            , where you can{' '}
            <a href={`${site.githubUrl}/issues`} target="_blank" rel="noreferrer">
              open an issue
            </a>
            .
          </p>
        </Container>
      </section>
    </>
  );
}
