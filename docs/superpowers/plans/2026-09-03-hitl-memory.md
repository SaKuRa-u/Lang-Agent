# Fase C: HITL + Memory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tambah persetujuan manusia sebelum rekomendasi final + memory per ticker via checkpointer.

**Architecture:** `src/graph.py:build_graph(checkpointer=None)` tetap dipakai Studio tanpa checkpointer; CLI (`main.py`) memakai `SqliteSaver` + `interrupt_before=["reporter"]` dengan `thread_id` per ticker.

**Tech Stack:** langgraph (sudah terinstal, termasuk `langgraph-checkpoint`), `langgraph-checkpoint-sqlite`, pytest, 9Router Fer.

**Spec:** `docs/superpowers/specs/2026-09-03-stock-multiagent-design.md` (bagian upgrade C)

## Global Constraints

- Engine hanya 9Router lokal `http://localhost:20128/v1`, model `Fer`, kredensial via `.env` (jangan commit `.env`).
- Ticker IDX wajib suffix `.JK` via `normalize_ticker`.
- Bahasa output Indonesia + footer "Bukan nasihat finansial. Lakukan riset mandiri."
- Graph entry tetap `src/graph.py:graph` agar `langgraph.json` Studio tidak rusak.
- Windows: `$env:PYTHONUTF8="1"` untuk CLI Studio.
- Test cepat: JANGAN panggil LLM/9Router di unit test — mock `src.llm.get_llm` dan tools.

---

### Task 1: Checkpointer + interrupt reporter

**Files:**
- Modify: `src/graph.py`
- Modify: `pyproject.toml` (tambah `langgraph-checkpoint-sqlite` bila belum ada)
- Test: `tests/test_hitl.py` (baru, mock LLM)

**Interfaces:**
- Consumes: `AgentState` + `history` yang sudah ada.
- Produces: `build_graph(checkpointer=None, interrupt_before=())`, `graph = build_graph()` tanpa checkpointer (Studio aman), helper `build_hitl_graph(db_path)` untuk CLI.

- [ ] **Step 1: Write the failing test**

```python
from unittest.mock import patch
from src.graph import build_hitl_graph

def test_hitl_graph_pauses_before_reporter():
    with patch("src.agents.sentiment.get_llm"), patch("src.agents.reporter.get_llm"):
        g = build_hitl_graph(":memory:")
        cfg = {"configurable": {"thread_id": "t1"}}
        out = g.invoke({"ticker": "BBCA.JK", "news": [{"title": "x"}], "fundamentals": {"price": 1}, "sentiment": "", "report": "", "recommendation": "", "history": ["news_collector", "fundamental_analyst"], "messages": []}, config=cfg)
    assert out.get("report", "") == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_hitl.py::test_hitl_graph_pauses_before_reporter -q`
Expected: FAIL with "build_hitl_graph not defined" (atau ImportError)

- [ ] **Step 3: Write minimal implementation**

```python
from langgraph.checkpoint.sqlite import SqliteSaver

def build_graph(checkpointer=None, interrupt_before=()):
    g = StateGraph(AgentState)
    # ... node & edge sama seperti sekarang ...
    return g.compile(checkpointer=checkpointer, interrupt_before=interrupt_before)

def build_hitl_graph(db_path="checkpoints.sqlite"):
    conn = __import__("sqlite3").connect(db_path, check_same_thread=False)
    return build_graph(checkpointer=SqliteSaver(conn), interrupt_before=["reporter"])

graph = build_graph()
```

Sesuaikan dengan kode aktual (jangan duplikat definisi node).

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_hitl.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/graph.py pyproject.toml tests/test_hitl.py
git commit -m "feat: hitl graph with sqlite checkpointer and reporter interrupt"
```

### Task 2: Alur approve/resume di CLI

**Files:**
- Modify: `main.py`
- Test: `tests/test_hitl.py` (tambah, mock LLM + tools, tanpa network)

**Interfaces:**
- Consumes: `build_hitl_graph` dari Task 1.
- Produces: `main.py BBCA.JK` pause sebelum reporter, tampilkan sentimen+fundamental, minta `lanjut? [y/n]`, `y` resume dengan `thread_id` sama, `n` batal.

- [ ] **Step 1: Write the failing test**

```python
from unittest.mock import patch, MagicMock
import main as cli

def test_cli_resume_keeps_thread_id(monkeypatch, tmp_path, capsys):
    db = str(tmp_path / "c.sqlite")
    with patch("src.tools.news.fetch_stock_news", return_value=[{"title": "x"}]), \
         patch("src.tools.market.get_fundamentals", return_value={"price": 1}), \
         patch("src.agents.sentiment.get_llm") as m1, \
         patch("src.agents.reporter.get_llm") as m2:
        m1.return_value.invoke.return_value = MagicMock(content="netral")
        m2.return_value.invoke.return_value = MagicMock(content="Laporan BELI. Bukan nasihat finansial.")
        monkeypatch.setattr("builtins.input", lambda _: "y")
        cli.run_hitl("BBCA.JK", db_path=db)
    assert "BELI" in capsys.readouterr().out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_hitl.py::test_cli_resume_keeps_thread_id -q`
Expected: FAIL with "run_hitl not defined"

- [ ] **Step 3: Write minimal implementation**

```python
def run_hitl(ticker, db_path="checkpoints.sqlite"):
    from src.graph import build_hitl_graph
    from src.state import normalize_ticker
    ticker = normalize_ticker(ticker)
    g = build_hitl_graph(db_path)
    cfg = {"configurable": {"thread_id": ticker}}
    init = {"ticker": ticker, "news": [], "fundamentals": {}, "sentiment": "", "report": "", "recommendation": "", "history": [], "messages": []}
    out = g.invoke(init, config=cfg)
    print(f"Sentimen: {out.get('sentiment')}\nFundamental: {out.get('fundamentals')}")
    if input("lanjut ke rekomendasi? [y/n]: ").lower() != "y":
        print("dibatalkan."); return
    out = g.invoke(None, config=cfg)
    print(f"\n=== {out['ticker']} -> {out.get('recommendation')} ===\n{out.get('report', '')}")
```

`main()` tetap E2E lama secara default; tambah flag `--hitl` untuk rute ini.

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_hitl.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add main.py tests/test_hitl.py
git commit -m "feat: hitl approve resume cli with thread per ticker"
```

### Task 3: Docs Studio + checkpoints gitignore

**Files:**
- Modify: `docs/superpowers/specs/2026-09-03-stock-multiagent-design.md` (tambah bagian Fase C)
- Modify: `.gitignore` (tambah `*.sqlite*`, `.superpowers/`)
- Modify: `langgraph.json` (tidak berubah — verifikasi saja)

**Interfaces:**
- Consumes: Task 1-2 selesai.
- Produces: docs menjelaskan `thread_id` = ticker, Studio tanpa interrupt, CLI `--hitl` dengan interrupt.

- [ ] **Step 1: Update `.gitignore`**

Run: cek `git status --short` setelah run CLI — `*.sqlite` tidak boleh muncul.

- [ ] **Step 2: Tulis bagian Fase C di spec (max 30 baris)**

Isi: checkpointer sqlite, interrupt_before reporter, thread_id=ticker, Studio vs CLI.

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/specs/2026-09-03-stock-multiagent-design.md .gitignore
git commit -m "docs: fase C hitl memory usage and studio notes"
```
