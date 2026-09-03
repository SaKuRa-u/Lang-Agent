from src.state import AgentState
from src.llm import get_llm


def sentiment_analyst(state: AgentState) -> dict:
    titles = "\n".join(f"- {n.get('title', '')}" for n in state.get("news", [])[:8])
    hist = [*state.get("history", []), "sentiment_analyst"]
    if not titles.strip():
        return {"sentiment": "netral (data berita terbatas)", "history": hist}
    llm = get_llm()
    prompt = (
        "Analisa sentimen berita saham berikut dalam Bahasa Indonesia. "
        "Jawab: POSITIF/NEGATIF/NETRAL + 3 bullet alasan.\n\n" + titles
    )
    res = llm.invoke(prompt)
    return {"sentiment": str(res.content), "history": hist}
