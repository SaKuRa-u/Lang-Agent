"""Universe saham + parser request batch (tanpa LLM)."""

import re

# Watchlist default: emiten IDX likuid untuk fallback.
WATCHLIST = [
    "BBCA", "BBRI", "BMRI", "TLKM", "ASII", "GOTO",
    "UNTR", "INDF", "ICBP", "KLBF", "SMGR", "PTBA",
]

# LQ45 (per 2025 — update berkala bila IDX revisi konstituen).
LQ45 = [
    "ACES", "ADRO", "AKRA", "AMMN", "ANTM", "ARTO", "ASII", "BBCA",
    "BBNI", "BBRI", "BBTN", "BMRI", "BRIS", "BRPT", "BUKA", "CPIN",
    "CTRA", "EMTK", "ERAA", "EXCL", "GOTO", "ICBP", "INCO", "INDF",
    "INKP", "INTP", "ISAT", "ITMG", "JSMR", "KLBF", "MAPI", "MDKA",
    "MEDC", "PGAS", "PTBA", "SCMA", "SMGR", "SMRA", "TBIG", "TINS",
    "TKIM", "TLKM", "UNTR", "UNVR", "ADMR",
]

KNOWN = set(WATCHLIST) | set(LQ45)

# Kata penanda niat analisa (substring, case-insensitive via upper).
ANALYSIS_KEYWORDS = {
    "ANALISA", "ANALISIS", "CARI", "BANDING", "PROYEKSI", "DIVIDEN",
    "REKOMENDASI", "REKOMENDASIKAN", "SAHAM", "RINGKAS", "UNTUNG",
    "KEUNTUNGAN", "BAGUS", "TERBAIK", "PILIH", "SARAN", "INVESTASI",
    "STRATEGI", "BANDINGKAN", "SCREENING", "SCREENER",
}


def has_analysis_intent(text: str) -> bool:
    t = (text or "").upper()
    return any(kw in t for kw in ANALYSIS_KEYWORDS)


# Kata umum yang terlihat seperti ticker tapi bukan.
STOPWORDS = {
    "TOP", "DAN", "ATAU", "SAHAM", "ANALISA", "ANALISIS", "BANDING",
    "BANDINGKAN", "RINGKAS", "RINGKASAN", "BELI", "JUAL", "TAHAN",
    "TUNGGU", "JANGAN", "YANG", "DARI", "PLUS", "DENGAN", "BUAT",
    "MINTA", "TOLONG", "COBA", "LIHAT", "KASIH", "BERIKAN",
}


def normalize_code(code: str) -> str:
    c = code.strip().upper().removesuffix(".JK")
    return f"{c}.JK"


def parse_batch_request(text: str, default_top_n: int = 5) -> dict:
    """Ekstrak {tickers, top_n, universe} dari pesan bebas.

    - Token `.JK` eksplisit selalu diterima.
    - Kode 4 huruf diterima bila ada di KNOWN (anti false-positive kata umum).
    - "LQ45" -> universe LQ45; "TOP N" -> top_n.
    - Kosong -> fallback WATCHLIST + flag fallback=True.
    """
    t = (text or "").upper()
    m = re.search(r"TOP\s*(\d+)", t)
    top_n = int(m.group(1)) if m else default_top_n
    top_n = max(1, min(top_n, 45))

    tickers: list[str] = []
    for tok in re.findall(r"[A-Z]{4}\.JK", t):
        code = normalize_code(tok)
        if code not in tickers:
            tickers.append(code)
    for tok in re.findall(r"\b[A-Z]{4}\b", t):
        if tok in STOPWORDS or tok == "LQ45":
            continue
        if tok in KNOWN:
            code = normalize_code(tok)
            if code not in tickers:
                tickers.append(code)

    universe = None
    if not tickers and "LQ45" in t:
        universe = "LQ45"
        tickers = [normalize_code(c) for c in LQ45]

    fallback = False
    if not tickers:
        fallback = True
        tickers = [normalize_code(c) for c in WATCHLIST]

    return {"tickers": tickers, "top_n": top_n, "universe": universe, "fallback": fallback}
