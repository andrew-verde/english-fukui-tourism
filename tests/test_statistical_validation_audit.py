import importlib
import os

import pandas as pd


def _reload_statistical_validation(cutoff: str = "2021-05-29"):
    os.environ["REVIEW_DATE_CUTOFF"] = cutoff
    import scripts.statistical_validation as mod
    return importlib.reload(mod)


def test_input_data_audit_accepts_mixed_iso_timestamp_precision():
    mod = _reload_statistical_validation()
    df = pd.DataFrame([
        {
            "city": "Fukui",
            "review_id": "r1",
            "review_date": "2026-03-05T15:39:25.948153532Z",
            "review_rating": 5,
            "review_text": "A useful English review.",
            "review_language": "en",
            "vader_compound": 0.5,
            "sentiment_norm": 0.75,
            "emotional_intensity_score": 0.5,
            "primary_theme": "Cultural",
        },
        {
            "city": "Kanazawa",
            "review_id": "r2",
            "review_date": "2025-05-04T21:24:57.344135Z",
            "review_rating": 4,
            "review_text": "Another useful English review.",
            "review_language": "en",
            "vader_compound": -0.2,
            "sentiment_norm": 0.4,
            "emotional_intensity_score": 0.2,
            "primary_theme": "Scenic",
        },
        {
            "city": "Toyama",
            "review_id": "r3",
            "review_date": "2024-06-01T00:00:00+00:00",
            "review_rating": 4,
            "review_text": "A third useful English review.",
            "review_language": "en",
            "vader_compound": 0.0,
            "sentiment_norm": 0.5,
            "emotional_intensity_score": 0.0,
            "primary_theme": "Food",
        },
    ])

    result = mod.input_data_audit(df)

    assert result.details["checks"]["all_dates_parse"] is True
    assert result.details["valid"] is True
