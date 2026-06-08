import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.official_fukui.ftas import normalize_ftas_survey, normalize_ishikawa_survey, tag_japanese_text, tag_ftas_dataframe


def test_normalize_ftas_survey_core_fields():
    raw = pd.DataFrame([
        {
            "会員ID": "abc",
            "回答日時": "2024-03-17 10:00:00",
            "回答エリア": "福井駅前 エリア",
            "市町村": "福井市",
            "満足度": "満足",
            "福井県内での交通手段の満足度": "とても不満",
            "不便さ": "あり",
            "不便さの内容": "バスの本数が少なく交通が不便",
            "新幹線": "1",
        }
    ])
    df = normalize_ftas_survey(raw)
    assert df.loc[0, "respondent_id"] == "abc"
    assert df.loc[0, "overall_satisfaction_score"] == 4
    assert df.loc[0, "transport_satisfaction_score"] == 1
    assert bool(df.loc[0, "reported_inconvenience"]) is True
    assert bool(df.loc[0, "transport_to_fukui_shinkansen"]) is True
    assert bool(df.loc[0, "post_hokuriku_shinkansen_fukui"]) is True
    assert "バスの本数" in df.loc[0, "friction_source_text"]


def test_tag_japanese_text_transport_and_wayfinding():
    codebook = {
        "transport_access": {"keywords": ["交通が不便", "バスの本数"]},
        "wayfinding_signage": {"keywords": ["案内がわかりにく"]},
    }
    codes = tag_japanese_text("交通が不便で、案内がわかりにくかった。", codebook)
    assert codes == ["transport_access", "wayfinding_signage"]


def test_tag_ftas_dataframe_sets_boolean_columns():
    df = pd.DataFrame({"friction_source_text": ["混雑して待ち時間が長い", "とても満足"]})
    codebook = {
        "waiting_crowding": {"keywords": ["混雑", "待ち時間"]},
        "price_value": {"keywords": ["高い"]},
    }
    tagged = tag_ftas_dataframe(df, "friction_source_text", codebook)
    assert bool(tagged.loc[0, "waiting_crowding"]) is True
    assert bool(tagged.loc[0, "price_value"]) is False
    assert tagged.loc[0, "friction_codes"] == ["waiting_crowding"]
    assert bool(tagged.loc[1, "any_friction"]) is False


def test_normalize_ishikawa_survey_core_fields():
    raw = pd.DataFrame([
        {
            "ID": "ish001",
            "回答エリア": "金沢",
            "施設": "Test",
            "回答日時": "2024-04-01 12:00:00+09:00",
            "交通手段": "新幹線, 在来線",
            "交通手段（施設）": "路線バス, 徒歩",
            "満足度（交通手段）": "不満",
            "満足度（施設）": "満足",
            "不便（施設）": "感じた",
            "不便理由": "案内がわかりにくく、混雑していた",
            "NPS": "7",
            "リピート意向": "機会があれば行きたい",
        }
    ])
    df = normalize_ishikawa_survey(raw)
    assert df.loc[0, "survey_prefecture"] == "Ishikawa"
    assert df.loc[0, "survey_area_group"] == "金沢"
    assert df.loc[0, "transport_satisfaction_score"] == 2
    assert df.loc[0, "overall_satisfaction_score"] == 4
    assert bool(df.loc[0, "reported_inconvenience"]) is True
    assert bool(df.loc[0, "transport_to_fukui_shinkansen"]) is True
    assert bool(df.loc[0, "transport_in_fukui_route_bus"]) is True
    assert df.loc[0, "nps"] == 7
