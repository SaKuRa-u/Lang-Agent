"""Batch graph: two-stage scan (tahap 1 tanpa LLM, tahap 2 deep-dive top-N)."""

from concurrent.futures import ThreadPoolExecutor
from typing import Annotated, TypedDict

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import AIMessage, AnyMessage

from src.state import normalize_ticker
from src.universe import parse_batch_request
from src.scoring import score_fundamentals
from src.tools import market as market_mod
from src.tools import news as news_mod
from src.agents.sentiment import sentiment_analyst
from src.agents.reporter import reporter
from src.llm import get_llm

DISCLAIMER = "Bukan nasihat finansial. Lakukan riset mandiri."
MAX_WORKERS = 5


class BatchState(TypedDict):
    request: str
    tickers: list[str]
    top_n: int
    fallback: bool
    scanned: list[dict]
    ranked: list[str]
    picks: list[dict]
    summary: str
    messages: Annotated[list[AnyMessage], add_messages]


def parse_node(state: BatchState) -> dict:
    parsed = parse_batch_request(state.get("request", ""))
    return {"tickers": parsed["tickers"], "top_n": parsed["top_n"], "fallback": parsed["fallback"]}


def _scan_one(ticker: str) -> dict:
    t = normalize_ticker(ticker)
    f = market_mod.get_fundamentals(t)
    score, reasons = score_fundamentals(f)
    return {"ticker": t, "fundamentals": f, "score": score, "reasons": reasons}


def scan_node(state: BatchState) -> dict:
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        scanned = list(pool.map(_scan_one, state.get("tickers", [])))
    return {"scanned": scanned}


def rank_node(state: BatchState) -> dict:
    ranked = sorted(state.get("scanned", []), key=lambda r: r["score"], reverse=True)
    return {"scanned": ranked, "ranked": [r["ticker"] for r in ranked]}


def _deepdive_one(row: dict) -> dict:
    """Analisa penuh 1 finalis: pakai fundamental hasil scan (tanpa refetch)."""
    sub = {
        "ticker": row["ticker"], "news": [], "fundamentals": row["fundamentals"],
        "sentiment": "", "report": "", "recommendation": "",
        "history": [], "messages": [],
    }
    sub["news"] = news_mod.fetch_stock_news(row["ticker"])
    sub.update(sentiment_analyst(sub))
    sub.update(reporter(sub))
    return {
        "ticker": row["ticker"], "report": sub["report"],
        "recommendation": sub["recommendation"], "score": row["score"],
        "reasons": row["reasons"],
    }


def deepdive_node(state: BatchState) -> dict:
    top = state.get("scanned", [])[: state.get("top_n", 5)]
    with ThreadPoolExecutor(max_workers=min(3, max(1, len(top)))) as pool:
        picks = list(pool.map(_deepdive_one, top))
    # Kembalikan urutan ranking (thread pool tidak menjamin urutan).
    order = {r["ticker"]: i for i, r in enumerate(top)}
    picks.sort(key=lambda p: order.get(p["ticker"], 99))
    return {"picks": picks}


def _lot_price(f: dict) -> str:
    p = (f or {}).get("price")
    if isinstance(p, (int, float)) and p > 0:
        return f"Rp{int(p * 100):,}".replace(",", ".")
    return "n/a"


def _hist_str(f: dict) -> str:
    r = (f or {}).get("ret_1y")
    if isinstance(r, (int, float)):
        return f"{r:+.1%}/thn"
    return "n/a"


def summarize_node(state: BatchState) -> dict:
    lines = ["| Rank | Ticker | Skor | 1 Lot | Hist 1thn | Alasan |",
             "|---|---|---|---|---|---|"]
    for i, r in enumerate(state.get("scanned", []), 1):
        f = r.get("fundamentals", {})
        lines.append(
            f"| {i} | {r['ticker']} | {r['score']:.1f} | {_lot_price(f)} | "
            f"{_hist_str(f)} | {'; '.join(r['reasons'])} |"
        )
    table = "\n".join(lines)
    briefs = "\n\n".join(
        f"### {p['ticker']} -> {p['recommendation']}\n{p['report']}" for p in state.get("picks", [])
    )
    uni = ("watchlist default (pesan user tidak menyebut ticker)"
           if state.get("fallback") else "sesuai permintaan user")
    llm = get_llm()
    prompt = (
        "Buat laporan ringkas batch saham IDX dalam Bahasa Indonesia.\n"
        f"Permintaan user (JAWAB LANGSUNG bila berisi pertanyaan): {state.get('request') or '-'}\n"
        f"Universe: {uni}. Top-N: {state.get('top_n')}.\n"
        f"Tabel ranking:\n{table}\n\n"
        f"Deep-dive finalis:\n{briefs}\n\n"
        "Aturan:\n"
        "1) Salin tabel leaderboard apa adanya.\n"
        "2) Bedah top picks (1-2 kalimat + rekomendasi tiap pick).\n"
        "3) Bila user menyebut budget: bandingkan dengan kolom 1 Lot; bila budget "
        "< 1 lot katakan jujur dan beri alternatif (saham <Rp1000/lembar, menabung "
        "beberapa bulan, atau platform berfitur fraksional/odd-lot — kriteria umum: "
        "terdaftar OJK, fee transparan; tanpa menjamin).\n"
        "4) Bila user tanya proyeksi keuntungan: JANGAN janjikan return; beri tabel "
        "ILUSTRASI 3 skenario berjangkar data historis dari tabel/fundamental "
        "(ret_1y, cagr_3y, volatility, max_drawdown) — pesimis ≈ basis − volatilitas, "
        "basis ≈ CAGR historis, optimis ≈ basis + volatilitas — atas total setoran, "
        "berlabel jelas 'ekstrapolasi statistik, bukan prediksi; kinerja masa lalu "
        "tidak menjamin masa depan'.\n"
        "5) Bila user tanya platform: kriteria umum saja, tanpa klaim mutlak.\n"
        f"Akhiri dengan: {DISCLAIMER}"
    )
    res = llm.invoke(prompt)
    summary = str(res.content)
    return {"summary": summary, "messages": [AIMessage(content=summary)]}


def build_batch_graph():
    g = StateGraph(BatchState)
    g.add_node("parse", parse_node)
    g.add_node("scan", scan_node)
    g.add_node("rank", rank_node)
    g.add_node("deepdive", deepdive_node)
    g.add_node("summarize", summarize_node)
    g.set_entry_point("parse")
    g.add_edge("parse", "scan")
    g.add_edge("scan", "rank")
    g.add_edge("rank", "deepdive")
    g.add_edge("deepdive", "summarize")
    g.add_edge("summarize", END)
    return g.compile()


batch_graph = build_batch_graph()
