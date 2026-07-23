// Pretty display for the measurement label codes (target / topology / measurement_type).
// Pure & client-safe (no fs) so both server components and client components
// (PapersTable, TableBuilder) can share one source of truth. The underlying data
// values are unchanged — these only affect display.

const SUB_DIGIT: Record<string, string> = {
  '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄',
  '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉',
};
const SUP_CHARGE: Record<string, string> = { '+': '⁺', '-': '⁻', '0': '⁰' };

/** Capitalize the first letter (double-diff → Double-diff, rock → Rock). */
export function capitalizeLabel(s: string): string {
  return s ? s[0].toUpperCase() + s.slice(1) : s;
}

/** Chemical-formula target: subscript every digit (CH2 → CH₂, H2O → H₂O, CaCO3 → CaCO₃). */
export function targetLabel(t: string): string {
  return t.replace(/[0-9]/g, (d) => SUB_DIGIT[d]);
}

/** Topology code: ν in CEvNS, and superscript particle charges (π+ → π⁺, π0 → π⁰,
 *  K+ → K⁺, D*+ → D*⁺). Leading counts (0π, 1π, 2p) stay as normal digits. */
export function topologyLabel(t: string): string {
  return t
    .replace('CEvNS', 'CEνNS')
    .replace(/([πK*])([+\-0])/g, (_, p: string, c: string) => p + SUP_CHARGE[c]);
}

/** One entry point for facet/label display, keyed by facet/field name. Flavor is
 *  handled separately (it needs KaTeX), so it's passed through unchanged here. */
export function facetValueLabel(key: string, value: string): string {
  switch (key) {
    case 'target':
    case 'material':
      return capitalizeLabel(targetLabel(value));
    case 'topology':
      return capitalizeLabel(topologyLabel(value));
    case 'measurement_type':
      return capitalizeLabel(value);
    default:
      return value; // current (CC/NC), experiment, year, … unchanged
  }
}
