import type { Metadata } from 'next';
import { Container, PageHero, SectionHeader } from '@/components/UI';
import { ClusteredTimeline } from '@/components/ClusteredTimeline';
import { getAllPapers, getStats, getTimeline } from '@/lib/papers';
import { getAllOscPapers, getOscTimeline, paperExperiments } from '@/lib/oscillation';

export const metadata: Metadata = {
  title: 'Statistics',
  description:
    'How the tracked neutrino interaction and oscillation measurements are distributed across experiments and over time.',
};

export default function StatsPage() {
  const papers = getAllPapers();
  const oscPapers = getAllOscPapers();
  const stats = getStats(papers);
  const timeline = getTimeline(papers);
  const oscTimeline = getOscTimeline(oscPapers);

  // Combined coverage across both clusters for the hero line.
  const totalPapers = papers.length + oscPapers.length;
  const allExperiments = new Set<string>([
    ...stats.experiments.map(([e]) => e),
    ...oscPapers.flatMap(paperExperiments),
  ]);
  const allYears = [...papers, ...oscPapers]
    .map((p) => p.year)
    .filter((y): y is number => Boolean(y));
  const yearRange: [number, number] = [Math.min(...allYears), Math.max(...allYears)];

  return (
    <>
      <PageHero
        eyebrow="Database statistics"
        title="What the collection covers"
        body={`${totalPapers} interaction and oscillation papers across ${allExperiments.size} experiments, from ${yearRange[0]} to ${yearRange[1]}.`}
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
