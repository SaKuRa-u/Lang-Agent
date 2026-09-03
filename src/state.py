from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    ticker: str
    news: list[dict]
    fundamentals: dict
    sentiment: str
    report: str
    recommendation: str
    history: list[str]
    messages: Annotated[list, add_messages]


def normalize_ticker(ticker: str) -> str:
    t = ticker.strip().upper()
    return t if t.endswith(".JK") else f"{t}.JK"


class StockState(TypedDict, total=False):
    """State gabungan: satu pintu untuk mode single dan batch."""

    request: str
    mode: str  # "single" | "batch"
    ticker: str
    tickers: list[str]
    top_n: int
    fallback: bool
    news: list[dict]
    fundamentals: dict
    sentiment: str
    report: str
    recommendation: str
    scanned: list[dict]
    ranked: list[str]
    picks: list[dict]
    summary: str
    history: list[str]
    messages: Annotated[list, add_messages]
