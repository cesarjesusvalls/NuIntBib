'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { Icon } from '@/components/Icon';

export type PaperRow = {
  slug: string;
  bibtag: string;
  title: string;
  titleHtml: string;
  collaboration: string;
  year: number | null;
  citation_count: number | null;
  arxiv: string | null;
  doi: string | null;
  inspire: string | null;
  bibtex: string;
  experiment: string[];
  current: string[];
  flavor: string[];
  target: string[];
  topology: string[];
  measurement_type: string[];
  searchText: string;
};

export type RowFacet = { key: string; label: string; allLabel: string; values: string[] };

const ALL = 'All';
type SortKey = 'year-desc' | 'year-asc' | 'cites-desc' | 'title-asc';

const FLAVOR_LABEL: Record<string, string> = {
  numu: 'νμ',
  numubar: 'ν̄μ',
  nue: 'νe',
  nuebar: 'ν̄e',
};

function flavorLabel(f: string) {
  return FLAVOR_LABEL[f] ?? f;
}

function CopyCite({ bibtex, bibtag }: { bibtex: string; bibtag: string }) {
  const [copied, setCopied] = useState(false);
  async function copy() {
    try {
      await navigator.clipboard.writeText(bibtex);
    } catch {
      const ta = document.createElement('textarea');
      ta.value = bibtex;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      ta.remove();
    }
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  }
  return (
    <button
      className={`src-badge src-cite${copied ? ' is-copied' : ''}`}
      onClick={copy}
      type="button"
      title={`Copy BibTeX for ${bibtag}`}
      aria-label={`Copy BibTeX citation for ${bibtag}`}
    >
      <Icon name={copied ? 'check' : 'quote'} size={13} />
      <span>{copied ? 'Copied' : 'Cite'}</span>
    </button>
  );
}

function LinkCluster({ row }: { row: PaperRow }) {
  return (
    <div className="src-cluster">
      {row.arxiv ? (
        <a
          className="src-badge src-arxiv"
          href={`https://arxiv.org/abs/${row.arxiv}`}
          target="_blank"
          rel="noreferrer"
          title={`arXiv:${row.arxiv}`}
        >
          <span>arXiv</span>
          <Icon name="external" size={11} />
        </a>
      ) : null}
      {row.doi ? (
        <a
          className="src-badge src-doi"
          href={`https://doi.org/${row.doi}`}
          target="_blank"
          rel="noreferrer"
          title="Journal article (DOI)"
        >
          <span>DOI</span>
          <Icon name="external" size={11} />
        </a>
      ) : null}
      {row.inspire ? (
        <a
          className="src-badge src-inspire"
          href={row.inspire}
          target="_blank"
          rel="noreferrer"
          title="INSPIRE-HEP record"
        >
          <span>INSPIRE</span>
          <Icon name="external" size={11} />
        </a>
      ) : null}
      <CopyCite bibtex={row.bibtex} bibtag={row.bibtag} />
      {typeof row.citation_count === 'number' ? (
        <span className="src-cites" title={`${row.citation_count} citations (INSPIRE)`}>
          <Icon name="quote" size={11} />
          {row.citation_count}
        </span>
      ) : null}
    </div>
  );
}

export function PapersTable({ rows, facets }: { rows: PaperRow[]; facets: RowFacet[] }) {
  const [active, setActive] = useState<Record<string, string>>({});
  const [query, setQuery] = useState('');
  const [sort, setSort] = useState<SortKey>('year-desc');

  // Pre-select filters from the URL query string (e.g. /papers?experiment=MINERvA),
  // so deep links from the home page land on the right subset.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const next: Record<string, string> = {};
    for (const f of facets) {
      const v = params.get(f.key);
      if (v && (v === ALL || f.values.includes(v))) next[f.key] = v;
    }
    if (Object.keys(next).length) setActive((c) => ({ ...c, ...next }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const topFacet = facets.find((f) => f.key === 'experiment')!;
  const sidebarFacets = facets.filter((f) => f.key !== 'experiment');
  const q = query.trim().toLowerCase();

  function matchesQuery(r: PaperRow) {
    return !q || r.searchText.includes(q);
  }
  function matchesFacet(r: PaperRow, key: string, value: string) {
    return value === ALL || (r[key as keyof PaperRow] as string[]).includes(value);
  }

  const visible = useMemo(() => {
    const list = rows.filter(
      (r) =>
        matchesQuery(r) && facets.every((f) => matchesFacet(r, f.key, active[f.key] ?? ALL)),
    );
    const sorted = [...list];
    sorted.sort((a, b) => {
      switch (sort) {
        case 'year-asc':
          return (a.year ?? 0) - (b.year ?? 0) || a.bibtag.localeCompare(b.bibtag);
        case 'cites-desc':
          return (b.citation_count ?? 0) - (a.citation_count ?? 0);
        case 'title-asc':
          return a.title.localeCompare(b.title);
        default:
          return (b.year ?? 0) - (a.year ?? 0) || a.bibtag.localeCompare(b.bibtag);
      }
    });
    return sorted;
  }, [rows, facets, active, q, sort]);

  function count(facet: RowFacet, value: string) {
    return rows.filter(
      (r) =>
        matchesQuery(r) &&
        facets.every((f) => {
          const v = f.key === facet.key ? value : active[f.key] ?? ALL;
          return matchesFacet(r, f.key, v);
        }),
    ).length;
  }

  function clearAll() {
    setActive({});
    setQuery('');
  }

  const activeChips = facets
    .map((f) => ({ f, value: active[f.key] ?? ALL }))
    .filter((c) => c.value !== ALL);

  return (
    <div className="challenge-browser">
      <nav className="challenge-detector-strip" aria-label="Filter by experiment">
        <span>Experiment</span>
        <div className="challenge-detector-tabs">
          {[ALL, ...topFacet.values].map((value) => {
            const label = value === ALL ? topFacet.allLabel : value;
            const isActive = (active.experiment ?? ALL) === value;
            return (
              <button
                key={value}
                aria-pressed={isActive}
                className="challenge-detector-tab"
                onClick={() => setActive((c) => ({ ...c, experiment: value }))}
                type="button"
              >
                <span>{label}</span>
                <small>{count(topFacet, value)}</small>
              </button>
            );
          })}
        </div>
      </nav>

      <div className="challenge-browser-body">
        <aside className="challenge-filter-rail">
          <div className="challenge-filter-rail-heading">
            <strong>Filter by</strong>
            <button onClick={clearAll} type="button">
              Clear all
            </button>
          </div>
          {sidebarFacets.map((facet) => (
            <fieldset className="challenge-filter-group" key={facet.key}>
              <legend>{facet.label}</legend>
              <div className="challenge-filter-chips">
                {[ALL, ...facet.values].map((value) => {
                  const label =
                    value === ALL
                      ? facet.allLabel
                      : facet.key === 'flavor'
                        ? flavorLabel(value)
                        : value;
                  const isActive = (active[facet.key] ?? ALL) === value;
                  const n = count(facet, value);
                  const disabled = value !== ALL && n === 0 && !isActive;
                  return (
                    <button
                      key={value}
                      aria-pressed={isActive}
                      className="challenge-chip"
                      disabled={disabled}
                      onClick={() => setActive((c) => ({ ...c, [facet.key]: value }))}
                      type="button"
                    >
                      <span>{label}</span>
                      <small>{n}</small>
                    </button>
                  );
                })}
              </div>
            </fieldset>
          ))}
        </aside>

        <div className="challenge-results">
          <div className="challenge-search-row">
            <div className="challenge-search-field">
              <input
                aria-label="Search papers"
                autoComplete="off"
                onChange={(e) => setQuery(e.currentTarget.value)}
                placeholder="Search title, experiment, topology, bibtag…"
                type="search"
                value={query}
              />
              {query ? (
                <button aria-label="Clear search" onClick={() => setQuery('')} type="button">
                  x
                </button>
              ) : null}
            </div>
            <label className="papers-sort">
              Sort
              <select value={sort} onChange={(e) => setSort(e.currentTarget.value as SortKey)}>
                <option value="year-desc">Newest first</option>
                <option value="year-asc">Oldest first</option>
                <option value="cites-desc">Most cited</option>
                <option value="title-asc">Title A–Z</option>
              </select>
            </label>
          </div>

          <div className="challenge-results-header">
            <p>
              {visible.length} {visible.length === 1 ? 'paper' : 'papers'}
            </p>
            {activeChips.length ? (
              <div className="challenge-active-filters" aria-label="Active filters">
                {activeChips.map(({ f, value }) => (
                  <button
                    key={f.key}
                    onClick={() => setActive((c) => ({ ...c, [f.key]: ALL }))}
                    type="button"
                  >
                    {f.key === 'flavor' ? flavorLabel(value) : value}
                    <span aria-hidden="true">x</span>
                  </button>
                ))}
              </div>
            ) : null}
          </div>

          <ul className="papers-list">
            {visible.map((r) => (
              <li className="panel paper-row" key={r.slug}>
                <div className="paper-row-main">
                  <Link className="paper-title" href={`/papers/${r.slug}/`}>
                    <span dangerouslySetInnerHTML={{ __html: r.titleHtml }} />
                  </Link>
                  <div className="paper-meta">
                    <span className="tag tag-exp">{r.collaboration}</span>
                    <span className="tag">{r.year ?? '—'}</span>
                    {r.current.map((c) => (
                      <span className={`tag tag-${c.toLowerCase()}`} key={c}>
                        {c}
                      </span>
                    ))}
                    {r.flavor.map((f) => (
                      <span className="tag tag-flavor" key={f}>
                        {flavorLabel(f)}
                      </span>
                    ))}
                    {r.target.map((t) => (
                      <span className="tag tag-target" key={t}>
                        {t}
                      </span>
                    ))}
                    {r.topology.map((t) => (
                      <span className="tag tag-topo" key={t}>
                        {t}
                      </span>
                    ))}
                    {r.measurement_type.map((t) => (
                      <span className="tag tag-type" key={t}>
                        {t}
                      </span>
                    ))}
                  </div>
                </div>
                <LinkCluster row={r} />
              </li>
            ))}
          </ul>
          {visible.length === 0 ? (
            <p className="papers-empty">No papers match these filters. Try clearing some.</p>
          ) : null}
        </div>
      </div>
    </div>
  );
}
