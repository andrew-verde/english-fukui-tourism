#!/usr/bin/env python3
"""
evaluate_gold_set.py — Score the keyword friction tagger against the human gold set.

Reads (from output/gold_set/):
  gold_set_key.csv              — machine tags per gold_id
  gold_set_coder_A.csv          — completed coder sheet (1 = code applies)
  gold_set_coder_B.csv          — completed second coder sheet (optional)

Writes (to output/gold_set/):
  inter_rater_reliability.csv   — per-code Cohen's kappa + agreement (if 2 coders)
  disagreements.csv             — rows needing adjudication (if 2 coders)
  tagger_evaluation.csv         — per-code precision / recall / F1 vs gold
  gold_set_report.md            — human-readable summary

Gold label = agreement of both coders; disagreements are excluded until
adjudicated (re-run after editing coder sheets, or fill disagreements.csv's
`adjudicated` column and re-run with --adjudication disagreements.csv).
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.official_fukui.ftas import load_japanese_codebook
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

ROOT = Path(__file__).resolve().parent.parent
GOLD_DIR = ROOT / "output" / "gold_set"
CODEBOOK_PATH = ROOT / "config" / "official_japanese_friction_codebook.yaml"


def cohens_kappa(a: pd.Series, b: pd.Series) -> float:
    """Cohen's kappa for two binary label vectors."""
    po = float((a == b).mean())
    pa, pb = float(a.mean()), float(b.mean())
    pe = pa * pb + (1 - pa) * (1 - pb)
    if pe == 1.0:
        return float("nan")
    return (po - pe) / (1 - pe)


def load_coder(path: Path, codes: list) -> pd.DataFrame:
    df = pd.read_csv(path)
    for col in codes + ["no_friction"]:
        df[col] = (
            pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int).clip(0, 1)
        )
    return df.set_index("gold_id")


def prf(machine: pd.Series, gold: pd.Series) -> tuple:
    tp = int(((machine == 1) & (gold == 1)).sum())
    fp = int(((machine == 1) & (gold == 0)).sum())
    fn = int(((machine == 0) & (gold == 1)).sum())
    precision = tp / (tp + fp) if tp + fp else float("nan")
    recall = tp / (tp + fn) if tp + fn else float("nan")
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision and recall and not np.isnan(precision) and not np.isnan(recall)
        else float("nan")
    )
    return tp, fp, fn, precision, recall, f1


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate friction tagger vs gold set")
    parser.add_argument("--gold-dir", type=Path, default=GOLD_DIR)
    args = parser.parse_args()
    gold_dir = args.gold_dir

    codes = list(load_japanese_codebook(CODEBOOK_PATH).keys())
    key = pd.read_csv(gold_dir / "gold_set_key.csv").set_index("gold_id")
    for code in codes:
        key[code] = key[code].astype(bool).astype(int)

    coder_a = load_coder(gold_dir / "gold_set_coder_A.csv", codes)
    path_b = gold_dir / "gold_set_coder_B.csv"
    coder_b = load_coder(path_b, codes) if path_b.exists() else None
    if coder_b is not None and coder_b[codes + ["no_friction"]].to_numpy().sum() == 0:
        logger.warning("Coder B sheet is empty — running single-coder evaluation.")
        coder_b = None

    if coder_a[codes + ["no_friction"]].to_numpy().sum() == 0:
        raise ValueError("Coder A sheet has no labels yet. Complete labeling first.")

    report = ["# Gold-set evaluation report", ""]

    if coder_b is not None:
        ids = coder_a.index.intersection(coder_b.index)
        irr_rows, disagreement_rows = [], []
        for code in codes + ["no_friction"]:
            a, b = coder_a.loc[ids, code], coder_b.loc[ids, code]
            irr_rows.append({
                "code": code,
                "kappa": cohens_kappa(a, b),
                "percent_agreement": float((a == b).mean()),
                "n": len(ids),
            })
        irr = pd.DataFrame(irr_rows)
        irr.to_csv(gold_dir / "inter_rater_reliability.csv", index=False)

        mismatch_mask = (coder_a.loc[ids, codes] != coder_b.loc[ids, codes]).any(axis=1)
        disagreements = pd.DataFrame({
            "gold_id": ids[mismatch_mask],
            "text": key.loc[ids[mismatch_mask], "friction_source_text"],
        })
        for code in codes:
            disagreements[f"A_{code}"] = coder_a.loc[ids[mismatch_mask], code].values
            disagreements[f"B_{code}"] = coder_b.loc[ids[mismatch_mask], code].values
        disagreements.to_csv(gold_dir / "disagreements.csv", index=False)

        # Gold = consensus rows only.
        consensus_ids = ids[~mismatch_mask]
        gold = coder_a.loc[consensus_ids, codes]
        report += [
            f"Double-coded rows: {len(ids)}; consensus: {len(consensus_ids)}; "
            f"disagreements pending adjudication: {int(mismatch_mask.sum())}",
            "",
            "## Inter-rater reliability (Cohen's kappa)",
            "```\n" + irr.to_string(index=False, float_format=lambda v: f"{v:.3f}") + "\n```",
            "",
        ]
    else:
        gold = coder_a[codes]
        report += [f"Single coder, {len(gold)} rows (no kappa available).", ""]

    eval_rows = []
    for code in codes:
        machine = key.loc[gold.index, code]
        tp, fp, fn, p, r, f1 = prf(machine, gold[code])
        eval_rows.append({
            "code": code, "gold_positives": int(gold[code].sum()),
            "tp": tp, "fp": fp, "fn": fn,
            "precision": p, "recall": r, "f1": f1,
        })
    machine_any = key.loc[gold.index, codes].max(axis=1)
    gold_any = gold.max(axis=1)
    tp, fp, fn, p, r, f1 = prf(machine_any, gold_any)
    eval_rows.append({
        "code": "ANY_FRICTION", "gold_positives": int(gold_any.sum()),
        "tp": tp, "fp": fp, "fn": fn, "precision": p, "recall": r, "f1": f1,
    })
    evaluation = pd.DataFrame(eval_rows)
    evaluation.to_csv(gold_dir / "tagger_evaluation.csv", index=False)

    report += [
        "## Keyword tagger vs gold labels",
        "```\n" + evaluation.to_string(index=False, float_format=lambda v: f"{v:.3f}") + "\n```",
        "",
        "Note: recall is estimated within the sampled strata (per-code positives +",
        "untagged probe), not corpus-wide; see thesis methods for prevalence weighting.",
    ]
    (gold_dir / "gold_set_report.md").write_text("\n".join(report), encoding="utf-8")
    logger.info(f"Wrote evaluation outputs to {gold_dir}")
    print("\n".join(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
