#!/usr/bin/env python3
"""
fetch_national_direct.py — Download direct-URL national supplementary files
(JR West press-release PDFs, 国土数値情報 archives) listed under `direct:` in
config/national_data_sources.yaml.

Writes:
  output/national_stats/raw/*
  output/national_stats/direct_manifest.json

Usage:
    python scripts/fetch_national_direct.py [--force]
"""

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils.logger import setup_logger

logger = setup_logger(__name__)

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "national_data_sources.yaml"
OUTPUT_DIR = ROOT / "output" / "national_stats"
RAW_DIR = OUTPUT_DIR / "raw"
MANIFEST_PATH = OUTPUT_DIR / "direct_manifest.json"

# JR West serves 403 to default urllib UA.
USER_AGENT = "Mozilla/5.0 (academic-research-fetch; contact: thesis author)"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _download(url: str, timeout: int) -> bytes:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=timeout) as response:
        return response.read()


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch direct-URL national data files")
    parser.add_argument("--config", default=str(CONFIG_PATH), help="Path to source YAML")
    parser.add_argument("--timeout", type=int, default=120, help="Download timeout per file")
    parser.add_argument("--force", action="store_true", help="Re-download even when raw file exists")
    args = parser.parse_args()

    with open(args.config) as f:
        sources = yaml.safe_load(f).get("direct", {}) or {}

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "config": str(Path(args.config).resolve()),
        "sources": {},
    }

    failures = 0
    for key, source in sources.items():
        target = RAW_DIR / source["filename"]
        if target.exists() and not args.force:
            data = target.read_bytes()
            logger.info("skip (exists): %s", target.name)
        else:
            try:
                data = _download(source["url"], args.timeout)
            except Exception as exc:  # noqa: BLE001 — record and continue
                logger.error("failed %s: %s", key, exc)
                manifest["sources"][key] = {"url": source["url"], "error": str(exc)}
                failures += 1
                continue
            target.write_bytes(data)
            logger.info("downloaded: %s (%d bytes)", target.name, len(data))

        manifest["sources"][key] = {
            "url": source["url"],
            "filename": source["filename"],
            "description": source.get("description", ""),
            "bytes": len(data),
            "sha256": _sha256(data),
        }

    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    logger.info("manifest written: %s", MANIFEST_PATH)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
