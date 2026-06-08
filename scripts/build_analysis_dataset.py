#!/usr/bin/env python3
"""
build_analysis_dataset.py — Build the unified review-level analysis dataset.

Reads all three city JSON checkpoints and poi_metadata.json, then:
  - Applies English language filter
  - Applies REVIEW_DATE_CUTOFF env var (default 2024-06-01)
  - Joins poi_category from poi_metadata.json
  - Runs fresh VADER sentiment
  - Assigns primary_theme via keyword taxonomy

Output:
  output/friction_analysis/reviews_unified.csv

Schema:
  city, poi_id, poi_name, poi_category, place_id,
  review_id, review_date, review_rating, review_text,
  review_language, review_author, collection_date,
  source_platform, review_order_within_poi,
  vader_compound, sentiment_norm, emotional_intensity_score,
  primary_theme

Usage:
    python scripts/build_analysis_dataset.py
"""

import hashlib
import json
import os
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv()

import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from src.utils.filters import language_filter
from src.analysis.topic_modeling import assign_primary_theme_with_keyword
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

OUTPUT_DIR         = Path(__file__).resolve().parent.parent / "output"
CHECKPOINT_DIR     = OUTPUT_DIR / "checkpoints"
FRICTION_OUT_DIR   = OUTPUT_DIR / "friction_analysis"
OUTPUT_CSV         = FRICTION_OUT_DIR / "reviews_unified.csv"
METADATA_FILE      = CHECKPOINT_DIR / "poi_metadata.json"

CITY_CHECKPOINT_MAP = {
    "Fukui":    CHECKPOINT_DIR / "google_fukui.json",
    "Kanazawa": CHECKPOINT_DIR / "google_kanazawa.json",
    "Toyama":   CHECKPOINT_DIR / "google_toyama.json",
}

REVIEW_DATE_CUTOFF = os.getenv("REVIEW_DATE_CUTOFF", "2024-06-01")
DROP_UNPARSEABLE_TIMESTAMPS = os.getenv("DROP_UNPARSEABLE_TIMESTAMPS", "0").lower() in {"1", "true", "yes"}

# Name-based fallback when Google Places types are unavailable.
# Keyword substrings matched case-insensitively against poi_name.
_NAME_CATEGORY_RULES = [
    (["museum", "gallery", "art museum", "washi", "pottery", "craft museum",
      "phonograph", "noh museum", "gold leaf", "glass art", "science museum",
      "cultural complex", "folk museum", "minka", "memorial museum",
      "prefectural art", "city museum", "history museum", "prefectural museum"],
     "museum_cultural"),
    (["temple", "shrine", "jingu", "daibutsu", "eiheiji", "jinguji",
      "heisenji", "zuiryuji", "hakusan", "imizu", "masumida", "oyama shrine",
      "kehi", "buddhist"],
     "temple_shrine"),
    (["castle", "ruins", "asakura", "ichijodani", "kitamaebune", "warehouse",
      "red brick", "yokokan"],
     "castle_historic"),
    (["onsen", "spa", "thermal", "awara", "unazuki"],
     "onsen_wellness"),
    (["market", "omicho", "kitokito", "himi fishing", "mikuniminato",
      "knife village", "takefu"],
     "market_shopping"),
    (["cliff", "cave", "tojinbo", "sotomo", "gorge", "alpine route",
      "kurobe gorge", "kurobe dam", "park", "garden", "river", "promenade",
      "island", "port", "botanical", "tateyama", "gokayama", "ainokura",
      "kureha", "tulip", "nishiyama", "saigawa", "asanogawa", "asano river",
      "asuwa", "fugan canal", "sakai port", "oshima"],
     "nature_scenic"),
    (["food", "crab", "restaurant", "dining", "echizen crab"],
     "food_dining"),
]


def _infer_category_from_name(poi_name: str) -> str:
    """Fallback: infer poi_category from poi_name when API types are unavailable."""
    name_lower = poi_name.lower()
    for keywords, category in _NAME_CATEGORY_RULES:
        if any(kw in name_lower for kw in keywords):
            return category
    return "other"

SCHEMA_COLUMNS = [
    "city", "poi_id", "poi_name", "poi_category", "place_id",
    "review_id", "review_date", "review_rating", "review_text",
    "review_language", "review_author", "collection_date",
    "source_platform", "review_order_within_poi",
    "vader_compound", "sentiment_norm", "emotional_intensity_score",
    "primary_theme",
]

_vader = SentimentIntensityAnalyzer()


def _make_review_id(city: str, place_id: str, poi_name: str, order: int) -> str:
    raw = f"{city}_{place_id}_{poi_name}_{order}"
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


def _make_stable_review_id(city: str, place_id: str, poi_name: str, order: int, review: dict) -> str:
    source_key = review.get("source_review_id") or review.get("review_url")
    if source_key:
        raw = f"{city}_{place_id}_{source_key}"
        return hashlib.sha256(raw.encode()).hexdigest()[:12]
    return _make_review_id(city, place_id, poi_name, order)


def _load_json(path: Path) -> dict:
    if not path.exists():
        logger.warning(f"Checkpoint not found: {path}")
        return {}
    with open(path) as f:
        return json.load(f)


def _load_metadata(path: Path) -> dict:
    if not path.exists():
        logger.warning(f"poi_metadata.json not found — poi_category will default to 'other'")
        return {}
    with open(path) as f:
        return json.load(f)


def _vader_score(text: str) -> float:
    if not isinstance(text, str) or not text.strip():
        return 0.0
    return _vader.polarity_scores(text)["compound"]


def _parse_reviews_from_checkpoint(
    city: str,
    data: dict,
    metadata: dict,
    cutoff: str,
    stats: dict,
) -> list[dict]:
    """Parse raw checkpoint dict into list of review dicts with unified schema."""
    rows = []
    collection_date = str(date.today())

    for poi_name, poi_data in data.items():
        if isinstance(poi_data, dict):
            reviews = poi_data.get("reviews", [])
            checkpoint_source = poi_data.get("source_platform") or "google_places"
        elif isinstance(poi_data, list):
            reviews = poi_data
            checkpoint_source = "google_places"
        else:
            continue

        for order, review in enumerate(reviews):
            text = review.get("review_text", "") or ""
            language = review.get("language", "") or ""

            # Language filter — keep English only
            if language and language != "en":
                continue
            if not language_filter(text):
                continue

            place_id = review.get("place_id", "") or ""
            timestamp = review.get("timestamp", "") or ""

            # Date filter (auditable + optional strict mode)
            if cutoff:
                if not timestamp:
                    stats["missing_timestamp"] += 1
                else:
                    try:
                        ts = pd.Timestamp(timestamp, tz="UTC")
                        cutoff_ts = pd.Timestamp(cutoff, tz="UTC")
                        if ts < cutoff_ts:
                            stats["dropped_by_cutoff"] += 1
                            continue
                    except Exception:
                        stats["unparseable_timestamp"] += 1
                        if DROP_UNPARSEABLE_TIMESTAMPS:
                            stats["dropped_unparseable_timestamp"] += 1
                            continue

            # poi_category from metadata; fall back to name-based inference
            meta = metadata.get(place_id, {})
            poi_category = meta.get("poi_category", "other")
            if poi_category == "other" or not meta.get("types"):
                poi_category = _infer_category_from_name(poi_name)

            review_id = _make_stable_review_id(city, place_id if place_id else poi_name, poi_name, order, review)
            vader_compound = _vader_score(text)
            primary_theme, theme_keyword = assign_primary_theme_with_keyword(text)

            rows.append({
                "city":                   city,
                "poi_id":                 place_id or poi_name,
                "poi_name":               poi_name,
                "poi_category":           poi_category,
                "place_id":               place_id,
                "review_id":              review_id,
                "review_date":            timestamp,
                "review_rating":          review.get("rating"),
                "review_text":            text,
                "review_language":        language or "en",
                "review_author":          review.get("author_name", ""),
                "collection_date":        collection_date,
                "source_platform":        review.get("source_platform") or checkpoint_source,
                "review_order_within_poi": order,
                "vader_compound":         vader_compound,
                "sentiment_norm":         round((vader_compound + 1) / 2, 6),
                "emotional_intensity_score": round(abs(vader_compound), 6),
                "primary_theme":          primary_theme,
            })

            if primary_theme is None:
                stats["theme_none"] += 1
            else:
                stats["theme_counts"][primary_theme] = stats["theme_counts"].get(primary_theme, 0) + 1
                if theme_keyword:
                    k = (primary_theme, theme_keyword)
                    stats["theme_keyword_counts"][k] = stats["theme_keyword_counts"].get(k, 0) + 1

    return rows


def main():
    FRICTION_OUT_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 55)
    logger.info("Build unified analysis dataset")
    logger.info(f"  Date cutoff: {REVIEW_DATE_CUTOFF}")
    logger.info("=" * 55)

    metadata = _load_metadata(METADATA_FILE)
    logger.info(f"POI metadata loaded: {len(metadata)} place_ids")

    all_rows = []
    stats = {
        "missing_timestamp": 0,
        "unparseable_timestamp": 0,
        "dropped_by_cutoff": 0,
        "dropped_unparseable_timestamp": 0,
        "theme_none": 0,
        "theme_counts": {},
        "theme_keyword_counts": {},
    }
    for city, checkpoint_path in CITY_CHECKPOINT_MAP.items():
        logger.info(f"Processing {city}...")
        data = _load_json(checkpoint_path)
        if not data:
            logger.warning(f"  No data for {city} — skipping")
            continue
        rows = _parse_reviews_from_checkpoint(city, data, metadata, REVIEW_DATE_CUTOFF, stats)
        logger.info(f"  {city}: {len(rows)} English reviews retained")
        all_rows.extend(rows)

    if not all_rows:
        logger.error("No reviews collected — check that checkpoint files exist")
        sys.exit(1)

    df = pd.DataFrame(all_rows, columns=SCHEMA_COLUMNS)

    # Deduplicate on (city, review_text) — same review text pulled via multiple
    # POI entries for the same physical place (e.g. Higashi Chaya District vs
    # Higashi Chaya Seifukan) produces exact duplicate sentences that inflate
    # mention-level counts. Keep first occurrence (preserves poi_name of first POI).
    before_dedup = len(df)
    df = df.drop_duplicates(subset=["city", "review_text"], keep="first").reset_index(drop=True)
    dupes_removed = before_dedup - len(df)
    if dupes_removed:
        logger.info(f"  Removed {dupes_removed} duplicate reviews (same text, same city)")

    df.to_csv(OUTPUT_CSV, index=False)

    # ── Auditing summaries ──────────────────────────────────────────────────
    logger.info("")
    logger.info("Audit summary")
    logger.info(f"  Missing timestamps:     {stats['missing_timestamp']}")
    logger.info(f"  Unparseable timestamps: {stats['unparseable_timestamp']}")
    logger.info(f"  Dropped by cutoff:      {stats['dropped_by_cutoff']}")
    if DROP_UNPARSEABLE_TIMESTAMPS:
        logger.info(f"  Dropped unparseable (strict): {stats['dropped_unparseable_timestamp']}")
    logger.info(f"  primary_theme=None:     {stats['theme_none']} ({100*stats['theme_none']/len(df):.1f}%)")

    # % None by city
    by_city = df.groupby("city")["primary_theme"].apply(lambda s: (s.isna() | (s == "")).mean() * 100)
    for city, pct in by_city.items():
        logger.info(f"  {city:<12} primary_theme=None: {pct:.1f}%")

    # Top 20 matched keywords per theme (diagnostic)
    if stats["theme_keyword_counts"]:
        logger.info("  Top matched keywords per theme (up to 20 total):")
        top = sorted(stats["theme_keyword_counts"].items(), key=lambda kv: kv[1], reverse=True)[:20]
        for (theme, kw), n in top:
            logger.info(f"    {theme:<10} {kw:<20} {n}")

    logger.info("")
    logger.info(f"Output written: {OUTPUT_CSV}")
    logger.info(f"  Total reviews: {len(df)}")
    for city, grp in df.groupby("city"):
        logger.info(f"  {city:<12} {len(grp)} reviews")
    logger.info("")
    logger.info("Next step: make build-mentions")
    logger.info("=" * 55)


if __name__ == "__main__":
    main()
