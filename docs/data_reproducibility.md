# Data Reproducibility Notes

This repository keeps public aggregate outputs and analysis code in Git, while
large raw/source-cache files are recreated from their upstream source or API.

## Official Code for Fukui / FTAS

Source of truth:

- <https://github.com/code4fukui/fukui-kanko-survey>
- <https://github.com/code4fukui/fukui-kanko-reservation>
- <https://github.com/code4fukui/ishikawa-kanko-survey>

Local raw copies live under `output/official_fukui/raw/` and are gitignored.
Run:

```bash
make fetch-official-fukui
make build-ftas
```

### Pinned FTAS vintage (committed thesis numbers)

The Code4Fukui repositories are **living datasets** — new survey responses are
appended continuously. All committed official-analysis artifacts
(`statistical_results_official.json`, `output/sem/`, the README data snapshot,
and the source-ledger rows) are pinned to the **2026-05-28 fetch vintage**:
95,422 Fukui respondent rows, 50,285 unique members after dedup, 121,064
combined Fukui + Ishikawa rows. The per-file SHA-256 hashes of that vintage are
recorded in the historical source manifest:

```bash
git show e1f8e31:output/official_fukui/source_manifest.json
```

A fresh `make fetch-official-fukui` downloads the **current** upstream vintage
and will NOT reproduce the committed artifacts byte-for-byte (checked
2026-06-13: 96,291 Fukui rows; per-code comparison showed no rate change above
10% and no BH-corrected significance flips, so conclusions hold — but the
numbers drift).

**The full pinned dataset is LFS-tracked in the current tree** — Fukui raw +
derived files, Ishikawa raw + derived files, and
`official_surveys_tagged_combined.csv`, every one hash-verified against the
committed source manifest. On any machine:

```bash
git clone … && git lfs pull
```

and `make stats-official`, `make sem-ftas`, and `make build-ftas` reproduce the
committed results with no fetch step (reproduction checks 2026-06-13:
identical up to last-decimal float noise).

**Rule:** never overwrite the committed official-analysis artifacts from a
fresh (newer-vintage) fetch unless the README data snapshot and the source
ledger are updated to the new vintage in the same commit.

`make build-ftas` regenerates:

- `output/official_fukui/ftas_survey_normalized.csv`
- `output/official_fukui/ftas_tagged_survey.csv`
- `output/official_fukui/ishikawa_survey_normalized.csv`
- `output/official_fukui/ishikawa_tagged_survey.csv`
- `output/official_fukui/official_surveys_tagged_combined.csv`

`make stats-official` intentionally fails if
`official_surveys_tagged_combined.csv` is missing, because otherwise the
Fukui-vs-Ishikawa comparison sections would be silently omitted.

## Google Review Checkpoints

The checkpoint JSONs (`output/checkpoints/google_{fukui,kanazawa,toyama}.json`,
`poi_metadata.json`, collection manifest) are **tracked in Git** with
pseudonymized reviewer handles (`Reviewer_XXXXXX`, author URLs stripped). They
are the irreplaceable collection cache: a fresh API pull costs money and
returns a *different* review sample, so these files are the pinned source of
the entire review layer.

Reproduction checks (2026-06-13): `make build-dataset` and
`make multilingual-reviews` regenerate the committed row-level CSVs from these
checkpoints exactly — the only diff is the `collection_date` column, which the
builders stamp with the run date. Treat `collection_date` churn in regenerated
CSVs as noise; do not commit it without reason.

Fresh API collection (only to *extend* the dataset, never to reproduce it):

```bash
make fetch-fukui-data
make fetch-comparison-data
make fetch-metadata
# deeper Outscraper path: set OUTSCRAPER_API_KEY, then
make fetch-google-maps-reviews
```

## Hokuriku Merged Survey Microdata

Source of truth:

- <https://github.com/hokuriku-inbound-kanko/opendata>

Local raw copies live under `output/hokuriku_merged/raw/` and are gitignored.
Run:

```bash
make fetch-hokuriku-merged
```

### Pinned Hokuriku vintage (committed DiD numbers)

This upstream is also a **living dataset** — the current-year file
(`merged_survey_2026.csv`) grows as responses arrive. The committed DiD
artifacts (`did_thesis_estimates.csv`, event-study outputs) and the committed
`output/hokuriku_merged/source_manifest.json` pin the **2026-06-11 fetch**
(per-file SHA-256 in the manifest). A fresh `make fetch-hokuriku-merged` pulls
the current upstream and will drift (checked 2026-06-13: +29–75 rows, estimate
movement in the 3rd decimal, headline numbers unchanged at reported precision).

**The pinned raw files are LFS-tracked in the current tree**
(`output/hokuriku_merged/raw/merged_survey_*.csv`, hash-verified against the
committed manifest; DiD reproduction check 2026-06-13: committed estimates
match to ~1e-13). `git lfs pull` is all a fresh machine needs — only run
`make fetch-hokuriku-merged` when you *intend* to move to a newer vintage.

Fallback if the LFS copy is ever lost: the pinned current-year file also lives
in upstream git history at commit `72c29d7818e31971d4c3525a2c673131f1d85e73`
(`https://raw.githubusercontent.com/hokuriku-inbound-kanko/opendata/<commit>/output_merge/merged_survey_2026.csv`);
verify sha256 against the committed manifest. The same rule applies as for
FTAS: never overwrite committed DiD artifacts from a newer-vintage fetch unless
the ledger and README are updated in the same commit.

Then run DiD outputs:

```bash
make hokuriku-did-audit
make hokuriku-did-event-study
```

## National Supplementary Data

The national raw directory contains refetchable public MLIT/JTA/JR West files
listed in `config/national_data_sources.yaml`. Local copies live under
`output/national_stats/raw/` and are gitignored. Run:

```bash
make fetch-national-direct
make accommodation-panel
```

The tracked `output/national_stats/accommodation_panel.csv` is the rebuilt
analysis panel, not the raw source archive.
