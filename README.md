# Fukui Tourism Friction Analysis

Research pipeline for a master's thesis on tourism friction in Fukui Prefecture after the 2024 Hokuriku Shinkansen extension.

**Thesis arc (see [docs/results_overview.md](docs/results_overview.md) for the current numbers):**

1. **Impact** — difference-in-differences / event study around the March 2024 Shinkansen extension (Fukui treated, Ishikawa control; merged tri-prefecture survey microdata, CC-BY).
2. **Mechanism** — two-stage SEM on deduplicated official FTAS respondents: friction → satisfaction → visit intention.
3. **Intervention** — evidence-weighted nudge priority ranking (SEM path × prevalence), delivered through the `experiments/nudge-pilot/` artifact.

Supporting evidence layers, all exploratory:

- English-language Google Maps reviews for Fukui, Kanazawa, and Toyama (collected through mid-2026; see `output/statistical_summary.md` for the audit date).
- Chinese-language Xiaohongshu and Douyin recommendation text, prepared as a parallel social-media layer once colleague CSV exports are populated.

The Likert pilot survey was retired as a data-collection path (ADR 0002); all quantitative claims rest on official open data. Design decisions live in `docs/adr/`, canonical terminology in `CONTEXT.md`.

---

## Pipeline Overview

```
Step 1a  pull.py                          Fetch Fukui Google Places seed checkpoints / place IDs
Step 1b  fetch_comparison_city_data.py    Fetch Kanazawa + Toyama seed checkpoints / place IDs
Step 1c  fetch_google_maps_reviews.py     Optional larger Outscraper Google Maps review pull
Step 1d  fetch_poi_metadata.py            Fetch POI types → poi_category
Step 2   build_analysis_dataset.py        Unified review schema + VADER
Step 3   build_mentions_dataset.py        Sentence-level mention splitting
Step 4   auto_tag_friction_codes.py       Keyword-based friction/nudge tagging
Step 5   generate_friction_summaries.py   Summary tables + plots
Step 6   audit_review_sample_readiness.py Sample adequacy / expected-count audit
Step 7   generate_presentation_figures.py Presentation figure files
Step 8   statistical_validation.py        Review-level SR statistical checks
Step 9   synthesis_pipeline.py            Statistical summary + test explanations
Side     build_chinese_social_media_dataset.py Chinese Xiaohongshu/Douyin scaffold
Side     build_gold_set.py                 Blind gold-set kit for friction-tagger evaluation
Side     evaluate_gold_set.py              Inter-rater kappa + tagger precision/recall/F1
Side     fetch_hokuriku_merged.py          Merged tri-prefecture survey microdata (CC-BY)
Side     hokuriku_did_audit.py             Shinkansen-extension DiD feasibility audit
Core     hokuriku_did_event_study.py       Thesis DiD: event study + robustness battery
Core     sem_ftas.py                       Two-stage SEM (CFA, Stage 1, Stage 2)
Core     rank_nudge_priorities.py          Evidence-weighted nudge priority ranking
```

Steps 2–9 require no API calls once checkpoints exist.

---

## Setup

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt

cp .env.example .env   # add your GOOGLE_API_KEY
```

**Required for legacy Google Places collection and metadata:**

```
GOOGLE_API_KEY=...              # Google Places API key
REVIEW_DATE_CUTOFF=2024-06-01   # (optional) drop reviews before this date
```

**Optional environment variable for deeper Google Maps review collection:**

```
OUTSCRAPER_API_KEY=...          # Outscraper Google Maps Reviews API key
GOOGLE_MAPS_DEEP_REVIEW_LIMIT=100
GOOGLE_MAPS_DEEP_QUERY_MODE=place-id-or-search
```

---

## Running the Pipeline

```bash
# Step 1: Data collection
make fetch-fukui-data          # fetch Fukui → output/checkpoints/google_fukui.json
make fetch-comparison-data     # fetch Kanazawa + Toyama comparison cities
make fetch-google-maps-reviews # optional deeper review pull for all three cities
make fetch-metadata            # fetch POI types → output/checkpoints/poi_metadata.json

# Steps 2–9: Analysis (no API keys needed)
make build-dataset             # → output/friction_analysis/reviews_unified.csv
make build-mentions            # → output/friction_analysis/mentions_dataset.csv
make tag-codes                 # → tagged_reviews.csv, tagged_mentions.csv
make summarize                 # → summary CSVs + 4 plots
make sample-readiness          # → review_sample_readiness.json/.md
make presentation-figures      # → local presentation figure files
make stats                     # → output/statistical_results.json
make synth                     # → output/statistical_summary.md + test explanations

# Or run everything in one command (assumes google_fukui.json already exists):
make friction-all

# Or run the deeper non-Places review workflow:
make deep-review-all

# Official Code for Fukui / FTAS parallel analysis:
make official-all

# Chinese Xiaohongshu / Douyin parallel layer:
make chinese-social

# Gold-set evaluation of the Japanese friction tagger:
make gold-set                  # → output/gold_set/ blind coder sheets + CODING_GUIDE.md
make gold-set-eval             # after coders fill the sheets: kappa + precision/recall

# Hokuriku merged survey + Shinkansen DiD groundwork:
make fetch-hokuriku-merged     # → output/hokuriku_merged/raw/ (gitignored, ~94 MB)
make hokuriku-did-audit        # → did_feasibility_report.md + parallel_trends.png

# Tests
make test
```

Design decisions for the statistical restructure (FTAS-based SEM, Shinkansen
difference-in-differences, gold-set tagger evaluation) are recorded in
`docs/adr/0001-ftas-sem-and-shinkansen-did-as-primary-contribution.md`;
canonical terminology lives in `CONTEXT.md`.

## Data Snapshot and Audit Trail

Current generated outputs use `REVIEW_DATE_CUTOFF=2024-06-01`.

- English review dataset: 915 rows after language/date filtering and city-text deduplication.
- Sentence-level mentions: 3,130 rows.
- Official FTAS dataset: 95,422 Fukui respondent rows.
- Combined official comparison dataset: 121,064 Fukui + Ishikawa respondent rows.

Reviewer nationality is not inferred from Google review data. Source labels should stay at the level the data supports: English-language reviews, Japanese-language reviews, or official Japanese tourist survey respondents.

The main method trail is:

- `output/statistical_summary.md`
- `output/statistical_test_explanations.md`
- `output/review_sample_readiness.md`
- `output/official_fukui/statistical_summary_official.md`
- `output/official_fukui/thesis_readiness_assessment.md`

Raw checkpoints, row-level review/comment files, reviewer names, full review text, manual validation samples, and presentation-generation workspaces under `outputs/` are gitignored. They can be regenerated locally from the scripts when credentials and cached sources are available.

---

## Focused Friction Analysis Workflow

### Analytical framing

This pipeline implements **descriptive content analysis** of English-language tourism reviews. Friction codes are derived from keyword co-occurrence in review sentences. Rates represent the proportion of sentences containing a matched keyword phrase — they are frequency counts, not validated sentiment scores or causal measurements.

### Deeper Google Maps review collection

Google Places Details is still supported, but it only returns a small review slice per POI. To collect a larger review sample without relying on that Places limit, use the Outscraper-backed Google Maps Reviews collector:

```bash
# Add OUTSCRAPER_API_KEY to .env first.
make fetch-google-maps-reviews

# Preview POI matching without an API key or network call:
.venv/bin/python3 scripts/fetch_google_maps_reviews.py --all --dry-run

# Or tune the collection size directly:
.venv/bin/python3 scripts/fetch_google_maps_reviews.py --all --reviews-limit 100

# Then run the complete deeper review workflow:
make deep-review-all
```

The script writes the same checkpoint files used by the rest of the pipeline, so the follow-up remains:

```bash
make build-dataset
make build-mentions
make tag-codes
make summarize
make sample-readiness
make stats
make synth
```

When earlier Google Places checkpoints already contain `place_id` values, the collector uses those IDs as the Outscraper query by default. This keeps POI matching stable while avoiding Places Details as the review source. A collection manifest is written to `output/checkpoints/google_maps_review_collection_manifest.json`.

With `REVIEW_DATE_CUTOFF` set, the collector sends Outscraper a `cutoff` timestamp. Outscraper treats cutoff requests as newest-first, so `--reviews-limit 100` means up to the 100 newest available text-bearing Google reviews for each POI within the configured cutoff window. It is not a popularity, helpfulness, controversy, rating, or review-length sample.

After rebuilding the dataset, run `make sample-readiness` before treating the larger dataset as inferentially stronger. It reports city-level review counts, source mix, POI coverage, city × theme expected-count diagnostics, and remaining gaps to the configured thresholds.

### Multilingual Cached-Review Analysis

To compare the English-review layer with Japanese and other detected review-language segments without making new API calls:

```bash
make multilingual-reviews
```

This reads the cached city checkpoints only, applies the same `REVIEW_DATE_CUTOFF` and same `(city, review_text)` deduplication rule as the English pipeline, detects the actual review text language with `langdetect`, and writes outputs to `output/multilingual_review_analysis/`.

Key outputs:

| File | Description |
|------|-------------|
| `reviews_multilingual.csv` | Generated locally; cached text-bearing reviews after cutoff/dedup, with detected language and language group (gitignored row-level data) |
| `language_summary_by_city.csv` | City × language-group review counts |
| `rating_summary_by_city_language_group.csv` | Rating summaries by city and language group |
| `tagged_reviews_multilingual.csv` | Generated locally; English and Japanese reviews tagged with mirrored friction-code labels (gitignored row-level data) |
| `japanese_reviews_tagged.csv` | Generated locally; Japanese detected-language subset with Japanese friction tags (gitignored row-level data) |
| `japanese_friction_by_city.csv` | Japanese review-level friction-code rates by city |
| `japanese_english_friction_comparison.csv` | Review-level English vs Japanese friction-code comparison with Fisher exact p-values |
| `japanese_review_friction_analysis.md` | Japanese friction summary with translated labels and comparison highlights |
| `non_english_non_japanese_reviews.csv` | Generated locally; detected-language segment that is neither English nor Japanese (gitignored row-level data) |
| `other_foreign_language_summary_by_city.csv` | City × detected-language counts for the non-English/non-Japanese segment |
| `multilingual_readiness.md` | Human-readable audit and caveats |

Interpret the non-English/non-Japanese segment as a review-language proxy, not confirmed foreign tourist origin. Review language is not reviewer nationality or residency. Japanese and English friction labels are mirrored, but keyword coverage is not a validated cross-language classifier.

Comparison across cities is observational. Observed differences in code rates indicate that certain friction themes appear more frequently in one city's reviews than another's; they do not imply that one city causes more friction, or that any intervention would produce a measurable outcome. All findings should be presented as candidate signals for further investigation.

### Chinese Social-Media Recommendation Text

To prepare Xiaohongshu and Douyin CSV exports from `/Users/andrewgreen/Repositories/tourism-data` for comparison with the Google-review layers:

```bash
make chinese-social
```

This target reads local CSV exports only and writes outputs to `output/chinese_social_media_analysis/`. The expected source schemas are the companion project's Xiaohongshu columns (`note_id,title,note_url,author,author_url`) and Douyin columns (`video_id,title,video_url,author`). Empty schema-only CSVs are accepted, so the framework can exist before the colleague data is populated.

Treat this as Chinese-language social-media recommendation text, not as reviewer nationality. The unit of analysis is one Xiaohongshu note row or Douyin video row, currently title/text-level. It is analogous to Google reviews only in its role as traveler-facing recommendation media; source behavior, text length, and platform ranking are different.

Key outputs:

| File | Description |
|------|-------------|
| `chinese_social_posts.csv` | Generated locally; normalized row-level title/text data (gitignored because it can contain author handles and source URLs) |
| `tagged_chinese_social_posts.csv` | Generated locally; row-level Chinese friction tags (gitignored) |
| `chinese_friction_by_city_platform.csv` | Aggregate city × platform × friction-code rates |
| `chinese_sentiment_by_city_platform.csv` | Aggregate keyword-polarity sentiment scaffold |
| `chinese_city_platform_friction_tests.csv` | Fisher exact comparisons across Chinese cities/platforms when populated |
| `chinese_vs_review_language_friction_comparison.csv` | Descriptive comparison against cached English/Japanese Google-review friction rates when available |
| `chinese_social_readiness.md` | Human-readable readiness and caveat report |

Chinese friction tags use `config/chinese_social_friction_codebook.yaml`, mirrored to the English/Japanese friction-code labels. Matching is substring-based and should be manually validated once real rows exist. Sentiment fields use a transparent Chinese keyword-polarity scaffold (`sentiment_score`, `sentiment_norm`, `emotional_intensity_score`) rather than VADER; do not treat them as a validated Chinese sentiment model.

### Assumptions

- Unit of analysis: **one review** (whole review) and **one mention** (sentence from a review)
- Language: English-language reviews only (langdetect filter, seed=0)
- Date filter: reviews published before `REVIEW_DATE_CUTOFF` are excluded (90-day post-Shinkansen settling period)
- Sample size depends on the active checkpoint source. The legacy Google Places path keeps up to 5 English reviews per POI; the current larger Outscraper path requests up to 100 reviews per POI. Current large-pull checkpoints contain 6,669 raw review records, and the current unified English analysis dataset contains 915 rows after filtering and deduplication with the `2024-06-01` cutoff.
- Friction coding is **heuristic and keyword-based** — designed for exploratory pilot analysis, not validated classification
- **Denominator: sentence-level mentions, not review-level.** Each review is split into sentences via `nltk.sent_tokenize`. Percentage rates divide matched-keyword sentences by total sentences for that city. This gives higher resolution for multi-issue reviews but produces low absolute rates per cell. Current city denominators are 664-1,694 sentences, so even a few matched sentences produce sub-1% rates in many cells. Interpret all friction-code counts directionally, not inferentially.
- `poi_category` is derived from Google Places `types` field via priority mapping (see `scripts/fetch_poi_metadata.py`)
- `primary_theme` is assigned by priority keyword matching (Dinosaur > Food > Scenic > Cultural > Logistics)

### Input Files

Raw checkpoint inputs are generated locally and intentionally gitignored because they can contain reviewer display names and full review text.

| File | Description |
|------|-------------|
| `output/checkpoints/google_fukui.json` | Cached Fukui review checkpoint, from legacy `pull.py` or the Outscraper large-review pull |
| `output/checkpoints/google_kanazawa.json` | Cached Kanazawa review checkpoint, from legacy `fetch_comparison_city_data.py` or the Outscraper large-review pull |
| `output/checkpoints/google_toyama.json` | Cached Toyama review checkpoint, from legacy `fetch_comparison_city_data.py` or the Outscraper large-review pull |
| `output/checkpoints/poi_metadata.json` | POI types + category (from `fetch_poi_metadata.py`) |
| `config/friction_codebook.yaml` | Editable friction/nudge keyword rules |
| `config/nudge_mapping.yaml` | Editable friction → intervention scaffold |

### Output Files

Aggregate outputs are tracked for public auditability. Row-level files containing review text, reviewer names, sentence excerpts, or official survey comment text are generated locally but intentionally gitignored.

All in `output/friction_analysis/`:

| File | Description |
|------|-------------|
| `reviews_unified.csv` | Generated locally; unified review-level dataset (gitignored because it contains review text and reviewer display names) |
| `mentions_dataset.csv` | Generated locally; sentence-level mentions linked to reviews (gitignored because it contains sentence text) |
| `tagged_reviews.csv` | Generated locally; reviews + bool column per friction/nudge code (gitignored because it contains review text and reviewer display names) |
| `tagged_mentions.csv` | Generated locally; mentions + bool column per friction/nudge code (gitignored because it contains sentence text) |
| `friction_by_city.csv` | Friction code frequency by city (count + %) |
| `friction_by_poi_category.csv` | Friction code frequency by POI category |
| `city_x_friction_crosstab.csv` | Pivot: city × friction code (raw counts) |
| `poi_category_x_friction_crosstab.csv` | Pivot: POI category × friction code |
| `top_excerpts_by_code.csv` | Generated locally; top 3 example sentences per friction code (gitignored because it contains sentence text) |
| `nudge_opportunity_table.csv` | Friction → intervention candidates + evidence counts |
| `fukui_frequency_comparison.csv` | Fukui mention rate vs baseline, delta, ratio |

Statistical outputs in `output/`:

| File | Description |
|------|-------------|
| `statistical_results.json` | Statistical validation payload |
| `statistical_summary.md` | Cite-ready statistical summary |
| `statistical_test_explanations.md` | Plain-language explanation of every statistical test |
| `review_sample_readiness.json` | Post-collection sample size and expected-count audit |
| `review_sample_readiness.md` | Human-readable sample readiness report |

Official Code for Fukui / FTAS outputs in `output/official_fukui/`:

| File | Description |
|------|-------------|
| `raw/*.csv` | Downloaded public Code for Fukui CSVs |
| `source_manifest.json` | Source URLs, fetch timestamp, byte counts, and SHA-256 hashes |
| `ftas_survey_normalized.csv` | Generated locally; normalized respondent-level FTAS survey dataset (gitignored row-level data) |
| `ftas_tagged_survey.csv` | Generated locally; FTAS rows tagged with Japanese friction codes mapped to the English codebook (gitignored row-level data) |
| `ishikawa_survey_normalized.csv` | Generated locally; normalized respondent-level Ishikawa official survey dataset (gitignored row-level data) |
| `ishikawa_tagged_survey.csv` | Generated locally; Ishikawa rows tagged with the same Japanese friction codes (gitignored row-level data) |
| `official_surveys_tagged_combined.csv` | Generated locally; harmonized Fukui + Ishikawa official survey rows for comparison tests (gitignored row-level data) |
| `ftas_friction_by_area.csv` | Official survey friction rates by tourism area |
| `ftas_friction_by_municipality.csv` | Official survey friction rates by municipality |
| `ftas_friction_by_transport_mode.csv` | Official survey friction rates by transport mode |
| `statistical_results_official.json` | Official-data statistical validation payload |
| `statistical_summary_official.md` | Cite-ready official-data summary |
| `english_vs_japanese_friction_comparison.csv` | Descriptive comparison of English-review and Japanese-survey friction rates |
| `official_prefecture_friction_comparison.csv` | Fukui vs Ishikawa official-survey friction tests |
| `thesis_readiness_assessment.md` | Defense-readiness assessment and remaining data gaps |
| `japanese_friction_validation_sample.csv` | Generated locally; manual validation sample for Japanese friction tag precision checks (gitignored because it contains source comment text) |

### Friction Code Categories

**Friction (12 codes):**
`transport_access`, `wayfinding_signage`, `english_information_gap`, `staff_communication`,
`booking_ticketing`, `waiting_crowding`, `price_value`, `cleanliness_comfort`,
`opening_hours_availability`, `itinerary_fit_time_cost`, `accessibility_mobility`, `food_amenities_gap`

**Nudge/positive (6 codes):**
`scenic_value`, `worthwhile_destination`, `friendly_service`, `underpromoted_feature`,
`easy_if_guided`, `good_for_itinerary_bundle`

Edit `config/friction_codebook.yaml` to modify keywords for any code.
Edit `config/nudge_mapping.yaml` to edit intervention candidates.

Keyword rules support a simple co-occurrence operator: `term1 && term2` requires both terms
to appear (negation-aware) somewhere in the same sentence.

### Limits of the Analysis

- **Exploratory English-review layer**: the current unified dataset has 915 English review rows after filtering and deduplication; shared-theme city tests meet expected-count checks, but mention-level friction counts are still sparse and not sufficient for strong friction-code inference
- **Very low absolute counts**: many friction codes still register only a few sentence matches per city, despite the larger pull; findings are directional signals only
- **Keyword heuristics**: friction codes are matched by keyword presence, not semantic understanding; false positives and missed mentions occur; negation handling is approximate
- **English-language only**: reviews from non-English-speaking visitors are excluded; findings reflect the English-language reviewer perspective only
- **No reviewer nationality**: Google review data does not expose reviewer nationality; reviewers are described as "English-language reviewers" not by country of origin
- **Timestamp coverage**: legacy Google Places checkpoints may only expose relative review dates, while Outscraper checkpoints include normalized timestamps when available. Some timestamps can still be missing or unparseable, so event-timing claims remain limited.
- **poi_category**: derived from Google Places `types` field via priority mapping; may not perfectly reflect visitor experience
- **POI-category breakdown**: counts are too sparse for strong claims by POI type; use `friction_by_poi_category.csv` only for exploratory reference.

---

## Project Structure

```
scripts/
  pull.py                           Fetch Fukui Google Places seed data / place IDs
  fetch_comparison_city_data.py     Fetch Kanazawa + Toyama seed data / place IDs
  fetch_google_maps_reviews.py      Fetch deeper Google Maps reviews via Outscraper
  fetch_poi_metadata.py             Fetch POI types from Places Details API
  fetch_code4fukui_data.py          Fetch official Code for Fukui CSVs
  build_analysis_dataset.py         Build reviews_unified.csv
  audit_review_sample_readiness.py  Audit post-collection sample adequacy
  build_multilingual_review_dataset.py Build cached review-language comparison suite
  build_chinese_social_media_dataset.py Build Chinese Xiaohongshu/Douyin analysis scaffold
  build_ftas_survey_dataset.py      Build official FTAS survey dataset
  build_mentions_dataset.py         Build mentions_dataset.csv
  auto_tag_friction_codes.py        Apply friction codebook
  generate_friction_summaries.py    Generate summary tables + plots
  generate_presentation_figures.py  Generate presentation figure files
  statistical_validation.py         Run English-review SR statistical validation
  synthesis_pipeline.py             Generate English-review statistical summaries
  statistical_validation_official.py Run official FTAS statistical validation
  synthesis_official_pipeline.py    Generate official-data summary
  build_gold_set.py                 Build blind gold-set coder sheets + answer key
  evaluate_gold_set.py              Score gold set: Cohen's kappa, tagger P/R/F1
  fetch_hokuriku_merged.py          Fetch merged Hokuriku survey microdata (CC-BY)
  hokuriku_did_audit.py             Shinkansen DiD feasibility audit + trends plot

src/
  scrapers/
    google_maps_scraper.py      Google Places API wrapper
  analysis/
    topic_modeling.py           assign_primary_theme() keyword taxonomy
  friction/
    mention_splitter.py         nltk sentence splitter
    tagger.py                   Codebook loader + multi-label negation-aware tagger
  official_fukui/
    ftas.py                     FTAS normalization + Japanese friction tagging
  utils/
    filters.py                  language_filter()
    logger.py                   setup_logger()

config/
  friction_codebook.yaml        Editable keyword rules (12 friction + 6 nudge)
  chinese_social_friction_codebook.yaml Chinese social-media friction rules mapped to the shared codes
  official_fukui_sources.yaml   Code for Fukui source URLs
  official_japanese_friction_codebook.yaml Japanese friction rules mapped to English codes
  nudge_mapping.yaml            Friction → intervention candidates

output/
  checkpoints/                  Raw API data (JSON, cached; gitignored)
  friction_analysis/            Aggregate analysis outputs (CSV + PNG)

tests/
  test_friction_tagger.py       Unit tests for schema, splitter, tagger
```

---

## License

Academic research — Fukui Prefecture tourism analysis.
