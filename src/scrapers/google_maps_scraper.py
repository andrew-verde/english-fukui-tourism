"""
Google Maps Scraper Module

This module provides functionality for scraping Google Places reviews
using the Google Places API.
"""

import hashlib
import os
import logging
import re
import time
from typing import Optional, List, Dict
import pandas as pd
import requests

from ..utils.logger import setup_logger

logger = setup_logger(__name__)


def _anonymize(name: str) -> str:
    if not name:
        return ""
    return "Reviewer_" + hashlib.sha256(name.encode()).hexdigest()[:6].upper()



class GoogleMapsScraper:
    """Scrape Google Maps reviews using Google Places API."""

    def __init__(self, api_key: Optional[str] = None, testing_mode: Optional[bool] = None):
        """
        Initialize Google Maps scraper.

        Args:
            api_key: Google Maps API key
            testing_mode: Limit API calls for testing (optional, uses TESTING_MODE env var if not provided)
        """
        import os
        self.api_key = api_key or os.getenv('GOOGLE_API_KEY')
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set")

        self.testing_mode = testing_mode if testing_mode is not None else os.getenv('TESTING_MODE', 'false').lower() == 'true'
        self.review_limit = int(os.getenv('GOOGLE_MAPS_REVIEW_LIMIT', '500'))
        self.base_url = "https://places.googleapis.com/v1/places"

        logger.info(f"Google Maps scraper initialized (testing_mode: {self.testing_mode}, review_limit: {self.review_limit})")

    def get_place_reviews(self, place_id: str, location_name: str = "") -> pd.DataFrame:
        """Fetch English reviews for a Google Place."""
        if self.testing_mode:
            logger.info(f"Testing mode: Returning sample data for {location_name or place_id}")
            sample_reviews = [
                {
                    "location": location_name or place_id,
                    "place_id": place_id,
                    "review_text": (
                        f"Sample review for {location_name or place_id}. "
                        "Beautiful place with amazing architecture and peaceful atmosphere."
                    ),
                    "rating": 4.5,
                    "timestamp": pd.Timestamp("2024-01-15"),
                    "author_name": _anonymize("Sample Reviewer"),
                    "author_url": "",
                    "language": "en",
                    "relative_time": "3 months ago",
                    "review_url": "",
                },
                {
                    "location": location_name or place_id,
                    "place_id": place_id,
                    "review_text": (
                        f"Another sample review for {location_name or place_id}. "
                        "The exhibits are well-maintained and educational."
                    ),
                    "rating": 4.0,
                    "timestamp": pd.Timestamp("2024-02-20"),
                    "author_name": _anonymize("Another Reviewer"),
                    "author_url": "",
                    "language": "en",
                    "relative_time": "2 months ago",
                    "review_url": "",
                },
            ]
            df = pd.DataFrame(sample_reviews)
            logger.info(f"Returned {len(df)} sample reviews for {location_name or place_id}")
            return df

        try:
            url = f"{self.base_url}/{place_id}"
            headers = {
                "X-Goog-Api-Key": self.api_key,
                "X-Goog-FieldMask": "id,displayName,reviews",
            }
            logger.info(f"Fetching reviews for {location_name or place_id}")
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

            if "error" in data:
                logger.warning(
                    f"API error for {location_name or place_id}: "
                    f"{data['error'].get('message', '')}"
                )
                return pd.DataFrame()

            reviews_data = []
            for review in data.get("reviews", [])[:self.review_limit]:
                lang = review.get("text", {}).get("languageCode", "en") or "en"
                if lang not in ("en", ""):
                    continue
                reviews_data.append({
                    "location": location_name or place_id,
                    "place_id": place_id,
                    "review_text": review.get("text", {}).get("text", ""),
                    "rating": review.get("rating", 0),
                    "timestamp": review.get("publishTime", ""),
                    "author_name": _anonymize(review.get("authorAttribution", {}).get("displayName", "")),
                    "author_url": "",
                    "language": lang,
                    "relative_time": review.get("relativePublishTimeDescription", ""),
                    "review_url": review.get("googleMapsUri", ""),
                })

            df = pd.DataFrame(reviews_data) if reviews_data else pd.DataFrame()
            logger.info(f"Fetched {len(df)} English reviews for {location_name or place_id}")
            return df

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {location_name or place_id}: {e}")
            return pd.DataFrame()

    def get_fukui_reviews(self, place_ids: Optional[List[str]] = None, location_names: Optional[Dict[str, str]] = None) -> pd.DataFrame:
        """
        Get reviews for major Fukui attractions.

        Args:
            place_ids: List of Google Place IDs for Fukui attractions
            location_names: Dictionary mapping place_id to human-readable names

        Returns:
            DataFrame with all reviews, including 'Location' column
        """
        # Try to get actual Place IDs if none provided and not in testing mode
        if place_ids is None:
            if not self.testing_mode:
                logger.info("Attempting to find actual Place IDs for Fukui attractions")
                actual_ids = self.get_actual_fukui_place_ids()
                if actual_ids:
                    place_ids = list(actual_ids.keys())
                    location_names = actual_ids
                else:
                    logger.warning("Could not find actual Place IDs, using placeholders")
                    # Fall back to placeholders
                    place_ids = [
                        'ChIJ_example_eiheiji',  # Eiheiji Temple
                        'ChIJ_example_dinosaur',  # Fukui Dinosaur Museum
                        'ChIJ_example_tojinbo',   # Tojinbo Cliffs
                    ]
                    location_names = {
                        'ChIJ_example_eiheiji': 'Eiheiji Temple',
                        'ChIJ_example_dinosaur': 'Fukui Dinosaur Museum',
                        'ChIJ_example_tojinbo': 'Tojinbo Cliffs',
                    }
            else:
                # Use placeholders in testing mode
                place_ids = [
                    'ChIJ_example_eiheiji',  # Eiheiji Temple
                    'ChIJ_example_dinosaur',  # Fukui Dinosaur Museum
                ]
                location_names = {
                    'ChIJ_example_eiheiji': 'Eiheiji Temple',
                    'ChIJ_example_dinosaur': 'Fukui Dinosaur Museum',
                }
                logger.info("Testing mode: Using placeholder Place IDs")

        if location_names is None:
            location_names = {pid: pid for pid in place_ids}

        all_reviews = []

        # Limit number of places
        max_locations = 2 if self.testing_mode else 10
        if len(place_ids) > max_locations:
            place_ids = place_ids[:max_locations]
            logger.info(f"Limiting to {max_locations} attractions")

        for place_id in place_ids:
            location_name = location_names.get(place_id, place_id)
            df = self.get_place_reviews(place_id, location_name)

            if not df.empty:
                all_reviews.append(df)

        if all_reviews:
            combined_df = pd.concat(all_reviews, ignore_index=True)
            logger.info(f"Combined {len(combined_df)} reviews from {len(all_reviews)} Fukui attractions")
            return combined_df
        else:
            logger.warning("No reviews retrieved for any Fukui attractions")
            return pd.DataFrame()

    def scrape_place_reviews(
        self,
        place_id: str,
        max_reviews: int = 500
    ) -> pd.DataFrame:
        """
        Scrape reviews for a specific place (legacy method).

        Args:
            place_id: Google Maps place ID
            max_reviews: Maximum reviews to retrieve

        Returns:
            DataFrame with reviews, ratings, author info
        """
        return self.get_place_reviews(place_id)

    def scrape_fukui_landmarks(self) -> pd.DataFrame:
        """
        Scrape reviews for Fukui landmarks (legacy method).

        Returns:
            DataFrame with reviews from Fukui landmarks
        """
        return self.get_fukui_reviews()

    def find_place_id(self, query: str) -> Optional[str]:
        """
        Find Google Place ID for a location query.

        Args:
            query: Search query (e.g., "Eiheiji Temple Fukui")

        Returns:
            Place ID if found, None otherwise
        """
        if self.testing_mode:
            logger.info(f"Testing mode: Skipping place ID search for {query}")
            return None

        try:
            search_url = "https://places.googleapis.com/v1/places:searchText"
            headers = {
                'X-Goog-Api-Key': self.api_key,
                'X-Goog-FieldMask': 'places.id,places.displayName',
                'Content-Type': 'application/json',
            }

            response = requests.post(search_url, headers=headers, json={'textQuery': query})
            response.raise_for_status()

            data = response.json()
            places = data.get('places', [])

            if places:
                place_id = places[0]['id']
                name = places[0].get('displayName', {}).get('text', query)
                logger.info(f"Found Place ID for '{query}': {place_id} ({name})")
                return place_id
            else:
                logger.warning(f"No results found for query: {query}")
                return None

        except Exception as e:
            logger.error(f"Error searching for place '{query}': {str(e)}")
            return None

    def get_actual_fukui_place_ids(self) -> Dict[str, str]:
        """
        Get actual Google Place IDs for major Fukui attractions.

        Returns:
            Dictionary mapping attraction names to Place IDs
        """
        fukui_attractions = {
            'Eiheiji Temple': 'Eiheiji Temple Fukui Japan',
            'Fukui Dinosaur Museum': 'Fukui Prefectural Dinosaur Museum Japan',
            'Tojinbo Cliffs': 'Tojinbo Japan',
            'Fukui Castle': 'Fukui Castle Ruins Japan',
            'Awara Onsen': 'Awara Onsen Fukui Japan',
            'Katsuyama Castle': 'Katsuyama Castle Fukui Japan',
            'Maruoka Castle': 'Maruoka Castle Fukui Japan',
            'Echizen Daibutsu': 'Echizen Daibutsu Fukui Japan',
            'Kehi Grand Shrine': 'Kehi Jingu Tsuruga Fukui Japan',
            'Fukui Prefectural Museum': 'Fukui Prefectural Museum Japan',
        }

        place_ids = {}

        for name, query in fukui_attractions.items():
            place_id = self.find_place_id(query)
            if place_id:
                place_ids[place_id] = name

        logger.info(f"Found {len(place_ids)} Place IDs for Fukui attractions")
        return place_ids
if __name__ == '__main__':
    # Example usage
    scraper = GoogleMapsScraper()

    # Get reviews for Fukui attractions
    fukui_reviews = scraper.get_fukui_reviews()
    print(f"Retrieved {len(fukui_reviews)} reviews from Fukui attractions")

    if not fukui_reviews.empty:
        print(f"Columns: {list(fukui_reviews.columns)}")
        print(f"Sample review:\n{fukui_reviews.iloc[0] if len(fukui_reviews) > 0 else 'No reviews'}")
