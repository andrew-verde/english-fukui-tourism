#!/usr/bin/env python3
"""
statistical_validation_official.py — Statistical checks for official FTAS data.

Reads:
  output/official_fukui/ftas_tagged_survey.csv
  output/official_fukui/raw/fukui_reservation_sum.csv
  output/official_fukui/raw/fukui_reservation_prefecture_sum.csv

Writes:
  output/official_fukui/statistical_results_official.json

Usage:
    python scripts/statistical_validation_official.py
"""

import json
import sys
from dataclasses import asdict, dataclass
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.official_fukui.ftas import load_japanese_codebook
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output" / "official_fukui"
TAGGED_CSV = OUTPUT_DIR / "ftas_tagged_survey.csv"
COMBINED_TAGGED_CSV = OUTPUT_DIR / "official_surveys_tagged_combined.csv"
RESERVATION_SUM_CSV = OUTPUT_DIR / "raw" / "fukui_reservation_sum.csv"
RESERVATION_PREF_CSV = OUTPUT_DIR / "raw" / "fukui_reservation_prefecture_sum.csv"
CODEBOOK_PATH = ROOT / "config" / "official_japanese_friction_codebook.yaml"
RESULTS_JSON = OUTPUT_DIR / "statistical_results_official.json"
SHINKANSEN_DATE = pd.Timestamp("2024-03-16")
SHINKANSEN_DATE_UTC = pd.Timestamp("2024-03-16", tz="UTC")


@dataclass
class TestResult:
    name: str
    n: int
    details: dict


def _dedup_respondents(df: pd.DataFrame, scope_cols: list[str] | None = None) -> tuple[pd.DataFrame, dict]:
    """Keep one response per respondent (earliest by response_datetime).

    Why deduplication is necessary
    ------------------------------
    FTAS (Fukui Tourism Activation Survey) members receive an incentive for
    participation — a bag of rice — which encourages the *same* member to
    submit the survey repeatedly across visits (or even within one visit
    window). In the raw export this manifests as 95,422 response rows but
    only 50,285 unique 会員ID ("member ID", renamed to ``respondent_id``
    during normalization). Roughly half the rows are therefore repeat
    submissions by already-counted people.

    Every inferential procedure downstream (chi-square, Mann-Whitney U,
    Benjamini-Hochberg-adjusted family tests) assumes independent
    observations. Treating repeat submissions as independent respondents
    would (a) silently inflate effective sample size and thus deflate
    p-values, and (b) over-weight the most enthusiastic repeat responders,
    who are plausibly systematically different from one-time responders.

    Dedup rule
    ----------
    We retain the *first* response per respondent, "first" meaning earliest
    by 回答日時 ("response date-time", renamed ``response_datetime``). The
    earliest response is preferred over, e.g., the latest or a random draw
    because it is the response least contaminated by survey-learning /
    incentive-gaming behavior, and the rule is deterministic and easy to
    audit. The stable sort below guarantees reproducible tie-breaking when
    timestamps are equal or unparseable.

    The ``scope_cols`` parameter
    ----------------------------
    Member IDs are issued *per survey system*, not globally: a Fukui FTAS
    会員ID and an Ishikawa survey ID live in separate namespaces and may
    collide numerically without referring to the same person. When this
    function is applied to the combined Fukui+Ishikawa table, callers must
    pass ``scope_cols=["survey_prefecture"]`` so that deduplication happens
    *within* each survey system; otherwise a coincidental Fukui/Ishikawa ID
    collision would wrongly drop a legitimate respondent.

    Rows without a respondent_id are kept as-is (we cannot prove they are
    duplicates, so we do not drop them). The returned audit dict records
    row counts before/after so the exact number of dropped repeat
    responses is traceable in the published JSON output.
    """
    if "respondent_id" not in df.columns:
        return df, {"n_rows": int(len(df)), "n_dropped_repeat_responses": 0,
                    "note": "no respondent_id column; dedup skipped"}
    d = df.copy()
    if "response_datetime" in d.columns:
        d["_dt"] = pd.to_datetime(d["response_datetime"], errors="coerce", utc=True)
        d = d.sort_values("_dt", kind="stable")
    has_id = d["respondent_id"].notna()
    keys = (scope_cols or []) + ["respondent_id"]
    deduped = pd.concat([d[has_id].drop_duplicates(subset=keys, keep="first"), d[~has_id]])
    deduped = deduped.drop(columns=["_dt"], errors="ignore").sort_index()
    audit = {
        "n_rows": int(len(df)),
        "n_after_dedup": int(len(deduped)),
        "n_dropped_repeat_responses": int(len(df) - len(deduped)),
        "rule": "first response per respondent_id retained"
        + (f" within {scope_cols}" if scope_cols else ""),
    }
    return deduped, audit


def _load_tagged() -> pd.DataFrame:
    if not TAGGED_CSV.exists():
        raise FileNotFoundError(f"Missing input: {TAGGED_CSV}. Run build_ftas_survey_dataset.py first.")
    return pd.read_csv(TAGGED_CSV, low_memory=False)


def _load_combined() -> pd.DataFrame:
    if not COMBINED_TAGGED_CSV.exists():
        raise FileNotFoundError(
            f"Missing input: {COMBINED_TAGGED_CSV}. "
            "Run build_ftas_survey_dataset.py after fetch_code4fukui_data.py so "
            "Fukui vs Ishikawa comparison sections are not silently omitted."
        )
    return pd.read_csv(COMBINED_TAGGED_CSV, low_memory=False)


def _has_text(df: pd.DataFrame) -> pd.Series:
    """Boolean mask: respondent wrote *any* free text (the "text-writer" set).

    This mask defines the denominator for every friction-rate comparison in
    this module, and the choice is methodologically load-bearing:

    Friction tags (``any_friction`` and the per-code columns) are derived
    exclusively from free-text fields. A respondent who wrote no text
    *cannot* be tagged, regardless of whether they experienced friction.
    Crucially, the two survey instruments differ in how aggressively they
    elicit text: Fukui's FTAS yields a non-empty ``friction_source_text``
    for only ~42% of respondents, whereas Ishikawa's instrument (different
    survey delivery / question framing) yields ~100%.

    If friction rates were computed over ALL respondents, the comparison
    would conflate instrument format with actual friction — and in this
    project's data it actually *reversed the direction* of the headline
    Fukui-vs-Ishikawa comparison. Conditioning on text-writers makes the
    denominators comparable across instruments.

    Selection caveat (must accompany any reported rate): the propensity to
    write free text correlates with dissatisfaction, so conditioned rates
    describe friction *among those who report*, not population prevalence.
    """
    return df["friction_source_text"].fillna("").astype(str).str.strip().ne("")


def _safe_p(p: float) -> float:
    # Avoid storing a literal 0.0 from floating-point underflow. At n ≈ 50k,
    # extreme test statistics can underflow to exactly 0.0; clamping to the
    # smallest positive float preserves provenance, because a stored 0.0 in
    # the results JSON would be indistinguishable from a coding error
    # (e.g., a field accidentally initialized to zero), whereas ~2.2e-308
    # is unambiguously "smaller than float64 can represent".
    return float(max(p, np.finfo(float).tiny))


def _as_bool(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series.fillna(False)
    return series.astype(str).str.lower().isin({"true", "1", "yes", "あり", "感じた"})


def _cramers_v(table: np.ndarray, chi2: float) -> float | None:
    n = table.sum()
    if n <= 0:
        return None
    r, c = table.shape
    denom = n * max(min(r - 1, c - 1), 1)
    return float(np.sqrt(chi2 / denom)) if denom else None


def _chi_square_binary(df: pd.DataFrame, row_col: str, col: str, label: str) -> TestResult:
    d = df[[row_col, col]].dropna().copy()
    if d.empty or d[row_col].nunique() < 2:
        return TestResult(label, int(len(d)), {"error": "Need at least two groups."})
    d[col] = _as_bool(d[col])
    ct = pd.crosstab(d[row_col], d[col])
    if ct.shape[1] < 2:
        return TestResult(label, int(len(d)), {"error": "Only one outcome level present.", "contingency_table": ct.to_dict()})
    # Note: scipy.stats.chi2_contingency applies Yates' continuity
    # correction automatically for 2x2 tables (correction=True is the
    # default); larger tables receive the standard Pearson statistic.
    chi2, p, dof, expected = stats.chi2_contingency(ct.to_numpy())
    return TestResult(
        label,
        int(len(d)),
        {
            "row_col": row_col,
            "outcome": col,
            "chi2": float(chi2),
            "df": int(dof),
            "p_value": _safe_p(p),
            "cramers_v": _cramers_v(ct.to_numpy(), float(chi2)),
            "expected_min": float(np.min(expected)),
            "assumption_expected_ge5": bool(np.min(expected) >= 5),
            "contingency_table": ct.to_dict(),
        },
    )


def input_data_audit(df: pd.DataFrame, codes: list[str]) -> TestResult:
    required = [
        "respondent_id", "response_datetime", "response_area", "municipality",
        "transport_satisfaction_score", "overall_satisfaction_score",
        "nps", "friction_source_text", "any_friction",
    ]
    missing = [c for c in required if c not in df.columns]
    dates = pd.to_datetime(df["response_datetime"], errors="coerce") if "response_datetime" in df.columns else pd.Series(dtype="datetime64[ns]")
    return TestResult(
        name="official_input_data_audit",
        n=int(len(df)),
        details={
            "valid": not missing and not dates.isna().all(),
            "missing_columns": missing,
            "date_min": str(dates.min()) if not dates.empty else None,
            "date_max": str(dates.max()) if not dates.empty else None,
            "n_response_areas": int(df["response_area"].nunique()) if "response_area" in df.columns else None,
            "n_municipalities": int(df["municipality"].nunique()) if "municipality" in df.columns else None,
            "any_friction_count": int(_as_bool(df["any_friction"]).sum()) if "any_friction" in df.columns else None,
            "friction_code_counts": {
                code: int(_as_bool(df[code]).sum()) for code in codes if code in df.columns
            },
        },
    )


def _mannwhitney_outcome(yes: np.ndarray, no: np.ndarray, label_yes: str, label_no: str) -> dict:
    """Two-sided Mann-Whitney U comparison with rank-biserial effect size.

    Test choice
    -----------
    The outcomes compared here are *ordinal*, not interval: 5-point Likert
    satisfaction (満足度, 1=とても不満 … 5=とても満足) and the 0-10 NPS
    recommendation item. A t-test would assume the distance between scale
    points is meaningful; Mann-Whitney only assumes ordering, which is the
    correct level of measurement for these items.

    Effect size, not significance, is the finding
    ---------------------------------------------
    With n ≈ 50k respondents, essentially *every* nonzero difference is
    statistically significant — p-values carry almost no information about
    practical importance. We therefore report the rank-biserial correlation
    r = 2U/(n1*n2) - 1, the natural effect size for Mann-Whitney (it equals
    the difference between P(yes > no) and P(no > yes)). Interpretation of
    results should lead with |r| magnitudes, not p.

    Why both means and medians are reported
    ---------------------------------------
    Medians are the canonical ordinal summary, but on coarse 5-point scales
    they frequently *tie* (e.g., both groups have median 4) even when the
    full distributions clearly differ — the test operates on ranks of the
    whole distribution, not the medians. Means are reported alongside as a
    more granular (if technically interval-assuming) descriptive aid.
    """
    u, p = stats.mannwhitneyu(yes, no, alternative="two-sided")
    # Rank-biserial r = 2U/(n1*n2) - 1; bounded in [-1, 1], sign gives
    # direction (positive => "yes" group stochastically larger).
    rank_biserial = float(2.0 * u / (len(yes) * len(no)) - 1.0)
    mean_diff = float(np.mean(yes) - np.mean(no))
    if abs(rank_biserial) < 1e-12:
        direction = f"no rank difference between {label_yes} and {label_no}"
    else:
        higher, lower = (label_yes, label_no) if rank_biserial > 0 else (label_no, label_yes)
        direction = f"{higher} ranks higher than {lower}"
    return {
        f"n_{label_yes}": int(len(yes)),
        f"n_{label_no}": int(len(no)),
        f"median_{label_yes}": float(np.median(yes)),
        f"median_{label_no}": float(np.median(no)),
        f"mean_{label_yes}": float(np.mean(yes)),
        f"mean_{label_no}": float(np.mean(no)),
        "mean_difference": mean_diff,
        "mannwhitney_u": float(u),
        "p_value": _safe_p(p),
        "rank_biserial_r": rank_biserial,
        "effect_direction": direction,
    }


def friction_vs_satisfaction(df: pd.DataFrame) -> TestResult:
    """Friction exposure vs satisfaction outcomes — two-exposure design.

    Two complementary exposure definitions are analyzed, mirroring the
    Stage 1 / Stage 2 logic documented in ADR 0001:

    1. PRIMARY — ``reported_inconvenience``: the explicit survey item 不便さ
       ("inconvenience"), answered 感じた ("felt it") / 感じなかった ("did
       not feel it"). Because this closed-form question is asked of EVERY
       respondent, the exposure is free of free-text selection bias and is
       the only exposure that can be interpreted at full-sample level.

    2. SECONDARY — tagged ``any_friction``: keyword-derived friction tags
       from free text. Tags only exist where text exists, so this analysis
       is deliberately conditioned on text-writers (see ``_has_text``).
       An untagged non-writer is NOT evidence of "no friction" — it is
       missing data; coding non-writers as friction-free would bias the
       no-friction group toward people who simply skipped the text boxes.

    Concordant results across the two exposures (one selection-bias-free
    but coarse, one detailed but conditioned) is the triangulation that
    supports the substantive claim; either alone is weaker.
    """
    outcome_cols = ["overall_satisfaction_score", "transport_satisfaction_score", "nps"]
    analyses = {}

    exposures = []
    if "reported_inconvenience" in df.columns:
        exposures.append(("reported_inconvenience_full_sample", df, "reported_inconvenience"))
    if "any_friction" in df.columns and "friction_source_text" in df.columns:
        exposures.append(("tagged_friction_among_text_writers", df[_has_text(df)], "any_friction"))

    for analysis_name, frame, exposure in exposures:
        outcomes = {}
        flags = _as_bool(frame[exposure])
        for col in outcome_cols:
            sub = frame[[col]].assign(flag=flags.values).dropna(subset=[col])
            if sub.empty or sub["flag"].nunique() < 2:
                outcomes[col] = {"error": "Need both friction and no-friction rows."}
                continue
            yes = sub.loc[sub["flag"], col].astype(float).to_numpy()
            no = sub.loc[~sub["flag"], col].astype(float).to_numpy()
            outcomes[col] = _mannwhitney_outcome(yes, no, "friction", "no_friction")
        analyses[analysis_name] = {
            "exposure": exposure,
            "n_analyzed": int(len(frame)),
            "outcomes": outcomes,
        }
    analyses["selection_note"] = (
        "any_friction tags exist only for respondents with free text; the tagged "
        "analysis is conditioned on text-writers to avoid coding non-writers as friction-free."
    )
    return TestResult("official_friction_vs_satisfaction", int(len(df)), analyses)


def shinkansen_survey_shift(df: pd.DataFrame) -> TestResult:
    if "transport_to_fukui_shinkansen" not in df.columns or "response_datetime" not in df.columns:
        return TestResult("official_shinkansen_survey_shift", 0, {"error": "Missing Shinkansen/date columns."})
    d = df.copy()
    d["response_datetime"] = pd.to_datetime(d["response_datetime"], errors="coerce")
    d = d[d["response_datetime"].notna()]
    d["post"] = d["response_datetime"] >= SHINKANSEN_DATE_UTC
    d["uses_shinkansen"] = _as_bool(d["transport_to_fukui_shinkansen"])
    ct = pd.crosstab(d["post"], d["uses_shinkansen"]).reindex(index=[False, True], columns=[False, True], fill_value=0)
    chi2, p, dof, expected = stats.chi2_contingency(ct.to_numpy())
    pre_rate = float(ct.loc[False, True] / ct.loc[False].sum()) if ct.loc[False].sum() else None
    post_rate = float(ct.loc[True, True] / ct.loc[True].sum()) if ct.loc[True].sum() else None
    return TestResult(
        "official_shinkansen_survey_shift",
        int(len(d)),
        {
            "event_date": str(SHINKANSEN_DATE.date()),
            "pre_shinkansen_rate": pre_rate,
            "post_shinkansen_rate": post_rate,
            "delta_rate": (post_rate - pre_rate) if pre_rate is not None and post_rate is not None else None,
            "chi2": float(chi2),
            "df": int(dof),
            "p_value": _safe_p(p),
            "cramers_v": _cramers_v(ct.to_numpy(), float(chi2)),
            "expected_min": float(np.min(expected)),
            "contingency_table": ct.to_dict(),
        },
    )


def reservation_event_context() -> TestResult:
    """Pre/post Shinkansen reservation volumes — DESCRIPTIVE CONTEXT ONLY.

    Seasonality caveat (also embedded in the output JSON): with the
    Hokuriku Shinkansen extension opening 2024-03-16, a symmetric 180-day
    window puts the *pre* period in autumn/winter and the *post* period in
    spring/summer. Any pre/post difference therefore confounds the rail
    opening with ordinary tourism seasonality, and no causal reading is
    licensed. This test is retained for descriptive context and provenance;
    it is superseded by the Hokuriku difference-in-differences analysis,
    which uses a comparison prefecture to net out seasonal trends.
    """
    if not RESERVATION_SUM_CSV.exists():
        return TestResult("official_reservation_event_context", 0, {"error": f"Missing {RESERVATION_SUM_CSV}"})
    d = pd.read_csv(RESERVATION_SUM_CSV)
    d["date_visit"] = pd.to_datetime(d["date_visit"], errors="coerce")
    d = d[d["date_visit"].notna()].copy()
    # Symmetric 180-day windows avoid using far-future reservation targets.
    d = d[(d["date_visit"] >= SHINKANSEN_DATE - pd.Timedelta(days=180)) & (d["date_visit"] <= SHINKANSEN_DATE + pd.Timedelta(days=180))]
    d["post"] = d["date_visit"] >= SHINKANSEN_DATE
    summaries = {}
    for col in ["n_people", "n_reserve", "amount_fee"]:
        if col not in d.columns:
            continue
        pre = d.loc[~d["post"], col].astype(float).to_numpy()
        post = d.loc[d["post"], col].astype(float).to_numpy()
        if len(pre) < 2 or len(post) < 2:
            summaries[col] = {"error": "Insufficient pre/post rows."}
            continue
        u, p = stats.mannwhitneyu(post, pre, alternative="two-sided")
        summaries[col] = {
            "n_pre_days": int(len(pre)),
            "n_post_days": int(len(post)),
            "median_pre": float(np.median(pre)),
            "median_post": float(np.median(post)),
            "mannwhitney_u": float(u),
            "p_value": _safe_p(p),
        }
    return TestResult(
        "official_reservation_event_context",
        int(len(d)),
        {
            "event_date": str(SHINKANSEN_DATE.date()),
            "window_days_each_side": 180,
            "outcomes": summaries,
            "caveat": (
                "The pre window is autumn/winter and the post window spring/summer, so this "
                "test confounds the Shinkansen opening with seasonality. Treat as descriptive "
                "context only; the Hokuriku DiD with a comparison prefecture supersedes it."
            ),
        },
    )


def top_area_friction_tests(df: pd.DataFrame, codes: list[str], top_n: int = 12) -> TestResult:
    """Area-by-friction-code chi-square tests with BH correction.

    Multiple-comparison policy: the Benjamini-Hochberg adjustment is applied
    WITHIN the family of friction-code tests run here (one test per code),
    not globally across every test in this script. Per BH's false-discovery-
    rate logic, a "family" is a coherent hypothesis group — here, "which
    friction codes vary by response area" — and pooling unrelated hypothesis
    groups into one global family would dilute power without conceptual
    justification. The same per-family convention is used for the transport-
    mode family in official_prefecture_comparison.
    """
    if "response_area" not in df.columns:
        return TestResult("official_top_area_friction_tests", 0, {"error": "Missing response_area."})
    top_areas = df["response_area"].value_counts().head(top_n).index.tolist()
    d = df[df["response_area"].isin(top_areas)].copy()
    tests = []
    p_values = []
    for code in codes:
        if code not in d.columns or int(d[code].astype(bool).sum()) < 5:
            continue
        result = _chi_square_binary(d, "response_area", code, f"area_x_{code}")
        if "p_value" in result.details:
            p_values.append(result.details["p_value"])
            tests.append(result)
    adjusted = _benjamini_hochberg(p_values)
    records = []
    for result, p_adj in zip(tests, adjusted):
        details = result.details.copy()
        details["name"] = result.name
        details["p_value_bh"] = p_adj
        records.append(details)
    return TestResult(
        "official_top_area_friction_tests",
        int(len(d)),
        {"top_n_areas": top_n, "areas": top_areas, "tests": records},
    )


def _benjamini_hochberg(p_values: list[float]) -> list[float]:
    """Benjamini-Hochberg FDR-adjusted p-values for one hypothesis family.

    Callers pass exactly one family at a time (friction-code family,
    transport-mode family, ...) — see the family-definition rationale in
    top_area_friction_tests. The step-up procedure below computes
    p_adj(i) = min over j >= rank(i) of (p(j) * m / rank(j)), capped at 1,
    via a reverse pass that carries the running minimum.
    """
    m = len(p_values)
    if m == 0:
        return []
    order = np.argsort(p_values)
    adjusted = np.empty(m, dtype=float)
    running_min = 1.0
    for rank_from_end, idx in enumerate(reversed(order), start=1):
        rank = m - rank_from_end + 1
        value = min(p_values[idx] * m / rank, 1.0)
        running_min = min(running_min, value)
        adjusted[idx] = running_min
    return [float(v) for v in adjusted]


def _binary_group_test(df: pd.DataFrame, group_col: str, outcome_col: str, groups: list[str]) -> dict:
    d = df[df[group_col].isin(groups)][[group_col, outcome_col]].dropna().copy()
    d[outcome_col] = _as_bool(d[outcome_col])
    ct = pd.crosstab(d[group_col], d[outcome_col]).reindex(index=groups, columns=[False, True], fill_value=0)
    chi2, p, dof, expected = stats.chi2_contingency(ct.to_numpy())
    rates = {
        group: float(ct.loc[group, True] / ct.loc[group].sum()) if ct.loc[group].sum() else None
        for group in groups
    }
    counts = {
        group: {"n": int(ct.loc[group].sum()), "true": int(ct.loc[group, True])}
        for group in groups
    }
    return {
        "groups": groups,
        "outcome": outcome_col,
        "counts": counts,
        "rates": rates,
        "chi2": float(chi2),
        "df": int(dof),
        "p_value": _safe_p(p),
        "cramers_v": _cramers_v(ct.to_numpy(), float(chi2)),
        "expected_min": float(np.min(expected)),
        "assumption_expected_ge5": bool(np.min(expected) >= 5),
    }


def official_prefecture_comparison(df: pd.DataFrame, codes: list[str]) -> TestResult:
    if "survey_prefecture" not in df.columns:
        return TestResult("official_prefecture_comparison", 0, {"error": "Missing combined survey_prefecture column."})
    groups = ["Fukui", "Ishikawa"]
    d = df[df["survey_prefecture"].isin(groups)].copy()
    if d.empty:
        return TestResult("official_prefecture_comparison", 0, {"error": "No Fukui/Ishikawa rows."})

    # Friction tags only exist where free text was written, and text-response
    # rates differ drastically by instrument (Fukui ~42% vs Ishikawa ~100%,
    # a consequence of different survey delivery formats, not of respondent
    # behavior). Friction comparisons therefore condition on text-writers;
    # comparing over all respondents would measure questionnaire format, not
    # friction — in earlier runs it reversed the direction of the headline
    # Fukui-vs-Ishikawa friction comparison. Remaining caveat: text-writing
    # correlates with dissatisfaction, so these are rates among reporters,
    # not population prevalence (see _has_text docstring).
    text_writers = d[_has_text(d)]
    text_rates = {
        g: float(_has_text(d[d["survey_prefecture"] == g]).mean()) for g in groups
    }

    any_friction = _binary_group_test(text_writers, "survey_prefecture", "any_friction", groups)
    code_tests = []
    p_values = []
    for code in codes:
        if code not in text_writers.columns:
            continue
        if int(_as_bool(text_writers[code]).sum()) < 5:
            continue
        result = _binary_group_test(text_writers, "survey_prefecture", code, groups)
        p_values.append(result["p_value"])
        code_tests.append(result)
    for result, p_adj in zip(code_tests, _benjamini_hochberg(p_values)):
        result["p_value_bh"] = p_adj

    outcome_tests = []
    for outcome in ["overall_satisfaction_score", "transport_satisfaction_score", "nps"]:
        if outcome not in d.columns:
            continue
        sub = d[["survey_prefecture", outcome]].dropna().copy()
        a = sub.loc[sub["survey_prefecture"] == "Fukui", outcome].astype(float).to_numpy()
        b = sub.loc[sub["survey_prefecture"] == "Ishikawa", outcome].astype(float).to_numpy()
        if len(a) < 2 or len(b) < 2:
            continue
        record = _mannwhitney_outcome(a, b, "fukui", "ishikawa")
        record["outcome"] = outcome
        outcome_tests.append(record)

    # Transport-mode usage is a separate hypothesis family from friction
    # codes, so it receives its own Benjamini-Hochberg pass below (families
    # are defined by hypothesis group, not globally — see
    # top_area_friction_tests). Unlike the friction tests, these checkbox
    # items are answered by all respondents, so the full sample is used.
    transport_tests = []
    transport_p = []
    for mode in [
        "transport_to_fukui_private_car",
        "transport_to_fukui_rental_car",
        "transport_to_fukui_shinkansen",
        "transport_to_fukui_local_train",
        "transport_to_fukui_airplane",
        "transport_in_fukui_route_bus",
        "transport_in_fukui_walk",
    ]:
        if mode not in d.columns:
            continue
        result = _binary_group_test(d, "survey_prefecture", mode, groups)
        transport_p.append(result["p_value"])
        transport_tests.append(result)
    for result, p_adj in zip(transport_tests, _benjamini_hochberg(transport_p)):
        result["p_value_bh"] = p_adj

    return TestResult(
        "official_prefecture_comparison",
        int(len(d)),
        {
            "friction_denominator": "respondents with non-empty friction_source_text",
            "text_response_rates": text_rates,
            "n_text_writers": int(len(text_writers)),
            "any_friction": any_friction,
            "friction_code_tests": sorted(code_tests, key=lambda r: r.get("p_value_bh", 1.0)),
            "outcome_tests": outcome_tests,
            "transport_mode_tests": transport_tests,
        },
    )


def official_fukui_vs_ishikawa_kanazawa_area_comparison(df: pd.DataFrame, codes: list[str]) -> TestResult:
    if "survey_prefecture" not in df.columns or "survey_area_group" not in df.columns:
        return TestResult(
            "official_fukui_vs_ishikawa_kanazawa_area_comparison",
            0,
            {"error": "Missing combined survey columns."},
        )
    d = df[
        (df["survey_prefecture"].eq("Fukui")) |
        ((df["survey_prefecture"].eq("Ishikawa")) & (df["survey_area_group"].astype(str).eq("金沢")))
    ].copy()
    d["comparison_scope"] = np.where(d["survey_prefecture"].eq("Fukui"), "Fukui", "Ishikawa_Kanazawa_area")
    groups = ["Fukui", "Ishikawa_Kanazawa_area"]
    if d["comparison_scope"].nunique() < 2:
        return TestResult(
            "official_fukui_vs_ishikawa_kanazawa_area_comparison",
            int(len(d)),
            {"error": "Need both Fukui and Ishikawa Kanazawa-area rows."},
        )

    text_writers = d[_has_text(d)]
    text_rates = {
        g: float(_has_text(d[d["comparison_scope"] == g]).mean()) for g in groups
    }
    any_friction = _binary_group_test(text_writers, "comparison_scope", "any_friction", groups)
    code_tests = []
    p_values = []
    for code in codes:
        if code in text_writers.columns and int(_as_bool(text_writers[code]).sum()) >= 5:
            result = _binary_group_test(text_writers, "comparison_scope", code, groups)
            p_values.append(result["p_value"])
            code_tests.append(result)
    for result, p_adj in zip(code_tests, _benjamini_hochberg(p_values)):
        result["p_value_bh"] = p_adj

    outcome_tests = []
    for outcome in ["overall_satisfaction_score", "transport_satisfaction_score", "nps"]:
        if outcome not in d.columns:
            continue
        sub = d[["comparison_scope", outcome]].dropna().copy()
        a = sub.loc[sub["comparison_scope"] == "Fukui", outcome].astype(float).to_numpy()
        b = sub.loc[sub["comparison_scope"] == "Ishikawa_Kanazawa_area", outcome].astype(float).to_numpy()
        if len(a) < 2 or len(b) < 2:
            continue
        record = _mannwhitney_outcome(a, b, "fukui", "ishikawa_kanazawa_area")
        record["outcome"] = outcome
        outcome_tests.append(record)

    return TestResult(
        "official_fukui_vs_ishikawa_kanazawa_area_comparison",
        int(len(d)),
        {
            "scope_note": "Compares all Fukui official survey rows against Ishikawa official survey rows whose survey_area_group is 金沢.",
            "friction_denominator": "respondents with non-empty friction_source_text",
            "text_response_rates": text_rates,
            "n_text_writers": int(len(text_writers)),
            "any_friction": any_friction,
            "friction_code_tests": sorted(code_tests, key=lambda r: r.get("p_value_bh", 1.0)),
            "outcome_tests": outcome_tests,
        },
    )


def main() -> int:
    df, dedup_audit = _dedup_respondents(_load_tagged())
    combined_df = _load_combined()
    # Scope dedup by survey_prefecture: member IDs are issued per survey
    # system (Fukui FTAS vs Ishikawa), not globally, so an ID may recur
    # across prefectures without being the same person. See
    # _dedup_respondents docstring.
    combined_df, combined_dedup_audit = _dedup_respondents(
        combined_df, scope_cols=["survey_prefecture"]
    )
    codebook = load_japanese_codebook(CODEBOOK_PATH)
    codes = list(codebook.keys())

    results = [
        input_data_audit(df, codes),
        friction_vs_satisfaction(df),
        shinkansen_survey_shift(df),
        reservation_event_context(),
        top_area_friction_tests(df, codes),
    ]
    results.extend([
        official_prefecture_comparison(combined_df, codes),
        official_fukui_vs_ishikawa_kanazawa_area_comparison(combined_df, codes),
    ])
    payload = {
        "method_notes": {
            "unit_of_analysis": (
                "one survey respondent (first response retained for members who "
                "submitted multiple responses) unless test name says reservation/day context"
            ),
            "respondent_dedup": dedup_audit,
            "respondent_dedup_combined": combined_dedup_audit,
            "friction_rate_denominator": (
                "friction-tag comparisons condition on respondents with non-empty "
                "friction_source_text; text-response rates differ by instrument "
                "(Fukui ~42% vs Ishikawa ~100%), so all-respondent rates are not comparable"
            ),
            "official_data_source": "Code for Fukui FTAS CSVs and Ishikawa official tourism survey CSVs",
            "official_data_only": True,
            "shinkansen_event_date": str(SHINKANSEN_DATE.date()),
        },
        "results": [asdict(r) for r in results],
    }
    RESULTS_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    logger.info(f"Wrote official statistical results: {RESULTS_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
