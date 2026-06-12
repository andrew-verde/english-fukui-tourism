# Code for Fukui Data Integration Plan

> **Status: superseded (2026-06-12).** Kept as a historical record of the
> 2026-05-28 planning state. The implementation path (items 1–5) and Section A
> were executed and now live in the `official-all` pipeline. Section C's
> interrupted-time-series design was superseded by the stronger Shinkansen
> difference-in-differences event study (`make hokuriku-did-event-study`,
> see `docs/results_overview.md` §1), enabled by merged tri-prefecture
> microdata unavailable when this was written. Sections B and D were dropped
> when the English-review layer was descoped to side-project status (June
> 2026 restructure): both are ecological and underpowered at n=81 Fukui
> reviews. The plan's framing of FTAS as "triangulation/context" is inverted
> relative to the current thesis, where FTAS SEM + DiD are the primary
> analyses. The "Thesis-Safe Interpretation" constraints remain in force via
> `CONTEXT.md` and `docs/methods_appendix.md`.

This note identifies Code for Fukui datasets that can extend the English-language Google review analysis. The goal is to add official context without changing the current thesis constraints: reviewers are English-language reviewers, not assumed to be American or North American; review-level tests remain one review per row; friction summaries remain sentence-level.

## Best Sources

### 1. FTAS Fukui Tourism Survey

Source: <https://github.com/code4fukui/fukui-kanko-survey>

Direct CSVs:

- `https://code4fukui.github.io/fukui-kanko-survey/all.csv`
- `https://code4fukui.github.io/fukui-kanko-survey/all-cnt.csv`
- `https://code4fukui.github.io/fukui-kanko-survey/area.csv`

Observed schema and size on 2026-05-28:

- `all.csv`: 95,422 respondent rows, 92 columns.
- `all-cnt.csv`: 1,491 daily count rows, 2022-04-01 through 2026-05-27, total count 95,422.
- `area.csv`: 98 tourism areas with municipality, Japanese area name, description, latitude, and longitude.

Useful fields in `all.csv`:

- Respondent context: `年代`, `都道府県`, `会員市町村`, `同行者`.
- Visit context: `回答日時`, `回答月`, `回答エリア`, `市町村`, `宿泊数（全体）`, `宿泊数（県内）`, `エリア訪問回数`.
- Visit purpose flags: food, nature, historic sites, theme parks/museums, shopping, events, outdoors, walking, experiences, driving.
- Information source flags: DMO website, internet/apps, Twitter, Instagram, Facebook, blogs, friends, tourist offices, local people, lodging.
- Transport fields: `福井県までの交通手段ALL`, `自家用車`, `レンタカー`, `新幹線`, `在来線`, `飛行機`, `旅行会社ツアーバス`, `福井県内での交通手段ALL`, `タクシー`, `路線バス`, `徒歩`, `レンタサイクル`.
- Outcomes: `福井県内での交通手段の満足度`, `福井県内での交通手段の満足度の理由`, `満足度`, `満足度の理由`, `不便さ`, `不便さの内容`, `NPS`, `今後の来訪意向`.

Best use: this is the highest-value dataset. It can support statistically powered official-survey analyses, then be compared with Google review findings at area/category level.

### 2. Fukui Tourism Reservation Data

Source: <https://github.com/code4fukui/fukui-kanko-reservation>

Direct CSVs:

- `https://code4fukui.github.io/fukui-kanko-reservation/latest_rsv_sum.csv`
- `https://code4fukui.github.io/fukui-kanko-reservation/latest_rsv_prefecture_sum.csv`
- `https://code4fukui.github.io/fukui-kanko-reservation/booking_curve.csv`

Observed schema and size on 2026-05-28:

- `latest_rsv_sum.csv`: 1,061 daily rows from 2023-10-01 through 2026-08-26; fields include `n_stay`, `n_people`, `n_room`, `amount_fee`, `n_reserve`.
- `latest_rsv_prefecture_sum.csv`: 32,272 date-prefecture rows from 2023-10-01 through 2026-08-25.
- `booking_curve.csv`: booking pace by target date and days-before-arrival columns.

Best use: day-level time-series validation around external events, especially the Hokuriku Shinkansen extension to Fukui on 2024-03-16. This should be treated as demand context, not review-level visitor behavior.

### 3. Japan Tourism Arrival Dashboard

Source: <https://github.com/code4fukui/japan-kanko-dashboard>

The repo describes monthly tourist-visitor data by prefecture and city, sourced from Digital Tourism Statistics Open Data / Japan Tourism Agency and consumed as CSV by the dashboard.

Best use: city-level baseline demand context for Fukui, Kanazawa, and Toyama. It can help normalize review volume or frame whether review activity is aligned with broader visitor trends. Avoid row-level clustering or causal claims.

### 4. People Flow Sensor Data

Source: <https://github.com/code4fukui/jinryu>

The repo stores historical people-flow sensor CSVs under `/data` and documents live/current data from the PUSH Open Data platform. It supports daily and hourly aggregations and, for AICAM views, age/gender breakdowns.

Best use: local congestion and seasonality context around sensor-covered areas. It is potentially useful for validating `waiting_crowding` and transport-load narratives, but only where sensor locations can be matched to tourism areas.

### 5. Open Traffic Data

Source: <https://github.com/code4fukui/opentraffic>

The repo wraps JARTIC open traffic feeds for five-minute and hourly traffic counts, with coordinates and road-type fields.

Best use: road-access pressure near car-dependent POIs. This is lower priority than FTAS because it is not tourism-specific and requires geospatial matching.

### 6. Dinosaur Open Data

Source: <https://github.com/code4fukui/dinosaur-opendata>

Direct CSVs:

- `https://code4fukui.github.io/dinosaur-opendata/latest_dino_sum.csv`
- `https://code4fukui.github.io/dinosaur-opendata/dinosaur-fukui.csv`

Observed schema and size on 2026-05-28:

- `latest_dino_sum.csv`: 61 future/near-current daily reservation rows from 2026-05-27 through 2026-07-26, with `n_people` and `amount_fee`.
- `dinosaur-fukui.csv`: 7 rows of Fukui dinosaur species metadata.

Best use: narrow dinosaur-theme context. Useful for a Dinosaur Museum case vignette, not for the main statistical analysis because the reservation window is short and does not overlap the current review cutoff period well.

## Recommended Analysis Additions

### A. Official Survey Replication of Friction Themes

Build a new official-survey dataset from FTAS:

- Input: `fukui-kanko-survey/all.csv`.
- Unit: one survey respondent.
- Translate or code Japanese free-text fields `不便さの内容`, `福井県内での交通手段の満足度の理由`, and `満足度の理由`.
- Apply a Japanese friction codebook mapped to the existing English codes: transport access, wayfinding/signage, information gap, staff communication, ticketing/booking, crowding, value, comfort, opening hours, itinerary fit, mobility, food/amenities.
- Output: `output/official_fukui/ftas_tagged_survey.csv`.

Statistical tests:

- Chi-square or Fisher/permutation tests: friction-code presence by tourism area category, municipality, transport mode, and visitor origin.
- Ordinal/logistic models: lower satisfaction or lower transport satisfaction as a function of friction-code presence, transport mode, overnight stay, visit purpose, and area fixed effects.
- Rank tests: NPS or satisfaction by transport mode and by area category.

Why this can produce significant findings:

- FTAS has 95,422 rows, far larger than the 251 Google review rows. Even after restricting to recent rows or non-empty comments, it should have enough power for inferential tests.

Caveat:

- This is a parallel official-survey analysis, not a direct extension of English-language reviewer behavior.

### B. Area-Level Triangulation With Google Reviews

Create an area bridge between current Fukui POIs and FTAS areas:

- Inputs: `output/friction_analysis/reviews_unified.csv`, `output/friction_analysis/tagged_reviews.csv`, `fukui-kanko-survey/area.csv`.
- Join method: curated alias table plus coordinates. Do not use blind string matching; English Google POI names and Japanese FTAS area names do not match reliably.
- Output: `config/fukui_area_crosswalk.csv` with columns:
  - `poi_name`
  - `place_id`
  - `ftas_parent_id`
  - `ftas_area_name`
  - `match_method`
  - `match_confidence`
  - `notes`

Area-level measures:

- Google: review count, mean sentiment, transport/accessibility/waiting friction rates, primary-theme distribution.
- FTAS: survey count, mean satisfaction, mean NPS, transport satisfaction distribution, inconvenience rate, transport-mode composition, visit-purpose composition.

Statistical tests:

- Spearman correlation between Google friction rate and FTAS inconvenience / transport dissatisfaction by matched area.
- Permutation test across matched areas because `n_area` will be small.
- Bootstrap confidence intervals for area-level correlations.

Expected value:

- This is good triangulation. It can show whether English-language review friction aligns with official Japanese survey dissatisfaction at the same tourism areas.

Caveat:

- This is ecological and likely underpowered because the current Fukui review sample has only 81 rows.

### C. Hokuriku Shinkansen Event Context

Use FTAS and reservation data around 2024-03-16:

- FTAS: compare transport-mode mix, transport satisfaction, and area distribution before/after 2024-03-16.
- Reservation: interrupted time series on `latest_rsv_sum.csv` for daily `n_people`, `n_reserve`, and `amount_fee`.
- Prefecture-origin reservation: compare Kanto-origin share before/after 2024-03-16 using `latest_rsv_prefecture_sum.csv`.

Statistical tests:

- Interrupted time-series regression with day-of-week, month/season, holidays if available, and linear time trend.
- Difference in proportions for `新幹線` usage in FTAS before/after the extension.
- Logistic regression: Shinkansen usage as outcome, post-extension indicator plus origin/area controls.

Expected value:

- This is the clearest path to statistically significant official-data results because it uses daily or respondent-level data around a known infrastructure event.

Caveat:

- Keep separate from SR-04 as currently defined. Review timestamps are unreliable for review-level event testing, but official FTAS/reservation timestamps are suitable for event-context analysis.

### D. Demand-Normalized Review Context

Use monthly official visitor data from `japan-kanko-dashboard` for Fukui, Kanazawa, and Toyama:

- Create city-month official visitor counts.
- Aggregate current Google reviews by city-month only if review timestamps are parseable and sufficiently dense.
- Report review volume per official visitors as descriptive context.

Statistical tests:

- Prefer descriptive normalization unless monthly review counts are large enough.
- If sufficient, use Poisson or negative-binomial models for review counts with official visitors as exposure.

Caveat:

- The current review sample is small, so this should not become a headline statistical result.

## Implementation Path

1. Add `scripts/fetch_code4fukui_data.py`.
   - Download official CSVs into `output/official_fukui/raw/`.
   - Record source URL, fetch date, row count, and hash in `output/official_fukui/source_manifest.json`.

2. Add `scripts/build_ftas_survey_dataset.py`.
   - Normalize Japanese column names to English snake-case.
   - Parse dates.
   - Convert satisfaction/NPS fields to ordered numeric variables.
   - Create binary columns for transport modes, visit purposes, info sources.

3. Add `config/fukui_area_crosswalk.csv`.
   - Start manually with high-confidence POIs:
     - Ichijodani Asakura Ruins -> 一乗谷朝倉氏遺跡 エリア.
     - Tojinbo Cliffs -> 東尋坊 エリア.
     - Maruoka Castle -> 丸岡城 エリア.
     - Yokokan Garden -> 名勝 養浩館庭園 エリア.
     - Fukui Dinosaur Museum -> likely 恐竜博物館 / Katsuyama area; verify in `area.csv`.
   - Add coordinates to the existing POI metadata if not already present.

4. Add `scripts/statistical_validation_official.py`.
   - Keep this separate from current SR tests.
   - Write `output/official_fukui/statistical_results_official.json`.
   - Include assumption audits and multiple-comparison correction.

5. Add synthesis.
   - Extend `scripts/synthesis_pipeline.py` or add `scripts/synthesis_official_pipeline.py`.
   - Write `output/official_fukui/statistical_summary_official.md`.
   - Explicitly label official-survey results as triangulation/context.

## Priority

1. FTAS survey respondent data.
2. FTAS area master and curated POI-area crosswalk.
3. Reservation time series for Shinkansen event context.
4. Japan tourism visitor counts for city-level demand context.
5. People-flow and open-traffic data only after the FTAS bridge is working.
6. Dinosaur open data only for a narrow Dinosaur Museum case study.

## Thesis-Safe Interpretation

Strong claim:

- Official FTAS survey responses identify which visitor segments, transport modes, or areas are statistically associated with lower satisfaction, NPS, inconvenience, or transport dissatisfaction.

Moderate claim:

- English-language Google review friction patterns can be triangulated against official FTAS area-level dissatisfaction signals where POI-area matches are reliable.

Avoid:

- Claiming reviewer nationality.
- Claiming causality from Google reviews.
- Treating aggregate visitor counts or spending as row-level features.
- Mixing review-level Google rows and respondent-level FTAS rows in the same inferential model.
