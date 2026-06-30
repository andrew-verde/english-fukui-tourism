# Fukui Tourism Official-Data Analysis

Reproducible research pipeline for a master's thesis on tourism friction in
Fukui Prefecture after the March 2024 Hokuriku Shinkansen extension.

## Research design

1. **Impact:** difference-in-differences and event study using merged
   Fukui/Ishikawa/Toyama official survey microdata.
2. **Mechanism:** two-stage SEM on deduplicated Fukui Tourism Area Survey
   (FTAS) respondents: friction → satisfaction → visit intention.
3. **Intervention:** evidence-weighted nudge priorities from SEM paths and
   official-survey friction prevalence.
4. **Behavioral context:** prefecture-month accommodation stays from the Japan
   Tourism Agency.

Official Japanese survey text is tagged with the shared friction package in
`src/friction/` and the Japanese codebook in
`config/official_japanese_friction_codebook.yaml`. Platform-review collection
and analysis are outside this repository.

Canonical terminology lives in `CONTEXT.md`; design decisions live in
`docs/adr/`.

## Setup

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.lock.txt
```

Optional credentials:

```bash
ESTAT_APP_ID=...  # only needed for e-Stat API discovery/fetching
```

Raw official datasets pinned for thesis reproduction are tracked with Git LFS.
Refetchable national-stat downloads remain ignored.
Code4Fukui inputs are locked by upstream commit and SHA256 in
`config/official_fukui_sources.yaml`; refreshes are explicit, reviewed changes.

## Main commands

```bash
make official-all                 # FTAS build, official tests, summary
make sem-ftas                     # two-stage SEM
make nudge-ranking                # evidence-weighted intervention ranking
make hokuriku-did-event-study     # thesis DiD/event-study battery
make accommodation-panel         # JTA prefecture-month stays panel
make result-charts                # official-data result charts
make data-manifest                # hashes, schemas, row counts
make reproduce-submission         # no-network verification path
make test                         # full maintained test suite
```

Fetch commands requiring network access:

```bash
make fetch-official-fukui
make fetch-hokuriku-merged
make fetch-national-direct
make fetch-estat
```

`make fetch-estat-list` performs e-Stat discovery only.

## Outputs

- `output/official_fukui/`: normalized/tagged official surveys and tests
- `output/sem/`: SEM estimates and nudge ranking
- `output/hokuriku_merged/`: DiD/event-study artifacts
- `output/national_stats/`: accommodation panel and source manifests
- `output/result_charts/`: official-data figures
- `output/data_manifest.{json,md}`: aggregate audit manifest

`experiments/nudge-pilot/` contains the standalone intervention prototype.
The Chinese social-media side analysis remains separate and exploratory; it
does not feed thesis claims or official-data models.

## Reproducibility

See:

- `docs/reproducibility_checklist.md`
- `docs/data_reproducibility.md`
- `docs/methods_appendix.md`
- `docs/source_ledger.md`
- `docs/results_overview.md`

Main quantitative claims derive only from official survey and accommodation
datasets.
