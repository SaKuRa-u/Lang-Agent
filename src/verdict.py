"""Verdict deterministik: BELI/TUNGGU/JANGAN dari aturan, bukan tebakan LLM.

Tujuan: run berbeda dengan data sama -> verdict sama. LLM hanya menulis
narasi; bila tak setuju, salurannya via critic (dissent eksplisit).
"""

BEARISH_MODIFIER = "regime bearish (IHSG di bawah MA50)"


def rule_verdict(fundamentals: dict, flags=None, regime=None,
                 score=None) -> tuple[str, list[str]]:
    """Return (verdict, alasan). Murni fungsi — gampang di-test."""
    from src.scoring import score_fundamentals

    f = fundamentals or {}
    fl = " ".join(flags or [])
    if f.get("error"):
        return ("TUNGGU", ["data gagal diambil"])
    if "harga tidak tersedia" in fl or "PER tidak wajar" in fl:
        return ("TUNGGU", ["flag pemblokir data — tunggu data valid"])
    s = score if isinstance(score, (int, float)) else score_fundamentals(f)[0]
    if s == float("-inf"):
        return ("TUNGGU", ["skor tak terhitung"])
    bearish = isinstance(regime, dict) and (
        regime.get("ihsg") or {}).get("di_atas_ma50") is False
    volatile = "volatilitas sangat tinggi" in fl
    if s >= 5 and not volatile and not bearish:
        return ("BELI", [f"skor {s:.1f} memenuhi ambang BELI"])
    if s >= 5:
        why = "volatilitas ekstrem" if volatile else BEARISH_MODIFIER
        return ("TUNGGU", [f"skor {s:.1f} terhalang {why}"])
    if s >= 2:
        return ("TUNGGU", [f"skor {s:.1f} di zona tunggu"])
    return ("JANGAN", [f"skor {s:.1f} di bawah ambang"])
