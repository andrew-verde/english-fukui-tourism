import pytest

from scripts.build_japan_kanko_panel import RAW, build_panel


@pytest.fixture(scope="module")
def panel():
    if len(list(RAW.glob("city20*.csv"))) != 5:
        pytest.skip("optional raw japan-kanko-stat data not available")
    return build_panel()


def test_panel_oracle(panel):
    assert panel.ym.nunique() == 60
    assert panel.loc[panel.ym < 202403, "ym"].nunique() == 38
    fukui = panel[panel["都道府県コード"] == 18]
    assert fukui["地域コード"].nunique() == 17
    eligible = panel[~panel["都道府県コード"].isin([15, 16, 17, 18])]
    assert eligible["地域コード"].nunique() == 1806
    full = eligible.groupby("地域コード").ym.nunique()
    assert (full == 60).sum() == 1709


@pytest.mark.parametrize(
    ("code", "pre", "post"),
    [(18201, 75166.9, 113439.0), (18206, 75590.4, 135633.0), (18322, 36739.4, 64464.5)],
)
def test_fukui_means(panel, code, pre, post):
    unit = panel[panel["地域コード"] == code]
    assert unit.loc[unit.ym < 202403, "人数"].mean() == pytest.approx(pre, abs=0.1)
    assert unit.loc[unit.ym >= 202403, "人数"].mean() == pytest.approx(post, abs=0.1)
