from unittest.mock import MagicMock, patch
from langgraph.graph import END

from src.graph import router, smart_supervisor
from src.universe import WATCHLIST, has_analysis_intent


import pytest


@pytest.fixture(autouse=True)
def _no_regime():
    with patch("src.graph.get_market_regime", return_value={}):
        yield


def _base(**kw):
    state = {"request": "", "ticker": "", "tickers": [], "top_n": 5,
             "fallback": False, "news": [], "fundamentals": {},
             "sentiment": "", "report": "", "recommendation": "",
             "scanned": [], "ranked": [], "picks": [], "summary": "",
             "history": [], "messages": []}
    state.update(kw)
    return state


def test_smart_routes_to_missing_worker():
    with patch("src.graph.get_llm") as m:
        m.return_value.invoke.return_value = MagicMock(content="fundamental_analyst")
        nxt = smart_supervisor(_base(history=["news_collector"]))
    assert nxt == "fundamental_analyst"


def test_smart_garbage_falls_back_to_rule():
    with patch("src.graph.get_llm") as m:
        m.return_value.invoke.return_value = MagicMock(content="pisang goreng")
        nxt = smart_supervisor(_base())
    assert nxt == "news_collector"


def test_smart_error_falls_back_to_rule():
    with patch("src.graph.get_llm") as m:
        m.return_value.invoke.side_effect = RuntimeError("9router down")
        nxt = smart_supervisor(_base(history=["news_collector"]))
    assert nxt == "fundamental_analyst"


def test_smart_max_steps_ends_without_llm():
    with patch("src.graph.get_llm") as m:
        nxt = smart_supervisor(_base(history=["x"] * 12))
    assert nxt == END
    m.assert_not_called()


def test_router_same_request_keeps_progress():
    full = ["news_collector", "fundamental_analyst", "sentiment_analyst", "reporter"]
    out = router(_base(request="analisa BBCA", last_request="analisa BBCA",
                       ticker="BBCA.JK", report="lama", history=list(full)))
    assert out["mode"] == "single"
    assert "history" not in out  # tidak di-reset: thread berlanjut


def test_router_new_request_clears_progress():
    old = _base(request="analisa BBCA", ticker="BBCA.JK", report="lama",
                history=["news_collector", "fundamental_analyst",
                         "sentiment_analyst", "reporter"])
    out = router({**old, "request": "analisa BBRI"})
    assert out["ticker"] == "BBRI.JK"
    assert out["history"] == []
    assert out["report"] == ""


def test_router_followup_without_ticker_continues_thread_ticker():
    old = _base(request="analisa BBCA", ticker="BBCA.JK", report="lama",
                history=["news_collector"])
    out = router({**old, "request": "bagaimana risikonya?"})
    assert out["mode"] == "single"
    assert out["ticker"] == "BBCA.JK"


def test_router_analysis_intent_without_ticker_screens_watchlist():
    assert has_analysis_intent("carikan yang dividennya bagus dan proyeksikan keuntungan")
    out = router(_base(
        request="carikan yang dividennya bagus dan proyeksikan keuntungan 1 tahun"))
    assert out["mode"] == "batch"
    assert [t.removesuffix(".JK") for t in out["tickers"]] == WATCHLIST
    assert out["fallback"] is True


def test_router_greeting_stays_guide():
    assert not has_analysis_intent("halo, apa kabar?")
    out = router(_base(request="halo, apa kabar?"))
    assert out["mode"] == "guide"
