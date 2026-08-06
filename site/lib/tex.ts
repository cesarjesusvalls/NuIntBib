import katex from 'katex';

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

const GREEK: Record<string, string> = {
  alpha: 'α', beta: 'β', gamma: 'γ', delta: 'δ', epsilon: 'ε', zeta: 'ζ',
  eta: 'η', theta: 'θ', iota: 'ι', kappa: 'κ', lambda: 'λ', mu: 'μ', nu: 'ν',
  xi: 'ξ', pi: 'π', rho: 'ρ', sigma: 'σ', tau: 'τ', upsilon: 'υ', phi: 'φ',
  chi: 'χ', psi: 'ψ', omega: 'ω', Gamma: 'Γ', Delta: 'Δ', Theta: 'Θ',
  Lambda: 'Λ', Xi: 'Ξ', Pi: 'Π', Sigma: 'Σ', Phi: 'Φ', Psi: 'Ψ', Omega: 'Ω',
};
const SYM: Record<string, string> = {
  times: '×', pm: '±', mp: '∓', to: '→', rightarrow: '→', approx: '≈',
  sim: '~', leq: '≤', le: '≤', geq: '≥', ge: '≥', cdot: '·', ell: 'ℓ',
  infty: '∞', simeq: '≃', parallel: '∥', perp: '⊥', cos: 'cos', sin: 'sin',
  tan: 'tan', langle: '⟨', rangle: '⟩',
};
const SUP: Record<string, string> = {
  '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴', '5': '⁵', '6': '⁶',
  '7': '⁷', '8': '⁸', '9': '⁹', '+': '⁺', '-': '⁻', '=': '⁼', '(': '⁽', ')': '⁾', n: 'ⁿ',
};
const SUB: Record<string, string> = {
  '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄', '5': '₅', '6': '₆',
  '7': '₇', '8': '₈', '9': '₉', '+': '₊', '-': '₋', '=': '₌', '(': '₍', ')': '₎',
};

function mapScript(body: string, table: Record<string, string>): string | null {
  let out = '';
  for (const ch of body) {
    if (table[ch]) out += table[ch];
    else return null; // bail out if any char is not scriptable
  }
  return out;
}

/** Best-effort conversion of common unwrapped LaTeX macros in plain text to Unicode. */
export function latexToUnicode(input: string): string {
  let s = input;
  // \bar{x} / \overline{x} -> x with combining overline
  s = s.replace(/\\(?:bar|overline)\s*\{([^}]*)\}/g, (_, x) => `${x}̅`);
  // \bar / \overline applied to a single following token (macro or char), no braces:
  // e.g. \bar\nu -> ν̄
  s = s.replace(/\\(?:bar|overline)\s*(\\[A-Za-z]+|\S)/g, (_, tok) => {
    const ch = tok.startsWith('\\') ? GREEK[tok.slice(1)] ?? SYM[tok.slice(1)] ?? tok : tok;
    return `${ch}̅`;
  });
  // roman/text font macros: \mathrm{X} \text{X} \operatorname{X} ... -> X
  s = s.replace(
    /\\(?:math(?:rm|bf|it|sf|cal|tt)|text(?:rm|it|bf)?|operatorname)\s*\{([^}]*)\}/g,
    '$1',
  );
  // spacing macros: \, \; \: \! \quad \qquad \ (backslash-space) -> a space
  s = s.replace(/\\(?:q?quad)/g, ' ').replace(/\\[\s,;:!]/g, ' ');
  // superscripts: ^{...} or ^x  (only when every char is scriptable)
  s = s.replace(/\^\{([^}]*)\}/g, (m, b) => mapScript(b, SUP) ?? m);
  s = s.replace(/\^(\S)/g, (m, b) => mapScript(b, SUP) ?? m);
  // subscripts: _{...} or _x
  s = s.replace(/_\{([^}]*)\}/g, (m, b) => mapScript(b, SUB) ?? m);
  s = s.replace(/_(\d)/g, (m, b) => mapScript(b, SUB) ?? m);
  // greek + symbol macros
  s = s.replace(/\\([A-Za-z]+)/g, (m, name) => GREEK[name] ?? SYM[name] ?? m);
  // drop braces that merely grouped macros (e.g. \nu{\mu} -> ν{μ} -> νμ)
  s = s.replace(/[{}]/g, '');
  return s;
}

// Author-defined shorthand macros that INSPIRE abstracts sometimes carry over from a
// paper's preamble (e.g. MiniBooNE's \numub, \mup, \qsq, \uz). KaTeX doesn't know them,
// so without this it renders them in red as undefined control sequences.
const TEX_MACROS: Record<string, string> = {
  '\\numu': '\\nu_\\mu', '\\numub': '\\bar\\nu_\\mu', '\\numubar': '\\bar\\nu_\\mu',
  '\\nue': '\\nu_e', '\\nueb': '\\bar\\nu_e', '\\nuebar': '\\bar\\nu_e',
  '\\nutau': '\\nu_\\tau', '\\nutaub': '\\bar\\nu_\\tau',
  '\\mup': '\\mu^+', '\\mum': '\\mu^-', '\\qsq': 'Q^2', '\\uz': '\\cos\\theta_\\mu',
};

/**
 * Render a string that mixes plain text with inline `$...$` LaTeX into HTML.
 * Runs at build time (server) via katex.renderToString; no client JS needed.
 * Unknown/broken math falls back to the escaped source rather than throwing.
 */
function renderInlineTex(text: string): string {
  // split keeping the $...$ delimited groups
  return text
    .split(/(\$[^$]*\$)/g)
    .map((seg) => {
      if (seg.length > 1 && seg.startsWith('$') && seg.endsWith('$')) {
        const tex = seg.slice(1, -1);
        try {
          return katex.renderToString(tex, { throwOnError: false, strict: false, macros: TEX_MACROS });
        } catch {
          return escapeHtml(seg);
        }
      }
      return escapeHtml(latexToUnicode(seg));
    })
    .join('');
}

export function texToHtml(input: string | null | undefined): string {
  if (!input) return '';
  // Some INSPIRE abstracts use \( … \) / \[ … \] LaTeX delimiters instead of $…$;
  // normalize them so the KaTeX pass below picks up the math.
  input = input.replace(/\\[()[\]]/g, '$');
  // Some INSPIRE titles ship raw MathML (<math>…</math>) instead of $…$ TeX.
  // Browsers render MathML natively, so pass those blocks through verbatim and
  // only TeX-process the surrounding text.
  return input
    .split(/(<math[\s\S]*?<\/math>)/g)
    .map((seg) =>
      seg.startsWith('<math') && seg.endsWith('</math>') ? seg : renderInlineTex(seg),
    )
    .join('');
}

/** Plain-text version (for search text and meta descriptions): drop markup. */
export function stripTex(input: string | null | undefined): string {
  if (!input) return '';
  return latexToUnicode(
    input
      .replace(/<[^>]+>/g, ' ') // MathML / HTML tags
      .replace(/\\[()[\]]/g, ' '), // \( \) \[ \] LaTeX delimiters
  )
    .replace(/\$/g, '')
    .replace(/[{}]/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}
