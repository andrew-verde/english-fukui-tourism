"""
mention_splitter.py — Split tourism text into sentence-level mentions.

Uses nltk.sent_tokenize which handles common abbreviations (Mr., Dr., St., etc.)
so they do not produce false sentence boundaries.
"""

import os
import re

import nltk

def _ensure_punkt():
    try:
        nltk.data.find("tokenizers/punkt_tab")
    except LookupError:
        nltk.download("punkt_tab", quiet=True)
    try:
        nltk.data.find("tokenizers/punkt")
    except LookupError:
        nltk.download("punkt", quiet=True)


def split_to_mentions(
    review_id: str,
    city: str,
    poi_name: str,
    poi_category: str,
    text: str,
    min_chars: int | None = None,
) -> list[dict]:
    """
    Split one text record into sentence-level mention dicts.

    Returns a list of dicts with fields:
        mention_id, review_id, city, poi_name, poi_category. `review_id` is
        retained as a compatibility field for existing callers.
        sentence_text, sentence_index
    """
    if not isinstance(text, str) or not text.strip():
        return []

    if min_chars is None:
        min_chars = int(os.getenv("MENTION_MIN_CHARS", "4"))

    _ensure_punkt()
    sentences = nltk.sent_tokenize(text)

    result = []
    for idx, sentence in enumerate(sentences):
        stripped = sentence.strip()
        if len(stripped) < min_chars:
            continue
        # Filter punctuation-only / emoji-only fragments while keeping short,
        # high-signal friction sentences like "Closed." / "Crowded."
        if not re.search(r"[A-Za-z0-9]", stripped):
            continue

        if len(stripped) >= min_chars:
            result.append({
                "mention_id": f"{review_id}_{idx}",
                "review_id": review_id,
                "city": city,
                "poi_name": poi_name,
                "poi_category": poi_category,
                "sentence_text": stripped,
                "sentence_index": idx,
            })
    return result
