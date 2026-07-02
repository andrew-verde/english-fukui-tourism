#!/usr/bin/env python3
"""Render durability figures from committed causal and synthesis outputs.

Figures:
  fig6_gap_trajectories.png       -- quarterly target gaps by durability regime
  fig7_durability_mechanisms.png  -- respondent mechanisms by regime pool
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

os.environ.setdefault("MPLCONFIGDIR", os.path.join(tempfile.gettempdir(), "matplotlib"))
import matplotlib

matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt


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


def fig6_gap_trajectories(gaps: pd.DataFrame, out: Path) -> None:
    """Plot quarterly synthetic-control gaps for five corridor municipalities."""
    _style()
    fig, ax = plt.subplots(figsize=(6.9, 4.6))

    series = [
        (18322, "Eiheiji", REG["durable"], "-", 1.8),
        (18210, "Sakai", "#7fb8d8", "-", 1.8),
        (18201, "Fukui City", REG["transient"], "--", 1.4),
        (18202, "Tsuruga", "#f0a955", "--", 1.4),
        (18208, "Awara", "#b3701e", "--", 1.4),
    ]
    event_quarters = np.arange(-4, 7)

    selected = gaps[gaps["area_code"].isin([row[0] for row in series])].copy()
    year = selected["ym"] // 100
    month = selected["ym"] % 100
    selected["event_month"] = (year - 2024) * 12 + (month - 3)
    selected["event_quarter"] = np.floor_divide(selected["event_month"], 3)
    selected = selected[selected["event_quarter"].between(-4, 6)]
    quarterly = (
        selected.groupby(["area_code", "event_quarter"], as_index=False)["gap_log"]
        .mean()
        .assign(gap_pct=lambda frame: 100 * np.expm1(frame["gap_log"]))
    )

    plotted: dict[int, np.ndarray] = {}
    for area_code, name, color, linestyle, linewidth in series:
        values = (
            quarterly[quarterly["area_code"] == area_code]
            .set_index("event_quarter")
            .reindex(event_quarters)["gap_pct"]
            .to_numpy()
        )
        plotted[area_code] = values
        ax.plot(
            event_quarters, values, color=color, linestyle=linestyle,
            linewidth=linewidth,
            solid_capstyle="round", label=name,
        )

    label_y = {
        area_code: plotted[area_code][-1] for area_code, *_ in series
    }
    ordered_codes = sorted(label_y, key=label_y.get)
    for _ in range(len(ordered_codes)):
        changed = False
        for lower_code, upper_code in zip(ordered_codes, ordered_codes[1:]):
            gap = label_y[upper_code] - label_y[lower_code]
            if gap < 2.5:
                shift = (2.5 - gap) / 2
                label_y[lower_code] -= shift
                label_y[upper_code] += shift
                changed = True
        if not changed:
            break
    for area_code, name, color, _, _ in series:
        ax.text(
            event_quarters[-1] + 0.16, label_y[area_code], name,
            color=color, fontsize=8,
            ha="left", va="center", clip_on=False,
        )

    ax.axhline(0, color=REG["none"], linewidth=0.8, zorder=0)
    ax.axvline(-0.5, color=REG["none"], linewidth=0.8, zorder=0)
    ax.text(
        -0.43, 0.98, "opening 2024-03", transform=ax.get_xaxis_transform(),
        color="#777777", fontsize=7, ha="left", va="top", rotation=90,
    )
    ax.text(
        1.15, 64.0, "durable: delayed ramp, then plateau",
        color="#777777", fontsize=7, ha="left", va="bottom",
    )
    ax.annotate(
        "transient: spike gone within a quarter",
        xy=(1, plotted[18201][5]), xytext=(0.65, -20),
        textcoords="data", color="#777777", fontsize=7, ha="left", va="top",
        arrowprops={"arrowstyle": "-", "color": "#aaaaaa", "lw": 0.5},
    )

    ax.set_xticks(event_quarters)
    ax.set_xticklabels([
        f"Q{quarter:+d}" for quarter in event_quarters
    ], fontsize=7)
    ax.set_xlim(-4.15, 7.45)
    ax.set_xlabel("Quarter relative to opening (Q+0 = Mar-May 2024)")
    ax.set_ylabel("Visitor gap vs synthetic control (%)")
    fig.tight_layout()
    fig.savefig(out, dpi=300)
    plt.close(fig)


def fig7_durability_mechanisms(mechanisms: dict, out: Path) -> None:
    """Compare respondent mechanism shares for durable and transient pools."""
    _style()
    fig, ax = plt.subplots(figsize=(6.4, 4.2))

    metrics = [
        ("car_share", "Arrived by car"),
        ("repeat_share", "Repeat visitors"),
        ("overnight_share", "Overnight in prefecture"),
        ("shinkansen_share", "Arrived by Shinkansen"),
    ]
    x = np.arange(len(metrics))
    width = 0.36
    durable = np.array([mechanisms[key]["durable_pct"] for key, _ in metrics])
    transient = np.array([mechanisms[key]["transient_pct"] for key, _ in metrics])

    durable_bars = ax.bar(
        x - width / 2, durable, width, color=REG["durable"],
        label="Durable pool (Eiheiji, Sakai)",
    )
    transient_bars = ax.bar(
        x + width / 2, transient, width, color=REG["transient"],
        label="Transient pool (Fukui City, Tsuruga, Awara, Sabae)",
    )

    for bars in (durable_bars, transient_bars):
        ax.bar_label(bars, fmt="%.1f%%", padding=2, fontsize=7.5)
    for i, (key, _) in enumerate(metrics):
        ax.text(
            i, max(durable[i], transient[i]) + 7,
            f"z={mechanisms[key]['z']:+.1f}",
            color="#777777", fontsize=7, ha="center", va="bottom",
        )

    ax.set_xticks(x)
    ax.set_xticklabels([label for _, label in metrics], fontsize=7)
    ax.set_ylabel("Share of FTAS respondents (%)")
    ax.set_ylim(0, max(durable.max(), transient.max()) + 16)
    ax.legend(loc="upper right", frameon=False)
    fig.tight_layout()
    fig.savefig(out, dpi=300)
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--output-dir", default="output/synthesis/figures",
        help="directory to write PNGs (default: output/synthesis/figures)",
    )
    args = ap.parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    gaps = pd.read_csv(
        "output/national_stats/causal_robustness/target_gap_trajectories.csv"
    )
    with Path("output/synthesis/durability_mechanisms_tests.json").open(
        encoding="utf-8"
    ) as handle:
        mechanisms = json.load(handle)

    fig6_out = output_dir / "fig6_gap_trajectories.png"
    fig7_out = output_dir / "fig7_durability_mechanisms.png"
    fig6_gap_trajectories(gaps, fig6_out)
    fig7_durability_mechanisms(mechanisms, fig7_out)
    print(f"wrote {fig6_out}")
    print(f"wrote {fig7_out}")


if __name__ == "__main__":
    main()
