#!/usr/bin/env python3
"""
fetch_poi_metadata.py — Fetch Google Places Details (types) for each unique place_id.

Reads all three city checkpoint files to collect place_ids, then calls the
Google Places Details API (fields=name,types) once per unique place_id.

Writes checkpoint:
  output/checkpoints/poi_metadata.json

Checkpoint schema (place_id keyed):
  {
    "ChIJ...": {
      "name": "Eiheiji Temple",
      "types": ["hindu_temple", "place_of_worship", "tourist_attraction", ...],
      "poi_category": "temple_shrine"
    }
  }

Re-running is safe: place_ids already in checkpoint are skipped.
Use --force to re-fetch all place_ids.

Usage:
    python scripts/fetch_poi_metadata.py
    python scripts/fetch_poi_metadata.py --force
"""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv()

import requests
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

OUTPUT_DIR     = Path(__file__).resolve().parent.parent / "output"
CHECKPOINT_DIR = OUTPUT_DIR / "checkpoints"
METADATA_FILE  = CHECKPOINT_DIR / "poi_metadata.json"

CITY_CHECKPOINT_FILES = [
    CHECKPOINT_DIR / "google_fukui.json",
    CHECKPOINT_DIR / "google_kanazawa.json",
    CHECKPOINT_DIR / "google_toyama.json",
]

# Priority: first match wins. Fallback is "other".
# poi_name containing "castle" or ending in "-jo" → override to "castle_historic".
TYPES_PRIORITY = [
    (["museum", "art_gallery"],                                        "museum_cultural"),
    (["buddhist_temple", "hindu_temple", "place_of_worship",
      "church", "shrine", "shinto_shrine"],                            "temple_shrine"),
    (["restaurant", "food", "cafe", "bar", "bakery",
      "meal_takeaway", "seafood_restaurant"],                          "food_dining"),
    (["natural_feature", "park", "campground", "beach",
      "scenic_spot", "garden", "botanical_garden",
      "observation_deck", "hiking_area", "national_park"],             "nature_scenic"),
    (["spa", "health", "onsen"],                                       "onsen_wellness"),
    (["store", "shopping_mall", "market", "fish_market"],              "market_shopping"),
    (["historical_landmark", "historical_place", "cultural_landmark",
      "heritage_building"],                                            "castle_historic"),
]

CASTLE_NAMES = {"castle", "jo", "jō"}


def _map_types_to_category(types: list[str], poi_name: str) -> str:
    """Map a Google Places types list to a poi_category string."""
    name_lower = poi_name.lower()
    if any(token in name_lower for token in CASTLE_NAMES):
        return "castle_historic"

    types_set = {t.lower() for t in types}
    for type_group, category in TYPES_PRIORITY:
        if any(t in types_set for t in type_group):
            return category
    return "other"


def _load(path: Path, default):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return default


def _save(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def _collect_place_ids() -> dict[str, str]:
    """
    Walk all city checkpoint files and return {place_id: poi_name}.
    Only place_ids that appear in the review data are collected.
    """
    place_ids = {}
    for fpath in CITY_CHECKPOINT_FILES:
        if not fpath.exists():
            logger.warning(f"Checkpoint not found: {fpath} — skipping")
            continue
        with open(fpath) as f:
            data = json.load(f)
        for poi_name, poi_data in data.items():
            reviews = poi_data.get("reviews", []) if isinstance(poi_data, dict) else []
            for review in reviews:
                pid = review.get("place_id")
                if pid and pid not in place_ids:
                    place_ids[pid] = poi_name
    return place_ids


def _fetch_place_details(place_id: str, api_key: str) -> dict | None:
    """Call Google Places (New) API for place types. Returns result dict or None on error."""
    url = f"https://places.googleapis.com/v1/places/{place_id}"
    headers = {
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "types,displayName",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            logger.warning(f"  API error for {place_id}: {data['error'].get('message')}")
            return None
        return data
    except Exception as e:
        logger.error(f"  Request error for {place_id}: {e}")
        return None


def main(force: bool = False):
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.error("GOOGLE_API_KEY not set in environment — cannot fetch metadata")
        sys.exit(1)

    logger.info("=" * 55)
    logger.info("Fetch POI metadata (Google Places Details)")
    logger.info("=" * 55)

    place_ids = _collect_place_ids()
    logger.info(f"Found {len(place_ids)} unique place_ids across all checkpoints")

    saved = _load(METADATA_FILE, {})
    if force:
        saved = {}
        logger.info("--force: clearing existing metadata cache")

    skipped = 0
    fetched = 0
    failed  = 0

    for place_id, poi_name in place_ids.items():
        if not force and place_id in saved:
            skipped += 1
            continue

        logger.info(f"Fetching: {poi_name} ({place_id})")
        result = _fetch_place_details(place_id, api_key)

        if result is None:
            failed += 1
            saved[place_id] = {
                "name": poi_name,
                "types": [],
                "poi_category": "other",
                "fetch_failed": True,
            }
        else:
            types = result.get("types", [])
            name  = result.get("displayName", {}).get("text", poi_name)
            category = _map_types_to_category(types, poi_name)
            saved[place_id] = {
                "name": name,
                "types": types,
                "poi_category": category,
            }
            logger.info(f"  → {category} ({', '.join(types[:3])}{'...' if len(types) > 3 else ''})")
            fetched += 1

        # Write after each fetch (crash-safe)
        _save(METADATA_FILE, saved)

    logger.info("")
    logger.info("Metadata fetch complete")
    logger.info(f"  Fetched:  {fetched}")
    logger.info(f"  Skipped:  {skipped} (already cached)")
    logger.info(f"  Failed:   {failed}")
    logger.info(f"  Total:    {len(saved)} place_ids in cache")
    logger.info("")
    logger.info("Next step: make build-dataset")
    logger.info("=" * 55)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fetch Google Places Details (types) for all POI place_ids"
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Re-fetch all place_ids, ignoring existing cache",
    )
    args = parser.parse_args()
    main(force=args.force)
