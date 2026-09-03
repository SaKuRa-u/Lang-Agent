from src.state import AgentState
from src.tools.news import fetch_stock_news


def news_collector(state: AgentState) -> dict:
    news = fetch_stock_news(state["ticker"])
    return {"news": news, "history": [*state.get("history", []), "news_collector"]}
