from pathlib import Path

import pandas as pd
import pytest

from scripts.build_resident_vision import (
    METHOD_SHIFT_CAVEAT,
    OVERVIEW_FILE,
    TIMESERIES_FILE,
    build_tables,
    load_inputs,
    write_report,
)

pytestmark = pytest.mark.skipif(
    not OVERVIEW_FILE.exists() or not TIMESERIES_FILE.exists(),
    reason="optional raw resident-vision data not available",
)


def test_resident_vision_oracles():
    overview, timeseries = load_inputs()
    stacked, net, migration = build_tables(overview, timeseries)

    assert len(stacked) == 39
    assert net["fiscal_year"].tolist() == list(range(2019, 2026))
    row_2024 = net.set_index("fiscal_year").loc[2024]
    assert row_2024["favorable_percent"] == pytest.approx(83.8)
    assert row_2024["migration_intention_percent"] == pytest.approx(11.2)
    assert row_2024["net_satisfaction_percent"] == pytest.approx(72.6)
    assert migration.set_index("fiscal_year").loc[
        2025, "migration_intention_percent"
    ] == pytest.approx(9.9)


def test_report_states_method_shift_and_no_causal_claim(tmp_path: Path):
    overview, timeseries = load_inputs()
    _, net, migration = build_tables(overview, timeseries)
    path = tmp_path / "report.md"
    write_report(net, migration, path)
    report = path.read_text(encoding="utf-8")

    assert METHOD_SHIFT_CAVEAT in report
    assert "postal-only in 2019-2021" in report
    assert "postal+WEB from 2022" in report
    assert "No causal claim" in report


def test_duplicate_living_option_rejected(tmp_path: Path):
    overview, timeseries = load_inputs()
    overview_path = tmp_path / "overview.csv"
    timeseries_path = tmp_path / "timeseries.csv"
    overview.to_csv(overview_path, index=False)
    pd.concat([timeseries, timeseries.iloc[[0]]]).to_csv(timeseries_path, index=False)

    with pytest.raises(ValueError, match="duplicate indicator/year/option"):
        load_inputs(overview_path, timeseries_path)
