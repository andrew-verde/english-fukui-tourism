from pathlib import Path
import subprocess
import sys

import pytest


def test_plot_synthesis_figures(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    synthesis_dir = repo_root / "output" / "synthesis"
    csv_names = [
        "synthesis_regime_friction_map.csv",
        "synthesis_mode_friction.csv",
        "synthesis_priority_matrix.csv",
    ]
    if not all((synthesis_dir / name).is_file() for name in csv_names):
        pytest.skip("synthesis CSVs have not been generated")

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "plot_synthesis_figures.py"),
            "--synthesis-dir",
            str(synthesis_dir),
            "--out-dir",
            str(tmp_path),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    for name in [
        "fig1_regime_friction_map.png",
        "fig2_mode_friction.png",
        "fig3_priority_matrix.png",
    ]:
        figure = tmp_path / name
        assert figure.is_file()
        assert figure.stat().st_size > 1000
