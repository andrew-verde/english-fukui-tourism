"""FTAS survey normalization and Japanese friction tagging helpers."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

import pandas as pd
import yaml


SATISFACTION_MAP = {
    "とても不満": 1,
    "不満": 2,
    "どちらでもない": 3,
    "普通": 3,
    "満足": 4,
    "とても満足": 5,
}

VISIT_INTENT_MAP = {
    "全くそう思わない": 1,
    "そう思わない": 2,
    "どちらでもない": 3,
    "そう思う": 4,
    "とてもそう思う": 5,
}

JAPANESE_COLUMN_MAP = {
    "会員ID": "respondent_id",
    "登録施設": "registered_facility",
    "性別": "gender",
    "生まれ年": "birth_year",
    "回答時の年齢": "age_at_response",
    "年代": "age_group",
    "都道府県": "home_prefecture",
    "会員市町村": "home_municipality",
    "世帯年収": "household_income",
    "UA": "user_agent",
    "回答日時": "response_datetime",
    "回答月": "response_month",
    "回答エリア": "response_area",
    "回答エリア2": "response_area_2",
    "市町村": "municipality",
    "6分類": "six_category",
    "DMO": "dmo",
    "宿泊数（全体）": "overnights_total",
    "宿泊数（県内）": "overnights_in_prefecture",
    "宿泊エリア（県内）": "overnight_area_in_prefecture",
    "宿泊エリア（県外）": "overnight_area_outside_prefecture",
    "同行者": "companions",
    "訪問目的ALL": "visit_purpose_all",
    "情報収集ALL": "info_source_all",
    "福井県までの交通手段ALL": "transport_to_fukui_all",
    "福井県内での交通手段ALL": "transport_in_fukui_all",
    "福井県内での交通手段の満足度": "transport_satisfaction",
    "福井県内での交通手段の満足度の理由": "transport_satisfaction_reason",
    "宿泊費": "lodging_spend",
    "交通費": "transport_spend",
    "県内消費額": "in_prefecture_spend",
    "エリア訪問回数": "area_visit_count",
    "アンケート回答前に訪問した主な場所": "visited_before_main",
    "アンケート回答前に訪問した主な場所FA": "visited_before_free_text",
    "アンケート回答後に訪問する予定の主な場所": "planned_after_main",
    "アンケート回答後に訪問する予定の主な場所FA": "planned_after_free_text",
    "エリア総消費額": "area_total_spend",
    "満足度": "overall_satisfaction",
    "満足度の理由": "overall_satisfaction_reason",
    "不便さ": "inconvenience",
    "不便さの内容": "inconvenience_text",
    "NPS": "nps",
    "推奨項目": "recommendation_items",
    "施設に求めるもの": "facility_needs",
    "今後の来訪意向": "future_visit_intent",
    "福井県に求めるもの": "fukui_needs",
    "登録エリア": "registered_area",
    "満足度(商品・サービス)": "product_service_satisfaction",
    "満足度(商品・サービス)の理由": "product_service_satisfaction_reason",
}

PURPOSE_COLUMNS = {
    "宿でのんびり過ごす": "purpose_relax_at_lodging",
    "温泉や露天風呂": "purpose_hot_springs",
    "地元の美味しいものを食べる": "purpose_local_food",
    "花見や紅葉などの自然鑑賞": "purpose_nature",
    "名所、旧跡の観光": "purpose_historic_sites",
    "テーマパーク（遊園地、動物園、博物館など）": "purpose_theme_parks_museums",
    "買い物、アウトレット": "purpose_shopping",
    "お祭りやイベントへの参加・見物": "purpose_events",
    "スポーツ観戦や芸能鑑賞（コンサート等）": "purpose_sports_performing_arts",
    "アウトドア（海水浴、釣り、登山など）": "purpose_outdoors",
    "まちあるき、都市散策": "purpose_city_walk",
    "各種体験（手作り、果物狩りなど）": "purpose_hands_on_experience",
    "スキー・スノボ、マリンスポーツ": "purpose_ski_marine_sports",
    "その他スポーツ（ゴルフ、テニスなど）": "purpose_other_sports",
    "ドライブ・ツーリング": "purpose_driving_touring",
    "友人・親戚を尋ねる": "purpose_visiting_friends_relatives",
    "出張など仕事関係": "purpose_business",
    "その他": "purpose_other",
}

INFO_SOURCE_COLUMNS = {
    "観光展・物産展": "info_tourism_fair",
    "新聞・雑誌・ガイドブック": "info_newspaper_magazine_guidebook",
    "TV・ラジオ番組やCM": "info_tv_radio_ad",
    "観光パンフレット・ポスター": "info_brochure_poster",
    "観光連盟やDMOのHP": "info_dmo_website",
    "インターネット・アプリ": "info_internet_app",
    "Twitter": "info_twitter",
    "Instagram": "info_instagram",
    "Facebook": "info_facebook",
    "ブログ": "info_blog",
    "友人・知人": "info_friends",
    "観光協会等の案内所": "info_tourist_information_center",
    "タクシードライバーや地元の人": "info_taxi_driver_local_people",
    "宿泊施設": "info_lodging",
}

TRANSPORT_COLUMNS = {
    "自家用車": "transport_to_fukui_private_car",
    "レンタカー": "transport_to_fukui_rental_car",
    "新幹線": "transport_to_fukui_shinkansen",
    "在来線": "transport_to_fukui_local_train",
    "飛行機": "transport_to_fukui_airplane",
    "旅行会社ツアーバス": "transport_to_fukui_tour_bus",
    "県外から訪れていない（福井県在住）": "transport_to_fukui_local_resident",
    "タクシー": "transport_in_fukui_taxi",
    "路線バス": "transport_in_fukui_route_bus",
    "徒歩": "transport_in_fukui_walk",
    "レンタサイクル": "transport_in_fukui_rental_bicycle",
}

ISHIKAWA_COLUMN_MAP = {
    "ID": "respondent_id",
    "回答エリア": "response_area",
    "施設": "registered_facility",
    "回答日時": "response_datetime",
    "宿泊数（全行程）": "overnights_total",
    "宿泊数（県内）": "overnights_in_prefecture",
    "宿泊エリア（県内）": "overnight_area_in_prefecture",
    "宿泊エリア（県外）": "overnight_area_outside_prefecture",
    "同行者": "companions",
    "宿泊目的": "visit_purpose_all",
    "交通手段": "transport_to_prefecture_all",
    "交通手段（施設）": "transport_to_facility_all",
    "満足度（交通手段）": "transport_satisfaction",
    "満足度理由（交通手段）": "transport_satisfaction_reason",
    "一人あたり宿泊費": "lodging_spend",
    "一人あたり交通費": "transport_spend",
    "一人あたり消費額（県内）": "in_prefecture_spend",
    "訪問回数": "area_visit_count",
    "情報源": "info_source_all",
    "訪問施設（前）": "visited_before_main",
    "訪問施設（前）自由記入": "visited_before_free_text",
    "訪問施設（後）自由記入": "planned_after_free_text",
    "一人あたり消費額（施設）": "area_total_spend",
    "満足度（商品・サービス）": "product_service_satisfaction",
    "満足度理由（商品・サービス）": "product_service_satisfaction_reason",
    "満足度（施設）": "overall_satisfaction",
    "満足度理由（施設）": "overall_satisfaction_reason",
    "不便（施設）": "inconvenience",
    "不便理由": "inconvenience_text",
    "NPS": "nps",
    "自由意見（施設）": "facility_needs",
    "リピート意向": "future_visit_intent",
    "自由意見（県内）": "prefecture_needs",
    "性別": "gender",
    "生年": "birth_year",
    "都道府県": "home_prefecture",
    "市区町村": "home_municipality",
    "世帯年収": "household_income",
    "回答動機": "response_motivation",
    "旅全体の総合満足度を教えてください。": "trip_overall_satisfaction",
    "石川県への旅行を、どのくらい家族や友人に勧めたいと薦めたいと思いますか。\n０（まったく薦めたくない）～１０（ぜひ薦めたい）でお答え下さい。": "prefecture_trip_nps",
    "今回の旅行またはお出かけにおいて、特に人に薦めたいと感じたものとその理由について具体的に教えてください。": "recommendation_reason",
}

ALL_RENAME_COLUMNS = {
    **JAPANESE_COLUMN_MAP,
    **PURPOSE_COLUMNS,
    **INFO_SOURCE_COLUMNS,
    **TRANSPORT_COLUMNS,
}


def load_japanese_codebook(path: str | Path) -> dict:
    """Load a Japanese friction codebook YAML."""
    with open(path) as f:
        raw = yaml.safe_load(f)
    codebook = {}
    for code, attrs in raw.get("friction_codes", {}).items():
        codebook[code] = {
            "label": attrs["label"],
            "type": attrs["type"],
            "keywords": [str(kw) for kw in attrs.get("keywords", [])],
        }
    return codebook


def _clean_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    value = value.strip()
    if not value or value.lower() == "nan":
        return ""
    return value


def combine_text_fields(row: pd.Series, fields: Iterable[str]) -> str:
    """Combine free-text survey fields into one taggable string."""
    parts = [_clean_text(row.get(field, "")) for field in fields]
    return "。".join(part for part in parts if part)


def normalize_flag(value: object) -> bool:
    """Return True for FTAS checkbox-like selected values."""
    if pd.isna(value):
        return False
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip()
    return text not in {"", "0", "0.0", "False", "false", "nan", "NaN", "なし", "無し"}


def contains_choice(value: object, choice: str) -> bool:
    """Return True when a comma-separated Japanese survey cell contains choice."""
    text = _clean_text(value)
    if not text:
        return False
    parts = [part.strip() for part in re.split(r"[,、/]", text) if part.strip()]
    return any(choice in part for part in parts)


def normalize_ftas_survey(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize raw FTAS respondent-level survey rows."""
    out = df.rename(columns={k: v for k, v in ALL_RENAME_COLUMNS.items() if k in df.columns}).copy()

    if "response_datetime" in out.columns:
        out["response_datetime"] = pd.to_datetime(out["response_datetime"], errors="coerce", utc=True)
        out["response_date"] = out["response_datetime"].dt.date.astype("string")
        out["response_year_month"] = out["response_datetime"].dt.tz_convert(None).dt.to_period("M").astype("string")
        out["post_hokuriku_shinkansen_fukui"] = out["response_datetime"] >= pd.Timestamp("2024-03-16", tz="UTC")

    flag_columns = list(PURPOSE_COLUMNS.values()) + list(INFO_SOURCE_COLUMNS.values()) + list(TRANSPORT_COLUMNS.values())
    for col in flag_columns:
        if col in out.columns:
            out[col] = out[col].apply(normalize_flag)

    for col in ["overnights_total", "overnights_in_prefecture", "lodging_spend", "transport_spend", "in_prefecture_spend", "area_total_spend", "nps"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")

    if "transport_satisfaction" in out.columns:
        out["transport_satisfaction_score"] = out["transport_satisfaction"].map(SATISFACTION_MAP)
    if "overall_satisfaction" in out.columns:
        out["overall_satisfaction_score"] = out["overall_satisfaction"].map(SATISFACTION_MAP)
    if "future_visit_intent" in out.columns:
        out["future_visit_intent_score"] = out["future_visit_intent"].map(VISIT_INTENT_MAP)
    if "inconvenience" in out.columns:
        out["reported_inconvenience"] = out["inconvenience"].apply(normalize_flag)

    text_fields = [
        "transport_satisfaction_reason",
        "overall_satisfaction_reason",
        "inconvenience_text",
        "facility_needs",
        "fukui_needs",
        "product_service_satisfaction_reason",
    ]
    for col in text_fields:
        if col not in out.columns:
            out[col] = ""
    out["friction_source_text"] = out.apply(lambda row: combine_text_fields(row, text_fields), axis=1)

    if "respondent_id" not in out.columns:
        out["respondent_id"] = pd.RangeIndex(start=1, stop=len(out) + 1).astype(str)
    else:
        missing = out["respondent_id"].isna() | out["respondent_id"].astype(str).str.strip().eq("")
        out.loc[missing, "respondent_id"] = [f"row_{i}" for i in out.index[missing]]

    return out


def normalize_ishikawa_survey(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize Ishikawa official tourism survey rows to the FTAS-like schema."""
    out = df.rename(columns={k: v for k, v in ISHIKAWA_COLUMN_MAP.items() if k in df.columns}).copy()
    out["survey_prefecture"] = "Ishikawa"

    if "response_area" in out.columns:
        out["survey_area_group"] = out["response_area"].astype(str).str.strip()
        out["municipality"] = out["survey_area_group"]

    if "response_datetime" in out.columns:
        out["response_datetime"] = pd.to_datetime(out["response_datetime"], errors="coerce", utc=True)
        out["response_date"] = out["response_datetime"].dt.date.astype("string")
        out["response_year_month"] = out["response_datetime"].dt.tz_convert(None).dt.to_period("M").astype("string")

    for col in ["overnights_total", "overnights_in_prefecture", "lodging_spend", "transport_spend", "in_prefecture_spend", "area_total_spend", "nps", "prefecture_trip_nps"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    if "prefecture_trip_nps" in out.columns:
        out["nps"] = out["prefecture_trip_nps"].combine_first(out.get("nps", pd.Series(index=out.index, dtype=float)))

    if "transport_satisfaction" in out.columns:
        out["transport_satisfaction_score"] = out["transport_satisfaction"].map(SATISFACTION_MAP)
    if "overall_satisfaction" in out.columns:
        out["overall_satisfaction_score"] = out["overall_satisfaction"].map(SATISFACTION_MAP)
    if "trip_overall_satisfaction" in out.columns:
        trip_score = out["trip_overall_satisfaction"].map(SATISFACTION_MAP)
        out["overall_satisfaction_score"] = trip_score.combine_first(out.get("overall_satisfaction_score", pd.Series(index=out.index, dtype=float)))
    if "future_visit_intent" in out.columns:
        out["future_visit_intent_score"] = out["future_visit_intent"].map({
            "行きたくない": 1,
            "あまり行きたいと思わない": 2,
            "どちらともいえない": 3,
            "機会があれば行きたい": 4,
            "また行きたい（1年以内）": 5,
            "また行きたい（１年以内）": 5,
            "石川県在住": pd.NA,
        })
    if "inconvenience" in out.columns:
        out["reported_inconvenience"] = out["inconvenience"].astype(str).str.contains("感じた", na=False)

    transport_to = out.get("transport_to_prefecture_all", pd.Series(index=out.index, dtype=object))
    transport_facility = out.get("transport_to_facility_all", pd.Series(index=out.index, dtype=object))
    out["transport_to_fukui_private_car"] = transport_to.apply(lambda v: contains_choice(v, "自家用車"))
    out["transport_to_fukui_rental_car"] = transport_to.apply(lambda v: contains_choice(v, "レンタカー"))
    out["transport_to_fukui_shinkansen"] = transport_to.apply(lambda v: contains_choice(v, "新幹線"))
    out["transport_to_fukui_local_train"] = transport_to.apply(lambda v: contains_choice(v, "在来線"))
    out["transport_to_fukui_airplane"] = transport_to.apply(lambda v: contains_choice(v, "飛行機"))
    out["transport_to_fukui_tour_bus"] = transport_to.apply(lambda v: contains_choice(v, "ツアーバス") or contains_choice(v, "高速バス") or contains_choice(v, "夜行バス"))
    out["transport_to_fukui_local_resident"] = transport_to.apply(lambda v: contains_choice(v, "県内在住"))
    out["transport_in_fukui_taxi"] = transport_facility.apply(lambda v: contains_choice(v, "タクシー"))
    out["transport_in_fukui_route_bus"] = transport_facility.apply(lambda v: contains_choice(v, "路線バス"))
    out["transport_in_fukui_walk"] = transport_facility.apply(lambda v: contains_choice(v, "徒歩"))
    out["transport_in_fukui_rental_bicycle"] = transport_facility.apply(lambda v: contains_choice(v, "レンタサイクル"))

    text_fields = [
        "transport_satisfaction_reason",
        "overall_satisfaction_reason",
        "inconvenience_text",
        "facility_needs",
        "prefecture_needs",
        "product_service_satisfaction_reason",
        "recommendation_reason",
    ]
    for col in text_fields:
        if col not in out.columns:
            out[col] = ""
    out["friction_source_text"] = out.apply(lambda row: combine_text_fields(row, text_fields), axis=1)

    if "respondent_id" not in out.columns:
        out["respondent_id"] = [f"ishikawa_{i}" for i in out.index]
    else:
        missing = out["respondent_id"].isna() | out["respondent_id"].astype(str).str.strip().eq("")
        out.loc[missing, "respondent_id"] = [f"ishikawa_{i}" for i in out.index[missing]]
    return out


def prepare_combined_official_surveys(fukui: pd.DataFrame, ishikawa: pd.DataFrame) -> pd.DataFrame:
    """Align Fukui FTAS and Ishikawa official survey rows into one table."""
    fukui = fukui.copy()
    fukui["survey_prefecture"] = "Fukui"
    if "survey_area_group" not in fukui.columns:
        fukui["survey_area_group"] = fukui.get("response_area", "")
    common = sorted(set(fukui.columns) | set(ishikawa.columns))
    return pd.concat(
        [fukui.reindex(columns=common), ishikawa.reindex(columns=common)],
        ignore_index=True,
        sort=False,
    )


def tag_japanese_text(text: str, codebook: dict) -> list[str]:
    """Return Japanese friction code names found by substring keyword matching."""
    text = _clean_text(text)
    if not text:
        return []
    matched = []
    for code, attrs in codebook.items():
        for keyword in attrs["keywords"]:
            if keyword and keyword in text:
                matched.append(code)
                break
    return matched


def tag_ftas_dataframe(df: pd.DataFrame, text_col: str, codebook: dict) -> pd.DataFrame:
    """Add one boolean column per Japanese friction code plus friction_codes."""
    out = df.copy()
    codes = list(codebook.keys())
    for code in codes:
        keywords = codebook[code]["keywords"]
        out[code] = out[text_col].fillna("").astype(str).apply(
            lambda text, keywords=keywords: any(keyword in text for keyword in keywords if keyword)
        )
    out["friction_codes"] = out[codes].apply(lambda row: [code for code in codes if bool(row[code])], axis=1)
    out["any_friction"] = out[codes].any(axis=1)
    return out


def normalize_area_name(name: object) -> str:
    """Normalize Japanese area names enough for deterministic joins."""
    text = _clean_text(name)
    text = re.sub(r"\s+", "", text)
    return text.replace("エリア", "")
