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


def _load_tagged() -> pd.DataFrame:
    if not TAGGED_CSV.exists():
        raise FileNotFoundError(f"Missing input: {TAGGED_CSV}. Run build_ftas_survey_dataset.py first.")
    return pd.read_csv(TAGGED_CSV, low_memory=False)


def _load_combined() -> pd.DataFrame | None:
    if not COMBINED_TAGGED_CSV.exists():
        return None
    return pd.read_csv(COMBINED_TAGGED_CSV, low_memory=False)


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
    d[col] = d[col].astype(bool)
    ct = pd.crosstab(d[row_col], d[col])
    if ct.shape[1] < 2:
        return TestResult(label, int(len(d)), {"error": "Only one outcome level present.", "contingency_table": ct.to_dict()})
    chi2, p, dof, expected = stats.chi2_contingency(ct.to_numpy())
    return TestResult(
        label,
        int(len(d)),
        {
            "row_col": row_col,
            "outcome": col,
            "chi2": float(chi2),
            "df": int(dof),
            "p_value": float(p),
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
            "any_friction_count": int(df["any_friction"].astype(bool).sum()) if "any_friction" in df.columns else None,
            "friction_code_counts": {
                code: int(df[code].astype(bool).sum()) for code in codes if code in df.columns
            },
        },
    )


def friction_vs_satisfaction(df: pd.DataFrame) -> TestResult:
    d = df[["any_friction", "overall_satisfaction_score", "transport_satisfaction_score", "nps"]].copy()
    d["any_friction"] = d["any_friction"].astype(bool)
    outcomes = {}
    for col in ["overall_satisfaction_score", "transport_satisfaction_score", "nps"]:
        sub = d[[col, "any_friction"]].dropna().copy()
        if sub.empty or sub["any_friction"].nunique() < 2:
            outcomes[col] = {"error": "Need both friction and no-friction rows."}
            continue
        yes = sub.loc[sub["any_friction"], col].astype(float).to_numpy()
        no = sub.loc[~sub["any_friction"], col].astype(float).to_numpy()
        u, p = stats.mannwhitneyu(yes, no, alternative="two-sided")
        outcomes[col] = {
            "n_friction": int(len(yes)),
            "n_no_friction": int(len(no)),
            "median_friction": float(np.median(yes)),
            "median_no_friction": float(np.median(no)),
            "mannwhitney_u": float(u),
            "p_value": float(p),
            "effect_note": "lower median_friction suggests official survey friction text aligns with lower satisfaction/NPS",
        }
    return TestResult("official_friction_vs_satisfaction", int(len(df)), outcomes)


def shinkansen_survey_shift(df: pd.DataFrame) -> TestResult:
    if "transport_to_fukui_shinkansen" not in df.columns or "response_datetime" not in df.columns:
        return TestResult("official_shinkansen_survey_shift", 0, {"error": "Missing Shinkansen/date columns."})
    d = df.copy()
    d["response_datetime"] = pd.to_datetime(d["response_datetime"], errors="coerce")
    d = d[d["response_datetime"].notna()]
    d["post"] = d["response_datetime"] >= SHINKANSEN_DATE_UTC
    d["uses_shinkansen"] = d["transport_to_fukui_shinkansen"].astype(bool)
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
            "p_value": float(p),
            "cramers_v": _cramers_v(ct.to_numpy(), float(chi2)),
            "expected_min": float(np.min(expected)),
            "contingency_table": ct.to_dict(),
        },
    )


def reservation_event_context() -> TestResult:
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
            "p_value": float(p),
        }
    return TestResult(
        "official_reservation_event_context",
        int(len(d)),
        {"event_date": str(SHINKANSEN_DATE.date()), "window_days_each_side": 180, "outcomes": summaries},
    )


def top_area_friction_tests(df: pd.DataFrame, codes: list[str], top_n: int = 12) -> TestResult:
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
        "p_value": float(p),
        "cramers_v": _cramers_v(ct.to_numpy(), float(chi2)),
        "expected_min": float(np.min(expected)),
    }


def official_prefecture_comparison(df: pd.DataFrame, codes: list[str]) -> TestResult:
    if "survey_prefecture" not in df.columns:
        return TestResult("official_prefecture_comparison", 0, {"error": "Missing combined survey_prefecture column."})
    groups = ["Fukui", "Ishikawa"]
    d = df[df["survey_prefecture"].isin(groups)].copy()
    if d.empty:
        return TestResult("official_prefecture_comparison", 0, {"error": "No Fukui/Ishikawa rows."})

    any_friction = _binary_group_test(d, "survey_prefecture", "any_friction", groups)
    code_tests = []
    p_values = []
    for code in codes:
        if code not in d.columns:
            continue
        if int(_as_bool(d[code]).sum()) < 5:
            continue
        result = _binary_group_test(d, "survey_prefecture", code, groups)
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
        u, p = stats.mannwhitneyu(a, b, alternative="two-sided")
        outcome_tests.append({
            "outcome": outcome,
            "n_fukui": int(len(a)),
            "n_ishikawa": int(len(b)),
            "median_fukui": float(np.median(a)),
            "median_ishikawa": float(np.median(b)),
            "mean_fukui": float(np.mean(a)),
            "mean_ishikawa": float(np.mean(b)),
            "mannwhitney_u": float(u),
            "p_value": float(p),
        })

    transport_tests = []
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
        transport_tests.append(_binary_group_test(d, "survey_prefecture", mode, groups))

    return TestResult(
        "official_prefecture_comparison",
        int(len(d)),
        {
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

    any_friction = _binary_group_test(d, "comparison_scope", "any_friction", groups)
    code_tests = []
    p_values = []
    for code in codes:
        if code in d.columns and int(_as_bool(d[code]).sum()) >= 5:
            result = _binary_group_test(d, "comparison_scope", code, groups)
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
        u, p = stats.mannwhitneyu(a, b, alternative="two-sided")
        outcome_tests.append({
            "outcome": outcome,
            "n_fukui": int(len(a)),
            "n_ishikawa_kanazawa_area": int(len(b)),
            "median_fukui": float(np.median(a)),
            "median_ishikawa_kanazawa_area": float(np.median(b)),
            "mean_fukui": float(np.mean(a)),
            "mean_ishikawa_kanazawa_area": float(np.mean(b)),
            "mannwhitney_u": float(u),
            "p_value": float(p),
        })

    return TestResult(
        "official_fukui_vs_ishikawa_kanazawa_area_comparison",
        int(len(d)),
        {
            "scope_note": "Compares all Fukui official survey rows against Ishikawa official survey rows whose survey_area_group is 金沢.",
            "any_friction": any_friction,
            "friction_code_tests": sorted(code_tests, key=lambda r: r.get("p_value_bh", 1.0)),
            "outcome_tests": outcome_tests,
        },
    )


def main() -> int:
    df = _load_tagged()
    combined_df = _load_combined()
    codebook = load_japanese_codebook(CODEBOOK_PATH)
    codes = list(codebook.keys())

    results = [
        input_data_audit(df, codes),
        friction_vs_satisfaction(df),
        shinkansen_survey_shift(df),
        reservation_event_context(),
        top_area_friction_tests(df, codes),
    ]
    if combined_df is not None:
        results.extend([
            official_prefecture_comparison(combined_df, codes),
            official_fukui_vs_ishikawa_kanazawa_area_comparison(combined_df, codes),
        ])
    payload = {
        "method_notes": {
            "unit_of_analysis": "one FTAS survey respondent unless test name says reservation/day context",
            "official_data_source": "Code for Fukui FTAS CSVs and Ishikawa official tourism survey CSVs",
            "google_review_results_not_mixed": True,
            "shinkansen_event_date": str(SHINKANSEN_DATE.date()),
        },
        "results": [asdict(r) for r in results],
    }
    RESULTS_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    logger.info(f"Wrote official statistical results: {RESULTS_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
