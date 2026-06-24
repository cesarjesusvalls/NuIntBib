# NuBib

A community-maintained, continuously updated index of published **neutrino
measurements**, organized into topical clusters and searchable / filterable by
experiment, channel, and more, with one-click links to arXiv, the journal,
INSPIRE, and BibTeX. Live at **[nubib.org](https://nubib.org)**.

Two clusters, each with the same Papers / Table builder / Stats / About views:

- **Interactions** — experimental cross-section results (inclusive or exclusive)
  and related interaction observables.
- **Oscillations** — measurements of the standard PMNS parameters, or tests of
  exotic physics (sterile neutrinos, etc.).

The canonical data is version-controlled YAML, validated against a JSON schema
and enriched from INSPIRE-HEP. The website is a static render of that database.

## Layout

| Path | What |
| --- | --- |
| `data/papers/*.yml` | **Interaction database** (one file per experiment, one record per paper) |
| `data/oscillation/*.yml` | **Oscillation database** (one file per experiment, one record per paper) |
| `schemas/paper.schema.json` | Interaction record contract (validated in CI and on every update) |
| `schemas/oscillation_paper.schema.json` | Oscillation record contract |
| `data/legacy_classification.json` | Frozen hand-classification from `PaperFeatures.ipynb` |
| `scripts/` | Python tooling (migrate, validate, discovery + add for both clusters) |
| `site/` | Next.js static-export website (deploys to GitHub Pages) |
| `*.bib`, `*.ipynb`, `results/` | Original hand-curated bibliography (kept as raw history) |
| `UPDATE.md` | Runbook for the recurring "find + classify + add new papers" session |

## The website

```bash
cd site
yarn install
yarn dev        # http://localhost:3000
yarn build      # static export to site/out
```

Built with Next.js 16 (static export). Pages: `/` overview, `/papers` filterable
table, `/papers/<bibtag>` detail, `/stats`, `/about` — each with an
**Interactions / Oscillations** cluster toggle. Inline LaTeX in titles, abstracts,
and the neutrino flavor / channel / parameter tags is rendered with KaTeX at
build time.

## The database tooling

```bash
uv venv .venv && uv pip install --python .venv -r requirements.txt

.venv/bin/python scripts/validate.py        # check every record against the schema
.venv/bin/python scripts/migrate.py          # rebuild data/papers/ from bib + classification + INSPIRE
```

`scripts/migrate.py` is how the interaction database was first built (merging the
`.bib` files, the legacy classification, and live INSPIRE-HEP enrichment). You
normally only run `validate.py` and the update workflow below.

## Keeping it up to date

See **[UPDATE.md](UPDATE.md)** for the full runbook (both clusters). In short:

```bash
# Interactions
.venv/bin/python scripts/find_new_papers.py        # discover candidates via INSPIRE
# ...classify each candidate's `measurements` (agent proposes, human approves)...
.venv/bin/python scripts/add_papers.py --from data/candidates.yml

# Oscillations
.venv/bin/python scripts/find_osc_papers.py        # discover candidates via INSPIRE
# ...classify (source / framework / channels / parameters)...
.venv/bin/python scripts/add_osc_papers.py <classification.json> ...

cd site && yarn build
```

## Deployment

`.github/workflows/deploy.yml` builds the site and publishes it to GitHub Pages
on every push to `main`. The site is served from the apex custom domain
**[nubib.org](https://nubib.org)** (DNS A records → GitHub Pages, `CNAME` file in
`site/public/`, HTTPS enforced); it is built at the domain root, so
`NEXT_PUBLIC_BASE_PATH` is empty and `cesarjesusvalls.github.io/NuIntBib`
redirects to nubib.org. **One-time setup:** in the repo's *Settings → Pages*, set
the source to **GitHub Actions**.
