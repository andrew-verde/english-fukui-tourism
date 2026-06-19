#!/usr/bin/env python3
"""Build paper-facing statistical claim registry from generated artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.provenance.claim_registry import ROOT, build_registry, write_markdown


OUT_JSON = ROOT / "output" / "claim_registry.json"
OUT_MD = ROOT / "output" / "claim_registry.md"


def main() -> int:
    registry = build_registry()
    OUT_JSON.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_MD.write_text(write_markdown(registry), encoding="utf-8")
    print(f"Wrote {OUT_JSON.relative_to(ROOT)} and {OUT_MD.relative_to(ROOT)}")
    if not registry["publication_ready"]:
        print("Publication ready: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
