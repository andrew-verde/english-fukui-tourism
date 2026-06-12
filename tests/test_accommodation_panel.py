import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.build_accommodation_panel import PREF_CODES, PREF_ROW, clean_value


def test_clean_value_numeric_passthrough():
    assert clean_value(55537490) == 55537490.0
    assert clean_value(340140.0) == 340140.0


def test_clean_value_strips_revision_marker_and_commas():
    # JTA cells occasionally arrive string-typed with '*' revision markers
    # and thousands separators (observed in the 2024 confirmed release).
    assert clean_value("*1,160") == 1160.0
    assert clean_value("1,098,250") == 1098250.0


def test_clean_value_missing_codes():
    assert clean_value(None) is None
    assert clean_value("") is None
    assert clean_value("-") is None
    assert clean_value("X") is None


@pytest.mark.parametrize(
    "label, code, name",
    [
        ("　18福井県", "18", "福井県"),   # confirmed-file format: code + name
        ("　福井県", None, "福井県"),     # 2025 preliminary format: name only
        ("　01北海道", "01", "北海道"),
    ],
)
def test_pref_row_matches_both_label_formats(label, code, name):
    m = PREF_ROW.match(label.replace("　", " "))
    assert m is not None
    assert m.group(1) == code
    assert m.group(2) == name


def test_pref_row_rejects_non_prefecture_rows():
    # National-total rows ("令和6年3月") match the regex but must be filtered
    # by the PREF_CODES membership check the parser applies.
    m = PREF_ROW.match("令和6年3月")
    assert m is None or m.group(2) not in PREF_CODES


def test_pref_codes_complete():
    assert len(PREF_CODES) == 47
    assert PREF_CODES["福井県"] == "18"
    assert PREF_CODES["石川県"] == "17"
