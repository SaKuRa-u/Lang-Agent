from src.state import AgentState, normalize_ticker
from src.llm import get_llm
from src.agents.news_collector import news_collector
from src.agents.fundamental import fundamental_analyst
from src.agents.sentiment import sentiment_analyst
from src.agents.reporter import reporter
from langgraph.graph import StateGraph, END

DONE = {"news": True, "fundamentals": True, "sentiment": True}


def supervisor(state: AgentState) -> str:
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


def build_graph():
    g = StateGraph(AgentState)
    g.add_node("supervisor", lambda s: {})
    g.add_node("news_collector", news_collector)
    g.add_node("fundamental_analyst", fundamental_analyst)
    g.add_node("sentiment_analyst", sentiment_analyst)
    g.add_node("reporter", reporter)
    g.set_entry_point("supervisor")
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
    return g.compile()


graph = build_graph()
