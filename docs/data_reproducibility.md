# Data Reproducibility

## Pinned official inputs

Thesis-critical official microdata is tracked with Git LFS:

- `output/official_fukui/raw/ftas_survey_all.csv`
- `output/official_fukui/raw/ishikawa_survey_*.csv`
- `output/hokuriku_merged/raw/merged_survey_*.csv`

Source manifests record upstream URLs, vintages, and hashes:

- `output/official_fukui/source_manifest.json`
- `output/hokuriku_merged/source_manifest.json`
- `output/national_stats/direct_manifest.json`
- `output/national_stats/estat/estat_manifest.json`

## Regeneration

```bash
make build-ftas
make stats-official
make synth-official
make sem-ftas
make nudge-ranking
make hokuriku-did-event-study
make accommodation-panel
make data-manifest
```

Network fetches are intentionally separate:

```bash
make fetch-official-fukui
make fetch-hokuriku-merged
make fetch-national-direct
make fetch-estat
```

Fresh upstream fetches can differ from pinned thesis vintages. Never overwrite
pinned inputs without reviewing source manifests and resulting estimate diffs.

`output/data_manifest.json` records aggregate row counts, schemas, byte sizes,
and SHA256 values for maintained analytical datasets.
