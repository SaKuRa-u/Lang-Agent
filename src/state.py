from typing import Annotated, TypedDict
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    ticker: str
    news: list[dict]
    fundamentals: dict
    flags: list[str]
    sentiment: str
    report: str
    recommendation: str
    critique: str
    history: list[str]
    messages: Annotated[list[AnyMessage], add_messages]


def normalize_ticker(ticker: str) -> str:
    t = ticker.strip().upper()
    return t if t.endswith(".JK") else f"{t}.JK"


class StockState(TypedDict, total=False):
    """State gabungan: satu pintu untuk mode single dan batch."""

    request: str
    last_request: str
    mode: str  # "single" | "batch"
    ticker: str
    tickers: list[str]
    top_n: int
    fallback: bool
    news: list[dict]
    fundamentals: dict
    flags: list[str]
    regime: dict
    sentiment: str
    report: str
    recommendation: str
    critique: str
    scanned: list[dict]
    ranked: list[str]
    picks: list[dict]
    summary: str
    history: list[str]
    messages: Annotated[list[AnyMessage], add_messages]
