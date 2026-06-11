#!/usr/bin/env python3
"""
evaluate_gold_set.py — Score the keyword friction tagger against the human gold set.

ROLE IN THE VALIDATION PIPELINE
-------------------------------
This is the second half of the gold-standard validation built by
`scripts/build_gold_set.py`. Once both coders have completed their blind
sheets, this script (1) quantifies how reliable the human labels themselves
are (inter-rater reliability, Cohen's kappa), (2) constructs the gold labels
from coder consensus, and (3) scores the keyword tagger's machine labels
against that gold standard (per-code precision / recall / F1 with Wilson
confidence intervals). The resulting numbers bound the validity of every
downstream friction analysis (SEM Stage 2, prefecture comparisons, nudge
ranking) and are reported in the thesis methods chapter.

STATISTICAL CHOICES (rationale)
-------------------------------
Cohen's kappa (κ), not raw % agreement:
  κ is chance-corrected agreement. With rare codes, two coders who both label
  almost every row 0 will show very high *raw* percent agreement purely by
  chance — the statistic is inflated by the skewed marginal prevalence. κ
  subtracts the agreement expected under independent labeling with each
  coder's observed marginals. κ is computed PER CODE (not pooled) precisely
  because marginal prevalence differs wildly across codes; a pooled statistic
  would be dominated by the common codes and hide unreliable rare ones.

Gold = consensus rows only:
  A row enters the gold set only where both coders agree on every friction
  code. Disagreeing rows are exported to disagreements.csv for explicit human
  adjudication rather than being resolved by majority vote — with exactly two
  coders there IS no majority, so any automatic tie-break would silently
  privilege one coder. Excluding disagreements keeps the gold labels honest
  at the cost of a slightly smaller n.

Wilson score interval, not Wald:
  The textbook Wald interval (p ± z·sqrt(p(1-p)/n)) collapses to zero width
  when p is exactly 0 or 1 and is badly mis-calibrated at small n — which is
  *exactly* the regime here (per-code evaluable counts of roughly 15–25, with
  precision often near 1). The Wilson score interval remains well-behaved in
  that regime and never escapes [0, 1].

indicative_only flag:
  Any code with fewer than 20 evaluable instances (for either the precision
  or the recall denominator) is flagged. The flag instructs the thesis text
  to cite the Wilson CI for that code rather than the point estimate, which
  at such small n is too unstable to stand alone.

Precision / recall / F1, not accuracy:
  The label matrix is extremely class-imbalanced — most rows do NOT carry
  most codes — so accuracy is dominated by trivially correct negatives and
  would look excellent even for a useless tagger. Per-code precision (of
  machine positives, fraction the humans confirm), recall (of human
  positives, fraction the machine found), and their harmonic mean F1 are the
  informative quantities. NOTE: recall here is within the sampled strata,
  not corpus-wide (see build_gold_set.py and thesis methods on prevalence
  weighting).

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
    """Cohen's kappa (κ) for two binary label vectors.

    κ = (p_o − p_e) / (1 − p_e), where
      p_o = observed agreement (fraction of rows the coders label identically)
      p_e = agreement expected by CHANCE given each coder's marginal positive
            rate: P(both say 1) + P(both say 0) under independence.

    Why chance correction matters here: friction codes are rare, so two coders
    answering 0 almost everywhere agree at a very high raw rate by chance
    alone. Raw percent agreement is therefore inflated for rare codes; κ
    removes that inflation. This is also why κ is computed per code — the
    marginal prevalence (and hence p_e) differs wildly between codes.

    Degenerate case: if both coders are unanimous (p_e == 1), κ is undefined
    (0/0); NaN is returned and should be read as "no variation to assess",
    not as zero reliability.
    """
    po = float((a == b).mean())
    pa, pb = float(a.mean()), float(b.mean())
    pe = pa * pb + (1 - pa) * (1 - pb)
    if pe == 1.0:
        return float("nan")
    return (po - pe) / (1 - pe)


def load_coder(path: Path, codes: list) -> pd.DataFrame:
    """Load a completed coder sheet, coercing labels to clean binary {0, 1}.

    Coders fill sheets by hand, so cells may be blank, '1', 1, or stray text;
    pd.to_numeric(..., errors='coerce') maps anything non-numeric to NaN,
    which is then treated as 0 ("code does not apply"), and clip(0, 1)
    flattens accidental values like 2 down to 1. Indexed by gold_id so coder
    sheets align with the key file regardless of row order.
    """
    df = pd.read_csv(path)
    for col in codes + ["no_friction"]:
        df[col] = (
            pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int).clip(0, 1)
        )
    return df.set_index("gold_id")


def wilson_ci(successes: int, total: int, z: float = 1.96) -> tuple:
    """Wilson score interval for a binomial proportion — sane for the small
    per-code counts here.

    Chosen over the textbook Wald interval (p ± z·sqrt(p(1−p)/n)) because Wald
    degenerates exactly in this study's regime: per-code evaluable counts are
    tiny (~15–25) and observed proportions sit near 0 or 1 (e.g. precision of
    14/15), where Wald collapses to zero width or spills outside [0, 1]. The
    Wilson interval inverts the score test instead, stays inside [0, 1] by
    construction (the min/max below only guards floating-point edge cases),
    and retains close-to-nominal coverage at small n. z = 1.96 gives the
    conventional 95% interval. Returns (NaN, NaN) when there are no evaluable
    instances at all.
    """
    if total == 0:
        return (float("nan"), float("nan"))
    p = successes / total
    denom = 1 + z**2 / total
    centre = (p + z**2 / (2 * total)) / denom
    half = z * np.sqrt(p * (1 - p) / total + z**2 / (4 * total**2)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def prf(machine: pd.Series, gold: pd.Series) -> tuple:
    """Per-code confusion counts and precision / recall / F1 vs the gold labels.

    Definitions (treating the human gold label as ground truth):
      tp — machine tagged the code AND humans agree (true positive)
      fp — machine tagged the code but humans disagree (false positive)
      fn — humans saw the friction but the machine missed it (false negative)
      precision = tp / (tp + fp): of the machine's positives, the human-
                  confirmed fraction. Low precision means downstream friction
                  counts are inflated by spurious tags.
      recall    = tp / (tp + fn): of human-identified positives, the fraction
                  the machine found. Low recall means friction is silently
                  undercounted. (Within sampled strata only — see module
                  docstring re: prevalence weighting for corpus-wide recall.)
      f1        = harmonic mean of the two, a single balance figure.

    Accuracy is deliberately NOT reported: with extreme class imbalance (most
    rows lack most codes), true negatives dominate and accuracy would look
    near-perfect for even a useless tagger. NaN is returned for any ratio
    whose denominator is zero (no evaluable instances) rather than faking 0
    or 1.
    """
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

        # A row counts as a disagreement if the coders differ on ANY friction
        # code. These rows are exported side-by-side (A_<code> / B_<code>) for
        # explicit human adjudication. They are NOT resolved by majority vote:
        # with exactly two coders there is no majority, and any automatic
        # tie-break (e.g. "trust coder A") would silently bias the gold set.
        mismatch_mask = (coder_a.loc[ids, codes] != coder_b.loc[ids, codes]).any(axis=1)
        disagreements = pd.DataFrame({
            "gold_id": ids[mismatch_mask],
            "text": key.loc[ids[mismatch_mask], "friction_source_text"],
        })
        for code in codes:
            disagreements[f"A_{code}"] = coder_a.loc[ids[mismatch_mask], code].values
            disagreements[f"B_{code}"] = coder_b.loc[ids[mismatch_mask], code].values
        disagreements.to_csv(gold_dir / "disagreements.csv", index=False)

        # Gold = consensus rows only. Where both coders agree on every code,
        # either coder's labels ARE the gold labels (coder_a is used purely
        # for convenience — by construction the values are identical).
        # Disagreeing rows stay out of the gold set until adjudicated and the
        # evaluation is re-run, keeping the ground truth strictly
        # human-validated.
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

    # --- Score the keyword tagger against the gold labels, per code ----------
    # Wilson CIs accompany every precision/recall point estimate because the
    # per-code denominators are small (~15-25); the indicative_only flag
    # (either denominator < 20) tells the thesis text to cite the CI rather
    # than the point estimate for that code.
    eval_rows = []
    for code in codes:
        machine = key.loc[gold.index, code]
        tp, fp, fn, p, r, f1 = prf(machine, gold[code])
        p_ci = wilson_ci(tp, tp + fp)
        r_ci = wilson_ci(tp, tp + fn)
        eval_rows.append({
            "code": code, "gold_positives": int(gold[code].sum()),
            "tp": tp, "fp": fp, "fn": fn,
            "precision": p, "precision_ci_low": p_ci[0], "precision_ci_high": p_ci[1],
            "recall": r, "recall_ci_low": r_ci[0], "recall_ci_high": r_ci[1],
            "f1": f1,
            "indicative_only": bool((tp + fp) < 20 or (tp + fn) < 20),
        })
    # ANY_FRICTION row: did the tagger detect *some* friction when the humans
    # did, regardless of which code? This coarser binary backs analyses that
    # only use the presence/absence of friction (e.g. friction-rate
    # comparisons) and is more robust than any single code at small n.
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
        "Codes flagged indicative_only have <20 evaluable instances — report their",
        "Wilson CIs rather than point estimates.",
    ]
    (gold_dir / "gold_set_report.md").write_text("\n".join(report), encoding="utf-8")
    logger.info(f"Wrote evaluation outputs to {gold_dir}")
    print("\n".join(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
