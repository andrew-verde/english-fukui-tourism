import hashlib
from pathlib import Path

import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "output" / "synthesis"
EXPECTED_MUNICIPALITIES = {
    "Katsuyama", "Eiheiji", "Ikeda", "Fukui City", "Tsuruga", "Sakai",
    "Awara", "Sabae", "Mihama", "Wakasa", "Obama", "Ono", "Echizen City",
    "Oi", "Echizen Town", "Takahama", "Minami-Echizen",
}
INPUT_CHECKSUMS = {
    "data/causal/fukui_municipalities_scm.csv":
        "ff6cd1afecb0ec1175434cba0ab9964511fe9167ef57166c50e8ba713f84d953",
    "output/official_fukui/ftas_friction_by_municipality.csv":
        "a5c6304c97a76775fa2f35f9dd222e6296c70e9dddd7bace19d3290be9769192",
    "output/official_fukui/ftas_friction_by_transport_mode.csv":
        "52a74615198651a8e08d45562aef719002b20a34e55695fcfb3b1a423e6dd64f",
    "output/sem/nudge_priority_ranking.csv":
        "738239c6da60797df0e5f224bf6b9855bfcb30f9ced9ad97fc6cd9274a49d374",
}
GENERATED_INPUTS = {
    "output/official_fukui/ftas_friction_by_municipality.csv",
    "output/official_fukui/ftas_friction_by_transport_mode.csv",
    "output/sem/nudge_priority_ranking.csv",
}


@pytest.fixture(scope="module")
def regime_map():
    path = OUTPUT / "synthesis_regime_friction_map.csv"
    if not path.exists():
        pytest.skip("Run `make synthesis` to generate synthesis outputs")
    return pd.read_csv(path)


@pytest.fixture(scope="module")
def mode_friction():
    path = OUTPUT / "synthesis_mode_friction.csv"
    if not path.exists():
        pytest.skip("Run `make synthesis` to generate synthesis outputs")
    return pd.read_csv(path)


@pytest.fixture(scope="module")
def priority_matrix():
    path = OUTPUT / "synthesis_priority_matrix.csv"
    if not path.exists():
        pytest.skip("Run `make synthesis` to generate synthesis outputs")
    return pd.read_csv(path)


def test_input_feed_checksums():
    for relative, expected in INPUT_CHECKSUMS.items():
        path = ROOT / relative
        if not path.exists():
            # These gitignored feeds are produced by `make build-ftas` /
            # `make nudge-ranking` and are absent in a clean CI checkout.
            if relative in GENERATED_INPUTS:
                continue
            pytest.fail(f"Missing pinned synthesis input: {path}")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            pytest.fail(f"Checksum drift for {path}: expected {expected}, got {actual}")


def test_join_completeness_and_regime_counts(regime_map):
    assert len(regime_map) == 17
    assert regime_map["regime"].notna().all()
    assert set(regime_map["en"]) == EXPECTED_MUNICIPALITIES
    assert regime_map["regime"].value_counts().to_dict() == {
        "none": 8, "transient": 6, "durable": 3
    }
    high = regime_map[regime_map["regime_confidence"] == "high"]
    assert high["regime"].value_counts().to_dict() == {
        "none": 7, "transient": 4, "durable": 2
    }


def test_high_confidence_dose_response(regime_map):
    high = regime_map[regime_map["regime_confidence"] == "high"]
    corr = high["transport_access"].corr(high["leaked_lift_pct"])
    transient = high.loc[high["regime"] == "transient", "transport_access"].mean()
    non_transient = high.loc[high["regime"] != "transient", "transport_access"].mean()
    assert corr == pytest.approx(0.83, abs=0.02)
    assert transient == pytest.approx(2.86, abs=0.02)
    assert non_transient == pytest.approx(1.73, abs=0.02)


def test_transport_access_arrival_mode_headline(mode_friction):
    row = mode_friction.set_index("friction_code").loc["transport_access"]
    assert row["shinkansen_pct"] == pytest.approx(7.09, abs=0.05)
    assert row["private_car_pct"] == pytest.approx(0.66, abs=0.05)
    assert row["other_arrival_pooled_pct"] == pytest.approx(1.77, abs=0.05)
    assert row["shk_minus_other"] == pytest.approx(5.32, abs=0.05)
    assert row["shk_over_other_ratio"] == pytest.approx(4.00, abs=0.05)
    maximum = mode_friction.loc[mode_friction["shk_minus_other"].idxmax()]
    assert maximum["friction_code"] == "transport_access"
    second = mode_friction.nlargest(2, "shk_minus_other").iloc[1]
    assert second["friction_code"] == "waiting_crowding"
    assert second["shk_minus_other"] == pytest.approx(0.91, abs=0.05)


def test_priority_matrix_oracles(priority_matrix):
    expected = {
        "transport_access": "ACT NOW",
        "opening_hours_availability": "ACT NOW",
        "food_amenities_gap": "ACT NOW",
        "itinerary_fit_time_cost": "watch",
        "cleanliness_comfort": "quick win",
        "wayfinding_signage": "deprioritize",
        "waiting_crowding": "deprioritize",
        "accessibility_mobility": "deprioritize",
    }
    indexed = priority_matrix.set_index("friction_code")
    assert set(indexed.index) == set(expected)
    for code, quadrant in expected.items():
        assert indexed.loc[code, "quadrant"] == quadrant

    corner = priority_matrix[
        (priority_matrix["quadrant"] == "ACT NOW")
        & (priority_matrix["causal_opportunity"] == 1.0)
        & (priority_matrix["priority_n"] == 1.0)
    ]
    assert corner["friction_code"].tolist() == ["transport_access"]
