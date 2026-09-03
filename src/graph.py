from src.state import StockState, normalize_ticker
from src.agents.news_collector import news_collector
from src.agents.fundamental import fundamental_analyst
from src.agents.sentiment import sentiment_analyst
from src.agents.reporter import reporter
from src.universe import parse_batch_request
from src.batch_graph import scan_node, rank_node, deepdive_node, summarize_node
from langgraph.graph import StateGraph, END

DEFAULT_TICKER = "BBCA.JK"


def router(state: StockState) -> dict:
    """Satu pintu: request berisi >1 ticker/universe -> batch, sisanya single."""
    req = (state.get("request") or "").strip()
    if req:
        parsed = parse_batch_request(req)
        if len(parsed["tickers"]) <= 1 and not parsed["universe"]:
            t = parsed["tickers"][0] if parsed["tickers"] else DEFAULT_TICKER
            return {"mode": "single", "ticker": normalize_ticker(t)}
        return {
            "mode": "batch",
            "tickers": parsed["tickers"],
            "top_n": parsed["top_n"],
            "fallback": parsed["fallback"],
        }
    # Input lawas Studio/CLI: ticker langsung tanpa request.
    return {"mode": "single", "ticker": normalize_ticker(state.get("ticker") or DEFAULT_TICKER)}


def route_mode(state: StockState) -> str:
    return "supervisor" if state.get("mode") == "single" else "scan"


def supervisor(state: StockState) -> str:
    """Router berbasis history agar tidak infinite-loop saat tools return kosong."""
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


def build_graph(checkpointer=None, interrupt_before=()):
    g = StateGraph(StockState)
    g.add_node("router", router)
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
        "router", route_mode, {"supervisor": "supervisor", "scan": "scan"}
    )
    g.add_conditional_edges(
        "supervisor",
        supervisor,
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
