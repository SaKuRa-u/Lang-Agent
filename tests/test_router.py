from unittest.mock import MagicMock, patch

from src.graph import graph


def _base(**kw):
    state = {"request": "", "ticker": "", "tickers": [], "top_n": 5,
             "fallback": False, "news": [], "fundamentals": {},
             "sentiment": "", "report": "", "recommendation": "",
             "scanned": [], "ranked": [], "picks": [], "summary": "",
             "history": [], "messages": []}
    state.update(kw)
    return state


def _mock_single_chain():
    return (
        patch("src.agents.news_collector.fetch_stock_news",
              return_value=[{"title": "x"}]),
        patch("src.agents.fundamental.get_fundamentals",
              return_value={"ticker": "BBCA.JK", "price": 100}),
        patch("src.agents.sentiment.get_llm"),
        patch("src.agents.reporter.get_llm"),
    )


def test_request_single_ticker_uses_single_path():
    p1, p2, p3, p4 = _mock_single_chain()
    with p1, p2, p3 as m3, p4 as m4:
        m3.return_value.invoke.return_value = MagicMock(content="netral")
        m4.return_value.invoke.return_value = MagicMock(
            content="Laporan BELI. Bukan nasihat finansial.")
        out = graph.invoke(_base(request="analisa BBCA dong"))
    assert out["mode"] == "single"
    assert out["ticker"] == "BBCA.JK"
    assert out["recommendation"] == "BELI"
    assert out["summary"] == ""


def test_legacy_ticker_input_still_single():
    p1, p2, p3, p4 = _mock_single_chain()
    with p1, p2, p3 as m3, p4 as m4:
        m3.return_value.invoke.return_value = MagicMock(content="netral")
        m4.return_value.invoke.return_value = MagicMock(
            content="Laporan TUNGGU. Bukan nasihat finansial.")
        out = graph.invoke(_base(ticker="BBCA.JK"))
    assert out["mode"] == "single"
    assert out["report"] != ""


def test_request_multi_ticker_uses_batch_path():
    funds = {"BBCA.JK": {"ticker": "BBCA.JK", "price": 100, "per": 8,
                         "pbv": 1.5, "dividendYield": 0.04,
                         "week52High": 200, "week52Low": 50,
                         "ma50": 90, "ma200": None, "name": "A"},
             "BBRI.JK": {"ticker": "BBRI.JK", "price": 100, "per": 40,
                         "pbv": 8, "dividendYield": 0,
                         "week52High": 200, "week52Low": 50,
                         "ma50": 200, "ma200": None, "name": "B"}}
    with patch("src.tools.market.get_fundamentals",
               side_effect=lambda t: funds[t]), \
         patch("src.tools.news.fetch_stock_news",
               return_value=[{"title": "x"}]), \
         patch("src.agents.sentiment.get_llm") as m1, \
         patch("src.agents.reporter.get_llm") as m2, \
         patch("src.batch_graph.get_llm") as m3:
        m1.return_value.invoke.return_value = MagicMock(content="netral")
        m2.return_value.invoke.return_value = MagicMock(
            content="Laporan BELI. Bukan nasihat finansial.")
        m3.return_value.invoke.return_value = MagicMock(
            content="Ringkasan. Bukan nasihat finansial.")
        out = graph.invoke(_base(request="analisa BBCA BBRI top 1"))
    assert out["mode"] == "batch"
    assert out["ranked"][0] == "BBCA.JK"
    assert len(out["picks"]) == 1
    assert "Bukan nasihat finansial" in out["summary"]
