from pathlib import Path

import pandas as pd

from scripts.audit_review_sample_readiness import build_readiness_report
from scripts import audit_review_sample_readiness as mod


def _write_reviews(path: Path, rows: list[dict]) -> None:
    pd.DataFrame(rows).to_csv(path, index=False)


def test_readiness_report_fails_when_city_counts_are_too_small(tmp_path):
    csv_path = tmp_path / "reviews.csv"
    rows = []
    for city in ["Fukui", "Kanazawa", "Toyama"]:
        for i in range(2):
            rows.append({
                "city": city,
                "poi_name": f"{city} POI",
                "source_platform": "google_places",
                "primary_theme": "Scenic",
                "review_text": f"{city} review {i}",
            })
    _write_reviews(csv_path, rows)

    report = build_readiness_report(csv_path, min_reviews_per_city=10, expected_min_target=5)

    assert report["ready_for_stronger_city_level_inference"] is False
    assert report["hard_gates"]["min_reviews_per_city_met"] is False
    assert report["additional_reviews_needed_by_city"] == {
        "Fukui": 8,
        "Kanazawa": 8,
        "Toyama": 8,
    }


def test_readiness_report_passes_when_city_and_theme_cells_are_adequate(tmp_path):
    csv_path = tmp_path / "reviews.csv"
    rows = []
    for city in ["Fukui", "Kanazawa", "Toyama"]:
        for theme in ["Dinosaur", "Food", "Scenic", "Cultural", "Logistics"]:
            for i in range(5):
                rows.append({
                    "city": city,
                    "poi_name": f"{city} {theme} POI",
                    "source_platform": "google_maps_outscraper",
                    "primary_theme": theme,
                    "review_text": f"{city} {theme} review {i}",
                })
    _write_reviews(csv_path, rows)

    report = build_readiness_report(csv_path, min_reviews_per_city=25, expected_min_target=5)

    assert report["ready_for_stronger_city_level_inference"] is True
    assert report["hard_gates"]["shared_city_x_theme_expected_counts_met"] is True
    assert report["theme_chi_square_readiness"]["expected_min"] == 5


def test_readiness_report_can_pass_shared_themes_when_dinosaur_is_sparse(tmp_path):
    csv_path = tmp_path / "reviews.csv"
    rows = []
    for city in ["Fukui", "Kanazawa", "Toyama"]:
        for theme in ["Food", "Scenic", "Cultural", "Logistics"]:
            for i in range(5):
                rows.append({
                    "city": city,
                    "poi_name": f"{city} {theme} POI",
                    "source_platform": "google_maps_outscraper",
                    "primary_theme": theme,
                    "review_text": f"{city} {theme} review {i}",
                })
    rows.append({
        "city": "Fukui",
        "poi_name": "Fukui Dinosaur Museum",
        "source_platform": "google_maps_outscraper",
        "primary_theme": "Dinosaur",
        "review_text": "Fukui dinosaur review",
    })
    _write_reviews(csv_path, rows)

    report = build_readiness_report(csv_path, min_reviews_per_city=20, expected_min_target=5)

    assert report["theme_chi_square_readiness"]["valid_for_chi_square_approximation"] is False
    assert report["shared_theme_chi_square_readiness"]["valid_for_chi_square_approximation"] is True
    assert report["ready_for_stronger_city_level_inference"] is True
    assert report["ready_for_all_theme_city_level_inference"] is False


def test_friction_signal_density_treats_empty_list_strings_as_empty(tmp_path, monkeypatch):
    tagged = tmp_path / "tagged_mentions.csv"
    pd.DataFrame([
        {"city": "Fukui", "friction_codes": "[]"},
        {"city": "Fukui", "friction_codes": "['transport_access']"},
        {"city": "Toyama", "friction_codes": ""},
    ]).to_csv(tagged, index=False)
    monkeypatch.setattr(mod, "TAGGED_MENTIONS_CSV", tagged)

    density = mod._friction_signal_density()

    assert density["signal_mentions_total"] == 1
    assert density["signal_mentions_by_city"]["Fukui"]["signal_mentions"] == 1
    assert density["signal_mentions_by_city"]["Toyama"]["signal_mentions"] == 0
