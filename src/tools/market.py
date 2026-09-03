import time
import yfinance as yf

_cache: dict[str, tuple[float, dict]] = {}
_TTL = 600


def get_fundamentals(ticker: str) -> dict:
    """Ambil data fundamental + harga via yfinance. Ticker wajib .JK untuk IDX."""
    now = time.time()
    if ticker in _cache and now - _cache[ticker][0] < _TTL:
        return _cache[ticker][1]

    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
        hist = t.history(period="6mo")
        price = float(hist["Close"].iloc[-1]) if len(hist) else info.get("currentPrice")
        ma50 = float(hist["Close"].rolling(50).mean().iloc[-1]) if len(hist) >= 50 else None
        ma200 = float(hist["Close"].rolling(200).mean().iloc[-1]) if len(hist) >= 200 else None
        dy = info.get("dividendYield")
        if isinstance(dy, (int, float)) and dy > 1:
            # yfinance tak konsisten: kadang persen (8.06) bukan fraksi (0.0806).
            dy = dy / 100
        data = {
            "ticker": ticker,
            "price": price,
            "per": info.get("trailingPE"),
            "pbv": info.get("priceToBook"),
            "marketCap": info.get("marketCap"),
            "dividendYield": dy,
            "week52High": info.get("fiftyTwoWeekHigh"),
            "week52Low": info.get("fiftyTwoWeekLow"),
            "ma50": ma50,
            "ma200": ma200,
            "name": info.get("longName") or info.get("shortName"),
        }
    except Exception as e:
        data = {"ticker": ticker, "error": f"data tidak tersedia: {e}"}

    _cache[ticker] = (now, data)
    return data
