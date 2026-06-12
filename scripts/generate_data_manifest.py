#!/usr/bin/env python3
"""Generate aggregate validation manifest for key datasets.

Raw row-level data stays out of git; this manifest records what an advisor
or reviewer needs to verify the analysis without the rows themselves:
row counts, column schemas, file hashes, and generation timestamps for
every dataset and headline artifact in the pipeline.

Output:
  output/data_manifest.json  (machine-readable)
  output/data_manifest.md    (human-readable table)

Usage:
    python scripts/generate_data_manifest.py
    make data-manifest
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_JSON = ROOT / "output" / "data_manifest.json"
OUT_MD = ROOT / "output" / "data_manifest.md"

# Key artifacts in the analytical chain. Globs allowed.
TRACKED = [
    "output/checkpoints/*.json",
    "output/official_fukui/*.csv",
    "output/hokuriku_merged/*.csv",
    "output/friction_analysis/*.csv",
    "output/multilingual_review_analysis/*.csv",
    "output/chinese_social_media_analysis/*.csv",
    "output/cross_language_trends/*.csv",
    "output/gold_set/*.csv",
    "output/national_stats/*.csv",
]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _describe_csv(path: Path) -> dict:
    with open(path, newline="", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.reader(f)
        header = next(reader, [])
        rows = sum(1 for _ in reader)
    return {"rows": rows, "columns": header}


def _describe_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {"rows": None, "columns": None, "note": "unparseable JSON"}
    if isinstance(data, dict):
        return {"rows": len(data), "columns": None, "note": "top-level keys counted as rows"}
    if isinstance(data, list):
        return {"rows": len(data), "columns": None}
    return {"rows": None, "columns": None}


def build_manifest() -> dict:
    entries = []
    for pattern in TRACKED:
        for path in sorted(ROOT.glob(pattern)):
            if not path.is_file() or ".bak-" in path.name:
                continue
            stat = path.stat()
            entry = {
                "path": str(path.relative_to(ROOT)),
                "bytes": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                "sha256": _sha256(path),
            }
            if path.suffix == ".csv":
                entry.update(_describe_csv(path))
            elif path.suffix == ".json":
                entry.update(_describe_json(path))
            entries.append(entry)
    return {
        "generated": datetime.now(tz=timezone.utc).isoformat(),
        "n_files": len(entries),
        "files": entries,
    }


def write_markdown(manifest: dict) -> str:
    lines = [
        "# Data Manifest — aggregate validation artifacts",
        "",
        f"Generated {manifest['generated']} by `scripts/generate_data_manifest.py` "
        "(`make data-manifest`). Row-level data stays local; this records row "
        "counts, schemas, and hashes so results can be audited without the rows.",
        "",
        "| File | Rows | Cols | Bytes | sha256 (12) | Modified |",
        "|---|---|---|---|---|---|",
    ]
    for e in manifest["files"]:
        cols = len(e["columns"]) if e.get("columns") else ""
        lines.append(
            f"| {e['path']} | {e.get('rows', '')} | {cols} | {e['bytes']} "
            f"| {e['sha256'][:12]} | {e['modified'][:10]} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    manifest = build_manifest()
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    OUT_MD.write_text(write_markdown(manifest), encoding="utf-8")
    print(f"Wrote {OUT_JSON.relative_to(ROOT)} and {OUT_MD.relative_to(ROOT)} "
          f"({manifest['n_files']} files described)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
