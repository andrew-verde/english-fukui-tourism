#!/usr/bin/env python3
"""
Generate presentation-ready result charts from current CSV outputs.

Writes PNG files to output/result_charts/.
"""

import os
import sys
import tempfile
import textwrap
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("MPLCONFIGDIR", os.path.join(tempfile.gettempdir(), "matplotlib"))

import matplotlib

matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"
CHART_DIR = OUTPUT_DIR / "result_charts"
MULTILINGUAL_DIR = OUTPUT_DIR / "multilingual_review_analysis"
OFFICIAL_DIR = OUTPUT_DIR / "official_fukui"

LANGUAGE_SUMMARY_CSV = MULTILINGUAL_DIR / "language_summary_by_city.csv"
REVIEW_COMPARISON_CSV = MULTILINGUAL_DIR / "japanese_english_friction_comparison.csv"
JAPANESE_FRICTION_BY_CITY_CSV = MULTILINGUAL_DIR / "japanese_friction_by_city.csv"
OFFICIAL_PREF_CSV = OFFICIAL_DIR / "official_prefecture_friction_comparison.csv"
OFFICIAL_AREA_CSV = OFFICIAL_DIR / "ftas_friction_by_area.csv"
OFFICIAL_STATS_JSON = OFFICIAL_DIR / "statistical_results_official.json"
OFFICIAL_FTAS_TAGGED_CSV = OFFICIAL_DIR / "ftas_tagged_survey.csv"

BLUE = "#1F4E79"
GREEN = "#2E7D5B"
RED = "#B8423A"
GOLD = "#B8872B"
INK = "#172033"
MUTED = "#5F6B7A"
GRID = "#D8D2C8"
SCORE_COLORS = {
    1: "#B8423A",
    2: "#D77A46",
    3: "#E4C36A",
    4: "#8EB57B",
    5: "#2E7D5B",
}

LABEL_OVERRIDES = {
    "transport_access": "Transport / Access",
    "wayfinding_signage": "Wayfinding / Signage",
    "english_information_gap": "English Info Gap",
    "staff_communication": "Staff Communication",
    "booking_ticketing": "Booking / Ticketing",
    "waiting_crowding": "Waiting / Crowding",
    "price_value": "Price / Value",
    "cleanliness_comfort": "Cleanliness / Comfort",
    "opening_hours_availability": "Opening Hours",
    "itinerary_fit_time_cost": "Itinerary Fit",
    "accessibility_mobility": "Accessibility / Mobility",
    "food_amenities_gap": "Food / Amenities",
}

AREA_TRANSLATIONS = {
    "越前そばの里 エリア": "Echizen Soba Village",
    "あわら湯のまち エリア": "Awara Yunomachi",
    "大本山 永平寺 エリア": "Eiheiji Temple",
    "福井駅前 エリア": "Fukui Station Area",
    "かつやま恐竜の森 エリア": "Katsuyama Dinosaur Forest",
    "一乗谷朝倉氏遺跡 エリア": "Ichijodani Asakura Ruins",
    "道の駅「南えちぜん山海里」 エリア": "RS Minami-Echizen Sankairi",
    "越前大野城・城下町 エリア": "Echizen Ono Castle / Town",
    "道の駅「越前」 エリア": "Roadside Station Echizen",
    "道の駅「恐竜渓谷かつやま」 エリア": "RS Dinosaur Valley Katsuyama",
    "道の駅「越前おおの荒島の郷」 エリア": "RS Echizen Ono Arashima",
    "丸岡城 エリア": "Maruoka Castle",
}


def setup_style() -> None:
    plt.rcParams.update(
        {
            "figure.dpi": 180,
            "savefig.dpi": 220,
            "font.family": "sans-serif",
            "font.sans-serif": [
                "Hiragino Sans",
                "Hiragino Maru Gothic Pro",
                "Yu Gothic",
                "Noto Sans CJK JP",
                "DejaVu Sans",
            ],
            "font.size": 11,
            "axes.titlesize": 15,
            "axes.labelsize": 11,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.edgecolor": GRID,
            "axes.labelcolor": INK,
            "xtick.color": INK,
            "ytick.color": INK,
            "text.color": INK,
        }
    )


def ensure_inputs(paths: list[Path]) -> None:
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise SystemExit("Missing required input(s):\n" + "\n".join(missing))


def save(fig: plt.Figure, filename: str) -> Path:
    CHART_DIR.mkdir(parents=True, exist_ok=True)
    path = CHART_DIR / filename
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def wrap_label(label: str, width: int = 22) -> str:
    return "\n".join(textwrap.wrap(label, width=width, break_long_words=False))


def bilingual_area_label(area: str) -> str:
    english = AREA_TRANSLATIONS.get(area)
    japanese = area.replace(" エリア", "")
    if english is None:
        return japanese
    return f"{wrap_label(english, 28)}\n{japanese}"


def add_source_note(fig: plt.Figure, note: str) -> None:
    return None


def plot_review_language_fukui() -> Path:
    df = pd.read_csv(REVIEW_COMPARISON_CSV)
    fukui = df[df["city"] == "Fukui"].copy()
    fukui = fukui.sort_values("japanese_minus_english_pp", key=lambda s: s.abs(), ascending=False).head(8)
    fukui = fukui.sort_values("japanese_pct_reviews")

    labels = [wrap_label(label, 21) for label in fukui["friction_label_with_ja"]]
    y = np.arange(len(fukui))

    fig, ax = plt.subplots(figsize=(10.8, 6.2))
    h = 0.36
    ax.barh(y - h / 2, fukui["english_pct_reviews"], height=h, color=BLUE, label="English-language reviews")
    ax.barh(y + h / 2, fukui["japanese_pct_reviews"], height=h, color=GREEN, label="Japanese-language reviews")

    for yi, row in enumerate(fukui.itertuples()):
        ax.text(row.english_pct_reviews + 0.12, yi - h / 2, f"{row.english_pct_reviews:.1f}%", va="center", fontsize=9)
        ax.text(row.japanese_pct_reviews + 0.12, yi + h / 2, f"{row.japanese_pct_reviews:.1f}%", va="center", fontsize=9)
        if bool(row.significant_bh_0_05):
            x = max(row.english_pct_reviews, row.japanese_pct_reviews) + 1.0
            ax.text(x, yi, "q<.05", va="center", fontsize=9, color=RED, fontweight="bold")

    ax.set_yticks(y, labels)
    ax.set_xlabel("Reviews with friction code (%)")
    ax.set_title("Fukui review-language friction rates")
    ax.legend(loc="lower right", frameon=False)
    ax.grid(axis="x", color=GRID, linewidth=0.8, alpha=0.7)
    ax.set_xlim(0, max(fukui["english_pct_reviews"].max(), fukui["japanese_pct_reviews"].max()) + 2.2)
    add_source_note(fig, "Source: output/multilingual_review_analysis/japanese_english_friction_comparison.csv")
    return save(fig, "review_language_fukui_friction_rates.png")


def plot_review_language_counts_by_city() -> Path:
    df = pd.read_csv(LANGUAGE_SUMMARY_CSV)
    df = df.rename(
        columns={
            "other_non_english_non_japanese": "other",
            "undetected_or_too_short": "undetected",
        }
    )
    cities = ["Fukui", "Kanazawa", "Toyama"]
    df = df.set_index("city").loc[cities]
    categories = [
        ("english", "English", BLUE),
        ("japanese", "Japanese", GREEN),
        ("other", "Other detected", GOLD),
        ("undetected", "Undetected/short", MUTED),
    ]

    fig, ax = plt.subplots(figsize=(10.4, 5.8))
    y = np.arange(len(df))
    left = np.zeros(len(df))
    for col, label, color in categories:
        vals = df[col].to_numpy()
        ax.barh(y, vals, left=left, color=color, label=label, height=0.58)
        for yi, val, start in zip(y, vals, left):
            if val >= 80:
                ax.text(start + val / 2, yi, f"{int(val):,}", ha="center", va="center", fontsize=10, color="white" if color in [BLUE, GREEN] else INK, fontweight="bold")
        left += vals

    totals = df[[c[0] for c in categories]].sum(axis=1)
    for yi, total in zip(y, totals):
        ax.text(total + 55, yi, f"total {int(total):,}", va="center", fontsize=10, color=MUTED)

    ax.set_yticks(y, df.index)
    ax.set_xlabel("Cached Google reviews after cutoff/dedup")
    ax.set_title("Google review sample by detected language group")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=4, frameon=False)
    ax.grid(axis="x", color=GRID, linewidth=0.8, alpha=0.7)
    ax.set_xlim(0, totals.max() + 320)
    ax.invert_yaxis()
    add_source_note(fig, "Source: output/multilingual_review_analysis/language_summary_by_city.csv; language is review text language, not reviewer nationality")
    return save(fig, "review_language_counts_by_city.png")


def plot_review_language_difference() -> Path:
    df = pd.read_csv(REVIEW_COMPARISON_CSV)
    sig = df[df["significant_bh_0_05"] == True].copy()  # noqa: E712
    sig = sig.reindex(sig["japanese_minus_english_pp"].abs().sort_values(ascending=False).index).head(12)
    sig = sig.sort_values("japanese_minus_english_pp")

    labels = [wrap_label(f"{row.city}: {row.friction_label_with_ja}", 26) for row in sig.itertuples()]
    y = np.arange(len(sig))
    colors = np.where(sig["japanese_minus_english_pp"] >= 0, GREEN, BLUE)

    fig, ax = plt.subplots(figsize=(10.8, 6.6))
    ax.axvline(0, color=INK, linewidth=1)
    ax.scatter(sig["japanese_minus_english_pp"], y, s=85, color=colors, zorder=3)

    for yi, row in enumerate(sig.itertuples()):
        dx = 0.25 if row.japanese_minus_english_pp >= 0 else -0.25
        ha = "left" if row.japanese_minus_english_pp >= 0 else "right"
        ax.text(row.japanese_minus_english_pp + dx, yi, f"{row.japanese_minus_english_pp:+.1f} pp", va="center", ha=ha, fontsize=9)

    ax.set_yticks(y, labels)
    ax.set_xlabel("Japanese minus English review rate (percentage points)")
    ax.set_title("Largest significant review-language friction differences")
    ax.grid(axis="x", color=GRID, linewidth=0.8, alpha=0.7)
    ax.text(0.02, 0.96, "Higher in English", transform=ax.transAxes, color=BLUE, fontweight="bold")
    ax.text(0.78, 0.96, "Higher in Japanese", transform=ax.transAxes, color=GREEN, fontweight="bold")
    add_source_note(fig, "Source: output/multilingual_review_analysis/japanese_english_friction_comparison.csv; Fisher exact p-values with BH correction")
    return save(fig, "review_language_significant_difference_dotplot.png")


def plot_japanese_friction_profile_by_area() -> Path:
    df = pd.read_csv(JAPANESE_FRICTION_BY_CITY_CSV)
    df["label"] = df["code"].map(LABEL_OVERRIDES).fillna(df["label"])
    cities = ["Fukui", "Kanazawa", "Toyama"]
    city_labels = {
        "Fukui": "Fukui",
        "Kanazawa": "Ishikawa\n(Kanazawa)",
        "Toyama": "Toyama",
    }

    pivot = df.pivot(index="label", columns="city", values="pct_reviews").reindex(columns=cities).fillna(0)
    top_labels = pivot.max(axis=1).sort_values(ascending=False).head(7).index
    pivot = pivot.loc[top_labels]
    pivot = pivot.sort_values("Fukui", ascending=False)

    display = pivot.rename(columns=city_labels)
    annot = display.map(lambda v: f"{v:.1f}%" if v > 0 else "")

    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    cmap = sns.blend_palette(["#F7F3EA", "#E4C36A", "#D77A46", "#B8423A"], as_cmap=True)
    sns.heatmap(
        display,
        ax=ax,
        cmap=cmap,
        vmin=0,
        vmax=max(9.0, float(display.max().max())),
        linewidths=1.2,
        linecolor="white",
        cbar=False,
        annot=annot,
        fmt="",
        annot_kws={"fontsize": 11, "fontweight": "bold", "color": INK},
    )

    ax.set_title("Japanese review friction profile", loc="left", fontsize=13, fontweight="bold", pad=10)
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.set_xticklabels(ax.get_xticklabels(), rotation=0, ha="center", fontsize=11, fontweight="bold")
    ax.set_yticklabels([wrap_label(t.get_text(), 22) for t in ax.get_yticklabels()], rotation=0, fontsize=10)
    ax.tick_params(length=0)

    # Add subtle row guide labels for quick reading at slide scale.
    for spine in ax.spines.values():
        spine.set_visible(False)
    fig.subplots_adjust(left=0.31, right=0.98, top=0.88, bottom=0.08)
    return save(fig, "review_japanese_friction_profile_by_area.png")


def plot_official_prefecture_rates() -> Path:
    df = pd.read_csv(OFFICIAL_PREF_CSV)
    df["label"] = df["friction_code"].map(LABEL_OVERRIDES).fillna(df["friction_code"])
    df["fukui_pct"] = df["fukui_rate"] * 100
    df["ishikawa_pct"] = df["ishikawa_rate"] * 100
    df = df.sort_values("ishikawa_pct").tail(10)

    labels = [wrap_label(label, 22) for label in df["label"]]
    y = np.arange(len(df))

    fig, ax = plt.subplots(figsize=(10.6, 6.0))
    h = 0.36
    ax.barh(y - h / 2, df["fukui_pct"], height=h, color=BLUE, label="Fukui FTAS")
    ax.barh(y + h / 2, df["ishikawa_pct"], height=h, color=GOLD, label="Ishikawa official survey")

    for yi, row in enumerate(df.itertuples()):
        ax.text(row.fukui_pct + 0.06, yi - h / 2, f"{row.fukui_pct:.2f}%", va="center", fontsize=8.8)
        ax.text(row.ishikawa_pct + 0.06, yi + h / 2, f"{row.ishikawa_pct:.2f}%", va="center", fontsize=8.8)
        if row.p_value_bh < 0.05:
            ax.text(max(row.fukui_pct, row.ishikawa_pct) + 0.45, yi, "q<.05", va="center", fontsize=9, color=RED, fontweight="bold")

    ax.set_yticks(y, labels)
    ax.set_xlabel("Respondents with friction code (%)")
    ax.set_title("Official survey friction rates: Fukui vs Ishikawa")
    ax.legend(loc="lower right", frameon=False)
    ax.grid(axis="x", color=GRID, linewidth=0.8, alpha=0.7)
    ax.set_xlim(0, max(df["fukui_pct"].max(), df["ishikawa_pct"].max()) + 1.4)
    add_source_note(fig, "Source: output/official_fukui/official_prefecture_friction_comparison.csv; respondent-level rates")
    return save(fig, "official_fukui_vs_ishikawa_friction_rates.png")


def plot_official_prefecture_difference() -> Path:
    df = pd.read_csv(OFFICIAL_PREF_CSV)
    df["label"] = df["friction_code"].map(LABEL_OVERRIDES).fillna(df["friction_code"])
    df["ishikawa_minus_fukui_pp"] = (df["ishikawa_rate"] - df["fukui_rate"]) * 100
    df = df.reindex(df["ishikawa_minus_fukui_pp"].abs().sort_values(ascending=False).index).head(10)
    df = df.sort_values("ishikawa_minus_fukui_pp")

    labels = [wrap_label(label, 24) for label in df["label"]]
    y = np.arange(len(df))
    colors = np.where(df["ishikawa_minus_fukui_pp"] >= 0, GOLD, BLUE)

    fig, ax = plt.subplots(figsize=(10.0, 5.8))
    ax.axvline(0, color=INK, linewidth=1)
    ax.scatter(df["ishikawa_minus_fukui_pp"], y, s=90, color=colors, zorder=3)

    for yi, row in enumerate(df.itertuples()):
        dx = 0.08 if row.ishikawa_minus_fukui_pp >= 0 else -0.08
        ha = "left" if row.ishikawa_minus_fukui_pp >= 0 else "right"
        ax.text(row.ishikawa_minus_fukui_pp + dx, yi, f"{row.ishikawa_minus_fukui_pp:+.2f} pp", va="center", ha=ha, fontsize=9)

    ax.set_yticks(y, labels)
    ax.set_xlabel("Ishikawa minus Fukui rate (percentage points)")
    ax.set_title("Which official friction rates differ most?")
    ax.grid(axis="x", color=GRID, linewidth=0.8, alpha=0.7)
    add_source_note(fig, "Source: output/official_fukui/official_prefecture_friction_comparison.csv")
    return save(fig, "official_fukui_vs_ishikawa_difference_dotplot.png")


def _find_official_result(payload: dict, name: str) -> dict:
    for result in payload.get("results", []):
        if result.get("name") == name:
            return result.get("details", {})
    raise KeyError(f"Official result not found: {name}")


def plot_official_any_friction_benchmark() -> Path:
    with open(OFFICIAL_STATS_JSON) as f:
        payload = json.load(f)

    pref = _find_official_result(payload, "official_prefecture_comparison")["any_friction"]
    kanazawa = _find_official_result(payload, "official_fukui_vs_ishikawa_kanazawa_area_comparison")["any_friction"]
    rows = [
        {
            "label": "Fukui FTAS",
            "rate": pref["rates"]["Fukui"] * 100,
            "n": pref["counts"]["Fukui"]["n"],
            "count": pref["counts"]["Fukui"]["true"],
            "color": BLUE,
        },
        {
            "label": "Ishikawa official survey",
            "rate": pref["rates"]["Ishikawa"] * 100,
            "n": pref["counts"]["Ishikawa"]["n"],
            "count": pref["counts"]["Ishikawa"]["true"],
            "color": GOLD,
        },
        {
            "label": "Ishikawa Kanazawa-area subset",
            "rate": kanazawa["rates"]["Ishikawa_Kanazawa_area"] * 100,
            "n": kanazawa["counts"]["Ishikawa_Kanazawa_area"]["n"],
            "count": kanazawa["counts"]["Ishikawa_Kanazawa_area"]["true"],
            "color": RED,
        },
    ]
    df = pd.DataFrame(rows)

    fig, ax = plt.subplots(figsize=(9.4, 5.4))
    bars = ax.barh(df["label"], df["rate"], color=df["color"], height=0.58)
    for bar, row in zip(bars, df.itertuples()):
        ax.text(
            row.rate + 0.35,
            bar.get_y() + bar.get_height() / 2,
            f"{row.rate:.2f}%\n{row.count:,}/{row.n:,}",
            va="center",
            ha="left",
            fontsize=10,
        )

    ax.set_xlabel("Respondents with at least one friction code (%)")
    ax.set_title("Official survey benchmark: Fukui has lower any-friction rates")
    ax.grid(axis="x", color=GRID, linewidth=0.8, alpha=0.7)
    ax.set_xlim(0, max(df["rate"]) + 4)
    ax.invert_yaxis()
    add_source_note(fig, "Source: output/official_fukui/statistical_results_official.json; chi-square p<0.001 for both comparisons")
    return save(fig, "official_any_friction_benchmark_rates.png")


def plot_official_satisfaction_by_friction() -> Path:
    usecols = ["any_friction", "overall_satisfaction_score", "transport_satisfaction_score"]
    df = pd.read_csv(OFFICIAL_FTAS_TAGGED_CSV, usecols=usecols)
    df["any_friction"] = df["any_friction"].astype(bool)
    metrics = [
        ("overall_satisfaction_score", "Overall satisfaction"),
        ("transport_satisfaction_score", "Transport satisfaction"),
    ]

    rows = []
    for col, label in metrics:
        sub = df[["any_friction", col]].dropna().copy()
        sub[col] = sub[col].astype(int)
        for has_friction, status in [(False, "No friction keyword"), (True, "Friction keyword")]:
            grp = sub[sub["any_friction"] == has_friction]
            n = len(grp)
            counts = grp[col].value_counts().reindex([1, 2, 3, 4, 5], fill_value=0)
            for score, count in counts.items():
                rows.append(
                    {
                        "metric": label,
                        "status": status,
                        "score": score,
                        "pct": 100 * count / n if n else 0,
                        "n": n,
                    }
                )
    dist = pd.DataFrame(rows)

    fig, axes = plt.subplots(2, 1, figsize=(10.8, 5.8), sharex=True)
    for ax, (metric, metric_label) in zip(axes, metrics):
        plot_df = dist[dist["metric"] == metric_label]
        statuses = ["No friction keyword", "Friction keyword"]
        left = np.zeros(len(statuses))
        y = np.arange(len(statuses))
        for score in [1, 2, 3, 4, 5]:
            vals = [
                float(plot_df[(plot_df["status"] == status) & (plot_df["score"] == score)]["pct"].iloc[0])
                for status in statuses
            ]
            ax.barh(y, vals, left=left, color=SCORE_COLORS[score], label=str(score), height=0.46)
            for yi, val, start in zip(y, vals, left):
                if val >= 7:
                    ax.text(start + val / 2, yi, f"{val:.0f}%", ha="center", va="center", fontsize=8.5, color="white" if score in [1, 5] else INK)
            left += np.array(vals)

        ns = plot_df.groupby("status")["n"].first().to_dict()
        labels = [f"{status}\nn={ns.get(status, 0):,}" for status in statuses]
        ax.set_yticks(y, labels)
        ax.set_title(metric_label, loc="left", fontsize=12, fontweight="bold")
        ax.set_xlim(0, 100)
        ax.grid(axis="x", color=GRID, linewidth=0.8, alpha=0.7)
        ax.invert_yaxis()

    axes[-1].set_xlabel("Distribution of 1-5 satisfaction scores (%)")
    handles = [plt.Rectangle((0, 0), 1, 1, color=SCORE_COLORS[s]) for s in [1, 2, 3, 4, 5]]
    fig.legend(handles, ["1 lowest", "2", "3", "4", "5 highest"], loc="upper center", ncol=5, frameon=False, bbox_to_anchor=(0.56, 0.93))
    fig.suptitle("Official FTAS survey: satisfaction distributions by friction keyword presence", y=0.99, fontsize=15)
    fig.text(0.01, 0.94, "Mann-Whitney tests: p<0.001 for both score distributions", ha="left", va="top", fontsize=10, color=MUTED)
    add_source_note(fig, "Source: output/official_fukui/ftas_tagged_survey.csv; respondent-level official survey rows")
    return save(fig, "official_satisfaction_by_friction_distribution.png")


def plot_official_top_area_heatmap() -> Path:
    df = pd.read_csv(OFFICIAL_AREA_CSV)
    top_areas = (
        df[["response_area", "n_respondents"]]
        .drop_duplicates()
        .sort_values("n_respondents", ascending=False)
        .head(12)["response_area"]
        .tolist()
    )

    heat = df[df["response_area"].isin(top_areas)].copy()
    heat["label"] = heat["friction_code"].map(LABEL_OVERRIDES).fillna(heat["friction_code"])
    pivot = heat.pivot(index="response_area", columns="label", values="pct_of_respondents")
    pivot = pivot.loc[top_areas]
    cols = pivot.max(axis=0).sort_values(ascending=False).head(8).index
    pivot = pivot[cols]

    annot = pivot.map(lambda v: "" if pd.isna(v) or v == 0 else f"{v:.1f}%")

    fig, ax = plt.subplots(figsize=(15.8, 7.5))
    sns.heatmap(
        pivot,
        ax=ax,
        cmap="YlOrRd",
        linewidths=0.5,
        linecolor="white",
        cbar_kws={"label": "% of respondents"},
        annot=annot,
        fmt="",
    )
    ax.set_title("Official FTAS survey: respondent-level friction rates across top Fukui survey areas")
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.set_xticklabels([wrap_label(t.get_text(), 16) for t in ax.get_xticklabels()], rotation=0, ha="center")
    ax.set_yticklabels([bilingual_area_label(t.get_text()) for t in ax.get_yticklabels()], rotation=0)
    ax.tick_params(axis="x", labelsize=9.5)
    ax.tick_params(axis="y", labelsize=8.5)
    fig.subplots_adjust(left=0.24, right=0.95, bottom=0.12, top=0.91)
    add_source_note(fig, "Source: output/official_fukui/ftas_friction_by_area.csv; top 12 areas by respondent count")
    return save(fig, "official_top12_area_friction_heatmap.png")


def main() -> None:
    setup_style()
    ensure_inputs([
        LANGUAGE_SUMMARY_CSV,
        REVIEW_COMPARISON_CSV,
        JAPANESE_FRICTION_BY_CITY_CSV,
        OFFICIAL_PREF_CSV,
        OFFICIAL_AREA_CSV,
        OFFICIAL_STATS_JSON,
        OFFICIAL_FTAS_TAGGED_CSV,
    ])
    paths = [
        plot_review_language_counts_by_city(),
        plot_review_language_fukui(),
        plot_review_language_difference(),
        plot_japanese_friction_profile_by_area(),
        plot_official_satisfaction_by_friction(),
        plot_official_any_friction_benchmark(),
        plot_official_prefecture_rates(),
        plot_official_prefecture_difference(),
        plot_official_top_area_heatmap(),
    ]
    print("Wrote charts:")
    for path in paths:
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
