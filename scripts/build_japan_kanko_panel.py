#!/usr/bin/env python3
"""Validate and combine japan-kanko-stat municipal monthly files."""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "output" / "national_stats" / "japan_kanko_stat" / "raw"
OUTPUT = ROOT / "output" / "national_stats" / "japan_kanko_stat_panel.csv"
COLS = ["年", "月", "地域区分", "データ区分", "都道府県コード", "都道府県名", "地域コード", "地域名称", "人数"]


def build_panel(raw_dir: Path = RAW) -> pd.DataFrame:
    paths = sorted(raw_dir.glob("city20*.csv"))
    if len(paths) != 5:
        raise FileNotFoundError(f"expected five city CSVs in {raw_dir}")
    frames = [pd.read_csv(path, encoding="utf-8-sig") for path in paths]
    for path, frame in zip(paths, frames):
        if list(frame.columns) != COLS:
            raise ValueError(f"{path.name}: unexpected schema")
    panel = pd.concat(frames, ignore_index=True)
    panel = panel[(panel["地域区分"] == "市区町村") & (panel["データ区分"] == "観光来訪者数")].copy()
    panel["ym"] = panel["年"].astype(int) * 100 + panel["月"].astype(int)
    panel["都道府県コード"] = pd.to_numeric(panel["都道府県コード"])
    panel["地域コード"] = pd.to_numeric(panel["地域コード"])
    panel["人数"] = pd.to_numeric(panel["人数"])
    if panel.duplicated(["ym", "地域コード"]).any():
        raise ValueError("duplicate municipality-month rows")
    return panel.sort_values(["地域コード", "ym"]).reset_index(drop=True)


def main() -> int:
    panel = build_panel()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(OUTPUT, index=False)
    print(f"Wrote {OUTPUT}: {len(panel)} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
