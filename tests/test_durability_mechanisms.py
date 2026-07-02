import json
from pathlib import Path

import pandas as pd
import pytest


def durability_outputs_or_skip():
    repo_root = Path(__file__).resolve().parents[1]
    output_dir = repo_root / "output" / "synthesis"
    paths = {
        "csv": output_dir / "durability_mechanisms.csv",
        "json": output_dir / "durability_mechanisms_tests.json",
        "md": output_dir / "durability_mechanisms.md",
    }
    if not all(path.is_file() for path in paths.values()):
        pytest.skip("durability mechanism outputs have not been generated")
    return paths


def test_durability_mechanism_invariants():
    paths = durability_outputs_or_skip()
    mechanisms = pd.read_csv(paths["csv"])

    assert len(mechanisms) == 17
    assert mechanisms["area_code"].is_unique

    eiheiji = mechanisms.loc[mechanisms["area_code"] == 18322].iloc[0]
    sakai = mechanisms.loc[mechanisms["area_code"] == 18210].iloc[0]
    assert eiheiji["n_respondents"] == 7218
    assert eiheiji["repeat_share_pct"] == pytest.approx(43.8349, abs=0.01)
    assert eiheiji["car_share_pct"] == pytest.approx(67.4702, abs=0.01)
    assert eiheiji["top1_purpose"] == "historic_sites"
    assert sakai["n_respondents"] == 8352
    assert sakai["car_share_pct"] == pytest.approx(74.0302, abs=0.01)

    with paths["json"].open(encoding="utf-8") as handle:
        tests = json.load(handle)
    car = tests["car_share"]
    assert car["durable_pct"] == pytest.approx(70.9891, abs=0.01)
    assert car["transient_pct"] == pytest.approx(62.3075, abs=0.01)
    assert car["z"] == pytest.approx(18.23, abs=0.05)
    assert car["z"] > 10
    assert car["p_two_sided"] < 1e-8
    assert car["durable_pct"] > car["transient_pct"]
