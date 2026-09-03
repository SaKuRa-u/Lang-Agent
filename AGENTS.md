# AGENTS.md

## Agent skills

### Issue tracker

Local markdown under `.scratch/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Default 5 canonical labels. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context. See `docs/agents/domain.md`.

## Project: Lang-Agent (IDX Stock Multi-Agent)

- Stack: Python 3.11+, LangGraph + LangGraph Studio, `langchain-openai` (ChatOpenAI ke 9Router OpenAI-compatible), `yfinance`, `feedparser`, `python-dotenv`, `pytest`.
- Engine: 9Router lokal `http://localhost:20128/v1`, model combo `Fer`. Jangan hardcode API key — pakai `.env` (`OPENAI_BASE_URL`, `OPENAI_API_KEY`, `MODEL_NAME`).
- Graph entry: `src/graph.py:graph`. Studio config: `langgraph.json`.
- Bahasa output: Indonesia + disclaimer bukan nasihat finansial.
- Ticker IDX wajib suffix `.JK` untuk `yfinance` (contoh `BBCA.JK`).
