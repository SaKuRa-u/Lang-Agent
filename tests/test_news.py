from types import SimpleNamespace
from unittest.mock import patch

from src.tools import news as news_mod


def _entry(title, link):
    return SimpleNamespace(title=title, link=link, published="p", summary="s")


def test_multi_query_and_dedupe():
    feeds = {
        "yahoo": [_entry("Y1", "u1")],
        "saham": [_entry("S1", "u2"), _entry("DUP", "u1")],
        "dividen": [_entry("D1", "u3")],
    }

    def fake_parse(url):
        if "yahoo" in url:
            return SimpleNamespace(entries=feeds["yahoo"])
        if "dividen" in url:
            return SimpleNamespace(entries=feeds["dividen"])
        return SimpleNamespace(entries=feeds["saham"])

    news_mod._cache.clear()
    with patch.object(news_mod.feedparser, "parse", side_effect=fake_parse) as mp:
        out = news_mod.fetch_stock_news("BBCA.JK", limit=8)
    urls = [c.args[0] for c in mp.call_args_list]
    assert any("yahoo" in u for u in urls)
    assert any("dividen" in u for u in urls)
    links = [i["link"] for i in out]
    assert links == ["u1", "u2", "u3"]  # duplikat u1 dibuang, urutan terjaga


def test_limit_respected():
    entries = [_entry(f"T{i}", f"u{i}") for i in range(20)]
    news_mod._cache.clear()
    with patch.object(news_mod.feedparser, "parse",
                      return_value=SimpleNamespace(entries=entries)):
        out = news_mod.fetch_stock_news("BBCA.JK", limit=5)
    assert len(out) == 5
