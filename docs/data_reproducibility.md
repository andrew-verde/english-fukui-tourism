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

**You do not need the pinned dataset to read or cite the published analysis** —
the committed artifacts in Git are the citable results on every machine.
The pinned data is needed only to *re-run* the official-data analyses and
match the committed numbers exactly. To recover it on any clone (requires
`git-lfs`; the objects live in this repo's LFS history at commit `c828346`):

```bash
git lfs fetch origin c828346
for f in raw/ftas_survey_all ftas_survey_normalized ftas_tagged_survey; do
  git cat-file -p c828346:output/official_fukui/$f.csv \
    | git lfs smudge > output/official_fukui/$f.csv
done
```

The Ishikawa raw files of that vintage were never stored in this repo; they are
pinned by SHA-256 + URL in the historical manifest above. Recover a matching
copy from the code4fukui/ishikawa-kanko-survey git history (verify the hash),
then `make build-ftas` deterministically rebuilds
`official_surveys_tagged_combined.csv` from the pinned raws.

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

Local checkpoint JSON files live under `output/checkpoints/` and are gitignored
because they contain row-level review payloads and collection cache data.

Recreate them with API-backed collection:

```bash
make fetch-fukui-data
make fetch-comparison-data
make fetch-metadata
```

For the deeper Outscraper collection path, set `OUTSCRAPER_API_KEY` and run:

```bash
make fetch-google-maps-reviews
```

The downstream CSV analysis snapshots are tracked in Git, so the current
published analysis can be read without the checkpoints. Rebuilding those CSVs
from scratch requires the checkpoint cache or a fresh API collection.

## Hokuriku Merged Survey Microdata

Source of truth:

- <https://github.com/hokuriku-inbound-kanko/opendata>

Local raw copies live under `output/hokuriku_merged/raw/` and are gitignored.
Run:

```bash
make fetch-hokuriku-merged
```

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
