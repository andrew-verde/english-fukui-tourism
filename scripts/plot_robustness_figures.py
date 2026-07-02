#!/usr/bin/env python3
"""Render the two synthetic-control ROBUSTNESS figures from the causal-robustness CSVs.

Reads the committed in-space / in-time placebo outputs and writes publication-grade
PNGs (300 dpi) to output/national_stats/causal_robustness/figures/. Pure function of
the CSVs -- no network, no RNG. Downstream of the `causal-robustness` target.

Figures:
  fig4_placebo_distribution.png -- in-space placebo test on the opening window:
                                    the treated corridor in the right tail of the
                                    ~1709-donor null (the LEAD robustness result).
  fig5_intime_placebo.png       -- backdated (2023-03) in-time placebo negative
                                    control: the real 2024 opening spike vanishes.
"""
from __future__ import annotations
import argparse
import os
from pathlib import Path

# --- headless, self-contained render (writable MPLCONFIGDIR before pyplot import) ---
os.environ.setdefault("MPLCONFIGDIR", str(Path(
    os.environ.get("TMPDIR", "/tmp")) / "mplconfig_robustness"))
Path(os.environ["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.gridspec import GridSpec


# ---- minimal publication style (self-contained; no external skill dependency) ----
def _style():
    plt.rcParams.update({
        "figure.dpi": 110, "savefig.dpi": 300,
        "font.size": 9, "axes.titlesize": 9, "axes.labelsize": 8,
        "xtick.labelsize": 8, "ytick.labelsize": 8, "legend.fontsize": 7.5,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.edgecolor": "#333333", "axes.linewidth": 0.8,
        "axes.grid": False, "figure.facecolor": "white", "axes.facecolor": "white",
        "font.family": ["DejaVu Sans"],
    })


# palette -- matches the synthesis figures for cross-figure visual consistency
C_DURABLE = "#2c7fb8"   # well-fit corridor (durable/positive corridor blue)
C_TRANS   = "#e6820a"   # transient orange
C_NONE    = "#9aa0a6"   # null / "none" grey
C_SHK     = "#c0392b"   # treated / Shinkansen red accent (Fukui City headline)

# the four well-fit, placebo-extreme corridor units (p_open_1s < 0.10 AND good_fit)
CORRIDOR = {"Fukui City", "Tsuruga", "Sakai", "Eiheiji"}


def _unit_color(en: str) -> str:
    if en == "Fukui City":
        return C_SHK
    if en in CORRIDOR:
        return C_DURABLE
    return C_NONE


def fig4_placebo_distribution(insp: pd.DataFrame, dist: pd.DataFrame,
                              metrics: dict, out: Path) -> None:
    """In-space placebo test on the opening window (the money figure)."""
    _style()
    null = dist["open_pct"].to_numpy()
    p90 = float(np.percentile(null, 90))   # one-sided placebo p = 0.10 reference

    treated = insp.sort_values("open_pct").reset_index(drop=True)
    y = np.arange(len(treated))
    # clip x to the informative window: all 17 treated units + the null's dense
    # body. The null has a sparse long tail (a few poor pre-fit donors reach
    # +380%); those are counted in the p-value but truncated from the axis so the
    # treated corridor and the p<0.10 threshold do not collapse into the left edge.
    xlo, xmax = -92.0, 78.0
    n_null_beyond = int((null > xmax).sum())

    fig = plt.figure(figsize=(7.0, 6.4))
    gs = GridSpec(2, 1, height_ratios=[3.05, 1.0], hspace=0.10, figure=fig)
    ax = fig.add_subplot(gs[0])      # treated dot plot
    axn = fig.add_subplot(gs[1], sharex=ax)   # null strip

    # shared tail shading + reference lines across both panels
    for a in (ax, axn):
        a.axvspan(p90, xmax, color="#fdece0", zorder=0)   # right-tail p<0.10 band
        a.axvline(0.0, color="#cccccc", lw=0.8, ls="-", zorder=1)
        a.axvline(p90, color=C_TRANS, lw=1.0, ls="--", zorder=2)

    # ---- top: 17 treated municipalities as a sorted dot plot ----
    for i, row in treated.iterrows():
        col = _unit_color(row.en)
        good = bool(row.good_fit)
        # thin neutral stem to zero (lollipop) for read-off
        ax.plot([0, row.open_pct], [i, i], color="#dddddd", lw=0.8, zorder=1)
        ax.scatter(row.open_pct, i, s=78,
                   facecolor=col if good else "none", edgecolor=col,
                   linewidth=1.0 if good else 1.7, marker="o", zorder=4)
    ax.set_yticks(y)
    ax.set_yticklabels(treated.en, fontsize=7.5)
    for lbl, en in zip(ax.get_yticklabels(), treated.en):
        lbl.set_color(_unit_color(en) if en in CORRIDOR else "#333333")
        if en in CORRIDOR:
            lbl.set_fontweight("bold")
    ax.set_ylim(-0.8, len(treated) - 0.2)
    ax.tick_params(axis="x", labelbottom=False)
    ax.set_ylabel("Treated Fukui municipality")
    ax.set_title("In-space placebo test: the Shinkansen corridor sits in the right\n"
                 "tail of the 1,709-donor opening-window null", fontsize=9)

    # headline annotation on Fukui City
    fc = treated[treated.en == "Fukui City"].iloc[0]
    fy = int(treated.index[treated.en == "Fukui City"][0])
    ax.annotate(f"Fukui City  +{metrics['fukui_city']['open_pct']:.1f}%\n"
                f"one-sided placebo $p$ = {metrics['fukui_city']['p_open_1s']:.3f}\n"
                f"($n$ = {metrics['fukui_city']['n_placebos_kept']:,} well-fit donors)",
                (fc.open_pct, fy), textcoords="offset points", xytext=(20, -34),
                fontsize=7.2, color=C_SHK, va="center", ha="left", zorder=6,
                arrowprops=dict(arrowstyle="-", lw=0.7, color=C_SHK, shrinkA=1, shrinkB=4))

    # honesty callout: poor-fit units with larger gaps are NOT trustworthy
    ky = int(treated.index[treated.en == "Katsuyama"][0])
    ax.annotate("Katsuyama & Ikeda: larger gap,\nbut poor SC fit \u2192 not trustworthy",
                (treated[treated.en == "Katsuyama"].iloc[0].open_pct, ky),
                textcoords="offset points", xytext=(16, -2), fontsize=6.8,
                color="#666666", va="center", ha="left", zorder=6,
                arrowprops=dict(arrowstyle="-", lw=0.6, color="#aaaaaa", shrinkA=2, shrinkB=4))

    # ---- bottom: null distribution as a grey jittered strip ----
    rng = np.random.default_rng(0)
    jit = rng.uniform(-0.42, 0.42, size=null.size)
    axn.scatter(null, jit, s=5, color=C_NONE, alpha=0.16, linewidth=0, zorder=2)
    axn.set_yticks([])
    axn.set_ylim(-0.7, 0.7)
    axn.set_xlabel("Opening-window synthetic-control gap  (%, Mar\u2013Apr 2024)")
    axn.text(0.015, 0.93, f"1,709 donor placebos (null distribution),  median = {np.median(null):.0f}%",
             transform=axn.transAxes, fontsize=7, color="#555555", ha="left", va="top")
    axn.annotate("placebo $p$ = 0.10\n(null 90th pct)", (p90, -0.6),
                 textcoords="offset points", xytext=(4, 0), fontsize=6.8,
                 color=C_TRANS, ha="left", va="bottom")
    if n_null_beyond:
        axn.text(0.985, 0.93,
                 f"+{n_null_beyond} donors beyond {xmax:.0f}% (max +{null.max():.0f}%), axis truncated",
                 transform=axn.transAxes, fontsize=6.3, color="#999999", ha="right", va="top")

    ax.set_xlim(xlo, xmax)

    # legend: colour identity + hollow=low-confidence fit
    handles = [
        Line2D([0], [0], marker="o", ls="", mfc=C_SHK, mec=C_SHK, ms=7.5,
               label="Fukui City (treated focus)"),
        Line2D([0], [0], marker="o", ls="", mfc=C_DURABLE, mec=C_DURABLE, ms=7.5,
               label="Well-fit corridor (Eiheiji, Tsuruga, Sakai)"),
        Line2D([0], [0], marker="o", ls="", mfc=C_NONE, mec=C_NONE, ms=7.5,
               label="Other treated municipality"),
        Line2D([0], [0], marker="o", ls="", mfc="none", mec="#555", mew=1.6, ms=7.5,
               label="Low-confidence fit (excluded from inference)"),
        Line2D([0], [0], marker="s", ls="", mfc="#fdece0", mec="#fdece0", ms=9,
               label="Placebo-extreme tail ($p$ < 0.10)"),
    ]
    ax.legend(handles=handles, loc="lower right", fontsize=6.7, handletextpad=0.4,
              borderpad=0.5, frameon=True, framealpha=0.92, edgecolor="#dddddd")
    fig.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)


def fig5_intime_placebo(insp: pd.DataFrame, intime: pd.DataFrame,
                        metrics: dict, out: Path) -> None:
    """Backdated (2023-03) in-time placebo negative control."""
    _style()
    real = insp[["area_code", "en", "good_fit", "open_pct"]]
    m = real.merge(intime[["area_code", "backdated_open_pct", "p_backdated_open_1s"]],
                   on="area_code", how="inner")
    m = m.sort_values("open_pct").reset_index(drop=True)
    y = np.arange(len(m))

    fig, ax = plt.subplots(figsize=(7.0, 6.0))
    ax.axvline(0.0, color="#cccccc", lw=0.8, zorder=1)

    for i, row in m.iterrows():
        col = _unit_color(row.en)
        good = bool(row.good_fit)
        # connector: real -> backdated (collapse toward zero)
        ax.plot([row.open_pct, row.backdated_open_pct], [i, i],
                color="#cfcfcf", lw=1.2, zorder=2)
        # backdated (fake 2023 event) -- open grey diamond
        ax.scatter(row.backdated_open_pct, i, s=42, marker="D",
                   facecolor="white", edgecolor=C_NONE, linewidth=1.1, zorder=3)
        # real opening spike -- coloured circle, hollow if poor fit
        ax.scatter(row.open_pct, i, s=80, marker="o",
                   facecolor=col if good else "none", edgecolor=col,
                   linewidth=1.0 if good else 1.7, zorder=4)

    ax.set_yticks(y)
    ax.set_yticklabels(m.en, fontsize=7.5)
    for lbl, en in zip(ax.get_yticklabels(), m.en):
        lbl.set_color(_unit_color(en) if en in CORRIDOR else "#333333")
        if en in CORRIDOR:
            lbl.set_fontweight("bold")
    ax.set_ylim(-0.8, len(m) - 0.2)
    ax.set_xlabel("Opening-window synthetic-control gap  (%)")
    ax.set_ylabel("Treated Fukui municipality")
    ax.set_title("In-time placebo (negative control): backdating the event to 2023-03\n"
                 "collapses the corridor's opening spike toward zero", fontsize=9)

    # headline annotation on Fukui City
    fc = m[m.en == "Fukui City"].iloc[0]
    fy = int(m.index[m.en == "Fukui City"][0])
    ax.annotate(f"real +{fc.open_pct:.1f}%  ($p$ = {metrics['fukui_city']['p_open_1s']:.3f})",
                (fc.open_pct, fy), textcoords="offset points", xytext=(8, 8),
                fontsize=7.2, color=C_SHK, va="bottom", ha="left", zorder=6)
    ax.annotate(f"backdated {fc.backdated_open_pct:+.1f}%\n($p$ = {fc.p_backdated_open_1s:.2f}, n.s.)",
                (fc.backdated_open_pct, fy), textcoords="offset points", xytext=(-8, -12),
                fontsize=7.0, color="#555555", va="top", ha="right", zorder=6)

    handles = [
        Line2D([0], [0], marker="o", ls="", mfc=C_SHK, mec=C_SHK, ms=7.5,
               label="Real 2024-03 opening spike (Fukui City)"),
        Line2D([0], [0], marker="o", ls="", mfc=C_DURABLE, mec=C_DURABLE, ms=7.5,
               label="Real spike, well-fit corridor"),
        Line2D([0], [0], marker="o", ls="", mfc=C_NONE, mec=C_NONE, ms=7.5,
               label="Real spike, other municipality"),
        Line2D([0], [0], marker="D", ls="", mfc="white", mec=C_NONE, mew=1.1, ms=6.5,
               label="Backdated 2023-03 placebo spike"),
        Line2D([0], [0], marker="o", ls="", mfc="none", mec="#555", mew=1.6, ms=7.5,
               label="Low-confidence fit (excluded from inference)"),
    ]
    ax.legend(handles=handles, loc="lower right", fontsize=6.7, handletextpad=0.4,
              borderpad=0.5, frameon=True, framealpha=0.92, edgecolor="#dddddd")
    ax.margins(x=0.06)
    fig.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--robustness-dir", default="output/national_stats/causal_robustness",
                    help="directory holding the robustness CSVs / metrics.json")
    ap.add_argument("--out-dir", default="output/national_stats/causal_robustness/figures",
                    help="directory to write PNGs")
    args = ap.parse_args()
    rdir = Path(args.robustness_dir)
    odir = Path(args.out_dir)
    odir.mkdir(parents=True, exist_ok=True)

    import json
    insp = pd.read_csv(rdir / "inspace_placebos.csv")
    dist = pd.read_csv(rdir / "placebo_open_distribution.csv")
    intime = pd.read_csv(rdir / "intime_placebo.csv")
    with open(rdir / "metrics.json") as fh:
        metrics = json.load(fh)

    fig4_placebo_distribution(insp, dist, metrics, odir / "fig4_placebo_distribution.png")
    fig5_intime_placebo(insp, intime, metrics, odir / "fig5_intime_placebo.png")
    print(f"wrote 2 figures to {odir}")


if __name__ == "__main__":
    main()
