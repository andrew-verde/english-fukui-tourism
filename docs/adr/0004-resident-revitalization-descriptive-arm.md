# ADR 0004: Resident-revitalization arm is descriptive, not an SEM or ITS

Date: 2026-07-01
Status: accepted (extends ADR 0001)

## Context

The lab's mission centers on 地域創生 (regional revitalization), yet the ADR 0001
quantitative design is entirely tourist-facing (FTAS satisfaction → intention,
Shinkansen DiD). A resident-side outcome was sought to align the thesis with the
lab's stated mission.

`code4fukui/fukui-vision-data` publishes the Fukui 県民意識調査 (resident
attitude survey) as a **tidy aggregate time series** — `indicator_id,
indicator_label, fiscal_year, option, count, percent` — not respondent-level
microdata. The flagship indicator `living_fukui` (福井県に暮らしてきて良かった
と思うか, with a migration-intention tail 県外に移り住みたい) runs **7 annual
waves, FY2019–2025** (5 pre-event, 2 post). Other indicators
(`happiness_current`, `regional_pride`, `work_wellbeing_*`) have 2–4 waves only.
The survey metadata records a 郵送→WEB (mail→web) mode change across waves.

## Decision

1. **The resident arm is scoped as descriptive**, not causal and not latent:
   pre/post satisfaction and migration-intention shares across waves, with the
   March 2024 event marked. `living_fukui` is the primary indicator.
2. **No SEM on this data.** It is aggregate option/percent, so it cannot support
   a latent-variable measurement model as the FTAS microdata does.
3. **No interrupted-time-series causal claim.** Five annual pre-points and two
   post-points are too few for a credible ITS; the arm illustrates trend, not
   effect.
4. **Provenance status is `descriptive`/`estimated`** in the ledger, never
   `verified` causal evidence.

## Consequences

- The thesis gains a resident-wellbeing narrative aligned with the lab's 地域創生
   mission without overclaiming.
- The mail→web mode shift is a known confound for cross-wave comparison and is
  stated in every figure caption using this data.
- The resident arm supports context and motivation, not the causal contribution;
  the causal weight remains on the DiD (ADR 0003) and synthetic control (ADR 0005).

## Alternatives considered

- **Latent SEM on resident wellbeing:** rejected — no respondent-level data;
  option/percent aggregates cannot yield a covariance structure.
- **Interrupted time series on `living_fukui`:** rejected — insufficient post-event
  points; annual cadence and the mode shift make a segmented-regression claim
  indefensible.
- **Drop the resident arm entirely:** rejected — it is the most direct link to the
  lab's mission and is defensible as descriptive context.
