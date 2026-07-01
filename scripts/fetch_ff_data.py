#!/usr/bin/env python3
"""
fetch_ff_data.py — Pull FF-Data records from the MLIT Data Platform API.

Writes:
  output/national_stats/ff_data/raw/catalog.json
  output/national_stats/ff_data/raw/<dataset_id>_<offset>.json
  output/national_stats/ff_data_manifest.json

Requires:
  MLIT_DATA_APP_ID env var — MLIT Data Platform API key.

Usage:
    MLIT_DATA_APP_ID=... python scripts/fetch_ff_data.py [--force]
"""

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

import yaml
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils.logger import setup_logger

logger = setup_logger(__name__)

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "national_data_sources.yaml"
OUTPUT_DIR = ROOT / "output" / "national_stats"
RAW_DIR = OUTPUT_DIR / "ff_data" / "raw"
MANIFEST_PATH = OUTPUT_DIR / "ff_data_manifest.json"
PAGE_SIZE = 100
CALL_DELAY_S = 1.0


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _graphql(endpoint: str, app_id: str, query: str, timeout: int) -> bytes:
    body = json.dumps({"query": query}).encode()
    request = Request(
        endpoint,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "apikey": app_id,
        },
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:
        data = response.read()
    payload = json.loads(data)
    if payload.get("errors"):
        raise RuntimeError(f"GraphQL errors: {payload['errors']}")
    if "data" not in payload:
        raise RuntimeError("unexpected API response: no data field")
    time.sleep(CALL_DELAY_S)
    return data


def _catalog_query(catalog_id: str) -> str:
    return """
query {
  dataCatalog(IDs: ["%s"]) {
    id
    title
    datasets {
      id
      title
      data_count
    }
  }
}
""".strip() % catalog_id.replace('"', '\\"')


def _search_query(dataset_id: str, offset: int) -> str:
    dataset_id = dataset_id.replace('"', '\\"')
    return """
query {
  search(
    term: ""
    phraseMatch: true
    attributeFilter: {attributeName: "DPF:dataset_id", is: "%s"}
    first: %d
    size: %d
  ) {
    totalNumber
    searchResults { id metadata }
  }
}
""".strip() % (dataset_id, offset, PAGE_SIZE)


def _write_raw(path: Path, data: bytes) -> dict:
    path.write_bytes(data)
    return {"filename": path.name, "bytes": len(data), "sha256": _sha256(data)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch FF-Data from MLIT Data Platform")
    parser.add_argument("--config", default=str(CONFIG_PATH), help="Path to source YAML")
    parser.add_argument("--timeout", type=int, default=120, help="Per-request timeout")
    parser.add_argument("--force", action="store_true", help="Re-fetch pages already on disk")
    args = parser.parse_args()

    app_id = os.environ.get("MLIT_DATA_APP_ID")
    if not app_id:
        logger.error("MLIT_DATA_APP_ID not set — register for an MLIT Data Platform API key")
        return 1

    with open(args.config) as f:
        spec = yaml.safe_load(f).get("ff_data")
    if not spec:
        logger.error("ff_data block missing from %s", args.config)
        return 1

    endpoint = spec["api_base"]
    catalog_id = spec.get("catalog_id", "ffd")
    dataset_ids = [
        spec.get("dataset_id_template", "ffd_{year}").format(year=year)
        for year in spec["years"]
    ]
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "config": str(Path(args.config).resolve()),
        "api_base": endpoint,
        "catalog_id": catalog_id,
        "page_size": PAGE_SIZE,
        "sources": {},
    }

    failures = 0
    catalog_path = RAW_DIR / "catalog.json"
    try:
        if catalog_path.exists() and not args.force:
            catalog_data = catalog_path.read_bytes()
            logger.info("skip (exists): %s", catalog_path.name)
        else:
            catalog_data = _graphql(endpoint, app_id, _catalog_query(catalog_id), args.timeout)
            catalog_path.write_bytes(catalog_data)
            logger.info("fetched catalog %s", catalog_id)
        manifest["sources"]["catalog"] = _write_raw(catalog_path, catalog_data)
    except Exception as exc:  # noqa: BLE001
        logger.error("catalog discovery failed: %s", exc)
        manifest["sources"]["catalog"] = {"error": str(exc)}
        MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
        return 1

    catalog_payload = json.loads(catalog_data)
    catalogs = catalog_payload.get("data", {}).get("dataCatalog", [])
    available = {
        dataset["id"]
        for catalog in catalogs or []
        for dataset in catalog.get("datasets", []) or []
    }

    for dataset_id in dataset_ids:
        entry = {"pages": []}
        manifest["sources"][dataset_id] = entry
        if dataset_id not in available:
            entry["error"] = f"dataset absent from catalog {catalog_id}"
            logger.error("%s: %s", dataset_id, entry["error"])
            failures += 1
            continue
        offset = 0
        total = None
        while total is None or offset < total:
            target = RAW_DIR / f"{dataset_id}_{offset:07d}.json"
            try:
                if target.exists() and not args.force:
                    data = target.read_bytes()
                    logger.info("skip (exists): %s", target.name)
                else:
                    data = _graphql(endpoint, app_id, _search_query(dataset_id, offset), args.timeout)
                    target.write_bytes(data)
                    logger.info("fetched %s offset %d", dataset_id, offset)
                page = json.loads(data).get("data", {}).get("search", {})
                page_total = int(page.get("totalNumber", 0))
                records = page.get("searchResults", []) or []
                if total is None:
                    total = page_total
                elif page_total != total:
                    raise RuntimeError(f"total changed during paging: {total} -> {page_total}")
                entry["pages"].append(
                    {
                        **_write_raw(target, data),
                        "offset": offset,
                        "records": len(records),
                    }
                )
                if not records and offset < total:
                    raise RuntimeError(f"empty page before total={total}")
                offset += len(records)
            except Exception as exc:  # noqa: BLE001
                logger.error("%s offset %d failed: %s", dataset_id, offset, exc)
                entry["error"] = str(exc)
                failures += 1
                break
        entry["records"] = offset
        entry["reported_total"] = total

    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    logger.info("manifest written: %s", MANIFEST_PATH)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
