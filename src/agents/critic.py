from langchain_core.messages import AIMessage

from src.state import AgentState
from src.llm import get_llm

DISCLAIMER = "Bukan nasihat finansial. Lakukan riset mandiri."


def critic(state: AgentState) -> dict:
    """Red-team rekomendasi reporter: cari lubang, kalibrasi keyakinan."""
    llm = get_llm()
    prompt = (
        "Kamu pengkritik independen analis saham IDX. Tugas: cari lubang dalam "
        "analisa berikut, JANGAN mengulang pujian reporter.\n"
        f"Ticker: {state.get('ticker')}\n"
        f"Fundamental: {state.get('fundamentals', {})}\n"
        f"Sentimen: {state.get('sentiment', '')}\n"
        f"Rekomendasi reporter: {state.get('recommendation')} — {state.get('report', '')[:1500]}\n"
        "Format jawaban (Bahasa Indonesia):\n"
        "1) KELEMAHAN: 2-3 lubang terkuat (data vs klaim, risiko terlewat).\n"
        "2) KEYAKINAN: angka 0-100 terhadap rekomendasi reporter.\n"
        "3) VERDIK: tulis persis 'SETUJU' atau 'TIDAK SETUJU' + 1 kalimat.\n"
        f"Akhiri dengan: {DISCLAIMER}"
    )
    res = llm.invoke(prompt)
    text = str(res.content)
    return {"critique": text,
            "history": [*state.get("history", []), "critic"],
            "messages": [AIMessage(content=text)]}
