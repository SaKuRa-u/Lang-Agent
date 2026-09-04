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
from src.llm import get_llm

DISCLAIMER = "Bukan nasihat finansial. Lakukan riset mandiri."
MAX_WORKERS = 5


class BatchState(TypedDict):
    request: str
    tickers: list[str]
    top_n: int
    fallback: bool
    risk: str
    horizon_months: int | None
    budget_monthly: int | None
    scanned: list[dict]
    ranked: list[str]
    picks: list[dict]
    summary: str
    batch_review: str
    messages: Annotated[list[AnyMessage], add_messages]


def parse_node(state: BatchState) -> dict:
    parsed = parse_batch_request(state.get("request", ""))
    return {"tickers": parsed["tickers"], "top_n": parsed["top_n"],
            "fallback": parsed["fallback"], "risk": parsed["risk"],
            "horizon_months": parsed["horizon_months"],
            "budget_monthly": parsed["budget_monthly"]}


def _scan_one(ticker: str) -> dict:
    from src.validate import validate_row

    t = normalize_ticker(ticker)
    f = market_mod.get_fundamentals(t)
    score, reasons = score_fundamentals(f)
    flags = validate_row(t, f)
    f["_flags"] = flags
    return {"ticker": t, "fundamentals": f, "score": score,
            "reasons": reasons, "flags": flags}


def scan_node(state: BatchState) -> dict:
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        scanned = list(pool.map(_scan_one, state.get("tickers", [])))
    return {"scanned": scanned}


def rank_node(state: BatchState) -> dict:
    from src.budget import rank_for_risk

    ranked = rank_for_risk(state.get("scanned", []), state.get("risk") or "moderat")
    return {"scanned": ranked, "ranked": [r["ticker"] for r in ranked]}


def scan_has_data(state: BatchState) -> bool:
    """Guard: lanjut rank hanya bila ada baris berskor valid."""
    scanned = state.get("scanned", [])
    return bool(scanned) and any(
        r.get("score", float("-inf")) != float("-inf") for r in scanned)


def batch_abort_node(state: BatchState) -> dict:
    text = ("Tidak ada data valid untuk dianalisa (semua ticker gagal diambil "
            "atau tak dikenal). Sebutkan ticker IDX yang valid (cth BBCA, BBRI) "
            "atau universe seperti LQ45. Bukan nasihat finansial.")
    return {"summary": text, "messages": [AIMessage(content=text)]}


_single_subgraph = None


def _single():
    global _single_subgraph
    if _single_subgraph is None:
        from src.single_flow import build_single_subgraph
        _single_subgraph = build_single_subgraph()
    return _single_subgraph


def _deepdive_one(row: dict, regime=None) -> dict:
    """Analisa 1 finalis via subgraph single yang SAMA dengan jalur single.

    Fundamental hasil scan dipakai ulang (history di-seed agar tak refetch);
    berita diambil fresh oleh news_collector di dalam subgraph.
    """
    sub = _single().invoke({
        "ticker": row["ticker"], "news": [], "fundamentals": row["fundamentals"],
        "flags": row.get("flags", []), "regime": regime or {},
        "sentiment": "", "report": "", "recommendation": "",
        "critique": "", "history": ["fundamental_analyst"], "messages": [],
    })
    return {
        "ticker": row["ticker"], "report": sub.get("report", ""),
        "recommendation": sub.get("recommendation", ""),
        "critique": sub.get("critique", ""),
        "score": row["score"], "reasons": row["reasons"],
        "flags": row.get("flags", []),
    }


def deepdive_node(state: BatchState) -> dict:
    from functools import partial

    top = state.get("scanned", [])[: state.get("top_n", 5)]
    regime = state.get("regime") or {}
    with ThreadPoolExecutor(max_workers=min(3, max(1, len(top)))) as pool:
        picks = list(pool.map(partial(_deepdive_one, regime=regime), top))
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


def _pick_brief(p: dict) -> str:
    flag_txt = ""
    if p.get("flags"):
        flag_txt = f"\n⚠ Flag data: {'; '.join(p['flags'])}"
    crit_txt = ""
    if p.get("critique"):
        crit_txt = f"\n🕵️ Penilaian independen: {p['critique']}"
    return (f"### {p['ticker']} -> {p['recommendation']}\n"
            f"{p['report']}{flag_txt}{crit_txt}")


def summarize_node(state: BatchState) -> dict:
    lines = ["| Rank | Ticker | Skor | 1 Lot | Hist 1thn | Alasan |",
             "|---|---|---|---|---|---|"]
    for i, r in enumerate(state.get("scanned", []), 1):
        f = r.get("fundamentals", {})
        why = list(r["reasons"]) + [f"⚠ {fl}" for fl in r.get("flags", [])]
        lines.append(
            f"| {i} | {r['ticker']} | {r['score']:.1f} | {_lot_price(f)} | "
            f"{_hist_str(f)} | {'; '.join(why)} |"
        )
    table = "\n".join(lines)
    briefs = "\n\n".join(_pick_brief(p) for p in state.get("picks", []))
    uni = ("watchlist default (pesan user tidak menyebut ticker)"
           if state.get("fallback") else "sesuai permintaan user")
    from src.budget import plan_budget, allocation_text
    alloc_txt = ""
    if state.get("budget_monthly"):
        rows = {r["ticker"]: r for r in state.get("scanned", [])}
        items = [{"ticker": p["ticker"], "score": p.get("score", 0),
                  "fundamentals": rows.get(p["ticker"], {}).get("fundamentals", {})}
                 for p in state.get("picks", [])]
        plan = plan_budget(state["budget_monthly"], items, state.get("horizon_months"))
        alloc_txt = "\nRencana budget ala-Bibit:\n" + allocation_text(plan) + "\n"
    risk = state.get("risk") or "moderat"
    horizon = state.get("horizon_months")
    dates = sorted({(r.get("fundamentals") or {}).get("as_of")
                    for r in state.get("scanned", [])} - {None})
    llm = get_llm(temperature=0)
    prompt = (
        "Buat laporan ringkas batch saham IDX dalam Bahasa Indonesia.\n"
        f"Permintaan user (JAWAB LANGSUNG bila berisi pertanyaan): {state.get('request') or '-'}\n"
        f"Tanggal data: {', '.join(dates) if dates else 'tidak tersedia'} "
        "(cantumkan di laporan agar run bisa dibandingkan).\n"
        f"Universe: {uni}. Top-N: {state.get('top_n')}.\n"
        f"Profil risiko user: {risk}."
        + (f" Horizon: {horizon} bulan.\n" if horizon else "\n")
        + alloc_txt
        + f"Konteks pasar: {state.get('regime') or 'tidak tersedia'} — "
        "kaitkan rekomendasi dengan regime (cth IHSG di bawah MA50 / Rupiah "
        "melemah -> defensif, turunkan keyakinan cyclical).\n"
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
        "6) Bila ada flag ⚠ pada tabel/pick: cantumkan di bagian risiko dan "
        "turunkan keyakinan rekomendasi terkait.\n"
        "7) Bila ada blok Rencana budget: sajikan apa adanya (alokasi lot, dana "
        "minimal mulai per saham, sisa, catatan) dan kaitkan dengan profil risiko "
        "user; reksadana/fraksional hanya sebagai alternatif edukatif.\n"
        f"Akhiri dengan: {DISCLAIMER}"
    )
    res = llm.invoke(prompt)
    summary = str(res.content)
    return {"summary": summary, "messages": [AIMessage(content=summary)]}


def review_batch_node(state: BatchState) -> dict:
    """Critic level batch: periksa ringkasan sebelum disajikan."""
    llm = get_llm(temperature=0)
    prompt = (
        "Kamu reviewer laporan batch saham IDX (Bahasa Indonesia). Periksa:\n"
        "1) tiap pick konsisten dengan verdict guardrail + tabel;\n"
        "2) angka budget/dana minimal masuk akal;\n"
        "3) proyeksi berlabel ilustrasi, bukan janji;\n"
        "4) flag data disebut.\n"
        "Balas: 'REVIEW: lolos' atau 'REVIEW: bermasalah' + temuan "
        "(maks 5 bullet).\n\n"
        f"LAPORAN:\n{state.get('summary', '')[:4000]}"
    )
    try:
        text = str(llm.invoke(prompt).content)
    except Exception:
        text = "REVIEW: dilewati (LLM tidak tersedia)."
    return {"batch_review": text, "messages": [AIMessage(content=text)]}


def build_batch_graph():
    g = StateGraph(BatchState)
    g.add_node("parse", parse_node)
    g.add_node("scan", scan_node)
    g.add_node("rank", rank_node)
    g.add_node("deepdive", deepdive_node)
    g.add_node("summarize", summarize_node)
    g.add_node("review_batch", review_batch_node)
    g.add_node("batch_abort", batch_abort_node)
    g.set_entry_point("parse")
    g.add_edge("parse", "scan")
    g.add_conditional_edges("scan", scan_has_data, {True: "rank", False: "batch_abort"})
    g.add_edge("batch_abort", END)
    g.add_edge("rank", "deepdive")
    g.add_edge("deepdive", "summarize")
    g.add_edge("summarize", "review_batch")
    g.add_edge("review_batch", END)
    return g.compile()


batch_graph = build_batch_graph()
