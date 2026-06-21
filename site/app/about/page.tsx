import type { Metadata } from 'next';
import { Container, PageHero } from '@/components/UI';
import { site } from '@/lib/site-data';

export const metadata: Metadata = {
  title: 'About',
  description: 'What NuBib keeps track of, and how to contribute.',
};

export default function AboutPage() {
  return (
    <>
      <PageHero
        eyebrow="About"
        title="A living index of neutrino measurements"
        body="A structured, validated database that anyone can browse, cite, and help grow."
        className="page-hero-flush"
      />
      <section className="section section-about">
        <Container className="prose">
          <h2 className="type-h3">What we keep track of</h2>
          <p>
            NuBib indexes published, peer-reviewed neutrino measurements from experiments, organized
            into topical clusters.
          </p>
          <p>
            Interactions: cross section results (inclusive or exclusive) and related interaction
            observables such as production yields.
          </p>
          <p>
            Oscillations: measurements of oscillation parameters and flavor transitions, such as
            mixing angles, mass splittings, δCP, and appearance or disappearance results.
          </p>
          <p>
            Not included: theory, generator, and phenomenology papers, global fits, sensitivity or
            projection studies, pure flux measurements, detector or method-only papers, and
            conference proceedings whose result also appears as a journal article.
          </p>

          <h2 className="type-h3" id="contribute">
            How to contribute
          </h2>
          <p>
            NuBib is developed and managed by {site.maintainer} ({site.maintainerAffiliation}).
            Corrections, additions, and suggestions are welcome by email (
            <a href={`mailto:${site.contactEmail}`}>{site.contactEmail}</a>) or on{' '}
            <a href={`${site.githubUrl}/issues`} target="_blank" rel="noreferrer">
              GitHub
            </a>
            .
          </p>
        </Container>
      </section>
    </>
  );
}
