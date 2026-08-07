"""Derive a display-ready `abstract_tex` from a raw INSPIRE `abstract`.

Old (pre-arXiv) INSPIRE abstracts store physics as plain ASCII ("nu_e", "12C",
"mu-", "10^-41 cm^2") with no markup, so the site's KaTeX/unicode renderer leaves
them raw. This turns the common patterns into inline `$...$` LaTeX.

Design: the raw `abstract` is preserved verbatim; ingestion calls `to_tex()` to
produce `abstract_tex`. Regenerating after improving this function re-derives all
of them.

Conservative by construction — `to_tex` returns the raw text UNCHANGED when it is
  * already marked up (`$` or a backslash macro — modern arXiv abstracts), or
  * contains any non-ASCII char (older PDF-extracted abstracts with unicode
    ν/μ/σ/× that already read fine and are too irregular to transform safely).
Only clean ASCII physics notation is converted, each token wrapped in its own
`$...$`, so the function never produces garbled output.
"""
import re

# Elements that appear as isotopes in these abstracts (extend as needed).
_ISO = r"(?:C|N|O|B|H|I|F|P|S|K|V|W|Xe|Ge|Ga|Cr|Ar|Ca|Fe|He|Li|Na|Al|Pb|Ne|Cl|Ti|Ni|Zn|Se|Mo)"

# (pattern, replacement) applied in order; replacements yield single backslashes.
_REPS = [
    (r"\bnu_e\b", r"$\\nu_e$"),
    (r"\bnu_mu\b", r"$\\nu_\\mu$"),
    (r"\bnu_tau\b", r"$\\nu_\\tau$"),
    (r"\bmu\s*\+", r"$\\mu^+$"),
    (r"\bmu\s*-", r"$\\mu^-$"),
    (r"\bpi\s*\+", r"$\\pi^+$"),
    (r"\bpi\s*-", r"$\\pi^-$"),
    (r"\be\s*\+(?![A-Za-z])", r"$e^+$"),
    (r"\be\s*-(?![A-Za-z])", r"$e^-$"),
    # isotopes: mass-first (12C) and element-first (C12); trailing lookahead so
    # "127Xe_(bound)" matches (\b fails before "_").
    (rf"\b(\d{{1,3}})({_ISO})(?![A-Za-z])", r"$^{\1}\\mathrm{\2}$"),
    (rf"\b({_ISO})(\d{{1,3}})(?![A-Za-z])", r"$^{\2}\\mathrm{\1}$"),
    (r"10\^[\({]?(-?\d+)[\)}]?", r"$10^{\1}$"),
    (r"\bcm\^?2\b", r"$\\mathrm{cm}^2$"),
    (r"\s*->\s*", r" $\\to$ "),
]


def to_tex(raw):
    if not raw:
        return raw
    if "$" in raw:                       # already inline-math LaTeX
        return raw
    if any(ord(c) > 127 for c in raw):   # unicode PDF extraction — leave readable
        return raw
    s = raw
    for pat, rep in _REPS:
        s = re.sub(pat, rep, s)
    s = re.sub(r"[ \t]{2,}", " ", s)
    return s


if __name__ == "__main__":
    import sys
    print(to_tex(sys.argv[1] if len(sys.argv) > 1 else ""))
