import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { ButtonLink, Container } from '@/components/UI';
import { Icon } from '@/components/Icon';
import { CiteBlock } from '@/components/CiteBlock';
import { Tex } from '@/components/Tex';
import { stripTex } from '@/lib/tex';
import { getAllPapers, getPaperBySlug, flavorTexSegment } from '@/lib/papers';
import { getDataRelease } from '@/lib/datasets';
import { DataRelease } from '@/components/DataRelease';
import {
  getAllOscPapers,
  getOscPaperBySlug,
  channelTexSegment,
  paramTexSegment,
  paperExperiments,
} from '@/lib/oscillation';

type PageProps = { params: Promise<{ slug: string }> };

// canonical "why there's no data release" sentences, keyed by a paper's release_status.
// Papers in the same category read identically; reword here once to change them all.
const RELEASE_STATUS_NOTE: Record<string, string> = {
  abstract:
    'The result is reported directly in the paper abstract and there is no cross-section measurement to release as data.',
  not_xsec:
    'This paper measures final-state observables rather than a neutrino cross section, so there is no cross-section measurement to release as data.',
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
  const dataRelease = intPaper ? getDataRelease(slug) : null;
  // when a paper has no data release, explain why: an explicit release_note wins,
  // else a canonical sentence keyed by release_status (e.g. every search reads the same)
  const noReleaseNote =
    intPaper && !dataRelease
      ? intPaper.release_note ?? RELEASE_STATUS_NOTE[intPaper.release_status ?? ''] ?? null
      : null;
  const seeAlso =
    noReleaseNote && intPaper?.release_see_also ? getPaperBySlug(intPaper.release_see_also) : null;

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
            {paper.abstract ? (
              <div className="text-panel">
                <h2 className="type-h3">Abstract</h2>
                <p>
                  <Tex text={paper.abstract} />
                </p>
              </div>
            ) : null}

            <div>
              <h2 className="type-h3">Labels</h2>
              <div className="labels-list">
                {oscPaper
                  ? oscPaper.measurements.map((m, i) => (
                      <div className="paper-meta" key={i}>
                        {m.source ? <span className="tag tag-source">{m.source}</span> : null}
                        {m.framework ? (
                          <span
                            className={`tag tag-framework${m.framework === 'Exotic' ? ' tag-exotic' : ''}`}
                          >
                            {m.framework}
                          </span>
                        ) : null}
                        {m.bsm_type ? <span className="tag tag-bsm">{m.bsm_type}</span> : null}
                        {m.channels?.map((c, ci) => (
                          <span className="tag tag-channel" key={ci}>
                            <Tex text={channelTexSegment(c)} />
                          </span>
                        ))}
                        {(m.mode ?? []).map((md) => (
                          <span className="tag" key={md}>
                            {md}
                          </span>
                        ))}
                        {m.parameters?.map((p) => (
                          <span className="tag tag-param" key={p}>
                            <Tex text={paramTexSegment(p)} />
                          </span>
                        ))}
                        {m.observables ? (
                          <span className="tag tag-obs">{m.observables}</span>
                        ) : null}
                      </div>
                    ))
                  : intPaper!.measurements.map((m, i) => (
                      <div className="paper-meta" key={i}>
                        <span className={`tag tag-${m.current.toLowerCase()}`}>{m.current}</span>
                        {m.flavor.length ? (
                          m.flavor.map((f) => (
                            <span className="tag tag-flavor" key={f}>
                              <Tex text={flavorTexSegment(f)} />
                            </span>
                          ))
                        ) : m.flavor_note ? (
                          <span className="tag tag-flavor">{m.flavor_note}</span>
                        ) : null}
                        {m.target.map((t) => (
                          <span className="tag tag-target" key={t}>
                            {t}
                          </span>
                        ))}
                        {m.topology ? <span className="tag tag-topo">{m.topology}</span> : null}
                        {m.measurement_type ? (
                          <span className="tag tag-type">{m.measurement_type}</span>
                        ) : null}
                        {/* observables descriptor intentionally not shown: it restates the
                            chips above and the data-release axes below */}
                      </div>
                    ))}
              </div>
            </div>

            {dataRelease ? (
              <DataRelease release={dataRelease} />
            ) : noReleaseNote ? (
              <div>
                <h2 className="type-h3">Data release</h2>
                <p className="no-release-note">{noReleaseNote}</p>
                {seeAlso ? (
                  <p className="no-release-note">
                    The same experiment later released a cross-section measurement:{' '}
                    <a className="dr-src-link" href={`/papers/${seeAlso.slug}/`}>
                      {seeAlso.bibtag}
                    </a>
                    .
                  </p>
                ) : null}
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
