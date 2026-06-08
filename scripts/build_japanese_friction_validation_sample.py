#!/usr/bin/env python3
"""
build_japanese_friction_validation_sample.py — Sample tagged Japanese survey text for manual validation.

Reads:
  output/official_fukui/official_surveys_tagged_combined.csv

Writes:
  output/official_fukui/japanese_friction_validation_sample.csv

Usage:
    python scripts/build_japanese_friction_validation_sample.py --per-code 15 --negative 30
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.official_fukui.ftas import load_japanese_codebook
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output" / "official_fukui"
COMBINED_CSV = OUTPUT_DIR / "official_surveys_tagged_combined.csv"
CODEBOOK_PATH = ROOT / "config" / "official_japanese_friction_codebook.yaml"
SAMPLE_CSV = OUTPUT_DIR / "japanese_friction_validation_sample.csv"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build manual validation sample for Japanese friction tags")
    parser.add_argument("--per-code", type=int, default=15, help="Positive rows to sample per friction code")
    parser.add_argument("--negative", type=int, default=30, help="Rows with no matched friction code to sample")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    if not COMBINED_CSV.exists():
        raise FileNotFoundError(f"Missing input: {COMBINED_CSV}. Run make official-all first.")

    codebook = load_japanese_codebook(CODEBOOK_PATH)
    codes = list(codebook.keys())
    df = pd.read_csv(COMBINED_CSV, low_memory=False)
    df = df[df["friction_source_text"].fillna("").astype(str).str.strip().ne("")].copy()

    sample_parts = []
    for code in codes:
        if code not in df.columns:
            continue
        hits = df[df[code].astype(bool)].copy()
        if hits.empty:
            continue
        sampled = hits.sample(n=min(args.per_code, len(hits)), random_state=args.seed)
        sampled["sample_reason"] = f"positive_{code}"
        sampled["target_code"] = code
        sample_parts.append(sampled)

    if "any_friction" in df.columns:
        negative = df[~df["any_friction"].astype(bool)].copy()
        if not negative.empty:
            sampled_negative = negative.sample(n=min(args.negative, len(negative)), random_state=args.seed)
            sampled_negative["sample_reason"] = "negative_no_code"
            sampled_negative["target_code"] = ""
            sample_parts.append(sampled_negative)

    if not sample_parts:
        raise ValueError("No validation rows could be sampled.")

    sample = pd.concat(sample_parts, ignore_index=True)
    keep = [
        "sample_reason", "target_code", "survey_prefecture", "survey_area_group",
        "response_area", "registered_facility", "friction_source_text", "friction_codes",
    ]
    for code in codes:
        if code in sample.columns:
            keep.append(code)
    sample = sample[[c for c in keep if c in sample.columns]].drop_duplicates()
    sample.insert(0, "validation_id", [f"jpval_{i:04d}" for i in range(1, len(sample) + 1)])
    sample["human_valid"] = ""
    sample["human_correct_code"] = ""
    sample["human_notes"] = ""
    sample.to_csv(SAMPLE_CSV, index=False)
    logger.info(f"Wrote validation sample: {SAMPLE_CSV} ({len(sample)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
