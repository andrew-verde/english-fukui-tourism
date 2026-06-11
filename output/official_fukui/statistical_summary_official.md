# Official Fukui Data Statistical Summary

## Method Notes
- Official-data analysis is separate from the English-language Google Maps review analysis.
- Unit of analysis is one survey respondent; repeat responses by the same member ID are deduplicated to the first response (see method_notes.respondent_dedup in the JSON).
- Friction-tag comparisons condition on respondents who wrote free text. Text-response rates differ by instrument (Fukui ~42% vs Ishikawa ~100%), so all-respondent friction rates are not comparable across prefectures.
- English reviewer friction and Japanese tourist survey friction are compared descriptively because they come from different sampling frames and languages.
- Reviewer nationality is not inferred.
- Sample sizes are large; emphasize effect sizes (rank-biserial r, Cramér's V) over p-values.

## Input Data Audit
- Status: PASS
- n (FTAS respondent rows): 50,285
- Response date range: 2022-04-28 00:06:15+00:00 to 2026-05-27 21:26:53+00:00
- Response areas: 118; municipalities: 17
- Rows with at least one Japanese friction code: 5155

## Official Friction vs Satisfaction
- Exposure: reported_inconvenience (reported_inconvenience_full_sample, n=50,285)
  - overall_satisfaction_score: mean friction=4.011 vs no-friction=4.331 (Δ=-0.320), rank-biserial r=-0.206, Mann-Whitney p=<0.001 — no_friction ranks higher than friction
  - transport_satisfaction_score: mean friction=3.944 vs no-friction=4.330 (Δ=-0.386), rank-biserial r=-0.210, Mann-Whitney p=<0.001 — no_friction ranks higher than friction
  - nps: mean friction=7.046 vs no-friction=7.871 (Δ=-0.825), rank-biserial r=-0.210, Mann-Whitney p=<0.001 — no_friction ranks higher than friction
- Exposure: any_friction (tagged_friction_among_text_writers, n=24,962)
  - overall_satisfaction_score: mean friction=4.083 vs no-friction=4.328 (Δ=-0.245), rank-biserial r=-0.162, Mann-Whitney p=<0.001 — no_friction ranks higher than friction
  - transport_satisfaction_score: mean friction=3.830 vs no-friction=4.314 (Δ=-0.484), rank-biserial r=-0.262, Mann-Whitney p=<0.001 — no_friction ranks higher than friction
  - nps: mean friction=7.503 vs no-friction=7.984 (Δ=-0.481), rank-biserial r=-0.138, Mann-Whitney p=<0.001 — no_friction ranks higher than friction

## Hokuriku Shinkansen Event Context
- Event date: 2024-03-16
- FTAS Shinkansen-use rate before: 0.08120944230226652
- FTAS Shinkansen-use rate after: 0.17754497208629128
- Chi-square p=<0.001; Cramer's V=0.13843531287188052

## Reservation Demand Context
- Caveat: The pre window is autumn/winter and the post window spring/summer, so this test confounds the Shinkansen opening with seasonality. Treat as descriptive context only; the Hokuriku DiD with a comparison prefecture supersedes it.
- n_people: median pre=869.0, median post=1016.0, p=0.003
- n_reserve: median pre=200.0, median post=238.0, p=<0.001
- amount_fee: median pre=20578199.0, median post=24208166.0, p=0.121

## Official Fukui vs Ishikawa Survey Comparison
- n: 75,927 respondent rows; friction rates conditioned on the 50,582 respondents with free text.
- Text-response rates: Fukui 49.64%, Ishikawa 99.91% (instrument difference; motivates the text-writer denominator).
- Any friction rate (among text-writers): Fukui 20.65%; Ishikawa 12.86%; p=<0.001; V=0.104
- opening_hours_availability: Fukui 2.63%, Ishikawa 1.18%, p_BH=<0.001, V=0.053
- food_amenities_gap: Fukui 1.75%, Ishikawa 0.61%, p_BH=<0.001, V=0.053
- transport_access: Fukui 5.46%, Ishikawa 3.41%, p_BH=<0.001, V=0.050
- accessibility_mobility: Fukui 2.66%, Ishikawa 1.35%, p_BH=<0.001, V=0.047
- wayfinding_signage: Fukui 1.69%, Ishikawa 0.68%, p_BH=<0.001, V=0.046
- waiting_crowding: Fukui 4.70%, Ishikawa 3.22%, p_BH=<0.001, V=0.038

## Official Fukui vs Ishikawa Kanazawa-Area Survey Comparison
- Scope: all Fukui official survey rows compared with Ishikawa official survey rows where `survey_area_group` is `金沢`.
- n: 60,814 respondent rows.
- Any friction rate (among text-writers, n=35,484): Fukui 20.65%; Ishikawa Kanazawa-area 14.62%; p=<0.001; V=0.070
- food_amenities_gap: Fukui 1.75%, Ishikawa Kanazawa-area 0.29%, p_BH=<0.001, V=0.058
- transport_access: Fukui 5.46%, Ishikawa Kanazawa-area 3.28%, p_BH=<0.001, V=0.046
- opening_hours_availability: Fukui 2.63%, Ishikawa Kanazawa-area 1.20%, p_BH=<0.001, V=0.044
- accessibility_mobility: Fukui 2.66%, Ishikawa Kanazawa-area 1.28%, p_BH=<0.001, V=0.042
- english_information_gap: Fukui 0.18%, Ishikawa Kanazawa-area 0.54%, p_BH=<0.001, V=0.030
- wayfinding_signage: Fukui 1.69%, Ishikawa Kanazawa-area 1.00%, p_BH=<0.001, V=0.026

## English Review vs Japanese Survey Friction
- Denominators differ: English Google rates use sentence-level mentions; FTAS rates use respondent rows.
- Transport / Access: English Fukui 8 (1.00% of sentences); FTAS 2042 (2.14% of respondents)
- Waiting / Crowding: English Fukui 0 (0.00% of sentences); FTAS 1738 (1.82% of respondents)
- Opening Hours / Availability: English Fukui 10 (1.30% of sentences); FTAS 1058 (1.11% of respondents)
- Accessibility / Mobility: English Fukui 6 (0.80% of sentences); FTAS 1003 (1.05% of respondents)
- Cleanliness / Comfort: English Fukui 2 (0.30% of sentences); FTAS 859 (0.90% of respondents)
- Food / Amenities Gap: English Fukui 1 (0.10% of sentences); FTAS 644 (0.68% of respondents)
- Wayfinding / Signage: English Fukui 1 (0.10% of sentences); FTAS 624 (0.65% of respondents)
- Itinerary Fit / Time & Cost: English Fukui 7 (0.90% of sentences); FTAS 335 (0.35% of respondents)

## Area-Level Official Tests
- Tested top 12 FTAS areas by respondent count.
- See `output/official_fukui/statistical_results_official.json` for full area x friction contingency tables and BH-adjusted p-values.

## Interpretation Guardrails
- Treat FTAS as official Japanese tourist survey evidence, not evidence about English-language reviewers.
- Treat Google review friction as a qualitative/observational signal with sparse counts.
- Strong thesis claim: official FTAS survey responses identify statistically associated friction, satisfaction, transport, and event-context patterns.
- Moderate thesis claim: English-language review friction can be triangulated against official Japanese tourist survey friction where the code definitions overlap.
