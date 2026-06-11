# Statistical Summary

## Method Notes
- Unit of analysis: one review (rows in `output/friction_analysis/reviews_unified.csv`).
- Chi-square tests exclude reviews where `primary_theme` is None.
- Bonferroni correction for 3 pairwise city comparisons. Reported p_adj values are already multiplied by 3 and should be compared against α = 0.05 (equivalently, raw p against 0.05/3 = 0.0167).
- Effect sizes: Cramér's V (with Bergsma bias-corrected variant) for chi-square, η² for ANOVA, Welch-consistent Cohen's d for Welch t-tests.
- Chi-square assumption: expected cell frequencies ≥ 5 required. See 'assumption_expected_ge5' flags.
- City × theme chi-square results are supplemented with deterministic permutation p-values (10,000 permutations, seed=42) because expected counts are sparse.

## Input Data Audit
- Status: PASS
- n (review rows): 915
- Review date cutoff: 2024-06-01
- City counts: Fukui 213, Kanazawa 533, Toyama 169
- Deterministic checks: all passed.
- Theme None rate: 56.1% (513/915); excluded from SR-01/SR-02.

## SR-01 — Theme distribution (Fukui) chi-square GoF
- n (Fukui themed reviews): 120
- χ²(4) = 45.917, p = <0.001, Cramér's V = 0.309 (expected: uniform across themes)
- Interpretation: Fukui's themed reviews are concentrated rather than evenly distributed across the five theme buckets.

## SR-01 — Theme distribution differs by city (chi-square independence)
- n (themed reviews across 3 cities): 402
- Overall: χ²(8) = 74.959, asymptotic p = <0.001; permutation p = <0.001, Cramér's V = 0.305
- Expected-count minimum: 2.943 ⚠ expected_min < 5 — chi-sq assumption violated
- Largest cell drivers: Fukui–Dinosaur observed 12 vs expected 3.9; Toyama–Scenic observed 44 vs expected 24.4; Toyama–Cultural observed 18 vs expected 38.0.
- Interpretation: theme mix varies by city, but the all-theme result has sparse-cell caveats; use the shared-theme test below for the cleaner cross-city comparison.
- Pairwise (Bonferroni-adjusted p-values):
  - Fukui vs Kanazawa: χ²(4) = 35.314, asym_p_adj = <0.001, perm_p_adj = <0.001, V = 0.337 ⚠ exp_min=4.63 (adjusted p vs α=0.05)
  - Fukui vs Toyama: χ²(4) = 24.596, asym_p_adj = <0.001, perm_p_adj = <0.001, V = 0.341 (adjusted p vs α=0.05)
  - Kanazawa vs Toyama: asymptotic χ² suppressed (expected_min=0.32 < 1.0 — asymptotic chi-square approximation invalid; exact permutation p-value reported instead); perm_p_adj = <0.001 (vs α=0.05)

## SR-01 — Shared theme distribution differs by city
- Scope: shared cross-city themes only (Food, Scenic, Cultural, Logistics); Dinosaur is retained elsewhere as a Fukui-specific destination theme.
- n (shared-theme reviews across 3 cities): 389
- Overall: χ²(6) = 48.997, asymptotic p = <0.001; permutation p = <0.001, Cramér's V = 0.251
- Expected-count minimum: 9.486
- Largest cell drivers: Toyama–Scenic observed 44 vs expected 25.0; Toyama–Cultural observed 18 vs expected 38.9; Kanazawa–Scenic observed 33 vs expected 53.0.
- Interpretation: cross-city theme differences remain after excluding Dinosaur, with acceptable expected counts.

## SR-02 — Emotional intensity by theme (ANOVA + Tukey HSD)
_(Theme 'Cultural' was formerly labelled 'Emotional'; renamed 2026-05-19.)_
- n (themed reviews): 402
- ANOVA: F = 1.827, p = 0.123, η² = 0.0181
- Assumptions: Levene median test p = 0.275; equal variance = True.
- Tukey HSD (pairwise p-values, selected pairs):
  - Cultural vs Dinosaur: Δmean = -0.097, p = 0.572
  - Cultural vs Food: Δmean = -0.007, p = 0.999
  - Cultural vs Logistics: Δmean = 0.034, p = 0.911
  - Cultural vs Scenic: Δmean = -0.052, p = 0.341
  - Dinosaur vs Food: Δmean = 0.089, p = 0.684
  - Dinosaur vs Logistics: Δmean = 0.130, p = 0.366
  - Dinosaur vs Scenic: Δmean = 0.045, p = 0.961
  - Food vs Logistics: Δmean = 0.041, p = 0.884
  - Food vs Scenic: Δmean = -0.044, p = 0.696
  - Logistics vs Scenic: Δmean = -0.086, p = 0.237
- Kruskal-Wallis robustness check (non-normality confirmed in 5/5 groups):
  H(4) = 9.319, p = 0.054, ε² = 0.0134
  Interpretation: Consistent with ANOVA null
  Pairwise Mann-Whitney after BH FDR: no theme pair remains significant.
  Interpretation: emotional-intensity magnitude does not differ clearly by theme in the current review sample.

## SR-05 — Sentiment differs by city (pairwise t-tests, Bonferroni)
- n (reviews): 915
- Fukui vs Kanazawa: mean=0.847 vs 0.814, p_adj=0.074, d_welch=0.181
- Fukui vs Toyama: mean=0.847 vs 0.850, p_adj=1.000, d_welch=-0.019
- Kanazawa vs Toyama: mean=0.814 vs 0.850, p_adj=0.063, d_welch=-0.202
- Interpretation: corrected mean tests do not show city-level sentiment differences.

## Additional — Spearman ρ: star rating vs VADER sentiment by city
_(Spearman used: review_rating is ordinal; vader_compound is right-skewed continuous.)_
_(Bonferroni correction across 3 city tests: α_adj = 0.0167.)_
- Fukui (n=213): ρ = 0.354, p = <0.001, p_adj = <0.001, 95% CI [0.219, 0.479] — ✓ significant (survives Bonferroni)
- Kanazawa (n=533): ρ = 0.362, p = <0.001, p_adj = <0.001, 95% CI [0.281, 0.435] — ✓ significant (survives Bonferroni)
- Toyama (n=169): ρ = 0.291, p = <0.001, p_adj = <0.001, 95% CI [0.149, 0.428] — ✓ significant (survives Bonferroni)
- All cities combined (n=915): ρ = 0.351, p = <0.001
- Interpretation: VADER text sentiment aligns with star ratings in every city, but only moderately.

## Additional — Review length by city (Kruskal-Wallis + Mann-Whitney)
_(3/3 city groups non-normal by Shapiro-Wilk; KW used in place of one-way ANOVA.)_
_(Pairwise Mann-Whitney with Benjamini-Hochberg FDR correction; Cliff's δ is signed, positive means first city has longer reviews.)_
- n (reviews): 915
- Kruskal-Wallis: H = 9.471, p = 0.009, ε² = 0.0082 (negligible effect)
- Medians: Fukui 176 chars, Kanazawa 157 chars, Toyama 192 chars
- Pairwise (BH FDR corrected):
  - Fukui vs Kanazawa: p = 0.006, p_BH = 0.017, δ = 0.129 — ✓
  - Fukui vs Toyama: p = 0.780, p_BH = 0.780, δ = 0.017 — NS
  - Kanazawa vs Toyama: p = 0.040, p_BH = 0.060, δ = -0.105 — NS
- Interpretation: review length differs by city overall; see pairwise rows for which gaps survive correction.

## Descriptive friction context (sentence-level, not inferential)
- Top friction codes by raw count (across cities, sentence-level denominator):
  - Kanazawa: waiting_crowding — n=25 (1.5% of sentences)
  - Kanazawa: opening_hours_availability — n=12 (0.7% of sentences)
  - Fukui: opening_hours_availability — n=10 (1.3% of sentences)
  - Kanazawa: price_value — n=9 (0.5% of sentences)
  - Fukui: transport_access — n=8 (1.0% of sentences)
  - Fukui: itinerary_fit_time_cost — n=7 (0.9% of sentences)
  - Fukui: price_value — n=6 (0.8% of sentences)
  - Fukui: accessibility_mobility — n=6 (0.8% of sentences)
  - Kanazawa: english_information_gap — n=5 (0.3% of sentences)
  - Toyama: accessibility_mobility — n=3 (0.5% of sentences)

## Skipped Analyses
- SR-04 event impact t-test is skipped (review timestamps are not reliably absolute).
- K-means clustering is skipped (no row-level spending data).

## Methodological Limitations
- SR-02 ANOVA and Kruskal-Wallis both fall short of conventional significance in the current output (ANOVA p=0.123; KW p=0.054), so emotional-intensity differences by theme should be described as not clearly supported.
- SR-05 reports Welch mean tests only. VADER sentiment is bounded and non-normal, so significant or null mean-test results should not be overread as destination equivalence or broad visitor feeling.
- Theme and friction coding are heuristic/keyword-based; missed mentions and false positives can occur.
- Reviewers are described as English-language reviewers; nationality is not available from source data.
- SR-01 Fukui goodness-of-fit uses a uniform five-theme benchmark. This is a neutral exploratory baseline, not an empirical expectation for real tourism discourse.
- Chi-square independence tests have sparse expected counts; use permutation p-values and cell-driver diagnostics rather than relying only on asymptotic p-values.
- Total sample: 915 reviews (Fukui 213, Kanazawa 533, Toyama 169). Unbalanced across cities.
- Theme None rate: 56.1% (513/915) excluded from SR-01/SR-02 tests.
- Statistical tests treat reviews as independent rows. Reviews may still be clustered by POI or recurring reviewer, so inferential claims should remain exploratory.
- emotional_intensity_score = abs(vader_compound) is a magnitude proxy, not a true affective depth measure.
- 5 of 12 review-level friction codes have count < 5; codes at or above that threshold: transport_access, english_information_gap, waiting_crowding, price_value, opening_hours_availability, itinerary_fit_time_cost, accessibility_mobility.
- Food theme: 'eat' and 'dish' keywords have minor false-positive risk (incidental mentions in non-food reviews). Impact estimated low; documented as limitation.
- Theme 'Cultural' formerly labelled 'Emotional'; renamed 2026-05-19 to reflect keyword scope (Zen/spiritual + heritage/cultural content).
