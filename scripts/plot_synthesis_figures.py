#!/usr/bin/env python3
"""Render the three synthesis figures from output/synthesis/*.csv.

Reads the committed synthesis join outputs and writes publication-grade PNGs
(300 dpi) to output/synthesis/figures/. Pure function of the CSVs — no network,
no RNG. Wired into the Makefile as the `synthesis-figures` target, downstream of
`synthesis`.

Figures:
  fig1_regime_friction_map.png   -- §4.1 regime x transport-access friction
  fig2_mode_friction.png         -- §4.2 arrival-mode mechanism (LEAD result)
  fig3_priority_matrix.png       -- §4.3 causal-opportunity x priority quadrants
"""
from __future__ import annotations
import argparse
import os
import tempfile
from pathlib import Path
import numpy as np
import pandas as pd

os.environ.setdefault("MPLCONFIGDIR", os.path.join(tempfile.gettempdir(), "matplotlib"))
import matplotlib
matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

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

REG = {"durable": "#2c7fb8", "transient": "#e6820a", "none": "#9aa0a6"}
QC  = {"ACT NOW": "#c0392b", "watch": "#e6820a", "quick win": "#2c7fb8", "deprioritize": "#9aa0a6"}


def fig1_regime(regime: pd.DataFrame, out: Path) -> None:
    _style()
    fig, ax = plt.subplots(figsize=(6.4, 4.6))
    hc = regime[regime.regime_confidence == "high"]
    b1, b0 = np.polyfit(hc.leaked_lift_pct, hc.transport_access, 1)
    r = np.corrcoef(hc.transport_access, hc.leaked_lift_pct)[0, 1]
    xs = np.linspace(0, hc.leaked_lift_pct.max() * 1.02, 50)
    ax.plot(xs, b0 + b1 * xs, color="#444444", lw=1.1, zorder=1)
    ax.text(0.60, 0.86, f"high-confidence fit\n$r$ = {r:.2f}  ($n$ = {len(hc)})",
            transform=ax.transAxes, ha="left", va="top", fontsize=7.5, color="#444444")
    for _, row in regime.iterrows():
        hi = row.regime_confidence == "high"
        ax.scatter(row.leaked_lift_pct, row.transport_access, s=70 if hi else 66,
                   facecolor=REG[row.regime] if hi else "none", edgecolor=REG[row.regime],
                   linewidth=1.6 if not hi else 0.6, marker="o", zorder=3, alpha=0.95)
    lab = {"Fukui City": (6, 6, "left"), "Tsuruga": (6, -2, "left"), "Awara": (-4, 7, "right"),
           "Ikeda": (-7, 0, "right"), "Katsuyama": (6, -8, "left")}
    for _, row in regime.iterrows():
        if row.en in lab:
            dx, dy, ha = lab[row.en]
            ax.annotate(row.en, (row.leaked_lift_pct, row.transport_access),
                        textcoords="offset points", xytext=(dx, dy), fontsize=7, ha=ha,
                        arrowprops=dict(arrowstyle="-", lw=0.5, color="#888888", shrinkA=0, shrinkB=3))
    ax.set_xlabel("Leaked visitor lift (%, opening spike not sustained to 2025)")
    ax.set_ylabel("Transport-access friction\n(% of FTAS respondents)")
    ax.set_title("Municipalities that leaked their Shinkansen visitor surge\n"
                 "report more transport-access friction", fontsize=9)
    ax.margins(0.06)
    h_reg = [Line2D([0], [0], marker="o", ls="", mfc=REG[k], mec=REG[k], ms=7,
                    label={"durable": "Durable gain", "transient": "Transient surge",
                           "none": "No effect"}[k]) for k in ["durable", "transient", "none"]]
    h_conf = [Line2D([0], [0], marker="o", ls="", mfc="#9aa0a6", mec="#9aa0a6", ms=7,
                     label="High confidence (good SC fit)"),
              Line2D([0], [0], marker="o", ls="", mfc="none", mec="#666", mew=1.4, ms=7,
                     label="Low confidence (excl. from fit)")]
    leg1 = ax.legend(handles=h_reg, loc="upper left", fontsize=7, title="Regime",
                     title_fontsize=7, handletextpad=0.3, borderpad=0.4)
    ax.add_artist(leg1)
    ax.legend(handles=h_conf, loc="center", bbox_to_anchor=(0.62, 0.40), fontsize=6.5,
              handletextpad=0.3, borderpad=0.4, frameon=True, framealpha=0.9)
    fig.tight_layout()
    fig.savefig(out, dpi=300)
    plt.close(fig)


def fig2_mode(mode: pd.DataFrame, out: Path) -> None:
    _style()
    fig, ax = plt.subplots(figsize=(6.8, 4.4))
    m = mode.sort_values("shk_minus_other", ascending=False).reset_index(drop=True)
    top = m.head(6)
    y = np.arange(len(top))[::-1]
    h = 0.26
    C_SHK, C_CAR, C_OTH = "#c0392b", "#2c7fb8", "#9aa0a6"
    ax.barh(y + h, top.shinkansen_pct, height=h, color=C_SHK, label="Shinkansen arrivers", zorder=3)
    ax.barh(y, top.other_arrival_pooled_pct, height=h, color=C_OTH, label="All other modes (pooled)", zorder=3)
    ax.barh(y - h, top.private_car_pct, height=h, color=C_CAR, label="Private-car arrivers", zorder=3)
    ax.set_yticks(y)
    ax.set_yticklabels([c.replace("_", " ") for c in top.friction_code], fontsize=8)
    ax.set_xlabel("Friction reported (% of arrivals in that mode)")
    ax.set_title("Shinkansen arrivers report 4\u00d7 more transport-access friction\n"
                 "than any other way of reaching Fukui", fontsize=9)
    ax.set_xlim(0, 9.2)
    ta = top.iloc[0]
    ratio = ta.shk_over_other_ratio
    ax.annotate(f"{ta.shinkansen_pct:.1f}%", (ta.shinkansen_pct, y[0] + h), xytext=(4, 0),
                textcoords="offset points", va="center", fontsize=7.5, color=C_SHK, fontweight="bold")
    ax.annotate(f"{ratio:.1f}\u00d7 vs pooled\n(z = 34.5)", (ta.shinkansen_pct, y[0] + h),
                xytext=(38, -7), textcoords="offset points", va="center", fontsize=7.5, color="#333")
    ax.legend(loc="lower right", fontsize=7.5, handletextpad=0.4, borderpad=0.5)
    ax.margins(y=0.04)
    fig.tight_layout()
    fig.savefig(out, dpi=300)
    plt.close(fig)


def fig3_priority(prio: pd.DataFrame, out: Path) -> None:
    _style()
    plt.rcParams.update({"axes.spines.top": True, "axes.spines.right": True})
    fig, ax = plt.subplots(figsize=(6.9, 5.4))
    xt, yt = 0.30, 0.15
    ax.axvspan(xt, 1.05, color="#f6f6f6", zorder=0)
    ax.axhline(yt, color="#cccccc", lw=0.8, zorder=1)
    ax.axvline(xt, color="#cccccc", lw=0.8, zorder=1)
    for _, row in prio.iterrows():
        ax.scatter(row.causal_opportunity, row.priority_n, s=95, color=QC[row.quadrant],
                   edgecolor="white", linewidth=0.8, zorder=3)
    ax.annotate("transport access", (1.0, 1.0), textcoords="offset points", xytext=(-10, 6),
                ha="right", fontsize=8, color="#c0392b", fontweight="bold", zorder=4)
    targets = {
        "opening_hours_availability": (0.47, 0.25, "left"),
        "itinerary_fit_time_cost": (0.54, 0.14, "left"),
        "food_amenities_gap": (0.50, 0.06, "left"),
        "wayfinding_signage": (0.42, -0.055, "left"),
        "waiting_crowding": (0.10, -0.075, "right"),
        "accessibility_mobility": (-0.20, 0.03, "left"),
        "cleanliness_comfort": (-0.20, 0.13, "left"),
    }
    for _, row in prio.iterrows():
        fc = row.friction_code
        if fc == "transport_access":
            continue
        tx, ty, ha = targets[fc]
        ax.annotate(fc.replace("_", " "), (row.causal_opportunity, row.priority_n),
                    textcoords="data", xytext=(tx, ty), fontsize=7, ha=ha, va="center",
                    color=QC[row.quadrant] if row.quadrant in ("ACT NOW", "watch") else "#333",
                    zorder=4, arrowprops=dict(arrowstyle="-", lw=0.5, color="#aaaaaa", shrinkA=2, shrinkB=3))
    ax.set_xlabel("Causal opportunity  (leaked-lift corr \u00d7 mode gap \u00d7 SEM damage)")
    ax.set_ylabel("Intervention priority  (SEM-scored nudge rank, normalized)")
    ax.set_title("Where survey-measured friction meets causal opportunity:\n"
                 "transport-access is the unique act-now target", fontsize=9)
    ax.set_xlim(-0.34, 1.12)
    ax.set_ylim(-0.11, 1.12)
    ax.text(1.03, 1.10, "ACT NOW", ha="right", va="top", fontsize=8, color="#c0392b", fontweight="bold")
    ax.text(0.31, 1.10, "high priority, lower leverage", ha="left", va="top", fontsize=6.5, color="#999")
    ax.text(1.03, -0.085, "quick wins", ha="right", va="bottom", fontsize=7, color="#999")
    ax.text(0.315, -0.085, "deprioritize", ha="left", va="bottom", fontsize=7, color="#999")
    fig.tight_layout()
    fig.savefig(out, dpi=300)
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--synthesis-dir", default="output/synthesis",
                    help="directory holding synthesis_*.csv (default: output/synthesis)")
    ap.add_argument("--out-dir", default="output/synthesis/figures",
                    help="directory to write PNGs (default: output/synthesis/figures)")
    args = ap.parse_args()
    sdir = Path(args.synthesis_dir)
    odir = Path(args.out_dir)
    odir.mkdir(parents=True, exist_ok=True)

    regime = pd.read_csv(sdir / "synthesis_regime_friction_map.csv")
    mode = pd.read_csv(sdir / "synthesis_mode_friction.csv")
    prio = pd.read_csv(sdir / "synthesis_priority_matrix.csv")

    fig1_regime(regime, odir / "fig1_regime_friction_map.png")
    fig2_mode(mode, odir / "fig2_mode_friction.png")
    fig3_priority(prio, odir / "fig3_priority_matrix.png")
    print(f"wrote 3 figures to {odir}")


if __name__ == "__main__":
    main()
