'use client';

import { useState, type ReactNode } from 'react';
import { PapersTable, type PaperRow, type RowFacet } from '@/components/PapersTable';

type Cluster = 'interactions' | 'oscillations';
type ClusterData = { rows: PaperRow[]; facets: RowFacet[]; count: number };

function oscTags(r: PaperRow): ReactNode {
  const arr = (k: string) => (r[k] as string[] | undefined) ?? [];
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
      {arr('channel').map((c) => (
        <span className="tag tag-channel" key={c}>
          {c}
        </span>
      ))}
      {arr('parameter').map((p) => (
        <span className="tag tag-param" key={p}>
          {p}
        </span>
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
          detailBase={null}
          searchPlaceholder="Search title, experiment, channel, parameter, bibtag…"
        />
      )}
    </>
  );
}
