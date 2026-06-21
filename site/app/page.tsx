import Link from 'next/link';
import { Container, ButtonLink, SectionHeader } from '@/components/UI';
import { Icon } from '@/components/Icon';
import { Tex } from '@/components/Tex';
import { getAllPapers, getStats } from '@/lib/papers';

export default function HomePage() {
  const papers = getAllPapers();
  const stats = getStats(papers);
  const latest = papers.slice(0, 5);

  const highlights = [
    { value: stats.papers, label: 'Papers tracked' },
    { value: stats.experiments.length, label: 'Experiments' },
    { value: `${stats.yearRange[0]}–${stats.yearRange[1]}`, label: 'Years covered' },
    { value: stats.totalCitations.toLocaleString(), label: 'Citations (INSPIRE)' },
  ];

  return (
    <>
      <section className="page-hero">
        <Container className="page-hero-inner">
          <div className="page-hero-copy">
            <p className="eyebrow">Neutrino measurements literature resource</p>
            <h1 className="type-h1">Neutrino measurements, in one place.</h1>
            <p>
              NuBib is a continuously updated index of published neutrino measurements — interaction
              and oscillation results — searchable and filterable by experiment, channel, and more,
              with one-click links to arXiv, the journal, INSPIRE, and BibTeX.
            </p>
            <div className="hero-actions">
              <ButtonLink href="/papers">
                Browse {stats.papers} papers
                <Icon name="arrow" size={14} />
              </ButtonLink>
              <ButtonLink href="/stats" variant="secondary">
                See statistics
              </ButtonLink>
            </div>
          </div>
        </Container>
      </section>

      <section className="section">
        <Container>
          <div className="stat-strip">
            {highlights.map((h) => (
              <div className="stat-cell" key={h.label}>
                <strong>{h.value}</strong>
                <span>{h.label}</span>
              </div>
            ))}
          </div>
        </Container>
      </section>

      <section className="section">
        <Container>
          <SectionHeader
            eyebrow="By experiment"
            title="Coverage across the field"
            body="Collaborations in the database, ordered by number of tracked papers."
          />
          <div className="exp-grid">
            {stats.experiments.map(([exp, n]) => (
              <Link
                className="panel exp-card"
                href={`/papers?experiment=${encodeURIComponent(exp)}`}
                key={exp}
              >
                <strong>{n}</strong>
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
                    {p.collaboration} · {p.year}
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
