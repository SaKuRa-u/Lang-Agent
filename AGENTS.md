# AGENTS.md — Lang-Agent (IDX Stock Multi-Agent)

Python 3.11+, LangGraph + LangGraph Studio, `langchain-openai`
(ChatOpenAI ke endpoint OpenAI-compatible lokal), `yfinance`, `feedparser`,
`python-dotenv`, `pytest`.

## Perintah

```powershell
.\.venv\Scripts\python -m pytest -q          # 59 test, semua mock (tanpa network/LLM)
.\.venv\Scripts\python main.py BBCA.JK
.\.venv\Scripts\python main.py --batch "analisa BBCA, BBRI top 3"
.\.venv\Scripts\python main.py --backtest BBCA.JK BBRI.JK years=3
$env:PYTHONUTF8="1"; .\.venv\Scripts\langgraph dev --port 8001 --no-browser --no-reload
```

## Konvensi

- Graph entry: `src/graph.py:graph` (satu graph `agent`). Studio config: `langgraph.json`.
- Kredensial hanya via `.env` (`OPENAI_BASE_URL`, `OPENAI_API_KEY`, `MODEL_NAME`) —
  jangan hardcode key/model, jangan commit `.env`. Contoh generik di `.env.example`.
- Ticker IDX wajib suffix `.JK` untuk `yfinance` (contoh `BBCA.JK`).
- Bahasa output: Indonesia + footer "Bukan nasihat finansial. Lakukan riset mandiri."
- Test tanpa network/LLM: mock `get_llm` di namespace pemanggil
  (`src.single_flow`, `src.agents.*`, `src.batch_graph`) dan tools di
  `src.tools.*` / `src.agents.*` (peringatan `from`-import).
- Verdict BELI/TUNGGU/JANGAN dari `src/verdict.py:rule_verdict` (deterministik);
  LLM hanya narasi. Desain: `docs/DESIGN.md`.
- Ingatan proyek: `MEMORY.md` (baca dulu). Masalah lampau: `docs/TROUBLESHOOTING.md`.
