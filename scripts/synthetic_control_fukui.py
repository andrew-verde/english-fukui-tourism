#!/usr/bin/env python3
"""Municipal synthetic control for Fukui City's March 2024 rail opening."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
EVENT_YM = 202403
TARGET = 18201


def fit_convex_weights(
    treated: np.ndarray, donors: np.ndarray, maxiter: int = 2_000
) -> np.ndarray:
    """Least-squares SCM weights: nonnegative and exactly sum to one.

    ``donors`` has shape (time, donor). Inputs should already be transformed.
    """
    y = np.asarray(treated, dtype=float)
    x = np.asarray(donors, dtype=float)
    if x.ndim != 2 or y.ndim != 1 or x.shape[0] != y.size or not x.shape[1]:
        raise ValueError("Expected treated (time,) and donors (time, donor)")
    if not np.isfinite(y).all() or not np.isfinite(x).all():
        raise ValueError("SCM inputs must be finite")
    # Frank-Wolfe solves least squares over simplex without a 1,700-variable
    # dense constrained Hessian. Exact line search; sparse weights.
    errors = np.square(x - y[:, None]).sum(axis=0)
    weights = np.zeros(x.shape[1])
    weights[int(errors.argmin())] = 1.0
    fitted = x @ weights
    for _ in range(maxiter):
        gradient = x.T @ (fitted - y)
        vertex = int(gradient.argmin())
        direction_fit = x[:, vertex] - fitted
        denominator = float(direction_fit @ direction_fit)
        if denominator == 0:
            break
        step = float(np.clip(-((fitted - y) @ direction_fit) / denominator, 0, 1))
        if step < 1e-12:
            break
        weights *= 1 - step
        weights[vertex] += step
        fitted += step * direction_fit
    return weights


def rmspe(actual: np.ndarray, synthetic: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(np.asarray(actual) - synthetic))))


def placebo_p_value(treated_effect: float, placebo_effects: np.ndarray) -> float:
    """Finite-sample, two-sided randomization p-value."""
    values = np.asarray(placebo_effects, dtype=float)
    values = values[np.isfinite(values)]
    return float((1 + np.sum(np.abs(values) >= abs(treated_effect))) / (1 + values.size))


def load_city_panel(paths: list[Path]) -> pd.DataFrame:
    required = {"年", "月", "都道府県コード", "地域コード", "地域名称", "人数"}
    frames = [pd.read_csv(path, encoding="utf-8-sig") for path in paths]
    if not frames:
        raise ValueError("No city CSV files supplied")
    data = pd.concat(frames, ignore_index=True)
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"Missing columns: {', '.join(sorted(missing))}")
    for col in ("年", "月", "都道府県コード", "地域コード", "人数"):
        data[col] = pd.to_numeric(data[col], errors="coerce")
    data = data.dropna(subset=["年", "月", "都道府県コード", "地域コード", "人数"])
    data["ym"] = data["年"].astype(int) * 100 + data["月"].astype(int)
    data["地域コード"] = data["地域コード"].astype(int)
    data["都道府県コード"] = data["都道府県コード"].astype(int)
    # Defensive aggregation; upstream currently has one row per municipality-month.
    return data.groupby(
        ["ym", "都道府県コード", "地域コード", "地域名称"], as_index=False
    )["人数"].sum()


def make_matrix(panel: pd.DataFrame, excluded_prefectures: set[int]) -> tuple[pd.DataFrame, pd.Series]:
    subset = panel[
        (panel["地域コード"].eq(TARGET))
        | (~panel["都道府県コード"].isin(excluded_prefectures))
    ]
    matrix = subset.pivot(index="ym", columns="地域コード", values="人数").sort_index()
    matrix = matrix.loc[:, matrix.notna().all()]
    if TARGET not in matrix:
        raise ValueError("Fukui City 18201 lacks complete coverage")
    names = panel.drop_duplicates("地域コード").set_index("地域コード")["地域名称"]
    return np.log1p(matrix), names


def estimate(matrix: pd.DataFrame) -> dict:
    pre = matrix.index < EVENT_YM
    if not pre.any() or pre.all():
        raise ValueError("Panel must contain pre- and post-event months")
    donor_codes = matrix.columns[matrix.columns != TARGET]
    weights = fit_convex_weights(
        matrix.loc[pre, TARGET].to_numpy(), matrix.loc[pre, donor_codes].to_numpy()
    )
    synthetic = matrix.loc[:, donor_codes].to_numpy() @ weights
    actual = matrix[TARGET].to_numpy()
    gap = actual - synthetic
    return {
        "donor_codes": donor_codes.to_numpy(),
        "weights": weights,
        "synthetic": synthetic,
        "actual": actual,
        "gap": gap,
        "pre_rmspe": rmspe(actual[pre], synthetic[pre]),
        "post_mean_gap": float(gap[~pre].mean()),
    }


def run_placebos(matrix: pd.DataFrame, max_units: int | None = None) -> pd.DataFrame:
    """In-space placebos, applying identical SCM to each donor municipality."""
    codes = list(matrix.columns)
    controls = [code for code in codes if code != TARGET]
    if max_units is not None:
        controls = controls[:max_units]
    pre = matrix.index < EVENT_YM
    rows = []
    for code in controls:
        donor_codes = [other for other in codes if other != code]
        try:
            weights = fit_convex_weights(
                matrix.loc[pre, code].to_numpy(),
                matrix.loc[pre, donor_codes].to_numpy(),
                maxiter=500,
            )
        except RuntimeError:
            continue
        synthetic = matrix.loc[:, donor_codes].to_numpy() @ weights
        actual = matrix[code].to_numpy()
        rows.append(
            {
                "area_code": code,
                "pre_rmspe": rmspe(actual[pre], synthetic[pre]),
                "post_mean_gap_log1p": float((actual[~pre] - synthetic[~pre]).mean()),
            }
        )
    return pd.DataFrame(rows)


def write_outputs(label: str, matrix: pd.DataFrame, names: pd.Series, result: dict,
                  output_dir: Path, max_placebos: int | None) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    gap = pd.DataFrame({
        "ym": matrix.index, "actual_log1p": result["actual"],
        "synthetic_log1p": result["synthetic"], "gap_log1p": result["gap"],
    })
    gap.to_csv(output_dir / f"{label}_gap.csv", index=False)
    weights = pd.DataFrame({"area_code": result["donor_codes"], "weight": result["weights"]})
    weights["municipality"] = weights["area_code"].map(names)
    weights.sort_values("weight", ascending=False).to_csv(
        output_dir / f"{label}_weights.csv", index=False
    )
    placebos = run_placebos(matrix, max_placebos)
    placebos.to_csv(output_dir / f"{label}_placebos.csv", index=False)
    p_value = placebo_p_value(
        result["post_mean_gap"], placebos["post_mean_gap_log1p"].to_numpy()
    )
    fig, ax = plt.subplots(figsize=(9, 4.5))
    dates = pd.to_datetime(matrix.index.astype(str), format="%Y%m")
    ax.plot(dates, result["actual"], label="Fukui City")
    ax.plot(dates, result["synthetic"], label="Synthetic Fukui")
    ax.axvline(pd.Timestamp("2024-03-01"), color="black", linestyle="--", linewidth=1)
    ax.set(ylabel="log(1 + estimated visitors)", title=f"Fukui City SCM — {label}")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_dir / f"{label}_gap.png", dpi=180)
    plt.close(fig)
    return {
        "label": label, "months": len(matrix), "pre_months": int((matrix.index < EVENT_YM).sum()),
        "donors": matrix.shape[1] - 1, "pre_rmspe": result["pre_rmspe"],
        "post_mean_gap_log1p": result["post_mean_gap"], "placebos": len(placebos),
        "randomization_p_value_two_sided": p_value,
    }


def default_paths() -> list[Path]:
    candidates = [
        ROOT / "output" / "official_fukui" / "raw",
        ROOT / "output" / "national_stats" / "raw" / "japan-kanko-stat",
        ROOT / "output" / "national_stats" / "japan_kanko_stat" / "raw",
    ]
    for directory in candidates:
        found = sorted(directory.glob("city20*.csv"))
        if found:
            return found
    return []


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", nargs="*", type=Path, help="Pinned city2021.csv … city2025.csv")
    parser.add_argument("--output-dir", type=Path,
                        default=ROOT / "output" / "national_stats" / "synthetic_control")
    parser.add_argument("--max-placebos", type=int, default=100,
                        help="Number of deterministic in-space placebos (default: 100; 0 = all)")
    args = parser.parse_args()
    paths = args.csv or default_paths()
    if args.max_placebos == 0:
        args.max_placebos = None
    if not paths:
        parser.error("No city20*.csv found; pass pinned CSV paths")
    panel = load_city_panel(paths)
    summaries = []
    # Primary removes Niigata, Toyama, Ishikawa, Fukui. Robustness admits Ishikawa.
    for label, excluded in (("primary", {15, 16, 17, 18}), ("ishikawa_included", {15, 16, 18})):
        matrix, names = make_matrix(panel, excluded)
        summaries.append(
            write_outputs(label, matrix, names, estimate(matrix), args.output_dir, args.max_placebos)
        )
    (args.output_dir / "report.json").write_text(
        json.dumps(summaries, ensure_ascii=False, indent=2) + "\n"
    )
    lines = ["# Fukui City synthetic control", "",
             "Outcome: `log1p(人数)`; intervention: 2024-03. Levels are mobile-derived estimates, not census headcounts.", ""]
    for row in summaries:
        lines += [f"## {row['label']}", "",
                  f"- Donors: {row['donors']}; pre RMSPE: {row['pre_rmspe']:.4f}",
                  f"- Post mean gap: {row['post_mean_gap_log1p']:.4f} log points",
                  f"- In-space placebo p-value: {row['randomization_p_value_two_sided']:.4f} ({row['placebos']} placebos)", ""]
    (args.output_dir / "report.md").write_text("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
