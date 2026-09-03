import time
import feedparser

_cache: dict[str, tuple[float, list[dict]]] = {}
_TTL = 600


def fetch_stock_news(ticker: str, limit: int = 8) -> list[dict]:
    """Riset web gratis multi-query: Yahoo Finance + Google News (umum +
    dividen/laba), deduplikasi per link."""
    now = time.time()
    if ticker in _cache and now - _cache[ticker][0] < _TTL:
        return _cache[ticker][1][:limit]

    base = ticker.removesuffix(".JK")
    queries = [f"{ticker}%20saham", f"{base}%20dividen%20laba%20saham"]
    urls = [f"https://finance.yahoo.com/rss/headline?s={ticker}"]
    for q in queries:
        urls.append(f"https://news.google.com/rss/search?q={q}&hl=id&gl=ID&ceid=ID%3Aid")
    items: list[dict] = []
    seen: set[str] = set()
    for url in urls:
        try:
            feed = feedparser.parse(url)
            for e in getattr(feed, "entries", [])[:limit]:
                link = getattr(e, "link", "") or getattr(e, "title", "")
                if link in seen:
                    continue
                seen.add(link)
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
        if len(items) >= limit * 2:
            break

    _cache[ticker] = (now, items)
    return items[:limit]
