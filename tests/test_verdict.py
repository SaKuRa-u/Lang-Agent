from unittest.mock import MagicMock, patch

from src.verdict import rule_verdict


def _fund(**kw):
    f = {"price": 100.0, "per": 10.0, "pbv": 1.5, "dividendYield": 0.05}
    f.update(kw)
    return f


def test_beli_on_strong_score():
    v, reasons = rule_verdict(_fund(), [], {})
    assert v == "BELI"
    assert reasons


def test_bearish_regime_downgrades_beli():
    regime = {"ihsg": {"di_atas_ma50": False}}
    v, reasons = rule_verdict(_fund(), [], regime)
    assert v == "TUNGGU"
    assert any("bearish" in r for r in reasons)


def test_blocking_flag_forces_tunggu():
    v, _ = rule_verdict({"price": None, "per": 10.0}, ["harga tidak tersedia"], {})
    assert v == "TUNGGU"


def test_weak_score_rejects():
    v, _ = rule_verdict({"price": 100.0, "per": 60.0, "pbv": 9.0,
                         "dividendYield": 0.0}, [], {})
    assert v == "JANGAN"


def test_error_data_waits():
    v, _ = rule_verdict({"ticker": "X.JK", "error": "boom"}, [], {})
    assert v == "TUNGGU"


def test_reporter_follows_guardrail_despite_llm_prose():
    from src.agents.reporter import reporter

    state = {"ticker": "BBCA.JK",
             "fundamentals": {"price": 100.0, "per": 60.0, "pbv": 9.0,
                              "dividendYield": 0.0},
             "sentiment": "netral", "history": [], "messages": []}
    with patch("src.agents.reporter.get_llm") as m:
        m.return_value.invoke.return_value = MagicMock(
            content="Laporan BELI fantastis!")
        out = reporter(state)
    assert out["recommendation"] == "JANGAN"
    # deterministik: prose boleh beda, verdict tetap
    with patch("src.agents.reporter.get_llm") as m:
        m.return_value.invoke.return_value = MagicMock(
            content="Laporan TUNGGU biasa.")
        out2 = reporter(state)
    assert out2["recommendation"] == out["recommendation"] == "JANGAN"
