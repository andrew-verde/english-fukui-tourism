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

**FTAS vintage pin:** every FTAS-derived row below (dedup counts, inconvenience
rate, SEM, nudge ranking, prefecture comparisons) reflects the pinned
2026-06-30 upstream commits (97,866 Fukui rows). Upstream Code4Fukui data is
living; exact commits, checksums, recreation, and drift rules are in
`docs/data_reproducibility.md` → "Pinned FTAS vintage".

## Primary thesis analyses

| Number | Claim | Status | Command | Script | Input | Output artifact |
|---|---|---|---|---|---|---|
| DiD NPS +0.55 (robust +0.65) | Shinkansen extension raised Fukui NPS vs Ishikawa | verified | `make hokuriku-did-event-study` | `scripts/hokuriku_did_event_study.py` | `output/hokuriku_merged/raw/` (merged tri-prefecture microdata, CC-BY) | `output/hokuriku_merged/did_thesis_estimates.csv`, `did_event_study_report.md` |
| DiD transport satisfaction +0.055 (robust +0.077) | Transport satisfaction rose post-extension | verified | `make hokuriku-did-event-study` | `scripts/hokuriku_did_event_study.py` | same | same |
| DiD revisit intention +0.04 | Fragile — not headlined | verified (fragile) | `make hokuriku-did-event-study` | `scripts/hokuriku_did_event_study.py` | same | same |
| SEM β = −0.21 / 0.80 / −0.06; ≈73% mediation | Friction → satisfaction → intention transmission | verified | `make sem-ftas` | `scripts/sem_ftas.py` | `output/official_fukui/ftas_tagged_survey.csv` (deduplicated respondents) | `output/sem/` |
| Nudge priorities 0.0200 / 0.0034 / 0.0017 | Transport/access dominates ~6× | verified | `make nudge-ranking` | `scripts/rank_nudge_priorities.py` | SEM stage-2 paths + prevalence | `output/sem/nudge_priority_ranking.md` |
| 97,866 rows ↔ 51,399 unique members | FTAS dedup justification | verified | `make stats-official` | `scripts/statistical_validation_official.py` | `output/official_fukui/ftas_survey_normalized.csv` | `output/official_fukui/` |
| reported_inconvenience rate 15.4% | True felt-inconvenience rate after recode | verified | `make stats-official` | `scripts/statistical_validation_official.py` | same | same |

## Supporting data

| Number | Claim | Status | Command | Script | Input | Output artifact |
|---|---|---|---|---|---|---|
| CN social layer: 105 XHS notes (Fukui), theme mix 65 ordinary / 22 fan / 18 travel | Chinese-language Xiaohongshu recommendation text, side-project only | verified (descriptive, side-project — never thesis evidence) | `make chinese-social` | `scripts/build_chinese_social_media_dataset.py` | `tourism-data/data/raw/social/fukui_xhs_reviews.csv` (colleague scrape, commit 6a38bee, 2026-06-12) + `data/processed/fukui_xhs_analysis.csv` (theme annotations) | `output/chinese_social_media_analysis/` — title-level text; friction tags directional only |
| JTA panel 4,512 rows; Fukui March stays 322,200 (2018) → 340,140 (2024) | Behavioral overnight-stay panel staged as companion DiD outcome; descriptive only until the event study runs on it | verified (descriptive) | `make fetch-national-direct` + `make accommodation-panel` | `scripts/build_accommodation_panel.py` | `output/national_stats/raw/jta_accommodation_*.xlsx` (JTA 宿泊旅行統計調査, MLIT) | `output/national_stats/accommodation_panel.csv`, `accommodation_panel_summary.md` — 2025 rows preliminary vintage; foreign series covers 10+ employee facilities only |
| Reservation inputs: Fukui Station 1,095 rows; Obama 1,071; Echizen Coast 698; Mikata-goko 523 | Checksum-gated locality reservation panels; Fukui Station and Obama span the 2024-03-16 event, while Echizen Coast and Mikata-goko are post-only | verified (dataset only; no effect estimate) | `python scripts/fetch_code4fukui_data.py` + `python scripts/build_reservation_panels.py` | `scripts/fetch_code4fukui_data.py`, `scripts/build_reservation_panels.py` | Four `latest_rsv_sum.csv` files pinned in `config/official_fukui_sources.yaml` | `output/official_fukui/raw/*_reservation.csv`; row/split oracles in `tests/test_reservation_panels.py` |
| Fukui Vision: FY2019→2025 favorable +4.5 pp; migration intention +3.0 pp | Aggregate resident-attitude trend; postal-to-web mode shift limits wave comparability and bars causal interpretation | verified (descriptive) | `make vision-descriptive` | `scripts/build_resident_vision.py` | `code4fukui/fukui-vision-data` commit `7eba2ff6ba50f73bb28e36554787882231007527` | `output/official_fukui/resident_vision_descriptive.md`, `resident_vision_stacked.png` |
| Fukui City synthetic-control post gap −0.0498 log points; 100-placebo p=0.8812 | No positive Fukui City effect detected against synthetic municipal donor pool in this specification; `人数` remains a mobile-derived estimate | estimated | `make fetch-japan-kanko-stat` + `make japan-kanko-panel` + `make synthetic-control` | `scripts/fetch_japan_kanko_stat.py`, `scripts/build_japan_kanko_panel.py`, `scripts/synthetic_control_fukui.py` | `code4fukui/japan-kanko-stat` commit `dfb906975b63adcaef20a3e7a35f2a10ab22ada5`, five pinned annual files | `output/national_stats/synthetic_control/report.md`, gap/weight/placebo CSVs and plots |

## Rules

1. New number in a report → add a row first.
2. Status changes → update the row in the same commit as the regenerated artifact.
3. `simulated/demo` rows must never appear in advisor-facing documents as
   empirical results; cite them only as pipeline demonstrations.
