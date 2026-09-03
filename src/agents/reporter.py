from langchain_core.messages import AIMessage

from src.state import AgentState
from src.llm import get_llm
from src.verdict import rule_verdict

DISCLAIMER = "Bukan nasihat finansial. Lakukan riset mandiri."


def reporter(state: AgentState) -> dict:
    llm = get_llm(temperature=0)
    flags = state.get("flags") or state.get("fundamentals", {}).get("_flags") or []
    guard, guard_reasons = rule_verdict(
        state.get("fundamentals", {}), flags, state.get("regime"))
    prompt = (
        "Buat laporan saham IDX dalam Bahasa Indonesia.\n"
        f"Ticker: {state['ticker']}\n"
        f"Fundamental: {state.get('fundamentals', {})}\n"
        f"Sentimen: {state.get('sentiment', '')}\n"
        f"Konteks pasar (IHSG/Rupiah): {state.get('regime') or 'tidak tersedia'}\n"
        "Format: Ringkasan, Data Fundamental (cantumkan tanggal data as_of), "
        "Sentimen Berita, Risiko, Rekomendasi + confidence.\n"
        f"Keputusan guardrail (WAJIB sama persis, jangan diubah): {guard} "
        f"— {'; '.join(guard_reasons)}.\n"
        "Bila analisismu berbeda, tulis bagian OVERRIDE: 1 kalimat alasan "
        "(tetap cantumkan verdict guardrail sebagai keputusan resmi).\n"
        f"Temuan validasi data: {flags or 'bersih'} — sebutkan eksplisit bila tidak bersih.\n"
        "Bila diminta proyeksi: jangkar pada data historis di Fundamental "
        "(ret_1y, cagr_3y, volatility, max_drawdown) dengan 3 skenario "
        "(pesimis/basis/optimis) berlabel 'ekstrapolasi, bukan prediksi'.\n"
        f"Akhiri dengan: {DISCLAIMER}"
    )
    res = llm.invoke(prompt)
    text = str(res.content)
    # Verdict deterministik dari guardrail: stabil antar run untuk data sama.
    rec = guard
    return {"report": text, "recommendation": rec,
            "history": [*state.get("history", []), "reporter"],
            "messages": [AIMessage(content=text)]}
