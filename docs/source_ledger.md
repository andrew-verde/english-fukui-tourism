# Source Ledger — every reported number, traced

One row per headline number used in the thesis, slides, or advisor reports.
A number may not appear in any outward-facing document unless it has a row
here. Status vocabulary (use exactly these labels in reports too):

- **verified** — regenerated from real data by the listed command; artifact on disk.
- **simulated/demo** — produced from placeholder or scaffold data; never cite as a finding.
- **estimated** — derived or extrapolated; assumptions stated in the linked artifact.
- **hypothesis** — stated expectation, no supporting computation yet.

Generation dates and dataset hashes live in `output/data_manifest.json`
(`make data-manifest`) — regenerate it after any pipeline run rather than
hand-editing dates here.

## Primary thesis analyses

| Number | Claim | Status | Command | Script | Input | Output artifact |
|---|---|---|---|---|---|---|
| DiD NPS +0.55 (robust +0.65) | Shinkansen extension raised Fukui NPS vs Ishikawa | verified | `make hokuriku-did-event-study` | `scripts/hokuriku_did_event_study.py` | `output/hokuriku_merged/raw/` (merged tri-prefecture microdata, CC-BY) | `output/hokuriku_merged/did_thesis_estimates.csv`, `did_event_study_report.md` |
| DiD transport satisfaction +0.05 | Transport satisfaction rose post-extension | verified | `make hokuriku-did-event-study` | `scripts/hokuriku_did_event_study.py` | same | same |
| DiD revisit intention +0.04 | Fragile — not headlined | verified (fragile) | `make hokuriku-did-event-study` | `scripts/hokuriku_did_event_study.py` | same | same |
| SEM β = −0.21 / 0.80 / −0.06; ~72% mediation | Friction → satisfaction → intention transmission | verified | `make sem-ftas` | `scripts/sem_ftas.py` | `output/official_fukui/ftas_tagged_survey.csv` (deduplicated respondents) | `output/sem/` |
| Nudge priorities 0.0202 / 0.0036 / 0.0013 | Transport/access dominates ~6× | verified | `make nudge-ranking` | `scripts/rank_nudge_priorities.py` | SEM stage-2 paths + prevalence | `output/sem/nudge_priority_ranking.md` |
| 95,422 rows ↔ 50,285 unique members | FTAS dedup justification | verified | `make stats-official` | `scripts/statistical_validation_official.py` | `output/official_fukui/ftas_survey_normalized.csv` | `output/official_fukui/` |
| reported_inconvenience rate 13.6% | True felt-inconvenience rate after recode | verified | `make stats-official` | `scripts/statistical_validation_official.py` | same | same |

## Supporting layers

| Number | Claim | Status | Command | Script | Input | Output artifact |
|---|---|---|---|---|---|---|
| n=915 English reviews; SR-01/02/05 results | Exploratory inbound-perception signal | verified (exploratory) | `make stats` + `make synth` | `scripts/statistical_validation.py`, `synthesis_pipeline.py` | `output/checkpoints/google_*.json` | `output/statistical_summary.md` |
| Gold-set κ / precision / recall | Tagger validity | hypothesis (awaiting coders) | `make gold-set-eval` | `scripts/evaluate_gold_set.py` | `output/gold_set/` coder sheets | pending |
| Chinese social media figures | Xiaohongshu/Douyin scaffold | simulated/demo (schema-first, currently 0 rows) | `make chinese-social` | `scripts/build_chinese_social_media_dataset.py` | companion-project CSV exports (none loaded yet) | `output/chinese_social_media_analysis/` — do not cite as findings until real exports loaded |
| JTA panel 4,512 rows; Fukui March stays 322,200 (2018) → 340,140 (2024) | Behavioral overnight-stay panel staged as companion DiD outcome; descriptive only until the event study runs on it | verified (descriptive) | `make fetch-national-direct` + `make accommodation-panel` | `scripts/build_accommodation_panel.py` | `output/national_stats/raw/jta_accommodation_*.xlsx` (JTA 宿泊旅行統計調査, MLIT) | `output/national_stats/accommodation_panel.csv`, `accommodation_panel_summary.md` — 2025 rows preliminary vintage; foreign series covers 10+ employee facilities only |

## Rules

1. New number in a report → add a row first.
2. Status changes (e.g. gold set scored) → update the row in the same commit
   as the regenerated artifact.
3. `simulated/demo` rows must never appear in advisor-facing documents as
   empirical results; cite them only as pipeline demonstrations.
