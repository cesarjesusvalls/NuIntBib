# NuIntBib

A community-maintained, continuously updated index of published **neutrino
cross-section measurements**, searchable and filterable by experiment, current,
flavor, target, and interaction topology, with one-click links to arXiv, the
journal, INSPIRE, and BibTeX.

The canonical data is version-controlled YAML, validated against a JSON schema
and enriched from INSPIRE-HEP. The website is a static render of that database.

## Layout

| Path | What |
| --- | --- |
| `data/papers/*.yml` | **Canonical database** (one file per experiment, one record per paper) |
| `schemas/paper.schema.json` | Record contract (validated in CI and on every update) |
| `data/legacy_classification.json` | Frozen hand-classification from `PaperFeatures.ipynb` |
| `scripts/` | Python tooling (migrate, validate, update workflow) |
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
table, `/papers/<bibtag>` detail, `/stats`, `/about`. Inline LaTeX in titles and
abstracts is rendered with KaTeX at build time.

## The database tooling

```bash
uv venv .venv && uv pip install --python .venv -r requirements.txt

.venv/bin/python scripts/validate.py        # check every record against the schema
.venv/bin/python scripts/migrate.py          # rebuild data/papers/ from bib + classification + INSPIRE
```

`scripts/migrate.py` is how the database was first built (merging the `.bib`
files, the legacy classification, and live INSPIRE-HEP enrichment). You normally
only run `validate.py` and the update workflow below.

## Keeping it up to date

See **[UPDATE.md](UPDATE.md)**. In short:

```bash
.venv/bin/python scripts/find_new_papers.py        # discover candidates via INSPIRE
# ...classify each candidate's `measurements` (agent proposes, human approves)...
.venv/bin/python scripts/add_papers.py --from data/candidates.yml
cd site && yarn build
```

## Deployment

`.github/workflows/deploy.yml` builds the site and publishes it to GitHub Pages
on every push to `main` that touches `site/`, `data/papers/`, or the `.bib`
files. **One-time setup:** in the repo's *Settings → Pages*, set the source to
**GitHub Actions**. The site is served from `https://<owner>.github.io/NuIntBib/`
(the base path is set in the workflow via `NEXT_PUBLIC_BASE_PATH`).
