#!/usr/bin/env python3
"""Fetch immutable japan-kanko-stat municipal CSVs with checksum gates."""

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config" / "national_data_sources.yaml"
RAW = ROOT / "output" / "national_stats" / "japan_kanko_stat" / "raw"
MANIFEST = ROOT / "output" / "national_stats" / "japan_kanko_stat_manifest.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args()
    spec = yaml.safe_load(CONFIG.read_text())["japan_kanko_stat"]
    slug = spec["repo"].removeprefix("https://github.com/")
    RAW.mkdir(parents=True, exist_ok=True)
    manifest = {"fetched_at_utc": datetime.now(timezone.utc).isoformat(), "sources": {}}
    for item in spec["files"]:
        name = Path(item["path"]).name
        target = RAW / name
        url = f"https://raw.githubusercontent.com/{slug}/{spec['commit']}/{item['path']}"
        data = target.read_bytes() if target.exists() and not args.force else urlopen(url, timeout=args.timeout).read()
        digest = hashlib.sha256(data).hexdigest()
        if digest != item["sha256"]:
            raise ValueError(f"{name}: SHA256 mismatch: {digest}")
        rows = max(sum(1 for _ in csv.reader(data.decode("utf-8-sig").splitlines())) - 1, 0)
        if rows != item["rows"]:
            raise ValueError(f"{name}: expected {item['rows']} rows, got {rows}")
        target.write_bytes(data)
        manifest["sources"][name] = {"url": url, "sha256": digest, "rows": rows}
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
