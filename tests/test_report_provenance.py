"""Provenance guards for outward-facing documents and scrape checkpoints.

Two failure modes these tests block:

1. A report claims significance ("statistically significant", "p <",
   "% visitor increase") in a document that never points at a script or
   make target — i.e. a number with no reproduction path.
2. A fetch run overwrites a good checkpoint with an empty or much smaller
   payload (scripts/checkpoint_guard.py policy).
"""

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.checkpoint_guard import ShrinkRefusedError, guarded_save_json

SIGNIFICANCE_PHRASES = [
    re.compile(r"statistically significant", re.IGNORECASE),
    re.compile(r"\bp\s*[<=]\s*0?\.\d"),
    re.compile(r"%\s*(visitor|tourist)\s+increase", re.IGNORECASE),
]
# A document making statistical claims must name its reproduction path.
PROVENANCE_MARKERS = [re.compile(r"\bmake [a-z][a-z0-9_-]+"), re.compile(r"scripts/[a-z_]+\.py")]

OUTWARD_DOCS = sorted((ROOT / "docs").glob("**/*.md")) + [ROOT / "README.md"]


@pytest.mark.parametrize("doc", OUTWARD_DOCS, ids=lambda p: str(p.relative_to(ROOT)))
def test_significance_claims_have_reproduction_path(doc):
    if not doc.exists():
        pytest.skip("absent")
    text = doc.read_text(encoding="utf-8")
    claims = [p.pattern for p in SIGNIFICANCE_PHRASES if p.search(text)]
    if not claims:
        return
    assert any(m.search(text) for m in PROVENANCE_MARKERS), (
        f"{doc.relative_to(ROOT)} makes statistical claims ({claims}) but cites "
        "no make target or script path. Add the reproduction command and a "
        "row in docs/source_ledger.md."
    )


def test_source_ledger_exists_and_covers_headlines():
    ledger = (ROOT / "docs" / "source_ledger.md").read_text(encoding="utf-8")
    for required in ["hokuriku-did-event-study", "sem-ftas", "nudge-ranking"]:
        assert required in ledger, f"source ledger missing primary analysis: {required}"
    # Demo data must stay explicitly quarantined.
    assert "simulated/demo" in ledger


def test_guard_refuses_empty_overwrite(tmp_path):
    path = tmp_path / "ckpt.json"
    guarded_save_json(path, {"poi": [1, 2, 3]})
    with pytest.raises(ShrinkRefusedError):
        guarded_save_json(path, {})
    # Original data intact.
    assert json.loads(path.read_text()) == {"poi": [1, 2, 3]}


def test_guard_refuses_large_shrink(tmp_path):
    path = tmp_path / "ckpt.json"
    guarded_save_json(path, {f"poi{i}": list(range(50)) for i in range(20)})
    with pytest.raises(ShrinkRefusedError):
        guarded_save_json(path, {"poi0": [1]})


def test_guard_allows_growth_and_backs_up(tmp_path):
    path = tmp_path / "ckpt.json"
    guarded_save_json(path, {"a": [1]})
    guarded_save_json(path, {"a": [1], "b": [2, 3]})
    assert json.loads(path.read_text()) == {"a": [1], "b": [2, 3]}
    backups = list(tmp_path.glob("ckpt.json.bak-*"))
    assert len(backups) == 1
    assert json.loads(backups[0].read_text()) == {"a": [1]}


def test_guard_override_env(tmp_path, monkeypatch):
    path = tmp_path / "ckpt.json"
    guarded_save_json(path, {"a": list(range(100))})
    monkeypatch.setenv("FUKUI_ALLOW_SHRINK", "1")
    guarded_save_json(path, {"a": [1]})
    assert json.loads(path.read_text()) == {"a": [1]}
    # Backup still taken even when override is used.
    assert list(tmp_path.glob("ckpt.json.bak-*"))
