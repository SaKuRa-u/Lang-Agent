from unittest.mock import patch

from src.graph import router
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


def test_router_vague_questions_do_not_trigger_blind_screening():
    for msg in ["saham apa yang bagus saat ini?",
                "Lakukan analisis terhadap klaim tersebut.",
                "Saya ingin investasi tapi bingung mulai dari mana"]:
        assert not has_analysis_intent(msg), msg
        out = router(_base(request=msg))
        assert out["mode"] == "guide", msg


def test_router_explicit_screening_words_still_screen():
    for msg in ["carikan yang dividennya bagus",
                "mencari saham murah",
                "tolong pilihkan 3 saham",
                "rekomendasi portofolio dong"]:
        assert has_analysis_intent(msg), msg
        out = router(_base(request=msg))
        assert out["mode"] == "batch", msg


def test_request_text_prefers_newest_human_message():
    from langchain_core.messages import AIMessage, HumanMessage

    from src.graph import request_text

    state = _base(request="pesan lama dividen",
                  messages=[HumanMessage(content="pesan lama dividen"),
                            AIMessage(content="jawaban lama")])
    assert request_text(state) == "pesan lama dividen"
    state["messages"].append(HumanMessage(content="analisa capital gain BBRI"))
    assert request_text(state) == "analisa capital gain BBRI"


def test_second_message_in_same_thread_routes_fresh():
    out = router(_base(request="analisa BBCA",
                       last_request="analisa BBCA",
                       messages=[]))
    assert out["mode"] == "single" and "history" not in out
