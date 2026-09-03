import pandas as pd
from unittest.mock import MagicMock, patch

from src.tools import market as market_mod
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


def test_market_regime_uptrend_strong_rupiah():
    idx = pd.date_range("2024-01-01", periods=300, freq="B")
    jkse = pd.DataFrame({"Close": [7000 * (1.0005 ** i) for i in range(300)]}, index=idx)
    fx = pd.DataFrame({"Close": [16000 * (0.9999 ** i) for i in range(130)]},
                      index=idx[:130])

    def fake_ticker(sym):
        m = MagicMock()
        m.history.return_value = jkse if sym == "^JKSE" else fx
        return m

    market_mod._regime_cache.clear()
    with patch.object(market_mod.yf, "Ticker", side_effect=fake_ticker):
        r = market_mod.get_market_regime()
    assert r["ihsg"]["di_atas_ma50"] is True
    assert r["ihsg"]["ret_1y"] > 0
    assert r["usdidr"]["rupiah_melemah"] is False
