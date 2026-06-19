#!/usr/bin/env python3
"""Fail final defense/publish runs when critical validation is incomplete."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.provenance.gold_set import require_gold_set_complete
from src.provenance.claim_registry import build_registry


def main() -> int:
    try:
        require_gold_set_complete()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    registry = build_registry()
    if not registry["publication_ready"]:
        print("Claim registry is not publication-ready.", file=sys.stderr)
        return 1
    print("Publication readiness checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
