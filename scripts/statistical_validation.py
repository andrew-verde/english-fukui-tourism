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

THEMES = ["Dinosaur", "Food", "Scenic", "Cultural", "Logistics"]
SHARED_CITY_THEMES = ["Food", "Scenic", "Cultural", "Logistics"]
CITIES = ["Fukui", "Kanazawa", "Toyama"]

BONFERRONI_ALPHA = 0.05 / 3  # 3 pairwise city comparisons
REVIEW_DATE_CUTOFF = os.getenv("REVIEW_DATE_CUTOFF", "2024-06-01")
PERMUTATION_N = int(os.getenv("STATS_PERMUTATIONS", "10000"))
PERMUTATION_SEED = int(os.getenv("STATS_PERMUTATION_SEED", "42"))


@dataclass
class TestResult:
    name: str
    n: int
    details: dict


def _load_reviews() -> pd.DataFrame:
    if not REVIEWS_CSV.exists():
        raise FileNotFoundError(f"Missing input: {REVIEWS_CSV}")
    df = pd.read_csv(REVIEWS_CSV)
    return df


def input_data_audit(df: pd.DataFrame) -> TestResult:
    """Deterministic audit of assumptions required before interpreting tests."""
    required = [
        "city", "review_id", "review_date", "review_rating", "review_text",
        "review_language", "vader_compound", "sentiment_norm",
        "emotional_intensity_score", "primary_theme",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        return TestResult(
            name="input_data_audit",
            n=int(len(df)),
            details={"valid": False, "missing_columns": missing},
        )

    sentiment_expected = (df["vader_compound"].astype(float) + 1.0) / 2.0
    intensity_expected = df["vader_compound"].astype(float).abs()
    dates = pd.to_datetime(df["review_date"], utc=True, errors="coerce", format="mixed")
    cutoff = pd.Timestamp(REVIEW_DATE_CUTOFF, tz="UTC")

    formula_tol = 1e-5
    sentiment_mismatch = int((sentiment_expected - df["sentiment_norm"].astype(float)).abs().gt(formula_tol).sum())
    intensity_mismatch = int((intensity_expected - df["emotional_intensity_score"].astype(float)).abs().gt(formula_tol).sum())
    language_values = sorted(str(v) for v in df["review_language"].dropna().unique())
    city_counts = {str(k): int(v) for k, v in df["city"].value_counts().sort_index().items()}
    theme_counts = {
        str(k): int(v)
        for k, v in df["primary_theme"].fillna("None").value_counts().sort_index().items()
    }
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
    """Return Pearson chi-square statistic, df, and expected counts."""
    chi2, _p, dof, expected = stats.chi2_contingency(table)
    return float(chi2), int(dof), expected


def _permutation_chi2_p(
    city_labels: np.ndarray,
    theme_labels: np.ndarray,
    cities: list[str],
    themes: list[str],
    observed_chi2: float,
) -> dict:
    """Permutation p-value for independence, preserving city and theme margins."""
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
    shuffled = theme_codes.copy()
    for _ in range(PERMUTATION_N):
        rng.shuffle(shuffled)
        perm_ct = np.zeros(shape, dtype=int)
        np.add.at(perm_ct, (city_codes, shuffled), 1)
        try:
            stat, _dof, _expected = _chi2_stat_from_table(perm_ct)
        except ValueError:
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
        "p_value": float((exceed + 1) / (valid + 1)) if valid else None,
    }


def _pearson_residuals(observed: pd.DataFrame, expected: np.ndarray) -> dict:
    """(O - E)/sqrt(E). Variance < 1, so NOT comparable to ±1.96 z cutoffs."""
    residuals = (observed.to_numpy(dtype=float) - expected) / np.sqrt(expected)
    return pd.DataFrame(residuals, index=observed.index, columns=observed.columns).round(4).to_dict()


def _adjusted_standardized_residuals(observed: pd.DataFrame, expected: np.ndarray) -> dict:
    """Haberman adjusted residuals: (O - E)/sqrt(E(1-p_row)(1-p_col)).

    Approximately N(0,1) under independence, so these ARE comparable to ±1.96.
    """
    obs = observed.to_numpy(dtype=float)
    n = obs.sum()
    row_p = obs.sum(axis=1, keepdims=True) / n
    col_p = obs.sum(axis=0, keepdims=True) / n
    denom = np.sqrt(expected * (1.0 - row_p) * (1.0 - col_p))
    residuals = np.divide(obs - expected, denom, out=np.full_like(obs, np.nan), where=denom > 0)
    return pd.DataFrame(residuals, index=observed.index, columns=observed.columns).round(4).to_dict()


def _cramers_v_bias_corrected(table: np.ndarray, chi2: float) -> float | None:
    """Bergsma (2013) bias-corrected Cramér's V."""
    n = table.sum()
    if n <= 1:
        return None
    r, c = table.shape
    phi2 = chi2 / n
    phi2_corr = max(0.0, phi2 - (r - 1) * (c - 1) / (n - 1))
    r_corr = r - (r - 1) ** 2 / (n - 1)
    c_corr = c - (c - 1) ** 2 / (n - 1)
    denom = min(r_corr - 1, c_corr - 1)
    return float(np.sqrt(phi2_corr / denom)) if denom > 0 else None


def _chi2_cell_contributions(observed: pd.DataFrame, expected: np.ndarray) -> list[dict]:
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
    """SR-01: Chi-square GoF on Fukui theme distribution vs uniform expected."""
    d = df[(df["city"] == "Fukui") & df["primary_theme"].notna()].copy()
    d = d[d["primary_theme"].isin(THEMES)]
    observed = d["primary_theme"].value_counts().reindex(THEMES, fill_value=0).to_numpy()
    n = int(observed.sum())
    if n == 0:
        return TestResult(
            name="SR-01 theme_chi_square_gof",
            n=0,
            details={"error": "No themed Fukui reviews available."},
        )
    expected = np.full_like(observed, fill_value=n / len(THEMES), dtype=float)
    chi2, p = stats.chisquare(f_obs=observed, f_exp=expected)
    k = len(THEMES)
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
    """City × theme chi-square independence for a selected theme set."""
    d = df[df["primary_theme"].notna()].copy()
    d = d[d["primary_theme"].isin(themes) & d["city"].isin(CITIES)]
    if d.empty:
        return TestResult(
            name=result_name,
            n=0,
            details={"error": "No themed reviews available."},
        )

    ct = pd.crosstab(d["city"], d["primary_theme"]).reindex(index=CITIES, columns=themes, fill_value=0)
    chi2, p, dof, expected = stats.chi2_contingency(ct.to_numpy())
    n_total = int(len(d))
    r, c = ct.shape
    cramers_v_overall = float(np.sqrt(chi2 / (n_total * min(r - 1, c - 1)))) if n_total > 0 else None
    exp_min = float(np.min(expected)) if expected.size else None
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
    """SR-01: City × theme chi-square independence using all primary themes."""
    return _theme_chi_square_independence_for_themes(
        df,
        THEMES,
        "SR-01 theme_chi_square_independence",
        "All primary themes, including Dinosaur. Dinosaur is substantively Fukui-specific, so expected-count caveats are expected.",
    )


def shared_theme_chi_square_independence(df: pd.DataFrame) -> TestResult:
    """SR-01: City × shared-theme chi-square independence excluding Fukui-specific Dinosaur."""
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
    """SR-02: ANOVA emotional_intensity_score ~ primary_theme + Tukey HSD."""
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

    f_stat, p = stats.f_oneway(*groups)
    lev_stat, lev_p = stats.levene(*groups, center="median")

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
            normality[theme] = {
                "n": int(len(vals)),
                "shapiro_W": None,
                "shapiro_p": None,
                "normal": None,
            }

    # η² = SS_between / SS_total
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
    a = a.astype(float)
    b = b.astype(float)
    na = len(a)
    nb = len(b)
    if na < 2 or nb < 2:
        return float("nan")
    sa2 = float(np.var(a, ddof=1))
    sb2 = float(np.var(b, ddof=1))
    sp = np.sqrt(((na - 1) * sa2 + (nb - 1) * sb2) / (na + nb - 2))
    if sp == 0:
        return 0.0
    return float((np.mean(a) - np.mean(b)) / sp)


def _cohens_d_welch(a: np.ndarray, b: np.ndarray) -> float:
    """Effect size consistent with the Welch t-test: no equal-variance pooling."""
    a = a.astype(float)
    b = b.astype(float)
    if len(a) < 2 or len(b) < 2:
        return float("nan")
    denom = np.sqrt((np.var(a, ddof=1) + np.var(b, ddof=1)) / 2.0)
    if denom == 0:
        return 0.0
    return float((np.mean(a) - np.mean(b)) / denom)


def _benjamini_hochberg(p_values: list[float]) -> list[float]:
    """Benjamini-Hochberg adjusted p-values with monotonicity correction."""
    m = len(p_values)
    if m == 0:
        return []
    order = sorted(range(m), key=lambda i: p_values[i])
    adjusted_sorted = [0.0] * m
    running_min = 1.0
    for rank_from_end, orig_i in enumerate(reversed(order), start=1):
        rank = m - rank_from_end + 1
        adj = min(p_values[orig_i] * m / rank, 1.0)
        running_min = min(running_min, adj)
        adjusted_sorted[orig_i] = running_min
    return [float(v) for v in adjusted_sorted]


def city_comparison(df: pd.DataFrame) -> TestResult:
    """SR-05: Pairwise city comparison on sentiment_norm (Welch t-test + Bonferroni)."""
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
        t_stat, p = stats.ttest_ind(xa, xb, equal_var=False, nan_policy="omit")
        results.append({
            "cities": [a, b],
            "n_a": int(len(xa)),
            "n_b": int(len(xb)),
            "mean_a": float(np.mean(xa)) if len(xa) else None,
            "mean_b": float(np.mean(xb)) if len(xb) else None,
            "t_stat_welch": float(t_stat),
            "p_value": float(p),
            "p_value_bonferroni": float(min(p * 3, 1.0)),
            "alpha_bonferroni": BONFERRONI_ALPHA,
            "alpha_for_adjusted_p": 0.05,
            "cohens_d_welch": _cohens_d_welch(xa, xb),
            "cohens_d_pooled": _cohens_d_pooled(xa, xb),
        })

    return TestResult(
        name="SR-05 city_comparison_sentiment_norm",
        n=int(len(d)),
        details={"pairwise": results},
    )


def _epsilon_squared(h: float, k: int, n: int) -> float | None:
    """Rank-based effect size for Kruskal-Wallis: ε² = (H - k + 1) / (n - k)."""
    denom = n - k
    if denom <= 0:
        return None
    return float((h - k + 1) / denom)


def _cliffs_delta_from_u(u: float, n_a: int, n_b: int) -> float:
    """Signed Cliff's delta from Mann-Whitney U. Positive means group A > group B."""
    denom = n_a * n_b
    if denom == 0:
        return float("nan")
    return float(2 * u / denom - 1)


def sr02_kruskal_wallis_robustness(df: pd.DataFrame) -> TestResult:
    """SR-02 robustness: Kruskal-Wallis on emotional_intensity_score ~ primary_theme.

    Complements the ANOVA. Run because Shapiro-Wilk shows non-normality in 4/5 theme
    groups. Consistent null across both tests strengthens the no-difference conclusion.
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

    # Shapiro-Wilk normality per group
    normality = {}
    for theme, vals in groups.items():
        if len(vals) >= 3:
            w, p_sw = stats.shapiro(vals)
            normality[theme] = {"n": int(len(vals)), "shapiro_W": float(w),
                                "shapiro_p": float(p_sw), "normal": bool(p_sw >= 0.05)}
        else:
            normality[theme] = {"n": int(len(vals)), "shapiro_W": None,
                                "shapiro_p": None, "normal": None}

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
    """
    d = df[df["city"].isin(CITIES)].copy()
    d = d[pd.notna(d["review_rating"]) & pd.notna(d["vader_compound"])]
    if d.empty:
        return TestResult(
            name="additional_spearman_rating_vs_sentiment",
            n=0,
            details={"error": "No rows with both review_rating and vader_compound."},
        )

    rng = np.random.default_rng(42)
    N_BOOT = 2000

    def _bootstrap_ci(arr_r, arr_v):
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
            "p_value_bonferroni": float(min(p * 3, 1.0)),
            "ci_95_bootstrap": [ci_lo, ci_hi],
            "significant_bonferroni": bool(p * 3 < 0.05),
        })

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
    """
    d = df[df["city"].isin(CITIES)].copy()
    d = d[pd.notna(d["review_text"])].copy()
    d["review_length"] = d["review_text"].str.len()

    groups = {c: d.loc[d["city"] == c, "review_length"].to_numpy(dtype=float)
              for c in CITIES}

    # Shapiro-Wilk per city
    normality = {}
    for city, vals in groups.items():
        w, p_sw = stats.shapiro(vals)
        normality[city] = {"n": int(len(vals)), "shapiro_W": float(w),
                           "shapiro_p": float(p_sw), "normal": bool(p_sw >= 0.05)}

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

    # BH correction
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
