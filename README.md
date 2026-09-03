# Lang-Agent — Analis Saham IDX Multi-Agent

Chat Bahasa Indonesia untuk analisa saham IDX: satu pesan, dapat leaderboard,
deep-dive top picks, rencana budget, dan proyeksi berjangkar data historis.
Berjalan di [LangGraph](https://github.com/langchain-ai/langgraph) +
[LangGraph Studio](https://github.com/langchain-ai/langgraph), engine LLM
OpenAI-compatible lokal ([9Router](https://9router.example) / Ollama / LM Studio),
data gratis via `yfinance` + RSS. **Bukan nasihat finansial.**

## Fitur

- **Chat satu pintu (Studio)** — ketik biasa: `"analisa BBCA"`,
  `"analisa BBCA, BBRI, TLKM top 3"`, `"top 5 LQ45"`, atau pertanyaan bebas
  (`"carikan yang dividennya bagus"` → screening watchlist otomatis).
- **Supervisor LLM + fallback deterministik** — routing dinamis tiap putaran
  (batas 12 langkah); output ngawur / LLM down → aturan history mengambil alih.
- **Batch two-stage hemat LLM** — scan fundamental paralel + skor deterministik
  → deep-dive hanya top-N.
- **Verdict deterministik** — BELI/TUNGGU/JANGAN dari guardrail aturan
  (stabil antar run untuk data sama); LLM hanya narasi, dissent via critic.
- **Critic red-team** — tiap rekomendasi dinilai independen
  (kelemahan + keyakinan 0-100 + SETUJU/TIDAK SETUJU), termasuk per pick batch.
- **Validator data** — flag harga hilang, PER ganjil, dividen ekstrem,
  0 berita, volatilitas >60%.
- **Konteks pasar** — tren IHSG (`^JKSE`) + Rupiah (cache 1 jam).
- **Perencana budget ala-Bibit** — profil risiko, dana minimal = 1 lot,
  alokasi lot/bulan + sisa, saran nabung N bulan, warning horizon <12 bulan.
- **Proyeksi berjangkar historis** — return 1 thn, CAGR, volatilitas,
  max drawdown → 3 skenario (pesimis/basis/optimis), label ekstrapolasi.
- **Backtest walk-forward** — keputusan hanya dari data ≤ T vs buy-hold IHSG.
- **HITL (CLI)** — approve sebelum rekomendasi final + memori per ticker.

## Mulai cepat

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
copy .env.example .env   # lalu isi OPENAI_BASE_URL / OPENAI_API_KEY / MODEL_NAME
```

Jalankan CLI:

```powershell
.\.venv\Scripts\python main.py BBCA.JK
.\.venv\Scripts\python main.py --batch "analisa BBCA, BBRI, TLKM top 3"
.\.venv\Scripts\python main.py --backtest BBCA.JK BBRI.JK TLKM.JK years=3
```

Jalankan Studio (UI web untuk chat + visualisasi graph):

```powershell
$env:PYTHONUTF8="1"
.\.venv\Scripts\langgraph dev --port 8001 --no-browser --no-reload
```

Buka `https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:8001`,
pilih graph **agent** → tab **Chat** → **+ New Thread** → ketik pesan biasa.

> `.env` berisi kredensial dan **tidak pernah di-commit** (lihat `.gitignore`).
> Contoh nilai ada di `.env.example` — model apa pun yang OpenAI-compatible.

## Arsitektur

Satu graph `agent` (`src/graph.py:graph`): `router` → mode `single`
(`supervisor` LLM → news / fundamental / sentimen → `reporter` → `critic`)
atau mode `batch` (`scan` → `rank` → `deepdive` → `summarize`), plus mode
`guide`. Detail desain: `docs/superpowers/specs/2026-09-03-stock-multiagent-design.md`.

## Test

```powershell
.\.venv\Scripts\python -m pytest -q   # 59 test, semua mock (tanpa network/LLM)
```

## Disclaimer

Bukan nasihat finansial. Lakukan riset mandiri dan konsultasikan dengan
penasihat keuangan berlisensi. Investasi saham berisiko kehilangan modal.
