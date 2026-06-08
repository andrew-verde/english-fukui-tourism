#!/usr/bin/env python3
"""
generate_presentation_figures.py — Generate presentation figure files.

Reads tagged_mentions.csv, reviews_unified.csv, top_excerpts_by_code.csv,
nudge_opportunity_table.csv, and config/friction_codebook.yaml.

Writes to output/friction_analysis/presentation_figures/:
  fukui_frequency_difference.png  Fukui frequency difference vs Kanazawa/Toyama baseline
  city_friction_heatmap.png       Full city × code heatmap (count + %)
  sentiment_distribution.png      VADER sentiment violin + strip by city
  friction_quote_examples.png     Top friction quote examples (Fukui-first)
  nudge_opportunity_table.png     Evidence-ranked nudge candidate table (codes with n>=1 only)
  fukui_frequency_comparison.csv  Fukui vs baseline rates + delta

All rates are sentence-level (denominator = total sentences per city).
Findings are descriptive; interpret directionally, not inferentially.

Usage:
    python scripts/generate_presentation_figures.py
"""

import sys
import os
import tempfile
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("MPLCONFIGDIR", os.path.join(tempfile.gettempdir(), "matplotlib"))

import matplotlib
matplotlib.use("Agg", force=True)
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import yaml

from src.friction.tagger import load_codebook
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

OUTPUT_DIR   = Path(__file__).resolve().parent.parent / "output"
FRICTION_DIR = OUTPUT_DIR / "friction_analysis"
PRES_DIR     = FRICTION_DIR / "presentation_figures"
CONFIG_DIR   = Path(__file__).resolve().parent.parent / "config"

TAGGED_MENTIONS_CSV = FRICTION_DIR / "tagged_mentions.csv"
TAGGED_REVIEWS_CSV  = FRICTION_DIR / "tagged_reviews.csv"
REVIEWS_CSV         = FRICTION_DIR / "reviews_unified.csv"
EXCERPTS_CSV        = FRICTION_DIR / "top_excerpts_by_code.csv"
NUDGE_CSV           = FRICTION_DIR / "nudge_opportunity_table.csv"
CODEBOOK_PATH       = CONFIG_DIR / "friction_codebook.yaml"

CITY_COLORS = {"Fukui": "#2563EB", "Kanazawa": "#16A34A", "Toyama": "#DC2626"}
CITIES = ["Fukui", "Kanazawa", "Toyama"]
DISPLAY_PLACE = {"Fukui": "Fukui", "Kanazawa": "Kanazawa", "Toyama": "Toyama"}

LABELS = {
    "transport_access":          "Transport & Access",
    "wayfinding_signage":        "Wayfinding & Signage",
    "english_information_gap":   "English Info Gap",
    "staff_communication":       "Staff Communication",
    "booking_ticketing":         "Booking & Ticketing",
    "waiting_crowding":          "Waiting & Crowding",
    "price_value":               "Price & Value",
    "cleanliness_comfort":       "Cleanliness",
    "opening_hours_availability":"Opening Hours",
    "itinerary_fit_time_cost":   "Itinerary Fit",
    "accessibility_mobility":    "Accessibility",
    "food_amenities_gap":        "Food & Amenities",
}

plt.rcParams.update({
    "font.family": "sans-serif", "font.size": 14,
    "axes.titlesize": 18, "axes.labelsize": 14,
    "xtick.labelsize": 13, "ytick.labelsize": 13,
    "axes.spines.top": False, "axes.spines.right": False,
    "figure.dpi": 180,
})


def _check_inputs():
    for p in [TAGGED_MENTIONS_CSV, TAGGED_REVIEWS_CSV, REVIEWS_CSV]:
        if not p.exists():
            logger.error(f"Required input not found: {p}")
            logger.error("Run full pipeline first: make friction-all")
            sys.exit(1)


def _build_pct_tables(mentions, friction_codes):
    """Return (crosstab counts, pct per city, city mention counts)."""
    city_n = {c: len(mentions[mentions.city == c]) for c in CITIES if c in mentions.city.values}
    counts = {}
    for city in CITIES:
        grp = mentions[mentions.city == city]
        counts[city] = {code: int(grp[code].sum()) if code in grp.columns else 0
                        for code in friction_codes}
    ct = pd.DataFrame(counts).T.fillna(0).astype(int)
    pct = ct.copy().astype(float)
    for city in ct.index:
        pct.loc[city] = ct.loc[city] / max(city_n.get(city, 1), 1) * 100
    return ct, pct, city_n


# ── Figure: Diverging bar — Fukui vs baseline ────────────────────────────────

def figure_frequency_difference(mentions, friction_codes, city_n):
    baseline = (
        pd.Series({c: 0.0 for c in friction_codes})
        if not any(c in mentions.columns for c in friction_codes)
        else pd.DataFrame({
            city: {
                code: 100 * int(mentions[mentions.city == city][code].sum() if code in mentions.columns else 0)
                      / max(city_n.get(city, 1), 1)
                for code in friction_codes
            }
            for city in ["Kanazawa", "Toyama"]
        }).mean(axis=1)
    )

    fukui_n   = city_n.get("Fukui", 1)
    fukui_pct = pd.Series({
        code: 100 * int(mentions[mentions.city == "Fukui"][code].sum() if code in mentions.columns else 0) / max(fukui_n, 1)
        for code in friction_codes
    })
    fukui_counts = pd.Series({
        code: int(mentions[mentions.city == "Fukui"][code].sum() if code in mentions.columns else 0)
        for code in friction_codes
    })
    kaz_counts = pd.Series({
        code: int(mentions[mentions.city == "Kanazawa"][code].sum() if code in mentions.columns else 0)
        for code in friction_codes
    })
    toy_counts = pd.Series({
        code: int(mentions[mentions.city == "Toyama"][code].sum() if code in mentions.columns else 0)
        for code in friction_codes
    })

    delta = fukui_pct - baseline

    # Show all codes where delta != 0 (including Fukui-exclusive and negative bars)
    SHOW = sorted(
        [c for c in friction_codes if delta[c] != 0],
        key=lambda c: delta[c]
    )

    if not SHOW:
        logger.warning("No codes with non-zero delta — frequency-difference figure will be empty")
        return None, None

    # Write comparison CSV
    comp_df = pd.DataFrame({
        "friction_code":         friction_codes,
        "friction_label":        [LABELS.get(c, c) for c in friction_codes],
        "fukui_pct":             [round(fukui_pct[c], 2) for c in friction_codes],
        "baseline_avg_pct":      [round(baseline[c], 2) for c in friction_codes],
        "delta_pp":              [round(delta[c], 2) for c in friction_codes],
        "fukui_count":           [fukui_counts[c] for c in friction_codes],
        "fukui_vs_baseline_ratio": [
            round(fukui_pct[c] / baseline[c], 2) if baseline[c] > 0 else None
            for c in friction_codes
        ],
    }).sort_values("delta_pp", ascending=False)
    comp_df.to_csv(FRICTION_DIR / "fukui_frequency_comparison.csv", index=False)
    logger.info("  Written: fukui_frequency_comparison.csv")

    fig, ax = plt.subplots(figsize=(12, max(5, len(SHOW) * 0.65 + 1.5)))
    colors = ["#2563EB" if delta[c] >= 0 else "#EF4444" for c in SHOW]
    y = np.arange(len(SHOW))

    ax.barh(y, [delta[c] for c in SHOW], color=colors, alpha=0.88,
            edgecolor="white", height=0.65)
    ax.axvline(0, color="#1e293b", linewidth=1.2)
    ax.set_yticks(y)
    ax.set_yticklabels([LABELS.get(c, c) for c in SHOW], fontsize=13)
    ax.set_xlabel("Percentage-point difference\nvs Kanazawa / Toyama baseline", fontsize=12)
    ax.set_title("Observed frequency differences — descriptive only",
                 fontweight="bold", pad=14)
    ax.spines["left"].set_visible(False)
    ax.tick_params(left=False)
    ax.grid(axis="x", linestyle="--", alpha=0.35, color="#94a3b8")

    # Raw count annotations
    x_max = max(abs(delta[c]) for c in SHOW)
    for i, code in enumerate(SHOW):
        val = delta[code]
        fc  = fukui_counts[code]
        kc  = kaz_counts[code]
        tc  = toy_counts[code]
        if val >= 0:
            label = f"(Fukui n={fc})"
            offset = x_max * 0.04
            ha = "left"
            ax.text(val + offset, i, label, va="center", ha=ha,
                    fontsize=9.5, color="#1e293b")
        else:
            label = f"(Kan n={kc}, Toy n={tc})"
            offset = x_max * 0.04
            ha = "right"
            ax.text(val - offset, i, label, va="center", ha=ha,
                    fontsize=9.5, color="#1e293b")

    legend_handles = [
        mpatches.Patch(color="#2563EB", label="Fukui higher than baseline"),
        mpatches.Patch(color="#EF4444", label="Fukui lower than baseline"),
    ]
    ax.legend(handles=legend_handles, fontsize=11, loc="lower right", framealpha=0.9)
    ax.set_xlim(
        min(delta[c] for c in SHOW) - x_max * 0.35,
        max(delta[c] for c in SHOW) + x_max * 0.45,
    )

    n_str = " · ".join(f"{DISPLAY_PLACE.get(c, c)} n={city_n.get(c, 0)} sentences" for c in CITIES)
    plt.tight_layout(rect=[0, 0.12, 1, 1])
    fig.text(0.01, 0.04,
             f"Sentence-level analysis  |  {n_str}\n"
             "Interpret directionally — sample size not sufficient for statistical inference.",
             fontsize=8.5, color="#64748b", transform=fig.transFigure)

    out = PRES_DIR / "fukui_frequency_difference.png"
    plt.savefig(out, bbox_inches="tight", facecolor="white")
    plt.close()
    return out, FRICTION_DIR / "fukui_frequency_comparison.csv"


# ── Figure: Heatmap — count + % dual annotation ─────────────────────────────

def figure_heatmap(ct, pct, city_n):
    display_ct  = ct.rename(columns=LABELS)
    display_pct = pct.rename(columns=LABELS)
    display_ct.index = [DISPLAY_PLACE.get(c, c) for c in display_ct.index]
    display_pct.index = [DISPLAY_PLACE.get(c, c) for c in display_pct.index]

    annot = np.empty(display_ct.shape, dtype=object)
    for i in range(display_ct.shape[0]):
        for j in range(display_ct.shape[1]):
            count = int(display_ct.iloc[i, j])
            p     = float(display_pct.iloc[i, j])
            annot[i, j] = f"{count}\n({p:.1f}%)"

    fig, ax = plt.subplots(figsize=(14, 4.2))
    sns.heatmap(display_ct, annot=annot, fmt="", cmap="YlOrRd",
                linewidths=0.6, ax=ax,
                cbar_kws={"label": "Mention count", "shrink": 0.8},
                annot_kws={"size": 10})
    ax.set_title("Friction rate by prefecture  (raw count, % of sentences)",
                 fontweight="bold", pad=14)
    ax.set_xlabel(""); ax.set_ylabel("")
    plt.xticks(rotation=38, ha="right", fontsize=11)
    plt.yticks(fontsize=13, rotation=0)

    n_str = "  |  ".join(
        f"{DISPLAY_PLACE.get(c, c)}: {city_n.get(c,0)} sentences ({len(pd.read_csv(REVIEWS_CSV)[pd.read_csv(REVIEWS_CSV).city==c])} reviews)"
        for c in CITIES
    )
    plt.tight_layout(rect=[0, 0.10, 1, 1])
    fig.text(0.01, 0.02, n_str, fontsize=9, color="#64748b", transform=fig.transFigure)
    out = PRES_DIR / "city_friction_heatmap.png"
    plt.savefig(out, bbox_inches="tight", facecolor="white")
    plt.close()
    return out


# ── Figure: Sentiment violin + strip ────────────────────────────────────────

def figure_sentiment(reviews, city_n_reviews):
    fig, ax = plt.subplots(figsize=(9, 6))
    parts = ax.violinplot(
        [reviews[reviews.city == c]["vader_compound"].values for c in CITIES],
        positions=[0, 1, 2], widths=0.55, showmedians=False, showextrema=False,
    )
    for pc, city in zip(parts["bodies"], CITIES):
        pc.set_facecolor(CITY_COLORS[city])
        pc.set_alpha(0.30)
        pc.set_edgecolor(CITY_COLORS[city])

    rng = np.random.default_rng(42)
    for i, city in enumerate(CITIES):
        vals = reviews[reviews.city == city]["vader_compound"].values
        jitter = rng.uniform(-0.08, 0.08, size=len(vals))
        ax.scatter(i + jitter, vals, color=CITY_COLORS[city], s=28, alpha=0.65, zorder=3)

    for i, city in enumerate(CITIES):
        med = reviews[reviews.city == city]["vader_compound"].median()
        ax.hlines(med, i - 0.22, i + 0.22, color=CITY_COLORS[city], linewidth=2.5, zorder=4)
        ax.text(i + 0.26, med, f"med={med:.2f}", va="center",
                fontsize=11.5, color=CITY_COLORS[city], fontweight="bold")

    ax.axhline(0, color="#94a3b8", linewidth=0.9, linestyle="--")
    ax.set_xticks([0, 1, 2])
    ax.set_xticklabels(
        [f"{DISPLAY_PLACE.get(c, c)}\n(n={city_n_reviews.get(c, 0)} reviews)" for c in CITIES],
        fontsize=14, fontweight="bold",
    )
    for label, city in zip(ax.get_xticklabels(), CITIES):
        label.set_color(CITY_COLORS[city])

    ax.set_ylabel("VADER compound  (−1 negative → +1 positive)", fontsize=12)
    ax.set_title("Sentiment skews positive across all prefectures", fontweight="bold", pad=12)
    ax.set_ylim(-1.05, 1.1)
    plt.tight_layout()
    out = PRES_DIR / "sentiment_distribution.png"
    plt.savefig(out, bbox_inches="tight", facecolor="white")
    plt.close()
    return out


# ── Figure: Top friction excerpts ───────────────────────────────────────────

def figure_excerpts(mentions, friction_codes, city_n):
    # Top codes by Fukui absolute count, then by total
    fukui_counts = {
        code: int(mentions[mentions.city == "Fukui"][code].sum() if code in mentions.columns else 0)
        for code in friction_codes
    }
    total_counts = {
        code: int(mentions[code].sum() if code in mentions.columns else 0)
        for code in friction_codes
    }
    top5 = sorted(
        [c for c in friction_codes if total_counts[c] > 0],
        key=lambda c: (fukui_counts[c], total_counts[c]),
        reverse=True,
    )[:5]

    if not top5:
        logger.warning("No friction hits — skipping excerpts figure")
        return None

    quote_rows = []
    for code in top5:
        label = LABELS.get(code, code)
        # Prefer Fukui hits, fall back to any city
        hits = mentions[(mentions.city == "Fukui") & (mentions[code] == True)].copy() \
               if code in mentions.columns else pd.DataFrame()
        if hits.empty:
            hits = mentions[mentions[code] == True].copy() if code in mentions.columns else pd.DataFrame()
        if hits.empty:
            continue
        row = hits.sample(1, random_state=42).iloc[0]
        quote_rows.append((label, str(row["sentence_text"])[:160], DISPLAY_PLACE.get(row["city"], row["city"]), row["poi_name"]))

    if not quote_rows:
        return None

    fig, ax = plt.subplots(figsize=(13, max(6, len(quote_rows) * 1.5 + 1)))
    ax.axis("off")
    ax.set_title("Illustrative friction quotes — keyword-matched sentences",
                 fontweight="bold", fontsize=17, pad=16)

    y = 0.93
    for label, quote, city, poi in quote_rows:
        ax.text(0.0, y, f"▸ {label}", fontsize=13, fontweight="bold",
                color="#1e293b", transform=ax.transAxes, va="top")
        wrapped = textwrap.fill(f'"{quote}"', width=110)
        ax.text(0.02, y - 0.06, wrapped, fontsize=11, color="#334155",
                fontstyle="italic", transform=ax.transAxes, va="top")
        ax.text(0.02, y - 0.13, f"— {city}, {poi}", fontsize=9.5, color="#64748b",
                transform=ax.transAxes, va="top")
        y -= 0.19

    fig.text(0.0, 0.01,
             "Quotes are illustrative keyword matches, not representative samples.",
             fontsize=9, color="#94a3b8")
    plt.tight_layout()
    out = PRES_DIR / "friction_quote_examples.png"
    plt.savefig(out, bbox_inches="tight", facecolor="white")
    plt.close()
    return out


# ── Figure: Nudge opportunity table (evidence ≥ 1 only) ─────────────────────

def figure_nudge_table():
    if not NUDGE_CSV.exists():
        logger.warning(f"nudge_opportunity_table.csv not found — skipping nudge-opportunity figure")
        return None

    nudge_df = pd.read_csv(NUDGE_CSV)
    # Show only codes with evidence (evidence_count >= 1)
    show = nudge_df[nudge_df["evidence_count"] >= 1].sort_values("evidence_count", ascending=False)
    if show.empty:
        logger.warning("No nudge rows with evidence >= 1 — skipping nudge-opportunity figure")
        return None

    show = show[["friction_label", "likely_journey_stage", "possible_nudge_type",
                 "evidence_count", "cities_observed"]].copy()
    show["cities_observed"] = show["cities_observed"].fillna("").astype(str)
    show["cities_observed"] = show["cities_observed"].replace(
        {"Kanazawa": "Kanazawa"}, regex=True
    )
    show.columns = ["Friction", "Journey Stage", "Nudge Type", "Evidence\n(mentions)", "Prefectures"]
    show["Evidence\n(mentions)"] = show["Evidence\n(mentions)"].astype(int)

    fig, ax = plt.subplots(figsize=(14, max(3.5, len(show) * 0.7 + 1.5)))
    ax.axis("off")
    ax.set_title("Candidate nudge opportunities — grounded in observed friction mentions",
                 fontweight="bold", fontsize=16, pad=14)

    tbl = ax.table(
        cellText=show.values,
        colLabels=show.columns,
        cellLoc="left", loc="center",
        bbox=[0, 0, 1, 0.88],
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(10.5)
    for (r, c), cell in tbl.get_celld().items():
        cell.set_edgecolor("#e2e8f0")
        cell.set_text_props(wrap=True)
        if r == 0:
            cell.set_facecolor("#1e293b")
            cell.set_text_props(color="white", fontweight="bold")
        elif r % 2 == 0:
            cell.set_facecolor("#f8fafc")
        else:
            cell.set_facecolor("white")
    tbl.auto_set_column_width(list(range(len(show.columns))))

    fig.text(0.01, 0.01,
             "Interventions are candidate suggestions based on observed keyword frequencies. "
             "Codes with zero evidence omitted. Interpret directionally.",
             fontsize=8.5, color="#64748b")
    plt.tight_layout()
    out = PRES_DIR / "nudge_opportunity_table.png"
    plt.savefig(out, bbox_inches="tight", facecolor="white")
    plt.close()
    return out


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    _check_inputs()
    PRES_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 55)
    logger.info("Generate presentation figures")
    logger.info("=" * 55)

    codebook       = load_codebook(CODEBOOK_PATH)
    friction_codes = [c for c, a in codebook.items() if a["type"] == "friction"]

    mentions = pd.read_csv(TAGGED_MENTIONS_CSV)
    for code in friction_codes:
        if code not in mentions.columns:
            mentions[code] = False

    reviews = pd.read_csv(REVIEWS_CSV)
    city_n_reviews  = {c: len(reviews[reviews.city == c]) for c in CITIES}

    ct, pct, city_n = _build_pct_tables(mentions, friction_codes)

    out1, comp_csv = figure_frequency_difference(mentions, friction_codes, city_n)
    if out1:
        logger.info(f"  Saved: {out1}")

    out2 = figure_heatmap(ct, pct, city_n)
    logger.info(f"  Saved: {out2}")

    out3 = figure_sentiment(reviews, city_n_reviews)
    logger.info(f"  Saved: {out3}")

    out4 = figure_excerpts(mentions, friction_codes, city_n)
    if out4:
        logger.info(f"  Saved: {out4}")

    out5 = figure_nudge_table()
    if out5:
        logger.info(f"  Saved: {out5}")

    logger.info("")
    logger.info("Presentation figures complete")
    logger.info(f"  Output: {PRES_DIR}")
    logger.info("=" * 55)


if __name__ == "__main__":
    main()
