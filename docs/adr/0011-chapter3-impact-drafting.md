# ADR 0011: Chapter 3 drafting decisions — impact chapter framing

Date: 2026-07-02
Status: accepted

## Context

Chapter 3 "Impact: the Shinkansen extension as a friction shock" was drafted
per the master map (ADR 0008). Evidence base:
`output/hokuriku_merged/did_thesis_estimates.csv`,
`did_event_study_report.md`, `did_event_study_coefficients.csv`,
`did_feasibility_report.md`, `source_manifest.json`, and ADRs 0001/0005.
ADR 0010 flagged one obligation: §5.1 already carries the Noto-contamination
argument as the SCM's motivation, so Chapter 3 must present it as its own
threat without duplicating the estimator justification.

## Decision

1. **Wrote §3 (docs/thesis/section3_impact.md)**: 3.0 purpose → 3.1 data and
   design → 3.2 results table + pattern logic → 3.3 threats → 3.4 hand-offs to
   Chapters 4 and 5.
2. **Framed Chapters 3 and 5 as complementary estimands** (experience quality
   via survey DiD vs visitor volume via SCM), not as a superseded and a
   superseding design. ADR 0005 demoted the DiD for the *demand* headline; the
   experience-quality result remains this chapter's own claim.
3. **Read the fragile revisit-intention result forward to Chapter 6** rather
   than burying it: +0.038 → +0.008 under earthquake mitigations is presented
   as the first evidence that repeat visitation is the wrong margin, which the
   durability mechanism later explains. This is interpretation, not a new
   number; both coefficients are in the committed estimates CSV.
4. **Characterized pre-trends from the coefficients CSV, not the summary
   line:** 6 of 20 pre-reference coefficients significant at 5%; mixed-sign;
   all but one inside ±0.28; the largest (−0.52) in the sparse earliest common
   month (2023-09). This replaces the looser "±0.1–0.4 wobble" phrasing in
   results_overview.md — the overview line was not edited this round since it
   is a rough visual summary, but the chapter states the artifact-derived
   values.
5. **Printed transport satisfaction as +0.055/+0.077** (artifact precision)
   rather than the overview's +0.05/+0.08 rounding; NPS as +0.55/+0.65
   (0.5508/0.6483). Earthquake-robust column = the combined
   drop_jan_mar_2024_and_noto specification.
6. **Assigned Figs. 8–9** to the existing DiD event-study and parallel-trends
   PNGs, appending to the global figure table per the master's append-only
   rule; the "new figures" pointer advanced to Fig. 10+.
7. Verified this round from artifacts: all 20 spec × outcome estimates,
   cluster counts (73/67), sample window and Toyama exclusion (feasibility
   report), pre-period NPS levels (7.48/8.40), the ~47% repeat-response
   caveat, ~50% transport-satisfaction item response, and the CC-BY license
   chain (source_manifest.json).

## Consequences

- Chapters 3–6 are written; the empirical spine of the thesis is complete in
  prose. Remaining: 1 (intro), 2 (data/reproducibility), 7 (conclusion) — all
  assembly-heavy rather than analytically novel.
- Documentation/prose only; no pipeline, test, or artifact changed;
  reproduce-submission not re-run.
- Chapter 2 should absorb the licensing/provenance detail (CC-BY chain, pinned
  checksums) so Chapter 3's data section can stay lean.
