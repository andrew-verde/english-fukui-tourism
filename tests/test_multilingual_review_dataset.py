import json
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.build_multilingual_review_dataset import build_multilingual_outputs


def _write_checkpoint(path: Path, reviews: list[dict]) -> None:
    path.write_text(
        json.dumps(
            {
                "Test POI": {
                    "source_platform": "google_maps_outscraper",
                    "reviews": reviews,
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_multilingual_builder_missing_checkpoint_fails_before_outputs(tmp_path):
    output_dir = tmp_path / "out"
    missing = tmp_path / "missing_checkpoint.json"
    metadata = tmp_path / "poi_metadata.json"
    metadata.write_text("{}", encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="Missing Google review checkpoint"):
        build_multilingual_outputs(
            cutoff="2024-06-01",
            output_dir=output_dir,
            checkpoint_map={"Fukui": missing},
            metadata_file=metadata,
        )

    assert not output_dir.exists()


def test_multilingual_builder_groups_languages_and_tags_japanese(tmp_path):
    checkpoint = tmp_path / "checkpoint.json"
    metadata = tmp_path / "poi_metadata.json"
    metadata.write_text("{}", encoding="utf-8")
    _write_checkpoint(
        checkpoint,
        [
            {
                "review_text": "The signs were clear and the staff were friendly.",
                "timestamp": "2025-01-01T00:00:00Z",
                "rating": 5,
                "place_id": "p1",
                "source_review_id": "en-1",
                "language": "en",
            },
            {
                "review_text": "バスが少なく交通が不便でした。",
                "timestamp": "2025-01-02T00:00:00Z",
                "rating": 3,
                "place_id": "p1",
                "source_review_id": "ja-1",
                "language": "en",
            },
            {
                "review_text": "버스가 조금 불편했지만 경치가 좋았습니다.",
                "timestamp": "2025-01-03T00:00:00Z",
                "rating": 4,
                "place_id": "p1",
                "source_review_id": "ko-1",
                "language": "en",
            },
        ],
    )

    report = build_multilingual_outputs(
        cutoff="2024-06-01",
        output_dir=tmp_path / "out",
        checkpoint_map={"Fukui": checkpoint},
        metadata_file=metadata,
    )

    assert report["rows_retained"] == 3
    assert report["language_group_counts"]["english"] == 1
    assert report["language_group_counts"]["japanese"] == 1
    assert report["language_group_counts"]["other_non_english_non_japanese"] == 1

    japanese = pd.read_csv(tmp_path / "out" / "japanese_reviews_tagged.csv")
    assert japanese.loc[0, "detected_language"] == "ja"
    assert bool(japanese.loc[0, "transport_access"]) is True
    assert bool(japanese.loc[0, "any_friction"]) is True

    comparison = pd.read_csv(tmp_path / "out" / "japanese_english_friction_comparison.csv")
    row = comparison[
        (comparison["city"] == "Fukui")
        & (comparison["friction_code"] == "transport_access")
    ].iloc[0]
    assert row["friction_label_with_ja"] == "Transport / Access (交通・アクセス)"
    assert row["english_n"] == 1
    assert row["japanese_n"] == 1
    assert row["japanese_count"] == 1
    assert "fisher_exact_p_bh" in comparison.columns

    report_md = (tmp_path / "out" / "japanese_review_friction_analysis.md").read_text(encoding="utf-8")
    assert "Transport / Access (交通・アクセス)" in report_md

    other = pd.read_csv(tmp_path / "out" / "non_english_non_japanese_reviews.csv")
    assert other.loc[0, "detected_language"] == "ko"


def test_multilingual_builder_uses_cutoff_and_city_text_dedup(tmp_path):
    checkpoint = tmp_path / "checkpoint.json"
    metadata = tmp_path / "poi_metadata.json"
    metadata.write_text("{}", encoding="utf-8")
    _write_checkpoint(
        checkpoint,
        [
            {
                "review_text": "バスが少なく交通が不便でした。",
                "timestamp": "2025-01-02T00:00:00Z",
                "rating": 3,
                "place_id": "p1",
                "source_review_id": "ja-1",
            },
            {
                "review_text": "バスが少なく交通が不便でした。",
                "timestamp": "2025-01-03T00:00:00Z",
                "rating": 3,
                "place_id": "p2",
                "source_review_id": "ja-2",
            },
            {
                "review_text": "Great place with useful English signs.",
                "timestamp": "2023-01-01T00:00:00Z",
                "rating": 5,
                "place_id": "p1",
                "source_review_id": "old-en-1",
            },
        ],
    )

    report = build_multilingual_outputs(
        cutoff="2024-06-01",
        output_dir=tmp_path / "out",
        checkpoint_map={"Fukui": checkpoint},
        metadata_file=metadata,
    )

    assert report["rows_before_dedup"] == 2
    assert report["duplicates_removed"] == 1
    assert report["rows_retained"] == 1
    assert report["dropped_by_cutoff"] == 1


def test_multilingual_builder_reports_comparison_outputs(tmp_path):
    checkpoint = tmp_path / "checkpoint.json"
    metadata = tmp_path / "poi_metadata.json"
    metadata.write_text("{}", encoding="utf-8")
    _write_checkpoint(
        checkpoint,
        [
            {
                "review_text": "There is no public transport.",
                "timestamp": "2025-01-01T00:00:00Z",
                "rating": 3,
                "place_id": "p1",
                "source_review_id": "en-1",
            },
            {
                "review_text": "バスが少なく交通が不便でした。",
                "timestamp": "2025-01-02T00:00:00Z",
                "rating": 3,
                "place_id": "p1",
                "source_review_id": "ja-1",
            },
        ],
    )

    report = build_multilingual_outputs(
        cutoff="2024-06-01",
        output_dir=tmp_path / "out",
        checkpoint_map={"Fukui": checkpoint},
        metadata_file=metadata,
    )

    assert "japanese_english_friction_comparison" in report["outputs"]
    assert "japanese_review_friction_analysis" in report["outputs"]
    assert Path(report["outputs"]["japanese_english_friction_comparison"]).exists()
    assert Path(report["outputs"]["japanese_review_friction_analysis"]).exists()

    tagged = pd.read_csv(tmp_path / "out" / "tagged_reviews_multilingual.csv")
    english = tagged[tagged["language_group"] == "english"].iloc[0]
    assert bool(english["transport_access"]) is True
    assert bool(english["any_friction"]) is True
