# IDX Stock Multi-Agent — Design Spec

Tanggal: 2026-09-03. Pendekatan: A Supervisor. Status: approved.

## 1. Tujuan

Multi-agent LangGraph + Studio untuk: tarik berita saham IDX (gratis), analisa fundamental + sentimen, reporting Bahasa Indonesia, rekomendasi BELI/TUNGGU/JANGAN. Engine 9Router lokal OpenAI-compatible.

## 2. Arsitektur

`supervisor` (LLM Fer) me-route ke:

```
user ticker -> supervisor -> news_collector -> supervisor ->
fundamental_analyst -> supervisor -> sentiment_analyst ->
supervisor -> reporter -> END
```

- `src/graph.py:graph` = `StateGraph(AgentState)` dikompilasi, diekspos ke Studio via `langgraph.json`.
- Tanpa checkpointer di v1 (upgrade ke SqliteSaver + HITL di fase C).

## 3. State

```python
class AgentState(TypedDict):
    ticker: str
    news: list[dict]
    fundamentals: dict
    sentiment: str
    report: str
    recommendation: str
    messages: Annotated[list, add_messages]
```

Ticker dinormalisasi ke `.JK` (contoh `BBCA` -> `BBCA.JK`).

## 4. Agen & Tools (gratis saja)

- `news_collector` (`src/tools/news.py:fetch_stock_news`): `feedparser` ke RSS Yahoo Finance `https://finance.yahoo.com/rss/headline?s=TICKER` + Google News RSS `https://news.google.com/rss/search?q=TICKER+saham`. Tanpa API key. Retry 2x, timeout 15s, return max 8 item {title, link, published, summary}.
- `fundamental_analyst` (`src/tools/market.py:get_fundamentals`): `yfinance.Ticker(ticker).info` + `history(period="6mo")` -> price, PE, PBV, marketCap, dividendYield, 52w high/low, ma50/ma200 sederhana. Cache in-memory 10 mnt.
- `sentiment_analyst`: LLM Fer meringkas sentimen news[] -> positif/netral/negatif + 3 bullet alasan, Bahasa Indonesia.
- `reporter`: LLM Fer menyusun laporan ID: ringkasan, data fundamental, sentimen, risiko, rekomendasi BELI/TUNGGU/JANGAN + confidence. Wajib footer: "Bukan nasihat finansial. Lakukan riset mandiri."

## 5. 9Router / LLM

- `src/llm.py:get_llm()`: `ChatOpenAI(base_url=os.getenv("OPENAI_BASE_URL"), api_key=os.getenv("OPENAI_API_KEY"), model=os.getenv("MODEL_NAME", "Fer"), temperature=0.2)`.
- `.env`: `OPENAI_BASE_URL=http://localhost:20128/v1`, `OPENAI_API_KEY=...`, `MODEL_NAME=Fer`. Jangan commit `.env`.

## 6. LangGraph Studio

- `langgraph.json`: `{"dependencies": ["."], "graphs": {"agent": "./src/graph.py:graph"}, "env": ".env"}`.
- Jalankan: `langgraph dev` lalu buka Studio, pilih graph `agent`, input `{"ticker": "BBCA.JK"}`.

## 7. Error handling

- yfinance kosong -> fundamentals={} + pesan "data tidak tersedia".
- RSS gagal semua -> news=[] + sentimen "netral (data terbatas)".
- 9Router down -> raise jelas "9Router tidak reachable di ...", jangan retry LLM >1x.
- Selalu tambah disclaimer finansial.

## 8. Testing

- `pytest tests/test_tools.py` dengan mock `yfinance` + `feedparser`.
- `pytest tests/test_graph.py -k live` opsional live BBCA.JK (butuh 9Router nyala + internet).
- Struktur: `src/graph.py`, `src/state.py`, `src/llm.py`, `src/agents/`, `src/tools/`, `tests/`.

## 9. Self-review

- Placeholder scan: tidak ada TBD/TODO.
- Konsistensi: state field dipakai semua agen; ticker `.JK` konsisten; env names konsisten dengan `.env.example` + `llm.py`.
- Scope: v1 tanpa HITL/memory, sesuai keputusan A. Upgrade C terpisah.
- Ambiguitas: sumber "gratis saja" di-lock ke yfinance+RSS, bukan Tavily/NewsAPI.
