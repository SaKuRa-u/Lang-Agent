"""Alur single-ticker: rantai handoffs tetap (bukan supervisor LLM).

Keputusan sadar (lihat riset pola LangGraph): urutan analis selalu sama
(news -> fundamental -> sentimen -> reporter -> critic), jadi routing LLM
per langkah hanya membakar call tanpa nilai tambah. Dinamisme yang benar
ada di: router entry (pilih mode), guardrail verdict, critic, dan fallback
data di tiap node. Satu definisi dipakai graph utama + subgraph deepdive.
"""

from langgraph.graph import StateGraph, END

from src.state import StockState
from src.agents.news_collector import news_collector
from src.agents.fundamental import fundamental_analyst
from src.agents.sentiment import sentiment_analyst
from src.agents.reporter import reporter
from src.agents.critic import critic

HANDOFF_ORDER = [
    "news_collector",
    "fundamental_analyst",
    "sentiment_analyst",
    "reporter",
    "critic",
]


def wire_single_flow(g: StateGraph) -> StateGraph:
    """Pasang rantai handoffs pipeline single ke graph `g`."""
    g.add_node("news_collector", news_collector)
    g.add_node("fundamental_analyst", fundamental_analyst)
    g.add_node("sentiment_analyst", sentiment_analyst)
    g.add_node("reporter", reporter)
    g.add_node("critic", critic)
    prev = None
    for name in HANDOFF_ORDER:
        if prev is not None:
            g.add_edge(prev, name)
        prev = name
    g.add_edge("critic", END)
    return g


def build_single_subgraph(checkpointer=None, interrupt_before=()):
    """Subgraph analis per saham untuk deepdive batch."""
    g = StateGraph(StockState)
    wire_single_flow(g)
    g.set_entry_point("news_collector")
    return g.compile(checkpointer=checkpointer, interrupt_before=interrupt_before)
