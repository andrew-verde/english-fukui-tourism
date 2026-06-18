# Academic Reproducibility Checklist

This note packages the repository for academic code review. It is written for
an editor, reviewer, or future researcher who wants to verify the computational
claims without guessing which files are authoritative.

## External Standard Used

The checklist follows the level of documentation commonly requested for
journal code supplements:

- JOSS review criteria: clear statement of need, automated installation,
  example usage, tests, and reviewer-verifiable functionality.
- Nature Portfolio code availability policy: custom code central to the
  conclusions should have a separate code-availability statement, release path,
  access restrictions, and enough detail for readers to repeat the published
  results.
- PLOS materials/software/code-sharing policy: research materials should be
  available on request or through repositories when possible, with privacy or
  confidentiality restrictions stated explicitly.

Reference URLs:

- <https://joss.readthedocs.io/en/latest/review_criteria.html>
- <https://www.nature.com/nature-portfolio/editorial-policies/reporting-standards>
- <https://journals.plos.org/plosone/s/materials-and-software-sharing>

## Environment

Primary verified environment:

- Python: 3.14.4
- Dependency install: `.venv/bin/pip install -r requirements.lock.txt`
- Dependency health check: `.venv/bin/python3 -m pip check`
- CI environment: GitHub Actions `ubuntu-latest`, Python 3.14,
  `pip install -r requirements.lock.txt`, then `python -m pytest tests/ -q`

Dependency files:

- `requirements.lock.txt` is the reproduction file. It pins the exact Python
  packages used for the committed results.
- `requirements.txt` is the maintenance file. It records looser lower bounds
  for intentional upgrades and development.

Recommended clean-room install:

```bash
git clone <repository-url>
cd america-fukui-tourism
git lfs pull

python3.14 -m venv .venv
.venv/bin/pip install -r requirements.lock.txt
.venv/bin/python3 -m pip check
```

If `python3.14` is not the executable name on your machine, use any CPython
3.14 interpreter and keep the same lock file.

## Minimal Reviewer Verification

This path checks installation, imports, tests, and the primary no-network
analysis layers from pinned local inputs:

```bash
make reproduce-submission
```

Equivalent expanded commands:

```bash
.venv/bin/python3 -m pytest tests/ -q

make build-dataset build-mentions tag-codes summarize sample-readiness stats synth
make build-ftas stats-official synth-official
make sem-ftas nudge-ranking
make hokuriku-did-event-study
make data-manifest
```

Expected regenerated artifacts:

- `output/statistical_summary.md`
- `output/statistical_results.json`
- `output/review_sample_readiness.md`
- `output/official_fukui/statistical_summary_official.md`
- `output/official_fukui/statistical_results_official.json`
- `output/sem/`
- `output/hokuriku_merged/did_event_study_report.md`
- `output/hokuriku_merged/did_thesis_estimates.csv`
- `output/data_manifest.md`
- `output/data_manifest.json`

The Google-review builders stamp a run-date field into regenerated row-level
CSVs. Date-only churn in `collection_date` is expected and is not a substantive
result change.

## Network, Credentials, and Paid Services

The primary reproduction path above requires no network calls after the Git
checkout and `git lfs pull`.

Network or credentialed targets are data-refresh targets, not the required
reviewer reproduction path:

- `make fetch-fukui-data`, `make fetch-comparison-data`, and
  `make fetch-metadata` require `GOOGLE_API_KEY`.
- `make fetch-google-maps-reviews` requires `OUTSCRAPER_API_KEY` and can incur
  API cost.
- `make fetch-estat` requires `ESTAT_APP_ID`.
- `make fetch-official-fukui`, `make fetch-hokuriku-merged`, and
  `make fetch-national-direct` fetch public upstream files, but those upstreams
  can drift over time.

Use the fetch targets only when intentionally moving to a newer data vintage.
For manuscript review, prefer the pinned inputs already tracked in Git or Git
LFS.

## Data Availability and Restrictions

Public and pinned inputs:

- Code for Fukui / FTAS official survey data: upstream public repositories
  listed in `docs/data_reproducibility.md`; thesis vintage is pinned through
  tracked raw/derived files in Git LFS.
- Hokuriku merged survey microdata: upstream public repository listed in
  `docs/data_reproducibility.md`; thesis vintage is pinned through Git LFS.
- Google review checkpoints: tracked cache files under `output/checkpoints/`
  with pseudonymized reviewer handles and stripped author URLs.
- National supplementary data: source list in `config/national_data_sources.yaml`;
  analysis panel tracked at `output/national_stats/accommodation_panel.csv`.

Restricted or local-only materials:

- `.env` and `.env.refs` are local credential material and must not be shared
  as manuscript supplements.
- Row-level review/comment files containing display names, review text,
  sentence excerpts, and manual validation samples are gitignored when they
  would expose unnecessary person-level text. Regenerate them locally from the
  pinned checkpoints when needed for audit.
- Presentation workspaces under `outputs/` are local working products, not
  source data.

The manuscript should describe those restrictions directly in the Data
Availability statement instead of implying that all local intermediate files
are public.

## Code Availability Statement

Suggested manuscript text:

> Analysis code, configuration files, tests, and reproducibility documentation
> are available in the project repository. The repository includes pinned
> Python dependencies (`requirements.lock.txt`), Makefile targets for each
> analysis stage, CI tests, source manifests, and data-provenance notes.
> Public official-data inputs used for the thesis results are pinned through
> Git LFS where upstream datasets are living sources. Google-review checkpoints
> are retained as pseudonymized cache files; row-level text outputs and
> credential files are excluded from public release for privacy and API-key
> reasons. The documented no-network reproduction path is:
> `git lfs pull`, install `requirements.lock.txt`, run tests, and execute the
> Makefile targets listed in `docs/reproducibility_checklist.md`.

Before journal submission, replace "project repository" with the public URL
and add a DOI after archiving a release on Zenodo, Figshare, OSF, or another
DOI-minting repository.

## Reviewer Checklist

| Requirement | Status | Evidence |
| --- | --- | --- |
| Statement of need | Present | Top-level `README.md`, `CONTEXT.md`, `docs/results_overview.md` |
| Installation instructions | Present | `README.md` setup section, this checklist |
| Pinned dependencies | Present | `requirements.lock.txt` |
| Automated execution | Present | `Makefile` targets |
| Tests | Present | `tests/`, `.github/workflows/tests.yml`, `make test` |
| Data provenance | Present | `docs/data_reproducibility.md`, `docs/source_ledger.md`, `output/data_manifest.*` |
| Rebuild path for reported results | Present | `README.md`, this checklist, `docs/source_ledger.md` |
| Living upstream data handled | Present | Pinned vintages documented in `docs/data_reproducibility.md` |
| Privacy/access restrictions stated | Present | `README.md`, `docs/data_reproducibility.md`, this checklist |
| License file | Missing | Add an OSI-approved `LICENSE` before public journal/software submission |
| Release DOI | Missing | Archive the exact submission commit/release before manuscript submission |
| Contribution/support guidelines | Optional gap | Useful for software-journal submission; less critical for a thesis code supplement |

## Submission Readiness Assessment

The repository is now adequate for an academic research code supplement if the
submission goal is to let reviewers rerun and audit the thesis analyses from
pinned inputs.

Two items should still be completed before a public journal or software-journal
submission:

1. Add an explicit `LICENSE` file. JOSS treats this as required, and most
   journals expect reuse rights to be unambiguous.
2. Archive the exact submission commit in a DOI-minting repository and cite
   that DOI in the manuscript code-availability statement.
