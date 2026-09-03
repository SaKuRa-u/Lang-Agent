from unittest.mock import MagicMock, patch

from src.agents.critic import critic


def _state():
    return {"ticker": "BBCA.JK",
            "fundamentals": {"price": 100, "per": 10},
            "sentiment": "netral", "report": "Laporan BELI.",
            "recommendation": "BELI", "history": ["reporter"], "messages": []}


def test_critic_appends_verdict_message():
    with patch("src.agents.critic.get_llm") as m:
        m.return_value.invoke.return_value = MagicMock(
            content="KELEMAHAN: mahal. KEYAKINAN: 60. VERDIK: TIDAK SETUJU karena mahal.")
        out = critic(_state())
    assert "critic" in out["history"]
    assert "TIDAK SETUJU" in out["critique"]
    assert out["messages"][-1].type == "ai"
