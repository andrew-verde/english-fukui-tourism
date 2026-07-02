# Data Reproducibility

## Pinned official inputs

Thesis-critical official microdata is **not committed**; it is re-materialized
from immutable commit-addressed upstream URLs and verified against the SHA-256
hashes recorded in the source manifests (`make fetch-official-fukui
fetch-hokuriku-merged`):

- `output/official_fukui/raw/ftas_survey_all.csv`
- `output/official_fukui/raw/ishikawa_survey_*.csv`
- `output/hokuriku_merged/raw/merged_survey_*.csv`

Source manifests record upstream URLs, vintages, and hashes:

- `output/official_fukui/source_manifest.json`
- `output/hokuriku_merged/source_manifest.json`
- `output/national_stats/direct_manifest.json`
- `output/national_stats/estat/estat_manifest.json`

`config/official_fukui_sources.yaml` is the lock file for Code4Fukui inputs.
Each entry contains the upstream repository, full Git commit, path at that
commit, and expected SHA256. The fetcher uses an immutable GitHub URL, verifies
content before replacing a local file, and records row counts plus verification
status in the manifest. A mutable branch or GitHub Pages URL is never a
thesis input.

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

## Updating a pinned vintage

1. Choose and record full upstream commit SHA.
2. Set `source_path` and SHA256 of file at that commit in source config.
3. Run `python scripts/fetch_code4fukui_data.py --force`.
4. Rebuild all dependent outputs and compare row counts, schemas, diagnostics,
   and estimates with prior vintage.
5. Commit lock config, source manifest, and reviewed analytical outputs
   together; re-stage the raw files locally via the fetch targets.

For publication, deposit final replication package in a durable research-data
repository (for example Zenodo, OSF, or an institutional repository), obtain a
DOI, and cite both original data creators and exact archived version. GitHub
forks may serve as mirrors; they are not archival identifiers.

Before public deposit, confirm upstream reuse license and document it in dataset
citation. “Open data” wording alone is not a license grant.

`output/data_manifest.json` records aggregate row counts, schemas, byte sizes,
and SHA256 values for maintained analytical datasets.
