# ADR 0001: FTAS-based SEM + Shinkansen DiD as the primary quantitative contribution

Date: 2026-06-11
Status: accepted

## Context

Midterm feedback judged the thesis "not engineering enough" — read as (a) no evaluated
built artifact and (b) no quantitative model beyond descriptive hypothesis tests. The
lab's preferred remedy is SEM evaluation of nudge effectiveness. The original plan
collected new Likert data via the nudge-pilot survey, but a defensible SEM needs
N≈150–200+ recruited respondents and recruitment funding is uncertain.

Meanwhile the project already holds official survey microdata: Fukui FTAS (n≈97,866)
with 5-point satisfaction items, future-visit intent, NPS, a universal
reported-inconvenience item, and free-text fields taggable by the friction codebook —
plus the merged tri-prefecture Hokuriku dataset (n≈54,695, Apr 2023–Feb 2026, CC-BY)
spanning the March 2024 Shinkansen extension on both sides.

## Decision

1. **Primary SEM runs on existing FTAS/Hokuriku microdata**, not on newly recruited
   survey respondents. Two-stage design:
   - Stage 1 (full sample): reported_inconvenience → satisfaction → behavioral
     intention. Satisfaction as a latent over the three domain items if CFA supports
     it; observed-mediator path model as fallback.
   - Stage 2 (friction reporters only): friction-type dummies → outcomes, producing
     the friction ranking that feeds nudge prioritization. Free-text selection bias is
     handled by conditioning, with a writer/non-writer comparison as honesty check.
2. **A difference-in-differences / event-study around the March 2024 Shinkansen
   extension** (Fukui treated; Ishikawa/Toyama controls; survey outcomes plus JTA
   guest-nights) provides the causal friction-impact claim. SEM remains the headline
   method per lab convention; DiD validates the mechanism's real-world impact.
3. **The nudge pilot is demoted to a small-N system demonstration** (artifact +
   feasibility), not a powered test. It can be upgraded if funding materializes.
4. **Friction tags remain transparent measured indicators.** Codebooks,
   matching behavior, and denominator rules are versioned and regression-tested.

## Consequences

- Removes recruitment funding as a critical-path dependency.
- Restricts primary inference to official Japanese survey respondents.
- Adds work: Hokuriku merge ingestion, schema-comparability checks for DiD (2023 rows
  have empty later-added columns), JTA back-series extension.
- DiD uses absolute official-survey timestamps.

## Alternatives considered

- **Recruited-survey SEM (original plan):** blocked on funding; underpowered fallback
  (5 conditions, lab-convenience N) would be statistically indefensible.
- **Collapsing to 2–3 pilot conditions with paid panel:** viable but still
  funding-dependent; retained as an optional upgrade path.
- **LLM tagging as primary instrument:** rejected; no institutional policy and
  lower auditability than versioned keyword rules.
