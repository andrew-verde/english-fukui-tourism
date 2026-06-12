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
