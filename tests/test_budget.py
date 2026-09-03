from src.universe import (parse_budget_idr, parse_horizon_months, parse_risk,
                          parse_batch_request)
from src.budget import allocation_text, lot_price, plan_budget, rank_for_risk, rupiah


def test_parse_budget_variants():
    assert parse_budget_idr("modal 100rb per bulan") == 100_000
    assert parse_budget_idr("budget 100 ribu") == 100_000
    assert parse_budget_idr("Rp100.000 per bulan") == 100_000
    assert parse_budget_idr("dana 2 juta") == 2_000_000
    assert parse_budget_idr("1jt sebulan") == 1_000_000
    assert parse_budget_idr("analisa BBCA top 5") is None
    assert parse_budget_idr("proyeksi 1 tahun") is None


def test_parse_risk_horizon():
    assert parse_risk("saya konservatif") == "konservatif"
    assert parse_risk("growth agresif ya") == "agresif"
    assert parse_risk("analisa BBCA") == "moderat"
    assert parse_horizon_months("untuk 1 tahun kedepan") == 12
    assert parse_horizon_months("nabung 6 bulan") == 6
    assert parse_horizon_months("analisa BBCA") is None


def test_parse_request_carries_bibit_fields():
    out = parse_batch_request("modal 100rb per bulan untuk 2 tahun, saya konservatif")
    assert out["budget_monthly"] == 100_000
    assert out["horizon_months"] == 24
    assert out["risk"] == "konservatif"


def _row(ticker, score, dy=0.0, cagr=0.0, price=1000.0):
    return {"ticker": ticker, "score": score,
            "fundamentals": {"price": price, "dividendYield": dy, "cagr_3y": cagr}}


def test_rank_tilts_by_risk():
    rows = [_row("A.JK", 5, dy=0.02, cagr=0.20),
            _row("B.JK", 6, dy=0.10, cagr=0.01)]
    assert rank_for_risk(rows, "konservatif")[0]["ticker"] == "B.JK"
    assert rank_for_risk(rows, "agresif")[0]["ticker"] == "A.JK"
    assert rank_for_risk(rows, "moderat")[0]["ticker"] == "B.JK"


def test_plan_budget_lots_and_minimum():
    picks = [{"ticker": "A.JK", "score": 3.0, "fundamentals": {"price": 3000.0}},
             {"ticker": "B.JK", "score": 1.0, "fundamentals": {"price": 500.0}}]
    plan = plan_budget(1_000_000, picks)
    by = {x["ticker"]: x for x in plan["lots"]}
    # bobot 4:2 -> A: 666rb -> 2 lot @300rb; B: 333rb -> 6 lot @50rb
    assert by["A.JK"]["lot_price"] == 300_000
    assert by["B.JK"]["lots"] == 6
    assert by["A.JK"]["lots"] == 2
    assert plan["total_cost"] == 900_000
    assert plan["remainder"] == 100_000
    txt = allocation_text(plan)
    assert "Rp300.000" in txt and "dana minimal" in txt


def test_plan_budget_too_small_suggests_saving():
    picks = [{"ticker": "A.JK", "score": 1.0, "fundamentals": {"price": 5000.0}}]
    plan = plan_budget(100_000, picks)
    assert plan["lots"][0]["lots"] == 0
    assert any("tabung 5 bulan" in n for n in plan["notes"])


def test_plan_budget_short_horizon_warns():
    picks = [{"ticker": "A.JK", "score": 1.0, "fundamentals": {"price": 100.0}}]
    plan = plan_budget(100_000, picks, horizon_months=6)
    assert any("jangka pendek" in n for n in plan["notes"])


def test_rupiah():
    assert rupiah(677500) == "Rp677.500"
    assert rupiah(None) == "n/a"
    assert lot_price({}) is None
