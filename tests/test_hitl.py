from unittest.mock import patch, MagicMock
from src.graph import build_hitl_graph
import main as cli


def test_hitl_graph_pauses_before_reporter():
    with patch("src.agents.sentiment.get_llm"), patch("src.agents.reporter.get_llm"), \
         patch("src.graph.get_llm") as mg:
        mg.return_value.invoke.side_effect = [
            MagicMock(content="sentiment_analyst"),
            MagicMock(content="reporter"),
        ]
        g = build_hitl_graph(":memory:")
        cfg = {"configurable": {"thread_id": "t1"}}
        out = g.invoke({"ticker": "BBCA.JK", "news": [{"title": "x"}], "fundamentals": {"price": 1}, "sentiment": "", "report": "", "recommendation": "", "history": ["news_collector", "fundamental_analyst"], "messages": []}, config=cfg)
    assert out.get("report", "") == ""


def test_cli_resume_keeps_thread_id(monkeypatch, tmp_path, capsys):
    db = str(tmp_path / "c.sqlite")
    with patch("src.tools.news.fetch_stock_news", return_value=[{"title": "x"}]), \
         patch("src.tools.market.get_fundamentals", return_value={"price": 1}), \
         patch("src.agents.news_collector.fetch_stock_news", return_value=[{"title": "x"}]), \
         patch("src.agents.fundamental.get_fundamentals", return_value={"price": 1}), \
         patch("src.agents.sentiment.get_llm") as m1, \
         patch("src.agents.reporter.get_llm") as m2, \
         patch("src.agents.critic.get_llm") as m3, \
         patch("src.graph.get_llm") as mg:
        mg.return_value.invoke.side_effect = [
            MagicMock(content="news_collector"),
            MagicMock(content="fundamental_analyst"),
            MagicMock(content="sentiment_analyst"),
            MagicMock(content="reporter"),
            MagicMock(content="DONE"),
        ]
        m1.return_value.invoke.return_value = MagicMock(content="netral")
        m2.return_value.invoke.return_value = MagicMock(content="Laporan BELI. Bukan nasihat finansial.")
        m3.return_value.invoke.return_value = MagicMock(
            content="KEYAKINAN: 70. VERDIK: SETUJU karena valuasi. Bukan nasihat finansial.")
        monkeypatch.setattr("builtins.input", lambda _: "y")
        cli.run_hitl("BBCA.JK", db_path=db)
    assert "BELI" in capsys.readouterr().out
