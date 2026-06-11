#!/usr/bin/env python3
"""
hokuriku_did_audit.py — DiD feasibility audit for the March 2024 Hokuriku
Shinkansen extension, using the merged tri-prefecture survey microdata.

IDENTIFICATION STRATEGY (academic traceability)
===============================================
The opening of the Hokuriku Shinkansen Kanazawa–Tsuruga extension on
2024-03-16 is treated as an EXOGENOUS transport-friction-reduction shock: its
timing was set years in advance by national rail-construction schedules, not
by anything about contemporaneous tourist satisfaction in Fukui, so visitors
surveyed just before vs just after differ in their exposure to dramatically
easier rail access but not (absent confounders) in anything else systematic.

* Fukui    = TREATED. It gained direct Shinkansen access for the first time.
* Ishikawa = CONTROL. Kanazawa has had Shinkansen service since the 2015
  Nagano–Kanazawa extension, so the 2024 opening changed little about access
  to Ishikawa itself; its visitors provide the counterfactual time path.
* Toyama   = EXCLUDED. It only enters the merged survey data in 2025, so it
  has NO pre-treatment observations — a DiD arm without a pre-period is
  unidentifiable. Its exclusion is noted in the report rather than silent.

Outcome selection: the two prefectures run DIFFERENT survey instruments
(Fukui FTAS vs the Ishikawa QR survey), so outcomes are restricted to items
verified to be IDENTICALLY WORDED in both. Comparing differently-worded items
across arms would confound treatment effects with instrument effects.

Outcomes (respondent level, available both prefectures 2023→present):
  transport_satisfaction   交通の満足度            (1–5)
  product_service_sat      満足度（商品・サービス）  (1–5)
  nps                      おすすめ度              (0–10)
  revisit_intent           再訪意向                (1–5 mapped; residents excluded)

Note on product_service_sat: it doubles as a PLACEBO-STYLE outcome. There is
no plausible mechanism by which reduced transport friction changes how
satisfied visitors are with products and services at the destination, so a
null effect there supports specification validity, while a "significant"
effect would flag a confounded design.

This script is the quick FEASIBILITY check (naive 2x2 + OLS interaction with
HC1 SEs, no controls). The thesis-grade estimates — prefecture×month
clustered SEs, composition controls, earthquake robustness, event study —
live in scripts/hokuriku_did_event_study.py.

Writes (to output/hokuriku_merged/):
  did_monthly_means.csv      — monthly mean outcomes by prefecture
  did_estimates.csv          — naive 2x2 DiD + OLS interaction (HC1 SEs)
  parallel_trends.png        — monthly trends with treatment line
  did_feasibility_report.md  — summary, caveats, coverage table

Usage:
    python scripts/hokuriku_did_audit.py
"""

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils.logger import setup_logger

logger = setup_logger(__name__)

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "output" / "hokuriku_merged" / "raw"
OUT_DIR = ROOT / "output" / "hokuriku_merged"
TREATMENT_DATE = pd.Timestamp("2024-03-16")  # Hokuriku Shinkansen Kanazawa–Tsuruga opening

PREF_COL = "対象県（富山/石川/福井）"
DATE_COL = "アンケート回答日"

# 再訪意向 (revisit intention) text labels → 1–5 ordinal scale.
#   また行きたい（1年以内） "want to visit again (within a year)" = 5 — appears
#   with BOTH a half-width "1" and a full-width "１" in the source data, hence
#   the duplicate key; missing the full-width variant would silently drop a
#   large share of the strongest-intent responses.
#   機会があれば行きたい "would visit given the chance" = 4;
#   どちらともいえない "can't say either way" = 3 (midpoint);
#   あまり行きたいと思わない "don't really want to" = 2;
#   行きたくない "don't want to visit" = 1.
# Residents ("地元/在住" response options) are deliberately ABSENT from the
# map: "revisit" is not a meaningful construct for someone who lives there,
# so resident responses map to NaN and drop out of the revisit outcome only.
REVISIT_MAP = {
    "また行きたい（1年以内）": 5,
    "また行きたい（１年以内）": 5,  # full-width variant in source data
    "機会があれば行きたい": 4,
    "どちらともいえない": 3,
    "あまり行きたいと思わない": 2,
    "行きたくない": 1,
    # Residents are not tourists for revisit purposes — excluded (NaN).
}

# The four outcomes verified to be identically worded in BOTH instruments
# (Fukui FTAS and Ishikawa QR survey). product_service_sat additionally
# serves as the placebo-style outcome — see module docstring.
OUTCOMES = {
    "transport_satisfaction": "交通の満足度",      # transport satisfaction, 1–5
    "product_service_sat": "満足度（商品・サービス）",  # product/service satisfaction, 1–5
    "nps": "おすすめ度",                            # recommendation (NPS), 0–10
    "revisit_intent": "再訪意向",                   # revisit intention, mapped 1–5
}


# 会員ID (member ID). Loaded so the repeat-responder problem can be checked,
# but in the PUBLIC merged file it is anonymized to a constant 0 — so
# deduplication is IMPOSSIBLE here. The local FTAS extract shows ~47% of
# Fukui rows are repeat responses by the same member, which means rows are
# not independent and the SEs below are anti-conservative; the thesis-grade
# script mitigates with clustering plus a dedup sensitivity run on the
# Fukui arm using local member IDs.
MEMBER_COL = "会員ID"


def load_merged() -> pd.DataFrame:
    """Load the merged tri-prefecture survey files and construct DiD variables.

    Key constructions:
      * prefecture     — from 対象県 (surveyed prefecture), mapped to English.
      * post           — response on/after the 2024-03-16 Kanazawa–Tsuruga
                         opening (the exogenous treatment date).
      * treated        — Fukui (the prefecture that newly gained Shinkansen
                         access); Ishikawa, with Shinkansen since 2015, is the
                         control.
      * nps            — kept only when within the instrument's 0–10 range;
                         out-of-range values are entry noise → NaN, not clipped.
      * revisit_intent — text labels mapped via REVISIT_MAP (residents → NaN
                         by design; see the map's comment).
    Toyama rows survive the prefecture map here but are filtered out of the
    DiD sample in main() — they have no pre-period (data starts 2025).
    """
    usecols = [PREF_COL, DATE_COL, MEMBER_COL] + list(OUTCOMES.values())
    frames = []
    for path in sorted(RAW_DIR.glob("merged_survey_*.csv")):
        frames.append(pd.read_csv(path, usecols=lambda c: c in usecols, low_memory=False))
        logger.info(f"Loaded {path.name}: {len(frames[-1]):,} rows")
    df = pd.concat(frames, ignore_index=True)

    df["prefecture"] = df[PREF_COL].map({"福井": "Fukui", "石川": "Ishikawa", "富山": "Toyama"})
    df["response_date"] = pd.to_datetime(df[DATE_COL], errors="coerce")
    df = df.dropna(subset=["prefecture", "response_date"])

    df["transport_satisfaction"] = pd.to_numeric(df["交通の満足度"], errors="coerce")
    df["product_service_sat"] = pd.to_numeric(df["満足度（商品・サービス）"], errors="coerce")
    df["nps"] = pd.to_numeric(df["おすすめ度"], errors="coerce").where(lambda s: s.between(0, 10))
    df["revisit_intent"] = df["再訪意向"].map(REVISIT_MAP)

    df["month"] = df["response_date"].dt.to_period("M").dt.to_timestamp()
    df["post"] = (df["response_date"] >= TREATMENT_DATE).astype(int)
    df["treated"] = (df["prefecture"] == "Fukui").astype(int)
    return df


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = load_merged()

    # DiD sample = treated (Fukui) + control (Ishikawa) only. Toyama is
    # excluded: it enters the merged data only in 2025, so it has no
    # pre-treatment period and cannot identify a DiD contrast.
    did = df[df["prefecture"].isin(["Fukui", "Ishikawa"])].copy()
    logger.info(f"DiD sample (Fukui+Ishikawa): {len(did):,} rows; "
                f"pre={int((did['post'] == 0).sum()):,}, post={int((did['post'] == 1).sum()):,}")

    monthly = (
        did.groupby(["prefecture", "month"])
        .agg(n=("post", "size"), **{k: (k, "mean") for k in OUTCOMES})
        .reset_index()
    )
    monthly.to_csv(OUT_DIR / "did_monthly_means.csv", index=False)

    # Naive 2x2 DiD + OLS with interaction, heteroskedasticity-robust (HC1)
    # SEs. Deliberately simple — this script answers "is a DiD feasible at
    # all?", not "what is the effect?". Known shortcomings, fixed in
    # hokuriku_did_event_study.py: HC1 ignores within prefecture-month
    # dependence (treatment varies at that level, so SEs should be clustered
    # there); no composition controls; no Noto-earthquake robustness; and the
    # 2x2 collapses all time variation that the event study makes visible.
    rows = []
    for outcome in OUTCOMES:
        sub = did.dropna(subset=[outcome])
        cell = sub.groupby(["treated", "post"])[outcome].mean()
        try:
            naive = (cell[1, 1] - cell[1, 0]) - (cell[0, 1] - cell[0, 0])
        except KeyError:
            logger.warning(f"{outcome}: missing a DiD cell, skipping")
            continue
        model = smf.ols(f"{outcome} ~ treated * post", data=sub).fit(cov_type="HC1")
        rows.append({
            "outcome": outcome,
            "n": len(sub),
            "pre_fukui": cell.get((1, 0), np.nan), "post_fukui": cell.get((1, 1), np.nan),
            "pre_ishikawa": cell.get((0, 0), np.nan), "post_ishikawa": cell.get((0, 1), np.nan),
            "did_estimate": naive,
            "ols_interaction": model.params["treated:post"],
            "se_hc1": model.bse["treated:post"],
            "p_value": model.pvalues["treated:post"],
        })
    estimates = pd.DataFrame(rows)
    estimates.to_csv(OUT_DIR / "did_estimates.csv", index=False)

    fig, axes = plt.subplots(2, 2, figsize=(13, 8), sharex=True)
    for ax, outcome in zip(axes.flat, OUTCOMES):
        for pref, grp in monthly.groupby("prefecture"):
            ax.plot(grp["month"], grp[outcome], marker=".", label=pref)
        ax.axvline(TREATMENT_DATE, color="red", linestyle="--", linewidth=1)
        ax.set_title(outcome)
        ax.legend(fontsize=8)
    fig.suptitle("Monthly mean outcomes, Fukui vs Ishikawa (red = Shinkansen extension)")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(OUT_DIR / "parallel_trends.png", dpi=150)

    pre = monthly[monthly["month"] < TREATMENT_DATE]
    report = [
        "# Shinkansen DiD feasibility audit",
        "",
        f"Treatment date: {TREATMENT_DATE.date()} (Kanazawa–Tsuruga extension opening).",
        f"Sample: Fukui (treated) vs Ishikawa (control), {len(did):,} respondents, "
        f"{did['response_date'].min().date()} – {did['response_date'].max().date()}.",
        "Toyama excluded: enters merged data only in 2025 (no pre-period).",
        "",
        "## Pre-period coverage",
        f"- Pre-treatment months with data: Fukui "
        f"{pre[pre['prefecture'] == 'Fukui']['month'].nunique()}, Ishikawa "
        f"{pre[pre['prefecture'] == 'Ishikawa']['month'].nunique()}.",
        "",
        "## Naive DiD estimates (treated x post interaction, OLS, HC1 SEs)",
        "```",
        estimates.to_string(index=False, float_format=lambda v: f"{v:.4f}"),
        "```",
        "",
        "## Caveats (to address before headline use)",
        "- Survey instruments differ by prefecture (FTAS vs Ishikawa QR survey);",
        "  identical wording verified only for the four outcomes above.",
        "- Respondents are surveyed *visitors* — composition shifts caused by the",
        "  Shinkansen (more first-timers, different origins) are part of the treatment",
        "  effect, not a confound, but must be described as such. Consider",
        "  composition-adjusted models (controls for origin prefecture, repeat visits).",
        "- transport_satisfaction has ~50% item response; check missingness stability",
        "  across the treatment boundary before relying on it.",
        "- 2024 Noto earthquake (Jan 2024) hit Ishikawa during the pre-period —",
        "  the single largest threat to parallel trends. Mitigations: drop Jan–Mar 2024,",
        "  drop Noto-area responses, or use event-study coefficients rather than 2x2.",
        "- Rows are survey responses, not unique respondents, and the public merged",
        "  file anonymizes 会員ID (constant/blank), so repeat responders cannot be",
        "  identified here. The local FTAS extract shows ~47% of Fukui rows are",
        "  repeat responses by the same member, so independence is violated and",
        "  these SEs are anti-conservative. The thesis estimate should cluster SEs",
        "  (e.g. by municipality x month) and run a dedup sensitivity check using",
        "  the local FTAS member IDs for the Fukui arm.",
        "- p-values here are unadjusted and the model has no time or seasonality",
        "  controls; this is a *feasibility* audit, not the thesis estimate.",
        "",
        "![parallel trends](parallel_trends.png)",
    ]
    (OUT_DIR / "did_feasibility_report.md").write_text("\n".join(report), encoding="utf-8")
    logger.info(f"Wrote report to {OUT_DIR / 'did_feasibility_report.md'}")
    print("\n".join(report[:25]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
