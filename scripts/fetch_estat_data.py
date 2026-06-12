#!/usr/bin/env python3
"""
fetch_estat_data.py — Pull government statistics via the e-Stat REST API for
the datasets listed under `estat:` in config/national_data_sources.yaml.

Two-step flow per dataset (statsDataId values change per release cycle, so we
never hardcode them):
  1. getStatsList   — discover table ids under the survey's stats_code
  2. getStatsData   — pull each table as JSON, save raw response

Writes:
  output/national_stats/estat/raw/<stats_code>/<statsDataId>.json
  output/national_stats/estat/tables_<stats_code>.json   (discovered table list)
  output/national_stats/estat/estat_manifest.json

Requires:
  ESTAT_APP_ID env var — free registration at https://www.e-stat.go.jp
  (Mi-page > API). The key is personal; do not commit it.

Usage:
    ESTAT_APP_ID=... python scripts/fetch_estat_data.py [--dataset accommodation_survey]
    python scripts/fetch_estat_data.py --list-only   # discovery pass, no data pull
"""

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

import yaml
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils.logger import setup_logger

logger = setup_logger(__name__)

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "national_data_sources.yaml"
OUTPUT_DIR = ROOT / "output" / "national_stats" / "estat"
MANIFEST_PATH = OUTPUT_DIR / "estat_manifest.json"

API_BASE = "https://api.e-stat.go.jp/rest/3.0/app/json"
# Politeness delay between API calls; e-Stat has no published rate limit but
# bulk hammering risks the AppID being throttled.
CALL_DELAY_S = 1.0
# getStatsData caps at 100k values per call; large tables need paging via
# startPosition. We page until NEXT_KEY is absent.
PAGE_LIMIT = 100_000


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _api_get(endpoint: str, params: dict, timeout: int) -> dict:
    url = f"{API_BASE}/{endpoint}?{urlencode(params)}"
    with urlopen(url, timeout=timeout) as response:
        payload = json.loads(response.read())
    time.sleep(CALL_DELAY_S)
    return payload


def discover_tables(app_id: str, stats_code: str, timeout: int) -> list:
    """Return table metadata list for a survey code via getStatsList."""
    payload = _api_get(
        "getStatsList",
        {"appId": app_id, "statsCode": stats_code, "limit": 1000},
        timeout,
    )
    result = payload.get("GET_STATS_LIST", {})
    status = result.get("RESULT", {}).get("STATUS")
    if status != 0:
        raise RuntimeError(f"getStatsList status={status}: {result.get('RESULT')}")
    tables = result.get("DATALIST_INF", {}).get("TABLE_INF", [])
    if isinstance(tables, dict):
        tables = [tables]
    return tables


def fetch_table(app_id: str, stats_data_id: str, area_codes: list, timeout: int) -> list:
    """Pull one table (all pages) via getStatsData; returns raw JSON pages."""
    pages = []
    start = 1
    while True:
        params = {
            "appId": app_id,
            "statsDataId": stats_data_id,
            "limit": PAGE_LIMIT,
            "startPosition": start,
        }
        if area_codes:
            params["cdArea"] = ",".join(area_codes)
        payload = _api_get("getStatsData", params, timeout)
        result = payload.get("GET_STATS_DATA", {})
        status = result.get("RESULT", {}).get("STATUS")
        if status != 0:
            raise RuntimeError(f"getStatsData status={status}: {result.get('RESULT')}")
        pages.append(payload)
        next_key = (
            result.get("STATISTICAL_DATA", {})
            .get("RESULT_INF", {})
            .get("NEXT_KEY")
        )
        if not next_key:
            return pages
        start = int(next_key)


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch e-Stat datasets")
    parser.add_argument("--config", default=str(CONFIG_PATH), help="Path to source YAML")
    parser.add_argument("--dataset", help="Fetch only this dataset key from the config")
    parser.add_argument("--list-only", action="store_true", help="Discover tables, skip data pull")
    parser.add_argument("--timeout", type=int, default=120, help="Per-request timeout")
    parser.add_argument("--force", action="store_true", help="Re-fetch tables already on disk")
    args = parser.parse_args()

    app_id = os.environ.get("ESTAT_APP_ID")
    if not app_id:
        logger.error("ESTAT_APP_ID not set — register at e-stat.go.jp and export the key")
        return 1

    with open(args.config) as f:
        datasets = yaml.safe_load(f).get("estat", {}) or {}
    if args.dataset:
        if args.dataset not in datasets:
            logger.error("unknown dataset %r; options: %s", args.dataset, sorted(datasets))
            return 1
        datasets = {args.dataset: datasets[args.dataset]}

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "config": str(Path(args.config).resolve()),
        "datasets": {},
    }

    failures = 0
    for key, spec in datasets.items():
        stats_code = spec["stats_code"]
        logger.info("discovering tables for %s (%s)", key, stats_code)
        try:
            tables = discover_tables(app_id, stats_code, args.timeout)
        except Exception as exc:  # noqa: BLE001
            logger.error("discovery failed for %s: %s", key, exc)
            manifest["datasets"][key] = {"stats_code": stats_code, "error": str(exc)}
            failures += 1
            continue

        tables_path = OUTPUT_DIR / f"tables_{stats_code}.json"
        tables_path.write_text(json.dumps(tables, indent=2, ensure_ascii=False))
        logger.info("%s: %d tables discovered -> %s", key, len(tables), tables_path.name)

        entry = {"stats_code": stats_code, "table_count": len(tables), "tables": {}}
        if not args.list_only:
            raw_dir = OUTPUT_DIR / "raw" / stats_code
            raw_dir.mkdir(parents=True, exist_ok=True)
            for table in tables:
                sid = table.get("@id")
                target = raw_dir / f"{sid}.json"
                if target.exists() and not args.force:
                    entry["tables"][sid] = {"status": "cached", "sha256": _sha256(target.read_bytes())}
                    continue
                try:
                    pages = fetch_table(app_id, sid, spec.get("area_codes", []), args.timeout)
                except Exception as exc:  # noqa: BLE001
                    logger.error("table %s failed: %s", sid, exc)
                    entry["tables"][sid] = {"status": "error", "error": str(exc)}
                    failures += 1
                    continue
                data = json.dumps(pages, ensure_ascii=False).encode()
                target.write_bytes(data)
                entry["tables"][sid] = {"status": "fetched", "bytes": len(data), "sha256": _sha256(data)}
                logger.info("fetched %s (%d pages)", sid, len(pages))
        manifest["datasets"][key] = entry

    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    logger.info("manifest written: %s", MANIFEST_PATH)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
