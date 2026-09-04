"""Alur single-ticker: satu-satunya implementasi pipeline analis per saham.

Dipakai dua tempat (sumber tunggal, tanpa duplikasi):
- graph utama (jalur single, inline) — termasuk HITL.
- deepdive batch — sebagai subgraph yang di-invoke per finalis.

Otaknya satu: smart_supervisor (LLM + guard + fallback aturan).
"""

from langgraph.graph import StateGraph, END

from src.state import StockState
from src.llm import get_llm
from src.agents.news_collector import news_collector
from src.agents.fundamental import fundamental_analyst
from src.agents.sentiment import sentiment_analyst
from src.agents.reporter import reporter
from src.agents.critic import critic

MAX_STEPS = 12


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
    if "critic" not in done:
        return "critic"
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
        "error/bermasalah), lalu reporter tepat sekali, lalu DONE. "
        "(Node critic berjalan otomatis setelah reporter.)"
    )
    try:
        out = str(llm.invoke(prompt).content).strip().lower()
    except Exception:
        return supervisor(state)
    done = set(hist)
    for cand in ("news_collector", "fundamental_analyst",
                 "sentiment_analyst", "reporter"):
        if cand in out and cand not in done:
            return cand
    if any(w in out for w in ("done", "selesai", "end", "finish")):
        return END
    return supervisor(state)


def wire_single_flow(g: StateGraph) -> StateGraph:
    """Pasang node + edge pipeline single ke graph `g`. Dipakai graph utama
    dan subgraph deepdive — satu definisi topologi."""
    g.add_node("supervisor", lambda s: {})
    g.add_node("news_collector", news_collector)
    g.add_node("fundamental_analyst", fundamental_analyst)
    g.add_node("sentiment_analyst", sentiment_analyst)
    g.add_node("reporter", reporter)
    g.add_node("critic", critic)
    g.add_conditional_edges(
        "supervisor",
        smart_supervisor,
        {
            "news_collector": "news_collector",
            "fundamental_analyst": "fundamental_analyst",
            "sentiment_analyst": "sentiment_analyst",
            "reporter": "reporter",
            "critic": "critic",
            END: END,
        },
    )
    for n in ["news_collector", "fundamental_analyst", "sentiment_analyst"]:
        g.add_edge(n, "supervisor")
    g.add_edge("reporter", "critic")
    g.add_edge("critic", "supervisor")
    return g


def build_single_subgraph(checkpointer=None, interrupt_before=()):
    """Subgraph analis per saham untuk deepdive batch."""
    g = StateGraph(StockState)
    wire_single_flow(g)
    g.set_entry_point("supervisor")
    return g.compile(checkpointer=checkpointer, interrupt_before=interrupt_before)
