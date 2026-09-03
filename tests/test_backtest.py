import pandas as pd

from src.backtest import (backtest_ticker, decision_points, features_at,
                          render_summary, summarize)


def _trend(start=100.0, daily=0.0005, n=800):
    idx = pd.date_range("2020-01-03", periods=n, freq="B")
    return pd.Series([start * ((1 + daily) ** i) for i in range(n)], index=idx)


def _fund():
    return {"per": 10.0, "pbv": 1.5, "dividendYield": 0.05,
            "marketCap": 1e12, "name": "T"}


def test_features_use_only_past_data():
    close = _trend(n=400)
    early = features_at(close, 100)
    full = features_at(close, 399)
    assert early["week52High"] <= full["week52High"]
    # ret_1y di T dihitung dari window[:T] saja
    assert "ret_1y" in early and "cagr_3y" in early


def test_decisions_are_quarterly_and_forward_covered():
    close = _trend(n=800)
    pts = decision_points(len(close), years=3)
    assert 8 <= len(pts) <= 16
    assert pts[-1] + 63 < len(close)
    diffs = {b - a for a, b in zip(pts, pts[1:])}
    assert diffs == {63}


def test_beli_on_uptrend_and_summary_math():
    close = _trend(daily=0.001, n=800)
    rows = backtest_ticker("T.JK", close, _fund(), years=1)
    assert rows, "tren naik + valuasi murah harus hasilkan keputusan"
    assert all(r["verdict"] == "BELI" for r in rows)
    assert all(r["fwd_ret"] > 0 for r in rows)
    s = summarize({"T.JK": rows}, 0.05)
    assert s["n_beli"] == len(rows)
    assert s["win_rate_beli"] == 1.0
    txt = render_summary(s)
    assert "T.JK" in txt and "IHSG buy-hold" in txt


def test_run_backtest_normalizes_and_skips_gracefully():
    from unittest.mock import patch

    import pandas as pd

    import src.backtest as bt

    idx = pd.date_range("2022-01-03", periods=800, freq="B")
    ok = pd.Series([100.0] * 800, index=idx)
    with patch.object(bt, "fetch_close",
                      side_effect=lambda t, period="4y": None if t == "XX.JK" else ok), \
         patch.object(bt, "get_fundamentals",
                      return_value={"per": 10.0, "pbv": 1.5, "dividendYield": 0.05,
                                    "marketCap": 1e12, "name": "T"}):
        out = bt.run_backtest(["BBCA", "XX"], years=1)
    assert "BBCA.JK" in out
    assert "Dilewati (data tidak tersedia): XX.JK" in out


def test_downtrend_with_expensive_valuation_rejects_beli():
    close = _trend(daily=-0.002, n=800)
    pricey = {"per": 40.0, "pbv": 8.0, "dividendYield": 0.0,
              "marketCap": 1e12, "name": "T"}
    rows = backtest_ticker("T.JK", close, pricey, years=1)
    assert rows
    assert all(r["verdict"] != "BELI" for r in rows)
    s = summarize({"T.JK": rows}, -0.02)
    assert s["n_beli"] == 0
    assert "Tidak ada sinyal BELI" in render_summary(s)
