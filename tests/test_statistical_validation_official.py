"""Regression tests for the 2026-06 statistical-suite audit fixes.

Locks in three bugs that changed published results:
1. reported_inconvenience coded 感じなかった as True (checkbox normalizer misuse)
2. repeat survey responses were not deduplicated (rows != respondents)
3. friction-rate comparisons used all respondents as denominator even though
   tags only exist for free-text writers
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.statistical_validation_official import _dedup_respondents, _has_text
from src.official_fukui.ftas import normalize_ftas_survey


def _ftas_row(**overrides):
    base = {
        "会員ID": "m1",
        "回答日時": "2024-05-01 10:00:00",
        "不便さ": "感じなかった",
        "不便さの内容": "",
    }
    base.update(overrides)
    return base


def test_reported_inconvenience_negative_response_is_false():
    df = normalize_ftas_survey(pd.DataFrame([_ftas_row(不便さ="感じなかった")]))
    assert bool(df.loc[0, "reported_inconvenience"]) is False


def test_reported_inconvenience_positive_responses_are_true():
    df = normalize_ftas_survey(pd.DataFrame([
        _ftas_row(不便さ="感じた"),
        _ftas_row(不便さ="あり"),
    ]))
    assert df["reported_inconvenience"].tolist() == [True, True]


def test_future_visit_intent_score_maps_actual_ftas_labels():
    df = normalize_ftas_survey(pd.DataFrame([
        _ftas_row(今後の来訪意向="また行きたい（1年以内）"),
        _ftas_row(今後の来訪意向="機会があれば行きたい"),
        _ftas_row(今後の来訪意向="福井県在住"),
    ]))
    assert df["future_visit_intent_score"].tolist()[:2] == [5, 4]
    assert pd.isna(df["future_visit_intent_score"].iloc[2])


def test_dedup_keeps_first_response_per_respondent():
    df = pd.DataFrame({
        "respondent_id": ["a", "a", "b", None, None],
        "response_datetime": [
            "2024-02-01", "2024-01-01", "2024-03-01", "2024-04-01", "2024-05-01",
        ],
        "value": [1, 2, 3, 4, 5],
    })
    deduped, audit = _dedup_respondents(df)
    # Respondent "a": earliest (2024-01-01, value=2) kept; null-ID rows kept as-is.
    assert audit["n_dropped_repeat_responses"] == 1
    assert sorted(deduped["value"].tolist()) == [2, 3, 4, 5]


def test_dedup_scoped_by_prefecture_keeps_cross_prefecture_ids():
    df = pd.DataFrame({
        "survey_prefecture": ["Fukui", "Ishikawa", "Fukui"],
        "respondent_id": ["x", "x", "x"],
        "response_datetime": ["2024-01-01", "2024-01-02", "2024-01-03"],
    })
    deduped, audit = _dedup_respondents(df, scope_cols=["survey_prefecture"])
    # Same ID in different prefectures is treated as distinct respondents.
    assert audit["n_dropped_repeat_responses"] == 1
    assert len(deduped) == 2


def test_has_text_excludes_blank_and_nan():
    df = pd.DataFrame({"friction_source_text": ["バスが少ない", "", "  ", None]})
    assert _has_text(df).tolist() == [True, False, False, False]
