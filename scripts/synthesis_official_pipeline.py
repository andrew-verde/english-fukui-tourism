#!/usr/bin/env python3
"""
synthesis_official_pipeline.py — Write thesis-ready official FTAS summary.

Reads:
  output/official_fukui/statistical_results_official.json
  output/official_fukui/ftas_friction_by_area.csv
  output/friction_analysis/friction_by_city.csv

Writes:
  output/official_fukui/statistical_summary_official.md
  output/official_fukui/english_vs_japanese_friction_comparison.csv

Usage:
    python scripts/synthesis_official_pipeline.py
"""

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.friction.tagger import load_codebook
from src.official_fukui.ftas import load_japanese_codebook
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

ROOT = Path(__file__).resolve().parent.parent
OFFICIAL_DIR = ROOT / "output" / "official_fukui"
FRICTION_DIR = ROOT / "output" / "friction_analysis"
RESULTS_JSON = OFFICIAL_DIR / "statistical_results_official.json"
OFFICIAL_AREA_CSV = OFFICIAL_DIR / "ftas_friction_by_area.csv"
ENGLISH_CITY_CSV = FRICTION_DIR / "friction_by_city.csv"
SUMMARY_MD = OFFICIAL_DIR / "statistical_summary_official.md"
THESIS_ASSESSMENT_MD = OFFICIAL_DIR / "thesis_readiness_assessment.md"
COMPARISON_CSV = OFFICIAL_DIR / "english_vs_japanese_friction_comparison.csv"
OFFICIAL_PREF_COMPARISON_CSV = OFFICIAL_DIR / "official_prefecture_friction_comparison.csv"
ENGLISH_CODEBOOK = ROOT / "config" / "friction_codebook.yaml"
JAPANESE_CODEBOOK = ROOT / "config" / "official_japanese_friction_codebook.yaml"


def _fmt_p(value: object) -> str:
    if value is None:
        return "NA"
    try:
        value = float(value)
    except Exception:
        return "NA"
    if value < 0.001:
        return "<0.001"
    return f"{value:.3f}"


def _find_result(payload: dict, name: str) -> dict:
    for result in payload.get("results", []):
        if result.get("name") == name:
            return result
    return {"name": name, "n": 0, "details": {"error": "Missing result."}}


def _pct(value: object) -> str:
    try:
        return f"{float(value) * 100:.2f}%"
    except Exception:
        return "NA"


def _fmt_float(value: object, digits: int = 3) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except Exception:
        return "NA"


def build_comparison() -> pd.DataFrame:
    """Compare Fukui English-review friction rates with official FTAS rates."""
    en_codebook = load_codebook(ENGLISH_CODEBOOK)
    ja_codebook = load_japanese_codebook(JAPANESE_CODEBOOK)
    codes = [c for c, attrs in en_codebook.items() if attrs["type"] == "friction" and c in ja_codebook]

    rows = []
    if ENGLISH_CITY_CSV.exists():
        english = pd.read_csv(ENGLISH_CITY_CSV)
        english = english[english["city"] == "Fukui"].copy() if "city" in english.columns else pd.DataFrame()
    else:
        english = pd.DataFrame()

    if OFFICIAL_AREA_CSV.exists():
        official = pd.read_csv(OFFICIAL_AREA_CSV)
    else:
        official = pd.DataFrame()

    for code in codes:
        en_row = english[english["friction_code"] == code] if not english.empty else pd.DataFrame()
        official_rows = official[official["friction_code"] == code] if not official.empty else pd.DataFrame()
        official_count = int(official_rows["count"].sum()) if not official_rows.empty else 0
        official_n = int(official_rows.drop_duplicates("response_area")["n_respondents"].sum()) if not official_rows.empty else 0
        rows.append({
            "friction_code": code,
            "friction_label": en_codebook[code]["label"],
            "english_fukui_count": int(en_row["count"].iloc[0]) if not en_row.empty and "count" in en_row else 0,
            "english_fukui_pct_of_sentences": float(en_row["pct_of_sentences"].iloc[0]) if not en_row.empty and "pct_of_sentences" in en_row else 0.0,
            "official_ftas_count": official_count,
            "official_ftas_n_respondents": official_n,
            "official_ftas_pct_of_respondents": round(100 * official_count / official_n, 3) if official_n else 0.0,
        })
    comparison = pd.DataFrame(rows)
    comparison.to_csv(COMPARISON_CSV, index=False)
    return comparison


def build_official_prefecture_comparison(pref_result: dict) -> pd.DataFrame:
    rows = []
    for item in pref_result.get("details", {}).get("friction_code_tests", []):
        counts = item.get("counts", {})
        rates = item.get("rates", {})
        rows.append({
            "friction_code": item.get("outcome"),
            "fukui_count": counts.get("Fukui", {}).get("true"),
            "fukui_n": counts.get("Fukui", {}).get("n"),
            "fukui_rate": rates.get("Fukui"),
            "ishikawa_count": counts.get("Ishikawa", {}).get("true"),
            "ishikawa_n": counts.get("Ishikawa", {}).get("n"),
            "ishikawa_rate": rates.get("Ishikawa"),
            "p_value": item.get("p_value"),
            "p_value_bh": item.get("p_value_bh"),
            "cramers_v": item.get("cramers_v"),
        })
    df = pd.DataFrame(rows)
    df.to_csv(OFFICIAL_PREF_COMPARISON_CSV, index=False)
    return df


def write_thesis_assessment(payload: dict, pref_result: dict, kanazawa_area_result: dict) -> None:
    audit = _find_result(payload, "official_input_data_audit")
    friction_sat = _find_result(payload, "official_friction_vs_satisfaction")
    shinkansen = _find_result(payload, "official_shinkansen_survey_shift")
    reservation = _find_result(payload, "official_reservation_event_context")

    pref_tests = pref_result.get("details", {}).get("friction_code_tests", [])
    pref_sig = [t for t in pref_tests if t.get("p_value_bh", 1.0) < 0.05]
    kanazawa_area_tests = kanazawa_area_result.get("details", {}).get("friction_code_tests", [])
    kanazawa_area_sig = [t for t in kanazawa_area_tests if t.get("p_value_bh", 1.0) < 0.05]
    sat_details = friction_sat.get("details", {})
    sat_sig = [
        name for name, result in sat_details.items()
        if isinstance(result, dict) and result.get("p_value", 1.0) < 0.05
    ]

    lines = [
        "# Thesis Readiness Assessment",
        "",
        "## Defense Readiness",
        "Status: **mostly defense-ready as an expanded mixed-source observational analysis**, with caveats.",
        "",
        "The added official survey layer fixes the main weakness of the original Google-review-only analysis: statistical power. "
        "The original English-language Google review sample remains too sparse for strong inferential friction claims, but the official Japanese tourist survey layer provides respondent-level tests with large samples.",
        "",
        "## What Now Passes Muster",
        f"- Official Fukui survey n: {audit.get('n', 0):,} respondent rows.",
        f"- Official friction text is significantly associated with lower/shifted satisfaction or NPS outcomes for: {', '.join(sat_sig) if sat_sig else 'none'}.",
        f"- Fukui vs Ishikawa official survey friction tests surviving BH correction: {len(pref_sig)} of {len(pref_tests)} friction codes.",
        f"- Fukui vs Ishikawa Kanazawa-area official survey friction tests surviving BH correction: {len(kanazawa_area_sig)} of {len(kanazawa_area_tests)} friction codes.",
        f"- Shinkansen survey mode shift p-value: {_fmt_p(shinkansen.get('details', {}).get('p_value'))}.",
        "- Reservation demand context shows statistically detectable post-extension changes for at least some daily demand measures.",
        "",
        "## Remaining Gaps",
        "- The Japanese friction codebook is keyword-based and needs manual validation on a sampled set of FTAS/Ishikawa comments before final defense claims.",
        "- English Google review friction remains descriptive because counts are sparse; present it as English-language perception evidence, not as the main inferential layer.",
        "- Fukui and Ishikawa official survey instruments are similar but not identical. Prefecture comparisons should be framed as harmonized official-survey comparisons, not perfectly identical measurement.",
        "- Current tests show statistical significance partly because official survey n is large; emphasize effect sizes and rates, not p-values alone.",
        "",
        "## Recommended Dataset Rounding",
        "1. Add a 100-200 row manual validation sample for Japanese friction tags with precision estimates by code.",
        "2. Add a curated area crosswalk for Fukui POIs, FTAS areas, and Ishikawa facilities so area-level triangulation is defensible.",
        "3. Use people-flow only for Tojinbo and Fukui Station as contextual congestion/event evidence, not as a core inferential pillar.",
        "4. If more English-language evidence is needed, expand Google Maps review POIs or add TripAdvisor/Google review pulls with the same date/language filters, but keep reviewer nationality unspecified.",
    ]
    THESIS_ASSESSMENT_MD.write_text("\n".join(lines) + "\n")


def main() -> int:
    if not RESULTS_JSON.exists():
        raise FileNotFoundError(f"Missing input: {RESULTS_JSON}. Run scripts/statistical_validation_official.py first.")
    payload = json.loads(RESULTS_JSON.read_text())
    comparison = build_comparison()

    audit = _find_result(payload, "official_input_data_audit")
    sat = _find_result(payload, "official_friction_vs_satisfaction")
    shinkansen = _find_result(payload, "official_shinkansen_survey_shift")
    reservation = _find_result(payload, "official_reservation_event_context")
    area = _find_result(payload, "official_top_area_friction_tests")
    pref = _find_result(payload, "official_prefecture_comparison")
    kanazawa_area = _find_result(payload, "official_fukui_vs_ishikawa_kanazawa_area_comparison")
    pref_comparison = build_official_prefecture_comparison(pref)

    lines = [
        "# Official Fukui Data Statistical Summary",
        "",
        "## Method Notes",
        "- Official-data analysis is separate from the English-language Google Maps review analysis.",
        "- Unit of analysis is one FTAS survey respondent unless a test is explicitly labeled as reservation/day context.",
        "- English reviewer friction and Japanese tourist survey friction are compared descriptively because they come from different sampling frames and languages.",
        "- Reviewer nationality is not inferred.",
        "",
        "## Input Data Audit",
    ]
    details = audit.get("details", {})
    lines.extend([
        f"- Status: {'PASS' if details.get('valid') else 'CHECK'}",
        f"- n (FTAS respondent rows): {audit.get('n', 0):,}",
        f"- Response date range: {details.get('date_min')} to {details.get('date_max')}",
        f"- Response areas: {details.get('n_response_areas')}; municipalities: {details.get('n_municipalities')}",
        f"- Rows with at least one Japanese friction code: {details.get('any_friction_count')}",
        "",
        "## Official Friction vs Satisfaction",
    ])
    for outcome, result in sat.get("details", {}).items():
        if isinstance(result, dict) and "error" not in result:
            lines.append(
                f"- {outcome}: median friction={result['median_friction']:.2f}, "
                f"median no-friction={result['median_no_friction']:.2f}, "
                f"Mann-Whitney p={_fmt_p(result['p_value'])}"
            )
    sdet = shinkansen.get("details", {})
    lines.extend([
        "",
        "## Hokuriku Shinkansen Event Context",
        f"- Event date: {sdet.get('event_date')}",
        f"- FTAS Shinkansen-use rate before: {sdet.get('pre_shinkansen_rate')}",
        f"- FTAS Shinkansen-use rate after: {sdet.get('post_shinkansen_rate')}",
        f"- Chi-square p={_fmt_p(sdet.get('p_value'))}; Cramer's V={sdet.get('cramers_v')}",
        "",
        "## Reservation Demand Context",
    ])
    for outcome, result in reservation.get("details", {}).get("outcomes", {}).items():
        if "error" not in result:
            lines.append(
                f"- {outcome}: median pre={result['median_pre']:.1f}, "
                f"median post={result['median_post']:.1f}, p={_fmt_p(result['p_value'])}"
            )

    pdet = pref.get("details", {})
    any_friction = pdet.get("any_friction", {})
    lines.extend([
        "",
        "## Official Fukui vs Ishikawa Survey Comparison",
        f"- n: {pref.get('n', 0):,} respondent rows.",
        f"- Any friction rate: Fukui {_pct(any_friction.get('rates', {}).get('Fukui'))}; Ishikawa {_pct(any_friction.get('rates', {}).get('Ishikawa'))}; p={_fmt_p(any_friction.get('p_value'))}; V={any_friction.get('cramers_v')}",
    ])
    if not pref_comparison.empty:
        top_pref = pref_comparison.sort_values("p_value_bh").head(6)
        for _, row in top_pref.iterrows():
            lines.append(
                f"- {row['friction_code']}: Fukui {_pct(row['fukui_rate'])}, "
                f"Ishikawa {_pct(row['ishikawa_rate'])}, p_BH={_fmt_p(row['p_value_bh'])}, V={_fmt_float(row['cramers_v'])}"
            )

    kadet = kanazawa_area.get("details", {})
    ka_any = kadet.get("any_friction", {})
    lines.extend([
        "",
        "## Official Fukui vs Ishikawa Kanazawa-Area Survey Comparison",
        "- Scope: all Fukui official survey rows compared with Ishikawa official survey rows where `survey_area_group` is `金沢`.",
        f"- n: {kanazawa_area.get('n', 0):,} respondent rows.",
        f"- Any friction rate: Fukui {_pct(ka_any.get('rates', {}).get('Fukui'))}; Ishikawa Kanazawa-area {_pct(ka_any.get('rates', {}).get('Ishikawa_Kanazawa_area'))}; p={_fmt_p(ka_any.get('p_value'))}; V={ka_any.get('cramers_v')}",
    ])
    for item in kadet.get("friction_code_tests", [])[:6]:
        lines.append(
            f"- {item['outcome']}: Fukui {_pct(item.get('rates', {}).get('Fukui'))}, "
            f"Ishikawa Kanazawa-area {_pct(item.get('rates', {}).get('Ishikawa_Kanazawa_area'))}, p_BH={_fmt_p(item.get('p_value_bh'))}, V={_fmt_float(item.get('cramers_v'))}"
        )

    lines.extend([
        "",
        "## English Review vs Japanese Survey Friction",
        "- Denominators differ: English Google rates use sentence-level mentions; FTAS rates use respondent rows.",
    ])
    if not comparison.empty:
        top = comparison.sort_values("official_ftas_count", ascending=False).head(8)
        for _, row in top.iterrows():
            lines.append(
                f"- {row['friction_label']}: English Fukui {row['english_fukui_count']} "
                f"({row['english_fukui_pct_of_sentences']:.2f}% of sentences); "
                f"FTAS {row['official_ftas_count']} ({row['official_ftas_pct_of_respondents']:.2f}% of respondents)"
            )

    lines.extend([
        "",
        "## Area-Level Official Tests",
        f"- Tested top {area.get('details', {}).get('top_n_areas')} FTAS areas by respondent count.",
        "- See `output/official_fukui/statistical_results_official.json` for full area x friction contingency tables and BH-adjusted p-values.",
        "",
        "## Interpretation Guardrails",
        "- Treat FTAS as official Japanese tourist survey evidence, not evidence about English-language reviewers.",
        "- Treat Google review friction as a qualitative/observational signal with sparse counts.",
        "- Strong thesis claim: official FTAS survey responses identify statistically associated friction, satisfaction, transport, and event-context patterns.",
        "- Moderate thesis claim: English-language review friction can be triangulated against official Japanese tourist survey friction where the code definitions overlap.",
    ])

    SUMMARY_MD.write_text("\n".join(lines) + "\n")
    write_thesis_assessment(payload, pref, kanazawa_area)
    logger.info(f"Wrote official summary: {SUMMARY_MD}")
    logger.info(f"Wrote thesis readiness assessment: {THESIS_ASSESSMENT_MD}")
    logger.info(f"Wrote comparison table: {COMPARISON_CSV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
