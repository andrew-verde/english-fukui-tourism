"""
Tests for the focused friction analysis modules.
  - test_unified_schema: reviews_unified.csv has required columns and correct cities
  - test_mention_splitter: sentence splitting handles abbreviations correctly
  - test_tagger_codes: tag_text matches expected codes and rejects neutral text
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ── test_unified_schema ───────────────────────────────────────────────────────

REQUIRED_COLUMNS = [
    "city", "poi_id", "poi_name", "poi_category", "place_id",
    "review_id", "review_date", "review_rating", "review_text",
    "review_language", "review_author", "collection_date",
    "source_platform", "review_order_within_poi",
    "vader_compound", "sentiment_norm", "emotional_intensity_score",
    "primary_theme",
]

REVIEWS_CSV = Path(__file__).resolve().parent.parent / "output" / "friction_analysis" / "reviews_unified.csv"


def test_unified_schema():
    """reviews_unified.csv must have all required columns. If file absent, skip gracefully."""
    if not REVIEWS_CSV.exists():
        pytest.skip("reviews_unified.csv not present — run build_analysis_dataset.py first")

    df = pd.read_csv(REVIEWS_CSV)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    assert not missing, f"Missing columns: {missing}"

    cities = set(df["city"].unique())
    expected = {"Fukui", "Kanazawa", "Toyama"}
    assert cities == expected, f"City mismatch. Got: {cities}"


# ── test_mention_splitter ─────────────────────────────────────────────────────

from src.friction.mention_splitter import split_to_mentions


def test_mention_splitter_abbreviation():
    """'Dr. Smith went. He liked it.' should produce 2 sentences, not 3."""
    text = "Dr. Smith went. He liked it."
    mentions = split_to_mentions("rev001", "Fukui", "Test POI", "museum_cultural", text)
    assert len(mentions) == 2, f"Expected 2 sentences, got {len(mentions)}: {[m['sentence_text'] for m in mentions]}"


def test_mention_splitter_mention_id_format():
    """mention_id must follow pattern review_id_N."""
    text = "Great place. Beautiful views."
    mentions = split_to_mentions("abc123", "Kanazawa", "Test POI", "nature_scenic", text)
    assert len(mentions) >= 2
    assert mentions[0]["mention_id"] == "abc123_0"
    assert mentions[1]["mention_id"] == "abc123_1"


def test_mention_splitter_sentence_index():
    """sentence_index must be sequential integers starting at 0."""
    text = "First sentence. Second sentence. Third one here."
    mentions = split_to_mentions("rev002", "Toyama", "Test POI", "other", text)
    indices = [m["sentence_index"] for m in mentions]
    assert indices == list(range(len(mentions)))


def test_mention_splitter_short_filter():
    """Very short sentences should be filtered out by default."""
    text = "OK. Closed. This is a proper sentence with enough content."
    mentions = split_to_mentions("rev003", "Fukui", "Test POI", "other", text, min_chars=4)
    for m in mentions:
        assert len(m["sentence_text"]) >= 4
    # Punkt may merge the first two short sentences; accept either form.
    assert any(m["sentence_text"] in {"Closed.", "OK. Closed."} for m in mentions)


def test_mention_splitter_filters_punctuation_only():
    """Punctuation/emoji-only fragments should not become mentions."""
    text = "!!!. 👍. Closed."
    mentions = split_to_mentions("rev004", "Fukui", "Test POI", "other", text, min_chars=4)
    assert any(m["sentence_text"] == "Closed." for m in mentions)
    assert not any(m["sentence_text"].strip() in {"!!!.", "👍."} for m in mentions)


def test_mention_splitter_empty_text():
    """Empty or blank text must return empty list without error."""
    assert split_to_mentions("r1", "Fukui", "POI", "other", "") == []
    assert split_to_mentions("r2", "Fukui", "POI", "other", "   ") == []


def test_mention_splitter_preserves_fields():
    """All output records must carry city, poi_name, poi_category, review_id."""
    mentions = split_to_mentions("rev999", "Kanazawa", "Kenrokuen Garden", "nature_scenic",
                                 "The garden is lovely. I recommend visiting in spring.")
    for m in mentions:
        assert m["review_id"] == "rev999"
        assert m["city"] == "Kanazawa"
        assert m["poi_name"] == "Kenrokuen Garden"
        assert m["poi_category"] == "nature_scenic"


# ── test_tagger_codes ─────────────────────────────────────────────────────────

from src.friction.tagger import load_codebook, tag_text


@pytest.fixture(scope="module")
def codebook():
    codebook_path = Path(__file__).resolve().parent.parent / "config" / "friction_codebook.yaml"
    return load_codebook(codebook_path)


def test_tagger_transport_match(codebook):
    """Text with clear transport friction should match transport_access."""
    text = "The bus service is very infrequent and hard to get here."
    codes = tag_text(text, codebook)
    assert "transport_access" in codes


def test_tagger_english_gap_match(codebook):
    """Text mentioning no English signs should match english_information_gap."""
    text = "There are no English signs anywhere, everything is only in Japanese."
    codes = tag_text(text, codebook)
    assert "english_information_gap" in codes


def test_tagger_multi_code(codebook):
    """Text with two distinct friction signals should return at least two codes."""
    text = "It is hard to get here and there are no English signs at all."
    codes = tag_text(text, codebook)
    assert len(codes) >= 2


def test_tagger_neutral_no_match(codebook):
    """Neutral text with no friction or nudge keywords should return empty list."""
    text = "We visited yesterday."
    codes = tag_text(text, codebook)
    assert codes == []


def test_tagger_nudge_match(codebook):
    """Text with clear scenic value should match scenic_value nudge code."""
    text = "The view was absolutely breathtaking and stunning."
    codes = tag_text(text, codebook)
    assert "scenic_value" in codes


def test_tagger_case_insensitive(codebook):
    """Matching must be case-insensitive."""
    text = "There is NO PUBLIC TRANSPORT to get here."
    codes = tag_text(text, codebook)
    assert "transport_access" in codes


def test_tagger_word_boundary(codebook):
    """'view' inside 'review' must NOT match scenic_value."""
    text = "We read the review and decided to come."
    codes = tag_text(text, codebook)
    assert "scenic_value" not in codes


def test_tagger_compound_and_keywords(codebook):
    """Compound '&&' keywords should match when both parts are present."""
    text = "Visitors should note the stairs are narrow and steep in places."
    codes = tag_text(text, codebook)
    assert "accessibility_mobility" in codes


def test_tagger_curly_apostrophe_negation_suppresses_friction(codebook):
    """Curly apostrophe contractions should suppress negated crowding friction."""
    text = "The layout is spacious, so it doesn’t seem crowded."
    codes = tag_text(text, codebook)
    assert "waiting_crowding" not in codes


def test_tagger_not_crowded_remains_nudge_only(codebook):
    """Positive low-crowding phrasing should not inflate friction counts."""
    text = "The area wasn’t crowded, so it was easy to take photos."
    codes = tag_text(text, codebook)
    assert "waiting_crowding" not in codes


def test_tagger_near_miss_closure_and_transport(codebook):
    """Validated near-miss closure and bus interval language should be tagged."""
    text = "Closed because of construction. I waited for the next bus after the limited bus schedule."
    codes = tag_text(text, codebook)
    assert "opening_hours_availability" in codes
    assert "transport_access" in codes


def test_tagger_near_miss_trip_value(codebook):
    """Near-miss low-value itinerary complaints should be tagged."""
    text = "Nothing to see here, not worth the trip, and honestly don't waste your time coming here."
    codes = tag_text(text, codebook)
    assert "itinerary_fit_time_cost" in codes
    assert "price_value" in codes
