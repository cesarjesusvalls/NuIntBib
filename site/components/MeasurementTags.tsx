import { facetValueLabel } from '@/lib/labels';

/** The single source of truth for the interaction measurement label chips
 *  (current / flavor / target / topology / measurement-type / dataset).
 *  Used by both the papers table (per row) and the paper detail page (per
 *  measurement) so the two never drift apart. Flavor is passed as pre-rendered
 *  KaTeX HTML (falling back to plain text) so this stays client-safe. */
export function MeasurementTags({
  current = [],
  flavorHtml = [],
  flavorText = [],
  target = [],
  topology = [],
  measurementType = [],
  dataset = false,
}: {
  current?: string[];
  flavorHtml?: string[];
  flavorText?: string[];
  target?: string[];
  topology?: string[];
  measurementType?: string[];
  dataset?: boolean;
}) {
  const nFlavor = Math.max(flavorHtml.length, flavorText.length);
  return (
    <>
      {current.map((c) => (
        <span className={`tag tag-${c.toLowerCase()}`} key={`c-${c}`}>
          {c}
        </span>
      ))}
      {Array.from({ length: nFlavor }).map((_, i) =>
        flavorHtml[i] ? (
          <span
            className="tag tag-flavor"
            key={`f-${i}`}
            dangerouslySetInnerHTML={{ __html: flavorHtml[i] }}
          />
        ) : (
          <span className="tag tag-flavor" key={`f-${i}`}>
            {flavorText[i]}
          </span>
        ),
      )}
      {target.map((t) => (
        <span className="tag tag-target" key={`t-${t}`}>
          {facetValueLabel('target', t)}
        </span>
      ))}
      {topology.map((t) => (
        <span className="tag tag-topo" key={`tp-${t}`}>
          {facetValueLabel('topology', t)}
        </span>
      ))}
      {measurementType.map((t) => (
        <span className="tag tag-type" key={`mt-${t}`}>
          {facetValueLabel('measurement_type', t)}
        </span>
      ))}
      {dataset ? (
        <span className="tag tag-data" title="A downloadable data release is available">
          Dataset
        </span>
      ) : null}
    </>
  );
}
