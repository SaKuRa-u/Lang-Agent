from src.state import StockState, normalize_ticker
from src.llm import get_llm
from src.agents.news_collector import news_collector
from src.agents.fundamental import fundamental_analyst
from src.agents.sentiment import sentiment_analyst
from src.agents.reporter import reporter
from src.universe import parse_batch_request, has_analysis_intent
from src.batch_graph import scan_node, rank_node, deepdive_node, summarize_node
from langgraph.graph import StateGraph, END
from langchain_core.messages import AIMessage

DEFAULT_TICKER = "BBCA.JK"
MAX_STEPS = 12
SINGLE_FRESH = {"news": [], "fundamentals": {}, "flags": [], "sentiment": "",
                "report": "", "recommendation": ""}
BATCH_FRESH = {"scanned": [], "ranked": [], "picks": [], "summary": ""}
GUIDE_TEXT = (
    "Halo! Saya analis saham IDX. Cukup tulis pesan biasa, contoh:\n"
    '- "analisa BBCA" (single)\n'
    '- "analisa BBCA, BBRI, TLKM top 3" (batch)\n'
    '- "top 5 LQ45"\n'
    "Hasil dalam Bahasa Indonesia + bukan nasihat finansial."
)


def request_text(state: StockState) -> str:
    """Ambil request: field `request` dulu, lalu pesan human terakhir."""
    req = (state.get("request") or "").strip()
    if req:
        return req
    for m in reversed(state.get("messages", [])):
        if isinstance(m, dict):
            kind = m.get("type", m.get("role", ""))
            if kind in ("human", "user"):
                return str(m.get("content", ""))
        elif getattr(m, "type", "") == "human":
            return str(getattr(m, "content", ""))
    return ""


def router(state: StockState) -> dict:
    """Satu pintu: request berisi >1 ticker/universe -> batch, ticker -> single,
    kosong total -> guide (tanpa panggil LLM).

    Request baru di thread yang sama me-reset progres (fresh run); pengulangan
    request yang sama melanjutkan state thread.
    """
    req = request_text(state)
    if req:
        parsed = parse_batch_request(req)
        changed = req != (state.get("last_request") or "")
        if parsed["fallback"] and not parsed["universe"]:
            # Pesan tanpa ticker: niat analisa -> screening watchlist;
            # lanjutkan ticker thread bila ada; else guide (sapaan/obrolan).
            if has_analysis_intent(req):
                upd = {"mode": "batch", "request": req, "last_request": req,
                       "tickers": parsed["tickers"], "top_n": parsed["top_n"],
                       "fallback": True}
                if changed:
                    upd.update({**BATCH_FRESH, "history": []})
                return upd
            if state.get("ticker"):
                upd = {"mode": "single", "request": req,
                       "last_request": req, "ticker": state.get("ticker")}
                if changed:
                    upd.update({**SINGLE_FRESH, "history": []})
                return upd
            return {"mode": "guide", "request": req, "last_request": req}
        if len(parsed["tickers"]) <= 1 and not parsed["universe"]:
            t = parsed["tickers"][0] if parsed["tickers"] else DEFAULT_TICKER
            upd = {"mode": "single", "request": req, "last_request": req,
                   "ticker": normalize_ticker(t)}
            if changed:
                upd.update({**SINGLE_FRESH, "history": []})
            return upd
        upd = {"mode": "batch", "request": req, "last_request": req,
               "tickers": parsed["tickers"],
               "top_n": parsed["top_n"], "fallback": parsed["fallback"]}
        if changed:
            upd.update({**BATCH_FRESH, "history": []})
        return upd
    if state.get("ticker"):
        # Input lawas Studio/CLI: ticker langsung tanpa request (selalu fresh).
        return {"mode": "single", "ticker": normalize_ticker(state.get("ticker")),
                **SINGLE_FRESH, "history": []}
    return {"mode": "guide"}


def route_mode(state: StockState) -> str:
    mode = state.get("mode")
    if mode == "batch":
        return "scan"
    if mode == "guide":
        return "guide"
    return "supervisor"


def guide(state: StockState) -> dict:
    return {"messages": [AIMessage(content=GUIDE_TEXT)]}


def supervisor(state: StockState) -> str:
    """Aturan deterministik (fallback bila LLM router gagal/di-bypass)."""
    done = set(state.get("history", []))
    if "news_collector" not in done:
        return "news_collector"
    if "fundamental_analyst" not in done:
        return "fundamental_analyst"
    if "sentiment_analyst" not in done:
        return "sentiment_analyst"
    if "reporter" not in done:
        return "reporter"
    return END


def smart_supervisor(state: StockState) -> str:
    """Supervisor LLM: memutuskan langkah berikut dari state.

    Guard: maks MAX_STEPS langkah -> END. Gagal parse/error LLM ->
    fallback aturan deterministik. Satu-satunya keputusan dinamis di graph.
    """
    hist = state.get("history", [])
    if len(hist) >= MAX_STEPS:
        return END
    llm = get_llm(temperature=0)
    fund = state.get("fundamentals", {})
    prompt = (
        "Kamu router analis saham. Balas HANYA satu kata: news_collector, "
        "fundamental_analyst, sentiment_analyst, reporter, atau DONE.\n"
        f"Request: {state.get('request') or state.get('ticker', '')}\n"
        f"Selesai: {', '.join(hist) if hist else '(belum ada)'}\n"
        f"Data: berita={len(state.get('news', []))} item, "
        f"fundamental={'error' if fund.get('error') else ('ada' if fund else 'belum')}, "
        f"sentimen={'ada' if state.get('sentiment') else 'belum'}, "
        f"laporan={'ada' if state.get('report') else 'belum'}.\n"
        "Aturan: kumpulkan berita + fundamental + sentimen dulu (lewati yang "
        "error/bermasalah), lalu reporter tepat sekali, lalu DONE."
    )
    try:
        out = str(llm.invoke(prompt).content).strip().lower()
    except Exception:
        return supervisor(state)
    for cand in ("news_collector", "fundamental_analyst",
                 "sentiment_analyst", "reporter"):
        if cand in out:
            return cand
    if any(w in out for w in ("done", "selesai", "end", "finish")):
        return END
    return supervisor(state)


def build_graph(checkpointer=None, interrupt_before=()):
    g = StateGraph(StockState)
    g.add_node("router", router)
    g.add_node("guide", guide)
    g.add_node("supervisor", lambda s: {})
    g.add_node("news_collector", news_collector)
    g.add_node("fundamental_analyst", fundamental_analyst)
    g.add_node("sentiment_analyst", sentiment_analyst)
    g.add_node("reporter", reporter)
    g.add_node("scan", scan_node)
    g.add_node("rank", rank_node)
    g.add_node("deepdive", deepdive_node)
    g.add_node("summarize", summarize_node)
    g.set_entry_point("router")
    g.add_conditional_edges(
        "router", route_mode,
        {"supervisor": "supervisor", "scan": "scan", "guide": "guide"},
    )
    g.add_edge("guide", END)
    g.add_conditional_edges(
        "supervisor",
        smart_supervisor,
        {
            "news_collector": "news_collector",
            "fundamental_analyst": "fundamental_analyst",
            "sentiment_analyst": "sentiment_analyst",
            "reporter": "reporter",
            END: END,
        },
    )
    for n in ["news_collector", "fundamental_analyst", "sentiment_analyst", "reporter"]:
        g.add_edge(n, "supervisor")
    g.add_edge("scan", "rank")
    g.add_edge("rank", "deepdive")
    g.add_edge("deepdive", "summarize")
    g.add_edge("summarize", END)
    return g.compile(checkpointer=checkpointer, interrupt_before=interrupt_before)


def build_hitl_graph(db_path="checkpoints.sqlite"):
    import sqlite3

    from langgraph.checkpoint.sqlite import SqliteSaver

    conn = sqlite3.connect(db_path, check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    checkpointer.setup()
    return build_graph(checkpointer=checkpointer, interrupt_before=["reporter"])


graph = build_graph()
