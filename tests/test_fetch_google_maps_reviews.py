import json

import pytest

from scripts import fetch_google_maps_reviews as mod
from scripts.fetch_google_maps_reviews import _query_for_poi


def test_query_for_poi_prefers_existing_place_id():
    query, source = _query_for_poi(
        "Test POI",
        "Test POI Fukui Japan",
        {"reviews": [{"place_id": "ChIJ_existing"}]},
        "place-id-or-search",
    )

    assert query == "ChIJ_existing"
    assert source == "place_id"


def test_query_for_poi_can_force_search_query():
    query, source = _query_for_poi(
        "Test POI",
        "Test POI Fukui Japan",
        {"place_id": "ChIJ_existing"},
        "search",
    )

    assert query == "Test POI Fukui Japan"
    assert source == "search"


def test_query_for_poi_place_id_mode_requires_place_id():
    with pytest.raises(ValueError):
        _query_for_poi("Test POI", "Test POI Fukui Japan", {"reviews": []}, "place-id")


def test_fetch_city_dry_run_does_not_require_client_or_modify_checkpoint(tmp_path, monkeypatch):
    checkpoint = tmp_path / "google_test.json"
    checkpoint.write_text(json.dumps({
        "POI A": {"reviews": [{"place_id": "ChIJ_same", "review_text": "Existing A"}]},
        "POI B": {"reviews": [{"place_id": "ChIJ_same", "review_text": "Existing B"}]},
        "POI C": {"reviews": []},
    }))
    monkeypatch.setitem(mod.CITY_CONFIGS, "test", {
        "display": "Test",
        "pois": {
            "POI A": "POI A Japan",
            "POI B": "POI B Japan",
            "POI C": "POI C Japan",
        },
        "checkpoint": checkpoint,
    })

    before = checkpoint.read_text()
    stats = mod.fetch_city("test", client=None, reviews_limit=100, dry_run=True)

    assert checkpoint.read_text() == before
    assert stats["place_id_queries"] == 2
    assert stats["search_queries"] == 1
    assert stats["duplicate_queries_planned"] == 1
