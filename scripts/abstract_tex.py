"""Derive a display-ready `abstract_tex` from a raw INSPIRE `abstract`.

Old (pre-arXiv) INSPIRE abstracts store physics as ASCII ("nu_e", "12C", "mu-",
"10^-41 cm^2") or messy PDF-extracted unicode ("νe", "ν¯e", "×10−41 cm2"), which
the site's KaTeX renderer leaves raw. `to_tex()` turns the common patterns into
inline `$...$` LaTeX.

Design: the raw `abstract` is preserved verbatim; ingestion calls `to_tex()` to
produce `abstract_tex`, stored only when it differs. Regenerating after improving
this function re-derives all of them.

Conservative: returns the raw text unchanged if it already contains `$` (already
inline-math LaTeX). Each recognised token is wrapped in its own `$...$` (no
grouping); molecules are protected by look-around and existing `\\macro`s are not
re-processed, so it does not garble. Unicode chars are built with chr() so the
source stays pure ASCII and encoding can never cause a miss.
"""
import re

# --- unicode codepoints (built as ASCII source) ---
NU = chr(0x03BD)      # ν
MU = chr(0x03BC)      # μ
PI = chr(0x03C0)      # π
TAU = chr(0x03C4)     # τ
TIMES = chr(0x00D7)   # ×
ARROW = chr(0x2192)   # →
# macron / overline variants that can sit over ν for antineutrino
BAR = "[" + chr(0x00AF) + chr(0x0304) + chr(0x0305) + chr(0x203E) + "]"
# minus-like chars normalised to hyphen (needed for exponents)
MINUSES = [chr(0x2212), chr(0x2013)]

# Elements that appear as isotopes (two-letter symbols first in the alternation).
_ISO = (r"(?:Xe|Ge|Ga|Cr|Ar|Ca|Fe|He|Li|Na|Al|Pb|Ne|Cl|Ti|Ni|Zn|Se|Mo"
        r"|C|N|O|B|H|I|F|P|S|K|V|W)")

# (pattern, replacement); replacements are raw strings yielding single backslashes.
_REPS = [
    # antineutrinos: ν + a macron/overline + flavor  (before plain neutrinos)
    (NU + r"\s*" + BAR + r"\s*_?\s*e", r"$\\bar\\nu_e$"),
    (NU + r"\s*" + BAR + r"\s*_?\s*(?:" + MU + r"|mu)", r"$\\bar\\nu_\\mu$"),
    (NU + r"\s*" + BAR + r"\s*_?\s*(?:" + TAU + r"|tau)", r"$\\bar\\nu_\\tau$"),
    (r"anti-?electron-?neutrino", r"$\\bar\\nu_e$"),
    (r"anti-?muon-?neutrino", r"$\\bar\\nu_\\mu$"),
    # neutrinos: ascii nu_x and unicode νx / ν x. (?<!\\) so this does not re-match
    # the "nu_e" inside a "\nu_e" the antineutrino rule just produced.
    (r"(?<!\\)\bnu_e\b", r"$\\nu_e$"),
    (r"(?<!\\)\bnu_mu\b", r"$\\nu_\\mu$"),
    (r"(?<!\\)\bnu_tau\b", r"$\\nu_\\tau$"),
    (NU + r"\s*_?\s*e\b", r"$\\nu_e$"),
    (NU + r"\s*_?\s*(?:" + MU + r"|mu)", r"$\\nu_\\mu$"),
    (NU + r"\s*_?\s*(?:" + TAU + r"|tau)", r"$\\nu_\\tau$"),
    # charged leptons / pions (ascii + unicode). (?<!\\) so "\mu", "\pi" in an
    # abstract that mixes ascii with stray LaTeX macros are left alone.
    (r"(?<!\\)\b(?:mu|" + MU + r")\s*\+", r"$\\mu^+$"),
    (r"(?<!\\)\b(?:mu|" + MU + r")\s*-", r"$\\mu^-$"),
    (r"(?<!\\)\b(?:pi|" + PI + r")\s*\+", r"$\\pi^+$"),
    (r"(?<!\\)\b(?:pi|" + PI + r")\s*-", r"$\\pi^-$"),
    (r"(?<!\\)\be\s*\+(?![A-Za-z])", r"$e^+$"),
    (r"(?<!\\)\be\s*-(?![A-Za-z])", r"$e^-$"),
    # isotopes: mass-first (12C) and element-first (C12); look-around keeps
    # molecules ("H2O", "D2O", "NaI") intact.
    (rf"(?<![A-Za-z])(\d{{1,3}})({_ISO})(?![A-Za-z])", r"$^{\1}\\mathrm{\2}$"),
    (rf"(?<![A-Za-z0-9])({_ISO})(\d{{1,3}})(?![A-Za-z])", r"$^{\2}\\mathrm{\1}$"),
    # powers of ten: ×10−41 / × 10 -42 / ×1013 (unicode, no caret) first, then
    # bare 10^-41 / 10^{-41} / 10^(-40); the lookbehind stops the second rule from
    # re-wrapping the "10^{..}" the first rule just produced.
    (TIMES + r"\s*10\s*\^?\s*[\({]?\s*(-?\d+)[\)}]?", r"$\\times 10^{\1}$"),
    (r"(?<!\\times )10\^[\({]?(-?\d+)[\)}]?", r"$10^{\1}$"),
    # cm^2 / cm2 / cm 2
    (r"\bcm\s*\^?\s*2\b", r"$\\mathrm{cm}^2$"),
    # reaction arrows (ascii -> and unicode →)
    (r"\s*->\s*", r" $\\to$ "),
    (r"\s*" + ARROW + r"\s*", r" $\\to$ "),
]


def to_tex(raw):
    if not raw:
        return raw
    if "$" in raw:                        # already inline-math LaTeX
        return raw
    s = raw
    for m in MINUSES:
        s = s.replace(m, "-")
    s = s.replace(chr(0x2217), "*").replace(chr(0x2032), "'")   # ∗ ′
    for pat, rep in _REPS:
        s = re.sub(pat, rep, s)
    s = s.replace("$$", "$ $")            # separate adjacent particle tokens
    s = re.sub(r"[ \t]{2,}", " ", s)
    return s


if __name__ == "__main__":
    import sys
    print(to_tex(sys.argv[1] if len(sys.argv) > 1 else ""))
