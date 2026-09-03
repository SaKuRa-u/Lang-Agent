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

- `langgraph.json`: `{"dependencies": ["."], "graphs": {"agent": "./src/graph.py:graph"}, "env": ".env"}` — SATU graph saja.
- Jalankan: `langgraph dev` lalu buka Studio, pilih graph `agent`.
  Cara chat (disarankan): ketik pesan biasa di panel chat Studio
  (cth `"analisa BBCA"`, `"analisa BBCA, BBRI top 3"`); router membaca pesan
  human terakhir bila field `request` kosong. Hasil akhir dibalas sebagai
  pesan AI (`reporter`/`summarize` append `AIMessage`).
  Input JSON lawas `{"ticker": "BBCA.JK"}` tetap jalan; input kosong total
  dibalas panduan (mode `guide`, tanpa panggil LLM).

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

## 10. Fase C — HITL + Memory

- Checkpointer: `src/graph.py:build_hitl_graph(db_path="checkpoints.sqlite")` memakai `SqliteSaver` (sqlite); `graph = build_graph()` tanpa checkpointer agar Studio aman.
- Interrupt: `build_graph(checkpointer, interrupt_before=["reporter"])` pause sebelum node `reporter`; resume via `g.invoke(None, config=cfg)`.
- `thread_id` = ticker ternormalisasi `.JK` (cth `BBCA.JK`); memory/history terisolasi per ticker.
- CLI: `python main.py BBCA.JK --hitl` tampilkan sentimen + fundamental, prompt `lanjut ke rekomendasi? [y/n]`; `y` resume dengan `thread_id` sama, `n` batal.
- Studio: graph `agent` (`./src/graph.py:graph`, `langgraph.json` tidak berubah) jalan tanpa interrupt/checkpointer — eksplorasi tanpa pause.
- Artefak `*.sqlite*` ter-gitignore; jangan commit `.env`, checkpoints, atau `.superpowers/`.
## 11. Fase D — Batch mode (multi-ticker, SATU graph)

- Satu pintu via `request`/messages + node `router` di `src/graph.py` (bukan graph terpisah):
  request 0-1 ticker (atau input lawas `ticker` langsung) -> jalur single (supervisor);
  request >1 ticker / universe LQ45 -> jalur batch (scan -> rank -> deepdive -> summarize).

- Input bebas via messages: `python main.py --batch "analisa BBCA, BBRI, TLKM top 5"`.
- Parser tanpa LLM (`src/universe.py:parse_batch_request`): token `.JK` selalu diterima; kode 4 huruf diterima bila ada di KNOWN (WATCHLIST + LQ45) agar kata umum tak jadi ticker; "LQ45" -> universe 45 emiten; "TOP N" -> top_n (default 5); kosong -> fallback WATCHLIST.
- Two-stage hemat LLM: tahap 1 scan fundamental paralel (~2 dtk/ticker) + skor deterministik (`src/scoring.py:score_fundamentals`: PER, PBV, dividen, MA50, posisi 52w) -> ranking + tabel; tahap 2 deep-dive (berita + sentimen + reporter existing) hanya top-N; tahap 3 `summarize` susun leaderboard + bedah picks + rekomendasi.
- Graph `src/batch_graph.py:batch_graph` tetap ada untuk reuse node + CLI `--batch`, tapi TIDAK didaftarkan di `langgraph.json` (Studio hanya tampilkan satu graph `agent`).
- Bahasa Indonesia + footer "Bukan nasihat finansial. Lakukan riset mandiri."
