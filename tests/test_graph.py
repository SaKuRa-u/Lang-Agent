from unittest.mock import MagicMock, patch

from src.state import normalize_ticker
from src.graph import graph


def test_normalize_ticker():
    assert normalize_ticker("bbca") == "BBCA.JK"
    assert normalize_ticker("BBCA.JK") == "BBCA.JK"


def _base(**kw):
    state = {"request": "", "ticker": "", "tickers": [], "top_n": 5,
             "fallback": False, "risk": "moderat", "horizon_months": None,
             "budget_monthly": None, "news": [], "fundamentals": {},
             "flags": [], "regime": {}, "sentiment": "", "report": "",
             "recommendation": "", "critique": "", "scanned": [],
             "ranked": [], "picks": [], "summary": "", "batch_review": "",
             "history": [], "messages": []}
    state.update(kw)
    return state


def test_handoff_chain_runs_fixed_order():
    """Rantai single deterministik: news -> fundamental -> sentimen ->
    reporter -> critic, tanpa routing LLM."""
    with patch("src.agents.news_collector.fetch_stock_news",
               return_value=[{"title": "x"}]), \
         patch("src.agents.fundamental.get_fundamentals",
               return_value={"ticker": "BBCA.JK", "price": 100.0, "per": 10.0,
                             "pbv": 1.5, "dividendYield": 0.05}), \
         patch("src.agents.sentiment.get_llm") as m1, \
         patch("src.agents.reporter.get_llm") as m2, \
         patch("src.agents.critic.get_llm") as m3:
        m1.return_value.invoke.return_value = MagicMock(content="netral")
        m2.return_value.invoke.return_value = MagicMock(
            content="Laporan BELI. Bukan nasihat finansial.")
        m3.return_value.invoke.return_value = MagicMock(
            content="KEYAKINAN: 70. VERDIK: SETUJU.")
        out = graph.invoke(_base(request="analisa BBCA"))
    assert out["history"] == ["news_collector", "fundamental_analyst",
                              "sentiment_analyst", "reporter", "critic"]
    assert out["recommendation"] == "BELI"
    assert "SETUJU" in out["critique"]
