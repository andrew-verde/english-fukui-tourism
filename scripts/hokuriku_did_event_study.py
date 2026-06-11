#!/usr/bin/env python3
"""
hokuriku_did_event_study.py — Thesis-grade DiD for the March 2024 Hokuriku
Shinkansen extension (Fukui treated, Ishikawa control).

Upgrades over hokuriku_did_audit.py (which remains as the quick feasibility check):
  1. Cluster-robust SEs (prefecture x month) instead of HC1.
  2. Composition controls: gender, harmonized age band, local-resident flag.
  3. Robustness battery:
       - drop Jan-Mar 2024 (Noto earthquake aftermath + opening transition)
       - drop Noto-area Ishikawa response sites (earthquake-affected control units)
  4. Event-study specification: treated x month coefficients (reference month =
     2024-02, the last full pre-treatment month) with 95% CIs and a plot.

Reads:  output/hokuriku_merged/raw/merged_survey_<year>.csv
Writes: output/hokuriku_merged/did_thesis_estimates.csv
        output/hokuriku_merged/did_event_study_coefficients.csv
        output/hokuriku_merged/did_event_study.png
        output/hokuriku_merged/did_event_study_report.md

Usage:
    python scripts/hokuriku_did_event_study.py
"""

import re
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
TREATMENT_DATE = pd.Timestamp("2024-03-16")
REFERENCE_MONTH = "2024-02"  # last full pre-treatment month

PREF_COL = "対象県（富山/石川/福井）"
DATE_COL = "アンケート回答日"
SITE_COL = "回答場所"
RESIDENCE_COL = "居住都道府県"
GENDER_COL = "性別"
AGE_COL = "年代"

REVISIT_MAP = {
    "また行きたい（1年以内）": 5,
    "また行きたい（１年以内）": 5,
    "機会があれば行きたい": 4,
    "どちらともいえない": 3,
    "あまり行きたいと思わない": 2,
    "行きたくない": 1,
}

OUTCOMES = {
    "transport_satisfaction": "交通の満足度",
    "product_service_sat": "満足度（商品・サービス）",
    "nps": "おすすめ度",
    "revisit_intent": "再訪意向",
}

# Noto peninsula response sites (earthquake-affected control areas).
NOTO_PATTERN = "能登|輪島|珠洲|七尾|和倉|穴水|志賀|羽咋|中能登|宝達"


def _age_band(value: object) -> str | None:
    """Harmonize Fukui decade strings (50代) and Ishikawa birth years (1972)."""
    if pd.isna(value):
        return None
    text = str(value).strip()
    if text.endswith("代"):
        return text
    if re.fullmatch(r"(19|20)\d{2}(\.0)?", text):
        age = 2024 - int(float(text))
        decade = max(10, min(80, (age // 10) * 10))
        return f"{decade}代"
    return None


def load_merged() -> pd.DataFrame:
    usecols = [PREF_COL, DATE_COL, SITE_COL, RESIDENCE_COL, GENDER_COL, AGE_COL] + list(OUTCOMES.values())
    frames = [
        pd.read_csv(path, usecols=lambda c: c in usecols, low_memory=False)
        for path in sorted(RAW_DIR.glob("merged_survey_*.csv"))
    ]
    df = pd.concat(frames, ignore_index=True)
    df["prefecture"] = df[PREF_COL].map({"福井": "Fukui", "石川": "Ishikawa"})
    df = df.dropna(subset=["prefecture"])
    df["response_date"] = pd.to_datetime(df[DATE_COL], errors="coerce")
    df = df.dropna(subset=["response_date"])

    df["transport_satisfaction"] = pd.to_numeric(df["交通の満足度"], errors="coerce")
    df["product_service_sat"] = pd.to_numeric(df["満足度（商品・サービス）"], errors="coerce")
    df["nps"] = pd.to_numeric(df["おすすめ度"], errors="coerce").where(lambda s: s.between(0, 10))
    df["revisit_intent"] = df["再訪意向"].map(REVISIT_MAP)

    df["month"] = df["response_date"].dt.to_period("M").astype(str)
    df["post"] = (df["response_date"] >= TREATMENT_DATE).astype(int)
    df["treated"] = (df["prefecture"] == "Fukui").astype(int)
    df["cluster"] = df["prefecture"] + "_" + df["month"]

    home_pref = {"Fukui": "福井県", "Ishikawa": "石川県"}
    df["local_resident"] = (
        df[RESIDENCE_COL].astype(str).str.strip() == df["prefecture"].map(home_pref)
    ).astype(int)
    df["gender"] = df[GENDER_COL].astype(str).str.strip().where(
        df[GENDER_COL].astype(str).str.strip().isin(["男", "女"]), "other_or_na"
    )
    df["age_band"] = df[AGE_COL].apply(_age_band).fillna("unknown")
    df["noto_site"] = (
        df[SITE_COL].astype(str).str.contains(NOTO_PATTERN, na=False, regex=True)
    )
    return df


def _fit_did(sub: pd.DataFrame, outcome: str, controls: bool) -> dict | None:
    formula = f"{outcome} ~ treated * post"
    if controls:
        formula += " + C(gender) + C(age_band) + local_resident"
    data = sub.dropna(subset=[outcome])
    if data.empty or data["treated"].nunique() < 2 or data["post"].nunique() < 2:
        return None
    model = smf.ols(formula, data=data).fit(
        cov_type="cluster", cov_kwds={"groups": data["cluster"]}
    )
    coef = "treated:post"
    return {
        "estimate": float(model.params[coef]),
        "se_cluster": float(model.bse[coef]),
        "p_value": float(model.pvalues[coef]),
        "ci_low": float(model.conf_int().loc[coef, 0]),
        "ci_high": float(model.conf_int().loc[coef, 1]),
        "n": int(model.nobs),
        "n_clusters": int(data["cluster"].nunique()),
    }


def run_specifications(df: pd.DataFrame) -> pd.DataFrame:
    specs = {
        "baseline": (df, False),
        "composition_controls": (df, True),
        "drop_jan_mar_2024": (
            df[~df["month"].isin(["2024-01", "2024-02", "2024-03"])], True,
        ),
        "drop_noto_sites": (df[~df["noto_site"]], True),
        "drop_jan_mar_2024_and_noto": (
            df[~df["month"].isin(["2024-01", "2024-02", "2024-03"]) & ~df["noto_site"]], True,
        ),
    }
    rows = []
    for spec_name, (sub, controls) in specs.items():
        for outcome in OUTCOMES:
            fitted = _fit_did(sub, outcome, controls)
            if fitted is None:
                continue
            rows.append({"spec": spec_name, "outcome": outcome, **fitted})
    return pd.DataFrame(rows)


def run_event_study(df: pd.DataFrame, outcome: str) -> pd.DataFrame:
    data = df.dropna(subset=[outcome]).copy()
    months = sorted(m for m in data["month"].unique())
    # Keep months observed in BOTH prefectures so coefficients are identified.
    both = [
        m for m in months
        if data.loc[data["month"] == m, "treated"].nunique() == 2
    ]
    data = data[data["month"].isin(both)]
    if REFERENCE_MONTH not in both:
        logger.warning(f"{outcome}: reference month {REFERENCE_MONTH} not in common months; skipping")
        return pd.DataFrame()
    data["month_c"] = pd.Categorical(data["month"], categories=both)
    formula = (
        f"{outcome} ~ C(month_c) + treated "
        f"+ treated:C(month_c, Treatment(reference='{REFERENCE_MONTH}'))"
    )
    # Prefecture x month clustering degenerates here (each treated:month
    # coefficient is identified within exactly two clusters → zero-width CIs),
    # so the event study uses heteroskedasticity-robust SEs instead.
    model = smf.ols(formula, data=data).fit(cov_type="HC1")
    rows = []
    for name, est in model.params.items():
        match = re.search(r"treated:.*\[T\.([0-9-]+)\]", name)
        if not match:
            continue
        ci = model.conf_int().loc[name]
        rows.append({
            "outcome": outcome,
            "month": match.group(1),
            "estimate": float(est),
            "ci_low": float(ci[0]),
            "ci_high": float(ci[1]),
            "p_value": float(model.pvalues[name]),
        })
    rows.append({
        "outcome": outcome, "month": REFERENCE_MONTH,
        "estimate": 0.0, "ci_low": 0.0, "ci_high": 0.0, "p_value": np.nan,
    })
    return pd.DataFrame(rows).sort_values("month")


def plot_event_study(coefs: pd.DataFrame) -> None:
    outcomes = coefs["outcome"].unique()
    fig, axes = plt.subplots(len(outcomes), 1, figsize=(12, 3.2 * len(outcomes)), sharex=True)
    if len(outcomes) == 1:
        axes = [axes]
    for ax, outcome in zip(axes, outcomes):
        sub = coefs[coefs["outcome"] == outcome]
        x = pd.to_datetime(sub["month"])
        ax.errorbar(
            x, sub["estimate"],
            yerr=[sub["estimate"] - sub["ci_low"], sub["ci_high"] - sub["estimate"]],
            fmt="o", markersize=3, capsize=2, linewidth=1,
        )
        ax.axhline(0, color="grey", linewidth=0.8)
        ax.axvline(TREATMENT_DATE, color="red", linestyle="--", linewidth=1)
        ax.set_title(f"{outcome}: treated x month (ref {REFERENCE_MONTH}), 95% CI, HC1 SEs")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(OUT_DIR / "did_event_study.png", dpi=150)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = load_merged()
    logger.info(
        f"Sample: {len(df):,} responses "
        f"(Fukui {int(df['treated'].sum()):,} / Ishikawa {int((1 - df['treated']).sum()):,}); "
        f"Noto-site responses: {int(df['noto_site'].sum()):,}"
    )

    estimates = run_specifications(df)
    estimates.to_csv(OUT_DIR / "did_thesis_estimates.csv", index=False)

    coef_frames = [run_event_study(df, outcome) for outcome in OUTCOMES]
    coefs = pd.concat([c for c in coef_frames if not c.empty], ignore_index=True)
    coefs.to_csv(OUT_DIR / "did_event_study_coefficients.csv", index=False)
    plot_event_study(coefs)

    pre_coefs = coefs[coefs["month"] < REFERENCE_MONTH]
    pre_sig = pre_coefs[pre_coefs["p_value"] < 0.05]
    pivot = estimates.pivot(index="outcome", columns="spec", values="estimate").round(4)

    report = [
        "# Shinkansen DiD — thesis specification",
        "",
        f"Fukui (treated) vs Ishikawa (control); treatment {TREATMENT_DATE.date()}; "
        f"DiD specs use prefecture-x-month clustered SEs; the event study uses HC1 "
        f"(clustering degenerates with two clusters per month); reference month {REFERENCE_MONTH}.",
        "",
        "## DiD estimates across specifications (treated x post)",
        "```",
        estimates.to_string(index=False, float_format=lambda v: f"{v:.4f}"),
        "```",
        "",
        "## Estimate stability (point estimates by spec)",
        "```",
        pivot.to_string(),
        "```",
        "",
        "## Pre-trend check",
        f"- Pre-reference event-study coefficients significant at 0.05: "
        f"{len(pre_sig)} of {len(pre_coefs)} "
        f"({'parallel-trends concern — inspect the plot' if len(pre_sig) else 'no individual pre-trend violations detected'}).",
        "",
        "## Caveats carried from the feasibility audit",
        "- Responses, not unique respondents (public file anonymizes member IDs);",
        "  clustering mitigates but does not eliminate repeat-responder dependence.",
        "- Outcome composition can shift with the visitor mix the Shinkansen itself",
        "  attracts; the composition-controls spec adjusts for gender, age band, and",
        "  local residency, but origin-mix shifts remain part of the treatment effect.",
        "- Instruments differ across prefectures; only identically-worded outcomes used.",
        "",
        "![event study](did_event_study.png)",
    ]
    (OUT_DIR / "did_event_study_report.md").write_text("\n".join(report), encoding="utf-8")
    logger.info(f"Wrote {OUT_DIR / 'did_event_study_report.md'}")
    print("\n".join(report[:20]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
