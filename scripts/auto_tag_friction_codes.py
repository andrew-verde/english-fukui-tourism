#!/usr/bin/env python3
"""
auto_tag_friction_codes.py — Tag reviews and mentions with friction/nudge codes.

Reads:
  output/friction_analysis/reviews_unified.csv
  output/friction_analysis/mentions_dataset.csv
  config/friction_codebook.yaml

Writes:
  output/friction_analysis/tagged_reviews.csv    (reviews + one bool col per code)
  output/friction_analysis/tagged_mentions.csv   (mentions + one bool col per code)

Both outputs include:
  - one bool column per codebook code
  - friction_codes  (list of matched friction code names)
  - nudge_codes     (list of matched nudge code names)
  - all_codes       (combined)

Usage:
    python scripts/auto_tag_friction_codes.py                  # keyword tagger (primary)
    python scripts/auto_tag_friction_codes.py --engine llm     # LLM comparator (ADR 0001 §4)

The keyword engine is the primary instrument. The LLM engine writes to
separate *_llm.csv outputs so the two never overwrite each other; it exists
only for the post-hoc gold-set comparison and requires OPENAI_API_KEY (.env).
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from src.friction.tagger import load_codebook, tag_dataframe
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

OUTPUT_DIR   = Path(__file__).resolve().parent.parent / "output"
FRICTION_DIR = OUTPUT_DIR / "friction_analysis"
CONFIG_DIR   = Path(__file__).resolve().parent.parent / "config"

REVIEWS_CSV          = FRICTION_DIR / "reviews_unified.csv"
MENTIONS_CSV         = FRICTION_DIR / "mentions_dataset.csv"
TAGGED_REVIEWS_CSV   = FRICTION_DIR / "tagged_reviews.csv"
TAGGED_MENTIONS_CSV  = FRICTION_DIR / "tagged_mentions.csv"
CODEBOOK_PATH        = CONFIG_DIR / "friction_codebook.yaml"


def tag_file(input_path: Path, output_path: Path, text_col: str, codebook: dict,
             label: str, llm_tagger=None):
    if not input_path.exists():
        logger.error(f"Input not found: {input_path}")
        logger.error(f"Run the preceding pipeline step first.")
        return False

    df = pd.read_csv(input_path)
    logger.info(f"{label}: {len(df)} rows loaded")

    if llm_tagger is not None:
        tagged = llm_tagger.tag_dataframe(df, text_col=text_col, delay=0.5)
        n_err = int(tagged["llm_error"].sum())
        if n_err:
            logger.warning(f"  {n_err} rows failed LLM tagging (llm_error=True); "
                           "exclude them from any comparison, do not treat as no-friction")
    else:
        tagged = tag_dataframe(df, text_col=text_col, codebook=codebook)
    tagged.to_csv(output_path, index=False)

    # Summary stats
    friction_codes = [c for c, a in codebook.items() if a["type"] == "friction"]
    nudge_codes    = [c for c, a in codebook.items() if a["type"] == "nudge"]

    any_friction = tagged[friction_codes].any(axis=1).sum()
    any_nudge    = tagged[nudge_codes].any(axis=1).sum()

    logger.info(f"  Rows with ≥1 friction code: {any_friction} ({100*any_friction/len(tagged):.1f}%)")
    logger.info(f"  Rows with ≥1 nudge code:    {any_nudge} ({100*any_nudge/len(tagged):.1f}%)")
    logger.info(f"  Output: {output_path}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Tag reviews/mentions with friction codes")
    parser.add_argument("--engine", choices=["keyword", "llm"], default="keyword",
                        help="keyword = primary deterministic tagger; "
                             "llm = optional OpenAI comparator (ADR 0001)")
    parser.add_argument("--model", default="gpt-4o-mini",
                        help="OpenAI model for --engine llm")
    args = parser.parse_args()

    logger.info("=" * 55)
    logger.info("Auto-tag friction and nudge codes")
    logger.info("=" * 55)

    if not CODEBOOK_PATH.exists():
        logger.error(f"Codebook not found: {CODEBOOK_PATH}")
        sys.exit(1)

    codebook = load_codebook(CODEBOOK_PATH)
    logger.info(f"Codebook loaded: {len(codebook)} codes "
                f"({sum(1 for a in codebook.values() if a['type']=='friction')} friction, "
                f"{sum(1 for a in codebook.values() if a['type']=='nudge')} nudge)")

    FRICTION_DIR.mkdir(parents=True, exist_ok=True)

    llm_tagger = None
    reviews_out, mentions_out = TAGGED_REVIEWS_CSV, TAGGED_MENTIONS_CSV
    if args.engine == "llm":
        from dotenv import load_dotenv
        load_dotenv()
        from src.friction.llm_tagger import LLMFrictionTagger
        llm_tagger = LLMFrictionTagger(model=args.model, codebook=codebook)
        reviews_out  = FRICTION_DIR / "tagged_reviews_llm.csv"
        mentions_out = FRICTION_DIR / "tagged_mentions_llm.csv"
        logger.info(f"Engine: LLM comparator ({args.model}) — outputs *_llm.csv")
    else:
        logger.info("Engine: keyword (primary instrument)")

    ok1 = tag_file(REVIEWS_CSV,  reviews_out,  "review_text",   codebook, "Reviews",  llm_tagger)
    ok2 = tag_file(MENTIONS_CSV, mentions_out, "sentence_text", codebook, "Mentions", llm_tagger)

    if ok1 and ok2:
        logger.info("")
        logger.info("Tagging complete")
        logger.info("Next step: make summarize")
    logger.info("=" * 55)


if __name__ == "__main__":
    main()
