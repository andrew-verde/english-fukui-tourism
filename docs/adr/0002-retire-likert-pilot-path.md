# ADR 0002: Retire the Likert pilot survey as a data-collection path

Date: 2026-06-11
Status: accepted (amends ADR 0001)

## Context

ADR 0001 demoted the browser nudge pilot to a "small-N system demonstration"
while keeping it as a live data-collection instrument. Recruitment funding
remained uncertain, and the FTAS-based two-stage SEM has since been implemented
(scripts/sem_ftas.py) and produces well-fitting models (Stage 1 CFI 0.99,
RMSEA 0.044, n=15,776) without any new survey data. The Shinkansen DiD
(scripts/hokuriku_did_event_study.py) supplies the causal layer, and
scripts/rank_nudge_priorities.py closes the friction → nudge bridge
quantitatively.

## Decision

The Likert pilot survey path is retired entirely:

- No participant recruitment, no pilot data collection, no pilot-based SEM.
- `experiments/nudge-pilot/` is retained in the repo as a built artifact
  (deployable nudge-delivery system) and is referenced in the thesis as the
  implementation vehicle for the ranked interventions — not as an experiment.
- The remote `sem-analysis-suite` branch (SEM tooling designed around the
  pilot's 5x3 Likert instrument) is superseded by `scripts/sem_ftas.py` and
  will not be merged.

## Consequences

- The thesis's quantitative claims rest entirely on official open data
  (FTAS, merged Hokuriku, JTA) — fully reproducible, no funding dependency,
  no human-subjects collection beyond the gold-set coding by lab members.
- Causal evidence about *nudge effectiveness* (as opposed to friction impact)
  is out of scope; the thesis claims mechanism (SEM), impact of a friction
  shock (DiD), and an evidence-ranked intervention design (bridge + artifact).
  A funded pilot remains possible future work.
