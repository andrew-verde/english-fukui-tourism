#!/usr/bin/env python3
"""
audit_review_sample_readiness.py — Post-collection sample adequacy audit.

This is a diagnostic gate for the expanded Google Maps review collection path.
It does not decide thesis validity by itself, but it makes the main data-risk
visible after a deeper pull: whether the review sample is large enough and
balanced enough for the planned city-level statistical checks.

Reads:
  output/friction_analysis/reviews_unified.csv

Writes:
  output/review_sample_readiness.json
  output/review_sample_readiness.md
"""

import argparse
import ast
import json
import sys
from math import ceil
from pathlib import Path

import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils.logger import setup_logger

logger = setup_logger(__name__)

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
FRICTION_DIR = OUTPUT_DIR / "friction_analysis"
REVIEWS_CSV = FRICTION_DIR / "reviews_unified.csv"
TAGGED_MENTIONS_CSV = FRICTION_DIR / "tagged_mentions.csv"
RESULTS_JSON = OUTPUT_DIR / "review_sample_readiness.json"
RESULTS_MD = OUTPUT_DIR / "review_sample_readiness.md"

CITIES = ["Fukui", "Kanazawa", "Toyama"]
THEMES = ["Dinosaur", "Food", "Scenic", "Cultural", "Logistics"]
SHARED_CITY_THEMES = ["Food", "Scenic", "Cultural", "Logistics"]


def _load_reviews(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing input: {path}. Run make build-dataset first.")
    return pd.read_csv(path)


def _counts(series: pd.Series, index: list[str] | None = None) -> dict:
    counts = series.value_counts().sort_index()
    if index:
        counts = counts.reindex(index, fill_value=0)
    return {str(k): int(v) for k, v in counts.items()}


def _source_counts(df: pd.DataFrame) -> dict:
    if "source_platform" not in df.columns:
        return {}
    table = pd.crosstab(df["city"], df["source_platform"]).reindex(index=CITIES, fill_value=0)
    return {
        str(city): {str(source): int(value) for source, value in row.items()}
        for city, row in table.iterrows()
    }


def _theme_expected_count_diagnostics(df: pd.DataFrame, expected_min_target: float, themes: list[str] = THEMES) -> dict:
    themed = df[df["primary_theme"].notna()].copy()
    themed = themed[themed["city"].isin(CITIES) & themed["primary_theme"].isin(themes)]
    if themed.empty:
        return {
            "themed_reviews": 0,
            "themes": themes,
            "valid_for_chi_square_approximation": False,
            "reason": "No themed reviews available.",
        }

    ct = pd.crosstab(themed["city"], themed["primary_theme"]).reindex(
        index=CITIES,
        columns=themes,
        fill_value=0,
    )
    try:
        _chi2, _p, _dof, expected = stats.chi2_contingency(ct.to_numpy())
    except ValueError as exc:
        return {
            "themed_reviews": int(len(themed)),
            "themes": themes,
            "contingency_table": ct.to_dict(),
            "valid_for_chi_square_approximation": False,
            "reason": str(exc),
        }

    expected_min = float(expected.min()) if expected.size else 0.0
    expected_below_target = int((expected < expected_min_target).sum())
    scale_factor = expected_min_target / expected_min if expected_min > 0 else None
    estimated_themed_reviews_needed = (
        int(ceil(len(themed) * scale_factor)) if scale_factor and scale_factor > 1 else int(len(themed))
    )

    return {
        "themed_reviews": int(len(themed)),
        "themes": themes,
        "theme_counts": _counts(themed["primary_theme"], themes),
        "city_x_theme_table": {
            str(city): {str(theme): int(value) for theme, value in row.items()}
            for city, row in ct.iterrows()
        },
        "expected_min": expected_min,
        "expected_cells_below_target": expected_below_target,
        "expected_min_target": expected_min_target,
        "valid_for_chi_square_approximation": expected_below_target == 0,
        "estimated_themed_reviews_needed_for_target": estimated_themed_reviews_needed,
        "estimated_additional_themed_reviews_needed": max(0, estimated_themed_reviews_needed - int(len(themed))),
    }


def _friction_signal_density() -> dict:
    if not TAGGED_MENTIONS_CSV.exists():
        return {"available": False, "reason": f"Missing input: {TAGGED_MENTIONS_CSV}"}

    df = pd.read_csv(TAGGED_MENTIONS_CSV)
    if "friction_codes" not in df.columns:
        return {"available": False, "reason": "tagged_mentions.csv has no friction_codes column"}

    def has_friction_signal(value) -> bool:
        if pd.isna(value):
            return False
        if isinstance(value, list):
            return len(value) > 0
        text = str(value).strip()
        if text in {"", "[]", "nan", "None"}:
            return False
        try:
            parsed = ast.literal_eval(text)
            if isinstance(parsed, list):
                return len(parsed) > 0
        except (SyntaxError, ValueError):
            pass
        return True

    has_signal = df["friction_codes"].apply(has_friction_signal)
    by_city = df.assign(has_signal=has_signal).groupby("city")["has_signal"].agg(["sum", "count"])
    return {
        "available": True,
        "mentions_total": int(len(df)),
        "signal_mentions_total": int(has_signal.sum()),
        "signal_mentions_by_city": {
            str(city): {
                "signal_mentions": int(row["sum"]),
                "mentions": int(row["count"]),
                "signal_rate": float(row["sum"] / row["count"]) if row["count"] else 0.0,
            }
            for city, row in by_city.iterrows()
        },
    }


def build_readiness_report(
    reviews_csv: Path = REVIEWS_CSV,
    min_reviews_per_city: int = 100,
    expected_min_target: float = 5.0,
) -> dict:
    df = _load_reviews(reviews_csv)

    city_counts = _counts(df["city"], CITIES)
    below_city_target = {
        city: max(0, min_reviews_per_city - count)
        for city, count in city_counts.items()
    }
    poi_counts = (
        df.groupby(["city", "poi_name"]).size().reset_index(name="reviews").sort_values(["city", "reviews", "poi_name"])
        if {"city", "poi_name"}.issubset(df.columns)
        else pd.DataFrame(columns=["city", "poi_name", "reviews"])
    )
    low_poi_rows = poi_counts[poi_counts["reviews"] < 5]

    theme_diag = _theme_expected_count_diagnostics(df, expected_min_target, THEMES)
    shared_theme_diag = _theme_expected_count_diagnostics(df, expected_min_target, SHARED_CITY_THEMES)
    hard_gates = {
        "all_cities_present": set(df["city"].dropna().unique()) == set(CITIES),
        "min_reviews_per_city_met": all(gap == 0 for gap in below_city_target.values()),
        "shared_city_x_theme_expected_counts_met": bool(shared_theme_diag.get("valid_for_chi_square_approximation")),
    }

    return {
        "input_csv": str(reviews_csv),
        "reviews_total": int(len(df)),
        "min_reviews_per_city_target": min_reviews_per_city,
        "city_counts": city_counts,
        "additional_reviews_needed_by_city": below_city_target,
        "source_counts_by_city": _source_counts(df),
        "poi_count_summary": {
            "pois_total": int(poi_counts["poi_name"].nunique()) if not poi_counts.empty else 0,
            "min_reviews_per_poi": int(poi_counts["reviews"].min()) if not poi_counts.empty else 0,
            "median_reviews_per_poi": float(poi_counts["reviews"].median()) if not poi_counts.empty else 0.0,
            "max_reviews_per_poi": int(poi_counts["reviews"].max()) if not poi_counts.empty else 0,
            "pois_below_5_reviews": int(len(low_poi_rows)),
        },
        "theme_chi_square_readiness": theme_diag,
        "shared_theme_chi_square_readiness": shared_theme_diag,
        "friction_signal_density": _friction_signal_density(),
        "hard_gates": hard_gates,
        "ready_for_stronger_city_level_inference": all(hard_gates.values()),
        "ready_for_all_theme_city_level_inference": bool(theme_diag.get("valid_for_chi_square_approximation")) and all(
            v for k, v in hard_gates.items() if k != "shared_city_x_theme_expected_counts_met"
        ),
    }


def _write_markdown(report: dict, path: Path) -> None:
    lines = [
        "# Review Sample Readiness",
        "",
        f"Input: `{report['input_csv']}`",
        f"Total reviews: **{report['reviews_total']}**",
        "",
        "## City Counts",
        "",
        "| City | Reviews | Additional needed for target |",
        "|---|---:|---:|",
    ]
    for city, count in report["city_counts"].items():
        gap = report["additional_reviews_needed_by_city"].get(city, 0)
        lines.append(f"| {city} | {count} | {gap} |")

    theme = report["theme_chi_square_readiness"]
    lines.extend([
        "",
        "## City x Theme Readiness (All Themes)",
        "",
        f"Themed reviews: **{theme.get('themed_reviews', 0)}**",
        f"Minimum expected cell count: **{theme.get('expected_min', 0):.3f}**",
        f"Cells below target ({theme.get('expected_min_target', 5.0)}): **{theme.get('expected_cells_below_target', 'n/a')}**",
        f"Additional themed reviews estimated for target: **{theme.get('estimated_additional_themed_reviews_needed', 'n/a')}**",
        "",
        "## City x Theme Readiness (Shared Themes)",
        "",
        "Shared themes exclude `Dinosaur`, which is treated as a Fukui-specific destination theme rather than a comparable cross-city category.",
    ])
    shared_theme = report["shared_theme_chi_square_readiness"]
    lines.extend([
        f"Shared themed reviews: **{shared_theme.get('themed_reviews', 0)}**",
        f"Minimum expected cell count: **{shared_theme.get('expected_min', 0):.3f}**",
        f"Cells below target ({shared_theme.get('expected_min_target', 5.0)}): **{shared_theme.get('expected_cells_below_target', 'n/a')}**",
        "",
        "## Gates",
        "",
    ])
    for name, ok in report["hard_gates"].items():
        lines.append(f"- `{name}`: {'PASS' if ok else 'FAIL'}")
    lines.extend([
        "",
        f"Ready for stronger city-level inference: **{'YES' if report['ready_for_stronger_city_level_inference'] else 'NO'}**",
        "",
        "This audit checks sample adequacy only. It does not remove the need for exploratory framing, source-bias caveats, or manual review of keyword-code precision.",
        "",
    ])
    path.write_text("\n".join(lines))


def main() -> dict:
    parser = argparse.ArgumentParser(description="Audit whether expanded review data is statistically ready")
    parser.add_argument("--input", type=Path, default=REVIEWS_CSV, help="Review-level dataset CSV")
    parser.add_argument("--min-reviews-per-city", type=int, default=100, help="Minimum review rows required per city")
    parser.add_argument("--expected-min-target", type=float, default=5.0, help="Target minimum expected count for chi-square cells")
    args = parser.parse_args()

    report = build_readiness_report(
        reviews_csv=args.input,
        min_reviews_per_city=args.min_reviews_per_city,
        expected_min_target=args.expected_min_target,
    )
    RESULTS_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    _write_markdown(report, RESULTS_MD)

    logger.info(f"Output written: {RESULTS_JSON}")
    logger.info(f"Output written: {RESULTS_MD}")
    logger.info(f"Ready for stronger city-level inference: {report['ready_for_stronger_city_level_inference']}")
    return report


if __name__ == "__main__":
    main()
