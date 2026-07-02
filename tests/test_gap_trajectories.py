from pathlib import Path

import numpy as np
import pandas as pd
import pytest


def gap_trajectories_or_skip():
    repo_root = Path(__file__).resolve().parents[1]
    csv_path = (
        repo_root
        / "output"
        / "national_stats"
        / "causal_robustness"
        / "target_gap_trajectories.csv"
    )
    if not csv_path.is_file():
        pytest.skip("SCM target gap trajectories have not been generated")
    return pd.read_csv(csv_path)


def test_gap_trajectory_invariants():
    trajectories = gap_trajectories_or_skip()

    assert len(trajectories) == 1020
    assert trajectories["area_code"].nunique() == 17
    assert trajectories["ym"].min() == 202101
    assert trajectories["ym"].max() == 202512

    effects = trajectories.groupby("area_code").apply(
        lambda target: pd.Series(
            {
                "open_pct": 100
                * (
                    np.exp(
                        target.loc[target["ym"] >= 202403, "gap_log"]
                        .iloc[:2]
                        .mean()
                    )
                    - 1
                ),
                "sust_pct": 100
                * (
                    np.exp(
                        target.loc[
                            target["ym"] // 100 == 2025, "gap_log"
                        ].mean()
                    )
                    - 1
                ),
            }
        )
    )
    assert abs(effects.loc[18322, "open_pct"] - 49.026225) <= 1e-3
    assert effects.loc[18322, "sust_pct"] > 0
    assert effects.loc[18201, "sust_pct"] < 0
