#!/usr/bin/env python3
"""
generate_keyword_wordcloud.py — Build a ranked keyword panel + word cloud figure.

Reads:
  output/friction_analysis/reviews_unified.csv
  output/multilingual_review_analysis/tagged_reviews_multilingual.csv

Writes:
  output/friction_analysis/figures/google_maps_review_keyword_wordcloud_<city>.png
  output/friction_analysis/figures/english_review_keyword_wordcloud_<city>.png
  output/friction_analysis/figures/japanese_review_keyword_wordcloud_<city>.png

Usage:
    .venv/bin/python3 scripts/generate_keyword_wordcloud.py
    .venv/bin/python3 scripts/generate_keyword_wordcloud.py --city Kanazawa
    .venv/bin/python3 scripts/generate_keyword_wordcloud.py --city all
    .venv/bin/python3 scripts/generate_keyword_wordcloud.py --comparison-clouds
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", os.path.join(tempfile.gettempdir(), "matplotlib"))

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.analysis.keyword_cloud import generate_keyword_cloud_report, generate_review_language_keyword_cloud_report
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

ROOT_DIR = Path(__file__).resolve().parent.parent
INPUT_CSV = ROOT_DIR / "output" / "friction_analysis" / "reviews_unified.csv"
MULTILINGUAL_CSV = ROOT_DIR / "output" / "multilingual_review_analysis" / "tagged_reviews_multilingual.csv"
FIGURES_DIR = ROOT_DIR / "output" / "friction_analysis" / "figures"


def _as_white_rgb(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2:
        return np.repeat(image[..., None], 3, axis=2)
    if image.shape[2] == 3:
        return image
    rgb = image[..., :3]
    alpha = image[..., 3:4]
    return rgb * alpha + (1.0 - alpha)


def merge_keyword_cloud_panels(paths: list[Path], output_path: Path, gutter_px: int = 28) -> Path:
    """Stack already-rendered keyword cloud panels into one white-background PNG."""
    panels = [_as_white_rgb(plt.imread(path)) for path in paths]
    if not panels:
        raise ValueError("At least one keyword cloud panel is required.")

    max_width = max(panel.shape[1] for panel in panels)
    padded_panels = []
    for panel in panels:
        if panel.shape[1] == max_width:
            padded_panels.append(panel)
            continue
        left = (max_width - panel.shape[1]) // 2
        right = max_width - panel.shape[1] - left
        padded_panels.append(np.pad(panel, ((0, 0), (left, right), (0, 0)), constant_values=1.0))

    gutter = np.ones((gutter_px, max_width, 3), dtype=padded_panels[0].dtype)
    merged_parts = []
    for idx, panel in enumerate(padded_panels):
        if idx:
            merged_parts.append(gutter)
        merged_parts.append(panel)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.imsave(output_path, np.vstack(merged_parts))
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a keyword word-cloud figure from Google Maps reviews.")
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
        help="Also generate separate English- and Japanese-language Google review keyword clouds.",
    )
    parser.add_argument(
        "--multilingual-csv",
        type=Path,
        default=MULTILINGUAL_CSV,
        help="Review-level multilingual CSV used for English/Japanese comparison clouds.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    city = None if args.city.lower() == "all" else args.city

    if args.output is None:
        city_slug = "all_cities" if city is None else city.strip().lower().replace(" ", "_")
        output_path = FIGURES_DIR / f"google_maps_review_keyword_wordcloud_{city_slug}.png"
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

        english_output = FIGURES_DIR / f"english_review_keyword_wordcloud_{city_slug}.png"
        japanese_output = FIGURES_DIR / f"japanese_review_keyword_wordcloud_{city_slug}.png"

        english_ranked, english_path = generate_review_language_keyword_cloud_report(
            input_csv=args.multilingual_csv,
            output_path=english_output,
            language_group="english",
            title="ENGLISH GOOGLE REVIEWS（英語グーグルレビュー）",
            subtitle="WORD CLOUD（ワードクラウド）",
            city=city,
            source_platform="google",
            top_n=args.top_n,
            cloud_terms=args.cloud_terms,
            min_frequency=args.min_frequency,
            seed=args.seed,
        )
        japanese_ranked, japanese_path = generate_review_language_keyword_cloud_report(
            input_csv=args.multilingual_csv,
            output_path=japanese_output,
            language_group="japanese",
            title="JAPANESE GOOGLE REVIEWS（日本語グーグルレビュー）",
            subtitle="WORD CLOUD（ワードクラウド）",
            city=city,
            source_platform="google",
            top_n=args.top_n,
            cloud_terms=args.cloud_terms,
            min_frequency=args.min_frequency,
            seed=args.seed,
        )

        logger.info(f"Saved English review keyword cloud: {english_path}")
        if english_ranked.empty:
            logger.warning("No English review keywords were found after filtering.")
        logger.info(f"Saved Japanese review keyword cloud: {japanese_path}")
        if japanese_ranked.empty:
            logger.warning("No Japanese review keywords were found after filtering.")
    logger.info("=" * 55)


if __name__ == "__main__":
    main()
