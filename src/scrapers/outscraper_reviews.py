"""
Outscraper Google Maps Reviews client.

This collector is intentionally separate from the Google Places wrapper because
Google Places exposes only a small review slice per place. Outscraper returns
Google Maps review data from Maps queries/place IDs without using Places
Details' reviews field.
"""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

import requests

from ..utils.logger import setup_logger

logger = setup_logger(__name__)


def _anonymize(name: str) -> str:
    if not name:
        return ""
    return "Reviewer_" + hashlib.sha256(name.encode()).hexdigest()[:6].upper()


def _to_iso_timestamp(review: Dict[str, Any]) -> str:
    """Return a normalized UTC timestamp string when Outscraper provides one."""
    raw_ts = review.get("review_timestamp")
    if raw_ts not in (None, ""):
        try:
            return datetime.fromtimestamp(int(raw_ts), tz=timezone.utc).isoformat()
        except (TypeError, ValueError, OSError):
            pass

    raw_dt = review.get("review_datetime_utc") or ""
    if raw_dt:
        for fmt in ("%m/%d/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(raw_dt, fmt).replace(tzinfo=timezone.utc).isoformat()
            except ValueError:
                continue

    return ""


class OutscraperGoogleReviewsClient:
    """Fetch Google Maps reviews through Outscraper's Google Maps Reviews API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        self.api_key = api_key or os.getenv("OUTSCRAPER_API_KEY")
        if not self.api_key:
            raise ValueError("OUTSCRAPER_API_KEY environment variable not set")

        self.base_url = (base_url or os.getenv("OUTSCRAPER_BASE_URL") or "https://api.outscraper.cloud").rstrip("/")
        self.timeout = timeout or int(os.getenv("OUTSCRAPER_TIMEOUT_SECONDS", "180"))
        self.session = requests.Session()

    def fetch_place_reviews(
        self,
        query: str,
        reviews_limit: int,
        language: str = "en",
        region: str = "JP",
        sort: str = "newest",
        cutoff_timestamp: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Fetch and normalize one place result for a Maps query or place ID."""
        params: Dict[str, Any] = {
            "query": query,
            "reviewsLimit": reviews_limit,
            "limit": 1,
            "language": language,
            "region": region,
            "source": "google",
            "ignoreEmpty": "true",
            "async": "false",
        }
        if cutoff_timestamp:
            params["cutoff"] = cutoff_timestamp
        else:
            params["sort"] = sort

        logger.info(f"[OUTSCRAPER] Fetching {reviews_limit} reviews for {query}")
        response = self.session.get(
            f"{self.base_url}/google-maps-reviews",
            headers={"X-API-KEY": self.api_key},
            params=params,
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()

        if payload.get("error"):
            raise RuntimeError(payload.get("errorMessage") or "Outscraper request failed")
        if payload.get("status") not in {None, "Success"}:
            raise RuntimeError(f"Outscraper returned status {payload.get('status')}: {payload}")

        places = payload.get("data") or []
        if not places:
            return {
                "reviews": [],
                "source_platform": "google_maps_outscraper",
                "source_query": query,
                "english_reviews_count": 0,
            }

        return normalize_outscraper_place(places[0], source_query=query)


def cutoff_date_to_timestamp(cutoff: str) -> Optional[int]:
    """Convert YYYY-MM-DD cutoff to a UTC epoch timestamp for Outscraper."""
    if not cutoff:
        return None
    try:
        dt = datetime.strptime(cutoff, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    return int(dt.timestamp())


def normalize_outscraper_place(place: Dict[str, Any], source_query: str = "") -> Dict[str, Any]:
    """Convert one Outscraper place payload into this repo's checkpoint schema."""
    place_id = place.get("place_id") or ""
    google_id = place.get("google_id") or ""
    reviews = []

    for raw in place.get("reviews_data") or []:
        text = raw.get("review_text") or ""
        if not text.strip():
            continue

        reviews.append({
            "location": place.get("name") or source_query,
            "place_id": place_id,
            "google_id": raw.get("google_id") or google_id,
            "review_text": text,
            "rating": raw.get("review_rating"),
            "timestamp": _to_iso_timestamp(raw),
            "author_name": _anonymize(raw.get("author_title") or ""),
            "author_url": "",
            "language": "en",
            "relative_time": "",
            "review_url": raw.get("review_link") or "",
            "source_platform": "google_maps_outscraper",
            "source_review_id": raw.get("review_id") or raw.get("reviews_id") or "",
        })

    return {
        "reviews": reviews,
        "total_reviews_all_langs": place.get("reviews"),
        "english_reviews_count": len(reviews),
        "source_platform": "google_maps_outscraper",
        "source_query": source_query,
        "place_id": place_id,
        "google_id": google_id,
        "reviews_link": place.get("reviews_link") or "",
        "location_link": place.get("location_link") or "",
        "reviews_per_score": place.get("reviews_per_score") or {},
    }


def dedupe_reviews(reviews: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Deduplicate review records from checkpoint merges while preserving order."""
    seen = set()
    deduped = []
    for review in reviews:
        key = (
            review.get("source_review_id")
            or review.get("review_url")
            or f"{review.get('author_name', '')}|{review.get('timestamp', '')}|{review.get('review_text', '')}"
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(review)
    return deduped
