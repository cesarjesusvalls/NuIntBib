import Link from 'next/link';
import { Container, ButtonLink, SectionHeader } from '@/components/UI';
import { Icon } from '@/components/Icon';
import { Tex } from '@/components/Tex';
import { getAllPapers, getStats } from '@/lib/papers';
import { getAllOscPapers, paperExperiments } from '@/lib/oscillation';

export default function HomePage() {
  const intPapers = getAllPapers();
  const oscPapers = getAllOscPapers();
  const intStats = getStats(intPapers);

  // combined, two-cluster headline numbers
  const totalPapers = intPapers.length + oscPapers.length;
  const oscCitations = oscPapers.reduce((n, p) => n + (p.citation_count ?? 0), 0);
  const totalCitations = intStats.totalCitations + oscCitations;
  const years = [...intPapers, ...oscPapers]
    .map((p) => p.year)
    .filter((y): y is number => Boolean(y));
  const yearRange: [number, number] = [Math.min(...years), Math.max(...years)];

  // experiment coverage across both clusters
  const expCount = new Map<string, { int: number; osc: number }>();
  for (const [e, n] of intStats.experiments) expCount.set(e, { int: n, osc: 0 });
  for (const p of oscPapers) {
    for (const e of paperExperiments(p)) {
      const c = expCount.get(e) ?? { int: 0, osc: 0 };
      c.osc += 1;
      expCount.set(e, c);
    }
  }
  const experiments = [...expCount.entries()]
    .map(([exp, c]) => ({
      exp,
      total: c.int + c.osc,
      cluster: c.int >= c.osc ? 'interactions' : 'oscillations',
    }))
    .sort((a, b) => b.total - a.total);

  // Coverage summary folded into the "by experiment" section intro.
  const coverageBody =
    `Spanning ${yearRange[0]} to ${yearRange[1]}, the database tracks ${totalPapers} interaction ` +
    `and oscillation papers across ${expCount.size} experiments, with ` +
    `${totalCitations.toLocaleString()} INSPIRE citations in total.`;

  // latest additions across both clusters, newest first
  const dateOf = (d: string | null | undefined, y: number | null) =>
    d ?? (y != null ? `${y}-00` : '0000');
  const latest = [
    ...intPapers.map((p) => ({
      slug: p.slug,
      title: p.title,
      exp: p.collaboration,
      year: p.year,
      date: dateOf(p.published_date, p.year),
      cluster: 'Interaction',
    })),
    ...oscPapers.map((p) => ({
      slug: p.slug,
      title: p.title,
      exp: paperExperiments(p).join(' + '),
      year: p.year,
      date: dateOf(p.published_date, p.year),
      cluster: 'Oscillation',
    })),
  ]
    .sort((a, b) => b.date.localeCompare(a.date))
    .slice(0, 6);

  return (
    <>
      <section className="page-hero">
        <Container className="page-hero-inner">
          <div className="page-hero-copy">
            <p className="eyebrow">Neutrino measurements literature resource</p>
            <h1 className="type-h1">Neutrino measurements, in one place.</h1>
            <p>
              NuBib is a continuously updated index of published neutrino measurements, covering
              both interaction and oscillation results. Search and filter by experiment, channel,
              and more, with one-click links to arXiv, the journal, INSPIRE, and BibTeX.
            </p>
            <div className="hero-actions">
              <ButtonLink href="/papers">
                <span className="hero-cta">
                  <strong>Browse interaction papers</strong>
                  <small>{intPapers.length} tracked</small>
                </span>
                <Icon name="arrow" size={14} />
              </ButtonLink>
              <ButtonLink href="/papers?cluster=oscillations" variant="secondary">
                <span className="hero-cta">
                  <strong>Browse oscillation measurements</strong>
                  <small>{oscPapers.length} tracked</small>
                </span>
                <Icon name="arrow" size={14} />
              </ButtonLink>
            </div>
          </div>
        </Container>
      </section>

      <section className="section">
        <Container>
          <SectionHeader
            eyebrow="By experiment"
            title="Coverage across the field"
            body={coverageBody}
          />
          <div className="exp-grid">
            {experiments.map(({ exp, total, cluster }) => (
              <Link
                className="panel exp-card"
                href={`/papers?experiment=${encodeURIComponent(exp)}${cluster === 'oscillations' ? '&cluster=oscillations' : ''}`}
                key={exp}
              >
                <strong>{total}</strong>
                <span>{exp}</span>
              </Link>
            ))}
          </div>
        </Container>
      </section>

      <section className="section">
        <Container>
          <SectionHeader eyebrow="Recently published" title="Latest additions" />
          <ul className="latest-list">
            {latest.map((p) => (
              <li className="panel latest-row" key={p.slug}>
                <Link href={`/papers/${p.slug}/`}>
                  <span className="latest-meta">
                    <span className={`latest-cluster cluster-${p.cluster.toLowerCase()}`}>
                      {p.cluster}
                    </span>
                    {p.exp} · {p.year}
                  </span>
                  <span className="latest-title">
                    <Tex text={p.title} />
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </Container>
      </section>
    </>
  );
}
