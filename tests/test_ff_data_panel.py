import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.build_ff_data_panel import build_panel, clean_value, parse_payload


COLUMNS = [
    "pref_code",
    "pref_name",
    "year",
    "quarter",
    "dimension_set",
    "nationality_code",
    "nationality_name",
    "purpose_code",
    "purpose_name",
    "transport_mode_code",
    "transport_mode_name",
    "flow_people",
]


def record(
    *,
    destination_code,
    nationality_code,
    nationality_name,
    mode_code,
    mode_name,
    values=(10, 20, 30, 40),
):
    return {
        "id": f"{destination_code}-{nationality_code}-{mode_code}",
        "metadata": {
            "DPF:year": "2024",
            "FFD:departure_prefecture_code": "13000",
            "FFD:destination_prefecture_code": destination_code,
            "FFD:nationality_code": nationality_code,
            "FFD:nationality_name": nationality_name,
            "FFD:purpose_code": "1",
            "FFD:purpose_name": "観光・レジャー",
            "FFD:transport_mode_code": mode_code,
            "FFD:transport_mode_name": mode_name,
            "FFD:first_quarter": values[0],
            "FFD:second_quarter": values[1],
            "FFD:third_quarter": values[2],
            "FFD:fourth_quarter": values[3],
        },
    }


def payload(*records):
    return {
        "data": {
            "search": {
                "totalNumber": len(records),
                "searchResults": list(records),
            }
        }
    }


def test_clean_value():
    assert clean_value(1160) == 1160.0
    assert clean_value("1,098,250") == 1098250.0
    assert clean_value(None) is None
    assert clean_value("") is None
    assert clean_value("-") is None
    assert clean_value("X") is None


def test_parse_payload_keeps_dimension_sets_separate():
    rows = parse_payload(
        payload(
            record(
                destination_code="18000",
                nationality_code="US",
                nationality_name="米国",
                mode_code="0",
                mode_name="全機関",
            ),
            record(
                destination_code="17000",
                nationality_code="0",
                nationality_name="全国籍",
                mode_code="rail",
                mode_name="鉄道",
            ),
        )
    )

    assert len(rows) == 8
    nationality = [row for row in rows if row["dimension_set"] == "nationality"]
    transport = [row for row in rows if row["dimension_set"] == "transport_mode"]
    assert len(nationality) == 4
    assert len(transport) == 4
    assert {row["transport_mode_code"] for row in nationality} == {"0"}
    assert {row["nationality_code"] for row in transport} == {"0"}


def test_build_panel_schema_no_nulls_row_count_and_aggregation(tmp_path):
    nationality = record(
        destination_code="18000",
        nationality_code="US",
        nationality_name="米国",
        mode_code="0",
        mode_name="全機関",
    )
    transport = record(
        destination_code="17000",
        nationality_code="0",
        nationality_name="全国籍",
        mode_code="rail",
        mode_name="鉄道",
        values=(1, 2, 3, 4),
    )
    (tmp_path / "ffd_2024_0000000.json").write_text(
        json.dumps(payload(nationality, transport), ensure_ascii=False)
    )
    (tmp_path / "ffd_2024_0000002.json").write_text(
        json.dumps(payload(nationality), ensure_ascii=False)
    )

    panel = build_panel(tmp_path)

    assert list(panel.columns) == COLUMNS
    assert not panel.isnull().any().any()
    assert len(panel) == 8
    assert "vintage" not in panel.columns
    fukui_q1 = panel[
        (panel.pref_code == "18000")
        & (panel.quarter == 1)
        & (panel.dimension_set == "nationality")
    ]
    assert fukui_q1.iloc[0].flow_people == 20.0


def test_parse_payload_rejects_nationality_transport_cross():
    crossed = record(
        destination_code="18000",
        nationality_code="US",
        nationality_name="米国",
        mode_code="rail",
        mode_name="鉄道",
    )

    with pytest.raises(
        ValueError,
        match="record crosses nationality and transport mode",
    ):
        parse_payload(payload(crossed))
