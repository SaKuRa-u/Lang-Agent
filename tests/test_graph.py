from src.state import normalize_ticker
from src.graph import supervisor


def test_normalize_ticker():
    assert normalize_ticker("bbca") == "BBCA.JK"
    assert normalize_ticker("BBCA.JK") == "BBCA.JK"


def test_supervisor_routing():
    base = {"ticker": "BBCA.JK", "news": [], "fundamentals": {}, "sentiment": "", "report": "", "recommendation": "", "history": [], "messages": []}
    assert supervisor(base) == "news_collector"
    s2 = {**base, "history": ["news_collector"]}
    assert supervisor(s2) == "fundamental_analyst"
    s3 = {**s2, "history": ["news_collector", "fundamental_analyst"]}
    assert supervisor(s3) == "sentiment_analyst"
    s4 = {**s3, "history": ["news_collector", "fundamental_analyst", "sentiment_analyst"]}
    assert supervisor(s4) == "reporter"
    s5 = {**s3, "history": ["news_collector", "fundamental_analyst", "sentiment_analyst", "reporter"]}
    assert supervisor(s5) == "critic"
