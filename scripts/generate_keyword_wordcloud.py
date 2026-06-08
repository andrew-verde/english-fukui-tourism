#!/usr/bin/env python3
"""
generate_keyword_wordcloud.py — Build a ranked keyword panel + word cloud figure.

Reads:
  output/friction_analysis/reviews_unified.csv

Writes:
  output/friction_analysis/figures/google_places_keyword_wordcloud_<city>.png
  output/friction_analysis/figures/english_review_keyword_wordcloud_<city>.png
  output/official_fukui/japanese_kanko_keyword_wordcloud_<scope>.png

Usage:
    .venv/bin/python3 scripts/generate_keyword_wordcloud.py
    .venv/bin/python3 scripts/generate_keyword_wordcloud.py --city Kanazawa
    .venv/bin/python3 scripts/generate_keyword_wordcloud.py --city all
    .venv/bin/python3 scripts/generate_keyword_wordcloud.py --comparison-clouds
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.analysis.keyword_cloud import generate_japanese_tourism_keyword_cloud_report, generate_keyword_cloud_report
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

ROOT_DIR = Path(__file__).resolve().parent.parent
INPUT_CSV = ROOT_DIR / "output" / "friction_analysis" / "reviews_unified.csv"
OFFICIAL_CSV = ROOT_DIR / "output" / "official_fukui" / "official_surveys_tagged_combined.csv"
FIGURES_DIR = ROOT_DIR / "output" / "friction_analysis" / "figures"
OFFICIAL_DIR = ROOT_DIR / "output" / "official_fukui"
JAPANESE_TEXT_COLUMNS = [
    "transport_satisfaction_reason",
    "overall_satisfaction_reason",
    "product_service_satisfaction_reason",
    "inconvenience_text",
    "facility_needs",
    "fukui_needs",
    "prefecture_needs",
    "recommendation_reason",
    "visited_before_free_text",
    "planned_after_free_text",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a keyword word-cloud figure from Google Places reviews.")
    parser.add_argument(
        "--input-csv",
        type=Path,
        default=INPUT_CSV,
        help="Review-level dataset CSV. Defaults to output/friction_analysis/reviews_unified.csv",
    )
    parser.add_argument(
        "--city",
        default="Fukui",
        help="City filter. Use 'all' to include every city in the dataset.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional output PNG path.",
    )
    parser.add_argument("--top-n", type=int, default=10, help="Number of ranked keywords to show in the table.")
    parser.add_argument("--cloud-terms", type=int, default=18, help="Number of keywords to place in the cloud.")
    parser.add_argument("--min-frequency", type=int, default=2, help="Minimum keyword frequency to include.")
    parser.add_argument("--seed", type=int, default=7, help="Seed for deterministic word placement.")
    parser.add_argument(
        "--source-platform",
        default="",
        help="Optional source_platform filter for the generic review cloud. Empty includes all review sources.",
    )
    parser.add_argument(
        "--comparison-clouds",
        action="store_true",
        help="Also generate English-review and Japanese kanko-survey overall keyword clouds.",
    )
    parser.add_argument(
        "--official-csv",
        type=Path,
        default=OFFICIAL_CSV,
        help="Combined official kanko survey CSV used for the Japanese keyword cloud.",
    )
    parser.add_argument(
        "--official-prefecture",
        default="",
        help="Optional official survey_prefecture filter, e.g. Fukui or Ishikawa. Empty uses all official rows.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    city = None if args.city.lower() == "all" else args.city

    if args.output is None:
        city_slug = "all_cities" if city is None else city.strip().lower().replace(" ", "_")
        output_path = FIGURES_DIR / f"google_places_keyword_wordcloud_{city_slug}.png"
    else:
        output_path = args.output

    logger.info("=" * 55)
    logger.info("Generate keyword word cloud")
    logger.info("=" * 55)
    logger.info(f"Input CSV:  {args.input_csv}")
    logger.info(f"City:       {city or 'All Cities'}")
    logger.info(f"Output PNG: {output_path}")

    ranked_df, report_path = generate_keyword_cloud_report(
        input_csv=args.input_csv,
        output_path=output_path,
        city=city,
        source_platform=args.source_platform or None,
        top_n=args.top_n,
        cloud_terms=args.cloud_terms,
        min_frequency=args.min_frequency,
        seed=args.seed,
    )

    if ranked_df.empty:
        logger.warning("No keywords were found after filtering.")
    else:
        logger.info("Top keywords:")
        for row in ranked_df.itertuples(index=False):
            logger.info(f"  {row.rank:>2}. {row.term:<24} {row.percentage:>5.1f}%")

    logger.info(f"Saved figure: {report_path}")

    if args.comparison_clouds:
        city_slug = "all_cities" if city is None else city.strip().lower().replace(" ", "_")
        official_scope = args.official_prefecture.strip()
        official_slug = official_scope.lower().replace(" ", "_") if official_scope else "fukui_ishikawa"

        english_output = FIGURES_DIR / f"english_review_keyword_wordcloud_{city_slug}.png"
        japanese_output = OFFICIAL_DIR / f"japanese_kanko_keyword_wordcloud_{official_slug}.png"

        english_ranked, english_path = generate_keyword_cloud_report(
            input_csv=args.input_csv,
            output_path=english_output,
            city=city,
            source_platform=args.source_platform or None,
            top_n=args.top_n,
            cloud_terms=args.cloud_terms,
            min_frequency=args.min_frequency,
            seed=args.seed,
        )
        japanese_ranked, japanese_path = generate_japanese_tourism_keyword_cloud_report(
            input_csv=args.official_csv,
            output_path=japanese_output,
            title="JAPANESE KANKO SURVEY",
            subtitle="KEYWORD CLOUD（キーワードクラウド）",
            text_cols=JAPANESE_TEXT_COLUMNS,
            prefecture=official_scope or None,
            top_n=args.top_n,
            cloud_terms=args.cloud_terms,
            min_frequency=args.min_frequency,
            seed=args.seed,
        )

        logger.info(f"Saved English review keyword cloud: {english_path}")
        if english_ranked.empty:
            logger.warning("No English review keywords were found after filtering.")
        logger.info(f"Saved Japanese kanko keyword cloud: {japanese_path}")
        if japanese_ranked.empty:
            logger.warning("No Japanese kanko keywords were found after filtering.")
    logger.info("=" * 55)


if __name__ == "__main__":
    main()
