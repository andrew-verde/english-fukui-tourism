#!/usr/bin/env python3
"""
build_gold_set.py — Build a blind, stratified gold-standard labeling kit for the
Japanese friction tagger.

Unlike japanese_friction_validation_sample.csv (which exposes machine tags to the
reader), this kit separates:

  output/gold_set/gold_set_key.csv        — master file with machine tags + strata
                                            (do NOT give to coders)
  output/gold_set/gold_set_coder_A.csv    — blind coder sheet (shuffled, no tags)
  output/gold_set/gold_set_coder_B.csv    — identical blind sheet for second coder
  output/gold_set/CODING_GUIDE.md         — code definitions for coders

Strata:
  positive_<code>   : rows the keyword tagger assigned <code> (precision estimate)
  untagged_text     : rows with free text but no machine code (false-negative probe)

Usage:
    python scripts/build_gold_set.py --per-code 15 --untagged 120 --seed 42
"""

import argparse
import sys
from pathlib import Path

import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.official_fukui.ftas import load_japanese_codebook
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

ROOT = Path(__file__).resolve().parent.parent
COMBINED_CSV = ROOT / "output" / "official_fukui" / "official_surveys_tagged_combined.csv"
CODEBOOK_PATH = ROOT / "config" / "official_japanese_friction_codebook.yaml"
GOLD_DIR = ROOT / "output" / "gold_set"

MAX_TEXT_CHARS = 600  # very long responses slow coders without adding signal


def build_coding_guide(codebook_raw: dict, codes: list) -> str:
    lines = [
        "# Friction Coding Guide / フリクション・コーディングガイド",
        "",
        "Read each survey free-text response and mark **1** in every friction code",
        "column that applies (multiple codes allowed). If no friction is described,",
        "mark **1** in `no_friction`. Use `notes` for anything ambiguous.",
        "",
        "各自由記述を読み、当てはまるフリクションコードの列すべてに **1** を記入して",
        "ください（複数可）。フリクションが書かれていない場合は `no_friction` に **1**。",
        "迷った場合は `notes` にメモしてください。",
        "",
        "Judge what the respondent **experienced**, not the keywords used — the point",
        "of this exercise is to check the keyword system against human judgment, so do",
        "not try to guess what a machine would do.",
        "",
        "| Code | Label | 説明の目安 |",
        "|------|-------|-----------|",
    ]
    for code in codes:
        entry = codebook_raw["friction_codes"][code]
        examples = "、".join(entry.get("keywords", [])[:4])
        lines.append(f"| `{code}` | {entry.get('label', code)} | 例: {examples}… |")
    lines += [
        "",
        "Notes:",
        "- A complaint can carry several codes (e.g. 「駅から遠いしバスも少ない」 →",
        "  `transport_access` only; 「案内も分かりにくい」が加われば `wayfinding_signage` も).",
        "- Positive comments, suggestions with no experienced problem, and empty",
        "  pleasantries are `no_friction`.",
        "- Suggestions that imply an experienced gap (「飲食店が少ないので増やしてほしい」)",
        "  DO count as friction (`food_amenities_gap`).",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build blind gold-set labeling kit")
    parser.add_argument("--per-code", type=int, default=15, help="Positive rows per friction code")
    parser.add_argument("--untagged", type=int, default=120, help="Untagged free-text rows")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    if not COMBINED_CSV.exists():
        raise FileNotFoundError(f"Missing input: {COMBINED_CSV}. Run make official-all first.")

    codebook = load_japanese_codebook(CODEBOOK_PATH)
    codes = list(codebook.keys())
    with open(CODEBOOK_PATH, encoding="utf-8") as fh:
        codebook_raw = yaml.safe_load(fh)

    df = pd.read_csv(COMBINED_CSV, low_memory=False)
    df["friction_source_text"] = df["friction_source_text"].fillna("").astype(str).str.strip()
    df = df[df["friction_source_text"].ne("")].copy()
    df = df[df["friction_source_text"].str.len() <= MAX_TEXT_CHARS]
    df = df.drop_duplicates(subset=["friction_source_text"])

    parts = []
    for code in codes:
        hits = df[df[code].astype(bool)]
        if hits.empty:
            logger.warning(f"No rows for code {code}")
            continue
        sampled = hits.sample(n=min(args.per_code, len(hits)), random_state=args.seed)
        sampled = sampled.assign(stratum=f"positive_{code}")
        parts.append(sampled)

    untagged = df[~df["any_friction"].astype(bool)]
    parts.append(
        untagged.sample(n=min(args.untagged, len(untagged)), random_state=args.seed)
        .assign(stratum="untagged_text")
    )

    sample = pd.concat(parts, ignore_index=True).drop_duplicates(subset=["friction_source_text"])
    # Shuffle so coders cannot infer strata from ordering.
    sample = sample.sample(frac=1.0, random_state=args.seed + 1).reset_index(drop=True)
    sample.insert(0, "gold_id", [f"gold_{i:04d}" for i in range(1, len(sample) + 1)])

    GOLD_DIR.mkdir(parents=True, exist_ok=True)

    key_cols = ["gold_id", "stratum", "survey_prefecture", "response_area",
                "friction_source_text", "friction_codes"] + codes
    key = sample[[c for c in key_cols if c in sample.columns]]
    key.to_csv(GOLD_DIR / "gold_set_key.csv", index=False)

    coder = sample[["gold_id", "friction_source_text"]].rename(
        columns={"friction_source_text": "text"}
    )
    for code in codes:
        coder[code] = ""
    coder["no_friction"] = ""
    coder["notes"] = ""
    for name in ("A", "B"):
        coder.to_csv(GOLD_DIR / f"gold_set_coder_{name}.csv", index=False)

    (GOLD_DIR / "CODING_GUIDE.md").write_text(
        build_coding_guide(codebook_raw, codes), encoding="utf-8"
    )

    counts = sample["stratum"].value_counts()
    logger.info(f"Gold set: {len(sample)} rows -> {GOLD_DIR}")
    logger.info(f"Strata:\n{counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
