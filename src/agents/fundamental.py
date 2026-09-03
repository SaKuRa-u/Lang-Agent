from src.state import AgentState
from src.tools.market import get_fundamentals


def fundamental_analyst(state: AgentState) -> dict:
    return {"fundamentals": get_fundamentals(state["ticker"]), "history": [*state.get("history", []), "fundamental_analyst"]}
