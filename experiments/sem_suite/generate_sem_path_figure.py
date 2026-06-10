#!/usr/bin/env python3
"""Generate a presentation-ready SEM/path diagram from pilot outputs.

The figure follows common SEM diagram conventions:
- latent/proxy constructs are shown as rounded ovals;
- observed experimental/background predictors are shown as rectangles;
- directed paths are labeled with standardized beta weights where available;
- edge thickness encodes absolute coefficient magnitude;
- dashed edges mark paths that do not pass the selected p-value threshold.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-sem-suite")

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import yaml
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


DEFAULT_CONFIG = Path(__file__).with_name("sem_model_config.yaml")
DEFAULT_OUTPUT_DIR = Path("experiments/sem_suite/output")

NODE_POSITIONS = {
    "condition": (0.12, 0.72),
    "background": (0.12, 0.30),
    "information_clarity": (0.34, 0.72),
    "information_trust": (0.34, 0.30),
    "perceived_friction": (0.58, 0.72),
    "planning_confidence": (0.58, 0.30),
    "visit_intention": (0.84, 0.52),
}

NODE_LABELS = {
    "condition": "Nudge\ncondition",
    "background": "Background\ncontrols",
    "information_clarity": "Information\nclarity",
    "information_trust": "Information\ntrust",
    "perceived_friction": "Perceived\nfriction",
    "planning_confidence": "Planning\nconfidence",
    "visit_intention": "Visit\nintention",
}

CONDITION_PREFIX = "condition_"
BACKGROUND_PREDICTORS = {
    "background_public_transit_confidence",
    "background_fukui_familiarity",
}


@dataclass
class Edge:
    source: str
    target: str
    label: str
    beta: float | None
    p_value: float | None
    significant: bool


def load_config(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_optional_csv(path: Path) -> pd.DataFrame:
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


def build_edges(paths: pd.DataFrame, config: dict[str, Any], alpha: float) -> list[Edge]:
    if paths.empty or "predictor" not in paths.columns:
        return []

    paths = paths[paths["predictor"] != "__model__"].copy()
    if paths.empty:
        return []

    edges: list[Edge] = []
    for _, row in paths.iterrows():
        predictor = str(row.get("predictor", ""))
        target = str(row.get("outcome", ""))
        if predictor == "const" or not target:
            continue

        source = predictor_to_source(predictor, config)
        if source is None or source not in NODE_POSITIONS or target not in NODE_POSITIONS:
            continue

        beta = numeric_or_none(row.get("standardized_beta"))
        if beta is None:
            beta = numeric_or_none(row.get("coef"))
        p_value = numeric_or_none(row.get("p_value"))
        significant = bool(p_value is not None and p_value < alpha)
        label = format_edge_label(predictor, beta, p_value)
        edges.append(Edge(source=source, target=target, label=label, beta=beta, p_value=p_value, significant=significant))

    return collapse_condition_edges(edges)


def predictor_to_source(predictor: str, config: dict[str, Any]) -> str | None:
    if predictor.startswith(CONDITION_PREFIX):
        return "condition"
    if predictor in BACKGROUND_PREDICTORS:
        return "background"
    if predictor in config["constructs"]:
        return predictor
    return None


def collapse_condition_edges(edges: list[Edge]) -> list[Edge]:
    """Combine multiple dummy-condition paths to keep the diagram readable."""
    collapsed: dict[tuple[str, str], list[Edge]] = {}
    passthrough: list[Edge] = []
    for edge in edges:
        if edge.source == "condition":
            collapsed.setdefault((edge.source, edge.target), []).append(edge)
        else:
            passthrough.append(edge)

    for (source, target), group in collapsed.items():
        betas = [edge.beta for edge in group if edge.beta is not None and not math.isnan(edge.beta)]
        p_values = [edge.p_value for edge in group if edge.p_value is not None and not math.isnan(edge.p_value)]
        if betas:
            strongest = max(betas, key=lambda value: abs(value))
            label = f"max |β|={abs(strongest):.2f}"
        else:
            strongest = None
            label = "condition paths"
        if p_values:
            label += f"\nmin p={min(p_values):.3f}"
        passthrough.append(
            Edge(
                source=source,
                target=target,
                label=label,
                beta=strongest,
                p_value=min(p_values) if p_values else None,
                significant=any(edge.significant for edge in group),
            )
        )
    return passthrough


def numeric_or_none(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number):
        return None
    return number


def format_edge_label(predictor: str, beta: float | None, p_value: float | None) -> str:
    if beta is None:
        coef = "β=NA"
    else:
        coef = f"β={beta:+.2f}"
    stars = significance_stars(p_value)
    if predictor.startswith(CONDITION_PREFIX):
        condition = predictor.replace(CONDITION_PREFIX, "").replace("_", " ")
        return f"{condition}\n{coef}{stars}"
    return f"{coef}{stars}"


def significance_stars(p_value: float | None) -> str:
    if p_value is None:
        return ""
    if p_value < 0.001:
        return "***"
    if p_value < 0.01:
        return "**"
    if p_value < 0.05:
        return "*"
    return ""


def draw_figure(
    paths: pd.DataFrame,
    reliability: pd.DataFrame,
    readiness: dict[str, Any],
    config: dict[str, Any],
    output_path: Path,
    alpha: float,
    title: str,
) -> None:
    edges = build_edges(paths, config, alpha)

    fig, ax = plt.subplots(figsize=(13.5, 7.6))
    fig.patch.set_facecolor("#eff1f5")
    ax.set_facecolor("#eff1f5")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    draw_title(ax, title, readiness)
    draw_edges(ax, edges, config)
    draw_nodes(ax, reliability)
    draw_legend(ax, edges, readiness, paths)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220, bbox_inches="tight", facecolor=fig.get_facecolor())
    svg_path = output_path.with_suffix(".svg")
    fig.savefig(svg_path, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def draw_title(ax, title: str, readiness: dict[str, Any]) -> None:
    subtitle = (
        f"n={readiness.get('n_participants', 'NA')} participants; "
        f"{readiness.get('n_task_rows', 'NA')} task rows; "
        f"status={readiness.get('minimum_sem_status', 'unknown')}"
    )
    ax.text(0.02, 0.97, title, fontsize=19, fontweight="bold", color="#4c4f69", va="top")
    ax.text(0.02, 0.925, subtitle, fontsize=10.5, color="#6c6f85", va="top")


def draw_nodes(ax, reliability: pd.DataFrame) -> None:
    reliability_map = {}
    if not reliability.empty and {"construct", "cronbach_alpha"}.issubset(reliability.columns):
        reliability_map = dict(zip(reliability["construct"], reliability["cronbach_alpha"]))

    for node_id, (x, y) in NODE_POSITIONS.items():
        is_construct = node_id in reliability_map or node_id in {
            "information_clarity",
            "information_trust",
            "perceived_friction",
            "planning_confidence",
            "visit_intention",
        }
        width = 0.16 if node_id not in {"visit_intention"} else 0.17
        height = 0.115 if is_construct else 0.105
        color = "#dce5ff" if is_construct else "#ffffff"
        edge_color = "#1e66f5" if is_construct else "#bcc0cc"
        boxstyle = "round,pad=0.018,rounding_size=0.06" if is_construct else "round,pad=0.015,rounding_size=0.018"
        patch = FancyBboxPatch(
            (x - width / 2, y - height / 2),
            width,
            height,
            boxstyle=boxstyle,
            linewidth=1.4,
            edgecolor=edge_color,
            facecolor=color,
            zorder=3,
        )
        ax.add_patch(patch)
        ax.text(x, y + 0.012, NODE_LABELS[node_id], ha="center", va="center", fontsize=10.2, color="#4c4f69", zorder=4)
        if node_id in reliability_map and not pd.isna(reliability_map[node_id]):
            ax.text(
                x,
                y - 0.044,
                f"α={reliability_map[node_id]:.2f}",
                ha="center",
                va="center",
                fontsize=8.5,
                color="#6c6f85",
                zorder=4,
            )


def draw_edges(ax, edges: list[Edge], config: dict[str, Any]) -> None:
    if not edges:
        draw_hypothesized_edges(ax, config)
        ax.text(
            0.5,
            0.52,
            "Path weights not estimated yet\n(hypothesized paths shown)",
            ha="center",
            va="center",
            fontsize=14,
            color="#6c6f85",
            bbox={"boxstyle": "round,pad=0.5", "facecolor": "#ffffff", "edgecolor": "#bcc0cc"},
        )
        return

    for edge in edges:
        start = NODE_POSITIONS[edge.source]
        end = NODE_POSITIONS[edge.target]
        beta = edge.beta if edge.beta is not None else 0.0
        color = "#1e66f5" if beta >= 0 else "#d20f39"
        linewidth = 1.2 + min(abs(beta), 1.0) * 4.5
        linestyle = "-" if edge.significant else (0, (4, 3))
        arrow = FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=16,
            linewidth=linewidth,
            linestyle=linestyle,
            color=color,
            alpha=0.86,
            shrinkA=58,
            shrinkB=58,
            connectionstyle=connection_style(edge),
            zorder=1,
        )
        ax.add_patch(arrow)
        label_x = (start[0] + end[0]) / 2
        label_y = (start[1] + end[1]) / 2
        if edge.source == "background":
            label_y -= 0.035
        if edge.source == "condition":
            label_y += 0.04
        ax.text(
            label_x,
            label_y,
            edge.label,
            ha="center",
            va="center",
            fontsize=8.8,
            color="#4c4f69",
            bbox={"boxstyle": "round,pad=0.22", "facecolor": "#f7f8fb", "edgecolor": "#ccd0da", "alpha": 0.94},
            zorder=2,
        )


def draw_hypothesized_edges(ax, config: dict[str, Any]) -> None:
    for model in config.get("path_model", []):
        target = model.get("outcome")
        if target not in NODE_POSITIONS:
            continue
        for predictor in model.get("predictors", []):
            source = "condition" if predictor == "condition" else predictor_to_source(predictor, config)
            if source is None or source not in NODE_POSITIONS:
                continue
            start = NODE_POSITIONS[source]
            end = NODE_POSITIONS[target]
            arrow = FancyArrowPatch(
                start,
                end,
                arrowstyle="-|>",
                mutation_scale=13,
                linewidth=1.5,
                linestyle=(0, (3, 4)),
                color="#8c8fa1",
                alpha=0.46,
                shrinkA=58,
                shrinkB=58,
                connectionstyle=connection_style(Edge(source, target, "", 0.0, None, False)),
                zorder=0,
            )
            ax.add_patch(arrow)


def connection_style(edge: Edge) -> str:
    if edge.source == "condition" and edge.target in {"perceived_friction", "planning_confidence", "visit_intention"}:
        return "arc3,rad=-0.12"
    if edge.source == "background":
        return "arc3,rad=0.12"
    if edge.source == "information_clarity" and edge.target == "planning_confidence":
        return "arc3,rad=0.18"
    if edge.source == "perceived_friction" and edge.target == "visit_intention":
        return "arc3,rad=-0.10"
    return "arc3,rad=0.0"


def draw_legend(ax, edges: list[Edge], readiness: dict[str, Any], paths: pd.DataFrame) -> None:
    legend_lines = [
        "SEM/path diagram conventions:",
        "ovals = latent construct proxies; boxes = observed predictors",
        "arrow label = standardized β; thickness = |β|; blue/red = positive/negative",
        "dashed = p >= .05; * p<.05, ** p<.01, *** p<.001",
    ]
    if paths.empty or not edges:
        legend_lines.append("No stable model weights available yet; scaffold shown for planning.")
    elif "standardized_beta" not in paths.columns:
        legend_lines.append("Raw coefficients shown because standardized betas were unavailable.")
    if readiness.get("minimum_sem_status") == "pilot_only":
        legend_lines.append("Pilot-only: use as diagnostic visualization, not final causal evidence.")
    wrapped = "\n".join(textwrap.fill(line, width=72) for line in legend_lines)
    ax.text(
        0.02,
        0.03,
        wrapped,
        ha="left",
        va="bottom",
        fontsize=8.8,
        color="#6c6f85",
        bbox={"boxstyle": "round,pad=0.45", "facecolor": "#ffffff", "edgecolor": "#bcc0cc"},
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a presentation-ready SEM/path diagram.")
    parser.add_argument(
        "--analysis-dir",
        default=DEFAULT_OUTPUT_DIR,
        type=Path,
        help="Directory containing path_coefficients.csv, scale_reliability.csv, and readiness_report.json.",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT_DIR / "sem_path_diagram.png",
        type=Path,
        help="PNG output path. A same-name SVG is also written.",
    )
    parser.add_argument("--config", default=DEFAULT_CONFIG, type=Path)
    parser.add_argument("--alpha", default=0.05, type=float)
    parser.add_argument("--title", default="Fukui Nudge Pilot SEM Path Model")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    paths = load_optional_csv(args.analysis_dir / "path_coefficients.csv")
    reliability = load_optional_csv(args.analysis_dir / "scale_reliability.csv")
    readiness_path = args.analysis_dir / "readiness_report.json"
    readiness = json.loads(readiness_path.read_text(encoding="utf-8")) if readiness_path.exists() else {}
    draw_figure(paths, reliability, readiness, config, args.output, args.alpha, args.title)
    print(f"Wrote {args.output} and {args.output.with_suffix('.svg')}")


if __name__ == "__main__":
    main()
