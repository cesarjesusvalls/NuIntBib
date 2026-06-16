# Update runbook — adding new papers to NuIntBib

This is the procedure for the recurring **update session**: find neutrino
cross-section papers published since our last update, classify them, and add the
relevant ones to the database. It is designed to be driven by an agent (Claude
Code) with a human approving classifications, but every step is a plain script
you can also run by hand.

## TL;DR

```bash
# 0. one-time tooling setup
uv venv .venv && uv pip install --python .venv pyyaml requests jsonschema

# 1. discover candidates (queries INSPIRE-HEP, caches responses)
.venv/bin/python scripts/find_new_papers.py            # writes data/candidates.yml

# 2. classify each candidate's `measurements` (see "Classifying" below)
#    — agent proposes, human approves —

# 3. ingest the classified, relevant candidates
.venv/bin/python scripts/add_papers.py --from data/candidates.yml   # validates on write

# 4. rebuild the site
cd site && yarn build
```

## What "relevant" means

We track **published experimental neutrino cross-section measurements**. Include:
flux-averaged total / differential / double- / triple-differential cross sections
and cross-section ratios from neutrino experiments.

Exclude (these show up in the candidate list and must be filtered out):

- **Proceedings, reviews, theses** — usually have an **author-keyed** texkey
  (`Latham:2024zcq`, `Litchfield:2024zqw`) rather than a collaboration key. The
  discovery script tags each candidate with `_triage` to flag these.
- **Simulation / flux / detector / method papers** (e.g. "Development of T2K
  Beam Simulation", "BDT reweighting of simulated interactions").
- **Pure theory / generator / form-factor extraction** papers.

Rule of thumb: a real measurement almost always has a **collaboration-keyed**
texkey (`MicroBooNE:2025ooi`, `T2K:2025smz`, `MINERvA:2026ymp`) and a title that
reports a *measurement of a cross section*.

## 1. Discover

```bash
.venv/bin/python scripts/find_new_papers.py [--since YYYY-MM-DD] [--collaborations T2K MINERvA ...]
```

- Default `--since` is `(latest tracked published_date − 180 days)`, so late
  arrivals are not missed. De-duplication is against **all** known bibtags and
  arXiv ids, so re-scanning earlier dates is safe (nothing is added twice).
- Output: `data/candidates.yml` — one record per new paper, already enriched
  from INSPIRE (title, journal, arXiv, date, citations, abstract), with an empty
  `measurements: []` list and a `_triage` hint.

## 2. Classify

For each candidate worth keeping, fill its `measurements` list. A paper may hold
several measurements (different channel/target); add one entry each. Either:

- write a structured object matching `schemas/paper.schema.json`, **or**
- write a legacy 6-tuple `[topology, target, current, flavor, observables, energy]`
  — `add_papers.py` normalizes tuples via `scripts/classify.py`.

### Controlled vocabulary

| Field | Values |
| --- | --- |
| `current` | `CC`, `NC` |
| `flavor` | `numu`, `numubar`, `nue`, `nuebar` (list; use `flavor_note` for "unspecified") |
| `target` | material symbols: `Ar`, `CH`, `CH2`, `C`, `O`, `H2O`, `Fe`, `Pb`, `W`, `C8H8`, … |
| `topology` | `Inclusive`, `CCQE`, `CCQE-like`, `CCQEp`, `CC0pi`, `CC1pi+`, `CC1pi0`, `CCcoh pi`, `NC1pi0`, `NCcoh pi0`, `NC elastic`, `DIS`, `CC2p`, `CC K+`, `CC eta`, `CC Lambda`, … (π → `pi`) |
| `measurement_type` | `total`, `single-diff`, `double-diff`, `triple-diff`, `ratio`, `limit` |
| `pion_bucket` | `0pi`, `pi_charged`, `pi0`, `multi_pi`, or null (auto-derived if omitted) |

`observables` and `energy_notes` are free text (e.g. "double-differential in muon
pT, pL"; "mean energy ~0.8 GeV"). Read the INSPIRE abstract (already in the
candidate record) to fill these. The agent proposes all of this; the maintainer
reviews before step 3.

## 3. Ingest

```bash
.venv/bin/python scripts/add_papers.py --from data/candidates.yml [--dry-run]
```

- Skips candidates with empty `measurements` (still need classifying) and any
  bibtag already present.
- Appends the rest to `data/papers/<Experiment>.yml` (newest first) and runs
  `scripts/validate.py`. Non-zero exit means a schema problem to fix.
- `data/candidates.yml` is a scratch file (gitignored); delete it when done.

## 4. Rebuild & publish

```bash
cd site && yarn build      # static export to site/out
```

Commit the changed `data/papers/*.yml` (and, if used, regenerated `.bib`).
GitHub Actions rebuilds and deploys the site (see `.github/workflows/`).

## Notes

- INSPIRE responses are cached under `.cache/` (gitignored); delete it to force
  refresh.
- To widen coverage, add collaborations to `COLLABORATIONS` in
  `scripts/find_new_papers.py` (it already includes forward-looking experiments
  like SBND, ICARUS, DUNE, SND).
