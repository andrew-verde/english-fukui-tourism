"""Contract tests for the committed and reproducible causal-arm summary."""

import ast
import hashlib
import os
from pathlib import Path
import importlib.util

import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
FEED_A = ROOT / "data" / "causal" / "fukui_municipalities_scm.csv"
PRODUCER = ROOT / "scripts" / "build_causal_arm_summary.py"
EXPECTED_SHA256 = "ff6cd1afecb0ec1175434cba0ab9964511fe9167ef57166c50e8ba713f84d953"
EXPECTED_COLUMNS = [
    "area_code",
    "en",
    "name",
    "pre_rmspe",
    "good_fit",
    "open_spike_log",
    "sustained_2025_log",
    "post_mean_gap_log",
    "open_pct",
    "sust_pct",
    "rmspe_ratio",
    "p_meangap",
    "p_ratio",
]


def _producer_expected_sha256() -> str:
    tree = ast.parse(PRODUCER.read_text(encoding="utf-8"))
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "EXPECTED_SHA256"
                for target in node.targets
            )
        ):
            return ast.literal_eval(node.value)
    raise AssertionError("Producer does not define EXPECTED_SHA256")


def test_committed_causal_arm_summary_contract() -> None:
    summary = pd.read_csv(FEED_A)

    assert len(summary) == 17
    assert summary.columns.tolist() == EXPECTED_COLUMNS
    assert hashlib.sha256(FEED_A.read_bytes()).hexdigest() == EXPECTED_SHA256
    assert _producer_expected_sha256() == EXPECTED_SHA256


@pytest.mark.skipif(
    not os.environ.get("RUN_NETWORK_TESTS"),
    reason="set RUN_NETWORK_TESTS=1 to regenerate Feed A from the pinned upstream panel",
)
def test_full_network_regeneration() -> None:
    spec = importlib.util.spec_from_file_location("build_causal_arm_summary", PRODUCER)
    assert spec and spec.loader
    producer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(producer)

    regenerated = producer.build_summary()
    committed = pd.read_csv(FEED_A)
    assert regenerated[producer.EXACT_COLUMNS].reset_index(drop=True).equals(
        committed[producer.EXACT_COLUMNS].reset_index(drop=True)
    )
    assert np.allclose(
        regenerated[producer.NUMERIC_COLUMNS].to_numpy(float),
        committed[producer.NUMERIC_COLUMNS].to_numpy(float),
        atol=1e-6,
        rtol=0,
    )
    assert np.array_equal(regenerated["open_pct"] > 5, committed["open_pct"] > 5)
    assert np.array_equal(regenerated["sust_pct"] >= 0, committed["sust_pct"] >= 0)
