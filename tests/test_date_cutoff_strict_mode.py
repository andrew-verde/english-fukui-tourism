import importlib
import os
import hashlib


def _reload_build_analysis_dataset(drop_unparseable: bool):
    os.environ["REVIEW_DATE_CUTOFF"] = "2024-06-01"
    os.environ["DROP_UNPARSEABLE_TIMESTAMPS"] = "1" if drop_unparseable else "0"
    import scripts.build_analysis_dataset as mod
    return importlib.reload(mod)


def test_unparseable_timestamp_kept_by_default():
    mod = _reload_build_analysis_dataset(drop_unparseable=False)
    stats = {
        "missing_timestamp": 0,
        "unparseable_timestamp": 0,
        "dropped_by_cutoff": 0,
        "dropped_unparseable_timestamp": 0,
        "theme_none": 0,
        "theme_counts": {},
        "theme_keyword_counts": {},
    }
    data = {
        "Test POI": {
            "reviews": [
                {
                    "review_text": "Great place.",
                    "language": "en",
                    "place_id": "pid1",
                    "timestamp": "not-a-timestamp",
                    "rating": 5,
                    "author_name": "A",
                }
            ]
        }
    }
    rows = mod._parse_reviews_from_checkpoint("Fukui", data, metadata={}, cutoff="2024-06-01", stats=stats)
    assert len(rows) == 1
    assert stats["unparseable_timestamp"] == 1
    assert stats["dropped_unparseable_timestamp"] == 0


def test_unparseable_timestamp_dropped_in_strict_mode():
    mod = _reload_build_analysis_dataset(drop_unparseable=True)
    stats = {
        "missing_timestamp": 0,
        "unparseable_timestamp": 0,
        "dropped_by_cutoff": 0,
        "dropped_unparseable_timestamp": 0,
        "theme_none": 0,
        "theme_counts": {},
        "theme_keyword_counts": {},
    }
    data = {
        "Test POI": {
            "reviews": [
                {
                    "review_text": "Great place.",
                    "language": "en",
                    "place_id": "pid1",
                    "timestamp": "not-a-timestamp",
                    "rating": 5,
                    "author_name": "A",
                }
            ]
        }
    }
    rows = mod._parse_reviews_from_checkpoint("Fukui", data, metadata={}, cutoff="2024-06-01", stats=stats)
    assert len(rows) == 0
    assert stats["unparseable_timestamp"] == 1
    assert stats["dropped_unparseable_timestamp"] == 1


def test_checkpoint_source_platform_is_preserved():
    mod = _reload_build_analysis_dataset(drop_unparseable=False)
    stats = {
        "missing_timestamp": 0,
        "unparseable_timestamp": 0,
        "dropped_by_cutoff": 0,
        "dropped_unparseable_timestamp": 0,
        "theme_none": 0,
        "theme_counts": {},
        "theme_keyword_counts": {},
    }
    data = {
        "Test POI": {
            "source_platform": "google_maps_outscraper",
            "reviews": [
                {
                    "review_text": "Great place with helpful signs.",
                    "language": "en",
                    "place_id": "pid1",
                    "timestamp": "2024-06-02T00:00:00+00:00",
                    "rating": 5,
                    "author_name": "A",
                }
            ],
        }
    }

    rows = mod._parse_reviews_from_checkpoint("Fukui", data, metadata={}, cutoff="2024-06-01", stats=stats)

    assert len(rows) == 1
    assert rows[0]["source_platform"] == "google_maps_outscraper"


def test_source_review_id_makes_review_id_order_independent():
    mod = _reload_build_analysis_dataset(drop_unparseable=False)
    first = mod._make_stable_review_id(
        "Fukui",
        "pid1",
        "Test POI",
        0,
        {"source_review_id": "provider-review-1"},
    )
    second = mod._make_stable_review_id(
        "Fukui",
        "pid1",
        "Test POI",
        99,
        {"source_review_id": "provider-review-1"},
    )
    expected = hashlib.sha256("Fukui_pid1_provider-review-1".encode()).hexdigest()[:12]

    assert first == second == expected

