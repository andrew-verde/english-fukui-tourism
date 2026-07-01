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
import csv
import hashlib
import json
import re
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

def _raw_github_url(repo: str, commit: str, source_path: str) -> str:
    match = re.fullmatch(r"https://github\.com/([^/]+/[^/]+?)(?:\.git)?/?", repo)
    if not match:
        raise ValueError(f"Unsupported upstream_repo (expected GitHub HTTPS URL): {repo}")
    return f"https://raw.githubusercontent.com/{match.group(1)}/{commit}/{source_path}"


def _validate_source(key: str, attrs: dict) -> None:
    required = {"upstream_repo", "commit", "source_path", "sha256", "filename"}
    missing = sorted(required - attrs.keys())
    if missing:
        raise ValueError(f"{key}: missing pinned source fields: {', '.join(missing)}")
    if not re.fullmatch(r"[0-9a-f]{40}", str(attrs["commit"])):
        raise ValueError(f"{key}: commit must be a full 40-character Git SHA")
    if not re.fullmatch(r"[0-9a-f]{64}", str(attrs["sha256"])):
        raise ValueError(f"{key}: sha256 must be a 64-character lowercase digest")


def _row_count(data: bytes) -> int:
    text = data.decode("utf-8-sig")
    return max(sum(1 for _ in csv.reader(text.splitlines())) - 1, 0)


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
        _validate_source(key, attrs)
        url = _raw_github_url(
            attrs["upstream_repo"], attrs["commit"], attrs["source_path"]
        )
        out_path = RAW_DIR / attrs["filename"]
        if out_path.exists() and not args.force:
            data = out_path.read_bytes()
            status = "cached"
            logger.info(f"Using cached {key}: {out_path}")
        else:
            logger.info(f"Downloading {key}: {url}")
            data = _download(url, args.timeout)
            status = "downloaded"

        actual_sha256 = _sha256(data)
        expected_sha256 = attrs["sha256"]
        if actual_sha256 != expected_sha256:
            raise ValueError(
                f"{key}: SHA256 mismatch: expected {expected_sha256}, "
                f"got {actual_sha256}. File not accepted."
            )
        expected_rows = attrs.get("rows")
        actual_rows = _row_count(data)
        if expected_rows is not None and actual_rows != int(expected_rows):
            raise ValueError(
                f"{key}: row-count mismatch: expected {expected_rows}, got {actual_rows}"
            )
        if status == "downloaded":
            temporary_path = out_path.with_suffix(out_path.suffix + ".tmp")
            temporary_path.write_bytes(data)
            temporary_path.replace(out_path)

        manifest["sources"][key] = {
            "upstream_repo": attrs.get("upstream_repo", ""),
            "upstream_commit": attrs["commit"],
            "source_path": attrs["source_path"],
            "immutable_url": url,
            "description": attrs.get("description", ""),
            "path": str(out_path.relative_to(ROOT)),
            "bytes": len(data),
            "rows_excluding_header": actual_rows,
            "sha256": actual_sha256,
            "expected_sha256": expected_sha256,
            "checksum_verified": True,
            "status": status,
        }

    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    logger.info(f"Wrote manifest: {MANIFEST_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
