# ADR 0010: Chapter 5 drafting decisions — robustness chapter framing

Date: 2026-07-02
Status: accepted

## Context

Chapter 5 "Robustness: is the demand signal real?" was drafted per the master
map (ADR 0008) and the obligation inherited from ADR 0009: §4.1's regime map
forward-references the SCM estimator, so Chapter 5 must introduce it (panel
provenance, donor pool, fit criteria) before presenting the falsification
battery. Evidence base: `output/national_stats/causal_robustness/`
(metrics.json, inspace_placebos.csv, intime_placebo.csv,
leave_one_out_fukui_city.csv, target_gap_trajectories.csv), ADR 0005, and
Figs. 4–6.

## Decision

1. **Wrote §5 (docs/thesis/section5_robustness.md)** with the structure
   5.0 purpose → 5.1 estimator → 5.2 effect shape disciplines the statistic →
   5.3 in-space placebo → 5.4 negative control + leave-one-out → 5.5 what
   survives, handing the durability question to §6.
2. **Stated the significant-set threshold explicitly as the 10% one-sided
   level.** The set {Eiheiji, Fukui City, Tsuruga, Sakai} is defined in
   `scripts/causal_robustness.py` as `p_open_1s < 0.10 & good_fit` (Tsuruga p = 0.077,
   Sakai p = 0.096); earlier summaries named the set without its threshold,
   which a reader could mistake for 5%. The chapter notes Eiheiji and Fukui
   City also clear 5%.
3. **Led with the transient-effect rationale for the opening-window statistic**
   (post-mean gap averages a fading spike away; Fukui City post-mean two-sided
   p = 0.83 shown as the illustration), because the choice of test statistic is
   the chapter's most attackable decision and is defensible only via the
   effect-shape argument.
4. **Presented the fit-gate exclusions (Katsuyama +58.5%, Ikeda +48.0%, both
   pre-RMSPE 0.30 > 0.15) as evidence of design integrity** rather than hiding
   them — the battery discards its two largest point estimates for fit reasons.
5. **Reported the two-sided p-value (0.168) alongside the one-sided headline**
   and kept the one-sided posture as a named, pre-specified choice, consistent
   with §6.4's limitation framing.
6. **Did not include the Ishikawa-as-donor robustness re-run** (ADR 0005
   decision 5): no committed artifact in `causal_robustness/` carries its
   numbers, and the house rule is that unverifiable numbers do not enter prose.
   If that run's outputs are committed later, §5.4 is the insertion point.
7. All printed numbers verified from the artifacts this round, including the
   LOO donor count (24 positive-weight donors) and Fukui City's backdated
   placebo row (−3.5%, p = 0.472, 1,544 placebos kept).

## Consequences

- Chapters 4, 5, and 6 — the thesis's analytical core — are now written and
  mutually consistent: §4's forward reference resolves, §5 ends on the question
  §6 answers, and §6's recap numbers match §5's byte-for-byte.
- Documentation/prose only; no pipeline, test, or artifact changed;
  reproduce-submission not re-run.
- Remaining chapters: 1 (intro), 2 (data/reproducibility), 3 (DiD impact),
  7 (conclusion). Chapter 3 should present the Noto-earthquake contamination
  argument only briefly, as §5.1 now carries it as the SCM's motivation.
