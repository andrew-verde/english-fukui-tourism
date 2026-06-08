#!/usr/bin/env python3
"""
fetch_google_maps_reviews.py — Fetch deeper Google Maps review checkpoints.

This is the non-Places collection path for the thesis pipeline. It uses
Outscraper's Google Maps Reviews endpoint to collect more than the Google
Places Details review slice, then writes the same checkpoint files consumed by
scripts/build_analysis_dataset.py:

  output/checkpoints/google_fukui.json
  output/checkpoints/google_kanazawa.json
  output/checkpoints/google_toyama.json

Usage:
    python scripts/fetch_google_maps_reviews.py --only fukui --reviews-limit 100
    python scripts/fetch_google_maps_reviews.py --all --reviews-limit 100
    python scripts/fetch_google_maps_reviews.py --all --force --replace
"""

import argparse
import copy
import json
import os
import sys
from pathlib import Path
from typing import Dict, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv()

from scripts.fetch_comparison_city_data import KANAZAWA_POIS, TOYAMA_POIS
from scripts.pull import FUKUI_POIS
from src.scrapers.outscraper_reviews import (
    OutscraperGoogleReviewsClient,
    cutoff_date_to_timestamp,
    dedupe_reviews,
)
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
CHECKPOINT_DIR = OUTPUT_DIR / "checkpoints"
MANIFEST_FILE = CHECKPOINT_DIR / "google_maps_review_collection_manifest.json"

CITY_CONFIGS = {
    "fukui": {
        "display": "Fukui",
        "pois": FUKUI_POIS,
        "checkpoint": CHECKPOINT_DIR / "google_fukui.json",
    },
    "kanazawa": {
        "display": "Kanazawa",
        "pois": KANAZAWA_POIS,
        "checkpoint": CHECKPOINT_DIR / "google_kanazawa.json",
    },
    "toyama": {
        "display": "Toyama",
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
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


def _checkpoint_reviews(poi_entry) -> list:
    if isinstance(poi_entry, dict):
        return poi_entry.get("reviews", [])
    if isinstance(poi_entry, list):
        return poi_entry
    return []


def _first_place_id(poi_entry) -> str:
    if not isinstance(poi_entry, dict):
        return ""
    if poi_entry.get("place_id"):
        return poi_entry["place_id"]
    for review in poi_entry.get("reviews", []):
        if review.get("place_id"):
            return review["place_id"]
    return ""


def _query_for_poi(poi_name: str, search_query: str, existing_entry: dict, query_mode: str) -> tuple[str, str]:
    place_id = _first_place_id(existing_entry)
    if query_mode == "place-id" and not place_id:
        raise ValueError(f"No place_id available for {poi_name}; use --query-mode search or place-id-or-search")
    if query_mode in {"place-id", "place-id-or-search"} and place_id:
        return place_id, "place_id"
    return search_query, "search"


def _merge_poi_entry(existing: dict, incoming: dict, replace: bool) -> dict:
    if replace or not existing:
        return incoming

    existing_reviews = existing.get("reviews", []) if isinstance(existing, dict) else []
    incoming_reviews = incoming.get("reviews", [])
    merged = dict(existing)
    merged.update({k: v for k, v in incoming.items() if k != "reviews"})
    merged["reviews"] = dedupe_reviews([*incoming_reviews, *existing_reviews])
    merged["english_reviews_count"] = len(merged["reviews"])
    return merged


def fetch_city(
    city_key: str,
    client: Optional[OutscraperGoogleReviewsClient],
    reviews_limit: int,
    query_mode: str = "place-id-or-search",
    force: bool = False,
    replace: bool = False,
    dry_run: bool = False,
) -> dict:
    config = CITY_CONFIGS[city_key]
    pois = config["pois"]
    checkpoint_path = config["checkpoint"]
    saved = _load(checkpoint_path, {})
    cutoff_timestamp = cutoff_date_to_timestamp(os.getenv("REVIEW_DATE_CUTOFF", "2024-06-01"))
    query_cache = {}
    planned_queries = set()
    city_stats = {
        "city": config["display"],
        "pois_total": len(pois),
        "pois_fetched": 0,
        "pois_skipped": 0,
        "pois_failed": 0,
        "reviews_total": 0,
        "reviews_limit": reviews_limit,
        "query_mode": query_mode,
        "place_id_queries": 0,
        "search_queries": 0,
        "duplicate_queries_reused": 0,
        "duplicate_queries_planned": 0,
    }

    for poi_name, query in pois.items():
        existing_entry = saved.get(poi_name, {})
        try:
            outscraper_query, query_source = _query_for_poi(poi_name, query, existing_entry, query_mode)
        except Exception as exc:
            city_stats["pois_failed"] += 1
            logger.error(f"[{city_key.upper()} ERROR] {poi_name}: {exc}")
            continue

        if query_source == "place_id":
            city_stats["place_id_queries"] += 1
        else:
            city_stats["search_queries"] += 1
        if outscraper_query in planned_queries:
            city_stats["duplicate_queries_planned"] += 1
        planned_queries.add(outscraper_query)

        if dry_run:
            city_stats["pois_skipped"] += 1
            logger.info(f"[{city_key.upper()} DRY RUN] {poi_name} — {query_source}: {outscraper_query}")
            continue

        if not force and poi_name in saved:
            cached = saved[poi_name]
            cached_reviews = _checkpoint_reviews(cached)
            if len(cached_reviews) >= reviews_limit:
                city_stats["pois_skipped"] += 1
                logger.info(f"[{city_key.upper()} SKIP] {poi_name} — {len(cached_reviews)} reviews cached")
                continue

        try:
            if outscraper_query in query_cache:
                incoming = copy.deepcopy(query_cache[outscraper_query])
                city_stats["duplicate_queries_reused"] += 1
                logger.info(f"[{city_key.upper()} REUSE] {poi_name} — {query_source}: {outscraper_query}")
            else:
                if client is None:
                    raise RuntimeError("Outscraper client is not initialized")
                incoming = client.fetch_place_reviews(
                    query=outscraper_query,
                    reviews_limit=reviews_limit,
                    language="en",
                    region="JP",
                    cutoff_timestamp=cutoff_timestamp,
                )
                query_cache[outscraper_query] = copy.deepcopy(incoming)
            incoming["poi_name"] = poi_name
            incoming["configured_search_query"] = query
            incoming["query_source"] = query_source
        except Exception as exc:
            city_stats["pois_failed"] += 1
            logger.error(f"[{city_key.upper()} ERROR] {poi_name}: {exc}")
            if poi_name not in saved:
                saved[poi_name] = {
                    "reviews": [],
                    "source_platform": "google_maps_outscraper",
                    "source_query": query,
                    "fetch_error": str(exc),
                }
                _save(checkpoint_path, saved)
            continue

        saved[poi_name] = _merge_poi_entry(saved.get(poi_name, {}), incoming, replace=replace)
        _save(checkpoint_path, saved)
        city_stats["pois_fetched"] += 1
        logger.info(f"[{city_key.upper()}] {poi_name} — {len(saved[poi_name].get('reviews', []))} reviews")

    total = sum(
        len(v.get("reviews", [])) if isinstance(v, dict) else len(v)
        for v in saved.values()
    )
    city_stats["reviews_total"] = total
    logger.info(f"[{city_key.upper()}] Done — {total} reviews across {len(saved)} POIs")
    return city_stats


def main(
    only: Optional[str] = None,
    all_cities: bool = False,
    reviews_limit: int = 100,
    query_mode: str = "place-id-or-search",
    force: bool = False,
    replace: bool = False,
    dry_run: bool = False,
    allow_partial: bool = False,
):
    logger.info("=" * 55)
    logger.info("Fetch Google Maps reviews via Outscraper")
    logger.info("=" * 55)

    if not only and not all_cities:
        only = "fukui"

    city_keys = list(CITY_CONFIGS.keys()) if all_cities else [only]
    try:
        client = None if dry_run else OutscraperGoogleReviewsClient()
    except ValueError as exc:
        logger.error(str(exc))
        logger.error("Add OUTSCRAPER_API_KEY to .env, or run with --dry-run to inspect the query plan.")
        sys.exit(1)
    city_stats: Dict[str, dict] = {}

    for city_key in city_keys:
        city_stats[city_key] = fetch_city(
            city_key,
            client=client,
            reviews_limit=reviews_limit,
            query_mode=query_mode,
            force=force,
            replace=replace,
            dry_run=dry_run,
        )

    manifest = {
        "source_platform": "google_maps_outscraper",
        "review_date_cutoff": os.getenv("REVIEW_DATE_CUTOFF", "2024-06-01"),
        "reviews_limit": reviews_limit,
        "query_mode": query_mode,
        "dry_run": dry_run,
        "cities": city_stats,
    }
    if not dry_run:
        _save(MANIFEST_FILE, manifest)

    logger.info("")
    logger.info("Fetch complete")
    for city_key, stats in city_stats.items():
        logger.info(f"  {CITY_CONFIGS[city_key]['display']:<12} {stats['reviews_total']} reviews")
    logger.info("")
    if dry_run:
        logger.info("Dry run only; no checkpoint files were changed")
    else:
        logger.info(f"Manifest written: {MANIFEST_FILE}")
        logger.info("Next step: make build-dataset")
    logger.info("=" * 55)

    total_failures = sum(stats["pois_failed"] for stats in city_stats.values())
    if total_failures and not dry_run and not allow_partial:
        logger.error(f"Fetch failed for {total_failures} POIs; rerun with --allow-partial only if this is intentional.")
        sys.exit(1)
    return city_stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch deeper Google Maps reviews without Google Places")
    city_group = parser.add_mutually_exclusive_group()
    city_group.add_argument("--only", choices=list(CITY_CONFIGS.keys()), default=None, help="Fetch one city")
    city_group.add_argument("--all", action="store_true", help="Fetch Fukui, Kanazawa, and Toyama")
    parser.add_argument(
        "--reviews-limit",
        type=int,
        default=int(os.getenv("GOOGLE_MAPS_DEEP_REVIEW_LIMIT", "100")),
        help="Maximum reviews to request per POI",
    )
    parser.add_argument(
        "--query-mode",
        choices=["place-id-or-search", "place-id", "search"],
        default=os.getenv("GOOGLE_MAPS_DEEP_QUERY_MODE", "place-id-or-search"),
        help="Use existing checkpoint place_ids when available, plain search queries, or require place_ids",
    )
    parser.add_argument("--force", action="store_true", help="Re-fetch POIs even when checkpoint entries exist")
    parser.add_argument("--dry-run", action="store_true", help="Show query plan without requiring an API key or changing files")
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Exit successfully even if some POIs fail to fetch",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace existing POI checkpoint entries instead of merging with existing reviews",
    )
    args = parser.parse_args()
    main(
        only=args.only,
        all_cities=args.all,
        reviews_limit=args.reviews_limit,
        query_mode=args.query_mode,
        force=args.force,
        replace=args.replace,
        dry_run=args.dry_run,
        allow_partial=args.allow_partial,
    )
