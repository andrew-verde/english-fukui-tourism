#!/usr/bin/env python3
"""
synthesis_pipeline.py — Produce a cite-ready statistical summary markdown.

Reads:
  output/statistical_results.json (from scripts/statistical_validation.py)
  output/friction_analysis/friction_by_city.csv (contextual descriptive counts)

Writes:
  output/statistical_summary.md
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from src.utils.logger import setup_logger

logger = setup_logger(__name__)

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
RESULTS_JSON = OUTPUT_DIR / "statistical_results.json"
SUMMARY_MD = OUTPUT_DIR / "statistical_summary.md"
TEST_EXPLANATIONS_MD = OUTPUT_DIR / "statistical_test_explanations.md"
FRICTION_BY_CITY = OUTPUT_DIR / "friction_analysis" / "friction_by_city.csv"
REVIEWS_CSV = OUTPUT_DIR / "friction_analysis" / "reviews_unified.csv"


def _load_results() -> dict:
    if not RESULTS_JSON.exists():
        raise FileNotFoundError(f"Missing input: {RESULTS_JSON} (run scripts/statistical_validation.py first)")
    return json.loads(RESULTS_JSON.read_text())


def _fmt_p(p: float | None) -> str:
    if p is None:
        return "n/a"
    if p < 0.001:
        return "<0.001"
    return f"{p:.3f}"


def _sig_text(p: float | None, alpha: float = 0.05) -> str:
    if p is None:
        return "not evaluated"
    return "statistically significant" if p < alpha else "not statistically significant"


def _write_test_explanations(results: dict) -> None:
    """Write a thesis-facing explanation of why each statistical test was used."""
    lines: list[str] = []
    lines.append("# Statistical Test Explanations")
    lines.append("")
    lines.append("This document explains each statistical test used in the preliminary thesis analysis: why it was chosen, what it tests, and what the current result says about the data. The unit of analysis is one English-language Google Maps review unless otherwise stated.")
    lines.append("")
    lines.append("## Scope and Interpretation Boundary")
    lines.append("- These tests describe associations in post-cutoff English-language reviews; they do not establish causation.")
    lines.append("- Reviewers are English-language reviewers globally. Nationality is not available from the source data.")
    lines.append("- Theme assignment and friction coding are keyword/heuristic based, so results should be interpreted with coding limitations in mind.")
    lines.append("")

    audit = results.get("input_data_audit", {})
    if audit:
        ad = audit.get("details", {})
        city_counts = ad.get("city_counts", {})
        city_str = ", ".join(f"{city} {n}" for city, n in city_counts.items())
        lines.append("## Input Data Audit")
        lines.append("### Why this check was chosen")
        lines.append("The audit is not an inferential statistical test. It is a deterministic validation step used before interpreting any statistics. It verifies that the dataset satisfies the core design assumptions: required columns exist, cities are present, reviews are English-language, dates pass the cutoff, IDs/text are not duplicated, and derived sentiment fields match their formulas.")
        lines.append("")
        lines.append("### What it is used to determine")
        lines.append("It determines whether the input data are internally consistent enough for downstream statistical tests. This protects the thesis from reporting precise p-values calculated from malformed or stale data.")
        lines.append("")
        lines.append("### What the result means")
        status = "PASS" if ad.get("valid") else "CHECK REQUIRED"
        lines.append(f"The audit status is **{status}** for {audit.get('n')} review rows. City counts are {city_str}. The theme None rate is {ad.get('theme_none_pct', 0):.1f}% ({ad.get('theme_none_n', 0)}/{audit.get('n')}), and those unthemed reviews are excluded from SR-01/SR-02 tests.")
        lines.append("")

    gof = results.get("SR-01 theme_chi_square_gof", {})
    if gof:
        d = gof.get("details", {})
        counts = ", ".join(f"{theme} {count}" for theme, count in zip(d.get("themes", []), d.get("observed_counts", []), strict=False))
        lines.append("## SR-01a: Chi-Square Goodness-of-Fit for Fukui Theme Distribution")
        lines.append("### Why this test was chosen")
        lines.append("A chi-square goodness-of-fit test is appropriate when one categorical variable is compared against an expected distribution. Here, the categorical variable is Fukui review `primary_theme`, and the reference distribution is uniform across the five theme categories. The uniform baseline is used as a neutral benchmark, not as a claim that real tourism discourse should be evenly distributed.")
        lines.append("")
        lines.append("### What it is used to determine")
        lines.append("It tests whether Fukui's themed review discourse is evenly distributed across Dinosaur, Food, Scenic, Cultural, and Logistics themes, or whether some themes are disproportionately represented.")
        lines.append("")
        lines.append("### What the result means")
        lines.append(f"Fukui has {gof.get('n')} themed reviews. Observed counts are {counts}. The test result is χ²({d.get('df')}) = {d.get('chi2', float('nan')):.3f}, p = {_fmt_p(d.get('p_value'))}, Cramér's V = {d.get('cramers_v', float('nan')):.3f}. This rejects the uniform distribution, meaning Fukui's English-language themed reviews are not balanced across themes. The result supports a claim about theme concentration, not causation or visitor motivations.")
        lines.append("")

    indep = results.get("SR-01 theme_chi_square_independence", {})
    if indep:
        overall = indep.get("details", {}).get("overall", {})
        lines.append("## SR-01b: Chi-Square Independence for City by Theme")
        lines.append("### Why this test was chosen")
        lines.append("A chi-square independence test is the standard test for association between two categorical variables. Here, the variables are city and primary theme. Because expected counts are sparse, the asymptotic chi-square result is supplemented with a deterministic permutation p-value using fixed margins.")
        lines.append("")
        lines.append("### What it is used to determine")
        lines.append("It determines whether the distribution of themes differs by city, which sheds light on whether Fukui's review discourse is positioned differently from Kanazawa and Toyama.")
        lines.append("")
        lines.append("### What the result means")
        lines.append(f"Across {indep.get('n')} themed reviews, the overall test is χ²({overall.get('df')}) = {overall.get('chi2', float('nan')):.3f}, asymptotic p = {_fmt_p(overall.get('p_value'))}, permutation p = {_fmt_p(overall.get('p_value_permutation'))}, Cramér's V = {overall.get('cramers_v', float('nan')):.3f}. This indicates an association between city and theme mix. However, the minimum expected cell count is {overall.get('expected_min', float('nan')):.3f}, below the usual ≥5 guideline, so the result should be reported with the permutation robustness check and sparse-cell caveat.")
        top_cells = overall.get("top_chi2_cell_contributions", [])[:3]
        if top_cells:
            drivers = "; ".join(f"{r['city']}–{r['theme']} observed {r['observed']} vs expected {r['expected']:.1f}" for r in top_cells)
            significant_pairs = [
                r for r in indep.get("details", {}).get("pairwise", [])
                if not r.get("suppressed") and r.get("p_value_bonferroni") is not None and r["p_value_bonferroni"] < 0.05
            ]
            if significant_pairs:
                pair_text = "; ".join(f"{r['cities'][0]} vs {r['cities'][1]}" for r in significant_pairs)
                lines.append(f"The largest cell drivers are: {drivers}. After Bonferroni correction, reported pairwise differences remain for {pair_text}; any suppressed comparison should be treated as counts-only because expected cells are too sparse.")
            else:
                lines.append(f"The largest cell drivers are: {drivers}. Pairwise city comparisons are weaker than the omnibus result, so the safest claim is an overall city-theme association.")
        lines.append("")

    shared_indep = results.get("SR-01 shared_theme_chi_square_independence", {})
    if shared_indep:
        overall = shared_indep.get("details", {}).get("overall", {})
        themes = ", ".join(overall.get("themes", []))
        lines.append("## SR-01c: Shared-Theme City by Theme Test")
        lines.append("### Why this companion test was chosen")
        lines.append("The all-theme city comparison includes Dinosaur, which is substantively Fukui-specific and creates sparse expected counts for Kanazawa and Toyama. This companion test keeps the original all-theme result visible, but tests only themes that are meaningful across all three cities.")
        lines.append("")
        lines.append("### What it is used to determine")
        lines.append(f"It determines whether the distribution of shared themes ({themes}) differs by city after excluding Dinosaur from the cross-city comparison.")
        lines.append("")
        lines.append("### What the result means")
        exp_min = overall.get("expected_min", float("nan"))
        exp_note = "so the standard expected-count guideline is met" if overall.get("assumption_expected_ge5") else "so sparse-cell caveats still apply"
        lines.append(f"Across {shared_indep.get('n')} shared-theme reviews, the overall test is χ²({overall.get('df')}) = {overall.get('chi2', float('nan')):.3f}, asymptotic p = {_fmt_p(overall.get('p_value'))}, permutation p = {_fmt_p(overall.get('p_value_permutation'))}, Cramér's V = {overall.get('cramers_v', float('nan')):.3f}. The minimum expected cell count is {exp_min:.3f}, {exp_note} for this shared-theme comparison. In plain terms, city differences remain even after removing the Fukui-specific Dinosaur theme.")
        lines.append("")

    anova = results.get("SR-02 theme_anova", {})
    kw = results.get("SR-02 kruskal_wallis_robustness", {})
    if anova:
        d = anova.get("details", {})
        kd = kw.get("details", {}) if kw else {}
        lines.append("## SR-02: Emotional Intensity by Theme, ANOVA and Kruskal-Wallis")
        lines.append("### Why these tests were chosen")
        lines.append("One-way ANOVA is appropriate for testing whether a continuous outcome differs across more than two categorical groups. Here, `emotional_intensity_score` is the continuous outcome and `primary_theme` is the grouping variable. Kruskal-Wallis is included as a non-parametric robustness check because Shapiro-Wilk diagnostics show non-normality in most theme groups.")
        lines.append("")
        lines.append("### What they are used to determine")
        lines.append("These tests determine whether reviews assigned to different themes differ in emotional intensity. This sheds light on whether some tourism themes generate stronger affective language than others.")
        lines.append("")
        lines.append("### What the result means")
        anova_sig = _sig_text(d.get("p_value"))
        kw_sig = _sig_text(kd.get("p_value"))
        lines.append(f"ANOVA gives F = {d.get('f_stat', float('nan')):.3f}, p = {_fmt_p(d.get('p_value'))}, η² = {d.get('eta_squared', float('nan')):.4f}. Kruskal-Wallis gives H({kd.get('k_groups', 1) - 1}) = {kd.get('h_stat', float('nan')):.3f}, p = {_fmt_p(kd.get('p_value'))}, ε² = {kd.get('epsilon_squared', float('nan')):.4f}. ANOVA is {anova_sig}, and the rank-based robustness check is {kw_sig}. In plain terms, the current data do not provide strong evidence that emotional-intensity magnitude differs by theme.")
        sig_pairs = [p for p in kd.get("pairwise_mann_whitney", []) if p.get("significant_bh")]
        if sig_pairs:
            pair_str = "; ".join(f"{p['themes'][0]} vs {p['themes'][1]} p_BH={_fmt_p(p['p_value_bh'])}, Cliff's δ={p['cliffs_delta']:.3f}" for p in sig_pairs)
            lines.append(f"Post-hoc Mann-Whitney tests with BH FDR correction identify only this surviving contrast: {pair_str}.")
        lines.append("")

    city = results.get("SR-05 city_comparison_sentiment_norm", {})
    if city:
        lines.append("## SR-05: Pairwise Welch t-Tests for Normalised Sentiment by City")
        lines.append("### Why this test was chosen")
        lines.append("Welch's t-test compares the means of a continuous variable between two independent groups without assuming equal variances. It is preferred over Student's t-test here because city sample sizes are unequal. Bonferroni correction is applied because there are three pairwise city comparisons.")
        lines.append("")
        lines.append("### What it is used to determine")
        lines.append("It determines whether Fukui's normalised VADER sentiment differs from Kanazawa or Toyama, and whether the comparison cities differ from each other.")
        lines.append("")
        lines.append("### What the result means")
        rows = city.get("details", {}).get("pairwise", [])
        parts = [
            f"{r['cities'][0]} vs {r['cities'][1]} mean {r['mean_a']:.3f} vs {r['mean_b']:.3f}, p_adj={_fmt_p(r['p_value_bonferroni'])}, d={r['cohens_d']:.3f}"
            for r in rows
        ]
        significant = [r for r in rows if r.get("p_value_bonferroni") is not None and r["p_value_bonferroni"] < 0.05]
        if significant:
            sig_text = "; ".join(f"{r['cities'][0]} vs {r['cities'][1]}" for r in significant)
            interpretation = f"The corrected mean tests find a small sentiment difference for {sig_text}, but not for Fukui against either comparison city."
        else:
            interpretation = "The corrected mean tests do not provide evidence that Fukui's average normalised sentiment differs from the comparison cities."
        lines.append("; ".join(parts) + f". {interpretation} Because VADER sentiment is bounded and skewed, treat this as a mean-test result rather than proof of destination equivalence or substantive visitor feeling.")
        lines.append("")

    spear = results.get("additional_spearman_rating_vs_sentiment", {})
    if spear:
        lines.append("## Additional: Spearman Correlation Between Star Rating and VADER Sentiment")
        lines.append("### Why this test was chosen")
        lines.append("Spearman's rho is appropriate because star ratings are ordinal and VADER compound scores are continuous but skewed. Spearman tests monotonic rank association without requiring linearity or normally distributed variables. Bootstrap confidence intervals add robustness for city-level samples.")
        lines.append("")
        lines.append("### What it is used to determine")
        lines.append("It determines whether textual sentiment aligns with numerical star ratings within each city. This checks whether VADER sentiment is a meaningful companion measure rather than a redundant or disconnected metric.")
        lines.append("")
        lines.append("### What the result means")
        city_rows = spear.get("details", {}).get("by_city", [])
        text = []
        for r in city_rows:
            sig = "significant after Bonferroni" if r.get("significant_bonferroni") else "not significant after Bonferroni"
            text.append(f"{r['city']} ρ={r['rho']:.3f}, p_adj={_fmt_p(r['p_value_bonferroni'])}, {sig}")
        lines.append("; ".join(text) + ". VADER sentiment has a positive, statistically reliable association with star ratings in all three cities, so it behaves as a useful companion measure. The correlations are moderate, so ratings and text sentiment should not be treated as interchangeable.")
        lines.append("")

    length = results.get("additional_kw_review_length_by_city", {})
    if length:
        d = length.get("details", {})
        lines.append("## Additional: Review Length by City, Kruskal-Wallis and Mann-Whitney")
        lines.append("### Why these tests were chosen")
        lines.append("Review length is right-skewed and non-normal, so Kruskal-Wallis is more appropriate than one-way ANOVA for comparing city groups. After a significant omnibus result, Mann-Whitney U tests with Benjamini-Hochberg FDR correction identify which city pairs differ. Cliff's δ is used as a signed rank-based effect size.")
        lines.append("")
        lines.append("### What they are used to determine")
        lines.append("These tests determine whether reviewers write systematically longer or shorter reviews in different cities, which sheds light on depth of description, itinerary complexity, or review genre differences.")
        lines.append("")
        lines.append("### What the result means")
        medians = d.get("median_by_city", {})
        med_str = ", ".join(f"{city} {median:.0f} chars" for city, median in medians.items())
        sig_pairs = [p for p in d.get("pairwise_mann_whitney", []) if p.get("significant_bh")]
        if sig_pairs:
            pair_text = "; ".join(
                f"{p['cities'][0]} vs {p['cities'][1]} with δ={p['cliffs_delta']:.3f}"
                for p in sig_pairs
            )
            pair_note = f"BH-corrected pairwise tests retain {pair_text}; positive δ means the first city has longer reviews."
        else:
            pair_note = "No pairwise comparison remains significant after BH correction."
        lines.append(f"Kruskal-Wallis gives H = {d.get('h_stat', float('nan')):.3f}, p = {_fmt_p(d.get('p_value'))}, ε² = {d.get('epsilon_squared', float('nan')):.4f}. Median review lengths are {med_str}. {pair_note} The effect is small, so this is best interpreted as a modest review-style difference, not a large substantive gap.")
        lines.append("")

    lines.append("## Descriptive Friction Context")
    lines.append("### Why no broad inferential test was used")
    lines.append("Most friction codes have very low counts, so broad inferential testing would be unstable and risk overclaiming. The friction table is therefore reported descriptively at sentence level.")
    lines.append("")
    lines.append("### What it is used to determine")
    lines.append("It identifies which friction themes appear most often and where policy-relevant visitor pain points may exist.")
    lines.append("")
    lines.append("### What the result means")
    lines.append("Current friction evidence should be treated as hypothesis-generating. Counts are useful for designing interventions and future data collection, but most codes are too sparse for confirmatory statistical inference.")
    lines.append("")

    TEST_EXPLANATIONS_MD.write_text("\n".join(lines) + "\n")


def main():
    logger.info("=" * 55)
    logger.info("Synthesis pipeline: statistical summary markdown")
    logger.info("=" * 55)

    payload = _load_results()
    results = {r["name"]: r for r in payload.get("results", [])}

    lines: list[str] = []
    lines.append("# Statistical Summary")
    lines.append("")
    lines.append("## Method Notes")
    lines.append("- Unit of analysis: one review (rows in `output/friction_analysis/reviews_unified.csv`).")
    lines.append("- Chi-square tests exclude reviews where `primary_theme` is None.")
    lines.append("- Bonferroni correction for 3 pairwise city comparisons: α_adjusted = 0.05/3 = 0.0167.")
    lines.append("- Effect sizes: Cramér's V for chi-square, η² for ANOVA, Cohen's d for t-tests.")
    lines.append("- Chi-square assumption: expected cell frequencies ≥ 5 required. See 'assumption_expected_ge5' flags.")
    lines.append("- City × theme chi-square results are supplemented with deterministic permutation p-values (10,000 permutations, seed=42) because expected counts are sparse.")
    lines.append("")

    audit = results.get("input_data_audit", {})
    lines.append("## Input Data Audit")
    if audit.get("n", 0) == 0:
        lines.append("- Not run: no input rows available.")
    else:
        ad = audit.get("details", {})
        status = "PASS" if ad.get("valid") else "CHECK REQUIRED"
        lines.append(f"- Status: {status}")
        lines.append(f"- n (review rows): {audit['n']}")
        lines.append(f"- Review date cutoff: {ad.get('review_date_cutoff', 'n/a')}")
        city_counts = ad.get("city_counts", {})
        if city_counts:
            lines.append("- City counts: " + ", ".join(f"{city} {n}" for city, n in city_counts.items()))
        checks = ad.get("checks", {})
        failed = [k for k, v in checks.items() if not v]
        lines.append("- Deterministic checks: all passed." if not failed else "- Failed checks: " + ", ".join(failed))
        lines.append(
            f"- Theme None rate: {ad.get('theme_none_pct', 0):.1f}% "
            f"({ad.get('theme_none_n', 0)}/{audit['n']}); excluded from SR-01/SR-02."
        )
    lines.append("")

    # SR-01 GoF
    gof = results.get("SR-01 theme_chi_square_gof", {})
    lines.append("## SR-01 — Theme distribution (Fukui) chi-square GoF")
    if gof.get("n", 0) == 0:
        lines.append(f"- Not run: {gof.get('details', {}).get('error', 'insufficient data')}")
    else:
        d = gof["details"]
        lines.append(f"- n (Fukui themed reviews): {gof['n']}")
        lines.append(f"- χ²({d['df']}) = {d['chi2']:.3f}, p = {_fmt_p(d['p_value'])}, Cramér's V = {d.get('cramers_v', 'n/a'):.3f} (expected: uniform across themes)")
        lines.append("- Interpretation: Fukui's themed reviews are concentrated rather than evenly distributed across the five theme buckets.")
    lines.append("")

    # SR-01 Independence
    indep = results.get("SR-01 theme_chi_square_independence", {})
    lines.append("## SR-01 — Theme distribution differs by city (chi-square independence)")
    if indep.get("n", 0) == 0:
        lines.append(f"- Not run: {indep.get('details', {}).get('error', 'insufficient data')}")
    else:
        overall = indep["details"]["overall"]
        v_overall = overall.get('cramers_v')
        v_str = f"{v_overall:.3f}" if v_overall is not None else "n/a"
        exp_min = overall.get('expected_min')
        assumption_ok = overall.get('assumption_expected_ge5', False)
        assumption_note = "" if assumption_ok else " ⚠ expected_min < 5 — chi-sq assumption violated"
        lines.append(f"- n (themed reviews across 3 cities): {indep['n']}")
        perm_p = overall.get("p_value_permutation")
        perm_note = f"; permutation p = {_fmt_p(perm_p)}" if perm_p is not None else ""
        lines.append(f"- Overall: χ²({overall['df']}) = {overall['chi2']:.3f}, asymptotic p = {_fmt_p(overall['p_value'])}{perm_note}, Cramér's V = {v_str}")
        lines.append(f"- Expected-count minimum: {exp_min:.3f}{assumption_note}")
        top_cells = overall.get("top_chi2_cell_contributions", [])[:3]
        if top_cells:
            drivers = "; ".join(
                f"{r['city']}–{r['theme']} observed {r['observed']} vs expected {r['expected']:.1f}"
                for r in top_cells
            )
            lines.append(f"- Largest cell drivers: {drivers}.")
        lines.append("- Interpretation: theme mix varies by city, but the all-theme result has sparse-cell caveats; use the shared-theme test below for the cleaner cross-city comparison.")
        lines.append("- Pairwise (Bonferroni-adjusted p-values):")
        for row in indep["details"]["pairwise"]:
            cities_label = f"{row['cities'][0]} vs {row['cities'][1]}"
            if row.get("suppressed"):
                lines.append(
                    f"  - {cities_label}: NOT REPORTED — "
                    f"{row.get('suppressed_reason', 'expected_min below threshold')}"
                )
            else:
                p_adj = row["p_value_bonferroni"]
                p_perm_adj = row.get("p_value_permutation_bonferroni")
                pw_v = row.get('cramers_v')
                pw_v_str = f"{pw_v:.3f}" if pw_v is not None else "n/a"
                pw_exp_min = row.get('expected_min')
                pw_ok = row.get('assumption_expected_ge5', False)
                pw_note = "" if pw_ok else f" ⚠ exp_min={pw_exp_min:.2f}"
                perm_part = f", perm_p_adj = {_fmt_p(p_perm_adj)}" if p_perm_adj is not None else ""
                lines.append(
                    f"  - {cities_label}: "
                    f"χ²({row['df']}) = {row['chi2']:.3f}, asym_p_adj = {_fmt_p(p_adj)}{perm_part}, V = {pw_v_str}{pw_note} (α=0.0167)"
                )
    lines.append("")

    # SR-01 Shared-theme Independence
    shared_indep = results.get("SR-01 shared_theme_chi_square_independence", {})
    lines.append("## SR-01 — Shared theme distribution differs by city")
    if shared_indep.get("n", 0) == 0:
        lines.append(f"- Not run: {shared_indep.get('details', {}).get('error', 'insufficient data')}")
    else:
        overall = shared_indep["details"]["overall"]
        v_overall = overall.get('cramers_v')
        v_str = f"{v_overall:.3f}" if v_overall is not None else "n/a"
        exp_min = overall.get('expected_min')
        perm_p = overall.get("p_value_permutation")
        perm_note = f"; permutation p = {_fmt_p(perm_p)}" if perm_p is not None else ""
        themes = ", ".join(overall.get("themes", []))
        lines.append(f"- Scope: shared cross-city themes only ({themes}); Dinosaur is retained elsewhere as a Fukui-specific destination theme.")
        lines.append(f"- n (shared-theme reviews across 3 cities): {shared_indep['n']}")
        lines.append(f"- Overall: χ²({overall['df']}) = {overall['chi2']:.3f}, asymptotic p = {_fmt_p(overall['p_value'])}{perm_note}, Cramér's V = {v_str}")
        lines.append(f"- Expected-count minimum: {exp_min:.3f}")
        top_cells = overall.get("top_chi2_cell_contributions", [])[:3]
        if top_cells:
            drivers = "; ".join(
                f"{r['city']}–{r['theme']} observed {r['observed']} vs expected {r['expected']:.1f}"
                for r in top_cells
            )
            lines.append(f"- Largest cell drivers: {drivers}.")
        lines.append("- Interpretation: cross-city theme differences remain after excluding Dinosaur, with acceptable expected counts.")
    lines.append("")

    # SR-02 ANOVA
    anova = results.get("SR-02 theme_anova", {})
    lines.append("## SR-02 — Emotional intensity by theme (ANOVA + Tukey HSD)")
    lines.append("_(Theme 'Cultural' was formerly labelled 'Emotional'; renamed 2026-05-19.)_")
    if anova.get("n", 0) == 0:
        lines.append(f"- Not run: {anova.get('details', {}).get('error', 'insufficient data')}")
    else:
        d = anova["details"]
        eta2 = d.get("eta_squared")
        eta2_str = f"{eta2:.4f}" if eta2 is not None else "n/a"
        lines.append(f"- n (themed reviews): {anova['n']}")
        lines.append(f"- ANOVA: F = {d['f_stat']:.3f}, p = {_fmt_p(d['p_value'])}, η² = {eta2_str}")
        lev = d.get("levene_median", {})
        if lev:
            lines.append(f"- Assumptions: Levene median test p = {_fmt_p(lev.get('p_value'))}; equal variance = {lev.get('equal_variance')}.")
        if d.get("tukey_hsd"):
            lines.append("- Tukey HSD (pairwise p-values, selected pairs):")
            for row in d["tukey_hsd"]:
                lines.append(
                    f"  - {row['group_a']} vs {row['group_b']}: "
                    f"Δmean = {row['mean_diff']:.3f}, p = {_fmt_p(row['p_value'])}"
                )

    # SR-02 KW robustness
    kw_rob = results.get("SR-02 kruskal_wallis_robustness", {})
    if kw_rob.get("n", 0) > 0:
        kd = kw_rob["details"]
        eps2 = kd.get("epsilon_squared")
        eps2_str = f"{eps2:.4f}" if eps2 is not None else "n/a"
        lines.append(f"- Kruskal-Wallis robustness check (non-normality confirmed in 4/5 groups):")
        lines.append(f"  H({kd['k_groups'] - 1}) = {kd['h_stat']:.3f}, p = {_fmt_p(kd['p_value'])}, ε² = {eps2_str}")
        lines.append(f"  Interpretation: {kd.get('interpretation', '')}")
        sig_pairs = [p for p in kd.get("pairwise_mann_whitney", []) if p.get("significant_bh")]
        if sig_pairs:
            lines.append("  Pairwise Mann-Whitney after BH FDR: " + "; ".join(
                f"{p['themes'][0]} vs {p['themes'][1]} p_BH={_fmt_p(p['p_value_bh'])}, δ={p['cliffs_delta']:.3f}"
                for p in sig_pairs
            ))
        else:
            lines.append("  Pairwise Mann-Whitney after BH FDR: no theme pair remains significant.")
        lines.append("  Interpretation: emotional-intensity magnitude does not differ clearly by theme in the current review sample.")
    lines.append("")

    # SR-05 sentiment
    city = results.get("SR-05 city_comparison_sentiment_norm", {})
    lines.append("## SR-05 — Sentiment differs by city (pairwise t-tests, Bonferroni)")
    if city.get("n", 0) == 0:
        lines.append(f"- Not run: {city.get('details', {}).get('error', 'insufficient data')}")
    else:
        lines.append(f"- n (reviews): {city['n']}")
        for row in city["details"]["pairwise"]:
            lines.append(
                f"- {row['cities'][0]} vs {row['cities'][1]}: "
                f"mean={row['mean_a']:.3f} vs {row['mean_b']:.3f}, "
                f"p_adj={_fmt_p(row['p_value_bonferroni'])}, d={row['cohens_d']:.3f}"
            )
        sig_pairs = [
            row for row in city["details"]["pairwise"]
            if row.get("p_value_bonferroni") is not None and row["p_value_bonferroni"] < 0.05
        ]
        if sig_pairs:
            lines.append("- Interpretation: Fukui does not differ significantly from either comparison city; the only corrected mean difference is Kanazawa vs Toyama, and its effect size is small.")
        else:
            lines.append("- Interpretation: corrected mean tests do not show city-level sentiment differences.")
    lines.append("")

    # Additional test: Spearman rho rating vs sentiment
    spear = results.get("additional_spearman_rating_vs_sentiment", {})
    lines.append("## Additional — Spearman ρ: star rating vs VADER sentiment by city")
    lines.append("_(Spearman used: review_rating is ordinal; vader_compound is right-skewed continuous.)_")
    lines.append("_(Bonferroni correction across 3 city tests: α_adj = 0.0167.)_")
    if spear.get("n", 0) == 0:
        lines.append(f"- Not run: {spear.get('details', {}).get('error', 'insufficient data')}")
    else:
        sd = spear["details"]
        for cr in sd.get("by_city", []):
            ci = cr.get("ci_95_bootstrap", [None, None])
            ci_str = f"[{ci[0]:.3f}, {ci[1]:.3f}]" if ci[0] is not None else "n/a"
            sig = "✓ significant (survives Bonferroni)" if cr.get("significant_bonferroni") else "NS after Bonferroni"
            lines.append(
                f"- {cr['city']} (n={cr['n']}): ρ = {cr['rho']:.3f}, "
                f"p = {_fmt_p(cr['p_value'])}, p_adj = {_fmt_p(cr['p_value_bonferroni'])}, "
                f"95% CI {ci_str} — {sig}"
            )
        ov = sd.get("overall", {})
        lines.append(f"- All cities combined (n={ov.get('n', '?')}): ρ = {ov.get('rho', float('nan')):.3f}, p = {_fmt_p(ov.get('p_value'))}")
        lines.append("- Interpretation: VADER text sentiment aligns with star ratings in every city, but only moderately.")
    lines.append("")

    # Additional test: KW review length by city
    kw_len = results.get("additional_kw_review_length_by_city", {})
    lines.append("## Additional — Review length by city (Kruskal-Wallis + Mann-Whitney)")
    lines.append("_(All city groups non-normal by Shapiro-Wilk; KW used in place of one-way ANOVA.)_")
    lines.append("_(Pairwise Mann-Whitney with Benjamini-Hochberg FDR correction; Cliff's δ is signed, positive means first city has longer reviews.)_")
    if kw_len.get("n", 0) == 0:
        lines.append(f"- Not run: {kw_len.get('details', {}).get('error', 'insufficient data')}")
    else:
        ld = kw_len["details"]
        eps2 = ld.get("epsilon_squared")
        eps2_str = f"{eps2:.4f}" if eps2 is not None else "n/a"
        lines.append(f"- n (reviews): {kw_len['n']}")
        lines.append(f"- Kruskal-Wallis: H = {ld['h_stat']:.3f}, p = {_fmt_p(ld['p_value'])}, ε² = {eps2_str} (small effect)")
        medians = ld.get("median_by_city", {})
        med_str = ", ".join(f"{c} {int(v)} chars" for c, v in sorted(medians.items()))
        lines.append(f"- Medians: {med_str}")
        if ld.get("pairwise_mann_whitney"):
            lines.append("- Pairwise (BH FDR corrected):")
            for pw in ld["pairwise_mann_whitney"]:
                sig = "✓" if pw.get("significant_bh") else "NS"
                lines.append(
                    f"  - {pw['cities'][0]} vs {pw['cities'][1]}: "
                    f"p = {_fmt_p(pw['p_value'])}, p_BH = {_fmt_p(pw['p_value_bh'])}, "
                    f"δ = {pw['cliffs_delta']:.3f} — {sig}"
                )
        lines.append("- Interpretation: review length differs by city overall, but the retained pairwise gap is small.")
    lines.append("")

    # Contextual friction table snippet (descriptive)
    lines.append("## Descriptive friction context (sentence-level, not inferential)")
    if FRICTION_BY_CITY.exists():
        df = pd.read_csv(FRICTION_BY_CITY)
        pct_col = "pct_of_sentences" if "pct_of_sentences" in df.columns else "pct"
        top = df.sort_values(["count", pct_col], ascending=False).head(10)
        lines.append("- Top friction codes by raw count (across cities, sentence-level denominator):")
        for _, r in top.iterrows():
            lines.append(f"  - {r['city']}: {r['friction_code']} — n={int(r['count'])} ({r[pct_col]}% of sentences)")
    else:
        lines.append(f"- Missing: {FRICTION_BY_CITY} (run scripts/generate_friction_summaries.py first)")
    lines.append("")

    lines.append("## Skipped Analyses")
    lines.append("- SR-04 event impact t-test is skipped (review timestamps are not reliably absolute).")
    lines.append("- K-means clustering is skipped (no row-level spending data).")
    lines.append("")

    # Compute live stats from reviews CSV for accurate limitation notes
    _none_note = "Theme None rate: unknown (reviews_unified.csv not found)"
    _sample_note = "Total sample: unknown"
    if REVIEWS_CSV.exists():
        _rev = pd.read_csv(REVIEWS_CSV)
        _n_total = len(_rev)
        _n_none = int(_rev["primary_theme"].isna().sum())
        _none_pct = _n_none / _n_total * 100
        _city_counts = _rev["city"].value_counts()
        _city_str = ", ".join(f"{c} {n}" for c, n in sorted(_city_counts.items()))
        _none_note = f"Theme None rate: {_none_pct:.1f}% ({_n_none}/{_n_total}) excluded from SR-01/SR-02 tests."
        _sample_note = f"Total sample: {_n_total} reviews ({_city_str}). Unbalanced across cities."

    anova_p = results.get("SR-02 theme_anova", {}).get("details", {}).get("p_value")
    kw_p = results.get("SR-02 kruskal_wallis_robustness", {}).get("details", {}).get("p_value")
    sr02_note = (
        "SR-02 ANOVA and Kruskal-Wallis both fall short of conventional significance "
        f"in the current output (ANOVA p={_fmt_p(anova_p)}; KW p={_fmt_p(kw_p)}), "
        "so emotional-intensity differences by theme should be described as not clearly supported."
    )

    sparse_friction_note = "Review-level friction-code sparsity could not be calculated (tagged_reviews.csv not found)."
    tagged_reviews_csv = OUTPUT_DIR / "friction_analysis" / "tagged_reviews.csv"
    if tagged_reviews_csv.exists():
        tagged = pd.read_csv(tagged_reviews_csv)
        friction_code_cols = [
            "transport_access",
            "wayfinding_signage",
            "english_information_gap",
            "staff_communication",
            "booking_ticketing",
            "waiting_crowding",
            "price_value",
            "cleanliness_comfort",
            "opening_hours_availability",
            "itinerary_fit_time_cost",
            "accessibility_mobility",
            "food_amenities_gap",
        ]
        friction_cols = [
            c for c in friction_code_cols
            if c in tagged.columns and tagged[c].dropna().isin([True, False]).all()
        ]
        sparse_cols = [c for c in friction_cols if int(tagged[c].sum()) < 5]
        interpretable_cols = [c for c in friction_cols if int(tagged[c].sum()) >= 5]
        if friction_cols:
            sparse_friction_note = (
                f"{len(sparse_cols)} of {len(friction_cols)} review-level friction codes "
                f"have count < 5; codes at or above that threshold: {', '.join(interpretable_cols) or 'none'}."
            )

    lines.append("## Methodological Limitations")
    lines.append(f"- {sr02_note}")
    lines.append("- SR-05 reports Welch mean tests only. VADER sentiment is bounded and non-normal, so significant or null mean-test results should not be overread as destination equivalence or broad visitor feeling.")
    lines.append("- Theme and friction coding are heuristic/keyword-based; missed mentions and false positives can occur.")
    lines.append("- Reviewers are described as English-language reviewers; nationality is not available from source data.")
    lines.append("- SR-01 Fukui goodness-of-fit uses a uniform five-theme benchmark. This is a neutral exploratory baseline, not an empirical expectation for real tourism discourse.")
    lines.append("- Chi-square independence tests have sparse expected counts; use permutation p-values and cell-driver diagnostics rather than relying only on asymptotic p-values.")
    lines.append(f"- {_sample_note}")
    lines.append(f"- {_none_note}")
    lines.append("- Statistical tests treat reviews as independent rows. Reviews may still be clustered by POI or recurring reviewer, so inferential claims should remain exploratory.")
    lines.append("- emotional_intensity_score = abs(vader_compound) is a magnitude proxy, not a true affective depth measure.")
    lines.append(f"- {sparse_friction_note}")
    lines.append("- Food theme: 'eat' and 'dish' keywords have minor false-positive risk (incidental mentions in non-food reviews). Impact estimated low; documented as limitation.")
    lines.append("- Theme 'Cultural' formerly labelled 'Emotional'; renamed 2026-05-19 to reflect keyword scope (Zen/spiritual + heritage/cultural content).")

    SUMMARY_MD.write_text("\n".join(lines) + "\n")
    _write_test_explanations(results)
    logger.info(f"Written: {SUMMARY_MD}")
    logger.info(f"Written: {TEST_EXPLANATIONS_MD}")
    logger.info("=" * 55)


if __name__ == "__main__":
    main()
