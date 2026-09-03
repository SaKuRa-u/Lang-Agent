from unittest.mock import MagicMock, patch

import pandas as pd

from src.validate import validate_row
from src.tools import market as market_mod


def test_validate_clean():
    f = {"price": 100.0, "per": 10.0, "pbv": 1.5, "dividendYield": 0.05,
         "volatility": 0.3}
    assert validate_row("A.JK", f, news_count=3) == []


def test_validate_nan_price_and_extremes():
    f = {"price": None, "per": 80.0, "pbv": 1.5, "dividendYield": 0.35,
         "volatility": 0.9}
    flags = validate_row("A.JK", f, news_count=0)
    joined = " ".join(flags)
    assert "harga tidak tersedia" in joined
    assert "PER tidak wajar" in joined
    assert "ekstrem" in joined
    assert "0 berita" in joined
    assert "volatilitas sangat tinggi" in joined


def test_validate_error_short_circuits():
    flags = validate_row("A.JK", {"ticker": "A.JK", "error": "boom"})
    assert len(flags) == 1 and "boom" in flags[0]


def test_market_nan_tail_uses_last_valid_close():
    idx = pd.date_range("2024-01-01", periods=60, freq="B")
    closes = [100.0 + i for i in range(60)]
    closes[-1] = float("nan")
    fake_hist = pd.DataFrame({"Close": closes}, index=idx)
    fake_ticker = MagicMock()
    fake_ticker.info = {"trailingPE": 10.0, "currentPrice": 150.0}
    fake_ticker.history.return_value = fake_hist
    with patch.object(market_mod.yf, "Ticker", return_value=fake_ticker):
        d = market_mod.get_fundamentals("NANX.JK")
    assert d["price"] == 158.0  # baris valid terakhir, bukan NaN/currentPrice
    assert d["ma50"] == sum(closes[:59][-50:]) / 50


def test_fundamental_node_attaches_flags():
    from src.agents.fundamental import fundamental_analyst

    with patch("src.agents.fundamental.get_fundamentals",
               return_value={"ticker": "A.JK", "price": None, "per": 5}):
        out = fundamental_analyst({"ticker": "A.JK", "news": []})
    assert any("harga tidak tersedia" in fl for fl in out["flags"])
    assert out["fundamentals"]["_flags"] == out["flags"]
