# Official Fukui Data Statistical Summary

## Method Notes
- Official-data analysis is separate from the English-language Google Maps review analysis.
- Unit of analysis is one FTAS survey respondent unless a test is explicitly labeled as reservation/day context.
- English reviewer friction and Japanese tourist survey friction are compared descriptively because they come from different sampling frames and languages.
- Reviewer nationality is not inferred.

## Input Data Audit
- Status: PASS
- n (FTAS respondent rows): 95,422
- Response date range: 2022-04-28 00:06:15+00:00 to 2026-05-27 23:15:43+00:00
- Response areas: 119; municipalities: 17
- Rows with at least one Japanese friction code: 7888

## Official Friction vs Satisfaction
- overall_satisfaction_score: median friction=4.00, median no-friction=4.00, Mann-Whitney p=<0.001
- transport_satisfaction_score: median friction=4.00, median no-friction=4.00, Mann-Whitney p=<0.001
- nps: median friction=8.00, median no-friction=8.00, Mann-Whitney p=<0.001

## Hokuriku Shinkansen Event Context
- Event date: 2024-03-16
- FTAS Shinkansen-use rate before: 0.06016947021699228
- FTAS Shinkansen-use rate after: 0.14026954177897574
- Chi-square p=<0.001; Cramer's V=0.12778421019174954

## Reservation Demand Context
- n_people: median pre=869.0, median post=1016.0, p=0.003
- n_reserve: median pre=200.0, median post=238.0, p=<0.001
- amount_fee: median pre=20578199.0, median post=24208166.0, p=0.121

## Official Fukui vs Ishikawa Survey Comparison
- n: 121,064 respondent rows.
- Any friction rate: Fukui 8.27%; Ishikawa 12.85%; p=<0.001; V=0.06464419617744509
- waiting_crowding: Fukui 1.82%, Ishikawa 3.22%, p_BH=<0.001, V=0.040
- staff_communication: Fukui 0.14%, Ishikawa 0.58%, p_BH=<0.001, V=0.037
- cleanliness_comfort: Fukui 0.90%, Ishikawa 1.80%, p_BH=<0.001, V=0.035
- transport_access: Fukui 2.14%, Ishikawa 3.41%, p_BH=<0.001, V=0.034
- english_information_gap: Fukui 0.06%, Ishikawa 0.34%, p_BH=<0.001, V=0.032
- price_value: Fukui 0.29%, Ishikawa 0.58%, p_BH=<0.001, V=0.020

## Official Fukui vs Ishikawa Kanazawa-Area Survey Comparison
- Scope: all Fukui official survey rows compared with Ishikawa official survey rows where `survey_area_group` is `金沢`.
- n: 105,951 respondent rows.
- Any friction rate: Fukui 8.27%; Ishikawa Kanazawa-area 14.61%; p=<0.001; V=0.06657628210236785
- cleanliness_comfort: Fukui 0.90%, Ishikawa Kanazawa-area 2.91%, p_BH=<0.001, V=0.057
- staff_communication: Fukui 0.14%, Ishikawa Kanazawa-area 0.82%, p_BH=<0.001, V=0.044
- english_information_gap: Fukui 0.06%, Ishikawa Kanazawa-area 0.54%, p_BH=<0.001, V=0.043
- waiting_crowding: Fukui 1.82%, Ishikawa Kanazawa-area 3.74%, p_BH=<0.001, V=0.041
- price_value: Fukui 0.29%, Ishikawa Kanazawa-area 0.85%, p_BH=<0.001, V=0.028
- transport_access: Fukui 2.14%, Ishikawa Kanazawa-area 3.28%, p_BH=<0.001, V=0.023

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
