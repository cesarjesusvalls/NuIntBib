'use client';

import { useEffect, useState, type ReactNode } from 'react';
import { PapersTable, type PaperRow, type RowFacet } from '@/components/PapersTable';

type Cluster = 'interactions' | 'oscillations';
type ClusterData = { rows: PaperRow[]; facets: RowFacet[]; count: number };

function oscTags(r: PaperRow): ReactNode {
  const arr = (k: string) => (r[k] as string[] | undefined) ?? [];
  const channel = arr('channel');
  const channelHtml = arr('channelHtml');
  const parameter = arr('parameter');
  const parameterHtml = arr('parameterHtml');
  return (
    <>
      {arr('source').map((s) => (
        <span className="tag tag-source" key={s}>
          {s}
        </span>
      ))}
      {arr('framework').map((f) => (
        <span className={`tag tag-framework${f === 'Exotic' ? ' tag-exotic' : ''}`} key={f}>
          {f}
        </span>
      ))}
      {arr('bsm').map((b) => (
        <span className="tag tag-bsm" key={b}>
          {b}
        </span>
      ))}
      {channel.map((c, i) => (
        <span
          className="tag tag-channel"
          key={c}
          dangerouslySetInnerHTML={{ __html: channelHtml[i] ?? c }}
        />
      ))}
      {parameter.map((p, i) => (
        <span
          className="tag tag-param"
          key={p}
          dangerouslySetInnerHTML={{ __html: parameterHtml[i] ?? p }}
        />
      ))}
    </>
  );
}

export function ClusteredPapers({
  interactions,
  oscillations,
}: {
  interactions: ClusterData;
  oscillations: ClusterData;
}) {
  const [cluster, setCluster] = useState<Cluster>('interactions');

  // Honor a ?cluster=oscillations URL param on first mount (home-page deep links).
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('cluster') === 'oscillations') setCluster('oscillations');
  }, []);

  return (
    <>
      <div className="cluster-toggle" role="group" aria-label="Topic cluster">
        <button
          aria-pressed={cluster === 'interactions'}
          className={cluster === 'interactions' ? 'is-on' : ''}
          onClick={() => setCluster('interactions')}
          type="button"
        >
          Interactions <small>{interactions.count}</small>
        </button>
        <button
          aria-pressed={cluster === 'oscillations'}
          className={cluster === 'oscillations' ? 'is-on' : ''}
          onClick={() => setCluster('oscillations')}
          type="button"
        >
          Oscillations <small>{oscillations.count}</small>
        </button>
      </div>

      {cluster === 'interactions' ? (
        <PapersTable key="interactions" rows={interactions.rows} facets={interactions.facets} />
      ) : (
        <PapersTable
          key="oscillations"
          rows={oscillations.rows}
          facets={oscillations.facets}
          renderTags={oscTags}
          searchPlaceholder="Search title, experiment, channel, parameter, bibtag…"
        />
      )}
    </>
  );
}
