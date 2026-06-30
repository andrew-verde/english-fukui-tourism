"""Provenance guards for outward-facing documents."""

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

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
