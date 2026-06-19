import csv
from pathlib import Path

import pytest

from src.provenance.gold_set import get_gold_set_status, require_gold_set_complete


def test_gold_set_pending_when_coder_sheets_exist_without_evaluation(tmp_path: Path):
    gold_dir = tmp_path / "output" / "gold_set"
    gold_dir.mkdir(parents=True)
    (gold_dir / "gold_set_coder_A.csv").write_text("gold_id,friction_source_text\n", encoding="utf-8")

    status = get_gold_set_status(tmp_path)

    assert not status.complete
    assert "coder sheets exist" in status.reason
    assert "native-speaker gold-set review" in status.caveat


def test_gold_set_complete_requires_evaluation_and_report(tmp_path: Path):
    gold_dir = tmp_path / "output" / "gold_set"
    gold_dir.mkdir(parents=True)
    with (gold_dir / "tagger_evaluation.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "code",
                "gold_positives",
                "true_positive",
                "false_positive",
                "false_negative",
                "precision",
                "recall",
                "f1",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "code": "ANY_FRICTION",
                "gold_positives": 1,
                "true_positive": 1,
                "false_positive": 0,
                "false_negative": 0,
                "precision": 1.0,
                "recall": 1.0,
                "f1": 1.0,
            }
        )
    (gold_dir / "gold_set_report.md").write_text("# Gold-set evaluation report\n", encoding="utf-8")

    status = get_gold_set_status(tmp_path)

    assert status.complete
    assert status.caveat == ""


def test_publication_gate_fails_while_gold_set_pending(tmp_path: Path):
    with pytest.raises(RuntimeError, match="Gold-set review incomplete"):
        require_gold_set_complete(tmp_path)
