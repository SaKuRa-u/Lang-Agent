import time
import yfinance as yf

_cache: dict[str, tuple[float, dict]] = {}
_TTL = 600
_regime_cache: dict[str, tuple[float, dict]] = {}
_REGIME_TTL = 3600
TRADING_DAYS = 252


def _finite(x):
    """NaN/invalid -> None (harga NaN umum di ticker IDX)."""
    if isinstance(x, bool):
        return None
    if isinstance(x, (int, float)) and x == x:
        return float(x)
    return None


def get_market_regime() -> dict:
    """Konteks pasar gratis: tren IHSG + Rupiah via yfinance (cache 1 jam)."""
    now = time.time()
    if "r" in _regime_cache and now - _regime_cache["r"][0] < _REGIME_TTL:
        return _regime_cache["r"][1]
    out: dict = {}
    try:
        j = yf.Ticker("^JKSE").history(period="1y")["Close"].dropna()
        if len(j) >= 2:
            last = float(j.iloc[-1])
            base = float(j.iloc[-252]) if len(j) > 252 else float(j.iloc[0])
            ma = _finite(j.rolling(50).mean().iloc[-1]) if len(j) >= 50 else None
            out["ihsg"] = {"ret_1y": last / base - 1 if base else None,
                           "di_atas_ma50": (last > ma) if ma else None}
    except Exception:
        pass
    try:
        u = yf.Ticker("USDIDR=X").history(period="6mo")["Close"].dropna()
        if len(u) >= 2:
            last = float(u.iloc[-1])
            ma = _finite(u.rolling(50).mean().iloc[-1]) if len(u) >= 50 else None
            out["usdidr"] = {"kurs": last,
                             "rupiah_melemah": (last > ma) if ma else None}
    except Exception:
        pass
    _regime_cache["r"] = (now, out)
    return out


def history_stats(hist) -> dict:
    """Statistik historis dari DataFrame harga (kolom Close).

    Return 1 thn, CAGR ~3 thn, volatilitas tahunan, max drawdown —
    murni deskriptif (fakta masa lalu, bukan prediksi).
    """
    try:
        close = hist["Close"].dropna()
    except Exception:
        return {}
    n = len(close)
    if n < 2:
        return {}
    last = float(close.iloc[-1])
    out: dict = {}
    base = float(close.iloc[-252]) if n > TRADING_DAYS else float(close.iloc[0])
    if base > 0:
        out["ret_1y"] = last / base - 1
    if n > 30:
        years = n / TRADING_DAYS
        first = float(close.iloc[0])
        if first > 0 and years > 0:
            out["cagr_3y"] = (last / first) ** (1 / years) - 1
    if n >= 5:
        rets = close.pct_change().dropna()
        if len(rets) > 1:
            out["volatility"] = float(rets.std() * (TRADING_DAYS ** 0.5))
        out["max_drawdown"] = float((close / close.cummax() - 1).min())
    return out


def get_fundamentals(ticker: str) -> dict:
    """Ambil data fundamental + harga via yfinance. Ticker wajib .JK untuk IDX."""
    now = time.time()
    if ticker in _cache and now - _cache[ticker][0] < _TTL:
        return _cache[ticker][1]

    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
        hist = t.history(period="3y")
        try:
            close = hist["Close"].dropna()
        except Exception:
            close = hist["Close"] if len(hist) else []
        price = _finite(close.iloc[-1]) if len(close) else None
        if price is None:
            price = _finite(info.get("currentPrice"))
        ma50 = _finite(close.rolling(50).mean().iloc[-1]) if len(close) >= 50 else None
        ma200 = _finite(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else None
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
        data.update(history_stats(hist))
    except Exception as e:
        data = {"ticker": ticker, "error": f"data tidak tersedia: {e}"}

    _cache[ticker] = (now, data)
    return data
