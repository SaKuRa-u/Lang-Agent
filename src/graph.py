from src.state import StockState, normalize_ticker
from src.tools.market import get_market_regime
from src.universe import parse_batch_request, has_analysis_intent
from src.single_flow import (
    MAX_STEPS,
    supervisor,
    smart_supervisor,
    wire_single_flow,
)
from src.batch_graph import (
    scan_node,
    rank_node,
    deepdive_node,
    summarize_node,
    review_batch_node,
    scan_has_data,
    batch_abort_node,
)
from langgraph.graph import StateGraph, END
from langchain_core.messages import AIMessage

DEFAULT_TICKER = "BBCA.JK"
SINGLE_FRESH = {"news": [], "fundamentals": {}, "flags": [], "sentiment": "",
                "report": "", "recommendation": "", "critique": ""}
BATCH_FRESH = {"scanned": [], "ranked": [], "picks": [], "summary": ""}
GUIDE_TEXT = (
    "Halo! Saya analis saham IDX. Cukup tulis pesan biasa, contoh:\n"
    '- "analisa BBCA" (single)\n'
    '- "analisa BBCA, BBRI, TLKM top 3" (batch)\n'
    '- "top 5 LQ45"\n'
    "Hasil dalam Bahasa Indonesia + bukan nasihat finansial."
)


def request_text(state: StockState) -> str:
    """Ambil request TERBARU: pesan human terakhir dulu, lalu field `request`.

    Alasan: dalam 1 thread Studio pesan ke-2 dst masuk sebagai message baru
    TANPA menimpa field `request` (field tetap berisi pesan pertama). Membaca
    field dulu berarti pesan baru diabaikan -> perulangan request lama.
    """
    for m in reversed(state.get("messages", [])):
        if isinstance(m, dict):
            kind = m.get("type", m.get("role", ""))
            if kind in ("human", "user"):
                return str(m.get("content", ""))
        elif getattr(m, "type", "") == "human":
            return str(getattr(m, "content", ""))
    return (state.get("request") or "").strip()


def _with_regime(upd: dict) -> dict:
    """Regime pasar global (cache 1 jam) — sekali per run, bukan per node."""
    if upd.get("mode") != "guide":
        try:
            upd["regime"] = get_market_regime()
        except Exception:
            upd["regime"] = {}
    return upd


def _route(state: StockState) -> dict:
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
                       "fallback": True, "risk": parsed["risk"],
                       "horizon_months": parsed["horizon_months"],
                       "budget_monthly": parsed["budget_monthly"]}
                if changed:
                    upd.update({**BATCH_FRESH, "history": []})
                return upd
            if state.get("ticker"):
                upd = {"mode": "single", "request": req,
                       "last_request": req, "ticker": state.get("ticker"),
                       "risk": parsed["risk"],
                       "horizon_months": parsed["horizon_months"],
                       "budget_monthly": parsed["budget_monthly"]}
                if changed:
                    upd.update({**SINGLE_FRESH, "history": []})
                return upd
            return {"mode": "guide", "request": req, "last_request": req}
        if len(parsed["tickers"]) <= 1 and not parsed["universe"]:
            t = parsed["tickers"][0] if parsed["tickers"] else DEFAULT_TICKER
            upd = {"mode": "single", "request": req, "last_request": req,
                   "ticker": normalize_ticker(t), "risk": parsed["risk"],
                   "horizon_months": parsed["horizon_months"],
                   "budget_monthly": parsed["budget_monthly"]}
            if changed:
                upd.update({**SINGLE_FRESH, "history": []})
            return upd
        upd = {"mode": "batch", "request": req, "last_request": req,
               "tickers": parsed["tickers"],
               "top_n": parsed["top_n"], "fallback": parsed["fallback"],
               "risk": parsed["risk"], "horizon_months": parsed["horizon_months"],
               "budget_monthly": parsed["budget_monthly"]}
        if changed:
            upd.update({**BATCH_FRESH, "history": []})
        return upd
    if state.get("ticker"):
        # Input lawas Studio/CLI: ticker langsung tanpa request (selalu fresh).
        return {"mode": "single", "ticker": normalize_ticker(state.get("ticker")),
                "risk": "moderat", "horizon_months": None, "budget_monthly": None,
                **SINGLE_FRESH, "history": []}
    return {"mode": "guide"}


def router(state: StockState) -> dict:
    """Entry graph: routing + regime pasar sekali per run."""
    return _with_regime(_route(state))


def route_mode(state: StockState) -> str:
    mode = state.get("mode")
    if mode == "batch":
        return "scan"
    if mode == "guide":
        return "guide"
    return "supervisor"


def guide(state: StockState) -> dict:
    return {"messages": [AIMessage(content=GUIDE_TEXT)]}


def build_graph(checkpointer=None, interrupt_before=()):
    g = StateGraph(StockState)
    g.add_node("router", router)
    g.add_node("guide", guide)
    wire_single_flow(g)
    g.add_node("scan", scan_node)
    g.add_node("rank", rank_node)
    g.add_node("deepdive", deepdive_node)
    g.add_node("summarize", summarize_node)
    g.add_node("review_batch", review_batch_node)
    g.add_node("batch_abort", batch_abort_node)
    g.set_entry_point("router")
    g.add_conditional_edges(
        "router", route_mode,
        {"supervisor": "supervisor", "scan": "scan", "guide": "guide"},
    )
    g.add_edge("guide", END)
    g.add_conditional_edges(
        "scan", scan_has_data,
        {True: "rank", False: "batch_abort"},
    )
    g.add_edge("batch_abort", END)
    g.add_edge("rank", "deepdive")
    g.add_edge("deepdive", "summarize")
    g.add_edge("summarize", "review_batch")
    g.add_edge("review_batch", END)
    return g.compile(checkpointer=checkpointer, interrupt_before=interrupt_before)


def build_hitl_graph(db_path="checkpoints.sqlite"):
    import sqlite3

    from langgraph.checkpoint.sqlite import SqliteSaver

    conn = sqlite3.connect(db_path, check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    checkpointer.setup()
    return build_graph(checkpointer=checkpointer, interrupt_before=["reporter"])


graph = build_graph()
