import time
import feedparser

_cache: dict[str, tuple[float, list[dict]]] = {}
_TTL = 600


def fetch_stock_news(ticker: str, limit: int = 8) -> list[dict]:
    """Ambil berita gratis via RSS (Yahoo Finance + Google News)."""
    now = time.time()
    if ticker in _cache and now - _cache[ticker][0] < _TTL:
        return _cache[ticker][1][:limit]

    urls = [
        f"https://finance.yahoo.com/rss/headline?s={ticker}",
        f"https://news.google.com/rss/search?q={ticker}%20saham&hl=id&gl=ID&ceid=ID%3Aid",
    ]
    items: list[dict] = []
    for url in urls:
        try:
            feed = feedparser.parse(url)
            for e in getattr(feed, "entries", [])[:limit]:
                items.append(
                    {
                        "title": getattr(e, "title", ""),
                        "link": getattr(e, "link", ""),
                        "published": getattr(e, "published", ""),
                        "summary": getattr(e, "summary", "")[:500],
                    }
                )
        except Exception:
            continue
        if len(items) >= limit:
            break

    _cache[ticker] = (now, items)
    return items[:limit]
