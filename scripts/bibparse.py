"""Minimal, dependency-free BibTeX reader for NuIntBib .bib files.

The .bib files follow a regular shape:

    @article{T2K:2013nor,
        author = "Abe, K. and others",
        title = "{...}",
        eprint = "1302.4908",
        ...
    }

We only need a tolerant reader for `@article{key, field = "value", ...}` where
values are delimited by double quotes and may contain balanced `{...}` groups.
"""
from __future__ import annotations

import glob
import os
import re
from typing import Dict, List

_ENTRY_RE = re.compile(r"@(\w+)\s*\{", re.IGNORECASE)


def _read_value(text: str, i: int):
    """Read a quoted value starting at text[i] == '\"'. Returns (value, next_i)."""
    assert text[i] == '"'
    depth = 0
    out = []
    i += 1
    while i < len(text):
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        elif c == '"' and depth == 0:
            return "".join(out), i + 1
        out.append(c)
        i += 1
    raise ValueError("unterminated quoted value")


def parse_entries(text: str) -> List[Dict[str, str]]:
    entries: List[Dict[str, str]] = []
    for m in _ENTRY_RE.finditer(text):
        i = m.end()  # just after '{'
        # entry key up to first comma
        j = text.index(",", i)
        key = text[i:j].strip()
        entry: Dict[str, str] = {"ID": key, "ENTRYTYPE": m.group(1).lower()}
        i = j + 1
        # parse fields until the entry's closing brace at depth 0
        while i < len(text):
            # skip whitespace / commas
            while i < len(text) and text[i] in " \t\r\n,":
                i += 1
            if i >= len(text) or text[i] == "}":
                break
            fm = re.match(r"([A-Za-z][\w-]*)\s*=\s*", text[i:])
            if not fm:
                break
            fname = fm.group(1).lower()
            i += fm.end()
            if text[i] == '"':
                val, i = _read_value(text, i)
            elif text[i] == "{":
                depth = 0
                start = i
                while i < len(text):
                    if text[i] == "{":
                        depth += 1
                    elif text[i] == "}":
                        depth -= 1
                        if depth == 0:
                            break
                    i += 1
                val = text[start + 1 : i]
                i += 1
            else:  # bare token (number)
                mm = re.match(r"[^,}\s]+", text[i:])
                val = mm.group(0)
                i += mm.end()
            entry[fname] = val.strip()
        entries.append(entry)
    return entries


def load_bib_dir(directory: str) -> Dict[str, Dict[str, str]]:
    """Return {bibtag: entry} across every <Experiment>.bib in `directory`.

    The collaboration is taken from the entry, falling back to the filename.
    """
    out: Dict[str, Dict[str, str]] = {}
    for path in sorted(glob.glob(os.path.join(directory, "*.bib"))):
        exp = os.path.splitext(os.path.basename(path))[0]
        with open(path, encoding="utf-8") as fh:
            for e in parse_entries(fh.read()):
                e.setdefault("collaboration", exp)
                e["_file_experiment"] = exp
                out[e["ID"]] = e
    return out


if __name__ == "__main__":
    import sys

    d = sys.argv[1] if len(sys.argv) > 1 else "."
    entries = load_bib_dir(d)
    print(f"{len(entries)} entries")
    for k, v in list(entries.items())[:3]:
        print(k, "->", v.get("title", "")[:60])
