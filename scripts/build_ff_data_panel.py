#!/usr/bin/env python3
"""
build_ff_data_panel.py — Convert FF-Data API records into a tidy inbound-flow
prefecture × quarter panel for the Hokuriku Shinkansen analysis.

Inputs:
  output/national_stats/ff_data/raw/ffd_<year>_<offset>.json

Outputs:
  output/national_stats/ff_data_panel.csv
  output/national_stats/ff_data_panel_summary.md

Usage:
    python scripts/build_ff_data_panel.py
"""

import json
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils.logger import setup_logger

logger = setup_logger(__name__)

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "output" / "national_stats" / "ff_data" / "raw"
PANEL_PATH = ROOT / "output" / "national_stats" / "ff_data_panel.csv"
SUMMARY_PATH = ROOT / "output" / "national_stats" / "ff_data_panel_summary.md"
TARGET_PREFS = {
    "16000": "富山県",
    "17000": "石川県",
    "18000": "福井県",
    "21000": "岐阜県",
}
PREF_NAMES = {
    "北海道": "01000", "青森県": "02000", "岩手県": "03000", "宮城県": "04000",
    "秋田県": "05000", "山形県": "06000", "福島県": "07000", "茨城県": "08000",
    "栃木県": "09000", "群馬県": "10000", "埼玉県": "11000", "千葉県": "12000",
    "東京都": "13000", "神奈川県": "14000", "新潟県": "15000", "富山県": "16000",
    "石川県": "17000", "福井県": "18000", "山梨県": "19000", "長野県": "20000",
    "岐阜県": "21000", "静岡県": "22000", "愛知県": "23000", "三重県": "24000",
    "滋賀県": "25000", "京都府": "26000", "大阪府": "27000", "兵庫県": "28000",
    "奈良県": "29000", "和歌山県": "30000", "鳥取県": "31000", "島根県": "32000",
    "岡山県": "33000", "広島県": "34000", "山口県": "35000", "徳島県": "36000",
    "香川県": "37000", "愛媛県": "38000", "高知県": "39000", "福岡県": "40000",
    "佐賀県": "41000", "長崎県": "42000", "熊本県": "43000", "大分県": "44000",
    "宮崎県": "45000", "鹿児島県": "46000", "沖縄県": "47000",
}
PREF_NAMES.update({re.sub(r"[都府県]$", "", name): code for name, code in list(PREF_NAMES.items())})
QUARTER_KEYS = {
    1: ("FFD:first_quarter", "first_quarter", "第1四半期"),
    2: ("FFD:second_quarter", "second_quarter", "第2四半期"),
    3: ("FFD:third_quarter", "third_quarter", "第3四半期"),
    4: ("FFD:fourth_quarter", "fourth_quarter", "第4四半期"),
}


def clean_value(value):
    """Return numeric FF-Data flow value or None."""
    if value in (None, "", "-", "X", "x"):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return float(str(value).replace(",", "").strip())


def _pick(metadata: dict, *keys, default=None):
    for key in keys:
        if key in metadata and metadata[key] not in (None, ""):
            return metadata[key]
    return default


def _label(metadata: dict, stem: str, japanese: str, default: str) -> tuple[str, str]:
    aliases = ("transportation", "transport") if stem == "transport_mode" else ()
    code = str(
        _pick(
            metadata,
            f"FFD:{stem}_code",
            f"{stem}_code",
            *(f"FFD:{alias}_code" for alias in aliases),
            *(f"{alias}_code" for alias in aliases),
            f"{japanese}コード",
            default="0",
        )
    )
    name = str(
        _pick(
            metadata,
            f"FFD:{stem}_name",
            f"FFD:{stem}",
            stem,
            *(f"FFD:{alias}_name" for alias in aliases),
            *(f"FFD:{alias}" for alias in aliases),
            *aliases,
            japanese,
            default=default,
        )
    )
    return code, name


def _pref_code(metadata: dict, side: str) -> str | None:
    japanese = "出発都道府県" if side == "departure" else "目的都道府県"
    raw_code = _pick(
        metadata,
        f"FFD:{side}_prefecture_code",
        f"{side}_prefecture_code",
        f"{japanese}コード",
    )
    if raw_code is not None:
        digits = re.sub(r"\D", "", str(raw_code))
        if len(digits) == 5 and digits.endswith("000"):
            return digits
        if 1 <= len(digits) <= 2:
            return f"{int(digits):02d}000"
    name = str(
        _pick(
            metadata,
            f"FFD:{side}_prefecture_name",
            f"{side}_prefecture_name",
            japanese,
            f"FFD:{side}_point",
            f"{side}_point",
            "出発地" if side == "departure" else "目的地",
            default="",
        )
    ).strip()
    name = re.sub(r"^\d+\s*", "", name)
    return PREF_NAMES.get(name)


def parse_record(record: dict) -> list[dict]:
    """Return target-prefecture quarterly rows from one API record."""
    metadata = record.get("metadata") or {}
    year_raw = _pick(metadata, "DPF:year", "FFD:year", "year", "年")
    if year_raw is None:
        return []
    year_match = re.search(r"\d{4}", str(year_raw))
    if not year_match:
        raise ValueError(f"invalid year: {year_raw!r}")
    year = int(year_match.group())
    origin_code = _pref_code(metadata, "departure")
    pref_code = _pref_code(metadata, "destination")
    if pref_code not in TARGET_PREFS or origin_code is None or origin_code == pref_code:
        return []

    nationality_code, nationality_name = _label(metadata, "nationality", "国籍", "全国籍")
    purpose_code, purpose_name = _label(metadata, "purpose", "旅行目的", "全目的")
    mode_code, mode_name = _label(metadata, "transport_mode", "交通機関", "全機関")
    if mode_name == "全機関" or mode_code == "0":
        dimension_set = "nationality"
        mode_code, mode_name = "0", "全機関"
    elif nationality_name == "全国籍" or nationality_code == "0":
        dimension_set = "transport_mode"
        nationality_code, nationality_name = "0", "全国籍"
    else:
        raise ValueError("record crosses nationality and transport mode; FF-Data does not publish this")

    rows = []
    for quarter, keys in QUARTER_KEYS.items():
        value = clean_value(_pick(metadata, *keys))
        if value is None:
            continue
        rows.append(
            {
                "pref_code": pref_code,
                "pref_name": TARGET_PREFS[pref_code],
                "year": year,
                "quarter": quarter,
                "dimension_set": dimension_set,
                "nationality_code": nationality_code,
                "nationality_name": nationality_name,
                "purpose_code": purpose_code,
                "purpose_name": purpose_name,
                "transport_mode_code": mode_code,
                "transport_mode_name": mode_name,
                "flow_people": value,
            }
        )
    return rows


def parse_payload(payload: dict) -> list[dict]:
    search = payload.get("data", {}).get("search", {})
    return [
        row
        for record in search.get("searchResults", []) or []
        for row in parse_record(record)
    ]


def build_panel(raw_dir: Path) -> pd.DataFrame:
    rows = []
    paths = sorted(raw_dir.glob("ffd_*_*.json"))
    if not paths:
        raise FileNotFoundError(f"no FF-Data pages in {raw_dir}")
    for path in paths:
        payload = json.loads(path.read_text())
        parsed = parse_payload(payload)
        logger.info("%s: %d target-flow rows", path.name, len(parsed))
        rows.extend(parsed)
    if not rows:
        raise ValueError(
            "no quarterly FF-Data rows found; API dataset may expose only legacy annual OD fields"
        )
    panel = pd.DataFrame(rows)
    keys = [
        "pref_code", "pref_name", "year", "quarter", "dimension_set",
        "nationality_code", "nationality_name", "purpose_code", "purpose_name",
        "transport_mode_code", "transport_mode_name",
    ]
    panel = panel.groupby(keys, as_index=False, dropna=False).flow_people.sum()
    return panel.sort_values(keys).reset_index(drop=True)


def main() -> int:
    try:
        panel = build_panel(RAW_DIR)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        logger.error("%s — run `make fetch-ff-data` first", exc)
        return 1

    if panel.isnull().any().any():
        logger.error("panel contains null values")
        return 1
    dupes = panel.duplicated(
        subset=[
            "pref_code", "year", "quarter", "dimension_set",
            "nationality_code", "purpose_code", "transport_mode_code",
        ]
    ).sum()
    if dupes:
        logger.error("%d duplicate panel keys", dupes)
        return 1
    missing = {
        (int(year), pref)
        for year in panel.year.unique()
        for pref in TARGET_PREFS
        if not set(panel.loc[(panel.year == year) & (panel.pref_code == pref), "quarter"]) == {1, 2, 3, 4}
    }
    if missing:
        logger.error("incomplete prefecture-years (need quarters 1–4): %s", sorted(missing))
        return 1

    PANEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(PANEL_PATH, index=False)
    logger.info("panel written: %s (%d rows)", PANEL_PATH, len(panel))

    totals = (
        panel[
            (panel.nationality_code == "0")
            & (panel.purpose_code == "0")
            & (panel.transport_mode_code == "0")
        ]
        .groupby(["pref_name", "year", "quarter"])
        .flow_people.sum()
        .unstack([1, 2])
    )
    lines = [
        "# FF-Data panel summary",
        "",
        f"Rows: {len(panel)} ({panel.year.min()}–{panel.year.max()}, four target prefectures)",
        "",
        "## Published all-dimension inbound flow totals",
        "",
        totals.to_markdown() if not totals.empty else "No all-dimension rows published.",
        "",
        "Notes: domestic inter-prefecture arrivals only; same-prefecture and airport legs excluded.",
        "Nationality and transport-mode records are separate published tables, not a cross-product.",
        "2024 Q1 contains only 16 post-opening days after the 2024-03-16 extension.",
    ]
    SUMMARY_PATH.write_text("\n".join(lines))
    logger.info("summary written: %s", SUMMARY_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
