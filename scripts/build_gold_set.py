#!/usr/bin/env python3
"""
build_gold_set.py — Build a blind, stratified gold-standard labeling kit for the
Japanese friction tagger.

WHY THIS SCRIPT EXISTS (methodological motivation)
--------------------------------------------------
Every downstream quantitative result in the thesis — the SEM Stage 2 friction
constructs, the prefecture-level friction comparisons, and the ranking of nudge
candidates — is conditioned on the output of the keyword friction tagger. If
the tagger systematically over- or under-detects friction (誤判定 / 見逃し), every
one of those analyses inherits that error: garbage in, garbage out. An
*unevaluated* tagger is therefore an unbounded validity risk. The remedy is a
gold standard (正解データ / ゴールドセット): a hand-labeled sample of survey
free-text responses, coded independently by two human coders, against which the
machine tags can be scored (precision / recall per code, with inter-rater
reliability establishing that the human labels themselves are trustworthy).
This script builds the *labeling kit* for that gold standard; the companion
script `scripts/evaluate_gold_set.py` consumes the completed sheets.

STRATIFIED SAMPLING DESIGN
--------------------------
The sample is drawn in two kinds of strata, each targeting a different error
mode of the tagger:

  positive_<code>  : rows the keyword tagger assigned friction code <code>.
                     ~15 rows per code (configurable via --per-code). These
                     rows estimate per-code PRECISION (適合率): of the rows the
                     machine tagged with <code>, how many does a human agree
                     actually describe that friction? Sampling positives per
                     code (rather than a simple random sample of the corpus)
                     guarantees every code — including rare ones — gets enough
                     positive instances to be evaluable at all.

  untagged_text    : rows that contain free text but received NO machine code
                     (~120 rows, configurable via --untagged). These rows probe
                     FALSE NEGATIVES, i.e. RECALL (再現率): friction the
                     keyword system silently missed. Without this stratum, the
                     evaluation could only ever confirm what the tagger found,
                     never what it overlooked.

IMPORTANT CAVEAT ON RECALL: because the sample is stratified rather than a
simple random draw, recall computed from these rows is estimated *within the
sampled strata*, NOT corpus-wide. A corpus-wide recall estimate requires
re-weighting each stratum by its prevalence in the full corpus (prevalence
weighting); that adjustment is documented in the thesis methods chapter and is
deliberately NOT performed here, so the raw stratum-level numbers remain
transparent and auditable.

BLINDNESS (coder-sheet design)
------------------------------
The coder sheets deliberately EXCLUDE the machine tags and the stratum labels,
and the rows are shuffled (seed + 1) so that coders cannot reconstruct strata
from row ordering (e.g. "the first 15 rows are all transport complaints, so
the machine must have tagged them transport"). If coders could see — or
infer — the machine's answer, their labels would be anchored toward it
(anchoring bias), and the evaluation would degenerate into measuring agreement
with the machine rather than measuring the machine against independent human
judgment. This kit SUPERSEDES the earlier
`japanese_friction_validation_sample.csv`, which exposed the machine tags
in-sheet and is therefore unusable as an unbiased gold standard.

The machine tags and strata live only in `gold_set_key.csv`, which must NOT be
shown to coders; it is re-joined to the human labels at evaluation time.

DOUBLE-CODING AND REPRODUCIBILITY
---------------------------------
Both coders receive byte-identical sheets (coder_A / coder_B), enabling full
double-coding of every row and hence per-code Cohen's kappa (κ) as the
inter-rater reliability statistic. A fixed default random seed (42) makes the
entire sample reproducible: re-running this script with the same inputs and
arguments regenerates exactly the same kit, which matters for thesis
traceability (an examiner can reconstruct the sample).

PRACTICAL DESIGN CHOICES
------------------------
- MAX_TEXT_CHARS = 600 trims pathological, very long responses. Long texts
  multiply coder reading time without adding per-code signal; the cap keeps
  total coder burden in the ~2–3 hour range per coder.
- Deduplication on the exact text string prevents the same (possibly viral /
  boilerplate) phrasing from appearing twice and being double-counted.

OUTPUTS
-------
  output/gold_set/gold_set_key.csv        — master file with machine tags + strata
                                            (do NOT give to coders)
  output/gold_set/gold_set_coder_A.csv    — blind coder sheet (shuffled, no tags)
  output/gold_set/gold_set_coder_B.csv    — identical blind sheet for second coder
  output/gold_set/CODING_GUIDE.md         — code definitions for coders

Strata:
  positive_<code>   : rows the keyword tagger assigned <code> (precision estimate)
  untagged_text     : rows with free text but no machine code (false-negative probe)

Usage:
    python scripts/build_gold_set.py --per-code 15 --untagged 120 --seed 42
"""

import argparse
import sys
from pathlib import Path

import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.official_fukui.ftas import load_japanese_codebook
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

ROOT = Path(__file__).resolve().parent.parent
COMBINED_CSV = ROOT / "output" / "official_fukui" / "official_surveys_tagged_combined.csv"
CODEBOOK_PATH = ROOT / "config" / "official_japanese_friction_codebook.yaml"
GOLD_DIR = ROOT / "output" / "gold_set"

# Cap on response length included in the kit. Pathologically long free-text
# responses (essays, copy-pasted itineraries) inflate coder reading time far
# faster than they add per-code labeling signal; trimming them keeps total
# coder burden at roughly 2-3 hours per coder for the default sample size.
# Rows above the cap are EXCLUDED from the sampling frame (not truncated), so
# coders never label partial text.
MAX_TEXT_CHARS = 600  # very long responses slow coders without adding signal


def build_coding_guide(codebook_raw: dict, codes: list) -> str:
    """Render CODING_GUIDE.md — the bilingual (EN/JA) instructions for coders.

    The guide instructs coders to judge what the respondent *experienced*, not
    the surface keywords used. This is the crux of the validation: if coders
    simply pattern-matched keywords, their labels would trivially agree with
    the keyword tagger and the evaluation would be circular. The guide shows a
    few example keywords (例) per code purely to anchor the code's *meaning*,
    not as a matching rule.
    """
    lines = [
        "# Friction Coding Guide / フリクション・コーディングガイド",
        "",
        "Read each survey free-text response and mark **1** in every friction code",
        "column that applies (multiple codes allowed). If no friction is described,",
        "mark **1** in `no_friction`. Use `notes` for anything ambiguous.",
        "",
        "各自由記述を読み、当てはまるフリクションコードの列すべてに **1** を記入して",
        "ください（複数可）。フリクションが書かれていない場合は `no_friction` に **1**。",
        "迷った場合は `notes` にメモしてください。",
        "",
        "Judge what the respondent **experienced**, not the keywords used — the point",
        "of this exercise is to check the keyword system against human judgment, so do",
        "not try to guess what a machine would do.",
        "",
        "| Code | Label | 説明の目安 |",
        "|------|-------|-----------|",
    ]
    for code in codes:
        entry = codebook_raw["friction_codes"][code]
        examples = "、".join(entry.get("keywords", [])[:4])
        lines.append(f"| `{code}` | {entry.get('label', code)} | 例: {examples}… |")
    lines += [
        "",
        "Notes:",
        "- A complaint can carry several codes (e.g. 「駅から遠いしバスも少ない」 →",
        "  `transport_access` only; 「案内も分かりにくい」が加われば `wayfinding_signage` も).",
        "- Positive comments, suggestions with no experienced problem, and empty",
        "  pleasantries are `no_friction`.",
        "- Suggestions that imply an experienced gap (「飲食店が少ないので増やしてほしい」)",
        "  DO count as friction (`food_amenities_gap`).",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build blind gold-set labeling kit")
    parser.add_argument("--per-code", type=int, default=15, help="Positive rows per friction code")
    parser.add_argument("--untagged", type=int, default=120, help="Untagged free-text rows")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    if not COMBINED_CSV.exists():
        raise FileNotFoundError(f"Missing input: {COMBINED_CSV}. Run make official-all first.")

    codebook = load_japanese_codebook(CODEBOOK_PATH)
    codes = list(codebook.keys())
    with open(CODEBOOK_PATH, encoding="utf-8") as fh:
        codebook_raw = yaml.safe_load(fh)

    # --- Build the sampling frame -------------------------------------------
    # Restrict to rows with non-empty free text (only those are codable),
    # drop over-length responses (see MAX_TEXT_CHARS rationale above), and
    # deduplicate on the exact text string so the same viral/boilerplate
    # phrasing cannot enter the gold set twice and be double-counted in the
    # precision/recall estimates.
    df = pd.read_csv(COMBINED_CSV, low_memory=False)
    df["friction_source_text"] = df["friction_source_text"].fillna("").astype(str).str.strip()
    df = df[df["friction_source_text"].ne("")].copy()
    df = df[df["friction_source_text"].str.len() <= MAX_TEXT_CHARS]
    df = df.drop_duplicates(subset=["friction_source_text"])

    # --- Stratum 1: machine-positive rows per code (precision estimate) ------
    # For each friction code, sample up to --per-code rows that the keyword
    # tagger flagged with that code. Sampling per code (rather than from the
    # corpus at large) guarantees that rare codes still receive enough
    # positive instances to estimate per-code PRECISION at all. The fixed
    # random_state (--seed, default 42) makes the draw fully reproducible.
    parts = []
    for code in codes:
        hits = df[df[code].astype(bool)]
        if hits.empty:
            logger.warning(f"No rows for code {code}")
            continue
        sampled = hits.sample(n=min(args.per_code, len(hits)), random_state=args.seed)
        sampled = sampled.assign(stratum=f"positive_{code}")
        parts.append(sampled)

    # --- Stratum 2: untagged-with-text rows (false-negative / recall probe) --
    # Rows containing free text but NO machine friction code. Human labels on
    # these rows reveal friction the keyword system missed (false negatives).
    # Note: recall derived from this stratum is a within-strata estimate, not
    # corpus-wide recall — corpus-wide recall requires prevalence weighting,
    # documented in the thesis methods chapter.
    untagged = df[~df["any_friction"].astype(bool)]
    parts.append(
        untagged.sample(n=min(args.untagged, len(untagged)), random_state=args.seed)
        .assign(stratum="untagged_text")
    )

    # A row tagged with several codes can be drawn into several positive
    # strata; the second dedup keeps each text exactly once in the kit.
    sample = pd.concat(parts, ignore_index=True).drop_duplicates(subset=["friction_source_text"])
    # Shuffle so coders cannot infer strata from ordering (blindness): without
    # this, contiguous runs of same-code rows would leak the machine's answer
    # and anchor the coders toward it. seed + 1 is used (rather than the
    # sampling seed itself) so the shuffle permutation is independent of the
    # stratum draws while remaining deterministic/reproducible.
    sample = sample.sample(frac=1.0, random_state=args.seed + 1).reset_index(drop=True)
    sample.insert(0, "gold_id", [f"gold_{i:04d}" for i in range(1, len(sample) + 1)])

    GOLD_DIR.mkdir(parents=True, exist_ok=True)

    # --- Key file (researcher-only) ------------------------------------------
    # The key retains the machine tags and stratum labels needed at evaluation
    # time. It must NEVER be distributed to coders — doing so would break
    # blindness and reintroduce the anchoring flaw of the superseded
    # japanese_friction_validation_sample.csv.
    key_cols = ["gold_id", "stratum", "survey_prefecture", "response_area",
                "friction_source_text", "friction_codes"] + codes
    key = sample[[c for c in key_cols if c in sample.columns]]
    key.to_csv(GOLD_DIR / "gold_set_key.csv", index=False)

    # --- Blind coder sheets ---------------------------------------------------
    # Only gold_id + raw text are carried over; machine tags and strata are
    # withheld. Code columns are emptied for the coder to fill (1 = applies).
    # Both coders receive byte-identical sheets so every row is double-coded,
    # which is what makes per-code Cohen's kappa computable downstream.
    coder = sample[["gold_id", "friction_source_text"]].rename(
        columns={"friction_source_text": "text"}
    )
    for code in codes:
        coder[code] = ""
    coder["no_friction"] = ""
    coder["notes"] = ""
    for name in ("A", "B"):
        coder.to_csv(GOLD_DIR / f"gold_set_coder_{name}.csv", index=False)

    (GOLD_DIR / "CODING_GUIDE.md").write_text(
        build_coding_guide(codebook_raw, codes), encoding="utf-8"
    )

    counts = sample["stratum"].value_counts()
    logger.info(f"Gold set: {len(sample)} rows -> {GOLD_DIR}")
    logger.info(f"Strata:\n{counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
