#!/usr/bin/env python3
"""
build_mentions_dataset.py — Split reviews into sentence-level mentions.

Reads:
  output/friction_analysis/reviews_unified.csv

Writes:
  output/friction_analysis/mentions_dataset.csv

Schema:
  mention_id, review_id, city, poi_name, poi_category,
  sentence_text, sentence_index

Usage:
    python scripts/build_mentions_dataset.py
"""

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from src.friction.mention_splitter import split_to_mentions
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

OUTPUT_DIR       = Path(__file__).resolve().parent.parent / "output"
FRICTION_DIR     = OUTPUT_DIR / "friction_analysis"
INPUT_CSV        = FRICTION_DIR / "reviews_unified.csv"
OUTPUT_CSV       = FRICTION_DIR / "mentions_dataset.csv"


def main():
    if not INPUT_CSV.exists():
        logger.error(f"Input not found: {INPUT_CSV}")
        logger.error("Run build_analysis_dataset.py first.")
        sys.exit(1)

    logger.info("=" * 55)
    logger.info("Build mentions dataset (sentence-level split)")
    logger.info("=" * 55)

    df = pd.read_csv(INPUT_CSV)
    logger.info(f"Loaded {len(df)} reviews")

    all_mentions = []
    raw_sentence_count = 0
    kept_sentence_count = 0
    dropped_too_short = 0
    dropped_punct_only = 0
    min_chars = int(os.getenv("MENTION_MIN_CHARS", "4"))

    for _, row in df.iterrows():
        text = str(row["review_text"]) if pd.notna(row["review_text"]) else ""
        # Diagnostics: estimate how many sentences were produced before filters.
        # Use the same nltk tokenizer as the splitter (via helper) would, but
        # avoid re-downloading punkt by importing nltk directly here.
        try:
            import nltk  # noqa: PLC0415
            try:
                nltk.data.find("tokenizers/punkt")
            except LookupError:
                nltk.download("punkt", quiet=True)
            raw_sents = nltk.sent_tokenize(text) if text.strip() else []
        except Exception:
            raw_sents = []
        raw_sentence_count += len(raw_sents)
        for s in raw_sents:
            st = s.strip()
            if len(st) < min_chars:
                dropped_too_short += 1
            elif not re.search(r"[A-Za-z0-9]", st):
                dropped_punct_only += 1

        mentions = split_to_mentions(
            review_id=str(row["review_id"]),
            city=str(row["city"]),
            poi_name=str(row["poi_name"]),
            poi_category=str(row["poi_category"]),
            text=text,
        )
        all_mentions.extend(mentions)
        kept_sentence_count += len(mentions)

    FRICTION_DIR.mkdir(parents=True, exist_ok=True)
    mentions_df = pd.DataFrame(all_mentions, columns=[
        "mention_id", "review_id", "city", "poi_name", "poi_category",
        "sentence_text", "sentence_index",
    ])
    mentions_df.to_csv(OUTPUT_CSV, index=False)

    logger.info(f"Output written: {OUTPUT_CSV}")
    logger.info(f"  Total mentions: {len(mentions_df)}")
    logger.info(f"  Avg sentences per review: {len(mentions_df)/len(df):.1f}")
    if raw_sentence_count:
        filtered = raw_sentence_count - kept_sentence_count
        logger.info(f"  Raw sentences: {raw_sentence_count}")
        logger.info(f"  Filtered out:  {filtered} ({100*filtered/raw_sentence_count:.1f}%)")
        logger.info(f"    Too short (<{min_chars} chars): {dropped_too_short}")
        logger.info(f"    Punct/emoji only:               {dropped_punct_only}")
    for city, grp in mentions_df.groupby("city"):
        logger.info(f"  {city:<12} {len(grp)} mentions")
    logger.info("")
    logger.info("Next step: make tag-codes")
    logger.info("=" * 55)


if __name__ == "__main__":
    main()
