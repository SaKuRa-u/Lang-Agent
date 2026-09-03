"""Skor fundamental deterministik (tanpa LLM) untuk ranking tahap 1."""


def score_fundamentals(f: dict) -> tuple[float, list[str]]:
    """Return (skor, alasan). Skor lebih tinggi = lebih menarik."""
    if not f or f.get("error"):
        return (float("-inf"), ["data tidak tersedia"])

    score = 0.0
    reasons: list[str] = []

    pe = f.get("per")
    if isinstance(pe, (int, float)) and pe > 0:
        if pe <= 12:
            score += 2; reasons.append(f"PER murah {pe:.1f}x")
        elif pe <= 18:
            score += 1; reasons.append(f"PER wajar {pe:.1f}x")
        elif pe <= 25:
            reasons.append(f"PER agak premium {pe:.1f}x")
        else:
            score -= 1; reasons.append(f"PER mahal {pe:.1f}x")

    pbv = f.get("pbv")
    if isinstance(pbv, (int, float)) and pbv > 0:
        if pbv <= 1:
            score += 2; reasons.append(f"PBV murah {pbv:.2f}x")
        elif pbv <= 2:
            score += 1; reasons.append(f"PBV wajar {pbv:.2f}x")
        elif pbv <= 4:
            reasons.append(f"PBV premium {pbv:.2f}x")
        else:
            score -= 1; reasons.append(f"PBV sangat premium {pbv:.2f}x")

    dy = f.get("dividendYield") or 0
    if isinstance(dy, (int, float)) and dy > 1:
        dy = dy / 100  # toleransi bila sumber belum normalisasi
    if isinstance(dy, (int, float)) and dy > 0:
        if dy >= 0.05:
            score += 2; reasons.append(f"dividen {dy:.1%}")
        elif dy >= 0.03:
            score += 1; reasons.append(f"dividen {dy:.1%}")

    price, ma50 = f.get("price"), f.get("ma50")
    if isinstance(price, (int, float)) and isinstance(ma50, (int, float)) and ma50 > 0:
        if price > ma50:
            score += 1; reasons.append("di atas MA50")
        else:
            score -= 1; reasons.append("di bawah MA50")

    hi, lo = f.get("week52High"), f.get("week52Low")
    if all(isinstance(v, (int, float)) for v in (price, hi, lo)) and hi > lo:
        pos = (price - lo) / (hi - lo)
        if pos < 0.3:
            score += 1; reasons.append("dekat 52w low (murah)")
        elif pos > 0.8:
            score -= 1; reasons.append("dekat 52w high (mahal)")

    return (score, reasons or ["data minim"])
