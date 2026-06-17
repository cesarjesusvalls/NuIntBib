import type { Metadata } from 'next';
import { Container, PageHero, SectionHeader } from '@/components/UI';
import { PapersOverTime } from '@/components/PapersOverTime';
import { getAllPapers, getStats, getTimeline } from '@/lib/papers';

export const metadata: Metadata = {
  title: 'Statistics',
  description: 'Distribution of tracked neutrino interaction measurements by experiment, channel, target, flavor, and year.',
};

export default function StatsPage() {
  const papers = getAllPapers();
  const stats = getStats(papers);
  const timeline = getTimeline(papers);

  return (
    <>
      <PageHero
        eyebrow="Database statistics"
        title="What the collection covers"
        body={`${stats.papers} papers and ${stats.measurements} measurements across ${stats.experiments.length} experiments, ${stats.yearRange[0]}–${stats.yearRange[1]}.`}
        className="page-hero-flush"
      />
      <section className="section section-timeline">
        <Container>
          <SectionHeader
            eyebrow="Over time"
            title="Evolution of the field"
            body="Papers (or citations) per year, or accumulated. Break the field down by experiment, topology, flavour, current, or target material, then highlight any one to see its share within the whole."
          />
          <PapersOverTime data={timeline} />
        </Container>
      </section>
    </>
  );
}
