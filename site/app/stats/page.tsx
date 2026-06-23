import type { Metadata } from 'next';
import { Container, PageHero, SectionHeader } from '@/components/UI';
import { ClusteredTimeline } from '@/components/ClusteredTimeline';
import { getAllPapers, getStats, getTimeline } from '@/lib/papers';
import { getAllOscPapers, getOscTimeline } from '@/lib/oscillation';

export const metadata: Metadata = {
  title: 'Statistics',
  description:
    'How the tracked neutrino interaction and oscillation measurements are distributed across experiments and over time.',
};

export default function StatsPage() {
  const papers = getAllPapers();
  const stats = getStats(papers);
  const timeline = getTimeline(papers);
  const oscTimeline = getOscTimeline(getAllOscPapers());

  return (
    <>
      <PageHero
        eyebrow="Database statistics"
        title="What the collection covers"
        body={`${stats.papers} interaction papers across ${stats.experiments.length} experiments, ${stats.yearRange[0]}–${stats.yearRange[1]}, plus a growing oscillation cluster.`}
        className="page-hero-flush"
      />
      <section className="section section-timeline">
        <Container>
          <SectionHeader
            eyebrow="Over time"
            title="Evolution of the field"
            body="Papers (or citations) per year, or accumulated. Pick a cluster, break it down by experiment and other dimensions, then highlight any one to see its share within the whole."
          />
          <ClusteredTimeline interactions={timeline} oscillations={oscTimeline} />
        </Container>
      </section>
    </>
  );
}
