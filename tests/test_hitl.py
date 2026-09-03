from unittest.mock import patch
from src.graph import build_hitl_graph


def test_hitl_graph_pauses_before_reporter():
    with patch("src.agents.sentiment.get_llm"), patch("src.agents.reporter.get_llm"):
        g = build_hitl_graph(":memory:")
        cfg = {"configurable": {"thread_id": "t1"}}
        out = g.invoke({"ticker": "BBCA.JK", "news": [{"title": "x"}], "fundamentals": {"price": 1}, "sentiment": "", "report": "", "recommendation": "", "history": ["news_collector", "fundamental_analyst"], "messages": []}, config=cfg)
    assert out.get("report", "") == ""
