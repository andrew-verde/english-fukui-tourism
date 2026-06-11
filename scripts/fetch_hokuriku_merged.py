#!/usr/bin/env python3
"""
fetch_hokuriku_merged.py — Download the merged tri-prefecture Hokuriku survey
microdata (hokuriku-inbound-kanko/opendata, CC-BY 4.0).

Year-split respondent-level files produced by the consortium's merge pipeline
(Fukui FTAS + Ishikawa QR survey + Toyama CKAN), updated daily by their CI.

Writes:
  output/hokuriku_merged/raw/merged_survey_<year>.csv
  output/hokuriku_merged/source_manifest.json

Usage:
    python scripts/fetch_hokuriku_merged.py [--years 2023 2024 2025 2026] [--force]
"""

import argparse
import hashlib
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils.logger import setup_logger

logger = setup_logger(__name__)

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "output" / "hokuriku_merged" / "raw"
MANIFEST = ROOT / "output" / "hokuriku_merged" / "source_manifest.json"
BASE_URL = "https://raw.githubusercontent.com/hokuriku-inbound-kanko/opendata/main/output_merge"
LICENSE_NOTE = (
    "CC-BY 4.0. Attribution: 北陸インバウンド観光DX・データコンソーシアム "
    "(hokuriku-inbound-kanko/opendata); upstream sources: Fukui FTAS (CC-BY 4.0), "
    "Ishikawa QR survey (CC-BY 2.1 JP), Toyama CKAN (CC-BY)."
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch merged Hokuriku survey microdata")
    parser.add_argument("--years", type=int, nargs="+", default=[2023, 2024, 2025, 2026])
    parser.add_argument("--force", action="store_true", help="Re-download even if present")
    args = parser.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {"license": LICENSE_NOTE, "files": []}
    if MANIFEST.exists():
        manifest = json.loads(MANIFEST.read_text())

    existing = {f["filename"]: f for f in manifest.get("files", [])}
    for year in args.years:
        name = f"merged_survey_{year}.csv"
        dest = RAW_DIR / name
        url = f"{BASE_URL}/{name}"
        if dest.exists() and not args.force:
            logger.info(f"Already present, skipping: {name}")
            continue
        logger.info(f"Downloading {url}")
        with urllib.request.urlopen(url) as resp, open(dest, "wb") as fh:
            fh.write(resp.read())
        digest = hashlib.sha256(dest.read_bytes()).hexdigest()
        existing[name] = {
            "filename": name,
            "url": url,
            "sha256": digest,
            "bytes": dest.stat().st_size,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
        logger.info(f"Wrote {dest} ({dest.stat().st_size:,} bytes)")

    manifest["files"] = sorted(existing.values(), key=lambda f: f["filename"])
    manifest["license"] = LICENSE_NOTE
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    logger.info(f"Manifest: {MANIFEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
