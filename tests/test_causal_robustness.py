from pathlib import Path
import json
import subprocess
import sys

import pandas as pd
import pytest


CSV_NAMES = [
    "inspace_placebos.csv",
    "placebo_open_distribution.csv",
    "intime_placebo.csv",
    "leave_one_out_fukui_city.csv",
]


def robustness_dir_or_skip():
    repo_root = Path(__file__).resolve().parents[1]
    robustness_dir = (
        repo_root / "output" / "national_stats" / "causal_robustness"
    )
    if not all((robustness_dir / name).is_file() for name in CSV_NAMES):
        pytest.skip("causal robustness CSVs have not been generated")
    return repo_root, robustness_dir


def test_causal_robustness_invariants():
    _, robustness_dir = robustness_dir_or_skip()
    inspace = pd.read_csv(robustness_dir / "inspace_placebos.csv")

    assert len(inspace) == 17
    assert {
        "en",
        "pre_rmspe",
        "good_fit",
        "open_pct",
        "p_open_1s",
        "p_open_2s",
        "p_meangap_2s",
        "n_placebos_kept",
    }.issubset(inspace.columns)

    fukui_city = inspace.loc[inspace["en"] == "Fukui City"].iloc[0]
    assert abs(fukui_city["open_pct"] - 29.2) <= 0.5
    assert abs(fukui_city["p_open_1s"] - 0.041) <= 0.01
    assert bool(fukui_city["good_fit"]) is True
    assert fukui_city["n_placebos_kept"] == 1538

    significant = inspace.loc[
        (inspace["p_open_1s"] < 0.10) & inspace["good_fit"], "en"
    ]
    expected = {"Eiheiji", "Fukui City", "Tsuruga", "Sakai"}
    assert set(significant) == expected

    with (robustness_dir / "metrics.json").open() as f:
        metrics = json.load(f)
    assert metrics["n_donors"] == 1709
    assert set(metrics["sig_open_1s_goodfit"]) == expected
    assert metrics["intime_fukui_city_p_1s"] > 0.10

    leave_one_out = pd.read_csv(
        robustness_dir / "leave_one_out_fukui_city.csv"
    )
    assert leave_one_out["open_pct"].min() >= 25
    assert leave_one_out["open_pct"].max() <= 41


def test_plot_robustness_figures(tmp_path):
    repo_root, robustness_dir = robustness_dir_or_skip()

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "plot_robustness_figures.py"),
            "--robustness-dir",
            str(robustness_dir),
            "--out-dir",
            str(tmp_path),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    for name in [
        "fig4_placebo_distribution.png",
        "fig5_intime_placebo.png",
    ]:
        figure = tmp_path / name
        assert figure.is_file()
        assert figure.stat().st_size > 1000
