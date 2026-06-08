from src.scrapers.outscraper_reviews import dedupe_reviews, normalize_outscraper_place


def test_normalize_outscraper_place_maps_reviews_to_checkpoint_schema():
    payload = {
        "name": "Test Place",
        "place_id": "ChIJ_test",
        "google_id": "0xabc:0xdef",
        "reviews": 123,
        "reviews_data": [
            {
                "author_title": "Jane Reviewer",
                "review_text": "Helpful English signs and a beautiful view.",
                "review_rating": 5,
                "review_timestamp": 1717200000,
                "review_link": "https://example.com/review/1",
                "review_id": "review-1",
            }
        ],
    }

    result = normalize_outscraper_place(payload, source_query="Test Place Japan")

    assert result["source_platform"] == "google_maps_outscraper"
    assert result["total_reviews_all_langs"] == 123
    assert result["english_reviews_count"] == 1
    assert result["place_id"] == "ChIJ_test"
    review = result["reviews"][0]
    assert review["review_text"] == "Helpful English signs and a beautiful view."
    assert review["rating"] == 5
    assert review["timestamp"].startswith("2024-06-01")
    assert review["author_name"].startswith("Reviewer_")
    assert review["source_platform"] == "google_maps_outscraper"


def test_dedupe_reviews_prefers_source_review_id_then_url_then_content():
    reviews = [
        {"source_review_id": "a", "review_text": "First"},
        {"source_review_id": "a", "review_text": "First duplicate"},
        {"review_url": "https://example.com/review/2", "review_text": "Second"},
        {"review_url": "https://example.com/review/2", "review_text": "Second duplicate"},
        {"author_name": "Reviewer_X", "timestamp": "2024-06-01", "review_text": "Third"},
        {"author_name": "Reviewer_X", "timestamp": "2024-06-01", "review_text": "Third"},
    ]

    deduped = dedupe_reviews(reviews)

    assert [r["review_text"] for r in deduped] == ["First", "Second", "Third"]
