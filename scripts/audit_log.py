#!/usr/bin/env python3
"""Track which papers have had their classification audited.

The ledger lives in data/audit_log.yml, keyed by bibtag:

    T2K:2013nor:
      audited: 2026-06-16
      method: abstract        # abstract | fulltext
      status: clean           # clean | fix-proposed | fixed | needs-fulltext
      notes: ...

"Closed" statuses (clean, fixed) are skipped on future audit passes; "open"
ones (fix-proposed, needs-fulltext) remain on the to-do list. Use `pending` to
list database papers not yet audited (or still open).

Usage:
  scripts/audit_log.py stats
  scripts/audit_log.py pending          # bibtags still needing an audit
  scripts/audit_log.py open             # audited but unresolved (fix/fulltext)
"""
from __future__ import annotations

import datetime as dt
import os
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_PATH = os.path.join(ROOT, "data", "audit_log.yml")
CLOSED = {"clean", "fixed"}


def load() -> dict:
    if not os.path.exists(LOG_PATH):
        return {}
    with open(LOG_PATH, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def save(log: dict) -> None:
    with open(LOG_PATH, "w", encoding="utf-8") as fh:
        yaml.safe_dump(log, fh, allow_unicode=True, sort_keys=True, width=100)


def record(bibtag: str, method: str, status: str, notes: str = "",
           date: str | None = None) -> None:
    log = load()
    log[bibtag] = {
        "audited": date or dt.date.today().isoformat(),
        "method": method,
        "status": status,
        "notes": notes or None,
    }
    save(log)


def audited_closed(log: dict | None = None) -> set:
    """Bibtags whose audit is settled (clean/fixed) — skip these next pass."""
    log = log if log is not None else load()
    return {k for k, v in log.items() if v.get("status") in CLOSED}


def pending_bibtags() -> list:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import db  # noqa: E402
    closed = audited_closed()
    return sorted(r["bibtag"] for r in db.load_db() if r["bibtag"] not in closed)


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stats"
    log = load()
    if cmd == "stats":
        from collections import Counter
        c = Counter(v.get("status") for v in log.values())
        print(f"{len(log)} audited: " + ", ".join(f"{k} {n}" for k, n in c.most_common()))
        print(f"{len(pending_bibtags())} still need auditing (not closed)")
    elif cmd == "pending":
        for b in pending_bibtags():
            print(b)
    elif cmd == "open":
        for k, v in sorted(log.items()):
            if v.get("status") not in CLOSED:
                print(f"{k:26} {v.get('status'):14} {v.get('notes') or ''}")
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
