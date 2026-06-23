'use client';

import { useState } from 'react';
import { PapersOverTime } from '@/components/PapersOverTime';
import type { Timeline } from '@/lib/papers';

type Cluster = 'interactions' | 'oscillations';

const count = (t: Timeline) => t.total.papers.reduce((a, b) => a + b, 0);

export function ClusteredTimeline({
  interactions,
  oscillations,
}: {
  interactions: Timeline;
  oscillations: Timeline;
}) {
  const [cluster, setCluster] = useState<Cluster>('interactions');
  const data = cluster === 'interactions' ? interactions : oscillations;

  return (
    <>
      <div className="cluster-toggle" role="group" aria-label="Topic cluster">
        <button
          aria-pressed={cluster === 'interactions'}
          className={cluster === 'interactions' ? 'is-on' : ''}
          onClick={() => setCluster('interactions')}
          type="button"
        >
          Interactions <small>{count(interactions)}</small>
        </button>
        <button
          aria-pressed={cluster === 'oscillations'}
          className={cluster === 'oscillations' ? 'is-on' : ''}
          onClick={() => setCluster('oscillations')}
          type="button"
        >
          Oscillations <small>{count(oscillations)}</small>
        </button>
      </div>
      <PapersOverTime key={cluster} data={data} />
    </>
  );
}
