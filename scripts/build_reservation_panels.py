#!/usr/bin/env python3
"""Load checksum-gated locality reservation panels by column name."""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "output" / "official_fukui" / "raw"
EVENT_DATE = pd.Timestamp("2024-03-16")
EXPECTED_COLUMNS = {
    "date_visit", "n_stay", "n_people", "n_room", "amount_fee", "n_reserve"
}
FILES = {
    "fukui-station": "fukui_station_reservation.csv",
    "obama": "obama_reservation.csv",
    "echizen-coast": "echizen_coast_reservation.csv",
    "mikatagoko": "mikatagoko_reservation.csv",
}


def load_panel(locality: str, raw_dir: Path = RAW_DIR) -> pd.DataFrame:
    frame = pd.read_csv(raw_dir / FILES[locality])
    if set(frame.columns) != EXPECTED_COLUMNS:
        raise ValueError(
            f"{locality}: expected columns {sorted(EXPECTED_COLUMNS)}, "
            f"got {sorted(frame.columns)}"
        )
    frame = frame.loc[:, sorted(EXPECTED_COLUMNS)].copy()
    frame["date_visit"] = pd.to_datetime(frame["date_visit"], errors="raise")
    numeric = EXPECTED_COLUMNS - {"date_visit"}
    frame[list(numeric)] = frame[list(numeric)].apply(pd.to_numeric, errors="raise")
    if frame["date_visit"].duplicated().any():
        raise ValueError(f"{locality}: duplicate visit dates")
    return frame.sort_values("date_visit").reset_index(drop=True)


def panel_summary(frame: pd.DataFrame) -> dict:
    pre = frame[frame.date_visit < EVENT_DATE]
    post = frame[frame.date_visit >= EVENT_DATE]
    return {
        "date_min": frame.date_visit.min(),
        "date_max": frame.date_visit.max(),
        "n_days": len(frame),
        "n_pre": len(pre),
        "n_post": len(post),
        "pre_people": pre.n_people.mean(),
        "post_people": post.n_people.mean(),
        "pre_fee": pre.amount_fee.mean(),
        "post_fee": post.amount_fee.mean(),
    }
