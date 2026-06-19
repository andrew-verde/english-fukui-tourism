# Statistical Claim Registry

Generated: 2026-06-19T14:57:38.354391+00:00
Publication ready: False
Gold-set status: gold-set coder sheets exist, but tagger_evaluation.csv is missing

| Claim | Status | Unit | Denominator | Command |
|---|---|---|---|---|
| FTAS inference uses first response per respondent | verified | one survey respondent | deduplicated respondent rows | `make stats-official` |
| Reported inconvenience is associated with lower satisfaction and NPS | verified | one survey respondent | all respondents with nonmissing outcome values | `make stats-official` |
| Fukui/Ishikawa friction-code comparisons use text-writer denominator | provisional_pending_gold_set | one survey respondent with free text | respondents with non-empty friction_source_text | `make stats-official` |
| FTAS SEM supports friction -> satisfaction -> intention mechanism | verified | one deduplicated survey respondent | deduplicated respondents with complete SEM indicators | `make sem-ftas` |
| Transport/access is the top evidence-weighted nudge priority | provisional_pending_gold_set | one friction reporter with free text | friction reporters with free text | `make sem-ftas nudge-ranking` |
| Shinkansen shock raised Fukui NPS relative to control prefectures | verified | one survey respondent | survey respondents with outcome in DiD model | `make hokuriku-did-event-study` |
| Shinkansen shock raised Fukui transport satisfaction relative to controls | verified | one survey respondent | survey respondents with outcome in DiD model | `make hokuriku-did-event-study` |

## Caveats
- official_ftas_dedup_sample: Rows without respondent_id cannot be proven duplicates and are kept.
- reported_inconvenience_satisfaction_intention: Reported inconvenience is observational, not randomized.
- official_fukui_ishikawa_text_writer_friction: Text-response rates differ by instrument; all-respondent friction rates are not comparable.
- official_fukui_ishikawa_text_writer_friction: Japanese friction tags are keyword-derived and still await native-speaker gold-set review. Treat tag-dependent FTAS/Ishikawa code rankings, SEM Stage 2 paths, and nudge priorities as provisional until `make gold-set-eval` produces precision/recall evidence.
- ftas_sem_friction_satisfaction_intention: SEM is observational; causal interpretation depends on modeling assumptions.
- nudge_priority_transport_access: Japanese friction tags are keyword-derived and still await native-speaker gold-set review. Treat tag-dependent FTAS/Ishikawa code rankings, SEM Stage 2 paths, and nudge priorities as provisional until `make gold-set-eval` produces precision/recall evidence.
- hokuriku_did_nps: Parallel-trends and shock-exogeneity assumptions must be argued in text.
- hokuriku_did_transport_satisfaction: Parallel-trends and shock-exogeneity assumptions must be argued in text.
