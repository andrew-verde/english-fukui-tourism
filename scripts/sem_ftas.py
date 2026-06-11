#!/usr/bin/env python3
"""
sem_ftas.py — Two-stage SEM on the official FTAS survey (ADR 0001).

Stage 0 (CFA go/no-go): do the three domain-satisfaction items cohere as one
latent? Reported with loadings and fit indices; if loadings are weak the path
model is the documented fallback.

Stage 1 (full deduplicated sample): friction exposure -> satisfaction -> intention
    SATISFACTION =~ overall + transport + product_service   (latent)
    INTENTION    =~ future_visit_intent + nps               (latent)
    SATISFACTION ~ reported_inconvenience
    INTENTION    ~ SATISFACTION + reported_inconvenience    (direct + indirect)

Stage 2 (friction reporters with free text): which friction TYPE damages
satisfaction most? SATISFACTION regressed on the 12 friction-code dummies,
same measurement model. This conditioning avoids coding non-writers as
friction-free (free-text selection bias).

Reads:  output/official_fukui/ftas_tagged_survey.csv
Writes: output/sem/sem_stage1_results.md / .csv
        output/sem/sem_stage2_results.md / .csv
        output/sem/sem_fit_indices.csv

Usage:
    python scripts/sem_ftas.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import semopy

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.statistical_validation_official import _dedup_respondents, _has_text
from src.official_fukui.ftas import load_japanese_codebook
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

ROOT = Path(__file__).resolve().parent.parent
TAGGED_CSV = ROOT / "output" / "official_fukui" / "ftas_tagged_survey.csv"
CODEBOOK_PATH = ROOT / "config" / "official_japanese_friction_codebook.yaml"
OUT_DIR = ROOT / "output" / "sem"

SATISFACTION_MAP = {
    "とても満足": 5, "満足": 4, "普通": 3, "どちらでもない": 3,
    "不満": 2, "とても不満": 1,
}

CFA_DESC = """
SATISFACTION =~ sat_overall + sat_transport + sat_product
"""

STAGE1_DESC = """
SATISFACTION =~ sat_overall + sat_transport + sat_product
INTENTION =~ intent_revisit + intent_nps
SATISFACTION ~ friction
INTENTION ~ SATISFACTION + friction
"""


def load_data() -> pd.DataFrame:
    df = pd.read_csv(TAGGED_CSV, low_memory=False)
    df, audit = _dedup_respondents(df)
    logger.info(f"Deduplicated: {audit}")

    out = pd.DataFrame(index=df.index)
    out["sat_overall"] = pd.to_numeric(df["overall_satisfaction_score"], errors="coerce")
    out["sat_transport"] = pd.to_numeric(df["transport_satisfaction_score"], errors="coerce")
    out["sat_product"] = df["product_service_satisfaction"].map(SATISFACTION_MAP)
    out["intent_revisit"] = pd.to_numeric(df["future_visit_intent_score"], errors="coerce")
    out["intent_nps"] = pd.to_numeric(df["nps"], errors="coerce").where(lambda s: s.between(0, 10))
    out["friction"] = df["reported_inconvenience"].astype(bool).astype(int)
    out["has_text"] = _has_text(df)
    codes = list(load_japanese_codebook(CODEBOOK_PATH).keys())
    for code in codes:
        out[code] = df[code].astype(bool).astype(int) if code in df.columns else 0
    return out, codes


def _standardize(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    d = df.copy()
    for col in cols:
        d[col] = (d[col] - d[col].mean()) / d[col].std()
    return d


def _fit_stats(model: semopy.Model) -> dict:
    stats = semopy.calc_stats(model).T["Value"]
    return {
        "chi2": float(stats.get("chi2", np.nan)),
        "df": float(stats.get("DoF", np.nan)),
        "CFI": float(stats.get("CFI", np.nan)),
        "TLI": float(stats.get("TLI", np.nan)),
        "RMSEA": float(stats.get("RMSEA", np.nan)),
        "n": int(model.n_samples) if model.n_samples else None,
    }


def _params(model: semopy.Model) -> pd.DataFrame:
    est = model.inspect(std_est=True)
    return est[["lval", "op", "rval", "Estimate", "Est. Std", "Std. Err", "p-value"]]


def run_cfa(data: pd.DataFrame) -> tuple[pd.DataFrame, dict, bool]:
    cfa_data = (
        data[["sat_overall", "sat_transport", "sat_product"]].dropna().astype("float64")
    )
    model = semopy.Model(CFA_DESC)
    model.fit(cfa_data)
    params = _params(model)
    fit = _fit_stats(model)
    loadings = params[(params["op"] == "~") & (params["lval"].isin(
        ["sat_overall", "sat_transport", "sat_product"]))]["Est. Std"]
    # semopy stores measurement rows as indicator ~ latent in inspect() output
    std_loadings = params[params["op"] == "~"]["Est. Std"].astype(float)
    acceptable = bool((std_loadings.abs() >= 0.4).all())
    return params, fit, acceptable


def run_stage1(data: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    cols = ["sat_overall", "sat_transport", "sat_product", "intent_revisit", "intent_nps", "friction"]
    d = data[cols].dropna().astype("float64")
    d = _standardize(d, [c for c in cols if c != "friction"])
    model = semopy.Model(STAGE1_DESC)
    model.fit(d)
    return _params(model), {**_fit_stats(model), "n": len(d)}


def run_stage2(data: pd.DataFrame, codes: list[str]) -> tuple[pd.DataFrame, dict, pd.DataFrame]:
    reporters = data[(data["friction"] == 1) & data["has_text"]]
    cols = ["sat_overall", "sat_transport", "sat_product"] + codes
    d = reporters[cols].dropna(subset=["sat_overall", "sat_transport", "sat_product"]).astype("float64")
    active = [c for c in codes if d[c].sum() >= 30]
    d = _standardize(d, ["sat_overall", "sat_transport", "sat_product"])
    desc = (
        "SATISFACTION =~ sat_overall + sat_transport + sat_product\n"
        "SATISFACTION ~ " + " + ".join(active)
    )
    model = semopy.Model(desc)
    model.fit(d)
    params = _params(model)
    prevalence = pd.DataFrame({
        "friction_code": active,
        "n_reporters_tagged": [int(d[c].sum()) for c in active],
        "prevalence_among_reporters": [float(d[c].mean()) for c in active],
    })
    return params, {**_fit_stats(model), "n": len(d)}, prevalence


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data, codes = load_data()

    cfa_params, cfa_fit, cfa_ok = run_cfa(data)
    s1_params, s1_fit = run_stage1(data)
    s2_params, s2_fit, prevalence = run_stage2(data, codes)

    fits = pd.DataFrame([
        {"model": "CFA_satisfaction", **cfa_fit},
        {"model": "Stage1_full_sample", **s1_fit},
        {"model": "Stage2_friction_reporters", **s2_fit},
    ])
    fits.to_csv(OUT_DIR / "sem_fit_indices.csv", index=False)
    s1_params.to_csv(OUT_DIR / "sem_stage1_results.csv", index=False)
    s2_params.to_csv(OUT_DIR / "sem_stage2_results.csv", index=False)
    prevalence.to_csv(OUT_DIR / "sem_stage2_prevalence.csv", index=False)

    s2_paths = s2_params[
        (s2_params["op"] == "~") & (s2_params["lval"] == "SATISFACTION")
    ].copy()
    s2_paths = s2_paths.merge(
        prevalence, left_on="rval", right_on="friction_code", how="left"
    ).sort_values("Est. Std")

    report1 = [
        "# FTAS SEM — Stage 0 (CFA) and Stage 1 (full sample)",
        "",
        "## CFA: do the three satisfaction items form one latent?",
        f"Verdict: {'ACCEPTABLE — latent retained' if cfa_ok else 'WEAK — use observed-mediator path model (documented fallback)'}",
        "```",
        cfa_params.to_string(index=False),
        "```",
        "",
        "## Stage 1: friction -> satisfaction -> intention "
        f"(n={s1_fit['n']:,} deduplicated respondents)",
        "Exposure = reported_inconvenience (asked of all respondents; selection-bias-free).",
        "Indicators standardized; friction left binary, so paths are in SD units per friction exposure.",
        "```",
        s1_params.to_string(index=False),
        "```",
        "",
        "## Fit indices",
        "```",
        fits.to_string(index=False),
        "```",
        "",
        "Caveats: indicators are 5-point ordinal treated as continuous (ML); at this",
        "n everything is significant — interpret standardized magnitudes, not p-values.",
    ]
    (OUT_DIR / "sem_stage1_results.md").write_text("\n".join(report1), encoding="utf-8")

    report2 = [
        "# FTAS SEM — Stage 2 (friction reporters, n="
        f"{s2_fit['n']:,})",
        "",
        "Sample: respondents with reported_inconvenience = true AND free text",
        "(tags are only meaningful where text exists). Codes with <30 tagged",
        "reporters excluded from estimation.",
        "",
        "## Friction-type paths to SATISFACTION (sorted: most damaging first)",
        "```",
        s2_paths[["rval", "Estimate", "Est. Std", "p-value", "n_reporters_tagged",
                  "prevalence_among_reporters"]].to_string(index=False),
        "```",
        "",
        "Negative Est. Std = that friction type predicts lower satisfaction among",
        "friction reporters. These coefficients feed the nudge priority ranking",
        "(scripts/rank_nudge_priorities.py).",
    ]
    (OUT_DIR / "sem_stage2_results.md").write_text("\n".join(report2), encoding="utf-8")
    logger.info(f"Wrote SEM outputs to {OUT_DIR}")
    print("\n".join(report1[:8]))
    print("\nStage 2 top damaging codes:")
    print(s2_paths[["rval", "Est. Std", "p-value"]].head(6).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
