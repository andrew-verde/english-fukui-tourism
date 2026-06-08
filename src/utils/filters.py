"""
Utility functions for filtering data by language.
"""

import logging
from langdetect import detect, DetectorFactory

logger = logging.getLogger(__name__)
DetectorFactory.seed = 0


def language_filter(text: str, target_language: str = 'en') -> bool:
    """
    Return True if text is detected as target_language (default: English).
    Requires at least 10 characters; returns False on detection failure.
    """
    if not isinstance(text, str) or len(text) < 10:
        return False
    try:
        return detect(text) == target_language
    except Exception:
        return False


if __name__ == '__main__':
    samples = [
        "I'm flying from California to Japan next month. Can't wait to see Kyoto!",
        "Wir haben das Museum sehr genossen. Die Ausstellungen waren beeindruckend.",
        "We're planning a 2-week trip and wondering if we should visit Fukui.",
    ]
    for text in samples:
        print(f"English: {language_filter(text)}  |  {text[:60]}")
