#!/usr/bin/env python3
"""Generate nudge-pilot two-arm power calculations and stage-2 planning rule."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from statistics import NormalDist


EFFECT_GRID = [0.10, 0.125, 0.15, 0.20, 0.25, 0.30]


def n_per_arm(d: float, alpha: float = 0.05, power: float = 0.80) -> int:
    """Return per-arm sample size for a two-sided two-sample mean contrast."""
    if d <= 0:
        raise ValueError("d must be positive")
    normal = NormalDist()
    z_alpha = normal.inv_cdf(1 - alpha / 2)
    z_power = normal.inv_cdf(power)
    return math.ceil(2 * (z_alpha + z_power) ** 2 / d ** 2)


def d_plan(dhat: float, se: float) -> float:
    """Apply pre-specified stage-2 conservative effect-size rule."""
    return max(0.10, dhat - se)


def render_markdown(rows: list[dict], planned: dict | None) -> str:
    lines = [
        "# Nudge Pilot Power Analysis",
        "",
        "Two-sided two-sample means, α = 0.05, power = 0.80.",
        "",
        "| d | n/arm | Primary contrast (2 arms) |",
        "|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['d']:.3f}".rstrip("0").rstrip(".")
            + f" | {row['n_per_arm']:,} | {2 * row['n_per_arm']:,} |"
        )
    lines.extend([
        "",
        "## Stage 2",
        "",
        "Pre-specified rule: `d_plan = max(0.10, dhat - se)`.",
    ])
    if planned:
        lines.extend([
            "",
            f"For `dhat = {planned['dhat']:.4g}` and `se = {planned['se']:.4g}`, "
            f"`d_plan = {planned['d_plan']:.4g}` and n/arm = "
            f"{planned['n_per_arm']:,}.",
        ])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dhat", type=float)
    parser.add_argument("--se", type=float)
    parser.add_argument(
        "--output-dir", default="experiments/nudge-pilot",
        help="output directory (default: experiments/nudge-pilot)",
    )
    args = parser.parse_args()
    if (args.dhat is None) != (args.se is None):
        parser.error("--dhat and --se must be supplied together")
    if args.se is not None and args.se < 0:
        parser.error("--se must be non-negative")

    rows = [{"d": effect, "n_per_arm": n_per_arm(effect)} for effect in EFFECT_GRID]
    planned = None
    if args.dhat is not None:
        planned_effect = d_plan(args.dhat, args.se)
        planned = {
            "dhat": args.dhat,
            "se": args.se,
            "d_plan": planned_effect,
            "n_per_arm": n_per_arm(planned_effect),
        }

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = output_dir / "power_analysis.md"
    json_path = output_dir / "power_analysis.json"
    markdown_path.write_text(render_markdown(rows, planned), encoding="utf-8")
    json_path.write_text(
        json.dumps({
            "alpha": 0.05,
            "power": 0.80,
            "formula": "ceil(2*(z(1-alpha/2)+z(power))^2/d^2)",
            "grid": rows,
            "stage_2_rule": "d_plan = max(0.10, dhat - se)",
            "stage_2_plan": planned,
        }, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {markdown_path}")
    print(f"wrote {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
