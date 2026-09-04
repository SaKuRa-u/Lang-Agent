from src.state import AgentState
from src.tools.market import get_fundamentals
from src.validate import validate_row


def fundamental_analyst(state: AgentState) -> dict:
    hist = [*state.get("history", []), "fundamental_analyst"]
    old = state.get("fundamentals") or {}
    if old and not old.get("error"):
        # Data sudah ada (mis. dipakai ulang dari hasil scan) -> hemat fetch.
        return {"history": hist}
    data = get_fundamentals(state["ticker"])
    flags = validate_row(state["ticker"], data, len(state.get("news", [])))
    data["_flags"] = flags
    return {"fundamentals": data, "flags": flags, "history": hist}
