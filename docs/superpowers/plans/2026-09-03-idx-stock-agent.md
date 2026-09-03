# IDX Stock Multi-Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Verifikasi E2E multi-agent IDX (BBCA.JK) via 9Router Fer + Studio, lalu commit.

**Architecture:** Supervisor StateGraph di `src/graph.py:graph` dengan 4 node spesialis, LLM via `src/llm.py:get_llm()`.

**Tech Stack:** Python 3.11+, langgraph>=0.2, langchain-openai, yfinance, feedparser, langgraph-cli (Studio), pytest.

**Spec:** `docs/superpowers/specs/2026-09-03-stock-multiagent-design.md`

## Global Constraints

- Engine hanya 9Router lokal `http://localhost:20128/v1`, model `Fer`, kredensial via `.env` (jangan commit `.env`).
- Sumber data gratis saja: yfinance + RSS feedparser, tanpa Tavily/NewsAPI.
- Ticker IDX wajib suffix `.JK`.
- Bahasa output Indonesia + footer "Bukan nasihat finansial. Lakukan riset mandiri."
- Windows: jalankan Studio CLI dengan `$env:PYTHONUTF8="1"`.
- Graph entry `src/graph.py:graph`, Studio config `langgraph.json`.

---

### Task 1: Live E2E BBCA.JK

**Files:**
- Run: `main.py`
- Uses: `src/graph.py:graph`, `src/llm.py:get_llm()`, `src/tools/market.py:get_fundamentals`, `src/tools/news.py:fetch_stock_news`

**Interfaces:**
- Consumes: `.env` (`OPENAI_BASE_URL`, `OPENAI_API_KEY`, `MODEL_NAME=Fer`), internet + 9Router nyala.
- Produces: stdout `=== BBCA.JK -> BELI/TUNGGU/JANGAN ===` + laporan ID.

- [ ] **Step 1: Pastikan 9Router nyala**

Run: `.\.venv\Scripts\python.exe -c "import os,httpx; from dotenv import load_dotenv; load_dotenv(); print(httpx.get(os.getenv('OPENAI_BASE_URL')+'/models', headers={'Authorization':'Bearer '+os.getenv('OPENAI_API_KEY')}, timeout=15).status_code)"`
Expected: `200`

- [ ] **Step 2: Jalankan E2E**

Run: `.\.venv\Scripts\python.exe main.py BBCA.JK`
Expected: exit 0, output berisi rekomendasi + disclaimer "Bukan nasihat finansial".

- [ ] **Step 3: Jika yfinance/RSS kosong, cek fallback**

Run: `.\.venv\Scripts\python.exe -c "from src.tools.market import get_fundamentals; print(get_fundamentals('BBCA.JK'))"`
Expected: dict berisi `price` atau `error` yang jelas, tidak traceback.

### Task 2: Studio launch

**Files:**
- Config: `langgraph.json`
- Graph: `src/graph.py:graph`

**Interfaces:**
- Consumes: Task 1 lolos.
- Produces: Studio URL dengan graph `agent` bisa diinvoke.

- [ ] **Step 1: Start dev server (tanpa browser)**

Run: `$env:PYTHONUTF8="1"; .\.venv\Scripts\langgraph dev --no-browser --port 8000`
Expected: log "Ready" tanpa ModuleNotFoundError.

- [ ] **Step 2: Invoke via Studio UI**

Input di Studio: `{"ticker": "BBCA.JK", "news": [], "fundamentals": {}, "sentiment": "", "report": "", "recommendation": "", "messages": []}`
Expected: run selesai, node `reporter` mengisi `report` + `recommendation`.

### Task 3: Commit final

**Files:**
- Add: semua file kecuali `.env`, `.venv/`, `__pycache__/`

- [ ] **Step 1: Review diff**

Run: `git status --short; git diff --stat`
Expected: `.env` tidak muncul (gitignored).

- [ ] **Step 2: Commit**

```bash
git add AGENTS.md docs/ pyproject.toml langgraph.json .env.example .gitignore main.py src/ tests/
git commit -m "feat: IDX stock multi-agent supervisor + Studio + 9Router Fer"
```
