"""Backup-and-shrink guard for scrape checkpoint writes.

Every fetch run rewrites its checkpoint JSON in place. A failed or partial
API run must never silently replace a good checkpoint with an empty or
much smaller one — that destroys data we cannot re-fetch (review APIs are
paginated, rate-limited, and reviews get deleted upstream). Policy:

1. Before any overwrite, copy the existing file to
   ``<name>.bak-YYYYmmddHHMMSS`` next to it (kept, never auto-pruned).
2. Refuse the write if the new payload serializes to empty, or to less
   than ``SHRINK_RATIO`` of the existing file's size. The 50% threshold is
   deliberately loose: legitimate runs only append POIs/reviews, so any
   real shrink that large means a broken run, not new data.
3. Override only via ``FUKUI_ALLOW_SHRINK=1`` (explicit human review).
"""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime
from pathlib import Path

SHRINK_RATIO = 0.5
OVERRIDE_ENV = "FUKUI_ALLOW_SHRINK"


class ShrinkRefusedError(RuntimeError):
    pass


def backup_existing(path: Path) -> Path | None:
    """Copy ``path`` to a timestamped .bak sibling. Returns backup path."""
    if not path.exists():
        return None
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    backup = path.with_name(f"{path.name}.bak-{stamp}")
    shutil.copy2(path, backup)
    return backup


def guarded_save_json(path: Path, data, **json_kwargs) -> None:
    """Write JSON with backup + shrink refusal. Drop-in for naive _save()."""
    payload = json.dumps(data, indent=2, **json_kwargs)
    if path.exists():
        old_size = path.stat().st_size
        empty = not data
        shrunk = old_size > 0 and len(payload.encode("utf-8")) < old_size * SHRINK_RATIO
        if (empty or shrunk) and os.environ.get(OVERRIDE_ENV) != "1":
            raise ShrinkRefusedError(
                f"Refusing to overwrite {path} ({old_size} bytes) with "
                f"{'empty' if empty else 'much smaller'} payload "
                f"({len(payload.encode('utf-8'))} bytes). Existing data kept. "
                f"Set {OVERRIDE_ENV}=1 to override after manual review."
            )
        backup_existing(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(payload, encoding="utf-8")
    tmp.replace(path)
