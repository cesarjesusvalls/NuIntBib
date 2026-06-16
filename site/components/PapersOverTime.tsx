'use client';

import { useMemo, useState } from 'react';
import type { Timeline } from '@/lib/papers';

type Metric = 'papers' | 'citations';

const W = 960;
const H = 320;
const ML = 48;
const MR = 14;
const MT = 14;
const MB = 30;
const IW = W - ML - MR;
const IH = H - MT - MB;

function runningSum(a: number[]): number[] {
  let s = 0;
  return a.map((v) => (s += v));
}

function niceTicks(max: number, count = 4): number[] {
  if (max <= 0) return [0];
  const raw = max / count;
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) ?? mag;
  const ticks: number[] = [];
  for (let t = 0; t <= max + step / 2; t += step) ticks.push(Math.round(t));
  return ticks;
}

export function PapersOverTime({ data }: { data: Timeline }) {
  const [metric, setMetric] = useState<Metric>('papers');
  const [cumulative, setCumulative] = useState(false);
  const [exp, setExp] = useState<string>('');
  const [hover, setHover] = useState<number | null>(null);

  const { tot, sel } = useMemo(() => {
    let tot = data.total[metric].slice();
    let sel = exp ? (data.byExp[exp]?.[metric] ?? data.years.map(() => 0)).slice() : null;
    if (cumulative) {
      tot = runningSum(tot);
      if (sel) sel = runningSum(sel);
    }
    return { tot, sel };
  }, [data, metric, cumulative, exp]);

  const n = data.years.length;
  const max = Math.max(...tot, 1);
  const ticks = niceTicks(max);
  const tickMax = ticks[ticks.length - 1];
  const colW = IW / n;
  const barW = Math.max(2, colW * 0.74);
  const y = (v: number) => MT + IH - (v / tickMax) * IH;
  const x = (i: number) => ML + i * colW + (colW - barW) / 2;

  const fmt = (v: number) => (metric === 'citations' ? v.toLocaleString() : String(v));
  const metricLabel = metric === 'citations' ? 'citations' : 'papers';

  return (
    <div className="panel timeline-panel">
      <div className="timeline-controls">
        <div className="seg" role="group" aria-label="Metric">
          {(['papers', 'citations'] as Metric[]).map((m) => (
            <button key={m} className={metric === m ? 'is-on' : ''} onClick={() => setMetric(m)} type="button">
              {m === 'papers' ? 'Papers' : 'Citations'}
            </button>
          ))}
        </div>
        <div className="seg" role="group" aria-label="View">
          <button className={!cumulative ? 'is-on' : ''} onClick={() => setCumulative(false)} type="button">
            Per year
          </button>
          <button className={cumulative ? 'is-on' : ''} onClick={() => setCumulative(true)} type="button">
            Cumulative
          </button>
        </div>
        <label className="timeline-highlight">
          Highlight
          <select value={exp} onChange={(e) => setExp(e.currentTarget.value)}>
            <option value="">All experiments</option>
            {data.experiments.map((e) => (
              <option key={e} value={e}>
                {e}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="timeline-chart">
        <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${metricLabel} over time`}>
          {/* y gridlines + labels */}
          {ticks.map((t) => (
            <g key={t}>
              <line className="tl-grid" x1={ML} x2={W - MR} y1={y(t)} y2={y(t)} />
              <text className="tl-axis" x={ML - 8} y={y(t) + 4} textAnchor="end">
                {fmt(t)}
              </text>
            </g>
          ))}
          {/* x year labels (decade marks) */}
          {data.years.map((yr, i) =>
            yr % 10 === 0 ? (
              <text key={yr} className="tl-axis" x={x(i) + barW / 2} y={H - 10} textAnchor="middle">
                {yr}
              </text>
            ) : null,
          )}
          {/* bars */}
          {data.years.map((yr, i) => {
            const t = tot[i];
            const s = sel ? Math.min(sel[i], t) : 0;
            const isHover = hover === i;
            return (
              <g key={yr}>
                {/* rest (or full bar when no selection) */}
                {t > 0 && (
                  <rect
                    className={exp ? 'tl-bar-rest' : 'tl-bar'}
                    x={x(i)}
                    y={y(t)}
                    width={barW}
                    height={Math.max(0, y(s) - y(t))}
                    opacity={isHover ? 0.85 : 1}
                  />
                )}
                {/* selected experiment segment */}
                {s > 0 && (
                  <rect className="tl-bar-sel" x={x(i)} y={y(s)} width={barW} height={Math.max(0, MT + IH - y(s))} />
                )}
                {/* invisible hover target spanning the column */}
                <rect
                  x={ML + i * colW}
                  y={MT}
                  width={colW}
                  height={IH}
                  fill="transparent"
                  onMouseEnter={() => setHover(i)}
                  onMouseLeave={() => setHover((h) => (h === i ? null : h))}
                />
              </g>
            );
          })}
        </svg>

        {hover != null && tot[hover] >= 0 && (
          <div
            className="tl-tooltip"
            style={{ left: `${((x(hover) + barW / 2) / W) * 100}%`, top: `${(y(tot[hover]) / H) * 100}%` }}
          >
            <strong>{data.years[hover]}</strong>
            <span>
              {fmt(tot[hover])} {metricLabel}
              {cumulative ? ' (total)' : ''}
            </span>
            {exp && (
              <span className="tl-tooltip-sel">
                {exp}: {fmt(Math.min(sel ? sel[hover] : 0, tot[hover]))}
              </span>
            )}
          </div>
        )}
      </div>

      <p className="timeline-caption">
        {cumulative ? 'Cumulative' : 'Per-year'} {metricLabel}
        {exp ? (
          <>
            {' '}
            — <span className="tl-legend-sel" /> {exp} highlighted within the total
          </>
        ) : (
          <> across {data.experiments.length} experiments. Pick an experiment to highlight its share.</>
        )}
      </p>
    </div>
  );
}
