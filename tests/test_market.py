import pandas as pd

from src.tools.market import history_stats


def _prices(start=100.0, daily=0.001, n=600):
    return pd.DataFrame({"Close": [start * ((1 + daily) ** i) for i in range(n)]})


def test_history_stats_geometric_growth():
    stats = history_stats(_prices())
    # 1.001^252 - 1 ~= 0.287
    assert 0.25 < stats["ret_1y"] < 0.33
    assert 0.25 < stats["cagr_3y"] < 0.33
    assert 0 <= stats["volatility"] < 0.01
    assert stats["max_drawdown"] == 0.0


def test_history_stats_drawdown_and_short_series():
    prices = [100, 110, 90, 95, 80]
    stats = history_stats(pd.DataFrame({"Close": prices}))
    assert stats["ret_1y"] == 80 / 100 - 1
    assert stats["max_drawdown"] < 0
    assert history_stats(pd.DataFrame({"Close": [100]})) == {}
