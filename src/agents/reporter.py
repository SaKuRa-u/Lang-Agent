from langchain_core.messages import AIMessage

from src.state import AgentState
from src.llm import get_llm

DISCLAIMER = "Bukan nasihat finansial. Lakukan riset mandiri."


def reporter(state: AgentState) -> dict:
    llm = get_llm()
    prompt = (
        "Buat laporan saham IDX dalam Bahasa Indonesia.\n"
        f"Ticker: {state['ticker']}\n"
        f"Fundamental: {state.get('fundamentals', {})}\n"
        f"Sentimen: {state.get('sentiment', '')}\n"
        "Format: Ringkasan, Data Fundamental, Sentimen Berita, Risiko, "
        "Rekomendasi (BELI/TUNGGU/JANGAN) + confidence.\n"
        f"Akhiri dengan: {DISCLAIMER}"
    )
    res = llm.invoke(prompt)
    text = str(res.content)
    rec = "TUNGGU"
    upper = text.upper()
    if "BELI" in upper and "JANGAN BELI" not in upper:
        rec = "BELI"
    elif "JANGAN" in upper:
        rec = "JANGAN"
    return {"report": text, "recommendation": rec,
            "history": [*state.get("history", []), "reporter"],
            "messages": [AIMessage(content=text)]}
