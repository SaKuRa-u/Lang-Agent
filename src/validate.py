"""Validasi data deterministik: tandai anomali sebelum laporan dibuat."""


def validate_row(ticker: str, fundamentals: dict, news_count=None) -> list[str]:
    """Return daftar flag string (kosong bila bersih)."""
    flags: list[str] = []
    f = fundamentals or {}
    if f.get("error"):
        return [f"data gagal diambil ({f.get('error')})"]
    if not isinstance(f.get("price"), (int, float)):
        flags.append("harga tidak tersedia — angka valuasi mungkin basi")
    pe = f.get("per")
    if isinstance(pe, (int, float)) and (pe <= 0 or pe > 50):
        flags.append(f"PER tidak wajar ({pe:.1f}x) — abaikan skor valuasi")
    dy = f.get("dividendYield") or 0
    if isinstance(dy, (int, float)) and dy > 0.20:
        flags.append(f"dividen {dy:.1%} ekstrem — verifikasi manual sebelum dipakai")
    if news_count is not None and news_count == 0:
        flags.append("0 berita ditemukan — sentimen netral karena data minim")
    vol = f.get("volatility")
    if isinstance(vol, (int, float)) and vol > 0.60:
        flags.append(f"volatilitas sangat tinggi ({vol:.0%}) — ukuran posisi kecil")
    return flags
