# Statistical Test Explanations

This document explains each statistical test used in the preliminary thesis analysis: why it was chosen, what it tests, and what the current result says about the data. The unit of analysis is one English-language Google Maps review unless otherwise stated.

## Scope and Interpretation Boundary
- These tests describe associations in post-cutoff English-language reviews; they do not establish causation.
- Reviewers are English-language reviewers globally. Nationality is not available from the source data.
- Theme assignment and friction coding are keyword/heuristic based, so results should be interpreted with coding limitations in mind.

## Input Data Audit
### Why this check was chosen
The audit is not an inferential statistical test. It is a deterministic validation step used before interpreting any statistics. It verifies that the dataset satisfies the core design assumptions: required columns exist, cities are present, reviews are English-language, dates pass the cutoff, IDs/text are not duplicated, and derived sentiment fields match their formulas.

### What it is used to determine
It determines whether the input data are internally consistent enough for downstream statistical tests. This protects the thesis from reporting precise p-values calculated from malformed or stale data.

### What the result means
The audit status is **PASS** for 915 review rows. City counts are Fukui 213, Kanazawa 533, Toyama 169. The theme None rate is 56.1% (513/915), and those unthemed reviews are excluded from SR-01/SR-02 tests.

## SR-01a: Chi-Square Goodness-of-Fit for Fukui Theme Distribution
### Why this test was chosen
A chi-square goodness-of-fit test is appropriate when one categorical variable is compared against an expected distribution. Here, the categorical variable is Fukui review `primary_theme`, and the reference distribution is uniform across the five theme categories. The uniform baseline is used as a neutral benchmark, not as a claim that real tourism discourse should be evenly distributed.

### What it is used to determine
It tests whether Fukui's themed review discourse is evenly distributed across Dinosaur, Food, Scenic, Cultural, and Logistics themes, or whether some themes are disproportionately represented.

### What the result means
Fukui has 120 themed reviews. Observed counts are Dinosaur 12, Food 11, Scenic 31, Cultural 50, Logistics 16. The test result is χ²(4) = 45.917, p = <0.001, Cramér's V = 0.309. This rejects the uniform distribution, meaning Fukui's English-language themed reviews are not balanced across themes. The result supports a claim about theme concentration, not causation or visitor motivations.

## SR-01b: Chi-Square Independence for City by Theme
### Why this test was chosen
A chi-square independence test is the standard test for association between two categorical variables. Here, the variables are city and primary theme. Because expected counts are sparse, the asymptotic chi-square result is supplemented with a deterministic permutation p-value using fixed margins.

### What it is used to determine
It determines whether the distribution of themes differs by city, which sheds light on whether Fukui's review discourse is positioned differently from Kanazawa and Toyama.

### What the result means
Across 402 themed reviews, the overall test is χ²(8) = 74.959, asymptotic p = <0.001, permutation p = <0.001, Cramér's V = 0.305. This indicates an association between city and theme mix. The minimum expected cell count is 2.943; if below the usual ≥5 guideline, the result should be reported with the permutation robustness check and sparse-cell caveat.
The largest cell drivers are: Fukui–Dinosaur observed 12 vs expected 3.9; Toyama–Scenic observed 44 vs expected 24.4; Toyama–Cultural observed 18 vs expected 38.0. After Bonferroni correction, reported pairwise differences remain for Fukui vs Kanazawa; Fukui vs Toyama; any suppressed comparison should be treated as counts-only because expected cells are too sparse.

## SR-01c: Shared-Theme City by Theme Test
### Why this companion test was chosen
The all-theme city comparison includes Dinosaur, which is substantively Fukui-specific and creates sparse expected counts for Kanazawa and Toyama. This companion test keeps the original all-theme result visible, but tests only themes that are meaningful across all three cities.

### What it is used to determine
It determines whether the distribution of shared themes (Food, Scenic, Cultural, Logistics) differs by city after excluding Dinosaur from the cross-city comparison.

### What the result means
Across 389 shared-theme reviews, the overall test is χ²(6) = 48.997, asymptotic p = <0.001, permutation p = <0.001, Cramér's V = 0.251. The minimum expected cell count is 9.486, so the standard expected-count guideline is met for this shared-theme comparison. In plain terms, city differences remain even after removing the Fukui-specific Dinosaur theme.

## SR-02: Emotional Intensity by Theme, ANOVA and Kruskal-Wallis
### Why these tests were chosen
One-way ANOVA is appropriate for testing whether a continuous outcome differs across more than two categorical groups. Here, `emotional_intensity_score` is the continuous outcome and `primary_theme` is the grouping variable. Kruskal-Wallis is included as a non-parametric robustness check because Shapiro-Wilk diagnostics show non-normality in most theme groups.

### What they are used to determine
These tests determine whether reviews assigned to different themes differ in emotional intensity. This sheds light on whether some tourism themes generate stronger affective language than others.

### What the result means
ANOVA gives F = 1.827, p = 0.123, η² = 0.0181. Kruskal-Wallis gives H(4) = 9.319, p = 0.054, ε² = 0.0134. ANOVA is not statistically significant, and the rank-based robustness check is not statistically significant. In plain terms, the current data do not provide strong evidence that emotional-intensity magnitude differs by theme.

## SR-05: Pairwise Welch t-Tests for Normalised Sentiment by City
### Why this test was chosen
Welch's t-test compares the means of a continuous variable between two independent groups without assuming equal variances. It is preferred over Student's t-test here because city sample sizes are unequal. Bonferroni correction is applied because there are three pairwise city comparisons.

### What it is used to determine
It determines whether Fukui's normalised VADER sentiment differs from Kanazawa or Toyama, and whether the comparison cities differ from each other.

### What the result means
Fukui vs Kanazawa mean 0.847 vs 0.814, p_adj=0.074, d_welch=0.181; Fukui vs Toyama mean 0.847 vs 0.850, p_adj=1.000, d_welch=-0.019; Kanazawa vs Toyama mean 0.814 vs 0.850, p_adj=0.063, d_welch=-0.202. The corrected mean tests do not provide evidence that average normalised sentiment differs between any pair of cities. Because VADER sentiment is bounded and skewed, treat this as a mean-test result rather than proof of destination equivalence or substantive visitor feeling.

## Additional: Spearman Correlation Between Star Rating and VADER Sentiment
### Why this test was chosen
Spearman's rho is appropriate because star ratings are ordinal and VADER compound scores are continuous but skewed. Spearman tests monotonic rank association without requiring linearity or normally distributed variables. Bootstrap confidence intervals add robustness for city-level samples.

### What it is used to determine
It determines whether textual sentiment aligns with numerical star ratings within each city. This checks whether VADER sentiment is a meaningful companion measure rather than a redundant or disconnected metric.

### What the result means
Fukui ρ=0.354, p_adj=<0.001, significant after Bonferroni; Kanazawa ρ=0.362, p_adj=<0.001, significant after Bonferroni; Toyama ρ=0.291, p_adj=<0.001, significant after Bonferroni. VADER sentiment has a positive, statistically reliable association with star ratings in all three cities, so it behaves as a useful companion measure. The correlations are moderate, so ratings and text sentiment should not be treated as interchangeable.

## Additional: Review Length by City, Kruskal-Wallis and Mann-Whitney
### Why these tests were chosen
Review length is right-skewed and non-normal, so Kruskal-Wallis is more appropriate than one-way ANOVA for comparing city groups. After a significant omnibus result, Mann-Whitney U tests with Benjamini-Hochberg FDR correction identify which city pairs differ. Cliff's δ is used as a signed rank-based effect size.

### What they are used to determine
These tests determine whether reviewers write systematically longer or shorter reviews in different cities, which sheds light on depth of description, itinerary complexity, or review genre differences.

### What the result means
Kruskal-Wallis gives H = 9.471, p = 0.009, ε² = 0.0082. Median review lengths are Fukui 176 chars, Kanazawa 157 chars, Toyama 192 chars. BH-corrected pairwise tests retain Fukui vs Kanazawa with δ=0.129; positive δ means the first city has longer reviews. The effect is small, so this is best interpreted as a modest review-style difference, not a large substantive gap.

## Descriptive Friction Context
### Why no broad inferential test was used
Most friction codes have very low counts, so broad inferential testing would be unstable and risk overclaiming. The friction table is therefore reported descriptively at sentence level.

### What it is used to determine
It identifies which friction themes appear most often and where policy-relevant visitor pain points may exist.

### What the result means
Current friction evidence should be treated as hypothesis-generating. Counts are useful for designing interventions and future data collection, but most codes are too sparse for confirmatory statistical inference.

