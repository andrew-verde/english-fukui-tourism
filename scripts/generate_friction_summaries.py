#!/usr/bin/env python3
"""
generate_friction_summaries.py — Generate summary tables and plots from tagged mentions.

Reads:
  output/friction_analysis/tagged_mentions.csv
  output/friction_analysis/tagged_reviews.csv
  config/friction_codebook.yaml
  config/nudge_mapping.yaml

Writes CSVs to output/friction_analysis/:
  friction_by_city.csv
  friction_by_poi_category.csv
  city_x_friction_crosstab.csv
  poi_category_x_friction_crosstab.csv
  top_excerpts_by_code.csv
  nudge_opportunity_table.csv

Writes figures to output/friction_analysis/figures/:
  friction_by_city.png
  friction_by_poi_category.png
  city_x_friction_heatmap.png
  positive_vs_friction_by_city.png

Usage:
    python scripts/generate_friction_summaries.py
"""

import sys
import os
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("MPLCONFIGDIR", os.path.join(tempfile.gettempdir(), "matplotlib"))

import matplotlib
matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import seaborn as sns
import yaml

from src.friction.tagger import load_codebook
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

OUTPUT_DIR   = Path(__file__).resolve().parent.parent / "output"
FRICTION_DIR = OUTPUT_DIR / "friction_analysis"
FIGURES_DIR  = FRICTION_DIR / "figures"
CONFIG_DIR   = Path(__file__).resolve().parent.parent / "config"

TAGGED_MENTIONS_CSV = FRICTION_DIR / "tagged_mentions.csv"
TAGGED_REVIEWS_CSV  = FRICTION_DIR / "tagged_reviews.csv"
CODEBOOK_PATH       = CONFIG_DIR / "friction_codebook.yaml"
NUDGE_MAPPING_PATH  = CONFIG_DIR / "nudge_mapping.yaml"
NEAR_MISS_CSV       = FRICTION_DIR / "near_miss_sentences.csv"

# Thesis-friendly plot style
plt.rcParams.update({
    "figure.dpi": 150,
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.labelsize": 11,
    "axes.spines.top": False,
    "axes.spines.right": False,
})
CITY_COLORS    = {"Fukui": "#2563EB", "Kanazawa": "#16A34A", "Toyama": "#DC2626"}
FRICTION_COLOR = "#EF4444"
NUDGE_COLOR    = "#22C55E"


# ── Helpers ──────────────────────────────────────────────────────────────────

def _load_codebook_labels(codebook: dict) -> dict[str, str]:
    return {code: attrs["label"] for code, attrs in codebook.items()}


def _friction_codes(codebook: dict) -> list[str]:
    return [c for c, a in codebook.items() if a["type"] == "friction"]


def _nudge_codes(codebook: dict) -> list[str]:
    return [c for c, a in codebook.items() if a["type"] == "nudge"]


def _ensure_code_cols(df: pd.DataFrame, codes: list[str]) -> pd.DataFrame:
    """Ensure bool columns exist for all codes; fill missing with False."""
    for c in codes:
        if c not in df.columns:
            df[c] = False
    return df


# ── Summary tables ────────────────────────────────────────────────────────────

def friction_by_group(df: pd.DataFrame, group_col: str, friction_codes: list[str], labels: dict) -> pd.DataFrame:
    """Return long-form frequency table: group, friction_code, friction_label, count, n_sentences, pct_of_sentences.

    pct_of_sentences = count / n_sentences * 100 (sentence-level denominator).
    n_sentences column is included so downstream consumers know which denominator was used.
    """
    rows = []
    for group_val, grp in df.groupby(group_col):
        n_rows = len(grp)
        for code in friction_codes:
            count = int(grp[code].sum()) if code in grp.columns else 0
            rows.append({
                group_col:           group_val,
                "friction_code":     code,
                "friction_label":    labels.get(code, code),
                "count":             count,
                "n_sentences":       n_rows,
                "pct_of_sentences":  round(100 * count / n_rows, 1) if n_rows else 0,
            })
    return pd.DataFrame(rows)


def crosstab_counts(df: pd.DataFrame, row_col: str, codes: list[str]) -> pd.DataFrame:
    """Pivot: row_col rows × code columns, values = mention counts."""
    rows = {}
    for val, grp in df.groupby(row_col):
        rows[val] = {code: int(grp[code].sum()) for code in codes if code in grp.columns}
    return pd.DataFrame(rows).T.fillna(0).astype(int)


def top_excerpts(df: pd.DataFrame, friction_codes: list[str], n: int = 3) -> pd.DataFrame:
    """Return top N sentence_text examples per friction code."""
    records = []
    for code in friction_codes:
        if code not in df.columns:
            continue
        hits = df[df[code] == True].copy()
        if hits.empty:
            continue
        # Score by number of codes matched (most-coded sentences are richest examples)
        hits["_n_codes"] = hits[friction_codes].sum(axis=1)
        top = hits.nlargest(n, "_n_codes")
        for _, row in top.iterrows():
            records.append({
                "friction_code":  code,
                "city":           row.get("city", ""),
                "poi_name":       row.get("poi_name", ""),
                "poi_category":   row.get("poi_category", ""),
                "sentence_text":  row.get("sentence_text", ""),
                "review_id":      row.get("review_id", ""),
            })
    return pd.DataFrame(records)


def nudge_opportunity_table(
    tagged_mentions: pd.DataFrame,
    codebook: dict,
    nudge_mapping_path: Path,
) -> pd.DataFrame:
    """Build nudge opportunity table: mapping scaffold + computed evidence counts."""
    if not nudge_mapping_path.exists():
        logger.warning(f"nudge_mapping.yaml not found: {nudge_mapping_path}")
        return pd.DataFrame()

    with open(nudge_mapping_path) as f:
        mapping = yaml.safe_load(f).get("nudge_mappings", {})

    friction_codes_list = _friction_codes(codebook)
    rows = []
    for code, attrs in mapping.items():
        if code not in tagged_mentions.columns:
            hits = pd.DataFrame()
        else:
            hits = tagged_mentions[tagged_mentions[code] == True]

        evidence_count = len(hits)
        cities_observed = sorted(hits["city"].unique().tolist()) if not hits.empty and "city" in hits.columns else []
        poi_cats = sorted(hits["poi_category"].unique().tolist()) if not hits.empty and "poi_category" in hits.columns else []

        rows.append({
            "friction_code":         code,
            "friction_label":        attrs.get("friction_label", ""),
            "likely_journey_stage":  attrs.get("likely_journey_stage", ""),
            "possible_nudge_type":   attrs.get("possible_nudge_type", ""),
            "example_intervention":  attrs.get("example_intervention", ""),
            "evidence_count":        evidence_count,
            "cities_observed":       ", ".join(cities_observed),
            "poi_categories_observed": ", ".join(poi_cats),
        })
    return pd.DataFrame(rows)


# ── Plots ─────────────────────────────────────────────────────────────────────

def plot_friction_by_city(
    freq_df: pd.DataFrame,
    labels: dict,
    output_path: Path,
):
    """Grouped horizontal bar: friction code frequency (%) by city."""
    cities = sorted(freq_df["city"].unique())
    codes = freq_df["friction_code"].unique().tolist()
    n_codes = len(codes)
    n_cities = len(cities)

    fig, ax = plt.subplots(figsize=(10, max(4, n_codes * 0.6)))
    bar_h = 0.8 / n_cities
    y_pos = np.arange(n_codes)

    for i, city in enumerate(cities):
        pct_col = "pct_of_sentences" if "pct_of_sentences" in freq_df.columns else "pct"
        city_data = freq_df[freq_df["city"] == city].set_index("friction_code")[pct_col]
        vals = [float(city_data.get(c, 0)) for c in codes]
        offset = (i - n_cities / 2 + 0.5) * bar_h
        ax.barh(y_pos + offset, vals, bar_h * 0.9,
                label=city, color=CITY_COLORS.get(city, f"C{i}"), alpha=0.85)

    ax.set_yticks(y_pos)
    ax.set_yticklabels([labels.get(c, c) for c in codes])
    ax.set_xlabel("% of mentions in city")
    ax.set_title("Friction Code Frequency by City")
    ax.legend(title="City", bbox_to_anchor=(1.01, 1), loc="upper left")
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    logger.info(f"  Saved: {output_path}")


def plot_friction_by_poi_category(
    freq_df: pd.DataFrame,
    labels: dict,
    output_path: Path,
):
    """Horizontal bar: friction code frequency (%) by POI category."""
    pct_col = "pct_of_sentences" if "pct_of_sentences" in freq_df.columns else "pct"
    pivot = freq_df.pivot_table(index="friction_code", columns="poi_category", values=pct_col, fill_value=0)
    fig, ax = plt.subplots(figsize=(10, max(4, len(pivot) * 0.6)))
    pivot.plot(kind="barh", ax=ax, width=0.7)
    ax.set_yticklabels([labels.get(c, c) for c in pivot.index])
    ax.set_xlabel("% of mentions in category")
    ax.set_title("Friction Code Frequency by POI Category")
    ax.legend(title="POI Category", bbox_to_anchor=(1.01, 1), loc="upper left")
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    logger.info(f"  Saved: {output_path}")


def plot_city_x_friction_heatmap(
    crosstab: pd.DataFrame,
    pct_df: pd.DataFrame,
    labels: dict,
    output_path: Path,
):
    """Heatmap: city rows × friction code columns, dual annotation (count + %)."""
    import numpy as np
    display = crosstab.rename(columns=labels)
    pct_display = pct_df.rename(columns=labels)

    # Build string annotation matrix: "n\n(p%)"
    annot = np.empty(display.shape, dtype=object)
    for i, city in enumerate(display.index):
        for j, col in enumerate(display.columns):
            count = int(display.iloc[i, j])
            pct   = float(pct_display.iloc[i, j])
            annot[i, j] = f"{count}\n({pct:.1f}%)"

    fig, ax = plt.subplots(figsize=(max(8, len(display.columns) * 0.9), max(3, len(display) * 0.7)))
    sns.heatmap(
        display, annot=annot, fmt="", cmap="Blues",
        linewidths=0.4, ax=ax, cbar_kws={"label": "Mention count"},
        annot_kws={"size": 8},
    )
    ax.set_title("Friction Mentions: City × Code  (count, % of city sentences)")
    ax.set_xlabel("")
    ax.set_ylabel("")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    logger.info(f"  Saved: {output_path}")


def plot_positive_vs_friction(
    tagged_mentions: pd.DataFrame,
    friction_codes: list[str],
    nudge_codes_list: list[str],
    output_path: Path,
):
    """Stacked bar: friction vs nudge mention counts by city."""
    rows = []
    for city, grp in tagged_mentions.groupby("city"):
        f_count = int(grp[friction_codes].any(axis=1).sum()) if all(c in grp.columns for c in friction_codes) else 0
        n_count = int(grp[nudge_codes_list].any(axis=1).sum()) if all(c in grp.columns for c in nudge_codes_list) else 0
        rows.append({"city": city, "friction": f_count, "nudge": n_count})
    summary = pd.DataFrame(rows).set_index("city")

    fig, ax = plt.subplots(figsize=(7, 4))
    x = np.arange(len(summary))
    w = 0.35
    ax.bar(x - w/2, summary["friction"], w, label="Friction mentions", color=FRICTION_COLOR, alpha=0.85)
    ax.bar(x + w/2, summary["nudge"],    w, label="Nudge/positive mentions", color=NUDGE_COLOR, alpha=0.85)
    ax.set_xticks(x)
    ax.set_xticklabels(summary.index)
    ax.set_ylabel("Mention count")
    ax.set_title("Friction vs Positive Mentions by City")
    ax.legend()
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    logger.info(f"  Saved: {output_path}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    for path in [TAGGED_MENTIONS_CSV, TAGGED_REVIEWS_CSV]:
        if not path.exists():
            logger.error(f"Input not found: {path}")
            logger.error("Run auto_tag_friction_codes.py first.")
            sys.exit(1)

    logger.info("=" * 55)
    logger.info("Generate friction summary tables and plots")
    logger.info("=" * 55)

    codebook = load_codebook(CODEBOOK_PATH)
    labels   = _load_codebook_labels(codebook)
    f_codes  = _friction_codes(codebook)
    n_codes  = _nudge_codes(codebook)

    mentions = pd.read_csv(TAGGED_MENTIONS_CSV)
    mentions = _ensure_code_cols(mentions, f_codes + n_codes)
    logger.info(f"Mentions loaded: {len(mentions)} rows")

    FRICTION_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    # ── Frequency tables ─────────────────────────────────────────────────────

    freq_city = friction_by_group(mentions, "city", f_codes, labels)
    freq_city.to_csv(FRICTION_DIR / "friction_by_city.csv", index=False)
    logger.info("  Written: friction_by_city.csv")

    freq_cat = friction_by_group(mentions, "poi_category", f_codes, labels)
    freq_cat.to_csv(FRICTION_DIR / "friction_by_poi_category.csv", index=False)
    logger.info("  Written: friction_by_poi_category.csv")

    # ── Cross-tabs ────────────────────────────────────────────────────────────

    city_crosstab = crosstab_counts(mentions, "city", f_codes)
    city_crosstab.to_csv(FRICTION_DIR / "city_x_friction_crosstab.csv")
    logger.info("  Written: city_x_friction_crosstab.csv")

    # pct table for dual-annotation heatmap
    city_n = {c: len(mentions[mentions.city == c]) for c in city_crosstab.index}
    city_pct = city_crosstab.copy().astype(float)
    for c in city_crosstab.index:
        city_pct.loc[c] = city_crosstab.loc[c] / max(city_n.get(c, 1), 1) * 100

    cat_crosstab = crosstab_counts(mentions, "poi_category", f_codes)
    cat_crosstab.to_csv(FRICTION_DIR / "poi_category_x_friction_crosstab.csv")
    logger.info("  Written: poi_category_x_friction_crosstab.csv")

    # ── Excerpts ──────────────────────────────────────────────────────────────

    excerpts = top_excerpts(mentions, f_codes, n=3)
    excerpts.to_csv(FRICTION_DIR / "top_excerpts_by_code.csv", index=False)
    logger.info("  Written: top_excerpts_by_code.csv")

    # ── Nudge opportunity table ───────────────────────────────────────────────

    nudge_table = nudge_opportunity_table(mentions, codebook, NUDGE_MAPPING_PATH)
    if not nudge_table.empty:
        nudge_table.to_csv(FRICTION_DIR / "nudge_opportunity_table.csv", index=False)
        logger.info("  Written: nudge_opportunity_table.csv")

    # ── Diagnostics: near-miss sentences (common friction cues but no code) ──
    try:
        cue_re = r"\b(?:" \
                 r"hard|difficult|inconvenient|far|remote|limited|" \
                 r"no\s+english|japanese\s+only|language\s+barrier|" \
                 r"closed|closing|hours|" \
                 r"crowd|crowded|busy|wait|waited|waiting|queue|queued|line|lines|delayed|delay|" \
                 r"expensive|overpriced|pricey|rip[- ]?off|overcharged|" \
                 r"dirty|unclean|filthy|smell|smelly|toilet|bathroom|restroom|" \
                 r"stairs|steep|wheelchair|uneven|slippery" \
                 r")\b"
        has_cue = mentions["sentence_text"].astype(str).str.contains(cue_re, case=False, na=False, regex=True)
        has_friction = mentions[f_codes].any(axis=1)
        near_miss = mentions.loc[has_cue & ~has_friction, ["city", "poi_name", "poi_category", "sentence_text", "review_id"]].copy()
        if not near_miss.empty:
            population_n = len(near_miss)
            # Cap raised to 200 so the full population is captured at typical scale.
            # If population exceeds 200, a random sample is taken and the log notes it.
            sample_n = min(200, population_n)
            if sample_n < population_n:
                near_miss = near_miss.sample(sample_n, random_state=0)
            near_miss.to_csv(NEAR_MISS_CSV, index=False)
            captured = "full population" if sample_n == population_n else f"sample {sample_n}/{population_n}"
            logger.info(f"  Written: near_miss_sentences.csv ({captured})")
    except Exception as e:
        logger.warning(f"Near-miss diagnostic generation failed: {e}")

    # ── Plots ─────────────────────────────────────────────────────────────────

    logger.info("Generating plots...")
    plot_friction_by_city(freq_city, labels, FIGURES_DIR / "friction_by_city.png")
    plot_friction_by_poi_category(freq_cat, labels, FIGURES_DIR / "friction_by_poi_category.png")
    plot_city_x_friction_heatmap(city_crosstab, city_pct, labels, FIGURES_DIR / "city_x_friction_heatmap.png")
    plot_positive_vs_friction(
        mentions, f_codes, n_codes,
        FIGURES_DIR / "positive_vs_friction_by_city.png",
    )

    logger.info("")
    logger.info("Summary generation complete")
    logger.info(f"  CSVs:   {FRICTION_DIR}")
    logger.info(f"  Plots:  {FIGURES_DIR}")
    logger.info("=" * 55)


if __name__ == "__main__":
    main()
