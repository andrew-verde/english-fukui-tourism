# Methods Appendix

## Official survey normalization

`scripts/build_ftas_survey_dataset.py` normalizes Fukui FTAS and Ishikawa
survey schemas, preserves source fields, deduplicates respondents under the
documented ID/time rule, and applies Japanese friction codes.

Unit: respondent after deduplication. Text-tag rates use eligible free-text
respondents as denominator; structured-response rates use their documented
eligible population.

## Official statistical validation

`scripts/statistical_validation_official.py` runs respondent-level prevalence,
prefecture comparisons, satisfaction associations, and multiplicity
corrections. Outputs:

- `output/official_fukui/statistical_results_official.json`
- `output/official_fukui/statistical_summary_official.md`

Effect sizes and adjusted p-values accompany inferential claims.

## Structural equation model

`scripts/sem_ftas.py` fits:

1. measurement/CFA stage;
2. friction → satisfaction;
3. satisfaction → future visit intention.

Outputs include fit indices, path estimates, and friction prevalence under
`output/sem/`.

## Shinkansen impact analysis

`scripts/hokuriku_did_event_study.py` estimates event-time and robustness
specifications around March 2024 using merged official Hokuriku survey data.
Interpretation depends on pre-trend diagnostics and stated comparison groups.

## Intervention ranking

`scripts/rank_nudge_priorities.py` combines mechanism strength with official
friction prevalence. Ranking is evidence prioritization, not a causal estimate
of intervention efficacy.

## Shared friction tagging

`src/friction/` and `config/official_japanese_friction_codebook.yaml` implement
reproducible multi-label tagging. Keyword tags are measured indicators; manual
audit and codebook limitations must remain visible.
