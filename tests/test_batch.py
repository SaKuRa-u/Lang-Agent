from unittest.mock import MagicMock, patch

from src.universe import WATCHLIST, parse_batch_request
from src.scoring import score_fundamentals


def test_parse_explicit_tickers_top_n():
    out = parse_batch_request("analisa BBCA, bbri dan GOTO top 3")
    assert out["tickers"] == ["BBCA.JK", "BBRI.JK", "GOTO.JK"]
    assert out["top_n"] == 3
    assert out["fallback"] is False


def test_parse_lq45_keyword():
    out = parse_batch_request("minta top 10 LQ45")
    assert out["top_n"] == 10
    assert out["universe"] == "LQ45"
    assert len(out["tickers"]) == 45
    assert all(t.endswith(".JK") for t in out["tickers"])


def test_parse_empty_fallback_watchlist():
    out = parse_batch_request("halo, apa kabar?")
    assert out["fallback"] is True
    assert [t.removesuffix(".JK") for t in out["tickers"]] == WATCHLIST


def test_score_value_beats_premium():
    cheap = {"per": 8, "pbv": 0.9, "dividendYield": 0.06, "price": 100, "ma50": 90,
             "week52High": 200, "week52Low": 80}
    pricey = {"per": 40, "pbv": 8, "dividendYield": 0, "price": 190, "ma50": 200,
              "week52High": 200, "week52Low": 80}
    s_cheap, _ = score_fundamentals(cheap)
    s_pricey, _ = score_fundamentals(pricey)
    assert s_cheap > s_pricey


def test_score_error_data():
    s, reasons = score_fundamentals({"ticker": "X.JK", "error": "boom"})
    assert s == float("-inf")
    assert reasons == ["data tidak tersedia"]


def _fund(price_pe):
    price, pe = price_pe
    return {"ticker": "T.JK", "price": price, "per": pe, "pbv": 1.5,
            "dividendYield": 0.04, "week52High": 200, "week52Low": 50,
            "ma50": 90, "ma200": None, "name": "T"}


def test_batch_end_to_end_mocked():
    from src.batch_graph import batch_graph

    funds = {"BBCA.JK": _fund((100, 8)), "BBRI.JK": _fund((100, 40))}
    with patch("src.tools.market.get_fundamentals", side_effect=lambda t: funds[t]), \
         patch("src.tools.news.fetch_stock_news", return_value=[{"title": "x"}]), \
         patch("src.agents.sentiment.get_llm") as m1, \
         patch("src.agents.reporter.get_llm") as m2, \
         patch("src.batch_graph.get_llm") as m3:
        m1.return_value.invoke.return_value = MagicMock(content="netral")
        m2.return_value.invoke.return_value = MagicMock(
            content="Laporan BELI. Bukan nasihat finansial.")
        m3.return_value.invoke.return_value = MagicMock(
            content="Ringkasan. Bukan nasihat finansial.")
        out = batch_graph.invoke({
            "request": "analisa BBCA BBRI top 1", "tickers": [], "top_n": 5,
            "fallback": False, "scanned": [], "ranked": [],
            "picks": [], "summary": "", "messages": [],
        })
    assert out["ranked"][0] == "BBCA.JK"
    assert len(out["picks"]) == 1
    assert out["picks"][0]["ticker"] == "BBCA.JK"
    assert "Bukan nasihat finansial" in out["summary"]


def test_score_percent_style_dividend_normalized():
    f = {"per": 10, "pbv": 1.5, "dividendYield": 8.06, "price": 100,
         "ma50": 90, "week52High": 200, "week52Low": 50}
    s, reasons = score_fundamentals(f)
    assert any("8.1%" in r for r in reasons)
    assert s >= 2


def test_summarize_prompt_answers_user_request():
    from src.batch_graph import summarize_node

    state = {"request": "budget 100rb per bulan, platform apa?",
             "top_n": 1, "fallback": True,
             "scanned": [{"ticker": "BBCA.JK", "score": 3.0,
                          "reasons": ["PER wajar"],
                          "fundamentals": {"price": 6775}}],
             "picks": [{"ticker": "BBCA.JK", "report": "R",
                        "recommendation": "TUNGGU", "score": 3.0,
                        "reasons": ["PER wajar"]}],
             "summary": "", "messages": []}
    with patch("src.batch_graph.get_llm") as m:
        m.return_value.invoke.return_value = MagicMock(content="Ringkasan.")
        out = summarize_node(state)
    prompt = m.return_value.invoke.call_args[0][0]
    assert "budget 100rb" in prompt
    assert "1 Lot" in prompt and "Rp677.500" in prompt
    assert "Hist 1thn" in prompt and "ekstrapolasi" in prompt
    assert "JANGAN janjikan return" in prompt
    assert out["summary"] == "Ringkasan."
