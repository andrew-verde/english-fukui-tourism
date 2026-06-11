#!/usr/bin/env python3
"""
rank_nudge_priorities.py — Evidence-weighted nudge priority ranking.

The bridge between the thesis's mechanism analysis and its intervention
proposal: combines, per friction code,

  damage     — Stage 2 SEM standardized path to SATISFACTION (sem_ftas.py)
  prevalence — share of friction reporters tagged with the code
  mediation  — Stage 1 satisfaction -> intention path (common multiplier)
  intervention candidate — config/nudge_mapping.yaml

priority_score = (-min(path, 0)) * prevalence * |satisfaction->intention path|

INTERPRETATION OF THE SCORE (academic traceability)
===================================================
The score is the expected SD-units of VISIT-INTENTION damage transmitted by a
friction code per friction reporter — equivalently, the CEILING on what a
perfectly effective nudge targeting that code could recover. A real nudge
removes at most the friction it targets, so it can never recover more
intention than the friction was destroying; the score is that upper bound,
not a forecast of nudge effectiveness.

Why each factor is in the product:

* (-min(path, 0)) — the Stage 2 standardized path from the code dummy to the
  SATISFACTION latent, sign-flipped so "more damage" = larger score.
  Positive or zero paths are clipped to 0: if a code does not lower
  satisfaction, there is NOTHING for a nudge to recover, so it cannot earn
  priority no matter how prevalent it is. (Clipping rather than abs() is
  deliberate — a positive path must not masquerade as recoverable damage.)

* prevalence — the share of friction reporters tagged with the code. This is
  the aggregation step: a rare but individually damaging friction matters
  less in aggregate than a common, moderately damaging one, because policy
  acts on the population, not on a single respondent. Multiplying by
  prevalence converts per-tagged-respondent damage into expected damage per
  friction reporter.

* |satisfaction -> intention path| — the Stage 1 mediation multiplier. The
  damage estimated in Stage 2 lands on SATISFACTION; what the thesis (and
  the DMO) ultimately cares about is VISIT INTENTION. Under the mediation
  model the satisfaction damage reaches intention only through the
  satisfaction → intention path, so the product translates satisfaction
  SD-units into intention SD-units. It is a common multiplier across codes
  (it does not change the RANKING, only the units), but it is kept so the
  score is stated in the decision-relevant quantity.

Reads:  output/sem/sem_stage1_results.csv, sem_stage2_results.csv
        config/nudge_mapping.yaml
Writes: output/sem/nudge_priority_ranking.csv / .md

Usage:
    python scripts/rank_nudge_priorities.py
"""

import sys
from pathlib import Path

import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils.logger import setup_logger

logger = setup_logger(__name__)

ROOT = Path(__file__).resolve().parent.parent
SEM_DIR = ROOT / "output" / "sem"
STAGE1_CSV = SEM_DIR / "sem_stage1_results.csv"
STAGE2_CSV = SEM_DIR / "sem_stage2_results.csv"
NUDGE_MAPPING = ROOT / "config" / "nudge_mapping.yaml"
OUT_CSV = SEM_DIR / "nudge_priority_ranking.csv"
OUT_MD = SEM_DIR / "nudge_priority_ranking.md"


def main() -> int:
    for path in (STAGE1_CSV, STAGE2_CSV):
        if not path.exists():
            raise FileNotFoundError(f"Missing {path}. Run scripts/sem_ftas.py first.")
    stage1 = pd.read_csv(STAGE1_CSV)
    stage2 = pd.read_csv(STAGE2_CSV)
    mapping = yaml.safe_load(NUDGE_MAPPING.read_text())["nudge_mappings"]

    # Mediation multiplier: the Stage 1 standardized SATISFACTION → INTENTION
    # path. Friction damage estimated in Stage 2 lands on satisfaction; this
    # multiplier translates it into the decision-relevant unit (visit
    # intention). It is common to all codes, so it scales — never reorders —
    # the ranking.
    sat_to_intent = float(
        stage1[(stage1["op"] == "~") & (stage1["lval"] == "INTENTION")
               & (stage1["rval"] == "SATISFACTION")]["Est. Std"].iloc[0]
    )

    # Stage 2 structural rows: one standardized path per friction-code dummy
    # (≥30 tagged reporters; estimated among friction reporters with free text).
    paths = stage2[(stage2["op"] == "~") & (stage2["lval"] == "SATISFACTION")].copy()
    paths["path_std"] = paths["Est. Std"].astype(float)
    paths["p_value"] = pd.to_numeric(paths["p-value"], errors="coerce")

    # Prevalence among friction reporters, written by sem_ftas.py Stage 2 report.
    # Recompute here from the stage-2 CSV companion columns if absent.
    prev_csv = SEM_DIR / "sem_stage2_results.md"
    rows = []
    for _, row in paths.iterrows():
        code = row["rval"]
        meta = mapping.get(code, {})
        rows.append({
            "friction_code": code,
            "friction_label": meta.get("friction_label", code),
            "sem_path_to_satisfaction_std": row["path_std"],
            "p_value": row["p_value"],
            "journey_stage": meta.get("likely_journey_stage"),
            "nudge_type": meta.get("possible_nudge_type"),
            "example_intervention": meta.get("example_intervention"),
        })
    ranking = pd.DataFrame(rows)

    # Merge prevalence from the SEM stage-2 prevalence table if present.
    prevalence_csv = SEM_DIR / "sem_stage2_prevalence.csv"
    if prevalence_csv.exists():
        prevalence = pd.read_csv(prevalence_csv)
        ranking = ranking.merge(prevalence, on="friction_code", how="left")
        # priority_score = (-min(path, 0)) x prevalence x |sat→intent path|.
        #   clip(upper=0) then negate: positive/zero satisfaction paths
        #   contribute exactly 0 — no damage, nothing for a nudge to recover.
        #   prevalence converts per-tagged damage into expected damage per
        #   friction reporter (rare-but-nasty < common-and-moderate in
        #   aggregate). |sat_to_intent| restates the result in visit-intention
        #   SD units via the Stage 1 mediation path. See module docstring.
        ranking["priority_score"] = (
            (-ranking["sem_path_to_satisfaction_std"].clip(upper=0))
            * ranking["prevalence_among_reporters"].fillna(0)
            * abs(sat_to_intent)
        )
    else:
        # Degraded mode: without prevalence the score is damage-only, i.e. a
        # per-tagged-respondent ranking rather than an aggregate one.
        logger.warning("Prevalence table missing; ranking by path coefficient only.")
        ranking["priority_score"] = -ranking["sem_path_to_satisfaction_std"].clip(upper=0)

    ranking = ranking.sort_values("priority_score", ascending=False).reset_index(drop=True)
    ranking.insert(0, "rank", ranking.index + 1)
    ranking.to_csv(OUT_CSV, index=False)

    md = [
        "# Nudge Priority Ranking (evidence-weighted)",
        "",
        "Derived from the two-stage FTAS SEM: a code's priority is the expected",
        "visit-intention damage it transmits (path x prevalence x satisfaction->intention",
        f"path of {sat_to_intent:.3f}), i.e. the ceiling a nudge targeting it can recover.",
        "Non-negative satisfaction paths score 0 (no damage to recover).",
        "",
        "| # | Friction | SEM path (std) | p | Prevalence* | Priority | Nudge type |",
        "|---|----------|----------------|---|-------------|----------|------------|",
    ]
    for _, r in ranking.iterrows():
        prev = r.get("prevalence_among_reporters")
        prev_str = f"{prev:.1%}" if pd.notna(prev) else "n/a"
        md.append(
            f"| {r['rank']} | {r['friction_label']} | {r['sem_path_to_satisfaction_std']:+.3f} "
            f"| {r['p_value']:.3g} | {prev_str} | {r['priority_score']:.4f} | {r['nudge_type']} |"
        )
    md += [
        "",
        "*Prevalence = share of friction reporters (with free text) tagged with the code.",
        "",
        "## Top-3 intervention candidates",
    ]
    for _, r in ranking.head(3).iterrows():
        md += [f"### {r['rank']}. {r['friction_label']} ({r['journey_stage']})",
               f"{r['example_intervention']}", ""]
    OUT_MD.write_text("\n".join(md), encoding="utf-8")
    logger.info(f"Wrote {OUT_MD}")
    print("\n".join(md[:16]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
