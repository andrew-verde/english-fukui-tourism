#!/usr/bin/env python3
"""
pull.py — Fetch raw Fukui review data from Google Places.

Writes checkpoint under output/checkpoints/google_fukui.json.
Re-running is safe: POIs already in checkpoint are skipped.
Delete the checkpoint file to force a fresh pull.

Checkpoint schema (per POI):
  {
    "POI Name": {
      "reviews": [...],
      "total_reviews_all_langs": N,
      "english_reviews_count": N
    }
  }

Does NOT call OpenAI. Run analysis pipeline after this.

Usage:
    python scripts/pull.py
    python scripts/pull.py --force   # re-fetch all POIs
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv()

from src.scrapers.google_maps_scraper import GoogleMapsScraper
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

OUTPUT_DIR     = Path(__file__).resolve().parent.parent / "output"
CHECKPOINT_DIR = OUTPUT_DIR / "checkpoints"
GOOGLE_FILE    = CHECKPOINT_DIR / "google_fukui.json"

FUKUI_POIS = {
    # Original 10
    "Eiheiji Temple":                "Eiheiji Temple Fukui Japan",
    "Fukui Dinosaur Museum":         "Fukui Prefectural Dinosaur Museum Japan",
    "Tojinbo Cliffs":                "Tojinbo Japan",
    "Fukui Castle":                  "Fukui Castle Ruins Japan",
    "Katsuyama Castle":              "Katsuyama Castle Fukui Japan",
    "Maruoka Castle":                "Maruoka Castle Fukui Japan",
    "Echizen Daibutsu":              "Echizen Daibutsu Fukui Japan",
    "Kehi Grand Shrine":             "Kehi Jingu Tsuruga Fukui Japan",
    "Fukui Prefectural Museum":      "Fukui Prefectural Museum of Cultural History Japan",
    "Awara Onsen":                   "Awara Onsen Fukui Japan",
    # Extended — Fukui city
    "Ichijodani Asakura Ruins":      "Ichijodani Asakura Clan Ruins Fukui Japan",
    "Yokokan Garden":                "Yokokan Garden Fukui Japan",
    # Extended — Katsuyama / inland
    "Heisenji Hakusan Shrine":       "Heisenji Hakusan Shrine Katsuyama Fukui Japan",
    "Echizen Ono Castle":            "Echizen Ono Castle Fukui Japan",
    # Extended — Tsuruga / Wakasa
    "Tsuruga Red Brick Warehouse":   "Tsuruga Red Brick Warehouse Fukui Japan",
    "Wakasa Obama Furusato":         "Wakasa Obama Food Cultural Museum Fukui Japan",
    "Sotomo Caves":                  "Sotomo Caves Obama Fukui Japan",
    # Extended — coast / nature
    "Mikuniminato Port":             "Mikuniminato Fishing Port Fukui Japan",
    "Oshima Island Fukui":           "Oshima Island Sakai Fukui Japan",
    # Extended — craft / culture
    "Echizen Pottery Village":       "Echizen Pottery Village Fukui Japan",
    "Echizen Washi Village":         "Echizen Washi Village Paper Museum Fukui Japan",
    # Extended — Sabae / other
    "Nishiyama Park Sabae":          "Nishiyama Park Sabae Fukui Japan",
    "Fukui City Museum of History":  "Fukui City Museum of History Japan",
    # Reaching 30 POIs
    "Asuwa River Promenade":         "Asuwa River Cherry Blossom Promenade Fukui Japan",
    "Fukui Prefectural Art Museum":  "Fukui Prefectural Art Museum Japan",
    "Eiheiji Approach Town":         "Eiheiji Approach Temple Town Fukui Japan",
    "Echizen Crab Museum":           "Echizen Crab Kanpan Museum Fukui Japan",
    "Takefu Knife Village":          "Takefu Knife Village Echizen Fukui Japan",
    "Obama Jinguji Temple":          "Jinguji Temple Obama Fukui Japan",
    "Kitamaebune Sakai Port":        "Sakai Port Kitamaebune Museum Fukui Japan",
}

MAX_REVIEWS_PER_POI = 5


def _load(path: Path, default):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return default


def _save(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def pull_google(force: bool = False) -> int:
    """Fetch English Google Places reviews for each Fukui POI. Returns total English reviews collected."""
    saved = _load(GOOGLE_FILE, {})

    if not force and all(poi in saved for poi in FUKUI_POIS):
        total = sum(len(v.get("reviews", [])) if isinstance(v, dict) else len(v) for v in saved.values())
        logger.info(f"[GOOGLE] All {len(FUKUI_POIS)} POIs cached — {total} reviews (skipping)")
        return total

    scraper = GoogleMapsScraper()

    for poi_name, query in FUKUI_POIS.items():
        if not force and poi_name in saved:
            cached = saved[poi_name]
            cached_count = len(cached.get("reviews", []) if isinstance(cached, dict) else cached)
            logger.info(f"[GOOGLE SKIP] {poi_name} — {cached_count} reviews cached")
            continue

        logger.info(f"[GOOGLE] {poi_name}")
        place_id = scraper.find_place_id(query)

        if not place_id:
            logger.warning(f"  No Place ID for '{poi_name}' — skipping")
            saved[poi_name] = {"reviews": []}
            _save(GOOGLE_FILE, saved)
            continue

        df = scraper.get_place_reviews(place_id, poi_name)
        reviews = df.head(MAX_REVIEWS_PER_POI).to_dict("records") if not df.empty else []
        saved[poi_name] = {"reviews": reviews}
        _save(GOOGLE_FILE, saved)
        logger.info(f"  → {len(reviews)} reviews")

    total = sum(len(v.get("reviews", [])) if isinstance(v, dict) else len(v) for v in saved.values())
    logger.info(f"[GOOGLE] Done — {total} English reviews across {len(saved)} POIs")
    return total


def main(force: bool = False):
    logger.info("=" * 55)
    logger.info("Pull — Fetch Fukui Google Places data")
    logger.info("=" * 55)

    n = pull_google(force=force)

    logger.info("")
    logger.info("Pull complete")
    logger.info(f"  Google Places     {n} reviews")
    logger.info("")
    logger.info("Next step: make fetch-metadata && make build-dataset")
    logger.info("=" * 55)

    return {"Google Places": n}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch Fukui Google Places review data")
    parser.add_argument(
        "--force", action="store_true",
        help="Ignore existing checkpoint and re-fetch all POIs",
    )
    args = parser.parse_args()
    main(force=args.force)
