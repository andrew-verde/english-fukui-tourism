import math

import pytest

from scripts.build_reservation_panels import FILES, RAW_DIR, load_panel, panel_summary


ORACLE = {
    "fukui-station": ("2023-10-01", "2026-09-29", 1095, 167, 928, 238.102, 464.261, 1725634.2, 3686341.5),
    "obama": ("2023-10-25", "2026-09-29", 1071, 143, 928, 55.986, 132.128, 883804.9, 2014277.6),
    "echizen-coast": ("2024-11-01", "2026-09-29", 698, 0, 698, math.nan, 67.441, math.nan, 2243630.6),
    "mikatagoko": ("2025-04-24", "2026-09-28", 523, 0, 523, math.nan, 127.927, math.nan, 2028429.8),
}


@pytest.mark.parametrize("locality", ORACLE)
def test_reservation_panel_oracle(locality):
    if not (RAW_DIR / FILES[locality]).exists():
        pytest.skip("optional raw reservation data not available")
    summary = panel_summary(load_panel(locality))
    expected = ORACLE[locality]
    assert summary["date_min"].strftime("%Y-%m-%d") == expected[0]
    assert summary["date_max"].strftime("%Y-%m-%d") == expected[1]
    assert (summary["n_days"], summary["n_pre"], summary["n_post"]) == expected[2:5]
    for key, value in zip(("pre_people", "post_people", "pre_fee", "post_fee"), expected[5:]):
        if math.isnan(value):
            assert math.isnan(summary[key])
        else:
            assert summary[key] == pytest.approx(value, abs=0.1)
