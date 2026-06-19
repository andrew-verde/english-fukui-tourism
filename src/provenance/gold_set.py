from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent

REQUIRED_EVALUATION_COLUMNS = {
    "code",
    "gold_positives",
    "true_positive",
    "false_positive",
    "false_negative",
    "precision",
    "recall",
    "f1",
}

PENDING_CAVEAT = (
    "Japanese friction tags are keyword-derived and still await native-speaker "
    "gold-set review. Treat tag-dependent FTAS/Ishikawa code rankings, SEM "
    "Stage 2 paths, and nudge priorities as provisional until `make gold-set-eval` "
    "produces precision/recall evidence."
)


@dataclass(frozen=True)
class GoldSetStatus:
    complete: bool
    reason: str
    evaluation_csv: Path
    report_md: Path
    caveat: str


def _evaluation_columns(path: Path) -> set[str]:
    with path.open(newline="", encoding="utf-8-sig", errors="replace") as fh:
        reader = csv.reader(fh)
        return set(next(reader, []))


def get_gold_set_status(root: Path = ROOT) -> GoldSetStatus:
    gold_dir = root / "output" / "gold_set"
    evaluation_csv = gold_dir / "tagger_evaluation.csv"
    report_md = gold_dir / "gold_set_report.md"

    if not evaluation_csv.exists():
        if (gold_dir / "gold_set_coder_A.csv").exists() or (gold_dir / "gold_set_coder_B.csv").exists():
            reason = "gold-set coder sheets exist, but tagger_evaluation.csv is missing"
        elif (gold_dir / "gold_set_key.csv").exists():
            reason = "gold-set key exists, but coder sheets/evaluation are incomplete"
        else:
            reason = "gold-set artifacts are missing"
        return GoldSetStatus(False, reason, evaluation_csv, report_md, PENDING_CAVEAT)

    if evaluation_csv.stat().st_size == 0:
        return GoldSetStatus(False, "tagger_evaluation.csv is empty", evaluation_csv, report_md, PENDING_CAVEAT)

    columns = _evaluation_columns(evaluation_csv)
    missing = sorted(REQUIRED_EVALUATION_COLUMNS - columns)
    if missing:
        reason = "tagger_evaluation.csv missing columns: " + ", ".join(missing)
        return GoldSetStatus(False, reason, evaluation_csv, report_md, PENDING_CAVEAT)

    if not report_md.exists():
        reason = "tagger_evaluation.csv exists, but gold_set_report.md is missing"
        return GoldSetStatus(False, reason, evaluation_csv, report_md, PENDING_CAVEAT)

    return GoldSetStatus(True, "gold-set evaluation complete", evaluation_csv, report_md, "")


def require_gold_set_complete(root: Path = ROOT) -> None:
    status = get_gold_set_status(root)
    if not status.complete:
        raise RuntimeError(
            "Gold-set review incomplete: "
            f"{status.reason}. Run `make gold-set-eval` after native-speaker manual review "
            "before final defense/publish outputs."
        )
