'use client';

import { useState } from 'react';
import { TableBuilder, type TBPaper, type RowFacet, type Cluster } from '@/components/TableBuilder';

type ClusterData = { data: TBPaper[]; facets: RowFacet[]; count: number };

export function ClusteredTable({
  interactions,
  oscillations,
}: {
  interactions: ClusterData;
  oscillations: ClusterData;
}) {
  const [cluster, setCluster] = useState<Cluster>('interactions');
  const active = cluster === 'interactions' ? interactions : oscillations;

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
      <TableBuilder key={cluster} cluster={cluster} data={active.data} facets={active.facets} />
    </>
  );
}
