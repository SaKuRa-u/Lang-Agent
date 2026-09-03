"""Backtest walk-forward jujur: keputusan memakai HANYA data <= T.

Asumsi yang dinyatakan terbuka (bukan lookahead tersembunyi):
- Fitur harga (MA50, 52w, ret_1y, vol, drawdown) dihitung dari close[:T].
- Fundamental PER/PBV/dividen memakai nilai KINI (snapshot historis tidak
  tersedia gratis) — label: asumsi konstan.
- Regime pasar netral; dividen tidak masuk return (diremehkan, dinyatakan).
- Forward return 63 hari bursa (~1 kuartal) per keputusan.
"""

import pandas as pd

from src.tools.market import history_stats, get_fundamentals
from src.scoring import score_fundamentals
from src.validate import validate_row
from src.verdict import rule_verdict

FWD_DAYS = 63
QUARTER = 63


def features_at(close: pd.Series, t: int) -> dict:
    """Fitur + fundamental semu per tanggal-T (tanpa melihat masa depan)."""
    window = close.iloc[: t + 1]
    frame = pd.DataFrame({"Close": window})
    last = float(window.iloc[-1])
    f: dict = {"price": last}
    f.update(history_stats(frame))
    if len(window) >= 50:
        f["ma50"] = float(window.rolling(50).mean().iloc[-1])
    lookback = window.iloc[-252:] if len(window) > 252 else window
    f["week52High"] = float(lookback.max())
    f["week52Low"] = float(lookback.min())
    return f


def decision_points(n: int, years: int = 3, step: int = QUARTER) -> list[int]:
    """Indeks T kuartalan selama `years` terakhir, butuh +FWD_DAYS ke depan."""
    start = max(step, n - years * 252 - FWD_DAYS)
    return [t for t in range(start, n - FWD_DAYS, step)]


def backtest_ticker(ticker: str, close: pd.Series, fund_now: dict,
                    years: int = 3) -> list[dict]:
    """Simulasi per ticker. fund_now: PER/PBV/dividen kini (asumsi konstan)."""
    out = []
    for t in decision_points(len(close), years):
        f = dict(fund_now)
        f.update(features_at(close, t))
        flags = validate_row(ticker, f)
        score, _ = score_fundamentals(f)
        verdict, _ = rule_verdict(f, flags, {}, score=score)
        fwd = float(close.iloc[t + FWD_DAYS]) / float(close.iloc[t]) - 1
        out.append({"date": str(close.index[t].date()), "verdict": verdict,
                    "score": round(score, 1), "fwd_ret": round(fwd, 4)})
    return out


def summarize(decisions: dict[str, list[dict]],
              bench_buyhold: float | None) -> dict:
    """Agregat: hanya keputusan BELI vs benchmark buy-hold IHSG."""
    per_ticker = {}
    all_beli = []
    for ticker, rows in decisions.items():
        beli = [r["fwd_ret"] for r in rows if r["verdict"] == "BELI"]
        all_beli += beli
        per_ticker[ticker] = {
            "n": len(rows),
            "n_beli": len(beli),
            "win_rate_beli": (sum(1 for x in beli if x > 0) / len(beli)) if beli else None,
            "avg_fwd_beli": (sum(beli) / len(beli)) if beli else None,
        }
    return {"per_ticker": per_ticker,
            "n_beli": len(all_beli),
            "avg_fwd_beli": (sum(all_beli) / len(all_beli)) if all_beli else None,
            "win_rate_beli": (sum(1 for x in all_beli if x > 0) / len(all_beli)) if all_beli else None,
            "ihsg_buyhold": bench_buyhold}


def render_summary(summary: dict) -> str:
    lines = ["# Backtest walk-forward (tanpa lookahead)",
             "",
             "| Ticker | Keputusan | n BELI | Win% BELI | Rata2 fwd/kuartal |",
             "|---|---|---|---|---|"]
    for t, s in summary["per_ticker"].items():
        wr = f"{s['win_rate_beli']:.0%}" if s["win_rate_beli"] is not None else "n/a"
        av = f"{s['avg_fwd_beli']:+.1%}" if s["avg_fwd_beli"] is not None else "n/a"
        lines.append(f"| {t} | {s['n']} | {s['n_beli']} | {wr} | {av} |")
    a = summary["avg_fwd_beli"]
    w = summary["win_rate_beli"]
    b = summary["ihsg_buyhold"]
    lines += ["",
              f"BELI agregat: n={summary['n_beli']}, "
              f"rata2 {a:+.1%} (menang {w:.0%})" if a is not None else "Tidak ada sinyal BELI.",
              f"IHSG buy-hold periode sama: {b:+.1%}" if b is not None else "Benchmark n/a.",
              "",
              "Asumsi: fundamental PER/PBV/dividen konstan (snapshot historis tak tersedia); "
              "regime netral; dividen tidak masuk return; forward 63 hari bursa."]
    return "\n".join(lines)


def fetch_close(ticker: str, period: str = "4y") -> pd.Series | None:
    import yfinance as yf

    try:
        hist = yf.Ticker(ticker).history(period=period)["Close"].dropna()
    except Exception:
        return None
    return hist if len(hist) else None


def run_backtest(tickers: list[str], years: int = 3) -> str:
    """Orkestrasi network: fetch paralel, fund_now, benchmark IHSG, render."""
    from concurrent.futures import ThreadPoolExecutor

    from src.state import normalize_ticker

    tickers = [normalize_ticker(t) for t in tickers]
    with ThreadPoolExecutor(max_workers=5) as pool:
        closes = dict(zip(tickers, pool.map(fetch_close, tickers)))
    decisions, skipped = {}, []
    for t in tickers:
        close = closes[t]
        if close is None or len(close) < 100:
            skipped.append(t)
            continue
        info = get_fundamentals(t)
        fund_now = {k: info.get(k) for k in
                    ("per", "pbv", "dividendYield", "marketCap", "name")}
        decisions[t] = backtest_ticker(t, close, fund_now, years)
    bench = None
    try:
        j = fetch_close("^JKSE", period=f"{years}y")
        bench = float(j.iloc[-1]) / float(j.iloc[0]) - 1
    except Exception:
        pass
    out = render_summary(summarize(decisions, bench))
    if skipped:
        out += f"\n\nDilewati (data tidak tersedia): {', '.join(skipped)}."
    return out
