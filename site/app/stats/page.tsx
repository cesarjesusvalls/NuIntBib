import type { Metadata } from 'next';
import { Container, PageHero, SectionHeader } from '@/components/UI';
import { PapersOverTime } from '@/components/PapersOverTime';
import { getAllPapers, getStats, getTimeline } from '@/lib/papers';

export const metadata: Metadata = {
  title: 'Statistics',
  description: 'Distribution of tracked neutrino interaction measurements by experiment, channel, target, flavor, and year.',
};

const FLAVOR_LABEL: Record<string, string> = {
  numu: 'νμ',
  numubar: 'ν̄μ',
  nue: 'νe',
  nuebar: 'ν̄e',
};

function BarList({
  title,
  data,
  labelMap,
}: {
  title: string;
  data: [string, number][];
  labelMap?: Record<string, string>;
}) {
  const max = Math.max(...data.map(([, n]) => n), 1);
  return (
    <div className="panel stat-panel">
      <h3 className="type-h3">{title}</h3>
      <ul className="bar-list">
        {data.map(([key, n]) => (
          <li key={key}>
            <span className="bar-label">{labelMap?.[key] ?? key}</span>
            <span className="bar-track">
              <span className="bar-fill" style={{ width: `${(n / max) * 100}%` }} />
            </span>
            <span className="bar-value">{n}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

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
            body="Papers (or citations) published per year, or accumulated. Highlight any experiment to see its contribution within the whole."
          />
          <PapersOverTime data={timeline} />
        </Container>
      </section>
      <section className="section section-after-timeline">
        <Container>
          <SectionHeader eyebrow="Distributions" title="By category" />
          <div className="stat-grid">
            <BarList title="Experiment" data={stats.experiments} />
            <BarList title="Interaction topology" data={stats.byTopology.slice(0, 14)} />
            <BarList title="Target material" data={stats.byTarget} />
            <BarList title="Neutrino flavor" data={stats.byFlavor} labelMap={FLAVOR_LABEL} />
            <BarList title="Current" data={stats.byCurrent} />
            <BarList title="Publication year" data={stats.byYear} />
          </div>
        </Container>
      </section>
    </>
  );
}
