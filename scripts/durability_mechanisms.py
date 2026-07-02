#!/usr/bin/env python3
"""Summarize municipality durability mechanisms and pooled regime tests."""

import argparse
import json
from math import erfc, sqrt
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
SURVEY_CSV = ROOT / "output" / "official_fukui" / "ftas_survey_normalized.csv"
REGIME_CSV = ROOT / "output" / "synthesis" / "synthesis_regime_friction_map.csv"
REGIME_ORDER = {"durable": 0, "transient": 1, "none": 2}
NO_OVERNIGHT = "福井県内には宿泊しない"
FIRST_TIME = "初めて"
TEST_METRICS = {
    "repeat_share": "area_visit_count",
    "overnight_share": "overnight",
    "car_share": "transport_to_fukui_private_car",
    "shinkansen_share": "transport_to_fukui_shinkansen",
}


def require_inputs() -> None:
    missing = [path for path in (SURVEY_CSV, REGIME_CSV) if not path.is_file()]
    if missing:
        rendered = "\n".join(f"  - {path}" for path in missing)
        raise FileNotFoundError(f"Missing durability-mechanism input(s):\n{rendered}")


def percent(values: pd.Series) -> float:
    """Return boolean-series share as percent."""
    return float(100 * values.mean())


def municipality_summary(
    municipality: str, group: pd.DataFrame, purpose_columns: list[str]
) -> dict:
    visit_count = group["area_visit_count"].dropna()
    pre = group.loc[~group["post_hokuriku_shinkansen_fukui"]]
    post = group.loc[group["post_hokuriku_shinkansen_fukui"]]
    overnight = (
        group["overnight_area_in_prefecture"].notna()
        & group["overnight_area_in_prefecture"].ne(NO_OVERNIGHT)
    )
    ranked_purposes = (
        group[purpose_columns].mean().sort_values(ascending=False, kind="stable")
    )

    result = {
        "municipality": municipality,
        "n_respondents": int(len(group)),
        "repeat_share_pct": percent(visit_count.ne(FIRST_TIME)),
        "first_time_share_pre_pct": percent(pre["area_visit_count"].eq(FIRST_TIME)),
        "first_time_share_post_pct": percent(post["area_visit_count"].eq(FIRST_TIME)),
        "overnight_share_pct": percent(overnight),
        "car_share_pct": percent(group["transport_to_fukui_private_car"]),
        "shinkansen_share_pct": percent(group["transport_to_fukui_shinkansen"]),
        "car_share_pre_pct": percent(pre["transport_to_fukui_private_car"]),
        "car_share_post_pct": percent(post["transport_to_fukui_private_car"]),
    }
    for rank, (column, share) in enumerate(ranked_purposes.head(3).items(), start=1):
        result[f"top{rank}_purpose"] = column.removeprefix("purpose_")
        result[f"top{rank}_purpose_pct"] = float(100 * share)
    return result


def build_summary(survey: pd.DataFrame, regime: pd.DataFrame) -> pd.DataFrame:
    purpose_columns = [
        column for column in survey.columns
        if column.startswith("purpose_") and survey[column].dtype == bool
    ]
    if len(purpose_columns) < 3:
        raise ValueError("Survey has fewer than three boolean purpose columns")

    rows = [
        municipality_summary(municipality, group, purpose_columns)
        for municipality, group in survey.dropna(subset=["municipality"]).groupby(
            "municipality", sort=False
        )
    ]
    summary = pd.DataFrame(rows)
    regime_columns = [
        "municipality", "area_code", "en", "regime", "regime_confidence", "good_fit"
    ]
    if regime["municipality"].duplicated().any():
        raise ValueError("Regime map contains duplicate municipalities")
    summary = summary.merge(
        regime[regime_columns], on="municipality", how="left", validate="one_to_one"
    )
    if len(summary) != 17 or summary["area_code"].isna().any():
        raise ValueError("Exact municipality join did not match all 17 municipalities")

    metric_columns = [
        "n_respondents", "repeat_share_pct",
        "first_time_share_pre_pct", "first_time_share_post_pct",
        "overnight_share_pct", "car_share_pct", "shinkansen_share_pct",
        "car_share_pre_pct", "car_share_post_pct",
        "top1_purpose", "top1_purpose_pct",
        "top2_purpose", "top2_purpose_pct",
        "top3_purpose", "top3_purpose_pct",
    ]
    summary["_regime_order"] = summary["regime"].map(REGIME_ORDER)
    summary = summary.sort_values(
        ["_regime_order", "repeat_share_pct"], ascending=[True, False]
    ).drop(columns="_regime_order")
    return summary[[*regime_columns, *metric_columns]].reset_index(drop=True)


def proportion_test(
    durable_successes: int,
    durable_n: int,
    transient_successes: int,
    transient_n: int,
) -> dict:
    durable_p = durable_successes / durable_n
    transient_p = transient_successes / transient_n
    pooled_p = (
        (durable_successes + transient_successes) / (durable_n + transient_n)
    )
    standard_error = sqrt(
        pooled_p * (1 - pooled_p) * (1 / durable_n + 1 / transient_n)
    )
    z = (durable_p - transient_p) / standard_error
    p_two_sided = erfc(abs(z) / sqrt(2))
    return {
        "durable_pct": 100 * durable_p,
        "transient_pct": 100 * transient_p,
        "diff_pp": 100 * (durable_p - transient_p),
        "z": z,
        "p_two_sided": p_two_sided,
    }


def build_tests(survey: pd.DataFrame, regime: pd.DataFrame) -> dict:
    eligible = regime.loc[
        regime["good_fit"].astype(bool)
        & regime["regime_confidence"].eq("high")
        & regime["regime"].isin(["durable", "transient"])
    ]
    pools = {
        name: survey[survey["municipality"].isin(
            eligible.loc[eligible["regime"].eq(name), "municipality"]
        )].copy()
        for name in ("durable", "transient")
    }
    for pool in pools.values():
        pool["overnight"] = (
            pool["overnight_area_in_prefecture"].notna()
            & pool["overnight_area_in_prefecture"].ne(NO_OVERNIGHT)
        )

    tests = {}
    for metric, column in TEST_METRICS.items():
        samples = {}
        for regime_name, pool in pools.items():
            if metric == "repeat_share":
                valid = pool[column].dropna()
                samples[regime_name] = (int(valid.ne(FIRST_TIME).sum()), len(valid))
            else:
                samples[regime_name] = (int(pool[column].sum()), len(pool))
        tests[metric] = proportion_test(*samples["durable"], *samples["transient"])
    return tests


def write_markdown(
    path: Path, summary: pd.DataFrame, tests: dict
) -> None:
    test_table = pd.DataFrame.from_dict(tests, orient="index")
    test_table.index.name = "metric"
    content = (
        "# Durability mechanisms\n\n"
        f"{summary.to_markdown(index=False)}\n\n"
        "## Pooled two-proportion z-tests\n\n"
        f"{test_table.reset_index().to_markdown(index=False)}\n"
    )
    path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir", type=Path, default=ROOT / "output" / "synthesis",
        help="Directory for synthesis outputs",
    )
    args = parser.parse_args()
    require_inputs()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    survey = pd.read_csv(SURVEY_CSV, low_memory=False)
    regime = pd.read_csv(REGIME_CSV)
    summary = build_summary(survey, regime)
    tests = build_tests(survey, regime)

    summary.to_csv(args.output_dir / "durability_mechanisms.csv", index=False)
    (args.output_dir / "durability_mechanisms_tests.json").write_text(
        json.dumps(tests, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    write_markdown(args.output_dir / "durability_mechanisms.md", summary, tests)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
