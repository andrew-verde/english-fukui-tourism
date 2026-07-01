#!/usr/bin/env python3
"""Build descriptive resident-attitude artifacts from Fukui Vision aggregates."""

import os
import tempfile
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "matplotlib"))

import matplotlib

matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "output" / "official_fukui" / "raw"
OUTPUT_DIR = ROOT / "output" / "official_fukui"
OVERVIEW_FILE = RAW_DIR / "fukui_vision_overview.csv"
TIMESERIES_FILE = RAW_DIR / "fukui_vision_timeseries.csv"

EXPECTED_OVERVIEW = {
    "fiscal_year", "reiwa_year", "calendar_year", "survey_target",
    "target_count", "method", "period_start", "period_end", "response_count",
    "response_rate_percent", "result_pdf_url", "summary_pdf_url",
    "source_page_url",
}
EXPECTED_TIMESERIES = {
    "indicator_id", "indicator_label", "fiscal_year", "reiwa_year",
    "question_no", "denominator", "option", "score", "count", "percent",
    "source_pdf_url",
}

FAVORABLE = {
    "暮らしてきてよかった",
    "どちらかといえば暮らしてきてよかった",
}
MIGRATION = {
    "どちらかといえば県外に移り住みたい",
    "県外に移り住みたい",
}
DISPLAY_ORDER = [
    "暮らしてきてよかった",
    "どちらかといえば暮らしてきてよかった",
    "わからない",
    "どちらかといえば県外に移り住みたい",
    "県外に移り住みたい",
    "未記入・無効等",
]
DISPLAY_LABELS = {
    "暮らしてきてよかった": "Glad to have lived in Fukui",
    "どちらかといえば暮らしてきてよかった": "Somewhat glad",
    "わからない": "Unsure",
    "どちらかといえば県外に移り住みたい": "Somewhat prefer moving out",
    "県外に移り住みたい": "Prefer moving out",
    "未記入・無効等": "Missing / invalid",
}
METHOD_SHIFT_CAVEAT = (
    "Survey collection changed from postal-only in 2019-2021 to postal+WEB "
    "from 2022. Year differences may reflect mode, sampling, nonresponse, or "
    "other contemporaneous changes; these aggregate series are descriptive "
    "and support no causal claims."
)


def load_inputs(
    overview_path: Path = OVERVIEW_FILE,
    timeseries_path: Path = TIMESERIES_FILE,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    overview = pd.read_csv(overview_path)
    timeseries = pd.read_csv(timeseries_path)
    if set(overview.columns) != EXPECTED_OVERVIEW:
        raise ValueError("unexpected Fukui Vision overview columns")
    if set(timeseries.columns) != EXPECTED_TIMESERIES:
        raise ValueError("unexpected Fukui Vision timeseries columns")
    if overview["fiscal_year"].duplicated().any():
        raise ValueError("duplicate overview fiscal years")
    if timeseries.duplicated(["indicator_id", "fiscal_year", "option"]).any():
        raise ValueError("duplicate indicator/year/option rows")
    return overview, timeseries


def build_tables(
    overview: pd.DataFrame, timeseries: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    living = timeseries.loc[timeseries["indicator_id"] == "living_fukui"].copy()
    if living.empty:
        raise ValueError("living_fukui indicator missing")

    stacked = living[
        ["fiscal_year", "denominator", "option", "count", "percent", "source_pdf_url"]
    ].merge(
        overview[["fiscal_year", "method", "response_count"]],
        on="fiscal_year",
        how="left",
        validate="many_to_one",
    )
    if stacked["method"].isna().any():
        raise ValueError("timeseries year missing from overview")
    stacked["option_order"] = stacked["option"].map(
        {option: position for position, option in enumerate(DISPLAY_ORDER)}
    )
    if stacked["option_order"].isna().any():
        unknown = sorted(stacked.loc[stacked["option_order"].isna(), "option"].unique())
        raise ValueError(f"unknown living_fukui option(s): {unknown}")
    stacked = stacked.sort_values(["fiscal_year", "option_order"]).reset_index(drop=True)

    grouped = (
        stacked.assign(
            favorable_percent=stacked["percent"].where(stacked["option"].isin(FAVORABLE), 0),
            migration_intention_percent=stacked["percent"].where(
                stacked["option"].isin(MIGRATION), 0
            ),
        )
        .groupby("fiscal_year", as_index=False)
        .agg(
            favorable_percent=("favorable_percent", "sum"),
            migration_intention_percent=("migration_intention_percent", "sum"),
        )
    )
    net = grouped.copy()
    net["net_satisfaction_percent"] = (
        net["favorable_percent"] - net["migration_intention_percent"]
    )
    net = net.merge(
        overview[["fiscal_year", "method"]], on="fiscal_year", validate="one_to_one"
    )

    migration = (
        stacked.loc[stacked["option"].isin(MIGRATION)]
        .pivot(index="fiscal_year", columns="option", values="percent")
        .reset_index()
    )
    migration["migration_intention_percent"] = migration[list(MIGRATION)].sum(axis=1)
    migration = migration.merge(
        overview[["fiscal_year", "method"]], on="fiscal_year", validate="one_to_one"
    )
    return stacked, net, migration


def plot_stacked(stacked: pd.DataFrame, path: Path) -> None:
    pivot = stacked.pivot(index="fiscal_year", columns="option", values="percent")
    pivot = pivot.reindex(columns=DISPLAY_ORDER, fill_value=0)
    pivot = pivot.rename(columns=DISPLAY_LABELS)
    colors = ["#236192", "#79A9CF", "#C9C9C9", "#E8A36A", "#B8423A", "#6E7781"]
    ax = pivot.plot(
        kind="bar", stacked=True, figsize=(10.5, 6), color=colors, width=0.76
    )
    ax.axvline(2.5, color="#172033", linestyle="--", linewidth=1)
    ax.text(
        2.55, 102, "postal + WEB from 2022", fontsize=9, color="#172033", va="bottom"
    )
    ax.set_title("Fukui residents: views on living in Fukui (descriptive)")
    ax.set_xlabel("Fiscal year")
    ax.set_ylabel("Reported share (%)")
    ax.set_ylim(0, 108)
    ax.legend(title="", bbox_to_anchor=(1.02, 1), loc="upper left", frameon=False)
    ax.grid(axis="y", alpha=0.25)
    fig = ax.get_figure()
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def write_report(net: pd.DataFrame, migration: pd.DataFrame, path: Path) -> None:
    first = net.iloc[0]
    last = net.iloc[-1]
    lines = [
        "# Fukui resident vision descriptive series",
        "",
        "Aggregate official questionnaire results; no respondent-level inference.",
        "",
        "## Living-in-Fukui summary",
        "",
        "| Fiscal year | Favorable (%) | Migration intention (%) | Net satisfaction (pp) | Method |",
        "|---:|---:|---:|---:|---|",
    ]
    for row in net.itertuples():
        lines.append(
            f"| {row.fiscal_year} | {row.favorable_percent:.1f} | "
            f"{row.migration_intention_percent:.1f} | "
            f"{row.net_satisfaction_percent:.1f} | {row.method} |"
        )
    lines += [
        "",
        "Net satisfaction = favorable share minus migration-intention share. "
        "It is a descriptive contrast, not a validated scale.",
        "",
        f"From {int(first.fiscal_year)} to {int(last.fiscal_year)}, favorable share "
        f"changed {last.favorable_percent - first.favorable_percent:+.1f} pp; "
        f"migration intention changed "
        f"{last.migration_intention_percent - first.migration_intention_percent:+.1f} pp.",
        "",
        "## Method caveat",
        "",
        METHOD_SHIFT_CAVEAT,
        "",
        "No causal claim is made about tourism, policy, or the Hokuriku Shinkansen.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    overview, timeseries = load_inputs()
    stacked, net, migration = build_tables(overview, timeseries)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stacked.drop(columns="option_order").to_csv(
        OUTPUT_DIR / "resident_vision_stacked.csv", index=False
    )
    net.to_csv(OUTPUT_DIR / "resident_vision_net_satisfaction.csv", index=False)
    migration.to_csv(
        OUTPUT_DIR / "resident_vision_migration_intention.csv", index=False
    )
    plot_stacked(stacked, OUTPUT_DIR / "resident_vision_stacked.png")
    write_report(net, migration, OUTPUT_DIR / "resident_vision_descriptive.md")


if __name__ == "__main__":
    main()
