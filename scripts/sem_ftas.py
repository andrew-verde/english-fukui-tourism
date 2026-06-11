#!/usr/bin/env python3
"""
sem_ftas.py — Two-stage SEM on the official FTAS survey (ADR 0001).

WHY A TWO-STAGE DESIGN (academic traceability — see ADR 0001)
=============================================================
The split between Stage 1 and Stage 2 is not a convenience; it is the core
identification choice of the analysis, designed to keep selection bias out of
the headline friction → satisfaction → intention paths:

* Stage 1 uses the FULL deduplicated sample with the binary exposure
  ``reported_inconvenience`` (不便さ — "did you experience any inconvenience?").
  This item is asked of EVERY respondent on a closed-form scale, so it is free
  of the selection bias inherent in free-text data: answering it requires no
  decision to write anything. The Stage 1 paths are therefore interpretable
  as population-level associations for the whole surveyed visitor population.

* Stage 2 conditions on respondents who BOTH reported friction AND left free
  text, and regresses the satisfaction latent on the friction-code dummies
  produced by the Japanese friction codebook tagger. The conditioning is
  deliberate: friction-code tags are derived from free text, so they are only
  meaningful where free text exists. The tempting alternative — running the
  code dummies on the full sample and coding non-writers as "no friction of
  any type" — would CONFLATE "experienced no friction" with "chose not to
  write", i.e. it would correlate the measurement error in the friction
  indicators with the propensity to write, which itself plausibly correlates
  with satisfaction (the outcome). Conditioning on the writers keeps the
  Stage 2 estimand honest: "AMONG friction reporters who described their
  friction, which friction TYPE predicts the most satisfaction damage?"

Stage 0 (CFA go/no-go): before either structural stage, a confirmatory factor
analysis checks whether the three domain-satisfaction items cohere as a single
SATISFACTION latent. Important caveat baked into the verdict logic: with
exactly 3 indicators and 1 factor the CFA is JUST-IDENTIFIED (df = 0), so
chi-square and the fit indices are uninformative for the CFA alone — any
3-indicator/1-factor model reproduces its covariance matrix perfectly. The
go/no-go verdict therefore rests on the STANDARDIZED LOADINGS, using the
conventional |λ| ≥ 0.4 salience threshold, not on fit. (Observed loadings:
overall ≈ .87, transport ≈ .53, product/service ≈ .86. Transport is the
weakest because it is a domain-specific satisfaction rating rather than a
parallel measure of general satisfaction — expected, and still well above
the threshold.) If loadings were weak, the documented fallback is an
observed-variable path model instead of the latent.

Measurement decisions, with justification:

* All indicators are 5-point ordinal Likert items (NPS is 0–10) treated as
  CONTINUOUS under maximum likelihood. This is the standard pragmatic choice
  and is generally considered acceptable with ≥ 5 response categories and
  large n (the usual citation is Rhemtulla, Brosseau-Liard & Savalei 2012,
  Psychological Methods). The stricter alternative — ordinal estimation via
  WLSMV / polychoric correlations, as implemented in lavaan — is noted as
  robustness future work, not done here because semopy's WLS support is
  immature and the substantive conclusions are unlikely to flip at this n.

* Indicators (NOT the binary friction exposure) are z-standardized before
  fitting, so structural path coefficients read directly as "SD units of the
  outcome per unit of exposure": for the binary friction variable, the path
  is the SD-unit shift associated with reporting friction at all.

* Deduplication happens BEFORE everything else. The FTAS survey is tied to a
  rice-bag giveaway, producing repeat responders; repeat responses violate
  the independence assumption underlying the SEs, so the shared
  ``_dedup_respondents`` helper (same one used by the validation pipeline,
  for consistency) collapses them first.

* Stage 2 drops friction codes tagged on fewer than 30 reporters. Below that
  threshold a path estimate is dominated by a handful of respondents and is
  noise, not evidence.

Fit-index interpretation context (Hu & Bentler 1999): CFI ≥ .95 good,
≥ .90 acceptable; RMSEA ≤ .06 good. Observed: Stage 1 CFI .990 / RMSEA .044
(good); Stage 2 CFI .906 (acceptable). And a blanket caveat: at n ≈ 16k
essentially every path is statistically significant — inference rests on the
STANDARDIZED MAGNITUDES, not on p-values.

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

# Japanese satisfaction labels → 5-point numeric scale for the
# product/service item (満足度（商品・サービス）), which is stored as text.
#   とても満足 "very satisfied" = 5; 満足 "satisfied" = 4;
#   普通 "average" and どちらでもない "neither" both map to the midpoint 3
#   (both are neutral responses; the two wordings appear in different survey
#   waves and are treated as equivalent);
#   不満 "dissatisfied" = 2; とても不満 "very dissatisfied" = 1.
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
    """Load the tagged FTAS survey and build the SEM analysis frame.

    Deduplication happens FIRST, before any variable construction: the FTAS
    survey's rice-bag incentive produces repeat responders, and repeat rows
    from the same member violate the independence assumption behind every
    standard error downstream. ``_dedup_respondents`` is the same helper used
    by the statistical-validation pipeline, so the SEM sample is by
    construction identical to the validated sample.

    Variable construction notes (academic traceability):
      * sat_overall    — 満足度（総合） overall satisfaction, 1–5, already numeric.
      * sat_transport  — 交通の満足度 transport satisfaction, 1–5, already numeric.
      * sat_product    — 満足度（商品・サービス） product/service satisfaction,
                         stored as Japanese text labels → mapped via
                         SATISFACTION_MAP (see comment above the map).
      * intent_revisit — 再訪意向 future-visit intention, 1–5.
      * intent_nps     — おすすめ度 NPS recommendation, kept only if in [0, 10]
                         (values outside the instrument's range are data-entry
                         noise and are coerced to NaN rather than clipped).
      * friction       — reported_inconvenience (不便さ), the binary closed-form
                         exposure asked of ALL respondents (Stage 1's
                         selection-bias-free exposure; see module docstring).
      * has_text       — whether the respondent left ANY free text; this is the
                         conditioning variable that defines the Stage 2 sample,
                         because friction-code tags are only meaningful where
                         text exists.
      * one 0/1 dummy per codebook friction code; codes absent from the tagged
        CSV (never fired) are filled with the constant 0 so the column set is
        stable across reruns of the tagger.
    """
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
    """Z-standardize the named columns (mean 0, SD 1).

    Applied to the ordinal INDICATORS only — never to the binary friction
    exposure or the friction-code dummies. Standardizing a binary variable
    would destroy its natural interpretation; leaving the exposure on its
    0/1 scale while standardizing the indicators means every structural path
    reads as "SD units of the latent per friction exposure", which is the
    unit the thesis (and rank_nudge_priorities.py) interprets throughout.
    """
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
    """Stage 0 CFA go/no-go: do the three satisfaction items form one latent?

    Identification caveat (this is WHY the verdict ignores fit indices): a
    one-factor model with exactly three indicators is JUST-IDENTIFIED — the
    number of free parameters equals the number of unique covariance moments,
    so df = 0 and the model reproduces the observed covariance matrix exactly.
    Chi-square, CFI, TLI and RMSEA are therefore vacuous for the CFA in
    isolation (they only become informative in the larger Stage 1/2 models,
    where over-identifying restrictions exist). The substantive go/no-go test
    is whether every STANDARDIZED loading clears |λ| ≥ 0.4, the conventional
    salience threshold for "this indicator meaningfully reflects the factor".

    Observed result for the record: loadings ≈ .87 (overall), .53 (transport),
    .86 (product/service). Transport is the weakest because 交通の満足度 is a
    DOMAIN satisfaction (how good was the transport?) rather than a parallel
    measure of overall trip satisfaction — a lower but still salient loading
    is exactly what theory predicts, so the latent is retained.
    """
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
    # Go/no-go on the 0.4 salience threshold (NOT on fit indices — see the
    # just-identification caveat in the docstring: df = 0 makes fit vacuous).
    acceptable = bool((std_loadings.abs() >= 0.4).all())
    return params, fit, acceptable


def run_stage1(data: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Stage 1: friction → satisfaction → intention on the FULL sample.

    Exposure is the binary closed-form reported_inconvenience (不便さ) item,
    asked of every respondent — so this stage carries no free-text selection
    bias (see module docstring / ADR 0001). Indicators are standardized, the
    exposure is left binary, so paths read as SD units per friction exposure.
    Estimation is ML on ordinal-as-continuous indicators (acceptable with
    ≥ 5 categories and large n; Rhemtulla et al. 2012). Observed fit for the
    record: CFI .990 / RMSEA .044, comfortably inside the Hu & Bentler (1999)
    good-fit region (CFI ≥ .95, RMSEA ≤ .06).
    """
    cols = ["sat_overall", "sat_transport", "sat_product", "intent_revisit", "intent_nps", "friction"]
    d = data[cols].dropna().astype("float64")
    # Standardize the five ordinal indicators only; friction stays 0/1 so the
    # structural paths are interpretable in SD-units-per-exposure.
    d = _standardize(d, [c for c in cols if c != "friction"])
    model = semopy.Model(STAGE1_DESC)
    model.fit(d)
    return _params(model), {**_fit_stats(model), "n": len(d)}


def run_stage2(data: pd.DataFrame, codes: list[str]) -> tuple[pd.DataFrame, dict, pd.DataFrame]:
    """Stage 2: which friction TYPE damages satisfaction most?

    Sample is deliberately conditioned on friction == 1 AND has_text: friction
    -code tags are derived from free text, so they are only meaningful where
    text exists. Including non-writers and coding them as friction-type-free
    would correlate measurement error with the propensity to write — which
    plausibly correlates with satisfaction, the outcome — i.e. it would inject
    exactly the selection bias the two-stage design exists to avoid. The
    estimand here is conditional by design: "among friction reporters who
    described their friction, which code predicts the most damage?"

    Codes tagged on fewer than 30 reporters are excluded: below that, a path
    coefficient is dominated by a handful of respondents and reflects noise
    rather than a stable type effect. Observed fit for the record: CFI .906 —
    in the Hu & Bentler 'acceptable' band (≥ .90), below the 'good' .95 line,
    consistent with the smaller, more heterogeneous conditioned sample.
    """
    reporters = data[(data["friction"] == 1) & data["has_text"]]
    cols = ["sat_overall", "sat_transport", "sat_product"] + codes
    d = reporters[cols].dropna(subset=["sat_overall", "sat_transport", "sat_product"]).astype("float64")
    # ≥ 30 tagged reporters required for a code to enter the model (see docstring).
    active = [c for c in codes if d[c].sum() >= 30]
    # Indicators standardized; the 0/1 code dummies are NOT, so each path is
    # the SD-unit satisfaction shift associated with carrying that tag.
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
