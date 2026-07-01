#!/usr/bin/env python3
"""Synthesis stage: join causal-arm regime classification to FTAS friction feeds.

Reads four pre-existing causal, municipality-friction, mode-friction, and SEM
priority CSVs. Writes three synthesis tables and machine-readable narrative
metrics. This is pure post-processing: it does not run SCM, SEM, or fetch data.
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
OFFICIAL_DIR = ROOT / "output" / "official_fukui"
SCM_CSV = ROOT / "data" / "causal" / "fukui_municipalities_scm.csv"
MUNICIPALITY_CSV = OFFICIAL_DIR / "ftas_friction_by_municipality.csv"
MODE_CSV = OFFICIAL_DIR / "ftas_friction_by_transport_mode.csv"
NUDGE_CSV = ROOT / "output" / "sem" / "nudge_priority_ranking.csv"

VISITOR_MODES = [
    "transport_to_fukui_airplane",
    "transport_to_fukui_local_train",
    "transport_to_fukui_private_car",
    "transport_to_fukui_rental_car",
    "transport_to_fukui_tour_bus",
]
SHINKANSEN_MODE = "transport_to_fukui_shinkansen"
REGIME_ORDER = {"durable": 0, "transient": 1, "none": 2}


def minmax(values: pd.Series) -> pd.Series:
    """Return min-max normalized values, or zero for a constant series."""
    values = values.astype(float)
    span = values.max() - values.min()
    return (values - values.min()) / span if span else pd.Series(0.0, index=values.index)


def require_inputs() -> None:
    missing = [path for path in (SCM_CSV, MUNICIPALITY_CSV, MODE_CSV, NUDGE_CSV)
               if not path.exists()]
    if missing:
        rendered = "\n".join(f"  - {path}" for path in missing)
        raise FileNotFoundError(
            f"Missing synthesis input(s):\n{rendered}\n"
            "Run build-ftas, sem-ftas, and nudge-ranking as needed. "
            "The causal-arm SCM summary must be supplied separately."
        )


def build_regime_map() -> tuple[pd.DataFrame, pd.DataFrame]:
    scm = pd.read_csv(SCM_CSV)
    friction = pd.read_csv(MUNICIPALITY_CSV)
    municipality_rows = friction[friction["municipality"].notna()].copy()

    scm_names = set(scm["name"])
    friction_names = set(municipality_rows["municipality"])
    if len(scm) != 17 or scm_names != friction_names:
        raise ValueError(
            "Exact municipality join failed: "
            f"SCM-only={sorted(scm_names - friction_names)}, "
            f"FTAS-only={sorted(friction_names - scm_names)}"
        )

    pivot = municipality_rows.pivot(
        index="municipality", columns="friction_code", values="pct_of_respondents"
    ).fillna(0)
    result = scm[["area_code", "en", "name", "open_pct", "sust_pct", "good_fit"]].merge(
        pivot, left_on="name", right_index=True, how="left", validate="one_to_one"
    )
    if len(result) != 17 or result[pivot.columns].isna().any().any():
        raise ValueError("Municipality friction join did not match all 17 municipalities")

    opened = result["open_pct"] > 5
    result["regime"] = np.select(
        [opened & (result["sust_pct"] >= 0), opened & (result["sust_pct"] < 0)],
        ["durable", "transient"],
        default="none",
    )
    result["regime_confidence"] = np.where(result["good_fit"], "high", "low")
    result["leaked_lift_pct"] = np.where(
        opened, (result["open_pct"] - result["sust_pct"]).clip(lower=0), 0
    )

    top_rows = []
    for _, row in result.iterrows():
        ranked = row[pivot.columns].sort_values(ascending=False, kind="stable")
        item = {}
        for rank, (code, pct) in enumerate(ranked.head(3).items(), start=1):
            item[f"top{rank}_friction_code"] = code
            item[f"top{rank}_friction_pct"] = pct
        top_rows.append(item)
    result = pd.concat([result.reset_index(drop=True), pd.DataFrame(top_rows)], axis=1)
    result["municipality"] = result["name"]
    result["_regime_order"] = result["regime"].map(REGIME_ORDER)
    result = result.sort_values(
        ["_regime_order", "open_pct"], ascending=[True, False]
    ).drop(columns="_regime_order")

    columns = [
        "area_code", "en", "municipality", "regime", "regime_confidence",
        "good_fit", "open_pct", "sust_pct", "leaked_lift_pct",
        "transport_access", "wayfinding_signage", "food_amenities_gap",
        "top1_friction_code", "top1_friction_pct",
        "top2_friction_code", "top2_friction_pct",
        "top3_friction_code", "top3_friction_pct",
    ]
    return result[columns], result


def build_mode_friction() -> pd.DataFrame:
    modes = pd.read_csv(MODE_CSV)
    arrival = modes[
        modes["transport_mode"].isin([SHINKANSEN_MODE, *VISITOR_MODES])
    ].copy()
    expected = {SHINKANSEN_MODE, *VISITOR_MODES}
    if set(arrival["transport_mode"]) != expected:
        raise ValueError("Visitor arrival-mode feed is incomplete")

    prevalence = arrival.pivot(
        index="friction_code", columns="transport_mode", values="pct_of_respondents"
    )
    pooled = arrival[arrival["transport_mode"].isin(VISITOR_MODES)].groupby(
        "friction_code"
    ).agg(
        pooled_count=("count", "sum"), pooled_n=("n_respondents", "sum")
    )
    result = pd.DataFrame(index=prevalence.index)
    result["shinkansen_pct"] = prevalence[SHINKANSEN_MODE]
    result["private_car_pct"] = prevalence["transport_to_fukui_private_car"]
    result["other_arrival_pooled_pct"] = (
        100 * pooled["pooled_count"] / pooled["pooled_n"]
    )
    result["shk_minus_car"] = result["shinkansen_pct"] - result["private_car_pct"]
    result["shk_minus_other"] = (
        result["shinkansen_pct"] - result["other_arrival_pooled_pct"]
    )
    result["shk_over_other_ratio"] = (
        result["shinkansen_pct"] / result["other_arrival_pooled_pct"]
    )
    result = result.reset_index()

    nudge = pd.read_csv(NUDGE_CSV)
    sem_columns = [
        "friction_code", "priority_score", "sem_path_to_satisfaction_std", "p_value"
    ]
    result = result.merge(nudge[sem_columns], on="friction_code", how="left",
                          validate="one_to_one")
    return result.sort_values("shk_minus_other", ascending=False).reset_index(drop=True)


def build_priority_matrix(
    regime_full: pd.DataFrame, mode_friction: pd.DataFrame
) -> pd.DataFrame:
    scored = mode_friction[mode_friction["priority_score"].notna()].copy()
    high = regime_full[regime_full["good_fit"]]
    friction_codes = scored["friction_code"].tolist()
    correlations = {
        code: high[code].corr(high["leaked_lift_pct"]) for code in friction_codes
    }
    scored["leaked_lift_corr"] = scored["friction_code"].map(correlations)
    scored["ratio_n"] = minmax(scored["shk_over_other_ratio"])
    scored["leaked_lift_corr_n"] = minmax(scored["leaked_lift_corr"].clip(lower=0))
    scored["sem_path_n"] = minmax(scored["sem_path_to_satisfaction_std"].abs())
    scored["causal_opportunity"] = scored[
        ["ratio_n", "leaked_lift_corr_n", "sem_path_n"]
    ].mean(axis=1).round(3)
    scored["priority_n"] = minmax(scored["priority_score"].clip(lower=0))

    priority_median = scored["priority_n"].median()
    causal_median = scored["causal_opportunity"].median()
    priority_high = scored["priority_n"] >= priority_median
    causal_high = scored["causal_opportunity"] >= causal_median
    scored["quadrant"] = np.select(
        [priority_high & causal_high, priority_high, causal_high],
        ["ACT NOW", "quick win", "watch"],
        default="deprioritize",
    )
    columns = [
        "friction_code", "priority_score", "priority_n",
        "sem_path_to_satisfaction_std", "p_value", "shk_over_other_ratio",
        "leaked_lift_corr", "ratio_n", "leaked_lift_corr_n", "sem_path_n",
        "causal_opportunity", "quadrant",
    ]
    return scored[columns].sort_values(
        ["causal_opportunity", "priority_score"], ascending=False
    ).reset_index(drop=True)


def build_metrics(
    regime_map: pd.DataFrame, regime_full: pd.DataFrame,
    mode_friction: pd.DataFrame, priority: pd.DataFrame,
) -> dict:
    high = regime_full[regime_full["good_fit"]]
    transport = mode_friction.set_index("friction_code").loc["transport_access"]
    return {
        "regime_counts_all": regime_map["regime"].value_counts().to_dict(),
        "regime_counts_high_confidence": high["regime"].value_counts().to_dict(),
        "high_confidence_n": int(len(high)),
        "transport_access_leaked_lift_corr_high_confidence": float(
            high["transport_access"].corr(high["leaked_lift_pct"])
        ),
        "transport_access_mean_transient_high_confidence": float(
            high.loc[high["regime"] == "transient", "transport_access"].mean()
        ),
        "transport_access_mean_non_transient_high_confidence": float(
            high.loc[high["regime"] != "transient", "transport_access"].mean()
        ),
        "transport_access_mode_headline": {
            key: float(transport[key]) for key in (
                "shinkansen_pct", "private_car_pct", "other_arrival_pooled_pct",
                "shk_minus_other", "shk_over_other_ratio"
            )
        },
        "transport_access_is_max_shk_minus_other": bool(
            mode_friction.iloc[0]["friction_code"] == "transport_access"
        ),
        "priority_quadrants": priority.set_index("friction_code")["quadrant"].to_dict(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir", type=Path, default=ROOT / "output" / "synthesis",
        help="Directory for synthesis outputs",
    )
    args = parser.parse_args()
    require_inputs()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    regime_map, regime_full = build_regime_map()
    mode_friction = build_mode_friction()
    priority = build_priority_matrix(regime_full, mode_friction)
    metrics = build_metrics(regime_map, regime_full, mode_friction, priority)

    regime_map.to_csv(args.output_dir / "synthesis_regime_friction_map.csv", index=False)
    mode_friction.to_csv(args.output_dir / "synthesis_mode_friction.csv", index=False)
    priority.to_csv(args.output_dir / "synthesis_priority_matrix.csv", index=False)
    (args.output_dir / "synthesis_narrative_metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
