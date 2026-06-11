#!/usr/bin/env python3
"""
statistical_validation.py — SR-01/SR-02/SR-05 statistical checks.

Reads:
  output/friction_analysis/reviews_unified.csv

Writes:
  output/statistical_results.json

Notes:
  - Unit of analysis is one review (row-level) as per reviews_unified.csv.
  - Chi-square tests exclude rows where primary_theme is None.
  - City sentiment comparisons use Welch's t-test with Bonferroni correction.

================================================================================
ACADEMIC TRACEABILITY OVERVIEW
================================================================================

Unit of analysis and independence
---------------------------------
Every statistical procedure in this module treats ONE REVIEW as one
observation, and reviews are modeled as INDEPENDENT draws. This is a
simplifying assumption, not an established fact: reviews are nested within
points of interest (POIs) and, potentially, within reviewers (a single
reviewer may contribute multiple reviews; reviews of the same POI share
unmodeled POI-level effects). Such clustering, if present, would deflate
standard errors and make p-values anti-conservative. We document this as a
known limitation rather than fit multilevel models, because (a) reviewer
identifiers are not reliably available across platforms and (b) per-POI
review counts are too small to estimate POI random effects stably. All
inferential claims downstream of this script should carry this caveat.

Reproducibility
---------------
All Monte Carlo procedures (permutation tests, bootstrap CIs) are seeded.
The master permutation seed defaults to 42 (PERMUTATION_SEED); per-test RNG
streams are derived deterministically from it via crc32 (see
_permutation_chi2_p) so that Monte Carlo error is statistically independent
across tests yet the entire output is reproducible from a single seed.

Test inventory (what each suite ID covers)
------------------------------------------
  SR-01a  theme_chi_square_gof              — GoF of Fukui theme mix vs uniform
  SR-01b  theme_chi_square_independence     — city × theme (all 5 themes)
  SR-01c  shared_theme_chi_square_independence — city × theme (4 shared themes)
  SR-02   theme_anova / sr02_kruskal_wallis_robustness — intensity by theme
  SR-05   city_comparison                   — pairwise city sentiment (Welch)
  (extra) spearman_rating_sentiment         — rating vs VADER monotonic assoc.
  (extra) kw_review_length_by_city          — review length by city (KW)
"""

import json
import os
import sys
import zlib
from dataclasses import asdict, dataclass
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils.logger import setup_logger

logger = setup_logger(__name__)

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
FRICTION_DIR = OUTPUT_DIR / "friction_analysis"
REVIEWS_CSV = FRICTION_DIR / "reviews_unified.csv"
RESULTS_JSON = OUTPUT_DIR / "statistical_results.json"

# THEMES: the full 5-theme coding scheme applied during qualitative coding.
# SHARED_CITY_THEMES: the 4 themes that are substantively meaningful in ALL
# three cities. "Dinosaur" is excluded from the shared set because it is a
# Fukui-specific destination theme (Fukui Prefectural Dinosaur Museum); its
# near-absence in Kanazawa/Toyama is a substantive fact about the destinations,
# not evidence against statistical independence, so including it would make
# the independence test answer a question we already know the answer to.
THEMES = ["Dinosaur", "Food", "Scenic", "Cultural", "Logistics"]
SHARED_CITY_THEMES = ["Food", "Scenic", "Cultural", "Logistics"]
CITIES = ["Fukui", "Kanazawa", "Toyama"]

# Bonferroni-adjusted per-comparison alpha for the family of 3 pairwise city
# comparisons (3 = C(3,2)). NOTE ON USAGE: throughout this module we report
# EITHER (a) the raw p compared against this adjusted alpha (0.05/3 ≈ 0.0167),
# OR (b) the Bonferroni-adjusted p-value min(3p, 1) compared against the
# nominal 0.05. These are mathematically equivalent decision rules; applying
# both simultaneously (adjusted p vs adjusted alpha) would DOUBLE-correct and
# must never be done. Output entries expose both forms so the thesis can quote
# whichever convention the committee prefers, but each implies the same
# accept/reject decision.
BONFERRONI_ALPHA = 0.05 / 3  # 3 pairwise city comparisons
REVIEW_DATE_CUTOFF = os.getenv("REVIEW_DATE_CUTOFF", "2024-06-01")
# Number of Monte Carlo permutations per permutation test. 10,000 gives a
# minimum attainable p of ~1e-4 (with the +1 correction, 1/(10000+1)) and a
# Monte Carlo standard error of roughly sqrt(p(1-p)/10000) — about ±0.002 at
# p = 0.05 — which is amply precise for the decisions made in this thesis.
PERMUTATION_N = int(os.getenv("STATS_PERMUTATIONS", "10000"))
# Single master seed (default 42) from which all per-test RNG streams are
# deterministically derived; see _permutation_chi2_p for the derivation.
PERMUTATION_SEED = int(os.getenv("STATS_PERMUTATION_SEED", "42"))


@dataclass
class TestResult:
    """Uniform container for one test suite's output.

    Attributes:
        name:    Stable identifier (includes the SR-xx suite ID where
                 applicable) used as the lookup key in statistical_results.json.
        n:       Number of review-level observations actually used by the test
                 AFTER all filtering (theme/city/NaN exclusions). This is the
                 effective sample size to report in the thesis, which may be
                 smaller than the raw row count of reviews_unified.csv.
        details: Test-specific payload: statistics, p-values, effect sizes,
                 assumption checks, and interpretation notes.
    """
    name: str
    n: int
    details: dict


def _load_reviews() -> pd.DataFrame:
    """Load the unified review-level dataset (one row = one review).

    The CSV is produced upstream by the friction-analysis pipeline; this
    script deliberately performs NO cleaning or imputation of its own so that
    the statistical results are traceable to exactly one frozen input file.
    """
    if not REVIEWS_CSV.exists():
        raise FileNotFoundError(f"Missing input: {REVIEWS_CSV}")
    df = pd.read_csv(REVIEWS_CSV)
    return df


def input_data_audit(df: pd.DataFrame) -> TestResult:
    """Deterministic audit of assumptions required before interpreting tests.

    PURPOSE
    -------
    This is not a hypothesis test; it is a pre-registration-style integrity
    gate. Every downstream test assumes the input frame satisfies certain
    structural invariants (columns present, derived columns computed by the
    documented formulas, dates within the study window, etc.). Rather than
    assume these silently, we verify them and write the verdicts into the
    results JSON so the thesis can cite a machine-checked audit trail.

    WHAT IS CHECKED AND WHY
    -----------------------
    - required columns: downstream tests index these by name; a missing
      column would otherwise fail deep inside a test with an opaque error.
    - all three cities present / review_id unique / no (city, review_text)
      duplicates: guards against partial scrapes and double-ingestion, both
      of which would silently bias counts. Duplicate reviews would also
      violate the independence assumption in an especially direct way.
    - all_review_language_en: the VADER sentiment lexicon is English-only;
      non-English text would yield meaningless compound scores, so the
      pipeline restricts to English reviews and we verify that here.
    - date parsing + cutoff: confirms the study window (reviews on/after
      REVIEW_DATE_CUTOFF, default 2024-06-01) was applied upstream.
    - sentiment_norm formula check: sentiment_norm must equal
      (vader_compound + 1)/2, i.e. VADER's [-1, 1] compound rescaled to
      [0, 1]. Verified to a tolerance of 1e-5 (CSV round-tripping precision).
    - emotional_intensity formula check: emotional_intensity_score must equal
      |vader_compound|. IMPORTANT INTERPRETIVE CAVEAT (see SR-02): this is a
      MAGNITUDE-of-polarity proxy, not a validated measure of affective
      depth. The audit verifies only the arithmetic, not the construct.
    - range checks: both derived scores must lie in [0, 1] by construction;
      a violation would indicate upstream corruption.

    The 'valid' flag is the conjunction of all checks; any False value means
    downstream results should not be interpreted until the input is fixed.
    """
    required = [
        "city", "review_id", "review_date", "review_rating", "review_text",
        "review_language", "vader_compound", "sentiment_norm",
        "emotional_intensity_score", "primary_theme",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        # Short-circuit: with columns missing, none of the formula/range
        # checks below can even be computed, so report and bail out.
        return TestResult(
            name="input_data_audit",
            n=int(len(df)),
            details={"valid": False, "missing_columns": missing},
        )

    # Recompute the two derived columns from first principles so the audit is
    # independent of the upstream code that originally produced them.
    sentiment_expected = (df["vader_compound"].astype(float) + 1.0) / 2.0
    intensity_expected = df["vader_compound"].astype(float).abs()
    # errors="coerce" maps unparseable dates to NaT, which the
    # 'all_dates_parse' check below then flags rather than crashing here.
    dates = pd.to_datetime(df["review_date"], utc=True, errors="coerce", format="mixed")
    cutoff = pd.Timestamp(REVIEW_DATE_CUTOFF, tz="UTC")

    # Tolerance for float comparison: derived columns pass through CSV
    # serialization, so exact equality cannot be expected; 1e-5 is far below
    # any substantively meaningful difference on a [0, 1] scale.
    formula_tol = 1e-5
    sentiment_mismatch = int((sentiment_expected - df["sentiment_norm"].astype(float)).abs().gt(formula_tol).sum())
    intensity_mismatch = int((intensity_expected - df["emotional_intensity_score"].astype(float)).abs().gt(formula_tol).sum())
    language_values = sorted(str(v) for v in df["review_language"].dropna().unique())
    city_counts = {str(k): int(v) for k, v in df["city"].value_counts().sort_index().items()}
    theme_counts = {
        str(k): int(v)
        for k, v in df["primary_theme"].fillna("None").value_counts().sort_index().items()
    }
    # Reviews with no codable primary theme are EXCLUDED from all theme-based
    # tests (SR-01, SR-02). The count and percentage are recorded here so the
    # thesis can report the exclusion rate transparently.
    theme_none_n = int(df["primary_theme"].isna().sum())
    n = int(len(df))

    checks = {
        "required_columns_present": True,
        "all_cities_present": set(df["city"].dropna().unique()) == set(CITIES),
        "review_id_unique": not bool(df["review_id"].duplicated().any()),
        "city_text_duplicates": int(df.duplicated(["city", "review_text"]).sum()) == 0,
        "all_review_language_en": set(language_values) == {"en"},
        "all_dates_parse": not bool(dates.isna().any()),
        "all_dates_on_or_after_cutoff": not bool((dates < cutoff).any()),
        "ratings_complete": not bool(df["review_rating"].isna().any()),
        "sentiment_norm_formula_ok": sentiment_mismatch == 0,
        "emotional_intensity_formula_ok": intensity_mismatch == 0,
        "sentiment_norm_range_ok": bool(df["sentiment_norm"].between(0, 1, inclusive="both").all()),
        "emotional_intensity_range_ok": bool(df["emotional_intensity_score"].between(0, 1, inclusive="both").all()),
    }

    return TestResult(
        name="input_data_audit",
        n=n,
        details={
            "valid": all(checks.values()),
            "review_date_cutoff": REVIEW_DATE_CUTOFF,
            "checks": checks,
            "city_counts": city_counts,
            "language_values": language_values,
            "theme_counts_including_none": theme_counts,
            "theme_none_n": theme_none_n,
            "theme_none_pct": float(theme_none_n / n * 100) if n else None,
            "sentiment_norm_formula_mismatches": sentiment_mismatch,
            "emotional_intensity_formula_mismatches": intensity_mismatch,
        },
    )


def _chi2_stat_from_table(table: np.ndarray) -> tuple[float, int, np.ndarray]:
    """Return Pearson chi-square statistic, df, and expected counts.

    Thin wrapper around scipy.stats.chi2_contingency used by the permutation
    test, which needs only the STATISTIC (the asymptotic p-value returned by
    SciPy is discarded — the permutation reference distribution replaces it).
    Expected counts under independence are E_ij = (row_i total × col_j total)/n.
    """
    chi2, _p, dof, expected = stats.chi2_contingency(table)
    return float(chi2), int(dof), expected


def _permutation_chi2_p(
    city_labels: np.ndarray,
    theme_labels: np.ndarray,
    cities: list[str],
    themes: list[str],
    observed_chi2: float,
) -> dict:
    """Permutation p-value for independence, preserving city and theme margins.

    WHAT THIS TESTS
    ---------------
    H0: city and theme labels are independent, CONDITIONAL on the observed
    margins. The Pearson chi-square statistic is used purely as a measure of
    table-level discrepancy; its null distribution is generated empirically
    by permutation rather than taken from the asymptotic chi-square law.

    WHY A PERMUTATION TEST (RATIONALE OVER ALTERNATIVES)
    ----------------------------------------------------
    The asymptotic chi-square approximation is unreliable when expected cell
    counts are sparse (the classical guideline requires all expected counts
    ≥ 5, which several of our tables violate — most severely the tables that
    include the Fukui-specific 'Dinosaur' theme). Alternatives considered:
      * Fisher's exact test — exact, but SciPy supports it only for 2×2
        tables; our tables are up to 3×5. Network-algorithm generalizations
        exist but are not in our dependency set.
      * Yates continuity correction — only defined for 2×2 and known to be
        over-conservative.
      * Collapsing sparse categories — discards exactly the substantive
        distinctions (theme identities) the research questions are about.
    The Monte Carlo permutation test sidesteps all of this: shuffling the
    theme labels against the FIXED city labels holds BOTH margins fixed
    (each permuted table has the same row totals — city sizes are untouched —
    and the same column totals — the multiset of theme labels is merely
    reordered). This realizes the conditional-on-margins null, i.e. a Monte
    Carlo approximation to the exact conditional test, and its validity does
    NOT depend on expected cell counts. It is therefore reported even where
    the asymptotic result is suppressed (see suppression logic in
    _theme_chi_square_independence_for_themes).

    P-VALUE CONSTRUCTION
    --------------------
    p = (exceed + 1) / (valid + 1), the add-one estimator of Phipson & Smyth
    (2010, "Permutation p-values should never be zero"). The +1 counts the
    observed table itself as one realization from the null, which (a) makes
    the estimator strictly positive — a Monte Carlo p of exactly 0 is never
    justifiable — and (b) keeps the test valid (the resulting p-values are
    stochastically no smaller than uniform under H0).

    SEEDING / REPRODUCIBILITY
    -------------------------
    A distinct RNG stream is derived per test by hashing the test's identity
    (city list, theme list, observed statistic) with crc32 and adding the
    digest (mod 2^16) to the master seed. Consequence: Monte Carlo error is
    independent ACROSS tests (no two tests share a permutation sequence, so
    their MC errors cannot be correlated), yet the entire suite is exactly
    reproducible from the single master seed (default 42).

    NUMERICAL DETAILS
    -----------------
    - 'stat >= observed - 1e-12': the tiny tolerance guards against floating
      point round-off declaring an exactly-tied permuted statistic as not
      exceeding; ties must count toward 'exceed' for validity.
    - chi2_contingency raises ValueError when a permuted table contains an
      all-zero row/column (possible in small subtables); such permutations
      are skipped and the denominator uses 'valid' rather than PERMUTATION_N
      so the p-value remains a proper proportion of evaluable permutations.

    INTERPRETATION LIMITS
    ---------------------
    The test inherits the review-independence assumption (see module
    docstring); clustering by POI/reviewer would invalidate the exchange-
    ability of theme labels under H0. The minimum attainable p is
    1/(valid+1), so "p < 1e-4" claims beyond the permutation resolution are
    not supported.
    """
    if PERMUTATION_N <= 0:
        return {"enabled": False}

    # Derive a distinct stream per test so Monte Carlo error is independent
    # across tests while staying reproducible from PERMUTATION_SEED.
    stream = zlib.crc32(f"{cities}|{themes}|{observed_chi2:.6f}".encode()) % (2**16)
    rng = np.random.default_rng(PERMUTATION_SEED + stream)
    city_to_idx = {city: i for i, city in enumerate(cities)}
    theme_to_idx = {theme: i for i, theme in enumerate(themes)}
    city_codes = np.array([city_to_idx[v] for v in city_labels], dtype=int)
    theme_codes = np.array([theme_to_idx[v] for v in theme_labels], dtype=int)
    shape = (len(cities), len(themes))
    exceed = 0
    valid = 0
    # Shuffle in place each iteration: city_codes stay fixed (row margin
    # preserved) while the theme label multiset is reordered (column margin
    # preserved) — the both-margins-fixed conditional null described above.
    shuffled = theme_codes.copy()
    for _ in range(PERMUTATION_N):
        rng.shuffle(shuffled)
        perm_ct = np.zeros(shape, dtype=int)
        np.add.at(perm_ct, (city_codes, shuffled), 1)
        try:
            stat, _dof, _expected = _chi2_stat_from_table(perm_ct)
        except ValueError:
            # Degenerate table (zero margin) — not evaluable; excluded from
            # both numerator and denominator.
            continue
        valid += 1
        if stat >= observed_chi2 - 1e-12:
            exceed += 1

    return {
        "enabled": True,
        "method": "Permutation test of Pearson chi-square statistic with fixed city/theme margins",
        "n_permutations": PERMUTATION_N,
        "seed": PERMUTATION_SEED,
        "valid_permutations": valid,
        # Phipson & Smyth (2010) add-one estimator; never exactly zero.
        "p_value": float((exceed + 1) / (valid + 1)) if valid else None,
    }


def _pearson_residuals(observed: pd.DataFrame, expected: np.ndarray) -> dict:
    """(O - E)/sqrt(E). Variance < 1, so NOT comparable to ±1.96 z cutoffs.

    Pearson residuals are the signed square roots of each cell's chi-square
    contribution and are the conventional first look at WHERE association
    lives in a table. However, under independence their variance is
    (1 - p_row)(1 - p_col) < 1, so they are systematically SHRUNK relative
    to a standard normal: comparing them to ±1.96 is conservative and,
    strictly, incorrect. They are reported only for continuity with common
    textbook presentations; the thesis should cite the Haberman ADJUSTED
    residuals (next function) for any per-cell significance statement.
    """
    residuals = (observed.to_numpy(dtype=float) - expected) / np.sqrt(expected)
    return pd.DataFrame(residuals, index=observed.index, columns=observed.columns).round(4).to_dict()


def _adjusted_standardized_residuals(observed: pd.DataFrame, expected: np.ndarray) -> dict:
    """Haberman adjusted residuals: (O - E)/sqrt(E(1-p_row)(1-p_col)).

    Approximately N(0,1) under independence, so these ARE comparable to ±1.96.

    Haberman (1973) showed that dividing the raw (O - E) deviation by its
    actual standard deviation under independence — sqrt(E(1-p_row)(1-p_col)),
    where p_row and p_col are the marginal proportions — yields residuals
    that are asymptotically standard normal. This corrects the variance
    deflation of plain Pearson residuals (see _pearson_residuals) and makes
    the ±1.96 (5%) / ±2.58 (1%) z-cutoffs legitimate per-cell screens.
    Both residual types are written to the JSON for transparency; the thesis
    should cite THE ADJUSTED form. Caveats: (a) per-cell screening across
    many cells is itself a multiplicity problem — treat flagged cells as
    descriptive localization of the omnibus result, not independent tests;
    (b) the normal approximation degrades in cells with very small E, the
    same sparsity issue that motivates the permutation omnibus test.
    """
    obs = observed.to_numpy(dtype=float)
    n = obs.sum()
    row_p = obs.sum(axis=1, keepdims=True) / n
    col_p = obs.sum(axis=0, keepdims=True) / n
    denom = np.sqrt(expected * (1.0 - row_p) * (1.0 - col_p))
    # Cells where the denominator is 0 (a margin proportion of exactly 1,
    # only possible in degenerate tables) are emitted as NaN rather than inf.
    residuals = np.divide(obs - expected, denom, out=np.full_like(obs, np.nan), where=denom > 0)
    return pd.DataFrame(residuals, index=observed.index, columns=observed.columns).round(4).to_dict()


def _cramers_v_bias_corrected(table: np.ndarray, chi2: float) -> float | None:
    """Bergsma (2013) bias-corrected Cramér's V.

    Uncorrected Cramér's V = sqrt(chi2 / (n * min(r-1, c-1))) is a biased
    estimator of population association: even under exact independence its
    expectation is positive, and the bias grows as n shrinks and as the
    table gets larger/sparser — precisely our situation. Bergsma's
    correction (following Bartlett-type bias removal) subtracts the
    independence-expectation (r-1)(c-1)/(n-1) from phi² (flooring at 0 so
    the corrected V cannot be imaginary) and analogously shrinks the row and
    column dimension terms. The corrected V is reported ALONGSIDE the
    uncorrected V: the uncorrected value enables comparison with literature
    that reports the classical statistic; the corrected value is the better
    point estimate of association strength for this study's small-n, sparse
    tables and is the one the thesis should emphasize. Returns None for
    degenerate inputs (n ≤ 1 or corrected dimension ≤ 1).
    """
    n = table.sum()
    if n <= 1:
        return None
    r, c = table.shape
    phi2 = chi2 / n
    # Subtract the expected phi² under independence; floor at 0.
    phi2_corr = max(0.0, phi2 - (r - 1) * (c - 1) / (n - 1))
    # Bias-corrected effective dimensions.
    r_corr = r - (r - 1) ** 2 / (n - 1)
    c_corr = c - (c - 1) ** 2 / (n - 1)
    denom = min(r_corr - 1, c_corr - 1)
    return float(np.sqrt(phi2_corr / denom)) if denom > 0 else None


def _chi2_cell_contributions(observed: pd.DataFrame, expected: np.ndarray) -> list[dict]:
    """Per-cell chi-square contributions (O-E)²/E, sorted descending.

    Purely descriptive decomposition of the omnibus statistic: identifies
    WHICH city × theme cells drive the overall chi-square. 'pct_of_chi2'
    expresses each cell's share of the total. No inference is attached —
    use the adjusted standardized residuals for per-cell significance.
    """
    contrib = (observed.to_numpy(dtype=float) - expected) ** 2 / expected
    total = float(np.sum(contrib))
    rows = []
    for i, city in enumerate(observed.index):
        for j, theme in enumerate(observed.columns):
            rows.append({
                "city": str(city),
                "theme": str(theme),
                "observed": int(observed.iloc[i, j]),
                "expected": float(expected[i, j]),
                "chi2_contribution": float(contrib[i, j]),
                "pct_of_chi2": float(contrib[i, j] / total * 100) if total > 0 else None,
            })
    return sorted(rows, key=lambda r: r["chi2_contribution"], reverse=True)


def theme_chi_square_gof(df: pd.DataFrame) -> TestResult:
    """SR-01: Chi-square GoF on Fukui theme distribution vs uniform expected.

    WHAT THIS TESTS (SR-01a)
    ------------------------
    H0: among themed Fukui reviews, the five primary themes occur with equal
    probability (1/5 each). One-way Pearson chi-square goodness-of-fit with
    df = k - 1 = 4.

    WHY A UNIFORM BENCHMARK
    -----------------------
    The uniform distribution is a deliberately NEUTRAL, EXPLORATORY
    benchmark — it is NOT an empirical expectation that themes "should" be
    equally common. No external base rates for theme prevalence in Hokuriku
    tourism reviews exist that could supply a substantively motivated
    expected vector, and inventing one would smuggle in assumptions. The
    test therefore answers only the descriptive question "is the Fukui theme
    mix distinguishable from a flat profile?", which frames the subsequent
    discussion of which themes dominate. Rejection of uniformity carries no
    causal or comparative meaning by itself.

    ASSUMPTIONS
    -----------
    - Independent observations (one review = one observation; see module
      docstring for the clustering caveat).
    - Expected counts adequate for the chi-square approximation: here
      E = n/5 in every cell, comfortably above the ≥5 guideline for any
      realistic n, so no exact/permutation fallback is needed for this test.

    EFFECT SIZE CAVEAT
    ------------------
    Cramér's V is computed as sqrt(chi2 / (n(k-1))). Applying Cramér's V to
    a ONE-WAY goodness-of-fit table is a reporting CONVENTION (treating the
    comparison as if against a 1 × k reference), not the canonical two-way
    contingency definition. It is provided as a familiar 0–1 magnitude
    yardstick only; it should not be numerically compared against the V
    values from the two-way independence tests below, whose sampling model
    differs.
    """
    # Scope: Fukui only, themed reviews only (primary_theme non-null and in
    # the coding scheme). Untemed reviews are excluded by design; the
    # exclusion rate is reported by input_data_audit.
    d = df[(df["city"] == "Fukui") & df["primary_theme"].notna()].copy()
    d = d[d["primary_theme"].isin(THEMES)]
    # reindex(fill_value=0) makes the observed vector explicitly include any
    # theme with zero Fukui reviews, keeping df = k - 1 honest.
    observed = d["primary_theme"].value_counts().reindex(THEMES, fill_value=0).to_numpy()
    n = int(observed.sum())
    if n == 0:
        return TestResult(
            name="SR-01 theme_chi_square_gof",
            n=0,
            details={"error": "No themed Fukui reviews available."},
        )
    # Uniform expected counts: n/5 per theme (see benchmark rationale above).
    expected = np.full_like(observed, fill_value=n / len(THEMES), dtype=float)
    chi2, p = stats.chisquare(f_obs=observed, f_exp=expected)
    k = len(THEMES)
    # One-way Cramér's V convention — see effect-size caveat in docstring.
    cramers_v = float(np.sqrt(chi2 / (n * (k - 1)))) if n > 0 else None
    return TestResult(
        name="SR-01 theme_chi_square_gof",
        n=n,
        details={
            "themes": THEMES,
            "observed_counts": observed.tolist(),
            "expected_uniform": expected.tolist(),
            "chi2": float(chi2),
            "df": int(k - 1),
            "p_value": float(p),
            "cramers_v": cramers_v,
        },
    )


def _theme_chi_square_independence_for_themes(
    df: pd.DataFrame,
    themes: list[str],
    result_name: str,
    scope_note: str,
) -> TestResult:
    """City × theme chi-square independence for a selected theme set.

    WHAT THIS TESTS (SR-01b when themes=THEMES, SR-01c when SHARED_CITY_THEMES)
    ---------------------------------------------------------------------------
    H0: the distribution of primary themes is the same in every city
    (equivalently, city and theme are independent in the r × c contingency
    table of review counts). Pearson chi-square test of independence with
    df = (r-1)(c-1), supplemented by a margins-fixed permutation test.

    WHY THIS TEST, AND WHY THE PERMUTATION SUPPLEMENT
    -------------------------------------------------
    The chi-square test of independence is the standard procedure for
    nominal × nominal association and matches the data type exactly (city
    and theme are both unordered categories — no ordinal alternative such as
    a trend test applies). However, the ASYMPTOTIC chi-square reference
    distribution is unreliable when expected counts are sparse (classical
    guideline: all E_ij ≥ 5). Several of our subtables violate this —
    expectedly so where the Fukui-specific 'Dinosaur' theme appears.
    Therefore EVERY table is also evaluated with the permutation test
    documented in _permutation_chi2_p, which conditions on both margins and
    remains valid regardless of expected counts. Where both are reported and
    disagree, the permutation p is authoritative.

    ASSUMPTION CHECKS AND REPORTING
    -------------------------------
    - 'expected_min' and 'assumption_expected_ge5' record the smallest
      expected count and whether the ≥5 guideline holds, so the reader can
      judge the asymptotic result's credibility per table.
    - Asymptotic results are SUPPRESSED entirely (not merely flagged) when
      expected_min < 1.0 — a 5× violation of the guideline at which point
      the chi-square approximation produces numbers that are meaningless
      even directionally. The permutation p is still reported in those cases
      because its validity does not depend on expected counts.

    EFFECT SIZES
    ------------
    Cramér's V (canonical two-way form) and the Bergsma (2013) bias-corrected
    V are both reported; the corrected form should be cited because the
    uncorrected statistic overstates association at small n / sparse tables
    (see _cramers_v_bias_corrected).

    RESIDUAL DIAGNOSTICS
    --------------------
    Two residual matrices are emitted: plain Pearson residuals (variance < 1,
    NOT z-comparable — kept for textbook continuity) and Haberman adjusted
    standardized residuals (≈ N(0,1), comparable to ±1.96 — the form the
    thesis should cite). See the respective helper docstrings.

    PAIRWISE FOLLOW-UPS AND MULTIPLICITY
    ------------------------------------
    The three pairwise city subtables (2 × c each) localize any omnibus
    association. Bonferroni correction over the family of 3 comparisons is
    applied as adjusted p = min(3p, 1) compared against 0.05, equivalent to
    raw p vs 0.0167 — never both at once (that would double-correct; see
    the BONFERRONI_ALPHA comment). Bonferroni is chosen over BH here because
    the family is tiny (3) and strong familywise control is preferred for
    confirmatory pairwise claims.

    INTERPRETATION LIMITS
    ---------------------
    Association ≠ causation; the test describes compositional differences in
    what reviewers WRITE ABOUT, not differences in visitor experience. The
    review-independence assumption (module docstring) applies in full.
    """
    d = df[df["primary_theme"].notna()].copy()
    d = d[d["primary_theme"].isin(themes) & d["city"].isin(CITIES)]
    if d.empty:
        return TestResult(
            name=result_name,
            n=0,
            details={"error": "No themed reviews available."},
        )

    # reindex with fill_value=0 fixes row/column order and keeps zero cells
    # explicit so df and expected counts are computed over the full grid.
    ct = pd.crosstab(d["city"], d["primary_theme"]).reindex(index=CITIES, columns=themes, fill_value=0)
    chi2, p, dof, expected = stats.chi2_contingency(ct.to_numpy())
    n_total = int(len(d))
    r, c = ct.shape
    # Canonical two-way Cramér's V (uncorrected; bias-corrected form below).
    cramers_v_overall = float(np.sqrt(chi2 / (n_total * min(r - 1, c - 1)))) if n_total > 0 else None
    exp_min = float(np.min(expected)) if expected.size else None
    # Margins-fixed permutation test — valid irrespective of expected counts.
    permutation = _permutation_chi2_p(
        d["city"].to_numpy(),
        d["primary_theme"].to_numpy(),
        CITIES,
        themes,
        float(chi2),
    )
    overall = {
        "themes": themes,
        "scope_note": scope_note,
        "chi2": float(chi2),
        "df": int(dof),
        "p_value": float(p),
        "p_value_permutation": permutation.get("p_value"),
        "permutation": permutation,
        "cramers_v": cramers_v_overall,
        "cramers_v_bias_corrected": _cramers_v_bias_corrected(ct.to_numpy(), float(chi2)),
        "contingency_table": ct.to_dict(),
        "expected_min": exp_min,
        "assumption_expected_ge5": exp_min is not None and exp_min >= 5,
        "pearson_residuals": _pearson_residuals(ct, expected),
        "adjusted_standardized_residuals": _adjusted_standardized_residuals(ct, expected),
        "residual_note": (
            "Use adjusted_standardized_residuals against ±1.96; pearson_residuals "
            "have variance < 1 and are not z-comparable."
        ),
        "top_chi2_cell_contributions": _chi2_cell_contributions(ct, expected)[:10],
    }

    # Threshold below which the chi-square approximation is too unreliable to
    # report even directionally. Standard guidance is ≥5; we suppress at <1.0
    # (a 5× violation) to avoid citing numbers that are meaningless.
    # Rationale for suppressing rather than merely flagging: a printed
    # chi-square/p pair tends to get quoted regardless of caveats; omitting
    # it forces the (valid) permutation p to be the cited result.
    _SUPPRESS_EXPECTED_THRESHOLD = 1.0

    pairwise = []
    for a, b in combinations(CITIES, 2):
        sub = ct.loc[[a, b]].to_numpy()
        chi2_ab, p_ab, dof_ab, expected_ab = stats.chi2_contingency(sub)
        n_ab = int(sub.sum())
        r_ab, c_ab = sub.shape
        cramers_v_ab = float(np.sqrt(chi2_ab / (n_ab * min(r_ab - 1, c_ab - 1)))) if n_ab > 0 else None
        exp_min_ab = float(np.min(expected_ab)) if expected_ab.size else None
        assumption_ok = exp_min_ab is not None and exp_min_ab >= 5
        suppressed = exp_min_ab is not None and exp_min_ab < _SUPPRESS_EXPECTED_THRESHOLD
        entry: dict = {
            "cities": [a, b],
            "expected_min": exp_min_ab,
            "assumption_expected_ge5": assumption_ok,
            "suppressed": suppressed,
        }
        # The permutation test conditions on the observed margins and stays
        # valid regardless of expected counts, so it is reported even when the
        # asymptotic chi-square approximation is suppressed.
        sub_df = d[d["city"].isin([a, b])]
        permutation_ab = _permutation_chi2_p(
            sub_df["city"].to_numpy(),
            sub_df["primary_theme"].to_numpy(),
            [a, b],
            themes,
            float(chi2_ab),
        )
        # Bonferroni over the 3-comparison family: adjusted p = min(3p, 1),
        # to be compared against alpha = 0.05 ('alpha_for_adjusted_p').
        # Equivalent to comparing the raw p against 0.0167; do NOT apply both.
        entry.update({
            "p_value_permutation": permutation_ab.get("p_value"),
            "p_value_permutation_bonferroni": (
                float(min(permutation_ab["p_value"] * 3, 1.0))
                if permutation_ab.get("p_value") is not None else None
            ),
            "permutation": permutation_ab,
            "alpha_for_adjusted_p": 0.05,
        })
        if suppressed:
            entry["suppressed_reason"] = (
                f"expected_min={exp_min_ab:.2f} < {_SUPPRESS_EXPECTED_THRESHOLD} — "
                "asymptotic chi-square approximation invalid; "
                "exact permutation p-value reported instead"
            )
        else:
            # Asymptotic results only included when not suppressed. Note the
            # dual Bonferroni representation: 'p_value_bonferroni' (adjusted
            # p vs 0.05) and 'alpha_bonferroni' (raw p vs 0.0167) encode the
            # SAME decision rule in two conventions — use one, never both.
            entry.update({
                "chi2": float(chi2_ab),
                "df": int(dof_ab),
                "p_value": float(p_ab),
                "p_value_bonferroni": float(min(p_ab * 3, 1.0)),
                "alpha_bonferroni": BONFERRONI_ALPHA,
                "cramers_v": cramers_v_ab,
                "cramers_v_bias_corrected": _cramers_v_bias_corrected(sub, float(chi2_ab)),
            })
        pairwise.append(entry)

    return TestResult(
        name=result_name,
        n=int(len(d)),
        details={"overall": overall, "pairwise": pairwise},
    )


def theme_chi_square_independence(df: pd.DataFrame) -> TestResult:
    """SR-01: City × theme chi-square independence using all primary themes.

    SR-01b: the full 3 × 5 table INCLUDING the Fukui-specific 'Dinosaur'
    theme. Because Dinosaur reviews are structurally concentrated in Fukui,
    expected-count violations (and a strong association) are anticipated by
    construction here; this variant is retained for completeness and to
    quantify how much of the overall association the Dinosaur theme alone
    accounts for. The shared-theme variant (SR-01c) is the substantively
    fair cross-city comparison. See _theme_chi_square_independence_for_themes
    for the full methodological documentation.
    """
    return _theme_chi_square_independence_for_themes(
        df,
        THEMES,
        "SR-01 theme_chi_square_independence",
        "All primary themes, including Dinosaur. Dinosaur is substantively Fukui-specific, so expected-count caveats are expected.",
    )


def shared_theme_chi_square_independence(df: pd.DataFrame) -> TestResult:
    """SR-01: City × shared-theme chi-square independence excluding Fukui-specific Dinosaur.

    SR-01c: the 3 × 4 table restricted to themes that exist as comparable
    categories in all three cities (Food, Scenic, Cultural, Logistics).
    Excluding Dinosaur removes the structurally-Fukui cells whose deviation
    from independence is a destination fact rather than a finding, yielding
    a like-for-like compositional comparison. This is the SR-01 variant the
    thesis should treat as primary for cross-city claims. See
    _theme_chi_square_independence_for_themes for full documentation.
    """
    return _theme_chi_square_independence_for_themes(
        df,
        SHARED_CITY_THEMES,
        "SR-01 shared_theme_chi_square_independence",
        "Shared cross-city tourism themes only; Dinosaur is excluded because it is a Fukui-specific destination theme rather than a comparable city-wide theme.",
    )


def _tukey_hsd(df: pd.DataFrame, group_col: str, value_col: str) -> list[dict]:
    """
    Tukey HSD pairwise comparisons (no statsmodels dependency).
    Uses the studentized range distribution from SciPy.

    METHOD AND RATIONALE
    --------------------
    Post-hoc pairwise mean comparisons following a one-way ANOVA, with
    familywise error controlled via the studentized range distribution.
    Tukey's procedure is preferred over running pairwise t-tests with
    Bonferroni because it is exact for the all-pairwise-comparisons family
    (Bonferroni is conservative for this family), and over Scheffé because
    we only need pairwise contrasts, for which Scheffé is needlessly wide.

    UNEQUAL GROUP SIZES (TUKEY-KRAMER)
    ----------------------------------
    Our theme groups have unequal n. The standard error used here,
    SE = sqrt(MSE/2 × (1/n_a + 1/n_b)), is the Tukey-KRAMER generalization,
    which reduces to classical Tukey HSD under equal n and is known to be
    (slightly conservatively) valid under unequal n.

    IMPLEMENTATION NOTES
    --------------------
    - Implemented directly against scipy.stats.studentized_range to avoid a
      statsmodels dependency; q = |mean_a - mean_b| / SE, with p =
      P(Q_{k, df_error} ≥ q).
    - MSE and df_error are the pooled within-group variance and error df of
      the one-way ANOVA, recomputed here from the same groups.

    ASSUMPTIONS / LIMITS
    --------------------
    Inherits the ANOVA assumptions (normal residuals, homoscedasticity,
    independence). Since Shapiro-Wilk rejects normality for the intensity
    groups (see theme_anova), these p-values rely on large-sample robustness;
    the Kruskal-Wallis suite provides the distribution-free counterpart.
    """
    d = df[[group_col, value_col]].dropna().copy()
    groups = {g: vals[value_col].to_numpy(dtype=float) for g, vals in d.groupby(group_col)}
    if len(groups) < 2:
        return []

    # ANOVA components for MSE
    all_vals = np.concatenate(list(groups.values()))
    grand_mean = float(np.mean(all_vals))
    ss_within = 0.0
    df_error = 0
    for vals in groups.values():
        ss_within += float(np.sum((vals - float(np.mean(vals))) ** 2))
        df_error += max(len(vals) - 1, 0)
    if df_error <= 0:
        return []
    mse = ss_within / df_error

    k = len(groups)
    comparisons = []
    for a, b in combinations(sorted(groups.keys()), 2):
        xa = groups[a]
        xb = groups[b]
        na = len(xa)
        nb = len(xb)
        mean_a = float(np.mean(xa))
        mean_b = float(np.mean(xb))
        diff = mean_a - mean_b
        # Tukey-Kramer SE for unequal group sizes (see docstring).
        se = np.sqrt(mse / 2.0 * (1.0 / na + 1.0 / nb))
        q = float(abs(diff) / se) if se > 0 else float("inf")
        p = float(stats.studentized_range.sf(q, k, df_error))
        comparisons.append({
            "group_a": a,
            "group_b": b,
            "mean_a": mean_a,
            "mean_b": mean_b,
            "mean_diff": diff,
            "q_stat": q,
            "p_value": p,
            "df_error": int(df_error),
            "mse": float(mse),
        })
    return comparisons


def theme_anova(df: pd.DataFrame) -> TestResult:
    """SR-02: ANOVA emotional_intensity_score ~ primary_theme + Tukey HSD.

    WHAT THIS TESTS
    ---------------
    H0: mean emotional_intensity_score is equal across the five primary
    themes. One-way fixed-effects ANOVA (F-test), with Tukey-Kramer HSD
    post-hocs for pairwise localization.

    DEPENDENT VARIABLE CAVEAT (CRITICAL FOR INTERPRETATION)
    -------------------------------------------------------
    emotional_intensity_score = |vader_compound|, the absolute value of the
    VADER compound polarity. This is a MAGNITUDE-OF-POLARITY PROXY: it
    captures how strongly positive-or-negative the lexical sentiment signal
    is, NOT affective depth, arousal, or emotional engagement in any
    psychometrically validated sense. A review scoring 0.9 is not "more
    deeply felt" than one scoring 0.5 — it merely contains stronger
    polarity-bearing language. All SR-02 conclusions must be phrased in
    terms of lexical sentiment magnitude, not emotion.

    WHY ANOVA (AND ITS ROBUSTNESS COMPANION)
    ----------------------------------------
    One-way ANOVA is the canonical k-group mean comparison and is reported
    as the primary, literature-comparable analysis. Its normality assumption
    is, however, VIOLATED here: Shapiro-Wilk rejects normality in the theme
    groups (|vader_compound| is bounded on [0,1] and strongly skewed).
    ANOVA's F-test is fairly robust to non-normality at these group sizes
    (CLT on group means), but rather than lean solely on that argument, the
    distribution-free Kruskal-Wallis test is run as a parallel robustness
    check (sr02_kruskal_wallis_robustness). Agreement between the two is
    required before citing either conclusion confidently.

    ASSUMPTION CHECKS PERFORMED
    ---------------------------
    - Normality: Shapiro-Wilk per theme group (reported per group with n, W,
      p, and a boolean verdict at alpha = 0.05). Groups with n < 3 cannot be
      tested and are reported with nulls.
    - Homogeneity of variance: Levene's test with center='median', which is
      the BROWN-FORSYTHE variant — chosen over mean-centered Levene because
      median-centering is robust to exactly the skewness/non-normality the
      Shapiro results document.
    - Independence: assumed at the review level (module-level caveat).

    EFFECT SIZE
    -----------
    η² = SS_between / SS_total, the proportion of total variance in
    intensity attributable to theme membership. η² is upward-biased in small
    samples (ω² would be less biased) but is reported for comparability with
    the dominant convention in tourism research.

    INTERPRETATION LIMITS
    ---------------------
    A null result means no detectable difference in mean lexical sentiment
    magnitude across themes — not that themes are emotionally equivalent.
    Tukey p-values inherit the ANOVA assumptions (see _tukey_hsd).
    """
    d = df[df["primary_theme"].notna()].copy()
    d = d[d["primary_theme"].isin(THEMES)]
    d = d[pd.notna(d["emotional_intensity_score"])]
    if d.empty:
        return TestResult(
            name="SR-02 theme_anova",
            n=0,
            details={"error": "No themed reviews with emotional_intensity_score."},
        )

    groups = [grp["emotional_intensity_score"].astype(float).to_numpy() for _, grp in d.groupby("primary_theme")]
    if len(groups) < 2:
        return TestResult(
            name="SR-02 theme_anova",
            n=int(len(d)),
            details={"error": "Need >=2 themes for ANOVA."},
        )

    # Omnibus F-test; Levene with median centering = Brown-Forsythe variant,
    # robust to the documented non-normality (see docstring).
    f_stat, p = stats.f_oneway(*groups)
    lev_stat, lev_p = stats.levene(*groups, center="median")

    # Per-group Shapiro-Wilk normality screen. Shapiro-Wilk is preferred over
    # Kolmogorov-Smirnov/Anderson-Darling at these group sizes for power.
    # Note: with large n, Shapiro detects trivial departures; the verdicts
    # here are used qualitatively to motivate the Kruskal-Wallis companion,
    # not as gates.
    normality = {}
    for theme, grp in d.groupby("primary_theme"):
        vals = grp["emotional_intensity_score"].astype(float).to_numpy()
        if len(vals) >= 3:
            w, p_sw = stats.shapiro(vals)
            normality[theme] = {
                "n": int(len(vals)),
                "shapiro_W": float(w),
                "shapiro_p": float(p_sw),
                "normal": bool(p_sw >= 0.05),
            }
        else:
            # Shapiro-Wilk requires n >= 3; record the group as untestable.
            normality[theme] = {
                "n": int(len(vals)),
                "shapiro_W": None,
                "shapiro_p": None,
                "normal": None,
            }

    # η² = SS_between / SS_total — variance proportion explained by theme.
    all_vals = np.concatenate(groups)
    grand_mean = float(np.mean(all_vals))
    ss_total = float(np.sum((all_vals - grand_mean) ** 2))
    ss_between = sum(
        len(g) * (float(np.mean(g)) - grand_mean) ** 2 for g in groups
    )
    eta_squared = float(ss_between / ss_total) if ss_total > 0 else None

    theme_summary = (
        d.groupby("primary_theme")["emotional_intensity_score"]
        .agg(["count", "mean", "std"])
        .reindex(THEMES)
        .dropna(subset=["count"])
    )

    # Tukey-Kramer post-hocs (handles our unequal group sizes; see helper).
    tukey = _tukey_hsd(d, "primary_theme", "emotional_intensity_score")

    return TestResult(
        name="SR-02 theme_anova",
        n=int(len(d)),
        details={
            "f_stat": float(f_stat),
            "p_value": float(p),
            "eta_squared": eta_squared,
            "normality_by_theme": normality,
            "levene_median": {
                "stat": float(lev_stat),
                "p_value": float(lev_p),
                "equal_variance": bool(lev_p >= 0.05),
            },
            "theme_summary": theme_summary.reset_index().to_dict(orient="records"),
            "tukey_hsd": tukey,
        },
    )


def _cohens_d_pooled(a: np.ndarray, b: np.ndarray) -> float:
    """Classical Cohen's d with the POOLED standard deviation denominator.

    d = (mean_a - mean_b) / s_p, where s_p pools the two sample variances
    weighted by their degrees of freedom. This is the textbook form and is
    retained primarily FOR COMPARABILITY with this project's prior outputs
    and with literature that reports pooled d. NOTE THE INCONSISTENCY: the
    pooled denominator embeds an equal-variances assumption that the Welch
    t-test (SR-05) deliberately does NOT make. The Welch-consistent variant
    (_cohens_d_welch) is the effect size that matches the test actually
    performed; both are written to the JSON so the mismatch is transparent.
    Returns NaN when either group has n < 2 (sample variance undefined) and
    0.0 when the pooled SD is exactly zero (degenerate constant data).
    """
    a = a.astype(float)
    b = b.astype(float)
    na = len(a)
    nb = len(b)
    if na < 2 or nb < 2:
        return float("nan")
    sa2 = float(np.var(a, ddof=1))
    sb2 = float(np.var(b, ddof=1))
    # df-weighted pooled SD — assumes equal population variances.
    sp = np.sqrt(((na - 1) * sa2 + (nb - 1) * sb2) / (na + nb - 2))
    if sp == 0:
        return 0.0
    return float((np.mean(a) - np.mean(b)) / sp)


def _cohens_d_welch(a: np.ndarray, b: np.ndarray) -> float:
    """Effect size consistent with the Welch t-test: no equal-variance pooling.

    Standardizes the mean difference by sqrt((s_a² + s_b²)/2) — the root of
    the UNWEIGHTED average of the two sample variances. Because no pooling
    under an equal-variance assumption occurs, this denominator matches the
    Welch test's no-pooling premise, making it the internally consistent
    effect size to report alongside Welch p-values in SR-05. When the two
    variances happen to be equal it coincides with pooled d; when they
    differ, the two can diverge — which is exactly why both are reported
    (see _cohens_d_pooled for the comparability rationale). Same edge-case
    conventions: NaN for n < 2 in either group, 0.0 for zero denominator.
    """
    a = a.astype(float)
    b = b.astype(float)
    if len(a) < 2 or len(b) < 2:
        return float("nan")
    denom = np.sqrt((np.var(a, ddof=1) + np.var(b, ddof=1)) / 2.0)
    if denom == 0:
        return 0.0
    return float((np.mean(a) - np.mean(b)) / denom)


def _benjamini_hochberg(p_values: list[float]) -> list[float]:
    """Benjamini-Hochberg adjusted p-values with monotonicity correction.

    Implements the step-up FDR procedure of Benjamini & Hochberg (1995) in
    its adjusted-p-value form: for the i-th smallest p (rank i of m),
    p_adj = min(p * m / i, 1), then a reverse cumulative-minimum pass
    enforces monotonicity (an adjusted p may never exceed the adjusted p of
    a larger raw p). Comparing p_adj against alpha = 0.05 controls the FALSE
    DISCOVERY RATE — the expected proportion of false positives among
    rejected hypotheses — rather than the familywise error rate.

    WHY BH HERE (vs Bonferroni)
    ---------------------------
    BH is used for the pairwise Mann-Whitney FAMILIES in the exploratory
    robustness analyses (sr02_kruskal_wallis_robustness,
    kw_review_length_by_city), where FDR control is the appropriate,
    less-conservative criterion for screening which pairs merit discussion.
    The confirmatory SR-05 family keeps Bonferroni for strong familywise
    control. Standard BH assumes independent or positively dependent
    p-values (PRDS); pairwise comparisons sharing groups satisfy positive
    dependence in typical settings, which is the justification accepted here.
    """
    m = len(p_values)
    if m == 0:
        return []
    # Indices of p-values sorted ascending.
    order = sorted(range(m), key=lambda i: p_values[i])
    adjusted_sorted = [0.0] * m
    running_min = 1.0
    # Walk from the LARGEST p downward, carrying a running minimum so the
    # adjusted values are monotone in the raw values (step-up enforcement).
    for rank_from_end, orig_i in enumerate(reversed(order), start=1):
        rank = m - rank_from_end + 1
        adj = min(p_values[orig_i] * m / rank, 1.0)
        running_min = min(running_min, adj)
        adjusted_sorted[orig_i] = running_min
    return [float(v) for v in adjusted_sorted]


def city_comparison(df: pd.DataFrame) -> TestResult:
    """SR-05: Pairwise city comparison on sentiment_norm (Welch t-test + Bonferroni).

    WHAT THIS TESTS
    ---------------
    For each of the 3 city pairs, H0: equal mean sentiment_norm (VADER
    compound rescaled to [0, 1]) between the two cities. Two-sided Welch
    (unequal-variances) t-test.

    WHY WELCH RATHER THAN STUDENT'S t
    ---------------------------------
    The three cities have BOTH unequal sample sizes AND no a-priori reason
    to assume equal sentiment variances; under that combination Student's
    pooled t is anti-conservative when the smaller group has the larger
    variance. Welch's test drops the equal-variance assumption at a
    negligible power cost when variances happen to be equal, which is why
    methodological guidance (e.g. Delacre et al., 2017) recommends it as the
    default. Welch is therefore used unconditionally — no preliminary
    variance test gates the choice (two-stage testing distorts error rates).

    EFFECT SIZES — TWO FORMS, DELIBERATELY
    --------------------------------------
    Cohen's d is reported in BOTH the pooled form (denominator = df-weighted
    pooled SD; kept for comparability with this project's prior outputs and
    the broader literature) and the Welch-consistent form (denominator =
    sqrt((s_a² + s_b²)/2)), whose no-pooling construction matches the test's
    assumption set. When citing alongside the Welch p-value, the
    Welch-consistent d is the internally coherent choice.

    MULTIPLICITY
    ------------
    Bonferroni over the family of 3 comparisons. Each entry carries both
    conventions of the SAME rule: 'p_value_bonferroni' = min(3p, 1) to be
    compared against 'alpha_for_adjusted_p' = 0.05, OR the raw 'p_value' to
    be compared against 'alpha_bonferroni' = 0.0167. Using both at once
    would double-correct — pick one convention.

    ASSUMPTIONS / LIMITS
    --------------------
    - Review-level independence assumed (module docstring caveat applies:
      POI/reviewer clustering would understate standard errors).
    - sentiment_norm is bounded and non-normal, but per-city n is large
      enough for the CLT to make the Welch t reference distribution
      adequate for the MEAN comparison.
    - Differences are in lexical sentiment of review TEXT, not validated
      visitor satisfaction; cross-city composition differences (POI mix,
      reviewer mix) are uncontrolled confounders for any causal reading.
    """
    d = df[df["city"].isin(CITIES)].copy()
    d = d[pd.notna(d["sentiment_norm"])]
    if d.empty:
        return TestResult(
            name="SR-05 city_comparison_sentiment_norm",
            n=0,
            details={"error": "No sentiment_norm values available."},
        )

    results = []
    for a, b in combinations(CITIES, 2):
        xa = d.loc[d["city"] == a, "sentiment_norm"].astype(float).to_numpy()
        xb = d.loc[d["city"] == b, "sentiment_norm"].astype(float).to_numpy()
        # equal_var=False selects Welch's t with Welch-Satterthwaite df.
        t_stat, p = stats.ttest_ind(xa, xb, equal_var=False, nan_policy="omit")
        results.append({
            "cities": [a, b],
            "n_a": int(len(xa)),
            "n_b": int(len(xb)),
            "mean_a": float(np.mean(xa)) if len(xa) else None,
            "mean_b": float(np.mean(xb)) if len(xb) else None,
            "t_stat_welch": float(t_stat),
            "p_value": float(p),
            # Two equivalent Bonferroni conventions — apply ONE (see docstring).
            "p_value_bonferroni": float(min(p * 3, 1.0)),
            "alpha_bonferroni": BONFERRONI_ALPHA,
            "alpha_for_adjusted_p": 0.05,
            # Welch-consistent d matches the test; pooled d kept for
            # comparability with prior outputs (see helper docstrings).
            "cohens_d_welch": _cohens_d_welch(xa, xb),
            "cohens_d_pooled": _cohens_d_pooled(xa, xb),
        })

    return TestResult(
        name="SR-05 city_comparison_sentiment_norm",
        n=int(len(d)),
        details={"pairwise": results},
    )


def _epsilon_squared(h: float, k: int, n: int) -> float | None:
    """Rank-based effect size for Kruskal-Wallis: ε² = (H - k + 1) / (n - k).

    Formula per Tomczak & Tomczak (2014). ε² estimates the proportion of
    rank variance attributable to group membership — the nonparametric
    analogue of η² — and is preferred over the simpler H/(n-1) ratio because
    it corrects for the expected value of H under the null (k - 1).
    Conventional magnitude anchors: ~0.01 small, ~0.08 medium, ~0.26 large
    (heuristics, not substantive thresholds). Returns None when n ≤ k, where
    the denominator is undefined or non-positive.
    """
    denom = n - k
    if denom <= 0:
        return None
    return float((h - k + 1) / denom)


def _cliffs_delta_from_u(u: float, n_a: int, n_b: int) -> float:
    """Signed Cliff's delta from Mann-Whitney U. Positive means group A > group B.

    delta = 2U/(n_a · n_b) − 1, exploiting the identity U/(n_a·n_b) =
    P(A > B) + ½·P(A = B) (the common-language effect size). Delta ranges
    over [−1, 1]: 0 means stochastic equality; ±1 means complete separation.
    Chosen as the effect size for the Mann-Whitney pairwise comparisons
    because it is fully ordinal (invariant to monotone transformations,
    insensitive to the skew that motivated the rank tests in the first
    place), unlike Cohen's d. Conventional anchors: |δ| < 0.147 negligible,
    < 0.33 small, < 0.474 medium, else large (Romano et al., 2006). The
    SIGN convention follows SciPy's U for the first-named group: positive
    delta means the first group tends to have LARGER values. Returns NaN
    for empty groups.
    """
    denom = n_a * n_b
    if denom == 0:
        return float("nan")
    return float(2 * u / denom - 1)


def sr02_kruskal_wallis_robustness(df: pd.DataFrame) -> TestResult:
    """SR-02 robustness: Kruskal-Wallis on emotional_intensity_score ~ primary_theme.

    Complements the ANOVA. Run because Shapiro-Wilk shows non-normality in 4/5 theme
    groups. Consistent null across both tests strengthens the no-difference conclusion.

    WHAT THIS TESTS
    ---------------
    H0: the five theme groups are samples from the same distribution of
    emotional_intensity_score (strictly: no stochastic dominance among
    groups; under a shift-model reading, equal medians). Kruskal-Wallis H is
    the rank-based k-group omnibus test.

    WHY THIS COMPANION TEST EXISTS
    ------------------------------
    The primary SR-02 analysis is a one-way ANOVA (theme_anova). Shapiro-Wilk
    there rejects normality in 4 of 5 theme groups — |vader_compound| is
    bounded and skewed — so the ANOVA leans on large-sample robustness.
    Rather than argue robustness alone, Kruskal-Wallis is run as a
    distribution-free check: it requires no normality (only independent
    observations and an ordinal response). DECISION RULE: if both tests
    agree (both null or both significant), the shared conclusion is cited
    with confidence; if they disagree, BOTH are reported and the discrepancy
    discussed (encoded in the 'interpretation' field).

    DEPENDENT VARIABLE CAVEAT
    -------------------------
    As in theme_anova: the response is |vader_compound|, a lexical
    sentiment-magnitude proxy, NOT a validated measure of affective depth.

    EFFECT SIZE
    -----------
    ε² = (H − k + 1)/(n − k), per Tomczak & Tomczak (2014) — see
    _epsilon_squared for rationale and magnitude anchors.

    POST-HOCS AND MULTIPLICITY
    --------------------------
    Pairwise two-sided Mann-Whitney U tests localize any omnibus signal,
    with Benjamini-Hochberg FDR adjustment across the family of pairs (FDR
    rather than Bonferroni because this is an exploratory robustness family;
    see _benjamini_hochberg). Effect size per pair: signed Cliff's delta
    (see _cliffs_delta_from_u), with group medians reported for direction.

    LIMITS
    ------
    Review-level independence assumed (module caveat). KW does not compare
    means; if group distributions differ in shape/spread, a significant H
    cannot be read as a pure location difference.
    """
    d = df[df["primary_theme"].isin(THEMES)].copy()
    d = d[pd.notna(d["emotional_intensity_score"])]
    if d.empty:
        return TestResult(
            name="SR-02 kruskal_wallis_robustness",
            n=0,
            details={"error": "No themed reviews with emotional_intensity_score."},
        )

    groups = {t: d.loc[d["primary_theme"] == t, "emotional_intensity_score"].astype(float).to_numpy()
              for t in THEMES if (d["primary_theme"] == t).any()}
    if len(groups) < 2:
        return TestResult(
            name="SR-02 kruskal_wallis_robustness",
            n=int(len(d)),
            details={"error": "Need >=2 themes."},
        )

    # Shapiro-Wilk normality per group — recorded here (in addition to
    # theme_anova) so this result is self-contained as the documented
    # justification for preferring the rank-based analysis.
    normality = {}
    for theme, vals in groups.items():
        if len(vals) >= 3:
            w, p_sw = stats.shapiro(vals)
            normality[theme] = {"n": int(len(vals)), "shapiro_W": float(w),
                                "shapiro_p": float(p_sw), "normal": bool(p_sw >= 0.05)}
        else:
            normality[theme] = {"n": int(len(vals)), "shapiro_W": None,
                                "shapiro_p": None, "normal": None}

    # SciPy's kruskal applies the tie correction automatically (relevant
    # here: intensity scores contain exact ties, e.g. 0.0).
    h, p_kw = stats.kruskal(*groups.values())
    n_total = int(len(d))
    k = len(groups)
    eps2 = _epsilon_squared(float(h), k, n_total)

    pairwise = []
    for a, b in combinations(THEMES, 2):
        if a not in groups or b not in groups:
            continue
        u, p_mw = stats.mannwhitneyu(groups[a], groups[b], alternative="two-sided")
        delta = _cliffs_delta_from_u(float(u), len(groups[a]), len(groups[b]))
        pairwise.append({
            "themes": [a, b],
            "U": float(u),
            "p_value": float(p_mw),
            "cliffs_delta": delta,
            "median_a": float(np.median(groups[a])),
            "median_b": float(np.median(groups[b])),
        })
    # BH FDR across the pairwise family (exploratory screen; see helper).
    p_adj = _benjamini_hochberg([r["p_value"] for r in pairwise])
    for r, adj in zip(pairwise, p_adj):
        r["p_value_bh"] = adj
        r["significant_bh"] = bool(adj < 0.05)

    return TestResult(
        name="SR-02 kruskal_wallis_robustness",
        n=n_total,
        details={
            "h_stat": float(h),
            "p_value": float(p_kw),
            "epsilon_squared": eps2,
            "k_groups": k,
            "normality_by_theme": normality,
            "pairwise_mann_whitney": pairwise,
            "interpretation": (
                "Consistent with ANOVA null" if p_kw >= 0.05
                else "Contradicts ANOVA — report both"
            ),
        },
    )


def spearman_rating_sentiment(df: pd.DataFrame) -> TestResult:
    """Spearman ρ between review_rating and vader_compound, per city and overall.

    Rating is ordinal (1–5); vader_compound is continuous but skewed.
    Spearman preferred over Pearson for ordinal × skewed continuous pairs.
    Bootstrap 95% CI (2000 resamples, seed=42).
    Three city-level tests — family-wise note included but both significant
    results survive Bonferroni-corrected α=0.0167.

    WHAT THIS TESTS
    ---------------
    H0: no MONOTONIC association between a review's star rating and its
    VADER compound sentiment, per city and pooled. This is a convergent-
    validity check: if VADER scores carry signal, they should track the
    reviewer's own 1–5 rating monotonically.

    WHY SPEARMAN (vs Pearson / Kendall)
    -----------------------------------
    - vs Pearson: Pearson assumes interval-scaled variables and indexes
      LINEAR association. review_rating is ordinal — the psychological gap
      between 4 and 5 stars need not equal that between 1 and 2 — and
      vader_compound is heavily skewed (mass near +1). Spearman, computed on
      ranks, requires only ordinal scale and indexes monotonic association,
      matching both data properties.
    - vs Kendall's τ: also valid; Spearman is chosen for its wider use in
      the tourism literature and direct comparability. The heavy ties in the
      5-point rating make the exact ρ value tie-handling-dependent, which is
      one reason a bootstrap CI is reported rather than relying solely on
      the analytic p.

    UNCERTAINTY QUANTIFICATION
    --------------------------
    Per-city 95% CIs come from a nonparametric case-resampling bootstrap
    (2000 resamples, percentile method, seed 42): rows are resampled WITH
    replacement and ρ recomputed, so the CI reflects sampling variability
    without distributional assumptions — chosen for per-city ROBUSTNESS
    because the analytic (Fisher-z) CI assumes approximate bivariate
    normality of ranks that heavy ties undermine. 2000 resamples gives
    percentile endpoints stable to roughly ±0.01.

    MULTIPLICITY
    ------------
    Three city-level tests form a family; Bonferroni is applied (adjusted
    p = min(3p, 1) vs 0.05, equivalently raw p vs α = 0.0167 — one
    convention only, never both). The pooled overall test is a single
    pre-specified summary and is not corrected.

    LIMITS
    ------
    ρ measures monotonic association only; it says nothing about calibration
    (whether VADER's scale aligns with star units). Review-level independence
    is assumed (module caveat). Restriction of range matters: cities whose
    ratings cluster at 4–5 mechanically attenuate ρ.
    """
    d = df[df["city"].isin(CITIES)].copy()
    d = d[pd.notna(d["review_rating"]) & pd.notna(d["vader_compound"])]
    if d.empty:
        return TestResult(
            name="additional_spearman_rating_vs_sentiment",
            n=0,
            details={"error": "No rows with both review_rating and vader_compound."},
        )

    # Single seeded generator shared across the per-city bootstraps; the
    # sequence is consumed deterministically in city order, so results are
    # exactly reproducible for a fixed CITIES ordering.
    rng = np.random.default_rng(42)
    N_BOOT = 2000

    def _bootstrap_ci(arr_r, arr_v):
        # Case-resampling percentile bootstrap: resample row indices with
        # replacement (keeping rating/sentiment pairs intact), recompute rho.
        boot = []
        for _ in range(N_BOOT):
            idx = rng.integers(0, len(arr_r), size=len(arr_r))
            r2, _ = stats.spearmanr(arr_r[idx], arr_v[idx])
            boot.append(r2)
        return float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))

    city_results = []
    for city in CITIES:
        sub = d[d["city"] == city]
        arr_r = sub["review_rating"].to_numpy(dtype=float)
        arr_v = sub["vader_compound"].to_numpy(dtype=float)
        rho, p = stats.spearmanr(arr_r, arr_v)
        ci_lo, ci_hi = _bootstrap_ci(arr_r, arr_v)
        city_results.append({
            "city": city,
            "n": int(len(sub)),
            "rho": float(rho),
            "p_value": float(p),
            # Bonferroni over the 3 per-city tests (one convention only).
            "p_value_bonferroni": float(min(p * 3, 1.0)),
            "ci_95_bootstrap": [ci_lo, ci_hi],
            "significant_bonferroni": bool(p * 3 < 0.05),
        })

    # Pooled estimate across all cities — a single pre-specified summary,
    # not part of the corrected family.
    arr_r_all = d["review_rating"].to_numpy(dtype=float)
    arr_v_all = d["vader_compound"].to_numpy(dtype=float)
    rho_all, p_all = stats.spearmanr(arr_r_all, arr_v_all)

    return TestResult(
        name="additional_spearman_rating_vs_sentiment",
        n=int(len(d)),
        details={
            "method": "Spearman rho, bootstrap 95% CI (2000 resamples, seed=42)",
            "multiple_comparison": "Bonferroni correction across 3 city tests (alpha_adj=0.0167)",
            "by_city": city_results,
            "overall": {"rho": float(rho_all), "p_value": float(p_all), "n": int(len(d))},
        },
    )


def kw_review_length_by_city(df: pd.DataFrame) -> TestResult:
    """Kruskal-Wallis + pairwise Mann-Whitney on review length by city.

    Review length is right-skewed (confirmed by Shapiro-Wilk, all p<0.001).
    KW preferred over one-way ANOVA. Pairwise Mann-Whitney with BH FDR correction.
    Effect sizes: ε² (KW), rank-biserial r (Mann-Whitney).

    WHAT THIS TESTS
    ---------------
    H0: review character length (len(review_text)) is identically
    distributed across the three cities. This is an auxiliary engagement-
    proxy analysis: longer reviews are read as a rough indicator of
    elaboration effort. Character count is a crude proxy — it confounds
    verbosity with content richness and is sensitive to platform norms —
    so conclusions are framed descriptively.

    WHY KRUSKAL-WALLIS RATHER THAN ANOVA
    ------------------------------------
    Review lengths are strongly RIGHT-SKEWED with a long tail (Shapiro-Wilk
    rejects normality for every city, all p < 0.001 — verified and emitted
    in 'normality_by_city'). ANOVA on raw lengths would let tail outliers
    dominate the means; log-transforming then using ANOVA was rejected to
    keep the analysis on the interpretable raw scale; trimming/winsorizing
    introduces arbitrary cutoffs. The rank-based KW test is invariant to
    monotone transformation and robust to the tail, making it the natural
    choice. Medians per city are reported as the location summary.

    ASSUMPTIONS
    -----------
    Independent observations (module-level caveat applies) and an ordinal
    response — both satisfied. As with all KW applications, a significant H
    reflects stochastic ordering differences, not necessarily a pure median
    shift, if distribution shapes differ across cities.

    POST-HOCS, MULTIPLICITY, EFFECT SIZES
    -------------------------------------
    Pairwise two-sided Mann-Whitney U across the 3 city pairs, with
    Benjamini-Hochberg FDR adjustment (exploratory family — see
    _benjamini_hochberg for the BH-vs-Bonferroni rationale). Effect sizes:
    ε² for the omnibus (Tomczak & Tomczak 2014; see _epsilon_squared) and
    signed Cliff's delta per pair (equivalent up to sign convention to the
    rank-biserial correlation; positive = first-listed city tends to have
    LONGER reviews — see _cliffs_delta_from_u and 'effect_size_note').
    """
    d = df[df["city"].isin(CITIES)].copy()
    d = d[pd.notna(d["review_text"])].copy()
    # Response variable: raw character count of the review text.
    d["review_length"] = d["review_text"].str.len()

    groups = {c: d.loc[d["city"] == c, "review_length"].to_numpy(dtype=float)
              for c in CITIES}

    # Shapiro-Wilk per city — documents the non-normality that motivates the
    # rank-based test choice (expected: rejection in all cities).
    normality = {}
    for city, vals in groups.items():
        w, p_sw = stats.shapiro(vals)
        normality[city] = {"n": int(len(vals)), "shapiro_W": float(w),
                           "shapiro_p": float(p_sw), "normal": bool(p_sw >= 0.05)}

    # Omnibus rank test (tie-corrected by SciPy) + ε² effect size.
    h, p_kw = stats.kruskal(*groups.values())
    n_total = int(len(d))
    k = len(groups)
    eps2 = _epsilon_squared(float(h), k, n_total)
    medians = {c: float(np.median(v)) for c, v in groups.items()}

    # Pairwise Mann-Whitney with BH FDR
    pairs = list(combinations(CITIES, 2))
    raw_results = []
    for a, b in pairs:
        u, p_mw = stats.mannwhitneyu(groups[a], groups[b], alternative="two-sided")
        delta = _cliffs_delta_from_u(float(u), len(groups[a]), len(groups[b]))
        raw_results.append({"cities": [a, b], "U": float(u), "p_value": float(p_mw), "cliffs_delta": delta})

    # BH correction (FDR over the exploratory pairwise family).
    bh_ps = _benjamini_hochberg([r["p_value"] for r in raw_results])
    for r, p_bh in zip(raw_results, bh_ps):
        r["p_value_bh"] = float(p_bh)
        r["significant_bh"] = bool(p_bh < 0.05)

    return TestResult(
        name="additional_kw_review_length_by_city",
        n=n_total,
        details={
            "method": "Kruskal-Wallis; pairwise Mann-Whitney with BH FDR correction",
            "effect_size_note": "cliffs_delta is signed; positive means first city has longer reviews than second city",
            "h_stat": float(h),
            "p_value": float(p_kw),
            "epsilon_squared": eps2,
            "median_by_city": medians,
            "normality_by_city": normality,
            "pairwise_mann_whitney": raw_results,
        },
    )


def main():
    """Run every test suite in a fixed order and write statistical_results.json.

    The execution order below mirrors the analytic narrative: data audit
    first (gatekeeper), then SR-01 (a/b/c), SR-02 (parametric + rank-based),
    SR-05, and the two additional exploratory analyses. The output is a
    single JSON payload so the thesis appendix can reference one frozen,
    reproducible artifact.
    """
    logger.info("=" * 55)
    logger.info("Statistical validation (SR-01/SR-02/SR-05 + additional)")
    logger.info("=" * 55)

    df = _load_reviews()
    logger.info(f"Loaded reviews: {len(df)} rows")

    results = [
        input_data_audit(df),
        theme_chi_square_gof(df),
        theme_chi_square_independence(df),
        shared_theme_chi_square_independence(df),
        theme_anova(df),
        sr02_kruskal_wallis_robustness(df),
        city_comparison(df),
        spearman_rating_sentiment(df),
        kw_review_length_by_city(df),
    ]

    payload = {"results": [asdict(r) for r in results]}
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_JSON.write_text(json.dumps(payload, indent=2))

    logger.info(f"Written: {RESULTS_JSON}")
    logger.info("=" * 55)


if __name__ == "__main__":
    main()
