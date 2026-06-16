"""Normalize NuIntBib physics classification into structured measurement records.

The legacy hand-classification (PaperFeatures.ipynb -> paper_features dict) stores
each paper as a 6-tuple:

    [topology, target, current, flavor, observables, energy_notes]

e.g. ['CC1π+', '[CH]', 'CC', 'numu', 'differential cross sections ...', 'E: ...']

These helpers turn that tuple into the `measurements` object defined by
schemas/paper.schema.json, and are reused by the update workflow when proposing
classifications for newly discovered papers.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Dict, List, Optional

FLAVOR_TOKENS = ["numubar", "nuebar", "numu", "nue"]  # order: longest first


def _asciify(s: str) -> str:
    """Map Greek/symbols used in topology strings to ascii (π->pi, ★->star...)."""
    repl = {
        "π": "pi", "Λ": "Lambda", "γ": "gamma", "η": "eta",
        "★": "star", "∗": "star", "•": "", "≥": ">=",
    }
    for k, v in repl.items():
        s = s.replace(k, v)
    # strip any remaining non-ascii
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()


def normalize_topology(raw: str) -> str:
    return _asciify(raw).strip()


def normalize_targets(raw: str) -> List[str]:
    """'[CH,C,H2O,Fe,Pb]' -> ['CH','C','H2O','Fe','Pb']; '[Fe/C]' -> ['Fe','C']."""
    inner = raw.strip().strip("[]").strip()
    if not inner:
        return []
    parts = re.split(r"[,/]", inner)
    return [p.strip() for p in parts if p.strip()]


def normalize_flavor(raw: str):
    """Return (flavor_list, flavor_note).

    Pulls known neutrino tokens out of strings like 'numu+numubar',
    'numu/numubar', 'nue+nuebar'. Anything that does not map cleanly
    (e.g. 'unspecified (likely numu)') is preserved in flavor_note.
    """
    s = raw.strip()
    found: List[str] = []
    scan = s
    for tok in FLAVOR_TOKENS:
        if tok in scan:
            found.append(tok)
            scan = scan.replace(tok, " ")
    # preserve declaration order (numu before numubar, etc.)
    ordered = [t for t in ["numu", "numubar", "nue", "nuebar"] if t in found]
    leftover = re.sub(r"[+/,\s]+", " ", scan).strip()
    note: Optional[str] = None
    if not ordered or leftover not in ("", "nu", "nubar", "nu nubar"):
        # ambiguous / extra words -> keep the raw text as a note
        note = s if (not ordered or leftover) else None
    return ordered, note


def derive_pion_bucket(topology: str) -> Optional[str]:
    """Coarse pion-content bucket for filtering. None when not meaningful."""
    t = normalize_topology(topology).lower()
    if "multi" in t and "pi" in t:
        return "multi_pi"
    if "pi0" in t:
        return "pi0"
    if re.search(r"pi[+\-±]", topology) or "pi+" in t or "pi-" in t or "1pi" in t and "pi0" not in t:
        # charged-pion final states
        if "pi0" not in t:
            return "pi_charged"
    if "0pi" in t or "qe" in t or "elastic" in t or t.startswith("cc0") or t.startswith("nc0"):
        return "0pi"
    return None


def derive_measurement_type(observables: str) -> Optional[str]:
    o = (observables or "").lower()
    if not o:
        return None
    if "triple" in o:
        return "triple-diff"
    if "double" in o or "double-differential" in o:
        return "double-diff"
    if "ratio" in o:
        return "ratio"
    if "upper limit" in o or "limit" in o:
        return "limit"
    if "differential" in o:
        return "single-diff"
    if "total" in o or "cross section" in o:
        return "total"
    return None


def build_measurement(tup: List[str]) -> Dict:
    """Convert a legacy 6-tuple into a schema `measurements` item."""
    topology, target, current, flavor, observables, energy = (list(tup) + [""] * 6)[:6]
    flav, flav_note = normalize_flavor(flavor)
    m = {
        "current": "NC" if current.strip().upper() == "NC" else "CC",
        "flavor": flav,
        "target": normalize_targets(target),
        "topology": normalize_topology(topology),
        "pion_bucket": derive_pion_bucket(topology),
        "measurement_type": derive_measurement_type(observables),
        "observables": observables.strip() or None,
        "energy_notes": energy.strip() or None,
    }
    if flav_note:
        m["flavor_note"] = flav_note
    return m


if __name__ == "__main__":
    samples = [
        ["CC1π+", "[CH]", "CC", "numu", "differential cross sections", "E: 1.5-10GeV"],
        ["Inclusive", "[Ar]", "CC", "nue+nuebar", "total and lepton angle differential cross section", ""],
        ["NC1π0", "[H2O]", "NC", "numu", "ratio of NC1π0 to CC total cross section", "mean 1.3GeV"],
        ["CC2p", "[Ar]", "CC", "unspecified (likely numu)", "two-proton topology", "SRC"],
        ["DIS", "[CH,C,Fe,Pb]", "CC", "numu", "total and differential cross section ratios", "E: 5-50GeV"],
    ]
    import json
    for s in samples:
        print(json.dumps(build_measurement(s), ensure_ascii=False))
