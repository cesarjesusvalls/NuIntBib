import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { ButtonLink, Container } from '@/components/UI';
import { Icon } from '@/components/Icon';
import { CiteBlock } from '@/components/CiteBlock';
import { Tex } from '@/components/Tex';
import { stripTex } from '@/lib/tex';
import { getAllPapers, getPaperBySlug } from '@/lib/papers';
import {
  getAllOscPapers,
  getOscPaperBySlug,
  channelLabel,
  paperExperiments,
} from '@/lib/oscillation';

type PageProps = { params: Promise<{ slug: string }> };

const FLAVOR_LABEL: Record<string, string> = {
  numu: 'νμ',
  numubar: 'ν̄μ',
  nue: 'νe',
  nuebar: 'ν̄e',
};

export function generateStaticParams() {
  return [
    ...getAllPapers().map((p) => ({ slug: p.slug })),
    ...getAllOscPapers().map((p) => ({ slug: p.slug })),
  ];
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const paper = getPaperBySlug(slug) ?? getOscPaperBySlug(slug);
  return {
    title: paper ? stripTex(paper.title) : 'Paper',
    description: paper?.abstract ? stripTex(paper.abstract).slice(0, 200) : undefined,
  };
}

export default async function PaperDetailPage({ params }: PageProps) {
  const { slug } = await params;
  const intPaper = getPaperBySlug(slug);
  const oscPaper = intPaper ? undefined : getOscPaperBySlug(slug);
  if (!intPaper && !oscPaper) notFound();
  const paper = (intPaper ?? oscPaper)!;
  const expLabel = oscPaper ? paperExperiments(oscPaper).join(' + ') : intPaper!.collaboration;

  const citation = [paper.journal, paper.volume, paper.pages].filter(Boolean).join(' ');

  return (
    <>
      <section className="page-hero detail-hero">
        <Container className="page-hero-inner">
          <div className="page-hero-copy">
            <p className="eyebrow">
              {expLabel} · {paper.year ?? '–'}
            </p>
            <h1 className="type-h1">
              <Tex text={paper.title} />
            </h1>
            {citation ? (
              <p>
                {citation}
                {paper.doi ? ` · ${paper.doi}` : ''}
              </p>
            ) : null}
            <div className="hero-actions paper-detail-actions">
              {paper.arxiv ? (
                <ButtonLink href={`https://arxiv.org/abs/${paper.arxiv}`}>
                  arXiv:{paper.arxiv}
                  <Icon name="external" size={14} />
                </ButtonLink>
              ) : null}
              {paper.doi ? (
                <ButtonLink href={`https://doi.org/${paper.doi}`} variant="secondary">
                  Journal
                  <Icon name="external" size={14} />
                </ButtonLink>
              ) : null}
              {paper.links?.inspire ? (
                <ButtonLink href={paper.links.inspire} variant="secondary">
                  INSPIRE
                  <Icon name="external" size={14} />
                </ButtonLink>
              ) : null}
              <ButtonLink href="/papers" variant="ghost">
                All papers
              </ButtonLink>
            </div>
          </div>
        </Container>
      </section>

      <section className="section">
        <Container className="detail-layout">
          <aside className="detail-sidebar">
            <div className="panel detail-summary">
              <span className="status-pill">{expLabel}</span>
              <dl>
                <div>
                  <dt>Year</dt>
                  <dd>{paper.year ?? '–'}</dd>
                </div>
                <div>
                  <dt>Published</dt>
                  <dd>{paper.published_date ?? '–'}</dd>
                </div>
                <div>
                  <dt>Citations</dt>
                  <dd>{paper.citation_count ?? '–'}</dd>
                </div>
                <div>
                  <dt>BibTeX key</dt>
                  <dd>
                    <code>{paper.bibtag}</code>
                  </dd>
                </div>
                {paper.inspire_recid ? (
                  <div>
                    <dt>INSPIRE recid</dt>
                    <dd>{paper.inspire_recid}</dd>
                  </div>
                ) : null}
              </dl>
            </div>
          </aside>

          <div className="detail-main section-stack">
            <div>
              <h2 className="type-h3">Results</h2>
              <div className="data-table-wrap">
                {oscPaper ? (
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Source</th>
                        <th>Framework</th>
                        <th>Channel</th>
                        <th>Mode</th>
                        <th>Parameters</th>
                        <th>Observables</th>
                      </tr>
                    </thead>
                    <tbody>
                      {oscPaper.measurements.map((m, i) => (
                        <tr key={i}>
                          <td>{m.source}</td>
                          <td>{m.framework + (m.bsm_type ? ` (${m.bsm_type})` : '')}</td>
                          <td>{(m.channels ?? []).map(channelLabel).join(', ') || '–'}</td>
                          <td>{(m.mode ?? []).join(', ') || '–'}</td>
                          <td>{(m.parameters ?? []).join(', ') || '–'}</td>
                          <td>{m.observables ?? '–'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Current</th>
                        <th>Flavor</th>
                        <th>Target</th>
                        <th>Topology</th>
                        <th>Type</th>
                        <th>Observables</th>
                        <th>Energy</th>
                      </tr>
                    </thead>
                    <tbody>
                      {intPaper!.measurements.map((m, i) => (
                        <tr key={i}>
                          <td>{m.current}</td>
                          <td>
                            {m.flavor.map((f) => FLAVOR_LABEL[f] ?? f).join(', ') ||
                              m.flavor_note ||
                              '–'}
                          </td>
                          <td>{m.target.join(', ') || '–'}</td>
                          <td>{m.topology}</td>
                          <td>{m.measurement_type ?? '–'}</td>
                          <td>{m.observables ?? '–'}</td>
                          <td>{m.energy_notes ?? '–'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>

            {paper.abstract ? (
              <div className="text-panel">
                <h2 className="type-h3">Abstract</h2>
                <p>
                  <Tex text={paper.abstract} />
                </p>
              </div>
            ) : null}

            <div>
              <h2 className="type-h3">Citation</h2>
              <CiteBlock bibtex={paper.bibtex} />
            </div>
          </div>
        </Container>
      </section>
    </>
  );
}
