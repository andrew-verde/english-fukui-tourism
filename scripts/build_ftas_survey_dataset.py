#!/usr/bin/env python3
"""
build_ftas_survey_dataset.py — Normalize and tag FTAS official survey rows.

Reads:
  output/official_fukui/raw/ftas_survey_all.csv
  output/official_fukui/raw/ftas_area_master.csv
  config/official_japanese_friction_codebook.yaml

Writes:
  output/official_fukui/ftas_survey_normalized.csv
  output/official_fukui/ftas_tagged_survey.csv
  output/official_fukui/ftas_friction_by_area.csv
  output/official_fukui/ftas_friction_by_municipality.csv
  output/official_fukui/ftas_friction_by_transport_mode.csv

Usage:
    python scripts/build_ftas_survey_dataset.py
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.official_fukui.ftas import load_japanese_codebook, normalize_ftas_survey, tag_ftas_dataframe
from src.official_fukui.ftas import normalize_ishikawa_survey, prepare_combined_official_surveys
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output" / "official_fukui"
RAW_DIR = OUTPUT_DIR / "raw"
CODEBOOK_PATH = ROOT / "config" / "official_japanese_friction_codebook.yaml"
SURVEY_RAW = RAW_DIR / "ftas_survey_all.csv"
AREA_RAW = RAW_DIR / "ftas_area_master.csv"
NORMALIZED_CSV = OUTPUT_DIR / "ftas_survey_normalized.csv"
TAGGED_CSV = OUTPUT_DIR / "ftas_tagged_survey.csv"
ISHIKAWA_RAW = RAW_DIR / "ishikawa_survey_all.csv"
ISHIKAWA_NORMALIZED_CSV = OUTPUT_DIR / "ishikawa_survey_normalized.csv"
ISHIKAWA_TAGGED_CSV = OUTPUT_DIR / "ishikawa_tagged_survey.csv"
COMBINED_TAGGED_CSV = OUTPUT_DIR / "official_surveys_tagged_combined.csv"

TRANSPORT_MODE_COLUMNS = [
    "transport_to_fukui_private_car",
    "transport_to_fukui_rental_car",
    "transport_to_fukui_shinkansen",
    "transport_to_fukui_local_train",
    "transport_to_fukui_airplane",
    "transport_to_fukui_tour_bus",
    "transport_to_fukui_local_resident",
    "transport_in_fukui_taxi",
    "transport_in_fukui_route_bus",
    "transport_in_fukui_walk",
    "transport_in_fukui_rental_bicycle",
]


def _load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing input: {path}. Run scripts/fetch_code4fukui_data.py first.")
    return pd.read_csv(path, dtype=str, low_memory=False)


def _friction_by_group(df: pd.DataFrame, group_col: str, codes: list[str]) -> pd.DataFrame:
    rows = []
    for group_value, grp in df.groupby(group_col, dropna=False):
        n = len(grp)
        for code in codes:
            count = int(grp[code].sum()) if code in grp.columns else 0
            rows.append({
                group_col: group_value if pd.notna(group_value) else "",
                "friction_code": code,
                "count": count,
                "n_respondents": n,
                "pct_of_respondents": round(100 * count / n, 2) if n else 0.0,
            })
    return pd.DataFrame(rows)


def _friction_by_transport(df: pd.DataFrame, codes: list[str]) -> pd.DataFrame:
    rows = []
    for mode in [c for c in TRANSPORT_MODE_COLUMNS if c in df.columns]:
        grp = df[df[mode] == True]
        n = len(grp)
        for code in codes:
            count = int(grp[code].sum()) if code in grp.columns else 0
            rows.append({
                "transport_mode": mode,
                "friction_code": code,
                "count": count,
                "n_respondents": n,
                "pct_of_respondents": round(100 * count / n, 2) if n else 0.0,
            })
    return pd.DataFrame(rows)


def _attach_area_master(df: pd.DataFrame, area_path: Path) -> pd.DataFrame:
    if not area_path.exists() or "response_area" not in df.columns:
        return df
    area = pd.read_csv(area_path, dtype=str)
    rename = {
        "親番号": "ftas_parent_id",
        "エリア名": "response_area",
        "緯度": "ftas_latitude",
        "経度": "ftas_longitude",
        "エリア説明文": "ftas_area_description",
    }
    area = area.rename(columns=rename)
    keep = [c for c in ["response_area", "ftas_parent_id", "ftas_latitude", "ftas_longitude", "ftas_area_description"] if c in area.columns]
    area = area[keep].drop_duplicates("response_area")
    return df.merge(area, on="response_area", how="left")


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize and tag official FTAS survey rows")
    parser.add_argument("--sample", type=int, default=0, help="Read only N rows for quick local smoke tests")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Loading FTAS survey: {SURVEY_RAW}")
    raw = pd.read_csv(SURVEY_RAW, dtype=str, low_memory=False, nrows=args.sample or None)
    normalized = normalize_ftas_survey(raw)
    normalized = _attach_area_master(normalized, AREA_RAW)
    normalized.to_csv(NORMALIZED_CSV, index=False)
    logger.info(f"Wrote normalized survey: {NORMALIZED_CSV} ({len(normalized)} rows)")

    codebook = load_japanese_codebook(CODEBOOK_PATH)
    tagged = tag_ftas_dataframe(normalized, "friction_source_text", codebook)
    tagged.to_csv(TAGGED_CSV, index=False)
    logger.info(f"Wrote tagged survey: {TAGGED_CSV} ({len(tagged)} rows)")

    if ISHIKAWA_RAW.exists():
        logger.info(f"Loading Ishikawa survey: {ISHIKAWA_RAW}")
        ishikawa_raw = pd.read_csv(ISHIKAWA_RAW, dtype=str, low_memory=False, nrows=args.sample or None)
        ishikawa_normalized = normalize_ishikawa_survey(ishikawa_raw)
        ishikawa_normalized.to_csv(ISHIKAWA_NORMALIZED_CSV, index=False)
        logger.info(f"Wrote normalized Ishikawa survey: {ISHIKAWA_NORMALIZED_CSV} ({len(ishikawa_normalized)} rows)")

        ishikawa_tagged = tag_ftas_dataframe(ishikawa_normalized, "friction_source_text", codebook)
        ishikawa_tagged.to_csv(ISHIKAWA_TAGGED_CSV, index=False)
        logger.info(f"Wrote tagged Ishikawa survey: {ISHIKAWA_TAGGED_CSV} ({len(ishikawa_tagged)} rows)")

        combined = prepare_combined_official_surveys(tagged, ishikawa_tagged)
        combined.to_csv(COMBINED_TAGGED_CSV, index=False)
        logger.info(f"Wrote combined official survey: {COMBINED_TAGGED_CSV} ({len(combined)} rows)")
    else:
        logger.warning(f"Ishikawa input not found; skipping combined official survey: {ISHIKAWA_RAW}")

    codes = list(codebook.keys())
    _friction_by_group(tagged, "response_area", codes).to_csv(OUTPUT_DIR / "ftas_friction_by_area.csv", index=False)
    _friction_by_group(tagged, "municipality", codes).to_csv(OUTPUT_DIR / "ftas_friction_by_municipality.csv", index=False)
    _friction_by_transport(tagged, codes).to_csv(OUTPUT_DIR / "ftas_friction_by_transport_mode.csv", index=False)
    logger.info("Wrote FTAS friction summary tables")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
