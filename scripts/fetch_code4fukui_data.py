#!/usr/bin/env python3
"""
fetch_code4fukui_data.py — Download official Code for Fukui CSV datasets.

Writes:
  output/official_fukui/raw/*.csv
  output/official_fukui/source_manifest.json

Usage:
    python scripts/fetch_code4fukui_data.py
"""

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils.logger import setup_logger

logger = setup_logger(__name__)

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "official_fukui_sources.yaml"
OUTPUT_DIR = ROOT / "output" / "official_fukui"
RAW_DIR = OUTPUT_DIR / "raw"
MANIFEST_PATH = OUTPUT_DIR / "source_manifest.json"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _download(url: str, timeout: int) -> bytes:
    with urlopen(url, timeout=timeout) as response:
        return response.read()


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch official Code for Fukui CSV data")
    parser.add_argument("--config", default=str(CONFIG_PATH), help="Path to source YAML")
    parser.add_argument("--timeout", type=int, default=120, help="Download timeout per file")
    parser.add_argument("--force", action="store_true", help="Re-download even when raw file exists")
    args = parser.parse_args()

    with open(args.config) as f:
        sources = yaml.safe_load(f).get("sources", {})

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "config": str(Path(args.config).resolve()),
        "sources": {},
    }

    for key, attrs in sources.items():
        url = attrs["url"]
        out_path = RAW_DIR / attrs["filename"]
        if out_path.exists() and not args.force:
            data = out_path.read_bytes()
            status = "cached"
            logger.info(f"Using cached {key}: {out_path}")
        else:
            logger.info(f"Downloading {key}: {url}")
            data = _download(url, args.timeout)
            out_path.write_bytes(data)
            status = "downloaded"

        manifest["sources"][key] = {
            "upstream_repo": attrs.get("upstream_repo", ""),
            "url": url,
            "description": attrs.get("description", ""),
            "path": str(out_path.relative_to(ROOT)),
            "bytes": len(data),
            "sha256": _sha256(data),
            "status": status,
        }

    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    logger.info(f"Wrote manifest: {MANIFEST_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
