#!/usr/bin/env python3
"""
fetch_comparison_city_data.py — Fetch raw Google Places reviews for Kanazawa and Toyama.

Writes one checkpoint file per city:
  output/checkpoints/google_kanazawa.json
  output/checkpoints/google_toyama.json

Re-running is safe: a city is skipped if its checkpoint already exists (all POIs present).
Delete a checkpoint file to force a fresh pull for that city.
Use --force to re-fetch all POIs regardless of checkpoint state.

Checkpoint schema (per POI keyed dict):
  {
    "POI Name": {
      "reviews": [...],
      "total_reviews_all_langs": N,
      "english_reviews_count": N
    }
  }

Usage:
    python scripts/fetch_comparison_city_data.py
    python scripts/fetch_comparison_city_data.py --only kanazawa
    python scripts/fetch_comparison_city_data.py --only toyama
    python scripts/fetch_comparison_city_data.py --force
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

MAX_REVIEWS_PER_POI = 5

KANAZAWA_POIS = {
    "Kenrokuen Garden":                         "Kenrokuen Garden Kanazawa Japan",
    "Higashi Chaya District":                   "Higashi Chaya District Kanazawa Japan",
    "Kanazawa Castle Park":                     "Kanazawa Castle Park Japan",
    "21st Century Museum of Contemporary Art":  "21st Century Museum of Contemporary Art Kanazawa Japan",
    "Nagamachi Samurai District":               "Nagamachi Samurai District Kanazawa Japan",
    "Myoryuji Ninja Temple":                    "Myoryuji Temple Kanazawa Japan",
    "Omicho Market":                            "Omicho Market Kanazawa Japan",
    "Oyama Shrine":                             "Oyama Shrine Kanazawa Japan",
    "Nishi Chaya District":                     "Nishi Chaya District Kanazawa Japan",
    "Kanazawa Noh Museum":                      "Kanazawa Noh Museum Japan",
    "Kazuemachi Chaya District":                "Kazuemachi Chaya District Kanazawa Japan",
    "D.T. Suzuki Museum":                       "D.T. Suzuki Museum Kanazawa Japan",
    "Kutaniyaki Art Museum":                    "Kutaniyaki Art Museum Kanazawa Japan",
    "Ishikawa Prefectural Museum of Art":       "Ishikawa Prefectural Museum of Art Kanazawa Japan",
    "Honda Museum":                             "Honda Museum Kanazawa Japan",
    "Ishikawa Prefectural History Museum":      "Ishikawa Prefectural History Museum Kanazawa Japan",
    "Nomura Samurai House":                     "Nomura Clan Samurai House Kanazawa Japan",
    "Gyokusenin Maru Garden":                   "Gyokusenin Maru Garden Kanazawa Japan",
    "Kanazawa Yasue Gold Leaf Museum":          "Kanazawa Yasue Gold Leaf Museum Japan",
    "Shiinoki Cultural Complex":                "Shiinoki Cultural Complex Kanazawa Japan",
    "Kanazawa Phonograph Museum":               "Kanazawa Phonograph Museum Japan",
    "Seison-kaku Villa":                        "Seison-kaku Villa Kanazawa Japan",
    "Kanazawa Umimirai Library":                "Kanazawa Umimirai Library Japan",
    "Kanazawa Station Tsuzumi Gate":            "Kanazawa Station Tsuzumi Gate Japan",
    "Asanogawa Riverside":                      "Asano River Kanazawa Japan",
    "Ishikawa Prefectural Noh Theater":         "Ishikawa Prefectural Noh Theater Japan",
    "Saigawa Riverbank":                        "Saigawa River Walk Kanazawa Japan",
    "Higashi Chaya Seifukan":                   "Higashi Chaya Seifukan Kanazawa Japan",
    "Kanazawa Port":                            "Kanazawa Port Cruise Terminal Japan",
    "Kenroku-en Seison-kaku":                  "Seison-kaku Kanazawa Japan",
}

TOYAMA_POIS = {
    "Toyama Castle":                            "Toyama Castle Japan",
    "Toyama Glass Art Museum":                  "Toyama Glass Art Museum Japan",
    "TAD Toyama Art Museum":                    "Toyama Prefectural Museum of Art and Design Japan",
    "Gokayama Ainokura":                        "Ainokura Village Gokayama Toyama Japan",
    "Tateyama Kurobe Alpine Route":             "Tateyama Kurobe Alpine Route Japan",
    "Kurobe Gorge Railway":                     "Kurobe Gorge Railway Toyama Japan",
    "Zuiryuji Temple":                          "Zuiryuji Temple Takaoka Toyama Japan",
    "Takaoka Daibutsu":                         "Takaoka Daibutsu Great Buddha Toyama Japan",
    "Takaoka Sankyokai":                        "Sankyokai Merchant Town Takaoka Toyama Japan",
    "Kurobe Dam":                               "Kurobe Dam Toyama Japan",
    "Unazuki Onsen":                            "Unazuki Onsen Toyama Japan",
    "Himi Fishing Port":                        "Himi Fishing Port Toyama Japan",
    "Tonami Tulip Park":                        "Tonami Tulip Fair Park Toyama Japan",
    "Tateyama Museum":                          "Tateyama Museum Toyama Japan",
    "Fugan Canal Kansui Park":                  "Fugan Canal Kansui Park Toyama Japan",
    "Toyama Kirari":                            "Toyama Kirari Building Toyama Japan",
    "Hokuriku Minka Museum":                    "Hokuriku Minka Open Air Museum Toyama Japan",
    "Takaoka Craft Museum":                     "Takaoka Traditional Craft Museum Japan",
    "Nanto City Museum":                        "Nanto City History Museum Toyama Japan",
    "Johana Hikiyama Museum":                   "Johana Town Hikiyama Museum Toyama Japan",
    "Yatsuo Old Town":                          "Yatsuo Old Town Toyama Japan",
    "Toyama Science Museum":                    "Toyama Science Museum Japan",
    "Imizu Shrine":                             "Imizu Shrine Toyama Japan",
    "Toyama Prefectural Botanical Garden":      "Toyama Botanical Garden Japan",
    "Kitokito Market":                          "Toyama Kitokito Market Japan",
    "Masumida Shrine Takaoka":                  "Masumida Shrine Takaoka Toyama Japan",
    "Toyama Port":                              "Fushiki Port Toyama Japan",
    "Kureha Hills":                             "Kureha Hills Toyama Japan",
    "Asahi Town Folk Museum":                   "Asahi Town Folk Museum Toyama Japan",
    "Takaoka Okumura Memorial Museum":          "Okumura Memorial Museum Takaoka Japan",
}

CITY_CONFIGS = {
    "kanazawa": {
        "pois": KANAZAWA_POIS,
        "checkpoint": CHECKPOINT_DIR / "google_kanazawa.json",
    },
    "toyama": {
        "pois": TOYAMA_POIS,
        "checkpoint": CHECKPOINT_DIR / "google_toyama.json",
    },
}


def _load(path: Path, default):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return default


def _save(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def fetch_city(city_key: str, force: bool = False) -> int:
    """
    Fetch reviews for all POIs in a city. Returns total English reviews collected.
    Writes checkpoint after each POI (crash-safe).
    """
    config = CITY_CONFIGS[city_key]
    pois = config["pois"]
    checkpoint_path = config["checkpoint"]

    saved = _load(checkpoint_path, {})

    if not force and all(poi in saved for poi in pois):
        total = sum(len(v.get("reviews", [])) if isinstance(v, dict) else len(v) for v in saved.values())
        logger.info(f"[{city_key.upper()}] All {len(pois)} POIs cached — {total} reviews (skipping)")
        return total

    scraper = GoogleMapsScraper()

    for poi_name, query in pois.items():
        if not force and poi_name in saved:
            cached = saved[poi_name]
            n = len(cached.get("reviews", []) if isinstance(cached, dict) else cached)
            logger.info(f"[{city_key.upper()} SKIP] {poi_name} — {n} reviews cached")
            continue

        logger.info(f"[{city_key.upper()}] {poi_name}")
        place_id = scraper.find_place_id(query)

        if not place_id:
            logger.warning(f"  No Place ID for '{poi_name}' — skipping")
            saved[poi_name] = {"reviews": []}
            _save(checkpoint_path, saved)
            continue

        df = scraper.get_place_reviews(place_id, poi_name)
        reviews = df.head(MAX_REVIEWS_PER_POI).to_dict("records") if not df.empty else []

        # Enrich with total_reviews_all_langs if available from scraper
        poi_entry = {"reviews": reviews}
        if hasattr(scraper, "last_total_reviews"):
            poi_entry["total_reviews_all_langs"] = scraper.last_total_reviews
        poi_entry["english_reviews_count"] = len(reviews)

        saved[poi_name] = poi_entry
        _save(checkpoint_path, saved)
        logger.info(f"  → {len(reviews)} reviews")

    total = sum(
        len(v.get("reviews", [])) if isinstance(v, dict) else len(v)
        for v in saved.values()
    )
    logger.info(f"[{city_key.upper()}] Done — {total} English reviews across {len(saved)} POIs")
    return total


def main(only: str = None, force: bool = False):
    logger.info("=" * 55)
    logger.info("Fetch comparison city data (Kanazawa + Toyama)")
    logger.info("=" * 55)

    cities = [only] if only else list(CITY_CONFIGS.keys())
    counts = {}
    for city_key in cities:
        counts[city_key] = fetch_city(city_key, force=force)

    logger.info("")
    logger.info("Fetch complete")
    for city, n in counts.items():
        logger.info(f"  {city:<15} {n} reviews")
    logger.info("")
    logger.info("Next step: make fetch-metadata")
    logger.info("=" * 55)
    return counts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fetch raw Google Places reviews for Kanazawa and Toyama"
    )
    parser.add_argument(
        "--only", choices=["kanazawa", "toyama"], default=None,
        help="Fetch only this city",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Ignore existing checkpoints and re-fetch all POIs",
    )
    args = parser.parse_args()
    main(only=args.only, force=args.force)
