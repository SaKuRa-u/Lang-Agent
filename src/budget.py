"""Perencana budget ala-Bibit: dana minimal, alokasi lot, profil risiko, horizon."""


def rupiah(n) -> str:
    try:
        return f"Rp{int(n):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "n/a"


def lot_price(fundamentals: dict):
    p = (fundamentals or {}).get("price")
    if isinstance(p, (int, float)) and p == p and p > 0:
        return int(p * 100)
    return None


def rank_for_risk(rows: list[dict], risk: str) -> list[dict]:
    """Urutkan baris scan sesuai profil: konservatif -> dividen,
    agresif -> CAGR historis, moderat -> skor komposit."""
    def key_div(r):
        return (r.get("fundamentals", {}).get("dividendYield") or 0)

    def key_cagr(r):
        c = r.get("fundamentals", {}).get("cagr_3y")
        return c if isinstance(c, (int, float)) else float("-inf")

    if risk == "konservatif":
        return sorted(rows, key=lambda r: (key_div(r), r.get("score", 0)), reverse=True)
    if risk == "agresif":
        return sorted(rows, key=lambda r: (key_cagr(r), r.get("score", 0)), reverse=True)
    return sorted(rows, key=lambda r: r.get("score", 0), reverse=True)


def plan_budget(monthly: int, picks: list[dict], horizon_months=None) -> dict:
    """Alokasi lot bulanan per pick (bobot = skor), dana minimal, sisa.

    picks: [{ticker, score, fundamentals}]. Return dict siap render/teks.
    """
    lots = []
    total = 0
    for p in picks:
        lp = lot_price(p.get("fundamentals", {}))
        w = max(p.get("score", 0), 0) + 1
        lots.append({"ticker": p["ticker"], "lot_price": lp, "weight": w,
                     "lots": 0, "cost": 0})
    wsum = sum(x["weight"] for x in lots) or 1
    for x in lots:
        if x["lot_price"]:
            x["lots"] = int(monthly * x["weight"] / wsum // x["lot_price"])
            x["cost"] = x["lots"] * x["lot_price"]
            total += x["cost"]
    priced = [x["lot_price"] for x in lots if x["lot_price"]]
    cheapest = min(priced) if priced else None
    notes = []
    if cheapest and monthly < cheapest:
        n = (cheapest + monthly - 1) // monthly
        notes.append(f"budget belum cukup 1 lot termurah ({rupiah(cheapest)}): "
                     f"tabung {n} bulan, atau pakai platform fraksional/odd-lot, "
                     "atau reksadana mulai Rp10rb-an")
    if horizon_months is not None and horizon_months < 12:
        notes.append(f"horizon {horizon_months} bulan < 12 bulan: saham berisiko "
                     "untuk jangka pendek — pertimbangkan pasar uang/reksadana "
                     "pendapatan tetap")
    return {"monthly": monthly, "lots": lots, "total_cost": total,
            "remainder": monthly - total, "cheapest_lot": cheapest,
            "horizon_months": horizon_months, "notes": notes}


def allocation_text(plan: dict) -> str:
    """Blok teks alokasi untuk prompt LLM."""
    lines = [f"Budget/bulan {rupiah(plan['monthly'])}, "
             f"profil: dipakai untuk bobot skor."]
    for x in plan["lots"]:
        if x["lot_price"]:
            lines.append(f"- {x['ticker']}: {x['lots']} lot x {rupiah(x['lot_price'])} "
                         f"= {rupiah(x['cost'])} (dana minimal mulai: {rupiah(x['lot_price'])})")
        else:
            lines.append(f"- {x['ticker']}: harga tak tersedia — dana minimal belum bisa dihitung")
    lines.append(f"Total belanja: {rupiah(plan['total_cost'])}, sisa: {rupiah(plan['remainder'])}")
    for n in plan["notes"]:
        lines.append(f"Catatan: {n}")
    return "\n".join(lines)
