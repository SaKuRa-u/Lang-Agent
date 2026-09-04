# TROUBLESHOOTING — Lang-Agent

Setiap entri: gejala → akar (terbukti) → obat. Yang belum terbukti
ditandai HIPOTESIS.

## Studio: `404 assistant ... not found`

- **Akar:** browser memegang UUID asisten/thread dari sesi server lama;
  dev-server in-memory menghapus semuanya tiap restart.
- **Obat:** URL bersih (hanya `?baseUrl=...`), pilih ulang graph,
  **+ New Thread**. Jangan pakai URL/bookmark thread lama lintas restart.

## Thread lama tak bisa dibuka

- **Akar:** expected behavior — thread dev-server fana.
- **Obat:** jangan restart selama sesi eksplorasi. Butuh persisten →
  deployment LangSmith / checkpointer file (belum diimplementasikan).

## `Errno 10048` port sudah dipakai / PID hantu

- **Akar:** dua instance server (atau yatim dari proses yang dibunuh)
  berebut satu port; PID bisa terlihat di `netstat` tapi tak terlihat
  di `Get-Process` (sesi/admin berbeda).
- **Obat:** matikan semua instance (`Stop-Process`), hapus `.langgraph_api/`,
  nyalakan SATU instance. Jalan pintas: pindah port (`--port 8001`) dan
  pastikan `baseUrl` di URL Studio cocok.

## Traceback saat shutdown (pickle `.tmp` + blockbuster)

- **Akar:** noise shutdown Windows (tabrakan file `.tmp` basi + proteksi
  blocking-call). Terjadi saat exit, bukan saat run.
- **Obat:** abaikan bila pemakaian normal sehat. Hapus `.langgraph_api/`
  bila berulang.

## Log `changes detected` tiap ~10 detik saat idle

- **Akar:** sesuatu menulis di folder proyek → auto-reload → ID asisten
  berganti-ganti → 404 misterius.
- **Obat:** jalankan dengan `--no-reload`.

## Tab Chat disabled ("Create a graph with a messages key")

- **Akar:** channel `messages` bertipe `list` polos; Studio butuh tipe message.
- **Obat (sudah di kode):** `Annotated[list[AnyMessage], add_messages]`.

## Isi JSON membingungkan / pesan ke-2 diabaikan (historis)

- **Akar:** `request_text` membaca field `request` (pesan pertama) sebelum
  pesan terbaru → request lama terulang.
- **Obat (sudah di kode):** pesan human terakhir menang; field cadangan.

## `1 Lot: n/a` di tabel

- **Akar:** baris terakhir histori `yfinance` NaN (umum di ticker IDX);
  harga mentah lolos.
- **Obat (sudah di kode):** pakai close non-NaN terakhir + fallback
  `currentPrice`; validator menandai bila tetap hilang.

## Dividen 800%+

- **Akar:** `dividendYield` yfinance tak konsisten satuan (fraksi vs persen).
- **Obat (sudah di kode):** normalisasi `>1 → /100` di sumber + pengaman
  di skoring.

## Verdict flip-flop (BELI lalu TUNGGU, data sama)

- **Akar:** verdict diputuskan bebas oleh LLM (temperature > 0, tanpa rubrik).
- **Obat (sudah di kode):** guardrail `rule_verdict` deterministik;
  writer temperature 0; tanggal data `as_of` dicantumkan agar run bisa
  dibandingkan.

## Test lambat (>60 dtk) padahal mock

- **Akar:** SELALU kebocoran mock (node baru tanpa patch), bukan network lemot.
  Cari via `pytest --durations`.
- **Obat:** mock `get_llm` di namespace pemanggil (`src.graph`,
  `src.agents.*`, `src.batch_graph`); ingat jebakan `from`-import
  (patch di modul KONSUMEN, bukan sumber). Suite penuh wajib <15 dtk.

## Crash CLI di Windows / karakter aneh

- **Obat:** `$env:PYTHONUTF8="1"` sebelum perintah `langgraph`.

## Ticker tanpa `.JK` crash yfinance

- **Obat (sudah di kode):** `normalize_ticker` otomatis + entri dilewati
  dengan catatan bila data tetap tak tersedia.
