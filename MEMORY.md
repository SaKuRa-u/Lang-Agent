# MEMORY.md — Lang-Agent

Ingatan abadi proyek. Baca file ini dulu sebelum mengubah perilaku sistem.
Detail: `docs/DESIGN.md`. Masalah lampau: `docs/TROUBLESHOOTING.md`.

## Apa ini

Analis saham IDX berbahasa Indonesia: satu graph LangGraph (`agent`),
chat satu pintu (`request`/messages), engine LLM OpenAI-compatible lokal,
data gratis (`yfinance` + RSS). Bukan nasihat finansial.

## Invarian (jangan langgar)

1. **Verdict deterministik** — BELI/TUNGGU/JANGAN hanya dari
   `src/verdict.py:rule_verdict`. LLM (temperature 0) menulis narasi;
   dissent hanya via critic. Data sama → verdict sama.
2. **Bahasa Indonesia + footer disclaimer** di semua output user.
3. **Ticker `.JK`** untuk semua akses `yfinance` (normalisasi otomatis).
4. **Tanpa rahasia di repo** — kredensial hanya `.env` (gitignored).
   Contoh generik di `.env.example`. Jangan tulis ulang nama model
   spesifik di file ter-track.
5. **Tanpa lookahead** — keputusan/backtest hanya dari data ≤ T.
   Asumsi (fundamental konstan, regime netral) wajib dinyatakan di output.
6. **Proyeksi = ilustrasi skenario**, bukan prediksi. Label wajib.
7. **Test offline-cepat** — 59 test, semua mock, <15 detik. Bocor ke
   network/LLM = bug test, bukan flakiness.

## Operasional (pelajaran mahal)

- Studio dev-server: **satu instance**, `--no-reload`, thread **fana**
  (restart = thread hilang). URL bersih + New Thread tiap sesi baru.
- Pesan terbaru menang: router membaca pesan human terakhir.
- 1 thread = 1 topik. Topik beda jauh → thread baru.
- Windows: `$env:PYTHONUTF8="1"` untuk CLI Studio.

## Batas yang diakui

- Snapshot fundamental historis tak tersedia gratis → backtest mengasumsikan
  PER/PBV/dividen konstan (dinyatakan terbuka).
- Reksadana/fraksional disebut edukatif saja (tanpa data live).
- Upgrade tercatat (belum diambil): Tavily/browser-live research,
  monitoring terjadwal, portfolio tracker, verdict audit log.
