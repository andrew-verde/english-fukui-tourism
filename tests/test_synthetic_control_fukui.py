import numpy as np
import pandas as pd
import pytest

from scripts.synthetic_control_fukui import (
    fit_convex_weights,
    make_matrix,
    placebo_p_value,
    rmspe,
)


def test_convex_estimator_recovers_exact_mixture():
    donors = np.array([[1, 4], [2, 2], [4, 1], [3, 5]], dtype=float)
    treated = donors @ np.array([0.25, 0.75])
    weights = fit_convex_weights(treated, donors)
    assert weights == pytest.approx([0.25, 0.75], abs=1e-6)
    assert weights.sum() == pytest.approx(1)
    assert np.all(weights >= 0)


def test_rmspe_and_finite_sample_placebo_p_value():
    assert rmspe(np.array([1, 3]), np.array([1, 1])) == pytest.approx(np.sqrt(2))
    assert placebo_p_value(2.0, np.array([0.5, -2.5, 1.0])) == pytest.approx(0.5)


def test_primary_pool_excludes_hokuriku_and_requires_complete_units():
    rows = []
    for ym in (202401, 202402, 202403):
        for pref, code in ((18, 18201), (17, 17201), (20, 20201), (21, 21201)):
            if code == 21201 and ym == 202402:
                continue
            rows.append({"ym": ym, "都道府県コード": pref, "地域コード": code,
                         "地域名称": str(code), "人数": 10})
    matrix, _ = make_matrix(pd.DataFrame(rows), {15, 16, 17, 18})
    assert list(matrix.columns) == [18201, 20201]
